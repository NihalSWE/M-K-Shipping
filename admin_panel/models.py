from django.db import models

from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.conf import settings
import uuid








    

class Ship(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    total_capacity = models.IntegerField(default=0)
    # ADD THIS FIELD - NOTHING ELSE CHANGED
    image = models.ImageField(
        upload_to='ships/',
        null=True, 
        blank=True,
        help_text="Ship image (size: 275x145 pixels)"
    )
    
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
    
    def __str__(self):
        return self.label

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
    name = models.CharField(max_length=100) 
    district = models.ForeignKey('District', on_delete=models.SET_NULL, null=True, blank=True)
    code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def save(self, *args, **kwargs):
        # Only generate a new slug if it's a new object OR the name has changed
        if not self.slug or (self.pk and Location.objects.get(pk=self.pk).name != self.name):
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            # Check if this slug already exists (excluding the current instance if editing)
            while Location.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
            
        super().save(*args, **kwargs)

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
    
    
    
class CounterUser(models.Model):
    counter = models.ForeignKey('Counter', on_delete=models.CASCADE, related_name='user_assignments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='counter_assignments')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('counter', 'user')

    def __str__(self):
        return f"{self.user} -> {self.counter}"
    
    

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
    
    booking_close_offset_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Default minutes before departure when booking closes. Leave blank to use default 5 minutes."
    )
    
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
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name='trips')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='routes')
    departure_datetime = models.DateTimeField()
    arrival_datetime = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=True, help_text="Set to False to hide this specific date from customers")
    
    booking_close_offset_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minutes before departure when booking closes for this trip. Leave blank to inherit from schedule/default."
    )
    
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
    
    def get_booking_close_offset_minutes(self):
        """
        Priority:
        1. Trip-specific override
        2. Schedule default
        3. Fallback = 5 minutes
        """
        if self.booking_close_offset_minutes is not None:
            return self.booking_close_offset_minutes

        if self.schedule and self.schedule.booking_close_offset_minutes is not None:
            return self.schedule.booking_close_offset_minutes

        return 5

    def booking_cutoff_datetime(self):
        """
        After this datetime, the trip should not appear for booking.
        """
        return self.departure_datetime - timedelta(minutes=self.get_booking_close_offset_minutes())

    def is_booking_open(self):
        return timezone.now() < self.booking_cutoff_datetime()
    
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
    
    # Method 1: For frontend (simple version - used during booking)
    def is_seat_available(self, seat_object, from_stop, to_stop):
        """
        Simple version for frontend booking.
        This considers a seat available if:
        - It's not booked by anyone
        - User's own hold is OK (will be checked separately)
        """
        with transaction.atomic():
            start_order = from_stop.stop_order
            end_order = to_stop.stop_order

            # Check if seat is BOOKED by anyone
            booked_exists = self.tickets.select_for_update().filter(
                seat_object=seat_object,
                status__in=['BOOKED', 'CONFIRMED', 'LOCKED']
            ).filter(
                Q(from_stop__stop_order__lt=end_order) & 
                Q(to_stop__stop_order__gt=start_order)
            ).exists()

            if booked_exists:
                return False

            # If not booked, it's available (holds are handled separately)
            return True

    # Method 2: For admin panel (with exclude_user parameter)
    def is_seat_available_admin(self, seat_object, from_stop, to_stop, exclude_user=None):
        """
        Admin version that checks both tickets AND active holds.
        exclude_user: If provided, ignores holds/tickets belonging to this user.
        """
        with transaction.atomic():
            start_order = from_stop.stop_order
            end_order = to_stop.stop_order

            # Check TICKETS
            tickets_qs = self.tickets.select_for_update().filter(
                seat_object=seat_object,
                status__in=['BOOKED', 'CONFIRMED', 'LOCKED']
            ).filter(
                Q(from_stop__stop_order__lt=end_order) & 
                Q(to_stop__stop_order__gt=start_order)
            )

            # Check HOLDS
            holds_qs = SeatHold.objects.select_for_update().filter(
                trip=self,
                seat_object=seat_object,
                expires_at__gt=timezone.now()
            ).filter(
                Q(from_stop__stop_order__lt=to_stop.stop_order) &
                Q(to_stop__stop_order__gt=from_stop.stop_order)
            )

            # Handle exclude_user
            if exclude_user:
                if hasattr(exclude_user, 'is_authenticated') and exclude_user.is_authenticated:
                    tickets_qs = tickets_qs.exclude(booking__user=exclude_user)

                    # Support both old and new holder_id formats during transition
                    holds_qs = holds_qs.exclude(
                        Q(holder_id=str(exclude_user.id)) |
                        Q(holder_id=f"user_{exclude_user.id}")
                    )

            tickets_exist = tickets_qs.exists()
            holds_exist = holds_qs.exists()

            return not (tickets_exist or holds_exist)
        
    

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
    # --- CHOICES ---
    STATUS_CHOICES = (
        ('PENDING', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
        ('LOCKED', 'Admin Locked'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('PAID', 'Paid'),
        ('UNPAID', 'Unpaid'),
    )

    # --- FIELDS ---
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    trip = models.ForeignKey('Trip', on_delete=models.CASCADE) # specific 'Trip' string or class
    booking_ref = models.CharField(max_length=12, unique=True)
    
    # Counter Logic
    counter = models.ForeignKey('Counter', null=True, blank=True, on_delete=models.SET_NULL)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='issued_bookings',
        help_text="Admin/staff user who issued this booking."
    )
    
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='booked_bookings',
        help_text="Admin/staff user who created this booking."
    )
    
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cancelled_bookings',
        help_text="Admin/staff user who cancelled this booking."
    )
    
    sales_channel = models.CharField(max_length=20, default='ONLINE', choices=(('ONLINE', 'Online'), ('COUNTER', 'Counter')))

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    # Add this new field
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Booking Status (e.g., Is the seat held?)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # [NEW] Payment Status (e.g., Is the money collected?)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='UNPAID')
    
    # Return Trip Link
    linked_booking = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    # New field for time stop feature
    time_stopped = models.BooleanField(default=False)
    stopped_at = models.DateTimeField(null=True, blank=True)  # When time was stopped
    
    expiry_at = models.DateTimeField(null=True, blank=True, help_text="Auto-cancel time for unpaid bookings")
    seat_snapshot = models.CharField(max_length=255, blank=True, null=True, help_text="Stores seat numbers for expired bookings")
    
    # ===== NEW: Payment gateway fields =====
    payment_session_key = models.CharField(max_length=100, blank=True, null=True)
    payment_tran_id = models.CharField(max_length=100, blank=True, null=True)
    payment_val_id = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(blank=True, null=True)
    
    share_token = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    qr_image = models.ImageField(upload_to="booking_qr/", blank=True, null=True)
    ticket_pdf = models.FileField(upload_to="booking_pdfs/", blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Auto-set expiry if PENDING and not set
        if self.status == 'PENDING' and not self.expiry_at:
            self.expiry_at = timezone.now() + timezone.timedelta(hours=2)
        super().save(*args, **kwargs)
        
    @property
    def due_amount(self):
        total = self.total_amount or 0
        paid = self.paid_amount or 0
        due = total - paid
        return due if due > 0 else 0
    
    def ensure_share_token(self):
        if not self.share_token:
            self.share_token = uuid.uuid4().hex
            self.save(update_fields=["share_token"])
        return self.share_token

    def get_public_ticket_path(self):
        token = self.share_token or ""
        return f"/ticket/{self.booking_ref}/{token}/"
    
    
    def __str__(self):
        # Get first passenger name if exists, otherwise use user's name
        first_passenger = self.passengers.first()
        if first_passenger:
            passenger_display = first_passenger.name
        elif self.user:
            passenger_display = self.user.get_display_name() or self.user.phone_number or "Unknown"
        else:
            passenger_display = "No Passenger"
        
        return f"{self.booking_ref} - {passenger_display}"

    @property
    def passenger_name(self):
        """Returns the user's full name, or username if name is missing."""
        if self.user:
            full_name = f"{self.user.first_name} {self.user.last_name}".strip()
            if full_name:
                return full_name
            return self.user.username  # Fallback to username if name is blank
        return "Unknown Guest"
    

class Passenger(models.Model):
    GENDER_CHOICES = (
        (0, 'Male'),
        (1, 'Female'),
        (2, 'Other'),
    )

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='passengers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='booking_passengers')

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)

    gender = models.IntegerField(
        choices=GENDER_CHOICES,
        blank=True,
        null=True
    )

    address = models.TextField(blank=True, null=True)

    class Meta:
        pass
    
    

