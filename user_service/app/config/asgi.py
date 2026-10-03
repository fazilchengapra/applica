import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# The notifications websocket used to be served from here. It now lives in
# notification_service (Kong routes /ws/notifications/ there), which is also
# where the realtime fan-out happens, so this ASGI app is HTTP-only.
django_asgi_app = get_asgi_application()

application = django_asgi_app
