from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Producto, CategoriaAcero, Cotizacion, DetalleCotizacion, TransferenciaBancaria
from .forms import ProductoForm, CategoriaForm
import mercadopago
import os
import json
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO

logger = logging.getLogger(__name__)

# ============================================
# FUNCIONES AUXILIARES
# ============================================
def es_superusuario(user):
    return user.is_superuser

def aplicar_filtros_productos(queryset, request):
    """Aplicar filtros comunes a productos"""
    categoria_id = request.GET.get('categoria')
    busqueda = request.GET.get('q')
    
    if categoria_id:
        queryset = queryset.filter(categoria_id=categoria_id)
    if busqueda:
        queryset = queryset.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(codigo_producto__icontains=busqueda)
        )
    return queryset

def paginar_queryset(queryset, request, per_page=20):
    """Paginación común"""
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def home(request):
    """Vista principal de la página de inicio"""
    from django.core.mail import send_mail
    import threading
    
    if request.method == 'GET':
        context = {
            'productos_destacados': Producto.objects.filter(activo=True)[:6],
            'categorias': CategoriaAcero.objects.filter(activa=True)[:4],
            'titulo': 'Pozinox - Tienda de Aceros',
        }
        return render(request, 'tienda/home.html', context)

    # Procesar formulario POST
    elif request.method == 'POST':
        # Obtener datos del formulario
        nombre = request.POST.get('nombre', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        comuna = request.POST.get('comuna', '').strip()
        ciudad = request.POST.get('ciudad', '').strip()
        giro = request.POST.get('giro', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()

        # Construir cuerpo del correo
        cuerpo = f"""
Nuevo mensaje de contacto desde Pozinox

Datos del contacto:
Nombre: {nombre}
Email: {email}
Teléfono: {telefono}
"""
        
        # Agregar campos opcionales solo si fueron proporcionados
        if direccion:
            cuerpo += f"Dirección: {direccion}\n"
        if comuna:
            cuerpo += f"Comuna: {comuna}\n"
        if ciudad:
            cuerpo += f"Ciudad: {ciudad}\n"
        if giro:
            cuerpo += f"Actividad Económica / Giro: {giro}\n"
        
        cuerpo += f"""
Mensaje:
{mensaje}
"""
        
        # Función para enviar correo en segundo plano
        def enviar_correo_asincrono():
            try:
                send_mail(
                    subject=f"Nuevo mensaje de contacto de {nombre}",
                    message=cuerpo,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=["pozinox.empresa@gmail.com"],
                    fail_silently=True,  # No bloquear si falla
                )
            except Exception as e:
                # Log del error (puedes agregar logging aquí si lo necesitas)
                print(f"Error al enviar correo: {e}")
        
        # Enviar correo en un hilo separado para no bloquear la respuesta
        thread = threading.Thread(target=enviar_correo_asincrono)
        thread.daemon = True
        thread.start()
        
        # Mostrar mensaje de éxito inmediatamente
        success = "¡Mensaje enviado correctamente! Nos contactaremos pronto."

        context = {
            'productos_destacados': Producto.objects.filter(activo=True)[:6],
            'categorias': CategoriaAcero.objects.filter(activa=True)[:4],
            'titulo': 'Pozinox - Tienda de Aceros',
            'success': success,
        }
        return render(request, 'tienda/home.html', context)


def productos_publicos(request):
    """Vista pública de productos para todos los usuarios"""
    productos = aplicar_filtros_productos(Producto.objects.filter(activo=True), request)
    context = {
        'productos': paginar_queryset(productos, request, 12),
        'categorias': CategoriaAcero.objects.filter(activa=True),
        'categoria_actual': request.GET.get('categoria') or '',
        'busqueda': request.GET.get('q') or '',
    }
    return render(request, 'tienda/productos.html', context)


def detalle_producto(request, producto_id):
    """Vista de detalle de un producto específico"""
    producto = get_object_or_404(Producto, id=producto_id, activo=True)
    # Parse medidas JSON into a Python list for the template
    medidas_list = []
    try:
        import json
        medidas_list = json.loads(producto.medidas or '[]')
    except Exception:
        medidas_list = []
    context = {
        'producto': producto,
        'productos_relacionados': Producto.objects.filter(
            categoria=producto.categoria, activo=True
        ).exclude(id=producto.id)[:4],
        'medidas_list': medidas_list,
    }
    return render(request, 'tienda/detalle_producto.html', context)


@login_required
@user_passes_test(es_superusuario)
def panel_admin(request):
    """Panel de administración para superusuarios"""
    from apps.usuarios.models import VisitorLog
    from django.db.models import Count
    from datetime import timedelta
    
    # Estadísticas de productos
    total_productos = Producto.objects.count()
    productos_activos = Producto.objects.filter(activo=True).count()
    productos_stock_bajo = Producto.objects.filter(stock_actual__lte=F('stock_minimo')).count()
    total_categorias = CategoriaAcero.objects.count()
    
    # Estadísticas de visitantes
    now = timezone.now()
    visitas_hoy = VisitorLog.objects.filter(timestamp__date=now.date()).count()
    visitas_semana = VisitorLog.objects.filter(timestamp__gte=now - timedelta(days=7)).count()
    visitas_mes = VisitorLog.objects.filter(timestamp__gte=now - timedelta(days=30)).count()
    
    # Visitantes únicos (por session_id)
    visitantes_unicos_hoy = VisitorLog.objects.filter(
        timestamp__date=now.date()
    ).values('session_id').distinct().count()
    
    visitantes_unicos_semana = VisitorLog.objects.filter(
        timestamp__gte=now - timedelta(days=7)
    ).values('session_id').distinct().count()
    
    # Páginas más visitadas
    paginas_populares = VisitorLog.objects.filter(
        timestamp__gte=now - timedelta(days=30)
    ).values('page_url').annotate(
        visitas=Count('id')
    ).order_by('-visitas')[:10]
    
    # Dispositivos
    dispositivos = VisitorLog.objects.filter(
        timestamp__gte=now - timedelta(days=30)
    ).values('device_type').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')
    
    context = {
        'total_productos': total_productos,
        'productos_activos': productos_activos,
        'productos_stock_bajo': productos_stock_bajo,
        'total_categorias': total_categorias,
        # Estadísticas de visitantes
        'visitas_hoy': visitas_hoy,
        'visitas_semana': visitas_semana,
        'visitas_mes': visitas_mes,
        'visitantes_unicos_hoy': visitantes_unicos_hoy,
        'visitantes_unicos_semana': visitantes_unicos_semana,
        'paginas_populares': paginas_populares,
        'dispositivos': dispositivos,
    }
    return render(request, 'tienda/panel_admin.html', context)


@login_required
@user_passes_test(es_superusuario)
def lista_productos_admin(request):
    """Lista de productos para administración"""
    productos = Producto.objects.all().order_by('-fecha_creacion')
    
    # Aplicar filtros
    estado = request.GET.get('estado')
    if estado == 'activos':
        productos = productos.filter(activo=True)
    elif estado == 'inactivos':
        productos = productos.filter(activo=False)
    
    productos = aplicar_filtros_productos(productos, request)
    
    context = {
        'productos': paginar_queryset(productos, request, 20),
        'categorias': CategoriaAcero.objects.all(),
        'categoria_actual': request.GET.get('categoria'),
        'estado_actual': estado,
        'busqueda': request.GET.get('q'),
    }
    return render(request, 'tienda/admin/lista_productos.html', context)


@login_required
@user_passes_test(es_superusuario)
def crear_producto(request):
    """Crear nuevo producto"""
    form = ProductoForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        producto = form.save()
        messages.success(request, f'Producto "{producto.nombre}" creado exitosamente.')
        return redirect('lista_productos_admin')
    
    return render(request, 'tienda/admin/formulario_producto.html', {
        'form': form, 'titulo': 'Crear Producto'
    })


@login_required
@user_passes_test(es_superusuario)
def editar_producto(request, producto_id):
    """Editar producto existente"""
    producto = get_object_or_404(Producto, id=producto_id)
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto)
    
    if form.is_valid():
        producto = form.save()
        messages.success(request, f'Producto "{producto.nombre}" actualizado exitosamente.')
        return redirect('lista_productos_admin')
    
    return render(request, 'tienda/admin/formulario_producto.html', {
        'form': form, 'producto': producto, 'titulo': 'Editar Producto'
    })


@login_required
@user_passes_test(es_superusuario)
def eliminar_producto(request, producto_id):
    """Eliminar producto"""
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        nombre_producto = producto.nombre
        producto.delete()
        messages.success(request, f'Producto "{nombre_producto}" eliminado exitosamente.')
        return redirect('lista_productos_admin')
    
    return render(request, 'tienda/admin/confirmar_eliminar.html', {'producto': producto})


@login_required
@user_passes_test(es_superusuario)
def lista_categorias_admin(request):
    """Lista de categorías para administración"""
    categorias = CategoriaAcero.objects.all().order_by('nombre')
    
    # Aplicar filtros
    estado = request.GET.get('estado')
    if estado == 'activas':
        categorias = categorias.filter(activa=True)
    elif estado == 'inactivas':
        categorias = categorias.filter(activa=False)
    
    busqueda = request.GET.get('q')
    if busqueda:
        categorias = categorias.filter(
            Q(nombre__icontains=busqueda) | Q(descripcion__icontains=busqueda)
        )
    
    context = {
        'categorias': paginar_queryset(categorias, request, 20),
        'estado_actual': estado,
        'busqueda': busqueda,
    }
    return render(request, 'tienda/admin/lista_categorias.html', context)


@login_required
@user_passes_test(es_superusuario)
def crear_categoria(request):
    """Crear nueva categoría"""
    form = CategoriaForm(request.POST or None)
    if form.is_valid():
        categoria = form.save()
        messages.success(request, f'Categoría "{categoria.nombre}" creada exitosamente.')
        return redirect('lista_categorias_admin')
    
    return render(request, 'tienda/admin/formulario_categoria.html', {
        'form': form, 'titulo': 'Crear Categoría'
    })


@login_required
@user_passes_test(es_superusuario)
def editar_categoria(request, categoria_id):
    """Editar categoría existente"""
    categoria = get_object_or_404(CategoriaAcero, id=categoria_id)
    form = CategoriaForm(request.POST or None, instance=categoria)
    
    if form.is_valid():
        categoria = form.save()
        messages.success(request, f'Categoría "{categoria.nombre}" actualizada exitosamente.')
        return redirect('lista_categorias_admin')
    
    return render(request, 'tienda/admin/formulario_categoria.html', {
        'form': form, 'categoria': categoria, 'titulo': 'Editar Categoría'
    })


@login_required
@user_passes_test(es_superusuario)
def eliminar_categoria(request, categoria_id):
    """Eliminar categoría"""
    categoria = get_object_or_404(CategoriaAcero, id=categoria_id)
    
    if request.method == 'POST':
        nombre_categoria = categoria.nombre
        categoria.delete()
        messages.success(request, f'Categoría "{nombre_categoria}" eliminada exitosamente.')
        return redirect('lista_categorias_admin')
    
    return render(request, 'tienda/admin/confirmar_eliminar_categoria.html', {
        'categoria': categoria,
        'productos_asociados': Producto.objects.filter(categoria=categoria).count()
    })


# ============================================
# SISTEMA DE COTIZACIONES
# ============================================

@login_required
def mis_cotizaciones(request):
    """Lista de cotizaciones del usuario actual"""
    cotizaciones = Cotizacion.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    
    # Aplicar filtros
    estado = request.GET.get('estado')
    if estado:
        cotizaciones = cotizaciones.filter(estado=estado)
    
    return render(request, 'tienda/cotizaciones/mis_cotizaciones.html', {
        'cotizaciones': paginar_queryset(cotizaciones, request, 10),
        'estado_actual': estado,
    })


@login_required
def crear_cotizacion(request):
    """Crear nueva cotización o obtener la cotización en borrador actual"""
    cotizacion = Cotizacion.objects.filter(usuario=request.user, estado='borrador').first()
    
    if not cotizacion:
        cotizacion = Cotizacion.objects.create(usuario=request.user)
        messages.success(request, f'Nueva cotización {cotizacion.numero_cotizacion} creada.')
    
    return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)


