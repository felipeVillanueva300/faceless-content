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