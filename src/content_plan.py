import datetime

COOLDOWN_DIAS = 5   

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
]


def _between(today, m1, d1, m2, d2) -> bool:
    """¿(mes,día) de hoy cae en el rango [m1/d1 .. m2/d2]? Maneja cruce de año."""
    x = (today.month, today.day)
    a, b = (m1, d1), (m2, d2)
    if a <= b:
        return a <= x <= b
    return x >= a or x <= b   


def calendario_hint(today=None):
    """Devuelve (tema_de_temporada, peso) o (None, None). Fuerte = manda casi
    siempre en su ventana; Suave = solo un empujón. Orden: fuertes/específicos primero."""
    today = today or datetime.date.today()
    m, d = today.month, today.day

    if _between(today, 12, 26, 1, 6):
        return ("Año nuevo: propósitos financieros, arranque del año y Reyes sin endeudarte", "Fuerte")
    if m == 1 and d >= 7:
        return ("Cuesta de enero; predial y tenencia con descuento por pago anticipado", "Fuerte")
    if _between(today, 12, 1, 12, 24):
        return ("Aguinaldo (ley y cómo administrarlo), gastos decembrinos y posadas sin deuda", "Fuerte")
    if _between(today, 11, 14, 11, 20):
        return ("Buen Fin: MSI cuándo sí y cuándo no, comprar sin endeudarte", "Fuerte")
    if _between(today, 10, 25, 11, 2):
        return ("Día de Muertos: gastos de ofrenda, flores y pan sin descontrol", "Fuerte")
    if _between(today, 9, 1, 9, 16):
        return ("Mes patrio: presupuesto para las fiestas y el Grito sin endeudarte", "Fuerte")
    if m == 4:
        return ("Declaración anual del SAT (personas físicas): qué deducir y cómo", "Fuerte")
    if _between(today, 7, 1, 8, 31):
        return ("Vacaciones (presupuesto de viaje) y regreso a clases (útiles/uniformes sin deuda)", "Fuerte")
    # Suaves (nudges)
    if _between(today, 9, 20, 11, 10):
        return ("Preparar el Buen Fin: haz tu lista y compara precios con tiempo", "Suave")
    if m == 2 and d in (13, 14):
        return ("San Valentín con presupuesto", "Suave")
    if m == 5 and d in (10, 15):
        return ("Día de las madres / del maestro: regalos con presupuesto", "Suave")
    if _between(today, 6, 15, 6, 21):
        return ("Día del padre: regalo con presupuesto", "Suave")
    return (None, None)


def plan_del_dia(today=None, offset=0):
    """Elige categoría (con enfriamiento de COOLDOWN_DIAS), formato (sin repetir
    los últimos 2) y hint de calendario. Devuelve un dict con todo lo que el prompt
    necesita, más los ids para guardar en el historial."""
    today = today or datetime.date.today()

    recientes_pilares, recientes_formatos = [], []
    try:
        from src import history
        recientes_pilares = history.recent_pilares(COOLDOWN_DIAS)   # lista de ids
        recientes_formatos = history.recent_formatos(2)             # lista de nombres
    except Exception:
        pass

    disponibles = [p for p in PILARES if p["id"] not in recientes_pilares] or PILARES
    cat = disponibles[(today.toordinal() + offset) % len(disponibles)]

    fmts = [f for f in FORMATOS if f["nombre"] not in recientes_formatos] or FORMATOS
    fmt = fmts[today.toordinal() % len(fmts)]

    tema, peso = calendario_hint(today)
    return {
        "categoria_id": cat["id"],
        "categoria_nombre": cat["nombre"],
        "angulos": ", ".join(cat["angulos"]),
        "formato_nombre": fmt["nombre"],
        "formato_video": fmt["video"],
        "formato_imagen": fmt["imagen"],
        "cal_tema": tema,
        "cal_peso": peso,
    }


def calendario_linea(plan) -> str:
    """Línea lista para el prompt según el peso de la temporada."""
    tema, peso = plan.get("cal_tema"), plan.get("cal_peso")
    if not tema:
        return ""
    if peso == "Fuerte":
        return f"TEMA DE TEMPORADA (hoy PRIORÍZALO por encima del pilar): {tema}.\n"
    return f"Si encaja de forma natural, orienta el tema hacia: {tema}.\n"


def pilar_del_dia(today=None, offset=0):
    return plan_del_dia(today, offset)["categoria_nombre"]


def avoid_text(recientes, limite=40):
    """Bloque de texto para el prompt con los temas a NO repetir."""
    if not recientes:
        return ""
    lista = "; ".join(recientes[-limite:])
    return ("\nTEMAS YA PUBLICADOS RECIENTEMENTE (está PROHIBIDO repetirlos; "
            f"elige un ángulo o subtema claramente distinto):\n{lista}\n")