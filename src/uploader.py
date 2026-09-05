"""Sube el mp4 como asset de un Release de GitHub y devuelve su URL pública.

Meta necesita descargar el video desde una URL HTTPS pública. En un repo PÚBLICO,
la browser_download_url de un asset de release es accesible sin autenticación.

Si prefieres repo privado, cambia esta función por una subida a Cloudflare R2 /
un bucket público (ver README).
"""
import os
import datetime
import requests


def upload_public(video_path: str) -> str:
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]  # formato: owner/repo
    tag = "daily-" + datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    r = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers=headers,
        json={"tag_name": tag, "name": tag, "body": "Auto-generado"},
        timeout=60,
    )
    r.raise_for_status()
    upload_url = r.json()["upload_url"].split("{")[0]

    filename = os.path.basename(video_path)
    with open(video_path, "rb") as f:
        up = requests.post(
            f"{upload_url}?name={filename}",
            headers={**headers, "Content-Type": "video/mp4"},
            data=f,
            timeout=300,
        )
    up.raise_for_status()
    return up.json()["browser_download_url"]
