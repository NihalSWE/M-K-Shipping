import requests
import threading
from django.utils import timezone
from datetime import timedelta
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
        # Convert to string and keep only digits
        clean_number = ''.join(filter(str.isdigit, str(phone_number)))
        
        # If it starts with '01', add '88' (e.g. 01712 -> 8801712)
        if clean_number.startswith('01'):
            clean_number = '88' + clean_number
        # If it starts with '1', add '880' (e.g. 1712 -> 8801712)
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
        
        # Send the request
        response = requests.get(API_URL, params=params, timeout=10)
        
        # Print result to terminal so you can see it working
        print(f"SMS API RESPONSE: {response.text}")
        
    except Exception as e:
        print(f"SMS SYSTEM ERROR: {e}")



def send_booking_sms(booking, seats_list):
    """
    Prepares the message using strict templates and starts the thread.
    FETCHES EXACT SUB-ROUTE (e.g., Dhaka to Chandpur) instead of main route.
    """
    # 1. Get Specific Route (From -> To)
    # We look at the first ticket in this booking to see the actual stops.
    # Assuming related_name='tickets' in your Booking model. 
    # If standard Django default, use 'booking.ticket_set.first()'
    first_ticket = booking.tickets.first() 
    
    if first_ticket:
        source_name = first_ticket.from_stop.location.name
        dest_name = first_ticket.to_stop.location.name
    else:
        # Fallback if no tickets found (should not happen)
        source_name = booking.trip.route.source.name
        dest_name = booking.trip.route.destination.name

    # Create the route strings
    route_str = f"{source_name} to {dest_name}"       # "Dhaka to Chandpur"
    route_cancel_str = f"{source_name} – {dest_name}" # "Dhaka – Chandpur" (Hyphen)

    # 2. Other Variables
    seat_str = ", ".join(seats_list) if seats_list else "General"
    target_phone = booking.user.phone_number
    trip = booking.trip
    launch_name = trip.ship.name
    
    # Format Dates & Times
    formatted_date_long = trip.departure_datetime.strftime('%d %B %Y') # 07 January 2026
    formatted_time = trip.departure_datetime.strftime('%I:%M %p')      # 5:30 PM
    formatted_date_short = trip.departure_datetime.strftime('%d-%m-%Y') # 15-01-2026

    # Reporting Time (15 mins before)
    reporting_dt = trip.departure_datetime - timedelta(minutes=15)
    reporting_time = reporting_dt.strftime('%I:%M %p')

    # Money formatting
    total_fare = "{:,.0f}".format(booking.total_amount)

    msg_body = None 

    # ==========================================
    # 1. PENDING TEMPLATE
    # ==========================================
    if booking.status == 'PENDING':
        msg_body = (
            f"Booking Confirmation – MK Shipping Lines\n"
            f"Your journey from {route_str} on {formatted_date_long} at {formatted_time} by {launch_name} has been reserved.\n"
            f"Cabin No: {seat_str}\n"
            f"Total Fare: BDT {total_fare}\n"
            f"Please complete the full payment and confirm your booking within the next 2 hours.\n"
            f"bKash/Nagad (Merchant): 01714-858535\n"
            f"Regards,\n"
            f"MK Shipping Lines"
        )

    # ==========================================
    # 2. CONFIRMED TEMPLATE
    # ==========================================
    elif booking.status == 'CONFIRMED':
        msg_body = (
            f"Ticket Issued – MK Shipping Lines\n"
            f"Route: {route_str}\n"
            f"Date: {formatted_date_long}\n"
            f"Departure Time: {formatted_time}\n"
            f"Reporting Time: {reporting_time}\n"
            f"Launch: {launch_name}\n"
            f"Cabin No: {seat_str}\n"
            f"Regards,\n"
            f"MK Shipping Lines"
        )

    # ==========================================
    # 3. CANCELLED TEMPLATE
    # ==========================================
    elif booking.status == 'CANCELLED':
        msg_body = (
            f"Dear Passenger,\n"
            f"Your booking (Cabin No: {seat_str}) has been CANCELLED .\n"
            f"Route: {route_cancel_str}\n"
            f"Journey Date: {formatted_date_short}\n"
            f"Fare Amount: BDT {total_fare}\n"
            f"If any payment was made, refund will be processed as per company policy.\n"
            f"For support, contact: 09678330055\n"
            f"Regards,\n"
            f"MK Shipping Lines"
        )

    # ==========================================
    # SEND SMS
    # ==========================================
    if msg_body and target_phone:
        thread = threading.Thread(target=send_sms_task, args=(target_phone, msg_body))
        thread.start()