"""Prueba temporal: cómo dice la voz algunas siglas. Mide cuánto dura la palabra (deletrear
tarda mucho más que decirla de corrido) y transcribe palabra por palabra."""
import asyncio, json, os, subprocess
from src import tts
from faster_whisper import WhisperModel

os.makedirs("prueba_voz_out", exist_ok=True)
CASOS = {
    "pib_1_PIB": "Cuando el PIB cae dos trimestres seguidos, hay recesión.",
    "pib_2_pib": "Cuando el pib cae dos trimestres seguidos, hay recesión.",
    "pib_3_píb": "Cuando el píb cae dos trimestres seguidos, hay recesión.",
    "pib_4_Pib": "Cuando el Pib cae dos trimestres seguidos, hay recesión.",
    "pib_5_pibe": "Cuando el pibe cae dos trimestres seguidos, hay recesión.",
    "sin_sigla": "Cuando el cae dos trimestres seguidos, hay recesión.",
    "condusef": "La CONDUSEF recomienda juntar al menos tres meses.",
    "ieps_iva": "A eso se le suman dos impuestos: el IVA y el IEPS.",
    "conasami": "Lo negocia la CONASAMI, una comisión tripartita.",
}
def dur(p):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                          "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    return float(out.strip() or 0)
model = WhisperModel("medium", device="cpu", compute_type="int8")
res = {}
for k, frase in CASOS.items():
    out = f"prueba_voz_out/{k}.mp3"
    asyncio.run(tts._synth(frase, out))
    segs, _ = model.transcribe(out, language="es", beam_size=5, word_timestamps=True)
    palabras = [f"{w.word.strip()}({w.end - w.start:.2f}s)" for s in segs for w in s.words]
    res[k] = {"dura": round(dur(out), 2), "oye": " ".join(palabras)}
    print(f"{k}: {res[k]['dura']}s -> {res[k]['oye']}", flush=True)
json.dump(res, open("prueba_voz_out/resultado.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
