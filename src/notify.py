"""Aviso de UNA sola vía por Telegram (GitHub -> tu Telegram).

No escucha nada ni recibe órdenes: solo ENVÍA un mensaje. Sin superficie de
ataque. Si no hay token/chat configurados, no hace nada (silencioso).
"""
import os
import requests


def notify_telegram(titulo: str, caption: str, url: str, publicado: bool):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return  # no configurado: se omite en silencio

    estado = "Success PUBLICADO" if publicado else "BORRADOR (falta tu OK)"
    texto = (
        f"🎬 <b>{estado}</b>\n\n"
        f"<b>Título:</b> {titulo}\n\n"
        f"<b>Caption:</b>\n{caption}\n\n"
        f"<b>Ver video:</b>\n{url}"
    )
    if not publicado:
        texto += (
            "\n\n👉 Para publicarlo: GitHub → Actions → Run workflow → "
            "publicar: <b>true</b>"
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
