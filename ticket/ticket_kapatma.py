# ticket/ticket_kapatma.py

import discord
from ticket.ticket_mesaj_birlestirme import get_merged_messages, clear_ticket_messages


async def close_ticket(bot, channel: discord.TextChannel, stats: dict, CLOSE_LOG_CHANNEL_ID: int):
    """
    Ticket kapatma işlemini yapar:
    - Ticket özetini çıkarır
    - Log kanalına yollar
    - Ticket mesajlarını temizler
    """
    ticket_id = channel.id

    # Ticket geçmişini al
    merged_messages = get_merged_messages(ticket_id)

    # Log kanalını bul
    log_channel = bot.get_channel(CLOSE_LOG_CHANNEL_ID)

    if log_channel:
        log_text = (
            f"📁 **Ticket Kapatıldı**\n"
            f"**Kanal:** {channel.name} (`{channel.id}`)\n"
            f"-------------------------------\n"
            f"**Mesaj Geçmişi:**\n```\n{merged_messages}\n```"
        )

        # Çok uzun ise kısalt
        if len(log_text) > 1900:
            log_text = log_text[:1900] + "\n```...(kısaltıldı)```"

        await log_channel.send(log_text)

    # Stats güncelle
    stats["closed_tickets"] += 1

    # Ticket hafızasını temizle
    clear_ticket_messages(ticket_id)

    # Kanalı kapatma
    try:
        await channel.delete(reason="Ticket kapatıldı")
    except Exception as e:
        print(f"❌ Ticket kapatma hatası: {e}")
