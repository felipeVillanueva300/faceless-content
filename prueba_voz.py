"""Prueba temporal: transcribir la voz de los borradores del 25 nov (llamadas spam/cobranza y GBM).
Sin Gemini: solo Whisper. Espera a que exista el borrador de GBM."""
import os, subprocess, time, requests
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)
BASE = "https://github.com/felipeVillanueva300/faceless-content/releases/download/"
API = "https://api.github.com/repos/felipeVillanueva300/faceless-content/releases?per_page=5"
model = WhisperModel("medium", device="cpu", compute_type="int8")
tags = ["daily-20261125-201557"]
for _ in range(40):                      # hasta ~10 min esperando el de GBM
    nuevos = [r["tag_name"] for r in requests.get(API, timeout=30).json()
              if r["tag_name"].startswith("daily-") and r["tag_name"] > "daily-20261125-201557"]
    if nuevos:
        tags += sorted(nuevos)[:1]
        break
    time.sleep(15)
for tag in tags:
    open(f"{OUT}/reel.mp4", "wb").write(requests.get(BASE + tag + "/reel.mp4", timeout=120).content)
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", f"{OUT}/reel.mp4", "-vn", "-ac", "1",
                    "-ar", "16000", f"{OUT}/voz.wav"], check=True)
    segs, _ = model.transcribe(f"{OUT}/voz.wav", language="es", beam_size=5)
    for s in segs:
        print(f"VOZ {tag} [{s.start:5.1f}-{s.end:5.1f}] {s.text.strip()}", flush=True)
    os.remove(f"{OUT}/reel.mp4"); os.remove(f"{OUT}/voz.wav")
