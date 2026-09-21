"""Genera una imagen de FONDO a partir de una descripción, para cuando el stock
(Pexels/Pixabay) no tiene algo relevante. Varios proveedores con el mismo interfaz;
se elige con la variable AI_IMAGE_PROVIDER.

Proveedores:
- cloudflare : Cloudflare Workers AI (Stable Diffusion XL). GRATIS (10,000 neuronas/día).
               Necesita CF_ACCOUNT_ID y CF_API_TOKEN.
- pollinations: image.pollinations.ai. GRATIS y SIN API key (imagen por URL).
- gemini      : Nano Banana (imagen de Gemini). DE PAGA (~$0.04/img). Preparado por si
               algún día se activa; necesita GEMINI_API_KEY y AI_IMAGE_GEMINI_MODEL.

Todo es best-effort: si algo falla, devuelve None y el pipeline usa stock o el
fondo degradado. NUNCA rompe el video.

Variables:
  AI_IMAGE_ENABLED   "1" para activar (por defecto "0" = apagado)
  AI_IMAGE_PROVIDER  cloudflare | pollinations | gemini   (por defecto cloudflare)
  AI_IMAGE_MODE      always  -> genera imagen para CADA escena (mejor 'match')
                     fallback-> solo cuando el stock no trae clip
                     (lo consume main.py, no este módulo)
  CF_ACCOUNT_ID, CF_API_TOKEN
  AI_IMAGE_GEMINI_MODEL  (por defecto 'gemini-2.5-flash-image')
"""
import os
import requests

W, H = 1080, 1920

PROVIDER = os.environ.get("AI_IMAGE_PROVIDER", "cloudflare").strip().lower()
ENABLED = os.environ.get("AI_IMAGE_ENABLED", "0").strip().lower() in ("1", "true", "yes")

# Estilo fijo para que todos los fondos combinen ENTRE SÍ y con la marca, y NO lleven
# texto (los modelos escriben texto/números con errores; el texto lo pone tu pipeline).
# El estilo unificado + una SEMILLA fija hacen que las 4 imágenes de un video compartan
# tono e iluminación, para que no se sientan de videos distintos.
_ESTILO = ("cinematic vertical background photo, {p}, shallow depth of field, "
           "soft cinematic lighting, dark moody tone, consistent teal and navy color "
           "grading, clean modern minimal, no text, no words, no numbers, no letters, "
           "no watermark, high detail")
_NEGATIVO = "text, words, numbers, letters, watermark, logo, ui, low quality, blurry"

# Semilla base: mismo estilo/composición entre escenas del mismo video. Cambia con
# AI_IMAGE_SEED; -1 = aleatorio (cada imagen distinta).
SEED = int(os.environ.get("AI_IMAGE_SEED", "7"))


def _prompt(desc: str) -> str:
    return _ESTILO.format(p=desc.strip())


def _save(content: bytes, out_path: str) -> str:
    with open(out_path, "wb") as f:
        f.write(content)
    return out_path


def _cloudflare(desc: str, out_path: str):
    acc = os.environ.get("CF_ACCOUNT_ID", "").strip()
    tok = os.environ.get("CF_API_TOKEN", "").strip()
    if not (acc and tok):
        print("    (cloudflare: faltan CF_ACCOUNT_ID/CF_API_TOKEN)")
        return None
    model = os.environ.get("CF_IMAGE_MODEL", "@cf/stabilityai/stable-diffusion-xl-base-1.0")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{model}"
    cuerpo = {"prompt": _prompt(desc), "negative_prompt": _NEGATIVO,
              "width": 1024, "height": 1024}
    if SEED >= 0:
        cuerpo["seed"] = SEED
    r = requests.post(url, headers={"Authorization": f"Bearer {tok}"},
                      json=cuerpo, timeout=90)
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if "application/json" in ctype:      # algunos modelos devuelven base64 en JSON
        import base64
        data = r.json().get("result", {}).get("image")
        if not data:
            return None
        return _save(base64.b64decode(data), out_path)
    return _save(r.content, out_path)    # normalmente son bytes PNG directos


def _pollinations(desc: str, out_path: str):
    import urllib.parse
    p = urllib.parse.quote(_prompt(desc))
    seed_q = f"&seed={SEED}" if SEED >= 0 else ""
    url = (f"https://image.pollinations.ai/prompt/{p}"
           f"?width={W}&height={H}&nologo=true&model=flux{seed_q}")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return _save(r.content, out_path)


def _gemini(desc: str, out_path: str):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    from google import genai
    client = genai.Client(api_key=key)
    model = os.environ.get("AI_IMAGE_GEMINI_MODEL", "gemini-2.5-flash-image")
    resp = client.models.generate_content(model=model, contents=_prompt(desc))
    for cand in getattr(resp, "candidates", []) or []:
        for part in getattr(cand.content, "parts", []) or []:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                return _save(inline.data, out_path)
    return None


_PROVIDERS = {"cloudflare": _cloudflare, "pollinations": _pollinations, "gemini": _gemini}


def generate_image(desc: str, out_path: str):
    """Genera una imagen para la descripción 'desc'. Devuelve la ruta o None."""
    if not ENABLED:
        return None
    fn = _PROVIDERS.get(PROVIDER)
    if not fn:
        print(f"    (AI_IMAGE_PROVIDER '{PROVIDER}' no válido)")
        return None
    try:
        res = fn(desc, out_path)
        if res and os.path.isfile(res) and os.path.getsize(res) > 1000:
            print(f"    imagen IA ({PROVIDER}) para '{desc[:40]}'")
            return res
        return None
    except Exception as e:
        print(f"    (imagen IA {PROVIDER} falló para '{desc[:40]}': {e})")
        return None