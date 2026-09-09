import os
import json
import time
import datetime
from google import genai
from google.genai import types
from google.genai import errors

from src import content_plan

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

FORMATOS = [
    ("El dato que sorprende",
     "'big' = la cifra impactante (ej: '$3,200 AL AÑO'). "
     "'small' = frase clara que explica qué significa para la persona."),
    ("El error común",
     "'big' = 'EL ERROR #1'. "
     "'small' = el error concreto que comete la gente, en una frase clara."),
    ("El tip accionable",
     "'big' = una acción corta en mayúsculas (ej: 'REVISA ESTO HOY'). "
     "'small' = cómo hacerlo y para qué, en una frase clara."),
    ("Mito vs. realidad",
     "'big' = 'MITO'. "
     "'small' = la creencia falsa entre comillas + la verdad corta."),
    ("Comparativa simple",
     "'big' = 'A vs B' con dos conceptos cortos (ej: 'AHORRAR vs INVERTIR'). "
     "'small' = cuál conviene y por qué, en una frase clara."),
]


def _extract_json(text: str) -> dict:
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"El modelo no devolvió JSON:\n{text}")
    return json.loads(text[start:end + 1])


def _formato_del_dia(today):
    return FORMATOS[today.toordinal() % len(FORMATOS)]


def generate_image_post(niche="tecnología y finanzas", avoid=None, max_retries=6) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    today = datetime.date.today()
    pilar = content_plan.pilar_del_dia(today)          # imagen usa offset 0
    nombre_formato, reglas_formato = _formato_del_dia(today)
    evitar = content_plan.avoid_text(avoid)

    prompt = f"""Eres redactor de una cuenta mexicana de finanzas y tecnología llamada "Dinero Simple".
Tu público: personas normales en México, SIN conocimientos financieros. Escribes claro y directo,
como si le explicaras a un amigo. Nada de jerga. Nada de frases motivacionales vacías.

PILAR DE HOY (el tema base): {pilar}.
FORMATO DE HOY: "{nombre_formato}".
Instrucciones del formato:
{reglas_formato}
{evitar}
Genera UN post de UNA imagen sobre el PILAR y el FORMATO de hoy. UNA idea útil y concreta que
cualquiera entienda al instante y pueda aplicar. Usa la fecha como semilla: {today.isoformat()}.

Reglas de longitud:
- "big": máximo ~14 caracteres. El gancho grande de la imagen.
- "small": una FRASE CLARA Y COMPLETA de 8 a 12 palabras (que se entienda sola).
- "caption": 1 gancho + explicación útil en 2-3 frases + 1 llamado a la acción + 3-4 hashtags.
- "title": 3-5 palabras.
- "image_prompt": 1-2 frases EN INGLÉS para un fondo profesional del tema, SIN texto ni números.
- "topic": identificador corto del tema en minúsculas con guiones (ej: "cancelar-suscripciones").
  Sirve para no repetir; hazlo específico al ángulo de HOY.

Reglas de contenido:
- Que cualquier persona lo entienda en 3 segundos.
- NO inventes estadísticas falsas. Usa cifras realistas o habla en términos generales.
- Ortografía correcta en español de México, CON acentos y ñ.

Devuelve SOLO un objeto JSON válido, sin markdown, con estas claves exactas:
"big", "small", "caption", "title", "image_prompt", "topic"."""

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