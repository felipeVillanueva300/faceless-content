"""Genera el contenido de un post de IMAGEN con Gemini.

Devuelve un dict: big (cifra/idea corta), small (frase que la explica),
caption (para el post), title (corto) e image_prompt (para el fondo IA, en inglés
y SIN texto). Reintenta si Google satura (503/429).
"""
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

    prompt = f"""Eres redactor de una cuenta mexicana de finanzas y tecnología llamada "Dinero Simple".
Tu público: personas normales en México, SIN conocimientos financieros. Escribes claro y directo,
como si le explicaras a un amigo. Nada de jerga (evita "portafolio", "diversificar", "rendimiento",
"activos"), nada de frases motivacionales vacías ni clichés.

Genera UN post de UNA imagen sobre {niche}. UN SOLO mensaje, claro y corto, con UNA idea útil y
concreta que la gente pueda aplicar HOY (un truco, un dato o un error común que cometen).
Usa la fecha como semilla para variar el tema cada día: {today}.

Reglas de longitud (ESTRICTAS):
- "big": máximo ~10 caracteres. Una cifra o 1-2 palabras de golpe (ej: "70%", "$240", "3 ERRORES").
- "small": MÁXIMO 4 palabras. Explica el "big" con un beneficio claro.
- "caption": 1 gancho + 1 idea concreta accionable + 1 llamado a la acción corto + 3-4 hashtags.
  Máximo ~40 palabras antes de los hashtags.
- "title": 3-5 palabras.
- "image_prompt": 1-2 frases EN INGLÉS para un fondo profesional y cinematográfico del tema,
  SIN texto ni números.

Reglas de contenido:
- Que se entienda en 2 segundos. Si dudas si es claro, hazlo más simple.
- NO inventes estadísticas. Si no hay un dato sólido y verificable, usa un truco o error común en "big".
- Ortografía correcta en español de México, CON acentos y ñ.

Ejemplos SOLO del tono (no los copies, inspírate):
{{"big":"$0","small":"comisiones que evitas","caption":"...","title":"Adiós comisiones","image_prompt":"..."}}
{{"big":"3 APPS","small":"para ahorrar solo","caption":"...","title":"Ahorro automático","image_prompt":"..."}}
{{"big":"-40%","small":"en tu recibo de luz","caption":"...","title":"Baja tu luz","image_prompt":"..."}}

Devuelve SOLO un objeto JSON válido, sin markdown ni texto adicional, con estas claves exactas:
"big", "small", "caption", "title", "image_prompt"."""

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