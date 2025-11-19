import discord
from discord.ext import commands
import openai
import os
import json
from datetime import datetime
import asyncio

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
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Devre dışı kanallar ve istatistikler
disabled_channels = set()
stats = {
    'total_questions': 0,
    'turkish_questions': 0,
    'english_questions': 0,
    'support_escalations': 0,
    'tickets_handled': 0,
    'bot_start_time': None
}

# ⭐ YENİ: Activity log sistemi
activity_log = []
MAX_LOG_ENTRIES = 50

def add_to_log(entry_type, channel_name, user, message, language, escalated=False):
    """Activity log'a yeni giriş ekle"""
    activity_log.append({
        'timestamp': datetime.now(),
        'type': entry_type,
        'channel': channel_name,
        'user': str(user),
        'message': message[:100],
        'language': language,
        'escalated': escalated
    })
    # Son 50 girişi tut
    if len(activity_log) > MAX_LOG_ENTRIES:
        activity_log.pop(0)

# ⭐ YENİ: Ticket takip sistemi
ticket_data = {}

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

# 🔥 SON HAL: Kesin Dil Algılama
def detect_language(text):
    text_lower = text.lower().strip()
    
    # 1. ÖNCE: Türkçe karakterler varsa kesinlikle Türkçe
    turkish_chars = set('çğıöşüÇĞİÖŞÜ')
    if any(char in text for char in turkish_chars):
        print(f"🇹🇷 Türkçe karakter algılandı")
        return 'tr'
    
    # 2. KESİN İngilizce kelimeler (bu kelimeler varsa direkt İngilizce)
    definite_english = ['hello', 'hi', 'hey', 'thanks', 'thank you', 'please', 
                        'yes', 'no', 'okay', 'ok', 'what', 'how', 'why', 'when',
                        'where', 'who', 'can you', 'could you', 'would you']
    
    # Kesin İngilizce kontrolü
    for eng_word in definite_english:
        if eng_word in text_lower:
            print(f"🇬🇧 Kesin İngilizce kelime bulundu: '{eng_word}'")
            return 'en'
    
    # 3. Türkçe kelimeler (İngilizce'de OLMAYAN kelimeler)
    turkish_keywords = [
        'merhaba', 'selam', 'nedir', 'nasıl', 'neden', 'niye', 'var', 'yok', 
        'evet', 'hayır', 'teşekkür', 'teşekkürler', 'lütfen', 'için', 'ile', 
        'bu', 'şu', 'o', 'ben', 'sen', 'biz', 'siz', 'onlar', 'şey', 'gibi',
        'ama', 'veya', 've', 'ki', 'mi', 'mu', 'mü', 'mı', 'dir', 'dır',
        'nerede', 'hangi', 'kim', 'ne', 'kaç', 'olan', 'olur', 'yapılır',
        'acaba', 'bana', 'sana', 'onun', 'bizim', 'sizin', 'tamam'
    ]
    
    # Türkçe kelime var mı?
    for tr_word in turkish_keywords:
        if tr_word in text_lower:
            print(f"🇹🇷 Türkçe kelime bulundu: '{tr_word}'")
            return 'tr'
    
    # 4. İngilizce yardımcı fiiller ve makaleler
    english_grammar = ['the ', ' is ', ' are ', ' was ', ' were ', ' have ', ' has ',
                       ' do ', ' does ', ' can ', ' could ', ' would ', ' should ']
    
    for eng_grammar in english_grammar:
        if eng_grammar in f" {text_lower} ":
            print(f"🇬🇧 İngilizce dilbilgisi bulundu")
            return 'en'
    
    # 5. Hiçbiri yoksa → Türkçe (Türk sunucusu için varsayılan)
    print(f"🇹🇷 Varsayılan: Türkçe")
    return 'tr'

