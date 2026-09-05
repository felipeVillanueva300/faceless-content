"""Genera subtítulos .ass estilizados y sincronizados.

Dos caminos:
- Si edge-tts devolvió 'word boundaries' (tiempos por palabra), los usa (sync exacto).
- Si vienen vacíos (pasa en algunos Windows), reparte el texto de forma pareja
  sobre la duración real del audio (medida con ffprobe). Así SIEMPRE hay subtítulos.
"""
import os
import subprocess

FONT = os.environ.get("SUB_FONT", "DejaVu Sans")


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
Style: Default,{font},90,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,3,5,120,120,0,1

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
        return 30.0  # respaldo razonable si ffprobe falla


def _cues_from_boundaries(boundaries, words_per_cue):
    cues = []
    for i in range(0, len(boundaries), words_per_cue):
        group = boundaries[i:i + words_per_cue]
        if not group:
            continue
        start = group[0][0] / 1e7
        end = (group[-1][0] + group[-1][1]) / 1e7
        cues.append((start, end, " ".join(w[2] for w in group)))
    return cues


def _cues_from_text(text, duration, words_per_cue):
    words = text.split()
    groups = [words[i:i + words_per_cue] for i in range(0, len(words), words_per_cue)]
    total = sum(len(" ".join(g)) for g in groups) or 1
    cues, t = [], 0.0
    for g in groups:
        span = duration * (len(" ".join(g)) / total)
        cues.append((t, t + span, " ".join(g)))
        t += span
    return cues


def build_ass(text, boundaries, ass_path, audio_path, words_per_cue: int = 4):
    if boundaries:
        cues = _cues_from_boundaries(boundaries, words_per_cue)
    else:
        cues = _cues_from_text(text, _audio_duration(audio_path), words_per_cue)

    lines = [_header(FONT)]
    for start, end, txt in cues:
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{txt.upper()}"
        )
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))