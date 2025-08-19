from django.db import migrations
from datetime import time
import json

DROP_TIMES = {
    'com': time(19, 0),
    'co': time(22, 0),
    'io': time(0, 30),
    'ai': time(22, 0),
}

def create_periodic_tasks(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedules = {
        # TLD-specific pending → deleted transitions
        **{
            f'pending_transitions_{tld}': {
                "task": "api.tasks.transition_pending_to_deleted_task",
                "crontab": {"hour": drop.hour, "minute": drop.minute},
                "enabled": True,
                "expires": None,  # Changed from 1800 to None
                "kwargs": json.dumps({"tld": tld}),
            }
            for tld, drop in DROP_TIMES.items()
        },
        # Every 6 hours
        "availability_checks": {
            "task": "api.tasks.trigger_bulk_availability_check_task",
            "crontab": {"minute": 0, "hour": "*/6"},
            "enabled": True,
            "expires": None,  # Changed from 1800 to None
        },
        # Every 12 hours at :30
        "domain_rechecks": {
            "task": "api.tasks.second_check_task",
            "crontab": {"minute": 30, "hour": "*/12"},
            "enabled": True,
            "expires": None,  # Changed from 3600 to None
        },
        # Daily at 2 AM UTC
        "daily_maintenance": {
            "task": "api.tasks.daily_maintenance_task",
            "crontab": {"hour": 2, "minute": 0},
            "enabled": True,
            "expires": None,  # Changed from 3600 to None
        },
        # Daily at 3 AM UTC
        "file_processing": {
            "task": "api.tasks.process_pending_files",
            "crontab": {"hour": 3, "minute": 0},
            "enabled": True,
            "expires": None,  # Changed from 1800 to None
        },
    }

    for name, config in schedules.items():
        # Create or update the schedule first
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=str(config["crontab"].get("minute", "*")),
            hour=str(config["crontab"].get("hour", "*")),
            day_of_week=str(config["crontab"].get("day_of_week", "*")),
            day_of_month=str(config["crontab"].get("day_of_month", "*")),
            month_of_year=str(config["crontab"].get("month_of_year", "*")),
            timezone="UTC",
        )

        # Then create or update the periodic task
        PeriodicTask.objects.update_or_create(
            name=name,
            defaults={
                "task": config["task"],
                "crontab": schedule,
                "enabled": config["enabled"],
                "expires": config["expires"],
                "kwargs": config.get("kwargs", "{}"),
            },
        )

def remove_tld_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    for tld in DROP_TIMES:
        PeriodicTask.objects.filter(name=f'pending_transitions_{tld}').delete()

class Migration(migrations.Migration):
    dependencies = [
        ("api", "0037_remove_socialapp_sites"),
        ("django_celery_beat", "0016_alter_crontabschedule_timezone"),
    ]

    operations = [
        migrations.RunPython(create_periodic_tasks, remove_tld_tasks),
    ]