from django.urls import path
from .import views

urlpatterns = [
    path('', views.dashboard, name='admin_dashboard'),
    path("logout/", views.admin_logout, name="admin_logout"),

    # Ships
    path('ships/', views.ships, name='ships'),
    path('ships/<int:ship_id>/', views.ship_details, name='ship_details'),

    # Locations & Routes
    path('locations/', views.locations, name='locations'),
    path('counters/', views.counters, name='counters'),
    path('counters/<int:counter_id>/sales/', views.counter_sales_report, name='counter_sales_report'),
    path('counters/<int:counter_id>/sales/download-csv/', views.counter_sales_report_csv, name='counter_sales_report_csv'),
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
    path('deck/<int:deck_id>/view/', views.view_seat_plan, name='view_seat_plan'),
    
    # Trips
    path('trip/create/', views.save_trip_schedule, name='save_trip_schedule'),
    path('trip/schedule/', views.trip_schedule_list, name='trip_schedule_list'),
    path('trip/update/schedule/<int:schedule_id>/', views.update_trip_schedule, name='update_trip_schedule'),
    path('delete-trip-schedule/<int:pk>/', views.delete_trip_schedule, name='delete_trip_schedule'),
    path('trips/', views.trip_list, name='trip_list'),
    path('trips/<int:trip_id>/update/', views.update_trip, name='update_trip'),
    path('trips/management/', views.individual_trip_management, name='trip_management'),
    
    #team
    path('admin-panel/team/', views.manage_team, name='manage_team'),
    path('admin-panel/team/delete/<int:pk>/', views.delete_team_member, name='delete_team_member'),
    
    # Site Identity
    path('identity/', views.site_identity_view, name='site_identity'),
    path('banner/', views.banner, name='banner'),
    path('overview/', views.overview, name='overview'),
    
    # for search bar
    path('api/get-search-locations/', views.get_search_locations, name='get_search_locations'),

    
    #contact
    path('contact-us/banner/', views.contact_banner_view, name='contact_banner'),
    path('contact-us/messages/', views.contact_messages_view, name='contact_messages'),
    path('contact-us/info-cards/', views.contact_info_cards_view, name='contact_info_cards'),
    path('contact-us/map/', views.contact_map_view, name='contact_map'),
    path('contact-us/faq/', views.contact_faq_view, name='contact_faq'),
    
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
    
    #tckt booking
    path('tcktbook/', views.tcktbook, name='tcktbook'),
    path('book/seats/<int:trip_id>/', views.select_seats, name='select_seats'),
    path('book/confirm/', views.admin_book_confirm, name='admin_book_confirm'),
    path('booking/update-status/<int:booking_id>/<str:new_status>/', views.update_booking_status, name='update_booking_status'),
    path('trip/toggle-lock/<int:trip_id>/', views.toggle_trip_lock, name='toggle_trip_lock'),
    path('trip/toggle-single-seat/', views.toggle_single_seat_lock, name='toggle_single_seat_lock'),
    path('trip/report/<int:trip_id>/', views.trip_seat_report, name='trip_seat_report'),
    path('bookings/list/', views.passenger_list, name='passenger_list'),
    path('bookings/issued/', views.booking_issue_list, name='booking_issue_list'),
    path('bookings/pending/', views.booking_pending_list, name='booking_pending_list'),
    path('bookings/cancelled/', views.booking_cancel_list, name='booking_cancel_list'),
    path('bookings/expired/', views.booking_expired_list, name='booking_expired_list'),
    path('booking/extend-time/', views.extend_booking_time_api, name='extend_booking_time'),
    
    # In your urls.py
    path('booking/<int:booking_id>/stop-time/', views.stop_booking_time, name='stop_booking_time'),
    path('booking/<int:booking_id>/resume-time/', views.resume_booking_time, name='resume_booking_time'),
    path('booking/ticket/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('booking/visual-map/<int:booking_id>/', views.booking_visual_map, name='booking_visual_map'),
    path('booking/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('booking/booking/cancel-seats/', views.cancel_seats, name='admin_cancel_seats'),
    path('booking/trips/', views.trip_report_list, name='trip_report_list'),
    path('booking/manifest/<int:trip_id>/', views.trip_passenger_manifest, name='trip_passenger_manifest'),
    path('booking/manifest/<int:trip_id>/export/', views.export_manifest_xls, name='export_manifest_xls'),
    path('export-manifest-pdf/<int:trip_id>/', views.download_manifest_pdf, name='download_manifest_pdf'), 
    path('get-seat-details/<int:trip_id>/<int:seat_id>/', views.get_seat_details, name='get_seat_details'),
    
    # NEW API ENDPOINTS for seat holding - ADD THESE LINES
    path('check-seat-availability/', views.check_seat_availability, name='check_seat_availability'),
    path('create-seat-hold/', views.create_seat_hold, name='create_seat_hold'),
    path('release-seat-hold/', views.release_seat_hold, name='release_seat_hold'),
    path('api/check-multiple-seats/', views.check_multiple_seats_availability, name='check_multiple_seats'),
    path('api/create-multiple-holds/', views.create_multiple_seat_holds, name='create_multiple_holds'),
    path('api/release-multiple-holds/', views.release_multiple_seat_holds, name='release_multiple_holds'),
    
    #pos
    path('pos/select-trip/', views.pos_trip_select, name='pos_trip_select'),
    path('pos/booking/<int:trip_id>/', views.pos_booking_interface, name='pos_booking_interface'),
    path('pos/booking/confirm/', views.pos_book_confirm, name='pos_book_confirm'),
    
    # Vessel Showcase
    path('vessel-showcases/', views.vessel_showcase_list, name='vessel_showcases'),
    path('vessel-showcases/add/', views.add_vessel_showcase, name='add_vessel_showcase'),
    path('vessel-showcases/edit/<int:id>/', views.edit_vessel_showcase, name='edit_vessel_showcase'),
    
    # Cabin showcase
    path('cabins/', views.cabin_showcases, name='cabin_showcases'),
    path('cabins/add/', views.add_cabin_showcase, name='add_cabin_showcase'),
    path('cabins/edit/<int:pk>/', views.edit_cabin_showcase, name='edit_cabin_showcase'),
    
    # Featured Articles
    path('featured-articles/', views.featured_articles, name='featured_articles'),
    path('featured-articles/add/', views.add_featured_article, name='add_featured_article'),
    path('featured-articles/edit/<int:article_id>/', views.edit_featured_article, name='edit_featured_article'),
    
    # Footer Management
    # Main List & Column AJAX operations (Add/Edit/Delete)
    path('footer-management/', views.footer_management, name='footer_management'),
    path('footer-social-links/', views.footer_social_links_view, name='footer_social_links'),
    
    # Content Add/Edit (Separate Pages)
    path('footer-management/content/add/', views.add_content, name='add_content'),
    path('footer-management/content/edit/<int:id>/', views.edit_content, name='edit_content'),
]
