# Generated manually to fix migration conflicts
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0008_alter_producto_tipo_acero'),
    ]

    operations = [
        # Actualizar tipo_acero con las nuevas opciones
        migrations.AlterField(
            model_name='producto',
            name='tipo_acero',
            field=models.CharField(
                choices=[
                    ('304', '304'),
                    ('304L', '304L'),
                    ('316', '316'),
                    ('316L', '316L'),
                    ('Viton', 'Viton'),
                    ('Silicona', 'Silicona'),
                    ('Vidrio', 'Vidrio'),
                ],
                max_length=20
            ),
        ),
    ]
