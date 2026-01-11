from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import F
from datetime import timedelta, datetime
from django.utils.crypto import get_random_string
from django.utils.dateparse import parse_datetime
import uuid 
import json
from .models import *
from django.db.models import Max
from django.views.decorators.http import require_POST
from django.db.models import ProtectedError
from django.db import transaction
from django.contrib.auth import get_user_model
from .services import sync_route_prices
from .services import generate_smart_trips
from .forms import BlogPostForm, BlogBannerForm, AdminUserAddForm, TripSearchForm
from accounts.forms import AdminUserEditForm
from django.urls import reverse









User = get_user_model()


def dashboard(request):
    return render(request, 'admin_panel/dashboard/dashboard.html')



@csrf_exempt
def ships(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'add':
                name = data.get('name')
                code = data.get('code')
                total_capacity = data.get('total_capacity', 0)
                Ship.objects.create(name=name, code=code, total_capacity=total_capacity)
                return JsonResponse({'status': 'success', 'message': 'Ship added successfully!'})
            
            elif action == 'edit':
                ship_id = data.get('id')
                ship = get_object_or_404(Ship, id=ship_id)
                ship.name = data.get('name')
                ship.code = data.get('code')
                ship.total_capacity = data.get('total_capacity', 0)
                ship.save()
                return JsonResponse({'status': 'success', 'message': 'Ship updated successfully!'})
            
            elif action == 'delete':
                ship_id = data.get('id')
                ship = get_object_or_404(Ship, id=ship_id)
                ship.delete()
                return JsonResponse({'status': 'success', 'message': 'Ship deleted successfully!'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    ships = Ship.objects.all().order_by('-id')
    return render(request, 'admin_panel/ships/ship.html', {'ships': ships})


@csrf_exempt
def ship_details(request, ship_id):
    ship = get_object_or_404(Ship, id=ship_id)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')

            # --- SHIP ACTIONS ---
            if action == 'update_ship':
                ship.name = data.get('name')
                ship.code = data.get('code')
                ship.total_capacity = data.get('total_capacity', 0)
                ship.save()
                return JsonResponse({'status': 'success', 'message': 'Ship updated successfully'})

            # --- DECK ACTIONS ---
            elif action == 'add_deck':
                Deck.objects.create(
                    ship=ship,
                    name=data.get('name'),
                    level_order=data.get('level_order', 1),
                    grid_cols=data.get('grid_cols', 24),
                    total_rows=data.get('total_rows', 20)
                )
                return JsonResponse({'status': 'success', 'message': 'Deck added successfully'})

            elif action == 'edit_deck':
                deck = get_object_or_404(Deck, id=data.get('id'), ship=ship)
                deck.name = data.get('name')
                deck.level_order = data.get('level_order')
                deck.grid_cols = data.get('grid_cols')
                deck.total_rows = data.get('total_rows')
                deck.save()
                return JsonResponse({'status': 'success', 'message': 'Deck updated successfully'})

            elif action == 'delete_deck':
                deck = get_object_or_404(Deck, id=data.get('id'), ship=ship)
                deck.delete()
                return JsonResponse({'status': 'success', 'message': 'Deck deleted successfully'})

            return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    decks = ship.decks.all().order_by('level_order')
    return render(request, 'admin_panel/ships/ship_details.html', {
        'ship': ship,
        'decks': decks
    })
    
    
# @login_required
def manage_structures(request):
    """
    Manages non-bookable layout structures (Corridors, Walls, Labels).
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            icon_id = data.get('icon_id')
            icon_obj = SeatIcon.objects.filter(id=icon_id).first() if icon_id else None

            if action == 'add':
                SeatCategory.objects.create(
                    name=data.get('name'),
                    description=data.get('description', ''),
                    color_code=data.get('color_code', '#FFFFFF'),
                    icon=icon_obj,
                    is_bookable=False,  # Enforce Non-Bookable
                    capacity=0          # Structures usually have 0 capacity
                )
                return JsonResponse({'status': 'success', 'message': 'Structure added successfully!'})

            elif action == 'edit':
                category = get_object_or_404(SeatCategory, id=data.get('id'))
                category.name = data.get('name')
                category.description = data.get('description', '')
                category.color_code = data.get('color_code', '#FFFFFF')
                category.icon = icon_obj
                # Ensure we don't accidentally make it bookable via this view
                category.is_bookable = False 
                category.save()
                return JsonResponse({'status': 'success', 'message': 'Structure updated successfully!'})

            elif action == 'delete':
                category = get_object_or_404(SeatCategory, id=data.get('id'))
                category.delete()
                return JsonResponse({'status': 'success', 'message': 'Structure deleted successfully!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # GET Request: Only fetch non-bookable categories
    structures = SeatCategory.objects.filter(is_bookable=False).order_by('name')
    all_icons = SeatIcon.objects.all().order_by('name')
    
    context = {
        'structures': structures,
        'all_icons': all_icons,
    }
    return render(request, 'admin_panel/seat_layout/manage_structures.html', context)


# @login_required
def manage_bookable_categories(request):
    """
    Manages Bookable Seat Categories (Cabins, VIP Seats, Economy).
    Enforces is_bookable = True.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            # Get the Icon instance from the ID sent by the dropdown
            icon_id = data.get('icon_id')
            icon_obj = SeatIcon.objects.filter(id=icon_id).first() if icon_id else None

            if action == 'add':
                SeatCategory.objects.create(
                    name=data.get('name'),
                    description=data.get('description', ''),
                    color_code=data.get('color_code', '#000000'),
                    icon=icon_obj,
                    capacity=int(data.get('capacity', 1)),
                    is_bookable=True
                )
                return JsonResponse({'status': 'success', 'message': 'Category added successfully!'})

            elif action == 'edit':
                category = get_object_or_404(SeatCategory, id=data.get('id'))
                category.name = data.get('name')
                category.description = data.get('description', '')
                category.color_code = data.get('color_code', '#000000')
                category.icon = icon_obj
                category.capacity = int(data.get('capacity', 1))
                category.save()
                return JsonResponse({'status': 'success', 'message': 'Category updated successfully!'})

            elif action == 'delete':
                category = get_object_or_404(SeatCategory, id=data.get('id'))
                category.delete()
                return JsonResponse({'status': 'success', 'message': 'Category deleted successfully!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # GET: Only fetch bookable categories
    categories = SeatCategory.objects.filter(is_bookable=True).order_by('name')
    all_icons = SeatIcon.objects.all().order_by('name')
    
    context = {
        'categories': categories,
        'all_icons': all_icons,
    }
    return render(request, 'admin_panel/seat_layout/manage_bookable_categories.html', context)


def manage_seat_features(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")

            if action == "add":
                SeatFeature.objects.create(
                    name=data.get("name"),
                    description=data.get("description")
                )
                return JsonResponse({"status": "success", "message": "Feature added successfully!"})

            elif action == "edit":
                obj = SeatFeature.objects.get(id=data.get("id"))
                obj.name = data.get("name")
                obj.description = data.get("description")
                obj.save()
                return JsonResponse({"status": "success", "message": "Feature updated successfully!"})

            elif action == "delete":
                SeatFeature.objects.get(id=data.get("id")).delete()
                return JsonResponse({"status": "success", "message": "Feature deleted successfully!"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    # GET request
    context = {
        "features": SeatFeature.objects.all().order_by("-id"),
    }
    return render(request, "admin_panel/seat_layout/manage_seat_features.html", context)


def seat_icon_management(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")
            
            if action == "add":
                SeatIcon.objects.create(
                    name=data.get("name"),
                    iconify_code=data.get("iconify_code")
                )
                return JsonResponse({"status": "success", "message": "Icon added successfully!"})

            elif action == "edit":
                icon = SeatIcon.objects.get(id=data.get("id"))
                icon.name = data.get("name")
                icon.iconify_code = data.get("iconify_code")
                icon.save()
                return JsonResponse({"status": "success", "message": "Icon updated successfully!"})

            elif action == "delete":
                SeatIcon.objects.get(id=data.get("id")).delete()
                return JsonResponse({"status": "success", "message": "Icon deleted successfully!"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    icons = SeatIcon.objects.all().order_by('name')
    return render(request, 'admin_panel/seat_layout/seat_icons.html', {'icons': icons})
    


def seat_plan_editor(request, deck_id):
    deck = get_object_or_404(Deck, id=deck_id)
    
    # 1. Fetch Categories (The Brushes)
    categories = list(SeatCategory.objects.values(
        'id', 
        'name', 
        'color_code', 
        'is_bookable', 
        'icon__iconify_code'
    ))
    
    # 2. Fetch Features (The Tags like "River Side")
    features = list(SeatFeature.objects.values('id', 'name'))

    # 3. Fetch Existing Layout (If any)
    existing_objects = LayoutObject.objects.filter(deck=deck).select_related('category')
    layout_data = []
    for obj in existing_objects:
        layout_data.append({
            'row': obj.row_index,
            'col': obj.col_index,
            'row_span': obj.row_span,
            'col_span': obj.col_span,
            'category_id': obj.category.id,
            'label': obj.label,
            'features': list(obj.features.values_list('id', flat=True))
        })

    context = {
        'deck': deck,
        'categories_json': json.dumps(categories),
        'features_json': json.dumps(features),
        'layout_json': json.dumps(layout_data),
    }
    # Point this to your CUSTOM template location
    return render(request, 'admin_panel/seat_layout/seat_plan_editor.html', context)

# @csrf_exempt
# # @staff_member_required
# def save_seat_layout(request, deck_id):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         deck = get_object_or_404(Deck, id=deck_id)
        
#         # 1. Clear old layout for this deck (Simple approach)
#         LayoutObject.objects.filter(deck=deck).delete()
        
#         # 2. Bulk Create new objects
#         new_objects = []
#         feature_relations = [] # To handle ManyToMany
        
#         for item in data.get('layout', []):
#             obj = LayoutObject(
#                 deck=deck,
#                 row_index=item['row'],
#                 col_index=item['col'],
#                 row_span=item['row_span'],
#                 col_span=item['col_span'],
#                 category_id=item['category_id'],
#                 label=item.get('label', ''),
#                 seat_identifier=item.get('seat_id', None)
#             )
#             # We must save to get an ID before adding M2M
#             obj.save() 
            
#             # Add features
#             if 'feature_ids' in item:
#                 obj.features.set(item['feature_ids'])
        
#         return JsonResponse({'status': 'success', 'message': 'Layout saved successfully'})
#     return JsonResponse({'status': 'error'}, status=400)


# @staff_member_required
# @require_POST
@csrf_exempt
def update_deck_rows(request, deck_id):
    if request.method == 'POST':
        try:
            deck = Deck.objects.get(pk=deck_id)
            data = json.loads(request.body)
            action = data.get('action')
            
            # Rows
            if action == 'add': # Keep existing key for rows
                deck.total_rows += 1
            elif action == 'remove' and deck.total_rows > 1:
                deck.total_rows -= 1
            
            # Columns (New)
            elif action == 'add_col':
                deck.grid_cols += 1
            elif action == 'remove_col' and deck.grid_cols > 1:
                deck.grid_cols -= 1
                
            deck.save()
            return JsonResponse({
                'status': 'success', 
                'new_rows': deck.total_rows,
                'new_cols': deck.grid_cols
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'}, status=400)


@csrf_exempt
def save_seat_layout(request, deck_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    deck = get_object_or_404(Deck, id=deck_id)

    try:
        data = json.loads(request.body)
        layout_items = data.get('layout', [])
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)

    try:
        with transaction.atomic():
            # --- STEP 1: MAP EXISTING OBJECTS ---
            # We map (row, col) -> object so we can find them quickly.
            # This is crucial to PRESERVE IDs for existing bookings.
            existing_objects = {
                (obj.row_index, obj.col_index): obj 
                for obj in LayoutObject.objects.filter(deck=deck)
            }
            
            # Track which coordinates we have processed in this update
            processed_coords = set()

            # --- STEP 2: CREATE OR UPDATE ---
            for item in layout_items:
                row = int(item['row'])
                col = int(item['col'])
                coords = (row, col)
                processed_coords.add(coords)
                
                # Extract data from JSON
                category_id = item['category_id']
                label = item.get('label', '')
                row_span = int(item.get('row_span', 1))
                col_span = int(item.get('col_span', 1))
                feature_ids = item.get('feature_ids', [])

                # Check if we are updating an existing block or creating a new one
                obj = existing_objects.get(coords)
                
                if obj:
                    # UPDATE existing (Preserves Booking History)
                    obj.category_id = category_id
                    obj.label = label
                    obj.row_span = row_span
                    obj.col_span = col_span
                    # We save immediately to update basic fields
                    obj.save() 
                else:
                    # CREATE new
                    obj = LayoutObject.objects.create(
                        deck=deck,
                        row_index=row,
                        col_index=col,
                        category_id=category_id,
                        label=label,
                        row_span=row_span,
                        col_span=col_span
                    )
                
                # Update Many-to-Many Features (Tags)
                # .set() automatically handles add/remove of tags
                if feature_ids:
                    obj.features.set(feature_ids)
                else:
                    obj.features.clear()

            # --- STEP 3: DELETE REMOVED ITEMS ---
            # Any object that was in the DB but NOT in the new JSON payload must be deleted.
            for coords, obj in existing_objects.items():
                if coords not in processed_coords:
                    try:
                        obj.delete()
                    except ProtectedError:
                        # This happens if you try to delete a seat that has a Ticket.
                        # We fail safely and warn the admin.
                        raise Exception(f"Cannot delete '{obj.label}' at R{coords[0]}:C{coords[1]} because it has existing bookings.")

        return JsonResponse({'status': 'success', 'message': 'Layout saved successfully'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    

# @staff_member_required
def view_seat_plan(request, deck_id):
    deck = get_object_or_404(Deck, id=deck_id)
    
    # Fetch all objects. 'select_related' optimizes database access.
    layout_objects = LayoutObject.objects.filter(deck=deck).select_related('category')

    context = {
        'deck': deck,
        'layout_objects': layout_objects,
    }
    return render(request, 'admin_panel/seat_layout/view_seat_plan.html', context)



@csrf_exempt
def locations(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'get_districts':
                div_id = data.get('division_id')
                districts = District.objects.filter(division_id=div_id).values('id', 'name')
                return JsonResponse({'status': 'success', 'districts': list(districts)})

            elif action == 'add':
                # User selects a District to be a Location
                district_id = data.get('district_id')
                district = get_object_or_404(District, id=district_id)
                
                # Check if already exists
                if Location.objects.filter(district_id=district_id).exists():
                     return JsonResponse({'status': 'error', 'message': 'This district is already added as a location!'}, status=400)

                # Create Location
                # Name defaults to District Name, Code defaults to first 3 letters uppercased
                code = district.name[:3].upper()
                # Ensure unique code (simple logic)
                if Location.objects.filter(code=code).exists():
                    code = f"{code}-{district.id}"

                Location.objects.create(name=district.name, code=code, district=district)
                return JsonResponse({'status': 'success', 'message': 'Location added successfully!'})
            
            elif action == 'edit':
                loc_id = data.get('id')
                loc = get_object_or_404(Location, id=loc_id)
                loc.name = data.get('name')
                loc.code = data.get('code')
                loc.save()
                return JsonResponse({'status': 'success', 'message': 'Location updated successfully!'})
            
            elif action == 'delete':
                loc_id = data.get('id')
                loc = get_object_or_404(Location, id=loc_id)
                loc.delete()
                return JsonResponse({'status': 'success', 'message': 'Location deleted successfully!'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    locations = Location.objects.all().order_by('name')
    divisions = Division.objects.all().order_by('name')
    return render(request, 'admin_panel/routes/locations.html', {
        'locations': locations,
        'divisions': divisions
    })


@csrf_exempt
def counters(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'add':
                name = data.get('name')
                location_id = data.get('location_id')
                Counter.objects.create(name=name, location_id=location_id)
                return JsonResponse({'status': 'success', 'message': 'Counter added successfully!'})
            
            elif action == 'edit':
                c_id = data.get('id')
                counter = get_object_or_404(Counter, id=c_id)
                counter.name = data.get('name')
                counter.location_id = data.get('location_id')
                counter.save()
                return JsonResponse({'status': 'success', 'message': 'Counter updated successfully!'})
            
            elif action == 'delete':
                c_id = data.get('id')
                counter = get_object_or_404(Counter, id=c_id)
                counter.delete()
                return JsonResponse({'status': 'success', 'message': 'Counter deleted successfully!'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    counters = Counter.objects.select_related('location').all().order_by('location__name', 'name')
    locations = Location.objects.all().order_by('name')
    context = {
        'counters': counters,
        'locations': locations,
        'locations_json': json.dumps(list(locations.values('id', 'name')))
    }
    return render(request, 'admin_panel/routes/counters.html', context)


def routes(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            # --- ACTION: ADD ---
            if action == 'add':
                name = data.get('name')
                source_id = int(data.get('source_id'))
                dest_id = int(data.get('destination_id'))
                
                # Validation
                if source_id == dest_id:
                     return JsonResponse({'status': 'error', 'message': 'Source and Destination cannot be the same.'}, status=400)

                with transaction.atomic():
                    route = Route.objects.create(
                        name=name,
                        source_id=source_id,
                        destination_id=dest_id
                    )
                    # Create skeleton stops
                    RouteStop.objects.create(route=route, location_id=source_id, stop_order=0)
                    RouteStop.objects.create(route=route, location_id=dest_id, stop_order=1)
                
                return JsonResponse({'status': 'success', 'message': 'Route created successfully!'})
            
            # --- ACTION: EDIT ---
            elif action == 'edit':
                r_id = data.get('id')
                new_source_id = int(data.get('source_id'))
                new_dest_id = int(data.get('destination_id'))
                
                route = get_object_or_404(Route, id=r_id)
                
                # Validation
                if new_source_id == new_dest_id:
                     return JsonResponse({'status': 'error', 'message': 'Source and Destination cannot be the same.'}, status=400)

                old_source_id = route.source_id
                old_dest_id = route.destination_id # Keep for reference if needed, but we use logic now
                
                with transaction.atomic():
                    # 1. Update Route Metadata
                    route.name = data.get('name')
                    route.source_id = new_source_id
                    route.destination_id = new_dest_id 
                    route.save()

                    # 2. Sync Source Stop (Always order 0)
                    if old_source_id != new_source_id:
                        RouteStop.objects.filter(route=route, stop_order=0).update(location_id=new_source_id)

                    # 3. Sync Destination Stop (Always the last one)
                    if route.destination_id != new_dest_id: # Check if changed
                         # Get the very last stop logically
                        last_stop = RouteStop.objects.filter(route=route).order_by('-stop_order').first()
                        if last_stop:
                            last_stop.location_id = new_dest_id
                            last_stop.save()

                return JsonResponse({'status': 'success', 'message': 'Route updated successfully!'})
            
            # --- ACTION: DELETE ---
            elif action == 'delete':
                r_id = data.get('id')
                route = get_object_or_404(Route, id=r_id)
                route.delete()
                return JsonResponse({'status': 'success', 'message': 'Route deleted successfully!'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # GET Request
    routes = Route.objects.select_related('source', 'destination').all().order_by('name')
    locations = Location.objects.all().order_by('name')
    return render(request, 'admin_panel/routes/routes.html', {
        'routes': routes,
        'locations': locations
    })


def route_details(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            # --- ACTION: ADD STOP ---
            if action == 'add_stop':
                location_id = data.get('location_id')
                
                # 1. Validation
                if route.stops.filter(location_id=location_id).exists():
                    return JsonResponse({'status': 'error', 'message': 'Location already exists in this route!'}, status=400)

                with transaction.atomic():
                    # Get Destination Stop to determine insertion point
                    dest_stop = get_object_or_404(RouteStop, route=route, location=route.destination)
                    insert_index = dest_stop.stop_order
                    
                    # 2. SAFE SHIFT: Move existing stops down to make space.
                    # We fetch them ordered by '-stop_order' (DESCENDING)
                    # so we move the last one first, avoiding collisions.
                    stops_to_shift = route.stops.filter(
                        stop_order__gte=insert_index
                    ).order_by('-stop_order')

                    for stop in stops_to_shift:
                        stop.stop_order = stop.stop_order + 1
                        stop.save()
                    
                    # 3. Insert new stop in the now-empty slot
                    RouteStop.objects.create(
                        route=route, 
                        location_id=location_id, 
                        stop_order=insert_index,
                        time_offset_minutes=data.get('time_offset', 0)
                    )

                sync_route_prices(route)
                return JsonResponse({'status': 'success', 'message': 'Stop added successfully!'})

            # --- ACTION: DELETE STOP ---
            elif action == 'delete_stop':
                stop_id = data.get('id')
                stop = get_object_or_404(RouteStop, id=stop_id, route=route)
                
                # Validation: Don't delete Source/Dest
                if stop.location_id in [route.source.id, route.destination.id]:
                    return JsonResponse({'status': 'error', 'message': 'Cannot delete start or end points.'}, status=400)
                
                stop.delete() 
                # The signal automatically runs now. 
                # It detects the delete -> finds stops 3, 4, 5 -> updates them to 2, 3, 4.
                
                sync_route_prices(route)
                return JsonResponse({'status': 'success', 'message': 'Stop deleted successfully!'})

            # --- ACTION: REORDER STOPS ---
            elif action == 'reorder_stops':
                raw_ordered_ids = data.get('ordered_ids', [])
                ordered_ids = [int(x) for x in raw_ordered_ids if str(x).isdigit()]
                
                with transaction.atomic():
                    # 1. Integrity Check
                    current_stops = list(route.stops.values_list('id', flat=True))
                    if set(ordered_ids) != set(current_stops):
                         return JsonResponse({'status': 'error', 'message': 'Stop list mismatch. Please refresh.'}, status=400)

                    # 2. Logic Check: Ensure Source is first and Dest is last
                    # (Mapping IDs to verify logic)
                    id_to_loc = dict(route.stops.values_list('id', 'location_id'))
                    
                    if id_to_loc[ordered_ids[0]] != route.source.id:
                        return JsonResponse({'status': 'error', 'message': 'Source must remain the first stop.'}, status=400)
                    if id_to_loc[ordered_ids[-1]] != route.destination.id:
                         return JsonResponse({'status': 'error', 'message': 'Destination must remain the last stop.'}, status=400)

                    # 3. Two-Step Update (To avoid UniqueConstraint collisions on stop_order)
                    stops_to_update = []
                    
                    # Step A: Temporarily move to high numbers
                    for index, stop_id in enumerate(ordered_ids):
                         stop = RouteStop.objects.get(id=stop_id)
                         stop.stop_order = 10000 + index
                         stops_to_update.append(stop)
                    RouteStop.objects.bulk_update(stops_to_update, ['stop_order'])
                    
                    # Step B: Set to correct 0-indexed sequence
                    for index, stop in enumerate(stops_to_update):
                        stop.stop_order = index
                    RouteStop.objects.bulk_update(stops_to_update, ['stop_order'])
                    
                sync_route_prices(route)
                        
                return JsonResponse({'status': 'success', 'message': 'Sequence updated!'})
            
            elif action == 'save_prices':
                updates = data.get('prices', [])
                for item in updates:
                    RouteSegmentPricing.objects.filter(id=item.get('id'), route=route).update(price=item.get('price'))
                return JsonResponse({'status': 'success', 'message': 'Prices saved!'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # Query Optimization: Fetch District info to avoid N+1 queries in the template
    # Query Optimization
    stops = route.stops.select_related('location', 'location__district').order_by('stop_order')
    locations = Location.objects.all().order_by('name')
    
    # --- PRICING LOGIC STARTS HERE ---
    segment_prices = RouteSegmentPricing.objects.filter(route=route)\
        .select_related('from_stop__location', 'to_stop__location', 'seat_category')\
        .order_by('from_stop__stop_order', 'to_stop__stop_order', 'seat_category__name')

    # 1. Check for unset prices (triggers the flash)
    prices_exist = segment_prices.exists()
    has_unset_prices = segment_prices.filter(
        price__lte=0, 
        seat_category__is_bookable=True
    ).exists()

    # If no prices exist but we have stops, run sync once to generate them
    if not prices_exist and stops.count() >= 2:
        sync_route_prices(route)
        has_unset_prices = True 
        # Refetch to show in modal immediately
        segment_prices = RouteSegmentPricing.objects.filter(route=route)\
            .select_related('from_stop__location', 'to_stop__location', 'seat_category')

    # 2. Organize data for the Modal
    price_matrix = {}
    for obj in segment_prices:
        label = f"{obj.from_stop.location.name} → {obj.to_stop.location.name}"
        
        if label not in price_matrix:
            price_matrix[label] = {
                'prices': [],
                'needs_attention': False
            }
        
        price_matrix[label]['prices'].append(obj)
        
        # If any bookable price in this segment is 0, mark the whole segment
        if obj.seat_category.is_bookable and obj.price <= 0:
            price_matrix[label]['needs_attention'] = True

    return render(request, 'admin_panel/routes/route_details.html', {
        'route': route,
        'stops': stops,
        'locations': locations,
        'price_matrix': price_matrix,       # <--- New context variable
        'has_unset_prices': has_unset_prices # <--- New context variable
    })
    
    
    
def trip_schedule_list(request):
    # Fetching all schedules with related ship and route data for performance
    schedules = TripSchedule.objects.select_related(
        'ship', 
        'route__source', 
        'route__destination'
    ).all().order_by('-id')
    
    context = {
        'schedules': schedules
    }
    return render(request, 'admin_panel/trips/trip_schedule_list.html', context)

    
    
def save_trip_schedule(request):
    if request.method == "POST":
        ship_id = request.POST.get('ship_id')
        route_id = request.POST.get('route_id')
        departure_time_str = request.POST.get('departure_time')
        arrival_time_str = request.POST.get('arrival_time') # Might be empty now
        date_list_str = request.POST.get('date_range')
        is_active = request.POST.get('is_active') == 'on'

        try:
            dep_time_obj = datetime.strptime(departure_time_str, "%I:%M %p").time()
            
            # 3. PINPOINT CHANGE: HANDLE OPTIONAL ARRIVAL TIME
            if arrival_time_str:
                arr_time_obj = datetime.strptime(arrival_time_str, "%I:%M %p").time()
            else:
                # Default to departure time if not provided
                arr_time_obj = dep_time_obj 

            schedule = TripSchedule.objects.create(
                ship_id=ship_id,
                route_id=route_id,
                departure_time=dep_time_obj,
                arrival_time=arr_time_obj,
                is_active=is_active
            )

            selected_dates = [d.strip() for d in date_list_str.split(',')]
            for date_str in selected_dates:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                departure_dt = datetime.combine(date_obj, dep_time_obj)
                
                arrival_dt = datetime.combine(date_obj, arr_time_obj)
                # Only add a day if arrival time exists and is earlier than departure
                if arrival_time_str and arr_time_obj < dep_time_obj:
                    arrival_dt += timedelta(days=1)

                Trip.objects.create(
                    schedule=schedule,
                    ship_id=ship_id,
                    route_id=route_id,
                    departure_datetime=departure_dt,
                    arrival_datetime=arrival_dt,
                    is_published=True
                )

            return JsonResponse({'success': True, 'message': 'Schedule and trips created successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    # Data for the form
    ships = Ship.objects.all()
    routes = Route.objects.all()
    
    # List for the Day-Picker loop in HTML
    days_mapping = [
        ('monday', 'Mon'), ('tuesday', 'Tue'), ('wednesday', 'Wed'),
        ('thursday', 'Thu'), ('friday', 'Fri'), ('saturday', 'Sat'), ('sunday', 'Sun')
    ]
    
    context = {
        'ships': ships,
        'routes': routes,
        'days_mapping': days_mapping
    }
    
    return render(request, 'admin_panel/trips/create_trip_schedule.html', context)



def update_trip_schedule(request, schedule_id):
    schedule = get_object_or_404(TripSchedule, id=schedule_id)
    
    if request.method == "POST":
        ship_id = request.POST.get('ship_id')
        route_id = request.POST.get('route_id')
        departure_time_str = request.POST.get('departure_time')
        date_list_str = request.POST.get('date_range')
        is_active = request.POST.get('is_active') == 'on'

        try:
            dep_time_obj = datetime.strptime(departure_time_str, "%I:%M %p").time()
            
            schedule.ship_id = ship_id
            schedule.route_id = route_id
            schedule.departure_time = dep_time_obj
            schedule.is_active = is_active
            schedule.save()

            # 1. FIX: Use 'generated_trips' instead of 'trips'
            selected_dates = [d.strip() for d in date_list_str.split(',')]
            schedule.generated_trips.all().delete() 

            for date_str in selected_dates:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                departure_dt = datetime.combine(date_obj, dep_time_obj)
                
                Trip.objects.create(
                    schedule=schedule,
                    ship_id=ship_id,
                    route_id=route_id,
                    departure_datetime=departure_dt,
                    arrival_datetime=departure_dt,
                    is_published=True
                )

            return JsonResponse({'success': True, 'message': 'Schedule and trips updated successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    # 2. FIX: Use 'generated_trips' here as well
    existing_dates = schedule.generated_trips.values_list('departure_datetime__date', flat=True)
    formatted_dates = ", ".join([d.strftime('%Y-%m-%d') for d in existing_dates])

    return render(request, 'admin_panel/trips/update_trip_schedule.html', {
        'schedule': schedule,
        'ships': Ship.objects.all(),
        'routes': Route.objects.all(),
        'formatted_dates': formatted_dates,
    })


@require_POST
def delete_trip_schedule(request, pk):
    try:
        schedule = get_object_or_404(TripSchedule, pk=pk)
        schedule.delete()
        return JsonResponse({'status': 'success', 'message': 'Schedule deleted successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        

def trip_list(request):
    # Optimizing to get Ship and Route names in one go
    trips = Trip.objects.select_related(
        'ship', 
        'route__source', 
        'route__destination',
        'schedule'
    ).all().order_by('-departure_datetime')
    
    return render(request, 'admin_panel/trips/trip_list.html', {'trips': trips})
    

def individual_trip_management(request):
    # Use select_related here too for performance
    trips = Trip.objects.select_related(
        'ship', 
        'route__source', 
        'route__destination'
    ).all().order_by('-departure_datetime')

    date_range = request.GET.get('date_range')

    if date_range:
        # Splits "2026-01-07, 2026-01-08" into ['2026-01-07', '2026-01-08']
        selected_dates = [d.strip() for d in date_range.split(',') if d.strip()]
        # Backend filter on the date portion of the datetime field
        trips = trips.filter(departure_datetime__date__in=selected_dates)

    context = {
        'trips': trips,
        'date_range_value': date_range
    }
    
    # FIXED: Changed from 'your_app/trip_list.html' to the correct path below
    return render(request, 'admin_panel/trips/trip_list.html', context)


def update_trip(request, trip_id):
    # Fetch trip with related data for optimization
    trip = get_object_or_404(Trip.objects.select_related('ship', 'route'), id=trip_id)
    
    # Get all stops for this route to calculate itinerary
    route_stops = RouteStop.objects.filter(route=trip.route).order_by('stop_order')
    
    # Base segments for pricing overrides
    base_segments = RouteSegmentPricing.objects.filter(route=trip.route).select_related(
        'seat_category', 'from_stop__location', 'to_stop__location'
    )

    # Check for existing bookings
    has_bookings = trip.tickets.filter(status__in=['BOOKED', 'LOCKED']).exists()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                new_date_str = request.POST.get('departure_datetime')
                new_multiplier = request.POST.get('price_multiplier', 1.0)
                # is_published = request.POST.get('is_published') == 'on'

                # --- VALIDATION: Date Change ---
                if new_date_str:
                    new_date = parse_datetime(new_date_str)
                    if trip.departure_datetime.strftime('%Y-%m-%d %H:%M') != new_date.strftime('%Y-%m-%d %H:%M'):
                        if has_bookings:
                            return JsonResponse({
                                'status': 'error',
                                'origin': 'Booking Validator',
                                'message': 'Cannot change date: Tickets have already been issued for this trip.'
                            }, status=400)
                        trip.departure_datetime = new_date

                # --- UPDATE CORE FIELDS ---
                trip.price_multiplier = new_multiplier
                trip.is_published = True
                trip.save()
                
                # --- UPDATE ITINERARY OFFSETS ---
                for stop in route_stops:
                    offset_val = request.POST.get(f'offset_{stop.id}')
                    if offset_val is not None:
                        # We enforce 0 for the first stop regardless of input
                        if stop.stop_order == 0:
                            stop.time_offset_minutes = 0
                        else:
                            stop.time_offset_minutes = int(offset_val)
                        stop.save()

                # --- UPDATE PRICING ---
                for segment in base_segments:
                    price_val = request.POST.get(f'price_override_{segment.id}')
                    if price_val and price_val.strip() != "":
                        TripPricing.objects.update_or_create(
                            trip=trip, seat_category=segment.seat_category,
                            from_stop=segment.from_stop, to_stop=segment.to_stop,
                            defaults={'price': price_val}
                        )
                    else:
                        TripPricing.objects.filter(
                            trip=trip, seat_category=segment.seat_category,
                            from_stop=segment.from_stop, to_stop=segment.to_stop
                        ).delete()

                return JsonResponse({
                    'status': 'success',
                    'message': 'Trip updated successfully.'
                })

        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'origin': 'System Server',
                'message': str(e)
            }, status=500)

    # --- PREPARE DATA FOR DISPLAY ---
    
    # 1. Calculate Itinerary (Departure + Offset)
    itinerary = []
    for stop in route_stops:
        arrival_time = trip.departure_datetime + timedelta(minutes=stop.time_offset_minutes)
        itinerary.append({
            'stop_id': stop.id,  # ADD THIS LINE
            'location': stop.location.name,
            'time': arrival_time,
            'offset': stop.time_offset_minutes,
            'is_start': stop.stop_order == 0,
            'is_end': stop == route_stops.last()
        })

    # 2. Map Overrides
    current_overrides = TripPricing.objects.filter(trip=trip)
    override_map = {(p.seat_category_id, p.from_stop_id, p.to_stop_id): p.price for p in current_overrides}

    for segment in base_segments:
        key = (segment.seat_category_id, segment.from_stop_id, segment.to_stop_id)
        segment.existing_override = override_map.get(key)
        segment.current_total_price = segment.existing_override if segment.existing_override else (segment.price * trip.price_multiplier)
        segment.is_fixed = bool(segment.existing_override)

    return render(request, 'admin_panel/trips/update_trip.html', {
        'trip': trip,
        'base_segments': base_segments,
        'has_bookings': has_bookings,
        'itinerary': itinerary
    })
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    














def site_identity_view(request):
    identity = SiteIdentity.objects.first()
    
    if request.method == 'POST':
        # Upload new logo
        if request.FILES.get('logo'):
            if not identity:
                identity = SiteIdentity.objects.create()
            
            identity.logo = request.FILES.get('logo')
            identity.save()
            messages.success(request, "Logo Updated Successfully!")
        
        return redirect('site_identity')

    return render(request, 'admin_panel/home/identity.html', {'identity': identity})



def banner(request):
    if request.method == 'POST':
        try:
            # We get data from request.POST because we are using FormData for images
            action = request.POST.get('action')

            if action == 'add':
                HomeBanner.objects.create(
                    title=request.POST.get('title'),
                    description=request.POST.get('description'),
                    # logo line removed here
                    background_image=request.FILES.get('background_image'),
                    is_active=request.POST.get('is_active') == 'on'
                )
                return JsonResponse({'status': 'success', 'message': 'Banner added successfully!'})

            elif action == 'edit':
                banner_id = request.POST.get('id')
                banner = HomeBanner.objects.get(id=banner_id)
                
                banner.title = request.POST.get('title')
                banner.description = request.POST.get('description')
                
                # Logo update block removed here
                
                # Only update background image if a new one is uploaded
                if request.FILES.get('background_image'):
                    banner.background_image = request.FILES.get('background_image')
                
                banner.is_active = request.POST.get('is_active') == 'on'
                banner.save()
                return JsonResponse({'status': 'success', 'message': 'Banner updated successfully!'})

            elif action == 'delete':
                banner_id = request.POST.get('id')
                HomeBanner.objects.get(id=banner_id).delete()
                return JsonResponse({'status': 'success', 'message': 'Banner deleted successfully!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    # GET Request: Render the list
    banners = HomeBanner.objects.all().order_by('-updated_at')
    return render(request, 'admin_panel/home/banner.html', {'banners': banners})





from .forms import CompanyOverviewForm
def overview(request):
    """
    Manages the 'Company Overview' section on the Home Page.
    Acts as a singleton editor (always edits the first object).
    """
    
    # 1. Try to get the existing record (we only want one 'About Us' section)
    obj = CompanyOverview.objects.first()

    if request.method == 'POST':
        # 2. If data is sent, bind it to the form (and the object if it exists)
        form = CompanyOverviewForm(request.POST, request.FILES, instance=obj)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Home Page Overview updated successfully!")
            return redirect('overview') # Reload the page to show changes
        else:
            messages.error(request, "Please correct the errors below.")
            
    else:
        # 3. If GET request, show the form with existing data (if any)
        form = CompanyOverviewForm(instance=obj)

    # 4. Prepare context for the template
    context = {
        'form': form,
        # Pass the image separately so we can show a preview in the HTML
        'existing_image': obj.image if obj else None 
    }
    
    return render(request, 'admin_panel/home/overview.html', context)



from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import ContactBanner # Import the model created in Part 1

def contact_banner_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            # --- ADD BANNER ---
            if action == 'add':
                title = request.POST.get('title')
                image = request.FILES.get('background_image')
                # Checkbox sends 'on' if checked, None if not.
                is_active = request.POST.get('is_active') == 'on' 

                if not title or not image:
                    return JsonResponse({'status': 'error', 'message': 'Title and Image are required.'})

                # Ensure only one banner is active if this one is set to active
                if is_active:
                    ContactBanner.objects.update(is_active=False)

                ContactBanner.objects.create(
                    title=title,
                    background_image=image,
                    is_active=is_active
                )
                return JsonResponse({'status': 'success', 'message': 'Banner added successfully!'})

            # --- EDIT BANNER ---
            elif action == 'edit':
                banner_id = request.POST.get('id')
                banner = get_object_or_404(ContactBanner, id=banner_id)
                
                banner.title = request.POST.get('title')
                
                # Update image only if a new one is uploaded
                if 'background_image' in request.FILES:
                    banner.background_image = request.FILES['background_image']
                
                is_active = request.POST.get('is_active') == 'on'
                
                # Logic to handle active state
                if is_active:
                    ContactBanner.objects.exclude(id=banner.id).update(is_active=False)
                
                banner.is_active = is_active
                banner.save()
                
                return JsonResponse({'status': 'success', 'message': 'Banner updated successfully!'})

            # --- DELETE BANNER ---
            elif action == 'delete':
                banner_id = request.POST.get('id')
                banner = get_object_or_404(ContactBanner, id=banner_id)
                banner.delete()
                return JsonResponse({'status': 'success', 'message': 'Banner deleted successfully!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    # --- GET REQUEST (Render Page) ---
    banners = ContactBanner.objects.all().order_by('-id')
    context = {
        'banners': banners
    }
    return render(request, 'admin_panel/contactus/banner.html', context)



def contact_messages_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        try:
            # --- DELETE MESSAGE ---
            if action == 'delete':
                msg_id = request.POST.get('id')
                message = get_object_or_404(ContactMessage, id=msg_id)
                message.delete()
                return JsonResponse({'status': 'success', 'message': 'Message deleted successfully!'})
            
            # --- MARK AS READ (Optional, triggered via JS when viewing) ---
            elif action == 'mark_read':
                msg_id = request.POST.get('id')
                message = get_object_or_404(ContactMessage, id=msg_id)
                message.is_read = True
                message.save()
                return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    # --- GET REQUEST (Render List) ---
    # Show newest messages first
    messages = ContactMessage.objects.all().order_by('-created_at')
    
    context = {
        'messages': messages
    }
    return render(request, 'admin_panel/contactus/messages.html', context)

def contact_info_cards_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        try:
            # --- ADD CARD ---
            if action == 'add':
                title = request.POST.get('title')
                description = request.POST.get('description')
                contact_info = request.POST.get('contact_info')
                icon = request.FILES.get('icon')
                is_active = request.POST.get('is_active') == 'on'

                ContactInfoCard.objects.create(
                    title=title, description=description, 
                    contact_info=contact_info, icon=icon, is_active=is_active
                )
                return JsonResponse({'status': 'success', 'message': 'Info Card added successfully!'})

            # --- EDIT CARD ---
            elif action == 'edit':
                card_id = request.POST.get('id')
                card = get_object_or_404(ContactInfoCard, id=card_id)

                card.title = request.POST.get('title')
                card.description = request.POST.get('description')
                card.contact_info = request.POST.get('contact_info')
                card.is_active = request.POST.get('is_active') == 'on'
                
                if request.FILES.get('icon'):
                    card.icon = request.FILES.get('icon')

                card.save()
                return JsonResponse({'status': 'success', 'message': 'Info Card updated successfully!'})

            # --- DELETE CARD ---
            elif action == 'delete':
                card_id = request.POST.get('id')
                ContactInfoCard.objects.filter(id=card_id).delete()
                return JsonResponse({'status': 'success', 'message': 'Info Card deleted successfully!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    # --- GET REQUEST ---
    cards = ContactInfoCard.objects.all()
    return render(request, 'admin_panel/contactus/info_cards.html', {'cards': cards})

def contact_map_view(request):
    # Fetch the existing map object (if any)
    map_obj = ContactMap.objects.first()

    if request.method == 'POST':
        embed_code = request.POST.get('map_embed_code')
        is_active = request.POST.get('is_active') == 'on'

        if map_obj:
            # Update existing
            map_obj.map_embed_code = embed_code
            map_obj.is_active = is_active
            map_obj.save()
            messages.success(request, "Map updated successfully!")
        else:
            # Create new
            ContactMap.objects.create(map_embed_code=embed_code, is_active=is_active)
            messages.success(request, "Map created successfully!")
        
        return redirect('contact_map')

    return render(request, 'admin_panel/contactus/map.html', {'map_obj': map_obj})


def contact_faq_view(request):
    # Fetch Settings (Create if doesn't exist to avoid errors)
    section_settings = ContactFAQSection.objects.first()
    if not section_settings:
        section_settings = ContactFAQSection.objects.create(title="Have questions?")

    if request.method == 'POST':
        action = request.POST.get('action')

        try:
            # --- 1. UPDATE SECTION SETTINGS ---
            if action == 'update_settings':
                section_settings.title = request.POST.get('title')
                section_settings.is_active = request.POST.get('is_active') == 'on'
                
                if request.FILES.get('side_image'):
                    section_settings.side_image = request.FILES.get('side_image')
                
                section_settings.save()
                return JsonResponse({'status': 'success', 'message': 'Settings updated!'})

            # --- 2. ADD FAQ ITEM ---
            elif action == 'add_item':
                ContactFAQItem.objects.create(
                    question=request.POST.get('question'),
                    answer=request.POST.get('answer'),
                    order=request.POST.get('order', 0),
                    is_active=request.POST.get('is_active') == 'on'
                )
                return JsonResponse({'status': 'success', 'message': 'FAQ added!'})

            # --- 3. EDIT FAQ ITEM ---
            elif action == 'edit_item':
                item = get_object_or_404(ContactFAQItem, id=request.POST.get('id'))
                item.question = request.POST.get('question')
                item.answer = request.POST.get('answer')
                item.order = request.POST.get('order', 0)
                item.is_active = request.POST.get('is_active') == 'on'
                item.save()
                return JsonResponse({'status': 'success', 'message': 'FAQ updated!'})

            # --- 4. DELETE FAQ ITEM ---
            elif action == 'delete_item':
                ContactFAQItem.objects.filter(id=request.POST.get('id')).delete()
                return JsonResponse({'status': 'success', 'message': 'FAQ deleted!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    # GET Request
    faq_items = ContactFAQItem.objects.all().order_by('order')
    return render(request, 'admin_panel/contactus/faq.html', {
        'settings': section_settings,
        'faq_items': faq_items
    })
    
    
def about_banner_view(request):
    banner = AboutBanner.objects.first()
    
    if request.method == 'POST':
        title = request.POST.get('title')
        is_active = request.POST.get('is_active') == 'on'
        
        if banner:
            banner.title = title
            banner.is_active = is_active
            if request.FILES.get('background_image'):
                banner.background_image = request.FILES.get('background_image')
            banner.save()
            messages.success(request, "About Banner Updated!")
        else:
            img = request.FILES.get('background_image')
            AboutBanner.objects.create(title=title, background_image=img, is_active=is_active)
            messages.success(request, "About Banner Created!")
        return redirect('about_banner')
        
    return render(request, 'admin_panel/about/banner.html', {'banner': banner})

from .forms import AboutStoryForm
def about_story_view(request):
    story = AboutStory.objects.first()

    if request.method == 'POST':
        form = AboutStoryForm(request.POST, request.FILES, instance=story)
        if form.is_valid():
            form.save()
            messages.success(request, "About Us content updated!")
            return redirect('about_story')
    else:
        form = AboutStoryForm(instance=story)

    return render(request, 'admin_panel/about/story.html', {'form': form, 'story': story})






# --- 1. MAIN GALLERY ADMIN VIEW ---
def gallery_main_view(request):
    settings = GallerySection.objects.first()
    if not settings:
        settings = GallerySection.objects.create()

    if request.method == 'POST':
        action = request.POST.get('action')

        # Update Settings
        if action == 'update_settings':
            settings.subtitle = request.POST.get('subtitle')
            settings.title = request.POST.get('title')
            settings.description = request.POST.get('description')
            settings.save()
            messages.success(request, "Settings Updated")

        # Add Image
        elif action == 'add_image':
            if request.FILES.get('image'):
                GalleryImage.objects.create(
                    image=request.FILES.get('image'),
                    order=request.POST.get('order', 0)
                )
                messages.success(request, "Image Added")

        # Delete Image
        elif action == 'delete_image':
            GalleryImage.objects.filter(id=request.POST.get('id')).delete()
            messages.success(request, "Image Deleted")
            
        return redirect('gallery_main')

    images = GalleryImage.objects.all()
    return render(request, 'admin_panel/gallery/main.html', {'settings': settings, 'images': images})


# --- 2. SEASONAL TOURS ADMIN VIEW ---
def gallery_seasonal_view(request):
    settings = SeasonalSection.objects.first()
    if not settings:
        settings = SeasonalSection.objects.create()

    if request.method == 'POST':
        action = request.POST.get('action')

        # Update Settings
        if action == 'update_settings':
            settings.subtitle = request.POST.get('subtitle')
            settings.title = request.POST.get('title')
            settings.save()
            messages.success(request, "Settings Updated")

        # Add Tour
        elif action == 'add_tour':
            SeasonalTour.objects.create(
                title=request.POST.get('title'),
                link=request.POST.get('link'),
                image=request.FILES.get('image'),
                order=request.POST.get('order', 0)
            )
            messages.success(request, "Tour Added")

        # --- NEW: EDIT TOUR LOGIC ---
        elif action == 'edit_tour':
            tour_id = request.POST.get('id')
            tour = SeasonalTour.objects.get(id=tour_id)
            
            tour.title = request.POST.get('title')
            tour.link = request.POST.get('link')
            tour.order = request.POST.get('order')
            
            # Only update image if a new one is selected
            if request.FILES.get('image'):
                tour.image = request.FILES.get('image')
            
            tour.save()
            messages.success(request, "Tour Updated Successfully")
        
        
        # Delete Tour
        elif action == 'delete_tour':
            SeasonalTour.objects.filter(id=request.POST.get('id')).delete()
            messages.success(request, "Tour Deleted")

        return redirect('gallery_seasonal')

    tours = SeasonalTour.objects.all()
    return render(request, 'admin_panel/gallery/seasonal.html', {'settings': settings, 'tours': tours})



def blog_banner_update(request):
    # Try to get the first existing banner, or create one if none exists
    banner = BlogBanner.objects.first()
    
    if request.method == 'POST':
        form = BlogBannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            form.save()
            messages.success(request, "Blog Banner Updated Successfully!")
            return redirect('admin_blog_banner')
    else:
        # If banner doesn't exist yet, we pass None so it creates a new one
        form = BlogBannerForm(instance=banner)

    return render(request, 'admin_panel/blog/banner_form.html', {
        'form': form,
        'current_banner': banner
    })





#team
from .forms import TeamMemberForm
def manage_team(request):
    """
    Allows the admin to:
    1. See a list of all members.
    2. Add a new member (Name, Designation, Description, Image).
    """
    # Get all current members to show in the table
    members = TeamMember.objects.all().order_by('-created_at')
    
    # Handle the "Add New Member" Form
    if request.method == 'POST':
        form = TeamMemberForm(request.POST, request.FILES)
        if form.is_valid():
            form.save() # This saves Name, Designation, Description, and Image
            messages.success(request, "New Team Member Added Successfully!")
            return redirect('manage_team')
        else:
            messages.error(request, "Error adding member. Please check the form.")
    else:
        form = TeamMemberForm()

    context = {
        'members': members,
        'form': form
    }
    return render(request, 'admin_panel/team/manage_team.html', context)

# ==========================================
# 3. DELETE VIEW (Admin Action)
# ==========================================
def delete_team_member(request, pk):
    """
    Deletes a specific team member by their ID (pk).
    """
    member = get_object_or_404(TeamMember, pk=pk)
    member.delete()
    messages.success(request, "Team member deleted.")
    return redirect('manage_team')







# 1. LIST VIEW
def blog_list(request):
    blogs = BlogPost.objects.all().order_by('-date')
    return render(request, 'admin_panel/blog/list.html', {'blogs': blogs})

# 2. ADD VIEW
def blog_add(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Blog Post Added Successfully!")
            return redirect('admin_blog_list')
    else:
        form = BlogPostForm()
    
    return render(request, 'admin_panel/blog/form.html', {'form': form, 'title': 'Add New Blog'})

# 3. EDIT VIEW
def blog_edit(request, slug):
    blog = get_object_or_404(BlogPost, slug=slug)
    
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=blog)
        if form.is_valid():
            form.save()
            messages.success(request, "Blog Updated Successfully!")
            return redirect('admin_blog_list')
    else:
        form = BlogPostForm(instance=blog)

    return render(request, 'admin_panel/blog/form.html', {'form': form, 'title': 'Edit Blog', 'blog': blog})

# 4. DELETE VIEW
def blog_delete(request, slug):
    blog = get_object_or_404(BlogPost, slug=slug)
    blog.delete()
    messages.success(request, "Blog Deleted Successfully!")
    return redirect('admin_blog_list')

from django.db.models import Count
def admin_comment_list(request):
    posts = BlogPost.objects.annotate(
        total_comments=Count('comments')
    ).filter(total_comments__gt=0).prefetch_related('comments').order_by('-date')
    
    context = {
        'posts': posts, # We are sending POSTS now
        'title': 'Blog Comments'
    }
    return render(request, 'admin_panel/blog/comments.html', context)


def admin_comment_delete(request, id):
    comment = get_object_or_404(BlogComment, id=id)
    comment.delete()
    messages.success(request, "Comment deleted successfully!")
    # Redirect back to the comments list
    return redirect('admin_comment_list')


def get_search_locations(request):
    # Fetch all locations, selecting only necessary fields for speed
    locations = list(Location.objects.values('id', 'name', 'code'))
    return JsonResponse({'status': 'success', 'data': locations})


def admin_user_list(request):
    # Fetch all users, newest first
    users = User.objects.all().order_by('-created_at')
    
    context = {
        'users': users,
        'title': 'User Management'
    }
    return render(request, 'admin_panel/users/user_list.html', context)


def user_add(request):
    
    # 3. SAFETY CHECK: Even if you are logged in, we make sure you have the 'user_type' attribute
    # This prevents the crash if something goes wrong with the user object
    if not hasattr(request.user, 'user_type'):
         messages.error(request, "Error: Your account information is incomplete.")
         return redirect('home')

    # 4. ADMIN CHECK: specific logic to ensure only admins enter
    if not request.user.is_superuser and request.user.user_type != 0:
         messages.error(request, "Access denied. Admins only.")
         return redirect('home')

    if request.method == 'POST':
        form = AdminUserAddForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User created successfully!")
            return redirect('admin_user_list') 
    else:
        form = AdminUserAddForm()

    return render(request, 'admin_panel/users/add.html', {'form': form})


def admin_user_edit(request, id):
    user_obj = get_object_or_404(User, id=id)
    
    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"User '{user_obj.email}' updated successfully.")
            return redirect('admin_user_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill the form with existing user data
        form = AdminUserEditForm(instance=user_obj)

    context = {
        'form': form,
        'user_obj': user_obj, # We pass this so we can show the name in the title
    }
    return render(request, 'admin_panel/users/edit.html', context)


def admin_user_delete(request, id):
    user_to_delete = get_object_or_404(User, id=id)
    
    # SAFETY: Prevent deleting yourself (the currently logged-in admin)
    if user_to_delete == request.user:
        messages.error(request, "You cannot delete your own admin account!")
        return redirect('admin_user_list')

    # Delete the user
    user_to_delete.delete()
    messages.success(request, "User deleted successfully.")
    return redirect('admin_user_list')



def tcktbook(request):
    search_results = []
    form = TripSearchForm(request.GET or None) # Bind data if it exists in URL
    
    # These will be useful for the template to know what we searched for
    searched_from = None
    searched_to = None

    if form.is_valid():
        source = form.cleaned_data['from_location']
        destination = form.cleaned_data['to_location']
        date = form.cleaned_data['journey_date']
        
        searched_from = source
        searched_to = destination

        # --- LOGIC START ---
        
        # 1. Find Routes that have BOTH the source and destination
        # We find RouteStops matching source, and RouteStops matching destination
        # Then we check which Routes appear in BOTH lists.
        
        routes_with_source = RouteStop.objects.filter(location=source).values_list('route_id', 'stop_order')
        routes_with_dest = RouteStop.objects.filter(location=destination).values_list('route_id', 'stop_order')
        
        # Convert to dictionaries for easier lookup: {route_id: stop_order}
        source_map = {r_id: order for r_id, order in routes_with_source}
        dest_map = {r_id: order for r_id, order in routes_with_dest}
        
        valid_route_ids = []
        
        # 2. Compare Orders: Source must be BEFORE Destination
        for route_id, source_order in source_map.items():
            if route_id in dest_map:
                dest_order = dest_map[route_id]
                if source_order < dest_order:
                    valid_route_ids.append(route_id)
        
        # 3. Find TRIPS for these valid routes on the specific date
        if valid_route_ids:
            search_results = Trip.objects.filter(
                route_id__in=valid_route_ids,
                departure_datetime__date=date
            ).select_related('ship', 'route')
            
        # --- LOGIC END ---

    context = {
        'form': form,
        'trips': search_results,
        'searched_from': searched_from,
        'searched_to': searched_to,
    }
    return render(request, 'admin_panel/book/book.html', context)




def select_seats(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    
    # 1. Get Route Segment Info from GET params
    from_loc_id = request.GET.get('from_loc')
    to_loc_id = request.GET.get('to_loc')
    
    if not from_loc_id or not to_loc_id:
        messages.error(request, "Please select source and destination first.")
        return redirect('admin_search_trips') # Replace with your search url name

    # 2. Get the RouteStop objects to determine order (Stop 1 -> Stop 5)
    try:
        from_stop = RouteStop.objects.get(route=trip.route, location_id=from_loc_id)
        to_stop = RouteStop.objects.get(route=trip.route, location_id=to_loc_id)
    except RouteStop.DoesNotExist:
        messages.error(request, "Invalid route stops.")
        return redirect('admin_home')

    # 3. Calculate Pricing for each Category (Map ID -> Price)
    # We'll create a dictionary to pass to JS: { 'AC Cabin': 1500, 'Deck': 300 }
    category_prices = {}
    
    # We fetch all unique categories used in this ship's layout
    # This avoids calculating prices for categories that don't exist on this ship
    layout_categories = LayoutObject.objects.filter(deck__ship=trip.ship).values_list('category', flat=True).distinct()
    
    for cat_id in layout_categories:
        # We need the actual category object to pass to get_price if your logic expects objects
        # Or if get_price expects ID, pass ID. Assuming it takes the object:
        from .models import SeatCategory
        category = SeatCategory.objects.get(id=cat_id)
        price = trip.get_price(category, from_stop, to_stop)
        category_prices[cat_id] = float(price) # Convert Decimal to float for JSON

    # 4. Determine Availability (The Overlap Logic)
    # Find all tickets for this trip that OVERLAP with our requested segment.
    # Logic: Ticket Start < Our End AND Ticket End > Our Start
    booked_tickets = Ticket.objects.filter(
        trip=trip,
        status__in=['BOOKED', 'LOCKED']
    ).filter(
        Q(from_stop__stop_order__lt=to_stop.stop_order) & 
        Q(to_stop__stop_order__gt=from_stop.stop_order)
    )
    
    booked_seat_ids = list(booked_tickets.values_list('seat_object_id', flat=True))

    # 5. Fetch Layout grouped by Deck
    decks = trip.ship.decks.all().order_by('level_order')
    
    context = {
        'trip': trip,
        'from_stop': from_stop,
        'to_stop': to_stop,
        'decks': decks,
        'booked_seat_ids': booked_seat_ids,
        'category_prices': category_prices,
    }
    return render(request, 'admin_panel/book/select_seats.html', context)


@login_required
def admin_book_confirm(request):
    if request.method != 'POST':
        return redirect('admin_home')

    # --- GET DATA ---
    trip_id = request.POST.get('trip_id')
    seat_ids_str = request.POST.get('selected_seats')
    
    # Customer Data (Now Mandatory)
    c_phone = request.POST.get('customer_phone')
    c_email = request.POST.get('customer_email')
    c_name = request.POST.get('customer_name')
    
    # Route Data
    from_stop_id = request.POST.get('from_stop_id')
    to_stop_id = request.POST.get('to_stop_id')
    
    # [NEW] Payment Status from Dropdown
    payment_status_input = request.POST.get('payment_status') # 'PAID' or 'UNPAID'

    if not seat_ids_str:
        messages.error(request, "No seats selected.")
        return redirect(request.META.get('HTTP_REFERER'))

    trip = get_object_or_404(Trip, id=trip_id)
    seat_ids = seat_ids_str.split(',')
    from_stop = get_object_or_404(RouteStop, id=from_stop_id)
    to_stop = get_object_or_404(RouteStop, id=to_stop_id)

    # --- LOGIC: DETERMINE STATUS ---
    # If admin selects PAID, status is CONFIRMED.
    # If admin selects UNPAID, status is PENDING.
    if payment_status_input == 'PAID':
        final_status = 'CONFIRMED'
        final_payment_status = 'PAID'
    else:
        final_status = 'PENDING'
        final_payment_status = 'UNPAID'

    try:
        with transaction.atomic():
            
            # A. Handle User (Find or Create)
            booking_user = request.user 
            if c_name and c_phone:
                user = User.objects.filter(phone_number=c_phone).first()
                if not user and c_email:
                    user = User.objects.filter(email=c_email).first()

                if not user:
                    final_email = c_email if c_email else f"{c_phone}@guest.com"
                    random_pass = get_random_string(length=12)
                    
                    user = User.objects.create_user(
                        email=final_email,
                        username=c_phone,
                        phone_number=c_phone,
                        first_name=c_name,
                        password=random_pass,
                        user_type=1
                    )
                booking_user = user

            # B. Create Booking (With NEW Status)
            booking = Booking.objects.create(
                user=booking_user,
                trip=trip,
                booking_ref=str(uuid.uuid4())[:12].upper(),
                status=final_status,          # <--- UPDATED
                payment_status=final_payment_status, # <--- UPDATED (Ensure your model has this field)
                sales_channel='COUNTER', 
                total_amount=0 
            )

            # C. Create Tickets
            total_amount = 0
            
            for seat_id in seat_ids:
                layout_obj = get_object_or_404(LayoutObject, id=seat_id)
                
                # Check Availability
                if not trip.is_seat_available(layout_obj, from_stop, to_stop):
                    raise Exception(f"Seat {layout_obj.label} was just booked by someone else!")

                price = trip.get_price(layout_obj.category, from_stop, to_stop)

                Ticket.objects.create(
                    booking=booking,
                    trip=trip,
                    seat_object=layout_obj,
                    from_stop=from_stop,
                    to_stop=to_stop,
                    passenger_name=c_name if c_name else "Walk-in Guest",
                    fare_amount=price,
                    status='BOOKED',
                    lock_expires_at=timezone.now(),
                )
                total_amount += price

            # D. Update Total
            booking.total_amount = total_amount
            booking.save()

            msg_type = "success" if final_status == 'CONFIRMED' else "warning"
            msg_text = f"Booking {final_status}! Ref: {booking.booking_ref}"
            messages.add_message(request, getattr(messages, msg_type.upper()), msg_text)
            
            return redirect('admin_booking_list')

    except Exception as e:
        print(f"Booking Failed: {e}")
        messages.error(request, f"Booking Failed: {e}")
        return redirect(request.META.get('HTTP_REFERER'))




# --- 2. NEW VIEW: QUICK STATUS UPDATE (For the list page) ---
@login_required
def update_booking_status(request, booking_id, new_status):
    """
    Called when admin clicks the Checkmark on a PENDING booking.
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    if new_status == 'CONFIRMED':
        booking.status = 'CONFIRMED'
        booking.payment_status = 'PAID' # Auto-mark as paid if confirmed via this button
        booking.save()
        messages.success(request, f"Booking #{booking.id} has been Confirmed & Marked as Paid.")
    
    # You can add more status logic here if needed (e.g. CANCELLED)
    
    return redirect('admin_booking_list')



@require_POST
@login_required
def toggle_trip_lock(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    
    # 1. CHECK: Is it currently locked by Admin?
    locked_booking = Booking.objects.filter(trip=trip, status='LOCKED').first()
    
    if locked_booking:
        # --- UNLOCK ACTION ---
        locked_booking.delete()
        return JsonResponse({'status': 'unlocked', 'message': 'Seats have been released.'})
        
    else:
        # --- LOCK ACTION ---
        with transaction.atomic():
            # A. Create the "Blocker" Booking
            booking = Booking.objects.create(
                user=request.user,
                trip=trip,
                booking_ref=f"LOCK-{str(uuid.uuid4())[:8].upper()}",
                status='LOCKED',
                payment_status='UNPAID',
                total_amount=0,
                sales_channel='COUNTER'
            )
            
            # B. [FIXED] Identify Route Start/End safely using 'stop_order'
            route_stops = RouteStop.objects.filter(route=trip.route).order_by('stop_order')
            
            if not route_stops.exists():
                return JsonResponse({'status': 'error', 'message': 'Route has no stops defined.'})

            start_stop = route_stops.first()
            end_stop = route_stops.last()
            
            # C. Find ALL Seats
            all_seats = LayoutObject.objects.filter(
                deck__ship=trip.ship,
                category__is_bookable=True
            )

            
            locked_count = 0
            
            # Define a long expiry (10 years)
            long_expiry = timezone.now() + timedelta(days=3650)

            for seat in all_seats:
                # D. Check Availability
                if trip.is_seat_available(seat, start_stop, end_stop):
                    Ticket.objects.create(
                        booking=booking,
                        trip=trip,
                        seat_object=seat,
                        from_stop=start_stop,
                        to_stop=end_stop,
                        passenger_name="ADMIN LOCKED",
                        fare_amount=0,
                        status='LOCKED',
                        lock_expires_at=long_expiry 
                    )
                    locked_count += 1
            
            if locked_count == 0:
                booking.delete()
                return JsonResponse({'status': 'error', 'message': 'No available seats to lock!'})

            return JsonResponse({
                'status': 'locked', 
                'message': f'{locked_count} seats have been locked successfully.'
            })



from django.db.models import Sum, Count, Q

@login_required
def trip_seat_report(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    
    # 1. Get Total Capacity (using our fixed is_bookable logic)
    total_capacity = LayoutObject.objects.filter(
        deck__ship=trip.ship, 
        category__is_bookable=True
    ).count()

    # 2. Get Locked Count (Admin locks)
    locked_count = Ticket.objects.filter(trip=trip, status='LOCKED').count()

    # 3. Get Sold Tickets (Grouped by Category)
    # assuming 'BOOKED' is your sold status based on previous logs
    sold_stats = Ticket.objects.filter(trip=trip, status='BOOKED').values(
        'seat_object__category__name'
    ).annotate(
        count=Count('id'),
        total_revenue=Sum('fare_amount')
    )

    # 4. Calculate Totals
    total_sold = sum(item['count'] for item in sold_stats)
    total_revenue = sum(item['total_revenue'] for item in sold_stats) or 0
    unsold_count = total_capacity - (total_sold + locked_count)

    data = {
        'breakdown': list(sold_stats), # Converts QuerySet to list for JSON
        'summary': {
            'total_capacity': total_capacity,
            'total_sold': total_sold,
            'total_locked': locked_count,
            'total_unsold': unsold_count,
            'total_revenue': total_revenue
        }
    }
    return JsonResponse(data)






def booking_list(request):
    # Get all bookings, newest first
    bookings = Booking.objects.select_related('trip', 'user').all().order_by('-created_at')
    
    context = {
        'bookings': bookings
    }
    return render(request, 'admin_panel/book/booking_list.html', context)




@login_required
def booking_issue_list(request):
    # 1. ISSUE (Confirmed) Page
    bookings = Booking.objects.filter(status='CONFIRMED').order_by('-created_at')
    context = {
        'bookings': bookings,
        'page_title': 'Issued (Confirmed) Tickets' # <--- Custom Title
    }
    return render(request, 'admin_panel/book/booking_list.html', context)

@login_required
def booking_pending_list(request):
    # 2. PENDING Page
    bookings = Booking.objects.filter(status='PENDING').order_by('-created_at')
    context = {
        'bookings': bookings,
        'page_title': 'Pending Payment Tickets'
    }
    return render(request, 'admin_panel/book/booking_list.html', context)

@login_required
def booking_cancel_list(request):
    # 3. CANCELLED Page
    bookings = Booking.objects.filter(status='CANCELLED').order_by('-created_at')
    context = {
        'bookings': bookings,
        'page_title': 'Cancelled Tickets History'
    }
    return render(request, 'admin_panel/book/booking_list.html', context)




def ticket_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    
    # 👇 THIS IS THE FIX
    # We try 'tickets' (the custom name) first. 
    # If that doesn't work, we fall back to 'ticket_set' (the default).
    if hasattr(booking, 'tickets'):
        tickets = booking.tickets.all()
    else:
        tickets = booking.ticket_set.all()

    context = {
        'booking': booking,
        'tickets': tickets,
        'seat_count': tickets.count(),
    }
    return render(request, 'admin_panel/book/ticket_detail.html', context)



def cancel_booking(request, booking_id):
    if not request.user.is_staff: # Security check
        messages.error(request, "Access Denied.")
        return redirect('admin_home')
        
    booking = get_object_or_404(Booking, id=booking_id)

    # Prevent cancelling already cancelled bookings
    if booking.status == 'CANCELLED':
        messages.warning(request, "This booking is already cancelled.")
        return redirect('admin_booking_list')

    try:
        with transaction.atomic():
            # 1. Update Booking Status
            booking.status = 'CANCELLED'
            booking.save()

            # 2. Update All Associated Tickets
            # This effectively "Releases" the seats because your availability logic 
            # only looks for 'BOOKED' or 'LOCKED' tickets.
            tickets = Ticket.objects.filter(booking=booking)
            count = tickets.count()
            tickets.update(status='CANCELLED')

            messages.success(request, f"Booking Cancelled. {count} seats have been released back to the pool.")
            
    except Exception as e:
        messages.error(request, f"Error cancelling booking: {e}")

    return redirect('admin_booking_list')
    
    
    


from django.core.serializers.json import DjangoJSONEncoder
import json
from .models import Location, Trip, RouteStop, LayoutObject, Ticket  # Ensure imports are correct

@login_required
def pos_trip_select(request):
    """
    Step 1: Search for a Trip based on Source, Dest, and Date.
    """
    stops = Location.objects.all()

    # 1. Get Search Params from the URL (HTML Form)
    source_id = request.GET.get('source')      # e.g., "1" (Dhaka)
    dest_id = request.GET.get('destination')   # e.g., "5" (Barisal)
    date_str = request.GET.get('date')

    search_results = []

    # 2. Perform Logic (Find trips that actually connect these two stops)
    if source_id and dest_id and date_str:
        # A. Find routes having these stops
        routes_with_source = RouteStop.objects.filter(location_id=source_id).values_list('route_id', 'stop_order')
        routes_with_dest = RouteStop.objects.filter(location_id=dest_id).values_list('route_id', 'stop_order')
        
        source_map = {r_id: order for r_id, order in routes_with_source}
        dest_map = {r_id: order for r_id, order in routes_with_dest}
        
        valid_route_ids = []
        
        # B. Ensure Source comes BEFORE Destination
        for route_id, source_order in source_map.items():
            if route_id in dest_map:
                dest_order = dest_map[route_id]
                if source_order < dest_order:
                    valid_route_ids.append(route_id)
        
        # C. Query Trips
        if valid_route_ids:
            search_results = Trip.objects.filter(
                route_id__in=valid_route_ids,
                departure_datetime__date=date_str,
                is_published=True
            ).select_related('ship', 'route', 'route__source', 'route__destination')

    # 3. Context - sending 'selected_source' to HTML to build the link correctly
    context = {
        'trips': search_results,
        'stops': stops,
        'selected_source': int(source_id) if source_id else '',
        'selected_dest': int(dest_id) if dest_id else '',
        'selected_date': date_str if date_str else '',
    }

    return render(request, 'admin_panel/pos/pos_trip_select.html', context)


@login_required
def pos_booking_interface(request, trip_id):
    """
    Step 2: Show Room Selection.
    CRITICAL: Converts Location IDs (from search) to RouteStop IDs (for pricing).
    """
    trip = get_object_or_404(Trip, pk=trip_id)
    
    # 1. Get Location IDs passed from the previous page
    loc_from_id = request.GET.get('from_loc')
    loc_to_id = request.GET.get('to_loc')

    from_stop = None
    to_stop = None

    # 2. THE TRANSLATOR: Convert "Location ID" -> "RouteStop ID" for THIS trip
    if loc_from_id and loc_to_id:
        from_stop = RouteStop.objects.filter(route=trip.route, location_id=loc_from_id).first()
        to_stop = RouteStop.objects.filter(route=trip.route, location_id=loc_to_id).first()

    # 3. Fallback: If conversion fails (or no params), use full route (A to Z)
    if not from_stop or not to_stop:
        from_stop = RouteStop.objects.filter(route=trip.route).order_by('stop_order').first()
        to_stop = RouteStop.objects.filter(route=trip.route).order_by('stop_order').last()

    # 4. Get Seats & Calculate Price
    seats = LayoutObject.objects.filter(deck__ship=trip.ship).select_related('deck', 'category')
    
    booked_ids = Ticket.objects.filter(
        booking__trip=trip,
        booking__status__in=['CONFIRMED', 'PENDING']
    ).values_list('seat_object_id', flat=True)

    pos_data = []
    for seat in seats:
        try:
            # Pricing now uses the SPECIFIC stops (e.g., Dhaka->Chandpur), not just A->Z
            price = trip.get_price(seat.category, from_stop, to_stop)
        except:
            price = 0 

        pos_data.append({
            'id': seat.id,
            'label': seat.label,
            'deck_name': seat.deck.name,
            'category_name': seat.category.name if seat.category else 'General',
            'category_color': '#2563eb',
            'price': float(price),
            'is_booked': seat.id in booked_ids
        })

    # 5. Send RouteStop IDs (from_stop.id) to the template form
    context = {
        'trip': trip,
        'from_id': from_stop.id,  # This is the RouteStop ID
        'to_id': to_stop.id,      # This is the RouteStop ID
        'pos_data_json': json.dumps(pos_data, cls=DjangoJSONEncoder)
    }
    return render(request, 'admin_panel/pos/pos_booking.html', context)


# ==========================================
# 3. CONFIRM: Saving the Ticket Correctly
# ==========================================
from .services import BookingService
def pos_book_confirm(request):
    if request.method != "POST":
        return redirect('admin_home')

    try:
        # 1. Extract Data from POST
        trip_id = request.POST.get('trip_id')
        seat_ids_str = request.POST.get('selected_seats')
        
        # Route info
        from_id = request.POST.get('from_id')
        to_id = request.POST.get('to_id')
        
        # Customer Info
        customer_data = {
            'name': request.POST.get('passenger_name'),
            'phone': request.POST.get('passenger_phone'),
            'email': request.POST.get('passenger_email'), # Added email support
        }

        if not seat_ids_str:
            messages.error(request, "No seats selected.")
            return redirect(request.META.get('HTTP_REFERER'))

        seat_ids_list = [int(s) for s in seat_ids_str.split(',') if s.isdigit()]

        # 2. CALL THE SERVICE (The One Source of Truth)
        booking = BookingService.create_booking(
            admin_user=request.user,
            trip_id=trip_id,
            from_id=from_id,
            to_id=to_id,
            seat_ids_list=seat_ids_list,
            customer_data=customer_data
        )

        # 3. Success!
        messages.success(request, f"POS Booking Confirmed! Ref: {booking.booking_ref} - Total: {booking.total_amount}")
        
        # Redirect back to the seat selection page (maintaining the search params)
        return redirect(f"{reverse('pos_booking_interface', args=[trip_id])}?from={from_id}&to={to_id}")

    except Exception as e:
        # Handles "Seat already booked" and other errors
        messages.error(request, f"Error: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER'))
#----------------------------------End---------------------------------------
#--------------------------#################---------------------------------
