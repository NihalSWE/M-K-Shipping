from django.db import models

from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.conf import settings








    

class Ship(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    total_capacity = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.name

class Deck(models.Model):
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name='decks')
    name = models.CharField(max_length=50) # e.g., "1st Floor"
    level_order = models.IntegerField(default=1)

    # Grid Configuration
    grid_cols = models.IntegerField(default=24)
    total_rows = models.IntegerField(default=20, help_text="Current rows in the grid")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['level_order']
        
        
class SeatIcon(models.Model):
    """
    Defines available icons for the admin to choose from.
    Get codes from: https://icon-sets.iconify.design/
    """
    name = models.CharField(max_length=50, help_text="Human readable name (e.g., 'Double Bed')")
    iconify_code = models.CharField(max_length=100, help_text="The Iconify string (e.g., 'mdi:bed-double-outline')")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.iconify_code})"
    
    

class SeatCategory(models.Model):
    """ 
    Visual Categories: 'Double Cabin', 'Corridor', 'Section Label' 
    """
    name = models.CharField(max_length=50) 
    description = models.TextField(blank=True) # Added based on your request
    
    # Logic Flags
    is_bookable = models.BooleanField(default=True) 
    capacity = models.IntegerField(default=1) 
    
    # Visuals
    color_code = models.CharField(max_length=7, default="#FFFFFF") 
    
    icon = models.ForeignKey(
        SeatIcon, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='categories',
        help_text="Select the icon to display on the booking grid"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return self.name

class SeatFeature(models.Model):
    """ 
    Searchable Tags: 'River Side', 'AC', 'Quiet Zone'
    """
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.name

# --- 2. THE GRID SYSTEM ---

class LayoutObject(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='layout_objects')
    
    # Visual Classification
    category = models.ForeignKey(SeatCategory, on_delete=models.PROTECT)
    
    # Logical Tags (Multiple allowed)
    features = models.ManyToManyField(SeatFeature, blank=True)
    
    # Positioning
    row_index = models.PositiveIntegerField() 
    col_index = models.PositiveIntegerField()
    row_span = models.PositiveIntegerField(default=1)
    col_span = models.PositiveIntegerField(default=1)
    
    # Identity
    label = models.CharField(max_length=50) # "301" or "River Side"
    seat_identifier = models.CharField(max_length=20, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        # This ensures '101' can exist on Deck 1 and Deck 2, 
        # but you can't have two '101's on the SAME deck.
        unique_together = (('deck', 'row_index', 'col_index'), ('deck', 'seat_identifier'))

# --- 3. PRICING & TRIPS ---

class Division(models.Model):
    name = models.CharField(max_length=50)
    bn_name = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return self.name

class District(models.Model):
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=50)
    bn_name = models.CharField(max_length=50, blank=True)
    lat = models.CharField(max_length=20, null=True, blank=True)
    lon = models.CharField(max_length=20, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return self.name

class Thana(models.Model): # Upazila
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='thanas')
    name = models.CharField(max_length=50)
    bn_name = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.name

class Location(models.Model):
    name = models.CharField(max_length=100) # Can be same as district or custom
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    code = models.CharField(max_length=10, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return self.name

class Counter(models.Model):
    name = models.CharField(max_length=100)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='counters')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.location.name})"

class Route(models.Model):
    name = models.CharField(max_length=100)
    source = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='routes_starting')
    destination = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='routes_ending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return self.name

class RouteStop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    stop_order = models.PositiveIntegerField() # 0, 1, 2...
    time_offset_minutes = models.PositiveIntegerField(default=0, help_text="Minutes from start")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    class Meta:
        ordering = ['stop_order']
        unique_together = ('route', 'stop_order')

    def __str__(self):
        return f"{self.route.name} - Stop {self.stop_order}: {self.location.name}"

class RouteSegmentPricing(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='segment_prices')
    seat_category = models.ForeignKey(SeatCategory, on_delete=models.CASCADE)
    
    # Segment Logic
    from_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name='segment_prices_starts')
    to_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name='segment_prices_ends')
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        # One price per category per segment
        unique_together = ('route', 'seat_category', 'from_stop', 'to_stop')

    def __str__(self):
        return f"{self.route.name}: {self.from_stop.location.name} -> {self.to_stop.location.name} ({self.seat_category.name})"
    
    
    
class TripSchedule(models.Model):
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # What time of day does this trip start?
    departure_time = models.TimeField(null=True, blank=True, help_text="Standard daily departure time")
    arrival_time = models.TimeField(null=True, blank=True, help_text="Standard arrival time")
    
    # Is this schedule active?
    is_active = models.BooleanField(default=True)
    
    # How many days in advance should the system automatically open bookings?
    advance_booking_days = models.PositiveIntegerField(default=10)
    
    run_monday = models.BooleanField(default=True)
    run_tuesday = models.BooleanField(default=True)
    run_wednesday = models.BooleanField(default=True)
    run_thursday = models.BooleanField(default=True)
    run_friday = models.BooleanField(default=True)
    run_saturday = models.BooleanField(default=True)
    run_sunday = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ship.name} Schedule - {self.departure_time}"
    

