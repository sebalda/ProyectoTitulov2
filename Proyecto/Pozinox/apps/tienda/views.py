from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F, Count, Sum
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings
from django.urls import reverse
from .models import Producto, CategoriaAcero, Cotizacion, DetalleCotizacion, TransferenciaBancaria, RecepcionCompra, DetalleRecepcionCompra, VentaN8n
from .forms import ProductoForm, CategoriaForm
import mercadopago
import os
import json
import logging
from datetime import timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO

logger = logging.getLogger(__name__)

# ============================================
# FUNCIONES AUXILIARES
# ============================================
def es_superusuario(user):
    return user.is_superuser

def puede_editar_cotizacion(user, cotizacion):
    """Verifica si el usuario puede editar la cotización"""
    # Verificar si es staff (superusuario, trabajador o administrador)
    es_staff = user.is_superuser or (
        hasattr(user, 'perfil') and 
        user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    # Puede editar si: está en borrador Y (es el propietario O es quien la creó O es staff)
    return (
        cotizacion.estado == 'borrador' and (
            cotizacion.usuario == user or 
            cotizacion.creado_por == user or
            es_staff
        )
    )

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
        
        # Intentar enviar correos
        try:
            # Enviar correo a la empresa
            send_mail(
                subject=f"Nuevo mensaje de contacto de {nombre}",
                message=cuerpo,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=["pozinox.empresa@gmail.com"],
                fail_silently=False,
            )
            
            # Enviar correo de confirmación al usuario (HTML)
            from django.core.mail import EmailMultiAlternatives
            
            subject = "Confirmación de Contacto - Pozinox"
            text_content = f"Estimado/a {nombre}, hemos recibido tu mensaje correctamente."
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    
                    <!-- Header con logo -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 30px; text-align: center;">
                            <img src="https://mxwwqzguzcsgbefvyyge.supabase.co/storage/v1/object/public/Productos/static/footer_logopozi.png" 
                                 alt="Pozinox" style="max-width: 200px; height: auto;">
                            <h1 style="color: #ffffff; margin: 15px 0 0 0; font-size: 24px; font-weight: bold;">
                                CONFIRMACIÓN DE CONTACTO
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Contenido principal -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="color: #1e3a8a; font-size: 18px; font-weight: bold; margin: 0 0 20px 0;">
                                Estimado/a {nombre},
                            </p>
                            
                            <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                ¡Gracias por contactarnos! Nos complace confirmar que hemos recibido tu solicitud 
                                de contacto con éxito.
                            </p>
                            
                            <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                                Tu consulta ha sido registrada en nuestro sistema y será atendida por nuestro 
                                equipo de especialistas a la brevedad.
                            </p>
                            
                            <!-- Resumen de consulta -->
                            <div style="background-color: #f3f4f6; border-left: 4px solid #f59e0b; padding: 20px; margin: 0 0 30px 0; border-radius: 5px;">
                                <h3 style="color: #1e3a8a; margin: 0 0 15px 0; font-size: 16px; font-weight: bold;">
                                    📋 RESUMEN DE TU CONSULTA
                                </h3>
                                <p style="color: #4b5563; font-size: 14px; line-height: 1.6; margin: 0; white-space: pre-wrap;">
{mensaje}
                                </p>
                            </div>
                            
                            <!-- Información de contacto -->
                            <div style="background-color: #eff6ff; padding: 20px; border-radius: 5px; margin: 0 0 20px 0;">
                                <h3 style="color: #1e3a8a; margin: 0 0 15px 0; font-size: 16px; font-weight: bold;">
                                    📞 INFORMACIÓN DE CONTACTO
                                </h3>
                                <table width="100%" cellpadding="5" cellspacing="0">
                                    <tr>
                                        <td style="color: #4b5563; font-size: 14px; padding: 5px 0;">
                                            <strong>Teléfono:</strong> +56 2 2345 6789
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="color: #4b5563; font-size: 14px; padding: 5px 0;">
                                            <strong>Email:</strong> ventas@pozinox.cl
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="color: #4b5563; font-size: 14px; padding: 5px 0;">
                                            <strong>Web:</strong> www.pozinox.cl
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="color: #4b5563; font-size: 14px; padding: 5px 0;">
                                            <strong>Dirección:</strong> Av. Industrial 1234, Santiago - Chile
                                        </td>
                                    </tr>
                                </table>
                            </div>
                            
                            <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 0; font-style: italic;">
                                En Pozinox nos especializamos en ofrecer soluciones integrales en acero inoxidable 
                                de la más alta calidad, respaldados por años de experiencia y un compromiso 
                                inquebrantable con la excelencia.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #1e293b; padding: 30px; text-align: center;">
                            <p style="color: #94a3b8; font-size: 14px; margin: 0 0 10px 0; font-weight: bold;">
                                Equipo Comercial POZINOX
                            </p>
                            <p style="color: #94a3b8; font-size: 12px; margin: 0 0 15px 0;">
                                Especialistas en Acero Inoxidable | Tecnología e Innovación
                            </p>
                            <div style="border-top: 1px solid #475569; padding-top: 15px;">
                                <p style="color: #64748b; font-size: 11px; margin: 0; line-height: 1.5;">
                                    Este es un mensaje automático, por favor no responder directamente a este correo.<br>
                                    Para consultas, utiliza los canales de contacto indicados anteriormente.
                                </p>
                            </div>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
            
            msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            success = "¡Mensaje enviado correctamente! Hemos enviado un correo de confirmación a tu email."
            
        except Exception as e:
            success = "¡Mensaje recibido! Nos contactaremos pronto."

        context = {
            'productos_destacados': Producto.objects.filter(activo=True)[:6],
            'categorias': CategoriaAcero.objects.filter(activa=True)[:4],
            'titulo': 'Pozinox - Tienda de Aceros',
            'success': success,
        }
        return render(request, 'tienda/home.html', context)


def contacto(request):
    """Vista de la página de contacto"""
    from django.core.mail import send_mail
    
    if request.method == 'GET':
        return render(request, 'tienda/contacto.html')
    
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
        
        # Intentar enviar correos
        try:
            # Enviar correo a la empresa
            send_mail(
                subject=f"Nuevo mensaje de contacto de {nombre}",
                message=cuerpo,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=["pozinox.empresa@gmail.com"],
                fail_silently=False,
            )
            
            # Enviar correo de confirmación al usuario (HTML)
            from django.core.mail import EmailMultiAlternatives
            
            subject = "Confirmación de Contacto - Pozinox"
            text_content = f"Estimado/a {nombre}, hemos recibido tu mensaje correctamente."
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    
                    <!-- Header con logo -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 30px; text-align: center;">
                            <img src="https://mxwwqzguzcsgbefvyyge.supabase.co/storage/v1/object/public/Productos/static/footer_logopozi.png" 
                                 alt="Pozinox" style="max-width: 200px; height: auto;">
                            <h1 style="color: #ffffff; margin: 15px 0 0 0; font-size: 24px; font-weight: bold;">
                                CONFIRMACIÓN DE CONTACTO
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Contenido principal -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="color: #1e3a8a; font-size: 18px; font-weight: bold; margin: 0 0 20px 0;">
                                Estimado/a {nombre},
                            </p>
                            
                            <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                ¡Gracias por contactarnos! Nos complace confirmar que hemos recibido tu solicitud 
                                de contacto con éxito.
                            </p>
                            
                            <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                                Tu consulta ha sido registrada en nuestro sistema y será atendida por nuestro 
                                equipo de especialistas a la brevedad.
                            </p>
                            
                            <!-- Resumen de consulta -->
                            <div style="background-color: #f3f4f6; border-left: 4px solid #f59e0b; padding: 20px; margin: 0 0 30px 0; border-radius: 5px;">
                                <h3 style="color: #1e3a8a; margin: 0 0 15px 0; font-size: 16px; font-weight: bold;">
                                    📋 RESUMEN DE TU CONSULTA
                                </h3>
                                <p style="color: #4b5563; font-size: 14px; line-height: 1.6; margin: 0; white-space: pre-wrap;">
{mensaje}
                                </p>
                            </div>
                            
                            <!-- Información de contacto -->
                            <div style="background-color: #eff6ff; padding: 20px; border-radius: 5px; margin: 0 0 20px 0;">
                                <h3 style="color: #1e3a8a; margin: 0 0 15px 0; font-size: 16px; font-weight: bold;">
                                    📞 INFORMACIÓN DE CONTACTO
                                </h3>
                                <table width="100%" cellpadding="5" cellspacing="0">
                                    <tr>
                                        <td style="color: #4b5563; font-size: 14px; padding: 5px 0;">
                                            <strong>Teléfono:</strong> +56 2 2345 6789
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="color: #4b5563; font-size: 14px; padding: 5px 0;">
                                            <strong>Email:</strong> ventas@pozinox.cl
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="color: #4b5563; font-size: 14px; padding: 5px 0;">
                                            <strong>Web:</strong> www.pozinox.cl
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="color: #4b5563; font-size: 14px; padding: 5px 0;">
                                            <strong>Dirección:</strong> Av. Industrial 1234, Santiago - Chile
                                        </td>
                                    </tr>
                                </table>
                            </div>
                            
                            <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 0; font-style: italic;">
                                En Pozinox nos especializamos en ofrecer soluciones integrales en acero inoxidable 
                                de la más alta calidad, respaldados por años de experiencia y un compromiso 
                                inquebrantable con la excelencia.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #1e293b; padding: 30px; text-align: center;">
                            <p style="color: #94a3b8; font-size: 14px; margin: 0 0 10px 0; font-weight: bold;">
                                Equipo Comercial POZINOX
                            </p>
                            <p style="color: #94a3b8; font-size: 12px; margin: 0 0 15px 0;">
                                Especialistas en Acero Inoxidable | Tecnología e Innovación
                            </p>
                            <div style="border-top: 1px solid #475569; padding-top: 15px;">
                                <p style="color: #64748b; font-size: 11px; margin: 0; line-height: 1.5;">
                                    Este es un mensaje automático, por favor no responder directamente a este correo.<br>
                                    Para consultas, utiliza los canales de contacto indicados anteriormente.
                                </p>
                            </div>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
            
            msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            # Mostrar mensaje de éxito
            success = "¡Mensaje enviado correctamente! Hemos enviado un correo de confirmación a tu email."
            
        except Exception as e:
            # Mostrar mensaje de éxito aunque falle el correo (para no confundir al usuario)
            success = "¡Mensaje recibido! Nos contactaremos pronto."
        
        context = {
            'success': success,
        }
        return render(request, 'tienda/contacto.html', context)


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
def reportes_generales(request):
    """Generar reportes generales: ventas, stock, cotizaciones"""
    import datetime

    tipo = request.GET.get('tipo') or request.POST.get('tipo') or 'ventas'
    # Rango por defecto: últimos 30 días
    hoy = timezone.now()
    fecha_desde = request.GET.get('desde') or request.POST.get('desde')
    fecha_hasta = request.GET.get('hasta') or request.POST.get('hasta')
    try:
        if fecha_desde:
            fecha_desde_dt = timezone.make_aware(datetime.datetime.fromisoformat(fecha_desde))
        else:
            fecha_desde_dt = hoy - datetime.timedelta(days=30)
    except Exception:
        fecha_desde_dt = hoy - datetime.timedelta(days=30)
    try:
        if fecha_hasta:
            fecha_hasta_dt = timezone.make_aware(datetime.datetime.fromisoformat(fecha_hasta))
        else:
            fecha_hasta_dt = hoy
    except Exception:
        fecha_hasta_dt = hoy

    results = []
    no_data = False

    # Normalize fecha_hasta to include the whole day if it is a date
    try:
        if hasattr(fecha_hasta_dt, 'hour') and fecha_hasta_dt.hour == 0 and fecha_hasta_dt.minute == 0 and fecha_hasta_dt.second == 0:
            fecha_hasta_dt = fecha_hasta_dt.replace(hour=23, minute=59, second=59)
    except Exception:
        pass

    # Estados de cotización que consideramos para ventas/ingresos/productos vendidos
    estados_ventas = ['pagada', 'finalizada', 'en_revision']

    if tipo == 'ventas':
        # Ventas: sumamos el total por día dentro del rango
        qs = Cotizacion.objects.filter(fecha_creacion__gte=fecha_desde_dt, fecha_creacion__lte=fecha_hasta_dt, estado__in=estados_ventas)
        if not qs.exists():
            no_data = True
        else:
            ventas_por_dia = qs.extra(select={'dia': "date(fecha_creacion)"}).values('dia').annotate(total=Sum('total')).order_by('dia')
            results = [{'label': v['dia'], 'value': v['total'] or 0} for v in ventas_por_dia]

    elif tipo == 'ingresos':
        # Ingresos por fecha: similar a ventas, pero explícito
        qs = Cotizacion.objects.filter(fecha_creacion__gte=fecha_desde_dt, fecha_creacion__lte=fecha_hasta_dt, estado__in=estados_ventas)
        if not qs.exists():
            no_data = True
        else:
            ingresos_por_dia = qs.extra(select={'dia': "date(fecha_creacion)"}).values('dia').annotate(total=Sum('total')).order_by('dia')
            results = [{'label': v['dia'], 'value': v['total'] or 0} for v in ingresos_por_dia]

    elif tipo == 'productos_mas_vendidos':
        # Productos más vendidos: sumar cantidades en DetalleCotizacion para cotizaciones pagadas/finalizadas
        detalles_qs = DetalleCotizacion.objects.filter(cotizacion__fecha_creacion__gte=fecha_desde_dt, cotizacion__fecha_creacion__lte=fecha_hasta_dt, cotizacion__estado__in=estados_ventas)
        if not detalles_qs.exists():
            no_data = True
        else:
            vendidos = detalles_qs.values('producto__id', 'producto__nombre').annotate(total_vendido=Sum('cantidad')).order_by('-total_vendido')[:100]
            results = list(vendidos)

    elif tipo == 'clientes':
        # Reporte de clientes: top por total comprado y número de pedidos
        qs = Cotizacion.objects.filter(fecha_creacion__gte=fecha_desde_dt, fecha_creacion__lte=fecha_hasta_dt, estado__in=estados_ventas)
        if not qs.exists():
            no_data = True
        else:
            clientes_qs = qs.values('usuario__id', 'usuario__username', 'usuario__first_name', 'usuario__last_name').annotate(total_gastado=Sum('total'), pedidos=Count('id')).order_by('-total_gastado')[:100]
            results = list(clientes_qs)

    elif tipo == 'stock':
        # Productos con stock bajo
        qs = Producto.objects.filter(stock_actual__lte=F('stock_minimo'))
        if not qs.exists():
            no_data = True
        else:
            results = list(qs.values('id', 'nombre', 'stock_actual', 'stock_minimo', 'categoria__nombre'))

    elif tipo == 'cotizaciones':
        qs = Cotizacion.objects.filter(fecha_creacion__gte=fecha_desde_dt, fecha_creacion__lte=fecha_hasta_dt)
        if not qs.exists():
            no_data = True
        else:
            results = list(qs.values('numero_cotizacion', 'usuario__username', 'estado', 'total', 'fecha_creacion')[:100])

    else:
        no_data = True

    context = {
        'tipo': tipo,
        'results': results,
        'no_data': no_data,
        'fecha_desde': fecha_desde_dt.date() if fecha_desde_dt else None,
        'fecha_hasta': fecha_hasta_dt.date() if fecha_hasta_dt else None,
    }
    return render(request, 'tienda/admin/reportes_generales.html', context)


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
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado exitosamente.')
            
            # Restaurar todos los parámetros de navegación desde POST
            params = []
            page = request.POST.get('page', '')
            categoria = request.POST.get('categoria', '')
            estado = request.POST.get('estado', '')
            busqueda = request.POST.get('q', '')
            scroll = request.POST.get('scroll_position', '')
            
            if page:
                params.append(f"page={page}")
            if categoria:
                params.append(f"categoria={categoria}")
            if estado:
                params.append(f"estado={estado}")
            if busqueda:
                params.append(f"q={busqueda}")
            if scroll:
                params.append(f"scroll={scroll}")
            
            redirect_url = reverse('lista_productos_admin')
            if params:
                redirect_url += '?' + '&'.join(params)
            
            return redirect(redirect_url)
    else:
        form = ProductoForm(instance=producto)
    
    # Capturar parámetros de navegación desde GET
    context = {
        'form': form, 
        'producto': producto, 
        'titulo': 'Editar Producto',
        'scroll_position': request.GET.get('scroll', '0'),
        'page': request.GET.get('page', ''),
        'categoria': request.GET.get('categoria', ''),
        'estado': request.GET.get('estado', ''),
        'busqueda': request.GET.get('q', ''),
    }
    
    return render(request, 'tienda/admin/formulario_producto.html', context)


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
def todas_cotizaciones(request):
    """Lista de TODAS las cotizaciones - Solo para staff/trabajadores/administradores"""
    # Verificar permisos
    tiene_permiso = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if not tiene_permiso:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('mis_cotizaciones')
    
    # Obtener TODAS las cotizaciones
    cotizaciones = Cotizacion.objects.all().select_related('usuario', 'creado_por').order_by('-fecha_creacion')
    
    # Aplicar filtros
    estado = request.GET.get('estado')
    busqueda = request.GET.get('q', '').strip()
    
    if estado:
        cotizaciones = cotizaciones.filter(estado=estado)
    
    if busqueda:
        from django.db.models import Q
        cotizaciones = cotizaciones.filter(
            Q(numero_cotizacion__icontains=busqueda) |
            Q(usuario__username__icontains=busqueda) |
            Q(usuario__first_name__icontains=busqueda) |
            Q(usuario__last_name__icontains=busqueda) |
            Q(usuario__email__icontains=busqueda)
        )
    
    return render(request, 'tienda/cotizaciones/todas_cotizaciones.html', {
        'cotizaciones': paginar_queryset(cotizaciones, request, 20),
        'estado_actual': estado,
        'busqueda': busqueda,
    })


@login_required
def crear_cotizacion(request):
    """Crear nueva cotización o obtener la cotización en borrador actual"""
    cotizacion = Cotizacion.objects.filter(usuario=request.user, estado='borrador').first()
    
    if not cotizacion:
        cotizacion = Cotizacion.objects.create(usuario=request.user)
        messages.success(request, f'Nueva cotización {cotizacion.numero_cotizacion} creada.')
    
    # Si se proporciona un producto_id, agregarlo automáticamente
    producto_id = request.GET.get('producto_id')
    if producto_id:
        try:
            producto = Producto.objects.get(id=producto_id, activo=True)
            cantidad = int(request.GET.get('cantidad', 1))
            
            # Verificar si el producto ya está en la cotización
            detalle, created = DetalleCotizacion.objects.get_or_create(
                cotizacion=cotizacion,
                producto=producto,
                defaults={'cantidad': cantidad, 'precio_unitario': producto.precio_por_unidad}
            )
            
            if not created:
                # Si ya existe, incrementar la cantidad
                detalle.cantidad += cantidad
                detalle.save()
                messages.success(request, f'Se agregó {cantidad} más de "{producto.nombre}" a tu cotización.')
            else:
                messages.success(request, f'"{producto.nombre}" agregado a tu cotización.')
        except Producto.DoesNotExist:
            messages.error(request, 'El producto seleccionado no está disponible.')
    
    return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)


