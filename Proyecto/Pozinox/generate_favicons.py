"""
Script para generar favicons en múltiples tamaños desde logo_fondoblanco.png
"""
from PIL import Image
import os

# Ruta de la imagen original
static_images = os.path.join('static', 'images')
source_image = os.path.join(static_images, 'logo_fondoblanco.png')

# Verificar que existe la imagen
if not os.path.exists(source_image):
    print(f"Error: No se encuentra {source_image}")
    exit(1)

# Abrir imagen original
img = Image.open(source_image)
print(f"Imagen original: {img.size}")

# Asegurar que tiene canal alpha para transparencia
if img.mode != 'RGBA':
    img = img.convert('RGBA')

# Tamaños a generar
sizes = {
    'favicon-16x16.png': (16, 16),
    'favicon-32x32.png': (32, 32),
    'apple-touch-icon.png': (180, 180),
    'android-chrome-192x192.png': (192, 192),
    'android-chrome-512x512.png': (512, 512),
}

# Generar cada tamaño
for filename, size in sizes.items():
    output_path = os.path.join(static_images, filename)
    resized = img.resize(size, Image.Resampling.LANCZOS)
    resized.save(output_path, 'PNG', optimize=True)
    print(f"✓ Generado: {filename} ({size[0]}x{size[1]})")

# Generar favicon.ico (múltiples tamaños en un solo archivo)
ico_sizes = [(16, 16), (32, 32), (48, 48)]
ico_images = []
for size in ico_sizes:
    ico_images.append(img.resize(size, Image.Resampling.LANCZOS))

ico_path = os.path.join(static_images, 'favicon.ico')
ico_images[0].save(
    ico_path,
    format='ICO',
    sizes=ico_sizes,
    append_images=ico_images[1:]
)
print(f"✓ Generado: favicon.ico (16x16, 32x32, 48x48)")

print("\n✅ Todos los favicons generados exitosamente!")
