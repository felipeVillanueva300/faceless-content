import os
import shutil
import subprocess

FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")

VIDEO_CRF = os.environ.get("VIDEO_CRF", "18")
VIDEO_PRESET = os.environ.get("VIDEO_PRESET", "medium")
VIDEO_MAXRATE = os.environ.get("VIDEO_MAXRATE", "12M")
_ENC_FINAL = [
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", VIDEO_PRESET, "-crf", VIDEO_CRF,
    "-profile:v", "high", "-level", "4.1", "-r", "30", "-g", "60",
    "-maxrate", VIDEO_MAXRATE, "-bufsize", "24M",
]
_ENC_INTER = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "14"]
WATERMARK = os.environ.get("WATERMARK_TEXT", "@dinerosimple.mx")
SUB_FONT = os.environ.get("SUB_FONT", "DejaVu Sans")

BG_TARGET_LUMA = float(os.environ.get("BG_TARGET_LUMA", "105"))
BG_VIGNETTE = os.environ.get("BG_VIGNETTE", "PI/5").strip()

CARD_MAX_W = int(os.environ.get("CARD_MAX_W", "940"))

CARD_SHOW_SMALL = os.environ.get("CARD_SHOW_SMALL", "1").strip().lower() in ("1", "true", "yes")

HOOK_DUR = float(os.environ.get("HOOK_DUR", "2.8"))

OUTRO_CTA = os.environ.get("OUTRO_CTA", "SÍGUEME").strip()
OUTRO_SUB = os.environ.get("OUTRO_SUB", "uno nuevo cada día").strip()
OUTRO_DUR = float(os.environ.get("OUTRO_DUR", "3.0"))

_FIT_FONT_CANDIDATES = [
    os.environ.get("IMG_FONT_FILE", ""),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\Arial.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def _fit_fontsize(text: str, max_w: int, start: int, minimum: int) -> int:
    """Devuelve el fontsize (<= start, >= minimum) con el que 'text' cabe en max_w px.
    Usa Pillow si hay una fuente .ttf; si no, cae a una estimación por caracteres."""
    text = (text or "").strip()
    if not text:
        return start
    path = next((p for p in _FIT_FONT_CANDIDATES if p and os.path.isfile(p)), None)
    if path:
        try:
            from PIL import ImageFont
            size = start
            while size > minimum:
                if ImageFont.truetype(path, size).getlength(text) <= max_w:
                    return size
                size -= 4
            return minimum
        except Exception:
            pass
    size = start
    while size > minimum and 0.62 * size * len(text) > max_w:
        size -= 4
    return size


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
MUSIC_VOLUME = os.environ.get("MUSIC_VOLUME", "0.17")


def _pick_music():
    """Elige una pista de assets/music/ ROTANDO: recorre todas antes de repetir.
    El índice sale de la fecha (2 turnos por día: mañana y tarde), así el diario y la
    miniserie no llevan la misma y no se necesita guardar estado.
    Si no hay carpeta o está vacía, devuelve None (video solo con voz)."""
    import glob
    import datetime
    if not os.path.isdir(MUSIC_DIR):
        return None
    files = []
    for ext in ("*.mp3", "*.m4a", "*.wav", "*.ogg"):
        files += glob.glob(os.path.join(MUSIC_DIR, ext))
    if not files:
        return None
    files.sort()
    ahora = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=6)  # CDMX
    turno = 1 if ahora.hour >= 15 else 0
    return files[(ahora.date().toordinal() * 2 + turno) % len(files)]


