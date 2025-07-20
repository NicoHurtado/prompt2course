from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta


class User(AbstractUser):
    """Modelo de usuario personalizado para Cursia"""
    
    class MembershipChoices(models.TextChoices):
        FREE = 'free', 'Free (1 curso)'
        STARTER = 'starter', 'Starter (5 cursos/mes)'
        PROFESSIONAL = 'professional', 'Professional (10 cursos/mes)'  
        PREMIUM = 'premium', 'Premium (20 cursos/mes)'
    
    # Campo de membresía
    membership = models.CharField(
        max_length=20, 
        choices=MembershipChoices.choices, 
        default=MembershipChoices.FREE,
        verbose_name="Plan de Suscripción"
    )
    
    # Campos de facturación y límites
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    current_month_courses = models.IntegerField(default=0, help_text="Cursos creados en el mes actual")
    last_course_reset = models.DateField(auto_now_add=True, help_text="Última vez que se reinició el contador mensual")
    
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
    
    def get_monthly_course_limit(self):
        """Retorna el límite de cursos por mes según el plan"""
        limits = {
            self.MembershipChoices.FREE: 1,
            self.MembershipChoices.STARTER: 5,
            self.MembershipChoices.PROFESSIONAL: 10,
            self.MembershipChoices.PREMIUM: 20,
        }
        return limits.get(self.membership, 1)
    
    def reset_monthly_counter_if_needed(self):
        """Reinicia el contador mensual si ha pasado un mes"""
        today = timezone.now().date()
        if self.last_course_reset.month != today.month or self.last_course_reset.year != today.year:
            self.current_month_courses = 0
            self.last_course_reset = today
            self.save()
    
    def can_create_course(self):
        """Verifica si el usuario puede crear un curso según su plan"""
        self.reset_monthly_counter_if_needed()
        return self.current_month_courses < self.get_monthly_course_limit()
    
    def increment_course_count(self):
        """Incrementa el contador de cursos del mes actual"""
        self.reset_monthly_counter_if_needed()
        self.current_month_courses += 1
        self.save()
    
    def get_courses_remaining(self):
        """Retorna cuántos cursos le quedan este mes"""
        self.reset_monthly_counter_if_needed()
        return max(0, self.get_monthly_course_limit() - self.current_month_courses)
    
    def is_subscription_active(self):
        """Verifica si la suscripción está activa"""
        if self.membership == self.MembershipChoices.FREE:
            return True
        if not self.subscription_end_date:
            return False
        return timezone.now() <= self.subscription_end_date
    
    def get_plan_price_info(self):
        """Retorna información de precios del plan actual"""
        plan_info = {
            self.MembershipChoices.FREE: {
                'name': 'Gratis',
                'courses': 1,
                'price': 0,
                'original_price': 0,
                'discount': 0
            },
            self.MembershipChoices.STARTER: {
                'name': 'Starter',
                'courses': 5,
                'price': 49900,
                'original_price': 80000,
                'discount': 38
            },
            self.MembershipChoices.PROFESSIONAL: {
                'name': 'Professional',
                'courses': 10,
                'price': 79900,
                'original_price': 150000,
                'discount': 47
            },
            self.MembershipChoices.PREMIUM: {
                'name': 'Premium',
                'courses': 20,
                'price': 99000,
                'original_price': 280000,
                'discount': 65
            },
        }
        return plan_info.get(self.membership, plan_info[self.MembershipChoices.FREE]) 