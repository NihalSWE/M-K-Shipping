from collections import defaultdict
from .models import Ticket, LayoutObject

class POSBookingService:
    """
    Adapter between Original Booking Engine and POS UI
    """

    @staticmethod
    def get_pos_structure(trip, from_stop, to_stop):
        structure = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

        # All seats of this ship
        seats = LayoutObject.objects.filter(
            deck__ship=trip.ship
        ).select_related('deck', 'category')

        # Already booked seats
        booked_ids = set(
            Ticket.objects.filter(
                booking__trip=trip,
                booking__status__in=["CONFIRMED", "PENDING"]
            ).values_list("seat_object_id", flat=True)
        )

        for seat in seats:
            if seat.id in booked_ids:
                continue

            deck = seat.deck.name
            category = seat.category.name
            category_name = seat.category.name

            variant = "AC" if "AC" in category_name.upper() else "NON-AC"


            price = trip.get_price(seat.category, from_stop, to_stop)

            structure[deck][category].setdefault(variant, {
                "price": price,
                "seats": []
            })

            structure[deck][category][variant]["seats"].append({
                "id": seat.id,
                "label": seat.label
            })

        return structure
