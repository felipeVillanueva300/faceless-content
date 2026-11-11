"""Cliente de Gemini con tiempo límite por llamada.

Por qué: sin límite, una llamada que se queda colgada se come los 15-25 minutos del paso
y el job muere sin decir nada (10 nov: 3 intentos de 15 min, sin un solo mensaje).
Con límite, la llamada falla rápido y el código ya sabe qué hacer: probar el siguiente
modelo o seguir sin ese paso.

GEMINI_TIMEOUT (segundos, default 240) cambia el límite sin tocar código.
Con el límite, Gemini a veces contesta 504 DEADLINE_EXCEEDED: también cuenta como "no contestó".
"""
import os

TIMEOUT_S = int(os.environ.get("GEMINI_TIMEOUT", "240"))


def cliente(api_key: str = None, timeout_s: int = None):
    from google import genai
    from google.genai import types
    segundos = timeout_s or TIMEOUT_S
    return genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"],
                        http_options=types.HttpOptions(timeout=segundos * 1000))


def es_timeout(e) -> bool:
    """True si el error es porque Gemini no contestó a tiempo."""
    if getattr(e, "code", None) == 504 or "DEADLINE_EXCEEDED" in str(e):
        return True
    return (isinstance(e, TimeoutError) or "timeout" in type(e).__name__.lower()
            or "timed out" in str(e).lower())
