from django.core.cache import cache
from django.contrib.auth.models import User

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Name, UseCase, UserProfile 


# Creating a UserProfile instance automatically when a new user is registered
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        
# Signal to clear cache when categories change
# receiver([post_save, post_delete], sender=NameCategory)
# def clear_category_cache(sender, **kwargs):
#     cache.delete_many(['all_categories', 'category_names'])


# @receiver([post_save, post_delete], sender=UseCase)
# def update_name_fields(sender, instance, **kwargs):
#     name = instance.domain
#     first_usecase = name.use_cases.filter(order=1).first()
#     if first_usecase:
#         name.difficulty = first_usecase.difficulty
#         name.competition = first_usecase.competition
#     else:
#         name.difficulty = None
#         name.competition = None
#     name.save()



@receiver(post_save, sender=UseCase)
def update_name_fields(sender, instance, **kwargs):
    """
    Post-save signal for UseCase.
    Updates competition, difficulty, and suggested_usecase fields in Name model
    based on the first UseCase (order=1).
    """
    name = instance.domain_name
    first_usecase = name.use_cases_domain.order_by('order').first()

    if first_usecase:
        # Update Name fields based on the first UseCase
        name.competition = first_usecase.competition
        name.difficulty = first_usecase.difficulty
        name.suggested_usecase = first_usecase
        name.save()