"""Descarga un video vertical de stock (Pexels) según palabras clave del guion.

Gratis con API key (variable de entorno PEXELS_API_KEY). Si no hay key, no hay
resultados, o algo falla, devuelve None y el pipeline usa el fondo degradado.
"""
import os
import requests

PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")


def fetch_broll(keywords: str, out_path: str) -> str | None:
    if not PEXELS_KEY:
        print("    (sin PEXELS_API_KEY: uso fondo degradado)")
        return None
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_KEY},
            params={
                "query": keywords,
                "orientation": "portrait",
                "size": "medium",
                "per_page": 10,
            },
            timeout=30,
        )
        r.raise_for_status()
        videos = r.json().get("videos", [])
        if not videos:
            print(f"    (Pexels sin resultados para '{keywords}': fondo degradado)")
            return None

        # Elegir el primer video y, dentro, el archivo mp4 vertical de mejor
        # resolución que no sea gigante (para no tardar en descargar).
        best_url = None
        for v in videos:
            files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4"]
            verticales = [f for f in files if (f.get("height") or 0) >= (f.get("width") or 0)]
            candidatos = verticales or files
            # ordenar por altura, preferir ~1080-1920
            candidatos.sort(key=lambda f: abs((f.get("height") or 0) - 1920))
            if candidatos:
                best_url = candidatos[0]["link"]
                break

        if not best_url:
            return None

        dl = requests.get(best_url, timeout=120, stream=True)
        dl.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in dl.iter_content(chunk_size=1 << 16):
                f.write(chunk)
        print(f"    b-roll descargado para '{keywords}'")
        return out_path
    except Exception as e:
        print(f"    (Pexels falló: {e}; uso fondo degradado)")
        return None
