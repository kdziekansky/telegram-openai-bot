from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import CREDIT_PACKAGES, CREDITS_INFO_MESSAGE, BUY_CREDITS_MESSAGE, CREDIT_PURCHASE_SUCCESS, BOT_NAME
from database.credits_client import (
    get_user_credits, add_user_credits, deduct_user_credits, 
    get_credit_packages, get_package_by_id, purchase_credits,
    get_user_credit_stats
)

async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /credits
    Wyświetla informacje o kredytach użytkownika
    """
    user_id = update.effective_user.id
    credits = get_user_credits(user_id)
    
    # Utwórz przyciski do zakupu kredytów
    keyboard = [[InlineKeyboardButton("🛒 Kup kredyty", callback_data="buy_credits")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Wyślij informacje o kredytach
    await update.message.reply_text(
        CREDITS_INFO_MESSAGE.format(
            bot_name=BOT_NAME,
            credits=credits
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /buy
    Pozwala użytkownikowi kupić kredyty
    """
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
        BUY_CREDITS_MESSAGE.format(packages=packages_text),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, package_id):
    """
    Przetwarza zakup pakietu kredytów
    """
    user_id = update.effective_user.id
    
    # Symuluj zakup kredytów (w rzeczywistym scenariuszu tutaj byłaby integracja z systemem płatności)
    success, package = purchase_credits(user_id, package_id)
    
    if success and package:
        current_credits = get_user_credits(user_id)
        await update.message.reply_text(
            CREDIT_PURCHASE_SUCCESS.format(
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
            BUY_CREDITS_MESSAGE.format(packages=packages_text),
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
                CREDIT_PURCHASE_SUCCESS.format(
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