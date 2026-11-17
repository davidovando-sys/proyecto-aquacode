from django import template

register = template.Library()


@register.inclusion_tag('partials/paginacion.html', takes_context=True)
def paginacion(context, pagina_obj, ancla=''):
    request = context['request']
    # Conserva todos los filtros y elimina la página actual.
    parametros = request.GET.copy()
    parametros.pop('page', None)

    return {
        'pagina_obj': pagina_obj,
        'parametros_url': parametros.urlencode(),
        'ancla': ancla,
        'paginas': list(pagina_obj.paginator.get_elided_page_range(
            pagina_obj.number, on_each_side=2, on_ends=1
        )),
    }