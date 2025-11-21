# utils/metin_temizlik.py

def clean_text(text: str) -> str:
    """
    Metindeki gereksiz boşlukları, özel karakterleri temizler.
    AI'nin daha doğru çalışmasını sağlar.
    """
    text = text.strip()
    while "  " in text:
        text = text.replace("  ", " ")

    return text
