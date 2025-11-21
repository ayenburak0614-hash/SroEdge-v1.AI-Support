
import discord
from discord.ext import commands
import openai
import os
import json
from datetime import datetime
import asyncio

# ================================
#  ENVIRONMENT VARIABLES
# ================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SUPPORT_ROLE_ID = int(os.getenv("SUPPORT_ROLE_ID", "0"))
LEARNING_CHANNEL_ID = int(os.getenv("LEARNING_CHANNEL_ID", "0"))  # ai-learn kanalı
COMMANDS_CHANNEL_ID = int(os.getenv("COMMANDS_CHANNEL_ID", "0"))  # yönetim komut kanalı
AI_LOGS_CHANNEL_ID = int(os.getenv("AI_LOGS_CHANNEL_ID", "0"))    # ai-logs kanalı

ALLOWED_USER_IDS = json.loads(os.getenv("ALLOWED_USER_IDS", "[]"))

openai.api_key = OPENAI_API_KEY

# ================================
#  BOT SETUP
# ================================
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================================
#  RUNTIME STATE
# ================================
disabled_channels = set()  # AI devre dışı ticket kanalları

stats = {
    "total_questions": 0,
    "turkish_questions": 0,
    "english_questions": 0,
    "support_escalations": 0,
    "tickets_handled": 0,
    "bot_start_time": None,
}

activity_log = []
MAX_LOG_ENTRIES = 50

ticket_data = {}         # ticket istatistikleri
user_messages = {}       # mesaj birleştirme
support_messages = {}    # supporter cevapları (ticket bazlı)
delete_confirmations = {}  # mesaj silme onayları
ticket_learn_queue = {}    # ticket -> ai-learn embed onay kuyruğu

MESSAGE_DELAY = 5  # saniye (mesaj birleştirme süresi)


# ================================
#  YARDIMCI FONKSİYONLAR
# ================================
def add_to_log(entry_type, channel_name, user, message, language, escalated=False):
    """Activity log'a yeni giriş ekle."""
    activity_log.append(
        {
            "timestamp": datetime.now(),
            "type": entry_type,
            "channel": channel_name,
            "user": str(user),
            "message": message[:100],
            "language": language,
            "escalated": escalated,
        }
    )
    if len(activity_log) > MAX_LOG_ENTRIES:
        activity_log.pop(0)


def load_knowledge_base():
    try:
        with open("knowledge_base.txt", "r", encoding="utf-8") as f:
            content = f.read()
            print(f"✅ Knowledge base yüklendi: {len(content)} karakter")
            return content
    except Exception as e:
        print(f"❌ Knowledge base yüklenemedi: {e}")
        return ""


def save_knowledge_base(content: str):
    try:
        with open("knowledge_base.txt", "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Knowledge base kaydedildi")
    except Exception as e:
        print(f"❌ Knowledge base kaydedilemedi: {e}")


def append_to_knowledge_base(block: str):
    """Yeni formatlı bloğu knowledge_base.txt sonuna ekler."""
    kb = load_knowledge_base()
    updated = (kb.rstrip() + "\n\n" + block.strip() + "\n").lstrip()
    save_knowledge_base(updated)


def detect_language(text: str) -> str:
    text_lower = text.lower().strip()

    turkish_chars = set("çğıöşüÇĞİÖŞÜ")
    if any(char in text for char in turkish_chars):
        print("🇹🇷 Türkçe karakter algılandı")
        return "tr"

    definite_english = [
        "hello",
        "hi",
        "hey",
        "thanks",
        "thank you",
        "please",
        "yes",
        "no",
        "okay",
        "ok",
        "what",
        "how",
        "why",
        "when",
        "where",
        "who",
        "can you",
        "could you",
        "would you",
    ]

    for eng_word in definite_english:
        if eng_word in text_lower:
            print(f"🇬🇧 Kesin İngilizce kelime bulundu: '{eng_word}'")
            return "en"

    turkish_keywords = [
        "merhaba",
        "selam",
        "nedir",
        "nasıl",
        "neden",
        "niye",
        "var",
        "yok",
        "evet",
        "hayır",
        "teşekkür",
        "teşekkürler",
        "lütfen",
        "için",
        "ile",
        "bu",
        "şu",
        "o",
        "ben",
        "sen",
        "biz",
        "siz",
        "onlar",
        "şey",
        "gibi",
        "ama",
        "veya",
        "ve",
        "ki",
        "mi",
        "mu",
        "mü",
        "mı",
        "dir",
        "dır",
        "nerede",
        "hangi",
        "kim",
        "ne",
        "kaç",
        "olan",
        "olur",
        "yapılır",
        "acaba",
        "bana",
        "sana",
        "onun",
        "bizim",
        "sizin",
        "tamam",
    ]

    for tr_word in turkish_keywords:
        if tr_word in text_lower:
            print(f"🇹🇷 Türkçe kelime bulundu: '{tr_word}'")
            return "tr"

    english_grammar = [
        " the ",
        " is ",
        " are ",
        " was ",
        " were ",
        " have ",
        " has ",
        " do ",
        " does ",
        " can ",
        " could ",
        " would ",
        " should ",
    ]

    for eng_grammar in english_grammar:
        if eng_grammar in f" {text_lower} ":
            print("🇬🇧 İngilizce dilbilgisi bulundu")
            return "en"

    print("🇹🇷 Varsayılan: Türkçe")
    return "tr"


