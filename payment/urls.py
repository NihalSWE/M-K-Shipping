# payment/urls.py
from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('initiate/<int:booking_id>/', views.initiate_payment, name='initiate_payment'),
    path('success/', views.payment_success, name='payment_success'),
    path('fail/', views.payment_fail, name='payment_fail'),
    path('cancel/', views.payment_cancel, name='payment_cancel'),
    path('ipn/', views.payment_ipn, name='payment_ipn'),
]