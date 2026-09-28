"""Segunda pasada sobre el guion: REVISOR DE REDACCIÓN + nombres de marca consistentes.

Por qué: Gemini a veces se come palabras al escribir de corrido. Ej. real (reel de fondo
de emergencia): "guárdalo donde rendimiento diario y retiro en días hábiles" (faltaba
"tenga"). La voz lo lee tal cual y se nota.

Qué hace:
1. normalizar_marcas(): escribe SIEMPRE igual los nombres (CetesDirecto, Mercado Pago...)
   para que voz y subtítulos no cambien de forma a media frase. Local, sin costo.
2. revisar(): una llamada barata (flash-lite) que corrige SOLO redacción: oraciones sin
   verbo, palabras faltantes, concordancia, y que las cards no contradigan a la voz.
   Luego se VALIDA cada campo: si el revisor cambió cifras, alargó/acortó de más o
   rompió el formato, se queda el texto original de ESE campo.

Best-effort: si el revisor falla (cuota, red, JSON raro), el guion sigue igual.
NUNCA tumba el video.

Variables:
  SCRIPT_REVIEW        "1" (default) activa; "0" apaga.
  SCRIPT_REVIEW_MODEL  modelo del revisor (default gemini-3.5-flash-lite).
  MARCAS_FIX           extra "como viene=como se escribe;..." (ej. "Nu Mexico=Nu México").
"""
import json
import os
import re
import time

REVIEW_ON = os.environ.get("SCRIPT_REVIEW", "1").strip().lower() in ("1", "true", "yes")
REVIEW_MODEL = os.environ.get("SCRIPT_REVIEW_MODEL", "gemini-3.5-flash-lite").strip()

# patrón (sin distinguir mayúsculas) -> forma oficial
_MARCAS_BASE = [
    (r"\bcetes\s*directo\b", "CetesDirecto"),
    (r"\bmercado\s*pago\b", "Mercado Pago"),
    (r"\bafore\s*m[oó]vil\b", "AforeMóvil"),
]


def _tabla_marcas():
    tabla = list(_MARCAS_BASE)
    for par in os.environ.get("MARCAS_FIX", "").split(";"):
        if "=" in par:
            k, v = par.split("=", 1)
            if k.strip() and v.strip():
                patron = r"\b" + r"\s*".join(re.escape(w) for w in k.split()) + r"\b"
                tabla.append((patron, v.strip()))
    return tabla


def normalizar_marcas(texto: str) -> str:
    if not texto:
        return texto
    for patron, oficial in _tabla_marcas():
        # respeta MAYÚSCULAS: "CETES DIRECTO" -> "CETESDIRECTO" (cards), "Cetes Directo" -> "CetesDirecto"
        texto = re.sub(patron,
                       lambda m, o=oficial: o.upper() if m.group(0).isupper() else o,
                       texto, flags=re.IGNORECASE)
    return texto


def _aplicar_marcas(data: dict) -> dict:
    for k in ("hook", "hook_card", "caption", "title", "script"):
        if isinstance(data.get(k), str):
            data[k] = normalizar_marcas(data[k])
    for b in data.get("beats") or []:
        if isinstance(b, dict) and isinstance(b.get("narration"), str):
            b["narration"] = normalizar_marcas(b["narration"])
    for c in data.get("cards") or []:
        if isinstance(c, dict):
            for k in ("big", "small"):
                if isinstance(c.get(k), str):
                    c[k] = normalizar_marcas(c[k])
    return data


# ---------------------------------------------------------------------------
# Validación de lo que devuelve el revisor
# ---------------------------------------------------------------------------
def _cifras(texto: str):
    """Multiconjunto de cifras del texto, sin separadores: '$24,000' -> '24000'."""
    return sorted(re.sub(r"[,.]", "", n) for n in re.findall(r"\d[\d,.]*\d|\d", texto or ""))


def _campo_ok(original: str, nuevo, max_ratio=1.35, min_ratio=0.75) -> bool:
    if not isinstance(nuevo, str) or not nuevo.strip():
        return False
    if _cifras(original) != _cifras(nuevo):
        return False
    lo, ln = len(original.strip()), len(nuevo.strip())
    if lo >= 12 and not (min_ratio <= ln / lo <= max_ratio):
        return False
    return True


