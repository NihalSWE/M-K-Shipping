import json
import os
from django.core.management.base import BaseCommand
from admin_panel.models import Division, District, Thana

class Command(BaseCommand):
    help = 'Populates Division, District, and Thana from JSON fixtures'

    def handle(self, *args, **kwargs):
        base_path = 'admin_panel/fixtures/'
        
        # 1. Load Divisions
        self.stdout.write("Loading Divisions...")
        with open(os.path.join(base_path, 'divisions.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
            # data[2]['data'] is the list based on the nuhil structure
            # Structure: [{"type":...}, ..., {"type":"table", "data": [...]}]
            # We need to find the element with "data" key that is a list
            
            # Helper to find data list in the phpMyAdmin export format
            def get_data_list(json_data, table_name):
                for item in json_data:
                    if item.get('type') == 'table' and item.get('name') == table_name:
                         return item.get('data')
                return []

            divisions = get_data_list(data, 'divisions')
            
            for item in divisions:
                Division.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'name': item['name'],
                        'bn_name': item['bn_name']
                    }
                )

        # 2. Load Districts
        self.stdout.write("Loading Districts...")
        with open(os.path.join(base_path, 'districts.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
            districts = get_data_list(data, 'districts')
            
            for item in districts:
                # Remove division_id from defaults as it is a FK
                District.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'division_id': item['division_id'],
                        'name': item['name'],
                        'bn_name': item['bn_name'],
                        'lat': item.get('lat'),
                        'lon': item.get('lon')
                    }
                )

        # 3. Load Thanas (Upazilas)
        self.stdout.write("Loading Thanas...")
        try:
            with open(os.path.join(base_path, 'upazilas.json'), 'r', encoding='utf-8') as f:
                data = json.load(f)
                thanas = get_data_list(data, 'upazilas')
                
                for item in thanas:
                    Thana.objects.update_or_create(
                        id=item['id'],
                        defaults={
                            'district_id': item['district_id'],
                            'name': item['name'],
                            'bn_name': item['bn_name']
                        }
                    )
        except FileNotFoundError:
            self.stdout.write("Upazilas file not found, skipping.")

        self.stdout.write(self.style.SUCCESS('Successfully populated Geo Data'))