class Ticket(models.Model):
    STATUS_CHOICES = (
        ('LOCKED', 'Temporary Hold'),
        ('BOOKED', 'Booked'),
        ('CANCELLED', 'Cancelled'),
    )
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='tickets')
    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE, related_name='tickets')
    trip = models.ForeignKey('Trip', on_delete=models.CASCADE, related_name='tickets')
    seat_object = models.ForeignKey(LayoutObject, on_delete=models.CASCADE)
    passenger_name = models.CharField(max_length=100)
    
    # Segment Logic
    from_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name='tickets_starting')
    to_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name='tickets_ending')
    
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

class SeatHold(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="seat_holds")
    from_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name="seat_holds_from")
    to_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name="seat_holds_to")
    seat_object = models.ForeignKey(LayoutObject, on_delete=models.CASCADE, related_name="seat_holds")

    # holder_id = models.CharField(max_length=64, db_index=True)
    # holder = models.ForeignKey(
    #     settings.AUTH_USER_MODEL,
    #     on_delete=models.CASCADE,
    #     related_name="seat_holds",
    #     db_index=True
    # )
    holder_id = models.CharField(max_length=64, db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "from_stop", "to_stop", "seat_object"],
                name="uniq_seat_hold_per_segment"
            )
        ]

    def is_active(self):
        return self.expires_at > timezone.now()
    
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
    

