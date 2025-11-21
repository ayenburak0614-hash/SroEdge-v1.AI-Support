# ticket/ticket_yetkili_etiket.py

import discord


KEYWORDS_SUPPORT = [
    "ban",
    "dc",
    "bug",
    "exploit",
    "hacker",
    "hack",
    "item kayıp",
    "silindi",
    "silinmiş",
    "kurtarma",
    "account",
    "hesap",
    "çalındı",
    "çalıntı",
    "login error",
    "error",
    "crash",
    "disconnect",
]


async def check_need_support(message: discord.Message, SUPPORT_ROLE_ID: int):
    """
    Mesaj içinde kritik kelimeler varsa support rolünü çağırır.
    """

    if SUPPORT_ROLE_ID == 0:
        return False

    content = message.content.lower()
    channel = message.channel

    for keyword in KEYWORDS_SUPPORT:
        if keyword in content:
            support_role = message.guild.get_role(SUPPORT_ROLE_ID)

            if support_role:
                await channel.send(
                    f"⚠️ **Dikkat!** Önemli bir durum tespit edildi. {support_role.mention}, lütfen ticketa göz atın."
                )
            return True

    return False
