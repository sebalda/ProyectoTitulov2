# Generated manually for updating user roles

from django.db import migrations, models


def migrate_user_roles(apps, schema_editor):
    """Migrar roles existentes a los nuevos roles: Cliente, Trabajador, Administrador"""
    PerfilUsuario = apps.get_model('usuarios', 'PerfilUsuario')
    
    # Convertir roles antiguos a 'trabajador'
    # vendedor, inventario, contabilidad -> trabajador
    PerfilUsuario.objects.filter(tipo_usuario__in=['vendedor', 'inventario', 'contabilidad']).update(tipo_usuario='trabajador')
    
    # Mantener: cliente -> cliente, administrador -> administrador


def reverse_migrate_user_roles(apps, schema_editor):
    """Revertir migración - convertir trabajador a vendedor por defecto"""
    PerfilUsuario = apps.get_model('usuarios', 'PerfilUsuario')
    
    # Convertir trabajador -> vendedor (un rol antiguo por defecto)
    PerfilUsuario.objects.filter(tipo_usuario='trabajador').update(tipo_usuario='vendedor')


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0005_passwordresettoken'),
    ]

    operations = [
        # Primero migrar los datos existentes
        migrations.RunPython(migrate_user_roles, reverse_migrate_user_roles),
        
        # Luego cambiar las opciones del campo
        migrations.AlterField(
            model_name='perfilusuario',
            name='tipo_usuario',
            field=models.CharField(
                choices=[
                    ('cliente', 'Cliente'),
                    ('trabajador', 'Trabajador'),
                    ('administrador', 'Administrador'),
                ],
                default='cliente',
                max_length=20
            ),
        ),
    ]

