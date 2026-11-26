"""Prueba temporal: transcribir la voz de los borradores del 25 nov (Que no te roben el aguinaldo 1/3).
Sin Gemini: solo Whisper. Espera a que exista el borrador de GBM."""
import os, subprocess, time, requests
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)
BASE = "https://github.com/felipeVillanueva300/faceless-content/releases/download/"
API = "https://api.github.com/repos/felipeVillanueva300/faceless-content/releases?per_page=5"
model = WhisperModel("medium", device="cpu", compute_type="int8")
tags = ["daily-20261126-180452"]
for tag in tags:
    open(f"{OUT}/reel.mp4", "wb").write(requests.get(BASE + tag + "/reel.mp4", timeout=120).content)
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", f"{OUT}/reel.mp4", "-vn", "-ac", "1",
                    "-ar", "16000", f"{OUT}/voz.wav"], check=True)
    segs, _ = model.transcribe(f"{OUT}/voz.wav", language="es", beam_size=5)
    for s in segs:
        print(f"VOZ {tag} [{s.start:5.1f}-{s.end:5.1f}] {s.text.strip()}", flush=True)
    os.remove(f"{OUT}/reel.mp4"); os.remove(f"{OUT}/voz.wav")
