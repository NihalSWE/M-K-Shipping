from celery import shared_task
from django.utils import timezone
from django.utils.timezone import localtime
from .models import Booking, Ticket, SeatHold
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
# Import the SMS helper
from django.core.cache import cache
from .utils import send_booking_sms
from portal.utils import seat_hold_key









@shared_task
def send_sms_task(phone_number, message):
    """
    This is the low-level task that actually hits the SMS API.
    It is called BY utils.py.
    """
    from .utils import send_sms_task as utils_send_sms
    utils_send_sms(phone_number, message)
    

@shared_task
def auto_cancel_booking(booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
        
         # NEW: Check if time is stopped - don't auto-cancel!
        if booking.time_stopped:
            print(f"Time stopped for Booking #{booking.id} - skipping auto-cancel")
            return f"Time stopped for booking {booking.id}, not cancelled"
        
        # ONLY Cancel if it is still PENDING
        if booking.status == 'PENDING':
            print(f"Time is up! Auto-expiring Booking #{booking.id}")

            # 1. SAVE DATA BEFORE DELETING TICKETS
            # Get seat numbers
            seats = booking.tickets.all()
            seat_list = [t.seat_object.label for t in seats]
            seat_str = ", ".join(seat_list) # e.g. "A1, B2"
            
            # 2. SAVE Snapshot to Booking Model
            booking.seat_snapshot = seat_str 
            booking.save()  # <--- This saves the seats permanently
            
            # Get the correct Route Name (e.g., "Dhaka to Chandpur")
            first_ticket = seats.first()
            if first_ticket:
                saved_route = f"{first_ticket.from_stop.location.name} to {first_ticket.to_stop.location.name}"
            else:
                saved_route = f"{booking.trip.route.source.name} to {booking.trip.route.destination.name}"

            # Get the correct Price
            saved_price = booking.total_amount 

            # 2. BROADCAST WEBSOCKET RELEASES BEFORE DELETING TICKETS
            channel_layer = get_channel_layer()
            group_name = f"seats_{booking.trip_id}"
            
            for ticket in seats:
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        "type": "seat_event",
                        "action": "release",
                        "seat_id": ticket.seat_object_id,
                        "start_order": ticket.from_stop.stop_order if ticket.from_stop else None,
                        "end_order": ticket.to_stop.stop_order if ticket.to_stop else None,
                    }
                )

            # 3. NOW DELETE TICKETS (Release Seats from DB)
            seats.delete()

            # 4. UPDATE STATUS
            # Use update() so we don't trigger a .save() that might recalculate price to 0
            Booking.objects.filter(id=booking.id).update(status='EXPIRED')
            
            # Refresh booking object to get the new status, but KEEP our saved variables
            booking.refresh_from_db()

            # 4. SEND SMS (Pass the saved data!)
            send_booking_sms(
                booking, 
                seat_list, 
                custom_route=saved_route, 
                custom_price=saved_price
            )
            
            return f"Booking {booking.id} expired, seats released, SMS sent."
            
    except Booking.DoesNotExist:
        return "Booking not found"
    
    
@shared_task
def cleanup_expired_seat_holds():
    """
    Finds all expired SeatHold instances, broadcasts a release event 
    via WebSockets to update the UI, clears Redis cache, and deletes them.
    """
    now = timezone.now()
    
    # 1. Get all expired holds (using select_related to speed up stop_order lookups)
    expired_holds = SeatHold.objects.filter(expires_at__lte=now).select_related('from_stop', 'to_stop')

    if not expired_holds.exists():
        return "No expired holds to clean up."

    channel_layer = get_channel_layer()
    count = 0

    # 2. Iterate through them to broadcast the release and clear cache
    for hold in expired_holds:
        trip_id = hold.trip_id
        seat_id = hold.seat_object_id
        
        # We need from_stop and to_stop to clear the exact Redis cache key
        from_stop_id = hold.from_stop_id if hasattr(hold, 'from_stop_id') else None
        to_stop_id = hold.to_stop_id if hasattr(hold, 'to_stop_id') else None

        # Clear Redis cache explicitly
        if from_stop_id and to_stop_id:
            cache.delete(seat_hold_key(trip_id, from_stop_id, to_stop_id, seat_id))

        # Broadcast the release event so the UI updates for ALL users
        group_name = f"seats_{trip_id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "seat_event",
                "action": "release",
                "seat_id": seat_id,
                "start_order": hold.from_stop.stop_order if hold.from_stop else None,
                "end_order": hold.to_stop.stop_order if hold.to_stop else None,
            }
        )
        count += 1

    # 3. Delete them from the database
    expired_holds.delete()

    return f"Cleaned up and released {count} expired seat holds."
    
