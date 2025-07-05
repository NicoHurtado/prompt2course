from django.shortcuts import render
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone

from courses.models import Course, Module, Chunk, UserProgress
from generation.tasks import generate_course_metadata, generate_remaining_modules
from .serializers import (
    CourseCreateSerializer, CourseDetailSerializer, CourseListSerializer,
    CourseStatusSerializer, CourseMetadataSerializer, ModuleSerializer,
    ModuleDetailSerializer, UserProgressSerializer, MarkChunkCompleteSerializer,
    NextModuleSerializer, CourseWithLogsSerializer
)

logger = logging.getLogger(__name__)


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet principal para gestión de cursos del sistema P2C
    
    Endpoints disponibles:
    - POST /api/courses/ - Crear nuevo curso (Fase 1)
    - GET /api/courses/{id}/ - Obtener curso completo
    - GET /api/courses/{id}/status/ - Monitorear estado de generación
    - POST /api/courses/{id}/start_course/ - Iniciar curso (Fase 3)
    - POST /api/courses/{id}/next_module/ - Navegar módulos
    - GET /api/courses/{id}/metadata/ - Obtener solo metadata
    """
    
    queryset = Course.objects.all()
    permission_classes = [AllowAny]  # Para MVP, sin autenticación
    
    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == 'create':
            return CourseCreateSerializer
        elif self.action == 'list':
            return CourseListSerializer
        elif self.action == 'status':
            return CourseStatusSerializer
        elif self.action == 'metadata':
            return CourseMetadataSerializer
        elif self.action == 'logs':
            return CourseWithLogsSerializer
        else:
            return CourseDetailSerializer
    
    def create(self, request):
        """
        Crear nuevo curso e iniciar Fase 1 (generación de metadata)
        
        POST /api/courses/
        {
            "user_prompt": "quiero aprender Machine learning para analizar datos deportivos",
            "user_level": "principiante",
            "user_interests": ["Deportes", "Tecnología"]
        }
        
        Respuesta inmediata:
        {
            "id": "course-uuid-123",
            "status": "generating_metadata",
            "title": null
        }
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Crear curso con status inicial
            course = Course.objects.create(
                user_prompt=serializer.validated_data['user_prompt'],
                user_level=serializer.validated_data['user_level'],
                user_interests=serializer.validated_data.get('user_interests', []),
                status=Course.StatusChoices.GENERATING_METADATA,
                language='es'  # Por defecto español
            )
            
            logger.info(f"Curso creado: {course.id}")
            
            # Iniciar tarea asíncrona de generación de metadata (Fase 1)
            generate_course_metadata.delay(str(course.id))
            
            # Respuesta inmediata con datos básicos
            response_data = {
                'id': str(course.id),
                'status': course.status,
                'title': course.title or None,
                'message': 'Curso creado exitosamente. Generando metadata...'
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creando curso: {e}")
            return Response(
                {'error': 'Error interno del servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """
        Obtener curso completo con todos los módulos generados
        
        GET /api/courses/{id}/
        """
        try:
            course = get_object_or_404(Course, pk=pk)
            serializer = self.get_serializer(course)
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error obteniendo curso {pk}: {e}")
            return Response(
                {'error': 'Error obteniendo curso'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Monitorear estado de generación del curso (para polling)
        
        GET /api/courses/{id}/status/
        
        Posibles respuestas:
        {"status": "generating_metadata"}  - Fase 1 en progreso
        {"status": "metadata_ready"}       - Metadata lista, generando módulo 1
        {"status": "ready"}               - Listo para consumir (metadata + módulo 1)
        {"status": "complete"}           - Curso completo
        {"status": "failed"}             - Error en generación
        """
        try:
            course = get_object_or_404(Course, pk=pk)
            serializer = CourseStatusSerializer(course)
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error obteniendo status del curso {pk}: {e}")
            return Response(
                {'error': 'Error obteniendo status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def metadata(self, request, pk=None):
        """
        Obtener solo la metadata del curso (Fase 1 completa)
        
        GET /api/courses/{id}/metadata/
        """
        try:
            course = get_object_or_404(Course, pk=pk)
            
            # Verificar que la metadata esté lista
            if course.status not in [Course.StatusChoices.METADATA_READY, 
                                   Course.StatusChoices.READY, 
                                   Course.StatusChoices.COMPLETE]:
                return Response(
                    {'error': 'Metadata aún no está lista'},
                    status=status.HTTP_202_ACCEPTED
                )
            
            serializer = CourseMetadataSerializer(course)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error obteniendo metadata del curso {pk}: {e}")
            return Response(
                {'error': 'Error obteniendo metadata'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def start_course(self, request, pk=None):
        """
        Iniciar curso (Fase 3 - generar módulos restantes)
        
        POST /api/courses/{id}/start_course/
        
        Inicia la generación de módulos 2, 3, 4... en background.
        """
        try:
            course = get_object_or_404(Course, pk=pk)
            
            # Verificar que el curso esté listo para iniciar
            if course.status != Course.StatusChoices.READY:
                return Response(
                    {'error': f'Curso no está listo para iniciar. Status actual: {course.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Iniciar generación de módulos restantes
            generate_remaining_modules.delay(str(course.id))
            
            logger.info(f"Iniciado curso {course.id} - generando módulos restantes")
            
            return Response({
                'message': 'Curso iniciado exitosamente. Generando módulos restantes...',
                'status': 'generating_remaining'
            })
            
        except Exception as e:
            logger.error(f"Error iniciando curso {pk}: {e}")
            return Response(
                {'error': 'Error iniciando curso'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

    @action(detail=True, methods=['post'])
    def next_module(self, request, pk=None):
        """
        Navegar al siguiente módulo del curso
        
        POST /api/courses/{id}/next_module/
        {
            "current_module_order": 1,
            "direction": "next"  // o "previous"
        }
        """
        try:
            course = get_object_or_404(Course, pk=pk)
            
            serializer = NextModuleSerializer(
                data=request.data, 
                context={'course_id': pk}
            )
            serializer.is_valid(raise_exception=True)
            
            target_module = serializer.validated_data['target_module']
            module_serializer = ModuleDetailSerializer(target_module)
            
            return Response(module_serializer.data)
            
        except Exception as e:
            logger.error(f"Error navegando módulos del curso {pk}: {e}")
            return Response(
                {'error': 'Error navegando módulos'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def previous_module(self, request, pk=None):
        """
        Navegar al módulo anterior del curso
        
        POST /api/courses/{id}/previous_module/
        {
            "current_module_order": 2
        }
        """
        try:
            course = get_object_or_404(Course, pk=pk)
            current_order = request.data.get('current_module_order', 1)
            
            if current_order <= 1:
                return Response(
                    {'error': 'Ya estás en el primer módulo'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            previous_module = get_object_or_404(
                course.modules, 
                module_order=current_order - 1
            )
            
            serializer = ModuleDetailSerializer(previous_module)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error navegando al módulo anterior: {e}")
            return Response(
                {'error': 'Error navegando al módulo anterior'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """
        Obtener logs de generación para debugging (solo desarrollo)
        
        GET /api/courses/{id}/logs/
        """
        try:
            course = get_object_or_404(Course, pk=pk)
            serializer = CourseWithLogsSerializer(course)
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error obteniendo logs del curso {pk}: {e}")
            return Response(
                {'error': 'Error obteniendo logs'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModuleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para acceso a módulos individuales
    
    Endpoints:
    - GET /api/modules/{id}/ - Obtener módulo específico
    """
    
    queryset = Module.objects.all()
    serializer_class = ModuleDetailSerializer
    permission_classes = [AllowAny]
    
    def retrieve(self, request, pk=None):
        """
        Obtener módulo específico con todo su contenido
        
        GET /api/modules/{id}/
        """
        try:
            module = get_object_or_404(Module, pk=pk)
            serializer = self.get_serializer(module)
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error obteniendo módulo {pk}: {e}")
            return Response(
                {'error': 'Error obteniendo módulo'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProgressViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión del progreso del usuario
    
    Endpoints:
    - GET /api/progress/ - Obtener progreso de todos los cursos
    - GET /api/progress/{course_id}/ - Obtener progreso de curso específico
    - POST /api/progress/{course_id}/mark_chunk_complete/ - Marcar chunk como completado
    """
    
    queryset = UserProgress.objects.all()
    serializer_class = UserProgressSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filtrar por usuario si está autenticado"""
        queryset = UserProgress.objects.all()
        
        # TODO: Filtrar por usuario cuando se implemente autenticación
        # if self.request.user.is_authenticated:
        #     queryset = queryset.filter(user=self.request.user)
        
        return queryset
    
    @action(detail=True, methods=['post'], url_path='mark_chunk_complete')
    def mark_chunk_complete(self, request, pk=None):
        """
        Marcar un chunk como completado
        
        POST /api/progress/{course_id}/mark_chunk_complete/
        {
            "chunk_id": "modulo_1_chunk_1"
        }
        """
        try:
            course = get_object_or_404(Course, pk=pk)
            
            serializer = MarkChunkCompleteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            chunk_id = serializer.validated_data['chunk_id']
            chunk = get_object_or_404(Chunk, chunk_id=chunk_id)
            
            # Obtener o crear progreso del usuario
            # TODO: Usar usuario real cuando se implemente autenticación
            progress, created = UserProgress.objects.get_or_create(
                course=course,
                user=None,  # Temporal
                defaults={
                    'current_module': chunk.module,
                    'current_chunk': chunk
                }
            )
            
            # Agregar chunk a completados si no está ya
            if chunk_id not in progress.completed_chunks:
                progress.completed_chunks.append(chunk_id)
                progress.current_chunk = chunk
                progress.current_module = chunk.module
                progress.last_accessed = timezone.now()
                progress.save()
            
            # Verificar si el curso está completo
            total_chunks = sum(
                module.chunks.count() 
                for module in course.modules.all()
            )
            
            if len(progress.completed_chunks) >= total_chunks:
                progress.completed_at = timezone.now()
                progress.save()
            
            response_serializer = UserProgressSerializer(progress)
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"Error marcando chunk como completado: {e}")
            return Response(
                {'error': 'Error marcando chunk como completado'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
