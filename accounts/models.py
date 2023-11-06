from django.contrib.auth.models import User
from django.db import models

# Create your models here.
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    sex = models.IntegerField()
    age = models.IntegerField()
    job = models.IntegerField()
    englishLevel = models.IntegerField()

    class Meta:
        app_label = 'accounts'
