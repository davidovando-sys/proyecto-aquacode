"""Prepara la descarga GeoJSON de SUBPESCA sin dependencias GIS adicionales."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def simplificar(puntos, tolerancia=0.001):
    # Douglas-Peucker iterativo: conserva extremos, islas y anillos cerrados.
    conservar = {0, len(puntos) - 1}
    pendientes = [(0, len(puntos) - 1)]
    while pendientes:
        inicio, fin = pendientes.pop()
        a, b = puntos[inicio], puntos[fin]
        dx, dy = b[0] - a[0], b[1] - a[1]
        longitud = dx * dx + dy * dy
        mayor, indice = tolerancia ** 2, None
        for i in range(inicio + 1, fin):
            p = puntos[i]
            t = max(0, min(1, ((p[0]-a[0])*dx + (p[1]-a[1])*dy)/longitud)) if longitud else 0
            distancia = (p[0]-a[0]-t*dx)**2 + (p[1]-a[1]-t*dy)**2
            if distancia > mayor:
                mayor, indice = distancia, i
        if indice is not None:
            conservar.add(indice)
            pendientes.extend([(inicio, indice), (indice, fin)])
    resultado = [puntos[i] for i in sorted(conservar)]
    return resultado if len(resultado) >= 4 else puntos


def main():
    ruta = ROOT / 'static/data/comunas.geojson'
    datos = json.loads(ruta.read_text(encoding='utf-8'))
    assert not datos.get('exceededTransferLimit'), 'Descarga incompleta'
    catalogo = []
    for f in datos['features']:
        p = f['properties']
        comuna = dict(codigo=p['cut_com'].zfill(5), nombre=p['comuna'],
                      codigo_region=p['cut_reg'].zfill(2), region=p['region'])
        catalogo.append(comuna)
        f['properties'] = {'codigo': comuna['codigo']}
        g = f['geometry']
        poligonos = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        for poligono in poligonos:
            for i, anillo in enumerate(poligono):
                poligono[i] = [[round(x, 5) for x in punto] for punto in simplificar(anillo)]
    # La capa continental/insular no incluye el territorio antártico.
    catalogo.append(dict(codigo='12202', nombre='Antártica', codigo_region='12',
                         region='Magallanes y de la Antártica Chilena'))
    assert len({c['codigo'] for c in catalogo}) == 346
    (ROOT / 'core/data').mkdir(exist_ok=True)
    (ROOT / 'core/data/comunas.json').write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'static/data/catalogo-comunas.json').write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding='utf-8')
    ruta.write_text(json.dumps(datos, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    regiones = {c['codigo']: c['codigo_region'] for c in catalogo}
    for region in sorted(set(regiones.values())):
        regional = {'type': 'FeatureCollection', 'features': [
            f for f in datos['features'] if regiones[f['properties']['codigo']] == region]}
        (ROOT / f'static/data/comunas-{region}.geojson').write_text(
            json.dumps(regional, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'{len(catalogo)} comunas; {len(datos["features"])} geometrías; {ruta.stat().st_size} bytes')


if __name__ == '__main__':
    main()
