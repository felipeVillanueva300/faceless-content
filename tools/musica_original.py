"""Pista de fondo ORIGINAL generada por código (sin samples ni material de terceros):
lo-fi tranquilo con piano eléctrico (FM), pad, bajo y batería suave. Uso libre."""
import numpy as np, sys
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
rng = np.random.default_rng(int(sys.argv[2]) if len(sys.argv) > 2 else 7)

def nota(n):            # MIDI -> Hz
    return 440.0 * 2 ** ((n - 69) / 12)

def env_adsr(n, a, d, s, r, dur):
    t = np.arange(n) / SR
    e = np.where(t < a, t / a, np.where(t < a + d, 1 - (1 - s) * (t - a) / d, s))
    rel = np.clip((t - dur) / r, 0, 1)
    return e * (1 - rel)

def epiano(f, dur, vel=0.5):
    n = int((dur + 1.2) * SR); t = np.arange(n) / SR
    idx = 1.6 * np.exp(-t * 3.0) + 0.15
    mod = np.sin(2 * np.pi * f * 1.0 * t) * idx
    x = np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 1.4)
    x += 0.25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 4)
    x += 0.12 * np.sin(2 * np.pi * f * 3 * t + mod * 0.5) * np.exp(-t * 6)
    x += 0.06 * np.sin(2 * np.pi * f * 4.01 * t) * np.exp(-t * 9)
    return vel * x * env_adsr(n, 0.004, 0.3, 0.6, 0.4, dur)

def pad(f, dur, vel=0.10):
    n = int((dur + 1.5) * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for d in (-0.005, 0, 0.006):
        ph = rng.uniform(0, 6)
        for h in range(1, int(5000 / f) + 1):
            x += np.sin(2 * np.pi * f * (1 + d) * h * t + ph * h) / h
    return vel * 0.5 * x * env_adsr(n, 0.9, 0.5, 0.8, 1.2, dur)

def bajo(f, dur, vel=0.35):
    n = int((dur + 0.3) * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 2 * f * t)
    return vel * x * env_adsr(n, 0.01, 0.2, 0.7, 0.15, dur)

def kick(vel=0.5):
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t * 30)
    return vel * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)

_hp = butter(4, 6000, 'hp', fs=SR, output='sos')
_bp = butter(2, [1500, 5000], 'bp', fs=SR, output='sos')
def hat(vel=0.06):
    n = int(0.08 * SR); t = np.arange(n) / SR
    return vel * sosfilt(_hp, rng.standard_normal(n)) * np.exp(-t * 60)
_sh = butter(2, [5000, 11000], 'bp', fs=SR, output='sos')
def shaker(vel=0.03):
    n = int(0.06 * SR); t = np.arange(n) / SR
    return vel * sosfilt(_sh, rng.standard_normal(n)) * np.sin(np.pi * np.clip(t / 0.06, 0, 1))

def rim(vel=0.12):
    n = int(0.12 * SR); t = np.arange(n) / SR
    return vel * sosfilt(_bp, rng.standard_normal(n)) * np.exp(-t * 35)

