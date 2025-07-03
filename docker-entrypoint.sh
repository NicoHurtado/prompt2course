#!/bin/bash
set -e

# Crear directorio logs si no existe
mkdir -p logs

# Activar entorno virtual si existe (por si se usa localmente)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Migraciones
python manage.py migrate --noinput

# Crear datos de ejemplo solo si la base está vacía
if [ ! -f db.sqlite3 ] || [ $(sqlite3 db.sqlite3 ".tables" | wc -w) -eq 0 ]; then
    python create_sample_data.py || true
fi

# Ejecutar el comando que se pase (por defecto runserver)
if [ "$1" = "celery" ]; then
    shift
    celery -A config worker -l info "$@"
else
    python manage.py runserver 0.0.0.0:8000
fi 