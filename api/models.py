from django.db import models
from .utils import *
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify





# Create your models here.


#Domain
class Domain(models.Model):
    name = models.CharField(max_length=20)
    use_case = models.ForeignKey(
        UseCase,
        on_delete=models.CASCADE,
        related_name="approved_tool_category"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class UseCase(models.Model):
    description = models.CharField(max_length=200)

# Favorite
 class Favorite(models.Model):
    user = models.ForeignKey(UserProfile, related_name='user_favorites', on_delete=models.CASCADE)
    tool = models.ForeignKey('Tool',  related_name='tool', on_delete=models.CASCADE)
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
  





# class UserProfile(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     submissions = models.ManyToManyField('ToolSuggestion', related_name='my_submissions', blank=True) # Users can submit multiple tools
#     my_favorites = models.ManyToManyField('Favorite', related_name='my_favorites', blank=True) # Tools user likes
    # Explicitly define groups and user_permissions with unique related_name
    # THESE ARE NEEDED IF YOU ARE SUBCLASING ABSTRACTUSER
    # groups = models.ManyToManyField(
    #     'auth.Group',
    #     verbose_name='groups',
    #     blank=True,
    #     help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
    #     related_name="userprofile_groups",  # Unique related_name
    #     related_query_name="userprofile",
    # )
    # user_permissions = models.ManyToManyField(
    #     'auth.Permission',
    #     verbose_name= 'user permission',
    #     blank=True,
    #     help_text='Specific permissions for this user',
    #     related_name="userprofile_user_permissions",  # Unique related_name
    #     related_query_name="userprofile",
    # )
    
    
    # def __str__(self):
    #     return f"{self.user}"
    
    

  
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
    
    




