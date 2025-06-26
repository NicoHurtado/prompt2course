#!/usr/bin/env python3
"""
Script para crear datos de muestra para P2C (Prompt2Course)
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from courses.models import Course, Module, Chunk, Video, Quiz, UserProgress
from django.contrib.auth.models import User
import uuid
import json

def create_sample_course():
    """Crear un curso de muestra completo"""
    
    # Crear curso
    course = Course.objects.create(
        user_prompt="Quiero aprender Python desde cero",
        user_level=Course.LevelChoices.PRINCIPIANTE,
        user_interests=["programación", "desarrollo web", "automatización"],
        status=Course.StatusChoices.COMPLETE,
        title="Programación en Python desde Cero",
        description="Un curso completo para aprender Python desde los conceptos más básicos hasta proyectos prácticos. Perfecto para principiantes que quieren adentrarse en el mundo de la programación.",
        prerequisites=["Conocimientos básicos de computación", "Ganas de aprender", "Tiempo para practicar"],
        total_modules=4,
        module_list=[
            "Introducción y Configuración del Entorno",
            "Variables, Tipos de Datos y Operadores",
            "Estructuras de Control y Funciones",
            "Proyecto Final: Calculadora Avanzada"
        ],
        topics=["Variables", "Funciones", "Loops", "Condicionales", "Debugging", "Buenas Prácticas"],
        introduction="¡Bienvenido al mundo de Python! En este curso aprenderás desde cero uno de los lenguajes de programación más populares y versátiles del mundo. Python es usado en desarrollo web, análisis de datos, inteligencia artificial y mucho más.",
        podcast_script="""
María: ¡Hola! Soy María y te doy la bienvenida a este curso de Python.

Carlos: Y yo soy Carlos. Hoy comenzaremos un viaje increíble en el mundo de la programación.

María: Python es perfecto para principiantes porque su sintaxis es muy clara y fácil de entender.

Carlos: Exactamente. Al final de este curso, podrás crear tus propios programas y automatizar tareas.

María: ¡Empecemos esta aventura juntos!
        """,
        podcast_audio_url="https://www.learningcontainer.com/wp-content/uploads/2020/02/Kalimba.mp3",
        total_size_estimate="~500KB contenido interactivo",
        final_project_data={
            "title": "Calculadora Avanzada",
            "description": "Crear una calculadora que maneje operaciones básicas y avanzadas",
            "objectives": [
                "Aplicar conceptos de funciones",
                "Manejar entrada del usuario",
                "Implementar validación de errores"
            ],
            "deliverables": [
                "Código fuente comentado",
                "Documentación del proyecto",
                "Video demo del funcionamiento"
            ]
        }
    )
    
    print(f"✅ Curso creado: {course.title} (ID: {course.course_id})")
    
    # Crear módulos
    modules_data = [
        {
            "title": "Introducción y Configuración del Entorno",
            "description": "Aprende qué es Python, por qué es importante y cómo configurar tu entorno de desarrollo.",
            "objective": "Al finalizar este módulo sabrás instalar Python y escribir tu primer programa.",
            "concepts": ["Python", "Instalación", "IDE", "Variables básicas", "Print"],
            "chunks": [
                {
                    "title": "¿Qué es Python y por qué aprenderlo?",
                    "content": """Python es un lenguaje de programación de alto nivel, interpretado y de propósito general creado por Guido van Rossum en 1991. Se ha convertido en uno de los lenguajes más populares del mundo debido a su sintaxis clara y legible.

**¿Por qué Python es tan popular?**

1. **Sintaxis simple**: Python se lee casi como inglés, lo que lo hace perfecto para principiantes
2. **Versatilidad**: Se usa en desarrollo web, análisis de datos, inteligencia artificial, automatización y más
3. **Gran comunidad**: Millones de desarrolladores contribuyen con librerías y recursos
4. **Mercado laboral**: Alta demanda en empresas de tecnología

**Ejemplos de lo que puedes hacer con Python:**
- Crear sitios web (Instagram, YouTube usan Python)
- Análisis de datos y ciencia de datos
- Inteligencia artificial y machine learning
- Automatizar tareas repetitivas
- Crear juegos y aplicaciones

Python es usado por gigantes tecnológicos como Google, Netflix, Spotify y NASA. ¡Estás tomando una excelente decisión al aprenderlo!"""
                },
                {
                    "title": "Instalación de Python en tu computadora",
                    "content": """Para comenzar a programar en Python, necesitas instalarlo en tu sistema. Te guiaré paso a paso:

