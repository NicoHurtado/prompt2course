from rest_framework import serializers
from courses.models import Course, Module, Chunk, Video, Quiz, UserProgress, GenerationLog


class VideoSerializer(serializers.ModelSerializer):
    """Serializer para videos de YouTube"""
    
    class Meta:
        model = Video
        fields = [
            'video_id', 'title', 'url', 'embed_url', 
            'thumbnail_url', 'duration', 'view_count'
        ]


class ChunkSerializer(serializers.ModelSerializer):
    """Serializer para chunks de contenido"""
    video = VideoSerializer(read_only=True)
    
    class Meta:
        model = Chunk
        fields = [
            'chunk_id', 'chunk_order', 'total_chunks', 
            'content', 'checksum', 'video'
        ]


class QuizSerializer(serializers.ModelSerializer):
    """Serializer para quizzes de módulos"""
    
    class Meta:
        model = Quiz
        fields = ['question', 'options', 'correct_answer', 'explanation']


class ModuleSerializer(serializers.ModelSerializer):
    """Serializer para módulos del curso"""
    chunks = ChunkSerializer(many=True, read_only=True)
    quizzes = QuizSerializer(many=True, read_only=True)
    
    class Meta:
        model = Module
        fields = [
            'module_id', 'title', 'description', 'objective', 
            'concepts', 'summary', 'practical_exercise', 
            'resources', 'chunks', 'quizzes', 'module_order'
        ]


class CourseCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear nuevos cursos"""
    
    class Meta:
        model = Course
        fields = ['user_prompt', 'user_level', 'user_interests']
        
    def validate_user_prompt(self, value):
        """Validar que el prompt tenga contenido suficiente"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "El prompt debe tener al menos 10 caracteres"
            )
        return value.strip()
    
    def validate_user_interests(self, value):
        """Validar lista de intereses"""
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "Los intereses deben ser una lista"
            )
        if len(value) > 10:
            raise serializers.ValidationError(
                "Máximo 10 intereses permitidos"
            )
        return value


class CourseStatusSerializer(serializers.ModelSerializer):
    """Serializer para estado del curso (polling)"""
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'status', 'title', 'progress_percentage']
    
    def get_progress_percentage(self, obj):
        return obj.get_progress_percentage()


class CourseMetadataSerializer(serializers.ModelSerializer):
    """Serializer para metadata del curso (Fase 1 completa)"""
    
    class Meta:
        model = Course
        fields = [
            'id', 'course_id', 'title', 'description', 'level', 
            'prerequisites', 'total_modules', 'module_list', 'topics',
            'podcast_script', 'podcast_audio_url', 'introduction',
            'total_size_estimate', 'status', 'created_at'
        ]


class CourseDetailSerializer(serializers.ModelSerializer):
    """Serializer completo del curso con todos los módulos"""
    modules = ModuleSerializer(many=True, read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'course_id', 'title', 'description', 'user_level',
            'prerequisites', 'total_modules', 'module_list', 'topics',
            'podcast_script', 'podcast_audio_url', 'introduction',
            'final_project_data', 'modules', 'status', 'progress_percentage',
            'created_at', 'updated_at', 'completed_at'
        ]
    
    def get_progress_percentage(self, obj):
        return obj.get_progress_percentage()


class CourseListSerializer(serializers.ModelSerializer):
    """Serializer para lista de cursos"""
    progress_percentage = serializers.SerializerMethodField()
    modules_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'course_id', 'title', 'description', 'user_level',
            'status', 'progress_percentage', 'modules_count', 
            'created_at', 'updated_at'
        ]
    
    def get_progress_percentage(self, obj):
        return obj.get_progress_percentage()
    
    def get_modules_count(self, obj):
        return obj.modules.count()


class UserProgressSerializer(serializers.ModelSerializer):
    """Serializer para progreso del usuario"""
    completion_percentage = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='course.title', read_only=True)
    current_module_title = serializers.CharField(source='current_module.title', read_only=True)
    
    class Meta:
        model = UserProgress
        fields = [
            'course', 'course_title', 'current_module', 'current_module_title',
            'current_chunk', 'completed_chunks', 'completion_percentage',
            'started_at', 'last_accessed', 'completed_at'
        ]
    
    def get_completion_percentage(self, obj):
        return obj.get_completion_percentage()


class MarkChunkCompleteSerializer(serializers.Serializer):
    """Serializer para marcar chunks como completados"""
    chunk_id = serializers.CharField(max_length=100)
    
    def validate_chunk_id(self, value):
        """Validar que el chunk existe"""
        try:
            chunk = Chunk.objects.get(chunk_id=value)
            return value
        except Chunk.DoesNotExist:
            raise serializers.ValidationError("Chunk no encontrado")


class GenerationLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de generación"""
    
    class Meta:
        model = GenerationLog
        fields = [
            'action', 'message', 'duration_seconds', 
            'details', 'created_at'
        ]


class CourseWithLogsSerializer(CourseDetailSerializer):
    """Serializer de curso con logs para debugging"""
    logs = GenerationLogSerializer(many=True, read_only=True)
    
    class Meta(CourseDetailSerializer.Meta):
        fields = CourseDetailSerializer.Meta.fields + ['logs']


class ModuleDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para un módulo específico"""
    chunks = ChunkSerializer(many=True, read_only=True)
    quizzes = QuizSerializer(many=True, read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Module
        fields = [
            'module_id', 'title', 'description', 'objective', 
            'concepts', 'summary', 'practical_exercise', 
            'resources', 'chunks', 'quizzes', 'module_order',
            'course_title', 'created_at', 'updated_at'
        ]


class NextModuleSerializer(serializers.Serializer):
    """Serializer para navegación de módulos"""
    current_module_order = serializers.IntegerField()
    direction = serializers.ChoiceField(choices=['next', 'previous'])
    
    def validate(self, data):
        """Validar que el módulo existe"""
        course_id = self.context.get('course_id')
        current_order = data['current_module_order']
        direction = data['direction']
        
        if direction == 'next':
            target_order = current_order + 1
        else:
            target_order = current_order - 1
        
        try:
            course = Course.objects.get(id=course_id)
            module = course.modules.get(module_order=target_order)
            data['target_module'] = module
        except (Course.DoesNotExist, Module.DoesNotExist):
            raise serializers.ValidationError("Módulo no encontrado")
        
        return data 