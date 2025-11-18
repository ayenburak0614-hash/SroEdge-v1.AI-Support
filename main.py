import discord
from discord.ext import commands
import openai
import os
import json
from datetime import datetime

# Environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SUPPORT_ROLE_ID = int(os.getenv('SUPPORT_ROLE_ID', '0'))
LEARNING_CHANNEL_ID = int(os.getenv('LEARNING_CHANNEL_ID', '0'))
COMMANDS_CHANNEL_ID = int(os.getenv('COMMANDS_CHANNEL_ID', '0'))
ALLOWED_USER_IDS = json.loads(os.getenv('ALLOWED_USER_IDS', '[]'))

openai.api_key = OPENAI_API_KEY

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Devre dışı kanallar listesi
disabled_channels = set()

# Knowledge base okuma
def load_knowledge_base():
    try:
        with open('knowledge_base.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ""

# Knowledge base yazma
def save_knowledge_base(content):
    with open('knowledge_base.txt', 'w', encoding='utf-8') as f:
        f.write(content)

# Dil algılama
def detect_language(text):
    tr_keywords = [
        'nedir', 'nasil', 'ne zaman', 'neden', 'var mi', 
        'kac', 'fiyat', 'sure', 'gunde', 'oran', 'drobu',
        'buffer', 'event', 'unique', 'slot', 'mob', 'giris'
    ]

    en_keywords = [
        'what', 'when', 'how', 'where', 'why',
        'rate', 'drop', 'event', 'unique', 'skill'
    ]

    # Türkçe karakter kontrolü
    turkish_chars = set('çğıöşüÇĞİÖŞÜ')
    if any(c in turkish_chars for c in text):
        return 'tr'

    # Türkçe kelime kontrolü
    if any(word in text.lower() for word in tr_keywords):
        return 'tr'

    # İngilizce kelime kontrolü
    if any(word in text.lower() for word in en_keywords):
        return 'en'

    # Karışık dil → daha uzun kelime ağırlığı
    tr_score = sum(text.lower().count(w) for w in tr_keywords)
    en_score = sum(text.lower().count(w) for w in en_keywords)

    return 'tr' if tr_score >= en_score else 'en'
    
# AI yanıt üretme
async def get_ai_response(user_message, language):
    kb = load_knowledge_base()

    system_prompt = f"""
Sen Jaynora AI Support botsun. Profesyonel bir oyun yoneticisi gibi cevap verirsin.

GENEL KURALLAR:
1. Sadece knowledge_base icindeki bilgilerle cevap ver.
2. Asla uydurma, tahmin yapma, baska sunuculardan bilgi getirme.
3. Bilgi yoksa Support rolune yonlendir.
4. Tum cevaplari kısa, net ve madde madde yaz.
5. Gereksiz cumle, selamlama, tekrar yok.
6. En fazla 1–2 emoji kullanabilirsin.
7. Cevaplarda asiri uzun paragraflardan kacın.
8. Oyuncuya karsi GM tarzi profesyonel + sicakkanli ton kullan.
9. Kullanicinin dili: {language}

KNOWLEDGE BASE:
{kb}

CEVAP FORMATIN:
- Madde madde
- Kısa ve net
- Bilgi varsa direkt ver
- Bilgi yoksa: "Bu konu hakkında kesin bir bilgi bulunmuyor. Seni ilgili birime yonlendiriyorum <@&{SUPPORT_ROLE_ID}>"
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
        return f"⚠️ Bir hata olustu: {str(e)}"


# Bilgi güncelleme
def update_knowledge(new_info):
    kb = load_knowledge_base()
    lines = kb.split('\n')
    
    # Basit güncelleme mantığı: yeni bilgiyi sona ekle
    # Gelişmiş sürümde konu tespiti yapılabilir
    updated_kb = kb + f"\n\n[UPDATE_{datetime.now().strftime('%Y%m%d_%H%M%S')}]\n{new_info}\n"
    save_knowledge_base(updated_kb)
    return True

@bot.event
async def on_ready():
    print(f'✅ {bot.user} olarak giriş yapıldı!')
    print(f'Bot ID: {bot.user.id}')

@bot.event
async def on_message(message):
    # Bot kendi mesajlarına cevap vermesin
    if message.author.bot:
        return
    
    # Komutları işle
    await bot.process_commands(message)
    
    # Learning channel kontrolü
    if message.channel.id == LEARNING_CHANNEL_ID:
        if message.author.id in ALLOWED_USER_IDS or not ALLOWED_USER_IDS:
            try:
                update_knowledge(message.content)
                await message.add_reaction('✅')
            except:
                await message.add_reaction('❌')
        return
    
    # Ticket kanalı kontrolü (kanal adı "ticket" içeriyorsa)
    if 'ticket' not in message.channel.name.lower():
        return
    
    # Kanal devre dışı mı?
    if message.channel.id in disabled_channels:
        return
    
    # AI yanıt üret
    language = detect_language(message.content)
    response = await get_ai_response(message.content, language)
    
    # Support etiketleme kontrolü
    if "@Support" in response or "kesin bir bilgiye sahip değilim" in response:
        if SUPPORT_ROLE_ID:
            response = response.replace("@Support", f"<@&{SUPPORT_ROLE_ID}>")
    
    await message.reply(response)

# Komutlar
@bot.command(name='ai-restart')
async def ai_restart(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    load_knowledge_base()
    await ctx.send("Senin için yeniden hazırım <3")

@bot.command(name='ai-add')
async def ai_add(ctx, *, new_info: str):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    try:
        update_knowledge(new_info)
        await ctx.send("✅ Bilgi başarıyla eklendi/güncellendi!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {str(e)}")

@bot.command(name='ai-dur')
async def ai_dur(ctx):
    if 'ticket' not in ctx.channel.name.lower():
        await ctx.send("⚠️ Bu komut sadece ticket kanallarında kullanılabilir!")
        return
    
    disabled_channels.add(ctx.channel.id)
    await ctx.send("⏸️ Bu kanalde AI devre dışı bırakıldı.")

@bot.command(name='ai-go')
async def ai_go(ctx):
    if 'ticket' not in ctx.channel.name.lower():
        await ctx.send("⚠️ Bu komut sadece ticket kanallarında kullanılabilir!")
        return
    
    disabled_channels.discard(ctx.channel.id)
    await ctx.send("▶️ Bu kanalde AI aktif edildi.")

@bot.command(name='ai-test')
async def ai_test(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    try:
        test_response = await get_ai_response("Merhaba, test mesajı", "tr")
        await ctx.send(f"✅ Bot çalışıyor!\n\nTest cevabı: {test_response[:200]}...")
    except Exception as e:
        await ctx.send(f"❌ Hata: {str(e)}")

@bot.command(name='ailearn')
async def ailearn(ctx, *, new_info: str):
    if ctx.channel.id != LEARNING_CHANNEL_ID:
        return
    
    if ctx.author.id in ALLOWED_USER_IDS or not ALLOWED_USER_IDS:
        try:
            update_knowledge(new_info)
            await ctx.send("✅ Bilgi öğrenildi!")
        except Exception as e:
            await ctx.send(f"❌ Hata: {str(e)}")

bot.run(DISCORD_TOKEN)

