#!/usr/bin/env python3
"""
Script para generar manualmente el módulo 2 del curso actual
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from courses.models import Course
from generation.tasks import generate_remaining_modules

def generate_module_2():
    """Activar generación del módulo 2 para el curso más reciente"""
    try:
        # Obtener el curso más reciente
        latest_course = Course.objects.filter(status=Course.StatusChoices.READY).latest('created_at')
        
        print(f"🎯 Curso encontrado: {latest_course.title}")
        print(f"📊 Estado actual: {latest_course.status}")
        print(f"🔢 ID del curso: {latest_course.id}")
        
        # Activar generación de módulos restantes
        print("🚀 Activando generación de módulos restantes...")
        task = generate_remaining_modules.delay(str(latest_course.id))
        
        print(f"✅ Tarea iniciada: {task.id}")
        print("⏳ El módulo 2 se generará en unos 2-3 minutos")
        print("🔄 Puedes refrescar la página en unos minutos para ver el contenido")
        
        return True
        
    except Course.DoesNotExist:
        print("❌ No se encontró ningún curso listo")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    generate_module_2() 