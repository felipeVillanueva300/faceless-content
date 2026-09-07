
import os
import requests


def notify_telegram(titulo, caption, url, publicado, publish_id=None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return 

    estado = " PUBLICADO" if publicado else " BORRADOR (falta tu OK)"
    texto = (
        f"<b>{estado}</b>\n\n"
        f"<b>Título:</b> {titulo}\n\n"
        f"<b>Caption:</b>\n{caption}\n\n"
        f"<b>Ver video:</b>\n{url}"
    )
    if not publicado and publish_id:
        texto += (
            f"\n\n<b>Para publicar ESTE video:</b>\n"
            f"GitHub → Actions → Run workflow →\n"
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