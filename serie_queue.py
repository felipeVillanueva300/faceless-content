import datetime
import json
import os
import sys

RUTA = os.environ.get("SERIE_JSON", "serie.json")
COLA = os.environ.get("SERIES_COLA_JSON", "series_cola.json")


def _log(msg):
    print(msg, file=sys.stderr)


def _cargar(ruta=RUTA):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _guardar(data, ruta=RUTA):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _hoy():
    hoy = os.environ.get("SERIE_HOY", "").strip()
    if hoy:
        return datetime.date.fromisoformat(hoy)
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=6)).date()


def _fecha(txt):
    try:
        return datetime.date.fromisoformat(str(txt).strip())
    except Exception:
        return None


def _total(serie):
    try:
        return int(serie.get("total") or len(serie.get("episodios") or []))
    except (TypeError, ValueError):
        return len(serie.get("episodios") or [])


def elegir(series, hoy, silencioso=False):
    """Devuelve (índice de la serie que arranca hoy o None, lista sin las vencidas)."""
    log = (lambda m: None) if silencioso else _log
    vigentes = []
    for s in series:
        lim = _fecha(s.get("no_despues_de"))
        if lim and lim < hoy:
            log(f"Cola: '{s.get('nombre') or s.get('tema')}' ya no alcanzó su fecha "
                 f"(a más tardar {lim}); se quita de la cola.")
            continue
        vigentes.append(s)
    con_fecha = [(i, s) for i, s in enumerate(vigentes) if _fecha(s.get("no_antes_de"))]
    ya_toca = [(i, s) for i, s in con_fecha if _fecha(s["no_antes_de"]) <= hoy]
    if ya_toca:
        return ya_toca[0][0], vigentes                     # temporada primero
    proxima = min((_fecha(s["no_antes_de"]) for _, s in con_fecha), default=None)
    for i, s in enumerate(vigentes):
        if _fecha(s.get("no_antes_de")):
            continue
        if proxima is None or _total(s) <= (proxima - hoy).days:
            return i, vigentes
    if proxima:
        if any(not _fecha(s.get("no_antes_de")) for s in vigentes):
            log(f"Cola: ninguna serie alcanza a terminar antes del {proxima}; hoy no hay serie.")
        else:
            log(f"Cola: no quedan series sin fecha; la próxima de temporada arranca el {proxima}.")
    return None, vigentes


def _arrancar_siguiente():
    """Si la serie actual ya terminó, pasa la siguiente de la cola a serie.json."""
    cola = _cargar(COLA)
    if not cola or not cola.get("series"):
        _log("Cola: no hay series en espera (series_cola.json vacío).")
        return None
    idx, vigentes = elegir(cola["series"], _hoy())
    if idx is None:
        cola["series"] = vigentes
        _guardar(cola, COLA)
        return None
    nueva = dict(vigentes.pop(idx))
    nueva.pop("no_antes_de", None)
    nueva.pop("no_despues_de", None)
    nueva["siguiente"] = 0
    cola["series"] = vigentes
    _guardar(nueva)
    _guardar(cola, COLA)
    _log(f"Cola: arranca la serie '{nueva.get('nombre') or nueva.get('tema')}' "
         f"({_total(nueva)} partes). Quedan {len(vigentes)} en espera.")
    return nueva


def proxima_serie():
    """La serie que va a arrancar cuando termine la actual (o None). No modifica nada.
    La usa el reel diario para no adelantarse tampoco a la PRÓXIMA serie."""
    data = _cargar() or {}
    cola = _cargar(COLA) or {}
    if not cola.get("series"):
        return None
    try:
        faltan = max(0, _total(data) - int(data.get("siguiente", 0))) if data else 0
    except (TypeError, ValueError):
        faltan = 0
    idx, vigentes = elegir(cola["series"], _hoy() + datetime.timedelta(days=faltan), silencioso=True)
    return vigentes[idx] if idx is not None else None


def _episodio_actual(data):
    if not data:
        return None
    eps = data.get("episodios") or []
    i = int(data.get("siguiente", 0))
    if 0 <= i < len(eps) and i < _total(data):
        return i, eps[i]
    return None


def peek():
    data = _cargar()
    actual = _episodio_actual(data)
    if not actual:
        data = _arrancar_siguiente()
        actual = _episodio_actual(data)
    if not actual:
        print("HAY_EPISODIO=0")
        return
    i, ep = actual
    eps = data.get("episodios") or []
    total = data.get("total", len(eps))
    siguiente = ""
    if i + 1 < len(eps) and i + 1 < int(total):
        sig = eps[i + 1]
        siguiente = sig.get("titulo") or sig.get("subtema", "")
    # Una línea KEY=valor por variable (formato de $GITHUB_ENV). Valores de una sola línea.
    lineas = {
        "HAY_EPISODIO": "1",
        "SERIE_TEMA": data.get("tema", ""),
        "SERIE_PARTE": str(i + 1),
        "SERIE_TOTAL": str(total),
        "SERIE_SUBTEMA": ep.get("subtema", ""),
        "SERIE_ANTERIOR": ep.get("anterior", ""),
        "SERIE_FORMATO": ep.get("formato", ""),
        "SERIE_SIGUIENTE": siguiente,
        "SERIE_NOMBRE": data.get("nombre", ""),
    }
    for k, v in lineas.items():
        v = " ".join(str(v).splitlines())   # asegura una sola línea
        print(f"{k}={v}")


def advance():
    data = _cargar()
    actual = _episodio_actual(data)
    if not actual:
        return
    data["siguiente"] = int(data.get("siguiente", 0)) + 1
    _guardar(data)
    print(f"Cola avanzada a episodio índice {data['siguiente']}")


def calendario(dias=120):
    """python serie_queue.py calendario -> simula qué serie sale cada día (no modifica nada)."""
    import copy
    data = copy.deepcopy(_cargar()) or {}
    cola = copy.deepcopy(_cargar(COLA)) or {"series": []}
    dia = _hoy()
    for _ in range(dias):
        act = _episodio_actual(data)
        if not act:
            idx, cola["series"] = elegir(cola["series"], dia)
            if idx is not None:
                data = dict(cola["series"].pop(idx))
                data["siguiente"] = 0
                act = _episodio_actual(data)
        if act:
            i, _ep = act
            print(f"{dia}  {data.get('nombre') or data.get('tema')} ({i + 1}/{_total(data)})")
            data["siguiente"] = i + 1
        else:
            print(f"{dia}  — sin serie —")
        dia += datetime.timedelta(days=1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "peek"
    if cmd == "advance":
        advance()
    elif cmd == "calendario":
        calendario(int(sys.argv[2]) if len(sys.argv) > 2 else 120)
    else:
        peek()