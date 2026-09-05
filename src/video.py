"""Arma el video vertical 1080x1920 con FFmpeg: fondo + subtítulos quemados + audio.

Fondo por defecto: degradado azul marino (se ve bien y el texto blanco resalta).
- Colores configurables con BG_C0 (arriba-izq) y BG_C1 (abajo-der), formato 0xRRGGBB.
- Si defines BG_VIDEO con la ruta a un video loop, lo usa como fondo recortado a 9:16.

Si FFmpeg no está en el PATH, apunta al ejecutable con FFMPEG_BIN.
"""
import os
import shutil
import subprocess

FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")
WATERMARK = os.environ.get("WATERMARK_TEXT", "@villanuevagallegosf")
SUB_FONT = os.environ.get("SUB_FONT", "DejaVu Sans")
 
 

def _escape_drawtext(txt: str) -> str:
    return (txt.replace("\\", "\\\\")
               .replace(":", "\\:")
               .replace("'", "\\'")
               .replace("%", "\\\\%"))
 
 
def build_video(audio_path, ass_path, out_path, bg_video=None, cards=None):
    """cards: lista opcional de dicts {'big': '70%', 'small': 'texto', 'start': s, 'end': s}."""
    if shutil.which(FFMPEG) is None and not os.path.isfile(FFMPEG):
        raise FileNotFoundError(
            "No se encontró FFmpeg. Instálalo con 'winget install -e --id Gyan.FFmpeg' "
            "y abre una terminal NUEVA, o define FFMPEG_BIN con la ruta completa a ffmpeg.exe."
        )
 
    work_dir = os.path.dirname(os.path.abspath(ass_path)) or "."
    audio = os.path.basename(audio_path)
    subs = os.path.basename(ass_path)
    out = os.path.basename(out_path)
 
    if bg_video:
        bg = os.path.basename(bg_video)
        inputs = ["-stream_loop", "-1", "-i", bg, "-i", audio]
        base = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,eq=brightness=-0.12:saturation=1.05,setsar=1[bg]"
        )
    else:
        c0 = os.environ.get("BG_C0", "0x1B3A5C")
        c1 = os.environ.get("BG_C1", "0x070B12")
        grad = (f"gradients=s=1080x1920:c0={c0}:c1={c1}"
                ":x0=0:y0=0:x1=1080:y1=1920:speed=0.008:rate=30")
        inputs = ["-f", "lavfi", "-i", grad, "-i", audio]
        base = "[0:v]setsar=1[bg]"
 
    chain = [base]
    last = "bg"
 
    for i, card in enumerate(cards or []):
        big = _escape_drawtext(str(card.get("big", "")))
        small = _escape_drawtext(str(card.get("small", "")))
        st, en = float(card["start"]), float(card["end"])
      
        chain.append(
            f"[{last}]drawtext=font='{SUB_FONT}':text='{big}':fontcolor=0x00E5FF:"
            f"fontsize=170:borderw=6:bordercolor=black:x=(w-tw)/2:y=h*0.20:"
            f"enable='between(t,{st},{en})'[c{i}a]"
        )
        chain.append(
            f"[c{i}a]drawtext=font='{SUB_FONT}':text='{small}':fontcolor=white:"
            f"fontsize=52:borderw=4:bordercolor=black:x=(w-tw)/2:y=h*0.34:"
            f"enable='between(t,{st},{en})'[c{i}b]"
        )
        last = f"c{i}b"
 
    chain.append(f"[{last}]subtitles={subs}[subd]")
    last = "subd"
 
    wm = _escape_drawtext(WATERMARK)
    chain.append(
        f"[{last}]drawtext=font='{SUB_FONT}':text='{wm}':fontcolor=white@0.75:"
        f"fontsize=40:borderw=3:bordercolor=black@0.6:x=40:y=h-90[v]"
    )
 
    vf = ";".join(chain)
 
    cmd = [
        FFMPEG, "-y",
        *inputs,
        "-filter_complex", vf,
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        out,
    ]
    subprocess.run(cmd, check=True, cwd=work_dir)