**Paso 1: Descargar Python**
1. Ve a https://python.org
2. Haz clic en "Download Python 3.x.x" (la versión más reciente)
3. Descarga el instalador para tu sistema operativo

**Paso 2: Instalar Python**

*En Windows:*
1. Ejecuta el instalador descargado
2. **¡MUY IMPORTANTE!** Marca la casilla "Add Python to PATH"
3. Selecciona "Install Now"
4. Espera a que termine la instalación

*En macOS:*
1. Abre el archivo .pkg descargado
2. Sigue las instrucciones del instalador
3. Python se instalará automáticamente

*En Linux:*
Python generalmente viene preinstalado. Verifica escribiendo en terminal:
```
python3 --version
```

**Verificar la instalación:**
Abre la terminal/command prompt y escribe:
```
python --version
```
Deberías ver algo como "Python 3.11.0"

Si ves un error, repite el proceso asegurándote de marcar "Add to PATH" en Windows."""
                },
                {
                    "title": "Configuración del entorno de desarrollo (IDE)",
                    "content": """Un IDE (Integrated Development Environment) es tu herramienta principal para escribir código. Te recomiendo dos opciones excelentes para principiantes:

**Opción 1: Visual Studio Code (RECOMENDADO)**

VS Code es gratuito, liviano y muy popular entre desarrolladores.

*Instalación:*
1. Ve a https://code.visualstudio.com/
2. Descarga e instala VS Code
3. Abre VS Code
4. Ve a Extensions (Ctrl+Shift+X)
5. Instala la extensión "Python" de Microsoft

*Configuración básica:*
1. Crea una carpeta para tus proyectos Python
2. Abre VS Code
3. File > Open Folder > Selecciona tu carpeta
4. Crea un archivo nuevo: archivo.py

**Opción 2: PyCharm Community (Alternativa)**

PyCharm es más robusto pero consume más recursos.

1. Ve a https://www.jetbrains.com/pycharm/
2. Descarga "Community Edition" (gratuita)
3. Instala siguiendo las instrucciones

**Configuración de tu primer proyecto:**
```
# Crea esta estructura de carpetas:
mi_curso_python/
    ├── modulo_1/
    ├── modulo_2/
    └── proyectos/
```

**Consejo profesional:** Organiza tu código desde el principio. Crea carpetas separadas para cada módulo del curso."""
                },
                {
                    "title": "Variables en Python: Almacenando información",
                    "content": """Las variables son contenedores que almacenan datos. En Python, crear variables es súper fácil.

**Sintaxis básica:**
```python
nombre_variable = valor
```

**Ejemplos prácticos:**
```python
# Variables de texto (strings)
nombre = "Ana"
apellido = 'García'
ciudad = "Madrid"

# Variables numéricas
edad = 25
altura = 1.65
peso = 60.5

# Variables booleanas (True/False)
es_estudiante = True
tiene_trabajo = False
```

**Reglas para nombres de variables:**
1. Deben comenzar con letra o guión bajo (_)
2. Pueden contener letras, números y guiones bajos
3. No pueden contener espacios
4. Son sensibles a mayúsculas (edad ≠ Edad)

**Ejemplos de nombres válidos:**
```python
nombre = "Juan"
nombre_completo = "Juan Pérez"
edad2023 = 30
_variable_privada = "secreto"
```

**Ejemplos de nombres INVÁLIDOS:**
```python
# 2edad = 30        # No puede empezar con número
# nombre completo = "Juan"  # No puede tener espacios
# class = "A"       # 'class' es palabra reservada
```

**Convención de nombres (PEP 8):**
- Usa snake_case: `nombre_completo` en lugar de `nombreCompleto`
- Nombres descriptivos: `precio_producto` en lugar de `p`

**Verificar el tipo de variable:**
```python
nombre = "Ana"
edad = 25
print(type(nombre))  # <class 'str'>
print(type(edad))    # <class 'int'>
```"""
                },
                {
                    "title": "La función print(): Mostrando información",
                    "content": """La función `print()` es una de las más importantes en Python. Te permite mostrar información en la pantalla.

**Sintaxis básica:**
```python
print("Hola, mundo!")
```

**Ejemplos básicos:**
```python
print("¡Bienvenido a Python!")
print("Este es mi primer programa")
print(123)
print(3.14159)
```

