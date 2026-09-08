import os
import time
import requests

VER = os.environ.get("GRAPH_VERSION", "v23.0")
BASE = f"https://graph.facebook.com/{VER}"


def _token() -> str:
    return os.environ["META_ACCESS_TOKEN"]


def publish_instagram_image(ig_user_id: str, image_url: str, caption: str) -> str:
    r = requests.post(
        f"{BASE}/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": _token()},
        timeout=60,
    )
    r.raise_for_status()
    container_id = r.json()["id"]

    for _ in range(20):
        s = requests.get(
            f"{BASE}/{container_id}",
            params={"fields": "status_code", "access_token": _token()},
            timeout=30,
        ).json()
        code = s.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram falló al procesar la imagen: {s}")
        time.sleep(3)

    # 3) Publicar
    p = requests.post(
        f"{BASE}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": _token()},
        timeout=60,
    )
    p.raise_for_status()
    return p.json().get("id", "")


def _page_token(page_id: str) -> str:
    """Obtiene el token de la PÁGINA (publicar en /{page}/photos lo requiere)."""
    r = requests.get(
        f"{BASE}/{page_id}",
        params={"fields": "access_token", "access_token": _token()},
        timeout=30,
    )
    r.raise_for_status()
    tok = r.json().get("access_token")
    if not tok:
        raise RuntimeError(
            "No se pudo obtener el token de la Página. Revisa que el System User "
            "tenga la Página asignada con control total y el permiso pages_show_list."
        )
    return tok


def publish_facebook_photo(page_id: str, image_url: str, caption: str) -> str:
    tok = _page_token(page_id)
    r = requests.post(
        f"{BASE}/{page_id}/photos",
        data={"url": image_url, "caption": caption, "access_token": tok},
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("id", "")
