from django.core.paginator import Paginator


def paginar(request, queryset, por_pagina=10, parametro='page'):
    paginador = Paginator(queryset, por_pagina)
    return paginador.get_page(request.GET.get(parametro, 1))