**Imprimiendo variables:**
```python
nombre = "Carlos"
edad = 28
ciudad = "Barcelona"

print(nombre)
print(edad)
print(ciudad)
```

**Combinando texto y variables:**
```python
nombre = "María"
edad = 22

# Método 1: Concatenación
print("Hola, mi nombre es " + nombre)

# Método 2: Comas (automáticamente añade espacios)
print("Mi nombre es", nombre, "y tengo", edad, "años")

# Método 3: f-strings (MÁS RECOMENDADO)
print(f"Mi nombre es {nombre} y tengo {edad} años")
```

**Caracteres especiales:**
```python
# Salto de línea
print("Primera línea\\nSegunda línea")

# Tabulación
print("Nombre:\\tCarlos")
print("Edad:\\t25")

# Comillas dentro de strings
print("Ella dijo: \\"¡Hola!\\"")
print('El libro "1984" es excelente')
```

**Parámetros útiles de print():**
```python
# Cambiar el separador
print("A", "B", "C", sep="-")  # A-B-C

# Cambiar el final (por defecto es \\n)
print("Hola", end=" ")
print("Mundo")  # Imprime: Hola Mundo

# Múltiples líneas
print('''Este es un texto
que ocupa varias
líneas''')
```

**Ejercicio práctico:**
```python
# Crea un programa que muestre tu información personal
nombre = "Tu nombre"
edad = 20
ciudad = "Tu ciudad"
hobby = "Tu hobby favorito"

print(f"¡Hola! Soy {nombre}")
print(f"Tengo {edad} años")
print(f"Vivo en {ciudad}")
print(f"Me gusta {hobby}")
```"""
                },
                {
                    "title": "Tu primer programa completo",
                    "content": """¡Es hora de crear tu primer programa completo en Python! Vamos a crear algo interactivo y útil.

**Proyecto: Tarjeta de presentación personal**

Crea un archivo llamado `mi_presentacion.py` y escribe:

```python
# Mi primer programa en Python
# Tarjeta de presentación personal

print("=" * 40)
print("     TARJETA DE PRESENTACIÓN")
print("=" * 40)

# Mis datos personales
nombre = "Tu Nombre Completo"
edad = 25
profesion = "Estudiante de Python"
ciudad = "Tu Ciudad"
email = "tu_email@ejemplo.com"

# Mostrar información
print(f"Nombre: {nombre}")
print(f"Edad: {edad} años")
print(f"Profesión: {profesion}")
print(f"Ubicación: {ciudad}")
print(f"Email: {email}")

print("-" * 40)
print("¡Gracias por conocerme!")
print("Sígueme en mi viaje aprendiendo Python")
print("=" * 40)
```

**Resultado esperado:**
```
========================================
     TARJETA DE PRESENTACIÓN
========================================
Nombre: Tu Nombre Completo
Edad: 25 años
Profesión: Estudiante de Python
Ubicación: Tu Ciudad
Email: tu_email@ejemplo.com
----------------------------------------
¡Gracias por conocerme!
Sígueme en mi viaje aprendiendo Python
========================================
```

**Cómo ejecutar tu programa:**

1. **En VS Code:**
   - Abre tu archivo .py
   - Presiona F5 o click en "Run Python File"

2. **En terminal:**
   ```
   python mi_presentacion.py
   ```

**Desafío adicional:**
Modifica el programa para que calcule automáticamente en qué año naciste:
```python
año_actual = 2024
año_nacimiento = año_actual - edad
print(f"Año de nacimiento: {año_nacimiento}")
```

**¡Felicitaciones!** Has creado tu primer programa completo en Python. Has aprendido a:
- Usar variables
- Formatear texto con f-strings
- Organizar código con comentarios
- Crear output atractivo

Este es solo el comienzo de tu aventura en Python. En el próximo módulo aprenderemos sobre diferentes tipos de datos y operaciones más avanzadas."""
                }
            ]
        },
        {
            "title": "Variables, Tipos de Datos y Operadores",
            "description": "Domina los conceptos fundamentales de variables, tipos de datos y operaciones en Python.",
            "objective": "Serás capaz de trabajar con diferentes tipos de datos y realizar operaciones básicas.",
            "concepts": ["Variables", "Strings", "Números", "Booleanos", "Operadores", "Input"],
            "chunks": [
                {
                    "title": "Tipos de datos fundamentales en Python",
                    "content": """Python maneja varios tipos de datos que debes conocer. Cada tipo tiene características y usos específicos.

