from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
import json
from .forms import SignUpForm
from courses.models import Course


def home_view(request):
    """Vista del home principal de Cursia"""
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    context = {
        'show_auth_buttons': True,
    }
    return render(request, 'index.html', context)


def login_view(request):
    """Vista de login"""
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido de vuelta, {user.first_name or user.username}!')
                
                # Redirigir a la página solicitada o al dashboard
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('users:dashboard')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = AuthenticationForm()
    
    context = {
        'form': form,
        'page_title': 'Iniciar Sesión'
    }
    return render(request, 'users/login.html', context)


def signup_view(request):
    """Vista de registro"""
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            
            # Autenticar y hacer login automáticamente
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Cuenta creada exitosamente! Bienvenido a Cursia, {user.first_name or user.username}!')
                
                # Check if there's a next URL (from course creation flow)
                next_url = request.GET.get('next')
                if next_url == 'create-course':
                    # Check if course data was provided
                    course_topic = request.POST.get('course_topic')
                    course_level = request.POST.get('course_level', 'principiante')
                    course_interests = request.POST.get('course_interests', '[]')
                    
                    if course_topic:
                        # Create the course immediately
                        try:
                            import json
                            from courses.models import Course
                            from generation.tasks import generate_course_metadata
                            
                            # Parse interests
                            try:
                                interests = json.loads(course_interests)
                                if not isinstance(interests, list):
                                    interests = []
                            except (json.JSONDecodeError, TypeError):
                                interests = []
                            
                            # Create course
                            course = Course.objects.create(
                                user=user,
                                user_prompt=course_topic,
                                user_level=course_level,
                                user_interests=interests,
                                status=Course.StatusChoices.GENERATING_METADATA,
                                language='es'
                            )
                            
                            # Increment course count
                            user.increment_course_count()
                            
                            # Start generation
                            generate_course_metadata.delay(str(course.id))
                            
                            messages.success(request, f'¡Curso "{course_topic}" creado exitosamente! Estamos generando el contenido con IA...')
                            return redirect('course_view', course_id=course.id)
                            
                        except Exception as e:
                            messages.error(request, f'Error al crear el curso: {str(e)}')
                            return redirect('new_course')
                    else:
                        return redirect('new_course')
                return redirect('users:dashboard')
    else:
        form = SignUpForm()
    
    context = {
        'form': form,
        'page_title': 'Crear Cuenta'
    }
    return render(request, 'users/signup.html', context)


def logout_view(request):
    """Vista de logout"""
    if request.user.is_authenticated:
        messages.success(request, f'¡Hasta luego, {request.user.first_name or request.user.username}!')
        logout(request)
    return redirect('users:home')


@login_required
def dashboard_view(request):
    """Dashboard del usuario con sus cursos"""
    user = request.user
    
    # Obtener cursos del usuario ordenados por fecha de creación
    courses = Course.objects.filter(user=user).order_by('-created_at')
    
    # Estadísticas del usuario
    stats = {
        'total_courses': courses.count(),
        'completed_courses': courses.filter(status=Course.StatusChoices.COMPLETE).count(),
        'in_progress_courses': courses.filter(
            status__in=[
                Course.StatusChoices.READY,
                Course.StatusChoices.GENERATING_REMAINING
            ]
        ).count(),
        'generating_courses': courses.filter(
            status__in=[
                Course.StatusChoices.GENERATING_METADATA,
                Course.StatusChoices.GENERATING_MODULES_METADATA,
                Course.StatusChoices.GENERATING_MODULE_1
            ]
        ).count(),
    }
    
    # Verificar si puede crear más cursos
    can_create_more = user.can_create_course()

    context = {
        'user': user,
        'courses': courses,
        'stats': stats,
        'can_create_more': can_create_more,
        'courses_remaining': user.get_courses_remaining(),
        'current_plan': user.get_plan_price_info(),
        'page_title': 'Mi Dashboard'
    }
    return render(request, 'users/dashboard.html', context)


@login_required
def profile_view(request):
    """Vista del perfil del usuario"""
    context = {
        'user': request.user,
        'page_title': 'Mi Perfil'
    }
    return render(request, 'users/profile.html', context)


@login_required
def payment_simulation_view(request):
    """Vista para simular el proceso de pago"""
    if request.method == 'GET':
        plan = request.GET.get('plan', 'aprendiz')
        context = {
            'selected_plan': plan,
            'page_title': 'Proceso de Pago'
        }
        return render(request, 'payment_simulation.html', context)
    
    return redirect('users:dashboard')


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def process_payment_simulation(request):
    """Procesar la simulación de pago y actualizar suscripción"""
    try:
        data = json.loads(request.body)
        plan = data.get('plan')
        payment_method = data.get('payment_method')
        
        # Map plan names to model choices
        plan_mapping = {
            'aprendiz': request.user.MembershipChoices.STARTER,
            'experto': request.user.MembershipChoices.PROFESSIONAL,
            'familiar': request.user.MembershipChoices.PREMIUM,
        }
        
        if plan not in plan_mapping:
            return JsonResponse({'error': 'Plan inválido'}, status=400)
        
        # Simulate payment processing delay
        import time
        time.sleep(2)  # Simulate processing time
        
        # Update user subscription
        user = request.user
        user.membership = plan_mapping[plan]
        user.subscription_start_date = timezone.now()
        user.subscription_end_date = timezone.now() + timedelta(days=30)  # 30 day subscription
        user.current_month_courses = 0  # Reset course count
        user.last_course_reset = timezone.now().date()
        user.save()
        
        plan_info = user.get_plan_price_info()
        
        return JsonResponse({
            'success': True,
            'message': f'¡Pago procesado exitosamente! Tu plan {plan_info["name"]} está activo.',
            'new_plan': plan_info,
            'redirect_url': reverse('users:dashboard')
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error al procesar el pago: {str(e)}'
        }, status=500) 