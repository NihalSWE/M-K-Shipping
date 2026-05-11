from django.shortcuts import render,get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from urllib3 import request
from admin_panel.models import *
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse, Http404
import io
import qrcode
from qrcode.constants import ERROR_CORRECT_M
from django.core.paginator import Paginator
from datetime import datetime
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth import update_session_auth_hash
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.core.cache import cache
from django.db.models import Q, Min, Prefetch, Count
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
import traceback
import logging
import random
import json
import uuid
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .utils import seat_hold_key, get_holder_id
from .booking_invoice.qr_generation import ensure_booking_qr
from .booking_invoice.pdf_generation import render_booking_pdf_from_html
from admin_panel.utils import send_sms_task, send_booking_sms












User = get_user_model()
logger = logging.getLogger(__name__)






# def home(request):
#     banner = HomeBanner.objects.filter(is_active=True).first()
#     locations = Location.objects.all().order_by('name')
#     overview = CompanyOverview.objects.filter(is_active=True).first()
    
#     # Fetch the latest 8 cabins for the slider
#     latest_cabins = CabinShowcase.objects.all().order_by('-id')[:8]
    
#     context = {
#         'banner': banner,
#         'locations': locations,
#         'overview': overview, 
#         'latest_cabins': latest_cabins,
#     }
    
#     return render(request, 'portal/index.html', context)


def home(request):
    banner = HomeBanner.objects.filter(is_active=True).first()
    locations = Location.objects.all().order_by('name')
    overview = CompanyOverview.objects.filter(is_active=True).first()
    
    # Fetch the latest 8 cabins for the slider
    latest_cabins = CabinShowcase.objects.all().order_by('-id')[:8]
    
    # --- NEW ROUTING LOGIC ---
    now = timezone.now()
    
    # 1. Get active trips (looking back 12 hours for ongoing trips)
    active_trips = Trip.objects.filter(
        departure_datetime__gte=now - timedelta(hours=12),
        is_published=True
    ).select_related('route')
    
    # --- NEW ROUTING LOGIC ---
    now = timezone.now()
    
    # 1. Get active trips (ONLY future trips, no looking back into the past)
    active_routes_qs = Trip.objects.filter(
        departure_datetime__gte=now,
        is_published=True
    ).values_list(
        'route__source__name', 
        'route__destination__name'
    ).distinct()
    
    # 2. Convert to a list and sort it alphabetically
    available_routes = sorted(list(active_routes_qs))
    # -------------------------
    
    # --- FEATURED ARTICLES LOGIC ---
    featured_articles = FeaturedArticle.objects.filter(is_active=True)

    context = {
        'banner': banner,
        'locations': locations,
        'overview': overview, 
        'latest_cabins': latest_cabins,
        'available_routes': available_routes,
        'featured_articles': featured_articles,
    }
    
    return render(request, 'portal/index.html', context)



def contact(request):
    # ==========================================
    # PART 2: Handle Form Submission (POST)
    # ==========================================
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            message = request.POST.get('message')

            if not name or not email or not message:
                return JsonResponse({'status': 'error', 'message': 'Please fill in required fields.'})

            ContactMessage.objects.create(
                name=name, email=email, phone=phone, message=message
            )
            return JsonResponse({'status': 'success', 'message': 'Your message has been sent successfully!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Something went wrong.'})

    # ==========================================
    # PART 1: Page Load (GET)
    # ==========================================
    
    # 1. Fetch Banner
    banner = ContactBanner.objects.filter(is_active=True).first()
    
    # 2. Fetch Info Cards (New!)
    cards = ContactInfoCard.objects.filter(is_active=True)
    
    # Fetch the Map
    google_map = ContactMap.objects.filter(is_active=True).first()
    
    # Fetch FAQ Data
    faq_settings = ContactFAQSection.objects.filter(is_active=True).first()
    faq_items = ContactFAQItem.objects.filter(is_active=True).order_by('order')

    context = {
        'banner': banner,
        'cards': cards, 
        'google_map': google_map,
        'faq_settings': faq_settings, 
        'faq_items': faq_items,
    }
    
    return render(request, 'portal/contact/contact.html', context)


def aboutUs (request):
    banner = AboutBanner.objects.filter(is_active=True).first()
    story = AboutStory.objects.filter(is_active=True).first()
    
    context = {
        'banner': banner,
        'story': story,
    }
    return render(request,'portal/aboutus/aboutus.html',context)
    
def services(request):
    return render(request,'portal/services/services.html')    
    

def team(request):
    """
    Displays the list of team members on the public 'Our Team' page.
    """
    # Fetch all members, newest first
    members = TeamMember.objects.all().order_by('-created_at')
    
    context = {
        'team_members': members
    }
    return render(request, 'portal/team/team.html', context)
    
    
    
def technology_innovation_view(request):
    context = {
        'page_title': 'Technology & Innovation',
        'breadcrumb_title': 'Technology & Innovation',
        'meta_description': 'Explore our advanced technology solutions for river transportation including online ticketing, GPS tracking, and digital innovations.'
    }
    return render(request, 'portal/t&i/technology_innovation.html', context)    

def blog(request): # This is your blog_list view
    
    # 1. Start with all posts
    posts_list = BlogPost.objects.all().order_by('-date')
    
    # 2. Check for Search Query
    query = request.GET.get('q')
    if query:
        # Filter by Title OR Content
        posts_list = posts_list.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query)
        )

    # 3. Pagination (Keep your existing code)
    paginator = Paginator(posts_list, 6)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    
    # 4. Sidebar Data
    recent_posts = BlogPost.objects.all().order_by('-date')[:3]
    banner = BlogBanner.objects.first()

    context = {
        'posts': posts,
        'recent_posts': recent_posts,
        'banner': banner,
        'query': query, # Pass query back to template (optional, to keep text in box)
    }
    return render(request, 'portal/blog/blog.html', context)

