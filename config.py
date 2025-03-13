import os
from dotenv import load_dotenv

# Ładowanie zmiennych środowiskowych z pliku .env
load_dotenv()

# Konfiguracja Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Konfiguracja OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEFAULT_MODEL = "gpt-4o"  # Domyślny model OpenAI
DALL_E_MODEL = "dall-e-3"  # Model do generowania obrazów

# Dostępne modele
AVAILABLE_MODELS = {
    "gpt-3.5-turbo": "GPT-3.5 Turbo", 
    "gpt-4": "GPT-4",
    "gpt-4o": "GPT-4o"
}

# Konfiguracja Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Konfiguracja subskrypcji - zmiana na model ilości wiadomości
MESSAGE_PLANS = {
    100: {"name": "Pakiet Podstawowy", "price": 25.00},
    250: {"name": "Pakiet Standard", "price": 50.00},
    500: {"name": "Pakiet Premium", "price": 80.00},
    1000: {"name": "Pakiet Biznes", "price": 130.00}
}

# Stara konfiguracja subskrypcji czasowej (zachowana dla kompatybilności)
SUBSCRIPTION_PLANS = {
    30: {"name": "Plan miesięczny", "price": 30.00},
    60: {"name": "Plan dwumiesięczny", "price": 50.00},
    90: {"name": "Plan kwartalny", "price": 75.00}
}

# Predefiniowane szablony promptów
DEFAULT_SYSTEM_PROMPT = "Jesteś pomocnym asystentem AI."

# Maksymalna długość kontekstu (historia konwersacji)
MAX_CONTEXT_MESSAGES = 20

# Komunikaty
WELCOME_MESSAGE = """Witaj! Jestem botem zasilanym przez ChatGPT. 
Aby rozpocząć korzystanie, aktywuj swoją licencję za pomocą komendy /activate [klucz licencyjny].

Dostępne komendy:
/start - Pokaż tę wiadomość
/activate [klucz] - Aktywuj pakiet wiadomości
/status - Sprawdź stan konta
/newchat - Rozpocznij nową konwersację
/models - Pokaż dostępne modele AI
/templates - Pokaż dostępne szablony promptów
"""

SUBSCRIPTION_EXPIRED_MESSAGE = """Wykorzystałeś limit wiadomości w swoim pakiecie. 
Aby kontynuować korzystanie z bota, aktywuj nowy pakiet wiadomości za pomocą komendy /activate [klucz licencyjny].
"""

LICENSE_ACTIVATED_MESSAGE = """Licencja została pomyślnie aktywowana! 
Twój pakiet zawiera {message_limit} wiadomości.
"""

INVALID_LICENSE_MESSAGE = "Podany klucz licencyjny jest nieprawidłowy lub został już wykorzystany."