# Dockerfile para Django + Celery (usando SQLite)
FROM python:3.12-slim

# Variables de entorno para evitar prompts y configurar Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev gcc sqlite3 && \
    apt-get clean

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear carpetas necesarias
RUN mkdir -p logs static

# Copiar el entrypoint
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"] 