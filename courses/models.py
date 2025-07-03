import uuid
import json
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


class Course(models.Model):
    """Modelo principal del curso generado por P2C"""
    
    class StatusChoices(models.TextChoices):
        GENERATING_METADATA = 'generating_metadata', 'Generando Metadata'
        GENERATING_MODULES_METADATA = 'generating_modules_metadata', 'Generando Metadata de Módulos'
        METADATA_READY = 'metadata_ready', 'Metadata Lista'
        GENERATING_MODULE_1 = 'generating_module_1', 'Generando Módulo 1'
        READY = 'ready', 'Listo para Consumir'
        GENERATING_REMAINING = 'generating_remaining', 'Generando Módulos Restantes'
        COMPLETE = 'complete', 'Completo'
        FAILED = 'failed', 'Error en Generación'
    
    class LevelChoices(models.TextChoices):
        PRINCIPIANTE = 'principiante', 'Principiante'
        INTERMEDIO = 'intermedio', 'Intermedio'
        AVANZADO = 'avanzado', 'Avanzado'

    # Identificadores únicos
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_id = models.CharField(max_length=100, unique=True, blank=True)
    
    # Información del usuario y generación
    user_prompt = models.TextField(verbose_name="Prompt del usuario")
    user_level = models.CharField(max_length=20, choices=LevelChoices.choices, default=LevelChoices.PRINCIPIANTE)
    user_interests = models.JSONField(default=list, blank=True)
    
    # Estado y timestamps
    status = models.CharField(max_length=30, choices=StatusChoices.choices, default=StatusChoices.GENERATING_METADATA)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadatos del curso
    title = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    prerequisites = models.JSONField(default=list, blank=True)
    total_modules = models.PositiveIntegerField(default=4)
    module_list = models.JSONField(default=list, blank=True)
    topics = models.JSONField(default=list, blank=True)
    
    # Podcast information
    podcast_script = models.TextField(blank=True)
    podcast_audio_url = models.URLField(blank=True)
    
    # Introducción y proyecto final
    introduction = models.TextField(blank=True)
    final_project_data = models.JSONField(default=dict, blank=True)
    
    # Metadatos adicionales
    total_size_estimate = models.CharField(max_length=100, blank=True)  # "~300KB contenido interactivo"
    language = models.CharField(max_length=10, default='es')
    
    def save(self, *args, **kwargs):
        if not self.course_id:
            self.course_id = f"course-{self.id}"
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validaciones personalizadas"""
        if self.total_modules < 1 or self.total_modules > 10:
            raise ValidationError("El número de módulos debe estar entre 1 y 10")
            
        if isinstance(self.user_interests, list) and len(self.user_interests) > 10:
            raise ValidationError("Máximo 10 intereses permitidos")
            
        if isinstance(self.topics, list) and len(self.topics) > 20:
            raise ValidationError("Máximo 20 temas permitidos")
    
    def mark_complete(self):
        """Marca el curso como completo"""
        self.status = self.StatusChoices.COMPLETE
        self.completed_at = timezone.now()
        self.save()
    
    def get_progress_percentage(self):
        """Calcula el porcentaje de progreso del curso"""
        if self.status == self.StatusChoices.COMPLETE:
            return 100
        elif self.status == self.StatusChoices.READY:
            return 75
        elif self.status == self.StatusChoices.METADATA_READY:
            return 50
        elif self.status == self.StatusChoices.GENERATING_METADATA:
            return 25
        return 0

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['course_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user_level']),
        ]

    def __str__(self):
        return self.title or f"Curso {self.course_id}"


class Module(models.Model):
    """Módulo individual del curso"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    
    # Identificadores
    module_id = models.CharField(max_length=50)  # "modulo_1", "modulo_2", etc.
    module_order = models.PositiveIntegerField()
    
    # Contenido del módulo
    title = models.CharField(max_length=300)
    description = models.TextField()
    objective = models.TextField(blank=True)
    concepts = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)
    
    # Ejercicio práctico
    practical_exercise = models.JSONField(default=dict, blank=True)
    
    # Recursos adicionales
    resources = models.JSONField(default=dict, blank=True)
    
    # Video representativo del módulo
    video_data = models.JSONField(default=dict, blank=True)  # Información del video principal
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"
        unique_together = ['course', 'module_order']
        ordering = ['module_order']
        indexes = [
            models.Index(fields=['course', 'module_order']),
            models.Index(fields=['module_id']),
        ]

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Chunk(models.Model):
    """Chunk de contenido dentro de un módulo"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='chunks')
    
    # Identificadores
    chunk_id = models.CharField(max_length=100)  # "modulo_1_chunk_1"
    chunk_order = models.PositiveIntegerField()
    total_chunks = models.PositiveIntegerField(default=6)
    
    # Contenido
    title = models.CharField(max_length=300, blank=True)  # Título descriptivo del chunk
    content = models.TextField()  # Contenido markdown/texto del chunk
    checksum = models.CharField(max_length=32, blank=True)  # MD5 hash para verificación
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chunk"
        verbose_name_plural = "Chunks"
        unique_together = ['module', 'chunk_order']
        ordering = ['chunk_order']

    def __str__(self):
        return f"{self.module.title} - Chunk {self.chunk_order}"


class Video(models.Model):
    """Video de YouTube asociado a un chunk"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chunk = models.OneToOneField(Chunk, on_delete=models.CASCADE, related_name='video')
    
    # Información del video de YouTube
    video_id = models.CharField(max_length=50)  # YouTube video ID
    title = models.CharField(max_length=300)
    url = models.URLField()  # URL completa
    embed_url = models.URLField()  # URL para embed
    thumbnail_url = models.URLField()
    duration = models.CharField(max_length=20)  # "12:34"
    view_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videos"

    def __str__(self):
        return f"{self.chunk.module.title} - {self.title}"


