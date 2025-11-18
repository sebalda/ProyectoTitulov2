from django.db import migrations


def forwards_func(apps, schema_editor):
    Producto = apps.get_model('tienda', 'Producto')
    # Map old values to new values. Any unmapped value will be set to '304' as safe default.
    mapping = {
        'inoxidable': '304',
        'carbono': '304',
        'galvanizado': '304',
        'estructural': '304',
    }
    for producto in Producto.objects.all():
        old = producto.tipo_acero
        if old in mapping:
            producto.tipo_acero = mapping[old]
            producto.save(update_fields=['tipo_acero'])
        elif old not in dict(Producto._meta.get_field('tipo_acero').choices).keys():
            # set safe default
            producto.tipo_acero = '304'
            producto.save(update_fields=['tipo_acero'])


def reverse_func(apps, schema_editor):
    # Reversing is non-trivial; we'll leave values as-is when migrating backwards.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0004_cotizacion_comentarios_pago_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
