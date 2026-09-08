import os
import random
import requests

BACKEND = os.environ.get("IMAGE_BACKEND", "gemini").strip().lower()
_DEFAULT_MODEL = "gemini-2.5-flash-image" if BACKEND == "gemini" else "imagen-4.0-generate-001"
MODEL = os.environ.get("IMAGE_MODEL", _DEFAULT_MODEL).strip()

_NO_TEXT = ("Vertical 4:5 composition. No text, no letters, no numbers, "
            "no logos, no watermark, clean background.")


# ---------- PEXELS (gratis) ----------
def _fetch_pexels(query: str, out_path: str):
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        print("    (sin PEXELS_API_KEY: uso degradado de marca)")
        return None

    terminos = [
        (query or "").strip(),
        "finance money technology",
        "business dark background",
    ]
    for term in [t for t in terminos if t]:
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": key},
                params={"query": term, "orientation": "portrait",
                        "per_page": 15, "size": "large"},
                timeout=30,
            )
            r.raise_for_status()
            fotos = r.json().get("photos", [])
            if not fotos:
                continue
            foto = random.choice(fotos)
            src = foto.get("src", {})
            img_url = src.get("portrait") or src.get("large2x") or src.get("original")
            if not img_url:
                continue
            img = requests.get(img_url, timeout=60)
            img.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(img.content)
            print(f"    fondo Pexels ok (término '{term}', foto de {foto.get('photographer', '?')})")
            return out_path
        except Exception as e:
            print(f"    (Pexels falló con '{term}': {e})")
    return None


def _gen_gemini(prompt: str, out_path: str, model: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    intentos = []
    try:
        intentos.append(types.GenerateContentConfig(response_modalities=["IMAGE"]))
    except Exception:
        pass
    intentos.append(None)

    last = None
    for cfg in intentos:
        try:
            if cfg is not None:
                resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
            else:
                resp = client.models.generate_content(model=model, contents=prompt)
            for part in resp.candidates[0].content.parts:
                data = getattr(part, "inline_data", None)
                if data and getattr(data, "data", None):
                    with open(out_path, "wb") as f:
                        f.write(data.data)
                    return out_path
        except Exception as e:
            last = e
    if last:
        raise last
    raise RuntimeError("Gemini no devolvió imagen")


def _gen_imagen(prompt: str, out_path: str, model: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_images(
        model=model, prompt=prompt,
        config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="3:4"),
    )
    img = resp.generated_images[0].image
    data = getattr(img, "image_bytes", None) or getattr(img, "data", None)
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


def fetch_background(prompt: str, out_path: str):
    # Pexels no necesita GEMINI_API_KEY.
    if BACKEND == "pexels":
        return _fetch_pexels(prompt, out_path)

    if not os.environ.get("GEMINI_API_KEY"):
        print("    (sin GEMINI_API_KEY: uso degradado de marca)")
        return None
    full = f"{(prompt or 'clean dark blue finance and technology background').strip()}. {_NO_TEXT}"
    try:
        if BACKEND == "imagen":
            path = _gen_imagen(full, out_path, MODEL)
        else:
            path = _gen_gemini(full, out_path, MODEL)
        print(f"    fondo IA generado con {BACKEND}/{MODEL}")
        return path
    except Exception as e:
        print(f"    (generación IA falló: {e}; uso degradado de marca)")
        return None