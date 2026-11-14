"""Prueba temporal (v2): ¿en qué sílaba carga la voz 'CONDUSEF' y qué escritura la deja bien?

En México se dice con-du-SEF (aguda). La v1 mostró que 'conduséf' y 'cóndusef' salen IDÉNTICOS
(la voz no respeta esos acentos en una palabra inventada), así que no sirven de referencia.
Aquí la referencia son palabras REALES con las mismas vocales o-u-e y acento conocido:
  consumé (aguda) · consumen (llana) · cónsules (esdrújula)
Se compara la entonación (tono y energía) de cada versión contra esas tres dentro de la misma
frase. Además se guardan los mp3 para oírlos, y se transcriben con Whisper los guiones fijos
de economía 4 y 5 completos (con pronunciacion.json aplicado) para cazar otras palabras."""
import asyncio, json, os, subprocess
import numpy as np
import librosa
import edge_tts
from src import tts
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)
SR = 16000

REFS = {"ref_aguda": "consumé", "ref_llana": "consumen", "ref_esdrujula": "cónsules"}
CANDIDATAS = {
    "tal_cual": "CONDUSEF",
    "condu_sef": "condu sef",
    "condu_séf": "condu séf",
    "condu-séf": "condu-séf",
    "con_du_séf": "con du séf",
}
FRASES = {   # (antes, después) de la palabra
    "A": ("La", "recomienda juntar al menos tres meses de gastos."),
    "B": ("Si el banco no te responde, quéjate ante la", "."),
    "C": ("Revisa en la página de la", "si tu banco tiene quejas."),
}
ETIQUETAS = {
    "et_actual": "Versión actual.",
    "et_1": "Opción uno.",
    "et_2": "Opción dos.",
    "et_3": "Opción tres.",
    "et_4": "Opción cuatro.",
}


