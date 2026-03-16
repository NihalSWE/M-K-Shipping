import requests
import threading
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum # Import Sum for safety calculation

# Your API Credentials
API_KEY = "vsoTbO3dzegZfLpTzdbs"
SENDER_ID = "MK SHIPPING"
API_URL = "http://bulksmsbd.net/api/smsapi"

def send_sms_task(phone_number, message):
    """
    Runs in the background to send SMS without freezing the admin panel.
    """
    try:
        if not phone_number:
            print("SMS SKIPPED: No phone number found.")
            return

        # 1. Sanitize Phone Number
        clean_number = ''.join(filter(str.isdigit, str(phone_number)))
        
        # Format for BD
        if clean_number.startswith('01'):
            clean_number = '88' + clean_number
        elif clean_number.startswith('1'):
            clean_number = '880' + clean_number
            
        print(f"--- ATTEMPTING SMS TO: {clean_number} ---")

        params = {
            "api_key": API_KEY,
            "type": "text",
            "number": clean_number,
            "senderid": SENDER_ID,
            "message": message
        }
        
        response = requests.get(API_URL, params=params, timeout=10)
        print(f"SMS API RESPONSE: {response.text}")
        
    except Exception as e:
        print(f"SMS SYSTEM ERROR: {e}")


def send_booking_sms(booking, seats_list=None, custom_route=None, custom_price=None):
    """
    Updated Logic to fix '0 Total' and '0 Paid' issues.
    """
    # ---------------- 1. Route Logic ----------------
    if custom_route:
        route_str = custom_route
        route_cancel_str = custom_route.replace(" to ", " – ")
    else:
        if hasattr(booking, 'tickets'):
            first_ticket = booking.tickets.first()
        else:
            first_ticket = booking.ticket_set.first()
        
        if first_ticket:
            source_name = first_ticket.from_stop.location.name
            dest_name = first_ticket.to_stop.location.name
        else:
            source_name = booking.trip.route.source.name
            dest_name = booking.trip.route.destination.name

        route_str = f"{source_name} to {dest_name}"
        route_cancel_str = f"{source_name} – {dest_name}"

    # ---------------- 2. Smart Seat Logic (Hide Cancelled) ----------------
    if booking.status in ['CONFIRMED', 'PENDING', 'BOOKED']:
        active_tickets = booking.tickets.exclude(status='CANCELLED')
        if active_tickets.exists():
            seats_list = [t.seat_object.label for t in active_tickets]

    seat_str = ", ".join(seats_list) if seats_list else "General"

    # ---------------- 3. FIX: Smart Payment Logic ----------------
    
    # A. Get Total Amount
    if custom_price is not None:
        total_val = float(custom_price)
    else:
        total_val = float(booking.total_amount)
        
        # SAFETY CHECK: If Total is 0 (bug in Pending), calculate it from tickets now
        if total_val == 0 and booking.status == 'PENDING':
            # Sum up the fare of active tickets
            calculated_total = booking.tickets.exclude(status='CANCELLED').aggregate(Sum('fare_amount'))['fare_amount__sum']
            if calculated_total:
                total_val = float(calculated_total)

    # B. Get Paid Amount
    paid_val = float(getattr(booking, 'paid_amount', 0))

    # LOGIC FIX: If Status is CONFIRMED, assume it is Fully Paid
    # (Even if database says paid_amount is 0)
    if booking.status == 'CONFIRMED':
        if paid_val < total_val:
            paid_val = total_val  # Force Paid to equal Total

    # C. Calculate Due
    due_val = total_val - paid_val
    if due_val < 0: due_val = 0 # Prevent negative numbers

    # D. Format numbers
    total_fmt = "{:,.0f}".format(total_val)
    paid_fmt = "{:,.0f}".format(paid_val)
    due_fmt = "{:,.0f}".format(due_val)

    # E. Create Payment String
    if booking.status == 'PENDING':
        # For Pending, we usually just show Total and Due
        payment_info = (
            f"Total Fare: BDT {total_fmt}\n"
            f"Paid: BDT {paid_fmt}\n"
            f"Due: BDT {due_fmt}"
        )
    else:
        # For Confirmed
        if due_val == 0:
            payment_info = (
                f"Total: BDT {total_fmt}\n"
                f"Paid: BDT {paid_fmt}\n"
                f"Due: BDT 0"
            )
        else:
            payment_info = (
                f"Total: BDT {total_fmt}\n"
                f"Paid: BDT {paid_fmt}\n"
                f"Due: BDT {due_fmt}"
            )

    # ---------------- 4. Standard Variables ----------------
    if not booking.user or not booking.user.phone_number:
        return

    target_phone = booking.user.phone_number
    trip = booking.trip
    launch_name = trip.ship.name
    
    formatted_date_long = trip.departure_datetime.strftime('%d %B %Y') 
    formatted_time = trip.departure_datetime.strftime('%I:%M %p')      
    formatted_date_short = trip.departure_datetime.strftime('%d-%m-%Y') 
    reporting_dt = trip.departure_datetime - timedelta(minutes=15)
    reporting_time = reporting_dt.strftime('%I:%M %p')

    msg_body = None 

    # ---------------- 5. Templates ----------------
    
    if booking.status == 'PENDING':
        msg_body = (
            f"Booking Confirmation – MK Shipping Lines\n"
            f"Your journey from {route_str} on {formatted_date_long} at {formatted_time} by {launch_name} has been reserved.\n"
            f"Cabin No: {seat_str}\n"
            f"{payment_info}\n"
            f"Please complete payment within 2 hours.\n"
            f"bKash/Nagad: 01714-858535\n"
            f"Regards,\nMK Shipping Lines"
        )

    elif booking.status == 'CONFIRMED':
        msg_body = (
            f"Ticket Issued – MK Shipping Lines\n"
            f"Route: {route_str}\n"
            f"Date: {formatted_date_long}\n"
            f"Time: {formatted_time}\n"
            f"Reporting Time: {reporting_time}\n"
            f"Launch: {launch_name}\n"
            f"Cabin No: {seat_str}\n"
            f"{payment_info}\n"
            f"Regards,\nMK Shipping Lines"
        )

    elif booking.status == 'CANCELLED':
        msg_body = (
            f"Dear Passenger,\n"
            f"Your booking (Cabin No: {seat_str}) has been CANCELLED.\n"
            f"Route: {route_cancel_str}\n"
            f"Date: {formatted_date_short}\n"
            f"Fare: BDT {total_fmt}\n"
            f"Regards,\nMK Shipping Lines"
        )

    elif booking.status == 'EXPIRED':
        msg_body = (
            f"Booking Expired – MK Shipping Lines\n"
            f"Your booking for {route_cancel_str} on {formatted_date_short} has EXPIRED due to non-payment.\n"
            f"Cabin No: {seat_str} have been released.\n"
            f"Regards,\nMK Shipping Lines"
        )

    # ---------------- 6. Send ----------------
    if msg_body and target_phone:
        thread = threading.Thread(target=send_sms_task, args=(target_phone, msg_body))
        thread.start()


# ------------------- PARTIAL CANCELLATION -------------------
# Kept exactly as it was.

def send_partial_cancel_sms(booking, cancelled_seat_labels, new_total):
    """
    Sends an SMS specifically for PARTIAL cancellations.
    """
    if not booking.user or not booking.user.phone_number:
        return

    target_phone = booking.user.phone_number
    seats_str = ", ".join(cancelled_seat_labels)
    
    # Message Logic
    message = (
        f"Update for Trip: Seats {seats_str} have been CANCELLED. "
        f"Booking Ref: {booking.booking_ref}. "
        f"New Total Amount: {new_total}. "
        f"Current Status: {booking.status}."
    )

    try:
        thread = threading.Thread(target=send_sms_task, args=(target_phone, message))
        thread.start()
        
    except Exception as e:
        print(f"Error sending Partial SMS: {e}")
        
        
def get_logged_in_counter(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, 'assigned_counter', None)