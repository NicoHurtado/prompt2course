"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from courses import views as course_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API REST
    path('api/', include('api.urls')),
    
    # Authentication and User Management
    path('', include('users.urls')),
    
    # Course Management
    path('course/<uuid:course_id>/', course_views.course_view, name='course_view'),
    path('course/<uuid:course_id>/metadata/', course_views.course_metadata, name='course_metadata'),
    path('course/<uuid:course_id>/module/<str:module_id>/', course_views.module_view, name='module_view'),
    path('course/<uuid:course_id>/status/', course_views.course_status, name='course_status'),
    
    # Course creation
    path('create-course/', course_views.simple_course_create, name='create_course'),
    path('new-course/', course_views.index, name='new_course'),
    path('create-course-from-home/', course_views.create_course_from_home, name='create_course_from_home'),
    
    # Course management
    path('course/<uuid:course_id>/delete/', course_views.delete_course, name='delete_course'),
    path('course/<uuid:course_id>/regenerate/', course_views.regenerate_course_modules, name='regenerate_course_modules'),
]

# Configuración para archivos estáticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug Toolbar URLs
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns = [
            path('__debug__/', include('debug_toolbar.urls')),
        ] + urlpatterns

# Custom error handlers
handler404 = 'config.views.custom_404'
