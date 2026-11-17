
document.addEventListener('DOMContentLoaded', function () {
    const formulario = document.getElementById('form-filtros-mediciones');

    if (!formulario) return;

    const parametro = formulario.querySelector('#parametro');
    const minimo = formulario.querySelector('#minimo');
    const maximo = formulario.querySelector('#maximo');
    const aplicar = formulario.querySelector('#aplicar-filtros');
    const limpiar = formulario.querySelector('#limpiar-filtros');

    const nombres = [
        'parametro',
        'minimo',
        'maximo',
        'alerta',
        'desde',
        'hasta',
        'bloque_horario'
    ];

    if (!parametro || !minimo || !maximo || !aplicar || !limpiar) return;

    const busqueda = new URLSearchParams(window.location.search);

    const hayFiltrosAplicados = nombres.some(
        nombre => (busqueda.get(nombre) || '').trim() !== ''
    );

    function valor(nombre) {
        const campo = formulario.elements.namedItem(nombre);
        return campo ? campo.value.trim() : '';
    }

    function actualizarBotones() {
        const hayFiltrosSeleccionados = nombres.some(
            nombre => valor(nombre) !== ''
        );

        aplicar.disabled = !hayFiltrosSeleccionados;

        const permitirLimpiar =
            hayFiltrosSeleccionados || hayFiltrosAplicados;

        limpiar.classList.toggle('disabled', !permitirLimpiar);
        limpiar.setAttribute('aria-disabled', String(!permitirLimpiar));
        limpiar.tabIndex = permitirLimpiar ? 0 : -1;
    }

    function actualizarRango() {
        const habilitar = parametro.value !== '';

        minimo.disabled = !habilitar;
        maximo.disabled = !habilitar;

        if (!habilitar) {
            minimo.value = '';
            maximo.value = '';
        }
    }

    formulario.addEventListener('change', function (evento) {
        if (evento.target === parametro) {
            actualizarRango();
        }

        actualizarBotones();
    });

    formulario.addEventListener('input', actualizarBotones);

    limpiar.addEventListener('click', function (evento) {
        if (limpiar.getAttribute('aria-disabled') === 'true') {
            evento.preventDefault();
        }
    });

    actualizarRango();
    actualizarBotones();
});