@login_required
def detalle_cotizacion(request, cotizacion_id):
    """Ver detalle de una cotización"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    detalles = cotizacion.detalles.all().select_related('producto')
    
    # Productos disponibles para agregar
    productos_en_cotizacion = detalles.values_list('producto_id', flat=True)
    productos_disponibles = Producto.objects.filter(activo=True).exclude(
        id__in=productos_en_cotizacion
    )
    
    # Aplicar filtros
    categoria_id = request.GET.get('categoria')
    busqueda = request.GET.get('q')
    
    if categoria_id:
        productos_disponibles = productos_disponibles.filter(categoria_id=categoria_id)
    if busqueda:
        productos_disponibles = productos_disponibles.filter(
            Q(nombre__icontains=busqueda) | Q(codigo_producto__icontains=busqueda)
        )
    
    return render(request, 'tienda/cotizaciones/detalle_cotizacion.html', {
        'cotizacion': cotizacion,
        'detalles': detalles,
        'productos_disponibles': productos_disponibles[:20],
        'categorias': CategoriaAcero.objects.filter(activa=True),
        'puede_editar': cotizacion.estado == 'borrador',
    })


@login_required
@require_POST
def agregar_producto_cotizacion(request, cotizacion_id):
    """Agregar un producto a la cotización"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    if cotizacion.estado != 'borrador':
        messages.error(request, 'No se pueden agregar productos a una cotización finalizada.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    producto = get_object_or_404(Producto, id=request.POST.get('producto_id'), activo=True)
    cantidad = int(request.POST.get('cantidad', 1))
    
    detalle, created = DetalleCotizacion.objects.get_or_create(
        cotizacion=cotizacion, producto=producto,
        defaults={'cantidad': cantidad, 'precio_unitario': producto.precio_por_unidad}
    )
    
    if not created:
        detalle.cantidad += cantidad
        detalle.save()
        messages.info(request, f'Se actualizó la cantidad de {producto.nombre} en la cotización.')
    else:
        messages.success(request, f'{producto.nombre} agregado a la cotización.')
    
    return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)


