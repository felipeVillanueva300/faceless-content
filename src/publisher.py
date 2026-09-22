"""Publica el video en Instagram (Reels) y en una Página de Facebook (Reels)."""
import os
import time
import requests

VER = os.environ.get("GRAPH_VERSION", "v23.0")
BASE = f"https://graph.facebook.com/{VER}"


def _token() -> str:
    return os.environ["META_ACCESS_TOKEN"]


def _check(r, paso: str):
    """Si Meta respondió con error, lanza un mensaje CLARO con el detalle real de la
    Graph API (código, subcódigo, mensaje). Sin esto, solo se veía '400 Bad Request'."""
    if r.status_code >= 400:
        try:
            err = r.json().get("error", {})
        except Exception:
            err = {"message": r.text[:300]}
        raise RuntimeError(
            f"[{paso}] Meta {r.status_code}: {err.get('message', '?')} "
            f"(type={err.get('type')}, code={err.get('code')}, "
            f"subcode={err.get('error_subcode')}, "
            f"fbtrace={err.get('fbtrace_id')})"
        )
    return r


def publish_instagram(ig_user_id: str, video_url: str, caption: str) -> str:
    r = _check(requests.post(
        f"{BASE}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": _token(),
        },
        timeout=60,
    ), "IG crear contenedor")
    container_id = r.json()["id"]
    print(f"    IG: contenedor {container_id} creado; esperando a que procese...")

    ultimo = {}
    for _ in range(60):
        s = _check(requests.get(
            f"{BASE}/{container_id}",
            params={"fields": "status_code,status", "access_token": _token()},
            timeout=30,
        ), "IG estado contenedor").json()
        ultimo = s
        code = s.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(
                f"IG procesó con ERROR el video. status={s.get('status')} | {s}"
            )
        time.sleep(5)
    else:
        raise TimeoutError(
            f"IG: el contenedor no quedó listo a tiempo (5 min). Último estado: {ultimo}"
        )

    # 3) Publicar
    p = _check(requests.post(
        f"{BASE}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": _token()},
        timeout=60,
    ), "IG publicar")
    media_id = p.json().get("id", "")
    print(f"    IG: publicado (media_id={media_id})")
    return media_id


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

    print(f"    FB Reel: transfiriendo (video_id={video_id})...")
    up = requests.post(
        upload_url,
        headers={"Authorization": f"OAuth {page_tok}", "file_url": video_url},
        timeout=180,
    )
    up.raise_for_status()

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