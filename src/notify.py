import os
import requests


def notify_telegram(titulo, caption, url, publicado, publish_id=None,
                    tipo="video", workflow=None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return 

    tipo = (tipo or "video").strip().lower()
    es_imagen = tipo == "imagen"
    sust = "imagen" if es_imagen else "video"
    art = "esta" if es_imagen else "este"
    emoji = "🖼️" if es_imagen else "🎬"
    if not workflow:
        workflow = "Publicar Imagen diaria" if es_imagen else "Publicar Reel diario"

    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    wf_file = "publish_image.yml" if es_imagen else "publish.yml"
    link = f"https://github.com/{repo}/actions/workflows/{wf_file}" if repo else ""

    estado = "PUBLICADO" if publicado else "BORRADOR (falta tu OK)"
    texto = (
        f"{emoji} <b>{estado}</b>\n\n"
        f"<b>Título:</b> {titulo}\n\n"
        f"<b>Caption:</b>\n{caption}\n\n"
        f"<b>Ver {sust}:</b>\n{url}"
    )
    if not publicado and publish_id:
        texto += f"\n\n👉 <b>Para publicar {art} {sust}:</b>\n"
        if link:
            texto += f'1) Abre el workflow: <a href="{link}">{workflow}</a>\n'
            texto += "2) Run workflow → pega este ID en «publicar_id»:\n"
        else:
            texto += f"GitHub → Actions → «{workflow}» → Run workflow → publicar_id:\n"
        texto += f"<code>{publish_id}</code>"  # tócalo para copiarlo

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": texto,
                "parse_mode": "HTML",
                "disable_web_page_preview": "false",
            },
            timeout=30,
        )
    except Exception as e:
        print(f"    (aviso de Telegram falló, no crítico: {e})")