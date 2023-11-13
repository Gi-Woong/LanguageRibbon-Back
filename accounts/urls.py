# from django.contrib import admin
from django.urls import path, include
# from django.shortcuts import redirect
# from allauth.socialaccount.providers.kakao import views as kakao_views
from accounts import views

urlpatterns = [
    path("login/", views.login, name="login"),
    # path("social/", kakao_views.oauth2_login),
    path("", include("allauth.socialaccount.providers.kakao.urls")),
    path("logout/", views.logout, name="logout"),
    path("signup/", views.signup, name="signup"),
    path("uploadvoice/", views.uploadvoice, name="uploadvoice"),
]
