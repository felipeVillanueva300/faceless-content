"""Reglas FIJAS de revisión del guion (sin IA): errores que ya nos pasaron y que el verificador
de Gemini dejó pasar porque son de aritmética o de coherencia con el plan.

Casos reales que las originaron (nov 2026):
- "¿Auto propio o transporte?": $2,000 + $800 + $1,000 ... "Son $4,500" (suman $3,800).
- "Horas de trabajo": "si ganas $4,000 a la quincena" con 80 horas = menos que el salario mínimo.
- Video suelto que decía "El truco de hoy en la serie".
- Muletilla "que no te vean la cara" en casi todos los guiones.
- Capítulos de serie que decían "Parte 2 de 4" en la parte 3, o adelantaban mal la siguiente.

revisar(data) devuelve una lista de problemas (frases en español). En script_gen.py se suman
a los del verificador: si hay alguno se pide UNA reescritura y, si siguen, salen en Telegram
como "Revisa antes de publicar". En los guiones fijos (guiones/*.json) solo avisan.

Variables:
  SALARIO_MINIMO_DIARIO  salario mínimo general vigente (default 315.04, año 2026).
                         ACTUALIZAR cada 1 de enero (la CONASAMI lo anuncia en diciembre).
  FRASES_PROHIBIDAS      frases separadas por ";" (default: "que no te vean la cara").
  REGLAS                 "0" apaga estas reglas.
"""
import os
import re
import unicodedata

REGLAS_ON = os.environ.get("REGLAS", "1").strip().lower() in ("1", "true", "yes")
SALARIO_MINIMO_DIARIO = float(os.environ.get("SALARIO_MINIMO_DIARIO", "315.04") or 315.04)
FRASES_PROHIBIDAS = [f.strip() for f in
                     os.environ.get("FRASES_PROHIBIDAS", "que no te vean la cara").split(";")
                     if f.strip()]

_DIAS_PERIODO = {"dia": 1, "semana": 7, "quincena": 15, "mes": 30}

_MONTO = r"\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
_RE_MONTO = re.compile(_MONTO)

# "... son $4,500", "suman $3,800", "en total $1,200", "te da $600".
_APROX = r"(?:unos|como|casi|más de|mas de|menos de|alrededor de|cerca de|aproximadamente)"
_RE_TOTAL = re.compile(
    r"\b(?:son|suman|en total(?: son)?|total de|te da|te dan)\s+(?:(" + _APROX + r")\s+)?(?:los\s+)?"
    + _MONTO, re.IGNORECASE)

# "si ganas $4,000 a la quincena", "te quedan $8,000 libres al mes", "una quincena de $6,000".
_VERBO_SUELDO = (r"(?:gan[ao]s|ganan|cobr[ao]s|cobran|te pagan|le pagan|te quedan|te llegan|"
                 r"recibes|sueldo de|salario de|ingreso de|ingresos de)")
_RE_SUELDO = re.compile(
    _VERBO_SUELDO + r"\s+(?:unos\s+|solo\s+|apenas\s+)?" + _MONTO
    + r"(?:\s+(?:libres|netos|brutos|limpios))?\s+(?:a la|al|por|cada|de|a)\s+"
    r"(d[ií]a|semana|quincena|mes)\b", re.IGNORECASE)
_RE_QUINCENA_DE = re.compile(r"\b(?:una|tu|su)\s+(quincena|semana)\s+de\s+" + _MONTO,
                             re.IGNORECASE)

_RE_SERIE = re.compile(r"\b(?:en la serie|de la serie|esta serie|la serie de hoy|"
                       r"parte\s+\d+(?:\s+de\s+\d+)?)\b", re.IGNORECASE)
_RE_PARTE_DE = re.compile(r"\bparte\s+(\d+)\s+de\s+(\d+)\b", re.IGNORECASE)
_RE_MANANA_PARTE = re.compile(r"\bmañana[^.!?]{0,40}?\bparte\s+(\d+)\b", re.IGNORECASE)


def _num(txt: str) -> float:
    return float(txt.replace(",", ""))


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _fmt(x: float) -> str:
    return f"${x:,.0f}" if float(x).is_integer() else f"${x:,.2f}"


def minimo(periodo: str) -> float:
    return SALARIO_MINIMO_DIARIO * _DIAS_PERIODO.get(_norm(periodo), 1)


