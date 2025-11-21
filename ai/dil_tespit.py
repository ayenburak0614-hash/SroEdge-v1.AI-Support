# ai/dil_tespit.py

def detect_language(text: str) -> str:
    text_lower = text.lower().strip()

    turkish_chars = set("çğıöşüÇĞİÖŞÜ")
    if any(char in text for char in turkish_chars):
        print("🇹🇷 Türkçe karakter algılandı")
        return "tr"

    definite_english = [
        "hello", "hi", "hey", "thanks", "thank you",
        "please", "yes", "no", "okay", "ok",
        "what", "how", "why", "when", "where", "who",
        "can you", "could you", "would you",
    ]

    for eng_word in definite_english:
        if eng_word in text_lower:
            print(f"🇬🇧 Kesin İngilizce kelime bulundu: '{eng_word}'")
            return "en"

    turkish_keywords = [
        "merhaba", "selam", "nedir", "nasıl", "neden", "niye", "var", "yok",
        "evet", "hayır", "teşekkür", "teşekkürler", "lütfen", "için", "ile",
        "bu", "şu", "o", "ben", "sen", "biz", "siz", "onlar", "şey", "gibi",
        "ama", "veya", "ve", "ki", "mi", "mu", "mü", "mı", "dir", "dır",
        "nerede", "hangi", "kim", "ne", "kaç", "olan", "olur", "yapılır",
        "acaba", "bana", "sana", "onun", "bizim", "sizin", "tamam",
    ]

    for tr_word in turkish_keywords:
        if tr_word in text_lower:
            print(f"🇹🇷 Türkçe kelime bulundu: '{tr_word}'")
            return "tr"

    english_grammar = [
        " the ", " is ", " are ", " was ", " were ",
        " have ", " has ", " do ", " does ",
        " can ", " could ", " would ", " should ",
    ]

    for eng_grammar in english_grammar:
        if eng_grammar in f" {text_lower} ":
            print("🇬🇧 İngilizce dilbilgisi bulundu")
            return "en"

    print("🇹🇷 Varsayılan: Türkçe")
    return "tr"
