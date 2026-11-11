from django.db import models
from django.contrib.auth.models import User
class userProfile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    age=models.IntegerField(null=True,blank=True)
    height=models.FloatField(null=True,blank=True)
    weight=models.FloatField(null=True,blank=True)
    fitness_goal=models.CharField(max_length=100,blank=True)
    experience_level=models.CharField(max_length=50,blank=True)
    def __str__(self):
        return self.user.username
# Create your models here