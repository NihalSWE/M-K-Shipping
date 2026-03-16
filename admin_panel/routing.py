# from django.urls import re_path
# from . import consumers

# websocket_urlpatterns = [
#     re_path(r'ws/seats/(?P<trip_id>\w+)/$', consumers.SeatConsumer.as_asgi()),
# ]

# If you have an empty list, at least keep this:
websocket_urlpatterns = []  # Empty list is fine