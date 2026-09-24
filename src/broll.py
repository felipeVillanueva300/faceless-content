import os
import requests

PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
PIXABAY_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
SOURCES = [s.strip().lower() for s in
           os.environ.get("BROLL_SOURCES", "pexels,pixabay").split(",") if s.strip()]


def _download(url: str, out_path: str) -> str | None:
    dl = requests.get(url, timeout=120, stream=True)
    dl.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in dl.iter_content(chunk_size=1 << 16):
            f.write(chunk)
    return out_path


_DINERO_FISICO = {
    "money", "cash", "banknote", "banknotes", "bill", "bills",
    "currency", "currencies", "peso", "pesos", "dollar", "dollars", "euro", "euros",
    "coin", "coins", "wad", "argentina", "argentine", "argentinian", "usd",
}
_BLOQUEO_RESULTADOS = {
    "money", "cash", "banknote", "banknotes", "bill", "bills", "currency", "coin", "coins",
    "dollar", "dollars", "usd", "euro", "euros", "peso", "pesos", "argentina", "argentine",
    "argentinian", "rupee", "rupees", "yen", "yuan", "ruble", "rubles", "pound", "pounds",
    "sterling", "reais", "lira", "franc", "flag",
} | {w.strip().lower() for w in os.environ.get("BROLL_BLOCK", "").split(",") if w.strip()}


def limpiar_escena(desc: str) -> str:
    """Quita de la escena las palabras de dinero físico. Si quitó alguna, añade
    'savings' una vez para no perder el sentido. Ej:
      'money under mattress'  -> 'savings under mattress'
      'counting cash hands'   -> 'savings counting hands'
      'credit card hand'      -> 'credit card hand' (sin cambios)"""
    import re
    pals = (desc or "").split()
    limpias, quito = [], False
    for p in pals:
        base = re.sub(r"[^a-z]", "", p.lower())
        if base in _DINERO_FISICO:
            quito = True
            continue
        limpias.append(p)
    if quito:
        limpias = ["savings"] + limpias
    out = " ".join(limpias).strip()
    return out or "personal finance planning"


# IDs concretos que nunca queremos (ej. el carrito con notas en alemán). Separados por coma.
_IDS_BLOQUEADOS = {x.strip() for x in os.environ.get("BROLL_BLOCK_IDS", "").split(",") if x.strip()}
# Entre cuántos resultados buenos se elige al azar (1 = siempre el primero, como antes).
TOP_N = max(1, int(os.environ.get("BROLL_TOP_N", "5")))


def _bloqueado(texto: str) -> bool:
    import re
    palabras = set(re.split(r"[^a-z]+", (texto or "").lower()))
    return bool(palabras & _BLOQUEO_RESULTADOS)


def _best_vertical(candidatos):
    """De una lista de dicts {link,width,height}, elige el archivo que se verá NÍTIDO
    en 1080x1920. El fondo se escala hasta cubrir 1920 de alto, así que:
      - prefiere verticales (alto >= ancho);
      - dentro de ellos, el MÁS CHICO que ya tenga >= 1920 de alto (nítido y ligero);
      - si ninguno llega a 1920, el más grande que haya (se estira lo menos posible).
    Antes se tomaba 'el más cercano a 1920', y un horizontal 1920x1080 salía estirado
    1.8x (borroso)."""
    if not candidatos:
        return None
    verticales = [c for c in candidatos if (c.get("height") or 0) >= (c.get("width") or 0)]
    pool = verticales or candidatos
    suficientes = [c for c in pool if (c.get("height") or 0) >= 1920]
    if suficientes:
        suficientes.sort(key=lambda c: c.get("height") or 0)
        return suficientes[0]["link"]
    pool.sort(key=lambda c: c.get("height") or 0, reverse=True)
    return pool[0]["link"] if pool else None


VISION_ON = os.environ.get("BROLL_VISION", "1").strip().lower() in ("1", "true", "yes")
VISION_MODEL = os.environ.get("BROLL_VISION_MODEL", "gemini-3.5-flash-lite").strip()
VISION_TRIES = max(1, int(os.environ.get("BROLL_VISION_TRIES", "3")))
_FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")

