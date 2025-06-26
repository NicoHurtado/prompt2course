# Esto asegurará que la aplicación Celery se importe cuando Django inicie
from .celery import app as celery_app

__all__ = ('celery_app',)
