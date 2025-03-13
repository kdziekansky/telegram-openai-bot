from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import DEFAULT_MODEL, SUBSCRIPTION_EXPIRED_MESSAGE, MAX_CONTEXT_MESSAGES, AVAILABLE_MODELS
from database.supabase_client import (
    check_active_subscription, get_active_conversation, 
    save_message, get_conversation_history
)
from utils.openai_client import chat_completion, prepare_messages_from_history

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa wiadomości tekstowych od użytkownika"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Sprawdź, czy użytkownik ma aktywną subskrypcję
    if not check_active_subscription(user_id):
        await update.message.reply_text(SUBSCRIPTION_EXPIRED_MESSAGE)
        return
    
    # Pobierz lub utwórz aktywną konwersację
    conversation = get_active_conversation(user_id)
    conversation_id = conversation['id']
    
    # Zapisz wiadomość użytkownika do bazy danych
    save_message(conversation_id, user_id, user_message, is_from_user=True)
    
    # Wyślij informację, że bot pisze
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
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
    
    # Wyślij odpowiedź do użytkownika
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

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
    
    context.chat_data['user_data'][user_id] = {
        'current_model': model_id
    }
    
    model_name = AVAILABLE_MODELS[model_id]
    await query.edit_message_text(f"Wybrany model: *{model_name}*\n\nMożesz teraz zadać pytanie.", parse_mode=ParseMode.MARKDOWN)