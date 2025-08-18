# nametrackerapi/__init__.py
from api.celery import app as celery_app
__all__ = ('celery_app',)