import boto3
import uuid
import re
import asyncio
import logging
from typing import Dict, Any, Optional
from io import BytesIO
from django.conf import settings

logger = logging.getLogger(__name__)


class PollyService:
    """Servicio para síntesis de voz con AWS Polly y almacenamiento en S3"""
    
    def __init__(self):
        self._polly_client = None
        self._s3_client = None
        self.bucket_name = settings.AWS_S3_BUCKET
    
    @property
    def polly_client(self):
        """Lazy initialization of Polly client"""
        if self._polly_client is None:
            if not settings.AWS_ACCESS_KEY_ID:
                raise ValueError("AWS credentials not configured")
            self._polly_client = boto3.client(
                'polly',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        return self._polly_client
    
    @property
    def s3_client(self):
        """Lazy initialization of S3 client"""
        if self._s3_client is None:
            if not settings.AWS_ACCESS_KEY_ID:
                raise ValueError("AWS credentials not configured")
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        return self._s3_client
    
    async def text_to_speech(self, text: str, course_id: str, voice_id: str = None) -> Dict[str, Any]:
        """
        Convertir texto a voz usando AWS Polly y subir a S3
        """
        try:
            # Seleccionar voz por defecto si no se especifica
            if not voice_id:
                voice_id = settings.AWS_POLLY_VOICE_FEMALE  # Lucia por defecto
            
            logger.info(f"Iniciando síntesis de voz para curso {course_id} con voz {voice_id}")
            
            # Limpiar texto para Polly
            clean_text = self._clean_text_for_polly(text)
            
            # Síntesis de voz
            polly_response = await asyncio.to_thread(
                self._synthesize_speech,
                clean_text,
                voice_id
            )
            
            # Generar nombre único para el archivo
            file_name = f"audios/podcast_{course_id}_{uuid.uuid4().hex[:8]}.mp3"
            
            # Subir a S3
            s3_url = await asyncio.to_thread(
                self._upload_to_s3,
                polly_response['AudioStream'],
                file_name
            )
            
            # Estimar duración (aproximadamente 150 palabras por minuto)
            word_count = len(clean_text.split())
            estimated_duration = max(1, round(word_count / 150 * 60))  # en segundos
            
            result = {
                'audio_url': s3_url,
                'duration_seconds': estimated_duration,
                'voice_id': voice_id,
                'file_name': file_name,
                'text_length': len(clean_text),
                'word_count': word_count
            }
            
            logger.info(f"Audio generado exitosamente: {s3_url}")
            return result
            
        except Exception as e:
            logger.error(f"Error en síntesis de voz: {e}")
            raise
    
    async def generate_podcast_audio(self, podcast_script: str, course_id: str) -> Dict[str, Any]:
        """
        Generar audio de podcast usando voces alternadas para María y Carlos
        """
        try:
            logger.info(f"Generando podcast para curso {course_id}")
            
            # Dividir script por personajes
            dialogue_parts = self._parse_dialogue(podcast_script)
            
            audio_parts = []
            combined_duration = 0
            
            for part in dialogue_parts:
                speaker = part['speaker']
                text = part['text']
                
                # Seleccionar voz según el personaje
                voice_id = self._get_voice_for_speaker(speaker)
                
                # Generar audio para esta parte
                audio_result = await self.text_to_speech(
                    text, 
                    f"{course_id}_{speaker.lower()}", 
                    voice_id
                )
                
                audio_parts.append({
                    'speaker': speaker,
                    'audio_url': audio_result['audio_url'],
                    'duration': audio_result['duration_seconds']
                })
                
                combined_duration += audio_result['duration_seconds']
            
            # TODO: En una implementación completa, combinar los audios
            # Por ahora, retornamos el primer audio como principal
            main_audio_url = audio_parts[0]['audio_url'] if audio_parts else None
            
            result = {
                'main_audio_url': main_audio_url,
                'total_duration': combined_duration,
                'parts': audio_parts,
                'speakers_count': len(set(part['speaker'] for part in dialogue_parts))
            }
            
            logger.info(f"Podcast generado exitosamente con duración de {combined_duration} segundos")
            return result
            
        except Exception as e:
            logger.error(f"Error generando podcast: {e}")
            raise
    
    def _synthesize_speech(self, text: str, voice_id: str) -> Dict[str, Any]:
        """
        Llamada síncrona a AWS Polly
        """
        try:
            # Intentar usar motor neural primero
            engine = 'neural' if settings.AWS_POLLY_ENGINE == 'neural' else 'standard'
            
            try:
                response = self.polly_client.synthesize_speech(
                    Text=text,
                    OutputFormat='mp3',
                    VoiceId=voice_id,
                    Engine=engine,
                    TextType='text'
                )
                return response
                
            except Exception as neural_error:
                # Fallback a motor estándar si neural falla
                if engine == 'neural':
                    logger.warning(f"Motor neural falló, usando estándar: {neural_error}")
                    response = self.polly_client.synthesize_speech(
                        Text=text,
                        OutputFormat='mp3',
                        VoiceId=voice_id,
                        Engine='standard',
                        TextType='text'
                    )
                    return response
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"Error en síntesis de Polly: {e}")
            raise
    
    def _upload_to_s3(self, audio_stream: BytesIO, file_name: str) -> str:
        """
        Subir audio a S3 y retornar URL pública
        """
        try:
            # Leer contenido del stream
            audio_content = audio_stream.read()
            
            # Subir a S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=audio_content,
                ContentType='audio/mpeg',
                CacheControl='max-age=31536000'  # Cache por 1 año
            )
            
            # Generar URL pública
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{file_name}"
            
            return s3_url
            
        except Exception as e:
            logger.error(f"Error subiendo a S3: {e}")
            raise
    
    def _clean_text_for_polly(self, text: str) -> str:
        """
        Limpiar texto para mejorar la síntesis de voz
        """
        # Remover caracteres de markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **bold** -> texto
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # *italic* -> texto
        text = re.sub(r'`(.*?)`', r'\1', text)        # `code` -> texto
        text = re.sub(r'#+ ', '', text)               # Headers
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
        
        # Remover emojis y caracteres especiales problemáticos
        text = re.sub(r'[📖🛠️🎯🔍💡🎉]', '', text)
        
        # Limpiar múltiples espacios y saltos de línea
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Mejorar pronunciación de términos técnicos comunes
        replacements = {
            'API': 'A P I',
            'URL': 'U R L',
            'HTML': 'H T M L',
            'CSS': 'C S S',
            'JSON': 'J S O N',
            'XML': 'X M L',
            'HTTP': 'H T T P',
            'HTTPS': 'H T T P S',
            'SQL': 'S Q L',
        }
        
        for term, replacement in replacements.items():
            text = text.replace(term, replacement)
        
        return text.strip()
    
    def _parse_dialogue(self, script: str) -> list:
        """
        Parsear script de diálogo para identificar personajes
        """
        dialogue_parts = []
        lines = script.split('\n')
        
        current_speaker = None
        current_text = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Buscar patrones de personajes (MARÍA:, CARLOS:)
            speaker_match = re.match(r'^(MARÍA|CARLOS|MARIA):\s*(.*)', line, re.IGNORECASE)
            
            if speaker_match:
                # Guardar texto anterior si existe
                if current_speaker and current_text:
                    dialogue_parts.append({
                        'speaker': current_speaker,
                        'text': ' '.join(current_text)
                    })
                
                # Iniciar nuevo personaje
                current_speaker = speaker_match.group(1).upper()
                current_text = [speaker_match.group(2)] if speaker_match.group(2) else []
            else:
                # Continuar texto del personaje actual
                if current_speaker:
                    current_text.append(line)
        
        # Agregar último fragmento
        if current_speaker and current_text:
            dialogue_parts.append({
                'speaker': current_speaker,
                'text': ' '.join(current_text)
            })
        
        return dialogue_parts
    
    def _get_voice_for_speaker(self, speaker: str) -> str:
        """
        Obtener voz AWS Polly según el personaje
        """
        speaker = speaker.upper()
        if speaker in ['MARÍA', 'MARIA']:
            return settings.AWS_POLLY_VOICE_FEMALE  # Lucia
        elif speaker == 'CARLOS':
            return settings.AWS_POLLY_VOICE_MALE    # Enrique
        else:
            return settings.AWS_POLLY_VOICE_FEMALE  # Default


# Instancia global del servicio
polly_service = PollyService() 