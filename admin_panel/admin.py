from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Prefetch
from .models import *









class DeckInline(admin.TabularInline):
    model = Deck
    extra = 1

class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 2
    ordering = ['stop_order']

class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    readonly_fields = ['fare_amount', 'lock_expires_at']
    can_delete = True

class TripPricingInline(admin.TabularInline):
    model = TripPricing
    extra = 1

# --- 2. ASSETS & SEATING CONFIGURATION ---

@admin.register(Ship)
class ShipAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'total_capacity', 'created_at')
    search_fields = ('name', 'code')
    inlines = [DeckInline]

@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ('name', 'ship', 'level_order', 'grid_cols', 'total_rows')
    list_filter = ('ship',)
    # Added search_fields to fix autocomplete error
    search_fields = ('name', 'ship__name') 

@admin.register(SeatIcon)
class SeatIconAdmin(admin.ModelAdmin):
    list_display = ('name', 'iconify_code')
    search_fields = ('name', 'iconify_code')

@admin.register(SeatCategory)
class SeatCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_bookable', 'capacity', 'color_code')
    list_editable = ('is_bookable', 'color_code')
    # Added search_fields to fix autocomplete error
    search_fields = ('name',) 

@admin.register(SeatFeature)
class SeatFeatureAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(LayoutObject)
class LayoutObjectAdmin(admin.ModelAdmin):
    list_display = ('label', 'seat_identifier', 'deck', 'category', 'row_index', 'col_index')
    list_filter = ('deck__ship', 'deck', 'category')
    search_fields = ('label', 'seat_identifier')
    # These require search_fields in DeckAdmin and SeatCategoryAdmin
    autocomplete_fields = ('category', 'deck')

# --- 3. GEOGRAPHY & LOCATIONS ---

@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ('name', 'bn_name')
    search_fields = ('name', 'bn_name')

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'division', 'bn_name')
    list_filter = ('division',)
    search_fields = ('name', 'bn_name')

@admin.register(Thana)
class ThanaAdmin(admin.ModelAdmin):
    list_display = ('name', 'district')
    list_filter = ('district__division', 'district')
    search_fields = ('name', 'bn_name')

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'district')
    search_fields = ('name', 'code')

@admin.register(Counter)
class CounterAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'is_active')
    list_filter = ('location', 'is_active')
    search_fields = ('name',)

# --- 4. ROUTES & PRICING ---

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'source', 'destination')
    search_fields = ('name',)
    inlines = [RouteStopInline]

@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = ('route', 'location', 'stop_order', 'time_offset_minutes')
    list_filter = ('route',)
    # Helps when selecting stops in pricing forms
    search_fields = ('location__name', 'route__name')

@admin.register(RouteSegmentPricing)
class RouteSegmentPricingAdmin(admin.ModelAdmin):
    list_display = ('route', 'seat_category', 'from_stop', 'to_stop', 'price')
    list_filter = ('route', 'seat_category')

# --- 5. TRIP OPERATIONS ---

@admin.register(TripSchedule)
class TripScheduleAdmin(admin.ModelAdmin):
    list_display = ('ship', 'route', 'departure_time', 'is_active')
    list_filter = ('is_active', 'ship', 'route')
    fieldsets = (
        (None, {'fields': ('ship', 'route', 'is_active')}),
        ('Date Range', {'fields': ('start_date', 'end_date', 'departure_time', 'arrival_time', 'advance_booking_days')}),
        ('Running Days', {'fields': (
            'run_monday', 'run_tuesday', 'run_wednesday', 'run_thursday', 
            'run_friday', 'run_saturday', 'run_sunday'
        )}),
    )

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('ship', 'route', 'departure_datetime', 'price_multiplier', 'is_published')
    list_filter = ('is_published', 'ship', 'departure_datetime')
    list_editable = ('is_published', 'price_multiplier')
    inlines = [TripPricingInline]
    date_hierarchy = 'departure_datetime'
    # Important for selecting trips in Booking admin
    search_fields = ('ship__name', 'route__name') 

@admin.register(TripPricing)
class TripPricingAdmin(admin.ModelAdmin):
    list_display = ('trip', 'seat_category', 'price')
    list_filter = ('trip__ship', 'seat_category')

# --- 6. BOOKINGS & TICKETS ---

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_ref', 'user', 'trip', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'sales_channel', 'created_at')
    search_fields = ('booking_ref', 'user__username', 'user__email', 'user__first_name')
    readonly_fields = ('booking_ref',)
    inlines = [TicketInline]
    autocomplete_fields = ('trip', 'user')
    actions = ['really_delete_selected']

    def really_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.delete() # This ensures our Step 1 cleanup logic runs
    really_delete_selected.short_description = "Safely delete selected bookings"

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('seat_object', 'passenger_name', 'trip', 'status', 'from_stop', 'to_stop')
    list_filter = ('status', 'trip__departure_datetime')
    search_fields = ('passenger_name', 'booking__booking_ref', 'seat_object__label')
    autocomplete_fields = ('booking', 'trip', 'seat_object')