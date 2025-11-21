# ai/bilgi_kaynagi.py

def load_knowledge_base():
    """knowledge_base.txt dosyasını okur ve içerik döndürür."""
    try:
        with open("knowledge_base.txt", "r", encoding="utf-8") as f:
            content = f.read()
            print(f"✅ Knowledge base yüklendi: {len(content)} karakter")
            return content
    except Exception as e:
        print(f"❌ Knowledge base yüklenemedi: {e}")
        return ""


def save_knowledge_base(content: str):
    """knowledge_base.txt dosyasına içerik yazar."""
    try:
        with open("knowledge_base.txt", "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Knowledge base kaydedildi")
    except Exception as e:
        print(f"❌ Knowledge base kaydedilemedi: {e}")


def append_to_knowledge_base(block: str):
    """Yeni formatlanmış bilgi bloğunu knowledge_base.txt'ye ekler."""
    kb = load_knowledge_base()
    updated = (kb.rstrip() + "\n\n" + block.strip() + "\n").lstrip()
    save_knowledge_base(updated)
