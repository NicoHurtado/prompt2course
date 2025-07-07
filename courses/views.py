from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import Course, Module, UserProgress
from django.urls import reverse
from generation.tasks import generate_course_metadata, generate_remaining_modules, regenerate_missing_modules


@login_required
def index(request):
    """Vista principal para crear cursos"""
    # Verificar si el usuario puede crear más cursos
    if not request.user.can_create_course():
        return redirect('users:dashboard')
    
    context = {
        'can_create_more': request.user.can_create_course(),
    }
    return render(request, 'index.html', context)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def simple_course_create(request):
    """Vista para crear cursos reales usando la API de Claude"""
    try:
        # Verificar si el usuario puede crear más cursos
        if not request.user.can_create_course():
            return JsonResponse({
                'error': f'Has alcanzado el límite de cursos para tu membresía {request.user.get_membership_display()}. Actualiza tu plan para crear más cursos.'
            }, status=403)
        
        # Obtener datos del formulario
        user_prompt = request.POST.get('user_prompt', '').strip()
        user_level = request.POST.get('user_level', 'principiante')
        user_interests_json = request.POST.get('user_interests', '[]')
        
        # Validar datos requeridos
        if not user_prompt:
            return JsonResponse({
                'error': 'El prompt es requerido'
            }, status=400)
            
        if len(user_prompt) < 10:
            return JsonResponse({
                'error': 'El prompt debe tener al menos 10 caracteres'
            }, status=400)
        
        # Parsear intereses
        try:
            user_interests = json.loads(user_interests_json)
            if not isinstance(user_interests, list):
                user_interests = []
        except (json.JSONDecodeError, TypeError):
            user_interests = []
        
        # Crear curso con status inicial
        course = Course.objects.create(
            user=request.user,
            user_prompt=user_prompt,
            user_level=user_level,
            user_interests=user_interests,
            status=Course.StatusChoices.GENERATING_METADATA,
            language='es'  # Por defecto español
        )
        
        # Iniciar tarea asíncrona de generación de metadata (Fase 1)
        generate_course_metadata.delay(str(course.id))
        
        # Respuesta inmediata con datos básicos
        return JsonResponse({
            'id': str(course.id),
            'status': course.status,
            'title': course.title or None,
            'message': 'Curso creado exitosamente. Generando metadata con IA...'
        }, status=201)
            
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno del servidor: {str(e)}'
        }, status=500)


@login_required
def course_view(request, course_id):
    """Vista del curso completo"""
    course = get_object_or_404(Course, id=course_id, user=request.user)
    
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
        'breadcrumbs': [
            (reverse('users:dashboard'), 'Dashboard'),
            (None, course.title),
        ],
    }
    return render(request, 'course.html', context)


@login_required
def course_metadata(request, course_id):
    """Vista de metadata del curso"""
    course = get_object_or_404(Course, id=course_id, user=request.user)
    
    context = {
        'course': course,
    }
    return render(request, 'metadata.html', context)


@login_required
def module_view(request, course_id, module_id):
    """Vista de módulo individual"""
    course = get_object_or_404(Course, id=course_id, user=request.user)
    module = get_object_or_404(Module, course=course, module_id=module_id)
    
    # AUTO-GENERACIÓN: Si el módulo no tiene contenido, activar generación (fallback)
    # Nota: Con el nuevo flujo automático, esto solo debería ejecutarse como respaldo
    if module.chunks.count() == 0 and module.module_order > 1:
        # Solo para módulos 2+ que estén vacíos
        # Verificar que no esté ya en proceso de generación
        if course.status == Course.StatusChoices.READY:
            # Activar generación de módulos restantes como fallback
            generate_remaining_modules.delay(str(course.id))
            
            # Cambiar status a indicar que se están generando módulos restantes
            course.status = Course.StatusChoices.GENERATING_REMAINING
            course.save()
    
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
        'breadcrumbs': [
            (reverse('users:dashboard'), 'Dashboard'),
            (reverse('course_view', kwargs={'course_id': course.id}), course.title),
            (None, module.title),
        ],
    }
    return render(request, 'module.html', context)


@login_required
def course_status(request, course_id):
    """API endpoint para verificar el estado del curso"""
    course = get_object_or_404(Course, id=course_id, user=request.user)
    
    return JsonResponse({
        'status': course.status,
        'status_display': course.get_status_display(),
        'progress_percentage': course.get_progress_percentage(),
        'title': course.title,
        'description': course.description,
    })


@login_required
@require_http_methods(["POST"])
def regenerate_course_modules(request, course_id):
    """Vista para regenerar módulos faltantes de un curso"""
    try:
        course = get_object_or_404(Course, id=course_id, user=request.user)
        
        # Verificar que hay módulos faltantes
        missing_modules = []
        for module_number in range(1, course.total_modules + 1):
            existing_module = Module.objects.filter(course=course, module_order=module_number).first()
            if not existing_module or existing_module.chunks.count() == 0:
                missing_modules.append(module_number)
        
        if not missing_modules:
            return JsonResponse({
                'error': False,
                'message': 'No hay módulos faltantes en este curso',
                'missing_modules': []
            })
        
        # Iniciar tarea de regeneración
        regenerate_missing_modules.delay(str(course.id))
        
        return JsonResponse({
            'error': False,
            'message': f'Iniciando regeneración de {len(missing_modules)} módulos faltantes',
            'missing_modules': missing_modules
        })
        
    except Exception as e:
        return JsonResponse({
            'error': True,
            'message': f'Error al iniciar regeneración: {str(e)}'
        }, status=500)


