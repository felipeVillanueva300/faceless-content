"""Prueba temporal: cómo suena 'NIP' con distintas escrituras. Sin Gemini: edge-tts + Whisper.
Si Whisper escribe 'N.I.P.' o 'ene i pe', la voz lo deletrea (mal); 'nip' = bien."""
import asyncio, os
from src import tts
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)
model = WhisperModel("medium", device="cpu", compute_type="int8")
frases = [
    "Te la cambia por otra y un cómplice ve tu {w}.",
    "Como el chip y tu {w}, puede negarse a ese abono rápido. Por eso nadie debe ver tu {w}.",
    "Los pagos sin contacto piden tu {w} arriba de cierto monto.",
    "El banco nunca te pide tu {w}, contraseñas ni códigos.",
]
for v in ["NIP", "nip", "níp", "Nip", "nipp"]:
    for i, f in enumerate(frases):
        texto = f.format(w=v)
        mp3 = f"{OUT}/nip_{v}_{i}.mp3"
        asyncio.run(tts._synth(texto, mp3))
        segs, _ = model.transcribe(mp3, language="es", beam_size=5)
        print(f"VAR {v:5s} {i} | {' '.join(s.text.strip() for s in segs)}", flush=True)
