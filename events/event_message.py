# events/event_message.py

import discord

# AI modülleri
from ai.dil_tespit import detect_language
from ai.ai_yanit import get_ai_response

# Ticket modülleri
from ticket.ticket_karsilama import handle_ticket_creation
from ticket.ticket_ai_isleme import process_ticket_message
from ticket.ticket_kapatma import close_ticket
from ticket.ticket_yetkili_etiket import check_need_support

# Öğrenme modülleri
from ogrenme.ogrenme_komut import handle_ai_learn_command


async def on_message_event(bot, message, config, stats):
    """
    Botun tüm mesajlarını kontrol eden ana event.
    Ticket sistemi, öğrenme sistemi ve AI buradan tetiklenir.
    """

    # Bot kendi mesajına cevap vermesin
    if message.author.bot:
        return

    content = message.content.strip()
    channel = message.channel
    channel_name = channel.name.lower()

    # ================================
    # 1) Öğrenme Komutu (!ai-add)
    # ================================
    if content.startswith("!ai-add"):
        await handle_ai_learn_command(
            bot=bot,
            message=message,
            ALLOWED_USER_IDS=config["ALLOWED_USER_IDS"],
            AI_LOGS_CHANNEL_ID=config["AI_LOGS_CHANNEL_ID"]
        )
        return

    # ================================
    # 2) Ticket açılışı (support kanalında kullanıcı yazınca)
    # ================================
    if "ticket" in channel_name and "closed" not in channel_name:

        # Ticket karşılama ve ilk mesaj
        history = [msg async for msg in channel.history(limit=5)]
        if len(history) <= 1:   # ÖNEMLİ DÜZELTME ✔
            await handle_ticket_creation(bot, message, stats)
            return

        # Yetkili çağırma kontrolü
        await check_need_support(message, SUPPORT_ROLE_ID=config["SUPPORT_ROLE_ID"])

        # Ticket içi mesajlar → AI işleme sistemi
        await process_ticket_message(
            bot=bot,
            message=message,
            stats=stats,
            SUPPORT_ROLE_ID=config["SUPPORT_ROLE_ID"]
        )
        return

    # ================================
    # 3) Ticket kapatma komutu (!kapat)
    # ================================
    if content == "!kapat":
        await close_ticket(
            bot=bot,
            channel=channel,
            stats=stats,
            CLOSE_LOG_CHANNEL_ID=config["CLOSE_LOG_CHANNEL_ID"]
        )
        return

    # ================================
    # 4) Normal mesajlar (ticket dışında)
    # ================================
    return
