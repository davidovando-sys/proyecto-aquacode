import unicodedata


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto or ''))
                   if not unicodedata.combining(c)).casefold().strip()


def resolver_comuna(valor):
    from .models import Comuna
    valor = str(valor or '').strip()
    if valor.isdigit():
        return Comuna.objects.filter(pk=valor.zfill(5)).first()
    coincidencias = [c for c in Comuna.objects.all() if normalizar(c.nombre) == normalizar(valor)]
    return coincidencias[0] if len(coincidencias) == 1 else None


def exigir_comuna(valor):
    comuna = resolver_comuna(valor)
    if comuna is None:
        raise ValueError('Selecciona una comuna válida de la lista de sugerencias.')
    return comuna