async def get_ai_response(user_message: str, language: str) -> str:
    kb = load_knowledge_base()

    if not kb:
        return "⚠️ Bilgi bankası yüklenemedi. Lütfen yöneticiye bildirin."

    if language == "tr":
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
        print(f"🤖 AI çağrısı yapılıyor... Dil: {language}")
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.4,
            max_tokens=1000,
        )
        answer = response.choices[0].message.content
        print(f"✅ AI cevap verdi: {len(answer)} karakter")

        stats["total_questions"] += 1
        if language == "tr":
            stats["turkish_questions"] += 1
        else:
            stats["english_questions"] += 1

        return answer
    except Exception as e:
        print(f"❌ AI hatası: {e}")
        if language == "tr":
            return f"⚠️ Bir hata oluştu: {str(e)}"
        else:
            return f"⚠️ An error occurred: {str(e)}"


def format_new_knowledge(new_info: str, user_question: str | None = None) -> str:
    """
    Gelen ham metni Jaynora knowledge_base formatına dönüştürmek için
    OpenAI'ye kısa bir istek gönderir.
    """
    base_instruction = """Sen Jaynora AI Support için knowledge base formatlayıcısısın.

Görevin:
- Verilen bilgiyi, mevcut Jaynora knowledge_base yapısına uygun şekilde formatlamak.
- Mümkünse uygun bir CATEGORY seç (örnek: [SYSTEM_LIMITS], [UNIQUE_MEDUSA], [EVENT_LOGIN], [SHOP_SILK] vb.)
- Uygun kategori yoksa yeni ve mantıklı bir CATEGORY oluştur (örnek: [EVENT_ICE_DEMON]).

FORMAT ÖRNEĞİ:
===============================================================
[CATEGORY_NAME]
Başlık
===============================================================
- Madde 1
- Madde 2
- Madde 3

Sadece bu formatta cevap ver. Açıklama ekleme, sistem mesajı yazma.
"""

    if user_question:
        user_content = f"Kullanıcı sorusu:\n{user_question}\n\nYeni bilgi:\n{new_info}"
    else:
        user_content = f"Yeni bilgi:\n{new_info}"

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": base_instruction},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        formatted = resp.choices[0].message.content.strip()
        print("✅ Yeni bilgi formatlandı")
        return formatted
    except Exception as e:
        print(f"❌ Bilgi formatlama hatası: {e}")
        # Formatlama başarısız olursa, ham bilgiyi basit bir UPDATE bloğu olarak ekle
        fallback = f"""===============================================================
[UPDATE_{datetime.now().strftime("%Y%m%d_%H%M%S")}]
Manuel Güncelleme
===============================================================
- {new_info}
"""
        return fallback


async def log_learned_info(source: str, formatted_block: str):
    """Detaylı ai-logs formatı"""
    if AI_LOGS_CHANNEL_ID == 0:
        return
    channel = bot.get_channel(AI_LOGS_CHANNEL_ID)
    if channel is None:
        return
    import re
    category_match = re.search(r"\[(.*?)\]", formatted_block)
    category_name = category_match.group(1) if category_match else "Bilinmeyen_Kategori"
    lines = formatted_block.splitlines()
    items = [line.strip()[2:] for line in lines if line.strip().startswith("- ")]
    if not items:
        items = [formatted_block.strip()]
    header = "🧠 Bugün çok güzel bilgiler öğrendim!"
    separator = "====================="
    content_lines = [
        header,
        separator,
        f"📌 **Kategori:** [{category_name}]",
        f"📥 **Kaynak:** {source}",
        separator,
        "📝 **Eklenen / Güncellenen Bilgi:**",
    ]
    for item in items:
        content_lines.append(f"- {item}")
        content_lines.append(separator)
    text = "
".join(content_lines)
    if len(text) > 1900:
        text = text[:1800] + "
... (kısaltıldı)"
    await channel.send(text)


# ================================
#  TICKET MESAJLARI / WELCOME & SUMMARY
# ================================
async def send_welcome_message(channel: discord.TextChannel, language: str):
    if language == "tr":
        embed = discord.Embed(
            title="🎮 Jaynora AI Support'a Hoş Geldin!",
            description="Merhaba! Ben Jaynora AI, sana yardımcı olmak için buradayım! 💙",
            color=0x5865F2,
        )
        embed.add_field(
            name="📝 Nasıl Yardımcı Olabilirim?",
            value="• Oyun sistemleri hakkında bilgi\n• Event ve unique detayları\n• Drop ve ödüller\n• Kurallar ve limitler",
            inline=False,
        )
        embed.add_field(
            name="⚠️ Önemli",
            value="Eğer bilmediğim bir şey sorarsan, destek ekibini etiketleyeceğim!",
            inline=False,
        )
        embed.set_footer(text="Sorunu detaylı anlat, sana en iyi şekilde yardımcı olayım! 🚀")
    else:
        embed = discord.Embed(
            title="🎮 Welcome to Jaynora AI Support!",
            description="Hello! I'm Jaynora AI, here to help you! 💙",
            color=0x5865F2,
        )
        embed.add_field(
            name="📝 How Can I Help?",
            value="• Game systems info\n• Events and uniques\n• Drops and rewards\n• Rules and limits",
            inline=False,
        )
        embed.add_field(
            name="⚠️ Important",
            value="If you ask something I don't know, I'll tag the support team!",
            inline=False,
        )
        embed.set_footer(text="Describe your issue in detail, I'll help you best! 🚀")

    await channel.send(embed=embed)


