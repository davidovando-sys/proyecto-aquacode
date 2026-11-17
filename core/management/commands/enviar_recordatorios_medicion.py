from django.core.management.base import BaseCommand, CommandError

from core.recordatorios import enviar_recordatorios_pendientes


class Command(BaseCommand):
    help = 'Envía recordatorios a usuarios que llevan 1 o 7 días sin registrar mediciones.'

    def handle(self, *args, **options):
        resultado = enviar_recordatorios_pendientes()
        resumen = (
            f"Revisados: {resultado['usuarios_revisados']}. "
            f"Enviados: {resultado['enviados']}. "
            f"Omitidos: {resultado['omitidos']}. "
            f"Errores: {resultado['errores']}."
        )

        if resultado['errores']:
            raise CommandError(resumen)

        self.stdout.write(self.style.SUCCESS(resumen))
