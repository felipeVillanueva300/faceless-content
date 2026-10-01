import json
import os
import sys

RUTA = os.environ.get("SERIE_JSON", "serie.json")


def _cargar():
    try:
        with open(RUTA, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _guardar(data):
    with open(RUTA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _episodio_actual(data):
    if not data:
        return None
    eps = data.get("episodios") or []
    i = int(data.get("siguiente", 0))
    if 0 <= i < len(eps):
        return i, eps[i]
    return None


def peek():
    data = _cargar()
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


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "peek"
    if cmd == "advance":
        advance()
    else:
        peek()