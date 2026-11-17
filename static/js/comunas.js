document.addEventListener('DOMContentLoaded', () => {
    const catalogs = new Map();
    const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es').trim();
    function loadCatalog(url) {
        if (!catalogs.has(url)) {
            catalogs.set(url, fetch(url).then(response => {
                if (!response.ok) throw new Error('catalogo');
                return response.json();
            }).then(rows => rows.map(c => ({...c, search: normalize(c.nombre)})))
                .catch(error => { catalogs.delete(url); throw error; }));
        }
        return catalogs.get(url);
    }
    document.querySelectorAll('[data-comuna-busqueda]').forEach(root => {
        const input = root.querySelector('[role=combobox]');
        const code = root.querySelector('[data-comuna-codigo]');
        const list = root.querySelector('[role=listbox]');
        const help = root.querySelector('.comuna-ayuda');
        const regionSelect = root.dataset.regionSelect ? document.getElementById(root.dataset.regionSelect) : null;
        const region = () => (regionSelect ? regionSelect.value : '');
        const ayuda = () => region()
            ? 'Elige una comuna de la región o escribe para buscar.'
            : 'Escribe al menos 2 letras y selecciona una comuna.';
 
        let results = [], active = -1, timer, version = 0;
        let selected = input.value, selectedRegion = '';

        // si la página ya trae una comuna elegida, se recupera su región para poder compararla después.
        loadCatalog(root.dataset.url).then(catalog => {
            const c = catalog.find(x => x.codigo === code.value);
            if (c) selectedRegion = c.codigo_region;
        }).catch(() => {});
 
        const close = () => { list.hidden = true; input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); active = -1; };
 
        function choose(index) {
            const c = results[index];
            if (!c) return;
            version++; clearTimeout(timer);
            input.value = selected = c.nombre; code.value = c.codigo; selectedRegion = c.codigo_region;
            input.setCustomValidity(''); close();
            help.textContent = c.region;
            input.dispatchEvent(new CustomEvent('comuna:selected', {bubbles: true, detail: c}));
            input.form?.requestSubmit();
        }
 
        // Limpia la selección sin disparar eventos de "input" (no abre la lista ni notifica cambios).
        function reset() {
            version++; clearTimeout(timer); close();
            input.value = ''; code.value = ''; selected = ''; selectedRegion = '';
            input.setCustomValidity('');
            help.textContent = ayuda();
        }
 
        async function mostrar(q, current) {
            help.textContent = 'Buscando comunas…';
            try {
                const catalog = await loadCatalog(root.dataset.url);
                if (current !== version) return;
                const texto = normalize(q), reg = region();
                results = catalog.filter(c =>
                    (!reg || String(c.codigo_region) === String(reg)) &&
                    c.search.includes(texto)
                )
                    .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
                list.replaceChildren();
                results.forEach((c, i) => {
                    const option = document.createElement('div');
                    option.className = 'comuna-opcion'; option.id = `${input.id}-opcion-${i}`;
                    option.setAttribute('role', 'option'); option.setAttribute('aria-selected', 'false');
                    option.textContent = c.nombre;
                    const regionTexto = document.createElement('small'); regionTexto.textContent = c.region;
                    option.append(regionTexto); option.addEventListener('mousedown', e => e.preventDefault());
                    option.addEventListener('click', () => choose(i)); list.append(option);
                });
                list.hidden = !results.length;
                input.setAttribute('aria-expanded', String(!!results.length));
                help.textContent = results.length ? `${results.length} comunas encontradas. Usa las flechas y Enter para seleccionar.` : 'No se encontraron comunas.';
            } catch {
                if (current === version) help.textContent = 'No se pudieron cargar las comunas. Vuelve a escribir para reintentar.';
            }
        }
 
        input.addEventListener('input', () => {
            code.value = ''; selected = ''; selectedRegion = ''; close(); clearTimeout(timer);
            const current = ++version, q = input.value.trim();
            input.setCustomValidity(q ? 'Selecciona una comuna de las sugerencias.' : '');
            help.textContent = ayuda();
            // Sin región se exigen 2 letras; con región se puede listar todo (también con el campo vacío).
            if (q.length < 2 && !region()) return;
            timer = setTimeout(() => mostrar(q, current), 0);
        });
 
        // Con una región elegida y el campo vacío, un clic o la flecha abajo muestran todas sus comunas.
        const abrirDeLaRegion = () => {
            if (!region() || input.value.trim() || !list.hidden) return;
            mostrar('', ++version);
        };
        input.addEventListener('focus', abrirDeLaRegion);
        input.addEventListener('click', abrirDeLaRegion);
 
        input.addEventListener('keydown', e => {
            if (e.key === 'Escape') { version++; clearTimeout(timer); close(); }
            if (list.hidden && e.key === 'ArrowDown') { e.preventDefault(); abrirDeLaRegion(); return; }
            if (list.hidden) return;
            if (['ArrowDown', 'ArrowUp'].includes(e.key)) {
                e.preventDefault(); active = (active + (e.key === 'ArrowDown' ? 1 : -1) + results.length) % results.length;
                Array.from(list.children).forEach((o, i) => o.setAttribute('aria-selected', String(i === active)));
                input.setAttribute('aria-activedescendant', list.children[active].id);
                list.children[active].scrollIntoView({block: 'nearest'});
            } else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); choose(active); }
        });
        input.addEventListener('blur', () => { version++; clearTimeout(timer); close(); });
 
        input.addEventListener('comuna:reset', reset);
 
        if (regionSelect) {
            regionSelect.addEventListener('change', () => {

                if (code.value && region() && selectedRegion && selectedRegion !== region()) {
                    reset();
                } else {
                    close();
                    help.textContent = ayuda();
                }

                // Aplicar el filtro de región en el servidor.
                input.form?.requestSubmit();
            });
        }
 
        input.form?.addEventListener('submit', e => {
            if (input.value && input.value !== selected) { e.preventDefault(); input.reportValidity(); }
        });
    });
});