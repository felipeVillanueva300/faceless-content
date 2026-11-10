"""Filtro DURO anti-repetición del reel diario.

Por qué: la lista de "temas y conceptos ya explicados" que va en el prompt es solo una
petición; Gemini a veces la ignora o cambia las palabras. Ej. real: "tarjeta digital para
comprar en línea" salió el 16, el 21 y el 27 de octubre con títulos distintos.

Qué hace: compara el título + concepto del guion nuevo contra lo que ya salió (historial de
los últimos días, diario y series) por RAÍCES de palabras con sentido. Si comparten al menos
2 raíces y eso es la mitad o más de las palabras del más corto, es el mismo tema.
Ej.: "El peligro de usar tu tarjeta de débito en compras online" vs "Por qué debes usar tarjeta
digital en tus compras en línea" -> comparten tarjeta, compras, línea -> repetido.
"""
import re
import unicodedata

# Palabras que no dicen de qué trata el video (conectores, relleno de títulos, genéricas).
_VACIAS = {
    "el", "la", "los", "las", "lo", "un", "una", "unos", "unas", "de", "del", "al", "ante",
    "con", "contra", "en", "entre", "hacia", "hasta", "para", "por", "segun", "sin", "sobre",
    "tras", "que", "como", "cuando", "donde", "cual", "cuales", "quien", "porque", "si", "no",
    "ya", "mas", "muy", "tan", "tu", "tus", "te", "ti", "mi", "mis", "su", "sus", "se", "le",
    "les", "nos", "es", "son", "esta", "este", "estos", "estas", "ese", "esa", "eso", "aqui",
    "ahi", "hay", "ser", "estar", "tener", "tienes", "hacer", "haz", "hace", "puedes", "puede",
    "debes", "debe", "sirve", "usar", "uso", "usa", "dinero", "pesos", "peso", "cuenta",
    "cuentas", "error", "errores", "mito", "mitos", "peligro", "peligroso", "cuidado", "truco",
    "trucos", "consejo", "verdad", "nadie", "dice", "dicen", "cosa", "cosas", "forma", "manera",
    "paso", "pasos", "guia", "gratis", "hoy", "mexico", "banco", "bancos", "parte", "serie",
    "facil", "rapido", "simple", "explicado", "explicada", "secreto", "nunca", "siempre",
    "todo", "todos", "quieres", "necesitas", "saber", "sabias", "real", "mejor", "peor",
    "nuevo", "nueva", "deja", "dejar", "evita", "evitar", "sale", "salir", "gana", "pierdes",
    "realmente", "aunque", "otro", "otra", "cada", "pero", "cara", "vean", "miedo",
    # relleno de títulos gancho ("el costo oculto de...", "lo que arruina tu..."):
    "oculto", "oculta", "ocultos", "ocultas", "arruina", "arruinar", "fracasar", "fracaso",
    "protege", "protegete", "conviene", "vale", "pena", "antes", "despues", "trampa",
}
# Palabras cortas que sí dicen el tema.
_CORTAS_OK = {"nu", "ia", "sat", "cat", "msi"}
# Mismo significado, misma raíz.
_SINONIMOS = {
    "online": "linea", "internet": "linea", "web": "linea", "virtual": "digital",
    "apps": "app", "aplicacion": "app", "aplicaciones": "app",
    "telefono": "celular", "movil": "celular", "smartphone": "celular",
    "pagar": "pago", "sms": "mensaje",
}


def _raiz(w: str) -> str:
    """Quita el plural y deja las primeras 6 letras: 'mensajes'/'mensaje' -> 'mensaj',
    'falsos'/'falso' -> 'falso', 'comprar'/'compras' -> 'compra'."""
    if len(w) > 4 and w.endswith("es") and w[-3] not in "aeiou":
        w = w[:-2]
    elif len(w) > 3 and w.endswith("s") and not w.isdigit():
        w = w[:-1]
    return w[:6]


def raices(texto: str) -> set:
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"(?<=\d)[,.](?=\d{3}\b)", "", t)           # "$25,000" -> "25000"
    out = set()
    for w in re.findall(r"[a-z0-9]+", t):
        w = _SINONIMOS.get(w, w)
        if w in _VACIAS:
            continue
        if len(w) < 3 and w not in _CORTAS_OK and not (w.isdigit() and len(w) >= 2):
            continue
        out.add(_raiz(w))
    return out


def _texto_registro(r: dict) -> str:
    t = " ".join(x for x in (r.get("titulo"), r.get("concepto")) if x)
    return t or (r.get("topic") or "").replace("-", " ")


def parecido(data: dict, registros, minimo: int = 2, proporcion: float = 0.5):
    """El registro del historial que trata el MISMO tema que 'data', o None."""
    nuevo = raices(f"{data.get('title', '')} {data.get('concepto', '')}")
    if not nuevo:
        return None
    mejor, mejor_score = None, 0.0
    for r in registros or []:
        previo = raices(_texto_registro(r))
        if not previo:
            continue
        comunes = nuevo & previo
        if len(comunes) < minimo:
            continue
        score = len(comunes) / min(len(nuevo), len(previo))
        if score >= proporcion and score > mejor_score:
            mejor, mejor_score = r, score
    return mejor