class CompanyOverview(models.Model):
    title = models.CharField(max_length=200, default="Welcome to MK Shipping Lines")
    description = models.TextField(help_text="The main paragraph text.")
    key_points = models.TextField(help_text=" The list of key highlights (bullet points).")
    image = models.ImageField(upload_to='company_overview/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Home Overview"
        verbose_name_plural = "Home Overview"

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
    subtitle = models.CharField(max_length=100, default="Our Story", help_text="Small text above title" ,null=True,blank=True)
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




class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100, help_text="e.g. Lead Wildlife")
    
    # NEW FIELD: Their point of view or quote
    description = models.TextField(blank=True, null=True, help_text="A short quote or bio about the member.")
    
    image = models.ImageField(upload_to='team/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    

class VesselShowcase(models.Model):
    """ Comprehensive marketing and display information for a Vessel/Ship """
    
    # --- Link to Operations (Optional for Pre-launch) ---
    ship = models.OneToOneField(
        'Ship', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='showcase',
        help_text="Leave blank if this vessel is not yet operational/bookable."
    )
    
    # --- Basic Display Info ---
    name = models.CharField(max_length=100, help_text="Display name (e.g., Carnival Cruise)")
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="Auto-generated if left blank. Used for the URL (e.g., mv-grand-aqua)")
    tagline = models.CharField(max_length=200, blank=True, help_text="E.g., The Queen of the River")
    short_description = models.TextField(max_length=500, help_text="Brief summary for list/grid views")
    full_description = models.TextField(help_text="Detailed description for the main vessel page")
    
    # --- Media ---
    hero_image = models.ImageField(upload_to='vessel_showcase/heroes/')
    banner_image = models.ImageField(upload_to='vessel_showcase/banners/', blank=True, null=True, help_text="Banner image (4:1 ratio)")
    video_tour_url = models.URLField(blank=True, help_text="YouTube or Vimeo link for a virtual tour")
    
    # --- Technical Specifications (For Display) ---
    build_year = models.CharField(max_length=4, blank=True)
    length_meters = models.CharField(max_length=20, blank=True, help_text="E.g., 85m")
    top_speed = models.CharField(max_length=50, blank=True, help_text="E.g., 15 Knots")
    display_capacity = models.CharField(max_length=50, blank=True, help_text="E.g., 500+ Passengers")
    
    # --- Key Amenities (Booleans for quick icons/filtering) ---
    has_wifi = models.BooleanField(default=False)
    has_restaurant = models.BooleanField(default=False)
    has_cafe_bar = models.BooleanField(default=False)
    has_prayer_room = models.BooleanField(default=False)
    has_medical_facility = models.BooleanField(default=False)
    is_wheelchair_accessible = models.BooleanField(default=False)
    has_kids_play_area = models.BooleanField(default=False)
    has_entertainment = models.BooleanField(default=False, help_text="Live music, TV lounges, etc.")
    
    # --- Marketing & Status ---
    is_published = models.BooleanField(default=True, help_text="Show on the public website")
    is_upcoming = models.BooleanField(default=False, help_text="Flag as 'Coming Soon'")
    launch_date = models.DateField(null=True, blank=True, help_text="Expected launch date if upcoming")
    
    # --- SEO Metadata ---
    meta_title = models.CharField(max_length=150, blank=True)
    meta_description = models.TextField(max_length=160, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Showcase)"
    
    def save(self, *args, **kwargs):
        # Only generate a slug if one doesn't already exist
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            
            # Keep checking the database until we find a unique slug
            while VesselShowcase.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
                
            self.slug = slug
            
        super().save(*args, **kwargs)
    
    
