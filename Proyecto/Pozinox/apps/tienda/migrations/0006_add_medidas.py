from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0005_update_tipo_acero'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='medidas',
            field=models.TextField(default='[]', help_text='JSON array de medidas disponibles para el producto', blank=True),
        ),
    ]
