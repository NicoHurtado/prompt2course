# Prompt2Course (P2C) - Plataforma de Cursos con IA

Una plataforma web desarrollada en Django que permite crear cursos educativos utilizando inteligencia artificial. El proyecto incluye generación automática de contenido, módulos interactivos y una interfaz moderna para el aprendizaje.

## 🚀 Características

- **Generación automática de cursos** usando IA (Claude/Anthropic)
- **Sistema de módulos** con contenido estructurado
- **Interfaz web moderna** y responsive
- **API REST** para integraciones
- **Sistema de autenticación** y administración
- **Tareas asíncronas** con Celery
- **Caché** con Redis
- **Datos de ejemplo** incluidos para desarrollo

## 📋 Requisitos Previos

### Software Necesario
- **Docker** (versión 20.10 o superior)
- **Docker Compose** (versión 2.0 o superior)

### Verificar Instalación
```bash
# Verificar Docker
docker --version

# Verificar Docker Compose
docker-compose --version
```

### Instalar Docker (si no lo tienes)
- **Ubuntu/Debian**: [Instrucciones oficiales](https://docs.docker.com/engine/install/ubuntu/)
- **Windows**: [Docker Desktop](https://docs.docker.com/desktop/install/windows/)
- **macOS**: [Docker Desktop](https://docs.docker.com/desktop/install/mac/)

## 🛠️ Instalación y Configuración

### 1. Clonar el Repositorio
```bash
git clone https://github.com/NicoHurtado/prompt2course.git p2c
cd p2c
```

### 2. Configurar Variables de Entorno
Crear un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```env
# Django Configuration
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration (SQLite para desarrollo)
DATABASE_URL=sqlite:///db.sqlite3

# AI Services (opcionales para desarrollo)
CLAUDE_API_KEY=your-claude-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# YouTube API (opcional)
YOUTUBE_DATA_API_KEY=your-youtube-api-key

# AWS S3 Configuration (opcional)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_S3_BUCKET=prompt2course
AWS_REGION=us-east-2

# AWS Polly Configuration (opcional)
AWS_POLLY_VOICE_FEMALE=Lucia
AWS_POLLY_VOICE_MALE=Enrique
AWS_POLLY_ENGINE=neural

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Time Zone
TIME_ZONE=America/Bogota

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Cache Configuration
CACHE_URL=redis://redis:6379/1

# File Upload Settings
MAX_UPLOAD_SIZE=10485760  # 10MB in bytes
```

**Nota**: Para desarrollo local, puedes usar valores dummy en las API keys. El proyecto funcionará con datos de ejemplo.

### 3. Levantar el Proyecto con Docker
```bash
# Construir las imágenes y levantar los servicios
docker-compose up --build
```

Este comando:
- Construye la imagen de Django con todas las dependencias
- Levanta Redis para Celery y caché
- Ejecuta las migraciones automáticamente
- Crea datos de ejemplo si la base está vacía
- Inicia el servidor de desarrollo

### 4. Verificar que Todo Funcione
Una vez que los contenedores estén corriendo, verás logs como:
```
✅ DATOS DE MUESTRA CREADOS EXITOSAMENTE!
🔗 URL del curso: http://127.0.0.1:8000/course/...
🔗 Admin: http://127.0.0.1:8000/admin/
👤 Usuario: admin / admin123
```

## 🌐 Acceso a la Aplicación

### URLs Principales
- **Página principal**: [http://localhost:8000](http://localhost:8000)
- **Admin de Django**: [http://localhost:8000/admin](http://localhost:8000/admin)
  - Usuario: `admin`
  - Contraseña: `admin123`
- **API REST**: [http://localhost:8000/api](http://localhost:8000/api)

### Curso de Ejemplo
El sistema crea automáticamente un curso de ejemplo. La URL exacta aparece en los logs, pero será algo como:
`http://localhost:8000/course/[uuid-del-curso]/`

## 🛠️ Comandos Útiles

### 🚀 **Flujo de Desarrollo - ¿Qué comando usar?**

| Tipo de Cambio | Comando | Cuándo Usarlo |
|----------------|---------|---------------|
| **Código Python/HTML/CSS/JS** | `docker-compose up` | Cambios en archivos del proyecto |
| **requirements.txt** | `docker-compose up --build` | Agregar/quitar dependencias |
| **Dockerfile** | `docker-compose up --build` | Cambiar configuración de Docker |
| **docker-compose.yml** | `docker-compose down && docker-compose up` | Cambiar servicios/puertos |
| **Problemas/Conflictos** | `docker-compose down --remove-orphans && docker-compose up --build` | Errores o contenedores huérfanos |

### 📋 **Comandos Detallados**

#### **Desarrollo Normal**
```bash
# Primera vez o después de cambios en dependencias
docker-compose up --build

# Desarrollo diario (cambios en código)
docker-compose up

# Levantar en segundo plano
docker-compose up -d
```

#### **Gestión de Contenedores**
```bash
# Detener servicios (mantiene volúmenes)
docker-compose down

# Detener y eliminar volúmenes (¡CUIDADO: borra la base de datos!)
docker-compose down -v

# Detener y eliminar contenedores huérfanos
docker-compose down --remove-orphans

# Ver logs en tiempo real
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f web
docker-compose logs -f celery
```

#### **Comandos de Django**
```bash
# Ejecutar comandos de Django dentro del contenedor
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic
```

#### **Reiniciar Servicios**
```bash
# Reiniciar solo el servicio web
docker-compose restart web

# Reconstruir y reiniciar todo
docker-compose up --build --force-recreate
```

### 🔄 **Guía Rápida de Uso**

#### **Para tu día a día:**
1. **Primera vez:** `docker-compose up --build`
2. **Desarrollo normal:** `docker-compose up`
3. **Si hay problemas:** `docker-compose down --remove-orphans && docker-compose up --build`

#### **¿Por qué estos comandos?**

- **`docker-compose up`**: El código está montado como volumen, los cambios se ven inmediatamente
- **`docker-compose up --build`**: Reconstruye la imagen cuando cambias dependencias o Dockerfile
- **`docker-compose down`**: Detiene servicios pero mantiene datos
- **`--remove-orphans`**: Elimina contenedores viejos de configuraciones anteriores

## 📁 Estructura del Proyecto

```
p2c/
├── api/                 # API REST
├── courses/            # Aplicación principal de cursos
├── generation/         # Generación de contenido con IA
├── config/            # Configuración de Django
├── templates/         # Plantillas HTML
├── static/           # Archivos estáticos
├── logs/             # Logs de la aplicación
├── Dockerfile        # Configuración de Docker
├── docker-compose.yml # Orquestación de servicios
├── docker-entrypoint.sh # Script de inicio
├── requirements.txt  # Dependencias de Python
├── create_sample_data.py # Datos de ejemplo
└── manage.py         # Comando de Django
```

## 🔧 Desarrollo

### Modificar Código
El código está montado como volumen, por lo que los cambios se reflejan automáticamente sin necesidad de reconstruir la imagen.

### Agregar Dependencias
Si necesitas agregar nuevas dependencias:
1. Agrega la dependencia a `requirements.txt`
2. Reconstruye la imagen:
   ```bash
   docker-compose build
   docker-compose up
   ```

### Debugging
```bash
# Ver logs detallados
docker-compose logs -f web

# Acceder al shell del contenedor
docker-compose exec web bash

# Verificar estado de los servicios
docker-compose ps
```

## 🚨 Solución de Problemas

### Error: "Port already in use"
```bash
# Verificar qué está usando el puerto 8000
sudo lsof -i :8000

# Cambiar puerto en docker-compose.yml
ports:
  - "8001:8000"  # Cambiar 8000 por 8001
```

### Error: "Permission denied"
```bash
# En Linux, agregar tu usuario al grupo docker
sudo usermod -aG docker $USER
# Luego cerrar sesión y volver a entrar
```

### Error: "Connection refused" en Docker
```bash
# Verificar que Docker esté corriendo
sudo systemctl status docker

# Iniciar Docker si no está activo
sudo systemctl start docker
```

### Base de Datos Corrupta
```bash
# Eliminar base de datos y recrear
docker-compose down -v
docker-compose up --build
```

### Problemas con Redis
```bash
# Reiniciar solo Redis
docker-compose restart redis

# Ver logs de Redis
docker-compose logs redis
```

## 📝 Notas Importantes

### Datos de Ejemplo
- El sistema crea automáticamente datos de ejemplo al iniciar
- Estos datos se recrean cada vez que levantas los contenedores
- Para desarrollo, esto es suficiente

### Servicios Externos
- **Redis**: Requerido para Celery y caché
- **Anthropic/Claude**: Opcional, solo si quieres generar contenido real
- **AWS S3/Polly**: Opcional, para almacenamiento y síntesis de voz
- **PostgreSQL**: No requerido, el proyecto usa SQLite por defecto

### Rendimiento
- En desarrollo, el rendimiento puede ser lento en la primera carga
- Los contenedores se optimizan automáticamente después del primer uso
- Para producción, considera usar PostgreSQL y optimizaciones adicionales

## 🤝 Contribución

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia [MIT](LICENSE).

## 👥 Equipo

- **Nico Hurtado** - Desarrollador principal
- **José Duque** - Configuración Docker y documentación

---

## 🆘 Soporte

Si tienes problemas:
1. Revisa la sección de "Solución de Problemas"
2. Verifica que Docker esté corriendo
3. Revisa los logs con `docker-compose logs`
4. Abre un issue en el repositorio

¡Disfruta desarrollando con P2C! 🚀 