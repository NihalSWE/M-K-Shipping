# payment/views.py
import uuid
import logging
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from admin_panel.models import Booking
from admin_panel.utils import send_booking_sms
from .sslcommerz import SSLCommerz

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def is_sslcommerz_ip(request):
    """Check if request is from SSLCOMMERZ IPs"""
    from django.conf import settings
    
    if settings.DEBUG:
        return True
    
    ALLOWED_IPS = [
        '103.26.139.87',   # Sandbox
        '103.26.139.81',   # Live primary
        '103.132.153.81',  # Live secondary
        '103.26.139.148',  # Additional
        '103.132.153.148', # Additional
    ]
    
    client_ip = get_client_ip(request)
    return client_ip in ALLOWED_IPS

@login_required
def initiate_payment(request, booking_id):
    """Step 1: Customer clicks Pay Now - Initialize payment"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.status != 'PENDING' or booking.payment_status == 'PAID':
        messages.error(request, 'This booking cannot be paid online.')
        return redirect('my_bookings')
    
    passenger = booking.passengers.first()
    
    tran_id = f"{booking.booking_ref}_{uuid.uuid4().hex[:8]}"
    
    payment_data = {
        'total_amount': float(booking.total_amount),
        'currency': 'BDT',
        'tran_id': tran_id,
        'success_url': request.build_absolute_uri(reverse('payment_success')),
        'fail_url': request.build_absolute_uri(reverse('payment_fail')),
        'cancel_url': request.build_absolute_uri(reverse('payment_cancel')),
        'ipn_url': request.build_absolute_uri(reverse('payment_ipn')),
        
        'cus_name': passenger.name if passenger else request.user.get_full_name(),
        'cus_email': passenger.email if passenger else request.user.email,
        'cus_phone': passenger.phone if passenger else request.user.phone_number,
        'cus_add1': passenger.address or 'N/A',
        'cus_city': 'Dhaka',
        'cus_country': 'Bangladesh',
        
        'product_name': f"Ticket for {booking.trip.ship.name}",
        'product_category': 'ticket',
        'num_of_item': booking.tickets.count(),
        
        'booking_id': booking.id,
        'user_id': request.user.id,
    }
    
    sslcz = SSLCommerz()
    response = sslcz.initiate_payment(payment_data)
    
    if response.get('status') == 'SUCCESS':
        booking.payment_session_key = response.get('sessionkey')
        booking.payment_tran_id = tran_id
        booking.save()
        return redirect(response['GatewayPageURL'])
    else:
        error_msg = response.get('failedreason', 'Unknown error')
        logger.error(f"Payment initiation failed for booking {booking.id}: {error_msg}")
        messages.error(request, 'Payment initiation failed. Please try again.')
        return redirect('my_bookings')

@csrf_exempt
@require_POST
def payment_ipn(request):
    """Step 2: SSLCOMMERZ sends Instant Payment Notification"""
    if not is_sslcommerz_ip(request):
        logger.warning(f"Blocked IPN from unauthorized IP: {get_client_ip(request)}")
        return HttpResponse('Unauthorized', status=403)
    
    try:
        post_data = request.POST.dict()
        logger.info(f"IPN received for transaction: {post_data.get('tran_id')}")
        
        sslcz = SSLCommerz()
        
        # Verify signature
        if not sslcz.verify_ipn_signature(
            post_data, 
            post_data.get('verify_sign'), 
            post_data.get('verify_key')
        ):
            logger.error(f"Invalid signature for transaction: {post_data.get('tran_id')}")
            return HttpResponse('Invalid signature', status=400)
        
        # Validate with SSLCOMMERZ
        val_id = post_data.get('val_id')
        validation = sslcz.validate_payment(val_id)
        
        if validation.get('status') not in ['VALID', 'VALIDATED']:
            logger.error(f"Validation failed for transaction: {post_data.get('tran_id')}")
            return HttpResponse('Validation failed', status=400)
        
        # Get booking
        booking_id = post_data.get('value_a')
        booking = Booking.objects.get(id=booking_id)
        
        # Verify amount
        paid_amount = float(post_data.get('amount', 0))
        if abs(paid_amount - float(booking.total_amount)) > 0.01:
            logger.error(f"Amount mismatch for booking {booking_id}")
            return HttpResponse('Amount mismatch', status=400)
        
        # Update booking
        booking.status = 'CONFIRMED'
        booking.payment_status = 'PAID'
        booking.payment_val_id = val_id
        booking.payment_date = timezone.now()
        booking.save()
        
        # Update tickets
        booking.tickets.update(status='CONFIRMED')
        
        # Send confirmation SMS
        try:
            seat_labels = [t.seat_object.label for t in booking.tickets.all()]
            send_booking_sms(booking, seat_labels)
        except Exception as e:
            logger.error(f"SMS failed for booking {booking_id}: {e}")
        
        logger.info(f"Payment successful for booking: {booking_id}")
        return HttpResponse('Payment processed successfully')
        
    except Booking.DoesNotExist:
        logger.error(f"Booking not found: {booking_id}")
        return HttpResponse('Booking not found', status=404)
    except Exception as e:
        logger.exception(f"IPN processing error: {e}")
        return HttpResponse('Internal error', status=500)

def payment_success(request):
    """Step 3a: User redirected here after successful payment"""
    messages.success(request, 'Payment completed successfully! Your tickets are confirmed.')
    return redirect('my_bookings')

def payment_fail(request):
    """Step 3b: User redirected here after failed payment"""
    messages.error(request, 'Payment failed. Please try again or contact support.')
    return redirect('my_bookings')

def payment_cancel(request):
    """Step 3c: User redirected here if they cancel payment"""
    messages.warning(request, 'Payment was cancelled. Your booking is still pending.')
    return redirect('my_bookings')