@login_required
def crear_cotizacion_para_cliente(request):
    """Vista para que trabajadores/administradores creen cotizaciones para clientes"""
    from django.contrib.auth.models import User
    
    # Verificar permisos
    tiene_permiso = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if not tiene_permiso:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('home')
    
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        
        if not cliente_id:
            messages.error(request, 'Debes seleccionar un cliente.')
            return redirect('crear_cotizacion_para_cliente')
        
        try:
            cliente = User.objects.get(id=cliente_id)
            
            # Verificar si el cliente ya tiene una cotización en borrador
            cotizacion = Cotizacion.objects.filter(usuario=cliente, estado='borrador').first()
            
            if cotizacion:
                messages.info(request, f'El cliente {cliente.get_full_name() or cliente.username} ya tiene una cotización en borrador.')
            else:
                # Crear cotización y registrar quién la creó
                cotizacion = Cotizacion.objects.create(
                    usuario=cliente,
                    creado_por=request.user  # Registrar el trabajador/admin que la creó
                )
                messages.success(request, f'Cotización {cotizacion.numero_cotizacion} creada para {cliente.get_full_name() or cliente.username}.')
            
            return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
            
        except User.DoesNotExist:
            messages.error(request, 'Cliente no encontrado.')
            return redirect('crear_cotizacion_para_cliente')
    
    # GET request - mostrar formulario simple
    return render(request, 'tienda/cotizaciones/crear_cotizacion_cliente.html', {})


@login_required
def detalle_cotizacion(request, cotizacion_id):
    """Ver detalle de una cotización"""
    # Superusuarios, administradores y trabajadores pueden ver cualquier cotización
    es_staff = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if es_staff:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    else:
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
    
    # Puede editar si: está en borrador Y (es el propietario O es quien la creó O es staff/admin/trabajador)
    puede_editar = (
        cotizacion.estado == 'borrador' and (
            cotizacion.usuario == request.user or 
            cotizacion.creado_por == request.user or
            es_staff
        )
    )
    
    return render(request, 'tienda/cotizaciones/detalle_cotizacion.html', {
        'cotizacion': cotizacion,
        'detalles': detalles,
        'productos_disponibles': productos_disponibles[:20],
        'categorias': CategoriaAcero.objects.filter(activa=True),
        'puede_editar': puede_editar,
    })


@login_required
@require_POST
def agregar_producto_cotizacion(request, cotizacion_id):
    """Agregar un producto a la cotización"""
    # Verificar permisos: staff puede ver cualquier cotización, usuarios solo las suyas
    es_staff = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if es_staff:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    else:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    # Verificar si puede editar
    if not puede_editar_cotizacion(request.user, cotizacion):
        messages.error(request, 'No tienes permisos para editar esta cotización.')
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
    
    if not puede_editar_cotizacion(request.user, cotizacion):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
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
    
    if not puede_editar_cotizacion(request.user, cotizacion):
        messages.error(request, 'No autorizado.')
        return redirect('mis_cotizaciones')
    
    producto_nombre = detalle.producto.nombre
    detalle.delete()
    messages.success(request, f'{producto_nombre} eliminado de la cotización.')
    
    return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)


@login_required
def finalizar_cotizacion(request, cotizacion_id):
    """Finalizar cotización y mostrar opciones de pago"""
    # Verificar permisos: staff puede ver cualquier cotización, usuarios solo las suyas
    es_staff = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if es_staff:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    else:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    if not puede_editar_cotizacion(request.user, cotizacion):
        messages.error(request, 'No tienes permisos para finalizar esta cotización.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    if cotizacion.estado != 'borrador':
        messages.error(request, 'Esta cotización ya fue finalizada.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    if not cotizacion.detalles.exists():
        messages.error(request, 'Debe agregar al menos un producto a la cotización.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    # Verificar si la cotización ha vencido
    if cotizacion.esta_vencida():
        messages.error(request, 'Esta cotización ha vencido. Los precios pueden haber cambiado. Por favor, crea una nueva cotización.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    cotizacion.estado = 'finalizada'
    cotizacion.fecha_finalizacion = timezone.now()
    cotizacion.save()
    
    messages.success(request, 'Cotización finalizada. Seleccione un método de pago.')
    return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)


@login_required
def seleccionar_pago(request, cotizacion_id):
    """Página para seleccionar método de pago"""
    # Verificar permisos: staff puede ver cualquier cotización, usuarios solo las suyas
    es_staff = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if es_staff:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    else:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    if cotizacion.estado not in ['finalizada', 'pagada']:
        messages.error(request, 'La cotización debe estar finalizada para proceder al pago.')
        return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)
    
    # Verificar si la cotización ha vencido
    if cotizacion.esta_vencida():
        messages.error(request, 'Esta cotización ha vencido. Los precios pueden haber cambiado. Por favor, crea una nueva cotización.')
        return redirect('mis_cotizaciones')
    
    return render(request, 'tienda/cotizaciones/seleccionar_pago.html', {
        'cotizacion': cotizacion,
        'detalles': cotizacion.detalles.all().select_related('producto'),
        'tiene_transferencia': hasattr(cotizacion, 'transferencia'),
    })


@login_required
def simular_pago_exitoso(request, cotizacion_id):
    """
    ⚠️ SOLO PARA PRUEBAS LOCALES - Simula un pago exitoso de MercadoPago
    Esta vista NO debe usarse en producción
    """
    if not settings.DEBUG:
        messages.error(request, 'Esta función solo está disponible en modo DEBUG.')
        return redirect('home')
    
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    
    # Verificar permisos
    es_propietario = cotizacion.usuario == request.user
    es_creador = cotizacion.creado_por == request.user if cotizacion.creado_por else False
    es_staff = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if not (es_propietario or es_creador or es_staff):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('home')
    
    # Simular pago exitoso
    import uuid
    fake_payment_id = f"TEST-{uuid.uuid4().hex[:8]}"
    
    return redirect(
        f"/cotizaciones/{cotizacion_id}/pago-exitoso/?payment_id={fake_payment_id}&status=approved&collection_status=approved"
    )


@login_required
def procesar_pago_mercadopago(request, cotizacion_id):
    """Crear preferencia de pago en MercadoPago y redirigir"""
    logger.error(f"=== PROCESAR PAGO MERCADOPAGO EJECUTADO === Cotización ID: {cotizacion_id}, Usuario: {request.user.username}")
    
    # Verificar permisos: staff puede ver cualquier cotización, usuarios solo las suyas
    es_staff = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    logger.error(f"Es staff: {es_staff}")
    
    if es_staff:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    else:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    logger.error(f"Cotización encontrada: {cotizacion.numero_cotizacion}, Estado: {cotizacion.estado}")
    
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
        # 1. Primero revisar si hay un MERCADOPAGO_BASE_URL configurado (para producción)
        base_url = os.getenv('MERCADOPAGO_BASE_URL') or getattr(settings, 'MERCADOPAGO_BASE_URL', None)
        
        if not base_url:
            # 2. Detectar si se está usando un túnel (ngrok, localtunnel, etc.)
            # Estos túneles envían el header X-Forwarded-Host o el Host original
            forwarded_host = request.META.get('HTTP_X_FORWARDED_HOST')
            
            if forwarded_host and 'ngrok' in forwarded_host:
                # Estamos detrás de ngrok, usar la URL pública
                base_url = f"https://{forwarded_host}"
                logger.info(f"✅ Detectado túnel ngrok: {base_url}")
            else:
                # 3. Usar la URL del request como último recurso
                scheme = request.scheme
                host = request.get_host()
                
                # Para desarrollo local sin túnel, advertir que no funcionará
                if host in ['localhost', '127.0.0.1'] or host.startswith('localhost:') or host.startswith('127.0.0.1:'):
                    scheme = 'http'
                    if ':' not in host:
                        host = f"{host}:8000"
                    logger.warning(f"⚠️ Usando localhost - MercadoPago NO podrá redirigir. Usa ngrok: ngrok http 8000")
                
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
            "auto_return": "approved",  # Redirección automática cuando el pago es aprobado
            "external_reference": cotizacion.numero_cotizacion,
            "statement_descriptor": "Pozinox",
            "notification_url": f"{base_url}/webhooks/mercadopago/",  # Webhook para notificaciones
            "payer": {
                "name": request.user.first_name or request.user.username,
                "surname": request.user.last_name or "",
                "email": request.user.email,
            },
            "metadata": {
                "cotizacion_id": str(cotizacion.id),
                "numero_cotizacion": cotizacion.numero_cotizacion,
            },
            "binary_mode": True,  # Forzar estados approved/rejected (sin pending)
        }
        
        # Log de los datos que se envían (sin información sensible)
        logger.error(f'Creando preferencia de MercadoPago para cotización {cotizacion.numero_cotizacion}')
        logger.error(f'SUCCESS URL: {success_url}')
        logger.error(f'FAILURE URL: {failure_url}')
        logger.error(f'PENDING URL: {pending_url}')
        logger.error(f'Items: {len(items)} productos, Total: ${cotizacion.total}')
        
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
        
        # ⚠️ MODO DE PRUEBA LOCAL: Si estamos en localhost, agregar parámetro para simular pago
        if 'localhost' in base_url or '127.0.0.1' in base_url:
            logger.warning('⚠️ MODO PRUEBA LOCAL: MercadoPago no podrá redirigir desde localhost.')
            logger.warning('💡 OPCIÓN 1: Después de pagar, copia manualmente esta URL en tu navegador:')
            logger.warning(f'   {success_url}?payment_id=TEST123&status=approved&collection_status=approved')
            logger.warning('💡 OPCIÓN 2: Usa ngrok para pruebas reales: ngrok http 8000')
        
        return redirect(init_point)
        
    except Exception as e:
        logger.exception(f'Error al procesar pago de MercadoPago para cotización {cotizacion_id}')
        messages.error(request, f'Error al procesar el pago: {str(e)}')
        return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)