def blogDetails(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    recent_posts = BlogPost.objects.all().order_by('-date')[:4]

    # Handle Comment Submission
   # 1. Handle Comment Submission
    if request.method == 'POST':
        name = request.POST.get('name')
        message = request.POST.get('message')
        
        if name and message:
            BlogComment.objects.create(
                post=post,
                name=name,
                message=message
            )
            # Redirect to same page to prevent duplicate submission on refresh
            return redirect('blog_details', slug=slug)

    # 2. Get Data for Display
    comments = post.comments.all().order_by('-created_at') # Newest first
    recent_posts = BlogPost.objects.all().order_by('-date')[:3]
    banner = BlogBanner.objects.first()
    context = {
        'banner':banner,
        'post': post,
        'recent_posts': recent_posts,
        'comments': comments,
    }
    return render(request, 'portal/blog/blog-details.html', context)

def tour(request):
    return render (request,'portal/tour/tour.html')

def tourDetails(request):
    return render (request,'portal/tour/tour-details.html')


def destinations(request):
    gallery_settings = GallerySection.objects.first()
    gallery_images = GalleryImage.objects.all()

    # Part 2 Data
    seasonal_settings = SeasonalSection.objects.first()
    seasonal_tours = SeasonalTour.objects.all()

    context = {
        'gallery_settings': gallery_settings,
        'gallery_images': gallery_images,
        'seasonal_settings': seasonal_settings,
        'seasonal_tours': seasonal_tours,
    }
    return render (request,'portal/destinations/destination-details.html',context)


def signin(request):
    return render(request,'portal/auth/signin.html')

def signup(request):
    return render (request,'portal/auth/signup.html')


# def get_available_destinations(request):
#     from_id = request.GET.get('from_id')

#     if not from_id:
#         return JsonResponse({'results': []})

#     locations = Location.objects.exclude(id=from_id).order_by('name')

#     results = [
#         {'id': str(loc.id), 'text': loc.name}
#         for loc in locations
#     ]

#     return JsonResponse({'results': results})

def get_available_destinations(request):
    from_id = request.GET.get('from_id')

    if not from_id:
        return JsonResponse({'results': []})

    now = timezone.now()
    valid_destination_ids = set()

    # 1. Find all upcoming, published trips
    # We prefetch the route stops to prevent massive database queries (N+1 problem)
    upcoming_trips = Trip.objects.filter(
        departure_datetime__gte=now,
        is_published=True
    ).select_related('route').prefetch_related('route__stops')

    # 2. Loop through the trips to map out valid destinations
    for trip in upcoming_trips:
        stops = list(trip.route.stops.all())
        
        # Identify if the selected 'from' location is on this trip's route
        from_stop = next((s for s in stops if str(s.location_id) == str(from_id)), None)
        
        # If the origin exists on this route, find all stops that come AFTER it
        if from_stop:
            for stop in stops:
                if stop.stop_order > from_stop.stop_order:
                    # Add to our set (Sets automatically handle duplicates so we don't get repeated locations)
                    valid_destination_ids.add(stop.location_id)

    # 3. Fetch the actual Location objects alphabetically, filtering by our valid IDs
    locations = Location.objects.filter(id__in=valid_destination_ids).order_by('name')

    results = [
        {'id': str(loc.id), 'text': loc.name}
        for loc in locations
    ]
    
    print(f"DEBUG: For from_id={from_id}, found valid destination IDs: {valid_destination_ids}")

    return JsonResponse({'results': results})


def all_cabins_view(request):
    # Cabin showcase update: pass the latest available cabin banner to the public page header
    cabins = CabinShowcase.objects.all().order_by('-id')
    page_banner = cabins.exclude(banner_image='').exclude(banner_image__isnull=True).first()
    
    context = {
        'cabins': cabins,
        'page_banner': page_banner,
    }
    return render(request, 'portal/cabin_showcase/all_cabins.html', context)


def all_vessels(request):
    # Fetch all vessels. You can add .order_by('name') or similar if needed.
    vessels = VesselShowcase.objects.all()
    
    context = {
        'vessels': vessels
    }
    return render(request, 'portal/vessels_showcase/all_vessels.html', context)



def search_trips(request):
    from_loc_id = request.GET.get('from')
    to_loc_id = request.GET.get('to')
    date_str = request.GET.get('date')
    
    trips_found = []
    now = timezone.now()
    
    if from_loc_id and to_loc_id and date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return redirect('home') # Or handle error

        # 1. Fetch trips for the date
        all_trips = Trip.objects.filter(
            departure_datetime__date=date_obj,
            is_published=True
        ).select_related('ship', 'route', 'schedule')

        for trip in all_trips:
            # Evaluate if the trip is bookable, instead of skipping it entirely
            is_bookable = now < trip.booking_cutoff_datetime()

            # 2. Get the specific stops for this route
            # We fetch them to verify they exist and check their order
            stops = list(trip.route.stops.filter(location_id__in=[from_loc_id, to_loc_id]))
            
            if len(stops) == 2:
                # Identify which is 'from' and which is 'to' based on location_id
                stop_from = next(s for s in stops if str(s.location_id) == from_loc_id)
                stop_to = next(s for s in stops if str(s.location_id) == to_loc_id)
                
                # 3. Directional Check: Only show trips going the right way
                if stop_from.stop_order < stop_to.stop_order:
                    
                    # 4. Calculate "Starting From" Price
                    # Look for the cheapest price in standard pricing for this segment
                    base_min_price = RouteSegmentPricing.objects.filter(
                        route=trip.route,
                        from_stop=stop_from,
                        to_stop=stop_to,
                        seat_category__is_bookable=True
                    ).aggregate(Min('price'))['price__min'] or 0

                    # Check if there are specific overrides for this trip
                    override_min_price = TripPricing.objects.filter(
                        trip=trip,
                        from_stop=stop_from,
                        to_stop=stop_to,
                        seat_category__is_bookable=True
                    ).aggregate(Min('price'))['price__min']

                    # Use override if it exists, otherwise base price * multiplier
                    if override_min_price:
                        final_preview_price = override_min_price
                    else:
                        final_preview_price = base_min_price * trip.price_multiplier

                    # Calculate segment-specific times using offsets
                    departure_time = trip.departure_datetime + timedelta(minutes=stop_from.time_offset_minutes)
                    arrival_time = trip.departure_datetime + timedelta(minutes=stop_to.time_offset_minutes)

                    # ✅ NEW: Skip this trip entirely if the segment departure time has already passed
                    if now >= departure_time:
                        continue

                    # ---------------------------------------
                    # Segment-aware available seats calculation
                    # ---------------------------------------
                    start_order = stop_from.stop_order
                    end_order = stop_to.stop_order

                    # 1) Total bookable seats on this ship (LayoutObject with bookable category)
                    total_bookable_seats = LayoutObject.objects.filter(
                        deck__ship=trip.ship,
                        category__is_bookable=True
                    ).count()

                    # 2) Booked/locked tickets overlapping this segment
                    # Overlap rule: ticket.from < requested_to AND ticket.to > requested_from
                    booked_seat_ids = trip.tickets.filter(
                        status__in=['BOOKED', 'LOCKED']  # your Ticket statuses
                    ).filter(
                        Q(from_stop__stop_order__lt=end_order) &
                        Q(to_stop__stop_order__gt=start_order)
                    ).values_list('seat_object_id', flat=True).distinct()

                    # 3) Active holds overlapping this segment (any holder)
                    held_seat_ids = trip.seat_holds.filter(
                        expires_at__gt=timezone.now()
                    ).filter(
                        Q(from_stop__stop_order__lt=end_order) &
                        Q(to_stop__stop_order__gt=start_order)
                    ).values_list('seat_object_id', flat=True).distinct()

                    # Combine both sets
                    unavailable_ids = set(booked_seat_ids) | set(held_seat_ids)
                    available_seats = total_bookable_seats - len(unavailable_ids)
                    if available_seats < 0:
                        available_seats = 0

                    trips_found.append({
                        'trip': trip,
                        'stop_from': stop_from,
                        'stop_to': stop_to,
                        'preview_price': final_preview_price,
                        'segment_departure': departure_time,
                        'segment_arrival': arrival_time,
                        'available_seats': available_seats,
                        'total_bookable_seats': total_bookable_seats,
                        'is_bookable': is_bookable, # <-- Pass the flag to the template
                    })
                    
    # holder_id = request.user.id if request.user.is_authenticated else None
    holder_id = get_holder_id(request)
    is_authenticated = request.user.is_authenticated

    logged_in_user_prefill = None
    if request.user.is_authenticated:
        full_name = f"{request.user.first_name or ''} {request.user.last_name or ''}".strip()
        logged_in_user_prefill = {
            "name": full_name,
            "phone": _to_local_bd_phone(request.user.phone_number or ""),
            "email": getattr(request.user, "email", "") or "",
            "address": getattr(request.user, "address", "") or "",
        }

    return render(request, 'portal/schedules/schedules.html', {
        'trips': trips_found,
        'locations': Location.objects.all(),
        'search_params': {
            'from': from_loc_id,
            'to': to_loc_id,
            'date': date_str
        },
        'holder_id': holder_id,
        'is_authenticated': is_authenticated,
        'logged_in_user_prefill': logged_in_user_prefill,
    })


def get_seat_layout(request, trip_id):
    trip = get_object_or_404(Trip.objects.select_related('schedule'), id=trip_id)

    # Calculate if booking is open, but do NOT return an error.
    # We will pass this to the template to disable UI elements instead.
    is_bookable = trip.is_booking_open()
    
    # uncomment this only if the above `is_bookable = trip.is_booking_open()` is commented
    # if not trip.is_booking_open():
    #     return HttpResponse("Booking for this trip is closed.", status=400)


    from_stop_id = request.GET.get('from_stop')
    to_stop_id = request.GET.get('to_stop')
    
    print(f"DEBUG: Trip {trip_id} - From Stop: {from_stop_id}, To Stop: {to_stop_id}")
    
    stop_from = get_object_or_404(RouteStop, id=from_stop_id)
    stop_to = get_object_or_404(RouteStop, id=to_stop_id)
    
    # ✅ SAME FILTER AS YOUR CORE LOGIC (for genders only)
    occupied_tickets = Ticket.objects.filter(
        trip=trip,
        status__in=['BOOKED', 'LOCKED', 'PENDING'] # <-- 1. ADDED PENDING
    ).filter(
        Q(from_stop__stop_order__lt=stop_to.stop_order) &
        Q(to_stop__stop_order__gt=stop_from.stop_order)
    ).select_related('passenger').only('seat_object_id', 'passenger__gender', 'status') # <-- 2. ADDED 'status'

    # Core logic: Find seats already booked for any part of this journey
    occupied_seat_ids = list(Ticket.objects.filter(
        trip=trip,
        status__in=['BOOKED', 'LOCKED', 'PENDING']
    ).filter(
        Q(from_stop__stop_order__lt=stop_to.stop_order) & 
        Q(to_stop__stop_order__gt=stop_from.stop_order)
    ).values_list('seat_object_id', flat=True).distinct())
    
    # ✅ NEW: map seat_id -> gender ("0"/"1"/None)
    occupied_seat_genders = {}
    for t in occupied_tickets:
        if t.seat_object_id not in occupied_seat_genders:
            # 4. NEW LOGIC: If pending, force fallback class. Otherwise, use gender.
            if t.status == 'PENDING':
                occupied_seat_genders[t.seat_object_id] = None 
            else:
                g = t.passenger.gender if t.passenger else None
                occupied_seat_genders[t.seat_object_id] = str(g) if g is not None else None
            
    # 1) DB holds (fallback + admin visibility)
    active_holds = SeatHold.objects.filter(
        trip=trip,
        expires_at__gt=timezone.now()
    ).filter(
        Q(from_stop__stop_order__lt=stop_to.stop_order) &
        Q(to_stop__stop_order__gt=stop_from.stop_order)
    ).values('seat_object_id', 'holder_id', 'expires_at')

    db_held_seats = set()
    db_held_holder_ids = {}   # seat_id -> holder_id
    db_held_expires = {}      # seat_id -> iso string

    for h in active_holds:
        sid = h['seat_object_id']
        db_held_seats.add(sid)
        db_held_holder_ids[sid] = h['holder_id']
        db_held_expires[sid] = h['expires_at'].isoformat()

    # 2) REDIS REMOVED: Redis keys are blind to overlaps. 
    # The database query above perfectly calculates stop_order overlaps. 
    # We map the frontend context directly to the DB results.
    held_seats = db_held_seats
    held_holder_ids = db_held_holder_ids
    held_expires = db_held_expires
    
    # Optional: Keep this here for 1 day to verify in your terminal that IDs are found
    print(f"DEBUG: Trip {trip_id} has occupied seats: {occupied_seat_ids}")

    decks = trip.ship.decks.all().prefetch_related('layout_objects__category__icon')

    legend_categories = SeatCategory.objects.filter(
        is_bookable=True,
        layoutobject__deck__ship=trip.ship
    ).select_related('icon').distinct().order_by('name')
    
    # holder_id = request.user.id
    holder_id = get_holder_id(request)
    
    print("UI DEBUG", {
        "segment": f"{stop_from.location.name}->{stop_to.location.name}",
        "occupied_seat_ids": occupied_seat_ids,
        "held_seats": list(held_seats),
        "held_holder_ids": held_holder_ids,
    })

    return render(request, 'portal/schedules/_seat_layout.html', {
        'trip': trip,
        'decks': decks,
        'occupied_seats': occupied_seat_ids,
        'occupied_seat_genders': occupied_seat_genders,
        'from_stop': stop_from,
        'to_stop': stop_to,
        'holder_id': holder_id,
        'is_authenticated': request.user.is_authenticated,
        'held_seats': held_seats,
        'held_holder_ids': held_holder_ids,
        'held_expires': held_expires,
        'legend_categories': legend_categories,
        'is_bookable': is_bookable,
    })
    
    
def save_booking_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
    
    if not request.user.is_authenticated:
        if not request.session.get("booking_otp_verified"):
            return JsonResponse({'success': False, 'error': 'OTP verification required.'}, status=401)

    try:
        data = json.loads(request.body)
        trip_id = data.get('trip_id')
        from_stop_id = data.get('from_stop')
        to_stop_id = data.get('to_stop')
        passengers_data = data.get('passengers', [])

        print('Received booking data for booking:', data)

        if not all([trip_id, from_stop_id, to_stop_id]) or not passengers_data:
            return JsonResponse({'success': False, 'error': 'Missing required booking data.'}, status=400)
        
        # --- STRICT VALIDATION START ---
        # 1. Validate First Passenger (Mandatory: Name, Phone, Email, Address)
        first_p = passengers_data[0]
        first_phone = (first_p.get("phone") or "").strip()
        first_name = (first_p.get("name") or "").strip()
        first_email = (first_p.get("email") or "").strip()
        first_address = (first_p.get("address") or "").strip()

        if not first_phone or not first_name:
            return JsonResponse({'success': False, 'error': 'First passenger Name and Phone are required.'}, status=400)
        
        if not first_email or not first_address:
            return JsonResponse({'success': False, 'error': 'First passenger Email and Address are required.'}, status=400)

        # 2. Validate All Other Passengers (Mandatory: Name, Phone)
        for i, p in enumerate(passengers_data):
            p_phone = (p.get("phone") or "").strip()
            p_name = (p.get("name") or "").strip()
            if not p_phone or not p_name:
                return JsonResponse({'success': False, 'error': f'Name and Phone are required for passenger {i+1}.'}, status=400)
        # --- STRICT VALIDATION END ---

        # (Recommended) prevent duplicate seats in same request
        seat_ids = [p.get('seat_id') for p in passengers_data]
        if len(seat_ids) != len(set(seat_ids)):
            return JsonResponse({'success': False, 'error': 'Duplicate seat selected.'}, status=400)

        trip = Trip.objects.select_related('schedule').get(id=trip_id)

        if not trip.is_booking_open():
            return JsonResponse(
                {'success': False, 'error': 'Booking for this trip is closed.'},
                status=400
            )

        from_stop = RouteStop.objects.get(id=from_stop_id)
        to_stop = RouteStop.objects.get(id=to_stop_id)
        
        was_guest_booking = not request.user.is_authenticated
        holder_id = get_holder_id(request)

        with transaction.atomic():
            if request.user.is_authenticated:
                booking_user = request.user
                print('******booking_user ***: ', booking_user.email)
            else:
                # For guest booking: use the OTP verified phone as booking owner
                otp_phone = request.session.get("booking_otp_phone")
                if not otp_phone:
                    raise Exception("OTP phone not found. Please request OTP again.")

                booking_user, _, otp_phone_local = _get_or_create_user_by_bd_phone(
                    otp_phone,
                    defaults={
                        "username": f"user_{_to_local_bd_phone(otp_phone)}_{uuid.uuid4().hex[:4]}",
                        "email": None,
                        "user_type": 1,
                        "is_guest": True,
                    }
                )

                if not booking_user:
                    raise Exception("Invalid OTP phone. Please request OTP again.")
                
            holder_id = get_holder_id(request)
            
            first_phone_local = _to_local_bd_phone(first_phone)
            
            first_p = passengers_data[0] if passengers_data else {}
            apply_user_profile_if_missing(
                booking_user,
                name=(first_p.get("name") or "").strip(),
                email=(first_p.get("email") or "").strip(),
                address=(first_p.get("address") or "").strip(),
            )

            # ✅ Always normalize booking owner's phone to local format (01...)
            if first_phone_local and (booking_user.phone_number or "").strip() != first_phone_local:
                conflict_exists = User.objects.filter(phone_number=first_phone_local).exclude(id=booking_user.id).exists()
                if not conflict_exists:
                    booking_user.phone_number = first_phone_local
                    booking_user.save(update_fields=["phone_number"])

            total_amount = 0
            booking_ref = f"BK-{uuid.uuid4().hex[:8].upper()}"

            booking = Booking.objects.create(
                user=booking_user,
                trip=trip,
                booking_ref=booking_ref,
                total_amount=0,
                status='CONFIRMED'
            )
            
            channel_layer = get_channel_layer()
            # group = f"seats_{trip.id}_{from_stop.id}_{to_stop.id}"
            group = f"seats_{trip_id}"
            
            updated_user_phones = set()

            for p in passengers_data:
                # ADDED: select_for_update() to strictly lock the seat row during checkout
                seat = LayoutObject.objects.select_for_update().get(id=p['seat_id'])

                # ✅ Seat availability check (kept from original logic)
                if not trip.is_seat_available(seat, from_stop, to_stop):
                    raise Exception(f"Seat {seat.label} is no longer available.")
                
                # ✅ Redis hold check kept for reference, but disabled for sync with DB-first flow
                # key = seat_hold_key(trip_id, from_stop_id, to_stop_id, p['seat_id'])
                # r_payload = cache.get(key)
                #
                # # Redis: payload is dict {"holder_id": "..."}
                # if not isinstance(r_payload, dict) or r_payload.get("holder_id") != holder_id:
                #     raise Exception(f"Seat {seat.label} is not held by you anymore. Please reselect.")

                # ✅ HOLD CHECK (DB is source of truth for sync with admin save flow)
                db_hold = SeatHold.objects.filter(
                    trip=trip,
                    from_stop=from_stop,
                    to_stop=to_stop,
                    seat_object_id=seat.id,
                    expires_at__gt=timezone.now()
                ).first()

                if not db_hold:
                    raise Exception(f"Seat {seat.label} is not held by you anymore. Please reselect.")

                if db_hold.holder_id != holder_id:
                    raise Exception(f"Seat {seat.label} is currently on hold by another user.")

                fare = trip.get_price(seat.category, from_stop, to_stop)
                total_amount += fare

                p_phone_raw = (p.get('phone') or '').strip()
                p_phone = _to_local_bd_phone(p_phone_raw)
                p_name = (p.get('name') or '').strip()
                p_email = (p.get('email') or '').strip() or None
                p_gender_raw = p.get('gender', None)  # can be 0, 1, "0", "1", None
                p_gender = int(p_gender_raw) if p_gender_raw is not None else None
                p_address = (p.get('address') or None)

                if not p_phone:
                    raise Exception("Each passenger must have a phone number.")

                pass_user, created, p_phone = _get_or_create_user_by_bd_phone(
                    p_phone,
                    defaults={
                        "username": f"user_{p_phone}_{uuid.uuid4().hex[:4]}",
                        "email": p_email,
                        "user_type": 1,
                        "is_guest": True,
                    }
                )
                
                # Fill missing profile fields for this phone only once per request
                if p_phone and p_phone not in updated_user_phones:
                    apply_user_profile_if_missing(pass_user, name=p_name, email=p_email, address=p_address)
                    updated_user_phones.add(p_phone)

                if not pass_user:
                    raise Exception("Invalid passenger phone number.")

                # If a user is found by phone, do NOT update their User profile.
                # Only set profile fields when a NEW user is created.
                if created:
                    dirty = []

                    # Set password for newly auto-created passenger user
                    temp_password = get_random_string(length=12)
                    pass_user.set_password(temp_password)
                    dirty.append('password')

                    # Ensure guest flag
                    if getattr(pass_user, 'is_guest', None) is not True:
                        pass_user.is_guest = True
                        dirty.append('is_guest')

                    if dirty:
                        dirty = list(dict.fromkeys(dirty))
                        pass_user.save(update_fields=dirty)

                # ✅ Create a fresh Passenger snapshot PER SEAT (even if phone/user repeats)
                passenger = Passenger.objects.create(
                    booking=booking,
                    user=pass_user,
                    name=p_name,
                    phone=p_phone,
                    email=p_email,
                    gender=p_gender,
                    address=p_address,
                )
                    
                Ticket.objects.create(
                    booking=booking,
                    trip=trip,
                    seat_object=seat,
                    passenger=passenger,
                    passenger_name=p_name,
                    from_stop=from_stop,
                    to_stop=to_stop,
                    fare_amount=fare,
                    status='BOOKED',
                    lock_expires_at=timezone.now() + timedelta(days=1)
                )

                
                
                SeatHold.objects.filter(
                    trip=trip,
                    from_stop=from_stop,
                    to_stop=to_stop,
                    seat_object_id=seat.id
                ).delete()
                
                # ✅ Redis delete kept but disabled for DB-first sync flow
                cache.delete(seat_hold_key(trip.id, from_stop.id, to_stop.id, seat.id))

                # ✅ FIX: include start_order and end_order in the broadcast
                async_to_sync(channel_layer.group_send)(group, {
                    "type": "seat_event",
                    "action": "booked",
                    "seat_id": int(seat.id),
                    "start_order": from_stop.stop_order,
                    "end_order": to_stop.stop_order,
                    "gender": p_gender,
                })
                
                logger.info(f"p_gender: {p_gender}")
                print(f"print p_gender: {p_gender}")

            booking.total_amount = total_amount
            booking.payment_status = 'PAID'
            booking.save(update_fields=['total_amount', 'payment_status'])
            
            # [NEW:SHARE_TOKEN]
            # later put in the ssl commerz callback
            booking.ensure_share_token()
            # [/NEW:SHARE_TOKEN]
            
            def _send_confirm_sms():
                try:
                    send_booking_sms(booking)
                except Exception as sms_err:
                    print(f"BOOKING SMS ERROR: {sms_err}")

            transaction.on_commit(_send_confirm_sms)

        if was_guest_booking:
            login(request, booking_user)

            # Clear OTP session state after successful booking
            request.session["booking_otp_verified"] = False
            request.session["booking_otp_phone"] = None
            request.session.modified = True

        return JsonResponse({
            'success': True,
            'booking_ref': booking_ref,
            'message': 'Booking saved successfully!',
            'logged_in': True if was_guest_booking else request.user.is_authenticated,
            'user': {
                'first_name': (request.user.first_name or "").strip(),
                'phone_number': (request.user.phone_number or "").strip(),
                'display_name': ((request.user.first_name or "").strip() or (request.user.phone_number or "").strip()),
            } if request.user.is_authenticated else None
        })

    except Exception as e:
        # ✅ FULL traceback in terminal/logs
        logger.exception("save_booking_view failed")   # best
        print("SAVE_BOOKING_VIEW ERROR:", str(e))
        print(traceback.format_exc())

        # ✅ safety: if guest flow, don't keep OTP verified on error
        if not request.user.is_authenticated:
            request.session["booking_otp_verified"] = False
            request.session.modified = True

        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    

def apply_user_profile_if_missing(user, name=None, email=None, address=None):
    """
    Fill missing User profile fields only (never overwrite existing non-empty values).
    """
    if not user:
        return

    dirty = []

    # Name -> first_name / last_name (only if both empty)
    name = (name or "").strip()
    if name and not ((user.first_name or "").strip() or (user.last_name or "").strip()):
        parts = name.split(" ", 1)
        first = parts[0].strip()
        last = parts[1].strip() if len(parts) > 1 else ""

        if first and (user.first_name or "").strip() != first:
            user.first_name = first
            dirty.append("first_name")

        if last and (user.last_name or "").strip() != last:
            user.last_name = last
            dirty.append("last_name")

    # Email (only if empty)
    email = (email or "").strip()
    if email and not (getattr(user, "email", "") or "").strip():
        user.email = email
        dirty.append("email")

    # Address (only if empty)
    address = (address or "").strip()
    if address and not (getattr(user, "address", "") or "").strip():
        user.address = address
        dirty.append("address")

    if dirty:
        user.save(update_fields=dirty)

    
    
def _normalize_bd_phone(phone: str) -> str:
    """
    Normalize BD phone to 8801XXXXXXXXX.
    Returns "" for invalid formats.
    """
    clean = "".join(ch for ch in str(phone or "") if ch.isdigit())

    # Handle 00 international prefix (e.g. 0088019...)
    if clean.startswith("008801") and len(clean) == 15:
        clean = clean[2:]  # -> 8801...

    # 01XXXXXXXXX -> 8801XXXXXXXXX
    if clean.startswith("01") and len(clean) == 11:
        return "88" + clean

    # 1XXXXXXXXX -> 8801XXXXXXXXX
    if clean.startswith("1") and len(clean) == 10:
        return "880" + clean

    # Already normalized
    if clean.startswith("8801") and len(clean) == 13:
        return clean

    # Reject invalid values (IMPORTANT)
    return ""


def _to_local_bd_phone(phone: str) -> str:
    """
    Convert any BD format to local 11-digit format: 01XXXXXXXXX
    Accepts:
      - 01XXXXXXXXX
      - 1XXXXXXXXX
      - 8801XXXXXXXXX
      - +8801XXXXXXXXX
    """
    clean = "".join(ch for ch in str(phone or "") if ch.isdigit())

    if clean.startswith("01") and len(clean) == 11:
        return clean

    if clean.startswith("1") and len(clean) == 10:
        return "0" + clean

    if clean.startswith("8801") and len(clean) == 13:
        return clean[2:]   # ✅ FIXED: Just remove "88", keep "01XXXXXXXXX"

    return clean


def _otp_cache_key(holder_id: str, phone_norm: str) -> str:
    return f"booking_otp:{holder_id}:{phone_norm}"


@require_POST
def send_booking_otp_view(request):
    try:
        data = json.loads(request.body or "{}")
        phone = (data.get("phone") or "").strip()

        if not phone:
            return JsonResponse({"success": False, "error": "Phone number is required."}, status=400)

        phone_norm = _normalize_bd_phone(phone)

        # Basic sanity check
        if not phone_norm.startswith("8801") or len(phone_norm) != 13:
            return JsonResponse({"success": False, "error": "Invalid BD phone number."}, status=400)

        holder_id = get_holder_id(request)

        otp = f"{random.randint(0, 999999):06d}"
        ttl_seconds = 5 * 60  # 5 minutes

        cache.set(
            _otp_cache_key(holder_id, phone_norm),
            {
                "otp": otp,
                "phone": phone_norm,
                "created_at": timezone.now().isoformat(),
                "attempts": 0,
            },
            timeout=ttl_seconds
        )

        # ✅ Send SMS using your existing sender
        msg = f"MK Shipping OTP: {otp}. Valid for 5 minutes."
        send_sms_task(phone_norm, msg)

        # Also keep phone in session so we can reference it later
        request.session["booking_otp_phone"] = phone_norm
        request.session["booking_otp_verified"] = False
        request.session.modified = True

        return JsonResponse({
            "success": True,
            "message": f"OTP sent to {phone_norm}. Please enter it below.",
            "expires_in": ttl_seconds
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_POST
def verify_booking_otp_view(request):
    try:
        data = json.loads(request.body or "{}")
        phone = (data.get("phone") or "").strip()
        otp_input = (data.get("otp") or "").strip()

        if not phone or not otp_input:
            return JsonResponse({"success": False, "error": "Phone and OTP are required."}, status=400)

        phone_norm = _normalize_bd_phone(phone)
        holder_id = get_holder_id(request)

        payload = cache.get(_otp_cache_key(holder_id, phone_norm))
        if not isinstance(payload, dict):
            return JsonResponse({"success": False, "error": "OTP expired. Please request again."}, status=400)

        # throttle attempts
        payload["attempts"] = int(payload.get("attempts") or 0) + 1
        if payload["attempts"] > 5:
            cache.delete(_otp_cache_key(holder_id, phone_norm))
            return JsonResponse({"success": False, "error": "Too many attempts. Please request a new OTP."}, status=429)

        if str(payload.get("otp")) != otp_input:
            # update attempts back into cache (keep remaining TTL)
            cache.set(_otp_cache_key(holder_id, phone_norm), payload, timeout=5 * 60)
            return JsonResponse({"success": False, "error": "Invalid OTP. Please try again."}, status=400)

        # ✅ Verified
        request.session["booking_otp_verified"] = True
        request.session["booking_otp_phone"] = phone_norm
        request.session.modified = True

        # Optional: delete OTP so it can't be reused
        cache.delete(_otp_cache_key(holder_id, phone_norm))

        return JsonResponse({"success": True, "message": "OTP verified. You can confirm booking now."})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    

@require_POST
@ensure_csrf_cookie
def verify_booking_otp_login_view(request):
    """
    Verifies OTP AND logs the user in immediately.
    Keeps save_booking_view login as fallback.
    """
    try:
        data = json.loads(request.body or "{}")
        phone = (data.get("phone") or "").strip()
        otp_input = (data.get("otp") or "").strip()

        if not phone or not otp_input:
            return JsonResponse({"success": False, "error": "Phone and OTP are required."}, status=400)

        phone_norm = _normalize_bd_phone(phone)
        holder_id = get_holder_id(request)

        payload = cache.get(_otp_cache_key(holder_id, phone_norm))
        if not isinstance(payload, dict):
            return JsonResponse({"success": False, "error": "OTP expired. Please request again."}, status=400)

        payload["attempts"] = int(payload.get("attempts") or 0) + 1
        if payload["attempts"] > 5:
            cache.delete(_otp_cache_key(holder_id, phone_norm))
            return JsonResponse({"success": False, "error": "Too many attempts. Please request a new OTP."}, status=429)

        if str(payload.get("otp")) != otp_input:
            cache.set(_otp_cache_key(holder_id, phone_norm), payload, timeout=5 * 60)
            return JsonResponse({"success": False, "error": "Invalid OTP. Please try again."}, status=400)

        # ✅ Mark session verified (fallback for save_booking_view)
        request.session["booking_otp_verified"] = True
        request.session["booking_otp_phone"] = phone_norm
        request.session.modified = True

        # ✅ Ensure a user exists and log them in NOW
        user, _, phone_local = _get_or_create_user_by_bd_phone(
            phone_norm,
            defaults={
                "username": f"user_{_to_local_bd_phone(phone_norm)}_{uuid.uuid4().hex[:4]}",
                "email": None,
                "user_type": 1,
                "is_guest": True,
            }
        )

        if not user:
            return JsonResponse({"success": False, "error": "Invalid phone. Please request OTP again."}, status=400)

        login(request, user)

        # ✅ FORCE a fresh CSRF token after login (token may rotate on login)
        csrf_token = get_token(request)

        # Optional: delete OTP so it can't be reused
        cache.delete(_otp_cache_key(holder_id, phone_norm))

        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

        resp = JsonResponse({
            "success": True,
            "message": "OTP verified. Logged in successfully.",
            "logged_in": True,
            "csrfToken": csrf_token,  # ✅ IMPORTANT: send to frontend
            "user": {
                "first_name": (user.first_name or "").strip(),
                "phone_number": (getattr(user, "phone_number", "") or "").strip(),
                "display_name": (full_name or (getattr(user, "phone_number", "") or "").strip() or "Account"),
            }
        })
        return resp

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    
def booking_success(request, booking_ref):
    booking = get_object_or_404(
        Booking.objects.prefetch_related('tickets__seat_object'),
        booking_ref=booking_ref
    )

    # [NEW:QR_ON_INVOICE]
    # Ensure share_token exists (only once)
    if not booking.share_token:
        booking.share_token = uuid.uuid4().hex
        booking.save(update_fields=["share_token"])

    # Shareable public URL (use token)
    public_url = request.build_absolute_uri(f"/ticket/{booking.booking_ref}/{booking.share_token}/")

    # Generate+save QR only if missing
    ensure_booking_qr(booking, public_url)
    booking.refresh_from_db(fields=["qr_image"])
    # [/NEW:QR_ON_INVOICE]

    return render(request, 'portal/schedules/booking_success.html', {
        'booking': booking,
        'public_url': public_url,   # for share buttons
    })
    
    
@require_POST
def hold_seats_view(request):
    # if not request.user.is_authenticated:
    #     return JsonResponse({'success': False, 'error': 'Authentication required.'}, status=401)
    
    data = json.loads(request.body)
    trip_id = data.get('trip_id')
    from_stop_id = data.get('from_stop')
    to_stop_id = data.get('to_stop')
    seat_ids = data.get('seat_ids', [])

    if not all([trip_id, from_stop_id, to_stop_id]) or not seat_ids:
        return JsonResponse({'success': False, 'error': 'Missing payload.'}, status=400)
    
    holder_id = get_holder_id(request)

    trip = get_object_or_404(Trip, id=trip_id)
    from_stop = get_object_or_404(RouteStop, id=from_stop_id)
    to_stop = get_object_or_404(RouteStop, id=to_stop_id)

    # expires_at is created HERE
    expires_at = timezone.now() + timedelta(seconds=getattr(settings, 'SEAT_HOLD_SECONDS', 300))

    # group name for websocket broadcasts
    # group = f"seats_{trip_id}_{from_stop_id}_{to_stop_id}"
    group = f"seats_{trip_id}"
    channel_layer = get_channel_layer()

    # cleanup expired holds for this segment
    SeatHold.objects.filter(
        trip=trip,
        expires_at__lte=timezone.now()
    ).delete()

    held = []
    rejected = []

    # 1. NEW: Wrap the entire hold process in an atomic transaction
    from django.db import transaction # (Make sure this is imported at the top of your file)
    with transaction.atomic():
        # 2. NEW: Lock the layout objects so no one else can hold/book them right now
        locked_seats = LayoutObject.objects.filter(id__in=seat_ids).select_for_update()
        locked_seat_map = {seat.id: seat for seat in locked_seats}

        for seat_id in seat_ids:
            if seat_id not in locked_seat_map:
                rejected.append({'seat_id': seat_id, 'reason': 'invalid_seat'})
                continue
            
            # 3. CHANGED: Database is now the PRIMARY source of truth for holds because Redis cannot calculate overlapping segments.
            db_hold = SeatHold.objects.filter(
                trip=trip,
                seat_object_id=seat_id,
                expires_at__gt=timezone.now()
            ).filter(
                Q(from_stop__stop_order__lt=to_stop.stop_order) &
                Q(to_stop__stop_order__gt=from_stop.stop_order)
            ).exclude(holder_id=holder_id).first()

            if db_hold:
                rejected.append({'seat_id': seat_id, 'reason': 'held'})
                continue

            # 4. CHANGED: Included 'LOCKED' and 'PENDING' statuses to match your get_seat_layout logic
            if Ticket.objects.filter(
                trip=trip,
                status__in=['BOOKED', 'LOCKED', 'PENDING'] 
            ).filter(
                Q(from_stop__stop_order__lt=to_stop.stop_order) &
                Q(to_stop__stop_order__gt=from_stop.stop_order)
            ).filter(seat_object_id=seat_id).exists():
                rejected.append({'seat_id': seat_id, 'reason': 'booked'})
                continue

            # Create or refresh hold
            obj, created = SeatHold.objects.update_or_create(
                trip=trip,
                from_stop=from_stop,
                to_stop=to_stop,
                seat_object_id=seat_id,
                defaults={
                    'holder_id': holder_id,
                    'expires_at': expires_at,
                }
            )

            held.append(seat_id)
            
            # Still write to Redis so you can clear it quickly later if needed, but we don't rely on it for overlaps
            cache.set(
                seat_hold_key(trip_id, from_stop_id, to_stop_id, seat_id),
                {"holder_id": holder_id, "expires_at": expires_at.isoformat()},
                timeout=getattr(settings, "SEAT_HOLD_SECONDS", 300),
            )

            # BROADCAST HOLD EVENT
            async_to_sync(channel_layer.group_send)(group, {
                "type": "seat_event",
                "action": "hold",
                "seat_id": seat_id,
                "holder_id": holder_id,
                "expires_at": expires_at.isoformat(),
                "start_order": from_stop.stop_order,
                "end_order": to_stop.stop_order,
            })

    return JsonResponse({'success': True, 'held': held, 'rejected': rejected})


@require_POST
def release_seats_view(request):
    # if not request.user.is_authenticated:
    #     return JsonResponse({'success': False, 'error': 'Authentication required.'}, status=401)

    data = json.loads(request.body)
    trip_id = data.get('trip_id')
    from_stop_id = data.get('from_stop')
    to_stop_id = data.get('to_stop')
    seat_ids = data.get('seat_ids', [])
    
    holder_id = get_holder_id(request)

    if not all([trip_id, from_stop_id, to_stop_id]) or not seat_ids:
        return JsonResponse({'success': False, 'error': 'Missing payload.'}, status=400)

    trip = get_object_or_404(Trip, id=trip_id)
    from_stop = get_object_or_404(RouteStop, id=from_stop_id)
    to_stop = get_object_or_404(RouteStop, id=to_stop_id)

    # group = f"seats_{trip_id}_{from_stop_id}_{to_stop_id}"
    group = f"seats_{trip_id}"
    channel_layer = get_channel_layer()

    deleted = []

    qs = SeatHold.objects.filter(
        trip=trip,
        from_stop=from_stop,
        to_stop=to_stop,
        holder_id=holder_id,
        seat_object_id__in=seat_ids
    )

    deleted = list(qs.values_list('seat_object_id', flat=True))
    qs.delete()

    for seat_id in deleted:
        cache.delete(seat_hold_key(trip_id, from_stop_id, to_stop_id, seat_id))
        
        # ✅ FIX: include start_order and end_order in the broadcast
        async_to_sync(channel_layer.group_send)(group, {
            "type": "seat_event",
            "action": "release",
            "seat_id": seat_id,
            "start_order": from_stop.stop_order,
            "end_order": to_stop.stop_order,
        })

    return JsonResponse({'success': True, 'released': deleted})


@require_GET
def get_passenger_profile_by_phone_view(request):
    try:
        phone = (request.GET.get("phone") or "").strip()
        phone_norm = _normalize_bd_phone(phone)

        # Expect BD normalized format: 8801XXXXXXXXX
        if not phone_norm.startswith("8801") or len(phone_norm) != 13:
            return JsonResponse({
                "success": False,
                "error": "Invalid phone number."
            }, status=400)

        phone_local = _to_local_bd_phone(phone)
        user = User.objects.filter(
            Q(phone_number=phone_norm) | Q(phone_number=phone_local)
        ).first()

        if not user:
            return JsonResponse({
                "success": True,
                "found": False
            })

        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        
        print('user phone:', user.phone_number)
        print('user first name', user.first_name)
        print('user first name', user.last_name)

        # Optional gender support (if your User model has gender)
        user_gender = getattr(user, "gender", None)
        if user_gender in [0, 1, "0", "1"]:
            user_gender = str(user_gender)
        else:
            user_gender = None

        return JsonResponse({
            "success": True,
            "found": True,
            "data": {
                "name": full_name,
                "email": getattr(user, "email", "") or "",
                "address": getattr(user, "address", "") or "",
                "gender": user_gender,
                "phone": phone_norm,
            }
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)
        
        
def _get_or_create_user_by_bd_phone(phone_raw, defaults=None):
    """
    Resolve a user by BD phone in local/880 formats safely.
    Prefers local format (01...) to avoid duplicate-normalization collisions.
    Creates a new user only if neither format exists.
    Returns: (user, created, phone_local)
    """
    defaults = defaults or {}

    phone_local = _to_local_bd_phone(phone_raw)
    if not phone_local or not phone_local.startswith("01") or len(phone_local) != 11:
        return None, False, None

    phone_880 = _normalize_bd_phone(phone_local)

    # ✅ Prefer local format first
    user_local = User.objects.filter(phone_number=phone_local).first()
    if user_local:
        return user_local, False, phone_local

    # Fallback to old 880-stored row
    user_880 = User.objects.filter(phone_number=phone_880).first()
    if user_880:
        # Normalize safely only if local-format row does not exist
        if (user_880.phone_number or "").strip() != phone_local:
            if not User.objects.filter(phone_number=phone_local).exclude(id=user_880.id).exists():
                user_880.phone_number = phone_local
                user_880.save(update_fields=["phone_number"])
        return user_880, False, phone_local

    # Create brand new user in local format
    user = User.objects.create(
        phone_number=phone_local,
        **defaults
    )
    return user, True, phone_local


@login_required
def my_bookings_view(request):
    now = timezone.now()

    base_qs = (
        Booking.objects
        .filter(user=request.user)
        .select_related(
            "trip",
            "trip__ship",
            "trip__route",
            "trip__route__source",
            "trip__route__destination",
            "counter",
        )
        .prefetch_related(
            "passengers",
            Prefetch(
                "tickets",
                queryset=Ticket.objects.select_related(
                    "seat_object",
                    "from_stop__location",
                    "to_stop__location",
                    "passenger",
                ).order_by("id")
            ),
        )
        .order_by("-trip__departure_datetime", "-created_at")
    )

    # Split correctly
    upcoming_bookings = list(
        base_qs.filter(trip__departure_datetime__gte=now).order_by("trip__departure_datetime")
    )
    past_bookings = list(
        base_qs.filter(trip__departure_datetime__lt=now).order_by("-trip__departure_datetime")
    )

    # Add seat labels dynamically (for your template's booking.seat_labels)
    all_bookings = upcoming_bookings + past_bookings

    for booking in all_bookings:
        # Seat labels (your existing logic)
        booking.seat_labels = [
            (t.seat_object.label if getattr(t.seat_object, "label", None) else str(t.seat_object_id))
            for t in booking.tickets.all()
        ]

        # [NEW:BOOKING_QR+PUBLIC_URL]
        # Ensure token exists
        if not booking.share_token:
            booking.share_token = uuid.uuid4().hex
            booking.save(update_fields=["share_token"])

        # Build shareable public URL (token-protected)
        booking.public_url = request.build_absolute_uri(
            reverse("ticket_public", args=[booking.booking_ref, booking.share_token])
        )

        # Ensure QR image exists (generate only if missing)
        # Your ensure_booking_qr should "do nothing" if already exists
        ensure_booking_qr(booking, booking.public_url)

        # ✅ NEW: ensure we read the updated field after save
        booking.refresh_from_db(fields=["qr_image"])

        # booking.qr_src = booking.qr_image.url if booking.qr_image else ""
        # [/NEW:BOOKING_QR+PUBLIC_URL]

    return render(request, "portal/my_bookings/my_bookings.html", {
        "upcoming_bookings": upcoming_bookings,
        "past_bookings": past_bookings,
    })
    
    
    
@login_required
def profile_edit_view(request):
    if request.method == "GET":
        return render(request, "portal/profile/profile_edit.html", {
            "page_title": "My Profile",
        })

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)

    user = request.user
    form_type = (request.POST.get("form_type") or "").strip()

    if form_type == "profile":
        full_name = (request.POST.get("full_name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        address = (request.POST.get("address") or "").strip()
        
        if not full_name:
            return JsonResponse({"success": False, "error": "Full name is required."}, status=400)

        if not email:
            return JsonResponse({"success": False, "error": "Email is required."}, status=400)

        if not address:
            return JsonResponse({"success": False, "error": "Address is required."}, status=400)
        
        name_parts = full_name.split()

        if len(name_parts) == 1:
            first_name = name_parts[0]
            last_name = ""
        else:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])

        if email:
            email_conflict = (
                User.objects
                .filter(email__iexact=email)
                .exclude(id=user.id)
                .exists()
            )
            if email_conflict:
                return JsonResponse(
                    {"success": False, "error": "This email is already used by another account."},
                    status=400
                )

        dirty_fields = []

        if user.first_name != first_name:
            user.first_name = first_name
            dirty_fields.append("first_name")

        if user.last_name != last_name:
            user.last_name = last_name
            dirty_fields.append("last_name")

        if user.address != address:
            user.address = address
            dirty_fields.append("address")

        normalized_email = email
        
        if user.email != normalized_email:
            user.email = normalized_email
            dirty_fields.append("email")

        if dirty_fields:
            user.save(update_fields=dirty_fields + ["updated_at"])

        return JsonResponse({
            "success": True,
            "message": "Profile updated successfully.",
            "user": {
                "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
                "email": user.email or "",
                "phone_number": user.phone_number or "",
                "address": user.address or "",
                "display_name": (user.get_display_name() or "").strip(),
            }
        })

    if form_type == "password":
        new_password = (request.POST.get("new_password") or "").strip()
        confirm_password = (request.POST.get("confirm_password") or "").strip()

        if not new_password:
            return JsonResponse({"success": False, "error": "New password is required."}, status=400)

        if not confirm_password:
            return JsonResponse({"success": False, "error": "Confirm password is required."}, status=400)

        if len(new_password) < 8:
            return JsonResponse({"success": False, "error": "New password must be at least 8 characters."}, status=400)

        if new_password != confirm_password:
            return JsonResponse({"success": False, "error": "New password and confirm password do not match."}, status=400)

        # Optional: prevent setting the same password again
        if user.check_password(new_password):
            return JsonResponse({"success": False, "error": "New password must be different from your current password."}, status=400)

        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        update_session_auth_hash(request, user)

        return JsonResponse({"success": True, "message": "Password changed successfully."})

    return JsonResponse({"success": False, "error": "Invalid form submission."}, status=400)


@login_required
def account_view(request):
    now = timezone.now()

    base_qs = (
        Booking.objects
        .filter(user=request.user)
        .select_related(
            "trip",
            "trip__ship",
            "trip__route",
            "trip__route__source",
            "trip__route__destination",
            "counter",
        )
        .prefetch_related(
            "passengers",
            Prefetch(
                "tickets",
                queryset=Ticket.objects.select_related(
                    "seat_object",
                    "from_stop__location",
                    "to_stop__location",
                    "passenger",
                ).order_by("id")
            ),
        )
        .order_by("-trip__departure_datetime", "-created_at")
    )

    # ✅ counts for tab labels (don't use |length on page_obj)
    upcoming_qs = base_qs.filter(trip__departure_datetime__gte=now).order_by("trip__departure_datetime")
    past_qs = base_qs.filter(trip__departure_datetime__lt=now).order_by("-trip__departure_datetime")

    upcoming_count = upcoming_qs.count()
    past_count = past_qs.count()

    # ✅ pagination (10 per tab)
    upcoming_paginator = Paginator(upcoming_qs, 10)
    past_paginator = Paginator(past_qs, 10)

    up_page = request.GET.get("up_page")
    hist_page = request.GET.get("hist_page")

    upcoming_page_obj = upcoming_paginator.get_page(up_page)
    past_page_obj = past_paginator.get_page(hist_page)

    # ✅ Only process bookings that are actually displayed (max 20)
    visible_bookings = list(upcoming_page_obj.object_list) + list(past_page_obj.object_list)

    for booking in visible_bookings:
        booking.seat_labels = [
            (t.seat_object.label if getattr(t.seat_object, "label", None) else str(t.seat_object_id))
            for t in booking.tickets.all()
        ]

        if not booking.share_token:
            booking.share_token = uuid.uuid4().hex
            booking.save(update_fields=["share_token"])

        booking.public_url = request.build_absolute_uri(
            reverse("ticket_public", args=[booking.booking_ref, booking.share_token])
        )

        ensure_booking_qr(booking, booking.public_url)
        booking.refresh_from_db(fields=["qr_image"])

    # main account tabs (bookings/profile)
    active_tab = request.GET.get("tab") or "bookings"
    if active_tab not in ("bookings", "profile"):
        active_tab = "bookings"

    # ✅ booking sub-tabs (upcoming/history) keep active on pagination clicks
    booking_tab = request.GET.get("booking_tab") or "upcoming"
    if booking_tab not in ("upcoming", "history"):
        booking_tab = "upcoming"

    return render(request, "portal/account/account.html", {
        "page_title": "My Account",

        # ✅ paginated objects (use these in template loops)
        "upcoming_page_obj": upcoming_page_obj,
        "past_page_obj": past_page_obj,

        # ✅ counts for labels
        "upcoming_count": upcoming_count,
        "past_count": past_count,

        # ✅ which booking sub-tab is active
        "booking_tab": booking_tab,

        "active_tab": active_tab,
    })
    
    
def ticket_public_view(request, booking_ref, token):
    booking = get_object_or_404(
        Booking.objects.prefetch_related('tickets__seat_object'),
        booking_ref=booking_ref
    )

    if not booking.share_token or booking.share_token != token:
        raise Http404("Invalid ticket link.")

    public_url = request.build_absolute_uri(f"/ticket/{booking.booking_ref}/{booking.share_token}/")

    # If QR is missing for some reason, generate it here too (safe)
    ensure_booking_qr(booking, public_url)

    return render(request, "portal/schedules/booking_success.html", {
        "booking": booking,
        "public_url": public_url,
    })


def booking_qr_png_view(request, booking_ref, token):
    booking = get_object_or_404(Booking, booking_ref=booking_ref)

    if not booking.share_token or booking.share_token != token:
        raise Http404("Invalid ticket link.")

    if booking.payment_status != "PAID":
        raise Http404("Ticket not available yet.")

    public_url = request.build_absolute_uri(booking.get_public_ticket_path())

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=2
    )
    qr.add_data(public_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0b4a78", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return HttpResponse(buf.getvalue(), content_type="image/png")


def booking_ticket_pdf(request, booking_ref):
    """
    Authenticated download (recommended for user dashboard / success page).
    """
    booking = get_object_or_404(
        Booking.objects.prefetch_related("tickets__seat_object__category", "tickets__from_stop__location", "tickets__to_stop__location"),
        booking_ref=booking_ref
    )

    # Optional: security (recommended)
    # Only the owner or staff can download
    if not request.user.is_authenticated:
        raise Http404("Not found.")
    if booking.user_id != request.user.id and not request.user.is_staff:
        raise Http404("Not found.")

    # Ensure token exists because we show share links inside PDF (optional but nice)
    if not booking.share_token:
        booking.share_token = uuid.uuid4().hex
        booking.save(update_fields=["share_token"])

    public_url = request.build_absolute_uri(f"/ticket/{booking.booking_ref}/{booking.share_token}/")

    html = render_to_string(
        "portal/my_bookings/booking_invoice_pdf.html",
        {
            "booking": booking,
            "public_url": public_url,
        },
        request=request
    )

    base_url = request.build_absolute_uri("/")  # so relative URLs /static/... resolve
    pdf_bytes = render_booking_pdf_from_html(html, base_url=base_url)

    filename = f"MK_Ticket_{booking.booking_ref}.pdf"
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


def subscribe_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email field cannot be empty.'})
        
        # Backend format validation
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'status': 'error', 'message': 'Invalid email format. Please enter a valid address.'})
        
        # Check for duplicates
        if NewsletterSubscriber.objects.filter(email=email).exists():
            return JsonResponse({'status': 'error', 'message': 'You are already subscribed!'})
        
        # Save to database
        NewsletterSubscriber.objects.create(email=email)
        return JsonResponse({'status': 'success', 'message': 'Successfully subscribed! Welcome aboard.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


def footer_page_view(request, page_path):
    # 1. Clean the incoming path completely
    clean_path = page_path.strip('/')
    
    # 2. Reconstruct exactly how it should look in the DB
    db_search_url = f"/{clean_path}"
    
    # DEBUG: This will print in your terminal. If you don't see this print, 
    # the request isn't even hitting this view (which points back to Suspect 1).
    print(f"\n--- DEBUG DYNAMIC PAGE ---")
    print(f"Browser requested path: {page_path}")
    print(f"Searching database for: {db_search_url}")
    print(f"--------------------------\n")
    
    # 3. Try to find it. If it fails, try adding a trailing slash just in case 
    # it was saved that way in the admin panel.
    try:
        page_data = FooterContent.objects.get(url=db_search_url)
    except FooterContent.DoesNotExist:
        try:
            page_data = FooterContent.objects.get(url=f"{db_search_url}/")
        except FooterContent.DoesNotExist:
            raise Http404("Dynamic page not found in FooterContent database.")
    
    # Pass it to your updated template path
    return render(request, 'portal/dynamic_pages/dynamic_footer_pages.html', {'page': page_data})


