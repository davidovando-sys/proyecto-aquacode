# Catálogo de comunas y cartografía

El catálogo `comunas.json` contiene 346 códigos CUT con nombre y región.
Se importa con la migración `0012_cargar_comunas`; las ubicaciones antiguas
solo se relacionan cuando su nombre normalizado tiene una coincidencia única.
Los textos originales y registros sin coincidencia se conservan.

Fuente geométrica: [IDE Chile, DPA 2020, publicada por SUBPESCA](https://geoportal.subpesca.cl/server/rest/services/Hosted/COMUNA/FeatureServer/0).
Descarga: 2 de noviembre de 2026. Campos: cut_com, cut_reg, comuna, region.
Consulta: `/query?where=1%3D1&outFields=cut_reg,cut_com,region,comuna&outSR=4326&maxAllowableOffset=0.001&geometryPrecision=5&f=geojson`.

La capa contiene 345 geometrías continentales e insulares. Antártica (12202)
se incluye en el catálogo conforme al [CUT de SUBDERE](https://www.subdere.cl/sites/default/files/documentos/articles-73111_recurso_2.pdf),
sin inventar un polígono. Está disponible en búsqueda y filtros.
Los límites son una representación simplificada para navegación, no para deslindes.

`scripts/preparar_comunas.py` prepara una descarga nueva, simplifica los anillos,
redondea coordenadas y genera archivos por región. Conservar este catálogo como
entrada histórica de la migración; futuros cambios deben tener su propia migración.
Los archivos se sirven localmente desde Django; no hay servicio externo de comunas
en ejecución. El panel dibuja los polígonos sobre un fondo neutro y no solicita
teselas externas. Leaflet se carga desde su CDN y sí requiere conexión.

Instalación: `python manage.py migrate`. Las relaciones son opcionales para
conservar datos antiguos, pero los formularios nuevos exigen comunas válidas.
La comuna de una cuenta no modifica las mediciones históricas.

El buscador descarga `static/data/catalogo-comunas.json` una vez por página y filtra
localmente desde dos letras, sin consultas de red por cada búsqueda. Su contenido
debe coincidir con `core/data/comunas.json`; Django mantiene la validación al guardar.