async def _una(texto, ruta, url):
    tts._ec.WSS_URL = url
    b = []
    c = edge_tts.Communicate(texto, tts.VOICE, rate=tts.RATE, pitch=tts.PITCH,
                             boundary="WordBoundary")
    with open(ruta, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                b.append((ch["offset"], ch["duration"], ch["text"]))
    return b


def synth(texto, ruta, pronunciar=False):
    if pronunciar:
        texto = tts._pronunciar(texto)
    ultimo = None
    for url in tts._endpoints():
        for _ in range(3):
            try:
                return asyncio.run(_una(texto, ruta, url))
            except Exception as e:
                ultimo = e
    raise RuntimeError(ultimo)


def a_wav(mp3, wav, ini=None, fin=None):
    cmd = ["ffmpeg", "-y", "-v", "quiet", "-i", mp3, "-ac", "1", "-ar", str(SR)]
    if ini is not None:
        cmd += ["-ss", f"{ini:.3f}", "-to", f"{fin:.3f}"]
    subprocess.run(cmd + [wav], check=True)


def prosodia(wav_frase, wav_palabra):
    yf, _ = librosa.load(wav_frase, sr=SR)
    f0f, _, _ = librosa.pyin(yf, fmin=60, fmax=300, sr=SR, frame_length=1024, hop_length=160)
    ref = float(np.nanmedian(f0f))
    y, _ = librosa.load(wav_palabra, sr=SR)
    f0, _, _ = librosa.pyin(y, fmin=60, fmax=300, sr=SR, frame_length=1024, hop_length=160)
    rms = librosa.feature.rms(y=y, frame_length=400, hop_length=160)[0]
    n = min(len(f0), len(rms))
    st = 12 * np.log2(f0[:n] / ref)
    idx = np.arange(n)
    ok = ~np.isnan(st)
    st_i = np.interp(idx, idx[ok], st[ok]) if ok.sum() > 2 else np.zeros(n)
    db = librosa.amplitude_to_db(rms[:n] + 1e-6)
    db = (db - db.mean()) / (db.std() + 1e-6)
    # dónde cae el pico de tono dentro de la palabra (0 = inicio, 1 = final)
    pico = float(np.nanargmax(np.where(ok, st, -99)) / max(1, n - 1)) if ok.any() else None
    return st_i, db, pico


def dtw(a, b):
    D, wp = librosa.sequence.dtw(X=a, Y=b, metric="euclidean")
    return float(D[-1, -1] / len(wp))


res = {"palabra": {}, "guiones": {}}
b = asyncio.run(tts._synth("La economía en tu bolsillo, parte cuatro.", f"{OUT}/real.mp3"))
print(f"PIPELINE REAL: {len(b)} tiempos de palabra con tts._synth tal cual", flush=True)

for k, t in ETIQUETAS.items():
    synth(t, f"{OUT}/{k}.mp3")

for fk, (antes, despues) in FRASES.items():
    datos = {}
    for vk, palabra in {**REFS, **CANDIDATAS}.items():
        frase = f"{antes} {palabra} {despues}".replace(" .", ".")
        mp3 = f"{OUT}/{fk}_{vk}.mp3"
        bnd = synth(frase, mp3)
        n_antes = len(antes.split())
        n_desp = len([w for w in despues.split() if w.strip(".")])
        obj = bnd[n_antes:len(bnd) - n_desp] if n_desp else bnd[n_antes:]
        ini = obj[0][0] / 1e7 - 0.02
        fin = (obj[-1][0] + obj[-1][1]) / 1e7 + 0.02
        wf, wp = f"{OUT}/{fk}_{vk}.wav", f"{OUT}/{fk}_{vk}_p.wav"
        a_wav(mp3, wf)
        a_wav(mp3, wp, ini, fin)
        st, db, pico = prosodia(wf, wp)
        datos[vk] = (st, db)
        res["palabra"][f"{fk}_{vk}"] = {"frase": frase, "dura": round(fin - ini - 0.04, 2),
                                        "pico_tono": None if pico is None else round(pico, 2)}
        print(f"[{fk}] {vk:14s} '{palabra}' dura={fin - ini - 0.04:.2f}s "
              f"pico de tono en {pico if pico is None else round(pico, 2)} de la palabra",
              flush=True)
    for vk in CANDIDATAS:
        for modo in ("tono", "tono+energia"):
            def v(x):
                st, db = datos[x]
                return np.vstack([st / 3.0]) if modo == "tono" else np.vstack([st / 3.0, db])
            dist = {r: round(dtw(v(vk), v(r)), 3) for r in REFS}
            gana = min(dist, key=dist.get).replace("ref_", "").upper()
            print(f"  >> [{fk}] {vk:14s} suena como {gana:10s} ({modo}: {dist})", flush=True)
            res["palabra"][f"{fk}_{vk}"][f"dtw_{modo}"] = dist

model = WhisperModel("medium", device="cpu", compute_type="int8")
for g in ("guiones/economia-4.json", "guiones/economia-5.json"):
    d = json.load(open(g, encoding="utf-8"))
    textos = [d["hook"]] + [x["narration"] for x in d["beats"]]
    for i, t in enumerate(textos):
        mp3 = f"{OUT}/{os.path.basename(g)[:-5]}_{i}.mp3"
        synth(t, mp3, pronunciar=True)
        segs, _ = model.transcribe(mp3, language="es", beam_size=5)
        oye = " ".join(s.text.strip() for s in segs)
        print(f"{os.path.basename(g)} [{i}] voz: {tts._pronunciar(t)}", flush=True)
        print(f"{os.path.basename(g)} [{i}] oye: {oye}", flush=True)
        res["guiones"][f"{g}_{i}"] = {"texto": t, "voz": tts._pronunciar(t), "oye": oye}

for f in os.listdir(OUT):
    if f.endswith(".wav"):
        os.remove(os.path.join(OUT, f))
json.dump(res, open(f"{OUT}/resultado.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
