from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import CHAT_MODES

async def show_modes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pokazuje dostępne tryby czatu"""
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

async def handle_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa wyboru trybu czatu"""
    query = update.callback_query
    await query.answer()  # Odpowiedz na callback_query, aby usunąć "zegar oczekiwania"
    
    # Sprawdź, czy callback zaczyna się od "mode_"
    if query.data.startswith("mode_"):
        mode_id = query.data[5:]  # Pobierz ID trybu (usuń prefix "mode_")
        user_id = query.from_user.id
        
        # Sprawdź, czy tryb istnieje
        if mode_id not in CHAT_MODES:
            await query.edit_message_text("Wybrany tryb nie jest dostępny.")
            return
        
        # Zapisz wybrany tryb w kontekście użytkownika
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['current_mode'] = mode_id
        
        mode_name = CHAT_MODES[mode_id]["name"]
        mode_description = CHAT_MODES[mode_id]["prompt"]
        
        # Skróć opis, jeśli jest zbyt długi
        if len(mode_description) > 100:
            short_description = mode_description[:97] + "..."
        else:
            short_description = mode_description
        
        await query.edit_message_text(
            f"Wybrany tryb: *{mode_name}*\n\n"
            f"Opis: _{short_description}_\n\n"
            f"Możesz teraz zadać pytanie w wybranym trybie.",
            parse_mode=ParseMode.MARKDOWN
        )