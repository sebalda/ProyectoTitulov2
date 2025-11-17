import random
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render
from apps.tienda.models import Producto, CategoriaAcero

def home(request):
    # ...tu lógica actual...
    # Generar suma aleatoria para el validador
    if request.method == 'GET':
        suma_a = random.randint(1, 10)
        suma_b = random.randint(1, 10)
        request.session['suma_a'] = suma_a
        request.session['suma_b'] = suma_b
        context = {
            'productos_destacados': Producto.objects.filter(activo=True)[:6],
            'categorias': CategoriaAcero.objects.filter(activa=True)[:4],
            'titulo': 'Pozinox - Tienda de Aceros',
            'suma_a': suma_a,
            'suma_b': suma_b,
        }
        return render(request, 'tienda/home.html', context)

    # Procesar formulario POST
    elif request.method == 'POST':
        suma_a = request.session.get('suma_a', 0)
        suma_b = request.session.get('suma_b', 0)
        suma_usuario = int(request.POST.get('suma', 0))
        error_suma = None
        success = None

        # Validar suma
        if suma_usuario != (suma_a + suma_b):
            error_suma = "La suma es incorrecta. Intenta nuevamente."
        else:
            # Enviar correo
            nombre = request.POST.get('nombre')
            rut = request.POST.get('rut')
            direccion = request.POST.get('direccion')
            comuna = request.POST.get('comuna')
            ciudad = request.POST.get('ciudad')
            giro = request.POST.get('giro')
            email = request.POST.get('email')
            telefono = request.POST.get('telefono')
            mensaje = request.POST.get('mensaje')

            cuerpo = f"""
Nombre: {nombre}
RUT: {rut}
Dirección: {direccion}
Comuna: {comuna}
Ciudad: {ciudad}
Giro: {giro}
Email: {email}
Teléfono: {telefono}
Mensaje: {mensaje}
"""
            send_mail(
                subject="Nuevo mensaje de contacto Pozinox",
                message=cuerpo,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=["pozinox.empresa@gmail.com"],
                fail_silently=False,
            )
            success = "¡Mensaje enviado correctamente! Nos contactaremos pronto."

        # Generar nueva suma para el siguiente intento
        suma_a = random.randint(1, 10)
        suma_b = random.randint(1, 10)
        request.session['suma_a'] = suma_a
        request.session['suma_b'] = suma_b

        context = {
            'productos_destacados': Producto.objects.filter(activo=True)[:6],
            'categorias': CategoriaAcero.objects.filter(activa=True)[:4],
            'titulo': 'Pozinox - Tienda de Aceros',
            'suma_a': suma_a,
            'suma_b': suma_b,
            'error_suma': error_suma,
            'success': success,
        }
        return render(request, 'tienda/home.html', context)