# Gelişmiş AI yanıt üretme
async def get_ai_response(user_message, language):
    kb = load_knowledge_base()
    
    if not kb:
        return "⚠️ Bilgi bankası yüklenemedi. Lütfen yöneticiye bildirin."
    
    if language == 'tr':
        system_prompt = f"""Sen Jaynora AI Support (SroEdge) botsun - oyuncuların en iyi yardımcısı! 🎮

🎯 KİŞİLİĞİN:
- Samimi ama profesyonel
- Hevesli ve yardımsever
- Oyuncu dostu
- Emojilerle desteklenmiş açık iletişim

📜 KURALLARIN:
1. SADECE knowledge base'deki bilgileri kullan - TAHMİN YAPMA!
2. Cevapları her zaman TÜRKÇE ver
3. Bilgi yoksa: "Bu konuda bilgim yok, <@&{SUPPORT_ROLE_ID}> ekibi yardımcı olacaktır 💙"
4. Cevap formatı:
   • Başlık emoji ile başla (ℹ️📊⚔️🎁)
   • Madde madde yaz
   • Kısa ve net ol
   • Önemli bilgileri **bold** yap

🎨 EMOJİ KULLANIMI:
• ℹ️ Genel bilgi
• ⚔️ Savaş/PvP
• 🎁 Ödüller/Drop
• 📊 İstatistikler/Limitler
• ⚠️ Uyarılar
• ✅ Başarı/Onay
• 🎮 Oyun mekaniği
• 💎 Özel itemler
• 🏆 Event/Yarışmalar
• 💙 Destek/Yardım

KNOWLEDGE BASE:
{kb}

Kullanıcı dili: Türkçe
TÜRKÇE, SAMİMİ VE NET CEVAP VER!"""
    else:
        system_prompt = f"""You are Jaynora AI Support (SroEdge) - players' best helper! 🎮

🎯 YOUR PERSONALITY:
- Friendly but professional
- Enthusiastic and helpful
- Player-friendly
- Clear communication with emojis

📜 YOUR RULES:
1. ONLY use information from knowledge base - NO GUESSING!
2. Always answer in ENGLISH
3. If no info: "I don't have info about this, <@&{SUPPORT_ROLE_ID}> team will help 💙"
4. Response format:
   • Start with emoji header (ℹ️📊⚔️🎁)
   • Use bullet points
   • Be concise and clear
   • **Bold** important info

🎨 EMOJI USAGE:
• ℹ️ General info
• ⚔️ Combat/PvP
• 🎁 Rewards/Drops
• 📊 Stats/Limits
• ⚠️ Warnings
• ✅ Success/Confirm
• 🎮 Game mechanics
• 💎 Special items
• 🏆 Events/Contests
• 💙 Support/Help

KNOWLEDGE BASE:
{kb}

User language: English
RESPOND IN ENGLISH, FRIENDLY AND CLEAR!"""

    try:
        print(f"🤖 AI cagrisi yapiliyor... Dil: {language}")
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.4,
            max_tokens=1000
        )
        answer = response.choices[0].message.content
        print(f"✅ AI cevap verdi: {len(answer)} karakter")
        
        stats['total_questions'] += 1
        if language == 'tr':
            stats['turkish_questions'] += 1
        else:
            stats['english_questions'] += 1
        
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

# ⭐ YENİ: Ticket hoş geldin mesajı
async def send_welcome_message(channel, language):
    if language == 'tr':
        embed = discord.Embed(
            title="🎮 Jaynora AI Support'a Hoş Geldin!",
            description="Merhaba! Ben Jaynora AI, sana yardımcı olmak için buradayım! 💙",
            color=0x5865F2
        )
        embed.add_field(
            name="📝 Nasıl Yardımcı Olabilirim?",
            value="• Oyun sistemleri hakkında bilgi\n• Event ve unique detayları\n• Drop ve ödüller\n• Kurallar ve limitler",
            inline=False
        )
        embed.add_field(
            name="⚠️ Önemli",
            value="Eğer bilmediğim bir şey sorarsan, destek ekibini etiketleyeceğim!",
            inline=False
        )
        embed.set_footer(text="Sorunu detaylı anlat, sana en iyi şekilde yardımcı olayım! 🚀")
    else:
        embed = discord.Embed(
            title="🎮 Welcome to Jaynora AI Support!",
            description="Hello! I'm Jaynora AI, here to help you! 💙",
            color=0x5865F2
        )
        embed.add_field(
            name="📝 How Can I Help?",
            value="• Game systems info\n• Events and uniques\n• Drops and rewards\n• Rules and limits",
            inline=False
        )
        embed.add_field(
            name="⚠️ Important",
            value="If you ask something I don't know, I'll tag the support team!",
            inline=False
        )
        embed.set_footer(text="Describe your issue in detail, I'll help you best! 🚀")
    
    await channel.send(embed=embed)

