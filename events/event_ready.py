# events/event_ready.py

import discord

async def on_ready_event(bot):
    """
    Bot başarılı şekilde giriş yaptığında çalışır.
    Sistem logunu ve başlangıç bildirimini gönderir.
    """

    print(f"🤖 Bot aktif: {bot.user} | ID: {bot.user.id}")
    print("✅ Tüm modüller yüklendi ve event sistemi aktif!")
