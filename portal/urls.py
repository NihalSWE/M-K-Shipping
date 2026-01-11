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
    path('booking/success/<str:booking_ref>/', views.booking_success, name='booking_success'),
]