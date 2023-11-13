import requests
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from .forms import SignupForm
from django.contrib.auth import authenticate

from .models import UserProfile


def login(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect("/")
    else:
        form = AuthenticationForm()
    context = {"form": form}
    return render(request, "registration/login.html", context)


def logout(request):
    if request.user.is_active:
        auth_logout(request)
        json_response = JsonResponse({"message": "user logout done."})
        redirect_url = '/'
        response = HttpResponseRedirect(redirect_url)
        response['X-Json-Response'] = json_response.content  # JSON 응답을 응답 헤더에 추가
        return response
    return redirect("login")


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

            user = authenticate(request, username=user.username, password=form.cleaned_data.get('password1'))
            auth_login(request, user)

            return JsonResponse({"message": "회원가입이 정상적으로 완료되었습니다."})

    else:
        form = SignupForm()

    context = {"form": form}
    return render(request, "registration/signup.html", context)

@csrf_exempt # CSRF 보호 기능 비활성화
def uploadvoice(request):
    if request.method == 'POST':
        audio_file = request.FILES['audio'] # 'audio'라는 이름의 파일
        url = "https://backend-api.languageribbon.kro.kr/uploadvoice"
        headers = {'Content-Type': 'multipart/form-data'}
        data = {'lang': 'kr'}
        files = {'audio': audio_file}

        response = requests.post(url, headers = headers, data = data, files = files)

        if response.status_code == 200:
            data = response.json()
            cer = data['metric']['cer']
            if cer <= 0.3:
                return render(request, "registration/uploadvoice.html", {"uploadSuccess": True, "confirm": True, "message": "초기 목소리 데이터 수집에 성공했습니다.", "metric": {"cer": cer}})
            elif cer > 0.3:
                return render(request, "registration/uploadvoice.html", {"uploadSuccess": True, "confirm": False, "message": "초기 목소리 데이터 수집에 실패했습니다.", "metric": {"cer": cer}})
        else:
            return render(request, "registration/uploadvoice.html", {"message": "POST 요청 실패"})
    else:
        return render(request, "registration/uploadvoice.html")


