# ai/bilgi_formatlama.py

from datetime import datetime
import openai


def format_new_knowledge(new_info: str, user_question: str | None = None) -> str:
    """
    AI'nin öğrendiği bilgiyi Jaynora formatına uygun hale getirir.
    Knowledge base'e eklenmeden önce tüm güncellemeler bu fonksiyondan geçer.
    """

    base_instruction = """Sen Jaynora AI Support için knowledge base formatlayıcısısın.

Görevin:
- Verilen bilgiyi mevcut Jaynora knowledge_base yapısına uygun şekilde formatlamak.
- Mümkünse uygun bir CATEGORY seç (örnek: [SYSTEM_LIMITS], [EVENT_LOGIN], [UNIQUE_MEDUSA] vb.)
- Uygun kategori yoksa yeni ve mantıklı bir CATEGORY oluştur (örnek: [UPDATE_GENERIC]).

FORMAT ÖRNEĞİ:
===============================================================
[CATEGORY_NAME]
Başlık Açıklaması
===============================================================
- Madde 1
- Madde 2
- Madde 3

Sadece bu formatta cevap ver. Açıklama ekleme.
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

        # Bir hata olursa fallback format
        fallback = f"""
===============================================================
[UPDATE_{datetime.now().strftime("%Y%m%d_%H%M%S")}]
Otomatik Formatlama Hatası
===============================================================
- {new_info}
"""
        return fallback.strip()
