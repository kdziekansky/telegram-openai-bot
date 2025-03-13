from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import WELCOME_MESSAGE
from database.supabase_client import get_or_create_user, check_active_subscription

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
    
    # Sprawdzanie czy użytkownik ma aktywną subskrypcję
    has_subscription = check_active_subscription(user.id)
    
    # Przygotowanie wiadomości powitalnej
    welcome_text = WELCOME_MESSAGE
    
    if has_subscription:
        from database.supabase_client import get_subscription_end_date
        end_date = get_subscription_end_date(user.id)
        
        if end_date:
            formatted_date = end_date.strftime('%d.%m.%Y %H:%M')
            welcome_text += f"\n\nTwoja subskrypcja jest aktywna do: *{formatted_date}*"
    else:
        welcome_text += "\n\nNie masz aktywnej subskrypcji. Aby korzystać z bota, aktywuj licencję."
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)