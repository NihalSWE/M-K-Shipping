from django.urls import path
from .import views





urlpatterns = [
    path('', views.dashboard, name='admin_dashboard'),

    # Ships
    path('ships/', views.ships, name='ships'),
    path('ships/<int:ship_id>/', views.ship_details, name='ship_details'),

    # Locations & Routes
    path('locations/', views.locations, name='locations'),
    path('counters/', views.counters, name='counters'),
    path('routes/', views.routes, name='routes'),
    path('routes/<int:route_id>/', views.route_details, name='route_details'),
    
    # Layouts and Seat Plans
    path('manage/structures/', views.manage_structures, name='manage_structures'),
    path('manage/bookables/', views.manage_bookable_categories, name='manage_bookable_categories'),
    path('manage-seat-features/', views.manage_seat_features, name='manage_seat_features'),
    path('seat-icons/', views.seat_icon_management, name='seat_icon_management'),
    path('deck/<int:deck_id>/design/', views.seat_plan_editor, name='seat_plan_editor'),
    path('deck/<int:deck_id>/save/', views.save_seat_layout, name='save_seat_layout'),
    path('deck/<int:deck_id>/update-rows/', views.update_deck_rows, name='update_deck_rows'),
    path('deck/<int:deck_id>/save/', views.save_seat_layout, name='save_seat_layout'),
    path('deck/<int:deck_id>/view/', views.view_seat_plan, name='view_seat_plan'),
    
    # Trips
    path('trip/create/', views.save_trip_schedule, name='save_trip_schedule'),
    path('trip/schedule/', views.trip_schedule_list, name='trip_schedule_list'),
    path('trip/update/schedule/<int:schedule_id>/', views.update_trip_schedule, name='update_trip_schedule'),
    path('delete-trip-schedule/<int:pk>/', views.delete_trip_schedule, name='delete_trip_schedule'),
    
    # Site Identity
    path('identity/', views.site_identity_view, name='site_identity'),
    path('banner/', views.banner, name='banner'),
    path('overview/', views.overview, name='overview'),
    #for search bar
    path('api/get-search-locations/', views.get_search_locations, name='get_search_locations'),

    #team
    path('admin-panel/team/', views.manage_team, name='manage_team'),
    path('admin-panel/team/delete/<int:pk>/', views.delete_team_member, name='delete_team_member'),
    #team
    #contact
    path('contact-us/banner/', views.contact_banner_view, name='contact_banner'),
    path('contact-us/messages/', views.contact_messages_view, name='contact_messages'),
    path('contact-us/info-cards/', views.contact_info_cards_view, name='contact_info_cards'),
    path('contact-us/map/', views.contact_map_view, name='contact_map'),
    path('contact-us/faq/', views.contact_faq_view, name='contact_faq'),
    #contact
    
    # About Us Management
    path('about-us/banner/', views.about_banner_view, name='about_banner'),
    path('about-us/story/', views.about_story_view, name='about_story'),
    
    #Destination gellery
    path('gallery/main/', views.gallery_main_view, name='gallery_main'),
    path('gallery/seasonal/', views.gallery_seasonal_view, name='gallery_seasonal'),
    
    # --- BLOG MANAGEMENT ---
    path('blog/banner/', views.blog_banner_update, name='admin_blog_banner'),
    path('blog/list/', views.blog_list, name='admin_blog_list'),
    path('blog/add/', views.blog_add, name='admin_blog_add'),
    path('blog/edit/<slug:slug>/', views.blog_edit, name='admin_blog_edit'),
    path('blog/delete/<slug:slug>/', views.blog_delete, name='admin_blog_delete'),
    path('blog/comments/', views.admin_comment_list, name='admin_comment_list'),
    path('blog/comments/delete/<int:id>/', views.admin_comment_delete, name='admin_comment_delete'),
    
    #user accounts---
    path('admin_user_list/', views.admin_user_list, name='admin_user_list'),
    path('admin_user_list/delete/<int:id>/', views.admin_user_delete, name='admin_user_delete'),
    path('users/edit/<int:id>/', views.admin_user_edit, name='admin_user_edit'),
    path('user_add/', views.user_add, name='user_add'),
    #user accounts---
    
    #tckt booking
    path('tcktbook/', views.tcktbook, name='tcktbook'),
    path('book/seats/<int:trip_id>/', views.select_seats, name='select_seats'),
    path('book/confirm/', views.admin_book_confirm, name='admin_book_confirm'),
    path('bookings/list/', views.booking_list, name='admin_booking_list'),
    path('booking/ticket/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('booking/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    #tckt booking
]