import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

W, H = 1080, 1350                 # 4:5, el formato que más pantalla ocupa en el feed
MARGIN = 90
ACCENT = (0, 229, 255)            # cian de marca (0x00E5FF)
WHITE = (255, 255, 255)
NAVY0 = (27, 58, 92)              # 0x1B3A5C  (arriba)
NAVY1 = (7, 11, 18)               # 0x070B12  (abajo)

WATERMARK = os.environ.get("WATERMARK_TEXT", "@villanuevagallegosf")
BG_DIM = float(os.environ.get("IMG_BG_DIM", "0.55"))

# Fuentes candidatas: Actions (Linux) trae DejaVu; en Windows local usa Arial.
_FONT_CANDIDATES = [
    os.environ.get("IMG_FONT_FILE", ""),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\Arial.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def _font(size: int):
    for path in _FONT_CANDIDATES:
        if path and os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _gradient_bg() -> Image.Image:
    base = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(base)
    for y in range(H):
        t = y / (H - 1)
        c = (int(NAVY0[0] * (1 - t) + NAVY1[0] * t),
             int(NAVY0[1] * (1 - t) + NAVY1[1] * t),
             int(NAVY0[2] * (1 - t) + NAVY1[2] * t))
        draw.line([(0, y), (W, y)], fill=c)
    return base


def _cover(img: Image.Image) -> Image.Image:
    """Escala y recorta la imagen para que cubra 1080x1350 sin deformar."""
    sw, sh = img.size
    scale = max(W / sw, H / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - W) // 2, (nh - H) // 2
    return img.crop((left, top, left + W, top + H))


def _prepare_bg(bg_path) -> Image.Image:
    if bg_path and os.path.isfile(bg_path):
        try:
            img = Image.open(bg_path).convert("RGB")
            img = _cover(img)
            img = ImageEnhance.Brightness(img).enhance(BG_DIM)   # oscurecer para legibilidad
            img = ImageEnhance.Color(img).enhance(1.08)          # un pelín más de color
            return img
        except Exception as e:
            print(f"    (no se pudo usar el fondo IA: {e}; uso degradado)")
    return _gradient_bg()


def _fit_font(draw, text, max_w, start_size, min_size=80):
    size = start_size
    while size > min_size:
        f = _font(size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return _font(min_size)


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for w in text.split():
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _draw_center(draw, text, font, y, fill):
    w = draw.textlength(text, font=font)
    x = (W - w) // 2
    draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0))   # sombra
    draw.text((x, y), text, font=font, fill=fill)


def _text_h(font, sample):
    box = font.getbbox(sample)
    return box[3] - box[1]


def render_image(big: str, small: str, out_path: str, bg_path=None) -> str:
    img = _prepare_bg(bg_path)
    draw = ImageDraw.Draw(img)
    max_w = W - 2 * MARGIN

    big = (big or "").strip().upper()
    small = (small or "").strip()

    big_font = _fit_font(draw, big, max_w, 240, 90) if big else None
    small_font = _font(60)
    small_lines = _wrap(draw, small, small_font, max_w) if small else []

    big_h = _text_h(big_font, big) if big else 0
    line_h = _text_h(small_font, "Ag") + 20
    accent_gap = 40 if big else 0
    block_h = big_h + accent_gap + line_h * len(small_lines)
    y = (H - block_h) // 2

    if big:
        _draw_center(draw, big, big_font, y, ACCENT)
        y += big_h + 26
        lw = min(max_w, int(draw.textlength(big, font=big_font)))
        draw.rectangle([(W - lw) // 2, y, (W + lw) // 2, y + 8], fill=ACCENT)  # línea de acento
        y += accent_gap - 26

    for ln in small_lines:
        _draw_center(draw, ln, small_font, y, WHITE)
        y += line_h

    wm_font = _font(34)
    draw.text((MARGIN, H - 72), WATERMARK, font=wm_font, fill=(255, 255, 255))

    img.save(out_path, "JPEG", quality=90)
    return out_path