async def send_ticket_summary(channel: discord.TextChannel, ticket_id: int):
    if ticket_id not in ticket_data:
        return

    data = ticket_data[ticket_id]
    duration = datetime.now() - data["created_at"]
    duration_str = (
        f"{duration.seconds // 60} dakika"
        if duration.seconds < 3600
        else f"{duration.seconds // 3600} saat"
    )

    language = data.get("language", "tr")

    if language == "tr":
        embed = discord.Embed(
            title="📊 Ticket Özeti",
            description="Bu ticket kapandı. İşte özet:",
            color=0x00FF00,
        )
        embed.add_field(name="⏰ Açık Kalma Süresi", value=duration_str, inline=True)
        embed.add_field(name="💬 Toplam Mesaj", value=str(data["message_count"]), inline=True)
        embed.add_field(name="🤖 AI Cevapları", value=str(data["ai_responses"]), inline=True)
        embed.add_field(name="🆘 Support Yönlendirme", value=str(data["escalations"]), inline=True)

        if data["escalations"] == 0:
            embed.add_field(name="✅ Sonuç", value="Sorun AI tarafından çözüldü!", inline=False)
        else:
            embed.add_field(name="👥 Sonuç", value="Support ekibi devreye girdi.", inline=False)

        embed.set_footer(text="Jaynora AI Support ile çalıştığımız için teşekkürler! 💙")
    else:
        embed = discord.Embed(
            title="📊 Ticket Summary",
            description="This ticket is closed. Here's the summary:",
            color=0x00FF00,
        )
        embed.add_field(name="⏰ Duration", value=duration_str, inline=True)
        embed.add_field(name="💬 Total Messages", value=str(data["message_count"]), inline=True)
        embed.add_field(name="🤖 AI Responses", value=str(data["ai_responses"]), inline=True)
        embed.add_field(name="🆘 Support Escalations", value=str(data["escalations"]), inline=True)

        if data["escalations"] == 0:
            embed.add_field(name="✅ Result", value="Issue resolved by AI!", inline=False)
        else:
            embed.add_field(name="👥 Result", value="Support team assisted.", inline=False)

        embed.set_footer(text="Thanks for using Jaynora AI Support! 💙")

    await channel.send(embed=embed)
    stats["tickets_handled"] += 1


# ================================
#  BOT EVENTS
# ================================
@bot.event
async def on_ready():
    print(f"✅ {bot.user} olarak giriş yapıldı!")
    print(f"Bot ID: {bot.user.id}")
    print(f"Sunucular: {len(bot.guilds)}")

    stats["bot_start_time"] = datetime.now()

    kb = load_knowledge_base()
    if kb:
        print(f"✅ Knowledge base OK: {len(kb)} karakter")
    else:
        print("❌ Knowledge base BOŞ!")

    await bot.change_presence(
        activity=discord.Game(name="🎮 Jaynora'da sorulara cevap veriyorum!")
    )


@bot.event
async def on_guild_channel_create(channel):
    # TicketTool ticket kanalları
    if "ticket" in channel.name.lower():
        await asyncio.sleep(2)
        language = "tr"

        ticket_data[channel.id] = {
            "created_at": datetime.now(),
            "message_count": 0,
            "ai_responses": 0,
            "escalations": 0,
            "language": language,
        }

        await send_welcome_message(channel, language)
        print(f"🎫 Yeni ticket: {channel.name}")


@bot.event
async def on_guild_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
    """
    TicketTool kapanışı:
    ticket-001  ->  closed-001
    """
    try:
        before_name = before.name.lower()
        after_name = after.name.lower()
    except AttributeError:
        return

    if before_name.startswith("ticket-") and after_name.startswith("closed-"):
        ticket_id = before.id
        print(f"📌 Ticket kapandı (rename): {before.name} → {after.name}")

        # Ticket özeti gönder
        if ticket_id in ticket_data:
            await send_ticket_summary(after, ticket_id)
            del ticket_data[ticket_id]

        # Support öğrenme sistemi tetikleme
        if ticket_id not in support_messages or len(support_messages[ticket_id]) == 0:
            print("ℹ️ Bu ticket için öğrenilecek kayıtlı support mesajı yok.")
            return

        learning_channel = bot.get_channel(LEARNING_CHANNEL_ID)
        if learning_channel is None:
            print("❌ LEARNING_CHANNEL bulunamadı!")
            return

        for idx, support_msg in enumerate(support_messages[ticket_id], 1):
            user_question = support_msg.get("user_question")
            support_answer = support_msg.get("content")
            supporter = support_msg.get("user")

            embed = discord.Embed(
                title=f"📚 Yeni Bilgi Öğrenme Talebi #{idx}",
                color=0xFFD700,
            )
            embed.add_field(name="🎫 Ticket", value=before.name, inline=False)

            if user_question:
                embed.add_field(
                    name="❓ Kullanıcı Sorusu",
                    value=f"```{user_question[:400]}```",
                    inline=False,
                )

            embed.add_field(
                name="💬 Support Cevabı",
                value=f"👨‍💼 {supporter}\n```{support_answer[:800]}```",
                inline=False,
            )

            embed.set_footer(text="Bu bilgiyi knowledge_base'e eklemek ister misin?")
            msg = await learning_channel.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            ticket_learn_queue[msg.id] = {
                "ticket_name": before.name,
                "supporter": supporter,
                "user_question": user_question,
                "support_answer": support_answer,
            }

        # Temizle
        del support_messages[ticket_id]
        print(f"📚 Ticket için öğrenme talepleri gönderildi: {before.name}")


