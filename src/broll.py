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


def _best_vertical(candidatos):
    """De una lista de dicts {link,width,height}, elige el más cercano a 1920 de
    alto, prefiriendo los verticales (alto >= ancho)."""
    if not candidatos:
        return None
    verticales = [c for c in candidatos if (c.get("height") or 0) >= (c.get("width") or 0)]
    pool = verticales or candidatos
    pool.sort(key=lambda c: abs((c.get("height") or 0) - 1920))
    return pool[0]["link"] if pool else None


def _from_pexels(keywords: str, out_path: str) -> str | None:
    if not PEXELS_KEY:
        return None
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_KEY},
        params={"query": keywords, "orientation": "portrait",
                "size": "medium", "per_page": 10},
        timeout=30,
    )
    r.raise_for_status()
    for v in r.json().get("videos", []):
        files = [{"link": f["link"], "width": f.get("width"), "height": f.get("height")}
                 for f in v.get("video_files", []) if f.get("file_type") == "video/mp4"]
        best = _best_vertical(files)
        if best:
            print(f"    b-roll (Pexels) para '{keywords}'")
            return _download(best, out_path)
    return None


def _from_pixabay(keywords: str, out_path: str) -> str | None:
    if not PIXABAY_KEY:
        return None
    r = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": PIXABAY_KEY, "q": keywords, "per_page": 10, "safesearch": "true"},
        timeout=30,
    )
    r.raise_for_status()
    for hit in r.json().get("hits", []):
        vids = hit.get("videos", {})
        cands = [{"link": v.get("url"), "width": v.get("width"), "height": v.get("height")}
                 for v in vids.values() if v.get("url")]
        best = _best_vertical(cands)
        if best:
            print(f"    b-roll (Pixabay) para '{keywords}'")
            return _download(best, out_path)
    return None


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