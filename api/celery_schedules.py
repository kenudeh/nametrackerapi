from celery import shared_task
from django.apps import apps

@shared_task
def initialize_schedules():
    CrontabSchedule = apps.get_model('django_celery_beat', 'CrontabSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    DEFAULT_SCHEDULES = {
        # Time-sensitive independent tasks
        'pending_transitions': {
            'task': 'api.tasks.transition_pending_to_deleted_task',
            'crontab': {'minute': 0, 'hour': '*'},  # Hourly
            'enabled': True,
            'expires': 1800
        },
        'availability_checks': {
            'task': 'api.tasks.trigger_bulk_availability_check_task',
            'crontab': {'minute': 0, 'hour': '*/4'},  # Every 4 hours
            'enabled': True,
            'expires': 1800
        },
        'domain_rechecks': {
            'task': 'api.tasks.second_check_task',
            'crontab': {'minute': 30, 'hour': '*/12'},  # Every 12 hours at :30
            'enabled': True,
            'expires': 3600
        },
        
        # Daily maintenance bundle
        'daily_maintenance': {
            'task': 'api.tasks.daily_maintenance_task',
            'crontab': {'hour': 2, 'minute': 0},  # 2 AM UTC
            'enabled': True,
            'expires': 3600
        },
        
        # File processing
        'file_processing': {
            'task': 'api.tasks.process_pending_files',
            'crontab': {'hour': 3, 'minute': 0},
            # 'crontab': {'minute': '*/30'},
            'enabled': True,
            'expires': 1800
        }
    }

    for name, config in DEFAULT_SCHEDULES.items():
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=config['crontab'].get('minute', '*'),
            hour=config['crontab'].get('hour', '*'),
            day_of_week=config['crontab'].get('day_of_week', '*'),
            day_of_month=config['crontab'].get('day_of_month', '*'),
            month_of_year=config['crontab'].get('month_of_year', '*')
        )
        PeriodicTask.objects.update_or_create(
            name=name,
            defaults={
                'task': config['task'],
                'crontab': schedule,
                'enabled': config['enabled'],
                'expires_seconds': config['expires']
            }
        )



# For locl settings, use these commands to run celery:
# :: First terminal (worker)
# celery -A api worker -l INFO --pool=solo

# :: Second terminal (beat)
# celery -A api beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler




# For cleanup locally:
#  Full Cleanup Process
# cmd
# :: Stop all Celery processes
# taskkill /im celery.exe /f

# :: Purge Celery queues
# celery -A api purge -f

# :: Clear Redis
# python -c "import redis; redis.Redis().flushall()"