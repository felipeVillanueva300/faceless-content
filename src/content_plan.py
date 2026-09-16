import datetime

COOLDOWN_DIAS = 5

# --------------------------------------------------------------------------
# Pilares (categorias base). El dia que NO es de temporada, se usa esto.
# --------------------------------------------------------------------------
PILARES = [
    {"id": "presupuesto", "nombre": "Presupuesto personal",
     "angulos": ["50/30/20", "base cero", "presupuesto inverso", "quincenal", "margen de error"]},
    {"id": "ahorro", "nombre": "Ahorro",
     "angulos": ["fondo de emergencia", "retos de ahorro", "apartados/cajitas", "ahorro por metas"]},
    {"id": "deudas", "nombre": "Manejo de deudas",
     "angulos": ["bola de nieve vs avalancha", "por qué no pagar el mínimo", "consolidar deudas"]},
    {"id": "inversion", "nombre": "Inversión para principiantes",
     "angulos": ["CETES/CetesDirecto", "SOFIPOs", "fondos", "rendimiento real vs inflación"]},
    {"id": "bancos", "nombre": "Bancos y comisiones",
     "angulos": ["cuenta básica sin comisiones", "comisiones ocultas", "cuentas digitales"]},
    {"id": "credito", "nombre": "Crédito y buró",
     "angulos": ["revisar tu buró gratis", "subir tu score", "mitos del buró", "primera tarjeta"]},
    {"id": "fraudes", "nombre": "Fraudes y seguridad",
     "angulos": ["phishing", "smishing", "apps falsas", "compras seguras", "robo de identidad"]},
    {"id": "fintech", "nombre": "Fintech y apps",
     "angulos": ["Nu", "Klar", "Hey Banco", "Mercado Pago", "comparativas de apps"]},
    {"id": "impuestos", "nombre": "Impuestos básicos",
     "angulos": ["RFC", "deducciones personales", "facturar", "declaración anual"]},
    {"id": "tramites", "nombre": "Trámites y gobierno",
     "angulos": ["Afore: elegir/cambiar", "IMSS", "pensión", "INFONAVIT básico"]},
    {"id": "compras", "nombre": "Compras inteligentes",
     "angulos": ["MSI cuándo sí/no", "Buen Fin", "comparar precios", "suscripciones fantasma"]},
    {"id": "ingresos", "nombre": "Ingresos extra",
     "angulos": ["freelance realista", "vender en línea", "cómo cobrar", "side hustles"]},
    {"id": "tecnologia", "nombre": "Tecnología para tu dinero",
     "angulos": ["hojas de cálculo", "automatización", "IA para finanzas con seguridad"]},
    {"id": "servicios", "nombre": "Servicios y hogar",
     "angulos": ["planes de celular", "CFE/luz", "internet", "renegociar servicios"]},
    {"id": "mentalidad", "nombre": "Mentalidad y hábitos",
     "angulos": ["gastos hormiga", "FOMO financiero", "metas realistas"]},
]

FORMATOS = [
    {"id": "tip", "nombre": "Tip rápido",
     "video": "Da UN consejo accionable y directo que la persona pueda aplicar hoy.",
     "imagen": "'big' = una acción corta en mayúsculas (ej: 'HAZLO HOY'). 'small' = qué hacer y para qué."},
    {"id": "howto", "nombre": "Configuración explicada (paso a paso)",
     "video": "Explica PASO A PASO cómo hacer o activar algo concreto (1, 2, 3). Usa una marca o "
              "plataforma REAL cuando aplique (CetesDirecto, SAT, Afore, apps de banco), sin inventar pasos.",
     "imagen": "'big' = 'PASO A PASO' o el resultado (ej: 'BURÓ GRATIS'). 'small' = el resultado que se logra."},
    {"id": "dato", "nombre": "El dato que sorprende",
     "video": "Arranca con una cifra o hecho concreto que sorprenda y explícalo simple. NO inventes cifras.",
     "imagen": "'big' = la cifra impactante (ej: '$3,200 AL AÑO'). 'small' = frase clara que explica qué significa."},
    {"id": "error", "nombre": "El error común",
     "video": "Nombra el error concreto que comete la gente y di cómo evitarlo.",
     "imagen": "'big' = 'EL ERROR #1'. 'small' = el error concreto en una frase clara."},
    {"id": "mito", "nombre": "Mito vs. realidad",
     "video": "Plantea una creencia falsa común y corrígela con la realidad, claro y breve.",
     "imagen": "'big' = 'MITO'. 'small' = la creencia falsa entre comillas + la verdad corta."},
    {"id": "comparativa", "nombre": "Comparativa simple",
     "video": "Compara dos opciones (A vs B) y di cuál conviene y por qué.",
     "imagen": "'big' = 'A vs B' con dos conceptos cortos. 'small' = cuál conviene y por qué."},
    # Formato extra SOLO para el golpe del día y la reacción (no entra en la rotación normal).
    {"id": "mensaje", "nombre": "Mensaje del día",
     "video": "Mensaje corto y humano para EL día de la fecha: disfruta con conciencia, sin sermón; "
              "un recordatorio ligero de que la cuenta llega después.",
     "imagen": "'big' = frase corta del día. 'small' = recordatorio ligero, sin regañar."},
]

