"""Plan de contenido COMPARTIDO por imagen y video.

Una sola fuente de verdad para los pilares del nicho y las utilidades de variedad.
Así no se duplican listas entre image_script.py y script_gen.py.
"""
import datetime

# 14 pilares del nicho: aseguran que el tema base cambie a diario.
PILARES = [
    "comisiones bancarias que puedes evitar",
    "suscripciones y cobros automáticos olvidados",
    "cómo empezar a ahorrar (metas y fondo de emergencia)",
    "manejo de deudas y tarjetas de crédito",
    "buró de crédito: cómo funciona y cómo mejorarlo",
    "inversión para principiantes (CETES, fondos, sin jerga)",
    "cómo hacer un presupuesto personal simple",
    "fraudes y seguridad digital con tu dinero",
    "apps y fintech mexicanas útiles",
    "compras inteligentes y no caer en descuentos falsos",
    "impuestos y SAT básico para personas normales",
    "seguros básicos (auto, gastos médicos) explicados fácil",
    "cómo bajar tus recibos (luz, celular, internet)",
    "herramientas de IA para cuidar tus finanzas",
]


def pilar_del_dia(today=None, offset=0):
    """Pilar del día. 'offset' desfasa la rotación: úsalo para que imagen y video
    NO caigan en el mismo pilar el mismo día (ej: video con offset=7)."""
    today = today or datetime.date.today()
    return PILARES[(today.toordinal() + offset) % len(PILARES)]


def avoid_text(recientes, limite=40):
    """Bloque de texto para el prompt con los temas a NO repetir."""
    if not recientes:
        return ""
    lista = "; ".join(recientes[-limite:])
    return ("\nTEMAS YA PUBLICADOS RECIENTEMENTE (está PROHIBIDO repetirlos; "
            f"elige un ángulo o subtema claramente distinto):\n{lista}\n")
