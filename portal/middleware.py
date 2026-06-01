from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.core.cache import cache
from admin_panel.models import UniqueVisitor

class VisitorTrackingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 1. Extract the IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        if not ip:
            return None

        # 2. Track "Live" Users via Redis (expires in 300 seconds / 5 minutes)
        cache_key = f"live_visitor_{ip}"
        cache.set(cache_key, True, 300) 

        # 3. Track Daily Unique Users in Postgres
        today = timezone.now().date()
        
        try:
            # get_or_create ensures the IP is only logged once per day
            UniqueVisitor.objects.get_or_create(ip_address=ip, date=today)
        except Exception:
            # Safely handle exact millisecond race conditions
            pass