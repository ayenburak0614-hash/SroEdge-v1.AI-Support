# ai/ai_kayit.py

import discord


async def log_learned_info(bot, AI_LOGS_CHANNEL_ID: int, source: str, formatted_block: str):
    """
    AI tarafından öğrenilen her bilgi bloğunu ai-logs kanalına gönderir.
    """
    if AI_LOGS_CHANNEL_ID == 0:
        return

    channel = bot.get_channel(AI_LOGS_CHANNEL_ID)
    if channel is None:
        print("❌ ai-logs kanalı bulunamadı")
        return

    # Önizleme çok uzunsa kesilir
    preview = formatted_block.strip()
    if len(preview) > 1500:
        preview = preview[:1500] + "\n... (kısaltıldı)"

    text = (
        f"🧠 **Yeni Bilgi Öğrenildi!**\n"
        f"**Kaynak:** {source}\n"
        f"---------------------------\n"
        f"{preview}"
    )

    await channel.send(text)
