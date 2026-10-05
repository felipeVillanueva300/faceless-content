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

_CTAS_FRAUDE = [
    "Mándaselo a tu familia, sobre todo a quien menos usa redes: así no les ven la cara.",
    "Compártelo con tu familia hoy: a quien ya está avisado es mucho más difícil engañarlo.",
]

_FRAUDE = re.compile(r"fraud|estaf|extorsi|clonad|suplant|phishing|hacke|montadeud|"
                     r"\broba[nr]?\b|\brobo\b|que no te roben", re.IGNORECASE)


def es_tema_fraude(data: dict) -> bool:
    """True si el TEMA central del video es un fraude/estafa/robo (no si solo se menciona
    de pasada en la narración)."""
    texto = " ".join(str(data.get(k) or "") for k in
                     ("title", "hook", "hook_card", "concepto", "topic"))
    return bool(_FRAUDE.search(_sin_acentos(texto)))


_SIGUEME_FINAL = re.compile(r"(^|(?<=[.!?…])\s+)¡?s[ií]gueme\b[^.!?…]*[.!?…]?\s*$",
                            re.IGNORECASE)
CTA_HABLADO_FRAUDE = os.environ.get("CTA_HABLADO_FRAUDE", "Mándaselo a tu familia hoy.")


def cta_hablado_fraude(data: dict) -> dict:
    """En un reel de fraude, si el último bloque cierra con "Sígueme…", lo cambia por
    "Mándaselo a tu familia hoy." ANTES de la voz: así lo que se oye y el cierre en
    pantalla (COMPÁRTELO) dicen lo mismo."""
    beats = [b for b in (data.get("beats") or []) if isinstance(b, dict) and b.get("narration")]
    if beats:
        ult = beats[-1]
        nuevo = _SIGUEME_FINAL.sub(lambda m: m.group(1) + CTA_HABLADO_FRAUDE, ult["narration"].strip())
        ult["narration"] = nuevo.strip()
    if isinstance(data.get("script"), str):
        data["script"] = _SIGUEME_FINAL.sub(lambda m: m.group(1) + CTA_HABLADO_FRAUDE,
                                            data["script"].strip()).strip()
    return data


_NUM_PALABRA = {2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho"}


def asegurar_adelanto(data: dict, plan: dict) -> dict:
    """Capítulo de serie que NO es el último: el cierre tiene que adelantar la siguiente
    parte (es lo que convierte vistas en seguidores). La Parte 2 de "Que no te roben" cerró
    con "Sígueme, mañana va otro" y no dijo que venía el préstamo falso. Si Gemini lo olvida,
    se cambia ese "Sígueme…" final por "Sígueme: mañana va la Parte N, <tema corto>.".
    Va ANTES de la voz, así que se oye igual que se lee."""
    try:
        parte, total = int(plan.get("serie_parte")), int(plan.get("serie_total"))
    except (TypeError, ValueError):
        return data
    corto = (plan.get("serie_siguiente_corto") or "").strip().rstrip(".")
    if parte >= total or not corto:
        return data
    beats = [b for b in (data.get("beats") or []) if isinstance(b, dict) and b.get("narration")]
    if not beats:
        return data
    ult = beats[-1]
    texto = _sin_acentos(ult["narration"]).lower()
    sig = parte + 1
    menciona_parte = re.search(rf"\bparte\s+({sig}|{_NUM_PALABRA.get(sig, '-')})\b", texto)
    claves = [w for w in re.findall(r"[a-z0-9]+", _sin_acentos(corto).lower()) if len(w) >= 5]
    menciona_tema = any(w in texto for w in claves) and re.search(r"manana|siguiente|proxim", texto)
    if menciona_parte or menciona_tema:
        return data
    adelanto = f"Sígueme: mañana va la Parte {sig}, {corto}."
    # quita del final las frases de cierre que ya traía ("Sígueme, mañana va otro.",
    # "Y sígueme, que mañana vemos <otro tema>.") y pone el adelanto correcto
    frases = re.split(r"(?<=[.!?…])\s+", ult["narration"].strip())
    while frases and re.search(r"s[ií]gueme|ma[nñ]ana|siguiente parte|pr[oó]xim",
                               frases[-1], re.IGNORECASE):
        frases.pop()
    nuevo = " ".join(frases + [adelanto])
    print(f"    (adelanto de serie agregado: '{adelanto}')")
    ult["narration"] = nuevo.strip()
    return data


# líneas de llamado que Gemini a veces agrega solo; las quitamos para no duplicar
_CTA_VIEJO = re.compile(r"^\s*(s[ií]gueme|guarda (este|el video)|gu[aá]rdalo|comp[aá]rtelo|"
                        r"m[aá]ndaselo)\b.*$", re.IGNORECASE)


def _sin_acentos(t: str) -> str:
    t = unicodedata.normalize("NFD", t or "")
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def hashtag_serie(nombre: str) -> str:
    pals = re.findall(r"[A-Za-z0-9]+", _sin_acentos(nombre))
    return "#" + "".join(p[:1].upper() + p[1:] for p in pals) if pals else ""


def _cta_del_dia(fraude: bool = False) -> str:
    try:
        corrida = int(os.environ.get("GITHUB_RUN_NUMBER", "0"))
    except ValueError:
        corrida = 0
    lista = _CTAS_FRAUDE if fraude else _CTAS
    return lista[(datetime.date.today().toordinal() + corrida) % len(lista)]


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
    fraude = es_tema_fraude(data)
    data["tema_fraude"] = fraude
    if fraude and not es_serie:
        data = cta_hablado_fraude(data)
    if es_serie:
        data = asegurar_adelanto(data, plan)
    cta = _cta_serie(serie_nombre, parte, total) if es_serie else _cta_del_dia(fraude)
    if es_serie:
        tag = hashtag_serie(serie_nombre)
        if tag and tag.lower() not in hashtags.lower():
            hashtags = (hashtags + " " + tag).strip()
    partes = ["\n".join(cuerpo).strip(), cta]
    if hashtags:
        partes.append(hashtags)
    data["caption"] = "\n\n".join(p for p in partes if p)
    return data