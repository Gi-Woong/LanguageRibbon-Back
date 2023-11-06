from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignupForm(UserCreationForm):
    name = forms.CharField(max_length=100)
    sex = forms.IntegerField()
    age = forms.IntegerField()
    job = forms.IntegerField()
    englishLevel = forms.IntegerField()

    class Meta:
        model = User
        fields = ('username', 'name', 'sex', 'age', 'job', 'englishLevel', 'password1', 'password2')