**Los 4 tipos básicos:**

**1. Strings (str) - Texto**
```python
nombre = "María"
apellido = 'González'
frase = "¡Hola, mundo!"
parrafo = '''Este es un texto
que puede ocupar
múltiples líneas'''

# Verificar el tipo
print(type(nombre))  # <class 'str'>
```

**2. Integers (int) - Números enteros**
```python
edad = 25
población = 47000000
temperatura = -5
año = 2024

print(type(edad))  # <class 'int'>
```

**3. Floats (float) - Números decimales**
```python
altura = 1.75
precio = 19.99
pi = 3.14159
temperatura = 36.5

print(type(altura))  # <class 'float'>
```

**4. Booleans (bool) - Verdadero/Falso**
```python
es_mayor_edad = True
tiene_descuento = False
llueve = True

print(type(es_mayor_edad))  # <class 'bool'>
```

**Conversión entre tipos:**
```python
# String a número
edad_texto = "25"
edad_numero = int(edad_texto)
print(edad_numero + 5)  # 30

altura_texto = "1.75"
altura_numero = float(altura_texto)
print(altura_numero * 2)  # 3.5

# Número a string
edad = 25
edad_texto = str(edad)
print("Tengo " + edad_texto + " años")

# A boolean
print(bool(1))      # True
print(bool(0))      # False
print(bool(""))     # False
print(bool("hola")) # True
```

**Funciones útiles:**
```python
numero = 3.7
print(round(numero))     # 4 (redondear)
print(abs(-5))          # 5 (valor absoluto)
print(len("Python"))    # 6 (longitud de string)
```"""
                },
                {
                    "title": "Trabajando con Strings: Texto en Python",
                    "content": """Los strings son secuencias de caracteres. Python ofrece muchas herramientas para trabajar con texto.

**Creación de strings:**
```python
# Diferentes formas de crear strings
nombre = "Ana"
apellido = 'Martínez'
mensaje = '''Este es un mensaje
que puede ocupar
varias líneas'''

# String vacío
vacio = ""
```

**Concatenación (unir strings):**
```python
nombre = "Carlos"
apellido = "Ruiz"

# Método 1: Operador +
nombre_completo = nombre + " " + apellido
print(nombre_completo)  # Carlos Ruiz

# Método 2: f-strings (RECOMENDADO)
presentacion = f"Hola, soy {nombre} {apellido}"
print(presentacion)  # Hola, soy Carlos Ruiz

# Método 3: .format()
mensaje = "Mi nombre es {} y mi apellido es {}".format(nombre, apellido)
print(mensaje)
```

**Métodos útiles de strings:**
```python
texto = "Python es Genial"

# Convertir a mayúsculas/minúsculas
print(texto.upper())      # PYTHON ES GENIAL
print(texto.lower())      # python es genial
print(texto.title())      # Python Es Genial

# Buscar y reemplazar
print(texto.find("es"))          # 7 (posición donde encuentra "es")
print(texto.replace("Genial", "Increíble"))  # Python es Increíble

# Dividir strings
frase = "manzana,banana,naranja"
frutas = frase.split(",")
print(frutas)  # ['manzana', 'banana', 'naranja']

# Unir strings
palabras = ["Python", "es", "awesome"]
frase = " ".join(palabras)
print(frase)  # Python es awesome
```

**Caracteres de escape:**
```python
# Comillas dentro de strings
print("Ella dijo: \\"¡Hola!\\"")
print('El libro \\'1984\\' es excelente')

# Otros caracteres especiales
print("Primera línea\\nSegunda línea")  # Salto de línea
print("Columna1\\tColumna2")            # Tabulación
print("C:\\\\Users\\\\Documentos")        # Barra invertida
```

**Indexing y slicing:**
```python
palabra = "Python"

# Acceder a caracteres individuales (empezando en 0)
print(palabra[0])   # P
print(palabra[1])   # y
print(palabra[-1])  # n (último carácter)
print(palabra[-2])  # o (penúltimo carácter)

# Slicing (extraer porciones)
print(palabra[0:3])   # Pyt (desde posición 0 hasta 3, sin incluir 3)
print(palabra[2:])    # thon (desde posición 2 hasta el final)
print(palabra[:4])    # Pyth (desde el inicio hasta posición 4)
print(palabra[::2])   # Pto (cada 2 caracteres)
```

