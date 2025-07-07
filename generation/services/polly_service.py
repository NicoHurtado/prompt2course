import boto3
import uuid
import re
import asyncio
import logging
import requests
import tempfile
import os
from typing import Dict, Any, Optional, List
from io import BytesIO
from django.conf import settings

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.warning("⚠️ pydub no disponible - concatenación de audio deshabilitada")

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
                voice_id = settings.AWS_POLLY_VOICE_FEMALE  # Lupe por defecto
            
            logger.info(f"Iniciando síntesis de voz para curso {course_id} con voz {voice_id}")
            
            # Limpiar texto para Polly
            clean_text = self._clean_text_for_polly(text)
            
            # Síntesis de voz
            polly_response = await asyncio.to_thread(
                self._synthesize_speech,
                clean_text,
                voice_id
            )
            
            # Generar nombre del archivo basado en course_id
            safe_course_id = str(course_id).replace('-', '')[:12]  # Limpiar course_id
            
            # Si es un archivo temporal (contiene "_segment_"), usar nombre temporal
            if "_segment_" in str(course_id):
                file_name = f"audios/temp_{safe_course_id}.mp3"
            else:
                file_name = f"audios/podcast_{safe_course_id}.mp3"
            
            # Subir a S3 (sobreescribir si ya existe)
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
        Generar UN SOLO AUDIO con ambas voces usando SSML
        """
        try:
            logger.info(f"🎙️ INICIANDO generación de AUDIO ÚNICO con dos voces para curso {course_id}")
            
            # Usar el nuevo método que genera UN SOLO AUDIO
            return await self.generate_single_audio_two_voices(podcast_script, course_id)
            
        except Exception as e:
            logger.error(f"❌ Error generando audio único: {e}")
            raise
    
    def _synthesize_speech(self, text: str, voice_id: str) -> Dict[str, Any]:
        """
        Llamada síncrona a AWS Polly para texto simple
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
    
    def _synthesize_speech_ssml(self, ssml: str) -> Dict[str, Any]:
        """
        Llamada síncrona a AWS Polly para SSML (conversaciones con múltiples voces)
        """
        try:
            logger.info("🎭 Ejecutando síntesis SSML...")
            
            # SSML requiere un VoiceId base aunque se especifiquen voces en el contenido
            base_voice = settings.AWS_POLLY_VOICE_FEMALE  # Lupe como voz base
            engine = 'neural' if settings.AWS_POLLY_ENGINE == 'neural' else 'standard'
            
            try:
                response = self.polly_client.synthesize_speech(
                    Text=ssml,
                    OutputFormat='mp3',
                    VoiceId=base_voice,  # REQUERIDO: voz base para SSML
                    TextType='ssml',     # Importante: usar SSML
                    Engine=engine
                )
                return response
                
            except Exception as neural_error:
                # Fallback a motor estándar si neural falla
                if engine == 'neural':
                    logger.warning(f"Motor neural SSML falló, usando estándar: {neural_error}")
                    response = self.polly_client.synthesize_speech(
                        Text=ssml,
                        OutputFormat='mp3',
                        VoiceId=base_voice,
                        TextType='ssml',
                        Engine='standard'
                    )
                    return response
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"❌ Error en síntesis SSML de Polly: {e}")
            raise
    
    def _upload_to_s3(self, audio_stream: BytesIO, file_name: str) -> str:
        """
        Subir audio a S3 y retornar URL pública
        """
        try:
            # Leer contenido del stream
            audio_content = audio_stream.read()
            
            # Subir a S3 (sin ACL - depende de política del bucket)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=audio_content,
                ContentType='audio/mpeg',
                CacheControl='max-age=31536000'  # Cache por 1 año
                # ACL removido - bucket no permite ACLs
            )
            
            # Generar URL pre-firmada (válida por 7 días) ya que el bucket no permite acceso público
            try:
                s3_url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': file_name},
                    ExpiresIn=604800  # 7 días en segundos
                )
                logger.info(f"✅ URL pre-firmada generada: {file_name}")
            except Exception as presign_error:
                logger.warning(f"⚠️ Error generando URL pre-firmada: {presign_error}")
                # Fallback a URL directa
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
    
    def _prepare_narrative_conversation(self, podcast_script: str) -> str:
        """
        Convertir diálogo en narración conversacional fluida
        """
        try:
            logger.info("🎭 Convirtiendo diálogo a narración conversacional")
            
            # Dividir el script por líneas de diálogo
            dialogue_parts = self._parse_dialogue(podcast_script)
            
            if not dialogue_parts:
                logger.warning("⚠️ No se encontró diálogo, usando texto original")
                return self._clean_text_for_polly(podcast_script)
            
            logger.info(f"🎯 Procesando {len(dialogue_parts)} intervenciones")
            
            # Construir narración con indicadores naturales
            narrative_parts = []
            
            for i, part in enumerate(dialogue_parts):
                speaker = part['speaker'].upper()
                text = self._clean_text_for_polly(part['text'])
                
                # Agregar indicador natural del personaje
                if speaker in ["MARÍA", "MARIA"]:
                    indicator = "María comenta:" if i == 0 else "María añade:"
                else:
                    indicator = "Carlos responde:" if i > 0 else "Carlos explica:"
                
                # Construir intervención narrativa
                narrative_parts.append(f"{indicator} {text}")
            
            # Unir todas las partes con pausas naturales
            narrative_script = " ".join(narrative_parts)
            
            logger.info(f"📝 Narración conversacional lista: {len(narrative_script)} caracteres")
            return narrative_script
            
        except Exception as e:
            logger.error(f"❌ Error preparando narración conversacional: {e}")
            # Fallback: texto simple limpio
            return self._clean_text_for_polly(podcast_script)
    
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
    
    def _prepare_conversation_ssml(self, script: str) -> str:
        """
        Convertir script de diálogo a SSML con voces alternadas para conversación real
        """
        logger.info("🎭 Preparando SSML para conversación entre María y Carlos")
        
        # Parsear el diálogo para obtener las partes
        dialogue_parts = self._parse_dialogue(script)
        
        if not dialogue_parts:
            # Si no hay diálogo parseado, crear uno genérico
            clean_text = self._clean_text_for_polly(script)
            return f"""
            <speak>
                <voice name="{settings.AWS_POLLY_VOICE_FEMALE}">
                    <prosody rate="medium" pitch="medium">
                        {clean_text}
                    </prosody>
                </voice>
            </speak>
            """.strip()
        
        # Construir SSML con voces alternadas
        ssml_parts = ['<speak>']
        
        for i, part in enumerate(dialogue_parts):
            speaker = part['speaker'].upper()
            text = self._clean_text_for_polly(part['text'])
            
            # Seleccionar voz según el personaje
            if speaker in ['MARÍA', 'MARIA']:
                voice = settings.AWS_POLLY_VOICE_FEMALE  # Lupe
                prosody = 'rate="medium" pitch="medium"'
            elif speaker == 'CARLOS':
                voice = settings.AWS_POLLY_VOICE_MALE    # Miguel
                prosody = 'rate="medium" pitch="low"'
            else:
                voice = settings.AWS_POLLY_VOICE_FEMALE  # Default a Lupe
                prosody = 'rate="medium" pitch="medium"'
            
            # Agregar pausa entre intervenciones
            if i > 0:
                ssml_parts.append('<break time="1s"/>')
            
            # Agregar intervención con voz específica
            ssml_parts.append(f'''
                <voice name="{voice}">
                    <prosody {prosody}>
                        {text}
                    </prosody>
                </voice>
            '''.strip())
        
        ssml_parts.append('</speak>')
        
        # Unir todo el SSML
        final_ssml = ' '.join(ssml_parts)
        
        logger.info(f"🎯 SSML generado con {len(dialogue_parts)} intervenciones")
        return final_ssml
    
    async def text_to_speech_ssml(self, ssml: str, course_id: str) -> Dict[str, Any]:
        """
        Convertir SSML a voz usando AWS Polly (para conversaciones con múltiples voces)
        """
        try:
            logger.info(f"🎙️ Iniciando síntesis SSML para curso {course_id}")
            
            # Síntesis de voz con SSML
            polly_response = await asyncio.to_thread(
                self._synthesize_speech_ssml,
                ssml
            )
            
            # Generar nombre fijo para el archivo
            safe_course_id = str(course_id).replace('-', '')[:12]
            file_name = f"audios/podcast_{safe_course_id}.mp3"
            
            # Subir a S3 (sobreescribir si ya existe)
            s3_url = await asyncio.to_thread(
                self._upload_to_s3,
                polly_response['AudioStream'],
                file_name
            )
            
            # Estimar duración (aproximadamente 120 palabras por minuto para conversación)
            word_count = len(ssml.split())
            estimated_duration = max(1, round(word_count / 120 * 60))  # en segundos
            
            result = {
                'audio_url': s3_url,
                'duration_seconds': estimated_duration,
                'voice_id': 'SSML_Conversation',
                'file_name': file_name,
                'text_length': len(ssml),
                'word_count': word_count
            }
            
            logger.info(f"✅ Audio SSML generado exitosamente: {s3_url}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en síntesis SSML: {e}")
            raise

    def _parse_dialogue(self, script: str) -> List[Dict[str, str]]:
        """
        Parsear script de diálogo en segmentos separados por personaje
        """
        logger.info(f"🎭 Parseando diálogo: {len(script)} caracteres")
        
        # Limpiar script
        script = script.strip()
        if not script:
            return []
        
        # Buscar patrones de diálogo: NOMBRE: texto
        dialogue_pattern = r'^(MARÍA|CARLOS):\s*(.+)$'
        
        parts = []
        lines = script.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Buscar patrón de diálogo
            match = re.match(dialogue_pattern, line, re.MULTILINE | re.IGNORECASE)
            if match:
                speaker = match.group(1).upper()
                text = match.group(2).strip()
                
                if text:  # Solo agregar si hay texto
                    parts.append({
                        'speaker': speaker,
                        'text': text
                    })
                    logger.info(f"🎤 Segmento: {speaker} - {len(text)} chars")
        
        logger.info(f"✅ Parseado completo: {len(parts)} segmentos de diálogo")
        return parts
    
    def _get_voice_for_speaker(self, speaker: str) -> str:
        """
        Obtener voz AWS Polly según el personaje
        """
        speaker = speaker.upper()
        if speaker in ['MARÍA', 'MARIA']:
            return settings.AWS_POLLY_VOICE_FEMALE  # Lupe
        elif speaker == 'CARLOS':
            return settings.AWS_POLLY_VOICE_MALE    # Miguel
        else:
            return settings.AWS_POLLY_VOICE_FEMALE  # Default
    
    async def _concatenate_audio_segments(self, temp_files: List[Dict], course_id: str) -> Dict[str, Any]:
        """
        Concatenar segmentos de audio en una conversación única
        """
        if not PYDUB_AVAILABLE:
            logger.warning("⚠️ pydub no disponible, usando primer segmento solamente")
            # Fallback: usar solo el primer segmento
            if temp_files:
                first_file = temp_files[0]
                # Renombrar el primer archivo como el archivo principal
                return await self._rename_temp_to_final(first_file['url'], course_id)
            raise Exception("No hay segmentos de audio para concatenar")
        
        try:
            logger.info(f"🔗 Iniciando concatenación de {len(temp_files)} segmentos")
            
            # Crear directorio temporal
            with tempfile.TemporaryDirectory() as temp_dir:
                # Descargar todos los segmentos temporales
                audio_segments = []
                for i, file_info in enumerate(temp_files):
                    logger.info(f"📥 Descargando segmento {i+1}: {file_info['speaker']}")
                    
                    # Descargar archivo de S3
                    response = requests.get(file_info['url'], timeout=30)
                    response.raise_for_status()
                    
                    # Guardar temporalmente
                    temp_path = os.path.join(temp_dir, f"segment_{i}.mp3")
                    with open(temp_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Cargar con pydub
                    audio_segment = AudioSegment.from_mp3(temp_path)
                    
                    # Agregar pausa entre segmentos (500ms)
                    if i > 0:
                        pause = AudioSegment.silent(duration=500)  # 500ms de silencio
                        audio_segments.append(pause)
                    
                    audio_segments.append(audio_segment)
                    logger.info(f"✅ Segmento {i+1} cargado: {len(audio_segment)}ms")
                
                # Concatenar todos los segmentos
                logger.info(f"🎵 Concatenando {len(audio_segments)} elementos")
                final_audio = sum(audio_segments)
                
                # Exportar audio final
                final_path = os.path.join(temp_dir, "final_conversation.mp3")
                final_audio.export(final_path, format="mp3", bitrate="128k")
                
                logger.info(f"🎯 Audio final generado: {len(final_audio)}ms")
                
                # Subir archivo final a S3
                with open(final_path, 'rb') as f:
                    audio_stream = BytesIO(f.read())
                
                # Generar nombre final del archivo
                safe_course_id = str(course_id).replace('-', '')[:12]
                final_file_name = f"audios/podcast_{safe_course_id}.mp3"
                
                # Subir a S3
                s3_url = await asyncio.to_thread(
                    self._upload_to_s3,
                    audio_stream,
                    final_file_name
                )
                
                return {
                    'audio_url': s3_url,
                    'file_name': final_file_name,
                    'duration_seconds': len(final_audio) // 1000,  # convertir ms a segundos
                    'segments_count': len(temp_files)
                }
                
        except Exception as e:
            logger.error(f"❌ Error concatenando audio: {e}")
            # Fallback: usar primer segmento
            if temp_files:
                logger.info("🔄 Fallback: usando primer segmento como audio principal")
                return await self._rename_temp_to_final(temp_files[0]['url'], course_id)
            raise
    
    async def _generate_ssml_conversation(self, dialogue_parts: List[Dict[str, str]], course_id: str) -> Dict[str, Any]:
        """
        Generar conversación narrativa (fallback cuando pydub no está disponible)
        """
        try:
            logger.info(f"🎭 Generando conversación narrativa con {len(dialogue_parts)} segmentos")
            
            # Convertir diálogo a narración descriptiva
            narrative_parts = []
            
            for i, part in enumerate(dialogue_parts):
                speaker = part['speaker'].upper()
                text = self._clean_text_for_polly(part['text'])
                
                if speaker in ['MARÍA', 'MARIA']:
                    narrative_parts.append(f"María dice: {text}")
                elif speaker == 'CARLOS':
                    narrative_parts.append(f"Carlos responde: {text}")
                else:
                    narrative_parts.append(f"{speaker} dice: {text}")
            
            # Unir todas las partes con pausas
            narrative_script = " ".join(narrative_parts)
            
            logger.info(f"📝 Script narrativo generado: {len(narrative_script)} caracteres")
            
            # Generar audio con voz única
            audio_result = await self.text_to_speech(
                narrative_script,
                course_id,
                settings.AWS_POLLY_VOICE_FEMALE
            )
            
            logger.info(f"✅ Conversación narrativa completada")
            
            return {
                'audio_url': audio_result['audio_url'],
                'file_name': audio_result['file_name'],
                'duration_seconds': audio_result['duration_seconds'],
                'method': 'narrative_fallback'
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando conversación narrativa: {e}")
            raise
    
    async def _generate_single_voice_conversation(self, dialogue_parts: List[Dict[str, str]], course_id: str) -> Dict[str, Any]:
        """
        Fallback: generar conversación narrativa con una sola voz
        """
        try:
            logger.info("🎭 Generando conversación narrativa con una sola voz")
            
            # Convertir diálogo a narración
            narrative_parts = []
            for part in dialogue_parts:
                speaker = part['speaker'].upper()
                text = self._clean_text_for_polly(part['text'])
                
                if speaker in ['MARÍA', 'MARIA']:
                    narrative_parts.append(f"María dice: {text}")
                elif speaker == 'CARLOS':
                    narrative_parts.append(f"Carlos responde: {text}")
                
            # Unir con pausas
            narrative_script = " ".join(narrative_parts)
            
            # Generar audio con voz única
            audio_result = await self.text_to_speech(
                narrative_script,
                course_id,
                settings.AWS_POLLY_VOICE_FEMALE
            )
            
            return {
                'audio_url': audio_result['audio_url'],
                'file_name': audio_result['file_name'],
                'duration_seconds': audio_result['duration_seconds'],
                'method': 'single_voice_narrative'
            }
            
        except Exception as e:
            logger.error(f"❌ Error en fallback de voz única: {e}")
            raise
    
    async def _rename_temp_to_final(self, temp_url: str, course_id: str) -> Dict[str, Any]:
        """
        Renombrar archivo temporal como archivo final (fallback)
        """
        try:
            # Descargar archivo temporal
            response = requests.get(temp_url, timeout=30)
            response.raise_for_status()
            
            # Generar nombre final
            safe_course_id = str(course_id).replace('-', '')[:12]
            final_file_name = f"audios/podcast_{safe_course_id}.mp3"
            
            # Subir como archivo final
            audio_stream = BytesIO(response.content)
            s3_url = await asyncio.to_thread(
                self._upload_to_s3,
                audio_stream,
                final_file_name
            )
            
            return {
                'audio_url': s3_url,
                'file_name': final_file_name,
                'duration_seconds': 60,  # estimado
                'segments_count': 1
            }
            
        except Exception as e:
            logger.error(f"❌ Error renombrando archivo temporal: {e}")
            raise

    async def generate_single_audio_two_voices(self, podcast_script: str, course_id: str) -> Dict[str, Any]:
        """
        Generar UN SOLO AUDIO con ambas voces concatenando segmentos individuales
        """
        try:
            logger.info(f"🎙️ Generando AUDIO ÚNICO con dos voces para curso {course_id}")
            
            # Parsear diálogo
            dialogue_parts = self._parse_dialogue(podcast_script)
            
            if not dialogue_parts:
                logger.warning("⚠️ No hay diálogo detectado")
                return await self.text_to_speech(
                    self._clean_text_for_polly(podcast_script),
                    course_id,
                    settings.AWS_POLLY_VOICE_FEMALE
                )
            
            logger.info(f"🎭 Generando {len(dialogue_parts)} segmentos: MARÍA-CARLOS-MARÍA-CARLOS...")
            
            # Generar cada segmento con su voz correspondiente
            audio_data_segments = []
            total_duration = 0
            
            for i, part in enumerate(dialogue_parts):
                speaker = part['speaker'].upper()
                text = self._clean_text_for_polly(part['text'])
                
                # Seleccionar voz según personaje
                if speaker in ['MARÍA', 'MARIA']:
                    voice_id = settings.AWS_POLLY_VOICE_FEMALE  # Lupe
                elif speaker == 'CARLOS':
                    voice_id = settings.AWS_POLLY_VOICE_MALE    # Miguel
                else:
                    voice_id = settings.AWS_POLLY_VOICE_FEMALE  # Default
                
                logger.info(f"🎤 Segmento {i+1}: {speaker} ({voice_id}) - '{text[:50]}...'")
                
                # Generar audio para este segmento
                polly_response = await asyncio.to_thread(
                    self._synthesize_speech,
                    text,
                    voice_id
                )
                
                # Leer datos de audio
                audio_data = polly_response['AudioStream'].read()
                audio_data_segments.append({
                    'data': audio_data,
                    'speaker': speaker,
                    'voice_id': voice_id
                })
                
                # Estimar duración (aproximado)
                duration = max(1, len(text) // 10)  # ~10 caracteres por segundo
                total_duration += duration
            
            # Concatenar todos los segmentos usando pydub
            final_audio_data = await self._concatenate_audio_data(audio_data_segments, course_id)
            
            # Subir audio final a S3
            safe_course_id = str(course_id).replace('-', '')[:12]
            file_name = f"audios/podcast_{safe_course_id}.mp3"
            
            s3_url = await asyncio.to_thread(
                self._upload_to_s3,
                final_audio_data,
                file_name
            )
            
            logger.info(f"✅ AUDIO ÚNICO generado: {s3_url}")
            
            return {
                'main_audio_url': s3_url,
                'total_duration': total_duration,
                'speakers_count': 2,
                'method': 'concatenated_segments',
                'parts': []
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando audio único: {e}")
            raise

    async def _synthesize_single_ssml_audio(self, ssml: str, course_id: str) -> Dict[str, Any]:
        """
        Sintetizar SSML en un solo audio
        """
        try:
            logger.info("🎭 Sintetizando SSML en audio único...")
            
            # Usar motor estándar (neural no soporta SSML con múltiples voces en us-east-2)
            polly_response = await asyncio.to_thread(
                self._synthesize_speech_ssml_single,
                ssml
            )
            
            # Generar nombre del archivo
            safe_course_id = str(course_id).replace('-', '')[:12]
            file_name = f"audios/podcast_{safe_course_id}.mp3"
            
            # Subir a S3
            s3_url = await asyncio.to_thread(
                self._upload_to_s3,
                polly_response['AudioStream'],
                file_name
            )
            
            # Estimar duración
            word_count = len(ssml.split())
            estimated_duration = max(1, round(word_count / 120 * 60))
            
            return {
                'audio_url': s3_url,
                'duration_seconds': estimated_duration,
                'file_name': file_name,
                'method': 'single_ssml'
            }
            
        except Exception as e:
            logger.error(f"❌ Error sintetizando SSML único: {e}")
            raise

    def _synthesize_speech_ssml_single(self, ssml: str) -> Dict[str, Any]:
        """
        Síntesis SSML usando motor estándar (compatible con múltiples voces)
        """
        try:
            logger.info("🎯 Ejecutando síntesis SSML con motor estándar")
            
            # Usar motor estándar y voz base femenina
            response = self.polly_client.synthesize_speech(
                Text=ssml,
                OutputFormat='mp3',
                VoiceId='Lupe',  # Voz base femenina
                TextType='ssml',
                Engine='standard'  # Motor estándar soporta múltiples voces
            )
            
            logger.info("✅ SSML sintetizado exitosamente")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error en síntesis SSML: {e}")
            raise

    async def _concatenate_audio_data(self, audio_data_segments: List[Dict], course_id: str) -> BytesIO:
        """
        Concatenar datos de audio en memoria usando pydub
        """
        if not PYDUB_AVAILABLE:
            logger.warning("⚠️ pydub no disponible, usando primer segmento")
            return BytesIO(audio_data_segments[0]['data'])
        
        try:
            logger.info(f"🔗 Concatenando {len(audio_data_segments)} segmentos en memoria")
            
            # Crear directorio temporal
            with tempfile.TemporaryDirectory() as temp_dir:
                audio_segments = []
                
                for i, segment_info in enumerate(audio_data_segments):
                    speaker = segment_info['speaker']
                    voice_id = segment_info['voice_id']
                    audio_data = segment_info['data']
                    
                    logger.info(f"📥 Procesando segmento {i+1}: {speaker} ({voice_id})")
                    
                    # Guardar temporalmente
                    temp_path = os.path.join(temp_dir, f"segment_{i}.mp3")
                    with open(temp_path, 'wb') as f:
                        f.write(audio_data)
                    
                    # Cargar con pydub
                    audio_segment = AudioSegment.from_mp3(temp_path)
                    
                    # Agregar pausa entre segmentos (500ms)
                    if i > 0:
                        pause = AudioSegment.silent(duration=500)  # 500ms de silencio
                        audio_segments.append(pause)
                    
                    audio_segments.append(audio_segment)
                    logger.info(f"✅ Segmento {i+1} cargado: {len(audio_segment)}ms")
                
                # Concatenar todos los segmentos
                logger.info(f"🎵 Concatenando {len(audio_segments)} elementos")
                final_audio = sum(audio_segments)
                
                # Exportar a BytesIO
                output_buffer = BytesIO()
                final_audio.export(output_buffer, format="mp3", bitrate="128k")
                output_buffer.seek(0)  # Resetear puntero al inicio
                
                logger.info(f"🎯 Audio final concatenado: {len(final_audio)}ms")
                
                return output_buffer
                
        except Exception as e:
            logger.error(f"❌ Error concatenando audio en memoria: {e}")
            # Fallback: devolver primer segmento
            logger.info("🔄 Fallback: usando primer segmento")
            return BytesIO(audio_data_segments[0]['data'])


# Instancia global del servicio
polly_service = PollyService() 