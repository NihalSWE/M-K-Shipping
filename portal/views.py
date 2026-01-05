from django.shortcuts import render,get_object_or_404, redirect
from admin_panel.models import *
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import datetime
from django.template.loader import render_to_string
from django.db.models import Min












def home (request):
    banner = HomeBanner.objects.filter(is_active=True).first()
    locations = Location.objects.all().order_by('name')
    # Fetch the overview section
    overview = CompanyOverview.objects.filter(is_active=True).first()
    
    
    context={
        'banner': banner,
        'locations': locations,
        'overview': overview, 
    }
    
    return render (request,'portal/index.html',context)

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



from django.db.models import Q # Import Q for complex queries

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


def get_available_destinations(request):
    from_id = request.GET.get('from_id')

    if not from_id:
        return JsonResponse({'results': []})

    locations = Location.objects.exclude(id=from_id).order_by('name')

    results = [
        {'id': str(loc.id), 'text': loc.name}
        for loc in locations
    ]

    return JsonResponse({'results': results})



def search_trips(request):
    from_loc_id = request.GET.get('from')
    to_loc_id = request.GET.get('to')
    date_str = request.GET.get('date')
    
    trips_found = []
    
    if from_loc_id and to_loc_id and date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return redirect('home') # Or handle error

        # 1. Fetch trips for the date
        all_trips = Trip.objects.filter(
            departure_datetime__date=date_obj, 
            is_published=True
        ).select_related('ship', 'route')

        for trip in all_trips:
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
                    
                    trips_found.append({
                        'trip': trip,
                        'stop_from': stop_from,
                        'stop_to': stop_to,
                        'preview_price': final_preview_price
                    })

    return render(request, 'portal/schedules/schedules.html', {
        'trips': trips_found,
        'locations': Location.objects.all(),
        'search_params': {
            'from': from_loc_id, # Matches {{ search_params.from }} in template
            'to': to_loc_id,     # Matches {{ search_params.to }} in template
            'date': date_str
        }
    })
    
    
# def get_trip_layout(request, trip_id):
#     trip = get_object_or_404(Trip, id=trip_id)
#     from_stop_id = request.GET.get('from_stop')
#     to_stop_id = request.GET.get('to_stop')
    
#     from_stop = get_object_or_404(RouteStop, id=from_stop_id)
#     to_stop = get_object_or_404(RouteStop, id=to_stop_id)

#     # 1. Get all booked/locked seat IDs for THIS specific segment
#     booked_seat_ids = set(trip.tickets.filter(
#         status__in=['BOOKED', 'LOCKED']
#     ).filter(
#         from_stop__stop_order__lt=to_stop.stop_order,
#         to_stop__stop_order__gt=from_stop.stop_order
#     ).values_list('seat_object_id', flat=True))

#     # 2. Pre-calculate prices per category (avoids calling get_price in loop)
#     # We only care about categories that are actually bookable
#     categories = SeatCategory.objects.filter(is_bookable=True)
#     price_map = {cat.id: trip.get_price(cat, from_stop, to_stop) for cat in categories}

#     # 3. Prepare the decks and objects
#     decks = trip.ship.decks.all().order_by('level_order').prefetch_related('layout_objects__category__icon')
    
#     # We attach the calculated data directly to the objects in memory
#     for deck in decks:
#         for obj in deck.layout_objects.all():
#             obj.is_booked = obj.id in booked_seat_ids
#             # If it's a bookable seat, get its pre-calculated price
#             obj.final_price = price_map.get(obj.category_id, 0) if obj.category.is_bookable else 0

#     context = {
#         'trip': trip,
#         'decks': decks,
#         'from_stop': from_stop,
#         'to_stop': to_stop,
#     }
    
#     html = render_to_string('portal/schedules/_seat_layout_content.html', context, request=request)
#     return JsonResponse({'html': html})

def get_seat_layout(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    from_stop_id = request.GET.get('from_stop')
    to_stop_id = request.GET.get('to_stop')
    
    stop_from = get_object_or_404(RouteStop, id=from_stop_id)
    stop_to = get_object_or_404(RouteStop, id=to_stop_id)

    # Core logic: Find seats already booked for any part of this journey
    occupied_seat_ids = Ticket.objects.filter(
        trip=trip,
        status__in=['BOOKED', 'LOCKED']
    ).filter(
        Q(from_stop__stop_order__lt=stop_to.stop_order) & 
        Q(to_stop__stop_order__gt=stop_from.stop_order)
    ).values_list('seat_object_id', flat=True)

    decks = trip.ship.decks.all().prefetch_related('layout_objects__category')

    return render(request, 'portal/schedules/_seat_layout.html', {
        'trip': trip,
        'decks': decks,
        'occupied_seats': occupied_seat_ids,
        'from_stop': stop_from,
        'to_stop': stop_to,
    })