from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import Course, Module, UserProgress


def index(request):
    """Vista principal para crear cursos"""
    return render(request, 'index.html')


@csrf_exempt
@require_http_methods(["POST"])
def simple_course_create(request):
    """Vista simple para demostrar la creación de cursos sin APIs externas"""
    try:
        # Obtener el último curso creado como demostración
        sample_course = Course.objects.filter(status=Course.StatusChoices.COMPLETE).last()
        
        if sample_course:
            return JsonResponse({
                'id': str(sample_course.id),
                'title': sample_course.title,
                'status': 'complete',
                'message': 'Redirigiendo al curso de demostración'
            }, status=201)
        else:
            return JsonResponse({
                'error': 'No hay cursos de demostración disponibles. Ejecuta create_sample_data.py'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'error': f'Error: {str(e)}'
        }, status=500)


def course_view(request, course_id):
    """Vista del curso completo"""
    course = get_object_or_404(Course, id=course_id)
    
    # Obtener progreso del usuario si está autenticado
    user_progress = None
    if request.user.is_authenticated:
        try:
            user_progress = UserProgress.objects.get(user=request.user, course=course)
        except UserProgress.DoesNotExist:
            # Crear progreso inicial para el usuario
            first_module = course.modules.first()
            user_progress = UserProgress.objects.create(
                user=request.user,
                course=course,
                current_module=first_module
            )
    
    context = {
        'course': course,
        'user_progress': user_progress,
    }
    return render(request, 'course.html', context)


def course_metadata(request, course_id):
    """Vista de metadata del curso"""
    course = get_object_or_404(Course, id=course_id)
    
    context = {
        'course': course,
    }
    return render(request, 'metadata.html', context)


def module_view(request, course_id, module_id):
    """Vista de módulo individual"""
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(Module, course=course, module_id=module_id)
    
    # Obtener módulos anterior y siguiente
    previous_module = Module.objects.filter(
        course=course, 
        module_order__lt=module.module_order
    ).order_by('-module_order').first()
    
    next_module = Module.objects.filter(
        course=course, 
        module_order__gt=module.module_order
    ).order_by('module_order').first()
    
    # Obtener progreso del usuario si está autenticado
    user_progress = None
    if request.user.is_authenticated:
        try:
            user_progress = UserProgress.objects.get(user=request.user, course=course)
        except UserProgress.DoesNotExist:
            # Crear progreso inicial para el usuario
            user_progress = UserProgress.objects.create(
                user=request.user,
                course=course,
                current_module=module
            )
    
    context = {
        'course': course,
        'module': module,
        'previous_module': previous_module,
        'next_module': next_module,
        'user_progress': user_progress,
    }
    return render(request, 'module.html', context)


def course_status(request, course_id):
    """API endpoint para verificar el estado del curso"""
    course = get_object_or_404(Course, id=course_id)
    
    return JsonResponse({
        'status': course.status,
        'status_display': course.get_status_display(),
        'progress_percentage': course.get_progress_percentage(),
        'title': course.title,
        'description': course.description,
    })