**Ejemplo práctico:**
```python
# Procesador de nombres
nombre_usuario = input("Introduce tu nombre completo: ")

# Limpiar y formatear
nombre_limpio = nombre_usuario.strip().title()
iniciales = nombre_limpio[0] + nombre_limpio[nombre_limpio.find(" ") + 1]

print(f"Nombre formateado: {nombre_limpio}")
print(f"Iniciales: {iniciales}")
print(f"Longitud: {len(nombre_limpio)} caracteres")
```"""
                }
            ]
        }
    ]
    
    for i, module_data in enumerate(modules_data, 1):
        module = Module.objects.create(
            course=course,
            module_id=f"modulo_{i}",
            module_order=i,
            title=module_data["title"],
            description=module_data["description"],
            objective=module_data["objective"],
            concepts=module_data["concepts"],
            summary=f"En este módulo aprendiste sobre {', '.join(module_data['concepts'][:3])} y más.",
            practical_exercise={
                "title": f"Ejercicio Práctico - Módulo {i}",
                "description": f"Pon en práctica lo aprendido en el módulo {i}",
                "steps": [
                    "Abre tu editor de código",
                    "Crea un nuevo archivo Python",
                    "Implementa los conceptos vistos",
                    "Ejecuta y prueba tu código"
                ]
            }
        )
        
        print(f"  📚 Módulo creado: {module.title}")
        
        # Añadir datos de video si el campo existe
        if hasattr(module, 'video_data'):
            module.video_data = {
                "video_id": f"demo_video_modulo_{i}",
                "title": f"Tutorial Completo: {module_data['title']}",
                "url": f"https://www.youtube.com/watch?v=demoM{i}",
                "embed_url": f"https://www.youtube.com/embed/demoM{i}",
                "thumbnail_url": "https://img.youtube.com/vi/default/maxresdefault.jpg",
                "duration": "15:45",
                "view_count": 25300,
                "description": f"Video tutorial completo sobre {module_data['title'].lower()}"
            }
            module.save()
        
        # Crear chunks para este módulo
        for j, chunk_data in enumerate(module_data["chunks"], 1):
            chunk = Chunk.objects.create(
                module=module,
                chunk_id=f"modulo_{i}_chunk_{j}",
                chunk_order=j,
                total_chunks=len(module_data["chunks"]),
                title=chunk_data["title"],
                content=chunk_data["content"]
            )
            
        # Los videos ahora están a nivel de módulo, no de chunk
        
        # Crear quiz para el módulo
        Quiz.objects.create(
            module=module,
            question=f"¿Cuál es el concepto más importante del módulo {i}?",
            options=[
                module_data["concepts"][0] if len(module_data["concepts"]) > 0 else "Opción A",
                "Opción incorrecta B",
                "Opción incorrecta C",
                "Opción incorrecta D"
            ],
            correct_answer=0,
            explanation=f"Correcto! {module_data['concepts'][0]} es fundamental en este módulo porque es la base para entender los conceptos posteriores."
        )
    
    print(f"🎉 Curso completo creado exitosamente!")
    print(f"🔗 Visita: http://127.0.0.1:8000/course/{course.id}/")
    return course

def create_sample_user_progress(course):
    """Crear progreso de usuario de muestra"""
    try:
        user = User.objects.get(username='admin')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        print(f"👤 Usuario admin creado (password: admin123)")
    
    # Crear progreso
    first_module = course.modules.first()
    first_chunk = first_module.chunks.first() if first_module else None
    
    progress = UserProgress.objects.create(
        user=user,
        course=course,
        current_module=first_module,
        current_chunk=first_chunk,
        completed_chunks=[first_chunk.chunk_id] if first_chunk else []
    )
    
    print(f"📊 Progreso de usuario creado")
    return progress

if __name__ == "__main__":
    print("🚀 Creando datos de muestra para P2C...")
    
    # Limpiar datos existentes si existen
    Course.objects.filter(title__contains="Python desde Cero").delete()
    
    # Crear datos de muestra
    course = create_sample_course()
    progress = create_sample_user_progress(course)
    
    print("\n" + "="*50)
    print("✅ DATOS DE MUESTRA CREADOS EXITOSAMENTE!")
    print("="*50)
    print(f"🔗 URL del curso: http://127.0.0.1:8000/course/{course.id}/")
    print(f"🔗 Admin: http://127.0.0.1:8000/admin/")
    print(f"👤 Usuario: admin / admin123")
    print("="*50) 