class Quiz(models.Model):
    """Quiz asociado a un módulo"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='quizzes')
    
    # Pregunta del quiz
    question = models.TextField()
    options = models.JSONField(default=list)  # Lista de opciones
    correct_answer = models.PositiveIntegerField()  # Índice de la respuesta correcta
    explanation = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return f"{self.module.title} - Quiz"


class UserProgress(models.Model):
    """Progreso del usuario en un curso"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    
    # Progreso
    current_module = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True)
    current_chunk = models.ForeignKey(Chunk, on_delete=models.SET_NULL, null=True, blank=True)
    completed_chunks = models.JSONField(default=list)  # Lista de IDs de chunks completados
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Progreso del Usuario"
        verbose_name_plural = "Progresos de Usuarios"
        unique_together = ['user', 'course']
        indexes = [
            models.Index(fields=['user', 'course']),
            models.Index(fields=['course']),
            models.Index(fields=['last_accessed']),
        ]

    def __str__(self):
        return f"{self.user} - {self.course.title if self.course.title else self.course.course_id}"

    def get_completion_percentage(self):
        """Calcula el porcentaje de completado"""
        total_chunks = sum(module.chunks.count() for module in self.course.modules.all())
        if total_chunks == 0:
            return 0
        return (len(self.completed_chunks) / total_chunks) * 100


class GenerationLog(models.Model):
    """Log de generación para debugging y métricas"""
    
    class ActionChoices(models.TextChoices):
        METADATA_GENERATION = 'metadata_generation', 'Generación de Metadata'
        MODULE_GENERATION = 'module_generation', 'Generación de Módulo'
        AUDIO_GENERATION = 'audio_generation', 'Generación de Audio'
        VIDEO_SEARCH = 'video_search', 'Búsqueda de Videos'
        COMPLETION = 'completion', 'Finalización'
        ERROR = 'error', 'Error'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='logs')
    
    # Información del log
    action = models.CharField(max_length=30, choices=ActionChoices.choices)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de Generación"
        verbose_name_plural = "Logs de Generación"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course.course_id} - {self.action} - {self.created_at}"
