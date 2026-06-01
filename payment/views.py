import requests
import uuid
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from django.db import transaction
from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from portal.views import _to_local_bd_phone
from django.utils import timezone
from datetime import timedelta
from admin_panel.utils import send_booking_sms
from portal.utils import seat_hold_key
from portal.ssl_constants import(
    SSL_LIVE_URL,
    SSL_SANDBOX_URL,
    SSL_GW_ENDPOINT,
    SSL_VALIDATION_ENDPOINT
)
from admin_panel.models import (
    PaymentTransaction,
    RouteStop,
    LayoutObject,
    SeatHold,
    Ticket,
    BookingVehicle,
)









# Use Sandbox Credentials
# STORE_ID = 'testbox'
# STORE_PASS = 'qwerty'
STORE_ID = 'iglto69abbebda8578'
STORE_PASS = 'iglto69abbebda8578@ssl'
# STORE_ID = 'felnatech0live'
# STORE_PASS = '6815E61C133C384115'
BASE_URL = "https://sandbox.sslcommerz.com"
# CHANGE THIS to your actual Ngrok URL
MY_DOMAIN = "https://fcf5-27-147-153-214.ngrok-free.app" 







@csrf_exempt
def payment_success(request):
    from admin_panel.models import Booking

    # SSLCommerz POSTs: tran_id, value_a (our booking_ref), status, etc.
    booking_ref = request.POST.get('value_a') or request.GET.get('value_a')
    tran_id     = request.POST.get('tran_id')  or request.GET.get('tran_id')

    # Fallback: look up booking_ref via tran_id
    if not booking_ref and tran_id:
        pt = PaymentTransaction.objects.filter(tran_id=tran_id).select_related('booking').first()
        if pt and pt.booking:
            booking_ref = pt.booking.booking_ref

    if not booking_ref:
        return render(request, 'payment/ssl_commerz/payment_statuses/payment_failed.html')

    booking = Booking.objects.filter(booking_ref=booking_ref).first()
    if not booking:
        return render(request, 'payment/ssl_commerz/payment_statuses/payment_failed.html')

    # IPN already processed — go straight to success
    if booking.status == 'CONFIRMED':
        # IPN already processed — go straight to success
        return redirect(f'/booking/success/{booking_ref}/')

    if booking.status == 'EXPIRED' and booking.payment_status == 'PAID':
        # Paid but hold expired during gateway — special page
        return redirect(f'/payment/expired/{booking_ref}/')

    if booking.status in ('CANCELLED', 'EXPIRED'):
        # IPN already marked it as failed, no money taken
        return render(request, 'payment/ssl_commerz/payment_statuses/payment_failed.html')

    # status is PROCESSING (or edge-case PENDING) — IPN not yet arrived
    return render(request, 'payment/ssl_commerz/payment_statuses/payment_processing.html', {
        'booking_ref': booking_ref,
    })
    
    
@csrf_exempt
def payment_fail(request):
    tran_id = request.POST.get('tran_id')

    if tran_id:
        payment = PaymentTransaction.objects.select_related(
            'booking__trip'
        ).filter(tran_id=tran_id).first()

        if payment and not payment.is_processed:
            # IPN hasn't run yet — handle it here as fallback
            _handle_failed_payment(payment, status='FAILED')

    return render(request, 'payment/ssl_commerz/payment_statuses/payment_failed.html')


@csrf_exempt
def payment_cancel(request):
    tran_id = request.POST.get('tran_id')

    if tran_id:
        payment = PaymentTransaction.objects.select_related(
            'booking__trip'
        ).filter(tran_id=tran_id).first()

        if payment and not payment.is_processed:
            # IPN hasn't run yet — handle it here as fallback
            _handle_failed_payment(payment, status='CANCELLED')

    return render(request, 'payment/ssl_commerz/payment_statuses/payment_cancelled.html')


