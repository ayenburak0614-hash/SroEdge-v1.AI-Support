# utils/kanal_kontrol.py

def check_channel(bot, channel_id: int):
    """
    Verilen kanal ID'sinin gerçekten var olup olmadığını kontrol eder.
    Kanal varsa döndürür, yoksa None döner.
    """
    if channel_id == 0:
        return None

    return bot.get_channel(channel_id)
