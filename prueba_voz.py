"""Prueba temporal: ¿en qué sílaba carga la voz 'CONDUSEF'? (y cómo dice IEPS y Pemex).

Whisper solo dice QUÉ palabra oye, no DÓNDE va el acento. Para el acento se compara la
palabra tal cual contra tres versiones con el acento forzado (condusÉf, condÚsef, cÓndusef)
dentro de la misma frase: la versión forzada que más se parece (DTW sobre tono, energía y
timbre) es la acentuación que la voz está usando. También imprime los núcleos de sílaba
(tono y energía de cada vocal fuerte)."""
import asyncio, json, os, subprocess
import numpy as np
import librosa
from src import tts
from faster_whisper import WhisperModel

OUT = "prueba_voz_out"
os.makedirs(OUT, exist_ok=True)

AGUDA = "conduséf"      # con-du-SEF (como se dice en México)
LLANA = "condúsef"      # con-DU-sef
ESDRU = "cóndusef"      # CON-du-sef
VARIANTES = {
    "tal_cual": "CONDUSEF",
    "Capital": "Condusef",
    "minus": "condusef",
    "aguda": AGUDA,
    "llana": LLANA,
    "esdrujula": ESDRU,
    "separada": "condu séf",
}
FRASES = {   # (antes, después) de la palabra
    "A": ("La", "recomienda juntar al menos tres meses de gastos."),
    "B": ("Si el banco no te responde, quéjate ante la", "."),
    "C": ("Revisa en la página de la", "si tu banco tiene quejas."),
}
EXTRA = {
    "ieps_tal_cual": "A eso se le suman dos impuestos: el IVA y el IEPS.",
    "ieps_deletreado": "A eso se le suman dos impuestos: el IVA y el i e pe ese.",
    "ieps_palabra": "A eso se le suman dos impuestos: el IVA y el iéps.",
    "pemex": "Pemex y las gasolineras ponen el precio final.",
    "profeco": "Si no te dan litros de a litro, quéjate en Profeco.",
    "estimulo": "Hacienda publica cada semana el estímulo fiscal.",
}

SR = 16000


async def _una(texto, ruta, url):
    import edge_tts
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


def synth(texto, ruta):
    texto = tts._pronunciar(texto)
    ultimo = None
    for url in tts._endpoints():
        for _ in range(3):
            try:
                return asyncio.run(_una(texto, ruta, url))
            except Exception as e:
                ultimo = e
    raise RuntimeError(ultimo)


# ¿Cuántos tiempos de palabra recibe hoy el pipeline real (sin boundary=WordBoundary)?
_b = asyncio.run(tts._synth("La economía en tu bolsillo, parte cuatro.", f"{OUT}/real.mp3"))
print(f"PIPELINE REAL: {len(_b)} tiempos de palabra con tts._synth tal cual", flush=True)


def a_wav(mp3, wav, ini=None, fin=None):
    cmd = ["ffmpeg", "-y", "-v", "quiet", "-i", mp3, "-ac", "1", "-ar", str(SR)]
    if ini is not None:
        cmd += ["-ss", f"{ini:.3f}", "-to", f"{fin:.3f}"]
    subprocess.run(cmd + [wav], check=True)


def rasgos(y, f0_ref):
    hop = 160
    mf = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=13, n_fft=400, hop_length=hop)
    rms = librosa.feature.rms(y=y, frame_length=400, hop_length=hop)[0]
    db = librosa.amplitude_to_db(rms + 1e-6)
    f0, vo, _ = librosa.pyin(y, fmin=60, fmax=300, sr=SR, frame_length=1024, hop_length=hop)
    n = min(mf.shape[1], len(db), len(f0))
    f0 = f0[:n]
    st = 12 * np.log2(np.where(np.isnan(f0), np.nan, f0) / f0_ref)
    idx = np.arange(n)
    ok = ~np.isnan(st)
    st_i = np.interp(idx, idx[ok], st[ok]) if ok.sum() > 2 else np.zeros(n)
    return mf[:, :n], db[:n], st, st_i


