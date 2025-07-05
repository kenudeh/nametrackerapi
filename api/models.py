from django.db import models
from django.contrib.auth.models import User
from .utils import *
from django.utils import timezone

from django.contrib.postgres.fields import ArrayField
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator 

# For syllable calculations
import textstat

# For drop times for different extensions
from .data.helpers import DROP_TIMES






# ============================================
# User profile model - now syncs to Clerk 
# ============================================
#Old User model that extended Django's built-in model
# class UserProfile(models.Model):
#     user = models.OneToOneField(
#         User, 
#         on_delete=models.CASCADE
#     )
#     is_logged_in = models.BooleanField(default=False)
#     payment_status = models.CharField(max_length=20, default='unpaid')
#     subscription_expiry = models.DateField(null=True, blank=True)
#     access_tier = models.CharField(max_length=20, default='free')
#     isPaid = models.BooleanField( default='False')
#     saved_names = models.PositiveIntegerField(null=True, blank=True)
#     acquired = models.PositiveIntegerField(null=True, blank=True) # names acquired from the marketplace only

#     def __str__(self):
#         return self.user.username
    

#Model syncing with clerk via the Authenticator logic
class AppUser(models.Model):
    clerk_id = models.CharField(max_length=128, primary_key=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.first_name or self.email} ({self.clerk_id})"
    
    #Method for deriving first and last name from the full_name field
    def split_full_name(self):
        if self.full_name:
            parts = self.full_name.strip().split(" ", 1)
            self.first_name = parts[0]
            self.last_name = parts[1] if len(parts) > 1 else ""
            self.save(update_fields=["first_name", "last_name"])



# ============================================
# Name model
# ============================================
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
        choices=ExtensionOptions.choices,
        editable=False  # Computed in save()
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
    competition = models.CharField(  # To be filled by post-save signal
        max_length=20,
        null=True,
        blank=True
    )
    difficulty = models.CharField(   # To be filled by post-save signal
        max_length=20,
        null=True,
        blank=True
    )
    suggested_usecase = models.ForeignKey(  # To be filled by post-save signal
        'UseCase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggested_for'
    )
    is_top_rated = models.BooleanField(default=False)
    top_rated_date = models.DateField(null=True, blank=True)  # Used to isolate daily top-rated names
    is_favorite = models.BooleanField(default=False)
    category = models.ForeignKey(  # To be handled in loader
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
        help_text="Set manually in loader per batch"
    )
    drop_time = models.DateTimeField(
        editable=False,
        help_text="Auto-computed in save() based on extension"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_checked = models.DateTimeField(null=True, blank=True)



    
    def save(self, *args, **kwargs):
        """
        Override save method to compute:
        - length and syllables of the domain (excluding extension),
        - extension extracted from domain_name,
        - drop_time based on extension and drop_date.
        """
        # Compute extension from domain_name
        self.extension = self.domain_name.split('.')[-1]

        # Compute length and syllables from domain_name (excluding extension)
        name_part = self.domain_name.split('.')[0]
        self.length = len(name_part)
        self.syllables = textstat.syllable_count(name_part)

        # Compute drop_time from extension lookup table (DROP_TIMES)
        drop_time_value = DROP_TIMES.get(self.extension)
        if drop_time_value:
            # Combine drop_date with the corresponding drop time
            self.drop_time = timezone.make_aware(
                timezone.datetime.combine(self.drop_date, drop_time_value)
            )
        else:
            # Default to timezone.now() if extension not found
            self.drop_time = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.domain_name



# ============================================
# CATEGORY MODEL
# ============================================

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



# ============================================
#TAG MODEL
# ============================================
class NameTag(models.Model):
    name = models.CharField(
        max_length=20,
        unique=True
    )

    def __str__(self):
        return self.name



# ============================================
# Use Case Model
# ============================================
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


    


# ============================================
# Saved Names
# ============================================
class SavedNames(models.Model):
    user = models.ForeignKey(AppUser, related_name='saved_names', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.user


# ============================================
# Acquired Names
# ============================================
class AcquiredNames(models.Model):
    user = models.ForeignKey(AppUser, related_name='acquired_names', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    acquired_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.user






# ============================================
# Plan model
# ============================================
#Plan type choices
class PlanType(models.TextChoices):
    FREE = 'free', 'Free'
    PAID = 'paid', 'Paid'
    FREEMIUM = 'freemium', 'Freemium'


class PlanModel(models.Model):
    plan_type = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        unique=True,
    )
    description = models.TextField(blank=True)
    api_quota = models.IntegerField(default=0)  # Optional
    monthly_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.plan_type


    

# ============================================
# Subscription model - Ties a user to a plan
# ============================================
class PaymentType(models.TextChoices): 
    UNPAID = 'unpaid', 'Unpaid' 
    PAID = 'paid', 'Paid'


class Subscription(models.Model):
    user = models.OneToOneField(AppUser, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(PlanModel, on_delete=models.PROTECT)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.UNPAID,
    )
    subscription_expiry = models.DateField(null=True, blank=True)
    isPaid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    def is_active(self):
        from django.utils import timezone
        return self.isPaid and self.subscription_expiry and self.subscription_expiry >= timezone.now().date()

     


    
    
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
    
    








