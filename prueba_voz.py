"""Prueba temporal: qué palabra se oye mal hacia el segundo 30 del video de beneficiarios del
IMSS (daily-20261121-185903) y cómo suena 'IMSS' / 'CURP' con distintas escrituras.
Sin Gemini: solo edge-tts + Whisper."""
import asyncio, json, os, subprocess, requests
from src import tts
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)
URL = ("https://github.com/felipeVillanueva300/faceless-content/releases/download/"
       "daily-20261121-191537/reel.mp4")
open(f"{OUT}/reel.mp4", "wb").write(requests.get(URL, timeout=120).content)
subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-ss", "26", "-to", "38", "-i", f"{OUT}/reel.mp4",
                "-vn", "-ac", "1", "-ar", "16000", f"{OUT}/tramo_26_38.wav"], check=True)
model = WhisperModel("medium", device="cpu", compute_type="int8")

def oye(path):
    segs, _ = model.transcribe(path, language="es", beam_size=5, word_timestamps=True)
    return " ".join(f"{w.word.strip()}({w.start:.1f}-{w.end:.1f})" for s in segs for w in s.words)

print("VIDEO 26-38s:", oye(f"{OUT}/tramo_26_38.wav"), flush=True)
base = "Se hace en la app {i} Digital o en la página del {i}, con tu {c}, la de tu familiar y un correo."
variantes = {
    "actual": ("IMSS", "CURP"),
    "ims": ("ims", "CURP"),
    "imse": ("ímss", "CURP"),
    "seguro": ("Seguro Social", "CURP"),
    "curp_min": ("IMSS", "curp"),
    "curp_acento": ("IMSS", "kúrp"),
}
for k, (i, c) in list(variantes.items())[:0]:
    texto = base.format(i=i, c=c)
    mp3 = f"{OUT}/var_{k}.mp3"
    asyncio.run(tts._synth(texto, mp3))
    print(f"{k:12s} voz: {tts._pronunciar(texto)}", flush=True)
    print(f"{k:12s} oye: {oye(mp3)}", flush=True)
os.remove(f"{OUT}/reel.mp4")
