from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0006_add_medidas'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='producto',
            name='precio_por_metro',
        ),
        migrations.RemoveField(
            model_name='producto',
            name='precio_por_kg',
        ),
    ]
