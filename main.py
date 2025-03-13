import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe
load_dotenv()

# Konfiguracja loggera
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Inicjalizacja bota
bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# States
class BotStates(StatesGroup):
    Chat = State()
    AwaitingImagePrompt = State()

# Obsługa komendy /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply(
        "Witaj! Jestem botem zasilanym przez ChatGPT. "
        "Aby rozpocząć korzystanie, aktywuj swoją licencję za pomocą komendy /activate [klucz licencyjny].\n\n"
        "Dostępne komendy:\n"
        "/start - Pokaż tę wiadomość\n"
        "/activate [klucz] - Aktywuj subskrypcję\n"
        "/status - Sprawdź status subskrypcji\n"
        "/newchat - Rozpocznij nową konwersację\n"
        "/models - Pokaż dostępne modele AI\n"
        "/templates - Pokaż dostępne szablony promptów"
    )

# Obsługa wiadomości tekstowych
@dp.message_handler(lambda message: True)
async def echo_all(message: types.Message):
    # W pełnej implementacji tutaj byłaby integracja z OpenAI
    await message.reply("Otrzymałem Twoją wiadomość: " + message.text)

# Funkcja do uruchomienia bota
async def main():
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())