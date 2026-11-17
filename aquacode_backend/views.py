from django.shortcuts import render, redirect
#NO USAR ESTE ARCHIVO, SE DEBE USAR EL VIEWS.PY DE CADA APP PARA CUMPLIR CON LA MODULARIZACION DE LA ARQUITECTURA

#creo que esta funcion no se esta usando, pero la dejo por si acaso
@staff_member_required(login_url='login') 
def configuracion_view(request):
    parametros = ConfiguracionParametro.objects.all()

    if request.method == 'POST':
        parametro_id = request.POST.get('parametro_id')
        parametro = get_object_or_404(ConfiguracionParametro, id=parametro_id)
        
        parametro.valor_min = request.POST.get('valor_min')
        parametro.valor_max = request.POST.get('valor_max')
        parametro.texto_informativo = request.POST.get('texto_informativo')
        parametro.save()
        
        messages.success(request, f'Se actualizó la configuración de {parametro.get_nombre_parametro_display()}.')
        return redirect('configuracion_admin')

    return render(request, 'configuracion_admin.html', {'parametros': parametros})
