"""Voz con edge-tts (gratis, sin API key).

Devuelve además los 'word boundaries' (offset y duración en unidades de 100 ns)
para poder generar subtítulos sincronizados sin Whisper ni torch.
"""
import os
import asyncio
import edge_tts

VOICE = os.environ.get("TTS_VOICE", "es-MX-JorgeNeural")


async def _synth(text: str, audio_path: str):
    boundaries = []
    communicate = edge_tts.Communicate(text, VOICE)
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append((chunk["offset"], chunk["duration"], chunk["text"]))
    return boundaries


def synthesize(text: str, audio_path: str):
    """Genera el mp3 y devuelve la lista de (offset_100ns, duracion_100ns, palabra)."""
    return asyncio.run(_synth(text, audio_path))
