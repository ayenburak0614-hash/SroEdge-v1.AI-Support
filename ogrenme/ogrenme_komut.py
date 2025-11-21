# ogrenme/ogrenme_komut.py

import discord
from ogrenme.ogrenme_yeni_bilgi import learn_new_information


async def handle_ai_learn_command(bot, message: discord.Message, ALLOWED_USER_IDS: list, AI_LOGS_CHANNEL_ID: int):
    """
    Yönetici tarafından manuel bilgi ekleme komutunu işler.
    Komut formatı:
    !ai-add <bilgi>
    """

    user_id = str(message.author.id)

    if user_id not in ALLOWED_USER_IDS:
        await message.channel.send("⛔ Bu komutu kullanma yetkin bulunmuyor.")
        return

    raw = message.content.replace("!ai-add", "", 1).strip()

    if not raw:
        await message.channel.send("ℹ️ Lütfen eklenecek bilgiyi yazın.\nÖrnek: `!ai-add Medusa 12 saatte bir çıkar.`")
        return

    formatted = await learn_new_information(
        bot=bot,
        AI_LOGS_CHANNEL_ID=AI_LOGS_CHANNEL_ID,
        raw_text=raw,
        user_question=None
    )

    await message.channel.send("✅ Bilgi başarıyla öğrenildi ve KB'ye eklendi!")
