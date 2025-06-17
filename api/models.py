from django.db import models
from django.contrib.auth.models import User
from .utils import *
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator 
from django.utils.text import slugify

# For syllable calculations
import textstat





# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE
    )
    is_logged_in = models.BooleanField(default=False)
    payment_status = models.CharField(max_length=20, default='unpaid')
    subscription_expiry = models.DateField(null=True, blank=True)
    access_tier = models.CharField(max_length=20, default='free')
    isPaid = models.BooleanField( default='False')

    def __str__(self):
        return self.user.username
    
    



# Options for Name model
class RegStatusOptions(models.TextChoices):
    PENDING = 'pending', 'Pending'
    AVAILABLE = 'available', 'Available'
    TAKEN = 'taken', 'Taken'
    UNVERIFIED = 'unverified', 'Unverified'

class ExtensionOptions(models.TextChoices):
    ALL_EXTENSIONS = 'all_extensions', 'All_extensions'
    COM = 'com', 'Com'
    CO = 'co', 'Co'
    IO = 'io', 'Io'
    AI = 'ai', 'Ai'


class DifficultyType(models.TextChoices):
    EASY = 'easy', 'Easy'
    MODERATE = 'moderate', 'Moderate'
    HARD = 'hard', 'Hard'

class CompetitionType(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'


class DomainListOptions(models.TextChoices):
    ALL_LIST = 'all_list', 'All List'
    PENDING_DELETE = 'pending_delete', 'Pending Delete'
    DELETED = 'deleted', 'Deleted'
    MARKETPLACE = 'marketplace', 'Marketplace'


#NAME MODEL
class Name(models.Model):
    domain_name = models.CharField(max_length=20)
    extension = models.CharField(
        max_length=20,
        choices = ExtensionOptions.choices,
        default = ExtensionOptions.ALL_EXTENSIONS
    )
    domain_list = models.CharField(
        max_length=50,
        choices = DomainListOptions.choices,
        default = DomainListOptions.PENDING_DELETE
    )
    status = models.CharField(
        max_length = 20,
        choices = RegStatusOptions.choices,
        default = RegStatusOptions.PENDING,
        unique = True
    )
    length = models.PositiveIntegerField(
        editable=False,
        null=True,
        blank=True
    )
    syllables = models.PositiveIntegerField(
        editable=False,
        null=True,
        blank=True
    )
    use_cases = models.ManyToManyField(
        'UseCase', 
        related_name="domain_use_cases"
    )
    competition = models.CharField(
        max_length=20,
        choices=CompetitionType.choices,
        null=True,
        blank=True
    )
    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyType.choices,
        null=True,
        blank=True
    )
    suggested_usecase = models.ForeignKey(
        'UseCase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggested_for'
    )
    is_top_rated = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    category = models.ForeignKey(
        'NameCategory',
        on_delete=models.SET_NULL,
        null=True,
        related_name='names'
    )
    tag = models.ManyToManyField(
        'NameTag',
        related_name='names'
    )
    drop_date = models.DateField(
        default=timezone.now,
        help_text="Default to current time if not specified"
    )
    drop_time = models.DateTimeField(
        default=timezone.now,
        help_text="Default to current time if not specified"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    
    def save(self, *args, **kwargs):
        # If length and syllables are not already set (first save), calculate them.
        if self.length is None or self.syllables is None:
            name_part = self.domain_name.split('.')[0]  # Exclude extension
            self.length = len(name_part)
            self.syllables = textstat.syllable_count(name_part)
        super().save(*args, **kwargs)


    def __str__(self):
        return self.domain_name


# CATEGORY MODEL
class CategoryType(models.TextChoices):
    HEALTH = 'health_and_wellness', 'Health_And_Wellness'
    TECH = 'tech', 'Tech'
 
class NameCategory(models.Model):
    name = models.CharField(
        max_length=20, 
        unique=True,
        choices=CategoryType.choices,
    )
    
    def __str__(self):
        return self.name

#TAG MODEL
class NameTag(models.Model):
    name = models.CharField(
        max_length=20,
        unique=True
    )

    def __str__(self):
        return self.name




#OPTIONS FOR USECASE MODEL
class RevenueOptions(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'

class UseCase(models.Model):
    domain_name = models.ForeignKey(
        Name,
        on_delete=models.CASCADE,
        related_name='use_cases_domain'
    )
    case_title = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyType.choices
    )
    competition = models.CharField(
        max_length=20,
        choices=DifficultyType.choices
    )
    target_market = models.CharField(max_length=20)
    revenue_potential = models.CharField(
        max_length=20,
        choices=RevenueOptions.choices
    )
    order = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )

    class Meta:
        unique_together = ('domain_name', 'order')  # Enforce unique order per Name

    def __str__(self):
        return f"{self.case_title} for {self.domain}"





# ============================================
# Model to define Drop Time Rules Per Extension
# ============================================

class ExtensionDropInfo(models.Model):
    """
    Holds expected drop processing times per domain extension (.com, .co, .ai, .io),
    allowing availability check schedules to be dynamically adjusted in Celery tasks.
    """
    extension = models.CharField(max_length=10, unique=True)  
    first_check_delay_hours = models.PositiveIntegerField(default=2)  # Delay after drop to run first check
    second_check_delay_hours = models.PositiveIntegerField(default=12)  # Delay for second check (if still unverified)

    def __str__(self):
        return f"{self.extension} drop timing rules"



# ============================================
# Model to Archive Names Older Than 90 Days
# ============================================

class ArchivedName(models.Model):
    """
    Stores minimal details of domain names whose drop dates exceeded 90 days,
    for historical reference while freeing up main Name table space.
    """
    domain_name = models.CharField(max_length=20)
    extension = models.CharField(max_length=10)
    original_drop_date = models.DateField()
    archived_on = models.DateTimeField(auto_now_add=True)  # When this record was archived

    def __str__(self):
        return f"Archived: {self.domain}{self.extension} (Dropped: {self.original_drop_date})"


    
    
    

     


    
    
# class NewsLetter(models.Model):
#     email = models.CharField(unique=True, max_length=255) #Added max_length
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.email

    
# class Support(models.Model):
#     subject = models.CharField(max_length=50)
#     message = models.TextField()
#     email = models.EmailField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.subject
    
    




# Subscription type
# class SubscriptionType(models.TextChoices):
#     FREE = 'free', 'Free'
#     PAID = 'paid', 'Paid'
#     FREEMIUM = 'freemium', 'Freemium'



# class PlanModel(models.Model):
#     type = models.CharField(
#         max_length=20,
#         choices=SubscriptionType.choices,
#         unique=True,
#     )
    
#     def __str__(self):
#         return self.type
  




# # Favorite
# class Favorite(models.Model):
#     # user = models.ForeignKey(UserProfile, related_name='user_favorites', on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.user

