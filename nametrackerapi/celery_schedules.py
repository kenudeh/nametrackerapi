from celery import shared_task
from django.apps import apps

@shared_task
def initialize_schedules():
    CrontabSchedule = apps.get_model('django_celery_beat', 'CrontabSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    DEFAULT_SCHEDULES = {
        # Domain tasks
        'full_domain_processing': {
            'task': 'full_domain_availability_task',
            'crontab': {'hour': 0, 'minute': 30},
            'enabled': True,
            'expires': 3600
        },
        'daily_archival': {
            'task': 'archive_old_domains_task',
            'crontab': {'hour': 3, 'minute': 0},
            'enabled': True,
            'expires': 3600
        },
        'periodic_availability_checks': {
            'task': 'trigger_bulk_availability_check_task',
            'crontab': {'minute': 0, 'hour': '*/6'},
            'enabled': True,
            'expires': 1800
        },
        'domain_rechecks': {
            'task': 'second_check_task',
            'crontab': {'minute': 15, 'hour': '*/12'},
            'enabled': True,
            'expires': 3600
        },
        'pending_transitions': {
            'task': 'transition_pending_to_deleted_task',
            'crontab': {'minute': 0, 'hour': '*'},
            'enabled': True,
            'expires': 1800
        },
        # File processing
        'file_processing': {
            'task': 'process_pending_files',
            'crontab': {'minute': '*/30'},  # Every 30 minutes
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