from django.core.cache import cache
from django.contrib.auth.models import User

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Name, UseCase 


# Creating a UserProfile instance automatically when a new user is registered(Overriden by switching to CLerk for authentication)
# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         UserProfile.objects.create(user=instance)
        


# Signal to clear cache when categories change
# receiver([post_save, post_delete], sender=NameCategory)
# def clear_category_cache(sender, **kwargs):
#     cache.delete_many(['all_categories', 'category_names'])


@receiver(post_save, sender=UseCase)
def assign_suggested_usecase(sender, instance, **kwargs):
    """
    When a UseCase is created or updated, ensure that the Name model's
    suggested_usecase field points to the one with order=1.
    """
    name = instance.domain_name
    first_usecase = name.use_cases.order_by('order').first()

    if first_usecase and name.suggested_usecase_id != first_usecase.id:
        name.suggested_usecase = first_usecase
        name.save(update_fields=["suggested_usecase"])




@receiver(post_delete, sender=UseCase)
def clean_up_suggested_usecase(sender, instance, **kwargs):
    """
    If the deleted use case was the suggested one, reassign or nullify.
    """
    try:
        name = instance.domain_name
        if name.suggested_usecase_id == instance.id:
            next_best = name.use_cases.order_by('order').first()
            name.suggested_usecase = next_best  # May be None
            name.save(update_fields=["suggested_usecase"])
    except Name.DoesNotExist:
        pass  # Safe fail if related name is already gone