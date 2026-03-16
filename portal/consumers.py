import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SeatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.trip_id = self.scope["url_route"]["kwargs"]["trip_id"]
        self.from_stop = self.scope["url_route"]["kwargs"]["from_stop"]
        self.to_stop = self.scope["url_route"]["kwargs"]["to_stop"]

        self.group_name = f"seats_{self.trip_id}_{self.from_stop}_{self.to_stop}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def seat_event(self, event):
        await self.send(text_data=json.dumps({
            "action": event["action"],
            "seat_id": event["seat_id"],
            "holder_id": event.get("holder_id"),
            "expires_at": event.get("expires_at"),
        }))