@bot.event
async def on_guild_channel_delete(channel):
    # Artık TicketTool kanalı silmediği için burada sadece temizleme yapıyoruz
    if channel.id in ticket_data:
        del ticket_data[channel.id]
    if channel.id in support_messages:
        del support_messages[channel.id]
    if channel.id in disabled_channels:
        disabled_channels.discard(channel.id)
    print(f"🗑️ Kanal silindi, veriler temizlendi: {channel.name}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Önce komutları işle
    await bot.process_commands(message)

    # === 1) LEARNING CHANNEL AUTO-UPDATE SİSTEMİ ===
    if message.channel.id == LEARNING_CHANNEL_ID:
        # Komut değilse (ör: !ai-learn hariç)
        if not message.content.startswith("!"):
            if message.author.id in ALLOWED_USER_IDS or not ALLOWED_USER_IDS:
                raw_text = message.content.strip()
                if raw_text:
                    # Yeni bilgiyi formatla ve kaydet
                    formatted = format_new_knowledge(raw_text)
                    append_to_knowledge_base(formatted)
                    await message.add_reaction("✅")
                    await log_learned_info("Update ile Öğrenim", formatted)
                    print(
                        f"📚 Otomatik update ile öğrenim: {message.author} - {len(raw_text)} karakter"
                    )
                else:
                    await message.add_reaction("❌")
            return

    # === 2) TICKET MESAJLARI ===
    if "ticket" not in message.channel.name.lower():
        return

    # AI devre dışıysa ve SUPPORT ise: support cevabını kaydet
    if message.channel.id in disabled_channels:
        member = message.author
        if isinstance(member, discord.Member):
            role_ids = [role.id for role in member.roles]
            if SUPPORT_ROLE_ID in role_ids:
                if message.channel.id not in support_messages:
                    support_messages[message.channel.id] = []

                last_user_question = None
                if (
                    message.channel.id in user_messages
                    and user_messages[message.channel.id]["messages"]
                ):
                    last_user_question = " ".join(
                        user_messages[message.channel.id]["messages"]
                    )

                support_messages[message.channel.id].append(
                    {
                        "user": str(message.author),
                        "content": message.content,
                        "timestamp": datetime.now(),
                        "user_id": message.author.id,
                        "user_question": last_user_question,
                    }
                )
                print(
                    f"📝 Support mesajı kaydedildi: {message.author} - {message.content[:50]}..."
                )
        return

    # Ticket istatistik
    if message.channel.id not in ticket_data:
        ticket_data[message.channel.id] = {
            "created_at": datetime.now(),
            "message_count": 0,
            "ai_responses": 0,
            "escalations": 0,
            "language": "tr",
        }

    ticket_data[message.channel.id]["message_count"] += 1

    print(f"💬 Mesaj alındı: {message.author} - {message.content[:50]}...")

    # Mesaj birleştirme (aynı ticket içerisinde)
    channel_id = message.channel.id
    user_id = message.author.id

    if channel_id not in user_messages:
        user_messages[channel_id] = {
            "user_id": user_id,
            "messages": [],
            "last_time": datetime.now(),
            "task": None,
        }

    if user_messages[channel_id]["user_id"] != user_id:
        if user_messages[channel_id]["task"]:
            user_messages[channel_id]["task"].cancel()

        user_messages[channel_id] = {
            "user_id": user_id,
            "messages": [],
            "last_time": datetime.now(),
            "task": None,
        }

    user_messages[channel_id]["messages"].append(message.content)
    user_messages[channel_id]["last_time"] = datetime.now()

    if user_messages[channel_id]["task"]:
        user_messages[channel_id]["task"].cancel()

    async def delayed_response():
        try:
            await asyncio.sleep(MESSAGE_DELAY)

            combined_message = " ".join(user_messages[channel_id]["messages"])
            print(
                f"📦 Mesajlar birleştirildi ({len(user_messages[channel_id]['messages'])} mesaj): {combined_message[:100]}..."
            )

            language = detect_language(combined_message)
            ticket_data[message.channel.id]["language"] = language

            response = await get_ai_response(combined_message, language)

            needs_escalation = False
            response_lower = response.lower()

            if (
                "bilgim yok" in response_lower
                or "don't have info" in response_lower
                or "i don't have" in response_lower
            ):
                needs_escalation = True
                ticket_data[message.channel.id]["escalations"] += 1
                stats["support_escalations"] += 1

                disabled_channels.add(message.channel.id)

                if SUPPORT_ROLE_ID and f"<@&{SUPPORT_ROLE_ID}>" not in response:
                    response += f"\n\n<@&{SUPPORT_ROLE_ID}>"

                if language == "tr":
                    response += "\n\n🤖 **Not:** Bu ticket için AI desteğini Support ekibine devraldım. Artık bu kanalda cevap vermeyeceğim. İyi çalışmalar! 💙"
                else:
                    response += "\n\n🤖 **Note:** I've handed over this ticket to the Support team. I won't respond in this channel anymore. Good luck! 💙"

            ticket_data[message.channel.id]["ai_responses"] += 1

            add_to_log(
                "question",
                message.channel.name,
                message.author,
                combined_message,
                language,
                needs_escalation,
            )

            await message.reply(response)
            print("✅ Cevap gönderildi")

            if needs_escalation:
                print(f"🔇 AI bu ticket için devre dışı: {message.channel.name}")

            user_messages[channel_id]["messages"] = []
            user_messages[channel_id]["task"] = None

        except asyncio.CancelledError:
            print("⏱️ Task iptal edildi (yeni mesaj geldi)")

    task = asyncio.create_task(delayed_response())
    user_messages[channel_id]["task"] = task


# ================================
#  REACTION EVENT (ÖĞRENME + DELETE ONAY)
# ================================
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    # 1) Mesaj silme onayı
    if payload.message_id in delete_confirmations:
        confirm_data = delete_confirmations[payload.message_id]

        if payload.user_id != confirm_data["user_id"]:
            return

        channel = confirm_data["channel"]
        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        if str(payload.emoji) == "✅":
            try:
                if confirm_data["type"] == "all":
                    deleted_count = 0
                    while True:
                        messages = []
                        async for msg in channel.history(limit=100):
                            messages.append(msg)

                        if not messages:
                            break

                        await channel.delete_messages(messages)
                        deleted_count += len(messages)

                        if len(messages) < 100:
                            break

                    success_msg = await channel.send(
                        f"✅ **{deleted_count}** mesaj silindi!"
                    )
                    await asyncio.sleep(5)
                    await success_msg.delete()

                    print(f"🗑️ Tüm mesajlar silindi: {deleted_count} mesaj")

                elif confirm_data["type"] == "user":
                    target_user_id = confirm_data["target"]
                    deleted_count = 0

                    def check_user(m):
                        return m.author.id == target_user_id

                    while True:
                        deleted = await channel.purge(limit=100, check=check_user)
                        deleted_count += len(deleted)

                        if len(deleted) < 100:
                            break

                    success_msg = await channel.send(
                        f"✅ **{deleted_count}** mesaj silindi!"
                    )
                    await asyncio.sleep(5)
                    await success_msg.delete()

                    print(f"🗑️ Kullanıcı mesajları silindi: {deleted_count} mesaj")

            except Exception as e:
                await channel.send(f"❌ Silme hatası: {str(e)}")

            del delete_confirmations[payload.message_id]

        elif str(payload.emoji) == "❌":
            cancel_embed = discord.Embed(
                title="❌ İşlem İptal Edildi",
                description="Mesajlar silinmedi.",
                color=0x95A5A6,
            )

            await message.edit(embed=cancel_embed)
            await message.clear_reactions()

            del delete_confirmations[payload.message_id]

            print("❌ Silme işlemi iptal edildi")

        return

    # 2) Ticket'tan gelen öğrenme embed'leri
    if payload.message_id in ticket_learn_queue:
        data = ticket_learn_queue[payload.message_id]

        channel = bot.get_channel(payload.channel_id)
        if channel is None:
            return

        try:
            msg = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        if str(payload.emoji) == "❌":
            # Öğrenme iptal
            await msg.edit(
                content="🙅‍♂️ **Kafam zaten çok karışıktı. Teşekkür ederim.**",
                embed=None,
            )
            await msg.clear_reactions()
            del ticket_learn_queue[payload.message_id]
            return

        if str(payload.emoji) == "✅":
            # Bilgiyi formatla ve KB'ye ekle
            formatted = format_new_knowledge(
                data.get("support_answer", ""), data.get("user_question")
            )
            append_to_knowledge_base(formatted)
            await msg.edit(
                content="✅ **Bu ticket'taki bilgi knowledge_base'e eklendi!**",
                embed=None,
            )
            await msg.clear_reactions()

            # ai-logs'a gönder
            await log_learned_info(
                f"Ticket Üzerinden Öğrenim ({data.get('ticket_name')})", formatted
            )

            del ticket_learn_queue[payload.message_id]
            return

    # 3) Diğer reaction'lar önemli değil
    return


# ================================
#  KOMUTLAR
# ================================
@bot.command(name="ai-restart")
async def ai_restart(ctx: commands.Context):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    load_knowledge_base()
    await ctx.send("🔄 Senin için yeniden hazırım! 💙")


@bot.command(name="ai-add")
async def ai_add(ctx: commands.Context, *, new_info: str):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    try:
        formatted = format_new_knowledge(new_info)
        append_to_knowledge_base(formatted)
        await ctx.send("✅ Bilgi başarıyla eklendi/güncellendi!")
        await log_learned_info("Komut ile Öğrenim (ai-add)", formatted)
    except Exception as e:
        await ctx.send(f"❌ Hata: {str(e)}")


@bot.command(name="ai-learn")
async def ai_learn(ctx: commands.Context, *, new_info: str):
    """
    1) Komut ile Öğrenim
    Sadece LEARNING_CHANNEL_ID içinde çalışır.
    """
    if ctx.channel.id != LEARNING_CHANNEL_ID:
        await ctx.send("⚠️ Bu komutu sadece ai-learn kanalında kullanabilirsin!")
        return

    if ctx.author.id not in ALLOWED_USER_IDS and ALLOWED_USER_IDS:
        await ctx.send("⛔ Bu komutu kullanma yetkiniz yok!")
        return

    formatted = format_new_knowledge(new_info)
    append_to_knowledge_base(formatted)
    await ctx.send("✅ Bilgi öğrenildi ve knowledge_base'e eklendi!")
    await log_learned_info("Komut ile Öğrenim (!ai-learn)", formatted)
    print(f"📚 Komut ile öğrenim (!ai-learn): {ctx.author} - {len(new_info)} karakter")


@bot.command(name="ai-dur")
async def ai_dur(ctx: commands.Context):
    if "ticket" not in ctx.channel.name.lower():
        await ctx.send("⚠️ Bu komut sadece ticket kanallarında kullanılabilir!")
        return

    disabled_channels.add(ctx.channel.id)
    await ctx.send("⏸️ Bu kanalde AI devre dışı bırakıldı.")


@bot.command(name="ai-go")
async def ai_go(ctx: commands.Context):
    if "ticket" not in ctx.channel.name.lower():
        await ctx.send("⚠️ Bu komut sadece ticket kanallarında kullanılabilir!")
        return

    disabled_channels.discard(ctx.channel.id)
    await ctx.send("▶️ Bu kanalde AI aktif edildi.")


@bot.command(name="ai-close")
async def ai_close(ctx: commands.Context):
    if "ticket" not in ctx.channel.name.lower():
        await ctx.send("⚠️ Bu komut sadece ticket kanallarında kullanılabilir!")
        return

    await send_ticket_summary(ctx.channel, ctx.channel.id)

    if ctx.channel.id in ticket_data:
        del ticket_data[ctx.channel.id]


@bot.command(name="ai-test")
async def ai_test(ctx: commands.Context):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    try:
        kb = load_knowledge_base()
        kb_status = f"✅ {len(kb)} karakter" if kb else "❌ BOŞ!"

        test_response = await get_ai_response("Mastery limiti nedir?", "tr")

        embed = discord.Embed(title="🧪 Bot Test Sonuçları", color=0x00FF00)
        embed.add_field(name="📊 Knowledge Base", value=kb_status, inline=False)
        embed.add_field(name="🌍 Test Dili", value="🇹🇷 Türkçe", inline=True)
        embed.add_field(name="📈 Toplam Soru", value=str(stats["total_questions"]), inline=True)
        embed.add_field(
            name="🎫 Ticket İşlendi", value=str(stats["tickets_handled"]), inline=True
        )
        embed.add_field(
            name="🎯 Test Cevabı", value=test_response[:300] + "...", inline=False
        )
        embed.set_footer(text="Bot çalışıyor ve hazır! ✅")

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Hata: {str(e)}")


@bot.command(name="ai-stats")
async def ai_stats(ctx: commands.Context):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    embed = discord.Embed(title="📊 Jaynora AI İstatistikleri", color=0x5865F2)
    embed.add_field(name="💬 Toplam Soru", value=str(stats["total_questions"]), inline=True)
    embed.add_field(name="🇹🇷 Türkçe", value=str(stats["turkish_questions"]), inline=True)
    embed.add_field(name="🇬🇧 İngilizce", value=str(stats["english_questions"]), inline=True)
    embed.add_field(
        name="🆘 Support Yönlendirme",
        value=str(stats["support_escalations"]),
        inline=True,
    )
    embed.add_field(
        name="🎫 Ticket İşlendi", value=str(stats["tickets_handled"]), inline=True
    )
    embed.add_field(
        name="⏸️ Kapalı Kanallar", value=str(len(disabled_channels)), inline=True
    )
    embed.add_field(
        name="🎮 Aktif Ticketlar", value=str(len(ticket_data)), inline=True
    )
    embed.add_field(name="🌐 Sunucular", value=str(len(bot.guilds)), inline=True)
    embed.set_footer(text="Jaynora AI Support 💙")

    await ctx.send(embed=embed)


@bot.command(name="ai-logs")
async def ai_logs(ctx: commands.Context):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    if not activity_log:
        await ctx.send("📋 Henüz log kaydı yok.")
        return

    recent_logs = activity_log[-10:]

    embed = discord.Embed(
        title="📋 Son Aktiviteler",
        description=f"Son {len(recent_logs)} aktivite",
        color=0x00D9FF,
    )

    for i, log in enumerate(reversed(recent_logs), 1):
        time_str = log["timestamp"].strftime("%H:%M:%S")
        lang_flag = "🇹🇷" if log["language"] == "tr" else "🇬🇧"
        escalated_icon = "🆘" if log["escalated"] else "✅"

        value = (
            f"{escalated_icon} {lang_flag} `{time_str}`\n"
            f"{log['user'][:20]}\n"
            f"*{log['message'][:50]}...*"
        )

        embed.add_field(
            name=f"{i}. {log['channel'][:20]}",
            value=value,
            inline=False,
        )

    embed.set_footer(text="Jaynora AI Activity Log 📊")
    await ctx.send(embed=embed)


@bot.command(name="ai-knowledge")
async def ai_knowledge(ctx: commands.Context):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    kb = load_knowledge_base()

    if not kb:
        await ctx.send("❌ Knowledge base yüklenemedi!")
        return

    categories = kb.count("[")
    lines = kb.count("\n")
    words = len(kb.split())

    embed = discord.Embed(title="📚 Knowledge Base Bilgileri", color=0xFFD700)
    embed.add_field(
        name="📊 Toplam Karakter", value=f"{len(kb):,}", inline=True
    )
    embed.add_field(name="📝 Toplam Satır", value=f"{lines:,}", inline=True)
    embed.add_field(name="💬 Toplam Kelime", value=f"{words:,}", inline=True)
    embed.add_field(name="🗂️ Kategori Sayısı", value=str(categories), inline=True)
    embed.add_field(name="📅 Son Güncelleme", value="2025-11-20", inline=True)
    embed.add_field(name="✅ Durum", value="Aktif ve Hazır", inline=True)

    main_categories = [
        "SYSTEM",
        "MAP",
        "EVENTS",
        "UNIQUES",
        "JOBS",
        "RANKINGS",
        "SKILLS",
        "SHOPS",
        "FIXES",
    ]

    embed.add_field(
        name="📑 Ana Kategoriler",
        value="\n".join([f"• {cat}" for cat in main_categories]),
        inline=False,
    )

    embed.set_footer(text="Knowledge Base Management 🔧")
    await ctx.send(embed=embed)


@bot.command(name="ai-channels")
async def ai_channels(ctx: commands.Context):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    embed = discord.Embed(title="🎫 Kanal Durumları", color=0xFF6B6B)

    active_tickets = len(ticket_data)
    embed.add_field(
        name="🎮 Aktif Ticketlar", value=str(active_tickets), inline=True
    )

    disabled_count = len(disabled_channels)
    embed.add_field(name="⏸️ Devre Dışı", value=str(disabled_count), inline=True)

    embed.add_field(
        name="✅ Tamamlanan", value=str(stats["tickets_handled"]), inline=True
    )

    if ticket_data:
        ticket_info = []
        for channel_id, data in list(ticket_data.items())[:5]:
            channel = bot.get_channel(channel_id)
            if channel:
                duration = datetime.now() - data["created_at"]
                duration_min = duration.seconds // 60
                lang_flag = "🇹🇷" if data["language"] == "tr" else "🇬🇧"
                ticket_info.append(
                    f"{lang_flag} `{channel.name[:15]}` - {duration_min}dk - {data['message_count']} msg"
                )

        if ticket_info:
            embed.add_field(
                name="📊 Son Aktif Ticketlar",
                value="\n".join(ticket_info),
                inline=False,
            )

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
                inline=False,
            )

    embed.set_footer(text="Channel Management 🎛️")
    await ctx.send(embed=embed)