class Trip(models.Model):
    schedule = models.ForeignKey(TripSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_trips')
    ship = models.ForeignKey(Ship, on_delete=models.PROTECT)
    route = models.ForeignKey(Route, on_delete=models.PROTECT)
    departure_datetime = models.DateTimeField()
    arrival_datetime = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=True, help_text="Set to False to hide this specific date from customers")
    
    price_multiplier = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=1.00,
        help_text="Global multiplier for this trip (e.g., 1.5 for Eid holiday)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"{self.ship.name} - {self.departure_datetime}"
    
    def get_price(self, category, from_stop, to_stop):
        """
        The 'Magic' function that handles your logic.
        """
        # 1. Check for specific amount override (TripPricing)
        override = self.pricings.filter(
            seat_category=category, 
            from_stop=from_stop, 
            to_stop=to_stop
        ).first()
        
        if override:
            return override.price

        # 2. Check for standard price (RouteSegmentPricing)
        standard = RouteSegmentPricing.objects.filter(
            route=self.route,
            seat_category=category,
            from_stop=from_stop,
            to_stop=to_stop
        ).first()

        if standard:
            # Apply the multiplier to the standard price
            return standard.price * self.price_multiplier
        
        return 0
    
    def is_seat_available(self, seat_object, from_stop, to_stop):
        # We use a transaction to prevent others from writing at the same time
        with transaction.atomic():
            start_order = from_stop.stop_order
            end_order = to_stop.stop_order

            # .select_for_update() locks these rows in the DB until the transaction is finished
            overlapping_exists = self.tickets.select_for_update().filter(
                seat_object=seat_object,
                status__in=['BOOKED', 'LOCKED']
            ).filter(
                Q(from_stop__stop_order__lt=end_order) & 
                Q(to_stop__stop_order__gt=start_order)
            ).exists()

            return not overlapping_exists
    
    

class TripPricing(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='pricings')
    seat_category = models.ForeignKey(SeatCategory, on_delete=models.CASCADE)
    
    # Segment Pricing Logic
    from_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name='pricing_starts')
    to_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name='pricing_ends')
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        unique_together = ('trip', 'seat_category', 'from_stop', 'to_stop')
        

# --- 4. BOOKING TRANSACTIONS ---

class Booking(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.PROTECT)
    booking_ref = models.CharField(max_length=12, unique=True)
    
    # Counter Logic
    counter = models.ForeignKey(Counter, null=True, blank=True, on_delete=models.SET_NULL)
    sales_channel = models.CharField(max_length=20, default='ONLINE', choices=(('ONLINE', 'Online'), ('COUNTER', 'Counter')))

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Return Trip Link
    linked_booking = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    
    @property
    def passenger_name(self):
        """Returns the user's full name, or username if name is missing."""
        if self.user:
            full_name = f"{self.user.first_name} {self.user.last_name}".strip()
            if full_name:
                return full_name
            return self.user.username  # Fallback to username if name is blank
        return "Unknown Guest"
    

class Ticket(models.Model):
    STATUS_CHOICES = (
        ('LOCKED', 'Temporary Hold'),
        ('BOOKED', 'Booked'),
        ('CANCELLED', 'Cancelled'),
    )
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='tickets')
    trip = models.ForeignKey('Trip', on_delete=models.PROTECT, related_name='tickets')
    seat_object = models.ForeignKey(LayoutObject, on_delete=models.PROTECT)
    passenger_name = models.CharField(max_length=100)
    
    # Segment Logic
    from_stop = models.ForeignKey(RouteStop, on_delete=models.PROTECT, related_name='tickets_starting')
    to_stop = models.ForeignKey(RouteStop, on_delete=models.PROTECT, related_name='tickets_ending')
    
    fare_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="The actual price the user paid/will pay at the time of booking."
    )

    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='LOCKED')
    
    # 5-Minute Lock Logic
    lock_created_at = models.DateTimeField(auto_now_add=True)
    lock_expires_at = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    
    
    
#-----------------------------------------------------------------------
#-------------------------------------------------------------------------

#Home

# --- SITE IDENTITY (Single Logo) ---
class SiteIdentity(models.Model):
    logo = models.ImageField(upload_to='site_identity/', help_text="Upload your website logo")

    def __str__(self):
        return "Website Logo"

