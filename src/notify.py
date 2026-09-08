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
    emoji = "image" if es_imagen else "video"
    if not workflow:
        workflow = "Publicar Imagen diaria" if es_imagen else "Publicar Reel diario"

    estado = "PUBLICADO" if publicado else "BORRADOR (falta tu OK)"
    texto = (
        f"{emoji} <b>{estado}</b>\n\n"
        f"<b>Título:</b> {titulo}\n\n"
        f"<b>Caption:</b>\n{caption}\n\n"
        f"<b>Ver {sust}:</b>\n{url}"
    )
    if not publicado and publish_id:
        texto += (
            f"\n\n👉 <b>Para publicar {art} {sust}:</b>\n"
            f"GitHub → Actions → «{workflow}» → Run workflow →\n"
            f"publicar_id = <code>{publish_id}</code>"
        )

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