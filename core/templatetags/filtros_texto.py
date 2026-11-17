#permite que se pueda acortar el nombre de usuario en la barra de navegación,
#ya que el campo usa first_name para el nombre completo, por lo que esto toma solo la primera palabra
#(primer nombre)
from django import template

register = template.Library()

@register.filter
def primer_nombre(valor):
    if not valor:
        return ''

    return valor.strip().split()[0]