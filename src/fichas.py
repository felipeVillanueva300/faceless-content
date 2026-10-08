import json
import os
import re
import unicodedata

RUTA = os.environ.get("FICHAS_JSON", "fichas.json")


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " " + re.sub(r"[^a-z0-9]+", " ", t).strip() + " "


def cargar() -> dict:
    try:
        with open(RUTA, encoding="utf-8") as f:
            return (json.load(f) or {}).get("fichas") or {}
    except Exception as e:
        if os.path.exists(RUTA):
            print(f"    (fichas.json no se pudo leer: {e}; sigo sin fichas)")
        return {}


def texto_prompt(fichas=None) -> str:
    fichas = cargar() if fichas is None else fichas
    if not fichas:
        return ""
    partes = []
    for f in fichas.values():
        datos = " ".join(f.get("datos") or [])
        partes.append(f"- {f.get('nombre', '')} ({f.get('link', '')}): {datos}")
    return ("DATOS VERIFICADOS DE INSTITUCIONES (si mencionas alguna, usa SOLO estos datos para "
            "ella y NO los contradigas; si necesitas un dato que no está aquí, no lo inventes: "
            "di dónde consultarlo):\n" + "\n".join(partes) + "\n")


def mencionadas(texto: str, fichas=None):
    """Fichas cuyo nombre/clave aparece en el texto (palabra completa)."""
    fichas = cargar() if fichas is None else fichas
    t = _norm(texto)
    out = []
    for fid, f in fichas.items():
        claves = [f.get("nombre", "")] + list(f.get("claves") or [])
        if any(c and _norm(c) in t for c in claves):
            out.append(f)
    return out


def agregar_links(data: dict, fichas=None) -> dict:
    """Agrega 'Link oficial' al caption para cada institución mencionada en el guion.
    No duplica si el link ya está. Lo pone antes de la línea de hashtags.
    Se salta las fichas con "link_en_caption": false (empresas privadas como Nu o
    Mercado Pago): su link parece anuncio y Telegram muestra su logo en la vista previa."""
    fichas = cargar() if fichas is None else fichas
    if not fichas:
        return data
    beats = " ".join((b.get("narration") or "") for b in (data.get("beats") or [])
                     if isinstance(b, dict))
    cards = " ".join(f"{c.get('big', '')} {c.get('small', '')}" for c in (data.get("cards") or [])
                     if isinstance(c, dict))
    texto = " ".join([data.get("hook", ""), data.get("script", ""), beats, cards])
    caption = data.get("caption") or ""
    t = _norm(texto)

    def _veces(f):
        claves = [f.get("nombre", "")] + list(f.get("claves") or [])
        return sum(t.count(_norm(c)) for c in claves if c)

    candidatas = [f for f in mencionadas(texto, fichas) if f.get("link_en_caption", True) is not False]
    candidatas = sorted(candidatas, key=_veces, reverse=True)[:2]
    lineas = []
    for f in candidatas:
        link = f.get("link", "")
        if link and link not in caption:
            lineas.append(f"🔗 {f.get('nombre', '')} (oficial): {link}")
    if not lineas:
        return data
    bloque = "\n".join(lineas)
    partes = caption.rstrip().rsplit("\n", 1)
    if len(partes) == 2 and partes[1].strip().startswith("#"):
        data["caption"] = f"{partes[0].rstrip()}\n\n{bloque}\n\n{partes[1].strip()}"
    else:
        data["caption"] = f"{caption.rstrip()}\n\n{bloque}"
    print(f"    links oficiales agregados al caption: {len(lineas)}")
    return data