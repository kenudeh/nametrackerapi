web: gunicorn nametrackerapi.wsgi:application
worker: celery -A api worker -l INFO -Q celery
beat: celery -A api beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseSchedulerflower: celery -A api flower --port=5555 --basic_auth=admin:complexpassword
flower: celery -A api flower --port=5555 --basic_auth=kemax:MatuIje@93