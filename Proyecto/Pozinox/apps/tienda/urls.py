from django.urls import path
from . import views

urlpatterns = [
    # URLs públicas
    path('', views.home, name='home'),
    path('productos/', views.productos_publicos, name='productos'),
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    
    # Panel Admin
    path('panel-admin/', views.panel_admin, name='panel_admin'),
    path('panel-admin/productos/', views.lista_productos_admin, name='lista_productos_admin'),
    path('panel-admin/productos/crear/', views.crear_producto, name='crear_producto'),
    path('panel-admin/productos/editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('panel-admin/productos/eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('panel-admin/categorias/', views.lista_categorias_admin, name='lista_categorias_admin'),
    path('panel-admin/categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('panel-admin/categorias/editar/<int:categoria_id>/', views.editar_categoria, name='editar_categoria'),
    path('panel-admin/categorias/eliminar/<int:categoria_id>/', views.eliminar_categoria, name='eliminar_categoria'),
    path('panel-admin/transferencias/', views.panel_verificacion_transferencias, name='panel_verificacion_transferencias'),
    path('panel-admin/transferencias/<int:transferencia_id>/verificar/', views.verificar_transferencia, name='verificar_transferencia'),
    
    # Gestión de estados para trabajadores
    path('trabajadores/estados-preparacion/', views.gestionar_estados_preparacion, name='gestionar_estados_preparacion'),
    path('trabajadores/estados-preparacion/<int:cotizacion_id>/cambiar/', views.cambiar_estado_preparacion, name='cambiar_estado_preparacion'),
    
    # Cotizaciones
    path('cotizaciones/', views.mis_cotizaciones, name='mis_cotizaciones'),
    path('cotizaciones/crear/', views.crear_cotizacion, name='crear_cotizacion'),
    path('cotizaciones/<int:cotizacion_id>/', views.detalle_cotizacion, name='detalle_cotizacion'),
    path('cotizaciones/<int:cotizacion_id>/agregar-producto/', views.agregar_producto_cotizacion, name='agregar_producto_cotizacion'),
    path('cotizaciones/detalle/<int:detalle_id>/actualizar-cantidad/', views.actualizar_cantidad_producto, name='actualizar_cantidad_producto'),
    path('cotizaciones/detalle/<int:detalle_id>/eliminar/', views.eliminar_producto_cotizacion, name='eliminar_producto_cotizacion'),
    path('cotizaciones/<int:cotizacion_id>/finalizar/', views.finalizar_cotizacion, name='finalizar_cotizacion'),
    
    # Pagos
    path('cotizaciones/<int:cotizacion_id>/seleccionar-pago/', views.seleccionar_pago, name='seleccionar_pago'),
    path('cotizaciones/<int:cotizacion_id>/pagar-mercadopago/', views.procesar_pago_mercadopago, name='procesar_pago_mercadopago'),
    path('cotizaciones/<int:cotizacion_id>/pago-exitoso/', views.pago_exitoso, name='pago_exitoso'),
    path('cotizaciones/<int:cotizacion_id>/pago-fallido/', views.pago_fallido, name='pago_fallido'),
    path('cotizaciones/<int:cotizacion_id>/pago-pendiente/', views.pago_pendiente, name='pago_pendiente'),
    path('cotizaciones/<int:cotizacion_id>/descargar-pdf/', views.descargar_cotizacion_pdf, name='descargar_cotizacion_pdf'),
    
    # Transferencias
    path('cotizaciones/<int:cotizacion_id>/pagar-transferencia/', views.procesar_pago_transferencia, name='procesar_pago_transferencia'),
    path('cotizaciones/<int:cotizacion_id>/pagar-efectivo/', views.procesar_pago_efectivo, name='procesar_pago_efectivo'),
    path('cotizaciones/<int:cotizacion_id>/transferencia/', views.detalle_transferencia, name='detalle_transferencia'),
    path('cotizaciones/<int:cotizacion_id>/subir-comprobante/', views.subir_comprobante, name='subir_comprobante'),
    
    # Páginas legales
    path('politica-privacidad/', views.politica_privacidad, name='politica_privacidad'),
    path('terminos-condiciones/', views.terminos_condiciones, name='terminos_condiciones'),
]
