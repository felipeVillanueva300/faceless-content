"""Prueba temporal: cómo suena 'hackeo' (y GBM, REPEP, REDECO, ETF) con distintas escrituras,
y qué se oye en el borrador daily-20261123-183349. Sin Gemini: edge-tts + Whisper."""
import asyncio, os, subprocess, requests
from src import tts
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)
model = WhisperModel("medium", device="cpu", compute_type="int8")

def oye(path):
    segs, _ = model.transcribe(path, language="es", beam_size=5)
    return " ".join(s.text.strip() for s in segs)

URL = ("https://github.com/felipeVillanueva300/faceless-content/releases/download/"
       "daily-20261123-183349/reel.mp4")
open(f"{OUT}/reel.mp4", "wb").write(requests.get(URL, timeout=120).content)
subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", f"{OUT}/reel.mp4", "-vn", "-ac", "1",
                "-ar", "16000", f"{OUT}/voz.wav"], check=True)
segs, _ = model.transcribe(f"{OUT}/voz.wav", language="es", beam_size=5)
for s in segs:
    print(f"VIDEO [{s.start:5.1f}-{s.end:5.1f}] {s.text.strip()}", flush=True)
os.remove(f"{OUT}/reel.mp4"); os.remove(f"{OUT}/voz.wav")

pruebas = {
    "hackeo": ("El mito del {w} bancario es que entran al sistema del banco.",
               ["hackeo", "jaqueo", "jakéo", "jáqueo"]),
    "hackear": ("No necesitan {w} la seguridad del banco para robarte.",
                ["hackear", "jaquear"]),
    "hackean": ("No {w} sistemas, te engañan a ti.", ["hackean", "jaquean"]),
    "hackers": ("Los {w} usan enlaces falsos.", ["hackers", "jáquers"]),
    "GBM": ("Abrí una cuenta en {w} para invertir desde el celular.",
            ["GBM", "ge be eme", "G B M"]),
    "REPEP": ("Registra tu número en el {w} de la Profeco.", ["REPEP", "repép", "re pep"]),
    "REDECO": ("Pon tu queja en el {w} de la CONDUSEF.", ["REDECO", "redéco"]),
    "ETF": ("Un {w} es una canasta de muchas empresas.", ["ETF", "e te efe"]),
}
for clave, (frase, variantes) in pruebas.items():
    for v in variantes:
        texto = frase.format(w=v)
        mp3 = f"{OUT}/{clave}_{v.replace(' ', '_')}.mp3"
        asyncio.run(tts._synth(texto, mp3))
        print(f"VAR {clave:8s} {v:12s} | voz: {tts._pronunciar(texto)} | oye: {oye(mp3)}", flush=True)