class CabinShowcase(models.Model):
    """ Comprehensive marketing information for Seat/Cabin categories """
    
    # --- Display Hierarchy & Operations ---
    vessel = models.ForeignKey(
        'VesselShowcase', 
        on_delete=models.SET_NULL,  # Changed from CASCADE to prevent accidental deletion
        null=True,                  # Allows the database to store it as empty
        blank=True,                 # Allows the admin form to be submitted empty
        related_name='cabins',
        help_text="Optional: Link this to a specific vessel, or leave blank to use as a generic cabin/seat type across the fleet."
    )
    
    # Optional link to operational categories (can map to multiple if needed)
    operational_categories = models.ManyToManyField(
        'SeatCategory', 
        blank=True, 
        related_name='showcases',
        help_text="Link to the actual bookable categories in the system."
    )
    
    features = models.ManyToManyField(
        'SeatFeature', 
        blank=True, 
        related_name='showcases',
        help_text="Select the operational features (e.g., AC, River Side) that apply to this cabin class."
    )
    
    # --- Basic Info ---
    title = models.CharField(max_length=100, help_text="E.g., VIP Balcony Suite")
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    subtitle = models.CharField(max_length=150, blank=True, help_text="E.g., Ultimate comfort with a private view")
    short_description = models.TextField(max_length=300)
    full_description = models.TextField()
    
    # --- Media ---
    cover_image = models.ImageField(upload_to='cabin_showcase/covers/')
    # Cabin showcase update: optional wide banner image, same pattern as vessel showcase
    banner_image = models.ImageField(upload_to='cabin_showcase/banners/', blank=True, null=True, help_text="Banner image (4:1 ratio)")
    video_tour_url = models.URLField(blank=True, help_text="YouTube or Vimeo link")
    
    # --- Cabin Specifications ---
    guest_capacity = models.CharField(max_length=50, help_text="E.g., 2 Adults, 1 Child")
    room_size = models.CharField(max_length=50, blank=True, help_text="E.g., 250 sq. ft.")
    bed_type = models.CharField(max_length=100, blank=True, help_text="E.g., 1 King Bed or 2 Twin Beds")
    view_type = models.CharField(max_length=100, blank=True, help_text="E.g., River View, Interior, Forward-facing")
    
    # --- Cabin Features & Amenities ---
    is_air_conditioned = models.BooleanField(default=True)
    has_attached_washroom = models.BooleanField(default=False)
    has_tv = models.BooleanField(default=False)
    has_mini_fridge = models.BooleanField(default=False)
    has_balcony = models.BooleanField(default=False)
    includes_breakfast = models.BooleanField(default=False)
    has_room_service = models.BooleanField(default=False)
    
    # --- Marketing ---
    display_order = models.PositiveIntegerField(default=0, help_text="Order in which cabins appear on the vessel page")
    is_published = models.BooleanField(default=True)
    is_sold_out_badge = models.BooleanField(default=False, help_text="Manually flag as High Demand or Sold Out")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['vessel', 'display_order']

    def __str__(self):
        return f"{self.vessel.name} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Only generate a slug if one doesn't already exist
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            
            # Keep checking the database until we find a unique slug
            while CabinShowcase.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
                
            self.slug = slug
            
        super().save(*args, **kwargs)
        
        
        