def linea_minimo() -> str:
    """Texto para el prompt: el mínimo vigente por periodo, redondeado."""
    q = round(minimo("quincena") / 100) * 100
    m = round(minimo("mes") / 50) * 50
    return (f"el salario mínimo vigente es ${SALARIO_MINIMO_DIARIO:,.2f} al día (unos ${q:,.0f} "
            f"a la quincena o ${m:,.0f} al mes)")


def _textos(data: dict):
    """(etiqueta, texto) de lo que dice la voz: el hook y cada bloque."""
    out = [("gancho", data.get("hook") or "")]
    for i, b in enumerate(data.get("beats") or [], 1):
        if isinstance(b, dict):
            out.append((f"bloque {i}", b.get("narration") or ""))
    return [(k, t) for k, t in out if t.strip()]


def cuentas(texto: str):
    """Totales que no cuadran con la suma de las cifras que se dijeron antes (en el mismo
    bloque y desde el total anterior). Solo cuando hay 2 o más cifras sumadas."""
    probs = []
    inicio = 0
    for m in _RE_TOTAL.finditer(texto):
        total = _num(m.group(2))
        sumandos = [_num(x) for x in _RE_MONTO.findall(texto[inicio:m.start()])]
        inicio = m.end()
        if len(sumandos) < 2 or total <= 0:
            continue
        suma = sum(sumandos)
        tolerancia = 0.12 if m.group(1) else 0.02
        if abs(suma - total) / total > tolerancia:
            cifras = " + ".join(_fmt(x) for x in sumandos)
            probs.append(f"dice {m.group(0).strip()!r} pero {cifras} = {_fmt(suma)}: "
                         f"la cuenta no cuadra")
    return probs


def sueldo_bajo_minimo(texto: str):
    probs = []
    vistos = set()
    for m in list(_RE_SUELDO.finditer(texto)) + list(_RE_QUINCENA_DE.finditer(texto)):
        if m.re is _RE_SUELDO:
            monto, periodo = _num(m.group(1)), _norm(m.group(2))
        else:
            periodo, monto = _norm(m.group(1)), _num(m.group(2))
        tope = minimo(periodo)
        if (monto, periodo) in vistos or monto >= tope * 0.97:
            continue
        vistos.add((monto, periodo))
        probs.append(f"el ejemplo de sueldo {_fmt(monto)} por {periodo} está por debajo del "
                     f"salario mínimo ({_fmt(round(tope))} por {periodo}); usa un ejemplo realista")
    return probs


def revisar(data: dict) -> list:
    """Lista de problemas encontrados por las reglas fijas ([] si todo bien)."""
    if not REGLAS_ON or not isinstance(data, dict):
        return []
    serie = data.get("serie") if isinstance(data.get("serie"), dict) else None
    try:
        parte = int(serie.get("parte")) if serie else None
        total = int(serie.get("total")) if serie else None
    except (TypeError, ValueError):
        parte = total = None
    probs = []
    for etiqueta, texto in _textos(data):
        for p in cuentas(texto) + sueldo_bajo_minimo(texto):
            probs.append(f"{etiqueta}: {p}")
        if not serie:
            m = _RE_SERIE.search(texto)
            if m:
                probs.append(f"{etiqueta}: dice {m.group(0)!r} y este video NO es de una serie")
        else:
            for m in _RE_PARTE_DE.finditer(texto):
                if parte and total and (int(m.group(1)), int(m.group(2))) != (parte, total):
                    probs.append(f"{etiqueta}: dice {m.group(0)!r} y este capítulo es la "
                                 f"parte {parte} de {total}")
            for m in _RE_MANANA_PARTE.finditer(texto):
                if parte and total and parte >= total:
                    probs.append(f"{etiqueta}: anuncia {m.group(0)!r} y esta es la última parte")
                elif parte and int(m.group(1)) != parte + 1:
                    probs.append(f"{etiqueta}: anuncia {m.group(0)!r} y la que sigue es la "
                                 f"parte {parte + 1}")
        tn = _norm(texto)
        for frase in FRASES_PROHIBIDAS:
            if _norm(frase) in tn:
                probs.append(f"{etiqueta}: usa la muletilla {frase!r}; quítala")
    return probs