_FORMATO_POR_ID = {f["id"]: f for f in FORMATOS}


# --------------------------------------------------------------------------
# EVENTOS FUERTES: cada uno con su fecha objetivo (mes, dia = el "mero dia").
# La cadencia se dispara alrededor de esa fecha, no toda la ventana.
# --------------------------------------------------------------------------
EVENTOS = [
    {"id": "patrio", "mes": 9, "dia": 15,
     "tema": "las fiestas patrias (la cena del 15, la coperacha, el Grito) sin endeudarte"},
    {"id": "muertos", "mes": 11, "dia": 2,
     "tema": "Día de Muertos: ofrenda, flores y pan sin descontrol"},
    {"id": "buenfin", "mes": 11, "dia": 17,   # aprox; el Buen Fin se mueve cada año, ajusta si hace falta
     "tema": "el Buen Fin: MSI cuándo sí y cuándo no, comprar sin endeudarte"},
    {"id": "aguinaldo", "mes": 12, "dia": 15,
     "tema": "el aguinaldo (qué te toca por ley y cómo administrarlo) y los gastos decembrinos"},
    {"id": "navidad", "mes": 12, "dia": 24,
     "tema": "Navidad: regalos y cena sin arruinar enero"},
    {"id": "reyes", "mes": 1, "dia": 6,
     "tema": "Reyes: rosca y regalos sin deuda, y arranque financiero del año"},
    {"id": "sat_anual", "mes": 4, "dia": 30,
     "tema": "la declaración anual del SAT (personas físicas): qué deducir y cómo, antes de que cierre"},
]

# Golpes de temporada = DÍAS PARA el evento (positivo = falta; 0 = el mero día;
# negativo = ya pasó). Espaciado ~3 días + el mero día + una reacción 2 días después.
# Edita esta lista para cambiar el ritmo (p.ej. mete 12 para arrancar 12 días antes).
RAMPA_OFFSETS = [10, 7, 4, 1, 0, -2]

# Rol de cada golpe: (etiqueta, formato_id, instruccion_extra_para_el_prompt).
# El formato del golpe REEMPLAZA la rotacion normal ese dia, para que los golpes
# de un mismo evento se sientan distintos entre si (dato -> howto -> mito -> tip -> mensaje).
BEATS = {
    10:  ("arranque", "dato",
          "Presenta el impacto o el costo REAL que se viene con esta fecha (sin inventar cifras). "
          "Es el primer aviso: pon el tema sobre la mesa."),
    7:   ("prepárate", "howto",
          "Enséñale a prepararse desde YA (apartar, planear, comparar). Algo accionable, no teoría."),
    4:   ("mito/error", "mito",
          "Desmonta un mito o error MUY común de estas fechas (ej: 'pagar el mínimo de la tarjeta sale gratis')."),
    1:   ("último ajuste", "tip",
          "Checklist o último ajuste para no pasarse justo antes de la fecha."),
    0:   ("el día", "mensaje",
          "Es el día: mensaje corto y humano. Disfruta con conciencia; sin regañar."),
    -2:  ("reacción", "mensaje",
          "Reacciona a lo que se movió/viralizó en la fecha con un ángulo de dinero. REQUIERE revisión humana."),
}

# Ventana en dias para considerar que un evento 'aplica' al buscar su ocurrencia.
_VENTANA_BUSQUEDA = 40


def _between(today, m1, d1, m2, d2) -> bool:
    """¿(mes,día) de hoy cae en el rango [m1/d1 .. m2/d2]? Maneja cruce de año."""
    x = (today.month, today.day)
    a, b = (m1, d1), (m2, d2)
    if a <= b:
        return a <= x <= b
    return x >= a or x <= b


def _delta_a_evento(today, mes, dia):
    """Días de HOY a la fecha objetivo más cercana (maneja cruce de año).
    Positivo = la fecha aún no llega; negativo = ya pasó."""
    candidatos = []
    for y in (today.year - 1, today.year, today.year + 1):
        try:
            f = datetime.date(y, mes, dia)
        except ValueError:
            continue
        candidatos.append((f - today).days)
    # el más cercano a 0 dentro de la ventana
    dentro = [c for c in candidatos if -_VENTANA_BUSQUEDA <= c <= _VENTANA_BUSQUEDA]
    if not dentro:
        return None
    return min(dentro, key=abs)


