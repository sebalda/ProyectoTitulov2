from PIL import Image, ImageDraw, ImageFont
import os


def ensure_outdir():
    base = os.path.dirname(__file__)
    out = os.path.abspath(os.path.join(base, '..', 'static', 'images'))
    os.makedirs(out, exist_ok=True)
    return out


def draw_entrelazado(size, primary="#1e3a8a", accent="#fbbf24", bg=None):
    # bg None => transparent, otherwise expects hex
    if bg is None:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    else:
        img = Image.new('RGBA', (size, size), tuple(int(bg[i:i+2], 16) for i in (1, 3, 5)) + (255,))
    draw = ImageDraw.Draw(img)

    # badge circle
    pad = int(size * 0.08)
    bbox = (pad, pad, size - pad - 1, size - pad - 1)
    draw.ellipse(bbox, fill=None, outline=None)

    # prepare fonts (bold). Try common ttf names
    font_size = int(size * 0.7)
    font = None
    for fname in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "SegoeUI-Bold.ttf"):
        try:
            font = ImageFont.truetype(fname, font_size)
            break
        except Exception:
            font = None
    if font is None:
        font = ImageFont.load_default()

    # Draw big 'P' in primary color, slightly left
    p_text = "P"
    z_text = "Z"

    # measure
    try:
        pb = draw.textbbox((0, 0), p_text, font=font)
        pw = pb[2] - pb[0]
        ph = pb[3] - pb[1]
    except Exception:
        pw, ph = font.getsize(p_text)

    # scale factors: we'll render at sizes relative to square
    # position P slightly left
    p_x = int(size * 0.18)
    p_y = int((size - ph) / 2) - int(size * 0.04)

    # Draw P with thick stroke by drawing text multiple times for pseudo-stroke
    prim_rgb = tuple(int(primary[i:i+2], 16) for i in (1, 3, 5))
    acc_rgb = tuple(int(accent[i:i+2], 16) for i in (1, 3, 5))

    # simulate bold/outline by drawing offset shadows
    for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        draw.text((p_x + ox, p_y + oy), p_text, font=font, fill=(0, 0, 0, 90))
    draw.text((p_x, p_y), p_text, font=font, fill=prim_rgb)

    # For Z, we draw rotated and overlapping the P to create an intertwined effect
    # Create a separate image for Z and rotate
    z_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    z_draw = ImageDraw.Draw(z_img)
    try:
        zb = z_draw.textbbox((0, 0), z_text, font=font)
        zw = zb[2] - zb[0]
        zh = zb[3] - zb[1]
    except Exception:
        zw, zh = font.getsize(z_text)

    z_x = int(size * 0.45)
    z_y = int((size - zh) / 2) + int(size * 0.02)

    # gold shadow for contrast
    z_draw.text((z_x + 3, z_y + 3), z_text, font=font, fill=(0, 0, 0, 100))
    z_draw.text((z_x, z_y), z_text, font=font, fill=acc_rgb)

    # rotate a bit (-14 degrees) and paste
    zr = z_img.rotate(-12, resample=Image.BICUBIC, center=(size//2, size//2))

    # Composite Z onto main image with alpha—this overlaps P to look intertwined
    img = Image.alpha_composite(img, zr)

    # add subtle inner highlight circle
    overlay = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    ov = ImageDraw.Draw(overlay)
    ov.ellipse((pad + int(size*0.02), pad + int(size*0.02), size - pad - int(size*0.02), size - pad - int(size*0.02)), outline=(255,255,255,18))
    img = Image.alpha_composite(img, overlay)

    return img


def main():
    out = ensure_outdir()
    sizes = [512, 256, 192, 128, 96, 64, 48, 32, 16]
    for s in sizes:
        im = draw_entrelazado(s)
        path = os.path.join(out, f"pz-entrelazado-{s}.png")
        im.save(path, format='PNG')
        print(f"Generado: {path}")

    try:
        ico_sizes = [64, 32, 16]
        im = draw_entrelazado(max(ico_sizes))
        ico_path = os.path.join(out, 'pz-entrelazado.ico')
        im.save(ico_path, format='ICO', sizes=[(s, s) for s in ico_sizes])
        print(f"Generado: {ico_path}")
    except Exception as e:
        print(f"Error creando ICO: {e}")


if __name__ == '__main__':
    main()
