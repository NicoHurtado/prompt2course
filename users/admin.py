from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Configuración del admin para el modelo de usuario personalizado"""
    
    # Campos a mostrar en la lista
    list_display = ['username', 'email', 'first_name', 'last_name', 'membership', 'get_course_count', 'is_active', 'date_joined']
    list_filter = ['membership', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    # Configuración de fieldsets para el formulario de edición
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('membership', 'preferred_language'),
        }),
        ('Fechas Importantes', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
    # Campos de solo lectura
    readonly_fields = ['created_at', 'updated_at', 'date_joined']
    
    # Configuración para agregar nuevo usuario
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('email', 'first_name', 'last_name', 'membership'),
        }),
    )
    
    def get_course_count(self, obj):
        """Mostrar cantidad de cursos creados"""
        return obj.get_course_count()
    
    get_course_count.short_description = 'Cursos Creados' 