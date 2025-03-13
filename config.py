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

# Konfiguracja subskrypcji
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
/activate [klucz] - Aktywuj subskrypcję
/status - Sprawdź status subskrypcji
/newchat - Rozpocznij nową konwersację
/models - Pokaż dostępne modele AI
/templates - Pokaż dostępne szablony promptów
"""

SUBSCRIPTION_EXPIRED_MESSAGE = """Twoja subskrypcja wygasła. 
Aby kontynuować korzystanie z bota, aktywuj nową licencję za pomocą komendy /activate [klucz licencyjny].
"""

LICENSE_ACTIVATED_MESSAGE = """Licencja została pomyślnie aktywowana! 
Twoja subskrypcja jest ważna do: {end_date}.
"""

INVALID_LICENSE_MESSAGE = "Podany klucz licencyjny jest nieprawidłowy lub został już wykorzystany."