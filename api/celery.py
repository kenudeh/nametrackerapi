import os
from celery import Celery


# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nametrackerapi.settings')

app = Celery('api')

# Load task modules from all registered Django apps
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()






# import os
# from celery import Celery


# # Set default Django settings module for Celery
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

# app = Celery('api')

# # Load task modules from all registered Django app configs.
# app.config_from_object('django.conf:settings', namespace='CELERY')
# app.autodiscover_tasks()


# # This enables the Celery Beat scheduler to work with Django settings
# app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'


# # Optional debug output
# @app.task(bind=True)
# def debug_task(self):
#     print(f'Request: {self.request!r}')
