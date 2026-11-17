// Mantiene coherentes dos inputs de fecha: "desde" nunca puede pasar de "hasta".
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(function (form) {
        var desde = form.querySelector('input[data-rango="desde"]');
        var hasta = form.querySelector('input[data-rango="hasta"]');
        if (!desde || !hasta) return;

        var limite = hasta.max;

        function sincronizar() {
            hasta.min = desde.value || '';
            desde.max = hasta.value || limite;
        }

        desde.addEventListener('input', sincronizar);
        hasta.addEventListener('input', sincronizar);
        sincronizar();
    });
});