@login_required
@require_POST
def actualizar_cantidad_producto(request, detalle_id):
    """Actualizar cantidad de un producto en la cotización"""
    detalle = get_object_or_404(DetalleCotizacion, id=detalle_id)
    cotizacion = detalle.cotizacion
    
    if cotizacion.usuario != request.user:
        return JsonResponse({'error': 'No autorizado'}, status=403)
    if cotizacion.estado != 'borrador':
        return JsonResponse({'error': 'No se puede editar una cotización finalizada'}, status=400)
    
    cantidad = int(request.POST.get('cantidad', 1))
    if cantidad <= 0:
        return JsonResponse({'error': 'La cantidad debe ser mayor a 0'}, status=400)
    
    detalle.cantidad = cantidad
    detalle.save()
    
    return JsonResponse({
        'success': True,
        'subtotal': float(detalle.subtotal),
        'total_cotizacion': float(cotizacion.total)
    })


@login_required
@require_POST
def eliminar_producto_cotizacion(request, detalle_id):
    """Eliminar un producto de la cotización"""
    detalle = get_object_or_404(DetalleCotizacion, id=detalle_id)
    cotizacion = detalle.cotizacion
    
    if cotizacion.usuario != request.user:
        messages.error(request, 'No autorizado.')
        return redirect('mis_cotizaciones')
    if cotizacion.estado != 'borrador':
        messages.error(request, 'No se pueden eliminar productos de una cotización finalizada.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    producto_nombre = detalle.producto.nombre
    detalle.delete()
    messages.success(request, f'{producto_nombre} eliminado de la cotización.')
    
    return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)


