"""Prueba temporal: cómo suena 'Profedet' con distintas escrituras. Sin Gemini: edge-tts + Whisper."""
import asyncio, os
from src import tts
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)
model = WhisperModel("medium", device="cpu", compute_type="int8")
frases = [
    "Si no te pagan antes del 20 de diciembre, la {p} te asesora gratis.",
    "La {p} o la Procuraduría del Trabajo de tu estado te revisan la cuenta.",
    "Antes de firmar, llama a la {p}.",
]
for k in ["Profedet", "Profedét", "Pro fe dét", "Profe dét", "Prófedet"]:
    for i, f in enumerate(frases):
        texto = f.format(p=k)
        mp3 = f"{OUT}/profedet_{k.replace(' ', '_')}_{i}.mp3"
        asyncio.run(tts._synth(texto, mp3))
        segs, _ = model.transcribe(mp3, language="es", beam_size=5)
        print(f"VAR {k:12s} | {' '.join(s.text.strip() for s in segs)}", flush=True)
