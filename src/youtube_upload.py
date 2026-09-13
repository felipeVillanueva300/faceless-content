import os
import json
import time
import tempfile

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = ("https://www.googleapis.com/upload/youtube/v3/videos"
              "?uploadType=resumable&part=snippet,status")


def _require(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Falta el secreto {name}. Configúralo en GitHub → Settings → "
            f"Secrets and variables → Actions (o en tu .env local)."
        )
    return val


def _access_token(max_retries: int = 3) -> str:
    """Cambia el refresh_token por un access_token de corta duración."""
    data = {
        "client_id": _require("YT_CLIENT_ID"),
        "client_secret": _require("YT_CLIENT_SECRET"),
        "refresh_token": _require("YT_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }
    last = None
    for attempt in range(max_retries):
        try:
            r = requests.post(TOKEN_URL, data=data, timeout=30)
            if r.status_code == 200:
                return r.json()["access_token"]
            if r.status_code == 400 and "invalid_grant" in r.text:
                raise RuntimeError(
                    "invalid_grant al refrescar el token de YouTube. El refresh token "
                    "caducó o fue revocado. Regénéralo y actualiza YT_REFRESH_TOKEN "
                    "(y pon la pantalla de OAuth en 'Production', no 'Testing')."
                )
            last = RuntimeError(f"Token endpoint devolvió {r.status_code}: {r.text[:300]}")
        except requests.RequestException as e:
            last = e
        time.sleep(4 * (attempt + 1))
    raise last


def _clean_title(title: str) -> str:
    t = (title or "").replace("<", "").replace(">", "").strip()
    if not t:
        t = "Dinero Simple"
    return t[:100]


def _build_description(description: str) -> str:
    desc = (description or "").strip()
    if "#shorts" not in desc.lower():
        desc = (desc + "\n\n#Shorts").strip()
    return desc[:4900]


def upload_short(video_path: str, title: str, description: str = "",
                 tags=None, privacy: str = None, category_id: str = None,
                 language: str = None) -> str:
    """Sube un archivo local a YouTube como Short. Devuelve el video_id."""
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"No existe el video a subir: {video_path}")

    privacy = (privacy or os.environ.get("YT_PRIVACY", "private")).strip().lower()
    category_id = category_id or os.environ.get("YT_CATEGORY_ID", "22")
    language = language or os.environ.get("YT_LANGUAGE", "es-MX")

    token = _access_token()
    size = os.path.getsize(video_path)

    metadata = {
        "snippet": {
            "title": _clean_title(title),
            "description": _build_description(description),
            "tags": tags or ["finanzas", "dinero", "ahorro", "mexico"],
            "categoryId": str(category_id),
            "defaultLanguage": language,
            "defaultAudioLanguage": language,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    init = requests.post(
        UPLOAD_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/*",
            "X-Upload-Content-Length": str(size),
        },
        data=json.dumps(metadata).encode("utf-8"),
        timeout=60,
    )
    if init.status_code not in (200, 201):
        raise RuntimeError(
            f"YouTube no aceptó la subida (init {init.status_code}): {init.text[:400]}"
        )
    session_url = init.headers.get("Location")
    if not session_url:
        raise RuntimeError("YouTube no devolvió la URL de subida (header Location).")

    with open(video_path, "rb") as f:
        payload = f.read()
    put = requests.put(
        session_url,
        headers={"Content-Type": "video/*", "Content-Length": str(size)},
        data=payload,
        timeout=600,
    )
    if put.status_code not in (200, 201):
        raise RuntimeError(
            f"Falló la subida del video (PUT {put.status_code}): {put.text[:400]}"
        )

    video_id = put.json().get("id")
    if not video_id:
        raise RuntimeError(f"YouTube no devolvió el id del video: {put.text[:400]}")
    print(f"    YouTube OK: https://youtu.be/{video_id}  (privacy={privacy})")
    return video_id


def upload_short_from_url(video_url: str, title: str, description: str = "",
                          **kwargs) -> str:
    """Descarga el mp4 de una URL pública (ej. el Release de GitHub) y lo sube.
    Útil para el flujo de 'publicar por ID', que solo tiene la URL."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        path = tmp.name
    try:
        dl = requests.get(video_url, timeout=300, stream=True)
        dl.raise_for_status()
        with open(path, "wb") as f:
            for chunk in dl.iter_content(chunk_size=1 << 16):
                f.write(chunk)
        return upload_short(path, title, description, **kwargs)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python -m src.youtube_upload <archivo.mp4> \"<título>\" [descripción]")
        raise SystemExit(1)
    _path = sys.argv[1]
    _title = sys.argv[2]
    _desc = sys.argv[3] if len(sys.argv) > 3 else ""
    vid = upload_short(_path, _title, _desc)
    print("video_id:", vid)
