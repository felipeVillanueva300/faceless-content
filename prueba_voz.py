"""Prueba temporal: transcribir con tiempos por palabra la parte 2/3 rehecha (daily-20261127-171046)
para revisar 'NIP', '911' y la frase del policía. Sin Gemini: solo Whisper."""
import os, subprocess, requests
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)
URL = ("https://github.com/felipeVillanueva300/faceless-content/releases/download/"
       "daily-20261127-171046/reel.mp4")
open(f"{OUT}/reel.mp4", "wb").write(requests.get(URL, timeout=120).content)
subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", f"{OUT}/reel.mp4", "-vn", "-ac", "1",
                "-ar", "16000", f"{OUT}/voz.wav"], check=True)
model = WhisperModel("medium", device="cpu", compute_type="int8")
segs, _ = model.transcribe(f"{OUT}/voz.wav", language="es", beam_size=5, word_timestamps=True)
for s in segs:
    print(f"VOZ [{s.start:5.1f}-{s.end:5.1f}] {s.text.strip()}", flush=True)
    print("PAL " + " ".join(f"{w.word.strip()}({w.start:.2f}-{w.end:.2f})" for w in s.words), flush=True)
subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", f"{OUT}/reel.mp4", "-vn", "-b:a", "128k",
                f"{OUT}/parte2_voz.mp3"], check=True)
os.remove(f"{OUT}/reel.mp4"); os.remove(f"{OUT}/voz.wav")