@login_required
def finalizar_cotizacion(request, cotizacion_id):
    """Finalizar cotización y mostrar opciones de pago"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    if cotizacion.estado != 'borrador':
        messages.error(request, 'Esta cotización ya fue finalizada.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    if not cotizacion.detalles.exists():
        messages.error(request, 'Debe agregar al menos un producto a la cotización.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    cotizacion.estado = 'finalizada'
    cotizacion.fecha_finalizacion = timezone.now()
    cotizacion.save()
    
    messages.success(request, 'Cotización finalizada. Seleccione un método de pago.')
    return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)


@login_required
def seleccionar_pago(request, cotizacion_id):
    """Página para seleccionar método de pago"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    if cotizacion.estado not in ['finalizada', 'pagada']:
        messages.error(request, 'La cotización debe estar finalizada para proceder al pago.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    return render(request, 'tienda/cotizaciones/seleccionar_pago.html', {
        'cotizacion': cotizacion,
        'detalles': cotizacion.detalles.all().select_related('producto'),
        'tiene_transferencia': hasattr(cotizacion, 'transferencia'),
    })


@login_required
def procesar_pago_mercadopago(request, cotizacion_id):
    """Crear preferencia de pago en MercadoPago y redirigir"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    # Verificar que esté finalizada
    if cotizacion.estado not in ['finalizada', 'pagada', 'en_revision']:
        messages.error(request, 'La cotización debe estar finalizada para proceder al pago.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    # Verificar que no esté ya pagada o en revisión
    if cotizacion.estado in ['pagada', 'en_revision']:
        messages.info(request, 'Esta cotización ya tiene un pago registrado.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    # Obtener el Access Token de MercadoPago desde settings
    mp_access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None) or os.getenv('MERCADOPAGO_ACCESS_TOKEN')
    
    if not mp_access_token:
        messages.error(request, 'MercadoPago no está configurado. Contacte al administrador.')
        logger.error('MercadoPago no está configurado: falta MERCADOPAGO_ACCESS_TOKEN')
        return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)
    
    # Validar formato básico del Access Token
    if len(mp_access_token) < 20:
        messages.error(request, 'El Access Token de MercadoPago parece ser inválido. Verifique la configuración.')
        logger.error(f'Access Token de MercadoPago parece inválido (longitud: {len(mp_access_token)})')
        return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)
    
    # Calcular totales antes de crear la preferencia
    cotizacion.calcular_totales()
    
    # Verificar que tenga productos
    if not cotizacion.detalles.exists():
        messages.error(request, 'La cotización no tiene productos.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    try:
        # Inicializar SDK de MercadoPago
        sdk = mercadopago.SDK(mp_access_token)
        
        # Crear items de la preferencia
        # Incluir los productos con sus precios sin IVA
        items = []
        for detalle in cotizacion.detalles.all():
            items.append({
                "title": f"{detalle.producto.nombre} ({detalle.producto.codigo_producto})",
                "quantity": detalle.cantidad,
                "unit_price": float(detalle.precio_unitario),
                "currency_id": "CLP"  # Peso chileno
            })
        
        # Agregar el IVA como un item adicional si existe
        if cotizacion.iva and cotizacion.iva > 0:
            items.append({
                "title": "IVA (19%)",
                "quantity": 1,
                "unit_price": float(cotizacion.iva),
                "currency_id": "CLP"
            })
        
        # Construir URLs absolutas
        scheme = request.scheme  # http o https
        host = request.get_host()  # Incluye el dominio y puerto si existe
        
        # Para desarrollo local, usar http://localhost:8000
        if host in ['localhost', '127.0.0.1'] or host.startswith('localhost:') or host.startswith('127.0.0.1:'):
            scheme = 'http'
            # Asegurar que tenga el puerto
            if ':' not in host:
                host = f"{host}:8000"
        
        # Construir URLs manualmente para asegurar que sean correctas
        base_url = f"{scheme}://{host}"
        
        # URLs de retorno (callbacks)
        success_url = f"{base_url}/cotizaciones/{cotizacion.id}/pago-exitoso/"
        failure_url = f"{base_url}/cotizaciones/{cotizacion.id}/pago-fallido/"
        pending_url = f"{base_url}/cotizaciones/{cotizacion.id}/pago-pendiente/"
        
        # Verificar que las URLs sean válidas
        if not success_url or not success_url.startswith(('http://', 'https://')):
            logger.error(f'URL de success inválida: {success_url}')
            messages.error(request, 'Error de configuración: URL de retorno inválida.')
            return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)
        
        # Crear preferencia
        preference_data = {
            "items": items,
            "back_urls": {
                "success": success_url,
                "failure": failure_url,
                "pending": pending_url,
            },
            "external_reference": cotizacion.numero_cotizacion,
            "statement_descriptor": "Pozinox",
            "payer": {
                "name": request.user.first_name or request.user.username,
                "surname": request.user.last_name or "",
                "email": request.user.email,
            },
            "metadata": {
                "cotizacion_id": str(cotizacion.id),
                "numero_cotizacion": cotizacion.numero_cotizacion,
            }
        }
        
        # Log de los datos que se envían (sin información sensible)
        logger.info(f'Creando preferencia de MercadoPago para cotización {cotizacion.numero_cotizacion}')
        logger.info(f'Items: {len(items)} productos, Total: ${cotizacion.total}')
        
        preference_response = sdk.preference().create(preference_data)
        
        # Verificar si hay errores en la respuesta
        if isinstance(preference_response, dict):
            # Verificar si hay un campo "status" que indique error HTTP
            status_code = preference_response.get("status")
            if status_code and isinstance(status_code, int) and status_code >= 400:
                error_msg = preference_response.get("message", "Error al crear preferencia")
                logger.error(f'Error HTTP ({status_code}) al crear preferencia de MercadoPago: {error_msg}')
                messages.error(request, f'Error al procesar el pago: {error_msg}')
                return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)
            
            # Verificar si hay un campo "error" que indique error
            if "error" in preference_response:
                error_msg = preference_response.get("message", "Error desconocido")
                logger.error(f'Error al crear preferencia de MercadoPago: {error_msg}')
                messages.error(request, f'Error al procesar el pago: {error_msg}')
                return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)
        
        # Obtener la preferencia de la respuesta
        if "response" in preference_response:
            preference = preference_response["response"]
        else:
            preference = preference_response
        
        # Verificar que la preferencia sea válida
        if not preference or not isinstance(preference, dict):
            logger.error(f'Respuesta inválida de MercadoPago: {preference_response}')
            messages.error(request, 'Error al procesar el pago: respuesta inválida de MercadoPago.')
            return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)
        
        # Obtener el ID de preferencia
        preference_id = preference.get("id") or preference.get("preference_id")
        
        if not preference_id:
            logger.error(f'No se encontró ID de preferencia en la respuesta: {preference}')
            messages.error(request, 'Error al procesar el pago: no se pudo obtener el ID de preferencia.')
            return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)
        
        # Guardar el ID de preferencia
        cotizacion.mercadopago_preference_id = str(preference_id)
        cotizacion.metodo_pago = 'mercadopago'
        cotizacion.save()
        
        # Obtener la URL de redirección (init_point)
        init_point = (
            preference.get("init_point") or 
            preference.get("sandbox_init_point") or
            preference.get("init_point_url")
        )
        
        if not init_point:
            logger.error(f'No se encontró init_point en la respuesta de MercadoPago: {preference}')
            messages.error(request, 'Error al obtener la URL de pago de MercadoPago.')
            return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)
        
        logger.info(f'Redirigiendo a MercadoPago: {init_point}')
        return redirect(init_point)
        
    except Exception as e:
        logger.exception(f'Error al procesar pago de MercadoPago para cotización {cotizacion_id}')
        messages.error(request, f'Error al procesar el pago: {str(e)}')
        return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)


@login_required
def pago_exitoso(request, cotizacion_id):
    """Página de confirmación de pago exitoso"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    # Obtener payment_id de MercadoPago si está disponible
    payment_id = request.GET.get('payment_id') or request.GET.get('preference_id')
    
    # Si hay un payment_id, verificar el estado del pago con MercadoPago
    if payment_id and getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None):
        try:
            mp_access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None) or os.getenv('MERCADOPAGO_ACCESS_TOKEN')
            sdk = mercadopago.SDK(mp_access_token)
            payment_response = sdk.payment().get(payment_id)
            
            if "error" not in payment_response:
                payment = payment_response["response"]
                status = payment.get("status")
                
                # Actualizar información del pago
                cotizacion.mercadopago_payment_id = str(payment.get("id", ""))
                
                if status == 'approved':
                    cotizacion.estado = 'en_revision'  # Ir a revisión para aprobación manual
                    cotizacion.pago_completado = False
                    messages.success(request, '¡Pago recibido! Está en revisión y te notificaremos cuando sea aprobado.')
                elif status == 'pending':
                    cotizacion.estado = 'en_revision'
                    cotizacion.pago_completado = False
                    messages.info(request, 'Tu pago está siendo procesado. Te notificaremos cuando sea confirmado.')
                elif status in ['rejected', 'cancelled']:
                    messages.warning(request, f'El pago fue {status}. Por favor, intenta nuevamente.')
                    return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)
                
                cotizacion.save()
        except Exception as e:
            logger.exception(f'Error al verificar pago {payment_id} en pago_exitoso')
            # Continuar de todas formas, mostrar la página de éxito
    
    # Mostrar la página de revisión si está en revisión o pagada
    if cotizacion.estado in ['pagada', 'en_revision']:
        context = {
            'cotizacion': cotizacion,
        }
        return render(request, 'tienda/cotizaciones/pago_exitoso.html', context)
    
    # Si no está en un estado válido, redirigir
    return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)


