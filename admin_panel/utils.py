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



def send_booking_sms(booking, seats_list, custom_route=None, custom_price=None):
    """
    Now accepts 'custom_route' and 'custom_price' to handle Expired bookings
    where tickets (and their data) have been deleted.
    """
    # 1. Get Route (Use Custom if provided, else fetch from tickets)
    if custom_route:
        route_str = custom_route
        route_cancel_str = custom_route.replace(" to ", " – ")
    else:
        # Try to find specific stops from existing tickets
        if hasattr(booking, 'tickets'):
            first_ticket = booking.tickets.first()
        else:
            first_ticket = booking.ticket_set.first()
        
        if first_ticket:
            source_name = first_ticket.from_stop.location.name
            dest_name = first_ticket.to_stop.location.name
        else:
            # Fallback only if no tickets exist and no custom route sent
            source_name = booking.trip.route.source.name
            dest_name = booking.trip.route.destination.name

        route_str = f"{source_name} to {dest_name}"
        route_cancel_str = f"{source_name} – {dest_name}"

    # 2. Get Price (Use Custom if provided, else use booking total)
    if custom_price:
        total_fare = "{:,.0f}".format(custom_price)
    else:
        total_fare = "{:,.0f}".format(booking.total_amount)

    # 3. Other Variables
    seat_str = ", ".join(seats_list) if seats_list else "General"
    target_phone = booking.user.phone_number
    trip = booking.trip
    launch_name = trip.ship.name
    
    formatted_date_long = trip.departure_datetime.strftime('%d %B %Y') 
    formatted_time = trip.departure_datetime.strftime('%I:%M %p')      
    formatted_date_short = trip.departure_datetime.strftime('%d-%m-%Y') 
    reporting_dt = trip.departure_datetime - timedelta(minutes=15)
    reporting_time = reporting_dt.strftime('%I:%M %p')

    msg_body = None 

    # --- TEMPLATES (Same as before) ---
    
    if booking.status == 'PENDING':
        msg_body = (
            f"Booking Confirmation – MK Shipping Lines\n"
            f"Your journey from {route_str} on {formatted_date_long} at {formatted_time} by {launch_name} has been reserved.\n"
            f"Cabin No: {seat_str}\n"
            f"Total Fare: BDT {total_fare}\n"
            f"Please complete the full payment within 2 hours.\n"
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
            f"Regards,\nMK Shipping Lines"
        )

    elif booking.status == 'CANCELLED':
        msg_body = (
            f"Dear Passenger,\n"
            f"Your booking (Cabin No: {seat_str}) has been CANCELLED.\n"
            f"Route: {route_cancel_str}\n"
            f"Date: {formatted_date_short}\n"
            f"Fare: BDT {total_fare}\n"
            f"Regards,\nMK Shipping Lines"
        )

    elif booking.status == 'EXPIRED':
        msg_body = (
            f"Booking Expired – MK Shipping Lines\n"
            f"Your booking for {route_cancel_str} on {formatted_date_short} has EXPIRED due to non-payment.\n"
            f"Cabin No: {seat_str} have been released.\n"
            f"Regards,\nMK Shipping Lines"
        )

    # --- SEND ---
    if msg_body and target_phone:
        thread = threading.Thread(target=send_sms_task, args=(target_phone, msg_body))
        thread.start()