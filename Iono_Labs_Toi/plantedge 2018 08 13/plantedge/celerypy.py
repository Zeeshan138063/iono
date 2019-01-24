# Prep to run celery worker as part of django application
import django
import os
from celery import Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plantedgews.settings')
django.setup()

#CELERY APP CREATION
from django.conf import settings
celery_app = Celery('plantedgews', backend='redis://localhost', broker='redis://localhost')
celery_app.autodiscover_tasks(settings.INSTALLED_APPS)
