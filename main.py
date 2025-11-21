# ============================================
#              MODÜLER ANA BOT
# ============================================

import discord
from discord.ext import commands
import os
import json

# EVENT MODÜLLERİ
from events.event_ready import on_ready_event
from events.event_message import on_message_event


# ============================================
#               KONFİG YÜKLEME
# ============================================

def load_config():
    """config.json veya environment üzerinden ayarları yükler."""
    config = {
        "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN"),
        "SUPPORT_ROLE_ID": int(os.getenv("SUPPORT_ROLE_ID", 0)),
        "CLOSE_LOG_CHANNEL_ID": int(os.getenv("CLOSE_LOG_CHANNEL_ID", 0)),
        "AI_LOGS_CHANNEL_ID": int(os.getenv("AI_LOGS_CHANNEL_ID", 0)),
        "ALLOWED_USER_IDS": json.loads(os.getenv("ALLOWED_USER_IDS", "[]")),
    }
    return config


config = load_config()


# ============================================
#               BOT BAŞLATMA
# ============================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ============================================
#               GLOBAL STATS
# ============================================

stats = {
    "total_tickets": 0,
    "closed_tickets": 0,
    "turkish_tickets": 0,
    "english_tickets": 0,
    "total_questions": 0,
    "turkish_questions": 0,
    "english_questions": 0
}


# ============================================
#             EVENT: BOT READY
# ============================================

@bot.event
async def on_ready():
    await on_ready_event(bot)


# ============================================
#          EVENT: MESAJ GELDİĞİNDE
# ============================================

@bot.event
async def on_message(message):
    await on_message_event(bot, message, config, stats)


# ============================================
#                BOTU BAŞLAT
# ============================================

if __name__ == "__main__":
    print("🔄 Bot başlatılıyor...")
    bot.run(config["DISCORD_TOKEN"])
