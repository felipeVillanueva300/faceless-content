import os
import json
import time
import datetime
from google import genai
from google.genai import types
from google.genai import errors

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def _extract_json(text: str) -> dict:
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"El modelo no devolvió JSON:\n{text}")
    return json.loads(text[start:end + 1])


def generate_image_post(niche: str = "tecnología y finanzas", max_retries: int = 6) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    today = datetime.date.today().isoformat()

    prompt = f"""Eres creador de posts de imagen para redes en español de México sobre {niche}.
Genera UN post de UNA sola imagen (no video), con un ángulo fresco y concreto.
Usa la fecha como semilla para variar el tema: {today}.

Devuelve SOLO un objeto JSON válido, sin markdown ni texto adicional, con esta forma:
{{
  "big": "cifra o idea MUY corta y llamativa (ej: 70%, $240, 3x, AHORRA YA) — pocas letras",
  "small": "frase de máximo 6 palabras que explica el 'big'",
  "caption": "descripción para el post, con un gancho y 3-5 hashtags relevantes",
  "title": "título corto de 3-6 palabras",
  "image_prompt": "1-2 frases EN INGLÉS para el fondo: profesional y cinematográfico, relacionado al tema, SIN texto ni números (ej: 'cinematic dark blue finance background with abstract growth charts and coins')"
}}
Reglas: NO inventes estadísticas falsas; si no hay un dato sólido, usa una idea corta
en 'big'. 'small' debe ser muy breve para que quepa en la imagen."""

    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=1.0,
                    response_mime_type="application/json",
                ),
            )
            return _extract_json(resp.text)
        except errors.APIError as e:
            code = getattr(e, "code", None) or getattr(e, "status_code", None)
            last_err = e
            if code in (429, 500, 502, 503) and attempt < max_retries - 1:
                wait = 10 * (attempt + 1)
                print(f"Gemini respondió {code} (saturado). Reintento en {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise last_err
