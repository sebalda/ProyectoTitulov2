from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0007_remove_precios'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='producto',
            name='grosor',
        ),
    ]
