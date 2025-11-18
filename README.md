?? Jaynora AI Support Bot
Discord ticket sistemi için yapay zeka destekli destek botu.

?? Özellikler
? Ticket kanallarýnda otomatik AI desteði
? Türkçe & Ýngilizce dil algýlama
? Knowledge base güncellemesi
? Learning channel ile otomatik öðrenme
? Komutlarla kontrol
?? Kurulum (Render)
1. GitHub'a Yükle
Bu dosyalarý GitHub reposuna yükle.

2. Render'da Oluþtur
https://render.com ? Sign Up/Login
"New +" ? "Background Worker"
GitHub reposunu baðla
Ayarlar:
Name: jaynora-bot
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: python main.py
3. Environment Variables Ekle
Render'da "Environment" sekmesinde:

DISCORD_TOKEN = bot_token_buraya
OPENAI_API_KEY = openai_key_buraya
SUPPORT_ROLE_ID = support_rol_id_buraya
LEARNING_CHANNEL_ID = ai_learn_kanal_id_buraya
COMMANDS_CHANNEL_ID = ai_commands_kanal_id_buraya
ALLOWED_USER_IDS = [user_id_1, user_id_2]
4. Deploy Et
"Create Background Worker" týkla!

?? Komutlar
Komut	Açýklama	Kanal
!ai-restart	Botu yeniden baþlat	ai-commands
!ai-add <bilgi>	Bilgi ekle/güncelle	ai-commands
!ai-dur	O tickette AI'yi durdur	ticket
!ai-go	O tickette AI'yi baþlat	ticket
!ai-test	Test yap	ai-commands
!ailearn <bilgi>	Manuel bilgi ekle	ai-learn
?? ID'leri Nasýl Bulacaksýn?
Discord Developer Mode Aç:
Discord ? User Settings ? Advanced
"Developer Mode" aktif et
ID Bulma:
Role ID: Sunucu ayarlarý ? Roller ? Role sað týk ? Copy ID
Channel ID: Kanal sað týk ? Copy ID
User ID: Kullanýcý sað týk ? Copy ID
?? Teknik Detaylar
Dil: Python 3.11
Discord API: discord.py 2.3.2
AI: OpenAI GPT-4o-mini
Platform: Render Background Worker
?? Destek
Sorun olursa Discord sunucusunda ticket aç!

Made with ?? by SroEdge Team
