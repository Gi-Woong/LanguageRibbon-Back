import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
import requests
import time
import json
from gtts import gTTS
import tempfile
from config.settings import ENV
from config.s3 import s3, bucket_name
from pydub import AudioSegment
from accounts.models import UserProfile

CLIENT_ID = ENV('CLIENT_ID')
CLIENT_SECRET = ENV('CLIENT_SECRET')
GPT_KEY = ENV('GPT_KEY')
HUG_KEY = ENV('HUG_KEY')

logger = logging.getLogger(__name__)


# TODO: 임시로 만든 home 컨트롤러임(추후 삭제 필요)
def home(request):
    data = {
        "message": "welcome!",
        "login": False
    }
    if request.user.is_authenticated:
        data["login"] = True
    return JsonResponse(data)


# 한국어 STT: 사용자 인증 위한 JWT 토큰 발급
@csrf_exempt
def authenticate():
    url = "https://openapi.vito.ai/v1/authenticate"
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    response = requests.post(url, headers=headers, data=data)
    response_data = response.json()
    jwt_token = response_data.get('access_token')
    logger.info("Authentication successful")

    return jwt_token


# 한국어 STT: 음성 파일 업로드 후 transcribe_id 받음
@csrf_exempt
def transcribe(jwt_token, audio_file):
    url = "https://openapi.vito.ai/v1/transcribe"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {jwt_token}'
    }
    files = {
        'file': audio_file,
        'config': (None, '{}')
    }

    response = requests.post(url, headers=headers, files=files)
    response_data = response.json()
    transcribe_id = response_data.get('id')
    logger.info("Transcription initiated")

    return transcribe_id


# 한국어 STT: transcribe_id로 결과 텍스트 받음
@csrf_exempt
def get_transcription_status(jwt_token, transcribe_id):
    url = f"https://openapi.vito.ai/v1/transcribe/{transcribe_id}"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {jwt_token}'
    }

    while True:
        response = requests.get(url, headers=headers)
        response_data = json.loads(response.content.decode('utf-8'))

        if response_data.get('status') != 'transcribing':
            break

        time.sleep(0.1)

    return response_data


# GPT 번역 과정: body의 target_lang과 생성된 텍스트를 넣고 번역 수행
@csrf_exempt
def translate_text(input_text, target_lang):
    if target_lang == 'kr':
        target_lang = 'korean'
    else:
        target_lang = 'english'

    data = {
        "model": "gpt-4-1106-preview",
        "messages": [
            {"role": "system",
             "content": f"{input_text}\n To {target_lang}, Rule: Translate the sentence exactly as it is.:"},
        ],
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {GPT_KEY}'
    }

    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, data=json.dumps(data))

    response_json = response.json()

    try:
        translated_text = response_json['choices'][0]['message']['content']
    except KeyError as error:
        print(f"Error: {error}")
        translated_text = str(error)

    return translated_text


def translate_text_to_voice(text, target_lang):
    if target_lang == 'kr':
        target_lang = 'ko'

    tts = gTTS(text=text, lang=target_lang)
    filename = f"{target_lang}_translated_voice.mp3"
    tts.save(filename)
    return filename


def eng_translate_voice_to_text(filename):
    API_URL = "https://api-inference.huggingface.co/models/jonatasgrosman/wav2vec2-large-xlsr-53-english"
    headers = {"Authorization": f'Bearer {HUG_KEY}'}

    with open(filename, "rb") as f:
        data = f.read()
    response = requests.post(API_URL, headers=headers, data=data)
    return response.json()


def get_temporary_file_path(file):
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    for chunk in file.chunks():
        temp_file.write(chunk)
    temp_file.close()
    return temp_file.name

