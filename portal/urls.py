from django.urls import path
from .import views


urlpatterns = [
    path('',views.home,name='home'),
    path('contact',views.contact,name='contact'),
    path('aboutus',views.aboutUs,name='aboutUs'),
    path('team',views.team,name='team'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blogDetails, name='blog_details'),
    path('destinations',views.destinations,name='destinations'),
    path('tour',views.tour,name='tour'),
    path('tourDetails',views.tourDetails,name='tourDetails'),
    

]