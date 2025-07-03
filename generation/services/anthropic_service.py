import json
import asyncio
import logging
from typing import Dict, Any, List
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)


class AnthropicService:
    """Servicio para integración con Claude API de Anthropic"""
    
    def __init__(self):
        self._client = None
        
        # Configurar Jinja2 para templates
        template_dir = Path(__file__).parent.parent / 'prompts'
        self.template_env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    @property
    def client(self):
        """Lazy initialization of Anthropic client"""
        if self._client is None:
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("Anthropic API key not configured")
            self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client
    
    async def create_course_metadata(self, prompt: str, level: str, interests: List[str], language: str = 'es') -> Dict[str, Any]:
        """
        Fase 1: Generar metadata del curso (título, descripción, módulos, podcast)
        """
        try:
            logger.info(f"Iniciando generación de metadata para prompt: {prompt[:50]}...")
            
            # Renderizar template con Jinja2
            template = self.template_env.get_template('course_metadata_prompt.j2')
            system_prompt = template.render(
                prompt=prompt,
                level=level,
                interests=interests,
                language=language
            )
            
            # Llamada asíncrona a Claude
            response = await asyncio.to_thread(
                self._call_claude_sync,
                system_prompt,
                "Genera la metadata del curso siguiendo exactamente la estructura P2C especificada.",
                max_tokens=4000
            )
            
            # Parse JSON response
            metadata = json.loads(response)
            
            logger.info(f"Metadata generada exitosamente: {metadata.get('title', 'Sin título')}")
            return metadata
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            raise ValueError(f"Respuesta de Claude no válida: {e}")
        except Exception as e:
            logger.error(f"Error en generación de metadata: {e}")
            raise
    
    async def create_module_content(self, course_metadata: Dict[str, Any], module_number: int) -> Dict[str, Any]:
        """
        Fase 2 y 3: Generar contenido completo de un módulo específico
        """
        try:
            logger.info(f"Iniciando generación de módulo {module_number}")
            
            template = self.template_env.get_template('module_content_prompt.j2')
            system_prompt = template.render(
                course_metadata=course_metadata,
                module_number=module_number,
                module_title=course_metadata['module_list'][module_number - 1]
            )
            
            response = await asyncio.to_thread(
                self._call_claude_sync,
                system_prompt,
                f"Generar contenido completo del módulo {module_number}: {course_metadata['module_list'][module_number - 1]}",
                max_tokens=8000
            )
            
            # Robusto manejo de JSON con limpieza de caracteres problemáticos
            try:
                # Limpiar caracteres de control que pueden causar errores de JSON
                import re
                cleaned_response = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response)
                cleaned_response = cleaned_response.replace('\\n', ' ').replace('\\t', ' ')
                
                module_data = json.loads(cleaned_response)
                
            except json.JSONDecodeError as json_error:
                logger.error(f"Error JSON en módulo {module_number}: {json_error}")
                logger.error(f"Respuesta problemática: {response[:500]}...")
                
                # Intentar extraer JSON válido de la respuesta
                try:
                    # Buscar el JSON dentro de la respuesta
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    
                    if json_start != -1 and json_end > json_start:
                        json_part = response[json_start:json_end]
                        # Limpiar caracteres problemáticos del JSON extraído
                        json_part = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_part)
                        module_data = json.loads(json_part)
                        logger.info(f"JSON recuperado exitosamente para módulo {module_number}")
                    else:
                        raise ValueError(f"No se encontró JSON válido en la respuesta para módulo {module_number}")
                        
                except (json.JSONDecodeError, ValueError) as recovery_error:
                    logger.error(f"No se pudo recuperar JSON para módulo {module_number}: {recovery_error}")
                    # Crear estructura mínima válida
                    module_data = {
                        "module_id": f"modulo_{module_number}",
                        "title": course_metadata['module_list'][module_number - 1],
                        "description": f"Contenido del módulo {module_number}",
                        "chunks": [],
                        "concepts": [],
                        "quiz": []
                    }
            
            logger.info(f"Módulo {module_number} generado exitosamente")
            return module_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing module content JSON: {e}")
            raise ValueError(f"Respuesta de Claude no válida para módulo: {e}")
        except Exception as e:
            logger.error(f"Error en generación de módulo {module_number}: {e}")
            raise
    
    async def create_module_metadata(self, course_metadata: Dict[str, Any], module_number: int) -> Dict[str, Any]:
        """
        Fase 1.5: Generar solo metadata de un módulo específico (sin contenido completo)
        """
        try:
            logger.info(f"Iniciando generación de metadata del módulo {module_number}")
            
            template = self.template_env.get_template('module_metadata_prompt.j2')
            system_prompt = template.render(
                course_metadata=course_metadata,
                module_number=module_number,
                module_title=course_metadata['module_list'][module_number - 1]
            )
            
            response = await asyncio.to_thread(
                self._call_claude_sync,
                system_prompt,
                f"Genera solo la metadata del módulo {module_number} siguiendo la estructura P2C.",
                max_tokens=2000
            )
            
            module_metadata = json.loads(response)
            
            logger.info(f"Metadata del módulo {module_number} generada exitosamente")
            return module_metadata
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing module metadata JSON: {e}")
            raise ValueError(f"Respuesta de Claude no válida para metadata del módulo: {e}")
        except Exception as e:
            logger.error(f"Error en generación de metadata del módulo {module_number}: {e}")
            raise
    
    async def create_final_project(self, course_metadata: Dict[str, Any], modules_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generar proyecto final del curso
        """
        try:
            logger.info("Generando proyecto final del curso")
            
            template = self.template_env.get_template('final_project_prompt.j2')
            system_prompt = template.render(
                course_metadata=course_metadata,
                modules_data=modules_data
            )
            
            response = await asyncio.to_thread(
                self._call_claude_sync,
                system_prompt,
                "Genera un proyecto final completo y práctico para el curso.",
                max_tokens=2500
            )
            
            final_project = json.loads(response)
            
            logger.info("Proyecto final generado exitosamente")
            return final_project
            
        except Exception as e:
            logger.error(f"Error en generación de proyecto final: {e}")
            raise
    
    async def generate_search_queries(self, topic: str, level: str) -> List[str]:
        """
        Generar consultas de búsqueda optimizadas para YouTube
        """
        try:
            prompt = f"""Genera 3 consultas de búsqueda específicas para encontrar videos educativos de YouTube sobre:
            
            Tema: {topic}
            Nivel: {level}
            
            Las consultas deben ser:
            - En español
            - Específicas y educativas
            - Apropiadas para el nivel {level}
            - Orientadas a tutoriales o explicaciones
            
            Responde solo con un array JSON de strings, sin explicaciones adicionales.
            
            Ejemplo: ["tutorial python principiantes", "introducción programación python", "python desde cero"]
            """
            
            response = await asyncio.to_thread(
                self._call_claude_sync,
                prompt,
                "Genera las consultas de búsqueda en formato JSON array.",
                max_tokens=200
            )
            
            queries = json.loads(response)
            return queries
            
        except Exception as e:
            logger.error(f"Error generando consultas de búsqueda: {e}")
            # Fallback queries
            return [f"{topic} tutorial {level}", f"aprende {topic}", f"{topic} explicación"]
    
    def _call_claude_sync(self, system_prompt: str, user_message: str, max_tokens: int = 3000) -> str:
        """
        Llamada síncrona a Claude API
        """
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                temperature=0.3,  # Reducir temperatura para más consistencia
                system=system_prompt,
                messages=[
                    {
                        "role": "user", 
                        "content": user_message
                    }
                ]
            )
            
            return message.content[0].text
            
        except anthropic.APIError as e:
            logger.error(f"Error en Claude API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado en llamada a Claude: {e}")
            raise
    
    def validate_course_structure(self, data: Dict[str, Any]) -> bool:
        """
        Validar que la estructura del curso generado sea correcta
        """
        required_fields = ['title', 'description', 'module_list', 'podcast_script']
        
        for field in required_fields:
            if field not in data:
                logger.error(f"Campo requerido faltante en metadata: {field}")
                return False
        
        if not isinstance(data.get('module_list'), list) or len(data['module_list']) < 3:
            logger.error("module_list debe ser una lista con al menos 3 módulos")
            return False
            
        return True
    
    def validate_module_structure(self, data: Dict[str, Any]) -> bool:
        """
        Validar estructura de módulo generado
        """
        required_fields = ['title', 'description', 'chunks', 'quiz']
        
        for field in required_fields:
            if field not in data:
                logger.error(f"Campo requerido faltante en módulo: {field}")
                return False
        
        if not isinstance(data.get('chunks'), list) or len(data['chunks']) < 4:
            logger.error("chunks debe ser una lista con al menos 4 elementos")
            return False
            
        return True


# Instancia global del servicio
anthropic_service = AnthropicService() 