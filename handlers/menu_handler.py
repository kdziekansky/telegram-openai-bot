from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import CHAT_MODES

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla główne menu bota z przyciskami
    """
    # Przygotuj klawiaturę z przyciskami menu
    keyboard = [
        [KeyboardButton("🔄 Select Chat Mode")],
        [KeyboardButton("📂 Dialog History")],
        [KeyboardButton("👥 Get Free Tokens")],
        [KeyboardButton("💰 Balance (Subscription)"), KeyboardButton("⚙️ Settings")],
        [KeyboardButton("❓ Help")]
    ]
    
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    await update.message.reply_text(
        "📋 *Menu główne*\n\nWybierz opcję z listy lub wprowadź wiadomość, aby porozmawiać z botem.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje wybór opcji z menu
    """
    message_text = update.message.text
    
    if message_text == "🔄 Select Chat Mode":
        await show_chat_modes(update, context)
    elif message_text == "📂 Dialog History":
        await show_dialog_history(update, context)
    elif message_text == "👥 Get Free Tokens":
        await show_get_tokens(update, context)
    elif message_text == "💰 Balance (Subscription)":
        await show_balance(update, context)
    elif message_text == "⚙️ Settings":
        await show_settings(update, context)
    elif message_text == "❓ Help":
        await show_help(update, context)
    else:
        # Przekazujemy obsługę wiadomości do głównego handlera wiadomości
        return False
    
    return True

async def show_chat_modes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla dostępne tryby czatu jako przyciski
    """
    # Sprawdzenie, czy użytkownik ma uprawnienia
    from database.sqlite_client import check_active_subscription
    user_id = update.effective_user.id
    
    if not check_active_subscription(user_id):
        from config import SUBSCRIPTION_EXPIRED_MESSAGE
        await update.message.reply_text(SUBSCRIPTION_EXPIRED_MESSAGE)
        return
    
    # Utwórz przyciski dla dostępnych trybów
    keyboard = []
    for mode_id, mode_info in CHAT_MODES.items():
        keyboard.append([
            InlineKeyboardButton(text=mode_info["name"], callback_data=f"mode_{mode_id}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Wybierz tryb czatu, którego chcesz używać:",
        reply_markup=reply_markup
    )

async def show_dialog_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla historię dialogu lub opcje jej zarządzania
    """
    keyboard = [
        [InlineKeyboardButton("📃 Pokaż ostatnią konwersację", callback_data="history_show_last")],
        [InlineKeyboardButton("🗑️ Usuń historię", callback_data="history_delete")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "*Historia dialogów*\n\nWybierz opcję:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_get_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla informacje o tym, jak zdobyć darmowe tokeny/wiadomości
    """
    await update.message.reply_text(
        "*Zdobądź darmowe tokeny*\n\n"
        "Możesz otrzymać dodatkowe tokeny/wiadomości przez:\n\n"
        "1️⃣ Polecenie bota znajomym (5 tokenów za każdą zaproszoną osobę)\n"
        "2️⃣ Udostępnienie opinii o bocie w mediach społecznościowych (10 tokenów)\n"
        "3️⃣ Subskrypcję naszego kanału z aktualizacjami: @twoj_kanal_z_aktualizacjami\n\n"
        "Aby odebrać tokeny, skontaktuj się z administracją: @twoj_kontakt_admina",
        parse_mode=ParseMode.MARKDOWN
    )

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla informacje o stanie konta i subskrypcji
    """
    # Przekieruj do funkcji sprawdzania statusu subskrypcji
    from main import check_subscription
    await check_subscription(update, context)

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla ustawienia bota
    """
    keyboard = [
        [InlineKeyboardButton("🤖 Model AI", callback_data="settings_model")],
        [InlineKeyboardButton("🌐 Język", callback_data="settings_language")],
        [InlineKeyboardButton("👤 Twoja nazwa", callback_data="settings_name")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "*Ustawienia*\n\nWybierz co chcesz zmienić:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla pomoc i informacje o bocie
    """
    help_text = """
*Pomoc i informacje*

*Dostępne komendy:*
/start - Rozpocznij korzystanie z bota
/activate [klucz] - Aktywuj pakiet wiadomości
/status - Sprawdź stan konta
/newchat - Rozpocznij nową konwersację
/mode - Wybierz tryb czatu
/image [opis] - Wygeneruj obraz
/restart - Odśwież informacje o bocie
/menu - Pokaż to menu

*Używanie bota:*
1. Po prostu wpisz wiadomość, aby otrzymać odpowiedź
2. Użyj przycisków menu, aby uzyskać dostęp do funkcji
3. Możesz przesyłać zdjęcia i dokumenty do analizy

*Wsparcie:*
Jeśli potrzebujesz pomocy, skontaktuj się z nami: @twoj_kontakt_wsparcia
"""
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

# Handler dodatkowych przycisków (ustawienia, historia itp.)
async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje callbacki związane z ustawieniami
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "settings_model":
        from main import show_models
        await show_models(update, context)
    elif query.data == "settings_language":
        # Przykładowa implementacja wyboru języka
        keyboard = [
            [InlineKeyboardButton("🇵🇱 Polski", callback_data="lang_pl")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "*Wybór języka*\n\nWybierz język interfejsu:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data.startswith("lang_"):
        language = query.data[5:]  # Pobierz kod języka (usuń prefix "lang_")
        
        user_id = query.from_user.id
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['language'] = language
        
        language_name = "Polski" if language == "pl" else "English"
        await query.edit_message_text(
            f"Język został zmieniony na: *{language_name}*",
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data == "settings_name":
        await query.edit_message_text(
            "*Zmiana nazwy*\n\nWpisz komendę /setname [twoja_nazwa] aby zmienić swoją nazwę w bocie.",
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data.startswith("history_"):
        action = query.data[8:]  # Pobierz akcję (usuń prefix "history_")
        
        if action == "show_last":
            # Tutaj można zaimplementować pokazywanie ostatniej konwersacji
            await query.edit_message_text(
                "*Ostatnia konwersacja*\n\nTutaj będzie wyświetlona ostatnia konwersacja.",
                parse_mode=ParseMode.MARKDOWN
            )
        elif action == "delete":
            # Tutaj można zaimplementować usuwanie historii
            user_id = query.from_user.id
            # Twórz nową konwersację (efektywnie "usuwając" historię)
            from database.sqlite_client import create_new_conversation
            conversation = create_new_conversation(user_id)
            
            if conversation:
                await query.edit_message_text(
                    "*Historia została wyczyszczona*\n\nRozpocznęto nową konwersację.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    "Wystąpił błąd podczas czyszczenia historii.",
                    parse_mode=ParseMode.MARKDOWN
                )

async def set_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ustawia niestandardową nazwę użytkownika
    Użycie: /setname [nazwa]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy podano nazwę
    if not context.args or len(' '.join(context.args)) < 1:
        await update.message.reply_text("Użycie: /setname [nazwa]\nNa przykład: /setname Jan Kowalski")
        return
    
    name = ' '.join(context.args)
    
    # Zapisz nazwę w kontekście użytkownika
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    context.chat_data['user_data'][user_id]['custom_name'] = name
    
    await update.message.reply_text(
        f"Twoja nazwa została zmieniona na: *{name}*",
        parse_mode=ParseMode.MARKDOWN
    )