from celery import shared_task
from django.utils import timezone
from .models import Booking, Ticket
# Import the SMS helper
from .utils import send_booking_sms 

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

            # 2. NOW DELETE TICKETS (Release Seats)
            seats.delete()

            # 3. UPDATE STATUS
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
    
    
