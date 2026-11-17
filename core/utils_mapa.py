from .geo_comunas import punto_en_comuna


def coordenadas_para_mapa(m):
    """Devuelve (lat, lng, aproximada) para una Medicion, o None si no se puede ubicar."""
    if m.latitud is not None and m.longitud is not None:
        return m.latitud, m.longitud, False

    if not m.comuna_id:  # codigo es la PK de Comuna, así que comuna_id es el código
        return None

    punto = punto_en_comuna(m.comuna_id, m.pk)
    if punto is None:
        return None
    return punto[0], punto[1], True