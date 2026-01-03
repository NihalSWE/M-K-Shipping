from django.urls import path
from .import views





urlpatterns = [
    
        
    #Auth
    path('signin/', views.signin, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.signout, name='logout'),
    
    
]