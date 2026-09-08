import os
import json
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


def load_recent(n: int = 60):
    """Devuelve los últimos n temas guardados (lista de strings). [] si no hay."""
    if not _activo():
        return []
    try:
        rel = _get_release(_repo())
        if not rel:
            return []
        temas = json.loads(rel.get("body") or "{}").get("topics", [])
        return temas[-n:]
    except Exception as e:
        print(f"    (no se pudo leer historial: {e})")
        return []


def add(topic: str, keep: int = 90):
    """Agrega un tema al historial (conserva los últimos 'keep')."""
    topic = (topic or "").strip()
    if not _activo() or not topic:
        return
    try:
        rel = _get_release(_repo())
        temas = []
        if rel:
            try:
                temas = json.loads(rel.get("body") or "{}").get("topics", [])
            except Exception:
                temas = []
        temas.append(topic)
        temas = temas[-keep:]
        body = json.dumps({"topics": temas}, ensure_ascii=False)
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
        print(f"    historial actualizado ({len(temas)} temas guardados)")
    except Exception as e:
        print(f"    (no se pudo guardar historial: {e}, no crítico)")
