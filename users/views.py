from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from .forms import SignUpForm
from courses.models import Course


def home_view(request):
    """Vista del home principal de Cursia"""
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    context = {
        'show_auth_buttons': True,
    }
    return render(request, 'users/home.html', context)


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