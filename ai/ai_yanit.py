# ai/ai_yanit.py

import openai
from ai.bilgi_kaynagi import load_knowledge_base


async def get_ai_response(user_message: str, language: str, SUPPORT_ROLE_ID: int, stats: dict) -> str:
    """
    Kullanıcıdan gelen mesajı işler, diline göre uygun yanıtı üretir,
    knowledge base'i kullanarak OpenAI'den cevap alır.
    """

    kb = load_knowledge_base()

    if not kb:
        return "⚠️ Bilgi havuzu yüklenemedi. Lütfen yöneticinize haber verin."

    system_prompt = f"""
Sen Jaynora Discord Ticket AI Support botusun.

Kurallar:
- Türkçe sorulara Türkçe cevap ver.
- İngilizce sorulara İngilizce cevap ver.
- Eğer mesajda sistem abuse, exploit, banlık durum varsa SUPPORT_ROLE_ID göre çağır.
- Bilmediğin veya KB'de bulunmayan bilgileri uydurma, 'Bu konuda net bir bilgiye ulaşamadım' gibi cevaplar kullan.

Knowledge Base:
----------------
{kb}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        answer = response.choices[0].message["content"]

        # Stats güncelleme
        stats["total_questions"] += 1
        if language == "tr":
            stats["turkish_questions"] += 1
        else:
            stats["english_questions"] += 1

        return answer

    except Exception as e:
        print(f"❌ AI yanıt motoru hata: {e}")
        return "⚠️ Yanıt üretirken bir hata oluştu. Lütfen tekrar deneyin."