def _handle_failed_payment(payment, status):
    """
    Shared cleanup for failed/cancelled payments.
    Only called when IPN has NOT already processed this transaction.
    """
    booking = payment.booking
    if not booking:
        return

    payload   = booking.booking_payload or {}
    holder_id = payload.get('holder_id', '')

    with transaction.atomic():
        # Update payment record
        payment.status       = status      # 'FAILED' or 'CANCELLED'
        payment.is_processed = True
        payment.save(update_fields=['status', 'is_processed'])

        # Update booking — payment_status stays UNPAID (it was never paid)
        booking.status         = 'CANCELLED'
        booking.payment_status = 'UNPAID'   # ← correct: money never moved
        booking.save(update_fields=['status', 'payment_status'])

        # Grab hold info before deleting (needed for WS broadcast)
        released_holds = list(
            SeatHold.objects.filter(
                trip=booking.trip,
                holder_id=holder_id
            ).values('seat_object_id', 'from_stop__stop_order', 'to_stop__stop_order')
        )

        # Release all seat holds so other users can book immediately
        SeatHold.objects.filter(
            trip=booking.trip,
            holder_id=holder_id
        ).delete()

        # Clear Redis cache entries and broadcast WS release
        channel_layer = get_channel_layer()
        group = f"seats_{booking.trip.id}"

        for hold in released_holds:
            cache.delete(seat_hold_key(
                booking.trip.id,
                payload.get('from_stop'),
                payload.get('to_stop'),
                hold['seat_object_id']
            ))
            async_to_sync(channel_layer.group_send)(group, {
                "type":        "seat_event",
                "action":      "release",
                "seat_id":     hold['seat_object_id'],
                "start_order": hold['from_stop__stop_order'],
                "end_order":   hold['to_stop__stop_order'],
            })