# ⭐ YENİ: Ticket kapanış özeti
async def send_ticket_summary(channel, ticket_id):
    if ticket_id not in ticket_data:
        return
    
    data = ticket_data[ticket_id]
    duration = datetime.now() - data['created_at']
    duration_str = f"{duration.seconds // 60} dakika" if duration.seconds < 3600 else f"{duration.seconds // 3600} saat"
    
    language = data.get('language', 'tr')
    
    if language == 'tr':
        embed = discord.Embed(
            title="📊 Ticket Özeti",
            description="Bu ticket kapandı. İşte özet:",
            color=0x00FF00
        )
        embed.add_field(name="⏰ Açık Kalma Süresi", value=duration_str, inline=True)
        embed.add_field(name="💬 Toplam Mesaj", value=str(data['message_count']), inline=True)
        embed.add_field(name="🤖 AI Cevapları", value=str(data['ai_responses']), inline=True)
        embed.add_field(name="🆘 Support Yönlendirme", value=str(data['escalations']), inline=True)
        
        if data['escalations'] == 0:
            embed.add_field(
                name="✅ Sonuç",
                value="Sorun AI tarafından çözüldü!",
                inline=False
            )
        else:
            embed.add_field(
                name="👥 Sonuç",
                value="Support ekibi devreye girdi.",
                inline=False
            )
        
        embed.set_footer(text="Jaynora AI Support ile çalıştığımız için teşekkürler! 💙")
    else:
        embed = discord.Embed(
            title="📊 Ticket Summary",
            description="This ticket is closed. Here's the summary:",
            color=0x00FF00
        )
        embed.add_field(name="⏰ Duration", value=duration_str, inline=True)
        embed.add_field(name="💬 Total Messages", value=str(data['message_count']), inline=True)
        embed.add_field(name="🤖 AI Responses", value=str(data['ai_responses']), inline=True)
        embed.add_field(name="🆘 Support Escalations", value=str(data['escalations']), inline=True)
        
        if data['escalations'] == 0:
            embed.add_field(
                name="✅ Result",
                value="Issue resolved by AI!",
                inline=False
            )
        else:
            embed.add_field(
                name="👥 Result",
                value="Support team assisted.",
                inline=False
            )
        
        embed.set_footer(text="Thanks for using Jaynora AI Support! 💙")
    
    await channel.send(embed=embed)
    stats['tickets_handled'] += 1

@bot.event
async def on_ready():
    print(f'✅ {bot.user} olarak giriş yapıldı!')
    print(f'Bot ID: {bot.user.id}')
    print(f'Sunucular: {len(bot.guilds)}')
    
    # ⭐ YENİ: Bot başlangıç zamanını kaydet
    stats['bot_start_time'] = datetime.now()
    
    kb = load_knowledge_base()
    if kb:
        print(f"✅ Knowledge base OK: {len(kb)} karakter")
    else:
        print(f"❌ Knowledge base BOŞ!")
    
    await bot.change_presence(activity=discord.Game(name="🎮 Jaynora'da sorulara cevap veriyorum!"))

# ⭐ YENİ: Ticket açılınca hoş geldin
@bot.event
async def on_guild_channel_create(channel):
    if 'ticket' in channel.name.lower():
        await asyncio.sleep(2)
        language = 'tr'
        
        # Ticket verisini başlat
        ticket_data[channel.id] = {
            'created_at': datetime.now(),
            'message_count': 0,
            'ai_responses': 0,
            'escalations': 0,
            'language': language
        }
        
        await send_welcome_message(channel, language)
        print(f"🎫 Yeni ticket: {channel.name}")

