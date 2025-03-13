from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import SUBSCRIPTION_EXPIRED_MESSAGE
from database.supabase_client import check_active_subscription
from utils.openai_client import generate_image_dall_e

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generuje obraz za pomocą DALL-E na podstawie opisu
    Użycie: /image [opis obrazu]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik ma aktywną subskrypcję
    if not check_active_subscription(user_id):
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
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    
    # Generuj obraz
    image_url = generate_image_dall_e(prompt)
    
    if image_url:
        # Usuń wiadomość o ładowaniu
        await message.delete()
        
        # Wyślij obraz
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=image_url,
            caption=f"*Wygenerowany obraz:*\n{prompt}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Aktualizuj wiadomość o błędzie
        await message.edit_text("Przepraszam, wystąpił błąd podczas generowania obrazu. Spróbuj ponownie z innym opisem.")