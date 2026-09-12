import os
import json
import time
import datetime
from google import genai
from google.genai import types
from google.genai import errors

from src import content_plan

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def _extract_json(text: str) -> dict:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"El modelo no devolvió JSON:\n{text}")
    return json.loads(text[start:end + 1])


def generate_script(niche: str = "tecnología y finanzas",
                    avoid=None, max_retries: int = 4) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    today = datetime.date.today()
    pilar = content_plan.pilar_del_dia(today, offset=7)   # video usa offset 7
    evitar = content_plan.avoid_text(avoid)

    prompt = f"""Eres guionista de Reels/Shorts en español de México para una cuenta
de finanzas y tecnología llamada "Dinero Simple". Tu público: personas normales en
México, SIN conocimientos financieros. Hablas claro y directo, como a un amigo.
Nada de jerga, nada de frases motivacionales vacías.

PILAR DE HOY (el tema base): {pilar}.
{evitar}
Genera UN guion para un video vertical de 30 a 45 segundos sobre el PILAR de hoy,
con un ángulo fresco, concreto y poco obvio. Usa la fecha como semilla: {today.isoformat()}.

MUY IMPORTANTE — cómo se usa el guion:
El "hook" y el "script" se CONCATENAN y se narran JUNTOS, en ese orden, como una
sola voz continua. Por eso:
- El "script" debe CONTINUAR justo después del hook, SIN repetirlo y SIN parafrasearlo.
- NO empieces el "script" retomando la idea del hook; entra directo al desarrollo.
- Leídos seguidos (hook + " " + script), NO debe haber ninguna frase ni idea repetida
  al inicio. Debe sonar natural, como si una persona hablara de corrido.

Ejemplo de lo que NO se debe hacer:
  hook:   "El error más grande al invertir es dejar tu dinero en el banco."
  script: "El error más grande al invertir es dejarlo en el banco. Los bancos..."  <-- MAL, repite el hook
Ejemplo correcto:
  hook:   "El error más grande al invertir es dejar tu dinero en el banco."
  script: "Tu cuenta de ahorro casi no paga intereses, y la inflación te come el resto..."  <-- BIEN, continúa

Devuelve SOLO un objeto JSON válido, sin markdown ni texto adicional, con estas claves EXACTAS:
{{
  "hook": "primera frase de 1 línea que enganche en los primeros 2 segundos",
  "script": "texto corrido que CONTINÚA después del hook (NO lo repitas), 90-130 palabras, frases cortas",
  "caption": "descripción para el post: 1 gancho + explicación útil + 1 llamado a la acción + 3-5 hashtags",
  "title": "título corto de 3-7 palabras",
  "topic": "identificador corto del tema en minúsculas con guiones (ej: 'comisiones-cajero'); específico al ángulo de HOY",
  "broll_keywords": "2-4 palabras EN INGLÉS para el video de fondo (Pexels). Debe ser una escena CONCRETA de finanzas o tecnología RELACIONADA con el tema de hoy, y variar entre videos. Ejemplos válidos: 'person budgeting notebook', 'counting coins table', 'online banking smartphone', 'paying bills laptop', 'shopping receipts hands', 'stock charts screen', 'atm withdrawal', 'saving money jar', 'calculator spreadsheet desk'. PROHIBIDO: (a) escenas genéricas sin relación con dinero (nada de 'texting', 'messaging', 'chatting', 'person walking', 'cafe coffee'); (b) close-ups de billetes o monedas de un país específico (evita 'cash', 'dollar bills', 'banknotes') para no mostrar dinero extranjero",
  "cards": [
    {{"big": "texto grande, máx ~14 caracteres", "small": "frase corta que lo explica"}}
  ],
  "graphics": []
}}

Reglas para "cards": 0 a 2 elementos. Son rótulos que refuerzan la narración. Si no aportan, deja [].

Reglas para "graphics": 0 o 1 elemento, SOLO si tienes un dato numérico REAL y concreto
que valga la pena animar (no inventes cifras). Si no, deja []. Cada gráfico debe ser
EXACTAMENTE uno de estos dos formatos, con números planos (sin comas ni signo $):
- Contador que sube:
  {{"type": "countup", "value": 3200, "prefix": "$", "suffix": "", "label": "AL AÑO EN COMISIONES"}}
- Barras comparativas (A en rojo vs B en verde):
  {{"type": "bars", "title": "AHORRO A 1 AÑO", "a_label": "EN EL BANCO", "a_value": 385,
    "b_label": "EN CETES", "b_value": 963, "a_color": "red", "b_color": "green", "money": true}}
No uses otros tipos ni omitas claves de estos formatos."""

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