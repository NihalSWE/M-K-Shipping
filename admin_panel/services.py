from datetime import datetime, timedelta
from .models import *

def sync_route_prices(route):
    stops = list(route.stops.order_by('stop_order'))
    # CHANGE: Only fetch bookable categories
    categories = SeatCategory.objects.filter(is_bookable=True) 
    
    valid_price_ids = []

    for i in range(len(stops)):
        for j in range(i + 1, len(stops)):
            from_stop = stops[i]
            to_stop = stops[j]
            
            for cat in categories:
                obj, created = RouteSegmentPricing.objects.get_or_create(
                    route=route,
                    seat_category=cat,
                    from_stop=from_stop,
                    to_stop=to_stop,
                    defaults={'price': 0.00}
                )
                valid_price_ids.append(obj.id)

    # The existing cleanup logic will now automatically DELETE 
    # any old non-bookable pricing entries because they aren't in valid_price_ids.
    if valid_price_ids:
        RouteSegmentPricing.objects.filter(route=route).exclude(id__in=valid_price_ids).delete()
    else:
        RouteSegmentPricing.objects.filter(route=route).delete()

def get_price_matrix(route):
    prices = RouteSegmentPricing.objects.filter(route=route)\
        .select_related('from_stop__location', 'to_stop__location', 'seat_category')\
        .order_by('from_stop__stop_order', 'to_stop__stop_order', 'seat_category__name')
    
    matrix = {}
    for obj in prices:
        label = f"{obj.from_stop.location.name} → {obj.to_stop.location.name}"
        if label not in matrix:
            matrix[label] = []
        matrix[label].append(obj)
    
    return matrix


def generate_smart_trips(ship_id, days_to_generate=10, override_time=None):
    """
    The Engine: Uses TripSchedule blueprints to chain trips together.
    It checks the ship's last location and only creates trips for 
    specific weekdays allowed by the blueprint.
    """
    created_trips = []
    
    with transaction.atomic():
        # We loop through the number of days in your advance booking window
        for _ in range(days_to_generate):
            
            # 1. FIND SHIP'S CURRENT LOCATION & NEXT DATE
            last_trip = Trip.objects.filter(ship_id=ship_id).order_by('-departure_datetime').first()

            if last_trip:
                # If there's a trip, the ship is at the destination of that trip
                current_location = last_trip.route.destination
                next_date = last_trip.departure_datetime.date() + timedelta(days=1)
            else:
                # First time setup: find the first available active schedule
                first_sched = TripSchedule.objects.filter(ship_id=ship_id, is_active=True).first()
                if not first_sched:
                    return "Error: No TripSchedule found. Create a blueprint first."
                
                current_location = first_sched.route.source
                next_date = timezone.now().date()

            # 2. FIND THE BLUEPRINT STARTING AT THIS LOCATION
            next_schedule = TripSchedule.objects.filter(
                ship_id=ship_id,
                is_active=True,
                route__source=current_location
            ).first()

            if not next_schedule:
                # Ship is stuck: no active schedule starts from its current port
                break

            # 3. VALIDATION: RESPECT WEEKDAY AND DATE RANGE
            
            # Check A: Is this date within the blueprint's start and end date?
            if next_schedule.start_date and next_date < next_schedule.start_date:
                # Skip this day and look at the next one
                # Note: We manually increment the date logic for the next loop
                # but since 'last_trip' logic handles it, we can just skip
                continue 

            if next_schedule.end_date and next_date > next_schedule.end_date:
                # The schedule has expired for this route
                break

            # Check B: Does the blueprint run on this specific day of the week?
            day_name = next_date.strftime('%A').lower() # 'monday', 'tuesday', etc.
            if not getattr(next_schedule, f'run_{day_name}'):
                # Ship doesn't run today. We need to create a "dummy" check 
                # or just skip this specific date. 
                # To move the logic forward, we can't create a Trip, 
                # but the ship is still at 'current_location'.
                # We stop here or the loop will spin on the same date.
                # Let's increment manually if no trip exists.
                # To prevent infinite loops, we need to ensure the logic advances:
                # (This is handled by the loop naturally if we were just date-based, 
                # but because we rely on 'last_trip', we need a way to look past today)
                
                # Logic: If we skip, we check tomorrow in the next iteration.
                # We need to temporarily "fake" a date move for the next loop pass.
                # Since we can't change 'last_trip', we'll use a local 'next_date' tracking.
                pass 

            # 4. CREATE THE TRIP (IF ALL CHECKS PASS)
            target_time = override_time if override_time else next_schedule.departure_time
            departure_dt = timezone.make_aware(
                datetime.combine(next_date, target_time)
            )

            # Check for existing trip to prevent duplicates
            exists = Trip.objects.filter(
                ship_id=ship_id, 
                departure_datetime__date=next_date,
                route=next_schedule.route
            ).exists()

            # Final check on the weekday again before creation
            if not exists and getattr(next_schedule, f'run_{day_name}'):
                new_trip = Trip.objects.create(
                    ship_id=ship_id,
                    route=next_schedule.route,
                    departure_datetime=departure_dt,
                    schedule=next_schedule,
                    price_multiplier=1.00 
                )
                created_trips.append(new_trip)

    return f"Generated {len(created_trips)} new trips."




