import os
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


def _animated_lines_from_boundaries(boundaries):
    """Una línea Dialogue por palabra activa: muestra el grupo con esa palabra
    resaltada, durante el intervalo en que se pronuncia."""
    lines = []
    for i in range(0, len(boundaries), WORDS_PER_CUE):
        group = boundaries[i:i + WORDS_PER_CUE]
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


def _silabas(palabra: str) -> int:
    """Cuenta sílabas aprox. en español: grupos de vocales (diptongos = 1).
    Es una buena aproximación de cuánto DURA una palabra al hablarse, mucho
    mejor que contar letras (que infla palabras con muchas consonantes)."""
    import re
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
    import re
    oraciones = [s for s in re.split(r'(?<=[\.\?\!])\s+', text.strip()) if s]
    groups = []
    for s in oraciones:
        pals = s.split()
        for i in range(0, len(pals), WORDS_PER_CUE):
            groups.append(pals[i:i + WORDS_PER_CUE])

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
    grupos = [pals[i:i + WORDS_PER_CUE] for i in range(0, len(pals), WORDS_PER_CUE)]

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