import os
import json
import time
import datetime
from google import genai
from google.genai import types
from google.genai import errors

from src import content_plan, script_review, fichas, caption

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
    conceptos = []
    try:
        from src import history
        conceptos = history.recent_conceptos(120)
    except Exception:
        pass
    evitar = content_plan.avoid_text(avoid, conceptos=conceptos)
    cal = content_plan.calendario_linea(plan)
    from src import datos_mx
    datos = datos_mx.datos_actuales()
    datos_txt = (f"DATOS VIGENTES (úsalos TAL CUAL para cualquier cifra actual; NO inventes otras "
                 f"tasas ni inflación): {datos}\n") if datos else (
                 "No tienes datos vigentes de tasas ni inflación: NO pongas tasas de CETES, "
                 "SOFIPOs ni inflación como hechos actuales; di 'revisa la tasa de hoy en "
                 "CetesDirecto' o usa un ejemplo marcado como ejemplo.\n")

    fichas_txt = fichas.texto_prompt()

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

DURACIÓN FLEXIBLE (clave): el video dura entre 30 y 60 segundos. NO rellenes para llegar
a un número. Usa el tiempo que el tema NECESITE para quedar BIEN explicado:
- Tip rápido de una sola acción -> 30-45s.
- Concepto, método, comparación, paso a paso o capítulo de serie -> 45-60s. Ahí el
  tiempo extra se usa en el ejemplo y en el "dónde / cómo", no en relleno.
- Prohibido el relleno/preámbulo ("hoy te voy a contar…", "muchos no saben que…"). El
  PRIMER bloque entra directo al valor.

EJEMPLOS QUE SE ENTIENDEN A LA PRIMERA: nada de referencias raras, chistes internos,
números sin contexto o frases que haya que "descifrar" (mal: "por la multa de la 34").
Si citas un ejemplo, que sea algo que cualquiera reconozca al instante (ej. un concepto de
transferencia como "pago de la tanda" o "lo de las chelas"). En formato MITO: enuncia el
mito con palabras simples y di claro qué parte es falsa y qué parte SÍ es cierta; no digas
"falso" a secas si una parte es real.

A QUIÉN LE HABLAS (realidad de la mayoría en México): gente que cobra por quincena, paga
mucho en efectivo o con débito, compra en el súper, el tianguis, el mercado o la tiendita,
y muchas veces no tiene tarjeta de crédito ni compra en línea.
- El consejo tiene que servirle a ESA persona. Si un truco solo aplica a quien compra en
  línea, tiene tarjeta de crédito o ya invierte, elige otro consejo o da primero la versión
  que sí puede hacer cualquiera (ej. la lista del súper/tianguis antes que el carrito en línea).
- Ejemplos y precios cotidianos: kilo de tortilla, despensa en el tianguis, pasaje, recarga
  del celular, no gastos de clase alta.

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
CERO CABOS SUELTOS (lo que más se nota cuando falta): si el guion dice "un instrumento",
"una app", "una cuenta", "una herramienta" o "el banco", DI CUÁL con su nombre real
(CETES en CetesDirecto, una SOFIPO regulada, Nu, Klar, Mercado Pago, Finerio, la app de tu
banco...) y UN paso concreto para empezar ("descárgala, conecta tu cuenta y activa X").
- Si usas una tasa o rendimiento, que sea realista para México HOY, dilo como aproximado y
  que cambia ("hoy CETES anda cerca de X% anual, cambia cada semana"). Si no conoces la
  tasa actual, usa un ejemplo marcado como ejemplo, pero SIEMPRE nombra dónde se consigue.
- Pregúntate al final: "¿quien lo ve sabe QUÉ hacer y DÓNDE hacerlo mañana?". Si no, falta.
- Cuando haya un nombre concreto (app, instrumento, institución), ponlo en una "card"
  para que se LEA en pantalla, no solo se escuche.
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
EL GANCHO TIENE QUE SER VERDAD para quien lo ve. No afirmes que ya hace, tiene o sufre algo
que no sabes (mal: "Le estás prestando tu dinero al gobierno y ni te enteraste" a alguien
que nunca invirtió). Si no aplica a todos, plantéalo como posibilidad o pregunta (bien:
"Puedes prestarle al gobierno desde $100 y te paga por hacerlo").
CERO FRASES DE RELLENO: nada que prometa algo que el video no da ("olvídate de los mitos"
si no hay mitos) ni frases redundantes ("te regresa más dinero de vuelta"). Tampoco
palabras fuertes o raras para la marca ("mensaje maldito"): directo, pero limpio.
{datos_txt}{fichas_txt}CIFRAS (somos cuenta de finanzas: la confianza es todo):
- Usa solo cifras que puedas respaldar (Banxico, INEGI, CONDUSEF, la app o el banco). Si
  la cifra es un EJEMPLO ilustrativo, dilo ("por ejemplo", "si tu tarjeta cobra 60%...").
- Si en el guion usas un dato real, el caption lo cierra con "Fuente: <institución, año>".
  Si no estás seguro de la cifra exacta, usa una consecuencia sin número.
- NUNCA recomiendes trucos para pagar menos impuestos de forma irregular (dividir compras,
  declarar menos, facturas de otro, no reportar ingresos). Solo deducciones y beneficios legales.
- Consecuencias legales o fiscales (SAT, bloqueos, multas, buró): solo si una fuente oficial
  lo dice (SAT, PRODECON, CONDUSEF, Banxico). Muchos "te va a caer el SAT" son rumores
  virales: si el tema viene de ahí, di qué es mito y qué es real, no lo amplifiques.
