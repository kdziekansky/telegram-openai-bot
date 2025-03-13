import logging
import os
import re
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode, ChatAction
from config import (
    TELEGRAM_TOKEN, DEFAULT_MODEL, SUBSCRIPTION_EXPIRED_MESSAGE, 
    MAX_CONTEXT_MESSAGES, AVAILABLE_MODELS, WELCOME_MESSAGE, 
    LICENSE_ACTIVATED_MESSAGE, INVALID_LICENSE_MESSAGE,
    MESSAGE_PLANS
)

# Import funkcji z modułu sqlite_client
from database.sqlite_client import (
    get_or_create_user, check_active_subscription, 
    get_subscription_end_date, activate_user_license,
    create_new_conversation, get_active_conversation,
    save_message, get_conversation_history,
    get_prompt_templates, get_prompt_template_by_id,
    save_prompt_template, create_license,
    check_message_limit, increment_messages_used,
    get_message_status
)

from utils.openai_client import (
    chat_completion, prepare_messages_from_history,
    generate_image_dall_e, analyze_document, analyze_image
)
from prompts.templates import initialize_templates_in_database

# Konfiguracja loggera
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Lista ID administratorów bota - tutaj należy dodać swoje ID
ADMIN_USER_IDS = [1743680448, 787188598]  # Lista dwóch administratorów

