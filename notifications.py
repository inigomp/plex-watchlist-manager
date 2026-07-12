"""Notificaciones a Telegram cuando aparece contenido nuevo en el servidor."""
import logging

import requests

import config

logger = logging.getLogger(__name__)


def send_telegram_notification(item):
    """Avisa por Telegram de que un elemento de la watchlist ya está disponible."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    msg = (
        "🍿 *¡Nuevo en tu Plex!*\n\n"
        f"🎬 *{item['title']}* ({item['year']})\n"
        f"📁 Tipo: {item['type']}\n"
        f"📍 Disponible en: {', '.join(item['libraries'])}\n\n"
        f"[Ver en FilmAffinity]({item['url']})"
    )

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }

    try:
        requests.post(url, json=payload, timeout=10)
        logger.info(f"Notificación de Telegram enviada para: {item['title']}")
    except Exception as e:
        logger.error(f"Error enviando Telegram: {e}")
