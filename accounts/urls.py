from django.urls import path
from .import views





urlpatterns = [
    
        
    #Auth
    path('signin/', views.signin, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.signout, name='logout'),
    
    path('auth/send-login-otp/', views.send_login_otp_view, name='send_login_otp'),
    path('auth/verify-login-otp/', views.verify_login_otp_view, name='verify_login_otp'),
    
    
]