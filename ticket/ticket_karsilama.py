# ticket/ticket_karsilama.py

import discord
from ai.dil_tespit import detect_language


async def handle_ticket_creation(bot, message, stats: dict):
    """
    Yeni açılan ticket mesajını yakalar ve otomatik karşılama gönderir.
    """

    user = message.author
    content = message.content.strip()

    # Dil tespiti
    language = detect_language(content)

    # Stats güncelleme
    stats["total_tickets"] += 1
    if language == "tr":
        stats["turkish_tickets"] += 1
    else:
        stats["english_tickets"] += 1

    # Kullanıcıya özel karşılama
    if language == "tr":
        reply = (
            f"👋 Merhaba {user.mention}!\n"
            "Sorununla ilgili sana yardımcı olmak için b
