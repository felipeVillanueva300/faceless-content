"""Cola de episodios para la MINISERIE automática de la tarde.

Lee/escribe 'serie.json' (en la raíz del repo). El workflow de la tarde llama:
  python serie_queue.py peek     -> imprime las variables SERIE_* del siguiente episodio
                                    (para volcarlas a $GITHUB_ENV). Si no hay pendientes,
                                    imprime HAY_EPISODIO=0.
  python serie_queue.py advance  -> marca el episodio actual como hecho (avanza el índice)
                                    y guarda serie.json.

Formato de serie.json:
{
  "tema": "cómo manejar tu tarjeta de crédito",
  "total": 4,
  "siguiente": 0,
  "episodios": [
    {"subtema": "...", "anterior": "", "formato": "howto"},
    ...
  ]
}
Cuando 'siguiente' llega a 'total' (o al final de la lista), la cola queda vacía y el
workflow no genera nada hasta que cargues otra serie.
"""
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
    total = data.get("total", len(data.get("episodios", [])))
    # Una línea KEY=valor por variable (formato de $GITHUB_ENV). Valores de una sola línea.
    lineas = {
        "HAY_EPISODIO": "1",
        "SERIE_TEMA": data.get("tema", ""),
        "SERIE_PARTE": str(i + 1),
        "SERIE_TOTAL": str(total),
        "SERIE_SUBTEMA": ep.get("subtema", ""),
        "SERIE_ANTERIOR": ep.get("anterior", ""),
        "SERIE_FORMATO": ep.get("formato", ""),
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
