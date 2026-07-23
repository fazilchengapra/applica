# app/config/test_settings.py
from .settings import *

DATABASES["default"]["NAME"] = "test_" + DATABASES["default"]["NAME"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]