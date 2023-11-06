from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpResponseRedirect

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