@login_required
def pago_fallido(request, cotizacion_id):
    """Página de pago fallido"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    context = {
        'cotizacion': cotizacion,
    }
    return render(request, 'tienda/cotizaciones/pago_fallido.html', context)


@login_required
def pago_pendiente(request, cotizacion_id):
    """Página de pago pendiente"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    # Verificar si es pago por Transferencia
    es_transferencia = cotizacion.metodo_pago == 'transferencia'
    
    # Verificar si el pago ya fue aprobado (solo para MercadoPago)
    if not es_transferencia:
        payment_id = request.GET.get('payment_id') or request.GET.get('preference_id')
        
        if payment_id and getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None):
            try:
                mp_access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None) or os.getenv('MERCADOPAGO_ACCESS_TOKEN')
                sdk = mercadopago.SDK(mp_access_token)
                payment_response = sdk.payment().get(payment_id)
                
                if "error" not in payment_response:
                    payment = payment_response["response"]
                    status = payment.get("status")
                    
                    if status == 'approved':
                        # El pago fue aprobado, redirigir a página de éxito
                        cotizacion.estado = 'pagada'
                        cotizacion.pago_completado = True
                        cotizacion.mercadopago_payment_id = str(payment.get("id", ""))
                        cotizacion.save()
                        messages.success(request, '¡Tu pago ha sido confirmado!')
                        return redirect('pago_exitoso', cotizacion_id=cotizacion.id)
                    elif status in ['rejected', 'cancelled']:
                        # El pago fue rechazado, redirigir a página de fallo
                        messages.error(request, 'El pago fue rechazado. Por favor, intenta nuevamente.')
                        return redirect('pago_fallido', cotizacion_id=cotizacion.id)
            except Exception as e:
                logger.exception(f'Error al verificar pago pendiente {payment_id}')
    
    # Obtener información de la transferencia si existe
    transferencia = None
    if es_transferencia:
        try:
            transferencia = cotizacion.transferencia
        except TransferenciaBancaria.DoesNotExist:
            pass
    
    context = {
        'cotizacion': cotizacion,
        'es_transferencia': es_transferencia,
        'transferencia': transferencia,
    }
    return render(request, 'tienda/cotizaciones/pago_pendiente.html', context)


