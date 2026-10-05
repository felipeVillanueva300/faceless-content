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


# Volumen final estándar de Reels/Shorts/TikTok (~-14 LUFS). Antes salía a ~-19 LUFS
# y se oía bajito junto a otros videos. "0"/"off" lo apaga.
AUDIO_LUFS = os.environ.get("AUDIO_LUFS", "-14").strip()


def _loudnorm():
    if AUDIO_LUFS.lower() in ("", "0", "off", "no", "false"):
        return ""
    try:
        objetivo = float(AUDIO_LUFS)
    except ValueError:
        objetivo = -14.0
    return f"loudnorm=I={objetivo:.1f}:TP=-1.5:LRA=11"


def _medir_loudnorm(path: str, objetivo: float):
    """Primera pasada de loudnorm sobre el audio del mp4 final. Devuelve el dict de
    mediciones (input_i, input_tp, input_lra, input_thresh, target_offset) o None."""
    import json
    try:
        p = subprocess.run(
            [FFMPEG, "-hide_banner", "-nostats", "-i", path, "-vn",
             "-af", f"loudnorm=I={objetivo:.1f}:TP=-1.5:LRA=11:print_format=json",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=180,
        )
        txt = p.stderr or ""
        ini, fin = txt.rfind("{"), txt.rfind("}")
        if ini < 0 or fin < 0:
            return None
        return json.loads(txt[ini:fin + 1])
    except Exception as e:
        print(f"    (no se pudo medir el volumen: {e})")
        return None


def _ajustar_volumen(out_path: str):
    """Segunda pasada: deja el video en AUDIO_LUFS (±0.5). La normalización dentro de la
    mezcla es de una sola pasada (modo dinámico) y se queda corta: el reel del 2-oct salió
    en -15.7 LUFS con objetivo -14.
    Cómo: saca el audio a WAV (sin pérdida), prueba ganancia + limitador (picos a -2 dBFS)
    midiendo hasta 3 veces, y al final lo vuelve a meter al mp4 UNA sola vez, copiando el
    video sin recomprimir. Best-effort: si algo falla, el archivo se queda como estaba."""
    if AUDIO_LUFS.lower() in ("", "0", "off", "no", "false"):
        return
    try:
        objetivo = float(AUDIO_LUFS)
    except ValueError:
        objetivo = -14.0
    m = _medir_loudnorm(out_path, objetivo)
    try:
        medido = float(m["input_i"]) if m else None
    except (KeyError, TypeError, ValueError):
        medido = None
    if medido is None:
        return
    if abs(medido - objetivo) <= 0.5:
        print(f"    volumen final {medido:.1f} LUFS (objetivo {objetivo:.0f}): OK")
        return

    base = os.path.splitext(out_path)[0]
    wav_in, wav_out, tmp = base + ".vol_in.wav", base + ".vol_out.wav", base + ".vol.mp4"
    limite = 10 ** (-2.0 / 20)
    try:
        subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", out_path,
                        "-vn", "-c:a", "pcm_s16le", wav_in], check=True, timeout=120)
        ganancia, logrado = objetivo - medido, medido
        aplicada = ganancia
        for _ in range(3):
            aplicada = ganancia
            # el limitador se come parte de la ganancia: se compensa y se vuelve a medir
            subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", wav_in,
                            "-af", f"volume={ganancia:.2f}dB,alimiter=limit={limite:.4f}:"
                                   f"attack=5:release=60:level=false",
                            "-c:a", "pcm_s16le", wav_out], check=True, timeout=120)
            mm = _medir_loudnorm(wav_out, objetivo) or {}
            logrado = float(mm.get("input_i", logrado))
            if abs(logrado - objetivo) <= 0.3:
                break
            ganancia = min(ganancia + (objetivo - logrado), 5.0)   # nunca más de +5 dB
        subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                        "-i", out_path, "-i", wav_out, "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                        "-movflags", "+faststart", tmp], check=True, timeout=300)
        os.replace(tmp, out_path)
        print(f"    volumen final ajustado: {medido:.1f} -> {logrado:.1f} LUFS "
              f"(objetivo {objetivo:.0f}, ganancia {aplicada:+.1f} dB)")
    except Exception as e:
        print(f"    (no se pudo ajustar el volumen final: {e}; se queda en {medido:.1f} LUFS)")
    finally:
        for f in (wav_in, wav_out, tmp):
            try:
                os.remove(f)
            except OSError:
                pass


MUSIC_DIR = os.environ.get("MUSIC_DIR", "assets/music")
MUSIC_VOLUME = os.environ.get("MUSIC_VOLUME", "0.17")


