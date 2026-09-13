import os
import json
import datetime
import requests

TAG = "state-topics"


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    }


def _repo():
    return os.environ.get("GITHUB_REPOSITORY", "").strip()


def _activo():
    return bool(_repo() and os.environ.get("GITHUB_TOKEN"))


def _get_release(repo):
    r = requests.get(
        f"https://api.github.com/repos/{repo}/releases/tags/{TAG}",
        headers=_headers(), timeout=30,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def _data():
    """Lee el body del release como dict. {} si no hay o falla."""
    if not _activo():
        return {}
    try:
        rel = _get_release(_repo())
        if not rel:
            return {}
        return json.loads(rel.get("body") or "{}")
    except Exception as e:
        print(f"    (no se pudo leer historial: {e})")
        return {}


def load_recent(n: int = 60):
    """Devuelve los últimos n temas guardados (lista de strings). [] si no hay."""
    return (_data().get("topics", []) or [])[-n:]


def recent_pilares(dias: int = 5):
    """Ids de categoría usados en los últimos 'dias' días (para el enfriamiento)."""
    recs = _data().get("records", []) or []
    hoy = datetime.date.today()
    out = []
    for r in recs:
        cat = r.get("categoria")
        if not cat:
            continue
        f = r.get("fecha")
        if f:
            try:
                if (hoy - datetime.date.fromisoformat(f)).days >= dias:
                    continue
            except Exception:
                pass
        out.append(cat)
    return out


def recent_formatos(n: int = 2):
    """Nombres de los últimos n formatos usados (para no repetir seguido)."""
    recs = _data().get("records", []) or []
    fmts = [r.get("formato") for r in recs if r.get("formato")]
    return fmts[-n:]


def add(topic: str, categoria=None, formato=None, keep: int = 90):
    """Agrega un registro al historial (conserva los últimos 'keep').
    Mantiene la lista 'topics' (compatibilidad) y una lista 'records' con
    fecha + categoría + formato para el enfriamiento y la rotación."""
    topic = (topic or "").strip()
    if not _activo() or not topic:
        return
    try:
        rel = _get_release(_repo())
        data = {}
        if rel:
            try:
                data = json.loads(rel.get("body") or "{}")
            except Exception:
                data = {}
        temas = data.get("topics", []) or []
        recs = data.get("records", []) or []

        temas.append(topic)
        temas = temas[-keep:]
        recs.append({
            "fecha": datetime.date.today().isoformat(),
            "topic": topic,
            "categoria": categoria,
            "formato": formato,
        })
        recs = recs[-keep:]

        body = json.dumps({"topics": temas, "records": recs}, ensure_ascii=False)
        if rel:
            requests.patch(
                f"https://api.github.com/repos/{_repo()}/releases/{rel['id']}",
                headers=_headers(), json={"body": body}, timeout=30,
            ).raise_for_status()
        else:
            requests.post(
                f"https://api.github.com/repos/{_repo()}/releases",
                headers=_headers(),
                json={"tag_name": TAG, "name": TAG, "body": body, "prerelease": True},
                timeout=30,
            ).raise_for_status()
        print(f"    historial actualizado ({len(temas)} temas, {len(recs)} registros)")
    except Exception as e:
        print(f"    (no se pudo guardar historial: {e}, no crítico)")