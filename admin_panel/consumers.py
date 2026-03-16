# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.db import database_sync_to_async
# from django.core.cache import cache
# from django.utils import timezone
# from .models import SeatHold, Trip, LayoutObject, RouteStop
# from accounts.models import User

# class SeatConsumer(AsyncWebsocketConsumer):
    
#     async def connect(self):
#         self.trip_id = self.scope['url_route']['kwargs']['trip_id']
#         self.room_group_name = f'trip_{self.trip_id}'
#         self.cache_key = f'trip_holds_{self.trip_id}'

#         # Join the room
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )
#         await self.accept()

#         # --- REDIS PRIMARY: Load state from Redis ---
#         # If Redis is empty (restart/crash), this function auto-refills from DB
#         current_holds = await self.get_holds_from_redis_or_db()
        
#         await self.send(text_data=json.dumps({
#             'type': 'initial_state',
#             'holds': current_holds 
#         }))

#     async def disconnect(self, close_code):
#         user = self.scope.get('user')
#         if user and user.is_authenticated:
#             # Clean up both Redis and DB
#             released_seats = await self.release_user_holds(user.id)
            
#             # Notify others
#             # for seat_id in released_seats:
#             #     await self.channel_layer.group_send(
#             #         self.room_group_name,
#             #         {
#             #             'type': 'seat_update',
#             #             'action': 'unselect',
#             #             'seat_id': seat_id,
#             #             'user_name': 'System',
#             #             'sender_channel_name': self.channel_name
#             #         }
#             #     )

#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         data = json.loads(text_data)
        
#         action = data.get('action')
#         seat_id = str(data.get('seat_id'))
#         user_name = data.get('user_name')
        
#         user_id = data.get('user_id')
#         from_stop_id = data.get('from_stop')
#         to_stop_id = data.get('to_stop')

#         if action == 'select':
#             # 1. TRY REDIS/DB LOCK
#             success = await self.attempt_lock_seat(seat_id, user_name, user_id, from_stop_id, to_stop_id)
            
#             if not success:
#                 # Failed (Taken by someone else) -> Revert user UI
#                 # await self.send(text_data=json.dumps({
#                 #     'action': 'unselect',
#                 #     'seat_id': seat_id,
#                 #     'user_name': 'System'
#                 # }))
#                 await self.send(text_data=json.dumps({
#                 'action': 'seat_held',
#                 'seat_id': seat_id,
#                 'message': 'This seat is already held by someone else',
#                 'alert': True
#                 }))
#                 return

#         elif action == 'unselect':
#             await self.unlock_seat(seat_id, user_id)

#         # Broadcast if successful
#         # await self.channel_layer.group_send(
#         #     self.room_group_name,
#         #     {
#         #         'type': 'seat_update',
#         #         'action': action,
#         #         'seat_id': seat_id,
#         #         'user_name': user_name,
#         #         'sender_channel_name': self.channel_name
#         #     }
#         # )

#     async def seat_update(self, event):
#         if self.channel_name == event.get('sender_channel_name'):
#             return

#         await self.send(text_data=json.dumps({
#             'action': event['action'],
#             'seat_id': event['seat_id'],
#             'user_name': event['user_name']
#         }))

#     # ============================================================
#     # HYBRID REDIS + DB HELPERS
#     # ============================================================

#     @database_sync_to_async
#     def get_holds_from_redis_or_db(self):
#         """ 
#         FAST: Tries Redis first. 
#         FALLBACK: If Redis is missing/empty, loads from DB and repopulates Redis.
#         """
#         # 1. Try Redis
#         holds = cache.get(self.cache_key)
        
#         if holds is not None:
#             return holds  # FAST EXIT
        
#         # 2. Fallback to DB (If Redis died)
#         db_holds = SeatHold.objects.filter(
#             trip_id=self.trip_id,
#             expires_at__gt=timezone.now()
#         ).select_related('holder', 'seat_object')

#         # Convert DB objects to simple Dict for Redis
#         # Format: { 'seat_id': 'User Name' }
#         holds = {str(h.seat_object.id): h.holder.username for h in db_holds}
        
#         # 3. Save back to Redis (Hydrate cache)
#         cache.set(self.cache_key, holds, timeout=300) # 5 mins
        
#         return holds

#     @database_sync_to_async
#     def attempt_lock_seat(self, seat_id, user_name, user_id, from_stop_id, to_stop_id):
#         """
#         1. Checks Redis for speed.
#         2. Checks DB for route availability.
#         3. Updates Redis AND DB.
#         """
#         # --- A. REDIS CHECK (FAST) ---
#         current_holds = cache.get(self.cache_key, {})
#         if seat_id in current_holds and current_holds[seat_id] != user_name:
#             return False # Taken in Redis by someone else

#         try:
#             trip = Trip.objects.get(id=self.trip_id)
#             seat = LayoutObject.objects.get(id=seat_id)
#             user = User.objects.get(id=user_id)
#             from_stop = RouteStop.objects.get(id=from_stop_id)
#             to_stop = RouteStop.objects.get(id=to_stop_id)

#             # --- B. DB LOGIC CHECK (STRICT) ---
#             # Ensure complex route logic allows this
#             if not trip.is_seat_available(seat, from_stop, to_stop, exclude_user=user):
#                 return False 

#             # --- C. UPDATE REDIS (FAST UI) ---
#             current_holds[seat_id] = user_name
#             cache.set(self.cache_key, current_holds, timeout=300)

#             # --- D. UPDATE DB (PERSISTENCE) ---
#             # Remove old hold for this user/seat combo if exists
#             SeatHold.objects.filter(trip=trip, seat_object=seat, holder=user).delete()
            
#             SeatHold.objects.create(
#                 trip=trip,
#                 seat_object=seat,
#                 holder=user,
#                 from_stop=from_stop,
#                 to_stop=to_stop,
#                 expires_at=timezone.now() + timezone.timedelta(minutes=5)
#             )
#             return True
            
#         except Exception as e:
#             print(f"Lock Error: {e}")
#             return False

#     @database_sync_to_async
#     def unlock_seat(self, seat_id, user_id):
#         """ Removes from Redis AND DB """
#         # 1. Update Redis
#         current_holds = cache.get(self.cache_key, {})
#         if seat_id in current_holds:
#             del current_holds[seat_id]
#             cache.set(self.cache_key, current_holds, timeout=300)

#         # 2. Update DB
#         SeatHold.objects.filter(
#             trip_id=self.trip_id,
#             seat_object_id=seat_id,
#             holder_id=user_id
#         ).delete()

#     @database_sync_to_async
#     def release_user_holds(self, user_id):
#         """ On disconnect, clear user from Redis and DB """
#         # 1. Get user's DB holds to know which IDs to clear from Redis
#         user_holds = SeatHold.objects.filter(trip_id=self.trip_id, holder_id=user_id)
#         seat_ids = [str(h.seat_object.id) for h in user_holds]
        
#         # 2. Clear from Redis
#         current_holds = cache.get(self.cache_key, {})
#         updated = False
#         for sid in seat_ids:
#             if sid in current_holds:
#                 del current_holds[sid]
#                 updated = True
        
#         if updated:
#             cache.set(self.cache_key, current_holds, timeout=300)

#         # 3. Clear from DB
#         user_holds.delete()

#         return seat_ids