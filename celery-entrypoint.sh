#!/bin/bash
set -e

# Crear directorio logs si no existe
mkdir -p logs

# Activar entorno virtual si existe (por si se usa localmente)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Esperar a que Redis esté disponible (sin redis-cli)
echo "Esperando a que Redis esté listo..."
sleep 10
echo "Redis debería estar listo!"

# Migraciones
python manage.py migrate --noinput

# Ejecutar Celery worker
echo "Iniciando Celery worker..."
celery -A config worker -l info 