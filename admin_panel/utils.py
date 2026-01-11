from .models import Trip, RouteStop

def find_valid_trips(source_id, dest_id, date_str):
    """
    Centralized search logic used by both POS and Website.
    Ensures we only return valid, published trips where source comes before destination.
    """
    
    # 1. Find routes that contain BOTH stops
    # We fetch only the route_id and order to match them in Python (faster than complex SQL joins sometimes)
    relevant_stops = RouteStop.objects.filter(
        location_id__in=[source_id, dest_id]
    ).values('route_id', 'location_id', 'stop_order')

    # 2. Check Order: Does Source come before Destination?
    route_map = {}
    for item in relevant_stops:
        rid = item['route_id']
        if rid not in route_map:
            route_map[rid] = {}
        route_map[rid][item['location_id']] = item['stop_order']

    valid_route_ids = []
    for rid, stops in route_map.items():
        # Must have both source and dest
        if source_id in stops and dest_id in stops:
            # Source order must be strictly less than Dest order
            if stops[source_id] < stops[dest_id]:
                valid_route_ids.append(rid)

    # 3. Fetch Trips (With Safety Filters)
    return Trip.objects.filter(
        route_id__in=valid_route_ids,
        departure_datetime__date=date_str,
        is_published=True,      # SAFETY: Don't show hidden trips
        status='SCHEDULED'      # SAFETY: Don't show cancelled trips (if you have a status field)
    ).select_related('ship', 'route', 'route__source', 'route__destination').order_by('departure_datetime')