@csrf_exempt
def payment_ipn(request):
    data = request.POST.dict()
    tran_id = data.get('tran_id')
    val_id  = data.get('val_id')
    status  = data.get('status')

    # ── Step 1: Lock the transaction row and guard against double-processing ──
    with transaction.atomic():
        payment = PaymentTransaction.objects.select_for_update(
            of=('self',)  # lock only PaymentTransaction row, not nullable joins
        ).filter(tran_id=tran_id).first()

        if not payment:
            return HttpResponse("Transaction not found.")

        if payment.is_processed:
            return HttpResponse("Already processed.")

        # Fetch related objects separately (can't select_related with select_for_update on nullable FKs)
        booking = payment.booking
        store   = payment.store

        # Persist raw gateway data immediately
        payment.raw_response  = data
        payment.val_id        = val_id
        payment.status        = status
        payment.bank_tran_id  = data.get('bank_tran_id')
        payment.card_type     = data.get('card_type')
        payment.card_brand    = data.get('card_brand')
        payment.save(update_fields=[
            'raw_response', 'val_id', 'status',
            'bank_tran_id', 'card_type', 'card_brand'
        ])

        # ── Step 2: Handle non-successful statuses (FAILED / CANCELLED / EXPIRED / UNATTEMPTED) ──
        if status not in ['VALID', 'VALIDATED']:
            payload   = booking.booking_payload or {}
            holder_id = payload.get('holder_id', '')

            booking.status         = 'CANCELLED'
            booking.payment_status = 'UNPAID'
            booking.save(update_fields=['status', 'payment_status'])

            # Grab stop info for WS broadcast before deleting holds
            released_holds = list(
                SeatHold.objects.filter(
                    trip=booking.trip,
                    holder_id=holder_id
                ).values('seat_object_id', 'from_stop__stop_order', 'to_stop__stop_order')
            )

            SeatHold.objects.filter(
                trip=booking.trip,
                holder_id=holder_id
            ).delete()

            # Broadcast release so other users' seat maps update immediately
            channel_layer = get_channel_layer()
            group = f"seats_{booking.trip.id}"
            for hold in released_holds:
                cache.delete(seat_hold_key(
                    booking.trip.id,
                    payload.get('from_stop'),
                    payload.get('to_stop'),
                    hold['seat_object_id']
                ))
                async_to_sync(channel_layer.group_send)(group, {
                    "type":        "seat_event",
                    "action":      "release",
                    "seat_id":     hold['seat_object_id'],
                    "start_order": hold['from_stop__stop_order'],
                    "end_order":   hold['to_stop__stop_order'],
                })

            payment.is_processed = True
            payment.save(update_fields=['is_processed'])

            return HttpResponse("Payment failed or cancelled.")

    # ── Step 3: Validate with SSLCommerz (network call — outside DB lock) ──
    store = store
    base_url = SSL_LIVE_URL if store.is_live else SSL_SANDBOX_URL
    validation_url = f"{base_url}{SSL_VALIDATION_ENDPOINT}"

    # Use a dictionary for the query parameters
    query_params = {
        'val_id': val_id,
        'store_id': store.store_id,
        'store_passwd': store.store_password,
        'format': 'json',
    }

    try:
        validation_response = requests.get(validation_url, params=query_params, timeout=30).json()
    except Exception as e:
        return HttpResponse(f"SSL validation request failed: {e}")

    validation_status = validation_response.get('status')

    if validation_status not in ['VALID', 'VALIDATED']:
        with transaction.atomic():
            booking.status = 'CANCELLED'
            booking.save(update_fields=['status'])
            payment.status       = 'FAILED'
            payment.is_processed = True
            payment.save(update_fields=['status', 'is_processed'])
        return HttpResponse("SSL validation failed.")

    # ── Step 4: Payment validated — create tickets, broadcast WS, confirm booking ──
    payload         = booking.booking_payload or {}
    holder_id       = payload.get('holder_id')
    passengers_data = payload.get('passengers', [])
    vehicles_data   = payload.get('vehicles', [])

    from_stop = RouteStop.objects.get(id=payload['from_stop'])
    to_stop   = RouteStop.objects.get(id=payload['to_stop'])

    # Tag each entry so we know how to build the ticket inside the loop.
    # Vehicle entries carry '_is_vehicle': True — no Passenger record needed.
    all_entries = passengers_data + [dict(v, _is_vehicle=True) for v in vehicles_data]

    with transaction.atomic():
        channel_layer = get_channel_layer()
        group = f"seats_{booking.trip.id}"

        for p in all_entries:
            is_vehicle = p.get('_is_vehicle', False)
            seat = LayoutObject.objects.select_for_update().get(id=p['seat_id'])

            # Verify hold is still active (same logic for every seat type)
            hold_exists = SeatHold.objects.filter(
                trip=booking.trip,
                from_stop=from_stop,
                to_stop=to_stop,
                seat_object=seat,
                holder_id=holder_id,
                expires_at__gt=timezone.now()
            ).exists()

            if not hold_exists:
                booking.status         = 'EXPIRED'
                booking.payment_status = 'PAID'
                booking.paid_amount    = booking.total_amount
                booking.payment_val_id = val_id
                booking.payment_date   = timezone.now()
                booking.save(update_fields=[
                    'status', 'payment_status', 'paid_amount',
                    'payment_val_id', 'payment_date'
                ])
                payment.status       = 'EXPIRED'
                payment.is_processed = True
                payment.save(update_fields=['status', 'is_processed'])

                def _send_expired_sms():
                    try:
                        send_booking_sms(booking)
                    except Exception as sms_err:
                        print(f"EXPIRED BOOKING SMS ERROR: {sms_err}")
                transaction.on_commit(_send_expired_sms)

                return HttpResponse(f"Seat hold expired for {seat.label}")

            fare = booking.trip.get_price(seat.category, from_stop, to_stop)

            if is_vehicle:
                plate = (p.get('license_plate') or '').strip().upper()
                ticket = Ticket.objects.create(
                    booking=booking,
                    trip=booking.trip,
                    seat_object=seat,
                    passenger=None,
                    passenger_name=plate,
                    from_stop=from_stop,
                    to_stop=to_stop,
                    fare_amount=fare,
                    status='BOOKED',
                    lock_expires_at=timezone.now() + timedelta(days=1)
                )
                # Link the now-created ticket back to the BookingVehicle record
                BookingVehicle.objects.filter(
                    booking=booking,
                    license_plate=plate
                ).update(ticket=ticket)
                gender = None
            else:
                passenger = booking.passengers.filter(
                    name=p.get('name'),
                    phone=_to_local_bd_phone(p.get('phone'))
                ).first()
                ticket = Ticket.objects.create(
                    booking=booking,
                    trip=booking.trip,
                    seat_object=seat,
                    passenger=passenger,
                    passenger_name=passenger.name if passenger else (p.get('name') or ''),
                    from_stop=from_stop,
                    to_stop=to_stop,
                    fare_amount=fare,
                    status='BOOKED',
                    lock_expires_at=timezone.now() + timedelta(days=1)
                )
                gender = passenger.gender if passenger else None

            SeatHold.objects.filter(
                trip=booking.trip,
                from_stop=from_stop,
                to_stop=to_stop,
                seat_object=seat
            ).delete()

            cache.delete(seat_hold_key(
                booking.trip.id, from_stop.id, to_stop.id, seat.id
            ))

            async_to_sync(channel_layer.group_send)(group, {
                "type":        "seat_event",
                "action":      "booked",
                "seat_id":     int(seat.id),
                "start_order": from_stop.stop_order,
                "end_order":   to_stop.stop_order,
                "gender":      gender,
            })

        # ── Confirm the booking — payment_status = 'PAID' is set here ──
        booking.status         = 'CONFIRMED'
        booking.payment_status = 'PAID'           # ← here
        booking.paid_amount    = booking.total_amount
        booking.payment_val_id = val_id
        booking.payment_date   = timezone.now()
        booking.save(update_fields=[
            'status', 'payment_status', 'paid_amount',
            'payment_val_id', 'payment_date'
        ])

        # Clean up any remaining holds for this holder
        SeatHold.objects.filter(
            trip=booking.trip,
            holder_id=holder_id
        ).delete()

        payment.status       = 'VALID'
        payment.is_processed = True
        payment.save(update_fields=['status', 'is_processed'])

        def _send_confirm_sms():
            try:
                send_booking_sms(booking)
            except Exception as sms_err:
                print(f"BOOKING SMS ERROR: {sms_err}")

        transaction.on_commit(_send_confirm_sms)

    return HttpResponse("OK")



