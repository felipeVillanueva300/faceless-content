import os
import datetime

COOLDOWN_DIAS = 5
TECH_CADA_DIAS = 3   

# --------------------------------------------------------------------------
# Pilares (categorias base). El dia que NO es de temporada, se usa esto.
# --------------------------------------------------------------------------

PILARES = [
    {"id": "presupuesto", "tipo": "fin", "nombre": "Presupuesto personal",
     "angulos": ["50/30/20", "base cero", "presupuesto inverso", "quincenal", "margen de error"]},
    {"id": "ahorro", "tipo": "fin", "nombre": "Ahorro",
     "angulos": ["fondo de emergencia", "retos de ahorro", "apartados/cajitas", "ahorro por metas"]},
    {"id": "deudas", "tipo": "fin", "nombre": "Manejo de deudas",
     "angulos": ["bola de nieve vs avalancha", "por qué no pagar el mínimo", "consolidar deudas",
                 "negociar una quita", "cobranza abusiva y cómo reportarla (REDECO)",
                 "préstamos gota a gota y apps montadeudas", "reestructurar una deuda"]},
    {"id": "inversion", "tipo": "fin", "nombre": "Inversión para principiantes",
     "angulos": ["CETES/CetesDirecto", "SOFIPOs", "fondos", "rendimiento real vs inflación"]},
    {"id": "bancos", "tipo": "fin", "nombre": "Bancos y comisiones",
     "angulos": ["cuenta básica sin comisiones", "comisiones ocultas", "cuentas digitales"]},
    {"id": "credito", "tipo": "fin", "nombre": "Crédito y buró",
     "angulos": ["revisar tu buró gratis", "subir tu score", "mitos del buró", "primera tarjeta"]},
    {"id": "impuestos", "tipo": "fin", "nombre": "Impuestos básicos",
     "angulos": ["RFC", "deducciones personales", "facturar", "declaración anual"]},
    {"id": "tramites", "tipo": "fin", "nombre": "Trámites y gobierno",
     "angulos": ["Afore: elegir/cambiar", "IMSS", "pensión", "INFONAVIT básico"]},
    {"id": "compras", "tipo": "fin", "nombre": "Compras inteligentes",
     "angulos": ["MSI cuándo sí/no", "Buen Fin", "comparar precios", "suscripciones fantasma"]},
    {"id": "ingresos", "tipo": "fin", "nombre": "Ingresos extra",
     "angulos": ["freelance realista", "vender en línea", "cómo cobrar", "side hustles"]},
    {"id": "servicios", "tipo": "fin", "nombre": "Servicios y hogar",
     "angulos": ["planes de celular", "CFE/luz", "internet", "renegociar servicios"]},
    {"id": "mentalidad", "tipo": "fin", "nombre": "Mentalidad y hábitos",
     "angulos": ["gastos hormiga", "FOMO financiero", "metas realistas"]},
    {"id": "trabajo", "tipo": "fin", "nombre": "Tu dinero y tu trabajo",
     "angulos": ["calcular tu aguinaldo", "finiquito vs liquidación", "prima vacacional",
                 "leer tu recibo de nómina", "reparto de utilidades (PTU)", "horas extra"]},
    {"id": "vivienda", "tipo": "fin", "nombre": "Vivienda",
     "angulos": ["rentar vs comprar", "crédito Infonavit paso a paso", "depósito de renta",
                 "predial y descuentos por pago anticipado", "gastos ocultos al comprar casa"]},
    {"id": "auto", "tipo": "fin", "nombre": "Auto y transporte",
     "angulos": ["cuánto cuesta de verdad tener coche", "seguro de auto: qué cubre",
                 "crédito automotriz y CAT", "gasolina y mantenimiento que ahorra", "auto usado sin fraude"]},
    {"id": "seguros", "tipo": "fin", "nombre": "Seguros y salud financiera",
     "angulos": ["seguro de gastos médicos vs IMSS", "seguro de vida: cuándo sí", "qué es un deducible",
                 "microseguros baratos", "qué hacer si te niegan un reembolso"]},
    {"id": "familia", "tipo": "fin", "nombre": "Dinero en familia",
     "angulos": ["hablar de dinero en pareja", "enseñar a tus hijos a ahorrar", "tandas: riesgos",
                 "prestar dinero a familiares", "remesas sin comisiones altas", "gastos de la escuela"]},
    {"id": "consumidor", "tipo": "fin", "nombre": "Tus derechos como consumidor",
     "angulos": ["PROFECO: cómo poner una queja", "garantías y devoluciones", "letras chiquitas de un contrato",
                 "cancelar un servicio que no te dejan cancelar", "precios engañosos"]},
    # --- Pilares TECH (garantizamos que salgan seguido) ---
    {"id": "fraudes", "tipo": "tech", "nombre": "Fraudes y seguridad digital",
     "angulos": ["fraude por WhatsApp/SMS", "links y apps falsas", "activar 2FA",
                 "compras seguras en línea", "robo de identidad", "revisar permisos de apps"]},
    {"id": "fintech", "tipo": "tech", "nombre": "Fintech y apps",
     "angulos": ["Nu", "Klar", "Hey Banco", "Mercado Pago", "cómo elegir app segura",
                 "apartados/cajitas", "comparar apps de banco"]},
    {"id": "tecnologia", "tipo": "tech", "nombre": "Tecnología para tu dinero",
     "angulos": ["IA para organizar tu dinero", "apps de presupuesto", "automatizar pagos",
                 "cancelar suscripciones desde el cel", "hojas de cálculo simples"]},
    {"id": "privacidad", "tipo": "tech", "nombre": "Privacidad y cuentas seguras",
     "angulos": ["gestor de contraseñas gratis", "qué hacer si te hackean WhatsApp",
                 "SIM swapping y cómo protegerte", "tus datos en apps de préstamo", "respaldo del celular"]},
    {"id": "compras_linea", "tipo": "tech", "nombre": "Compras en línea",
     "angulos": ["Temu/Shein: impuestos y aduana", "Mercado Libre: compra protegida", "tarjeta digital para comprar",
                 "detectar tiendas falsas", "devoluciones en línea"]},
    {"id": "ia", "tipo": "tech", "nombre": "IA para tu dinero",
     "angulos": ["usar IA para armar tu presupuesto", "IA para comparar precios", "prompts útiles para finanzas",
                 "estafas hechas con IA (voz clonada)", "qué NO compartir con una IA"]},
    {"id": "digital", "tipo": "tech", "nombre": "Dinero digital y pagos",
     "angulos": ["SPEI y CoDi sin comisión", "qué es tu CLABE", "transferencias seguras",
                 "domiciliación (y cómo cancelarla)", "e.firma / SAT en línea", "apps de gobierno"]},
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


def serie_override():
    """Lee de variables de entorno una SERIE forzada (Parte N de un tema).

    Cuando quieres una 'Parte 2/3…' de un tema concreto (ej. manejo de tarjeta:
    fecha de corte, fecha de pago, cuándo comprar), disparas el workflow a mano con
    estas variables y ESE día el pipeline ignora el pilar aleatorio y hace justo esa
    parte, sin repetir lo que ya dijiste en las partes anteriores.

    Variables (todas opcionales salvo SERIE_TEMA):
      SERIE_TEMA      -> el tema de la serie (ej: "cómo manejar tu tarjeta de crédito")
      SERIE_PARTE     -> número de parte (ej: "2")
      SERIE_TOTAL     -> total de partes, si lo sabes (ej: "4")
      SERIE_SUBTEMA   -> qué toca EXACTAMENTE hoy (ej: "la fecha de pago y cuándo comprar")
      SERIE_ANTERIOR  -> qué YA se cubrió en partes previas, para NO repetirlo
                         (ej: "Parte 1 explicó qué es la fecha de corte")
      SERIE_FORMATO   -> id de formato opcional (tip, howto, dato, error, mito, comparativa)
      SERIE_SIGUIENTE -> de qué trata la SIGUIENTE parte (para adelantarla bien).
                         Vacío + parte == total -> es el último capítulo y cierra la serie.

    Devuelve dict o None."""
    tema = os.environ.get("SERIE_TEMA", "").strip()
    if not tema:
        return None
    return {
        "tema": tema,
        "parte": os.environ.get("SERIE_PARTE", "").strip(),
        "total": os.environ.get("SERIE_TOTAL", "").strip(),
        "subtema": os.environ.get("SERIE_SUBTEMA", "").strip(),
        "anterior": os.environ.get("SERIE_ANTERIOR", "").strip(),
        "formato_id": os.environ.get("SERIE_FORMATO", "").strip().lower(),
        "siguiente": os.environ.get("SERIE_SIGUIENTE", "").strip(),
    }


def plan_del_dia(today=None, offset=0):
    """Elige categoría (enfriamiento de COOLDOWN_DIAS), formato (sin repetir los
    últimos 2) y, si hoy toca golpe de temporada, sobreescribe el formato con el
    del golpe y marca el tema. Si hay una SERIE forzada (ver serie_override),
    esa manda por encima de todo. Devuelve un dict con todo lo que el prompt necesita."""
    today = today or datetime.date.today()

    # --- SERIE forzada: manda por encima del pilar y de la temporada ---
    serie = serie_override()
    if serie:
        fmt = _FORMATO_POR_ID.get(serie["formato_id"])
        if not fmt:
            # sin formato explícito: how-to encaja para "parte N paso a paso"
            fmt = _FORMATO_POR_ID.get("howto", FORMATOS[0])
        etiqueta_parte = ""
        if serie["parte"]:
            etiqueta_parte = f"Parte {serie['parte']}"
            if serie["total"]:
                etiqueta_parte += f" de {serie['total']}"
        return {
            "categoria_id": "serie",
            "categoria_nombre": serie["tema"],
            "angulos": serie["subtema"] or "continúa la serie con el siguiente punto lógico",
            "formato_nombre": fmt["nombre"],
            "formato_video": fmt["video"],
            "formato_imagen": fmt["imagen"],
            "cal_tema": None,
            "cal_peso": None,
            "evento_id": None,
            "evento_beat": None,
            "evento_instruccion": "",
            "publicar_borrador": False,
            # datos de la serie para el prompt y el historial:
            "serie_tema": serie["tema"],
            "serie_parte": serie["parte"],
            "serie_etiqueta": etiqueta_parte,
            "serie_subtema": serie["subtema"],
            "serie_anterior": serie["anterior"],
            "serie_total": serie["total"],
            "serie_siguiente": serie["siguiente"],
        }

    recientes_pilares, recientes_formatos, recientes_tech = [], [], []
    try:
        from src import history
        recientes_pilares = history.recent_pilares(COOLDOWN_DIAS)     # ids (enfriamiento)
        recientes_formatos = history.recent_formatos(2)              # nombres
        recientes_tech = history.recent_pilares(TECH_CADA_DIAS)      # ids ventana corta
    except Exception:
        pass

    tech_ids = {p["id"] for p in PILARES if p.get("tipo") == "tech"}
    disponibles = [p for p in PILARES if p["id"] not in recientes_pilares] or PILARES

    if not any(pid in tech_ids for pid in recientes_tech):
        tech_disp = [p for p in disponibles if p["id"] in tech_ids]
        if tech_disp:
            disponibles = tech_disp

    cat = disponibles[(today.toordinal() + offset) % len(disponibles)]

    usados = []
    try:
        from src import history
        usados = history.recent_conceptos(120)
    except Exception:
        pass
    angulos_frescos = [a for a in cat["angulos"] if not _ya_usado(a, usados)]
    angulos_txt = ", ".join(angulos_frescos) if angulos_frescos else (
        "los ángulos típicos ya se usaron: propone uno NUEVO y concreto de este pilar")

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
        "angulos": angulos_txt,
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


def _cierre_serie(plan) -> str:
    """Instrucción para el FINAL de un capítulo: adelantar EXACTAMENTE la siguiente parte,
    o cerrar la serie si es la última. Nunca dejar que Gemini adivine el siguiente tema."""
    parte, total = plan.get("serie_parte") or "", plan.get("serie_total") or ""
    siguiente = plan.get("serie_siguiente") or ""
    try:
        ultima = bool(total) and int(parte) >= int(total)
    except ValueError:
        ultima = False
    if ultima:
        return ("Es el ÚLTIMO capítulo: al final CIERRA la serie (resume en 1 frase lo que ya "
                "sabe hacer quien la vio completa). PROHIBIDO decir que viene otra parte; el "
                "llamado es a seguir la cuenta para la próxima serie.\n")
    if siguiente:
        try:
            num = f"Parte {int(parte) + 1}"
        except ValueError:
            num = "siguiente parte"
        return (f"Al final adelanta la {num} con EXACTAMENTE este tema, resumido en máximo 8 "
                f"palabras (PROHIBIDO prometer otro tema): {siguiente}.\n")
    return ("Al final di que viene la siguiente parte SIN decir de qué trata (no lo sabes; "
            "PROHIBIDO inventarlo).\n")


def calendario_linea(plan) -> str:
    """Línea lista para el prompt. Si hay SERIE forzada, emite la directiva de la
    serie (Parte N, qué toca hoy, qué NO repetir). Si no, y hay golpe de temporada,
    pasa el tema + el ROL del golpe para que cada golpe sea distinto."""
    # --- SERIE forzada ---
    if plan.get("serie_tema"):
        if not plan.get("serie_parte"):
            linea = (f"TEMA FORZADO DE HOY (ignora el pilar normal): \"{plan['serie_tema']}\". "
                     f"Es un video SUELTO: PROHIBIDO decir 'parte', 'capítulo', 'serie' o "
                     f"número de parte, y PROHIBIDO decir que 'viene la siguiente parte'.\n"
                     f"Si toca un concepto, explica el PORQUÉ con un mecanismo causa → efecto y un "
                     f"ejemplo cotidiano de México, no solo QUÉ es.\n")
        else:
            etiqueta = plan.get("serie_etiqueta") or f"Parte {plan['serie_parte']}"
            linea = (f"SERIE (hoy IGNORA el pilar normal): esto es la {etiqueta} de una serie "
                     f"sobre \"{plan['serie_tema']}\". Debe sentirse CONTINUACIÓN, no un video suelto: "
                     f"menciona al inicio que es la {etiqueta}.\n"
                     f"{_cierre_serie(plan)}"
                     f"La mención de la parte va en MÁXIMO 6 palabras, pegada al valor y con el número "
                     f"CORRECTO ({etiqueta}). PROHIBIDO el preámbulo de serie ('conceptos que "
                     f"nadie te explicó', 'empecemos por lo básico'): cada segundo cuenta.\n"
                     f"Si toca un concepto, explica el PORQUÉ con un mecanismo causa → efecto y un "
                     f"ejemplo cotidiano de México, no solo QUÉ es.\n")
        if plan.get("serie_subtema"):
            linea += f"Lo que toca EXACTAMENTE hoy (no te desvíes): {plan['serie_subtema']}.\n"
        if plan.get("serie_anterior"):
            linea += (f"Ya se cubrió en partes anteriores (PROHIBIDO repetirlo, solo puedes "
                      f"referirlo en 1 frase): {plan['serie_anterior']}.\n")
        return linea

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


_VACIAS = {"de", "la", "el", "los", "las", "y", "en", "tu", "tus", "para", "con", "por", "que",
           "como", "vs", "del", "al", "un", "una", "sin", "mas", "metodo", "dinero", "pesos",
           "cuenta", "cuando", "tips", "truco", "error", "mito", "guia", "paso", "sobre", "hacer",
           # palabras de PILAR (demasiado generales para bloquear un ángulo):
           "ahorro", "ahorrar", "deuda", "deudas", "banco", "bancos", "tarjeta", "credito",
           "invertir", "inversion", "pagar", "gastos", "interes", "intereses", "mexico", "apps"}


def _palabras(t: str):
    import re
    import unicodedata
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return {w for w in re.findall(r"[a-z0-9]+", t) if len(w) >= 5 and w not in _VACIAS}


def _ya_usado(angulo: str, usados) -> bool:
    """True si el ángulo comparte una palabra clave con un concepto reciente
    ('bola de nieve vs avalancha' vs 'metodo avalancha deudas' -> 'avalancha')."""
    pa = _palabras(angulo)
    return any(pa & _palabras(u) for u in usados)


def avoid_text(recientes, limite=60, conceptos=None):
    """Bloque de texto para el prompt con los temas y CONCEPTOS a NO repetir."""
    out = ""
    if recientes:
        lista = "; ".join(recientes[-limite:])
        out += ("\nTEMAS YA PUBLICADOS RECIENTEMENTE (está PROHIBIDO repetirlos; "
                f"elige un ángulo o subtema claramente distinto):\n{lista}\n")
    if conceptos:
        out += ("CONCEPTOS YA EXPLICADOS (PROHIBIDO volver a explicarlos aunque cambies las palabras, "
                "el ejemplo o el formato; ej.: si ya salió 'método avalancha', no hagas 'paga primero "
                f"la deuda más cara'):\n{'; '.join(conceptos[-80:])}\n")
    return out