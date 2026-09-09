import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
CYAN = (0, 229, 255)
RED = (255, 90, 95)
GREEN = (34, 197, 94)
WHITE = (255, 255, 255)
DIM = (190, 205, 215)

_FONT_CANDIDATES = [
    os.environ.get("IMG_FONT_FILE", ""),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\Arial.ttf",
]


def _font(size):
    for p in _FONT_CANDIDATES:
        if p and os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _center(draw, text, font, cx, y, fill, shadow=True):
    w = draw.textlength(text, font=font)
    x = cx - w / 2
    if shadow:
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 180))
    draw.text((x, y), text, font=font, fill=fill)


def _rounded_bar(draw, x, y, w, h, color, radius=24):
    if h <= 1:
        return
    r = min(radius, w // 2, h // 2)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=color)


def _ease(t):
    # suavizado (easeOutCubic) para que la animación se sienta natural
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def render_bars_frame(spec, progress, out_path):
    """spec: {title, a_label, a_value, b_label, b_value, a_color?, b_color?}."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    p = _ease(progress)

    title = spec.get("title", "")
    a_val, b_val = float(spec["a_value"]), float(spec["b_value"])
    a_col = RED if spec.get("a_color", "red") == "red" else GREEN
    b_col = GREEN if spec.get("b_color", "green") == "green" else RED

    base_y = 1180
    max_h = 560
    bar_w = 300
    gap = 120
    cx = W // 2
    ax = cx - gap // 2 - bar_w
    bx = cx + gap // 2
    mx = max(a_val, b_val) or 1

    if title:
        _center(d, title.upper(), _font(60), cx, base_y - max_h - 150, WHITE)

    for x, val, col, lbl in [(ax, a_val, a_col, spec.get("a_label", "")),
                             (bx, b_val, b_col, spec.get("b_label", ""))]:
        h = int(max_h * (val / mx) * p)
        _rounded_bar(d, x, base_y - h, bar_w, h, col)
        # valor arriba de la barra (sube con la animación)
        shown = val * p
        txt = f"${shown:,.0f}" if spec.get("money", True) else f"{shown:,.0f}"
        _center(d, txt, _font(64), x + bar_w / 2, base_y - h - 90, WHITE)
        # etiqueta abajo
        _center(d, lbl, _font(44), x + bar_w / 2, base_y + 24, DIM, shadow=False)

    img.save(out_path)
    return out_path


def render_countup_frame(spec, progress, out_path):
    """spec: {value, prefix?, suffix?, label}."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    p = _ease(progress)

    value = float(spec["value"]) * p
    prefix = spec.get("prefix", "$")
    suffix = spec.get("suffix", "")
    num = f"{prefix}{value:,.0f}{suffix}"

    cy = 1000
    _center(d, num, _font(230), W // 2, cy - 150, CYAN)
    # línea de acento
    lw = 520
    d.rounded_rectangle([(W - lw) // 2, cy + 130, (W + lw) // 2, cy + 142], radius=6, fill=CYAN)
    _center(d, spec.get("label", "").upper(), _font(62), W // 2, cy + 175, WHITE)

    img.save(out_path)
    return out_path


def render_frames(spec, seconds, out_dir, fps=30):
    """Renderiza la animación completa como secuencia de PNG transparentes.

    Anima en los primeros ~1.2s (progreso 0->1) y sostiene el resto. Devuelve
    (patrón_absoluto, num_frames, fps) para que video.py lo superponga.
    """
    os.makedirs(out_dir, exist_ok=True)
    n = max(1, int(round(seconds * fps)))
    anim = max(1, int(fps * 1.2))
    typ = (spec.get("type") or "countup").lower()
    for i in range(n):
        progress = 1.0 if i >= anim else (i / anim)
        path = os.path.join(out_dir, f"f_{i:05d}.png")
        if typ == "bars":
            render_bars_frame(spec, progress, path)
        else:
            render_countup_frame(spec, progress, path)
    pattern = os.path.join(os.path.abspath(out_dir), "f_%05d.png")
    return pattern, n, fps