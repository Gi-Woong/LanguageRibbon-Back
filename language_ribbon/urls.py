from django.urls import path, include
from . import views

urlpatterns = [
    path("translate/to_text", views.translate_to_text, name="translate_to_text"),
    path("translate/to_voice", views.translate_to_voice, name="translate_to_voice"),
]