# Handlers dla podstawowych komend

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /start
    Tworzy lub pobiera użytkownika z bazy danych i wyświetla wiadomość powitalną
    """
    user = update.effective_user
    
    # Zapis użytkownika do bazy danych
    get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code
    )
    
    # Sprawdzanie statusu użytkownika
    message_status = get_message_status(user.id)
    has_subscription = check_active_subscription(user.id)
    
    # Przygotowanie wiadomości powitalnej
    welcome_text = WELCOME_MESSAGE
    
    if has_subscription:
        # Sprawdź subskrypcję czasową
        end_date = get_subscription_end_date(user.id)
        if end_date and end_date > datetime.datetime.now(pytz.UTC):
            formatted_date = end_date.strftime('%d.%m.%Y %H:%M')
            welcome_text += f"\n\nTwoja subskrypcja jest aktywna do: *{formatted_date}*"
        
        # Dodaj informację o dostępnych wiadomościach
        if message_status["messages_limit"] > 0:
            welcome_text += f"\n\nDostępne wiadomości: *{message_status['messages_left']}* z *{message_status['messages_limit']}*"
    else:
        welcome_text += "\n\nNie masz aktywnej subskrypcji ani dostępnych wiadomości. Aby korzystać z bota, aktywuj licencję."
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def activate_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Aktywuje licencję dla użytkownika
    Użycie: /activate [klucz_licencyjny]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy podano klucz licencyjny
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Użycie: /activate [klucz_licencyjny]")
        return
    
    license_key = context.args[0]
    
    # Aktywuj licencję
    success, end_date, message_limit = activate_user_license(user_id, license_key)
    
    if success:
        message_info = f"Licencja została pomyślnie aktywowana!\nTwój pakiet zawiera *{message_limit}* wiadomości."
        
        # Dodaj informację o dacie końca subskrypcji, jeśli istnieje
        if end_date:
            formatted_date = end_date.strftime('%d.%m.%Y %H:%M')
            message_info += f"\nTwoja subskrypcja jest ważna do: *{formatted_date}*"
        
        await update.message.reply_text(message_info, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(INVALID_LICENSE_MESSAGE)

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sprawdza status konta użytkownika
    Użycie: /status
    """
    user_id = update.effective_user.id
    
    # Pobierz status wiadomości
    message_status = get_message_status(user_id)
    
    # Pobierz datę końca subskrypcji (jeśli istnieje)
    end_date = get_subscription_end_date(user_id)
    subscription_info = ""
    
    if end_date and end_date > datetime.datetime.now(pytz.UTC):
        formatted_date = end_date.strftime('%d.%m.%Y %H:%M')
        subscription_info = f"\nTwoja subskrypcja czasowa jest aktywna do: *{formatted_date}*"
    
    # Stwórz wiadomość o statusie
    message = f"""
*Status twojego konta:*

Dostępne wiadomości: *{message_status['messages_left']}* z *{message_status['messages_limit']}*
Wykorzystane wiadomości: *{message_status['messages_used']}*
{subscription_info}

Aby dokupić więcej wiadomości, użyj komendy /activate z nowym kluczem licencyjnym.
"""
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rozpoczyna nową konwersację"""
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik ma aktywną subskrypcję
    if not check_active_subscription(user_id):
        await update.message.reply_text(SUBSCRIPTION_EXPIRED_MESSAGE)
        return
    
    # Utwórz nową konwersację
    conversation = create_new_conversation(user_id)
    
    if conversation:
        await update.message.reply_text("Rozpoczęto nową konwersację. Możesz teraz zadać pytanie.")
    else:
        await update.message.reply_text("Wystąpił błąd podczas tworzenia nowej konwersacji.")

async def show_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pokazuje dostępne modele AI"""
    # Utwórz przyciski dla dostępnych modeli
    keyboard = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        keyboard.append([InlineKeyboardButton(text=model_name, callback_data=f"model_{model_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Wybierz model AI, którego chcesz używać:",
        reply_markup=reply_markup
    )

async def show_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pokazuje dostępne szablony promptów"""
    templates = get_prompt_templates()
    
    if not templates:
        await update.message.reply_text("Brak dostępnych szablonów promptów.")
        return
    
    # Utwórz przyciski dla dostępnych szablonów
    keyboard = []
    for template in templates:
        keyboard.append([
            InlineKeyboardButton(
                text=template["name"], 
                callback_data=f"template_{template['id']}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Wybierz szablon prompta, którego chcesz używać:",
        reply_markup=reply_markup
    )

# Handlers dla obsługi wiadomości

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa wiadomości tekstowych od użytkownika"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Sprawdź, czy użytkownik ma dostępne wiadomości
    if not check_message_limit(user_id):
        await update.message.reply_text(SUBSCRIPTION_EXPIRED_MESSAGE)
        return
    
    # Pobierz lub utwórz aktywną konwersację
    conversation = get_active_conversation(user_id)
    conversation_id = conversation['id']
    
    # Zapisz wiadomość użytkownika do bazy danych
    save_message(conversation_id, user_id, user_message, is_from_user=True)
    
    # Wyślij informację, że bot pisze
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Pobierz historię konwersacji
    history = get_conversation_history(conversation_id, limit=MAX_CONTEXT_MESSAGES)
    
    # Określ model do użycia - domyślny lub wybrany przez użytkownika
    model_to_use = DEFAULT_MODEL
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_model' in user_data:
            model_to_use = user_data['current_model']
    
    # Przygotuj system prompt - domyślny lub z szablonu
    system_prompt = None
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_template' in user_data:
            system_prompt = user_data['current_template']
    
    # Przygotuj wiadomości dla API OpenAI
    messages = prepare_messages_from_history(history, user_message, system_prompt)
    
    # Wygeneruj odpowiedź
    response = chat_completion(messages, model=model_to_use)
    
    # Zapisz odpowiedź do bazy danych
    save_message(conversation_id, user_id, response, is_from_user=False, model_used=model_to_use)
    
    # Zwiększ licznik wykorzystanych wiadomości
    increment_messages_used(user_id)
    
    # Wyślij odpowiedź do użytkownika
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    # Sprawdź, ile pozostało wiadomości
    message_status = get_message_status(user_id)
    if message_status["messages_left"] <= 5 and message_status["messages_left"] > 0:
        await update.message.reply_text(
            f"*Uwaga:* Pozostało Ci tylko *{message_status['messages_left']}* wiadomości. "
            f"Aktywuj nowy pakiet, aby kontynuować korzystanie z bota.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa przesłanych dokumentów"""
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik ma dostępne wiadomości
    if not check_message_limit(user_id):
        await update.message.reply_text(SUBSCRIPTION_EXPIRED_MESSAGE)
        return
    
    document = update.message.document
    file_name = document.file_name
    
    # Sprawdź rozmiar pliku (limit 25MB)
    if document.file_size > 25 * 1024 * 1024:
        await update.message.reply_text("Plik jest zbyt duży. Maksymalny rozmiar to 25MB.")
        return
    
    # Pobierz plik
    message = await update.message.reply_text("Analizuję plik, proszę czekać...")
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    file = await context.bot.get_file(document.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Analizuj plik
    analysis = analyze_document(file_bytes, file_name)
    
    # Zwiększ licznik wykorzystanych wiadomości
    increment_messages_used(user_id)
    
    # Wyślij analizę do użytkownika
    await message.edit_text(
        f"*Analiza pliku:* {file_name}\n\n{analysis}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Sprawdź, ile pozostało wiadomości
    message_status = get_message_status(user_id)
    if message_status["messages_left"] <= 5 and message_status["messages_left"] > 0:
        await update.message.reply_text(
            f"*Uwaga:* Pozostało Ci tylko *{message_status['messages_left']}* wiadomości. "
            f"Aktywuj nowy pakiet, aby kontynuować korzystanie z bota.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa przesłanych zdjęć"""
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik ma dostępne wiadomości
    if not check_message_limit(user_id):
        await update.message.reply_text(SUBSCRIPTION_EXPIRED_MESSAGE)
        return
    
    # Wybierz zdjęcie o najwyższej rozdzielczości
    photo = update.message.photo[-1]
    
    # Pobierz zdjęcie
    message = await update.message.reply_text("Analizuję zdjęcie, proszę czekać...")
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Analizuj zdjęcie
    analysis = analyze_image(file_bytes, f"photo_{photo.file_unique_id}.jpg")
    
    # Zwiększ licznik wykorzystanych wiadomości
    increment_messages_used(user_id)
    
    # Wyślij analizę do użytkownika
    await message.edit_text(
        f"*Analiza zdjęcia:*\n\n{analysis}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Sprawdź, ile pozostało wiadomości
    message_status = get_message_status(user_id)
    if message_status["messages_left"] <= 5 and message_status["messages_left"] > 0:
        await update.message.reply_text(
            f"*Uwaga:* Pozostało Ci tylko *{message_status['messages_left']}* wiadomości. "
            f"Aktywuj nowy pakiet, aby kontynuować korzystanie z bota.",
            parse_mode=ParseMode.MARKDOWN
        )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generuje obraz za pomocą DALL-E na podstawie opisu
    Użycie: /image [opis obrazu]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik ma dostępne wiadomości
    if not check_message_limit(user_id):
        await update.message.reply_text(SUBSCRIPTION_EXPIRED_MESSAGE)
        return
    
    # Sprawdź, czy podano opis obrazu
    if not context.args or len(' '.join(context.args)) < 3:
        await update.message.reply_text("Użycie: /image [opis obrazu]\nNa przykład: /image pies na rowerze w parku")
        return
    
    prompt = ' '.join(context.args)
    
    # Powiadom użytkownika o rozpoczęciu generowania
    message = await update.message.reply_text("Generuję obraz, proszę czekać...")
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.UPLOAD_PHOTO)
    
    # Generuj obraz
    image_url = generate_image_dall_e(prompt)
    
    # Zwiększ licznik wykorzystanych wiadomości (generowanie obrazu również liczy się jako wiadomość)
    increment_messages_used(user_id)
    
    if image_url:
        # Usuń wiadomość o ładowaniu
        await message.delete()
        
        # Wyślij obraz
        await update.message.reply_photo(
            photo=image_url,
            caption=f"*Wygenerowany obraz:*\n{prompt}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Aktualizuj wiadomość o błędzie
        await message.edit_text("Przepraszam, wystąpił błąd podczas generowania obrazu. Spróbuj ponownie z innym opisem.")
    
    # Sprawdź, ile pozostało wiadomości
    message_status = get_message_status(user_id)
    if message_status["messages_left"] <= 5 and message_status["messages_left"] > 0:
        await update.message.reply_text(
            f"*Uwaga:* Pozostało Ci tylko *{message_status['messages_left']}* wiadomości. "
            f"Aktywuj nowy pakiet, aby kontynuować korzystanie z bota.",
            parse_mode=ParseMode.MARKDOWN
        )

# Handlers dla przycisków i callbacków

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa zapytań zwrotnych (z przycisków)"""
    query = update.callback_query
    await query.answer()  # Odpowiedz na callback_query, aby usunąć "zegar oczekiwania"
    
    # Obsługa wybrania modelu
    if query.data.startswith("model_"):
        model_id = query.data[6:]  # Pobierz ID modelu (usuń prefix "model_")
        await handle_model_selection(update, context, model_id)
    
    # Obsługa wybrania szablonu prompta
    elif query.data.startswith("template_"):
        template_id = int(query.data[9:])  # Pobierz ID szablonu (usuń prefix "template_")
        await handle_template_selection(update, context, template_id)

async def handle_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, model_id):
    """Obsługa wyboru modelu AI"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Sprawdź, czy model istnieje
    if model_id not in AVAILABLE_MODELS:
        await query.edit_message_text("Wybrany model nie jest dostępny.")
        return
    
    # Zapisz wybrany model w kontekście użytkownika
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    context.chat_data['user_data'][user_id]['current_model'] = model_id
    
    model_name = AVAILABLE_MODELS[model_id]
    await query.edit_message_text(f"Wybrany model: *{model_name}*\n\nMożesz teraz zadać pytanie.", parse_mode=ParseMode.MARKDOWN)

async def handle_template_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, template_id):
    """Obsługa wyboru szablonu prompta"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Pobierz szablon prompta
    template = get_prompt_template_by_id(template_id)
    
    if not template:
        await query.edit_message_text("Wybrany szablon nie jest dostępny.")
        return
    
    # Zapisz wybrany szablon w kontekście użytkownika
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    context.chat_data['user_data'][user_id]['current_template'] = template["prompt_text"]
    
    await query.edit_message_text(
        f"Wybrany szablon prompta: *{template['name']}*\n\n{template['description']}\n\nMożesz teraz zadać pytanie.", 
        parse_mode=ParseMode.MARKDOWN
    )

# Handlers dla komend administracyjnych

async def add_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Dodaje nową licencję do bazy danych
    Tylko dla administratorów
    Użycie: /addlicense [liczba_wiadomości] [ilość]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik jest administratorem
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("Nie masz uprawnień do tej komendy.")
        return
    
    # Sprawdź, czy podano argumenty
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Użycie: /addlicense [liczba_wiadomości] [ilość]")
        return
    
    try:
        message_limit = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Błędne argumenty. Użycie: /addlicense [liczba_wiadomości] [ilość]")
        return
    
    # Sprawdź, czy liczba wiadomości jest poprawna
    if message_limit not in MESSAGE_PLANS:
        valid_limits = ", ".join(str(d) for d in MESSAGE_PLANS.keys())
        await update.message.reply_text(f"Nieprawidłowa liczba wiadomości. Dostępne opcje: {valid_limits}")
        return
    
    # Sprawdź, czy ilość jest poprawna
    if amount <= 0 or amount > 100:
        await update.message.reply_text("Ilość musi być liczbą dodatnią, nie większą niż 100.")
        return
    
    # Generuj licencje
    price = MESSAGE_PLANS[message_limit]["price"]
    licenses = []
    
    for _ in range(amount):
        license = create_license(message_limit, price)
        if license:
            licenses.append(license["license_key"])
    
    # Wyślij wygenerowane licencje
    if licenses:
        licenses_str = "\n".join(licenses)
        await update.message.reply_text(
            f"Wygenerowano {len(licenses)} licencji na {message_limit} wiadomości:\n\n{licenses_str}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("Wystąpił błąd podczas generowania licencji.")

async def get_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Pobiera informacje o użytkowniku
    Tylko dla administratorów
    Użycie: /userinfo [user_id]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik jest administratorem
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("Nie masz uprawnień do tej komendy.")
        return
    
    # Sprawdź, czy podano ID użytkownika
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Użycie: /userinfo [user_id]")
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID użytkownika musi być liczbą.")
        return
    
    # Pobierz informacje o użytkowniku z SQLite
    user = get_or_create_user(target_user_id)
    
    if not user:
        await update.message.reply_text("Użytkownik nie istnieje w bazie danych.")
        return
    
    # Pobierz status wiadomości
    message_status = get_message_status(target_user_id)
    
    # Formatuj dane
    subscription_end = user.get('subscription_end_date', 'Brak subskrypcji')
    if subscription_end and subscription_end != 'Brak subskrypcji':
        end_date = datetime.datetime.fromisoformat(subscription_end.replace('Z', '+00:00'))
        subscription_end = end_date.strftime('%d.%m.%Y %H:%M')
    
    info = f"""
*Informacje o użytkowniku:*
ID: `{user['id']}`
Nazwa użytkownika: {user.get('username', 'Brak')}
Imię: {user.get('first_name', 'Brak')}
Nazwisko: {user.get('last_name', 'Brak')}
Język: {user.get('language_code', 'Brak')}
Subskrypcja do: {subscription_end}
Aktywny: {'Tak' if user.get('is_active', False) else 'Nie'}
Data rejestracji: {user.get('created_at', 'Brak')}

*Status wiadomości:*
Limit wiadomości: {message_status['messages_limit']}
Wykorzystane wiadomości: {message_status['messages_used']}
Pozostałe wiadomości: {message_status['messages_left']}
    """
    
    await update.message.reply_text(info, parse_mode=ParseMode.MARKDOWN)

async def add_prompt_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Dodaje nowy szablon prompta do bazy danych
    Tylko dla administratorów
    Użycie: /addtemplate [nazwa] [opis] [tekst prompta]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik jest administratorem
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("Nie masz uprawnień do tej komendy.")
        return
    
    # Sprawdź, czy wiadomość jest odpowiedzią na inną wiadomość
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Ta komenda musi być odpowiedzią na wiadomość zawierającą prompt.\n"
            "Format: /addtemplate [nazwa] [opis]\n"
            "Przykład: /addtemplate \"Asystent kreatywny\" \"Pomaga w kreatywnym myśleniu\""
        )
        return
    
    # Sprawdź, czy podano argumenty
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Użycie: /addtemplate [nazwa] [opis]\n"
            "Przykład: /addtemplate \"Asystent kreatywny\" \"Pomaga w kreatywnym myśleniu\""
        )
        return
    
    # Pobierz tekst prompta z odpowiedzi
    prompt_text = update.message.reply_to_message.text
    
    # Pobierz nazwę i opis
    # Obsługa nazwy i opisu w cudzysłowach
    text = update.message.text[len('/addtemplate '):]
    matches = re.findall(r'"([^"]*)"', text)
    
    if len(matches) < 2:
        await update.message.reply_text(
            "Nieprawidłowy format. Nazwa i opis muszą być w cudzysłowach.\n"
            "Przykład: /addtemplate \"Asystent kreatywny\" \"Pomaga w kreatywnym myśleniu\""
        )
        return
    
    name = matches[0]
    description = matches[1]
    
    # Dodaj szablon do bazy danych
    template = save_prompt_template(name, description, prompt_text)
    
    if template:
        await update.message.reply_text(
            f"Dodano nowy szablon prompta:\n"
            f"*Nazwa:* {name}\n"
            f"*Opis:* {description}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("Wystąpił błąd podczas dodawania szablonu prompta.")

# Główna funkcja uruchamiająca bota

def main():
    """Funkcja uruchamiająca bota"""
    # Inicjalizacja szablonów promptów
    templates_added = initialize_templates_in_database()
    logger.info(f"Dodano {templates_added} nowych szablonów promptów")
    
    # Inicjalizacja aplikacji
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Dodanie handlerów komend
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("activate", activate_license))
    application.add_handler(CommandHandler("status", check_subscription))
    application.add_handler(CommandHandler("newchat", new_chat))
    application.add_handler(CommandHandler("models", show_models))
    application.add_handler(CommandHandler("templates", show_templates))
    application.add_handler(CommandHandler("image", generate_image))
    
    # Dodanie handlerów komend administracyjnych
    application.add_handler(CommandHandler("addlicense", add_license))
    application.add_handler(CommandHandler("userinfo", get_user_info))
    application.add_handler(CommandHandler("addtemplate", add_prompt_template))
    
    # Dodanie handlerów dokumentów i zdjęć
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Dodanie handlera zapytań zwrotnych (z przycisków)
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Dodanie handlera wiadomości tekstowych (musi być na końcu)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Uruchomienie bota
    application.run_polling()

if __name__ == '__main__':
    main()