def pago_exitoso(request, cotizacion_id):
    """Página de confirmación de pago exitoso"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    
    # Verificar si viene de MercadoPago (tiene payment_id en la URL)
    viene_de_mercadopago = request.GET.get('payment_id') or request.GET.get('collection_id')
    
    # PERMITIR ACCESO SIN AUTENTICACIÓN si viene de MercadoPago
    # (Las cookies de sesión se pierden en la redirección externa)
    if not viene_de_mercadopago and not request.user.is_authenticated:
        messages.error(request, 'Debes iniciar sesión para ver esta página.')
        return redirect('login')
    
    # Verificar permisos solo si está autenticado
    if request.user.is_authenticated:
        es_propietario = cotizacion.usuario == request.user
        es_creador = cotizacion.creado_por == request.user if cotizacion.creado_por else False
        es_staff = request.user.is_superuser or (
            hasattr(request.user, 'perfil') and 
            request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
        )
        
        if not (es_propietario or es_creador or es_staff):
            messages.error(request, 'No tienes permisos para ver esta página.')
            return redirect('home')
    
    # Obtener payment_id de MercadoPago si está disponible
    # MercadoPago puede enviar payment_id, collection_id, o preference_id
    payment_id = (
        request.GET.get('payment_id') or 
        request.GET.get('collection_id') or 
        request.GET.get('preference_id')
    )
    
    # Obtener el estado directamente de los parámetros de la URL
    collection_status = request.GET.get('collection_status') or request.GET.get('status')
    
    # Si hay un payment_id, verificar el estado del pago con MercadoPago
    if payment_id and getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None):
        try:
            mp_access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None) or os.getenv('MERCADOPAGO_ACCESS_TOKEN')
            sdk = mercadopago.SDK(mp_access_token)
            
            # Intentar obtener el pago usando payment_id o collection_id
            payment_response = sdk.payment().get(payment_id)
            
            if "error" not in payment_response:
                payment = payment_response["response"]
                status = payment.get("status", collection_status)
                
                # Actualizar información del pago
                cotizacion.mercadopago_payment_id = str(payment.get("id", payment_id))
                
                if status == 'approved':
                    # Marcar como pagada cuando el pago está aprobado
                    cotizacion.estado = 'pagada'
                    cotizacion.pago_completado = True
                    cotizacion.metodo_pago = 'mercadopago'
                    cotizacion.save()
                    
                    # Enviar email de confirmación de compra
                    try:
                        from apps.tienda.views import enviar_confirmacion_compra
                        enviar_confirmacion_compra(cotizacion)
                    except Exception as e:
                        logger.exception(f'Error al enviar confirmación de compra: {e}')
                    
                    # IMPORTANTE: Facturación automática para pagos con MercadoPago desde la página web
                    # Boleta para persona natural, factura para empresa
                    try:
                        facturado = facturar_cotizacion_automaticamente(cotizacion, usuario_que_factura=None)
                        if facturado:
                            logger.info(f'✅ Facturación automática exitosa para cotización {cotizacion.numero_cotizacion}')
                            messages.success(request, f'¡Pago exitoso! Tu cotización ha sido pagada y facturada automáticamente.')
                        else:
                            logger.warning(f'⚠️ No se pudo facturar automáticamente la cotización {cotizacion.numero_cotizacion} (faltan datos del cliente o ya estaba facturada)')
                            messages.success(request, '¡Pago exitoso! Tu cotización ha sido pagada correctamente.')
                    except Exception as e:
                        logger.exception(f'Error en facturación automática para cotización {cotizacion.id}: {e}')
                        messages.success(request, '¡Pago exitoso! Tu cotización ha sido pagada correctamente.')
                elif status == 'pending':
                    cotizacion.estado = 'en_revision'
                    cotizacion.pago_completado = False
                    messages.info(request, 'Tu pago está siendo procesado. Te notificaremos cuando sea confirmado.')
                elif status in ['rejected', 'cancelled']:
                    messages.warning(request, f'El pago fue {status}. Por favor, intenta nuevamente.')
                    return redirect('seleccionar_pago', cotizacion_id=cotizacion.id)
                
                cotizacion.save()
            else:
                # Si no se pudo obtener el pago, verificar el estado desde la URL
                if collection_status == 'approved':
                    cotizacion.estado = 'pagada'
                    cotizacion.pago_completado = True
                    cotizacion.mercadopago_payment_id = str(payment_id)
                    cotizacion.metodo_pago = 'mercadopago'
                    cotizacion.save()
                    
                    # Enviar email de confirmación
                    try:
                        from apps.tienda.views import enviar_confirmacion_compra
                        enviar_confirmacion_compra(cotizacion)
                    except Exception as e:
                        logger.exception(f'Error al enviar confirmación de compra: {e}')
                    
                    # IMPORTANTE: Facturación automática para pagos con MercadoPago desde la página web
                    # Boleta para persona natural, factura para empresa
                    try:
                        facturado = facturar_cotizacion_automaticamente(cotizacion, usuario_que_factura=None)
                        if facturado:
                            logger.info(f'✅ Facturación automática exitosa para cotización {cotizacion.numero_cotizacion}')
                            messages.success(request, f'¡Pago exitoso! Tu cotización ha sido pagada y facturada automáticamente.')
                        else:
                            logger.warning(f'⚠️ No se pudo facturar automáticamente la cotización {cotizacion.numero_cotizacion} (faltan datos del cliente o ya estaba facturada)')
                            messages.success(request, '¡Pago exitoso! Tu cotización ha sido pagada correctamente.')
                    except Exception as e:
                        logger.exception(f'Error en facturación automática para cotización {cotizacion.id}: {e}')
                        messages.success(request, '¡Pago exitoso! Tu cotización ha sido pagada correctamente.')
        except Exception as e:
            logger.exception(f'Error al verificar pago {payment_id} en pago_exitoso: {e}')
            # Si falla la verificación pero el status en la URL es approved, marcar como pagada
            if collection_status == 'approved':
                cotizacion.estado = 'pagada'
                cotizacion.pago_completado = True
                cotizacion.mercadopago_payment_id = str(payment_id) if payment_id else ''
                cotizacion.metodo_pago = 'mercadopago'
                cotizacion.save()
                
                # IMPORTANTE: Facturación automática para pagos con MercadoPago desde la página web
                # Boleta para persona natural, factura para empresa
                try:
                    facturado = facturar_cotizacion_automaticamente(cotizacion, usuario_que_factura=None)
                    if facturado:
                        logger.info(f'✅ Facturación automática exitosa para cotización {cotizacion.numero_cotizacion}')
                        messages.success(request, f'¡Pago exitoso! Tu cotización ha sido pagada y facturada automáticamente.')
                    else:
                        logger.warning(f'⚠️ No se pudo facturar automáticamente la cotización {cotizacion.numero_cotizacion} (faltan datos del cliente o ya estaba facturada)')
                        messages.success(request, '¡Pago exitoso! Tu cotización ha sido pagada correctamente.')
                except Exception as e:
                    logger.exception(f'Error en facturación automática para cotización {cotizacion.id}: {e}')
                    messages.success(request, '¡Pago exitoso! Tu cotización ha sido pagada correctamente.')
            # Continuar de todas formas, mostrar la página de éxito
    
    # Mostrar la página de revisión si está en revisión o pagada
    if cotizacion.estado in ['pagada', 'en_revision']:
        context = {
            'cotizacion': cotizacion,
        }
        return render(request, 'tienda/cotizaciones/pago_exitoso.html', context)
    
    # Si no está en un estado válido, redirigir
    return redirect('detalle_cotizacion', cotizacion_id=cotizacion.id)


def pago_fallido(request, cotizacion_id):
    """Página de pago fallido"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    
    # Verificar si viene de MercadoPago
    viene_de_mercadopago = request.GET.get('payment_id') or request.GET.get('collection_id') or request.GET.get('preference_id')
    
    # PERMITIR ACCESO SIN AUTENTICACIÓN si viene de MercadoPago
    if not viene_de_mercadopago and not request.user.is_authenticated:
        messages.error(request, 'Debes iniciar sesión para ver esta página.')
        return redirect('login')
    
    # Verificar permisos solo si está autenticado
    if request.user.is_authenticated:
        es_propietario = cotizacion.usuario == request.user
        es_creador = cotizacion.creado_por == request.user if cotizacion.creado_por else False
        es_staff = request.user.is_superuser or (
            hasattr(request.user, 'perfil') and 
            request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
        )
        
        if not (es_propietario or es_creador or es_staff):
            messages.error(request, 'No tienes permisos para ver esta página.')
            return redirect('home')
    
    context = {
        'cotizacion': cotizacion,
    }
    return render(request, 'tienda/cotizaciones/pago_fallido.html', context)


