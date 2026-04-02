from django.urls import path
from .import views


urlpatterns = [
    path('',views.home,name='home'),
    path('services',views.services,name='services'),
    path('technology-innovation/', views.technology_innovation_view, name='technology_innovation'),
    path('contact',views.contact,name='contact'),
    path('aboutus',views.aboutUs,name='aboutUs'),
    path('team',views.team,name='team'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blogDetails, name='blog_details'),
    path('destinations',views.destinations,name='destinations'),
    path('tour',views.tour,name='tour'),
    path('tourDetails',views.tourDetails,name='tourDetails'),
    
    
    #Auth
    path('signin',views.signin,name='signin'),
    path('signup',views.signup,name='signup'),
    
    path('get-destinations/', views.get_available_destinations, name='get_available_destinations'),
    
    # Schedules
    path('search-trips/', views.search_trips, name='search_trips'),
    path('get-seat-layout/<int:trip_id>/', views.get_seat_layout, name='get_seat_layout'),
    
    # booking
    path('booking/save/', views.save_booking_view, name='save_booking'),
    path("booking/send-otp/", views.send_booking_otp_view, name="send_booking_otp"),
    path("booking/verify-otp/", views.verify_booking_otp_view, name="verify_booking_otp"),
    # path("booking/otp/verify-login/", views.verify_booking_otp_login_view, name="verify_booking_otp_login"),
    path('booking/success/<str:booking_ref>/', views.booking_success, name='booking_success'),
    path("seats/hold/", views.hold_seats_view, name="hold_seats"),
    path("seats/release/", views.release_seats_view, name="release_seats"),
    path('booking/passenger-profile-by-phone/', views.get_passenger_profile_by_phone_view, name='passenger_profile_by_phone'),
    
    # my bookings
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    
    # profile
    path("profile/edit/", views.profile_edit_view, name="profile_edit"),
    path("account/", views.account_view, name="account"),
    
    # tickets
    path("ticket/<str:booking_ref>/<str:token>/", views.ticket_public_view, name="ticket_public"),
    path("ticket/<str:booking_ref>/<str:token>/qr.png", views.booking_qr_png_view, name="ticket_qr_png"),
    path("booking/<str:booking_ref>/ticket.pdf/", views.booking_ticket_pdf, name="booking_ticket_pdf"),
    
    # Cabin Showcase
    path('cabins/', views.all_cabins_view, name='all_cabins'),
    
    # Vessels Showcase
    path('vessels/', views.all_vessels, name='all_vessels'),
]