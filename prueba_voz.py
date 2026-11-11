"""Prueba temporal: cómo suena 'Wi-Fi' con distintas escrituras, y transcripción de dos reels."""
import asyncio, json, os, urllib.request
from src import tts
from faster_whisper import WhisperModel

os.makedirs("prueba_voz_out", exist_ok=True)
FRASE = "Revisar tu app del banco con el {w} gratis de la plaza le da tu clave a cualquiera."
CANDIDATOS = {"1_tal_cual_Wi-Fi": "Wi-Fi", "2_uaifai": "uáifai", "3_uai_fai": "uái fai",
              "4_guaifai": "guáifai", "5_wifi": "wifi"}
model = WhisperModel("medium", device="cpu", compute_type="int8")
res = {}
for k, w in CANDIDATOS.items():
    out = f"prueba_voz_out/{k}.mp3"
    asyncio.run(tts._synth(FRASE.format(w=w), out))
    segs, _ = model.transcribe(out, language="es", beam_size=5)
    res[k] = " ".join(s.text.strip() for s in segs)
    print(k, "->", res[k], flush=True)
for tag in ["daily-20261111-183146", "daily-20261107-002341"]:
    url = f"https://github.com/felipeVillanueva300/faceless-content/releases/download/{tag}/reel.mp4"
    mp4 = f"/tmp/{tag}.mp4"
    urllib.request.urlretrieve(url, mp4)
    segs, _ = model.transcribe(mp4, language="es", beam_size=5)
    res[tag] = "\n".join(f"[{s.start:5.1f}] {s.text.strip()}" for s in segs)
    print(tag, "\n" + res[tag], flush=True)
json.dump(res, open("prueba_voz_out/resultado.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
