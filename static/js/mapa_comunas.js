document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('mapa-comunas');
    const status = document.getElementById('mapa-estado');
    const summary = new Map(JSON.parse(document.getElementById('resumen-comunas').textContent).map(c => [c.codigo, c]));
    function navigate(key, value) {
        const url = new URL(window.location.href); url.search = '';
        if (value) url.searchParams.set(key, value);
        window.location.assign(url);
    }
    document.getElementById('region-mapa').addEventListener('change', e => navigate('region', e.target.value));
    document.getElementById('buscar-comuna').addEventListener('comuna:selected', e => navigate('comuna', e.detail.codigo));
    if (!window.L) { status.textContent = 'No se pudo cargar el mapa. Puedes usar el buscador de comunas.'; return; }
    // Los polígonos locales son el mapa: no dependemos de servidores de teselas.
    const map = L.map(container, {minZoom: 3, maxZoom: 16}).setView([-33.45, -70.65], 9);
    map.attributionControl.addAttribution('Límites: IDE Chile / SUBPESCA');
    const selected = container.dataset.comuna;
    status.textContent = 'Cargando límites de las comunas…';
    try {
        const suffix = container.dataset.region ? `-${container.dataset.region}` : '';
        const response = await fetch(`${container.dataset.base}comunas${suffix}.geojson`);
        if (!response.ok) throw new Error('cartografia');
        const geojson = await response.json();
        let selectedLayer;
        const layer = L.geoJSON(geojson, {
            style: feature => {
                const c = summary.get(feature.properties.codigo);
                return {color: c.codigo === selected ? '#183b61' : '#526b80', weight: c.codigo === selected ? 3 : 1,
                    fillColor: c.codigo === selected ? '#183b61' : c.mediciones ? '#0088be' : '#c6d1da', fillOpacity: .65};
            },
            onEachFeature: (feature, polygon) => {
                const c = summary.get(feature.properties.codigo);
                const label = document.createElement('span');
                label.textContent = `${c.nombre} · ${c.mediciones} mediciones · ${c.usuarios} usuarios`;
                polygon.bindTooltip(label, {sticky: true});
                polygon.on('click', () => navigate('comuna', c.codigo));
                polygon.on('mouseover', () => polygon.setStyle({weight: 3, fillOpacity: .85}));
                polygon.on('mouseout', () => layer.resetStyle(polygon));
                if (c.codigo === selected) selectedLayer = polygon;
            }
        }).addTo(map);
        if (selectedLayer) { map.fitBounds(selectedLayer.getBounds(), {padding: [25, 25], maxZoom: 12}); selectedLayer.openTooltip(); }
        else if (container.dataset.region) map.fitBounds(layer.getBounds(), {padding: [15, 15], maxZoom: 10});
        else {
            const totals = new Map();
            summary.forEach(c => totals.set(c.region, (totals.get(c.region) || 0) + c.mediciones));
            const initialRegion = [...totals].sort((a, b) => b[1] - a[1])[0];
            const region = initialRegion?.[1] ? initialRegion[0] : '13';
            const bounds = L.latLngBounds([]);
            layer.eachLayer(p => {
                if (summary.get(p.feature.properties.codigo).region === region) bounds.extend(p.getBounds());
            });
            if (bounds.isValid()) map.fitBounds(bounds, {padding: [25, 25], maxZoom: 10});
            const overview = L.control({position: 'topright'});
            overview.onAdd = () => {
                const button = L.DomUtil.create('button', 'mapa-vista-chile');
                button.type = 'button'; button.textContent = 'Ver Chile completo';
                L.DomEvent.disableClickPropagation(button);
                button.addEventListener('click', () => map.fitBounds(layer.getBounds(), {padding: [20, 20]}));
                return button;
            };
            overview.addTo(map);
        }
        status.textContent = selected === '12202' ? 'Antártica no tiene geometría en esta capa. Sus registros y usuarios aparecen abajo.' : 'Selecciona una comuna para consultar sus registros y usuarios. Usa una región o el buscador para acercarte.';
        if (!selected && !container.dataset.region) status.textContent = 'Vista inicial de la región con más mediciones (Metropolitana si todavía no hay registros). Las tablas muestran todo Chile hasta que selecciones una comuna o región.';
        // Etiquetas independientes del detalle al pasar el cursor. Ocultamos solo
        // las que se superponen; al acercarse aparecen más nombres.
        const names = L.layerGroup().addTo(map);
        function labels() {
            names.clearLayers();
            if (map.getZoom() < 7) return;
            const occupied = [], polygons = [];
            layer.eachLayer(p => polygons.push(p));
            polygons.sort((a, b) => Number(b.feature.properties.codigo === selected) - Number(a.feature.properties.codigo === selected));
            polygons.forEach(p => {
                const c = summary.get(p.feature.properties.codigo);
                const center = p.getCenter();
                if (!map.getBounds().contains(center)) return;
                const point = map.latLngToContainerPoint(center);
                const width = c.nombre.length * 6.5 + 14;
                const box = {left: point.x - width / 2, right: point.x + width / 2, top: point.y - 12, bottom: point.y + 12};
                if (occupied.some(b => box.left < b.right && box.right > b.left && box.top < b.bottom && box.bottom > b.top)) return;
                occupied.push(box);
                const text = document.createElement('span'); text.textContent = c.nombre;
                L.tooltip({permanent: true, direction: 'center', className: 'comuna-nombre', opacity: 1})
                    .setLatLng(center).setContent(text).addTo(names);
            });
        }
        map.on('zoomend moveend', labels); labels();
    } catch {
        status.textContent = 'No se pudieron cargar los límites. Puedes seleccionar una comuna con el buscador o recargar la página.';
    }
});
