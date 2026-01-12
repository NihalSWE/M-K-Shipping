import requests
import threading

# Your API Credentials
API_KEY = "vsoTbO3dzegZfLpTzdbs"
SENDER_ID = "8809604902861"
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
    Prepares the message and starts the thread.
    Handles CONFIRMED, CANCELLED, and PENDING statuses.
    """
    seat_str = ", ".join(seats_list) if seats_list else "General"
    
    # Grab the phone number from the User model
    target_phone = booking.user.phone_number
    
    msg_body = None # Start empty

    # 1. CONFIRMED CASE
    if booking.status == 'CONFIRMED':
        msg_body = (
            f"Booking Confirmed!\n"
            f"Ref: {booking.booking_ref}\n"
            f"Trip: {booking.trip.ship.name}\n"
            f"Date: {booking.trip.departure_datetime.strftime('%d-%b %I:%M %p')}\n"
            f"Seats: {seat_str}\n"
            f"Thank you."
        )
        
    # 2. CANCELLED CASE (New)
    elif booking.status == 'CANCELLED':
        msg_body = (
            f"Booking Cancelled.\n"
            f"Ref: {booking.booking_ref}\n"
            f"Trip: {booking.trip.ship.name}\n"
            f"Your tickets have been cancelled.\n"
            f"Contact counter for details."
        )

    # 3. PENDING CASE (Changed from 'else' to 'elif' for safety)
    elif booking.status == 'PENDING':
        total_price = int(booking.total_amount)
        
        msg_body = (
            f"Booking Pending.\n"
            f"Ref: {booking.booking_ref}\n"
            f"Seats: {seat_str}\n"
            f"Total: {total_price} TK\n"
            f"Please pay to confirm."
        )

    # Only send if we matched one of the statuses above
    if msg_body:
        thread = threading.Thread(target=send_sms_task, args=(target_phone, msg_body))
        thread.start()