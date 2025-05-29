from django.db import models
from django.contrib.auth.models import User
from .utils import *
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify





# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_logged_in = models.BooleanField(default=False)
    payment_status = models.CharField(max_length=20, default='unpaid')
    subscription_expiry = models.DateField(null=True, blank=True)
    access_tier = models.CharField(max_length=20, default='free')

    def __str__(self):
        return self.user.username
    
    

  




#Domain
class Domain(models.Model):
    name = models.CharField(max_length=20)
    use_case = models.ForeignKey(
        'UseCase',
        on_delete=models.CASCADE,
        related_name="approved_tool_category"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



# Options for execution difficulty
class DifficultyType(models.TextChoices):
    EASY = 'easy', 'Easy'
    MEDIUM = 'medium', 'Medium'
    HARD = 'hard', 'Hard'


class UseCase(models.Model):
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    difficulty = models.CharField(
        max_length=20,
        choices = DifficultyType.choices,
        unique = True
        )
















# Favorite
class Favorite(models.Model):
    # user = models.ForeignKey(UserProfile, related_name='user_favorites', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user


# Subscription type
class SubscriptionType(models.TextChoices):
    FREE = 'free', 'Free'
    PAID = 'paid', 'Paid'
    FREEMIUM = 'freemium', 'Freemium'



class PlanModel(models.Model):
    type = models.CharField(
        max_length=20,
        choices=SubscriptionType.choices,
        unique=True,
    )
    
    def __str__(self):
        return self.type
  





class CategoryType(models.TextChoices):
    HEALTH = 'health_and_wellness', 'Health_And_Wellness'
    TECH = 'tech', 'Tech'
 

class Category(models.Model):
    name = models.CharField(
        max_length=50, 
        unique=True,
        choices=CategoryType.choices,
    )
    display_name = models.CharField(max_length=50)
    
    def __str__(self):
        return self.name
    
    

    
    
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, blank=False)
    
    def save(self, *args, **kwargs):
        # Clean JSON strings before saving
        if isinstance(self.name, str) and self.name.startswith('['):
            try:
                parsed = json.loads(self.name)
                self.name = parsed[0] if isinstance(parsed, list) else parsed
            except json.JSONDecodeError:
                pass
        self.name = self.name.lower().strip()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name
     


    
    
class NewsLetter(models.Model):
    email = models.CharField(unique=True, max_length=255) #Added max_length
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email

    
class Support(models.Model):
    subject = models.CharField(max_length=50)
    message = models.TextField()
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject
    
    




