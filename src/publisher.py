"""Publica el video en Instagram (Reels) y en una Página de Facebook (Reels)."""
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


def _page_token(page_id: str) -> str:
    """Obtiene el Page Access Token a partir del token de usuario/System User.
    Publicar Reels en la Página lo requiere."""
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


def publish_facebook(page_id: str, video_url: str, description: str) -> str:
    """Publica como REEL de Facebook (endpoint video_reels, 3 pasos).

    Ventaja vs /videos: aparece en la pestaña Reels de la Página y entra al feed
    de Reels (mucho mejor alcance). Requiere 9:16 y 5-90s (tu reel cumple).
    """
    page_tok = _page_token(page_id)

    # 1) Iniciar sesión de subida
    print("    FB Reel: iniciando subida...")
    r = requests.post(
        f"{BASE}/{page_id}/video_reels",
        data={"upload_phase": "start", "access_token": page_tok},
        timeout=60,
    )
    r.raise_for_status()
    j = r.json()
    video_id = j["video_id"]
    upload_url = j["upload_url"]

    # 2) Transferir el video (archivo hosteado: le pasamos la URL pública)
    print(f"    FB Reel: transfiriendo (video_id={video_id})...")
    up = requests.post(
        upload_url,
        headers={"Authorization": f"OAuth {page_tok}", "file_url": video_url},
        timeout=180,
    )
    up.raise_for_status()

    # 3) Finalizar y publicar
    print("    FB Reel: publicando...")
    fin = requests.post(
        f"{BASE}/{page_id}/video_reels",
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": description,
            "access_token": page_tok,
        },
        timeout=60,
    )
    fin.raise_for_status()

    # Esperar el procesamiento/publicación (hasta ~2.5 min). Si no confirma, igual
    # devolvemos el id: el paso 3 ya lo mandó a publicar.
    for _ in range(30):
        s = requests.get(
            f"{BASE}/{video_id}",
            params={"fields": "status", "access_token": page_tok},
            timeout=30,
        ).json()
        status = s.get("status", {}) or {}
        pub = (status.get("publishing_phase") or {}).get("status")
        proc = (status.get("processing_phase") or {}).get("status")
        vstatus = status.get("video_status")
        if pub in ("complete", "published") or vstatus in ("ready", "published", "complete"):
            break
        if pub == "error" or proc == "error":
            raise RuntimeError(f"Facebook falló al procesar el Reel: {status}")
        time.sleep(5)

    return video_id
