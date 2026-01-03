from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db.models import F
from .models import RouteStop

@receiver(post_delete, sender=RouteStop)
def normalize_route_order_on_delete(sender, instance, **kwargs):
    """
    When a stop is deleted, shift subsequent stops down by 1.
    We must use a loop with explicit ordering to avoid Unique Constraint errors on SQLite.
    """
    # 1. Find stops that come AFTER the deleted one.
    # CRITICAL: Order by 'stop_order' (Ascending). 
    # We must move #3 -> #2 first, so that #3 becomes empty for #4 to move into.
    subsequent_stops = RouteStop.objects.filter(
        route=instance.route,
        stop_order__gt=instance.stop_order
    ).order_by('stop_order') 
    
    # 2. Update them one by one
    for stop in subsequent_stops:
        stop.stop_order = stop.stop_order - 1
        stop.save()