_VISION_PROMPT = """Eres revisor de fondos de video para una cuenta de finanzas de MÉXICO.
Te doy 2 cuadros del MISMO clip. Marca "rechazar": true si en CUALQUIERA se ve:
- billetes, monedas o efectivo (de cualquier país);
- letreros, carteles, notas o texto legible en un idioma que NO sea español
  (ej. alemán, tailandés, chino, ruso, francés). Texto en inglés dentro de una app o
  pantalla sí se permite; letreros de tienda o calle en inglés NO;
- documentos oficiales o formularios de otro país (ej. formularios de impuestos de EE.UU.);
- banderas de otro país.
Si no ves nada de eso, "rechazar": false.
Responde SOLO JSON: {"rechazar": true|false, "motivo": "máx 8 palabras"}"""


def _frames(path: str):
    """Saca 2 cuadros JPG chicos (20% y 60% del clip). Devuelve lista de bytes."""
    import subprocess
    import tempfile
    base, ext = os.path.splitext(_FFMPEG)
    probe = (os.path.join(os.path.dirname(_FFMPEG), "ffprobe" + ext)
             if os.path.dirname(_FFMPEG) else "ffprobe")
    try:
        out = subprocess.run([probe, "-v", "quiet", "-show_entries", "format=duration",
                              "-of", "csv=p=0", path],
                             capture_output=True, text=True, timeout=30)
        dur = float(out.stdout.strip() or 0) or 5.0
    except Exception:
        dur = 5.0
    cuadros = []
    for frac in (0.2, 0.6):
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False).name
        try:
            subprocess.run([_FFMPEG, "-v", "error", "-y", "-ss", f"{dur * frac:.2f}", "-i", path,
                            "-frames:v", "1", "-vf", "scale=512:-2", tmp],
                           check=True, timeout=60)
            with open(tmp, "rb") as f:
                cuadros.append(f.read())
        except Exception:
            pass
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
    return cuadros


