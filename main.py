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
            content = f.read()
            print(f"✅ Knowledge base yuklendi: {len(content)} karakter")
            return content
    except Exception as e:
        print(f"❌ Knowledge base yuklenemedi: {e}")
        return ""

# Knowledge base yazma
def save_knowledge_base(content):
    try:
        with open('knowledge_base.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Knowledge base kaydedildi")
    except Exception as e:
        print(f"❌ Knowledge base kaydedilemedi: {e}")

# Geliştirilmiş dil algılama
def detect_language(text):
    # Türkçe karakterler
    turkish_chars = set('çğıöşüÇĞİÖŞÜ')
    if any(char in text for char in turkish_chars):
        print(f"🇹🇷 Turk karakteri algilandi")
        return 'tr'
    
    # Türkçe kelimeler (daha geniş liste)
    turkish_words = ['nedir', 'nasil', 'ne', 'bu', 'su', 'var', 'yok', 'icin', 
                     'nerede', 'nasil', 'hangi', 'kim', 'ne zaman', 'kac', 
                     'yapilir', 'olur', 'midir', 'medir', 'dir', 'tir',
                     'mastery', 'sistem', 'limit', 'odul', 'drop', 'unique',
                     've', 'ile', 'mi', 'mu', 'mı', 'mü']
    
    text_lower = text.lower()
    turkish_word_count = sum(1 for word in turkish_words if word in text_lower)
    
    if turkish_word_count >= 1:
        print(f"🇹🇷 {turkish_word_count} Turkce kelime bulundu")
        return 'tr'
    
    # İngilizce kelimeler
    english_words = ['what', 'how', 'where', 'when', 'who', 'is', 'are', 'the', 'a', 'an']
    english_word_count = sum(1 for word in english_words if word in text_lower)
    
    if english_word_count >= 1:
        print(f"🇬🇧 Ingilizce algilandi")
        return 'en'
    
    # Varsayılan: Türkçe (çünkü Türk sunucusu)
    print(f"🇹🇷 Varsayilan: Turkce")
    return 'tr'

# AI yanıt üretme
async def get_ai_response(user_message, language):
    kb = load_knowledge_base()
    
    if not kb:
        return "⚠️ Bilgi bankası yüklenemedi. Lütfen yöneticiye bildirin."
    
    if language == 'tr':
        system_prompt = f"""Sen Jaynora AI Support (SroEdge) botsun.

ÖNEMLİ KURALLAR:
1. SADECE knowledge base'deki bilgileri kullan - tahmin yapma!
2. Cevapları TÜRKÇE ver (Türk sunucusuyuz)
3. Bilgi yoksa: "Bu konuda bilgim yok, <@&{SUPPORT_ROLE_ID}> yardımcı olacaktır"
4. Kısa, net, madde madde cevapla
5. Samimi ama profesyonel ol
6. Emoji kullan: ℹ️ (bilgi), ⚠️ (uyarı), ✅ (başarı), 💙 (destek)

KNOWLEDGE BASE:
{kb}

Kullanıcı dili: Türkçe
TÜRKÇE CEVAP VER!"""
    else:
        system_prompt = f"""You are Jaynora AI Support (SroEdge).

IMPORTANT RULES:
1. ONLY use information from knowledge base - no guessing!
2. Answer in ENGLISH
3. If no info: "I don't have info about this, <@&{SUPPORT_ROLE_ID}> will help"
4. Be concise, clear, use bullet points
5. Friendly but professional tone
6. Use emojis: ℹ️ (info), ⚠️ (warning), ✅ (success), 💙 (support)

KNOWLEDGE BASE:
{kb}

User language: English
RESPOND IN ENGLISH!"""

    try:
        print(f"🤖 AI cagrisi yapiliyor... Dil: {language}")
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=800
        )
        answer = response.choices[0].message.content
        print(f"✅ AI cevap verdi: {len(answer)} karakter")
        return answer
    except Exception as e:
        print(f"❌ AI hatasi: {e}")
        if language == 'tr':
            return f"⚠️ Bir hata oluştu: {str(e)}"
        else:
            return f"⚠️ An error occurred: {str(e)}"

# Bilgi güncelleme
def update_knowledge(new_info):
    kb = load_knowledge_base()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    updated_kb = kb + f"\n\n[UPDATE_{timestamp}]\n{new_info}\n"
    save_knowledge_base(updated_kb)
    return True

@bot.event
async def on_ready():
    print(f'✅ {bot.user} olarak giriş yapıldı!')
    print(f'Bot ID: {bot.user.id}')
    print(f'Sunucular: {len(bot.guilds)}')
    
    # Knowledge base'i kontrol et
    kb = load_knowledge_base()
    if kb:
        print(f"✅ Knowledge base OK: {len(kb)} karakter")
    else:
        print(f"❌ Knowledge base BOŞ!")

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
                print(f"📚 Otomatik öğrenme: {message.author} - {len(message.content)} karakter")
            except Exception as e:
                await message.add_reaction('❌')
                print(f"❌ Öğrenme hatası: {e}")
        return
    
    # Ticket kanalı kontrolü (kanal adı "ticket" içeriyorsa)
    if 'ticket' not in message.channel.name.lower():
        return
    
    # Kanal devre dışı mı?
    if message.channel.id in disabled_channels:
        return
    
    print(f"💬 Mesaj alındı: {message.author} - {message.content[:50]}...")
    
    # AI yanıt üret
    language = detect_language(message.content)
    response = await get_ai_response(message.content, language)
    
    # Support etiketleme kontrolü
    if SUPPORT_ROLE_ID and ("<@&" not in response):
        if "support" in response.lower() or "yöneticiye" in response.lower() or "bilgim yok" in response.lower():
            response = response + f"\n\n<@&{SUPPORT_ROLE_ID}>"
    
    await message.reply(response)
    print(f"✅ Cevap gönderildi")

# Komutlar
@bot.command(name='ai-restart')
async def ai_restart(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    load_knowledge_base()
    await ctx.send("🔄 Senin için yeniden hazırım! 💙")

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
        # Knowledge base kontrolü
        kb = load_knowledge_base()
        kb_status = f"✅ {len(kb)} karakter" if kb else "❌ BOŞ!"
        
        # Test cevabı
        test_response = await get_ai_response("Mastery limiti nedir?", "tr")
        
        await ctx.send(f"""✅ **Bot Çalışıyor!**

📊 **Durum:**
- Knowledge Base: {kb_status}
- Test Dili: Türkçe 🇹🇷

📝 **Test Cevabı:**
{test_response[:300]}...""")
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
            print(f"📚 Manuel öğrenme: {ctx.author} - {len(new_info)} karakter")
        except Exception as e:
            await ctx.send(f"❌ Hata: {str(e)}")

bot.run(DISCORD_TOKEN)
