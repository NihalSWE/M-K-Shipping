import json
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone


class LicenseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_static_or_media_request(request) or self._is_license_valid():
            return self.get_response(request)

        return self._blocked_response()

    def _is_static_or_media_request(self, request):
        path = request.path
        static_url = getattr(settings, "STATIC_URL", "")
        media_url = getattr(settings, "MEDIA_URL", "")

        return any(
            url and path.startswith(url)
            for url in self._request_path_prefixes(static_url, media_url)
        )

    def _request_path_prefixes(self, *urls):
        prefixes = []

        for url in urls:
            if not url:
                continue

            prefixes.append(url)
            if not url.startswith("/"):
                prefixes.append(f"/{url}")

        return prefixes

    def _is_license_valid(self):
        try:
            license_path = settings.BASE_DIR / "license.json"

            with license_path.open("r", encoding="utf-8") as license_file:
                license_data = json.load(license_file)

            expires_value = license_data.get("expires")
            if not expires_value:
                return False

            expires_date = datetime.strptime(expires_value, "%Y-%m-%d").date()
            today = timezone.localdate()

            return today <= expires_date
        except Exception:
            return False

    def _blocked_response(self):
        html = """<!DOCTYPE html>
<html>
<head>
    <title>License Expired</title>
</head>
<body>
    <h1>License Expired</h1>
    <p>Please contact developer.</p>
</body>
</html>"""
        return HttpResponse(html, status=403, content_type="text/html")
