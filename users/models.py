from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Modelo de usuario personalizado para Prompt2Course"""
    
    class MembershipChoices(models.TextChoices):
        FREE = 'free', 'Free'
        PREMIUM = 'premium', 'Premium'
        ENTERPRISE = 'enterprise', 'Enterprise'
    
    # Campo de membresía
    membership = models.CharField(
        max_length=20, 
        choices=MembershipChoices.choices, 
        default=MembershipChoices.FREE,
        verbose_name="Tipo de Membresía"
    )
    
    # Campos adicionales
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Preferencias del usuario
    preferred_language = models.CharField(max_length=10, default='es')
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        
    def __str__(self):
        return self.username
    
    def get_course_count(self):
        """Retorna el número de cursos creados por el usuario"""
        return self.courses.count()
    
    def can_create_course(self):
        """Permitir crear cursos sin límite temporalmente"""
        return True 