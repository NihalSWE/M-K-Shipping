# payment/sslcommerz.py
import requests
import hashlib
import hmac
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class SSLCommerz:
    def __init__(self):
        self.store_id = settings.SSLCOMMERZ_STORE_ID
        self.store_pass = settings.SSLCOMMERZ_STORE_PASSWORD
        self.is_live = settings.SSLCOMMERZ_IS_LIVE
        
        if self.is_live:
            self.api_url = "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
            self.validation_url = "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"
        else:
            self.api_url = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
            self.validation_url = "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"
        
        logger.info(f"SSLCommerz initialized for store: {self.store_id}")
    
    def initiate_payment(self, data):
        """Step 1: Create payment session"""
        post_data = {
            'store_id': self.store_id,
            'store_passwd': self.store_pass,
            'total_amount': data['total_amount'],
            'currency': data.get('currency', 'BDT'),
            'tran_id': data['tran_id'],
            'success_url': data['success_url'],
            'fail_url': data['fail_url'],
            'cancel_url': data['cancel_url'],
            'ipn_url': data['ipn_url'],
            
            # Customer Information
            'cus_name': data['cus_name'],
            'cus_email': data['cus_email'],
            'cus_add1': data.get('cus_add1', 'N/A'),
            'cus_add2': data.get('cus_add2', 'N/A'),
            'cus_city': data.get('cus_city', 'Dhaka'),
            'cus_state': data.get('cus_state', 'Dhaka'),
            'cus_postcode': data.get('cus_postcode', '1000'),
            'cus_country': data.get('cus_country', 'Bangladesh'),
            'cus_phone': data['cus_phone'],
            
            # Shipping Information
            'shipping_method': 'NO',
            'ship_name': data.get('ship_name', data['cus_name']),
            'ship_add1': data.get('ship_add1', data.get('cus_add1', 'N/A')),
            'ship_city': data.get('ship_city', data.get('cus_city', 'Dhaka')),
            'ship_postcode': data.get('ship_postcode', data.get('cus_postcode', '1000')),
            'ship_country': data.get('ship_country', data.get('cus_country', 'Bangladesh')),
            
            # Product Information
            'product_name': data['product_name'],
            'product_category': data.get('product_category', 'ticket'),
            'product_profile': 'general',
            'num_of_item': data['num_of_item'],
            
            # Custom data for tracking
            'value_a': str(data.get('booking_id', '')),
            'value_b': str(data.get('user_id', '')),
        }
        
        try:
            logger.info(f"Initiating payment for booking: {data.get('booking_id')}")
            response = requests.post(self.api_url, data=post_data, timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"Payment initiation failed: {e}")
            return {'status': 'FAILED', 'failedreason': str(e)}
    
    def validate_payment(self, val_id):
        """Validate payment after IPN"""
        validation_data = {
            'val_id': val_id,
            'store_id': self.store_id,
            'store_passwd': self.store_pass,
            'format': 'json'
        }
        
        try:
            response = requests.get(self.validation_url, params=validation_data, timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"Payment validation failed: {e}")
            return {'status': 'FAILED'}
    
    def verify_ipn_signature(self, post_data, received_sign, verify_key):
        """Verify IPN signature for security"""
        try:
            if not received_sign or not verify_key:
                return False
            
            keys = verify_key.split(',')
            verify_string = ''
            for key in keys:
                if key in post_data:
                    verify_string += str(post_data[key])
            
            expected_sign = hashlib.md5(
                (verify_string + self.store_pass).encode()
            ).hexdigest()
            
            return hmac.compare_digest(expected_sign, received_sign)
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False