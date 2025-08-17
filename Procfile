web: gunicorn nametrackerapi.wsgi:application
worker: celery -A api worker -l INFO -Q celery # Include -E to enable task events reporting (needed byy flower for detailed reorting)
beat: celery -A api beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
flower: celery -A api flower --port=5555 --basic_auth=kemax:MatuIje@93
# flower: celery -A api flower --port=5555 --basic_auth=admin:complexpassword