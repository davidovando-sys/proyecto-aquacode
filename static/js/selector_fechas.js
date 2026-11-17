document.addEventListener('DOMContentLoaded', function () {
    if (typeof flatpickr === 'undefined') return;

    const instancias = new Map();

    function pareja(campo) {
        if (!campo.form) return null;
        const rol = campo.dataset.selectorFecha === 'desde' ? 'hasta' : 'desde';
        const otro = campo.form.querySelector('[data-selector-fecha="' + rol + '"]');
        return otro ? { campo: otro, fp: instancias.get(otro) } : null;
    }

    // "desde" no puede pasar de "hasta" y viceversa.
    function limitarPareja(campo, valor) {
        const otra = pareja(campo);
        if (!otra || !otra.fp) return;
        if (campo.dataset.selectorFecha === 'desde') {
            otra.fp.set('minDate', valor || otra.campo.dataset.min || null);
        } else {
            otra.fp.set('maxDate', valor || otra.campo.dataset.max || null);
        }
    }

    document.querySelectorAll('input[data-selector-fecha]').forEach(function (campo) {
        const fp = flatpickr(campo, {
            locale: 'es',
            dateFormat: 'Y-m-d',          // lo que se envía al servidor
            altInput: true,               // lo que ve la persona
            altFormat: 'd/m/Y',
            altInputClass: campo.className + ' bg-white',       // Bootstrap pinta gris los campos de solo lectura
            allowInput: false,            // no se puede escribir
            disableMobile: true,          // en celular también usa este calendario
            minDate: campo.dataset.min || null,
            maxDate: campo.dataset.max || null,
            onReady: function (_, __, instancia) {
                // El label debe apuntar al campo visible, no al oculto.
                instancia.altInput.id = campo.id + '-visible';
                const label = document.querySelector('label[for="' + campo.id + '"]');
                if (label) label.htmlFor = instancia.altInput.id;
            },
            onChange: function (_, texto) {
                limitarPareja(campo, texto);
                if (campo.hasAttribute('data-autoenviar') && campo.form) campo.form.requestSubmit();
            }
        });
        instancias.set(campo, fp);
    });

    // Aplica los límites cuando la página carga con fechas ya elegidas.
    instancias.forEach(function (_, campo) {
        if (campo.value) limitarPareja(campo, campo.value);
    });
});