from django.shortcuts import render,get_object_or_404, redirect
from admin_panel.models import *
from django.http import JsonResponse
from django.core.paginator import Paginator
# Create your views here.

def home (request):
    banner = HomeBanner.objects.filter(is_active=True).first()
     # Fetch FAQ Data
    faq_settings = ContactFAQSection.objects.filter(is_active=True).first()
    faq_items = ContactFAQItem.objects.filter(is_active=True).order_by('order')
    context={
        'banner': banner,
        'faq_settings': faq_settings, 
        'faq_items': faq_items,
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

def team(request):
    return render (request,'portal/team/team.html')

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