def pago_pendiente(request, cotizacion_id):
    """Página de pago pendiente"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    
    # Verificar si viene de MercadoPago
    viene_de_mercadopago = request.GET.get('payment_id') or request.GET.get('collection_id') or request.GET.get('preference_id')
    
    # PERMITIR ACCESO SIN AUTENTICACIÓN si viene de MercadoPago
    if not viene_de_mercadopago and not request.user.is_authenticated:
        messages.error(request, 'Debes iniciar sesión para ver esta página.')
        return redirect('login')
    
    # Verificar permisos solo si está autenticado
    if request.user.is_authenticated:
        es_propietario = cotizacion.usuario == request.user
        es_creador = cotizacion.creado_por == request.user if cotizacion.creado_por else False
        es_staff = request.user.is_superuser or (
            hasattr(request.user, 'perfil') and 
            request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
        )
    
    if not (es_propietario or es_creador or es_staff):
        messages.error(request, 'No tienes permisos para ver esta página.')
        return redirect('home')
    
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
                        cotizacion.metodo_pago = 'mercadopago'
                        cotizacion.mercadopago_payment_id = str(payment.get("id", ""))
                        cotizacion.save()
                        
                        # Enviar email de confirmación de compra
                        try:
                            enviar_confirmacion_compra(cotizacion)
                        except Exception as e:
                            logger.exception(f'Error al enviar confirmación de compra: {e}')
                        
                        # IMPORTANTE: Facturación automática para pagos con MercadoPago desde la página web
                        # Boleta para persona natural, factura para empresa
                        try:
                            facturado = facturar_cotizacion_automaticamente(cotizacion, usuario_que_factura=None)
                            if facturado:
                                logger.info(f'✅ Facturación automática exitosa para cotización {cotizacion.numero_cotizacion}')
                                messages.success(request, f'¡Tu pago ha sido confirmado! Cotización facturada automáticamente.')
                            else:
                                logger.warning(f'⚠️ No se pudo facturar automáticamente la cotización {cotizacion.numero_cotizacion} (faltan datos del cliente o ya estaba facturada)')
                                messages.success(request, '¡Tu pago ha sido confirmado!')
                        except Exception as e:
                            logger.exception(f'Error en facturación automática para cotización {cotizacion.id}: {e}')
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
    # Verificar permisos: staff puede descargar cualquier cotizacion, usuarios solo las suyas
    es_staff = request.user.is_superuser or request.user.is_staff or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if es_staff:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    else:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, usuario=request.user)
    
    detalles = cotizacion.detalles.all().select_related('producto')
    
    # Crear el buffer
    buffer = BytesIO()
    
    # Crear el documento PDF con margenes
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                           rightMargin=50, leftMargin=50,
                           topMargin=50, bottomMargin=50)
    
    # Contenedor para los elementos del PDF
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # ===== ENCABEZADO CON LOGO Y DATOS DE EMPRESA =====
    # Intentar cargar el logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'pozinox_logo.png')
    
    if os.path.exists(logo_path):
        try:
            logo_img = Image(logo_path, width=2*inch, height=0.5*inch)
            logo_cell = logo_img
        except:
            logo_cell = Paragraph('<b><font size=18 color="#1e3a8a">POZINOX</font></b><br/>'
                                 '<font size=10 color="#f59e0b">TECNOLOGÍA E INNOVACIÓN</font>', 
                                 styles['Normal'])
    else:
        logo_cell = Paragraph('<b><font size=18 color="#1e3a8a">POZINOX</font></b><br/>'
                             '<font size=10 color="#f59e0b">TECNOLOGÍA E INNOVACIÓN</font>', 
                             styles['Normal'])
    
    # Datos de la empresa
    empresa_data = Paragraph('<b>POZINOX SpA</b><br/>'
                            'RUT: 77.123.456-7<br/>'
                            'Av. Industrial 1234, Santiago<br/>'
                            'Tel: +56 2 2345 6789<br/>'
                            'Email: ventas@pozinox.cl<br/>'
                            'www.pozinox.cl', 
                            ParagraphStyle('EmpresaInfo', parent=styles['Normal'], 
                                         fontSize=8, alignment=TA_RIGHT, leading=10))
    
    logo_data = [[logo_cell, empresa_data]]
    
    logo_table = Table(logo_data, colWidths=[3.5*inch, 3.5*inch])
    logo_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(logo_table)
    elements.append(Spacer(1, 15))
    
    # Linea separadora
    elements.append(Table([['']], colWidths=[7*inch], style=[('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#1e3a8a'))]))
    elements.append(Spacer(1, 12))
    
    # ===== TITULO COTIZACIÓN =====
    cot_title = Paragraph(f'<b>COTIZACIÓN N° {cotizacion.numero_cotizacion}</b>', 
                         ParagraphStyle('CotTitle', parent=styles['Normal'], 
                                      fontSize=16, textColor=colors.HexColor('#1e3a8a'), 
                                      alignment=TA_CENTER, fontName='Helvetica-Bold'))
    elements.append(cot_title)
    elements.append(Spacer(1, 15))
    
    # ===== DATOS DEL CLIENTE Y COTIZACIÓN =====
    cliente = cotizacion.usuario
    cliente_perfil = cliente.perfil if hasattr(cliente, 'perfil') else None
    
    fecha_emision = cotizacion.fecha_creacion.strftime('%d/%m/%Y')
    fecha_vencimiento = (cotizacion.fecha_creacion + timedelta(days=30)).strftime('%d/%m/%Y')
    
    datos_cotizacion = [
        [Paragraph('<b>Fecha Emisión:</b>', styles['Normal']), fecha_emision,
         Paragraph('<b>Fecha Vencimiento:</b>', styles['Normal']), fecha_vencimiento],
        [Paragraph('<b>Cliente:</b>', styles['Normal']), 
         cliente.get_full_name() or cliente.username,
         Paragraph('<b>RUT:</b>', styles['Normal']), 
         cliente_perfil.rut if cliente_perfil else 'N/A'],
        [Paragraph('<b>Dirección:</b>', styles['Normal']), 
         cliente_perfil.direccion if cliente_perfil else 'N/A',
         Paragraph('<b>Comuna:</b>', styles['Normal']), 
         cliente_perfil.comuna if cliente_perfil else 'N/A'],
        [Paragraph('<b>Teléfono:</b>', styles['Normal']), 
         cliente_perfil.telefono if cliente_perfil else 'N/A',
         Paragraph('<b>Email:</b>', styles['Normal']), 
         cliente.email],
    ]
    
    datos_table = Table(datos_cotizacion, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    datos_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(datos_table)
    elements.append(Spacer(1, 20))
    
    # ===== TABLA DE PRODUCTOS =====
    table_data = [['ITEM', 'DESCRIPCIÓN', 'CANTIDAD', 'PRECIO UNIT.', 'TOTAL']]
    
    item_num = 1
    for detalle in detalles:
        descripcion = f"{detalle.producto.nombre}<br/>"
        descripcion += f"Código: {detalle.producto.codigo_producto}<br/>"
        if detalle.producto.tipo_acero:
            descripcion += f"Material: {detalle.producto.get_tipo_acero_display()}"
        
        table_data.append([
            str(item_num),
            Paragraph(descripcion, ParagraphStyle('Prod', parent=styles['Normal'], fontSize=8)),
            str(detalle.cantidad),
            f'${detalle.precio_unitario:,.0f}',
            f'${detalle.subtotal:,.0f}'
        ])
        item_num += 1
    
    # Crear tabla de productos
    product_table = Table(table_data, colWidths=[0.5*inch, 3.5*inch, 0.8*inch, 1.1*inch, 1.1*inch])
    product_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Contenido
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(product_table)
    elements.append(Spacer(1, 15))
    
    # ===== TOTALES =====
    totales_data = [
        ['', '', '', 'SUBTOTAL:', f'${cotizacion.subtotal:,.0f}'],
        ['', '', '', 'IVA (19%):', f'${cotizacion.iva:,.0f}'],
        ['', '', '', 'TOTAL:', f'${cotizacion.total:,.0f}'],
    ]
    
    totales_table = Table(totales_data, colWidths=[0.5*inch, 3.5*inch, 0.8*inch, 1.1*inch, 1.1*inch])
    totales_table.setStyle(TableStyle([
        ('FONTNAME', (3, 0), (3, 1), 'Helvetica-Bold'),
        ('FONTNAME', (4, 0), (4, 1), 'Helvetica'),
        ('FONTNAME', (3, 2), (4, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (3, 0), (-1, 1), 10),
        ('FONTSIZE', (3, 2), (-1, 2), 12),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('TEXTCOLOR', (3, 2), (-1, 2), colors.HexColor('#1e3a8a')),
        ('LINEABOVE', (3, 2), (-1, 2), 2, colors.HexColor('#1e3a8a')),
        ('TOPPADDING', (3, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (3, 0), (-1, -1), 4),
    ]))
    
    elements.append(totales_table)
    elements.append(Spacer(1, 25))
    
    # ===== CONDICIONES COMERCIALES =====
    condiciones_style = ParagraphStyle('Condiciones', parent=styles['Normal'], 
                                      fontSize=8, leading=10)
    
    elements.append(Paragraph('<b>CONDICIONES COMERCIALES:</b>', condiciones_style))
    elements.append(Spacer(1, 8))
    
    condiciones = [
        f'• Forma de pago: Según condiciones acordadas',
        f'• Plazo de entrega: A coordinar según disponibilidad de stock',
        f'• Garantía: Según especificaciones del fabricante',
        f'• Precios en pesos chilenos, incluyen IVA',
    ]
    
    for condicion in condiciones:
        elements.append(Paragraph(condicion, condiciones_style))
    
    elements.append(Spacer(1, 30))
    
    # ===== PIE DE PÁGINA =====
    footer_data = [[
        Paragraph('<b>POZINOX SpA</b><br/>'
                 'Especialistas en Acero Inoxidable<br/>'
                 'www.pozinox.cl | ventas@pozinox.cl | +56 2 2345 6789<br/>'
                 'Av. Industrial 1234, Santiago - Chile',
                 ParagraphStyle('Footer', parent=styles['Normal'], 
                              fontSize=7, alignment=TA_CENTER, 
                              textColor=colors.grey))
    ]]
    
    footer_table = Table(footer_data, colWidths=[7*inch])
    footer_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(footer_table)
    
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
    # Verificar permisos: staff puede ver cualquier cotización, usuarios solo las suyas
    es_staff = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if es_staff:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    else:
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
    # Verificar permisos: staff puede ver cualquier cotización, usuarios solo las suyas
    es_staff = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if es_staff:
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    else:
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
        # Marcar como pagada (retiro en tienda con pago confirmado)
        cotizacion.metodo_pago = 'efectivo'
        cotizacion.estado = 'pagada'
        cotizacion.pago_completado = True
        cotizacion.save()
        
        # Enviar email de confirmación de compra
        try:
            enviar_confirmacion_compra(cotizacion)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f'Error al enviar confirmación de compra: {e}')
        
        messages.success(request, 'Pago en efectivo confirmado. Recibirás notificaciones sobre el estado de tu pedido.')
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


@login_required
def gestionar_estados_preparacion(request):
    """Vista para que los trabajadores gestionen los estados de preparación de cotizaciones pagadas"""
    # Verificar que el usuario sea trabajador, administrador o superusuario
    tiene_permiso = request.user.is_superuser or request.user.is_staff
    
    # También verificar el tipo de usuario en el perfil
    if not tiene_permiso and hasattr(request.user, 'perfil'):
        tipo_usuario = request.user.perfil.get_tipo_usuario_real()
        tiene_permiso = tipo_usuario in ['administrador', 'trabajador']
    
    if not tiene_permiso:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('home')
    
    # Obtener TODAS las cotizaciones pagadas o en revisión (sin importar método de pago)
    cotizaciones = Cotizacion.objects.filter(
        estado__in=['pagada', 'en_revision']
    ).select_related('usuario').prefetch_related('detalles__producto').order_by('-fecha_creacion')
    
    # Aplicar filtros si existen
    estado_filtro = request.GET.get('estado_preparacion')
    metodo_pago_filtro = request.GET.get('metodo_pago')
    
    if estado_filtro:
        cotizaciones = cotizaciones.filter(estado_preparacion=estado_filtro)
    if metodo_pago_filtro:
        cotizaciones = cotizaciones.filter(metodo_pago=metodo_pago_filtro)
    
    context = {
        'cotizaciones': cotizaciones,
        'estados_preparacion': Cotizacion.ESTADOS_PREPARACION,
        'metodos_pago': Cotizacion.METODOS_PAGO,
        'estado_filtro': estado_filtro,
        'metodo_pago_filtro': metodo_pago_filtro,
    }
    
    return render(request, 'tienda/trabajadores/gestionar_estados.html', context)


@login_required
def cambiar_estado_preparacion(request, cotizacion_id):
    """Vista para cambiar el estado de preparación de una cotización"""
    # Verificar que el usuario sea trabajador, administrador o superusuario
    tiene_permiso = request.user.is_superuser or request.user.is_staff
    
    # También verificar el tipo de usuario en el perfil
    if not tiene_permiso and hasattr(request.user, 'perfil'):
        tipo_usuario = request.user.perfil.get_tipo_usuario_real()
        tiene_permiso = tipo_usuario in ['administrador', 'trabajador']
    
    if not tiene_permiso:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('home')
    
    if request.method == 'POST':
        cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, estado__in=['pagada', 'en_revision'])
        nuevo_estado = request.POST.get('nuevo_estado')
        
        # Validar que el nuevo estado sea válido
        estados_validos = [estado[0] for estado in Cotizacion.ESTADOS_PREPARACION]
        if nuevo_estado not in estados_validos:
            messages.error(request, 'Estado de preparación inválido.')
            return redirect('gestionar_estados_preparacion')
        
        # Guardar el estado anterior para comparar
        estado_anterior = cotizacion.estado_preparacion
        
        # Actualizar el estado
        cotizacion.estado_preparacion = nuevo_estado
        cotizacion.save()
        
        # Obtener el nombre legible del estado
        nombre_estado = dict(Cotizacion.ESTADOS_PREPARACION)[nuevo_estado]
        
        # Enviar notificación por email al cliente
        try:
            enviar_notificacion_cambio_estado(cotizacion, nombre_estado)
            messages.success(request, f'Estado actualizado a "{nombre_estado}" y notificación enviada al cliente.')
        except Exception as e:
            messages.warning(request, f'Estado actualizado pero hubo un error al enviar la notificación: {str(e)}')
        
        return redirect('gestionar_estados_preparacion')
    
    return redirect('gestionar_estados_preparacion')


def enviar_notificacion_cambio_estado(cotizacion, nombre_estado):
    """Envía un email al cliente notificando el cambio de estado de su cotización"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    
    # Preparar el contexto para el email
    context = {
        'cotizacion': cotizacion,
        'nombre_estado': nombre_estado,
        'cliente_nombre': cotizacion.usuario.get_full_name() or cotizacion.usuario.username,
    }
    
    # Renderizar el template del email
    html_message = render_to_string('tienda/emails/notificacion_estado.html', context)
    plain_message = strip_tags(html_message)
    
    # Asunto del email según el estado
    asuntos = {
        'iniciada': f'Tu pedido #{cotizacion.numero_cotizacion} está en proceso',
        'embalando': f'Estamos embalando tu pedido #{cotizacion.numero_cotizacion}',
        'listo_retiro': f'¡Tu pedido #{cotizacion.numero_cotizacion} está listo para retiro!'
    }
    
    asunto = asuntos.get(cotizacion.estado_preparacion, f'Actualización de tu pedido #{cotizacion.numero_cotizacion}')
    
    # Enviar el email
    send_mail(
        subject=asunto,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cotizacion.usuario.email],
        html_message=html_message,
        fail_silently=False,
    )


