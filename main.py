
import discord
from discord.ext import commands
import openai
import os
import json
import asyncio
import requests
from datetime import datetime

# ================================
# ENVIRONMENT VARIABLES
# ================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPPORT_ROLE_ID = int(os.getenv("SUPPORT_ROLE_ID", "0"))
LEARNING_CHANNEL_ID = int(os.getenv("LEARNING_CHANNEL_ID", "0"))
COMMANDS_CHANNEL_ID = int(os.getenv("COMMANDS_CHANNEL_ID", "0"))
AI_LOGS_CHANNEL_ID = int(os.getenv("AI_LOGS_CHANNEL_ID", "0"))
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_FILE_PATH = os.getenv("GITHUB_FILE_PATH", "knowledge_base.txt")

openai.api_key = OPENAI_API_KEY

# ================================
# BOT SETUP
# ================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================================
# LOG SEND FUNCTION
# ================================
async def send_log(msg):
    try:
        channel = bot.get_channel(AI_LOGS_CHANNEL_ID)
        if channel:
            await channel.send(f"📥 **AI Log:**
```
{msg}
```")
    except:
        pass

# ================================
# LOAD KNOWLEDGE BASE
# ================================
def load_kb():
    try:
        with open("knowledge_base.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def save_kb(text):
    with open("knowledge_base.txt", "w", encoding="utf-8") as f:
        f.write(text)

# ================================
# PUSH TO GITHUB
# ================================
def push_to_github(new_content):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    get_file = requests.get(url, headers=headers)
    sha = get_file.json().get("sha", None)

    data = {
        "message": "Auto-learn update",
        "content": new_content.encode("utf-8").decode("utf-8"),
        "sha": sha,
    }

    put = requests.put(url, headers=headers, data=json.dumps(data))
    return put.status_code

# ================================
# AI GENERATE REPLY
# ================================
async def ask_ai(question):
    kb = load_kb()
    prompt = f"""
### KNOWLEDGE BASE:
{kb}

### USER QUESTION:
{question}

### STRICT RULES:
- Answer ONLY using the info in knowledge base.
- If unknown: say "Bu bilgi elimde yok."
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"You are a knowledge base AI."},
            {"role":"user","content":prompt}
        ]
    )

    return response.choices[0].message["content"]

# ================================
# ON READY
# ================================
@bot.event
async def on_ready():
    print("🤖 Bot aktif!")
    await send_log("Bot başarıyla başlatıldı!")

# ================================
# MESSAGE LISTENER
# ================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Komutları botun algılaması için
    await bot.process_commands(message)

# ================================
# !ai-learn KOMUTU
# ================================
@bot.command()
async def ai_learn(ctx, *, text: str):
    if ctx.channel.id != LEARNING_CHANNEL_ID:
        return await ctx.reply("❌ Bu komut sadece öğrenme kanalında kullanılabilir.")

    old = load_kb()
    new = old + "\n" + text
    save_kb(new)

    encoded = new.encode("utf-8")
    import base64
    b64 = base64.b64encode(encoded).decode("utf-8")

    status = push_to_github(b64)

    await send_log(f"Yeni bilgi öğrenildi:
{text}
Github Status: {status}")
    await ctx.reply("✅ Öğrenildi!")

# ================================
# !ask KOMUTU
# ================================
@bot.command()
async def ask(ctx, *, question: str):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return await ctx.reply("❌ Bu komut sadece sorular kanalında kullanılabilir.")

    answer = await ask_ai(question)
    await ctx.reply(answer)
    await send_log(f"Soru: {question}
Cevap: {answer}")

# ================================
# START BOT
# ================================
bot.run(DISCORD_TOKEN)
