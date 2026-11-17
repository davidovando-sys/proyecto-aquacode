document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-tabla-expandible]').forEach(section => {
        const button = section.querySelector('[data-expandir-tabla]');
        if (!button) return;
        const rows = section.querySelectorAll('[data-fila-extra]');
        const count = section.querySelector('[data-cantidad-visible]');
        button.addEventListener('click', () => {
            const expand = button.getAttribute('aria-expanded') !== 'true';
            rows.forEach(row => { row.hidden = !expand; });
            button.setAttribute('aria-expanded', String(expand));
            button.textContent = expand ? `Mostrar solo 10 ${button.dataset.tipo}` : `Ver más ${button.dataset.tipo}`;
            count.textContent = String(expand ? 10 + rows.length : 10);
            const target = expand ? rows[0] : section;
            // Mantener la lectura en el comienzo de los registros recién abiertos.
            target.scrollIntoView({block: 'start', behavior: 'auto'});
        });
    });
});
