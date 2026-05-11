# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# import admin_panel.routing

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             admin_panel.routing.websocket_urlpatterns
#         )
#     ),
# })



import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 🔥 1. Initialize Django FIRST so the App Registry is loaded
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# 🔥 2. Import your routing AFTER Django is ready
import portal.routing
import admin_panel.routing # Keep this if you have other websockets in admin_panel

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            # Combine the lists so Daphne knows about routes in BOTH apps
            portal.routing.websocket_urlpatterns + 
            admin_panel.routing.websocket_urlpatterns
        )
    ),
})