@login_required
def descargar_cotizacion_pdf(request, cotizacion_id):
    """Generar y descargar PDF de la cotización"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    detalles = cotizacion.detalles.all().select_related('producto')
    
    # Crear el buffer
    buffer = BytesIO()
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Contenedor para los elementos del PDF
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para el título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para encabezados
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    # Estilo normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=12,
    )
    
    # Título
    elements.append(Paragraph('POZINOX', title_style))
    elements.append(Paragraph('Tienda de Aceros', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Información de la cotización
    elements.append(Paragraph(f'COTIZACIÓN N° {cotizacion.numero_cotizacion}', heading_style))
    
    # Datos del cliente y cotización
    info_data = [
        ['Cliente:', f'{request.user.get_full_name() or request.user.username}'],
        ['Email:', request.user.email],
        ['Fecha:', cotizacion.fecha_creacion.strftime('%d/%m/%Y %H:%M')],
        ['Estado:', cotizacion.get_estado_display()],
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e3a8a')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Tabla de productos
    elements.append(Paragraph('DETALLE DE PRODUCTOS', heading_style))
    
    # Encabezados de tabla
    table_data = [['Producto', 'Código', 'Cantidad', 'Precio Unit.', 'Subtotal']]
    
    # Datos de productos
    for detalle in detalles:
        table_data.append([
            Paragraph(detalle.producto.nombre, normal_style),
            detalle.producto.codigo_producto,
            str(detalle.cantidad),
            f'${detalle.precio_unitario:,.0f}',
            f'${detalle.subtotal:,.0f}'
        ])
    
    # Crear tabla
    product_table = Table(table_data, colWidths=[2.5*inch, 1.2*inch, 0.8*inch, 1*inch, 1*inch])
    product_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Contenido
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    elements.append(product_table)
    elements.append(Spacer(1, 20))
    
    # Totales
    totales_data = [
        ['Subtotal:', f'${cotizacion.subtotal:,.0f}'],
        ['IVA (19%):', f'${cotizacion.iva:,.0f}'],
        ['', ''],
        ['TOTAL:', f'${cotizacion.total:,.0f}'],
    ]
    
    totales_table = Table(totales_data, colWidths=[5*inch, 1.5*inch])
    totales_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 1), 'Helvetica'),
        ('FONTNAME', (1, 0), (1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 2), 11),
        ('FONTSIZE', (0, 3), (-1, 3), 14),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TEXTCOLOR', (0, 3), (-1, 3), colors.HexColor('#1e3a8a')),
        ('LINEABOVE', (0, 3), (-1, 3), 2, colors.HexColor('#1e3a8a')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(totales_table)
    elements.append(Spacer(1, 30))
    
    # Observaciones si existen
    if cotizacion.observaciones:
        elements.append(Paragraph('OBSERVACIONES:', heading_style))
        elements.append(Paragraph(cotizacion.observaciones, normal_style))
        elements.append(Spacer(1, 20))
    
    # Pie de página
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    
    elements.append(Spacer(1, 30))
    elements.append(Paragraph('_______________________________________________', footer_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph('POZINOX - Tienda de Aceros', footer_style))
    elements.append(Paragraph('www.pozinox.cl | info@pozinox.cl | +56 2 1234 5678', footer_style))
    elements.append(Paragraph('Este documento es una cotización y no constituye una factura', footer_style))
    
    # Construir PDF
    doc.build(elements)
    
    # Obtener el valor del buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Crear la respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Cotizacion_{cotizacion.numero_cotizacion}.pdf"'
    response.write(pdf)
    
    return response


# ============================================
# SISTEMA DE TRANSFERENCIAS BANCARIAS
# ============================================

@login_required
def procesar_pago_transferencia(request, cotizacion_id):
    """Página para procesar pago por transferencia bancaria"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    # Verificar que esté finalizada
    if cotizacion.estado not in ['finalizada', 'pagada', 'en_revision']:
        messages.error(request, 'La cotización debe estar finalizada para proceder al pago.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    # Verificar que no esté ya pagada o en revisión
    if cotizacion.estado in ['pagada', 'en_revision']:
        messages.info(request, 'Esta cotización ya tiene un pago registrado.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    # Si es POST, confirmar el pago
    if request.method == 'POST':
        # Obtener archivo y comentarios del formulario
        comprobante = request.FILES.get('comprobante_pago')
        comentarios = request.POST.get('comentarios_pago', '').strip()
        
        # Validar que se haya subido un comprobante
        if not comprobante:
            messages.error(request, 'Debes adjuntar el comprobante de transferencia.')
        else:
            # Validar tipo de archivo (solo imágenes y PDFs)
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.gif']
            file_extension = os.path.splitext(comprobante.name)[1].lower()
            
            if file_extension not in allowed_extensions:
                messages.error(request, f'Formato de archivo no permitido. Solo se aceptan: {", ".join(allowed_extensions)}')
            else:
                # Validar tamaño del archivo (máximo 10MB)
                if comprobante.size > 10 * 1024 * 1024:  # 10MB
                    messages.error(request, 'El archivo es demasiado grande. El tamaño máximo es 10MB.')
                else:
                    # Guardar comprobante y comentarios
                    cotizacion.comprobante_pago = comprobante
                    cotizacion.comentarios_pago = comentarios
                    cotizacion.metodo_pago = 'transferencia'
                    cotizacion.estado = 'en_revision'  # En revisión hasta que el admin apruebe
                    cotizacion.pago_completado = False  # No está completado hasta que se apruebe
                    cotizacion.save()
                    
                    # Crear o actualizar el objeto TransferenciaBancaria
                    transferencia, created = TransferenciaBancaria.objects.get_or_create(
                        cotizacion=cotizacion,
                        defaults={
                            'monto_transferencia': cotizacion.total,
                            'estado': 'pendiente',
                            'comprobante': comprobante,
                            'observaciones_cliente': comentarios,
                        }
                    )
                    
                    # Si ya existe, actualizar el comprobante y estado
                    if not created:
                        transferencia.comprobante = comprobante
                        transferencia.observaciones_cliente = comentarios
                        transferencia.estado = 'pendiente'
                        transferencia.save()
                    
                    messages.info(request, 'Tu comprobante de transferencia ha sido registrado. Está pendiente de verificación por un administrador.')
                    return redirect('pago_pendiente', cotizacion_id=cotizacion.id)
    
    # Obtener información de cuenta bancaria desde settings (o usar valores por defecto)
    cuenta_bancaria = {
        'banco': getattr(settings, 'BANCO_NOMBRE', 'Banco de Chile'),
        'tipo_cuenta': getattr(settings, 'BANCO_TIPO_CUENTA', 'Cuenta Corriente'),
        'numero_cuenta': getattr(settings, 'BANCO_NUMERO_CUENTA', '1234567890'),
        'rut_titular': getattr(settings, 'BANCO_RUT_TITULAR', '12.345.678-9'),
        'nombre_titular': getattr(settings, 'BANCO_NOMBRE_TITULAR', 'Pozinox S.A.'),
        'email_confirmacion': getattr(settings, 'BANCO_EMAIL_CONFIRMACION', 'info@pozinox.cl'),
    }
    
    detalles = cotizacion.detalles.all().select_related('producto')
    
    context = {
        'cotizacion': cotizacion,
        'detalles': detalles,
        'cuenta_bancaria': cuenta_bancaria,
    }
    return render(request, 'tienda/cotizaciones/pago_transferencia.html', context)


@login_required
def procesar_pago_efectivo(request, cotizacion_id):
    """Página para procesar pago en efectivo"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    # Verificar que esté finalizada
    if cotizacion.estado not in ['finalizada', 'pagada', 'en_revision']:
        messages.error(request, 'La cotización debe estar finalizada para proceder al pago.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    # Verificar que no esté ya pagada o en revisión
    if cotizacion.estado in ['pagada', 'en_revision']:
        messages.info(request, 'Esta cotización ya tiene un pago registrado.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    # Si es POST, confirmar el pago
    if request.method == 'POST':
        # Marcar como en revisión (se pagará al retirar)
        cotizacion.metodo_pago = 'efectivo'
        cotizacion.estado = 'en_revision'
        cotizacion.pago_completado = False  # No está completado hasta que se apruebe
        cotizacion.save()
        
        messages.success(request, 'Pago en efectivo registrado. Podrás pagar al retirar tu pedido.')
        return redirect('pago_exitoso', cotizacion_id=cotizacion.id)
    
    detalles = cotizacion.detalles.all().select_related('producto')
    
    # Información de retiro (desde settings o valores por defecto)
    info_retiro = {
        'direccion': getattr(settings, 'DIRECCION_RETIRO', 'Av. Principal 123, Santiago'),
        'horarios': getattr(settings, 'HORARIOS_RETIRO', 'Lunes a Viernes: 9:00 - 18:00'),
        'telefono': getattr(settings, 'TELEFONO_CONTACTO', '+56 2 1234 5678'),
    }
    
    context = {
        'cotizacion': cotizacion,
        'detalles': detalles,
        'info_retiro': info_retiro,
    }
    return render(request, 'tienda/cotizaciones/pago_efectivo.html', context)


@login_required
def detalle_transferencia(request, cotizacion_id):
    """Ver detalle de una transferencia bancaria"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    try:
        transferencia = cotizacion.transferencia
    except TransferenciaBancaria.DoesNotExist:
        messages.error(request, 'No existe una transferencia para esta cotización.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    context = {
        'cotizacion': cotizacion,
        'transferencia': transferencia,
    }
    return render(request, 'tienda/transferencias/detalle_transferencia.html', context)


@login_required
def subir_comprobante(request, cotizacion_id):
    """Subir comprobante de transferencia"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    try:
        transferencia = cotizacion.transferencia
    except TransferenciaBancaria.DoesNotExist:
        messages.error(request, 'No existe una transferencia para esta cotización.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    # Verificar que esté en estado pendiente
    if transferencia.estado != 'pendiente':
        messages.error(request, 'Esta transferencia ya fue procesada.')
        return redirect('detalle_transferencia', cotizacion_id=cotizacion.id)
    
    if request.method == 'POST':
        comprobante = request.FILES.get('comprobante')
        numero_transaccion = request.POST.get('numero_transaccion', '')
        fecha_transferencia = request.POST.get('fecha_transferencia', '')
        observaciones = request.POST.get('observaciones', '')
        
        if not comprobante:
            messages.error(request, 'Debes subir un comprobante de transferencia.')
            return redirect('subir_comprobante', cotizacion_id=cotizacion.id)
        
        # Actualizar la transferencia
        transferencia.comprobante = comprobante
        transferencia.numero_transaccion = numero_transaccion
        transferencia.observaciones_cliente = observaciones
        transferencia.estado = 'verificando'
        
        if fecha_transferencia:
            from datetime import datetime
            try:
                transferencia.fecha_transferencia = datetime.strptime(fecha_transferencia, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        transferencia.save()
        
        # Notificar a los trabajadores
        from apps.usuarios.models import Notificacion
        trabajadores = User.objects.filter(
            perfil__tipo_usuario__in=['administrador', 'trabajador']
        )
        
        for trabajador in trabajadores:
            Notificacion.objects.create(
                usuario=trabajador,
                tipo='info',
                titulo='Nueva Transferencia para Verificar',
                mensaje=f'Transferencia {transferencia.cotizacion.numero_cotizacion} requiere verificación.',
                modelo_relacionado='TransferenciaBancaria',
                objeto_id=transferencia.id
            )
        
        messages.success(request, 'Comprobante subido exitosamente. Será verificado en las próximas 24 horas.')
        return redirect('detalle_transferencia', cotizacion_id=cotizacion.id)
    
    context = {
        'cotizacion': cotizacion,
        'transferencia': transferencia,
    }
    return render(request, 'tienda/transferencias/subir_comprobante.html', context)


# ============================================
# PANEL DE VERIFICACIÓN PARA TRABAJADORES
# ============================================

@login_required
def panel_verificacion_transferencias(request):
    """Panel para verificar transferencias bancarias"""
    # Verificar permisos manualmente
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Verificar que el usuario tenga permisos de trabajador
    # Los superusuarios siempre tienen acceso
    if not request.user.is_superuser:
        # Verificar si tiene perfil y tipo de usuario válido (usa get_tipo_usuario_real para considerar superusuarios)
        if not hasattr(request.user, 'perfil') or request.user.perfil.get_tipo_usuario_real() not in ['administrador', 'trabajador']:
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('home')
    
    transferencias = TransferenciaBancaria.objects.filter(
        estado__in=['pendiente', 'verificando']
    ).order_by('-fecha_creacion')
    
    # Filtros
    estado = request.GET.get('estado')
    if estado:
        transferencias = transferencias.filter(estado=estado)
    
    # Paginación
    paginator = Paginator(transferencias, 10)
    page_number = request.GET.get('page')
    transferencias_paginadas = paginator.get_page(page_number)
    
    context = {
        'transferencias': transferencias_paginadas,
        'estado_actual': estado,
    }
    return render(request, 'tienda/transferencias/panel_verificacion.html', context)


@login_required
def verificar_transferencia(request, transferencia_id):
    """Verificar una transferencia bancaria"""
    # Verificar permisos manualmente
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Verificar que el usuario tenga permisos de trabajador
    # Los superusuarios siempre tienen acceso
    if not request.user.is_superuser:
        # Verificar si tiene perfil y tipo de usuario válido (usa get_tipo_usuario_real para considerar superusuarios)
        if not hasattr(request.user, 'perfil') or request.user.perfil.get_tipo_usuario_real() not in ['administrador', 'trabajador']:
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('home')
    
    transferencia = get_object_or_404(TransferenciaBancaria, id=transferencia_id)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        observaciones = request.POST.get('observaciones', '')
        
        if accion == 'aprobar':
            transferencia.aprobar(request.user, observaciones)
            messages.success(request, 'Transferencia aprobada exitosamente.')
            
            # Notificar al cliente
            from apps.usuarios.models import Notificacion
            Notificacion.objects.create(
                usuario=transferencia.cotizacion.usuario,
                tipo='success',
                titulo='Transferencia Aprobada',
                mensaje=f'Tu transferencia para la cotización {transferencia.cotizacion.numero_cotizacion} ha sido aprobada.',
                modelo_relacionado='TransferenciaBancaria',
                objeto_id=transferencia.id
            )
            
        elif accion == 'rechazar':
            transferencia.rechazar(request.user, observaciones)
            messages.success(request, 'Transferencia rechazada.')
            
            # Notificar al cliente
            from apps.usuarios.models import Notificacion
            Notificacion.objects.create(
                usuario=transferencia.cotizacion.usuario,
                tipo='error',
                titulo='Transferencia Rechazada',
                mensaje=f'Tu transferencia para la cotización {transferencia.cotizacion.numero_cotizacion} ha sido rechazada. Motivo: {observaciones}',
                modelo_relacionado='TransferenciaBancaria',
                objeto_id=transferencia.id
            )
        
        return redirect('panel_verificacion_transferencias')
    
    context = {
        'transferencia': transferencia,
    }
    return render(request, 'tienda/transferencias/verificar_transferencia.html', context)


# ============================================
# PÁGINAS LEGALES
# ============================================

def politica_privacidad(request):
    """Vista de política de privacidad"""
    return render(request, 'tienda/legal/politica_privacidad.html', {
        'titulo': 'Política de Privacidad - Pozinox'
    })


def terminos_condiciones(request):
    """Vista de términos y condiciones"""
    return render(request, 'tienda/legal/terminos_condiciones.html', {
        'titulo': 'Términos y Condiciones - Pozinox'
    })
