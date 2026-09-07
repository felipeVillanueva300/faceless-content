import os
import json
import datetime
import requests

KEEP_RELEASES = int(os.environ.get("KEEP_RELEASES", "4"))


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    }


def _cleanup_old_releases(repo: str, keep: int):
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/releases",
            headers=_headers(), params={"per_page": 100}, timeout=60,
        )
        r.raise_for_status()
        releases = r.json()
        daily = [rel for rel in releases if str(rel.get("tag_name", "")).startswith("daily-")]
        daily.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        for rel in daily[keep:]:
            rid = rel.get("id")
            tag = rel.get("tag_name")
            try:
                requests.delete(
                    f"https://api.github.com/repos/{repo}/releases/{rid}",
                    headers=_headers(), timeout=30,
                )
                requests.delete(
                    f"https://api.github.com/repos/{repo}/git/refs/tags/{tag}",
                    headers=_headers(), timeout=30,
                )
                print(f"    release viejo borrado: {tag}")
            except Exception as e:
                print(f"    (no se pudo borrar {tag}: {e})")
    except Exception as e:
        print(f"    (limpieza de releases omitida: {e})")


def upload_public(video_path: str, caption: str = "", title: str = ""):
    """Sube el mp4 a un Release y GUARDA el caption/título en el cuerpo del release.

    Así, cuando después publiques por ID, el texto viaja con el video y no se pierde.
    Devuelve (url, tag).
    """
    repo = os.environ["GITHUB_REPOSITORY"]
    tag = "daily-" + datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    body = json.dumps({"title": title or "", "caption": caption or ""}, ensure_ascii=False)

    r = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers=_headers(),
        json={"tag_name": tag, "name": tag, "body": body},
        timeout=60,
    )
    r.raise_for_status()
    upload_url = r.json()["upload_url"].split("{")[0]

    filename = os.path.basename(video_path)
    with open(video_path, "rb") as f:
        up = requests.post(
            f"{upload_url}?name={filename}",
            headers={**_headers(), "Content-Type": "video/mp4"},
            data=f,
            timeout=300,
        )
    up.raise_for_status()
    url = up.json()["browser_download_url"]

    _cleanup_old_releases(repo, KEEP_RELEASES)
    return url, tag


def get_release_info(repo: str, tag: str):
    """Devuelve (url_mp4, caption, title) de un release existente (por su tag/ID).

    El caption/title se leen del body (JSON). Si el body es viejo (no-JSON),
    caen a texto plano por compatibilidad.
    """
    r = requests.get(
        f"https://api.github.com/repos/{repo}/releases/tags/{tag}",
        headers=_headers(), timeout=30,
    )
    r.raise_for_status()
    rel = r.json()

    url = None
    for asset in rel.get("assets", []):
        if asset.get("name", "").endswith(".mp4"):
            url = asset["browser_download_url"]
            break
    if not url:
        raise RuntimeError(f"No se encontró un .mp4 en el release '{tag}'.")

    caption, title = "", ""
    body = (rel.get("body") or "").strip()
    if body:
        try:
            meta = json.loads(body)
            caption = (meta.get("caption") or "").strip()
            title = (meta.get("title") or "").strip()
        except Exception:
            caption = body if body != "Auto-generado" else ""
    return url, caption, title


def get_release_video_url(repo: str, tag: str) -> str:
    """Compat: solo la URL del mp4."""
    url, _caption, _title = get_release_info(repo, tag)
    return url