#------------------------------------------------------------------------------------------------------------
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
import uuid

from .models import Trip, RouteStop, LayoutObject, Booking, Ticket

User = get_user_model()

class BookingService:
    @staticmethod
    def create_booking(admin_user, trip_id, from_id, to_id, seat_ids_list, customer_data):
        """
        Replicates the EXACT logic from 'admin_book_confirm'
        """
        # 1. Validate Inputs
        trip = get_object_or_404(Trip, pk=trip_id)
        from_stop = get_object_or_404(RouteStop, pk=from_id)
        to_stop = get_object_or_404(RouteStop, pk=to_id)
        
        c_name = customer_data.get('name')
        c_phone = customer_data.get('phone')
        c_email = customer_data.get('email')

        # 2. Start Atomic Transaction (Safety First)
        with transaction.atomic():
            
            # --- A. User Handling (Copied from your Original View) ---
            booking_user = None
            
            # If Admin is booking for themselves (rare in POS, but possible)
            if not c_phone and not c_name:
                booking_user = admin_user
            else:
                # Prioritize searching by Phone
                if c_phone:
                    booking_user = User.objects.filter(phone_number=c_phone).first()
                
                # If not found by phone, try email
                if not booking_user and c_email:
                    booking_user = User.objects.filter(email=c_email).first()

                # If still not found, CREATE NEW
                if not booking_user:
                    final_email = c_email if c_email else f"{c_phone}@guest.com"
                    random_pass = get_random_string(length=12)
                    
                    # Ensure username is unique
                    username = c_phone if c_phone else final_email.split('@')[0]
                    if User.objects.filter(username=username).exists():
                         username = f"{username}_{get_random_string(4)}"

                    booking_user = User.objects.create_user(
                        email=final_email,
                        username=username,
                        phone_number=c_phone,
                        first_name=c_name if c_name else "Guest",
                        password=random_pass,
                        user_type=1 # Customer
                    )

            # --- B. Create Booking (Copied from Original) ---
            booking = Booking.objects.create(
                user=booking_user,
                trip=trip,
                booking_ref=str(uuid.uuid4())[:12].upper(), # Matches your format
                status='CONFIRMED',
                sales_channel='COUNTER', # Explicitly POS
                total_amount=0 # Will update later
            )

            # --- C. Create Tickets (Loop & Logic) ---
            total_amount = 0
            
            # Retrieve all layout objects at once for efficiency
            layout_objects = LayoutObject.objects.filter(id__in=seat_ids_list)

            if len(layout_objects) != len(seat_ids_list):
                raise Exception("Some seat IDs are invalid.")

            for layout_obj in layout_objects:
                # 1. CRITICAL: Re-check Availability
                if not trip.is_seat_available(layout_obj, from_stop, to_stop):
                    raise Exception(f"Seat {layout_obj.label} is already booked!")

                # 2. Calculate Price (Using your exact Logic)
                price = trip.get_price(layout_obj.category, from_stop, to_stop)
                
                # 3. Create Ticket
                Ticket.objects.create(
                    booking=booking,
                    trip=trip,
                    seat_object=layout_obj,
                    from_stop=from_stop,
                    to_stop=to_stop,
                    passenger_name=c_name if c_name else "Walk-in Guest",
                    fare_amount=price,
                    status='BOOKED', # Matches your Model choices (LOCKED/BOOKED)
                    lock_expires_at=timezone.now() # Satisfies NOT NULL constraint
                )
                
                total_amount += price

            # --- D. Finalize Booking ---
            booking.total_amount = total_amount
            booking.save()

            return booking
        
        
        
        
