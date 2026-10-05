import os
import re
import subprocess

FONT = os.environ.get("SUB_FONT", "DejaVu Sans")
WORDS_PER_CUE = int(os.environ.get("WORDS_PER_CUE", "4"))

SUB_ALIGN = os.environ.get("SUB_ALIGN", "2")
SUB_MARGIN_V = os.environ.get("SUB_MARGIN_V", "300")

COL_BASE = os.environ.get("SUB_COLOR", "&H00FFFFFF")   
COL_HL = os.environ.get("SUB_HL_COLOR", "&H0000E5FF")  

_QUITAR = str.maketrans("", "", "'\"‘’“”«»`´{}\\")


def _limpio(txt: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFC", txt or "")
    t = "".join(" " if unicodedata.category(c) == "Zs" else c for c in t)
    t = "".join(c for c in t if unicodedata.category(c) not in ("Mn", "Cf", "Cc"))
    return " ".join(t.translate(_QUITAR).split())


def _ass_time(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _header(font: str) -> str:
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},90,{COL_BASE},&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,{SUB_ALIGN},120,120,{SUB_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ffprobe_bin() -> str:
    ff = os.environ.get("FFMPEG_BIN", "")
    if ff and os.path.isfile(ff):
        cand = os.path.join(os.path.dirname(ff), "ffprobe.exe")
        if os.path.isfile(cand):
            return cand
    return "ffprobe"


def _audio_duration(audio_path: str) -> float:
    try:
        out = subprocess.run(
            [_ffprobe_bin(), "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except Exception:
        return 30.0


_DEBILES = {
    "a", "al", "ante", "con", "contra", "de", "del", "desde", "en", "entre", "hacia", "hasta",
    "para", "por", "segun", "sin", "sobre", "tras", "el", "la", "los", "las", "lo", "un", "una",
    "unos", "unas", "y", "e", "o", "u", "ni", "que", "si", "tu", "tus", "su", "sus", "mi", "mis",
    "se", "te", "me", "le", "les", "nos", "cada", "muy", "mas", "no", "como", "cuando", "donde",
    "porque", "pero", "este", "esta", "estos", "estas", "ese", "esa", "tan",
    "parte",
}
_FIN_FUERTE = (".", "?", "!", "…", ";", ":")
MAX_CHARS_CUE = int(os.environ.get("SUB_MAX_CHARS", "26"))


def _base(palabra: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", (palabra or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t.strip("¿?¡!.,;:…\"'()«»")


def _debil(palabra: str) -> bool:
    """True si la palabra NO puede cerrar un subtítulo (preposición, artículo, 'tu'...).
    Si trae puntuación al final ('tu,'), sí puede: ahí la voz hace pausa."""
    p = (palabra or "").rstrip("\"'»)")
    if p.endswith(_FIN_FUERTE + (",",)):
        return False
    return _base(p) in _DEBILES


def _costo_grupo(pals, maxw):
    n = len(pals)
    c = 0.0
    if n > maxw:
        c += (2.0 if len(" ".join(pals)) <= 20 else 6.0) * (n - maxw)
    elif n == 2:
        c += 2.0
    elif n == 1:
        c += 7.0
    largo = len(" ".join(pals))
    if largo > MAX_CHARS_CUE:
        c += 0.5 * (largo - MAX_CHARS_CUE)
    c += 3.0 * sum(1 for w in pals[:-1] if w.endswith(","))
    if _debil(pals[-1]):
        c += 9.0
    return c


_PEGADOS = {"artificial", "movil", "minimo", "minima", "comun", "digital", "personal",
            "bancaria", "bancario", "financiera", "financiero", "social", "fiscal", "real",
            "total", "segura", "seguro", "falso", "falsa", "falsos", "falsas", "oficial",
            "sospechosa", "sospechoso", "cotizadas", "exactas"}


def _costo_corte(pals, j):
    """Costo de cortar ENTRE pals[j-1] y pals[j]."""
    if j >= len(pals) or pals[j - 1].rstrip("\"'»)").endswith(_FIN_FUERTE + (",",)):
        return 0.0
    sig = _base(pals[j])
    if sig in _PEGADOS:
        return 5.0
    # "PARTE 1 / DE 5": un número seguido de "de" + número va junto
    if re.match(r"\d", _base(pals[j - 1])) and sig == "de" and j + 1 < len(pals) \
            and re.match(r"\d", _base(pals[j + 1])):
        return 9.0
    return 0.0


def _partir_clausula(pals, maxw):
    """Programación dinámica: el reparto de la cláusula en grupos con menor costo."""
    n = len(pals)
    inf = float("inf")
    mejor, previo = [0.0] + [inf] * n, [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(max(0, j - (maxw + 2)), j):
            c = mejor[i] + _costo_grupo(pals[i:j], maxw) + _costo_corte(pals, j)
            if c < mejor[j]:
                mejor[j], previo[j] = c, i
    cortes, j = [], n
    while j > 0:
        cortes.append((previo[j], j))
        j = previo[j]
    return cortes[::-1]


def agrupar(palabras, maxw=None):
    """Lista de palabras -> lista de (inicio, fin) para cada subtítulo.
    1) Corta SIEMPRE después de punto, pregunta, exclamación, ';' o ':' y antes de '¿'/'¡'.
    2) Dentro de cada cláusula reparte en grupos de hasta WORDS_PER_CUE palabras, parejos,
       prefiriendo cortar en comas y sin dejar una preposición/artículo colgando al final."""
    maxw = maxw or WORDS_PER_CUE
    clausulas, ini = [], 0
    for k, w in enumerate(palabras):
        sig = palabras[k + 1] if k + 1 < len(palabras) else ""
        if w.rstrip("\"'»)").endswith(_FIN_FUERTE) or sig[:1] in ("¿", "¡"):
            clausulas.append((ini, k + 1))
            ini = k + 1
    if ini < len(palabras):
        clausulas.append((ini, len(palabras)))
    grupos = []
    for a, b in clausulas:
        for i, j in _partir_clausula(palabras[a:b], maxw):
            grupos.append((a + i, a + j))
    return grupos


def _animated_lines_from_boundaries(boundaries):
    """Una línea Dialogue por palabra activa: muestra el grupo con esa palabra
    resaltada, durante el intervalo en que se pronuncia."""
    lines = []
    for gi, gj in agrupar([b[2] for b in boundaries]):
        group = boundaries[gi:gj]
        if not group:
            continue
        words = [_limpio(w[2]).upper() for w in group]
        for j, w in enumerate(group):
            start = w[0] / 1e7
            end = (w[0] + w[1]) / 1e7
            partes = []
            for k, palabra in enumerate(words):
                if k == j:
                    partes.append(f"{{\\1c{COL_HL}&}}{palabra}{{\\1c{COL_BASE}&}}")
                else:
                    partes.append(palabra)
            texto = " ".join(partes)
            lines.append(
                f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{texto}"
            )
    return lines


_UNIDADES = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
             "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
             "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
             "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho",
             "veintinueve"]
_DECENAS = ["", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta",
            "noventa"]
_CENTENAS = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos",
             "seiscientos", "setecientos", "ochocientos", "novecientos"]


def _num_a_palabras(n: int) -> str:
    """Número entero -> cómo lo dice la voz en español (solo para estimar duración)."""
    if n == 0:
        return "cero"
    if n >= 1_000_000:
        m, r = divmod(n, 1_000_000)
        return ("un millón" if m == 1 else _num_a_palabras(m) + " millones") + \
               (" " + _num_a_palabras(r) if r else "")
    if n >= 1000:
        m, r = divmod(n, 1000)
        return ("mil" if m == 1 else _num_a_palabras(m) + " mil") + \
               (" " + _num_a_palabras(r) if r else "")
    if n == 100:
        return "cien"
    c, r = divmod(n, 100)
    partes = [_CENTENAS[c]] if c else []
    if r < 30:
        if r:
            partes.append(_UNIDADES[r])
    else:
        d, u = divmod(r, 10)
        partes.append(_DECENAS[d] + (" y " + _UNIDADES[u] if u else ""))
    return " ".join(partes)


def _cifra_hablada(token: str) -> str:
    """'$8,000' -> 'ocho mil pesos'; '6.15%' -> 'seis punto quince por ciento';
    '91,' -> 'noventa y uno'. Si no hay cifra, devuelve el token tal cual."""
    import re
    if not re.search(r"\d", token):
        return token
    t = token.strip("¿?¡!.,;:()\"'")
    extra = []
    if t.startswith("$"):
        extra.append("pesos")
    if t.endswith("%"):
        extra.append("por ciento")
    t = t.strip("$%")
    ent, _, dec = t.replace(",", "").partition(".")
    try:
        dicho = _num_a_palabras(int(ent)) if ent else ""
        if dec.isdigit():
            dicho += " punto " + _num_a_palabras(int(dec))
    except ValueError:
        return token
    return " ".join([dicho] + extra)


def _silabas(palabra: str) -> int:
    """Cuenta sílabas aprox. en español: grupos de vocales (diptongos = 1).
    Es una buena aproximación de cuánto DURA una palabra al hablarse, mucho
    mejor que contar letras (que infla palabras con muchas consonantes).
    Las CIFRAS se cuentan como se DICEN: "364" = "trescientos sesenta y cuatro"
    (antes valían 0 y el subtítulo "91, 182 O 364" duraba 0.3 s contra ~4 s de voz)."""
    import re
    if re.search(r"\d", palabra):
        return sum(_silabas(w) for w in _cifra_hablada(palabra).split()) or 1
    p = palabra.lower()
    p = re.sub(r"[^a-záéíóúüñ]", "", p)
    if not p:
        return 0
    grupos = re.findall(r"[aeiouáéíóúü]+", p)
    return max(1, len(grupos))


def _static_lines_from_text(text, duration):
    """Reparte los subtítulos por el audio SIN tiempos de palabra reales, estimando
    la duración de cada grupo por sus SÍLABAS (+ una pausa extra si termina en signo).
    Deja un pequeño respiro inicial para que no arranque antes que la voz."""
    pals = text.split()
    groups = [pals[i:j] for i, j in agrupar(pals)]

    def peso(g):
        sil = sum(_silabas(w) for w in g) or 1
        # pausa extra por puntuación final (punto pesa más que coma)
        fin = g[-1][-1:] if g else ""
        pausa = 2.0 if fin in ".?!" else (1.0 if fin in ",;:" else 0.0)
        return sil + pausa

    total = sum(peso(g) for g in groups) or 1
    # pequeño offset inicial (la voz no arranca en el frame 0)
    lead = min(0.25, duration * 0.02)
    disp = max(0.1, duration - lead)

    lines, t = [], lead
    for g in groups:
        span = disp * (peso(g) / total)
        txt = _limpio(" ".join(g)).upper()
        lines.append(
            f"Dialogue: 0,{_ass_time(t)},{_ass_time(t + span)},Default,,0,0,0,,{txt}"
        )
        t += span
    return lines


def build_ass(text, boundaries, ass_path, audio_path, words_per_cue: int = None):
    if boundaries:
        body = _animated_lines_from_boundaries(boundaries)
    else:
        body = _static_lines_from_text(text, _audio_duration(audio_path))

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(_header(FONT) + "\n".join(body))

def _cues_en_ventana(texto, t0, t1):
    """Reparte el texto de UN bloque en subtítulos dentro de [t0, t1] (su tiempo real
    medido), pesando por sílabas. Como cada bloque tiene su propia ventana, el desfase
    no se acumula de un bloque a otro."""
    pals = (texto or "").split()
    if not pals:
        return []
    grupos = [pals[i:j] for i, j in agrupar(pals)]

    def peso(g):
        sil = sum(_silabas(w) for w in g) or 1
        fin = g[-1][-1:] if g else ""
        pausa = 2.0 if fin in ".?!" else (1.0 if fin in ",;:" else 0.0)
        return sil + pausa

    total = sum(peso(g) for g in grupos) or 1
    span_total = max(0.1, t1 - t0)
    lines, t = [], t0
    for g in grupos:
        span = span_total * (peso(g) / total)
        txt = _limpio(" ".join(g)).upper()
        lines.append(
            f"Dialogue: 0,{_ass_time(t)},{_ass_time(t + span)},Default,,0,0,0,,{txt}"
        )
        t += span
    return lines


def build_ass_segments(segmentos, ass_path):
    """segmentos: lista de (texto, inicio_seg, fin_seg) — un bloque de narración con su
    ventana de tiempo REAL. Genera el .ass con los subtítulos de cada bloque acomodados
    dentro de su ventana. Es lo que sincroniza voz y texto sin depender de edge-tts."""
    body = []
    for texto, t0, t1 in segmentos:
        body.extend(_cues_en_ventana(texto, t0, t1))
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(_header(FONT) + "\n".join(body))
    return ass_path