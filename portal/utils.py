from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from admin_panel.models import UniqueVisitor













def seat_hold_key(trip_id, from_stop_id, to_stop_id, seat_id):
    return f"seat_hold:{trip_id}:{from_stop_id}:{to_stop_id}:{seat_id}"


def get_holder_id(request):
    if request.user.is_authenticated:
        return f"user_{request.user.id}"

    if not request.session.session_key:
        request.session.save()

    return f"guest_{request.session.session_key}"



def get_visitor_stats():
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    seven_days_ago = today - timedelta(days=7)

    # Today's Unique Visitors
    users_today = UniqueVisitor.objects.filter(date=today).count()

    # Yesterday's Unique Visitors
    users_yesterday = UniqueVisitor.objects.filter(date=yesterday).count()

    # This Week's Unique Visitors (Distinct IPs only)
    users_this_week = UniqueVisitor.objects.filter(
        date__gte=seven_days_ago
    ).values('ip_address').distinct().count()

    # Live Users (Active in the last 5 minutes)
    # Searches Redis for all keys matching our prefix
    live_user_keys = cache.keys("live_visitor_*")
    live_users = len(live_user_keys) if live_user_keys else 0

    return {
        "live": live_users,
        "today": users_today,
        "yesterday": users_yesterday,
        "this_week": users_this_week
    }