import datetime
import os
import re
import unicodedata

_CTAS = [
    "Si te sirvió, guárdalo y compártelo con quien lo necesite.",
    "Guárdalo para tu próxima quincena. Mañana hay otro consejo.",
    "Mándaselo a alguien que siempre anda corto de quincena.",
    "Sígueme para un consejo de dinero al día, sin rollos.",
    "Pruébalo esta quincena y cuéntame en los comentarios cómo te fue.",
    "Compártelo con tu familia: a todos nos ha pasado.",
]

# líneas de llamado que Gemini a veces agrega solo; las quitamos para no duplicar
_CTA_VIEJO = re.compile(r"^\s*(s[ií]gueme|guarda (este|el video)|comp[aá]rtelo)\b.*$",
                        re.IGNORECASE)


def _sin_acentos(t: str) -> str:
    t = unicodedata.normalize("NFD", t or "")
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def hashtag_serie(nombre: str) -> str:
    pals = re.findall(r"[A-Za-z0-9]+", _sin_acentos(nombre))
    return "#" + "".join(p[:1].upper() + p[1:] for p in pals) if pals else ""


def _cta_del_dia() -> str:
    try:
        corrida = int(os.environ.get("GITHUB_RUN_NUMBER", "0"))
    except ValueError:
        corrida = 0
    return _CTAS[(datetime.date.today().toordinal() + corrida) % len(_CTAS)]


def _cta_serie(nombre, parte, total) -> str:
    try:
        p, t = int(parte), int(total)
    except (TypeError, ValueError):
        return f"📚 Esto es parte de la serie «{nombre}». Sígueme para no perderte la siguiente."
    if p >= t:
        return (f"📚 Última parte de la serie «{nombre}». Ve las {t} partes en mi perfil "
                f"y sígueme para la próxima serie.")
    return (f"📚 Parte {p} de {t} de la serie «{nombre}». Sígueme para no perderte "
            f"la parte {p + 1}.")


def finalizar(data: dict, plan: dict) -> dict:
    """Ajusta data['title'] y data['caption'] con la estructura fija."""
    serie_nombre = (plan.get("serie_nombre") or "").strip()
    parte, total = plan.get("serie_parte"), plan.get("serie_total")
    es_serie = bool(serie_nombre and parte)

    # --- título ---
    titulo = (data.get("title") or "").strip().rstrip(".")
    if es_serie:
        prefijo = f"{serie_nombre} ({parte}/{total}): " if total else f"{serie_nombre} (parte {parte}): "
        titulo = re.sub(r"\s*[\(\[]?\s*parte\s*\d+(\s*(de|/)\s*\d+)?\s*[\)\]]?\s*$", "", titulo,
                        flags=re.IGNORECASE).strip(" :-")
        if not titulo.lower().startswith(serie_nombre.lower()):
            titulo = prefijo + titulo
        data["serie"] = {"nombre": serie_nombre, "parte": parte, "total": total}
    data["title"] = titulo[:100]

    # --- caption ---
    lineas = [l.rstrip() for l in (data.get("caption") or "").strip().split("\n")]
    hashtags = ""
    if lineas and lineas[-1].strip().startswith("#"):
        hashtags = lineas.pop().strip()
    cuerpo = [l for l in lineas if not _CTA_VIEJO.match(l)]
    while cuerpo and not cuerpo[-1].strip():
        cuerpo.pop()
    cta = _cta_serie(serie_nombre, parte, total) if es_serie else _cta_del_dia()
    if es_serie:
        tag = hashtag_serie(serie_nombre)
        if tag and tag.lower() not in hashtags.lower():
            hashtags = (hashtags + " " + tag).strip()
    partes = ["\n".join(cuerpo).strip(), cta]
    if hashtags:
        partes.append(hashtags)
    data["caption"] = "\n\n".join(p for p in partes if p)
    return data
