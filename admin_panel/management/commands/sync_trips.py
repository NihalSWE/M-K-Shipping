import logging
from django.core.management.base import BaseCommand
# Replace 'your_app_name' with your actual app name (e.g., 'trips' or 'core')
from admin_panel.models import TripSchedule
from admin_panel.services import generate_smart_trips

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Daily sync to keep the advance booking window full based on TripSchedule blueprints'

    def handle(self, *args, **options):
        self.stdout.write("Starting trip synchronization engine...")

        # 1. Get all unique ship IDs that have an active schedule
        active_ships = TripSchedule.objects.filter(
            is_active=True
        ).values_list('ship_id', flat=True).distinct()

        if not active_ships:
            self.stdout.write(self.style.WARNING("No active schedules found. Nothing to sync."))
            return

        total_synced = 0
        for ship_id in active_ships:
            # 2. Get the specific schedule settings for this ship
            # We fetch one active schedule to determine the advance_booking_days limit
            latest_sched = TripSchedule.objects.filter(ship_id=ship_id, is_active=True).first()
            
            if latest_sched:
                self.stdout.write(f"Processing Ship ID: {ship_id} (Window: {latest_sched.advance_booking_days} days)")
                
                # 3. Call your Smart Engine (already in services.py)
                # It will check the ship's current location and chain the next trips
                result = generate_smart_trips(
                    ship_id=ship_id, 
                    days_to_generate=latest_sched.advance_booking_days
                )
                
                self.stdout.write(self.style.SUCCESS(f"Ship {ship_id}: {result}"))
                total_synced += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully synced {total_synced} ships."))