class FeaturedArticle(models.Model):
    # --- Core/Mandatory Fields ---
    name = models.CharField(
        max_length=255, 
        help_text="The headline or title of the article."
    )
    organization_name = models.CharField(
        max_length=255, 
        help_text="Name of the publisher or newspaper (e.g., Forbes, TechCrunch)."
    )
    logo = models.ImageField(
        upload_to='featured_articles/logos/', 
        help_text="The logo of the organization."
    )
    description = models.TextField(
        help_text="A short excerpt, quote, or summary of the article."
    )
    url = models.URLField(
        max_length=500, 
        help_text="The direct link to the published article."
    )
    
    # --- Article Identification ---
    article_identifier = models.SlugField(
        max_length=255, 
        unique=True, 
        blank=True, 
        help_text="Unique identifier/slug. Auto-generates from the name if left blank."
    )

    # --- Other Important Fields ---
    publication_date = models.DateField(
        null=True, 
        blank=True, 
        help_text="The official date the article was published."
    )
    is_active = models.BooleanField(
        default=True, 
        help_text="Uncheck this to hide the article from the live website without deleting it."
    )
    
    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Default sorting: Newest publications first, falling back to newest added
        ordering = ['-publication_date', '-created_at']
        verbose_name = "Featured Article"
        verbose_name_plural = "Featured Articles"

    def __str__(self):
        return f"{self.name} | {self.organization_name}"

    def save(self, *args, **kwargs):
        # Auto-generate the unique identifier from the name if it isn't provided
        if not self.article_identifier:
            # We add a bit of the organization name to make it truly unique
            base_string = f"{self.organization_name}-{self.name}"
            self.article_identifier = slugify(base_string)[:250] 
        super().save(*args, **kwargs)
        
        
class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email
    
    
# Custom validator to ensure the title has a maximum of two words
def validate_max_two_words(value):
    if value:
        words = value.strip().split()
        if len(words) > 2:
            raise ValidationError("The title cannot exceed two words.")

class FooterColumn(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., GET CONNECTED, PRICING, COMPANY")
    order = models.PositiveIntegerField(default=0, help_text="Controls the left-to-right display order.")

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Footer Column"
        verbose_name_plural = "Footer Columns"

    def __str__(self):
        return self.name


class FooterContent(models.Model):
    # The dropdown selecting the column
    column = models.ForeignKey(
        FooterColumn, 
        on_delete=models.CASCADE, 
        related_name='contents'
    )
    
    # Optional fields
    title = models.CharField(
        max_length=50, 
        validators=[validate_max_two_words], 
        null=True, 
        blank=True,
        help_text="Submenu link text. Maximum 2 words."
    )
    
    # Mandatory field for URL validation
    url = models.CharField(
        max_length=255,
        validators=[
            RegexValidator(
                regex=r'^/',
                message="URL must start with a forward slash (e.g., /about-us)"
            )
        ],
        help_text="The relative URL path starting with '/'."
    )
    
    image = models.ImageField(upload_to='footer/images/', null=True, blank=True)
    banner_image = models.ImageField(upload_to='footer/banners/', null=True, blank=True)
    
    # Mandatory field
    description = models.TextField()

    # Optional ordering for the submenu items
    order = models.PositiveIntegerField(default=0, help_text="Controls the top-to-bottom display order.")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Footer Content"
        verbose_name_plural = "Footer Contents"

    def __str__(self):
        return self.title if self.title else f"Content item {self.id} under {self.column.name}"


class FooterSocialSettings(models.Model):
    facebook_url = models.URLField(max_length=255, blank=True)
    instagram_url = models.URLField(max_length=255, blank=True)
    youtube_url = models.URLField(max_length=255, blank=True)
    linkedin_url = models.URLField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Footer Social Settings"
        verbose_name_plural = "Footer Social Settings"

    def __str__(self):
        return "Footer Social Links"
