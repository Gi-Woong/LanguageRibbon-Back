from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    name = models.CharField(max_length=200)
    sex = models.CharField(max_length=10)
    age = models.IntegerField()
    job = models.CharField(max_length=200)
    englishLevel = models.CharField(max_length=10)

    class Meta:
        db_table = 'accounts_userprofile'

