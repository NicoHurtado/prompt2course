import os
from celery import Celery
from django.conf import settings

# Configurar el módulo de configuración predeterminado de Django para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('p2c')

# Usar cadena de configuración para serialización JSON
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubrir tareas automáticamente
app.autodiscover_tasks()

# Configuración adicional
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=settings.TIME_ZONE,
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 