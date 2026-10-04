import os
import asyncio
import edge_tts

VOICE = os.environ.get("TTS_VOICE", "es-MX-JorgeNeural")
RATE = os.environ.get("TTS_RATE", "+0%")
PITCH = os.environ.get("TTS_PITCH", "+0Hz")


_PRONUNCIA_BASE = {"SPEI": "spéi", "CoDi": "códi", "CODI": "códi", "CLABE": "clábe"}

PRONUNCIA_JSON = os.environ.get("PRONUNCIA_JSON", "pronunciacion.json")


def tabla_pronunciacion(incluir_json: bool = True) -> dict:
    """Base + pronunciacion.json ("terminos") + variable TTS_PRONUNCIA ("A=b;C=d").
    Lo de más abajo gana si una palabra se repite."""
    import json
    tabla = dict(_PRONUNCIA_BASE)
    if incluir_json:
        try:
            with open(PRONUNCIA_JSON, encoding="utf-8") as f:
                data = json.load(f) or {}
            for k, v in (data.get("terminos") or {}).items():
                if k and not k.startswith("_") and isinstance(v, str) and v.strip():
                    tabla[k.strip()] = v.strip()
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"    ({PRONUNCIA_JSON} no se pudo leer: {e}; sigo con la tabla base)")
    for par in os.environ.get("TTS_PRONUNCIA", "").split(";"):
        if "=" in par:
            k, v = par.split("=", 1)
            if k.strip():
                tabla[k.strip()] = v.strip()
    return tabla


def _pronunciar(text: str, tabla: dict = None) -> str:
    """Cambia cada palabra del diccionario por cómo se debe DECIR. Palabra completa y
    respetando mayúsculas ("app" no toca "apple" ni "happy"). Una sola pasada: lo que ya se
    reemplazó no se vuelve a reemplazar."""
    import re
    tabla = tabla_pronunciacion() if tabla is None else tabla
    if tabla:
        claves = sorted(tabla, key=len, reverse=True)      # "apps" antes que "app"
        patron = re.compile(r"(?<!\w)(" + "|".join(re.escape(k) for k in claves) + r")(?!\w)")
        text = patron.sub(lambda m: tabla[m.group(1)], text)
    text = re.sub(r"(\$\s?\d[\d,\.]*)\s*(?:pesos|mxn|m\.n\.)(?![a-záéíóú])", r"\1", text,
                  flags=re.IGNORECASE)
    return text


async def _synth(text: str, audio_path: str):
    text = _pronunciar(text)
    boundaries = []
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append((chunk["offset"], chunk["duration"], chunk["text"]))
    print(f"    voz OK — {len(boundaries)} tiempos de palabra capturados "
          f"(voz={VOICE}, rate={RATE})")
    return boundaries


def synthesize(text: str, audio_path: str):
    """Genera el mp3 y devuelve la lista de (offset_100ns, duracion_100ns, palabra)."""
    return asyncio.run(_synth(text, audio_path))

def _duracion(path: str) -> float:
    """Duración real del audio en segundos (via ffprobe)."""
    import subprocess
    ff = os.environ.get("FFMPEG_BIN", "")
    probe = "ffprobe"
    if ff and os.path.isfile(ff):
        cand = os.path.join(os.path.dirname(ff), "ffprobe.exe")
        if os.path.isfile(cand):
            probe = cand
    try:
        out = subprocess.run(
            [probe, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except Exception:
        return 0.0


ULTIMO_LEAD = 0.0


def synthesize_segments(textos, out_dir):
    """Sintetiza CADA bloque de narración por separado, mide su duración REAL, y los
    une en un solo audio.mp3. Devuelve (ruta_audio_combinado, [duraciones_por_bloque]).

    Esto es lo que permite que el fondo cambie EXACTO cuando la voz pasa a ese bloque:
    no estimamos, medimos. Best-effort: si un bloque queda vacío, se omite.
    """
    import subprocess
    partes, duraciones = [], []
    for i, txt in enumerate(textos):
        txt = (txt or "").strip()
        if not txt:
            continue
        seg = os.path.join(out_dir, f"seg_{i}.mp3")
        asyncio.run(_synth(txt, seg))
        d = _duracion(seg)
        if d <= 0:
            continue
        partes.append(seg)
        duraciones.append(d)

    if not partes:
        return None, []

    global ULTIMO_LEAD
    ULTIMO_LEAD = 0.0
    lead = float(os.environ.get("TTS_LEAD", "0.1"))
    if lead > 0:
        sil = os.path.join(out_dir, "seg_lead.mp3")
        ffb = os.environ.get("FFMPEG_BIN", "ffmpeg")
        try:
            subprocess.run([ffb, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                            "-t", f"{lead:.2f}", "-c:a", "libmp3lame", "-b:a", "48k", sil],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            partes.insert(0, sil)
            ULTIMO_LEAD = _duracion(sil) or lead
            duraciones[0] += ULTIMO_LEAD
        except Exception:
            pass

    combinado = os.path.join(out_dir, "audio.mp3")
    if len(partes) == 1:
        # un solo bloque: cópialo tal cual
        import shutil
        shutil.copyfile(partes[0], combinado)
        return combinado, duraciones

    # concatenar los mp3 con el demuxer concat (sin recomprimir)
    lista = os.path.join(out_dir, "seglist.txt")
    with open(lista, "w", encoding="utf-8") as f:
        for p in partes:
            f.write(f"file '{os.path.abspath(p)}'\n")
    ff = os.environ.get("FFMPEG_BIN", "ffmpeg")
    try:
        subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", lista,
                        "-c", "copy", combinado],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        # respaldo: recomprimir si el copy falla (mp3 con params distintos)
        subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", lista,
                        "-c:a", "libmp3lame", "-q:a", "3", combinado],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print(f"    voz por bloques: {len(partes)} bloques, "
          f"{sum(duraciones):.1f}s total")
    return combinado, duraciones