import discord
from discord.ext import commands
import openai
import os
import json
from datetime import datetime

# ======================
# ENVIRONMENT VARIABLES
# ======================
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SUPPORT_ROLE_ID = int(os.getenv('SUPPORT_ROLE_ID', '0'))
LEARNING_CHANNEL_ID = int(os.getenv('LEARNING_CHANNEL_ID', '0'))
COMMANDS_CHANNEL_ID = int(os.getenv('COMMANDS_CHANNEL_ID', '0'))
ALLOWED_USER_IDS = json.loads(os.getenv('ALLOWED_USER_IDS', '[]'))

openai.api_key = OPENAI_API_KEY

# ======================
# BOT SETUP
# ======================
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

# AI devre dışı bırakılmış kanallar
disabled_channels = set()

# ======================
# KNOWLEDGE BASE
# ======================
def load_knowledge_base():
    try:
        with open('knowledge_base.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ""

def save_knowledge_base(content):
    with open('knowledge_base.txt', 'w', encoding='utf-8') as f:
        f.write(content)

def update_knowledge(new_info):
    kb = load_knowledge_base()
    updated_kb = kb + f"\n\n[UPDATE_{datetime.now().strftime('%Y%m%d_%H%M%S')}]\n{new_info}\n"
    save_knowledge_base(updated_kb)
    return True

# ======================
# LANGUAGE DETECTION
# ======================
def detect_language(text):
    tr_keywords = [
        'nedir', 'nasil', 'ne zaman', 'neden', 'var mi',
        'kac', 'fiyat', 'sure', 'oran', 'drop', 'giris'
    ]
    en_keywords = ['what', 'when', 'how', 'where', 'why', 'rate', 'drop', 'event']

    turkish_chars = set('çğıöşüÇĞİÖŞÜ')
    if any(c in turkish_chars for c in text):
        return 'tr'
    if any(w in text.lower() for w in tr_keywords):
        return 'tr'
    if any(w in text.lower() for w in en_keywords):
        return 'en'

    tr_score = sum(text.lower().count(w) for w in tr_keywords)
    en_score = sum(text.lower().count(w) for w in en_keywords)
    return 'tr' if tr_score >= en_score else 'en'

# ======================
# AI RESPONSE
# ======================
async def get_ai_response(user_message, language):
    kb = load_knowledge_base()

    system_prompt = f"""
Sen Jaynora AI Support botsun. Profesyonel bir oyun yöneticisi gibi cevap verirsin.

GENEL KURALLAR:
1. Sadece knowledge_base içindeki bilgilerle cevap ver.
2. Asla uydurma bilgi verme.
3. Bilgi yoksa Support rolüne yönlendir.
4. Cevaplar kısa, net, madde madde.
5. Gereksiz cümle yok.
6. 1–2 emoji serbest.
7. Profesyonel + samimi ton.
8. Kullanıcının dili: {language}

KNOWLEDGE BASE:
{kb}

CEVAP FORMATIN:
- Madde madde
- Bilgi varsa direkt ver
- Bilgi yoksa: "Bu konu hakkında kesin bir bilgi bulunmuyor. Seni ilgili birime yönlendiriyorum <@&{SUPPORT_ROLE_ID}>"
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.25,
            max_tokens=600
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ Bir hata oluştu: {e}"

# ======================
# BOT EVENTS
# ======================
@bot.event
async def on_ready():
    print(f"✅ {bot.user} giriş yaptı!")
    print(f"Bot ID: {bot.user.id}")

# TicketTool hoş geldin mesajı
@bot.event
async def on_guild_channel_update(before, after):
    if before.name != after.name and "ticket" in after.name.lower():
        try:
            await after.send(
                "Merhaba! 😊\n"
                "Destek talebin başarıyla oluşturuldu.\n\n"
                "Sorunu daha hızlı çözebilmem için lütfen kısaca açıklayarak başla.\n"
                "• Hangi konuda yardım istiyorsun? (skill/item/unique/event/job/payment/client/teknik)\n"
                "• Tam olarak ne sorun yaşıyorsun?\n\n"
                "Hazır olduğunda yazabilirsin!"
            )
        except Exception as e:
            print(f"[ERROR] Ticket hoş geldin mesajı gönderilemedi: {e}")

# ======================
# MAIN MESSAGE HANDLER (ÇİFT CEVAP %100 FIX)
# ======================
@bot.event
async def on_message(message):

    # Bot kendi mesajına tepki vermesin
    if message.author.bot:
        return

    # Komutları önceden işle
    await bot.process_commands(message)

    # Learning Channel kontrolü
    if message.channel.id == LEARNING_CHANNEL_ID:
        if message.author.id in ALLOWED_USER_IDS or not ALLOWED_USER_IDS:
            try:
                update_knowledge(message.content)
                await message.add_reaction("✅")
            except:
                await message.add_reaction("❌")
        return

    # Ticket değilse AI çalışmaz
    if "ticket" not in message.channel.name.lower():
        return

    # AI devre dışı mı?
    if message.channel.id in disabled_channels:
        return

    # AI yanıt üret
    language = detect_language(message.content)
    response = await get_ai_response(message.content, language)

    # Support etiket düzeltmesi
    if "@Support" in response or "ilgili birime" in response:
        if SUPPORT_ROLE_ID:
            response = response.replace("@Support", f"<@&{SUPPORT_ROLE_ID}>")

    # Mesajı gönder
    await message.reply(response)

# ======================
# BOT COMMANDS
# ======================
@bot.command(name='ai-restart')
async def ai_restart(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    load_knowledge_base()
    await ctx.send("🔄 AI yeniden hazır!")

@bot.command(name='ai-add')
async def ai_add(ctx, *, new_info: str):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    try:
        update_knowledge(new_info)
        await ctx.send("✅ Bilgi başarıyla eklendi!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command(name='ai-dur')
async def ai_dur(ctx):
    if "ticket" not in ctx.channel.name.lower():
        await ctx.send("⚠️ Bu komut sadece ticket kanallarında kullanılabilir!")
        return
    disabled_channels.add(ctx.channel.id)
    await ctx.send("⏸️ AI bu kanalda devre dışı bırakıldı.")

@bot.command(name='ai-go')
async def ai_go(ctx):
    if "ticket" not in ctx.channel.name.lower():
        await ctx.send("⚠️ Bu komut sadece ticket kanallarında kullanılabilir!")
        return
    disabled_channels.discard(ctx.channel.id)
    await ctx.send("▶️ AI bu kanalda aktif edildi.")

@bot.command(name='ai-test')
async def ai_test(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    try:
        test = await get_ai_response("Test mesajı", "tr")
        await ctx.send(f"✅ Bot çalışıyor!\n\n{test[:200]}...")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command(name='ailearn')
async def ailearn(ctx, *, new_info: str):
    if ctx.channel.id != LEARNING_CHANNEL_ID:
        return
    if ctx.author.id in ALLOWED_USER_IDS or not ALLOWED_USER_IDS:
        try:
            update_knowledge(new_info)
            await ctx.send("📚 Bilgi öğrenildi!")
        except Exception as e:
            await ctx.send(f"❌ Hata: {e}")

# ======================
# RUN BOT
# ======================
bot.run(DISCORD_TOKEN)
