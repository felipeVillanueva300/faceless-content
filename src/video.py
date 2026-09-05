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


def build_video(audio_path: str, ass_path: str, out_path: str):
    if shutil.which(FFMPEG) is None and not os.path.isfile(FFMPEG):
        raise FileNotFoundError(
            "No se encontró FFmpeg. Instálalo con 'winget install -e --id Gyan.FFmpeg' "
            "y abre una terminal NUEVA, o define FFMPEG_BIN con la ruta completa a ffmpeg.exe."
        )

    work_dir = os.path.dirname(os.path.abspath(ass_path)) or "."
    audio = os.path.basename(audio_path)
    subs = os.path.basename(ass_path)
    out = os.path.basename(out_path)

    bg = os.environ.get("BG_VIDEO", "").strip()
    if bg:
        inputs = ["-stream_loop", "-1", "-i", bg, "-i", audio]
        vf = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,subtitles={subs}[v]"
        )
    else:
        c0 = os.environ.get("BG_C0", "0x1B3A5C")  # azul marino (arriba-izq)
        c1 = os.environ.get("BG_C1", "0x070B12")  # casi negro (abajo-der)
        grad = (
            f"gradients=s=1080x1920:c0={c0}:c1={c1}"
            ":x0=0:y0=0:x1=1080:y1=1920:speed=0.008:rate=30"
        )
        inputs = ["-f", "lavfi", "-i", grad, "-i", audio]
        vf = f"[0:v]subtitles={subs}[v]"

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