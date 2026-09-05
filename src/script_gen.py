"""Genera el guion del día con Gemini y lo devuelve como dict.

Reintenta si Google responde 503/429 (saturación temporal), útil para el cron.
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
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"El modelo no devolvió JSON:\n{text}")
    return json.loads(text[start:end + 1])
 
 
def generate_script(niche: str = "tecnología y finanzas", max_retries: int = 6) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    today = datetime.date.today().isoformat()
 
    prompt = f"""Eres guionista de Reels/Shorts en español de México sobre {niche}.
Genera UN guion para un video vertical de 30 a 45 segundos, con un ángulo fresco,
concreto y poco obvio (evita frases genéricas y clichés). Usa la fecha como semilla
para variar el tema cada día: {today}.
 
Devuelve SOLO un objeto JSON válido, sin markdown ni texto adicional, con esta forma:
{{
  "hook": "primera frase de 1 línea que enganche en los primeros 2 segundos",
  "script": "texto corrido para narrar, 90-130 palabras, frases cortas y claras",
  "caption": "descripción para el post, con un gancho y 3-5 hashtags relevantes",
  "title": "título corto de 3-6 palabras",
  "broll_keywords": "1-2 palabras EN INGLÉS para buscar video de fondo (ej: money, technology, city)",
  "cards": [
    {{"big": "dato corto y llamativo (ej: 70%, $240, 3x)", "small": "frase de máx 5 palabras que lo explica"}}
  ]
}}
Reglas para "cards": incluye 1 o 2 como máximo. El "big" debe ser un número o cifra
corta. NO inventes estadísticas falsas: si no hay un dato sólido, usa una cifra que
se derive del propio guion o deja "cards" como lista vacía []."""
 
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