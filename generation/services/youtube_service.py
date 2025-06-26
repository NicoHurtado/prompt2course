import asyncio
import logging
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from django.conf import settings

logger = logging.getLogger(__name__)


class YouTubeService:
    """Servicio para buscar videos educativos en YouTube usando la API v3"""
    
    def __init__(self):
        self.api_key = settings.YOUTUBE_DATA_API_KEY
        self._youtube = None
    
    @property
    def youtube(self):
        """Lazy initialization of YouTube API client"""
        if self._youtube is None:
            if not self.api_key:
                raise ValueError("YouTube Data API key not configured")
            self._youtube = build('youtube', 'v3', developerKey=self.api_key)
        return self._youtube
    
    async def search_educational_videos(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Buscar videos educativos en YouTube basados en una consulta
        """
        try:
            logger.info(f"Buscando videos para: {query}")
            
            # Realizar búsqueda asíncrona
            search_results = await asyncio.to_thread(
                self._search_videos_sync,
                query,
                max_results
            )
            
            videos = []
            for item in search_results.get('items', []):
                video_data = self._extract_video_data(item)
                if video_data:
                    videos.append(video_data)
            
            logger.info(f"Encontrados {len(videos)} videos para la consulta: {query}")
            return videos
            
        except Exception as e:
            logger.error(f"Error buscando videos en YouTube: {e}")
            # Retornar lista vacía en caso de error
            return []
    
    async def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener detalles específicos de un video por su ID
        """
        try:
            logger.info(f"Obteniendo detalles del video: {video_id}")
            
            video_details = await asyncio.to_thread(
                self._get_video_details_sync,
                video_id
            )
            
            if video_details.get('items'):
                return self._extract_detailed_video_data(video_details['items'][0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles del video {video_id}: {e}")
            return None
    
    async def search_videos_for_chunk(self, chunk_data: Dict[str, Any], course_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Buscar videos específicos para un chunk de contenido
        """
        try:
            # Usar la consulta específica del chunk si existe
            search_query = chunk_data.get('video_search_query')
            
            if not search_query:
                # Generar consulta basada en el contenido del chunk
                content = chunk_data.get('content', '')
                search_query = self._generate_search_query_from_content(content, course_metadata)
            
            # Buscar videos
            videos = await self.search_educational_videos(search_query, max_results=3)
            
            # Filtrar videos apropiados
            filtered_videos = self._filter_appropriate_videos(videos, course_metadata)
            
            return filtered_videos[:1]  # Retornar solo el mejor video
            
        except Exception as e:
            logger.error(f"Error buscando videos para chunk: {e}")
            return []
    
    def _search_videos_sync(self, query: str, max_results: int) -> Dict[str, Any]:
        """
        Búsqueda síncrona en YouTube API
        """
        try:
            # Mejorar consulta para contenido educativo
            enhanced_query = f"{query} tutorial explicación"
            
            search_response = self.youtube.search().list(
                q=enhanced_query,
                part='id,snippet',
                maxResults=max_results,
                order='relevance',
                type='video',
                videoDefinition='any',
                videoDuration='medium',  # Videos de duración media (4-20 min)
                videoEmbeddable='true',  # Solo videos que se pueden embebir
                regionCode='ES',  # Preferir contenido en español
                relevanceLanguage='es'
            ).execute()
            
            return search_response
            
        except Exception as e:
            logger.error(f"Error en búsqueda síncrona de YouTube: {e}")
            raise
    
    def _get_video_details_sync(self, video_id: str) -> Dict[str, Any]:
        """
        Obtener detalles de video de forma síncrona
        """
        try:
            video_response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            ).execute()
            
            return video_response
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles síncronos del video: {e}")
            raise
    
    def _extract_video_data(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extraer datos relevantes de un item de búsqueda de YouTube
        """
        try:
            video_id = item['id']['videoId']
            snippet = item['snippet']
            
            # Validar que el video sea apropiado
            title = snippet.get('title', '')
            description = snippet.get('description', '')
            
            if not self._is_educational_content(title, description):
                return None
            
            video_data = {
                'video_id': video_id,
                'title': title,
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'embed_url': f"https://www.youtube.com/embed/{video_id}",
                'thumbnail_url': self._get_best_thumbnail(snippet.get('thumbnails', {})),
                'channel_title': snippet.get('channelTitle', ''),
                'published_at': snippet.get('publishedAt', ''),
                'duration': 'N/A',  # Se obtendrá después si es necesario
                'view_count': 0      # Se obtendrá después si es necesario
            }
            
            return video_data
            
        except Exception as e:
            logger.error(f"Error extrayendo datos del video: {e}")
            return None
    
    def _extract_detailed_video_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extraer datos detallados de un video específico
        """
        try:
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})
            
            video_data = {
                'video_id': item['id'],
                'title': snippet.get('title', ''),
                'url': f"https://www.youtube.com/watch?v={item['id']}",
                'embed_url': f"https://www.youtube.com/embed/{item['id']}",
                'thumbnail_url': self._get_best_thumbnail(snippet.get('thumbnails', {})),
                'duration': self._parse_duration(content_details.get('duration', '')),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'channel_title': snippet.get('channelTitle', ''),
                'published_at': snippet.get('publishedAt', ''),
                'description': snippet.get('description', '')[:200] + '...'  # Truncar descripción
            }
            
            return video_data
            
        except Exception as e:
            logger.error(f"Error extrayendo datos detallados del video: {e}")
            return {}
    
    def _get_best_thumbnail(self, thumbnails: Dict[str, Any]) -> str:
        """
        Obtener la mejor calidad de thumbnail disponible
        """
        # Prioridad: maxres > high > medium > default
        for quality in ['maxresdefault', 'high', 'medium', 'default']:
            if quality in thumbnails:
                return thumbnails[quality]['url']
        
        return 'https://img.youtube.com/vi/default/default.jpg'  # Fallback
    
    def _parse_duration(self, duration_string: str) -> str:
        """
        Convertir duración ISO 8601 a formato legible (MM:SS)
        """
        try:
            # Ejemplo: PT4M13S -> 4:13
            import re
            
            if not duration_string:
                return "N/A"
            
            # Extraer minutos y segundos
            pattern = r'PT(?:(\d+)M)?(?:(\d+)S)?'
            match = re.match(pattern, duration_string)
            
            if match:
                minutes = int(match.group(1) or 0)
                seconds = int(match.group(2) or 0)
                return f"{minutes}:{seconds:02d}"
            
            return "N/A"
            
        except Exception:
            return "N/A"
    
    def _is_educational_content(self, title: str, description: str) -> bool:
        """
        Determinar si el contenido es educativo basado en título y descripción
        """
        # Palabras clave que indican contenido educativo
        educational_keywords = [
            'tutorial', 'aprende', 'curso', 'explicación', 'introducción',
            'guía', 'clase', 'lección', 'enseñanza', 'formación',
            'principiantes', 'básico', 'fundamentos', 'conceptos'
        ]
        
        # Palabras que indican contenido no educativo
        exclude_keywords = [
            'música', 'canción', 'trailer', 'película', 'gaming',
            'vlog', 'reacción', 'unboxing', 'review'
        ]
        
        text = (title + ' ' + description).lower()
        
        # Verificar exclusiones primero
        for keyword in exclude_keywords:
            if keyword in text:
                return False
        
        # Verificar contenido educativo
        for keyword in educational_keywords:
            if keyword in text:
                return True
        
        # Si no hay indicadores claros, aceptar por defecto
        return True
    
    def _generate_search_query_from_content(self, content: str, course_metadata: Dict[str, Any]) -> str:
        """
        Generar consulta de búsqueda basada en el contenido del chunk
        """
        try:
            # Extraer palabras clave del contenido
            import re
            
            # Remover markdown y obtener texto limpio
            clean_content = re.sub(r'[*#`]', '', content)
            words = clean_content.split()[:20]  # Primeras 20 palabras
            
            # Combinar con información del curso
            course_topic = course_metadata.get('title', '').split()[0:3]  # Primeras 3 palabras del título
            level = course_metadata.get('level', 'principiante')
            
            # Crear consulta optimizada
            query_parts = course_topic + [level, 'tutorial']
            query = ' '.join(query_parts)
            
            return query[:50]  # Limitar longitud
            
        except Exception as e:
            logger.error(f"Error generando consulta de búsqueda: {e}")
            return "tutorial educativo"
    
    def _filter_appropriate_videos(self, videos: List[Dict[str, Any]], course_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filtrar videos apropiados para el nivel del curso
        """
        level = course_metadata.get('level', 'principiante').lower()
        
        filtered_videos = []
        for video in videos:
            title = video.get('title', '').lower()
            
            # Filtros básicos de calidad
            if len(title) < 10:  # Títulos muy cortos
                continue
                
            # Filtro por nivel
            if level == 'principiante':
                if any(word in title for word in ['avanzado', 'expert', 'profesional']):
                    continue
            elif level == 'avanzado':
                if any(word in title for word in ['básico', 'principiante', 'introducción']):
                    continue
            
            filtered_videos.append(video)
        
        return filtered_videos


# Instancia global del servicio
youtube_service = YouTubeService() 