def _vision_ok(path: str, etiqueta: str) -> bool:
    """True si el clip se puede usar. Ante cualquier error, True (no bloquea el video)."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not (VISION_ON and key):
        return True
    cuadros = _frames(path)
    if not cuadros:
        return True
    try:
        import json
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        partes = [types.Part.from_bytes(data=c, mime_type="image/jpeg") for c in cuadros]
        resp = client.models.generate_content(
            model=VISION_MODEL,
            contents=partes + [_VISION_PROMPT],
            config=types.GenerateContentConfig(temperature=0,
                                               response_mime_type="application/json"),
        )
        txt = (resp.text or "").strip()
        data = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        if data.get("rechazar"):
            print(f"    visión RECHAZA {etiqueta}: {data.get('motivo', '')}")
            return False
        print(f"    visión OK {etiqueta}")
        return True
    except Exception as e:
        print(f"    (visión no disponible, se acepta {etiqueta}: {str(e)[:120]})")
        return True


def _probar_candidatos(candidatos, out_path: str, fuente: str, keywords: str):
    """candidatos: lista de (id, link). Prueba en orden: descarga, revisa con visión y
    devuelve el primero que pase. Máximo VISION_TRIES descargas."""
    for cid, link in candidatos[:VISION_TRIES]:
        etiqueta = f"{fuente} #{cid}" if cid is not None else fuente
        try:
            _download(link, out_path)
        except Exception as e:
            print(f"    (descarga falló {etiqueta}: {e})")
            continue
        if _vision_ok(out_path, etiqueta):
            print(f"    b-roll ({etiqueta}) para '{keywords}'")
            return out_path
    return None


def _orden_aleatorio(buenos):
    """Los TOP_N primeros en orden aleatorio, luego el resto (respaldo si la visión
    rechaza varios)."""
    import random
    top = list(buenos[:TOP_N])
    random.shuffle(top)
    return top + list(buenos[TOP_N:])


def _from_pexels(keywords: str, out_path: str) -> str | None:
    if not PEXELS_KEY:
        return None
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_KEY},
        params={"query": keywords, "orientation": "portrait",
                "size": "medium", "per_page": 15},
        timeout=30,
    )
    r.raise_for_status()
    buenos = []
    for v in r.json().get("videos", []):
        firma = " ".join([v.get("url") or ""] + [str(t) for t in (v.get("tags") or [])])
        if _bloqueado(firma) or str(v.get("id")) in _IDS_BLOQUEADOS:
            continue
        files = [{"link": f["link"], "width": f.get("width"), "height": f.get("height")}
                 for f in v.get("video_files", []) if f.get("file_type") == "video/mp4"]
        best = _best_vertical(files)
        if best:
            buenos.append((v.get("id"), best))
    if not buenos:
        return None
    return _probar_candidatos(_orden_aleatorio(buenos), out_path, "Pexels", keywords)


def _from_pixabay(keywords: str, out_path: str) -> str | None:
    if not PIXABAY_KEY:
        return None
    r = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": PIXABAY_KEY, "q": keywords, "per_page": 10, "safesearch": "true"},
        timeout=30,
    )
    r.raise_for_status()
    hits = []
    for hit in r.json().get("hits", []):
        if _bloqueado(f"{hit.get('tags', '')} {hit.get('pageURL', '')}"):
            continue
        vids = hit.get("videos", {})
        cands = [{"link": v.get("url"), "width": v.get("width"), "height": v.get("height")}
                 for v in vids.values() if v.get("url")]
        if cands:
            hits.append(cands)
    # Pixabay no filtra por orientación: primero los hits que tengan versión vertical
    hits.sort(key=lambda cs: 0 if any((c.get("height") or 0) >= (c.get("width") or 0)
                                      for c in cs) else 1)
    buenos = [(None, b) for b in (_best_vertical(c) for c in hits) if b]
    if not buenos:
        return None
    return _probar_candidatos(_orden_aleatorio(buenos), out_path, "Pixabay", keywords)


_FETCHERS = {"pexels": _from_pexels, "pixabay": _from_pixabay}


def fetch_broll(keywords: str, out_path: str) -> str | None:
    fuentes = [s for s in SOURCES if s in _FETCHERS] or list(_FETCHERS)
    algun_key = PEXELS_KEY or PIXABAY_KEY
    if not algun_key:
        print("    (sin PEXELS_API_KEY ni PIXABAY_API_KEY: uso fondo degradado)")
        return None

    for fuente in fuentes:
        try:
            res = _FETCHERS[fuente](keywords, out_path)
            if res:
                return res
        except Exception as e:
            print(f"    ({fuente} falló: {e})")

    print(f"    (sin b-roll para '{keywords}' en {fuentes}: fondo degradado)")
    return None


def fetch_broll_scenes(scenes, out_dir: str, max_scenes: int = 4):
    import os
    escenas = [s.strip() for s in (scenes or []) if s and s.strip()][:max_scenes]
    if not escenas:
        return []
    if not (PEXELS_KEY or PIXABAY_KEY):
        print("    (sin API keys de b-roll: fondo degradado)")
        return []

    fuentes = [s for s in SOURCES if s in _FETCHERS] or list(_FETCHERS)
    rutas, vistos = [], set()
    for i, kw in enumerate(escenas):
        destino = os.path.join(out_dir, f"broll_{i}.mp4")
        bajado = None
        for fuente in fuentes:
            try:
                res = _FETCHERS[fuente](kw, destino)
            except Exception as e:
                print(f"    ({fuente} falló en escena '{kw}': {e})")
                res = None
            if res and os.path.isfile(res):
                firma = os.path.getsize(res)
                if firma in vistos:
                    continue
                vistos.add(firma)
                bajado = res
                break
        if bajado:
            rutas.append(bajado)
        else:
            print(f"    (escena '{kw}' sin clip usable; se salta)")
    print(f"    b-roll multi-escena: {len(rutas)}/{len(escenas)} clips")
    return rutas