def _pick_music():
    """Elige una pista de assets/music/ ROTANDO: recorre todas antes de repetir.
    El índice combina la fecha, el turno (mañana/tarde) y el número de corrida de GitHub
    (GITHUB_RUN_NUMBER), así también cambia si corres varias veces el mismo día (lab).
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
    try:
        corrida = int(os.environ.get("GITHUB_RUN_NUMBER", "0"))
    except ValueError:
        corrida = 0
    idx = (ahora.date().toordinal() * 2 + turno + corrida) % len(files)
    print(f"    música: pista {idx + 1} de {len(files)}")
    return files[idx]


def build_video(audio_path, ass_path, out_path, bg_video=None, cards=None,
                graphics=None, duration=None, hook=None, outro=None):
    """cards: lista opcional de dicts {'big': '70%', 'small': 'texto', 'start': s, 'end': s}.
    graphics: lista opcional de dicts {'pattern': ruta_%05d.png, 'start': s, 'end': s, 'fps': n}.
    duration: si se pasa, corta la salida a esos segundos (en vez de -shortest).
    outro: (texto_grande, texto_chico) del cierre; None = OUTRO_CTA / OUTRO_SUB de siempre
    (en temas de fraude main.py manda ("COMPÁRTELO", "mándaselo a tu familia"))."""
    outro_cta, outro_sub = (outro if outro else (OUTRO_CTA, OUTRO_SUB))
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
        raw_hook = " ".join(str(hook).strip().upper().split())
        ancho = CARD_MAX_W - 40
        lineas = [raw_hook]
        hook_fs = _fit_fontsize(raw_hook, ancho, 130, 96)
        if hook_fs <= 96:
            pals = raw_hook.split()
            if len(pals) >= 2:
                mejor = min(range(1, len(pals)),
                            key=lambda k: abs(len(" ".join(pals[:k])) - len(" ".join(pals[k:]))))
                lineas = [" ".join(pals[:mejor]), " ".join(pals[mejor:])]
            larga = max(lineas, key=len)
            hook_fs = _fit_fontsize(larga, ancho, 120, 56)
        alpha = (f"if(lt(t,0.35),t/0.35,"
                 f"if(gt(t,{HOOK_DUR - 0.3:.2f}),max(0,({HOOK_DUR:.2f}-t)/0.3),1))")
        salto = int(hook_fs * 1.15)
        y0 = f"h*0.30-{(len(lineas) - 1) * salto // 2}"
        for li, linea in enumerate(lineas):
            htxt = _escape_drawtext(linea)
            # entra deslizándose desde abajo + fade in; hace fade out al final
            yexpr = f"{y0}+{li * salto}+80*(1-min(t/0.45,1))"
            tag = f"hook{li}"
            chain.append(
                f"[{last}]drawtext=font='{SUB_FONT}':text='{htxt}':fontcolor=0x00E5FF:"
                f"fontsize={hook_fs}:borderw=9:bordercolor=black:shadowcolor=black@0.6:"
                f"shadowx=4:shadowy=4:x=(w-tw)/2:y='{yexpr}':alpha='{alpha}':"
                f"enable='between(t,0,{HOOK_DUR:.2f})'[{tag}]"
            )
            last = tag

    for i, card in enumerate(cards or []):
        raw_big = str(card.get("big", ""))
        raw_small = str(card.get("small", ""))
        big_fs = _fit_fontsize(raw_big, CARD_MAX_W, 170, 70)
        small_fs = _fit_fontsize(raw_small, CARD_MAX_W, 64, 40)   # antes 52-34: no se leía
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

    if outro_cta and duration:
        oc_st = max(0.0, float(duration) - OUTRO_DUR)
        oc_alpha = (f"if(lt(t,{oc_st:.2f}),0,"
                    f"if(lt(t,{oc_st + 0.3:.2f}),(t-{oc_st:.2f})/0.3,1))")
        big_txt = _escape_drawtext(outro_cta.upper())
        big_fs = _fit_fontsize(outro_cta.upper(), CARD_MAX_W, 150, 90)
        chain.append(
            f"[{last}]drawtext=font='{SUB_FONT}':text='{big_txt}':fontcolor=0x00E5FF:"
            f"fontsize={big_fs}:borderw=8:bordercolor=black:shadowcolor=black@0.6:"
            f"shadowx=4:shadowy=4:x=(w-tw)/2:y=h*0.40:alpha='{oc_alpha}':"
            f"enable='between(t,{oc_st:.2f},{float(duration):.2f})'[octa]"
        )
        last = "octa"
        if outro_sub:
            sub_txt = _escape_drawtext(outro_sub)
            sub_fs = _fit_fontsize(outro_sub, CARD_MAX_W, 58, 40)
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

    # Normalización de volumen al final de la mezcla (voz + música).
    norm = _loudnorm()
    if norm:
        src = audio_map if audio_map.startswith("[") else f"[{audio_map}]"
        vf = vf + f";{src}{norm}[anorm]"
        audio_map = "[anorm]"
        print(f"    volumen normalizado a {AUDIO_LUFS} LUFS")

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
    _ajustar_volumen(os.path.join(work_dir, out))


def _eq_por_clip(path) -> str:
    """Filtro eq para acercar ESTE clip al brillo objetivo. Los oscuros suben con gamma
    (aclara medios tonos sin lavar los negros); los muy claros bajan un poco."""
    y = _measure_luma(path)
    if y is None:
        return ""
    if y < BG_TARGET_LUMA:
        gamma = min(1.45, 1.0 + (BG_TARGET_LUMA - y) / 255 * 1.6)
        bright = min(0.08, (BG_TARGET_LUMA - y) / 255 * 0.5)
        return f",eq=brightness={bright:.3f}:gamma={gamma:.3f}"
    bright = max(-0.12, (BG_TARGET_LUMA - y) / 255)
    return f",eq=brightness={bright:.3f}"


def _duracion_video(path: str) -> float:
    base, ext = os.path.splitext(FFMPEG)
    probe = (os.path.join(os.path.dirname(FFMPEG), "ffprobe" + ext)
             if os.path.dirname(FFMPEG) else "ffprobe")
    try:
        out = subprocess.run([probe, "-v", "quiet", "-show_entries", "format=duration",
                              "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30)
        return float(out.stdout.strip() or 0)
    except Exception:
        return 0.0


def _toma(spec):
    """Una toma del fondo: ruta (clip tal cual) o dict {'path', 'zoom', 'ss'}.
    zoom > 1 = 'punch-in' (acercamiento) y ss = desde qué segundo del clip arranca: así una
    segunda toma del MISMO clip se ve como un corte nuevo y no como el mismo plano."""
    if isinstance(spec, dict):
        return spec.get("path"), float(spec.get("zoom") or 1.0), float(spec.get("ss") or 0.0)
    return spec, 1.0, 0.0


def build_multi_background(clips, duration, out_path, durations=None):
    """clips: lista de tomas (ruta o dict de _toma). durations: segundos de cada toma
    (medidos de la voz); si no vienen, partes iguales."""
    pares = list(zip(clips or [], durations)) if (durations and len(durations) == len(clips or [])) \
        else [(c, None) for c in (clips or [])]
    pares = [(c, d) for c, d in pares if _toma(c)[0] and os.path.isfile(_toma(c)[0])]
    if not pares:
        return None
    if len(pares) == 1 and _toma(pares[0][0])[1] == 1.0:
        return _toma(pares[0][0])[0]   # un solo clip: el pipeline normal ya lo maneja

    clips = [c for c, _ in pares]
    n = len(clips)
    # duraciones por toma: explícitas (medidas de la voz) o partes iguales
    if all(d is not None for _, d in pares):
        segs = [max(0.5, float(d)) for _, d in pares]
    else:
        segs = [max(1.0, float(duration) / n)] * n

    inputs = []
    eq_cache = {}
    for c, seg in zip(clips, segs):
        ruta, _zoom, ss = _toma(c)
        largo = _duracion_video(ruta)
        if largo > 1.5 and ss > 0 and ss + seg > largo:
            ss = max(0.0, largo - seg - 0.1)
        pre = ["-ss", f"{ss:.2f}"] if ss > 0 else []
        inputs += ["-stream_loop", "-1", *pre, "-i", os.path.basename(ruta)]

    parts, labels = [], []
    for i in range(n):
        labels.append(f"[v{i}]")
        ruta, zoom, _ss = _toma(clips[i])
        # Brillo POR CLIP: antes se medía solo el primero y el mismo ajuste se aplicaba a
        # todos (un inicio oscuro dejaba sobreexpuestos los clips claros).
        if ruta not in eq_cache:
            eq_cache[ruta] = _eq_por_clip(ruta)
        eq = eq_cache[ruta]
        acerca = ""
        if zoom > 1.0:
            zw, zh = int(1080 * zoom) // 2 * 2, int(1920 * zoom) // 2 * 2
            acerca = f",scale={zw}:{zh},crop=1080:1920"
        parts.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920{acerca},setsar=1,fps=30{eq},trim=0:{segs[i]:.3f},setpts=PTS-STARTPTS[v{i}]"
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
        segdesc = ("exacto por bloque" if all(d is not None for _, d in pares)
                   else f"{segs[0]:.1f}s c/u")
        print(f"    fondo multi-escena armado con {n} tomas ({segdesc}; "
              f"la más larga dura {max(segs):.1f}s)")
        return out_path
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode("utf-8", "ignore")[-300:]
        print(f"    (no se pudo armar fondo multi-escena: {err}); uso el primer clip")
        return _toma(clips[0])[0]


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