def enviar_confirmacion_compra(cotizacion):
    """Envía un email de confirmación de compra cuando la cotización es pagada"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    
    # Preparar el contexto para el email
    context = {
        'cotizacion': cotizacion,
        'cliente_nombre': cotizacion.usuario.get_full_name() or cotizacion.usuario.username,
        'detalles': cotizacion.detalles.all().select_related('producto'),
    }
    
    # Renderizar el template del email
    html_message = render_to_string('tienda/emails/confirmacion_compra.html', context)
    plain_message = strip_tags(html_message)
    
    # Enviar el email
    send_mail(
        subject=f'Confirmación de Compra - Orden #{cotizacion.numero_cotizacion}',
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cotizacion.usuario.email],
        html_message=html_message,
        fail_silently=False,
    )


# ============================================
# GESTIÓN DE FACTURACIÓN
# ============================================

@login_required
def gestionar_facturacion(request):
    """Vista para que trabajadores/admins gestionen la facturación de cotizaciones pagadas"""
    # Verificar permisos
    tiene_permiso = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if not tiene_permiso:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('home')
    
    # Obtener cotizaciones pagadas
    cotizaciones = Cotizacion.objects.filter(
        estado='pagada'
    ).select_related(
        'usuario',
        'usuario__perfil',
        'facturado_por',
        'creado_por'
    ).prefetch_related('detalles__producto').order_by('-fecha_creacion')
    
    # Aplicar filtros
    tipo_documento_filtro = request.GET.get('tipo_documento')
    estado_facturacion_filtro = request.GET.get('estado_facturacion')
    tipo_cliente_filtro = request.GET.get('tipo_cliente')
    busqueda = request.GET.get('q')
    
    if tipo_documento_filtro:
        cotizaciones = cotizaciones.filter(tipo_documento=tipo_documento_filtro)
    
    if estado_facturacion_filtro == 'pendiente':
        cotizaciones = cotizaciones.filter(facturada=False)
    elif estado_facturacion_filtro == 'facturada':
        cotizaciones = cotizaciones.filter(facturada=True)
    
    if tipo_cliente_filtro:
        cotizaciones = cotizaciones.filter(usuario__perfil__tipo_cliente=tipo_cliente_filtro)
    
    if busqueda:
        cotizaciones = cotizaciones.filter(
            Q(numero_cotizacion__icontains=busqueda) |
            Q(usuario__username__icontains=busqueda) |
            Q(usuario__first_name__icontains=busqueda) |
            Q(usuario__last_name__icontains=busqueda) |
            Q(usuario__email__icontains=busqueda) |
            Q(usuario__perfil__rut__icontains=busqueda) |
            Q(numero_documento__icontains=busqueda)
        )
    
    # Paginación
    paginator = Paginator(cotizaciones, 20)
    page_number = request.GET.get('page')
    cotizaciones_paginadas = paginator.get_page(page_number)
    
    # Estadísticas
    total_pendientes = Cotizacion.objects.filter(estado='pagada', facturada=False).count()
    total_facturadas = Cotizacion.objects.filter(estado='pagada', facturada=True).count()
    total_boletas = Cotizacion.objects.filter(estado='pagada', facturada=True, tipo_documento='boleta').count()
    total_facturas = Cotizacion.objects.filter(estado='pagada', facturada=True, tipo_documento='factura').count()
    
    context = {
        'cotizaciones': cotizaciones_paginadas,
        'tipo_documento_filtro': tipo_documento_filtro,
        'estado_facturacion_filtro': estado_facturacion_filtro,
        'tipo_cliente_filtro': tipo_cliente_filtro,
        'busqueda': busqueda,
        'total_pendientes': total_pendientes,
        'total_facturadas': total_facturadas,
        'total_boletas': total_boletas,
        'total_facturas': total_facturas,
    }
    
    return render(request, 'tienda/trabajadores/gestionar_facturacion.html', context)


@login_required
def generar_documento_electronico(request, cotizacion_id):
    """Vista para generar boleta o factura electrónica"""
    # Verificar permisos
    tiene_permiso = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if not tiene_permiso:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('home')
    
    cotizacion = get_object_or_404(
        Cotizacion.objects.select_related('usuario', 'usuario__perfil'),
        id=cotizacion_id,
        estado='pagada'
    )
    
    if request.method == 'POST':
        tipo_documento = request.POST.get('tipo_documento')
        
        # Validar tipo de documento
        if tipo_documento not in ['boleta', 'factura']:
            messages.error(request, 'Tipo de documento inválido.')
            return redirect('gestionar_facturacion')
        
        # Validar que no esté ya facturada
        if cotizacion.facturada:
            messages.warning(request, f'Esta cotización ya fue facturada el {cotizacion.fecha_facturacion.strftime("%d/%m/%Y %H:%M")} por {cotizacion.facturado_por.get_full_name()}')
            return redirect('gestionar_facturacion')
        
        # Validar datos del cliente para facturación
        perfil = cotizacion.usuario.perfil
        errores = []
        
        if not perfil.rut:
            errores.append('El cliente no tiene RUT registrado.')
        
        if tipo_documento == 'factura':
            # Para factura se requieren más datos
            if perfil.tipo_cliente == 'empresa':
                if not perfil.razon_social:
                    errores.append('La empresa no tiene razón social registrada.')
                if not perfil.giro:
                    errores.append('La empresa no tiene giro comercial registrado.')
                if not perfil.direccion_comercial:
                    errores.append('La empresa no tiene dirección comercial registrada.')
            else:
                if not perfil.direccion:
                    errores.append('El cliente no tiene dirección registrada.')
        
        if errores:
            for error in errores:
                messages.error(request, error)
            messages.warning(request, 'Completa los datos del cliente antes de facturar.')
            return redirect('gestionar_facturacion')
        
        try:
            # Actualizar información de facturación
            cotizacion.tipo_documento = tipo_documento
            cotizacion.facturada = True
            cotizacion.fecha_facturacion = timezone.now()
            cotizacion.facturado_por = request.user
            
            # TODO: Aquí se integrará con la API del SII
            # Por ahora generamos un número de folio temporal
            # En producción, este folio vendrá del SII
            import random
            cotizacion.numero_documento = f"{tipo_documento.upper()[0]}{timezone.now().year}{random.randint(10000, 99999)}"
            cotizacion.folio_sii = cotizacion.numero_documento
            cotizacion.estado_sii = 'PENDIENTE_ENVIO'
            
            # Descontar stock de productos
            detalles = cotizacion.detalles.all().select_related('producto')
            productos_sin_stock = []
            
            for detalle in detalles:
                producto = detalle.producto
                if producto.stock_actual >= detalle.cantidad:
                    producto.stock_actual -= detalle.cantidad
                    producto.save()
                else:
                    productos_sin_stock.append(f'{producto.nombre} (disponible: {producto.stock_actual}, necesario: {detalle.cantidad})')
            
            if productos_sin_stock:
                messages.warning(
                    request, 
                    f'⚠️ Algunos productos no tenían stock suficiente: {", ".join(productos_sin_stock)}'
                )
            
            # Generar PDF y guardarlo en la base de datos
            from django.core.files.base import ContentFile
            pdf_content = generar_pdf_documento_tributario(cotizacion)
            tipo_doc_filename = 'boleta' if tipo_documento == 'boleta' else 'factura'
            filename = f'{tipo_doc_filename}_{cotizacion.numero_documento}.pdf'
            
            # Guardar el PDF en el campo pdf_documento
            cotizacion.pdf_documento.save(filename, ContentFile(pdf_content), save=False)
            
            cotizacion.save()
            
            tipo_doc_texto = 'Boleta Electrónica' if tipo_documento == 'boleta' else 'Factura Electrónica'
            messages.success(
                request, 
                f'✅ {tipo_doc_texto} N° {cotizacion.numero_documento} generada exitosamente para la cotización #{cotizacion.numero_cotizacion}'
            )
            
            # Enviar notificación al cliente
            try:
                enviar_notificacion_facturacion(cotizacion, tipo_documento)
                messages.info(request, f'📧 Notificación enviada al cliente: {cotizacion.usuario.email}')
            except Exception as e:
                logger.exception(f'Error al enviar notificación de facturación: {e}')
                messages.warning(request, 'Documento generado pero hubo un error al enviar la notificación al cliente.')
            
            # Redirigir a la descarga del documento tributario
            return redirect('descargar_documento_tributario', cotizacion_id=cotizacion.id)
            
        except Exception as e:
            logger.exception(f'Error al generar documento electrónico: {e}')
            messages.error(request, f'❌ Error al generar el documento: {str(e)}')
            return redirect('gestionar_facturacion')
    
    # GET - Mostrar formulario de confirmación
    # Validar datos del cliente
    perfil = cotizacion.usuario.perfil
    datos_completos = bool(perfil.rut)
    
    warnings = []
    if not perfil.rut:
        warnings.append('⚠️ Falta RUT del cliente')
    if perfil.tipo_cliente == 'empresa' and not perfil.razon_social:
        warnings.append('⚠️ Falta razón social de la empresa')
    if perfil.tipo_cliente == 'empresa' and not perfil.giro:
        warnings.append('⚠️ Falta giro comercial')
    if not (perfil.direccion or perfil.direccion_comercial):
        warnings.append('⚠️ Falta dirección del cliente')
    
    context = {
        'cotizacion': cotizacion,
        'perfil': perfil,
        'datos_completos': datos_completos and len(warnings) == 0,
        'warnings': warnings,
    }
    return render(request, 'tienda/trabajadores/confirmar_facturacion.html', context)


def facturar_cotizacion_automaticamente(cotizacion, usuario_que_factura=None):
    """
    Factura automáticamente una cotización para pagos con MercadoPago
    Determina automáticamente si es boleta (persona natural) o factura (empresa)
    Aplica tanto para pagos desde n8n como desde la página web
    """
    from django.core.files.base import ContentFile
    import random
    
    # Verificar que la cotización esté pagada
    if cotizacion.estado != 'pagada':
        logger.warning(f'No se puede facturar cotización {cotizacion.id} porque no está pagada')
        return False
    
    # Verificar que no esté ya facturada
    if cotizacion.facturada:
        logger.info(f'Cotización {cotizacion.id} ya está facturada')
        return True
    
    # Verificar que sea pago con MercadoPago
    if cotizacion.metodo_pago != 'mercadopago':
        logger.warning(f'Facturación automática solo aplica para MercadoPago. Método: {cotizacion.metodo_pago}')
        return False
    
    # Obtener o crear perfil del cliente
    try:
        perfil = cotizacion.usuario.perfil
    except AttributeError:
        # Si no tiene perfil, crearlo
        from apps.usuarios.models import PerfilUsuario
        logger.warning(f'Usuario {cotizacion.usuario.id} no tiene perfil, creando uno nuevo')
        perfil = PerfilUsuario.objects.create(user=cotizacion.usuario)
        logger.info(f'✅ Perfil creado para usuario {cotizacion.usuario.id}')
    
    # Determinar tipo de documento automáticamente
    # Persona natural → Boleta
    # Empresa → Factura
    if perfil.tipo_cliente == 'persona':
        tipo_documento = 'boleta'
    elif perfil.tipo_cliente == 'empresa':
        tipo_documento = 'factura'
    else:
        # Por defecto, persona natural (boleta)
        tipo_documento = 'boleta'
        logger.warning(f'Perfil {perfil.id} no tiene tipo_cliente definido, usando boleta por defecto')
    
    # Validar datos del cliente para facturación
    errores = []
    
    # Verificar RUT - si está vacío o solo tiene espacios, considerarlo como no válido
    rut_valido = perfil.rut and perfil.rut.strip()
    if not rut_valido:
        logger.warning(f'⚠️ Usuario {cotizacion.usuario.id} ({cotizacion.usuario.email}) no tiene RUT registrado. Perfil ID: {perfil.id}, RUT actual: "{perfil.rut}"')
        errores.append('El cliente no tiene RUT registrado.')
    else:
        logger.info(f'✅ Usuario {cotizacion.usuario.id} tiene RUT: {perfil.rut}')
    
    if tipo_documento == 'factura':
        # Para factura se requieren más datos
        if perfil.tipo_cliente == 'empresa':
            if not perfil.razon_social:
                errores.append('La empresa no tiene razón social registrada.')
            if not perfil.giro:
                errores.append('La empresa no tiene giro comercial registrado.')
            if not perfil.direccion_comercial:
                errores.append('La empresa no tiene dirección comercial registrada.')
        else:
            if not perfil.direccion:
                errores.append('El cliente no tiene dirección registrada.')
    
    # Si hay errores de validación, no facturar pero no fallar
    if errores:
        logger.warning(f'No se puede facturar cotización {cotizacion.id} automáticamente: {", ".join(errores)}')
        return False
    
    try:
        # Actualizar información de facturación
        cotizacion.tipo_documento = tipo_documento
        cotizacion.facturada = True
        cotizacion.fecha_facturacion = timezone.now()
        cotizacion.facturado_por = usuario_que_factura  # Puede ser None para facturación automática
        
        # Generar número de folio temporal
        # TODO: En producción, integrar con API del SII
        cotizacion.numero_documento = f"{tipo_documento.upper()[0]}{timezone.now().year}{random.randint(10000, 99999)}"
        cotizacion.folio_sii = cotizacion.numero_documento
        cotizacion.estado_sii = 'PENDIENTE_ENVIO'
        
        # Descontar stock de productos
        detalles = cotizacion.detalles.all().select_related('producto')
        productos_sin_stock = []
        
        for detalle in detalles:
            producto = detalle.producto
            if producto.stock_actual >= detalle.cantidad:
                producto.stock_actual -= detalle.cantidad
                producto.save()
            else:
                productos_sin_stock.append(f'{producto.nombre} (disponible: {producto.stock_actual}, necesario: {detalle.cantidad})')
        
        if productos_sin_stock:
            logger.warning(f'Cotización {cotizacion.id}: Algunos productos no tenían stock suficiente: {", ".join(productos_sin_stock)}')
        
        # Generar PDF y guardarlo en la base de datos
        pdf_content = generar_pdf_documento_tributario(cotizacion)
        tipo_doc_filename = 'boleta' if tipo_documento == 'boleta' else 'factura'
        filename = f'{tipo_doc_filename}_{cotizacion.numero_documento}.pdf'
        
        # Guardar el PDF en el campo pdf_documento
        cotizacion.pdf_documento.save(filename, ContentFile(pdf_content), save=False)
        
        cotizacion.save()
        
        tipo_doc_texto = 'Boleta Electrónica' if tipo_documento == 'boleta' else 'Factura Electrónica'
        logger.info(f'✅ {tipo_doc_texto} N° {cotizacion.numero_documento} generada automáticamente para cotización {cotizacion.numero_cotizacion}')
        
        # Enviar notificación al cliente
        try:
            enviar_notificacion_facturacion(cotizacion, tipo_documento)
            logger.info(f'📧 Notificación de facturación enviada al cliente: {cotizacion.usuario.email}')
        except Exception as e:
            logger.exception(f'Error al enviar notificación de facturación: {e}')
        
        return True
        
    except Exception as e:
        logger.exception(f'Error al facturar cotización {cotizacion.id} automáticamente: {e}')
        return False


def generar_pdf_documento_tributario(cotizacion):
    """Generar PDF del documento tributario (Boleta o Factura) - Función reutilizable"""
    detalles = cotizacion.detalles.all().select_related('producto')
    cliente = cotizacion.usuario
    
    # Obtener perfil del cliente para datos adicionales
    perfil = getattr(cliente, 'perfil', None)
    
    # Crear el buffer
    buffer = BytesIO()
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50,
                           topMargin=50, bottomMargin=30)
    
    # Contenedor para los elementos del PDF
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo para el título del documento
    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#dc2626'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para encabezados
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    # Estilo normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=6,
    )
    
    # Estilo pequeño
    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
    )
    
    # ===== ENCABEZADO DEL DOCUMENTO =====
    
    # Logo y datos de la empresa (izquierda) + Tipo de documento (derecha)
    tipo_doc_texto = 'BOLETA ELECTRÓNICA' if cotizacion.tipo_documento == 'boleta' else 'FACTURA ELECTRÓNICA'
    
    header_data = [
        [
            Paragraph('<b>POZINOX</b><br/>Especialistas en Aceros Inoxidables<br/><br/>RUT: 76.XXX.XXX-X<br/>Dirección de la Empresa<br/>Teléfono: +56 9 XXXX XXXX<br/>info@pozinox.cl', normal_style),
            Paragraph(f'<b>R.U.T: 76.XXX.XXX-X</b><br/><br/><font size=18><b>{tipo_doc_texto}</b></font><br/><br/><b>N° {cotizacion.numero_documento or "SIN FOLIO"}</b><br/><br/>SII - {cotizacion.estado_sii or "PENDIENTE"}', subtitle_style)
        ]
    ]
    
    header_table = Table(header_data, colWidths=[3.5*inch, 3*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (1, 0), (1, 0), 2, colors.HexColor('#dc2626')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#fef2f2')),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 20))
    
    # ===== DATOS DEL CLIENTE =====
    elements.append(Paragraph('DATOS DEL CLIENTE', heading_style))
    
    # Preparar datos del cliente según tipo
    cliente_info = []
    
    if cotizacion.tipo_documento == 'factura':
        # Para factura: mostrar datos de empresa
        cliente_info = [
            ['Razón Social:', getattr(perfil, 'razon_social', 'N/A') if perfil else 'N/A'],
            ['RUT:', getattr(perfil, 'rut', 'N/A') if perfil else 'N/A'],
            ['Giro:', getattr(perfil, 'giro', 'N/A') if perfil else 'N/A'],
            ['Dirección:', getattr(perfil, 'direccion_comercial', 'N/A') if perfil else 'N/A'],
        ]
    else:
        # Para boleta: mostrar datos personales
        nombre_completo = cliente.get_full_name() or cliente.username
        cliente_info = [
            ['Nombre:', nombre_completo],
            ['RUT:', getattr(perfil, 'rut', 'N/A') if perfil else 'N/A'],
            ['Email:', cliente.email],
            ['Dirección:', getattr(perfil, 'direccion', 'N/A') if perfil else 'N/A'],
        ]
    
    cliente_info.append(['Fecha Emisión:', cotizacion.fecha_facturacion.strftime('%d/%m/%Y %H:%M') if cotizacion.fecha_facturacion else 'N/A'])
    
    cliente_table = Table(cliente_info, colWidths=[1.5*inch, 5*inch])
    cliente_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e3a8a')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(cliente_table)
    elements.append(Spacer(1, 20))
    
    # ===== DETALLE DE PRODUCTOS =====
    elements.append(Paragraph('DETALLE DE PRODUCTOS Y SERVICIOS', heading_style))
    
    # Encabezados de tabla
    table_data = [['Item', 'Descripción', 'Código', 'Cant.', 'Precio Unit.', 'Subtotal']]
    
    # Datos de productos
    for idx, detalle in enumerate(detalles, 1):
        table_data.append([
            str(idx),
            Paragraph(detalle.producto.nombre, normal_style),
            detalle.producto.codigo_producto,
            str(detalle.cantidad),
            f'${detalle.precio_unitario:,.0f}',
            f'${detalle.subtotal:,.0f}'
        ])
    
    # Crear tabla
    product_table = Table(table_data, colWidths=[0.4*inch, 2.3*inch, 1*inch, 0.6*inch, 1*inch, 1.2*inch])
    product_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        
        # Contenido
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    elements.append(product_table)
    elements.append(Spacer(1, 15))
    
    # ===== TOTALES =====
    totales_data = [
        ['', '', 'Subtotal Neto:', f'${cotizacion.subtotal:,.0f}'],
        ['', '', 'IVA (19%):', f'${cotizacion.iva:,.0f}'],
        ['', '', '', ''],
        ['', '', 'TOTAL A PAGAR:', f'${cotizacion.total:,.0f}'],
    ]
    
    totales_table = Table(totales_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    totales_table.setStyle(TableStyle([
        ('FONTNAME', (2, 0), (2, 1), 'Helvetica-Bold'),
        ('FONTNAME', (3, 0), (3, 1), 'Helvetica'),
        ('FONTNAME', (2, 3), (3, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (2, 0), (-1, 1), 10),
        ('FONTSIZE', (2, 3), (-1, 3), 14),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('TEXTCOLOR', (2, 3), (3, 3), colors.HexColor('#dc2626')),
        ('BACKGROUND', (2, 3), (3, 3), colors.HexColor('#fef2f2')),
        ('BOX', (2, 3), (3, 3), 2, colors.HexColor('#dc2626')),
        ('TOPPADDING', (2, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (2, 0), (-1, -1), 4),
        ('PADDING', (2, 3), (3, 3), 8),
    ]))
    
    elements.append(totales_table)
    elements.append(Spacer(1, 20))
    
    # ===== INFORMACIÓN ADICIONAL =====
    if cotizacion.folio_sii:
        elements.append(Paragraph(f'<b>Folio SII:</b> {cotizacion.folio_sii}', small_style))
    
    if cotizacion.track_id_sii:
        elements.append(Paragraph(f'<b>Track ID SII:</b> {cotizacion.track_id_sii}', small_style))
    
    elements.append(Spacer(1, 15))
    
    # ===== PIE DE PÁGINA =====
    footer_text = f"""
    <para align=center>
    <b>DOCUMENTO TRIBUTARIO ELECTRÓNICO</b><br/>
    Timbre Electrónico SII<br/>
    Resolución: EX. N° XXXX de YYYY<br/>
    Verifique documento en www.sii.cl<br/><br/>
    <font size=7>
    Este documento tributario electrónico ha sido generado conforme a las disposiciones<br/>
    del Servicio de Impuestos Internos de Chile. Para verificar su autenticidad,<br/>
    ingrese a www.sii.cl con el código de verificación.<br/><br/>
    Documento generado por: {cotizacion.facturado_por.get_full_name() if cotizacion.facturado_por else 'Sistema'}<br/>
    Fecha de generación: {cotizacion.fecha_facturacion.strftime('%d/%m/%Y %H:%M') if cotizacion.fecha_facturacion else 'N/A'}
    </font>
    </para>
    """
    
    elements.append(Paragraph(footer_text, small_style))
    
    # ===== CONSTRUIR PDF =====
    doc.build(elements)
    
    # Obtener el valor del buffer y retornarlo
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf

@login_required
def descargar_documento_tributario(request, cotizacion_id):
    """Descargar PDF del documento tributario (Boleta o Factura)"""
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, facturada=True)
    
    # Verificar permisos: staff puede descargar cualquier documento, usuarios solo los suyos
    es_staff = request.user.is_superuser or request.user.is_staff or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if not es_staff and cotizacion.usuario != request.user:
        messages.error(request, 'No tienes permisos para descargar este documento.')
        return redirect('home')
    
    if not cotizacion.tipo_documento:
        messages.error(request, 'Esta cotización no tiene un documento tributario asociado.')
        if es_staff:
            return redirect('gestionar_facturacion')
        return redirect('mis_cotizaciones')
    
    # Si el PDF ya está guardado en la BD, descargarlo directamente
    if cotizacion.pdf_documento:
        from django.http import FileResponse
        return FileResponse(
            cotizacion.pdf_documento.open('rb'),
            as_attachment=True,
            filename=f'{cotizacion.tipo_documento}_{cotizacion.numero_documento}.pdf'
        )
    
    # Si no existe el PDF guardado, generarlo on-the-fly
    pdf = generar_pdf_documento_tributario(cotizacion)
    
    # Crear respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    tipo_doc_filename = 'boleta' if cotizacion.tipo_documento == 'boleta' else 'factura'
    response['Content-Disposition'] = f'attachment; filename="{tipo_doc_filename}_{cotizacion.numero_documento or cotizacion.numero_cotizacion}.pdf"'
    response.write(pdf)
    
    return response


def enviar_notificacion_facturacion(cotizacion, tipo_documento):
    """Enviar email al cliente notificando la generación del documento con PDF adjunto"""
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    
    tipo_doc_texto = 'Boleta Electrónica' if tipo_documento == 'boleta' else 'Factura Electrónica'
    
    context = {
        'cotizacion': cotizacion,
        'cliente_nombre': cotizacion.usuario.get_full_name() or cotizacion.usuario.username,
        'tipo_documento': tipo_doc_texto,
        'numero_documento': cotizacion.numero_documento,
        'fecha_emision': cotizacion.fecha_facturacion.strftime('%d de %B de %Y'),
    }
    
    html_message = render_to_string('tienda/emails/notificacion_facturacion.html', context)
    plain_message = strip_tags(html_message)
    
    # Crear email con EmailMultiAlternatives para poder adjuntar archivos
    email = EmailMultiAlternatives(
        subject=f'📄 {tipo_doc_texto} N° {cotizacion.numero_documento} - Pozinox',
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[cotizacion.usuario.email],
    )
    
    # Adjuntar HTML
    email.attach_alternative(html_message, "text/html")
    
    # Generar y adjuntar PDF del documento tributario
    try:
        pdf_content = generar_pdf_documento_tributario(cotizacion)
        tipo_doc_filename = 'boleta' if cotizacion.tipo_documento == 'boleta' else 'factura'
        filename = f'{tipo_doc_filename}_{cotizacion.numero_documento or cotizacion.numero_cotizacion}.pdf'
        
        email.attach(filename, pdf_content, 'application/pdf')
    except Exception as e:
        logger.exception(f'Error al adjuntar PDF al email: {e}')
        # Continuar enviando el email sin adjunto si hay error
    
    # Enviar email
    email.send(fail_silently=False)


# ==========================================
# RECEPCIONES DE COMPRAS
# ==========================================

@login_required
def gestionar_recepciones(request):
    """Vista para gestionar recepciones de compras - Solo administradores"""
    # Verificar que sea administrador o superusuario
    es_admin = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario == 'administrador'
    )
    
    if not es_admin:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('home')
    
    # Obtener todas las recepciones
    recepciones = RecepcionCompra.objects.all().select_related('creado_por', 'confirmado_por').order_by('-fecha_creacion')
    
    # Filtros
    estado_filtro = request.GET.get('estado')
    busqueda = request.GET.get('busqueda')
    
    if estado_filtro:
        recepciones = recepciones.filter(estado=estado_filtro)
    
    if busqueda:
        recepciones = recepciones.filter(
            Q(numero_recepcion__icontains=busqueda) |
            Q(proveedor__icontains=busqueda) |
            Q(numero_factura__icontains=busqueda)
        )
    
    # Estadísticas
    total_recepciones = RecepcionCompra.objects.count()
    recepciones_confirmadas = RecepcionCompra.objects.filter(estado='confirmada').count()
    recepciones_borrador = RecepcionCompra.objects.filter(estado='borrador').count()
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(recepciones, 15)
    page = request.GET.get('page')
    recepciones_paginadas = paginator.get_page(page)
    
    context = {
        'recepciones': recepciones_paginadas,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        'total_recepciones': total_recepciones,
        'recepciones_confirmadas': recepciones_confirmadas,
        'recepciones_borrador': recepciones_borrador,
    }
    
    return render(request, 'tienda/admin/gestionar_recepciones.html', context)


@login_required
def crear_recepcion(request):
    """Crear nueva recepción de compra"""
    es_admin = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario == 'administrador'
    )
    
    if not es_admin:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('home')
    
    if request.method == 'POST':
        proveedor = request.POST.get('proveedor')
        numero_factura = request.POST.get('numero_factura', '')
        fecha_factura = request.POST.get('fecha_factura', None)
        observaciones = request.POST.get('observaciones', '')
        
        if not proveedor:
            messages.error(request, 'El nombre del proveedor es obligatorio.')
            return redirect('crear_recepcion')
        
        # Crear recepción
        recepcion = RecepcionCompra.objects.create(
            proveedor=proveedor,
            numero_factura=numero_factura,
            fecha_factura=fecha_factura if fecha_factura else None,
            observaciones=observaciones,
            creado_por=request.user,
            estado='borrador'
        )
        
        messages.success(request, f'✅ Recepción {recepcion.numero_recepcion} creada exitosamente.')
        return redirect('editar_recepcion', recepcion_id=recepcion.id)
    
    return render(request, 'tienda/admin/crear_recepcion.html')


@login_required
def editar_recepcion(request, recepcion_id):
    """Editar recepción y agregar productos"""
    es_admin = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario == 'administrador'
    )
    
    if not es_admin:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('home')
    
    recepcion = get_object_or_404(RecepcionCompra, id=recepcion_id)
    
    if recepcion.estado == 'confirmada':
        messages.warning(request, 'Esta recepción ya está confirmada y no puede modificarse.')
        return redirect('detalle_recepcion', recepcion_id=recepcion.id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'actualizar_datos':
            recepcion.proveedor = request.POST.get('proveedor')
            recepcion.numero_factura = request.POST.get('numero_factura', '')
            fecha_factura = request.POST.get('fecha_factura')
            recepcion.fecha_factura = fecha_factura if fecha_factura else None
            recepcion.observaciones = request.POST.get('observaciones', '')
            recepcion.save()
            messages.success(request, 'Datos de la recepción actualizados.')
        
        elif action == 'agregar_producto':
            producto_id = request.POST.get('producto_id')
            cantidad = request.POST.get('cantidad')
            precio_compra = request.POST.get('precio_compra', None)
            lote = request.POST.get('lote', '')
            observaciones_detalle = request.POST.get('observaciones_detalle', '')
            
            if producto_id and cantidad:
                producto = get_object_or_404(Producto, id=producto_id)
                DetalleRecepcionCompra.objects.create(
                    recepcion=recepcion,
                    producto=producto,
                    cantidad=int(cantidad),
                    precio_compra=precio_compra if precio_compra else None,
                    lote=lote,
                    observaciones=observaciones_detalle
                )
                messages.success(request, f'✅ Producto {producto.nombre} agregado.')
            else:
                messages.error(request, 'Debe seleccionar un producto y especificar la cantidad.')
        
        return redirect('editar_recepcion', recepcion_id=recepcion.id)
    
    # GET - Mostrar formulario
    productos = Producto.objects.filter(activo=True).order_by('nombre')
    detalles = recepcion.detalles.all().select_related('producto')
    
    context = {
        'recepcion': recepcion,
        'productos': productos,
        'detalles': detalles,
    }
    
    return render(request, 'tienda/admin/editar_recepcion.html', context)


@login_required
def eliminar_detalle_recepcion(request, detalle_id):
    """Eliminar un producto de la recepción"""
    es_admin = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario == 'administrador'
    )
    
    if not es_admin:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('home')
    
    detalle = get_object_or_404(DetalleRecepcionCompra, id=detalle_id)
    recepcion = detalle.recepcion
    
    if recepcion.estado == 'confirmada':
        messages.error(request, 'No se puede eliminar productos de una recepción confirmada.')
        return redirect('editar_recepcion', recepcion_id=recepcion.id)
    
    producto_nombre = detalle.producto.nombre
    detalle.delete()
    messages.success(request, f'Producto {producto_nombre} eliminado de la recepción.')
    
    return redirect('editar_recepcion', recepcion_id=recepcion.id)


@login_required
def confirmar_recepcion(request, recepcion_id):
    """Confirmar recepción y actualizar stock"""
    es_admin = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario == 'administrador'
    )
    
    if not es_admin:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('home')
    
    recepcion = get_object_or_404(RecepcionCompra, id=recepcion_id)
    
    if recepcion.estado == 'confirmada':
        messages.warning(request, 'Esta recepción ya está confirmada.')
        return redirect('detalle_recepcion', recepcion_id=recepcion.id)
    
    if recepcion.detalles.count() == 0:
        messages.error(request, 'No se puede confirmar una recepción sin productos.')
        return redirect('editar_recepcion', recepcion_id=recepcion.id)
    
    if request.method == 'POST':
        if recepcion.confirmar(request.user):
            messages.success(request, f'✅ Recepción {recepcion.numero_recepcion} confirmada. Stock actualizado.')
        else:
            messages.error(request, 'Error al confirmar la recepción.')
        
        return redirect('detalle_recepcion', recepcion_id=recepcion.id)
    
    # GET - Mostrar confirmación
    detalles = recepcion.detalles.all().select_related('producto')
    context = {
        'recepcion': recepcion,
        'detalles': detalles,
    }
    return render(request, 'tienda/admin/confirmar_recepcion.html', context)


@login_required
def detalle_recepcion(request, recepcion_id):
    """Ver detalle de una recepción"""
    es_admin = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario == 'administrador'
    )
    
    if not es_admin:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('home')
    
    recepcion = get_object_or_404(RecepcionCompra, id=recepcion_id)
    detalles = recepcion.detalles.all().select_related('producto')
    
    context = {
        'recepcion': recepcion,
        'detalles': detalles,
    }
    
    return render(request, 'tienda/admin/detalle_recepcion.html', context)


# ============================================
# VENTAS N8N - BOT DE VENTAS
# ============================================

def crear_cotizacion_desde_venta_n8n(venta):
    """
    Crea una nueva cotización pagada desde una venta de n8n
    """
    from django.contrib.auth.models import User
    from decimal import Decimal
    
    # Verificar si ya existe una cotización para esta venta (evitar duplicados)
    if venta.metadata and venta.metadata.get('cotizacion_id'):
        try:
            return Cotizacion.objects.get(id=venta.metadata['cotizacion_id'])
        except Cotizacion.DoesNotExist:
            pass
    
    # Obtener o crear usuario por email
    usuario = None
    if venta.usuario:
        usuario = venta.usuario
    elif venta.email_comprador:
        try:
            usuario = User.objects.get(email=venta.email_comprador)
            venta.usuario = usuario
            venta.save()
        except User.DoesNotExist:
            # Si no existe el usuario, crear uno básico
            username = venta.email_comprador.split('@')[0]
            # Asegurar que el username sea único
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
            
            usuario = User.objects.create_user(
                username=username,
                email=venta.email_comprador,
                first_name=venta.email_comprador.split('@')[0],
            )
            # Asegurar que el perfil existe (debería crearse automáticamente por la señal, pero verificamos)
            try:
                perfil = usuario.perfil
            except AttributeError:
                from apps.usuarios.models import PerfilUsuario
                perfil = PerfilUsuario.objects.create(user=usuario)
                logger.info(f'✅ Perfil creado para nuevo usuario {usuario.id} desde venta n8n')
            
            venta.usuario = usuario
            venta.save()
    
    if not usuario:
        logger.error(f'No se pudo crear usuario para venta n8n {venta.id}')
        return None
    
    # IMPORTANTE: Para ventas de n8n, el total de MercadoPago ya incluye IVA
    # Por lo tanto, debemos calcular el subtotal sin IVA desde el total que ya incluye IVA
    # Ejemplo: Si total = $1190 (incluye IVA), subtotal = $1190 / 1.19 = $1000
    # Luego IVA = $1000 * 0.19 = $190
    total_con_iva = venta.total
    subtotal_sin_iva = (total_con_iva / Decimal('1.19')).quantize(Decimal('0.01'))
    iva_calculado = (subtotal_sin_iva * Decimal('0.19')).quantize(Decimal('0.01'))
    
    # Crear la cotización con los totales correctos (solo para ventas n8n)
    cotizacion = Cotizacion.objects.create(
        usuario=usuario,
        estado='pagada',
        metodo_pago='mercadopago',
        pago_completado=True,
        mercadopago_preference_id=venta.mercadopago_preference_id,
        mercadopago_payment_id=venta.mercadopago_payment_id or '',
        subtotal=subtotal_sin_iva,  # Subtotal sin IVA
        iva=iva_calculado,  # IVA calculado correctamente
        total=total_con_iva,  # Total original de MercadoPago (ya incluye IVA)
        fecha_finalizacion=timezone.now(),
    )
    
    # Crear detalles de cotización basándose en los items
    for item in venta.items:
        producto_id = item.get('id') or (venta.metadata.get('product_id') if venta.metadata else None)
        sku = item.get('sku') or (venta.metadata.get('sku') if venta.metadata else None)
        
        producto = None
        
        # Intentar buscar el producto por ID o SKU
        if producto_id:
            try:
                producto = Producto.objects.get(id=producto_id, activo=True)
            except Producto.DoesNotExist:
                pass
        
        if not producto and sku:
            try:
                producto = Producto.objects.get(codigo_producto=sku, activo=True)
            except Producto.DoesNotExist:
                pass
        
        # Si no encontramos el producto, crear uno genérico
        if not producto:
            categoria_default = CategoriaAcero.objects.first()
            if not categoria_default:
                logger.warning(f'No se encontró categoría para crear producto de item: {item.get("title")}')
                continue
            
            codigo_producto = sku or f"N8N-{venta.id}-{len(cotizacion.detalles.all())}"
            producto, created = Producto.objects.get_or_create(
                codigo_producto=codigo_producto,
                defaults={
                    'nombre': item.get('title', 'Producto sin nombre')[:200],
                    'descripcion': item.get('description', '')[:500],
                    'categoria': categoria_default,
                    'tipo_acero': '304',
                    'precio_por_unidad': Decimal(str(item.get('unit_price', 0))),
                    'stock_actual': 0,
                    'activo': True,
                }
            )
        
        # Crear detalle de cotización
        # IMPORTANTE: Para ventas n8n, el precio unitario de MercadoPago ya incluye IVA
        # Calcular precio sin IVA: precio_con_iva / 1.19
        cantidad = item.get('quantity', 1)
        precio_unitario_con_iva = Decimal(str(item.get('unit_price', 0)))
        precio_unitario_sin_iva = (precio_unitario_con_iva / Decimal('1.19')).quantize(Decimal('0.01'))
        
        DetalleCotizacion.objects.create(
            cotizacion=cotizacion,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio_unitario_sin_iva,  # Precio sin IVA (solo para n8n)
        )
    
    # NO recalcular totales con calcular_totales() porque ya están calculados correctamente
    # calcular_totales() agregaría otro IVA encima, duplicando el IVA
    # Los totales ya están establecidos correctamente arriba
    
    # Asociar la cotización con la venta
    if not venta.metadata:
        venta.metadata = {}
    venta.metadata['cotizacion_id'] = cotizacion.id
    venta.save()
    
    # Enviar email de confirmación
    try:
        enviar_confirmacion_compra(cotizacion)
    except Exception as e:
        logger.exception(f'Error al enviar confirmación de compra para cotización {cotizacion.id}: {e}')
    
    # IMPORTANTE: Facturación automática solo para pagos con MercadoPago desde n8n
    # Para Transferencia/Efectivo se hace manualmente desde el panel de trabajadores
    if cotizacion.metodo_pago == 'mercadopago':
        try:
            # Facturar automáticamente: boleta para persona natural, factura para empresa
            facturado = facturar_cotizacion_automaticamente(cotizacion, usuario_que_factura=None)
            if facturado:
                logger.info(f'✅ Facturación automática exitosa para cotización {cotizacion.numero_cotizacion}')
            else:
                logger.warning(f'⚠️ No se pudo facturar automáticamente la cotización {cotizacion.numero_cotizacion} (faltan datos del cliente o ya estaba facturada)')
        except Exception as e:
            logger.exception(f'Error en facturación automática para cotización {cotizacion.id}: {e}')
            # Continuar de todas formas, la cotización se creó correctamente
    
    logger.info(f'Cotización {cotizacion.numero_cotizacion} creada desde venta n8n {venta.id}')
    
    return cotizacion


@require_POST
def api_crear_venta_n8n(request):
    """API endpoint para que n8n registre una venta cuando crea una preferencia de MercadoPago"""
    try:
        data = json.loads(request.body)
        
        # Validar datos requeridos
        preference_id = data.get('preference_id')
        email_comprador = data.get('email_comprador') or data.get('payer', {}).get('email')
        items = data.get('items', [])
        metadata = data.get('metadata', {})
        
        if not preference_id:
            return JsonResponse({'error': 'preference_id es requerido'}, status=400)
        if not email_comprador:
            return JsonResponse({'error': 'email_comprador es requerido'}, status=400)
        if not items:
            return JsonResponse({'error': 'items es requerido'}, status=400)
        
        # Calcular totales
        subtotal = sum(item.get('unit_price', 0) * item.get('quantity', 0) for item in items)
        total = subtotal  # Puedes agregar IVA si es necesario
        
        # Crear o actualizar venta
        venta, created = VentaN8n.objects.update_or_create(
            mercadopago_preference_id=preference_id,
            defaults={
                'email_comprador': email_comprador,
                'items': items,
                'metadata': metadata,
                'subtotal': subtotal,
                'total': total,
            }
        )
        
        # Intentar asociar usuario por email
        venta.asociar_usuario_por_email()
        
        return JsonResponse({
            'success': True,
            'venta_id': venta.id,
            'preference_id': venta.mercadopago_preference_id,
            'created': created
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        logger.exception(f'Error al crear venta n8n: {e}')
        return JsonResponse({'error': str(e)}, status=500)


def pago_exitoso_n8n(request):
    """Página de pago exitoso para ventas de n8n"""
    payment_id = request.GET.get('payment_id') or request.GET.get('collection_id')
    preference_id = request.GET.get('preference_id')
    collection_status = request.GET.get('collection_status') or request.GET.get('status', 'approved')
    status = collection_status
    
    logger.info(f'🔵 pago_exitoso_n8n llamado - payment_id: {payment_id}, preference_id: {preference_id}, status: {status}')
    
    if not preference_id and not payment_id:
        logger.warning('❌ No se encontró preference_id ni payment_id en la URL')
        messages.error(request, 'No se encontró información de pago.')
        return redirect('home')
    
    # Buscar la venta
    venta = None
    if preference_id:
        try:
            venta = VentaN8n.objects.get(mercadopago_preference_id=preference_id)
            logger.info(f'✅ Venta encontrada por preference_id: {venta.id}, estado: {venta.estado_pago}')
        except VentaN8n.DoesNotExist:
            logger.warning(f'⚠️ No se encontró venta con preference_id: {preference_id}')
            pass
    
    if not venta and payment_id:
        try:
            venta = VentaN8n.objects.get(mercadopago_payment_id=payment_id)
            logger.info(f'✅ Venta encontrada por payment_id: {venta.id}, estado: {venta.estado_pago}')
        except VentaN8n.DoesNotExist:
            logger.warning(f'⚠️ No se encontró venta con payment_id: {payment_id}')
            pass
    
    # Si no encontramos la venta, intentar obtenerla de MercadoPago
    if not venta and (payment_id or preference_id):
        try:
            mp_access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None) or os.getenv('MERCADOPAGO_ACCESS_TOKEN')
            if mp_access_token:
                sdk = mercadopago.SDK(mp_access_token)
                
                # Obtener información del pago
                if payment_id:
                    payment_response = sdk.payment().get(payment_id)
                    if "error" not in payment_response:
                        payment = payment_response["response"]
                        preference_id_from_payment = payment.get("preference_id")
                        if preference_id_from_payment:
                            try:
                                venta = VentaN8n.objects.get(mercadopago_preference_id=preference_id_from_payment)
                                venta.mercadopago_payment_id = str(payment.get("id", ""))
                                venta.estado_pago = payment.get("status", "approved")
                                if venta.estado_pago == 'approved':
                                    venta.fecha_pago = timezone.now()
                                    venta.save()
                                    # Crear cotización cuando el pago está aprobado
                                    crear_cotizacion_desde_venta_n8n(venta)
                                else:
                                    venta.save()
                            except VentaN8n.DoesNotExist:
                                pass
                
                # Si aún no tenemos la venta, intentar con preference_id
                if not venta and preference_id:
                    logger.info(f'🔍 Intentando obtener venta desde MercadoPago preference_id: {preference_id}')
                    preference_response = sdk.preference().get(preference_id)
                    if "error" not in preference_response:
                        preference = preference_response["response"]
                        # Crear o obtener venta desde la preferencia
                        items = preference.get("items", [])
                        payer = preference.get("payer", {})
                        metadata = preference.get("metadata", {})
                        # Intentar obtener email de múltiples fuentes
                        email = (
                            payer.get("email") or 
                            payer.get("email_address") or
                            (request.user.email if request.user.is_authenticated else None) or
                            (metadata.get("email_comprador") if metadata else None)
                        )
                        logger.info(f'📧 Email obtenido: {email if email else "NO ENCONTRADO"}')
                        logger.info(f'📦 Items obtenidos: {len(items)} items')
                        logger.info(f'👤 Payer info: {payer}')
                        logger.info(f'📝 Metadata: {metadata}')
                        
                        if email and items:
                            subtotal = sum(item.get("unit_price", 0) * item.get("quantity", 0) for item in items)
                            # Usar get_or_create para evitar errores de duplicados
                            venta, created = VentaN8n.objects.get_or_create(
                                mercadopago_preference_id=preference_id,
                                defaults={
                                    'email_comprador': email,
                                    'items': items,
                                    'metadata': metadata,
                                    'subtotal': subtotal,
                                    'total': subtotal,
                                    'estado_pago': status,
                                }
                            )
                            if created:
                                logger.info(f'✅ Venta creada desde preference_id: {venta.id}')
                            else:
                                logger.info(f'✅ Venta existente encontrada: {venta.id}')
                                # Actualizar datos si es necesario
                                if payment_id and not venta.mercadopago_payment_id:
                                    venta.mercadopago_payment_id = str(payment_id)
                                if status == 'approved' and venta.estado_pago != 'approved':
                                    venta.estado_pago = status
                                    venta.fecha_pago = timezone.now()
                                venta.save()
                            
                            venta.asociar_usuario_por_email()
                            # Si el estado es approved, crear la cotización
                            if status == 'approved':
                                venta.fecha_pago = timezone.now()
                                venta.save()
                                crear_cotizacion_desde_venta_n8n(venta)
                    else:
                        logger.warning(f'❌ Error al obtener preference de MercadoPago: {preference_response.get("error")}')
        except Exception as e:
            logger.exception(f'Error al obtener información de MercadoPago: {e}')
    
    # Si no hay venta después de todos los intentos, mostrar página de error pero NO redirigir
    # Permitir que el usuario vea que hubo un problema en lugar de redirigir
    if not venta:
        logger.error(f'❌ No se pudo encontrar venta después de todos los intentos - payment_id: {payment_id}, preference_id: {preference_id}')
        # NO redirigir, mostrar la página de éxito con error
        messages.error(request, 'No se pudo encontrar la información de tu compra. Por favor, contacta con soporte.')
        # Continuar para mostrar la página de éxito aunque no haya venta
    
    # Si el estado desde la URL es 'approved' y tenemos la venta, actualizar y crear cotización
    if venta and collection_status == 'approved' and venta.estado_pago != 'approved':
        logger.info(f'🔄 Actualizando estado de venta {venta.id} a approved')
        venta.estado_pago = 'approved'
        venta.fecha_pago = timezone.now()
        if payment_id:
            venta.mercadopago_payment_id = str(payment_id)
        venta.save()
        # Crear cotización cuando el pago está aprobado
        crear_cotizacion_desde_venta_n8n(venta)
    
    # Verificar permisos si la venta existe
    # IMPORTANTE: Permitir acceso a la página de éxito siempre, especialmente si viene de MercadoPago
    # Las cookies de sesión se pierden al redirigir desde MercadoPago
    if venta:
        # Si el usuario está logueado, verificar permisos solo para mostrar información adicional
        if request.user.is_authenticated:
            es_propietario = venta.usuario == request.user
            es_staff = request.user.is_superuser or (
                hasattr(request.user, 'perfil') and 
                request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
            )
            # También verificar por email
            if not es_propietario and not es_staff:
                es_propietario = request.user.email == venta.email_comprador
            
            if not (es_propietario or es_staff):
                # NO redirigir, permitir ver la página pero mostrar mensaje
                logger.warning(f'⚠️ Usuario {request.user.id} intenta ver venta {venta.id} que no le pertenece')
                messages.warning(request, 'Esta compra no está asociada a tu cuenta. Si es tuya, inicia sesión con el email correcto.')
        else:
            # Si no está logueado, permitir ver pero sugerir login
            messages.info(request, 'Inicia sesión para ver todas tus compras.')
    
    # Si la venta está aprobada, crear la cotización si no existe
    cotizacion = None
    if venta and venta.estado_pago == 'approved':
        # Verificar si ya tiene una cotización asociada
        if venta.metadata and venta.metadata.get('cotizacion_id'):
            try:
                cotizacion = Cotizacion.objects.get(id=venta.metadata['cotizacion_id'])
                logger.info(f'✅ Cotización encontrada para venta {venta.id}: {cotizacion.numero_cotizacion}')
            except Cotizacion.DoesNotExist:
                logger.warning(f'⚠️ Cotización {venta.metadata.get("cotizacion_id")} no existe en BD')
                pass
        
        # Si no existe, crear la cotización
        if not cotizacion:
            logger.info(f'📝 Creando nueva cotización para venta {venta.id}')
            cotizacion = crear_cotizacion_desde_venta_n8n(venta)
            if cotizacion:
                logger.info(f'✅ Cotización creada: {cotizacion.numero_cotizacion}')
        
        # IMPORTANTE: SIEMPRE mostrar la página de éxito, NO redirigir a detalle_cotizacion
        # Esto es porque el usuario viene de MercadoPago y espera ver la confirmación aquí
        if cotizacion:
            if request.user.is_authenticated:
                logger.info(f'📄 Mostrando página de éxito (usuario logueado) - cotización: {cotizacion.numero_cotizacion}')
                messages.success(request, f'¡Cotización {cotizacion.numero_cotizacion} creada y pagada!')
            else:
                # Si hay cotización pero el usuario no está logueado, mostrar página de éxito
                logger.info(f'📄 Mostrando página de éxito (usuario no logueado) - cotización: {cotizacion.numero_cotizacion}')
                messages.success(request, f'¡Pago exitoso! Cotización {cotizacion.numero_cotizacion} creada.')
    
    # Preparar items con subtotales calculados
    items_con_subtotal = []
    if venta and venta.items:
        for item in venta.items:
            item_copy = item.copy()
            item_copy['subtotal'] = item.get('unit_price', 0) * item.get('quantity', 0)
            items_con_subtotal.append(item_copy)
    
    logger.info(f'📄 Renderizando página de éxito - venta: {venta.id if venta else None}, cotizacion: {cotizacion.id if cotizacion else None}')
    logger.info(f'🔍 Estado final - payment_id: {payment_id}, preference_id: {preference_id}, status: {status}')
    
    # SIEMPRE renderizar la página de éxito, incluso si no hay venta
    # Esto es importante porque MercadoPago redirige aquí después del pago
    context = {
        'venta': venta,
        'cotizacion': cotizacion,
        'items': items_con_subtotal if items_con_subtotal else (venta.items if venta else []),
        'payment_id': payment_id,
        'preference_id': preference_id,
        'status': status,
        'payment_status': collection_status,
    }
    
    logger.info(f'✅ Mostrando página de éxito con context: venta={venta is not None}, cotizacion={cotizacion is not None}, items={len(context["items"])}')
    return render(request, 'tienda/ventas_n8n/pago_exitoso.html', context)


def pago_fallido_n8n(request):
    """Página de pago fallido para ventas de n8n"""
    payment_id = request.GET.get('payment_id')
    preference_id = request.GET.get('preference_id')
    status = request.GET.get('status', 'rejected')
    
    # Buscar la venta si existe
    venta = None
    if preference_id:
        try:
            venta = VentaN8n.objects.get(mercadopago_preference_id=preference_id)
            venta.estado_pago = status
            venta.save()
        except VentaN8n.DoesNotExist:
            pass
    
    context = {
        'venta': venta,
        'payment_id': payment_id,
        'preference_id': preference_id,
    }
    
    return render(request, 'tienda/ventas_n8n/pago_fallido.html', context)


def pago_pendiente_n8n(request):
    """Página de pago pendiente para ventas de n8n"""
    payment_id = request.GET.get('payment_id')
    preference_id = request.GET.get('preference_id')
    status = request.GET.get('status', 'pending')
    
    # Buscar la venta
    venta = None
    if preference_id:
        try:
            venta = VentaN8n.objects.get(mercadopago_preference_id=preference_id)
            venta.estado_pago = status
            venta.save()
        except VentaN8n.DoesNotExist:
            pass
    
    # Verificar si el pago ya fue aprobado
    if payment_id and getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None):
        try:
            mp_access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None) or os.getenv('MERCADOPAGO_ACCESS_TOKEN')
            sdk = mercadopago.SDK(mp_access_token)
            payment_response = sdk.payment().get(payment_id)
            
            if "error" not in payment_response:
                payment = payment_response["response"]
                payment_status = payment.get("status")
                
                if payment_status == 'approved':
                    if venta:
                        venta.estado_pago = 'approved'
                        venta.mercadopago_payment_id = str(payment.get("id", ""))
                        venta.fecha_pago = timezone.now()
                        venta.save()
                    messages.success(request, '¡Tu pago ha sido confirmado!')
                    url = reverse('pago_exitoso_n8n')
                    if payment_id:
                        url += f'?payment_id={payment_id}'
                    if preference_id:
                        url += f'&preference_id={preference_id}' if payment_id else f'?preference_id={preference_id}'
                    return redirect(url)
                elif payment_status in ['rejected', 'cancelled']:
                    messages.error(request, 'El pago fue rechazado. Por favor, intenta nuevamente.')
                    url = reverse('pago_fallido_n8n')
                    if payment_id:
                        url += f'?payment_id={payment_id}'
                    if preference_id:
                        url += f'&preference_id={preference_id}' if payment_id else f'?preference_id={preference_id}'
                    return redirect(url)
        except Exception as e:
            logger.exception(f'Error al verificar pago pendiente: {e}')
    
    context = {
        'venta': venta,
        'payment_id': payment_id,
        'preference_id': preference_id,
    }
    
    return render(request, 'tienda/ventas_n8n/pago_pendiente.html', context)
