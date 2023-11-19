# from dotenv import load_dotenv
import os
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import HttpResponseBadRequest
import requests
import time
import json

CLIENT_ID = "{CLIENT_ID}"
CLIENT_SECRET = "{CLIENT_SECRET}"
GPT_KEY = "{GPT_KEY}"

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
    data = {
        "model": "gpt-4-1106-preview",
        "messages": [
            {"role": "system", "content": f"{input_text}\n{target_lang} translation:"},
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


# translate_to_text: 음성을 넣었을 때 target_lang에 해당하는 텍스트 문장 생성
@csrf_exempt
def translate_to_text(request):
    if request.method == 'GET':
        return render(request, 'convert/language_ribbon.html')

    elif request.method == 'POST':
        lang = request.POST.get('lang')
        target_lang = request.POST.get('target-lang')

        if lang != 'kr' or target_lang != 'en':
            # 한국어 -> 영어 이외의 case는 영어 STT 모델이 붙은 후 개발 진행
            return HttpResponseBadRequest('아직 만들어지지 않았어요')

        jwt_token = authenticate()
        transcribe_id = transcribe(jwt_token, request.FILES['audio'])
        transcription_status = get_transcription_status(jwt_token, transcribe_id)

        formatted_data = json.dumps(transcription_status, ensure_ascii=False)

        data = json.loads(formatted_data)

        utterances = data['results']['utterances']
        msgs = [utterance['msg'] for utterance in utterances]

        translate_results = [translate_text(msg, target_lang) for msg in msgs]

        results = {
            "targetLang": target_lang,
            "original_messages(임의로 넣음)": msgs,
            "translation": translate_results
        }

        return HttpResponse(json.dumps(results, ensure_ascii=False), content_type="application/json")


# translate_to_voice: 음성을 넣었을 때 target_lang에 해당하는, 목소리 변조된 음성 출력(미완성)
@csrf_exempt
def translate_to_voice(request):
    if request.method == 'GET':
        return render(request, 'convert/language_ribbon.html')

    elif request.method == 'POST':
        lang = request.POST.get('lang')
        target_lang = request.POST.get('target-lang')

        if lang != 'kr' or target_lang != 'en':
            # 한국어 -> 영어 이외의 case는 영어 STT 모델이 붙은 후 개발 진행
            return HttpResponseBadRequest('아직 만들어지지 않았어요')

        jwt_token = authenticate()
        transcribe_id = transcribe(jwt_token, request.FILES['audio'])
        transcription_status = get_transcription_status(jwt_token, transcribe_id)

        formatted_data = json.dumps(transcription_status, ensure_ascii=False)

        data = json.loads(formatted_data)

        utterances = data['results']['utterances']
        msgs = [utterance['msg'] for utterance in utterances]

        translate_results = [translate_text(msg, target_lang) for msg in msgs]

        results = {
            "targetLang": target_lang,
            "original_messages(임의로 넣음)": msgs,
            "translation": translate_results
        }

        return HttpResponse(json.dumps(results, ensure_ascii=False), content_type="application/json")