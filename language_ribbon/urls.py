from django.urls import path, include
from . import views

urlpatterns = [
    path("translate/to_voice", views.translate_to_voice, name="translate_to_voice"),
]
