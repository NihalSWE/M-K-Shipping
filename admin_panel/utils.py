import requests
import threading
from django.utils.timezone import localtime
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
    # ---------------- 2. Smart Seat Logic (Hide Cancelled) ----------------
    if booking.status in ['CONFIRMED', 'PENDING', 'BOOKED']:
        active_tickets = booking.tickets.exclude(
            status='CANCELLED'
        ).select_related('seat_object__category')

        if active_tickets.exists():
            # Group by category name (only bookable categories)
            from collections import defaultdict
            category_seats = defaultdict(list)

            for t in active_tickets:
                cat = t.seat_object.category
                cat_name = cat.name if cat.is_bookable else None
                if cat_name:
                    category_seats[cat_name].append(t.seat_object.label)

            if category_seats:
                # Format: "Cabin: D-203, D-204; Seat: A-101, B-201"
                seat_str = "; ".join(
                    f"{cat}: {', '.join(labels)}"
                    for cat, labels in category_seats.items()
                )
            else:
                seat_str = "General"
        else:
            seat_str = seats_list and ", ".join(seats_list) or "General"
    else:
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
            f"Fare Total: BDT {total_fmt}\n"
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
    
    # Convert UTC time to Local Time (UTC+6)
    local_departure = localtime(trip.departure_datetime)

    formatted_date_long = local_departure.strftime('%d %B %Y') 
    formatted_time = local_departure.strftime('%I:%M %p')      
    formatted_date_short = local_departure.strftime('%d-%m-%Y') 
    
    # Calculate reporting time based on the local time
    reporting_dt = local_departure - timedelta(minutes=15)
    reporting_time = reporting_dt.strftime('%I:%M %p')

    msg_body = None 

    # ---------------- 5. Templates ----------------
    
    if booking.status == 'PENDING':
        msg_body = (
            f"Ticket Booked\n"
            f"{route_str} on {formatted_date_short} at {formatted_time} launch - {launch_name}, {seat_str} has been booked. "
            f"Fare Total: BDT {total_fmt}. Pay the full amount and confirm your ticket within next 2 hours. "
            f"Bkash/Nagad Merchant: 01714858535."
        )

    elif booking.status == 'CONFIRMED':
        msg_body = (
            f"Ticket Issued\n"
            f"{route_str} on {formatted_date_short} at {formatted_time} launch - {launch_name}, "
            f"{seat_str} has been issued. "
            f"Fare Total: BDT {total_fmt}. "
            f"Reporting time: {reporting_time}."
        )

    elif booking.status == 'CANCELLED':
        msg_body = (
            f"Ticket Cancelled\n"
            f"{route_cancel_str} on {formatted_date_short} at {formatted_time} launch - {launch_name}, "
            f"{seat_str} has been cancelled. "
        )

    elif booking.status == 'EXPIRED':
        msg_body = (
            f"Ticket Expired\n"
            f"{route_cancel_str} on {formatted_date_short} at {formatted_time} launch - {launch_name}, "
            f"{seat_str} has expired due to payment failure."
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