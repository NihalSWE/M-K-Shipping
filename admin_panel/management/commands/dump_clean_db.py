import os
import sys
from io import StringIO
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings

class Command(BaseCommand):
    help = 'Dumps database to mk_shipping.json in UTF-8, using natural keys and excluding system models.'

    def handle(self, *args, **options):
        # 1. Define the output file path (Project Root)
        output_file = os.path.join(settings.BASE_DIR, 'mk_shipping.json')

        # 2. List of models to exclude
        excludes = [
            "contenttypes.contenttype",
            "admin.logentry",
            "auth.permission",
            "sessions.session"
        ]

        self.stdout.write("⏳ Starting database dump with natural keys...")

        # 3. Capture the data in memory (StringIO)
        out = StringIO()
        
        try:
            # We call Django's native dumpdata with natural keys enabled
            call_command(
                'dumpdata',
                exclude=excludes,
                indent=4,
                natural_foreign=True,  # <-- NEW: Uses text names instead of raw foreign key IDs
                natural_primary=True,  # <-- NEW: Dependencies are resolved naturally
                stdout=out
            )

            # 4. Get the string content
            json_content = out.getvalue()

            # 5. Write to file forcing UTF-8 encoding
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_content)

            self.stdout.write(self.style.SUCCESS(f"✅ Cleaned fixture written to: {output_file}"))
            self.stdout.write(self.style.SUCCESS(f"🚀 You can now run: python manage.py loaddata mk_shipping.json"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error during dump: {str(e)}"))
            sys.exit(1)