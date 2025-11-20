"""
Script para agregar manualmente los campos de facturación a la tabla tienda_cotizacion
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Pozinox.settings')
django.setup()

from django.db import connection

def add_facturacion_fields():
    with connection.cursor() as cursor:
        try:
            # Agregar campo facturada
            cursor.execute("""
                ALTER TABLE tienda_cotizacion 
                ADD COLUMN IF NOT EXISTS facturada BOOLEAN DEFAULT FALSE NOT NULL;
            """)
            print("✅ Campo 'facturada' agregado")
        except Exception as e:
            print(f"❌ Error al agregar 'facturada': {e}")
        
        try:
            # Agregar campo tipo_documento
            cursor.execute("""
                ALTER TABLE tienda_cotizacion 
                ADD COLUMN IF NOT EXISTS tipo_documento VARCHAR(20);
            """)
            print("✅ Campo 'tipo_documento' agregado")
        except Exception as e:
            print(f"❌ Error al agregar 'tipo_documento': {e}")
        
        try:
            # Agregar campo numero_documento
            cursor.execute("""
                ALTER TABLE tienda_cotizacion 
                ADD COLUMN IF NOT EXISTS numero_documento VARCHAR(50);
            """)
            print("✅ Campo 'numero_documento' agregado")
        except Exception as e:
            print(f"❌ Error al agregar 'numero_documento': {e}")
        
        try:
            # Agregar campo fecha_facturacion
            cursor.execute("""
                ALTER TABLE tienda_cotizacion 
                ADD COLUMN IF NOT EXISTS fecha_facturacion TIMESTAMP WITH TIME ZONE;
            """)
            print("✅ Campo 'fecha_facturacion' agregado")
        except Exception as e:
            print(f"❌ Error al agregar 'fecha_facturacion': {e}")
        
        try:
            # Agregar campo facturado_por_id (FK a User)
            cursor.execute("""
                ALTER TABLE tienda_cotizacion 
                ADD COLUMN IF NOT EXISTS facturado_por_id INTEGER 
                REFERENCES usuarios_usuario(id) ON DELETE SET NULL;
            """)
            print("✅ Campo 'facturado_por_id' agregado")
        except Exception as e:
            print(f"❌ Error al agregar 'facturado_por_id': {e}")
        
        try:
            # Agregar campo folio_sii
            cursor.execute("""
                ALTER TABLE tienda_cotizacion 
                ADD COLUMN IF NOT EXISTS folio_sii VARCHAR(100);
            """)
            print("✅ Campo 'folio_sii' agregado")
        except Exception as e:
            print(f"❌ Error al agregar 'folio_sii': {e}")
        
        try:
            # Agregar campo track_id_sii
            cursor.execute("""
                ALTER TABLE tienda_cotizacion 
                ADD COLUMN IF NOT EXISTS track_id_sii VARCHAR(100);
            """)
            print("✅ Campo 'track_id_sii' agregado")
        except Exception as e:
            print(f"❌ Error al agregar 'track_id_sii': {e}")
        
        try:
            # Agregar campo estado_sii
            cursor.execute("""
                ALTER TABLE tienda_cotizacion 
                ADD COLUMN IF NOT EXISTS estado_sii VARCHAR(50);
            """)
            print("✅ Campo 'estado_sii' agregado")
        except Exception as e:
            print(f"❌ Error al agregar 'estado_sii': {e}")
        
        try:
            # Agregar campo xml_dte
            cursor.execute("""
                ALTER TABLE tienda_cotizacion 
                ADD COLUMN IF NOT EXISTS xml_dte TEXT;
            """)
            print("✅ Campo 'xml_dte' agregado")
        except Exception as e:
            print(f"❌ Error al agregar 'xml_dte': {e}")
        
        try:
            # Agregar campo pdf_documento
            cursor.execute("""
                ALTER TABLE tienda_cotizacion 
                ADD COLUMN IF NOT EXISTS pdf_documento VARCHAR(100);
            """)
            print("✅ Campo 'pdf_documento' agregado")
        except Exception as e:
            print(f"❌ Error al agregar 'pdf_documento': {e}")
        
        print("\n✅ Proceso completado")

if __name__ == '__main__':
    print("🔧 Agregando campos de facturación a tienda_cotizacion...\n")
    add_facturacion_fields()
