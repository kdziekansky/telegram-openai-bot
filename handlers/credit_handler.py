from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import BOT_NAME
from utils.translations import get_text
from database.credits_client import (
    get_user_credits, add_user_credits, deduct_user_credits, 
    get_credit_packages, get_package_by_id, purchase_credits,
    get_user_credit_stats
)

# Funkcja przeniesiona z menu_handler.py żeby uniknąć importu cyklicznego
def get_user_language(context, user_id):
    """
    Pobiera język użytkownika z kontekstu lub bazy danych
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        
    Returns:
        str: Kod języka (pl, en, ru)
    """
    # Sprawdź, czy język jest zapisany w kontekście
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data'] and 'language' in context.chat_data['user_data'][user_id]:
        return context.chat_data['user_data'][user_id]['language']
    
    # Jeśli nie, pobierz z bazy danych
    try:
        from database.sqlite_client import sqlite3, DB_PATH
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT language FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            # Zapisz w kontekście na przyszłość
            if 'user_data' not in context.chat_data:
                context.chat_data['user_data'] = {}
            
            if user_id not in context.chat_data['user_data']:
                context.chat_data['user_data'][user_id] = {}
            
            context.chat_data['user_data'][user_id]['language'] = result[0]
            return result[0]
    except Exception as e:
        print(f"Błąd pobierania języka z bazy: {e}")
    
    # Domyślny język, jeśli nie znaleziono w bazie
    return "pl"

async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /credits
    Wyświetla informacje o kredytach użytkownika
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    credits = get_user_credits(user_id)
    
    # Utwórz przyciski do zakupu kredytów
    keyboard = [[InlineKeyboardButton("🛒 Kup kredyty", callback_data="buy_credits")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Wyślij informacje o kredytach
    await update.message.reply_text(
        get_text("credits_info", language, bot_name=BOT_NAME, credits=credits),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /buy
    Pozwala użytkownikowi kupić kredyty
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy podano numer pakietu
    if context.args and len(context.args) > 0:
        try:
            package_id = int(context.args[0])
            await process_purchase(update, context, package_id)
            return
        except ValueError:
            await update.message.reply_text("Nieprawidłowy numer pakietu. Użyj liczby, np. /buy 2")
            return
    
    # Jeśli nie podano numeru pakietu, pokaż dostępne pakiety
    packages = get_credit_packages()
    
    packages_text = ""
    for pkg in packages:
        packages_text += f"*{pkg['id']}.* {pkg['name']} - *{pkg['credits']}* kredytów - *{pkg['price']} zł*\n"
    
    # Utwórz przyciski do zakupu kredytów
    keyboard = []
    for pkg in packages:
        keyboard.append([
            InlineKeyboardButton(
                f"{pkg['name']} - {pkg['credits']} kredytów ({pkg['price']} zł)", 
                callback_data=f"buy_package_{pkg['id']}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        get_text("buy_credits", language, packages=packages_text),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, package_id):
    """
    Przetwarza zakup pakietu kredytów
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Symuluj zakup kredytów (w rzeczywistym scenariuszu tutaj byłaby integracja z systemem płatności)
    success, package = purchase_credits(user_id, package_id)
    
    if success and package:
        current_credits = get_user_credits(user_id)
        await update.message.reply_text(
            get_text("credit_purchase_success", language,
                package_name=package['name'],
                credits=package['credits'],
                price=package['price'],
                total_credits=current_credits
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "Wystąpił błąd podczas przetwarzania zakupu. Spróbuj ponownie lub wybierz inny pakiet.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_credit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje przyciski związane z kredytami
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    if query.data == "buy_credits":
        # Przekieruj do komendy buy
        packages = get_credit_packages()
        
        packages_text = ""
        for pkg in packages:
            packages_text += f"*{pkg['id']}.* {pkg['name']} - *{pkg['credits']}* kredytów - *{pkg['price']} zł*\n"
        
        # Utwórz przyciski do zakupu kredytów
        keyboard = []
        for pkg in packages:
            keyboard.append([
                InlineKeyboardButton(
                    f"{pkg['name']} - {pkg['credits']} kredytów ({pkg['price']} zł)", 
                    callback_data=f"buy_package_{pkg['id']}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            get_text("buy_credits", language, packages=packages_text),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("buy_package_"):
        # Obsługa zakupu konkretnego pakietu
        package_id = int(query.data.split("_")[2])
        
        user_id = query.from_user.id
        
        # Symuluj zakup kredytów
        success, package = purchase_credits(user_id, package_id)
        
        if success and package:
            current_credits = get_user_credits(user_id)
            await query.edit_message_text(
                get_text("credit_purchase_success", language,
                    package_name=package['name'],
                    credits=package['credits'],
                    price=package['price'],
                    total_credits=current_credits
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                "Wystąpił błąd podczas przetwarzania zakupu. Spróbuj ponownie lub wybierz inny pakiet.",
                parse_mode=ParseMode.MARKDOWN
            )

async def credit_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /creditstats
    Wyświetla szczegółowe statystyki kredytów użytkownika
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    stats = get_user_credit_stats(user_id)
    
    # Formatuj datę ostatniego zakupu
    last_purchase = "Brak" if not stats['last_purchase'] else stats['last_purchase'].split('T')[0]
    
    # Utwórz wiadomość z statystykami
    message = f"""
*📊 Statystyki kredytów*

Aktualne saldo: *{stats['credits']}* kredytów
Łącznie zakupiono: *{stats['total_purchased']}* kredytów
Łącznie wydano: *{stats['total_spent']}* zł
Ostatni zakup: *{last_purchase}*

*📝 Historia użycia (ostatnie 10 transakcji):*
"""
    
    if not stats['usage_history']:
        message += "\nBrak historii transakcji."
    else:
        for i, transaction in enumerate(stats['usage_history']):
            date = transaction['date'].split('T')[0]
            if transaction['type'] == "add" or transaction['type'] == "purchase":
                message += f"\n{i+1}. ➕ +{transaction['amount']} kredytów ({date})"
                if transaction['description']:
                    message += f" - {transaction['description']}"
            else:
                message += f"\n{i+1}. ➖ -{transaction['amount']} kredytów ({date})"
                if transaction['description']:
                    message += f" - {transaction['description']}"
    
    # Dodaj przycisk do zakupu kredytów
    keyboard = [[InlineKeyboardButton("🛒 Kup kredyty", callback_data="buy_credits")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )