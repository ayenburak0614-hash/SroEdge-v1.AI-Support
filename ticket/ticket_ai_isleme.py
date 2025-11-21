# ticket/ticket_ai_isleme.py

import discord
from ai.dil_tespit import detect_language
from ai.ai_yanit import get_ai_response
from ticket.ticket_mesaj_birlestirme import add_message_to_ticket, get_merged_messages


async def process_ticket_message(bot, message, stats: dict, SUPPORT_ROLE_ID: int):
    """
    Ticket kanalındaki kullanıcı mesajını analiz eder,
    AI'nin cevap vermesi gereken durumlarda tetikler.
    """

    user = message.author
    content = message.content.strip()
    channel = message.channel

    # Bot kendi mesajına cevap vermesin
    if user.bot:
        return

    # Ticket ID (kanal ID)
    ticket_id = channel.id

    # Mesajı ticket listesine ekle
    add_message_to_ticket(ticket_id, user, content)

    # Dil tespiti
    language = detect_language(content)

    # Ticket geçmişini al
    merged = get_merged_messages(ticket_id)

    # AI'nin cevabı
    ai_reply = await get_ai_response(
        user_message=merged,
        language=language,
        SUPPORT_ROLE_ID=SUPPORT_ROLE_ID,
        stats=stats
    )

    # Kullanıcıya AI cevabını gönder
    await channel.send(ai_reply)
