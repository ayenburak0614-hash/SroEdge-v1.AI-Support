# utils/id_dogrulama.py

def is_valid_id(value) -> bool:
    """
    Bir ID'nin geçerli bir sayı olup olmadığını kontrol eder.
    """
    try:
        int(value)
        return True
    except:
        return False
