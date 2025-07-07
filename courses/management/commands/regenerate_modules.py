from django.core.management.base import BaseCommand
from django.utils import timezone
from courses.models import Course, Module
from generation.tasks import regenerate_missing_modules


class Command(BaseCommand):
    help = 'Regenera módulos faltantes para cursos específicos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--course-id',
            type=str,
            help='UUID del curso específico a regenerar',
        )
        parser.add_argument(
            '--all-incomplete',
            action='store_true',
            help='Regenerar módulos faltantes para todos los cursos incompletos',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué módulos se regenerarían sin ejecutar',
        )

    def handle(self, *args, **options):
        course_id = options.get('course_id')
        all_incomplete = options.get('all_incomplete')
        dry_run = options.get('dry_run')

        if not course_id and not all_incomplete:
            self.stdout.write(
                self.style.ERROR('Debes especificar --course-id o --all-incomplete')
            )
            return

        courses_to_check = []

        if course_id:
            try:
                course = Course.objects.get(id=course_id)
                courses_to_check = [course]
            except Course.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Curso con ID {course_id} no encontrado')
                )
                return
        elif all_incomplete:
            # Buscar cursos que no están completos
            courses_to_check = Course.objects.exclude(
                status=Course.StatusChoices.COMPLETE
            ).order_by('-created_at')

        total_courses_with_issues = 0
        total_missing_modules = 0

        for course in courses_to_check:
            # Verificar módulos faltantes
            missing_modules = []
            for module_number in range(1, course.total_modules + 1):
                existing_module = Module.objects.filter(
                    course=course, 
                    module_order=module_number
                ).first()
                if not existing_module or existing_module.chunks.count() == 0:
                    missing_modules.append(module_number)

            if missing_modules:
                total_courses_with_issues += 1
                total_missing_modules += len(missing_modules)
                
                self.stdout.write(
                    f"\n📚 Curso: {course.title} (ID: {course.id})"
                )
                self.stdout.write(
                    f"   Status: {course.get_status_display()}"
                )
                self.stdout.write(
                    f"   Módulos faltantes: {missing_modules}"
                )
                self.stdout.write(
                    f"   Total módulos esperados: {course.total_modules}"
                )

                if not dry_run:
                    try:
                        # Ejecutar regeneración
                        task_result = regenerate_missing_modules.delay(str(course.id))
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"   ✅ Tarea de regeneración iniciada: {task_result.id}"
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"   ❌ Error iniciando regeneración: {str(e)}"
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"   🔍 DRY RUN: Se regenerarían {len(missing_modules)} módulos"
                        )
                    )
            else:
                if course_id:  # Solo mostrar si es curso específico
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Curso {course.title} tiene todos los módulos completos"
                        )
                    )

        # Resumen final
        self.stdout.write(f"\n📊 RESUMEN:")
        self.stdout.write(f"   Cursos revisados: {len(courses_to_check)}")
        self.stdout.write(f"   Cursos con módulos faltantes: {total_courses_with_issues}")
        self.stdout.write(f"   Total módulos a regenerar: {total_missing_modules}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n🔍 Este fue un DRY RUN. Para ejecutar realmente, omite --dry-run"
                )
            )
        elif total_courses_with_issues > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n🚀 Se iniciaron {total_courses_with_issues} tareas de regeneración"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✅ No se encontraron cursos que requieran regeneración"
                )
            ) 