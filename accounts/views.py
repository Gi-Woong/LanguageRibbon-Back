import json
import logging
import tempfile
import time

import environ
import requests
import nlptutti as metrics
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from .forms import SignupForm
from .models import UserProfile

ENV = environ.Env(DEBUG=(bool, True))
environ.Env.read_env()

logger = logging.getLogger(__name__)

CLIENT_ID = ENV('CLIENT_ID')
CLIENT_SECRET = ENV('CLIENT_SECRET')
GPT_KEY = ENV('GPT_KEY')
HUG_KEY = ENV('HUG_KEY')


@csrf_exempt  # CSRF 보호 기능 비활성화
def login(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            response_json = {}
            auth_login(request, form.get_user())
            profile = UserProfile.objects.filter(user_id=form.get_user().id)
            profile_exists = profile.exists()
            if profile_exists:
                response_json["voice_info_en"] = True if profile.get().voice_info_en else False
                response_json["voice_info_kr"] = True if profile.get().voice_info_kr else False
                response_json["name"] = profile.get().name
            return JsonResponse(response_json, status=200)
        else:
            return JsonResponse({"error": "Invalid login details"}, status=400)
    else:
        form = AuthenticationForm()
    context = {"form": form}
    return render(request, "registration/login.html", context)


@csrf_exempt  # CSRF 보호 기능 비활성화
def logout(request):
    if request.user.is_active:
        auth_logout(request)
        json_response = JsonResponse({"message": "user logout done."})
        redirect_url = '/'
        response = HttpResponseRedirect(redirect_url)
        response['X-Json-Response'] = json_response.content  # JSON 응답을 응답 헤더에 추가
        return json_response
    return redirect("login")


@csrf_exempt  # CSRF 보호 기능 비활성화
def signup(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            user_profile = UserProfile(
                user=user,
                name=form.cleaned_data.get('name'),
                sex=form.cleaned_data.get('sex'),
                age=form.cleaned_data.get('age'),
                job=form.cleaned_data.get('job'),
                englishLevel=form.cleaned_data.get('englishLevel')
            )
            user_profile.save()

            user = authenticate(username=form.cleaned_data.get('username'), password=form.cleaned_data.get('password1'))
            auth_login(request, user)

            return JsonResponse({"message": "회원가입이 정상적으로 완료되었습니다."})

    else:
        form = SignupForm()

    context = {"form": form}
    return render(request, "registration/signup.html", context)


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


def get_response_based_on_cer(cer):
    if cer <= 0.3:
        return JsonResponse(
            {"uploadSuccess": True, "confirm": True, "message": "초기 목소리 데이터 수집에 성공했습니다.",
             "metric": {"cer": cer}})
    else:
        return JsonResponse(
            {"uploadSuccess": True, "confirm": False, "message": "초기 목소리 데이터 수집에 실패했습니다.",
             "metric": {"cer": cer}})


@csrf_exempt  # CSRF 보호 기능 비활성화
def uploadvoice(request):
    if request.method == 'POST':
        lang = request.POST.get('lang', 'kr')  # 'lang' 값 받기, 기본값은 'kr'
        audio_file = request.FILES.get('audio')  # 'audio'라는 이름의 파일

        # audio_file이 None이거나, lang이 'kr' 또는 'en'이 아닌 경우에 대한 예외 처리
        if not audio_file or lang not in ['kr', 'en']:
            return JsonResponse({"message": "잘못된 요청입니다."})

        elif lang == 'en':

            file_path = get_temporary_file_path(audio_file)

            transcription_status = eng_translate_voice_to_text(file_path)

            formatted_data = json.dumps(transcription_status, ensure_ascii=False)

            data_en = json.loads(formatted_data)

            received_text = data_en['text']  # STT 값

            original_script = "Eat well, Sleep well, and Stay healthy!"  # 스크립트

            result = metrics.get_cer(received_text, original_script)

            cer = result['cer']
            substitutions = result['substitutions']
            deletions = result['deletions']
            insertions = result['insertions']

            print(original_script)
            print(received_text)
            print(cer)
            print(substitutions)
            print(deletions)
            print(insertions)

            return get_response_based_on_cer(cer)
        
        elif lang == 'kr':

            jwt_token = authenticate()
            transcribe_id = transcribe(jwt_token, request.FILES['audio'])
            transcription_status = get_transcription_status(jwt_token, transcribe_id)

            formatted_data = json.dumps(transcription_status, ensure_ascii=False)

            data = json.loads(formatted_data)

            utterances = data['results']['utterances']
            msgs = ' '.join([utterance['msg'] for utterance in utterances])

            original_script = "잘 먹고 잘 자고 건강하세요"  # 스크립트

            result = metrics.get_cer(msgs, original_script)

            cer = result['cer']
            substitutions = result['substitutions']
            deletions = result['deletions']
            insertions = result['insertions']

            print(original_script)
            print(msgs)
            print(cer)
            print(substitutions)
            print(deletions)
            print(insertions)

            return get_response_based_on_cer(cer)

    else:
        return JsonResponse({"message": "POST 요청이 아닙니다."})
