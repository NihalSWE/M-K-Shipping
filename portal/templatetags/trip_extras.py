from django import template
register = template.Library()

@register.simple_tag
def get_segment_price(trip, category, from_stop, to_stop):
    return trip.get_price(category, from_stop, to_stop)