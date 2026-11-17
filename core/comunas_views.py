from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .comunas import normalizar
from .models import Comuna


@require_GET
def buscar_comunas(request):
    consulta = normalizar(request.GET.get('q', ''))[:100]
    if len(consulta) < 2:
        return JsonResponse({'results': []})
    resultados = [
        {'codigo': c.codigo, 'nombre': c.nombre, 'region': c.region}
        for c in Comuna.objects.all() if consulta in normalizar(c.nombre)
    ]
    return JsonResponse({'results': resultados})
