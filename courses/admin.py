from django.contrib import admin
from .models import Course, Module, Chunk, Video, Quiz, UserProgress, GenerationLog


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'course_id', 'status', 'user_level', 'created_at', 'get_progress_percentage']
    list_filter = ['status', 'user_level', 'created_at']
    search_fields = ['title', 'course_id', 'user_prompt']
    readonly_fields = ['id', 'course_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'course_id', 'status', 'user_prompt', 'user_level', 'user_interests')
        }),
        ('Metadatos del Curso', {
            'fields': ('title', 'description', 'prerequisites', 'total_modules', 'module_list', 'topics')
        }),
        ('Contenido Multimedia', {
            'fields': ('podcast_script', 'podcast_audio_url', 'introduction')
        }),
        ('Proyecto Final', {
            'fields': ('final_project_data',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'module_order', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'course', 'module_id', 'module_order')
        }),
        ('Contenido', {
            'fields': ('title', 'description', 'objective', 'concepts', 'summary')
        }),
        ('Ejercicios y Recursos', {
            'fields': ('practical_exercise', 'resources')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'chunk_order', 'total_chunks', 'created_at']
    list_filter = ['module__course', 'created_at']
    search_fields = ['content']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'video_id', 'duration', 'view_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'video_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'question', 'correct_answer', 'created_at']
    list_filter = ['module__course', 'created_at']
    search_fields = ['question']
    readonly_fields = ['id', 'created_at']


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'get_completion_percentage', 'started_at', 'last_accessed']
    list_filter = ['course', 'started_at', 'completed_at']
    search_fields = ['user__username', 'course__title']
    readonly_fields = ['id', 'started_at', 'last_accessed']


@admin.register(GenerationLog)
class GenerationLogAdmin(admin.ModelAdmin):
    list_display = ['course', 'action', 'message', 'duration_seconds', 'created_at']
    list_filter = ['action', 'created_at', 'course']
    search_fields = ['message', 'course__course_id']
    readonly_fields = ['id', 'created_at']
    
    def has_add_permission(self, request):
        return False  # Solo lectura, los logs se crean automáticamente
