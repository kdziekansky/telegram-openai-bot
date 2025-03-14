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
# Dodaj importy na początku pliku
from utils.credit_analytics import (
    generate_credit_usage_chart, generate_usage_breakdown_chart, 
    get_credit_usage_breakdown, predict_credit_depletion
)
import matplotlib
matplotlib.use('Agg')  # Konieczne dla działania bez interfejsu graficznego

from database.credits_client import add_stars_payment_option, get_stars_conversion_rate


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

    # Dodaj nową funkcję
async def credit_analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla analizę zużycia kredytów
    Użycie: /creditstats [dni]
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy podano liczbę dni
    days = 30  # Domyślnie 30 dni
    if context.args and len(context.args) > 0:
        try:
            days = int(context.args[0])
            # Ogranicz zakres
            if days < 1:
                days = 1
            elif days > 365:
                days = 365
        except ValueError:
            pass
    
    # Informuj użytkownika o rozpoczęciu analizy
    status_message = await update.message.reply_text(
        "⏳ Analizuję dane o zużyciu kredytów..."
    )
    
    # Pobierz prognozę wyczerpania kredytów
    depletion_info = predict_credit_depletion(user_id, days)
    
    if not depletion_info:
        await status_message.edit_text(
            "Nie masz wystarczającej historii zużycia kredytów do przeprowadzenia analizy. "
            "Spróbuj ponownie po wykonaniu kilku operacji.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Przygotuj wiadomość z analizą
    message = f"📊 *Analiza zużycia kredytów*\n\n"
    message += f"Aktualny stan: *{depletion_info['current_balance']}* kredytów\n"
    message += f"Średnie dzienne zużycie: *{depletion_info['average_daily_usage']}* kredytów\n"
    
    if depletion_info['days_left']:
        message += f"Przewidywane wyczerpanie kredytów: za *{depletion_info['days_left']}* dni "
        message += f"({depletion_info['depletion_date']})\n\n"
    else:
        message += f"Brak wystarczających danych do przewidywania wyczerpania kredytów.\n\n"
    
    # Pobierz rozkład zużycia kredytów
    usage_breakdown = get_credit_usage_breakdown(user_id, days)
    
    if usage_breakdown:
        message += f"*Rozkład zużycia kredytów:*\n"
        for category, amount in usage_breakdown.items():
            percentage = amount / sum(usage_breakdown.values()) * 100
            message += f"- {category}: *{amount}* kredytów ({percentage:.1f}%)\n"
    
    # Wyślij wiadomość z analizą
    await status_message.edit_text(
        message,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Wygeneruj i wyślij wykres historii zużycia
    usage_chart = generate_credit_usage_chart(user_id, days)
    
    if usage_chart:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=usage_chart,
            caption=f"📈 Historia zużycia kredytów z ostatnich {days} dni"
        )
    
    # Wygeneruj i wyślij wykres rozkładu zużycia
    breakdown_chart = generate_usage_breakdown_chart(user_id, days)
    
    if breakdown_chart:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=breakdown_chart,
            caption=f"📊 Rozkład zużycia kredytów z ostatnich {days} dni"
        )
        async def show_stars_purchase_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Pokazuje opcje zakupu kredytów za gwiazdki Telegram
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz kurs wymiany
    conversion_rates = get_stars_conversion_rate()
    
    # Utwórz przyciski dla różnych opcji zakupu za gwiazdki
    keyboard = []
    for stars, credits in conversion_rates.items():
        keyboard.append([
            InlineKeyboardButton(
                f"⭐ {stars} gwiazdek = {credits} kredytów", 
                callback_data=f"buy_stars_{stars}"
            )
        ])
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton("🔙 Powrót do opcji zakupu", callback_data="buy_credits")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌟 *Zakup kredytów za gwiazdki Telegram* 🌟\n\n"
        "Wybierz jedną z poniższych opcji, aby wymienić gwiazdki Telegram na kredyty.\n"
        "Im więcej gwiazdek wymienisz na raz, tym lepszy otrzymasz bonus!\n\n"
        "⚠️ *Uwaga:* Do zakupu za gwiazdki wymagane jest konto Telegram Premium.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def process_stars_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, stars_amount):
    """
    Przetwarza zakup kredytów za gwiazdki Telegram
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz kurs wymiany
    conversion_rates = get_stars_conversion_rate()
    
    # Sprawdź, czy podana liczba gwiazdek jest obsługiwana
    if stars_amount not in conversion_rates:
        await query.edit_message_text(
            "Wystąpił błąd. Nieprawidłowa liczba gwiazdek.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    credits_amount = conversion_rates[stars_amount]
    
    # Tu powinno być wywołanie Telegram Payments API do pobrania gwiazdek
    # Ponieważ jest to tylko symulacja, zakładamy, że płatność się powiodła
    
    # Dodaj kredyty do konta użytkownika
    success = add_stars_payment_option(user_id, stars_amount, credits_amount)
    
    if success:
        current_credits = get_user_credits(user_id)
        await query.edit_message_text(
            f"✅ *Zakup zakończony pomyślnie!*\n\n"
            f"Wymieniono *{stars_amount}* gwiazdek na *{credits_amount}* kredytów\n\n"
            f"Obecny stan kredytów: *{current_credits}*\n\n"
            f"Dziękujemy za zakup! 🎉",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text(
            "Wystąpił błąd podczas przetwarzania płatności. Spróbuj ponownie później.",
            parse_mode=ParseMode.MARKDOWN
        )

# Zmodyfikuj funkcję buy_command, dodając obsługę gwiazdek
# Dodaj te warunki na początku funkcji buy_command:
    
    # Sprawdź, czy użytkownik chce kupić za gwiazdki
    if context.args and len(context.args) > 0 and context.args[0].lower() == "stars":
        await show_stars_purchase_options(update, context)
        return

# W funkcji handle_credit_callback, dodaj obsługę przycisków gwiazdek
# Dodaj ten warunek do funkcji handle_credit_callback przed innymi warunkami:

    # Obsługa przycisku pokazania opcji gwiazdek
    if query.data == "show_stars_options":
        await show_stars_purchase_options(update, context)
        return
    
    # Obsługa przycisków zakupu za gwiazdki
    if query.data.startswith("buy_stars_"):
        stars_amount = int(query.data.split("_")[2])
        await process_stars_purchase(update, context, stars_amount)
        return