def build_video(audio_path, ass_path, out_path, bg_video=None, cards=None,
                graphics=None, duration=None, hook=None):
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

    if hook:
        raw_hook = str(hook).strip().upper()
        hook_fs = _fit_fontsize(raw_hook, CARD_MAX_W, 130, 64)
        htxt = _escape_drawtext(raw_hook)
        # entra deslizándose desde abajo + fade in; hace fade out al final
        yexpr = "h*0.30+80*(1-min(t/0.45,1))"
        alpha = (f"if(lt(t,0.35),t/0.35,"
                 f"if(gt(t,{HOOK_DUR - 0.3:.2f}),max(0,({HOOK_DUR:.2f}-t)/0.3),1))")
        chain.append(
            f"[{last}]drawtext=font='{SUB_FONT}':text='{htxt}':fontcolor=0x00E5FF:"
            f"fontsize={hook_fs}:borderw=9:bordercolor=black:shadowcolor=black@0.6:"
            f"shadowx=4:shadowy=4:x=(w-tw)/2:y='{yexpr}':alpha='{alpha}':"
            f"enable='between(t,0,{HOOK_DUR:.2f})'[hook]"
        )
        last = "hook"

    for i, card in enumerate(cards or []):
        raw_big = str(card.get("big", ""))
        raw_small = str(card.get("small", ""))
        big_fs = _fit_fontsize(raw_big, CARD_MAX_W, 170, 70)
        small_fs = _fit_fontsize(raw_small, CARD_MAX_W, 52, 34)
        big = _escape_drawtext(raw_big)
        small = _escape_drawtext(raw_small)
        st, en = float(card["start"]), float(card["end"])

        chain.append(
            f"[{last}]drawtext=font='{SUB_FONT}':text='{big}':fontcolor=0x00E5FF:"
            f"fontsize={big_fs}:borderw=6:bordercolor=black:x=(w-tw)/2:y=h*0.20:"
            f"enable='between(t,{st},{en})'[c{i}a]"
        )
        last = f"c{i}a"

        if CARD_SHOW_SMALL and raw_small.strip():
            chain.append(
                f"[{last}]drawtext=font='{SUB_FONT}':text='{small}':fontcolor=white:"
                f"fontsize={small_fs}:borderw=4:bordercolor=black:x=(w-tw)/2:y=h*0.34:"
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

    if OUTRO_CTA and duration:
        oc_st = max(0.0, float(duration) - OUTRO_DUR)
        oc_alpha = (f"if(lt(t,{oc_st:.2f}),0,"
                    f"if(lt(t,{oc_st + 0.3:.2f}),(t-{oc_st:.2f})/0.3,1))")
        big_txt = _escape_drawtext(OUTRO_CTA.upper())
        big_fs = _fit_fontsize(OUTRO_CTA.upper(), CARD_MAX_W, 150, 90)
        chain.append(
            f"[{last}]drawtext=font='{SUB_FONT}':text='{big_txt}':fontcolor=0x00E5FF:"
            f"fontsize={big_fs}:borderw=8:bordercolor=black:shadowcolor=black@0.6:"
            f"shadowx=4:shadowy=4:x=(w-tw)/2:y=h*0.40:alpha='{oc_alpha}':"
            f"enable='between(t,{oc_st:.2f},{float(duration):.2f})'[octa]"
        )
        last = "octa"
        if OUTRO_SUB:
            sub_txt = _escape_drawtext(OUTRO_SUB)
            sub_fs = _fit_fontsize(OUTRO_SUB, CARD_MAX_W, 58, 40)
            chain.append(
                f"[{last}]drawtext=font='{SUB_FONT}':text='{sub_txt}':fontcolor=white:"
                f"fontsize={sub_fs}:borderw=4:bordercolor=black:x=(w-tw)/2:"
                f"y=h*0.40+{big_fs + 24}:alpha='{oc_alpha}':"
                f"enable='between(t,{oc_st:.2f},{float(duration):.2f})'[octb]"
            )
            last = "octb"

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
        *_ENC_FINAL,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        *tail, "-movflags", "+faststart",
        out,
    ]
    subprocess.run(cmd, check=True, cwd=work_dir)


def build_multi_background(clips, duration, out_path, durations=None):
    """Une varios clips en UN fondo vertical 1080x1920 de largo 'duration', cortando
    entre clips. Devuelve out_path, o None si no se puede (cae al fondo degradado).

    'durations': si se pasa (una por clip), cada clip dura EXACTAMENTE eso — así el fondo
    cambia justo cuando la voz pasa a ese bloque. Si no, se reparte en partes iguales.

    Cada clip se escala a cubrir 1080x1920 (sin barras), se recorta y se hace loop si es
    más corto que su segmento. No lleva audio."""
    clips = [c for c in (clips or []) if c and os.path.isfile(c)]
    if not clips:
        return None
    if len(clips) == 1:
        return clips[0]   # un solo clip: el pipeline normal ya lo maneja

    n = len(clips)
    # duraciones por clip: explícitas (medidas de la voz) o partes iguales
    if durations and len(durations) == n:
        segs = [max(0.5, float(d)) for d in durations]
    else:
        segs = [max(1.0, float(duration) / n)] * n

    inputs = []
    for c in clips:
        inputs += ["-stream_loop", "-1", "-i", os.path.basename(c)]

    parts, labels = [], []
    for i in range(n):
        labels.append(f"[v{i}]")
        parts.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,fps=30,trim=0:{segs[i]:.3f},setpts=PTS-STARTPTS[v{i}]"
        )
    concat = "".join(labels) + f"concat=n={n}:v=1:a=0[bg]"
    filtro = ";".join(parts + [concat])

    work_dir = os.path.dirname(os.path.abspath(out_path)) or "."
    cmd = [
        FFMPEG, "-y",
        *inputs,
        "-filter_complex", filtro,
        "-map", "[bg]",
        "-t", f"{sum(segs):.2f}",
        *_ENC_INTER,
        "-an", os.path.basename(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, cwd=work_dir,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        segdesc = "exacto por bloque" if (durations and len(durations) == n) else f"{segs[0]:.1f}s c/u"
        print(f"    fondo multi-escena armado con {n} clips ({segdesc})")
        return out_path
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode("utf-8", "ignore")[-300:]
        print(f"    (no se pudo armar fondo multi-escena: {err}); uso el primer clip")
        return clips[0]


def image_to_clip(img_path, out_path, seconds=10.0):
    """Convierte una imagen fija en un clip vertical 1080x1920 con zoom lento
    (efecto Ken Burns), para que un fondo generado por IA se sienta vivo. Devuelve
    out_path o None si falla."""
    if not (img_path and os.path.isfile(img_path)):
        return None
    frames = max(30, int(seconds * 30))
    work_dir = os.path.dirname(os.path.abspath(out_path)) or "."
    vf = (
        "scale=1350:2400:force_original_aspect_ratio=increase,crop=1350:2400,"
        f"zoompan=z='min(zoom+0.0005,1.18)':d={frames}:"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,setsar=1"
    )
    cmd = [
        FFMPEG, "-y", "-loop", "1", "-i", os.path.basename(img_path),
        "-t", f"{seconds:.2f}", "-vf", vf,
        *_ENC_INTER,
        "-an", os.path.basename(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, cwd=work_dir,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return out_path
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode("utf-8", "ignore")[-200:]
        print(f"    (image_to_clip falló: {err})")
        return None