def nucleos(db, st, hop_s=0.01):
    """Picos de energía con voz = vocales. Devuelve [(t, tono_st, dB, ancho_s)]."""
    from scipy.signal import find_peaks
    sm = np.convolve(db, np.ones(5) / 5, mode="same")
    picos, prop = find_peaks(sm, prominence=2.5, distance=6, width=2)
    out = []
    for p, w in zip(picos, prop["widths"]):
        tono = st[p] if not np.isnan(st[p]) else np.nanmean(st[max(0, p - 3):p + 4])
        out.append((round(p * hop_s, 2), None if np.isnan(tono) else round(float(tono), 1),
                    round(float(sm[p]), 1), round(float(w) * hop_s, 2)))
    return out


def dtw(a, b):
    D, wp = librosa.sequence.dtw(X=a, Y=b, metric="euclidean")
    return float(D[-1, -1] / len(wp))


model = WhisperModel("medium", device="cpu", compute_type="int8")
res = {}

for fk, (antes, despues) in FRASES.items():
    datos = {}
    for vk, palabra in VARIANTES.items():
        frase = f"{antes} {palabra} {despues}".replace(" .", ".")
        mp3 = f"{OUT}/{fk}_{vk}.mp3"
        b = synth(frase, mp3)
        n_antes = len(antes.split())
        n_desp = len([w for w in despues.split() if w.strip(".")])
        objetivo = b[n_antes:len(b) - n_desp] if n_desp else b[n_antes:]
        ini = objetivo[0][0] / 1e7 - 0.03
        fin = (objetivo[-1][0] + objetivo[-1][1]) / 1e7 + 0.03
        wav_f, wav_p = f"{OUT}/{fk}_{vk}.wav", f"{OUT}/{fk}_{vk}_palabra.wav"
        a_wav(mp3, wav_f)
        a_wav(mp3, wav_p, ini, fin)
        yf, _ = librosa.load(wav_f, sr=SR)
        f0f, _, _ = librosa.pyin(yf, fmin=60, fmax=300, sr=SR, frame_length=1024, hop_length=160)
        ref = float(np.nanmedian(f0f))
        y, _ = librosa.load(wav_p, sr=SR)
        mf, db, st, st_i = rasgos(y, ref)
        segs, _ = model.transcribe(mp3, language="es", beam_size=5, word_timestamps=True)
        oye = " ".join(w.word.strip() for s in segs for w in s.words)
        datos[vk] = {"mf": mf, "db": db, "st": st_i}
        nuc = nucleos(db, st)
        res[f"{fk}_{vk}"] = {"frase": frase, "tokens": [t[2] for t in objetivo],
                             "dura": round(fin - ini - 0.06, 2), "oye": oye, "silabas": nuc}
        print(f"[{fk}] {vk:10s} '{palabra}' tokens={[t[2] for t in objetivo]} "
              f"dura={fin - ini - 0.06:.2f}s", flush=True)
        print(f"      oye: {oye}", flush=True)
        print(f"      vocales (t, tono st, dB, ancho): {nuc}", flush=True)

    def vec(d, solo_prosodia):
        db = (d["db"] - d["db"].mean()) / (d["db"].std() + 1e-6)
        st = d["st"] / 3.0
        if solo_prosodia:
            return np.vstack([db, st])
        mf = (d["mf"] - d["mf"].mean(axis=1, keepdims=True)) / (d["mf"].std(axis=1, keepdims=True) + 1e-6)
        return np.vstack([mf * 0.5, db, st])

    for vk in ("tal_cual", "Capital", "minus"):
        for modo in (True, False):
            dist = {ref: round(dtw(vec(datos[vk], modo), vec(datos[ref], modo)), 3)
                    for ref in ("aguda", "llana", "esdrujula")}
            gana = min(dist, key=dist.get)
            etiqueta = "prosodia" if modo else "completo"
            print(f"  >> [{fk}] {vk} se parece más a: {gana.upper()}  ({etiqueta}: {dist})",
                  flush=True)
            res[f"{fk}_{vk}"][f"dtw_{etiqueta}"] = dist

for k, frase in EXTRA.items():
    mp3 = f"{OUT}/{k}.mp3"
    synth(frase, mp3)
    segs, _ = model.transcribe(mp3, language="es", beam_size=5, word_timestamps=True)
    oye = " ".join(f"{w.word.strip()}({w.end - w.start:.2f}s)" for s in segs for w in s.words)
    res[k] = {"frase": frase, "oye": oye}
    print(f"{k}: {oye}", flush=True)

json.dump(res, open(f"{OUT}/resultado.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