# translate_to_voice: 음성을 넣었을 때 target_lang에 해당하는, 목소리 변조된 음성 출력(변조 미완성)
@csrf_exempt
def translate_to_voice(request):
    if request.method == 'GET':
        return render(request, 'convert/language_ribbon.html')

    elif request.method == 'POST':
        lang = request.POST.get('lang')
        target_lang = request.POST.get('target-lang')

        if lang == 'en' and target_lang == 'kr':
            file_path = get_temporary_file_path(request.FILES['audio'])

            transcription_status = eng_translate_voice_to_text(file_path)

            formatted_data = json.dumps(transcription_status, ensure_ascii=False)

            data = json.loads(formatted_data)

            msgs = [data['text']]

            translate_results = [translate_text(msg, target_lang) for msg in msgs]

            voice_files = [translate_text_to_voice(result, target_lang) for result in translate_results][0]
            print(f"{request.user.id}_{lang}")
            response = s3.get_object(Bucket=bucket_name,
                                     Key=UserProfile.objects.get(user_id=request.user.id).voice_info_kr)
            object_data = response['Body'].read()
            print(voice_files)
            wav_path = voice_files.rstrip(".mp3") + ".wav"
            AudioSegment.from_mp3(voice_files).export(wav_path, format="wav")
            files = {
                'file1': open(wav_path, 'rb'),  # 첫 번째 음성 파일
                'file2': object_data  # 두 번째 음성 파일
            }
            url = f"{ENV('AWS_DIFF_VC_SERVER')}/convert"
            diff_vc_response = requests.post(url, files=files)

            results = {
                "targetLang": target_lang,
                "original_messages(영어 문장)": msgs,
                "translation(한국어 문장)": translate_results,
                "voice_files": voice_files
            }

            # Django HttpResponse 생성
            response = HttpResponse(content_type='audio/wav')  # WAV 형식의 MIME 타입으로 설정
            response['Content-Disposition'] = 'attachment; filename="audio.wav"'  # WAV 파일 이름 설정
            response.write(diff_vc_response.content)  # 음성 파일을 HttpResponse에 작성

            # JSON 데이터를 응답 헤더에 추가
            response['X-Json-Response'] = results
            return response
            # return HttpResponse(json.dumps(results, ensure_ascii=False), content_type="application/json")

        if lang == 'kr' and target_lang == 'en':
            jwt_token = authenticate()
            transcribe_id = transcribe(jwt_token, request.FILES['audio'])
            transcription_status = get_transcription_status(jwt_token, transcribe_id)

            formatted_data = json.dumps(transcription_status, ensure_ascii=False)

            data = json.loads(formatted_data)

            utterances = data['results']['utterances']
            msgs = [utterance['msg'] for utterance in utterances]

            translate_results = [translate_text(msg, target_lang) for msg in msgs]

            voice_files = [translate_text_to_voice(result, target_lang) for result in translate_results][0]
            print(f"{request.user.id}_{lang}")
            response = s3.get_object(Bucket=bucket_name,
                                     Key=UserProfile.objects.get(user_id=request.user.id).voice_info_en)
            object_data = response['Body'].read()
            print(voice_files)
            wav_path = voice_files.rstrip(".mp3") + ".wav"
            AudioSegment.from_mp3(voice_files).export(wav_path, format="wav")
            files = {
                'file1': open(wav_path, 'rb'),  # 첫 번째 음성 파일
                'file2': object_data  # 두 번째 음성 파일
            }
            url = f"{ENV('AWS_DIFF_VC_SERVER')}/convert"
            diff_vc_response = requests.post(url, files=files)

            results = {
                "targetLang": target_lang,
                "original_messages(한국어 문장)": msgs,
                "translation(영어 문장)": translate_results,
                "voice_files": voice_files
            }

            # Django HttpResponse 생성
            response = HttpResponse(content_type='audio/wav')  # WAV 형식의 MIME 타입으로 설정
            response['Content-Disposition'] = 'attachment; filename="audio.wav"'  # WAV 파일 이름 설정
            response.write(diff_vc_response.content)  # 음성 파일을 HttpResponse에 작성

            # JSON 데이터를 응답 헤더에 추가
            response['X-Json-Response'] = results
            return response
            # return HttpResponse(json.dumps(results, ensure_ascii=False), content_type="application/json")

    return HttpResponseBadRequest('지원하지 않는 언어 조합입니다.')
