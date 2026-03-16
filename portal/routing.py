from django.urls import re_path
from .consumers import SeatConsumer

websocket_urlpatterns = [
    re_path(r"ws/seats/(?P<trip_id>\d+)/(?P<from_stop>\d+)/(?P<to_stop>\d+)/$", SeatConsumer.as_asgi()),
]
