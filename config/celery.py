import os
from celery import Celery

# 1. Set the default Django settings module for the 'celery' program.
# This tells Celery where to find your Django settings.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 2. Create the Celery app instance.
app = Celery('config')

# 3. Load configuration from the Django settings file.
# namespace='CELERY' means all celery-related settings in settings.py 
# must start with "CELERY_".
app.config_from_object('django.conf:settings', namespace='CELERY')

# 4. Auto-discover tasks in all your installed apps.
# This way you don't have to manually list every task.
app.autodiscover_tasks()

# config/celery.py