_PROMPT = """Eres corrector de estilo de guiones para videos cortos en español de México.
Te paso un guion en JSON. Corrige SOLO la REDACCIÓN, con cambios MÍNIMOS:

1. Cada oración de "hook" y de "beats" debe estar COMPLETA y tener VERBO CONJUGADO.
   Si falta una palabra (verbo, "que", artículo, preposición), agrégala.
   Mal: "guárdalo donde rendimiento diario y retiro en días hábiles".
   Bien: "guárdalo donde tenga rendimiento diario y retiro en días hábiles".
2. Concordancia de género y número, y ortografía (acentos).
   Quita redundancias obvias sin cambiar el sentido (mal: "te regresa más dinero de
   vuelta"; bien: "te regresa más dinero").
3. Las oraciones se LEEN EN VOZ ALTA seguidas: hook + beats deben sonar naturales.
4. "cards" son RÓTULOS en pantalla: NO necesitan verbo. Solo corrígelas si tienen falta
   de ortografía o si CONTRADICEN lo que dice la narración (ej. la voz dice "retiro en
   días hábiles" y la card "retiro diario": la card debe decir lo mismo que la voz).

PROHIBIDO: cambiar cifras, nombres de apps/instituciones, el sentido, el tono, el orden
o agregar información nueva. NO reescribas frases que ya están bien: déjalas IDÉNTICAS.
Mantén el mismo número de beats y de cards.

Devuelve SOLO JSON con esta forma exacta:
{"hook": "...", "beats": ["narración 1", "narración 2", ...],
 "cards": [{"big": "...", "small": "..."}],
 "cambios": ["antes -> después", ...]}
Si no hay nada que corregir, devuelve lo mismo y "cambios": [].

GUION:
"""


def _llamar(client, payload: dict):
    from google.genai import types
    prompt = _PROMPT + json.dumps(payload, ensure_ascii=False, indent=1)
    ultimo = None
    for intento in range(2):
        try:
            resp = client.models.generate_content(
                model=REVIEW_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0,
                                                   response_mime_type="application/json"),
            )
            txt = (resp.text or "").strip()
            return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        except Exception as e:   # 503/429 transitorio: 1 reintento corto
            ultimo = e
            if intento == 0:
                time.sleep(6)
    raise ultimo


def revisar(data: dict, client=None) -> dict:
    """Devuelve 'data' con redacción corregida y marcas normalizadas.
    Guarda en data['revision'] la lista de cambios aplicados (queda en script.json)."""
    data = _aplicar_marcas(data)
    if not REVIEW_ON:
        return data
    beats = [b for b in (data.get("beats") or []) if isinstance(b, dict)]
    cards = [c for c in (data.get("cards") or []) if isinstance(c, dict)]
    payload = {
        "hook": data.get("hook", ""),
        "beats": [b.get("narration", "") for b in beats],
        "cards": [{"big": c.get("big", ""), "small": c.get("small", "")} for c in cards],
    }
    try:
        if client is None:
            from google import genai
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        rev = _llamar(client, payload)
    except Exception as e:
        print(f"    (revisor de redacción no disponible, sigo con el original: {str(e)[:120]})")
        return data

    aplicados, rechazados = [], 0

    def _tomar(original, nuevo, etiqueta):
        nonlocal rechazados
        nuevo = normalizar_marcas(nuevo) if isinstance(nuevo, str) else nuevo
        if nuevo == original:
            return original
        if _campo_ok(original, nuevo):
            aplicados.append(f"{etiqueta}: {original!r} -> {nuevo!r}")
            return nuevo.strip()
        rechazados += 1
        return original

    data["hook"] = _tomar(payload["hook"], rev.get("hook"), "hook")

    nuevos_beats = rev.get("beats")
    if isinstance(nuevos_beats, list) and len(nuevos_beats) == len(beats):
        for i, (b, n) in enumerate(zip(beats, nuevos_beats)):
            b["narration"] = _tomar(b.get("narration", ""), n, f"bloque {i + 1}")
    elif nuevos_beats is not None:
        rechazados += 1

    nuevas_cards = rev.get("cards")
    if isinstance(nuevas_cards, list) and len(nuevas_cards) == len(cards):
        for i, (c, n) in enumerate(zip(cards, nuevas_cards)):
            if not isinstance(n, dict):
                continue
            for k in ("big", "small"):
                c[k] = _tomar(c.get(k, ""), n.get(k), f"card {i + 1}.{k}")

    if aplicados:
        print(f"    revisor de redacción: {len(aplicados)} corrección(es)")
        for a in aplicados:
            print(f"      - {a}")
    else:
        print("    revisor de redacción: sin correcciones")
    if rechazados:
        print(f"    (revisor: {rechazados} cambio(s) descartado(s) por tocar cifras/largo)")
    data["revision"] = aplicados
    return data