"""Prueba temporal: transcribir la voz de 'Que no te roben el aguinaldo' 1/3, 2/3 y 3/3 rehechos
(NIP como palabra). Sin Gemini: solo Whisper."""
import os, subprocess, requests
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)
BASE = "https://github.com/felipeVillanueva300/faceless-content/releases/download/"
model = WhisperModel("medium", device="cpu", compute_type="int8")
for tag in ["daily-20261126-185432", "daily-20261126-185358", "daily-20261126-185543"]:
    open(f"{OUT}/reel.mp4", "wb").write(requests.get(BASE + tag + "/reel.mp4", timeout=120).content)
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", f"{OUT}/reel.mp4", "-vn", "-ac", "1",
                    "-ar", "16000", f"{OUT}/voz.wav"], check=True)
    segs, _ = model.transcribe(f"{OUT}/voz.wav", language="es", beam_size=5)
    for s in segs:
        print(f"VOZ {tag} [{s.start:5.1f}-{s.end:5.1f}] {s.text.strip()}", flush=True)
    os.remove(f"{OUT}/reel.mp4"); os.remove(f"{OUT}/voz.wav")
