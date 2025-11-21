# ticket/ticket_mesaj_birlestirme.py

import discord

# Her ticket için mesaj listesi saklanır
ticket_messages = {}


def add_message_to_ticket(ticket_id: int, author: discord.Member, content: str):
    """
    Ticket içindeki mesajları hafızada toplar.
    AI'ye gönderilecek birleşik yapıyı oluşturmak için kullanılır.
    """

    if ticket_id not in ticket_messages:
        ticket_messages[ticket_id] = []

    ticket_messages[ticket_id].append({
        "author": author.display_name,
        "content": content
    })


def get_merged_messages(ticket_id: int) -> str:
    """
    AI'ye gönderilecek ticket mesajlarını düzgün bir formatta döndürür.
    """

    if ticket_id not in ticket_messages:
        return "Mesaj bulunamadı."

    merged = ""

    for msg in ticket_messages[ticket_id]:
        merged += f"{msg['author']}: {msg['content']}\n"

    return merged.strip()


def clear_ticket_messages(ticket_id: int):
    """
    Ticket kapandıktan sonra hafıza temizlenir.
    """

    if ticket_id in ticket_messages:
        del ticket_messages[ticket_id]
