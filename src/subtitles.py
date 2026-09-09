import os
import subprocess

FONT = os.environ.get("SUB_FONT", "DejaVu Sans")
WORDS_PER_CUE = int(os.environ.get("WORDS_PER_CUE", "4"))

SUB_ALIGN = os.environ.get("SUB_ALIGN", "2")
SUB_MARGIN_V = os.environ.get("SUB_MARGIN_V", "300")

COL_BASE = os.environ.get("SUB_COLOR", "&H00FFFFFF")   
COL_HL = os.environ.get("SUB_HL_COLOR", "&H0000E5FF")  

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
        words = [w[2].upper() for w in group]
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


def _static_lines_from_text(text, duration):
    import re
    oraciones = [s for s in re.split(r'(?<=[\.\?\!])\s+', text.strip()) if s]
    groups = []
    for s in oraciones:
        pals = s.split()
        for i in range(0, len(pals), WORDS_PER_CUE):
            groups.append(pals[i:i + WORDS_PER_CUE])

    def peso(g):
        base = len(" ".join(g))
        pausa = 6 if g and g[-1][-1:] in ".,;:?!" else 0
        return base + pausa

    total = sum(peso(g) for g in groups) or 1
    lines, t = [], 0.0
    for g in groups:
        span = duration * (peso(g) / total)
        txt = " ".join(g).upper()
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