class HomeBanner(models.Model):
    title = models.CharField(max_length=255, default="Gateway to Global Tours")
    description = models.TextField(default="Discover exclusive travel packages...")
    logo = models.FileField(upload_to='banner/logos/', help_text="Upload SVG or PNG")
    background_image = models.ImageField(upload_to='banner/bg/')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Home Banner"
        verbose_name_plural = "Home Banner"

    def __str__(self):
        return self.title
    
    
#Contact Us
class ContactBanner(models.Model):
    title = models.CharField(max_length=200, default="Contact Us", help_text="The main title like 'Contact Us'")
    background_image = models.ImageField(upload_to='banners/', help_text="Upload the breadcrumb background image")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "1. Contact Page Banner"
        verbose_name_plural = "1. Contact Page Banners"

    def __str__(self):
        return self.title
    
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False) # To track if admin opened it

    def __str__(self):
        return f"{self.name} - {self.created_at}"
    
class ContactInfoCard(models.Model):
    title = models.CharField(max_length=100) # e.g., "Our Location" or "Email Us"
    icon = models.ImageField(upload_to='contact_icons/') # The SVG or PNG icon
    description = models.TextField(help_text="The small gray text description") 
    contact_info = models.CharField(max_length=255, blank=True, null=True, help_text="The email, phone number, or link text. Leave empty for Location cards.")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
    
class ContactMap(models.Model):
    map_embed_code = models.TextField(help_text="Paste the full <iframe> code from Google Maps here.")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "Google Map Section"
    
    
# 1. FAQ Section Settings (Title & Image)
class ContactFAQSection(models.Model):
    title = models.CharField(max_length=200, default="Have questions?")
    side_image = models.ImageField(upload_to='contact/faq/', help_text="The image on the left side")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "Contact FAQ Section Settings"

# 2. The Actual Questions
class ContactFAQItem(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.IntegerField(default=0, help_text="Lower numbers appear first")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.question
    
    
# --- ABOUT US PAGE MODELS ---

class AboutBanner(models.Model):
    title = models.CharField(max_length=200, default="ABOUT US")
    background_image = models.ImageField(upload_to='about/banner/', help_text="Upload the top banner background image")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "About Page Banner"

class AboutStory(models.Model):
    subtitle = models.CharField(max_length=100, default="Our Story", help_text="Small text above title")
    title = models.CharField(max_length=200, default="Discover the World with Confidence")
    description = models.TextField(help_text="The main paragraph text")
    story_image = models.ImageField(upload_to='about/story/', help_text="The image on the right side")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "About Story Section"
    
    
# --- 1. MAIN GALLERY SECTION ---
class GallerySection(models.Model):
    subtitle = models.CharField(max_length=100, default="Gallery")
    title = models.CharField(max_length=200, default="Experience Through Images")
    description = models.TextField(default="Discover some of our finest work captured through visuals")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "Gallery Section Settings"

class GalleryImage(models.Model):
    image = models.ImageField(upload_to='gallery/main/')
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']

# --- 2. SEASONAL / TOURS SECTION ---
class SeasonalSection(models.Model):
    subtitle = models.CharField(max_length=100, default="Featured Tours")
    title = models.CharField(max_length=200, default="Discover Extraordinary Seasonal Specials")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return "Seasonal Section Settings"

class SeasonalTour(models.Model):
    title = models.CharField(max_length=200, help_text="e.g. 7 Days in Bali Paradise")
    image = models.ImageField(upload_to='gallery/tours/')
    link = models.CharField(max_length=255, default="#", help_text="Link to tour details page")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        
        
        
#Blog

class BlogBanner(models.Model):
    title = models.CharField(max_length=200, default="Our Blog")
    background_image = models.ImageField(upload_to='banners/', help_text="Upload the top banner image (e.g., 1920x400)")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Blog Page Banner"
        verbose_name_plural = "Blog Page Banners"

    def __str__(self):
        return "Blog Page Banner Setup"

from django.utils.text import slugify
class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='blog/')
    content = models.TextField()  # Use a RichText editor later if needed
    author = models.CharField(max_length=100, default="Admin")
    date = models.DateField(auto_now_add=True)
    read_time = models.CharField(max_length=50, default="2 Min Read", help_text="e.g. '5 Min Read'")
    
    slug = models.SlugField(unique=True, null=True, blank=True, max_length=200) 

    def save(self, *args, **kwargs):
        # 2. Logic: If slug is empty, create one from the Title
        if not self.slug:
            self.slug = slugify(self.title)
            
            # Simple check to handle duplicates (e.g., if you have 2 posts with same title)
            original_slug = self.slug
            counter = 1
            while BlogPost.objects.filter(slug=self.slug).exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
                
        super().save(*args, **kwargs)

    
    def __str__(self):
        return self.title

class BlogComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    name = models.CharField(max_length=100) # For now, simple text. Can be User FK later.
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.name} on {self.post.title}"