# ⭐ YENİ: Ticket silinince özet gönder
@bot.event
async def on_guild_channel_delete(channel):
    if 'ticket' in channel.name.lower() and channel.id in ticket_data:
        # Özet başka bir kanala gönderilemez çünkü kanal silindi
        # Sadece istatistiği güncelle
        stats['tickets_handled'] += 1
        del ticket_data[channel.id]
        print(f"🎫 Ticket silindi: {channel.name}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
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
    
    # Ticket kanalı kontrolü
    if 'ticket' not in message.channel.name.lower():
        return
    
    if message.channel.id in disabled_channels:
        return
    
    # ⭐ YENİ: Ticket verisini güncelle
    if message.channel.id not in ticket_data:
        ticket_data[message.channel.id] = {
            'created_at': datetime.now(),
            'message_count': 0,
            'ai_responses': 0,
            'escalations': 0,
            'language': 'tr'
        }
    
    ticket_data[message.channel.id]['message_count'] += 1
    
    print(f"💬 Mesaj alındı: {message.author} - {message.content[:50]}...")
    
    # AI yanıt üret
    language = detect_language(message.content)
    ticket_data[message.channel.id]['language'] = language
    response = await get_ai_response(message.content, language)
    
    # ⭐ YENİ: Support etiketleme ve AI susturma kontrolü
    needs_escalation = False
    response_lower = response.lower()
    
    # Bilgim yok veya Support geçiyorsa
    if ("bilgim yok" in response_lower or 
        "don't have info" in response_lower or 
        "i don't have" in response_lower or
        "supporter" in response_lower or
        "support" in response_lower):
        
        needs_escalation = True
        ticket_data[message.channel.id]['escalations'] += 1
        stats['support_escalations'] += 1
        
        # ⭐ YENİ: AI'ı bu ticket için devre dışı bırak
        disabled_channels.add(message.channel.id)
        
        # Support rolünü etiketle (eğer henüz etiketli değilse)
        if SUPPORT_ROLE_ID and f"<@&{SUPPORT_ROLE_ID}>" not in response:
            if language == 'tr':
                response += f"\n\n<@&{SUPPORT_ROLE_ID}>"
            else:
                response += f"\n\n<@&{SUPPORT_ROLE_ID}>"
        
        # AI devre dışı mesajı ekle
        if language == 'tr':
            response += "\n\n🤖 **Not:** Bu ticket için AI desteğini Support ekibine devraldım. Artık bu kanalda cevap vermeyeceğim. İyi çalışmalar! 💙"
        else:
            response += "\n\n🤖 **Note:** I've handed over this ticket to the Support team. I won't respond in this channel anymore. Good luck! 💙"
    
    ticket_data[message.channel.id]['ai_responses'] += 1
    
    # ⭐ YENİ: Activity log'a ekle
    add_to_log(
        'question',
        message.channel.name,
        message.author,
        message.content,
        language,
        needs_escalation
    )
    
    await message.reply(response)
    print(f"✅ Cevap gönderildi")
    
    # ⭐ YENİ: AI devre dışı bırakıldıysa log
    if needs_escalation:
        print(f"🔇 AI bu ticket için devre dışı: {message.channel.name}")

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

# ⭐ YENİ: Ticket özeti manuel komut
@bot.command(name='ai-close')
async def ai_close(ctx):
    if 'ticket' not in ctx.channel.name.lower():
        await ctx.send("⚠️ Bu komut sadece ticket kanallarında kullanılabilir!")
        return
    
    await send_ticket_summary(ctx.channel, ctx.channel.id)
    
    # Ticket verisini temizle
    if ctx.channel.id in ticket_data:
        del ticket_data[ctx.channel.id]

@bot.command(name='ai-test')
async def ai_test(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    try:
        kb = load_knowledge_base()
        kb_status = f"✅ {len(kb)} karakter" if kb else "❌ BOŞ!"
        
        test_response = await get_ai_response("Mastery limiti nedir?", "tr")
        
        embed = discord.Embed(
            title="🧪 Bot Test Sonuçları",
            color=0x00FF00
        )
        embed.add_field(name="📊 Knowledge Base", value=kb_status, inline=False)
        embed.add_field(name="🌍 Test Dili", value="🇹🇷 Türkçe", inline=True)
        embed.add_field(name="📈 Toplam Soru", value=str(stats['total_questions']), inline=True)
        embed.add_field(name="🎫 Ticket İşlendi", value=str(stats['tickets_handled']), inline=True)
        embed.add_field(name="🎯 Test Cevabı", value=test_response[:300] + "...", inline=False)
        embed.set_footer(text="Bot çalışıyor ve hazır! ✅")
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Hata: {str(e)}")

@bot.command(name='ai-stats')
async def ai_stats(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    embed = discord.Embed(
        title="📊 Jaynora AI İstatistikleri",
        color=0x5865F2
    )
    embed.add_field(name="💬 Toplam Soru", value=str(stats['total_questions']), inline=True)
    embed.add_field(name="🇹🇷 Türkçe", value=str(stats['turkish_questions']), inline=True)
    embed.add_field(name="🇬🇧 İngilizce", value=str(stats['english_questions']), inline=True)
    embed.add_field(name="🆘 Support Yönlendirme", value=str(stats['support_escalations']), inline=True)
    embed.add_field(name="🎫 Ticket İşlendi", value=str(stats['tickets_handled']), inline=True)
    embed.add_field(name="⏸️ Kapalı Kanallar", value=str(len(disabled_channels)), inline=True)
    embed.add_field(name="🎮 Aktif Ticketlar", value=str(len(ticket_data)), inline=True)
    embed.add_field(name="🌐 Sunucular", value=str(len(bot.guilds)), inline=True)
    embed.set_footer(text="Jaynora AI Support 💙")
    
    await ctx.send(embed=embed)

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

# ⭐ YENİ: Admin Panel Komutları

@bot.command(name='ai-logs')
async def ai_logs(ctx):
    """Son aktiviteleri göster"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    if not activity_log:
        await ctx.send("📋 Henüz log kaydı yok.")
        return
    
    # Son 10 girişi al
    recent_logs = activity_log[-10:]
    
    embed = discord.Embed(
        title="📋 Son Aktiviteler",
        description=f"Son {len(recent_logs)} aktivite",
        color=0x00D9FF
    )
    
    for i, log in enumerate(reversed(recent_logs), 1):
        time_str = log['timestamp'].strftime('%H:%M:%S')
        lang_flag = '🇹🇷' if log['language'] == 'tr' else '🇬🇧'
        escalated_icon = '🆘' if log['escalated'] else '✅'
        
        value = f"{escalated_icon} {lang_flag} `{time_str}`\n{log['user'][:20]}\n*{log['message'][:50]}...*"
        
        embed.add_field(
            name=f"{i}. {log['channel'][:20]}",
            value=value,
            inline=False
        )
    
    embed.set_footer(text="Jaynora AI Activity Log 📊")
    await ctx.send(embed=embed)

@bot.command(name='ai-knowledge')
async def ai_knowledge(ctx):
    """Knowledge base bilgileri"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    kb = load_knowledge_base()
    
    if not kb:
        await ctx.send("❌ Knowledge base yüklenemedi!")
        return
    
    # Kategorileri say
    categories = kb.count('[')
    lines = kb.count('\n')
    words = len(kb.split())
    
    embed = discord.Embed(
        title="📚 Knowledge Base Bilgileri",
        color=0xFFD700
    )
    embed.add_field(name="📊 Toplam Karakter", value=f"{len(kb):,}", inline=True)
    embed.add_field(name="📝 Toplam Satır", value=f"{lines:,}", inline=True)
    embed.add_field(name="💬 Toplam Kelime", value=f"{words:,}", inline=True)
    embed.add_field(name="🗂️ Kategori Sayısı", value=str(categories), inline=True)
    embed.add_field(name="📅 Son Güncelleme", value="2025-11-19", inline=True)
    embed.add_field(name="✅ Durum", value="Aktif ve Hazır", inline=True)
    
    # Ana kategoriler
    main_categories = [
        "SYSTEM", "MAP", "EVENTS", "UNIQUES",
        "JOBS", "RANKINGS", "SKILLS", "SHOPS", "FIXES"
    ]
    
    embed.add_field(
        name="📑 Ana Kategoriler",
        value="\n".join([f"• {cat}" for cat in main_categories]),
        inline=False
    )
    
    embed.set_footer(text="Knowledge Base Management 🔧")
    await ctx.send(embed=embed)

@bot.command(name='ai-channels')
async def ai_channels(ctx):
    """Kanal durumları"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    embed = discord.Embed(
        title="🎫 Kanal Durumları",
        color=0xFF6B6B
    )
    
    # Aktif ticketlar
    active_tickets = len(ticket_data)
    embed.add_field(name="🎮 Aktif Ticketlar", value=str(active_tickets), inline=True)
    
    # Devre dışı kanallar
    disabled_count = len(disabled_channels)
    embed.add_field(name="⏸️ Devre Dışı", value=str(disabled_count), inline=True)
    
    # Toplam ticket işlendi
    embed.add_field(name="✅ Tamamlanan", value=str(stats['tickets_handled']), inline=True)
    
    # Aktif ticket detayları
    if ticket_data:
        ticket_info = []
        for channel_id, data in list(ticket_data.items())[:5]:
            channel = bot.get_channel(channel_id)
            if channel:
                duration = datetime.now() - data['created_at']
                duration_min = duration.seconds // 60
                lang_flag = '🇹🇷' if data['language'] == 'tr' else '🇬🇧'
                ticket_info.append(
                    f"{lang_flag} `{channel.name[:15]}` - {duration_min}dk - {data['message_count']} msg"
                )
        
        if ticket_info:
            embed.add_field(
                name="📊 Son Aktif Ticketlar",
                value="\n".join(ticket_info),
                inline=False
            )
    
    # Devre dışı kanallar
    if disabled_channels:
        disabled_info = []
        for channel_id in list(disabled_channels)[:5]:
            channel = bot.get_channel(channel_id)
            if channel:
                disabled_info.append(f"⏸️ `{channel.name[:20]}`")
        
        if disabled_info:
            embed.add_field(
                name="🔇 Devre Dışı Kanallar",
                value="\n".join(disabled_info),
                inline=False
            )
    
    embed.set_footer(text="Channel Management 🎛️")
    await ctx.send(embed=embed)

@bot.command(name='ai-system')
async def ai_system(ctx):
    """Sistem durumu"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    # Uptime hesapla
    if stats['bot_start_time']:
        uptime = datetime.now() - stats['bot_start_time']
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        uptime_str = f"{uptime.days}g {hours}s {minutes}dk"
    else:
        uptime_str = "Bilinmiyor"
    
    embed = discord.Embed(
        title="🤖 Sistem Durumu",
        description="Jaynora AI Support Bot Status",
        color=0x00FF00
    )
    
    # Bot bilgileri
    embed.add_field(name="🌐 Sunucular", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="⏰ Uptime", value=uptime_str, inline=True)
    embed.add_field(name="🔋 Durum", value="🟢 Online", inline=True)
    
    # İstatistikler
    embed.add_field(name="💬 Toplam Soru", value=str(stats['total_questions']), inline=True)
    embed.add_field(name="🇹🇷 Türkçe", value=str(stats['turkish_questions']), inline=True)
    embed.add_field(name="🇬🇧 İngilizce", value=str(stats['english_questions']), inline=True)
    
    # Performance
    embed.add_field(name="🆘 Escalations", value=str(stats['support_escalations']), inline=True)
    embed.add_field(name="✅ Tickets Handled", value=str(stats['tickets_handled']), inline=True)
    embed.add_field(name="📋 Log Entries", value=str(len(activity_log)), inline=True)
    
    # Knowledge base
    kb = load_knowledge_base()
    kb_size = f"{len(kb):,} karakter" if kb else "❌ Yok"
    embed.add_field(name="📚 Knowledge Base", value=kb_size, inline=True)
    
    embed.add_field(name="🎮 Active Tickets", value=str(len(ticket_data)), inline=True)
    embed.add_field(name="⏸️ Disabled Channels", value=str(len(disabled_channels)), inline=True)
    
    embed.set_footer(text=f"Bot Version: 4.0 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    await ctx.send(embed=embed)

@bot.command(name='ai-reset-stats')
async def ai_reset_stats(ctx):
    """İstatistikleri sıfırla"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    # Onay mesajı
    embed = discord.Embed(
        title="⚠️ İstatistikleri Sıfırla?",
        description="Tüm istatistikler sıfırlanacak! Emin misiniz?",
        color=0xFF0000
    )
    embed.add_field(name="📊 Sıfırlanacaklar", value=(
        "• Toplam soru sayısı\n"
        "• Dil istatistikleri\n"
        "• Support yönlendirme\n"
        "• Ticket sayıları\n"
        "• Activity log"
    ))
    embed.set_footer(text="Onaylamak için: !ai-reset-confirm")
    
    await ctx.send(embed=embed)

@bot.command(name='ai-reset-confirm')
async def ai_reset_confirm(ctx):
    """İstatistikleri sıfırlama onayı"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    global activity_log
    
    # İstatistikleri sıfırla
    stats['total_questions'] = 0
    stats['turkish_questions'] = 0
    stats['english_questions'] = 0
    stats['support_escalations'] = 0
    stats['tickets_handled'] = 0
    activity_log = []
    
    embed = discord.Embed(
        title="✅ İstatistikler Sıfırlandı",
        description="Tüm istatistikler başarıyla sıfırlandı!",
        color=0x00FF00
    )
    embed.add_field(name="🔄 Yeni Başlangıç", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    await ctx.send(embed=embed)

@bot.command(name='ai-export')
async def ai_export(ctx):
    """İstatistikleri dışa aktar"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    # JSON formatında rapor oluştur
    report = {
        'timestamp': datetime.now().isoformat(),
        'stats': stats.copy(),
        'active_tickets': len(ticket_data),
        'disabled_channels': len(disabled_channels),
        'recent_activities': [
            {
                'time': log['timestamp'].isoformat(),
                'channel': log['channel'],
                'user': log['user'],
                'language': log['language'],
                'escalated': log['escalated']
            }
            for log in activity_log[-20:]
        ]
    }
    
    # Bot start time'ı string'e çevir
    if report['stats']['bot_start_time']:
        report['stats']['bot_start_time'] = report['stats']['bot_start_time'].isoformat()
    
    import json
    report_json = json.dumps(report, indent=2, ensure_ascii=False)
    
    embed = discord.Embed(
        title="📊 İstatistik Raporu",
        description="JSON formatında veri dışa aktarma",
        color=0x9B59B6
    )
    embed.add_field(name="📅 Tarih", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    embed.add_field(name="📈 Toplam Soru", value=str(stats['total_questions']))
    embed.add_field(name="🎫 Tickets", value=str(stats['tickets_handled']))
    
    # JSON'u code block olarak gönder (Discord limiti 2000 karakter)
    if len(report_json) < 1900:
        await ctx.send(embed=embed)
        await ctx.send(f"```json\n{report_json}\n```")
    else:
        # Çok uzunsa özet gönder
        await ctx.send(embed=embed)
        await ctx.send("⚠️ Rapor çok uzun, özet gönderiliyor...")
        summary = {
            'stats': report['stats'],
            'active_tickets': report['active_tickets'],
            'disabled_channels': report['disabled_channels'],
            'recent_activities_count': len(report['recent_activities'])
        }
        if summary['stats']['bot_start_time']:
            summary['stats']['bot_start_time'] = summary['stats']['bot_start_time']
        await ctx.send(f"```json\n{json.dumps(summary, indent=2, ensure_ascii=False)}\n```")

bot.run(DISCORD_TOKEN)
