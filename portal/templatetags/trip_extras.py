from django import template
register = template.Library()

@register.simple_tag
def get_segment_price(trip, category, from_stop, to_stop):
    return trip.get_price(category, from_stop, to_stop)

@register.filter
def get_item(d, key):
    """
    Usage: {{ my_dict|get_item:some_key }}
    Works for dicts. Returns None if missing.
    """
    if isinstance(d, dict):
        return d.get(key)
    return None