from django.conf import settings
from django.core.cache import cache

def seat_hold_key(trip_id, from_stop_id, to_stop_id, seat_id):
    return f"seat_hold:{trip_id}:{from_stop_id}:{to_stop_id}:{seat_id}"


def get_holder_id(request):
    if request.user.is_authenticated:
        return f"user_{request.user.id}"

    if not request.session.session_key:
        request.session.save()

    return f"guest_{request.session.session_key}"