@bot.command(name="ai-system")
async def ai_system(ctx: commands.Context):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    if stats["bot_start_time"]:
        uptime = datetime.now() - stats["bot_start_time"]
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        uptime_str = f"{uptime.days}g {hours}s {minutes}dk"
    else:
        uptime_str = "Bilinmiyor"

    embed = discord.Embed(
        title="🤖 Sistem Durumu",
        description="Jaynora AI Support Bot Status",
        color=0x00FF00,
    )

    embed.add_field(name="🌐 Sunucular", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="⏰ Uptime", value=uptime_str, inline=True)
    embed.add_field(name="🔋 Durum", value="🟢 Online", inline=True)

    embed.add_field(
        name="💬 Toplam Soru", value=str(stats["total_questions"]), inline=True
    )
    embed.add_field(
        name="🇹🇷 Türkçe", value=str(stats["turkish_questions"]), inline=True
    )
    embed.add_field(
        name="🇬🇧 İngilizce", value=str(stats["english_questions"]), inline=True
    )

    embed.add_field(
        name="🆘 Escalations", value=str(stats["support_escalations"]), inline=True
    )
    embed.add_field(
        name="✅ Tickets Handled", value=str(stats["tickets_handled"]), inline=True
    )
    embed.add_field(
        name="📋 Log Entries", value=str(len(activity_log)), inline=True
    )

    kb = load_knowledge_base()
    kb_size = f"{len(kb):,} karakter" if kb else "❌ Yok"
    embed.add_field(name="📚 Knowledge Base", value=kb_size, inline=True)

    embed.add_field(
        name="🎮 Active Tickets", value=str(len(ticket_data)), inline=True
    )
    embed.add_field(
        name="⏸️ Disabled Channels", value=str(len(disabled_channels)), inline=True
    )

    embed.set_footer(
        text=f"Bot Version: 5.0 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    await ctx.send(embed=embed)


@bot.command(name="ai-reset-stats")
async def ai_reset_stats(ctx: commands.Context):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    embed = discord.Embed(
        title="⚠️ İstatistikleri Sıfırla?",
        description="Tüm istatistikler sıfırlanacak! Emin misiniz?",
        color=0xFF0000,
    )
    embed.add_field(
        name="📊 Sıfırlanacaklar",
        value=(
            "• Toplam soru sayısı\n"
            "• Dil istatistikleri\n"
            "• Support yönlendirme\n"
            "• Ticket sayıları\n"
            "• Activity log"
        ),
    )
    embed.set_footer(text="Onaylamak için: !ai-reset-confirm")

    await ctx.send(embed=embed)


@bot.command(name="ai-reset-confirm")
async def ai_reset_confirm(ctx: commands.Context):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    global activity_log

    stats["total_questions"] = 0
    stats["turkish_questions"] = 0
    stats["english_questions"] = 0
    stats["support_escalations"] = 0
    stats["tickets_handled"] = 0
    activity_log = []

    embed = discord.Embed(
        title="✅ İstatistikler Sıfırlandı",
        description="Tüm istatistikler başarıyla sıfırlandı!",
        color=0x00FF00,
    )
    embed.add_field(
        name="🔄 Yeni Başlangıç",
        value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    await ctx.send(embed=embed)


@bot.command(name="ai-export")
async def ai_export(ctx: commands.Context):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    report = {
        "timestamp": datetime.now().isoformat(),
        "stats": stats.copy(),
        "active_tickets": len(ticket_data),
        "disabled_channels": len(disabled_channels),
        "recent_activities": [
            {
                "time": log["timestamp"].isoformat(),
                "channel": log["channel"],
                "user": log["user"],
                "language": log["language"],
                "escalated": log["escalated"],
            }
            for log in activity_log[-20:]
        ],
    }

    if report["stats"]["bot_start_time"]:
        report["stats"]["bot_start_time"] = report["stats"]["bot_start_time"].isoformat()

    report_json = json.dumps(report, indent=2, ensure_ascii=False)

    embed = discord.Embed(
        title="📊 İstatistik Raporu",
        description="JSON formatında veri dışa aktarma",
        color=0x9B59B6,
    )
    embed.add_field(
        name="📅 Tarih", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    embed.add_field(
        name="📈 Toplam Soru", value=str(stats["total_questions"])
    )
    embed.add_field(
        name="🎫 Tickets", value=str(stats["tickets_handled"])
    )

    if len(report_json) < 1900:
        await ctx.send(embed=embed)
        await ctx.send(f"```json\n{report_json}\n```")
    else:
        await ctx.send(embed=embed)
        await ctx.send("⚠️ Rapor çok uzun, özet gönderiliyor...")
        summary = {
            "stats": report["stats"],
            "active_tickets": report["active_tickets"],
            "disabled_channels": report["disabled_channels"],
            "recent_activities_count": len(report["recent_activities"]),
        }
        await ctx.send(
            f"```json\n{json.dumps(summary, indent=2, ensure_ascii=False)}\n```"
        )


# ================================
#  MESAJ SİLME KOMUTLARI
# ================================
@bot.command(name="ai-delete")
async def ai_delete(ctx: commands.Context, target: str | None = None):
    """Mesaj silme komutu."""
    if ctx.author.id not in ALLOWED_USER_IDS:
        await ctx.send("⛔ Bu komutu kullanma yetkiniz yok!")
        return

    if not target:
        await ctx.send(
            "⚠️ Kullanım: `!ai-delete [sayı]` veya `!ai-delete all` veya `!ai-delete @User`"
        )
        return

    # Tüm mesajları sil
    if target.lower() == "all":
        embed = discord.Embed(
            title="⚠️ Tüm Mesajları Sil?",
            description=f"**{ctx.channel.name}** kanalındaki TÜM mesajlar silinecek!\n\nOnaylıyor musun?",
            color=0xFF0000,
        )
        embed.set_footer(text="✅ Onayla | ❌ Vazgeç")

        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        delete_confirmations[msg.id] = {
            "user_id": ctx.author.id,
            "channel": ctx.channel,
            "type": "all",
            "target": None,
        }

        print(f"🗑️ Silme onayı bekleniyor: {ctx.author} - ALL messages")
        return

    # Belirli kullanıcı mesajlarını sil
    if ctx.message.mentions:
        target_user = ctx.message.mentions[0]

        embed = discord.Embed(
            title="⚠️ Kullanıcı Mesajlarını Sil?",
            description=(
                f"**{target_user.mention}** kullanıcısının **{ctx.channel.name}** "
                "kanalındaki TÜM mesajları silinecek!\n\nOnaylıyor musun?"
            ),
            color=0xFF6B6B,
        )
        embed.set_footer(text="✅ Onayla | ❌ Vazgeç")

        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        delete_confirmations[msg.id] = {
            "user_id": ctx.author.id,
            "channel": ctx.channel,
            "type": "user",
            "target": target_user.id,
        }

        print(
            f"🗑️ Silme onayı bekleniyor: {ctx.author} - User {target_user}"
        )
        return

    # Belirli sayıda mesaj sil
    try:
        amount = int(target)

        if amount < 1:
            await ctx.send("⚠️ Sayı 1'den büyük olmalı!")
            return

        if amount > 100:
            await ctx.send("⚠️ Bir seferde en fazla 100 mesaj silebilirsiniz!")
            return

        deleted = await ctx.channel.purge(limit=amount + 1)

        confirm_msg = await ctx.send(f"✅ {len(deleted) - 1} mesaj silindi!")
        await asyncio.sleep(3)
        await confirm_msg.delete()

        print(
            f"🗑️ {len(deleted) - 1} mesaj silindi: {ctx.author} - {ctx.channel.name}"
        )

    except ValueError:
        await ctx.send(
            "⚠️ Geçersiz format! Kullanım: `!ai-delete [sayı]` veya "
            "`!ai-delete all` veya `!ai-delete @User`"
        )


# ================================
#  BOT ÇALIŞTIR
# ================================
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN bulunamadı! .env dosyasını kontrol et.")
    else:
        bot.run(DISCORD_TOKEN)
