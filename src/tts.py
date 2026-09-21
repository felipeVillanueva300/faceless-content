import os
import asyncio
import edge_tts

VOICE = os.environ.get("TTS_VOICE", "es-MX-JorgeNeural")
RATE = os.environ.get("TTS_RATE", "+0%")
PITCH = os.environ.get("TTS_PITCH", "+0Hz")


async def _synth(text: str, audio_path: str):
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