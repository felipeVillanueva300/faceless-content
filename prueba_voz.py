"""Prueba temporal (v3): cómo lee la voz los guiones de 'Lo que te toca por ley' 2-5
(Profedet, ISR, cifras) y dos palabras sueltas. Transcribe con Whisper y guarda los mp3."""
import asyncio, json, os
from src import tts
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)
SUELTAS = {
    "profedet_1": "Si no te pagan, la Profedet te asesora gratis.",
    "profedet_2": "Si no te pagan, la PROFEDET te asesora gratis.",
    "isr": "Hasta $3,519 de tu aguinaldo no paga ISR.",
}
model = WhisperModel("medium", device="cpu", compute_type="int8")
res = {}
def oye(mp3):
    segs, _ = model.transcribe(mp3, language="es", beam_size=5, word_timestamps=True)
    return " ".join(f"{w.word.strip()}({w.end - w.start:.2f})" for s in segs for w in s.words)
for k, t in SUELTAS.items():
    mp3 = f"{OUT}/{k}.mp3"
    asyncio.run(tts._synth(t, mp3))
    res[k] = oye(mp3); print(f"{k}: {res[k]}", flush=True)
for g in sorted(f for f in os.listdir("guiones") if f.startswith("ley-")):
    d = json.load(open(f"guiones/{g}", encoding="utf-8"))
    for i, t in enumerate([d["hook"]] + [b["narration"] for b in d["beats"]]):
        mp3 = f"{OUT}/{g[:-5]}_{i}.mp3"
        asyncio.run(tts._synth(t, mp3))
        segs, _ = model.transcribe(mp3, language="es", beam_size=5)
        o = " ".join(s.text.strip() for s in segs)
        print(f"{g}[{i}] voz: {tts._pronunciar(t)}", flush=True)
        print(f"{g}[{i}] oye: {o}", flush=True)
