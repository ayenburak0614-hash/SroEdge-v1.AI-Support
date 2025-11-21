# ogrenme/ogrenme_yeni_bilgi.py

from ai.bilgi_kaynagi import append_to_knowledge_base
from ai.bilgi_formatlama import format_new_knowledge
from ai.ai_kayit import log_learned_info


async def learn_new_information(bot, AI_LOGS_CHANNEL_ID: int, raw_text: str, user_question: str | None = None):
    """
    AI'nin öğrenme sürecini yönetir.
    - Gelen bilgiyi formatlar
    - Knowledge base'e yazar
    - ai-logs kanalına gönderir
    """

    # Bilgiyi formatla
    formatted = format_new_knowledge(raw_text, user_question)

    # KB’ye yaz
    append_to_knowledge_base(formatted)

    # Log kanalına gönder
    await log_learned_info(
        bot=bot,
        AI_LOGS_CHANNEL_ID=AI_LOGS_CHANNEL_ID,
        source="MANUEL / YÖNETİCİ KOMUTU",
        formatted_block=formatted
    )

    return formatted
