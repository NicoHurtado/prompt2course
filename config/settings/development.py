from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Database for development (SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Additional development settings
CORS_ALLOW_ALL_ORIGINS = True

# Debug toolbar settings (disabled for cleaner UI)
# if DEBUG:
#     # debug_toolbar is already included in THIRD_PARTY_APPS in base.py
#     MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
#     
#     def show_toolbar(request):
#         return True
#     
#     DEBUG_TOOLBAR_CONFIG = {
#         'SHOW_TOOLBAR_CALLBACK': show_toolbar,
#     }

# Development specific logging
LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['root']['level'] = 'DEBUG' 