def check_booking_status(request, booking_ref):
    """Polled by the processing page to detect when IPN confirms the booking."""
    from admin_panel.models import Booking

    booking = Booking.objects.filter(booking_ref=booking_ref).only(
        'status', 'payment_status'
    ).first()

    if not booking:
        return JsonResponse({'status': 'NOT_FOUND'})

    return JsonResponse({
        'status':         booking.status,
        'payment_status': booking.payment_status,
        # Frontend needs to distinguish "expired but paid" from "expired unpaid"
        'paid_expired':   booking.status == 'EXPIRED' and booking.payment_status == 'PAID',
    })
    
    

def payment_expired_hold(request, booking_ref):
    """
    User paid successfully but their seat hold expired during the gateway session.
    Payment is recorded. Admin must manually resolve (refund or rebook).
    """
    from admin_panel.models import Booking

    booking = Booking.objects.filter(
        booking_ref=booking_ref,
        status='EXPIRED',
        payment_status='PAID'
    ).first()

    if not booking:
        # Wrong URL or not a paid-expired case — send to generic fail
        return render(request, 'payment/ssl_commerz/payment_statuses/payment_failed.html')

    return render(request, 'payment/ssl_commerz/payment_statuses/payment_expired_hold.html', {
        'booking': booking,
    })