import os
import json
import time
import datetime
from google import genai
from google.genai import types
from google.genai import errors

from src import content_plan

def _model_ladder():
    lista = os.environ.get("GEMINI_MODELS", "").strip()
    if lista:
        modelos = [m.strip() for m in lista.split(",") if m.strip()]
    else:
        modelos = [os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()]
    # sin duplicados, conservando el orden
    vistos, out = set(), []
    for m in modelos:
        if m and m not in vistos:
            vistos.add(m)
            out.append(m)
    return out


_DAILY_QUOTA_MARKS = ("PerDay", "GenerateRequestsPerDay", "free_tier_requests",
                      "RequestsPerDay")


def _is_daily_quota(err) -> bool:
    msg = str(err)
    return any(mark in msg for mark in _DAILY_QUOTA_MARKS)


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
    plan = content_plan.plan_del_dia(today, offset=7)   # video usa offset 7
    evitar = content_plan.avoid_text(avoid)
    cal = content_plan.calendario_linea(plan)

    prompt = f"""Eres guionista de Reels/Shorts en español de México para una cuenta
de finanzas y tecnología llamada "Dinero Simple". Tu público: personas normales en
México, SIN conocimientos financieros. Hablas claro y directo, como a un amigo.
Nada de jerga, nada de frases motivacionales vacías.

IDENTIDAD Y PERSONALIDAD (refuérzala SIEMPRE, es lo que hace única a la cuenta):
"Dinero Simple" está del lado de la gente: es el amigo que TE DEFIENDE para que NO te
vean la cara con tu dinero. Ángulo central: "lo que el banco/las apps/las letras chiquitas
NO te dicen, yo sí". Tono: directo, cómplice y protector — como un amigo que te dice la
verdad que otros te esconden, con un toque de "no te dejes". NADA de conspiración,
alarmismo falso ni odio; es defender al usuario con datos reales y consejos accionables.
Frases que reflejan la voz (úsalas de vez en cuando, no forzadas): "que no te vean la
cara", "el banco no te lo va a decir", "no te dejes cobrar de más".
Es una SERIE diaria: UN truco corto CADA DÍA. Que se sienta continua ("hoy te toca…",
"el de hoy…") para dar razón de seguir y esperar el de mañana.

PILAR DE HOY: {plan['categoria_nombre']} (ángulos posibles: {plan['angulos']}).
FORMATO DE HOY: {plan['formato_nombre']}. {plan['formato_video']}
{cal}{evitar}
Genera UN guion para un video vertical sobre el PILAR y el FORMATO de hoy, con un ángulo
fresco, concreto y poco obvio. Usa la fecha como semilla: {today.isoformat()}.

DURACIÓN FLEXIBLE (clave): el video dura entre 25 y 60 segundos. NO rellenes para llegar
a un número. Usa el tiempo que el tema NECESITE para quedar BIEN explicado:
- Tema simple -> corto (30-45s). Tema que necesita matiz o pasos -> más largo (hasta 60s).
- Prohibido el relleno/preámbulo ("hoy te voy a contar…", "muchos no saben que…"). El
  PRIMER bloque entra directo al valor.

CALIDAD DEL CONSEJO (lo más importante): da el consejo MÁS ÚTIL y COMPLETO, no el obvio
ni el técnicamente-correcto-pero-flojo. Incluye SIEMPRE el matiz práctico que ayuda a
quien NO está en el caso ideal. Ejemplos del nivel que quiero:
- Tarjeta: no digas solo "paga el total". Di que si no puedes el total, pagues al menos
  el monto que EVITA intereses (el saldo al corte), y dónde ver esa opción en la app.
- Ahorro: no digas solo "ahorra". Di cuánto, cómo automatizarlo y dónde.
EXPLICA EL PORQUÉ, NO SOLO EL QUÉ: si el tema es un concepto (inflación, intereses,
CAT, Afore...), dedica UN bloque al mecanismo causa → efecto en palabras de la calle y con
un ejemplo de México. Mal: "la inflación hace que suban los precios" (eso es el QUÉ).
Bien: "si al tortillero le sube el gas y el transporte, sube el kilo; y cuando todos suben
al mismo tiempo, tu sueldo compra menos" (eso es el PORQUÉ). Una causa bien explicada vale
más que tres mencionadas.
TODO LO QUE NOMBRAS, LO EXPLICAS: cada método, término o sigla que menciones (50/30/20,
base cero, CAT, Afore, SOFIPO...) se DEFINE en su propio bloque, en palabras simples y con
un ejemplo en pesos. Ej: "50/30/20: de una quincena de $8,000, $4,000 a lo necesario
(renta, luz, súper), $2,400 a gustos y $1,600 a ahorro". Nombrar algo sin explicarlo deja
al que ve con un hueco, y se va.
- Si comparas DOS métodos, cada uno lleva su bloque (qué es + ejemplo en pesos) ANTES de
  decir cuál conviene. Si no te caben los dos bien explicados en 60 s, habla de UNO solo.
- Mejor un solo concepto completo que dos a medias.
- Las frases de la marca ("no te dejes cobrar", "que no te vean la cara") solo si vienen
  al caso; si nadie te está cobrando nada en el tema, no las uses.
Si el consejo cabe en una frase obvia, te faltó el matiz. Un solo consejo, bien explicado,
mejor que tres a medias.

EL GANCHO (lo más importante — decide si te ven o te saltan en 1 segundo):
El "hook" NO es el título del tema. Es un FRENO DE SCROLL. Debe hacer que la persona
piense "espera, ¿qué?". Usa UNA de estas fórmulas:
- Cifra + consecuencia concreta: "Pagar el mínimo puede costarte 3 años y el doble de tu deuda."
- Callout que pica (háblale directo y con algo en juego): "Si pagas el mínimo de tu tarjeta, el banco te lo agradece — y tú lo pagas carísimo."
- Error/pérdida con la que se identifican: "Estás regalándole dinero a tu banco cada mes sin darte cuenta."
- Pregunta que incomoda: "¿Sabes cuánto de tu pago mínimo se va SOLO a intereses? Te va a doler."
PROHIBIDO como gancho: enunciar el tema ("El error del pago mínimo", "Hoy hablaremos de…",
"El pago mínimo de la tarjeta"). Eso NO engancha. Prohibido el preámbulo.
CIFRAS (somos cuenta de finanzas: la confianza es todo):
- Usa solo cifras que puedas respaldar (Banxico, INEGI, CONDUSEF, la app o el banco). Si
  la cifra es un EJEMPLO ilustrativo, dilo ("por ejemplo", "si tu tarjeta cobra 60%...").
- Si en el guion usas un dato real, el caption lo cierra con "Fuente: <institución, año>".
  Si no estás seguro de la cifra exacta, usa una consecuencia sin número.
Reglas: concreto, con una cifra o consecuencia real (sin inventar cifras), en segunda
persona ("tú/tu"), y que genere una PREGUNTA en la cabeza del que ve. Si tu hook podría
ser el subtítulo de un libro de texto, está mal.

MUY IMPORTANTE — cómo se arma el guion (POR BLOQUES):
El guion se cuenta en BLOQUES ("beats"). El "hook" se narra primero, y luego los
bloques en orden, como una sola voz continua. Cada bloque tiene su propia frase y su
propia escena de fondo, para que la imagen CAMBIE justo cuando la voz llega a ese punto.
- El primer bloque CONTINÚA justo después del hook, SIN repetirlo ni parafrasearlo.
- Leídos seguidos (hook + bloques), debe sonar natural, como alguien hablando de corrido.
- Longitud según lo que el tema necesite: ~70-200 palabras entre TODOS los bloques. Si
  el tema es un método, una comparación o un paso a paso, usa MÍNIMO ~120 palabras: la
  gente necesita el ejemplo para entenderlo. Cada
  bloque = UNA idea, sin apurar. El ÚLTIMO bloque cierra con un llamado a seguir corto
  (ej: 'Sígueme, mañana va otro.').
- Cada bloque va con su "scene": 2-4 palabras EN INGLÉS, escena CONCRETA de finanzas/
  tecnología ligada a LO QUE DICE ESE BLOQUE, distinta entre bloques.
- PROHIBIDO en "scene": efectivo de cualquier tipo (money, cash, banknotes, bills, coins,
  currency, pesos, dollars). Los bancos de video solo tienen billetes de OTROS países.
  Para hablar de dinero muestra cosas que sí son de aquí y de hoy: tarjeta, celular con
  app del banco, terminal de pago, carrito del súper, calculadora, recibo, laptop con
  gráficas, alcancía, persona pensativa revisando su celular.

Devuelve SOLO un objeto JSON válido, sin markdown ni texto adicional, con estas claves EXACTAS:
{{
  "hook": "FRENO DE SCROLL de 1 línea (ver EL GANCHO arriba): cifra+consecuencia, callout que pica, o pregunta que incomoda. En segunda persona. NUNCA el título del tema.",
  "hook_card": "versión MUY CORTA del hook para mostrarla GRANDE los primeros ~2.5s: 3-6 palabras con TENSIÓN, no el nombre del tema. Bien: '¿3 AÑOS PAGANDO?', 'LE REGALAS DINERO AL BANCO', 'TE VA A DOLER'. Mal: 'EL ERROR DEL PAGO MÍNIMO' (eso es el tema, no engancha). Debe entenderse SOLA y NO cambiar el sentido por acortar (mal: 'para médicos'; bien: 'gastos médicos')",
  "beats": [
    {{"narration": "frase del bloque 1 (continúa el hook, entra al desarrollo)", "scene": "credit card hand"}},
    {{"narration": "frase del bloque 2", "scene": "calendar planner desk"}},
    {{"narration": "frase del bloque 3", "scene": "online banking phone"}},
    {{"narration": "frase del bloque 4, cierra con el llamado a seguir", "scene": "shopping online laptop"}}
  ],
  "caption": "PRIMERA línea = la frase que la gente escribiría en el buscador de IG/TikTok/YouTube sobre este tema (ej: 'Cómo usar meses sin intereses sin endeudarte'); luego 2-3 frases útiles, luego un llamado claro a SEGUIR + guardar (ej: 'Sígueme @dinerosimplemx para un truco diario y guarda este para no olvidarlo.'), y OBLIGATORIO cerrar con una línea aparte de EXACTAMENTE 5 hashtags en español de México (nunca los omitas), mezclando 2 generales y 3 del tema. Ej: '#finanzaspersonales #dineromexico #ahorro #tarjetadecredito #educacionfinanciera'",
  "title": "título corto de 3-7 palabras, COMPLETO y sin ambigüedad — no omitas palabras que cambien el sentido (mal: 'Truco del SAT para médicos'; bien: 'Truco del SAT para gastos médicos')",
  "topic": "identificador corto del tema en minúsculas con guiones (ej: 'comisiones-cajero'); específico al ángulo de HOY",
  "broll_keywords": "2-4 palabras EN INGLÉS de respaldo (escena de finanzas/tecnología del tema). Mismas PROHIBICIONES: nada genérico sin relación con dinero; nada de billetes/monedas de otro país.",
  "cards": [
    {{"big": "texto grande, máx ~14 caracteres", "small": "frase corta que lo explica"}}
  ],
  "graphics": []
}}

Reglas para "beats": de 3 a 5 bloques (usa más SOLO si el tema necesita más explicación). Cada uno con "narration" (español) y "scene" (inglés, 2-4 palabras).
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

    modelos = _model_ladder()
    agotados = []
    last_err = None
    for mi, model in enumerate(modelos):
        for attempt in range(max_retries):
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=1.0,
                        response_mime_type="application/json",
                    ),
                )
                data = _extract_json(resp.text)
                data["categoria"] = plan["categoria_id"]
                data["formato"] = plan["formato_nombre"]
                data["publicar_borrador"] = plan.get("publicar_borrador", False)
                if mi > 0:
                    print(f"    (se usó el modelo de respaldo '{model}')")
                return data
            except errors.APIError as e:
                code = getattr(e, "code", None) or getattr(e, "status_code", None)
                last_err = e

                if code == 429 and _is_daily_quota(e):
                    agotados.append(model)
                    if mi < len(modelos) - 1:
                        print(f"Cuota diaria agotada en '{model}'. Salto al siguiente "
                              f"modelo: '{modelos[mi + 1]}'...")
                    break  # rompe el bucle de intentos -> siguiente modelo

                if code in (429, 500, 502, 503) and attempt < max_retries - 1:
                    wait = 8 * (attempt + 1)
                    print(f"Gemini respondió {code} (transitorio) en '{model}'. "
                          f"Reintento en {wait}s...")
                    time.sleep(wait)
                    continue

                if code in (429, 500, 502, 503):
                    print(f"'{model}' sigue fallando ({code}); pruebo el siguiente modelo.")
                    break

                raise

    if agotados:
        raise RuntimeError(
            "Cuota DIARIA del free tier de Gemini agotada en TODOS los modelos del "
            f"escalón ({', '.join(agotados)}). Se resetea a medianoche hora del "
            "Pacífico (~08:00 UTC / ~01:00 CDMX). Opciones: ampliar GEMINI_MODELS con "
            "otro modelo/flash-lite, o habilitar billing."
        )
    raise last_err