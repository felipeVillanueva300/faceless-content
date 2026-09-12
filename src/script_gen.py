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
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"El modelo no devolvió JSON:\n{text}")
    return json.loads(text[start:end + 1])


def generate_script(niche: str = "tecnología y finanzas", max_retries: int = 4) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    today = datetime.date.today().isoformat()

    prompt = f"""Eres guionista de Reels/Shorts en español de México sobre {niche}.
Genera UN guion para un video vertical de 30 a 45 segundos, con un ángulo fresco,
concreto y poco obvio (evita frases genéricas y clichés). Usa la fecha como semilla
para variar el tema cada día: {today}.

MUY IMPORTANTE — cómo se usa el guion:
El "hook" y el "script" se CONCATENAN y se narran JUNTOS, en ese orden, como una
sola voz continua. Por eso:
- El "script" debe CONTINUAR justo después del hook, SIN repetirlo y SIN parafrasearlo.
- NO empieces el "script" retomando la idea del hook; entra directo al desarrollo.
- Leídos seguidos (hook + " " + script), NO debe haber ninguna frase ni idea repetida
  al inicio. Debe sonar natural, como si una persona hablara de corrido.

Ejemplo de lo que NO se debe hacer:
  hook:   "El error más grande al empezar a invertir es dejar tu dinero en el banco."
  script: "El error más grande al invertir es dejarlo en el banco. Los bancos..."  <-- MAL, repite el hook

Ejemplo de lo correcto:
  hook:   "El error más grande al empezar a invertir es dejar tu dinero en el banco."
  script: "Tu cuenta de ahorro casi no paga intereses, mientras la inflación te come..."  <-- BIEN, continúa

Devuelve SOLO un objeto JSON válido, sin markdown ni texto adicional, con esta forma:
{{
  "hook": "primera frase de 1 línea que enganche en los primeros 2 segundos",
  "script": "texto corrido que CONTINÚA después del hook (NO lo repitas ni lo parafrasees), 90-130 palabras, frases cortas y claras",
  "caption": "descripción para el post, con un gancho y 3-5 hashtags relevantes",
  "title": "título corto de 3-7 palabras"
}}"""

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
                wait = 8 * (attempt + 1)
                print(f"Gemini respondió {code} (saturado). Reintento en {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise last_err