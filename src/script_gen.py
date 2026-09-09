import os
import json
import time
import datetime
from google import genai
from google.genai import types
from google.genai import errors

from src import content_plan

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

PILAR_OFFSET = 7

ANGULOS = [
    "El error común: abre señalando un error que casi todos cometen.",
    "El dato que sorprende: abre con una cifra o hecho poco obvio.",
    "El truco rápido: promete un truco concreto que toma segundos.",
    "Mito vs. realidad: desmiente una creencia falsa y da la verdad.",
    "Comparativa: contrasta dos opciones y di cuál conviene y por qué.",
]


def _extract_json(text: str) -> dict:
    text = text.strip()
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        raise ValueError(f"El modelo no devolvió JSON:\n{text}")
    return json.loads(text[s:e + 1])


def _angulo_del_dia(today):
    return ANGULOS[today.toordinal() % len(ANGULOS)]


def generate_script(niche: str = "tecnología y finanzas", avoid=None, max_retries: int = 4) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    today = datetime.date.today()
    pilar = content_plan.pilar_del_dia(today, offset=PILAR_OFFSET)
    angulo = _angulo_del_dia(today)
    evitar = content_plan.avoid_text(avoid)

    prompt = f"""Eres guionista de Reels/Shorts en español de México para la cuenta "Dinero Simple",
sobre {niche}. Público: personas normales SIN conocimientos financieros. Claro y directo, sin jerga,
sin frases motivacionales vacías.

PILAR DE HOY (tema base): {pilar}.
ÁNGULO DE HOY: {angulo}
{evitar}
Genera UN guion para un video vertical de 30 a 40 segundos siguiendo el pilar y el ángulo de hoy.
UNA idea útil y concreta que cualquiera entienda. Usa la fecha como semilla: {today.isoformat()}.

Devuelve SOLO un objeto JSON válido, sin markdown, con esta forma:
{{
  "hook": "primera frase de 1 línea que enganche en los primeros 2 segundos",
  "script": "texto corrido para narrar, 90-120 palabras, frases cortas y claras",
  "caption": "descripción para el post, con gancho y 3-5 hashtags relevantes",
  "title": "título corto de 3-6 palabras",
  "broll_keywords": "2-4 palabras EN INGLÉS de algo VISUAL y CONCRETO de finanzas/tecnología para buscar video de fondo (ej: 'credit card payment', 'mexican pesos cash', 'person using phone banking', 'calculator and money'). Evita términos abstractos o que traigan resultados sin relación (nada de gente genérica, niños, oficinas vacías)",
  "cards": [
    {{"big": "cifra o palabra corta (ej: '70%')", "small": "frase de máximo 4 palabras"}}
  ],
  "graphics": [
    {{"type": "countup", "value": 74000, "prefix": "$", "label": "de más en 5 años"}},
    {{"type": "bars", "title": "pagar solo el mínimo", "a_label": "Pago mínimo", "a_value": 74000, "b_label": "Pago mayor", "b_value": 18000, "a_color": "red", "b_color": "green"}}
  ],
  "topic": "identificador corto del tema en minúsculas con guiones (ej: 'cancelar-suscripciones')"
}}
Reglas: NO inventes estadísticas falsas. Ortografía correcta en español de México, CON acentos y ñ.
'cards': 1 o 2 como máximo. 'topic' debe ser específico al ángulo de hoy.
'graphics': 1 o 2 elementos que APOYEN el dato principal del video. Tipos permitidos SOLO:
"countup" (un número que sube: usa value numérico, prefix como "$" o "", label corta) y
"bars" (comparación de dos: a_label/a_value y b_label/b_value numéricos, title corto, colores
"red"/"green"). Usa cifras realistas y sensatas. Si el video no tiene un número claro, deja
"graphics": []."""

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