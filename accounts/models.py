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
    voice_info_kr = models.CharField(max_length=(200), null=True)
    voice_info_en = models.CharField(max_length=(200), null=True)

    class Meta:
        app_label = 'accounts'
