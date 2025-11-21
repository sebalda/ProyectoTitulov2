from django.contrib import admin
from .models import Producto, CategoriaAcero, Cliente, Pedido, DetallePedido, Cotizacion, DetalleCotizacion, TransferenciaBancaria, VentaN8n


@admin.register(CategoriaAcero)
class CategoriaAceroAdmin(admin.ModelAdmin):
    """Administración de categorías de acero"""
    list_display = ['nombre', 'activa', 'id']
    list_filter = ['activa']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    """Administración de productos"""
    list_display = ['codigo_producto', 'nombre', 'categoria', 'tipo_acero', 'precio_por_unidad', 'stock_actual', 'activo', 'imagen_preview']
    list_filter = ['categoria', 'tipo_acero', 'activo']
    search_fields = ['nombre', 'codigo_producto', 'descripcion']
    ordering = ['categoria', 'nombre']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'codigo_producto', 'categoria', 'tipo_acero')
        }),
        ('Especificaciones Técnicas', {
            'fields': ('grosor', 'ancho', 'largo', 'peso_por_metro'),
            'classes': ('collapse',)
        }),
        ('Precios', {
            'fields': ('precio_por_unidad',)
        }),
        ('Stock', {
            'fields': ('stock_actual', 'stock_minimo', 'unidad_medida')
        }),
        ('Imagen', {
            'fields': ('imagen',)
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )
    
    def imagen_preview(self, obj):
        """Mostrar preview de la imagen en el admin"""
        if obj.imagen:
            return f"✅ Tiene imagen: {obj.imagen.name}"
        return "❌ Sin imagen"
    imagen_preview.short_description = 'Imagen'


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    """Administración de clientes"""
    list_display = ['nombre', 'apellido', 'tipo_cliente', 'email', 'telefono', 'activo']
    list_filter = ['tipo_cliente', 'activo']
    search_fields = ['nombre', 'apellido', 'email', 'rut']
    ordering = ['apellido', 'nombre']


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    """Administración de pedidos"""
    list_display = ['numero_pedido', 'cliente', 'fecha_pedido', 'estado', 'total']
    list_filter = ['estado', 'metodo_pago', 'fecha_pedido']
    search_fields = ['numero_pedido', 'cliente__nombre', 'cliente__apellido']
    ordering = ['-fecha_pedido']


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    """Administración de detalles de pedidos"""
    list_display = ['pedido', 'producto', 'cantidad', 'precio_unitario', 'subtotal']
    list_filter = ['pedido__estado']
    search_fields = ['pedido__numero_pedido', 'producto__nombre']
    ordering = ['-pedido__fecha_pedido']


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    """Administración de cotizaciones"""
    list_display = ['numero_cotizacion', 'usuario', 'estado', 'fecha_creacion', 'total', 'pago_completado']
    list_filter = ['estado', 'pago_completado', 'metodo_pago', 'fecha_creacion']
    search_fields = ['numero_cotizacion', 'usuario__username', 'usuario__email']
    ordering = ['-fecha_creacion']
    readonly_fields = ['numero_cotizacion', 'fecha_creacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('usuario', 'numero_cotizacion', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion', 'fecha_finalizacion')
        }),
        ('Totales', {
            'fields': ('subtotal', 'iva', 'total')
        }),
        ('Pago', {
            'fields': ('metodo_pago', 'pago_completado', 'mercadopago_preference_id', 'mercadopago_payment_id')
        }),
        ('Observaciones', {
            'fields': ('observaciones',)
        }),
    )


class DetalleCotizacionInline(admin.TabularInline):
    """Inline para detalles de cotización"""
    model = DetalleCotizacion
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(DetalleCotizacion)
class DetalleCotizacionAdmin(admin.ModelAdmin):
    """Administración de detalles de cotizaciones"""
    list_display = ['cotizacion', 'producto', 'cantidad', 'precio_unitario', 'subtotal']
    list_filter = ['cotizacion__estado']
    search_fields = ['cotizacion__numero_cotizacion', 'producto__nombre']
    ordering = ['-cotizacion__fecha_creacion']


@admin.register(TransferenciaBancaria)
class TransferenciaBancariaAdmin(admin.ModelAdmin):
    """Administración de transferencias bancarias"""
    list_display = ['cotizacion', 'estado', 'monto_transferencia', 'fecha_creacion', 'verificada_por']
    list_filter = ['estado', 'fecha_creacion', 'verificada_por']
    search_fields = ['cotizacion__numero_cotizacion', 'numero_transaccion', 'observaciones_cliente']
    ordering = ['-fecha_creacion']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion', 'fecha_verificacion']
    
    fieldsets = (
        ('Información de la Transferencia', {
            'fields': ('cotizacion', 'estado', 'monto_transferencia', 'fecha_transferencia', 'numero_transaccion')
        }),
        ('Datos Bancarios', {
            'fields': ('banco_destino', 'tipo_cuenta', 'numero_cuenta', 'nombre_titular')
        }),
        ('Comprobante', {
            'fields': ('comprobante', 'observaciones_cliente')
        }),
        ('Verificación', {
            'fields': ('verificada_por', 'fecha_verificacion', 'observaciones_verificador')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion', 'fecha_expiracion')
        }),
    )
    
    def get_queryset(self, request):
        """Filtrar transferencias según el rol del usuario"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Los trabajadores solo ven transferencias pendientes y en verificación
            qs = qs.filter(estado__in=['pendiente', 'verificando'])
        return qs


@admin.register(VentaN8n)
class VentaN8nAdmin(admin.ModelAdmin):
    """Administración de ventas de N8N"""
    list_display = ['mercadopago_preference_id', 'email_comprador', 'usuario', 'estado_pago', 'total', 'fecha_creacion']
    list_filter = ['estado_pago', 'fecha_creacion', 'fecha_pago']
    search_fields = ['mercadopago_preference_id', 'mercadopago_payment_id', 'email_comprador', 'usuario__email', 'usuario__username']
    ordering = ['-fecha_creacion']
    readonly_fields = ['mercadopago_preference_id', 'fecha_creacion', 'fecha_actualizacion', 'fecha_pago']
    
    fieldsets = (
        ('Información de MercadoPago', {
            'fields': ('mercadopago_preference_id', 'mercadopago_payment_id', 'estado_pago')
        }),
        ('Información del Comprador', {
            'fields': ('email_comprador', 'usuario')
        }),
        ('Productos y Totales', {
            'fields': ('items', 'metadata', 'subtotal', 'total')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion', 'fecha_pago')
        }),
    )
