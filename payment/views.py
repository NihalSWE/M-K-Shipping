import requests
import uuid
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse

# Use Sandbox Credentials
STORE_ID = 'testbox'
STORE_PASS = 'qwerty'
BASE_URL = "https://sandbox.sslcommerz.com"
# CHANGE THIS to your actual Ngrok URL
MY_DOMAIN = "https://f2ff-27-147-153-214.ngrok-free.app" 

def payment_home(request):
    """Simple page with the 'Pay' button"""
    print('payment page loaded')
    return render(request, 'payment/ssl_commerz/test_payment.html')

def initiate_payment(request):
    """Step 1: Create a session and redirect user to SSLCommerz"""
    tran_id = str(uuid.uuid4())[:10]  # Unique ID for this ticket
    
    post_data = {
        'store_id': STORE_ID,
        'store_passwd': STORE_PASS,
        'total_amount': 100.00,
        'currency': 'BDT',
        'tran_id': tran_id,
        'success_url': f"{MY_DOMAIN}/payment/success/",
        'fail_url': f"{MY_DOMAIN}/payment/fail/",
        'cancel_url': f"{MY_DOMAIN}/payment/cancel/",
        'ipn_url': f"{MY_DOMAIN}/payment/ipn/",
        'cus_name': 'Test Passenger',
        'cus_email': 'test@example.com',
        'cus_phone': '01700000000',
        'cus_add1': 'Dhaka',
        'cus_city': 'Dhaka',
        'cus_country': 'Bangladesh',
        'shipping_method': 'NO',
        'product_name': 'Launch Ticket',
        'product_category': 'Travel',
        'product_profile': 'general',
    }

    response = requests.post(f"{BASE_URL}/gwprocess/v4/api.php", data=post_data)
    response_data = response.json()
    
    print('response data: ', response_data)

    if response_data.get('status') == 'SUCCESS':
        return redirect(response_data['GatewayPageURL'])
    else:
        return JsonResponse({"error": "Failed to initiate session", "details": response_data})

@csrf_exempt
def payment_success(request):
    """Step 2: User returns here + Validation API check"""
    # Grab the val_id sent back by SSLCommerz
    val_id = request.POST.get('val_id')
    
    # ALWAYS validate the payment via Server-to-Server API
    validation_url = f"{BASE_URL}/validator/api/validationserverAPI.php?val_id={val_id}&store_id={STORE_ID}&store_passwd={STORE_PASS}"
    v_response = requests.get(validation_url).json()

    if v_response.get('status') == 'VALID' or v_response.get('status') == 'VALIDATED':
        # --- UPDATE YOUR DATABASE HERE ---
        # e.g., Ticket.objects.filter(tran_id=v_response['tran_id']).update(status='Paid')
        return HttpResponse(f"<h1>Payment Successful!</h1><p>Transaction ID: {v_response['tran_id']}</p>")
    
    return HttpResponse("<h1>Validation Failed!</h1>")

@csrf_exempt
def payment_ipn(request):
    """The 'Backdoor' Webhook for connectivity issues"""
    print("******************************IPN RECEIVED FROM SSLCOMMERZ:***************************************", request.POST)
    # Logic same as payment_success: Get val_id, call Validation API, update DB
    return HttpResponse("IPN Received")