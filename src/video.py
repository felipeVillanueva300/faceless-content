import os
import shutil
import subprocess

FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")
WATERMARK = os.environ.get("WATERMARK_TEXT", "@dinerosimple.mx")
SUB_FONT = os.environ.get("SUB_FONT", "DejaVu Sans")

BG_TARGET_LUMA = float(os.environ.get("BG_TARGET_LUMA", "105"))
BG_VIGNETTE = os.environ.get("BG_VIGNETTE", "PI/5").strip()


def _escape_drawtext(txt: str) -> str:
    return (txt.replace("\\", "\\\\")
               .replace(":", "\\:")
               .replace("'", "\\'")
               .replace("%", "\\\\%"))


def _measure_luma(path: str):
    """Devuelve el brillo promedio (0-255) de los primeros ~2s del clip, o None."""
    try:
        p = subprocess.run(
            [FFMPEG, "-hide_banner", "-i", path,
             "-vf", "select='lt(t\\,2)',signalstats,metadata=print",
             "-an", "-f", "null", "-"],
            capture_output=True, text=True, timeout=90,
        )
        salida = (p.stderr or "") + (p.stdout or "")
        vals = []
        for line in salida.splitlines():
            if "signalstats.YAVG=" in line:
                try:
                    vals.append(float(line.split("signalstats.YAVG=")[1].split()[0]))
                except Exception:
                    pass
        if vals:
            return sum(vals) / len(vals)
    except Exception as e:
        print(f"    (no se pudo medir brillo del b-roll: {e})")
    return None


def _brightness_delta(bg_video: str) -> float:
    """Calcula el ajuste de brillo (rango eq: -1..1) para acercar el clip al objetivo."""
    yavg = _measure_luma(bg_video)
    if yavg is None:
        return -0.06
    delta = (BG_TARGET_LUMA - yavg) / 255.0
    delta = max(-0.15, min(0.22, delta))
    print(f"    brillo b-roll YAVG={yavg:.0f} -> eq brightness={delta:+.3f}")
    return delta


MUSIC_DIR = os.environ.get("MUSIC_DIR", "assets/music")
MUSIC_VOLUME = os.environ.get("MUSIC_VOLUME", "0.12")


def _pick_music():
    """Elige al azar una pista de assets/music/. Si no hay carpeta o está vacía,
    devuelve None y el video sale solo con la voz (sin romperse)."""
    import glob
    import random
    if not os.path.isdir(MUSIC_DIR):
        return None
    files = []
    for ext in ("*.mp3", "*.m4a", "*.wav", "*.ogg"):
        files += glob.glob(os.path.join(MUSIC_DIR, ext))
    return random.choice(files) if files else None


def build_video(audio_path, ass_path, out_path, bg_video=None, cards=None,
                graphics=None, duration=None):
    """cards: lista opcional de dicts {'big': '70%', 'small': 'texto', 'start': s, 'end': s}.
    graphics: lista opcional de dicts {'pattern': ruta_%05d.png, 'start': s, 'end': s, 'fps': n}.
    duration: si se pasa, corta la salida a esos segundos (en vez de -shortest)."""
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
        delta = _brightness_delta(bg_video)
        vig = f",vignette={BG_VIGNETTE}" if BG_VIGNETTE and BG_VIGNETTE != "0" else ""
        base = (
            "[0:v]scale=1188:2112:force_original_aspect_ratio=increase,crop=1188:2112,"
            f"eq=brightness={delta:.3f}:contrast=1.06:saturation=1.12{vig},setsar=1,"
            "crop=1080:1920:x='(in_w-out_w)/2+40*sin(t/5)':y='(in_h-out_h)/2+50*sin(t/7)'[bg]"
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

    graphics = graphics or []
    for gi, g in enumerate(graphics):
        inputs += ["-itsoffset", f"{g['start']}", "-framerate", str(g.get("fps", 30)),
                   "-i", g["pattern"]]
    for gi, g in enumerate(graphics):
        idx = 2 + gi 
        chain.append(
            f"[{last}][{idx}:v]overlay=0:0:"
            f"enable='between(t,{g['start']},{g['end']})':eof_action=pass[g{gi}]"
        )
        last = f"g{gi}"

    chain.append(f"[{last}]subtitles={subs}[subd]")
    last = "subd"

    wm = _escape_drawtext(WATERMARK)
    chain.append(
        f"[{last}]drawtext=font='{SUB_FONT}':text='{wm}':fontcolor=white@0.75:"
        f"fontsize=40:borderw=3:bordercolor=black@0.6:x=40:y=h-90[v]"
    )

    vf = ";".join(chain)

    music = _pick_music()
    audio_map = "1:a"
    if music:
        music_idx = 2 + len(graphics)
        inputs += ["-stream_loop", "-1", "-i", os.path.abspath(music)]
        amix = (f"[{music_idx}:a]volume={MUSIC_VOLUME}[bgm];"
                f"[1:a][bgm]amix=inputs=2:duration=first:normalize=0[amixed]")
        if duration:
            fade_st = max(0.0, float(duration) - 1.2)
            amix += f";[amixed]afade=t=out:st={fade_st:.2f}:d=1.2[aout]"
            audio_map = "[aout]"
        else:
            audio_map = "[amixed]"
        vf = vf + ";" + amix
        print(f"    música de fondo: {os.path.basename(music)} (vol {MUSIC_VOLUME})")

    tail = ["-t", f"{duration:.2f}"] if duration else ["-shortest"]
    cmd = [
        FFMPEG, "-y",
        *inputs,
        "-filter_complex", vf,
        "-map", "[v]", "-map", audio_map,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        *tail, "-movflags", "+faststart",
        out,
    ]
    subprocess.run(cmd, check=True, cwd=work_dir)