- UNA sola cuenta en todo el video: el hook, el hook_card, las cards, el gráfico y la
  narración usan LOS MISMOS números. Mal: hook "¿10 mil al año?", gráfico "$19,325" y voz
  "1,800 al mes". Haz la cuenta una vez (ej. $60 x 22 días x 12 = $15,840) y repítela igual.
Reglas: concreto, con una cifra o consecuencia real (sin inventar cifras), en segunda
persona ("tú/tu"), y que genere una PREGUNTA en la cabeza del que ve. Si tu hook podría
ser el subtítulo de un libro de texto, está mal.

MUY IMPORTANTE — cómo se arma el guion (POR BLOQUES):
El guion se cuenta en BLOQUES ("beats"). El "hook" se narra primero, y luego los
bloques en orden, como una sola voz continua. Cada bloque tiene su propia frase y su
propia escena de fondo, para que la imagen CAMBIE justo cuando la voz llega a ese punto.
- El primer bloque CONTINÚA justo después del hook, SIN repetirlo ni parafrasearlo.
- REDACCIÓN: cada oración COMPLETA y con VERBO CONJUGADO; que no falte ninguna palabra.
  Mal: "guárdalo donde rendimiento diario". Bien: "guárdalo donde tenga rendimiento diario".
  Escribe los nombres SIEMPRE igual (CetesDirecto, junto; Mercado Pago; Nu).
- Cantidades: escribe "$4,000" (la voz ya dice "pesos"). PROHIBIDO "$4,000 pesos" o
  "$4,000 MXN": se oye "cuatro mil pesos pesos".
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
  "caption": "PRIMERA línea = la frase que la gente escribiría en el buscador sobre este tema, con OTRAS palabras que el título (ej. título '¿SOFIPO o banco? Dónde está seguro tu dinero' -> primera línea 'Qué seguro protege tus ahorros en México'). Luego 2-3 frases con el dato clave y QUÉ hacer (no resumas todo el video). Luego UNA pregunta corta y concreta para que la gente comente (ej: '¿Tú dónde tienes tu ahorro hoy?'). PROHIBIDO: 'Sígueme', 'guarda este video', '@dinerosimplemx', links y frases de marca ('que no te vean la cara'): el llamado a seguir y los links se agregan solos. OBLIGATORIO cerrar con una línea aparte de EXACTAMENTE 5 hashtags en español de México, 2 generales y 3 del tema. Ej: '#finanzaspersonales #dineromexico #ahorro #tarjetadecredito #educacionfinanciera'",
  "title": "título de 35-60 caracteres que dé GANAS de verlo y que la gente buscaría: curiosidad o beneficio concreto + la palabra clave del tema (bien: '¿SOFIPO o banco? Dónde está seguro tu dinero', 'El error que te cuesta $4,000 en intereses'; mal: 'SOFIPO vs Banco vs CETES Parte 4', 'Ahorro quincenal'). Sin 'Parte N' (se agrega solo). COMPLETO y sin ambigüedad",
  "concepto": "el concepto financiero CENTRAL del video en 1-4 palabras, en su forma más común (ej: 'método avalancha', 'fondo de emergencia', 'CAT de una tarjeta'). Sirve para no repetirlo aunque cambien las palabras",
  "topic": "identificador corto del tema en minúsculas con guiones (ej: 'comisiones-cajero'); específico al ángulo de HOY",
  "broll_keywords": "2-4 palabras EN INGLÉS de respaldo (escena de finanzas/tecnología del tema). Mismas PROHIBICIONES: nada genérico sin relación con dinero; nada de billetes/monedas de otro país.",
  "cards": [
    {{"big": "texto grande, máx ~14 caracteres", "small": "frase corta que lo explica", "beat": 2}}
  ],
  "graphics": []
}}

Reglas para "beats": de 3 a 5 bloques (usa más SOLO si el tema necesita más explicación). Cada uno con "narration" (español) y "scene" (inglés, 2-4 palabras).
Reglas para "cards": 0 a 2 elementos. Son rótulos que refuerzan la narración. Si no aportan, deja [].
- "beat" = número (1, 2, 3...) del bloque cuya narración MENCIONA lo de la card: ahí aparece
  en pantalla. El "big" usa la MISMA palabra o cifra que dice la voz (si la voz dice
  "CetesDirecto", la card dice "CETESDIRECTO"), para que salga justo cuando se oye.
- El "small" dice LO MISMO que la voz, sin agregar ni cambiar datos (mal: voz "retiro en
  días hábiles" y card "retiro diario").

Reglas para "graphics": 0 o 1 elemento, SOLO si tienes un dato numérico REAL y concreto
que valga la pena animar (no inventes cifras). Si no, deja []. Cada gráfico debe ser
EXACTAMENTE uno de estos dos formatos, con números planos (sin comas ni signo $):
- Contador que sube:
  {{"type": "countup", "value": 3200, "prefix": "$", "suffix": "", "label": "AL AÑO EN COMISIONES"}}
- Barras comparativas (A en rojo vs B en verde):
  {{"type": "bars", "title": "AHORRO A 1 AÑO", "a_label": "EN EL BANCO", "a_value": 385,
    "b_label": "EN CETES", "b_value": 963, "a_color": "red", "b_color": "green", "money": true}}
Opcional en ambos: "beat": número del bloque donde la voz dice ese dato (ahí aparece).
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
                data = script_review.revisar(data, client)
                data = caption.finalizar(data, plan)
                data = fichas.agregar_links(data)
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