def main(salida, bpm=92, compases=56):
    beat = 60 / bpm; bar = 4 * beat
    total = compases * bar + 3
    L = np.zeros(int(total * SR)); Rr = np.zeros_like(L)
    def put(buf, x, t0):
        i = int(t0 * SR); j = min(len(buf), i + len(x))
        if i < len(buf): buf[i:j] += x[: j - i]
    # C mayor: Fmaj7, G6, Em7, Am7 (2 compases cada uno)
    acordes = [[53, 57, 60, 64], [55, 59, 62, 64], [52, 55, 59, 62], [57, 60, 64, 67]]
    raices = [41, 43, 40, 45]
    escala = [72, 74, 76, 79, 81, 84]        # pentatónica de C
    for c in range(compases):
        t0 = c * bar
        k = (c // 2) % 4
        ac, raiz = acordes[k], raices[k]
        intro = c < 4; outro = c >= compases - 4
        # pad (al empezar cada acorde)
        if c % 2 == 0:
            for n_ in ac:
                x = pad(nota(n_), 2 * bar)
                put(L, x * 0.9, t0); put(Rr, x * 1.1, t0 + 0.012)
        # piano: tiempos 1 y 2.5 (+ 4 a veces)
        for pos, vel in ((0, 0.32), (1.5 * beat, 0.24), (3 * beat, 0.2 if c % 2 else 0)):
            if vel == 0: continue
            for i, n_ in enumerate(ac):
                x = epiano(nota(n_ + 12), beat * 1.4, vel * rng.uniform(0.85, 1.05))
                dt = pos + i * 0.012 + rng.uniform(0, 0.006)
                put(L, x * (1.05 - i * 0.07), t0 + dt); put(Rr, x * (0.8 + i * 0.07), t0 + dt + 0.008)
        if intro or outro:
            continue
        # bajo
        put(L, bajo(nota(raiz), beat * 1.6), t0); put(Rr, bajo(nota(raiz), beat * 1.6), t0)
        put(L, bajo(nota(raiz + 7), beat * 0.9, 0.25), t0 + 2.5 * beat); put(Rr, bajo(nota(raiz + 7), beat * 0.9, 0.25), t0 + 2.5 * beat)
        # batería suave con swing
        for b in range(4):
            if b in (0, 2): x = kick(0.42 if b == 0 else 0.3); put(L, x, t0 + b * beat); put(Rr, x, t0 + b * beat)
            if b in (1, 3): x = rim(); put(L, x * 0.8, t0 + b * beat); put(Rr, x, t0 + b * beat + 0.004)
            for sub, sw in ((0, 0), (0.5, 0.06)):
                x = hat(0.05 if sub == 0 else 0.035); tt = t0 + (b + sub + sw) * beat
                put(L, x * 1.1, tt); put(Rr, x * 0.8, tt)
        for q in range(16):
            x = shaker(0.035 if q % 2 else 0.022); tt = t0 + q * beat / 4 + (0.03 if q % 2 else 0)
            put(L, x * 0.7, tt); put(Rr, x * 1.1, tt + 0.003)
        # melodía sencilla en la 2a mitad de cada frase de 8 compases
        if (c % 8) in (4, 5, 6):
            for s in range(0, 8, 2 if c % 2 else 3):
                n_ = escala[int(rng.integers(0, len(escala)))]
                x = epiano(nota(n_), beat * 0.9, 0.16)
                put(L, x, t0 + s * beat / 2); put(Rr, x * 0.9, t0 + s * beat / 2 + 0.01)
    # reverb (IR sintética) y filtro suave
    ir_n = int(2.2 * SR); t = np.arange(ir_n) / SR
    ir = rng.standard_normal(ir_n) * np.exp(-t * 3.2)
    ir = sosfilt(butter(2, 4500, 'lp', fs=SR, output='sos'), ir); ir /= np.abs(ir).sum() ** 0.5 * 20
    lp = butter(2, 12000, 'lp', fs=SR, output='sos')
    out = []
    for ch in (L, Rr):
        wet = fftconvolve(ch, ir)[: len(ch)]
        out.append(sosfilt(lp, ch * 0.8 + wet * 0.35))
    st = np.stack(out, 1)
    # fundidos de entrada/salida
    f_in, f_out = int(2 * SR), int(4 * SR)
    st[:f_in] *= np.linspace(0, 1, f_in)[:, None]; st[-f_out:] *= np.linspace(1, 0, f_out)[:, None]
    st /= np.max(np.abs(st)) / 0.89
    from scipy.io import wavfile
    wavfile.write(salida, SR, (st * 32767).astype(np.int16))

if __name__ == "__main__":
    main(sys.argv[1])
