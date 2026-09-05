"""Publica el video en Instagram (Reels) y en una Página de Facebook vía Graph API."""
import os
import time
import requests

VER = os.environ.get("GRAPH_VERSION", "v23.0")
BASE = f"https://graph.facebook.com/{VER}"


def _token() -> str:
    return os.environ["META_ACCESS_TOKEN"]


def publish_instagram(ig_user_id: str, video_url: str, caption: str) -> str:
    # 1) Crear el contenedor (media container) de tipo REELS
    r = requests.post(
        f"{BASE}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": _token(),
        },
        timeout=60,
    )
    r.raise_for_status()
    container_id = r.json()["id"]

    # 2) Esperar a que Meta procese el video (hasta ~5 min)
    for _ in range(60):
        s = requests.get(
            f"{BASE}/{container_id}",
            params={"fields": "status_code", "access_token": _token()},
            timeout=30,
        ).json()
        code = s.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram falló al procesar el video: {s}")
        time.sleep(5)
    else:
        raise TimeoutError("El contenedor de Instagram no quedó listo a tiempo.")

    # 3) Publicar
    p = requests.post(
        f"{BASE}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": _token()},
        timeout=60,
    )
    p.raise_for_status()
    return p.json().get("id", "")


def publish_facebook(page_id: str, video_url: str, description: str) -> str:
    # Sube un video a la Página usando la URL pública (file_url).
    r = requests.post(
        f"{BASE}/{page_id}/videos",
        data={
            "file_url": video_url,
            "description": description,
            "access_token": _token(),
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json().get("id", "")
