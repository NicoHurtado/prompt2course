import asyncio
import json
import time
import logging
from typing import Dict, Any
from celery import shared_task
from django.utils import timezone

from courses.models import Course, Module, Chunk, Video, Quiz, GenerationLog
from .services.anthropic_service import anthropic_service
from .services.polly_service import polly_service
from .services.youtube_service import youtube_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# EmojiLogFilter: añade emojis según el contenido del mensaje para identificar
# rápidamente el estado en la consola (✅, 🚀, ⚙️, 🎬, ❌, ℹ️)
# ---------------------------------------------------------------------------


class EmojiLogFilter(logging.Filter):
    """Filtro de logging que antepone un emoji basado en palabras clave."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        msg = record.getMessage()

        # Determinar emoji por palabras clave
        if any(keyword in msg.lower() for keyword in ["error", "failed", "falla"]):
            emoji = "❌"
        elif "video" in msg.lower():
            emoji = "🎬"
        elif any(keyword in msg.lower() for keyword in ["generando", "iniciando", "activando"]):
            emoji = "🚀"
        elif any(keyword in msg.lower() for keyword in ["exitosamente", "generada", "generado"]):
            emoji = "✅"
        else:
            emoji = "ℹ️"

        # Anteponer emoji si no existe ya
        if not msg.strip().startswith(emoji):
            record.msg = f"{emoji} {msg}"

        return True


# Adjuntar filtro una sola vez para evitar duplicados si el módulo se recarga
if not any(isinstance(f, EmojiLogFilter) for f in logger.filters):
    logger.addFilter(EmojiLogFilter())


@shared_task(bind=True)
def generate_course_metadata(self, course_id: str):
    """
    Fase 1: Generar metadata completa del curso usando Claude AI
    
    Esta fase genera toda la estructura del curso, incluyendo:
    - Título y descripción
    - Lista de módulos
    - Temas principales
    - Script del podcast
    - Audio del podcast
    """
    start_time = time.time()
    course = None
    
    try:
        logger.info(f"Iniciando generación de metadata para curso {course_id}")
        
        course = Course.objects.get(id=course_id)
        course.status = Course.StatusChoices.GENERATING_METADATA
        course.save()
        
        # Log de inicio
        GenerationLog.objects.create(
            course=course,
            action=GenerationLog.ActionChoices.METADATA_GENERATION,
            message="Iniciando generación de metadata"
        )
        
        # Ejecutar generación asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            metadata = loop.run_until_complete(
                anthropic_service.create_course_metadata(
                    prompt=course.user_prompt,
                    level=course.user_level,
                    interests=course.user_interests,
                    language=course.language
                )
            )
            
            # Validar estructura
            if not anthropic_service.validate_course_structure(metadata):
                raise ValueError("Estructura de metadata inválida")
            
            # Actualizar curso con metadata
            course.title = metadata.get('title', '')
            course.description = metadata.get('description', '')
            course.prerequisites = metadata.get('prerequisites', [])
            course.total_modules = metadata.get('total_modules', 4)
            course.module_list = metadata.get('module_list', [])
            course.topics = metadata.get('topics', [])
            course.podcast_script = metadata.get('podcast_script', '')
            course.total_size_estimate = metadata.get('total_size', '~300KB contenido interactivo')
            
            # Generar audio del podcast si hay script
            if course.podcast_script:
                try:
                    podcast_result = loop.run_until_complete(
                        polly_service.generate_podcast_audio(
                            course.podcast_script,
                            str(course_id)
                        )
                    )
                    course.podcast_audio_url = podcast_result.get('main_audio_url', '')
                    
                    GenerationLog.objects.create(
                        course=course,
                        action=GenerationLog.ActionChoices.AUDIO_GENERATION,
                        message="Podcast generado exitosamente",
                        details={'duration': podcast_result.get('total_duration', 0)}
                    )
                    
                except Exception as audio_error:
                    logger.error(f"Error generando audio del podcast: {audio_error}")
                    # Continuar sin audio si falla
            
            course.status = Course.StatusChoices.METADATA_READY
            course.save()
            
            duration = time.time() - start_time
            GenerationLog.objects.create(
                course=course,
                action=GenerationLog.ActionChoices.METADATA_GENERATION,
                message="Metadata generada exitosamente",
                duration_seconds=duration,
                details=metadata
            )
            
            logger.info(f"Metadata generada exitosamente para curso {course_id} en {duration:.2f}s")
            
            # Activar inmediatamente la generación del módulo 1 en background
            generate_module_1.delay(str(course_id))
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error en generación de metadata para curso {course_id}: {e}")
        
        if course:
            course.status = Course.StatusChoices.FAILED
            course.save()
            
            GenerationLog.objects.create(
                course=course,
                action=GenerationLog.ActionChoices.ERROR,
                message=f"Error en generación de metadata: {str(e)}",
                duration_seconds=time.time() - start_time
            )
        
        raise


@shared_task(bind=True)
def generate_modules_metadata(self, course_id: str):
    """
    Fase 1.5: Generar metadata de todos los módulos (sin contenido completo)
    
    Esta fase genera la metadata básica de todos los módulos para que el usuario
    pueda ver la estructura completa del curso antes de que se genere el contenido.
    """
    start_time = time.time()
    course = None
    
    try:
        logger.info(f"Iniciando generación de metadata de módulos para curso {course_id}")
        
        course = Course.objects.get(id=course_id)
        course.status = Course.StatusChoices.GENERATING_MODULES_METADATA
        course.save()
        
        GenerationLog.objects.create(
            course=course,
            action=GenerationLog.ActionChoices.MODULE_GENERATION,
            message="Iniciando generación de metadata de módulos"
        )
        
        # Preparar metadata del curso
        course_metadata = {
            'title': course.title,
            'description': course.description,
            'level': course.user_level,
            'module_list': course.module_list,
            'topics': course.topics,
            'total_modules': course.total_modules
        }
        
        # Ejecutar generación asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            modules_created = 0
            
            # Generar metadata para todos los módulos
            for module_number in range(1, course.total_modules + 1):
                # No crear si ya existe
                if Module.objects.filter(course=course, module_order=module_number).exists():
                    continue
                
                try:
                    logger.info(f"Generando metadata del módulo {module_number}")
                    
                    # Generar solo metadata del módulo (sin chunks)
                    module_metadata = loop.run_until_complete(
                        anthropic_service.create_module_metadata(course_metadata, module_number)
                    )
                    
                    # Crear módulo en la base de datos con solo metadata
                    Module.objects.create(
                        course=course,
                        module_id=module_metadata.get('module_id', f'modulo_{module_number}'),
                        module_order=module_number,
                        title=module_metadata.get('title', ''),
                        description=module_metadata.get('description', ''),
                        objective=module_metadata.get('objective', ''),
                        concepts=module_metadata.get('concepts', []),
                        summary=module_metadata.get('summary', ''),
                        practical_exercise=module_metadata.get('practical_exercise', {}),
                        resources=module_metadata.get('resources', {})
                    )
                    
                    modules_created += 1
                    logger.info(f"Metadata del módulo {module_number} generada exitosamente")
                    
                except Exception as module_error:
                    logger.error(f"Error generando metadata del módulo {module_number}: {module_error}")
                    # Continuar con siguiente módulo
            
            course.status = Course.StatusChoices.METADATA_READY
            course.save()
            
            duration = time.time() - start_time
            GenerationLog.objects.create(
                course=course,
                action=GenerationLog.ActionChoices.MODULE_GENERATION,
                message=f"Metadata de {modules_created} módulos generada exitosamente",
                duration_seconds=duration,
                details={'modules_created': modules_created, 'total_modules': course.total_modules}
            )
            
            logger.info(f"Metadata de módulos generada exitosamente para curso {course_id} en {duration:.2f}s")
            
            # Activar inmediatamente la generación del contenido del módulo 1
            generate_module_1.delay(str(course_id))
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error en generación de metadata de módulos para curso {course_id}: {e}")
        
        if course:
            course.status = Course.StatusChoices.FAILED
            course.save()
            
            GenerationLog.objects.create(
                course=course,
                action=GenerationLog.ActionChoices.ERROR,
                message=f"Error en generación de metadata de módulos: {str(e)}",
                duration_seconds=time.time() - start_time
            )
        
        raise


@shared_task(bind=True)
def generate_module_1(self, course_id: str):
    """
    Fase 2: Generar únicamente el contenido completo del módulo 1
    
    Esta fase genera el primer módulo completo con contenido y videos
    para que el usuario pueda empezar a consumir el curso.
    
    Al completarse, activa automáticamente la generación de módulos restantes
    para que el usuario pueda leer el módulo 1 mientras se generan los demás.
    """
    start_time = time.time()
    course = None
    
    try:
        logger.info(f"Iniciando generación de contenido del módulo 1 para curso {course_id}")
        
        course = Course.objects.get(id=course_id)
        course.status = Course.StatusChoices.GENERATING_MODULE_1
        course.save()
        
        GenerationLog.objects.create(
            course=course,
            action=GenerationLog.ActionChoices.MODULE_GENERATION,
            message="Iniciando generación de contenido del módulo 1"
        )
        
        # Preparar metadata del curso
        course_metadata = {
            'title': course.title,
            'description': course.description,
            'level': course.user_level,
            'module_list': course.module_list,
            'topics': course.topics
        }
        
        # Crear metadata básica para todos los módulos si no existen
        for module_number in range(1, course.total_modules + 1):
            if not Module.objects.filter(course=course, module_order=module_number).exists():
                Module.objects.create(
                    course=course,
                    module_id=f'modulo_{module_number}',
                    module_order=module_number,
                    title=course.module_list[module_number - 1] if len(course.module_list) >= module_number else f'Módulo {module_number}',
                    description=f'Descripción del módulo {module_number}',
                    objective=f'Objetivo del módulo {module_number}'
                )
        
        # Obtener el módulo 1 (ahora garantizamos que existe)
        module = Module.objects.get(course=course, module_order=1)
        
        # Ejecutar generación asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Generar contenido completo del módulo 1
            module_data = loop.run_until_complete(
                anthropic_service.create_module_content(course_metadata, 1)
            )
            
            # Validar estructura del módulo
            if not anthropic_service.validate_module_structure(module_data):
                raise ValueError("Estructura de módulo inválida")
            
            # Actualizar módulo con contenido completo
            module.title = module_data.get('title', module.title)
            module.description = module_data.get('description', module.description)
            module.objective = module_data.get('objective', module.objective)
            module.concepts = module_data.get('concepts', [])
            module.summary = module_data.get('summary', '')
            module.practical_exercise = module_data.get('practical_exercise', {})
            module.resources = module_data.get('resources', {})
            module.save()
            
            # Crear chunks del módulo
            chunks_data = module_data.get('chunks', [])
            first_video_for_module = None  # Para guardar el primer video en module.video_data
            used_video_ids = set()  # Para el módulo 1, empezamos sin videos usados
            
            for chunk_data in chunks_data:
                chunk = Chunk.objects.create(
                    module=module,
                    chunk_id=chunk_data.get('chunk_id', ''),
                    chunk_order=chunk_data.get('chunk_order', 1),
                    total_chunks=chunk_data.get('total_chunks', 6),
                    content=chunk_data.get('content', ''),
                    checksum=chunk_data.get('checksum', ''),
                    title=chunk_data.get('title', '')  # Campo disponible
                )
                
                # Buscar y asignar video para este chunk
                try:
                    videos = loop.run_until_complete(
                        youtube_service.search_videos_for_chunk(chunk_data, course_metadata)
                    )
                    
                    # Para módulo 1, seleccionar videos únicos dentro del mismo módulo
                    unique_video = None
                    for video_candidate in videos:
                        candidate_id = video_candidate.get('video_id', '')
                        if candidate_id and candidate_id not in used_video_ids:
                            unique_video = video_candidate
                            used_video_ids.add(candidate_id)  # Agregar a usados
                            break
                    
                    if unique_video:
                        Video.objects.create(
                            chunk=chunk,
                            video_id=unique_video.get('video_id', ''),
                            title=unique_video.get('title', ''),
                            url=unique_video.get('url', ''),
                            embed_url=unique_video.get('embed_url', ''),
                            thumbnail_url=unique_video.get('thumbnail_url', ''),
                            duration=unique_video.get('duration', 'N/A'),
                            view_count=unique_video.get('view_count', 0)
                        )
                        
                        # Guardar el primer video único encontrado para el módulo
                        if first_video_for_module is None:
                            first_video_for_module = unique_video
                            logger.info(f"Video único asignado al módulo 1: {unique_video.get('title', 'Sin título')}")
                    else:
                        logger.warning(f"No se encontraron videos únicos para chunk {chunk.chunk_id} en módulo 1")
                        
                except Exception as video_error:
                    logger.warning(f"Error buscando video para chunk {chunk.chunk_id}: {video_error}")
                    # Continuar sin video si falla la búsqueda
            
            # Asignar el primer video único encontrado al campo video_data del módulo
            if first_video_for_module:
                module.video_data = first_video_for_module
                module.save()
                logger.info(f"Video principal único asignado al módulo 1: {first_video_for_module.get('title', 'Sin título')}")
            else:
                logger.warning("No se pudo asignar video principal único al módulo 1")
            
            # Crear quiz del módulo
            quiz_data = module_data.get('quiz', [])
            for question_data in quiz_data:
                Quiz.objects.create(
                    module=module,
                    question=question_data.get('question', ''),
                    options=question_data.get('options', []),
                    correct_answer=question_data.get('correct_answer', 0),
                    explanation=question_data.get('explanation', '')
                )
            
            course.status = Course.StatusChoices.READY
            course.save()
            
            duration = time.time() - start_time
            GenerationLog.objects.create(
                course=course,
                action=GenerationLog.ActionChoices.MODULE_GENERATION,
                message="Contenido del módulo 1 generado exitosamente",
                duration_seconds=duration,
                details={'module_id': module.module_id, 'chunks_count': len(chunks_data)}
            )
            
            logger.info(f"Contenido del módulo 1 generado exitosamente para curso {course_id} en {duration:.2f}s")
            
            # Activar automáticamente la generación de módulos restantes
            # El usuario ya puede acceder al módulo 1 mientras se generan los demás
            if course.total_modules > 1:
                logger.info(f"Activando generación automática de módulos restantes para curso {course_id}")
                generate_remaining_modules.delay(str(course_id))
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error en generación de contenido del módulo 1 para curso {course_id}: {e}")
        
        if course:
            course.status = Course.StatusChoices.FAILED
            course.save()
            
            GenerationLog.objects.create(
                course=course,
                action=GenerationLog.ActionChoices.ERROR,
                message=f"Error en generación de contenido del módulo 1: {str(e)}",
                duration_seconds=time.time() - start_time
            )
        
        raise


@shared_task(bind=True)
def generate_remaining_modules(self, course_id: str):
    """
    Fase 3: Generar módulos restantes (2, 3, 4...) en background
    
    Esta fase se ejecuta cuando el usuario decide iniciar el curso,
    generando todos los módulos restantes en paralelo.
    """
    start_time = time.time()
    course = None
    
    try:
        logger.info(f"Iniciando generación de módulos restantes para curso {course_id}")
        
        course = Course.objects.get(id=course_id)
        course.status = Course.StatusChoices.GENERATING_REMAINING
        course.save()
        
        GenerationLog.objects.create(
            course=course,
            action=GenerationLog.ActionChoices.MODULE_GENERATION,
            message="Iniciando generación de módulos restantes"
        )
        
        # Preparar metadata del curso
        course_metadata = {
            'title': course.title,
            'description': course.description,
            'level': course.user_level,
            'module_list': course.module_list,
            'topics': course.topics
        }
        
        modules_generated = 0
        total_modules = course.total_modules
        
        # Ejecutar generación asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Generar módulos 2, 3, 4...
            for module_number in range(2, total_modules + 1):
                # Verificar si el módulo ya tiene contenido COMPLETO
                existing_module = Module.objects.filter(course=course, module_order=module_number).first()
                if existing_module and existing_module.chunks.count() > 0:
                    logger.info(f"Módulo {module_number} ya tiene contenido completo, saltando")
                    continue  # Skip solo si ya tiene chunks completos
                
                # Si existe pero sin chunks, lo vamos a actualizar con contenido
                if existing_module and existing_module.chunks.count() == 0:
                    logger.info(f"Módulo {module_number} existe pero sin contenido, generando contenido...")
                
                try:
                    logger.info(f"Generando módulo {module_number}")
                    
                    module_data = loop.run_until_complete(
                        anthropic_service.create_module_content(course_metadata, module_number)
                    )
                    
                    logger.info(f"Módulo {module_number} generado exitosamente")
                    
                    # Usar módulo existente o crear nuevo
                    if existing_module:
                        module = existing_module
                        # Actualizar módulo existente
                        module.title = module_data.get('title', module.title)
                        module.description = module_data.get('description', module.description)
                        module.objective = module_data.get('objective', module.objective)
                        module.concepts = module_data.get('concepts', [])
                        module.summary = module_data.get('summary', '')
                        module.practical_exercise = module_data.get('practical_exercise', {})
                        module.resources = module_data.get('resources', {})
                        module.save()
                    else:
                        # Crear módulo nuevo
                        module = Module.objects.create(
                            course=course,
                            module_id=module_data.get('module_id', f'modulo_{module_number}'),
                            module_order=module_number,
                            title=module_data.get('title', ''),
                            description=module_data.get('description', ''),
                            objective=module_data.get('objective', ''),
                            concepts=module_data.get('concepts', []),
                            summary=module_data.get('summary', ''),
                            practical_exercise=module_data.get('practical_exercise', {}),
                            resources=module_data.get('resources', {})
                        )
                    
                    # Obtener videos ya usados en otros módulos del curso para evitar duplicados
                    used_video_ids = set()
                    for existing_mod in course.modules.exclude(id=module.id):
                        if existing_mod.video_data and 'video_id' in existing_mod.video_data:
                            used_video_ids.add(existing_mod.video_data['video_id'])
                        # También obtener videos de chunks
                        for chunk in existing_mod.chunks.all():
                            if hasattr(chunk, 'video') and chunk.video:
                                used_video_ids.add(chunk.video.video_id)
                    
                    logger.info(f"Videos ya usados en el curso: {len(used_video_ids)}")
                    
                    # Crear chunks y videos
                    chunks_data = module_data.get('chunks', [])
                    first_video_for_module = None  # Para guardar el primer video en module.video_data
                    
                    for chunk_data in chunks_data:
                        chunk = Chunk.objects.create(
                            module=module,
                            chunk_id=chunk_data.get('chunk_id', ''),
                            chunk_order=chunk_data.get('chunk_order', 1),
                            total_chunks=chunk_data.get('total_chunks', 6),
                            content=chunk_data.get('content', ''),
                            checksum=chunk_data.get('checksum', ''),
                            title=chunk_data.get('title', '')  # Campo disponible
                        )
                        
                        # Buscar videos para chunks
                        try:
                            videos = loop.run_until_complete(
                                youtube_service.search_videos_for_chunk(chunk_data, course_metadata)
                            )
                            
                            # Filtrar videos ya usados y seleccionar uno único
                            unique_video = None
                            for video_candidate in videos:
                                candidate_id = video_candidate.get('video_id', '')
                                if candidate_id and candidate_id not in used_video_ids:
                                    unique_video = video_candidate
                                    used_video_ids.add(candidate_id)  # Agregar a usados
                                    break
                            
                            if unique_video:
                                Video.objects.create(
                                    chunk=chunk,
                                    video_id=unique_video.get('video_id', ''),
                                    title=unique_video.get('title', ''),
                                    url=unique_video.get('url', ''),
                                    embed_url=unique_video.get('embed_url', ''),
                                    thumbnail_url=unique_video.get('thumbnail_url', ''),
                                    duration=unique_video.get('duration', 'N/A'),
                                    view_count=unique_video.get('view_count', 0)
                                )
                                
                                # Guardar el primer video único encontrado para el módulo
                                if first_video_for_module is None:
                                    first_video_for_module = unique_video
                                    logger.info(f"Video único asignado al módulo {module_number}: {unique_video.get('title', 'Sin título')}")
                            else:
                                logger.warning(f"No se encontraron videos únicos para chunk {chunk.chunk_id}")
                                    
                        except Exception as video_error:
                            logger.warning(f"Error buscando video para chunk {chunk.chunk_id}: {video_error}")
                    
                    # Asignar el primer video único encontrado al campo video_data del módulo
                    if first_video_for_module:
                        module.video_data = first_video_for_module
                        module.save()
                        logger.info(f"Video principal único asignado al módulo {module_number}: {first_video_for_module.get('title', 'Sin título')}")
                    else:
                        logger.warning(f"No se pudo asignar video principal único al módulo {module_number}")
                    
                    # Crear quiz
                    quiz_data = module_data.get('quiz', [])
                    for question_data in quiz_data:
                        Quiz.objects.create(
                            module=module,
                            question=question_data.get('question', ''),
                            options=question_data.get('options', []),
                            correct_answer=question_data.get('correct_answer', 0),
                            explanation=question_data.get('explanation', '')
                        )
                    
                    modules_generated += 1
                    logger.info(f"Módulo {module_number} generado exitosamente")
                    
                except Exception as module_error:
                    logger.error(f"Error generando módulo {module_number}: {module_error}")
                    # Continuar con siguiente módulo
            
            # Generar proyecto final
            try:
                all_modules_data = []
                for module in course.modules.all():
                    all_modules_data.append({
                        'title': module.title,
                        'description': module.description,
                        'concepts': module.concepts
                    })
                
                final_project = loop.run_until_complete(
                    anthropic_service.create_final_project(course_metadata, all_modules_data)
                )
                
                course.final_project_data = final_project
                
            except Exception as project_error:
                logger.error(f"Error generando proyecto final: {project_error}")
                # Continuar sin proyecto final
            
            # Marcar curso como completo
            course.status = Course.StatusChoices.COMPLETE
            course.completed_at = timezone.now()
            course.save()
            
            duration = time.time() - start_time
            GenerationLog.objects.create(
                course=course,
                action=GenerationLog.ActionChoices.COMPLETION,
                message=f"Curso completado. {modules_generated} módulos generados",
                duration_seconds=duration,
                details={'modules_generated': modules_generated, 'total_modules': total_modules}
            )
            
            logger.info(f"Módulos restantes generados exitosamente para curso {course_id} en {duration:.2f}s")
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error en generación de módulos restantes para curso {course_id}: {e}")
        
        if course:
            # No cambiar status a FAILED si algunos módulos se generaron exitosamente
            GenerationLog.objects.create(
                course=course,
                action=GenerationLog.ActionChoices.ERROR,
                message=f"Error en generación de módulos restantes: {str(e)}",
                duration_seconds=time.time() - start_time
            )
        
        raise


@shared_task(bind=True)
def regenerate_missing_modules(self, course_id: str):
    """
    Tarea para regenerar módulos faltantes o sin contenido
    
    Esta tarea identifica módulos que deberían existir pero no tienen contenido
    y los regenera para completar el curso.
    """
    start_time = time.time()
    course = None
    
    try:
        logger.info(f"Iniciando regeneración de módulos faltantes para curso {course_id}")
        
        course = Course.objects.get(id=course_id)
        
        # Verificar que hay módulos que regenerar
        missing_modules = []
        for module_number in range(1, course.total_modules + 1):
            existing_module = Module.objects.filter(course=course, module_order=module_number).first()
            if not existing_module or existing_module.chunks.count() == 0:
                missing_modules.append(module_number)
        
        if not missing_modules:
            logger.info(f"No hay módulos faltantes en el curso {course_id}")
            return "No hay módulos faltantes"
        
        logger.info(f"Módulos faltantes detectados: {missing_modules}")
        
        GenerationLog.objects.create(
            course=course,
            action=GenerationLog.ActionChoices.MODULE_GENERATION,
            message=f"Iniciando regeneración de módulos faltantes: {missing_modules}"
        )
        
        # Preparar metadata del curso
        course_metadata = {
            'title': course.title,
            'description': course.description,
            'level': course.user_level,
            'module_list': course.module_list,
            'topics': course.topics
        }
        
        modules_regenerated = 0
        
        # Ejecutar generación asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Obtener videos ya usados en el curso para evitar duplicados
            used_video_ids = set()
            for existing_mod in course.modules.all():
                if existing_mod.video_data and 'video_id' in existing_mod.video_data:
                    used_video_ids.add(existing_mod.video_data['video_id'])
                # También obtener videos de chunks
                for chunk in existing_mod.chunks.all():
                    if hasattr(chunk, 'video') and chunk.video:
                        used_video_ids.add(chunk.video.video_id)
            
            logger.info(f"Videos ya usados en el curso: {len(used_video_ids)}")
            
            # Regenerar cada módulo faltante
            for module_number in missing_modules:
                try:
                    logger.info(f"Regenerando módulo {module_number}")
                    
                    module_data = loop.run_until_complete(
                        anthropic_service.create_module_content(course_metadata, module_number)
                    )
                    
                    # Buscar módulo existente o crear nuevo
                    existing_module = Module.objects.filter(course=course, module_order=module_number).first()
                    if existing_module:
                        module = existing_module
                        # Limpiar chunks existentes por si acaso
                        module.chunks.all().delete()
                        # Actualizar módulo existente
                        module.title = module_data.get('title', module.title)
                        module.description = module_data.get('description', module.description)
                        module.objective = module_data.get('objective', module.objective)
                        module.concepts = module_data.get('concepts', [])
                        module.summary = module_data.get('summary', '')
                        module.practical_exercise = module_data.get('practical_exercise', {})
                        module.resources = module_data.get('resources', {})
                        module.save()
                    else:
                        # Crear módulo nuevo
                        module = Module.objects.create(
                            course=course,
                            module_id=module_data.get('module_id', f'modulo_{module_number}'),
                            module_order=module_number,
                            title=module_data.get('title', ''),
                            description=module_data.get('description', ''),
                            objective=module_data.get('objective', ''),
                            concepts=module_data.get('concepts', []),
                            summary=module_data.get('summary', ''),
                            practical_exercise=module_data.get('practical_exercise', {}),
                            resources=module_data.get('resources', {})
                        )
                    
                    # Crear chunks y videos
                    chunks_data = module_data.get('chunks', [])
                    first_video_for_module = None
                    
                    for chunk_data in chunks_data:
                        chunk = Chunk.objects.create(
                            module=module,
                            chunk_id=chunk_data.get('chunk_id', ''),
                            chunk_order=chunk_data.get('chunk_order', 1),
                            total_chunks=chunk_data.get('total_chunks', 6),
                            content=chunk_data.get('content', ''),
                            checksum=chunk_data.get('checksum', ''),
                            title=chunk_data.get('title', '')
                        )
                        
                        # Buscar videos únicos para chunks
                        try:
                            videos = loop.run_until_complete(
                                youtube_service.search_videos_for_chunk(chunk_data, course_metadata)
                            )
                            
                            # Filtrar videos ya usados y seleccionar uno único
                            unique_video = None
                            for video_candidate in videos:
                                candidate_id = video_candidate.get('video_id', '')
                                if candidate_id and candidate_id not in used_video_ids:
                                    unique_video = video_candidate
                                    used_video_ids.add(candidate_id)  # Agregar a usados
                                    break
                            
                            if unique_video:
                                Video.objects.create(
                                    chunk=chunk,
                                    video_id=unique_video.get('video_id', ''),
                                    title=unique_video.get('title', ''),
                                    url=unique_video.get('url', ''),
                                    embed_url=unique_video.get('embed_url', ''),
                                    thumbnail_url=unique_video.get('thumbnail_url', ''),
                                    duration=unique_video.get('duration', 'N/A'),
                                    view_count=unique_video.get('view_count', 0)
                                )
                                
                                # Guardar el primer video único encontrado para el módulo
                                if first_video_for_module is None:
                                    first_video_for_module = unique_video
                                    logger.info(f"Video único asignado al módulo {module_number}: {unique_video.get('title', 'Sin título')}")
                            else:
                                logger.warning(f"No se encontraron videos únicos para chunk {chunk.chunk_id}")
                                
                        except Exception as video_error:
                            logger.warning(f"Error buscando video para chunk {chunk.chunk_id}: {video_error}")
                    
                    # Asignar el primer video único encontrado al campo video_data del módulo
                    if first_video_for_module:
                        module.video_data = first_video_for_module
                        module.save()
                        logger.info(f"Video principal único asignado al módulo {module_number}: {first_video_for_module.get('title', 'Sin título')}")
                    else:
                        logger.warning(f"No se pudo asignar video principal único al módulo {module_number}")
                    
                    # Crear quiz
                    quiz_data = module_data.get('quiz', [])
                    for question_data in quiz_data:
                        Quiz.objects.create(
                            module=module,
                            question=question_data.get('question', ''),
                            options=question_data.get('options', []),
                            correct_answer=question_data.get('correct_answer', 0),
                            explanation=question_data.get('explanation', '')
                        )
                    
                    modules_regenerated += 1
                    logger.info(f"Módulo {module_number} regenerado exitosamente")
                    
                except Exception as module_error:
                    logger.error(f"Error regenerando módulo {module_number}: {module_error}")
                    # Continuar con siguiente módulo
            
            # Actualizar status del curso si corresponde
            if modules_regenerated > 0:
                if course.status in [Course.StatusChoices.GENERATING_REMAINING, Course.StatusChoices.FAILED]:
                    course.status = Course.StatusChoices.COMPLETE
                    course.completed_at = timezone.now()
                    course.save()
            
            duration = time.time() - start_time
            GenerationLog.objects.create(
                course=course,
                action=GenerationLog.ActionChoices.COMPLETION,
                message=f"Regeneración completada. {modules_regenerated} módulos regenerados",
                duration_seconds=duration,
                details={'modules_regenerated': modules_regenerated, 'missing_modules': missing_modules}
            )
            
            logger.info(f"Regeneración de módulos completada para curso {course_id} en {duration:.2f}s")
            return f"Regenerados {modules_regenerated} módulos: {missing_modules}"
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error en regeneración de módulos para curso {course_id}: {e}")
        
        if course:
            GenerationLog.objects.create(
                course=course,
                action=GenerationLog.ActionChoices.ERROR,
                message=f"Error en regeneración de módulos: {str(e)}",
                duration_seconds=time.time() - start_time
            )
        
        raise


@shared_task(bind=True)
def cleanup_old_generation_logs(self):
    """
    Tarea de mantenimiento: limpiar logs antiguos de generación
    """
    try:
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted_count = GenerationLog.objects.filter(created_at__lt=cutoff_date).delete()[0]
        logger.info(f"Limpiados {deleted_count} logs de generación antiguos")
        
        return f"Limpiados {deleted_count} logs antiguos"
        
    except Exception as e:
        logger.error(f"Error en limpieza de logs: {e}")
        raise 