def evento_del_dia(today=None):
    """¿Hoy es un golpe de temporada? Devuelve dict o None.

    dict: {evento_id, tema, offset, etiqueta, formato_id, instruccion, es_borrador}
    """
    today = today or datetime.date.today()
    for ev in EVENTOS:
        delta = _delta_a_evento(today, ev["mes"], ev["dia"])
        if delta is None:
            continue
        if delta in RAMPA_OFFSETS:
            etiqueta, fmt_id, instr = BEATS[delta]
            return {
                "evento_id": ev["id"],
                "tema": ev["tema"],
                "offset": delta,
                "etiqueta": etiqueta,
                "formato_id": fmt_id,
                "instruccion": instr,
                "es_borrador": delta < 0,   # la 'reacción' post-fecha nunca se autopublica
            }
    return None


def calendario_hint(today=None):
    """Compat: devuelve (tema, peso). Fuerte solo en un golpe de temporada;
    fuera de eso, sin temporada. (Los 'nudges' suaves largos se quitaron a
    propósito: eran los que saturaban de repetición.)"""
    ev = evento_del_dia(today)
    if ev:
        return (ev["tema"], "Fuerte")
    return (None, None)


def plan_del_dia(today=None, offset=0):
    """Elige categoría (enfriamiento de COOLDOWN_DIAS), formato (sin repetir los
    últimos 2) y, si hoy toca golpe de temporada, sobreescribe el formato con el
    del golpe y marca el tema. Devuelve un dict con todo lo que el prompt necesita."""
    today = today or datetime.date.today()

    recientes_pilares, recientes_formatos = [], []
    try:
        from src import history
        recientes_pilares = history.recent_pilares(COOLDOWN_DIAS)   # ids
        recientes_formatos = history.recent_formatos(2)             # nombres
    except Exception:
        pass

    disponibles = [p for p in PILARES if p["id"] not in recientes_pilares] or PILARES
    cat = disponibles[(today.toordinal() + offset) % len(disponibles)]

    fmts = [f for f in FORMATOS if f["nombre"] not in recientes_formatos and f["id"] != "mensaje"] or FORMATOS
    fmt = fmts[today.toordinal() % len(fmts)]

    ev = evento_del_dia(today)
    beat_instr = ""
    es_borrador = False
    if ev:
        # El golpe manda: usa SU formato para que la cuenta regresiva no se repita.
        fmt = _FORMATO_POR_ID.get(ev["formato_id"], fmt)
        beat_instr = ev["instruccion"]
        es_borrador = ev["es_borrador"]

    tema, peso = (ev["tema"], "Fuerte") if ev else (None, None)
    return {
        "categoria_id": cat["id"],
        "categoria_nombre": cat["nombre"],
        "angulos": ", ".join(cat["angulos"]),
        "formato_nombre": fmt["nombre"],
        "formato_video": fmt["video"],
        "formato_imagen": fmt["imagen"],
        "cal_tema": tema,
        "cal_peso": peso,
        # nuevos (los consumidores viejos los ignoran sin romperse):
        "evento_id": ev["evento_id"] if ev else None,
        "evento_beat": ev["etiqueta"] if ev else None,
        "evento_instruccion": beat_instr,
        "publicar_borrador": es_borrador,
    }


def calendario_linea(plan) -> str:
    """Línea lista para el prompt. En un golpe de temporada, además del tema le pasa
    el ROL del golpe (arranque/mito/último ajuste/día/reacción) para que cada uno
    sea distinto."""
    tema, peso = plan.get("cal_tema"), plan.get("cal_peso")
    if not tema:
        return ""
    instr = plan.get("evento_instruccion", "")
    beat = plan.get("evento_beat", "")
    linea = f"TEMA DE TEMPORADA (hoy PRIORÍZALO por encima del pilar): {tema}.\n"
    if beat:
        linea += f"Rol de hoy en la cuenta regresiva ({beat}): {instr}\n"
    return linea


def pilar_del_dia(today=None, offset=0):
    return plan_del_dia(today, offset)["categoria_nombre"]


def avoid_text(recientes, limite=40):
    """Bloque de texto para el prompt con los temas a NO repetir."""
    if not recientes:
        return ""
    lista = "; ".join(recientes[-limite:])
    return ("\nTEMAS YA PUBLICADOS RECIENTEMENTE (está PROHIBIDO repetirlos; "
            f"elige un ángulo o subtema claramente distinto):\n{lista}\n")