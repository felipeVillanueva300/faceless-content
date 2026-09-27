"""Datos económicos VIGENTES de México, leídos en cada corrida desde la API oficial
de Banxico (SIE). Así Gemini no inventa tasas ni inflación y nadie tiene que actualizar
nada a mano.

Necesita el secret BANXICO_TOKEN (gratis, se pide una vez en
https://www.banxico.org.mx/SieAPIRest/service/v1/token).

Si la API falla o no hay token, se usa la variable DATOS_ACTUALES (respaldo manual).
Si tampoco existe, devuelve "" y el prompt le prohíbe a Gemini dar tasas como hecho.

Las etiquetas salen del propio 'titulo' que regresa Banxico, así que el texto siempre
describe correctamente la serie consultada.
"""
import os
import requests

# Series del SIE (se pueden cambiar sin tocar código con BANXICO_SERIES="id1,id2,...")
#   SP30578  inflación general anual (INPC)
#   SF61745  tasa objetivo de Banxico
#   SF43936  CETES a 28 días
#   SF43942  CETES a 182 días
#   SF43718  tipo de cambio FIX (pesos por dólar)
_SERIES_DEFAULT = "SP30578,SF61745,SF43936,SF43942,SF43718"
_URL = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/{ids}/datos/oportuno"


def _corto(titulo: str) -> str:
    """Recorta títulos largos del SIE a algo legible para el prompt."""
    t = " ".join((titulo or "").split())
    return t[:140]


def desde_banxico(timeout: int = 20) -> str:
    token = os.environ.get("BANXICO_TOKEN", "").strip()
    if not token:
        return ""
    ids = os.environ.get("BANXICO_SERIES", _SERIES_DEFAULT).replace(" ", "")
    r = requests.get(_URL.format(ids=ids), headers={"Bmx-Token": token}, timeout=timeout)
    r.raise_for_status()
    partes = []
    for serie in r.json().get("bmx", {}).get("series", []):
        datos = serie.get("datos") or []
        if not datos:
            continue
        dato, fecha = datos[-1].get("dato", ""), datos[-1].get("fecha", "")
        if not dato or dato.upper() == "N/E":
            continue
        partes.append(f"{_corto(serie.get('titulo', serie.get('idSerie', '')))}: {dato} (al {fecha})")
    if not partes:
        return ""
    return "Fuente Banxico (SIE). " + " | ".join(partes)


def datos_actuales() -> str:
    """Banxico en vivo -> respaldo manual DATOS_ACTUALES -> ''. Nunca lanza error."""
    try:
        txt = desde_banxico()
        if txt:
            print(f"    datos vigentes (Banxico): {txt[:160]}...")
            return txt
    except Exception as e:
        print(f"    (Banxico no disponible: {str(e)[:120]}; uso respaldo)")
    manual = os.environ.get("DATOS_ACTUALES", "").strip()
    if manual:
        print("    datos vigentes (variable DATOS_ACTUALES)")
    else:
        print("    (sin datos vigentes: Gemini no dará tasas como hecho)")
    return manual
