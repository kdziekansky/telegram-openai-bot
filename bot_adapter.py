# bot_adapter.py - Адаптер для python-telegram-bot 13.x
from telegram.ext import Updater, CallbackContext, Dispatcher

class ApplicationAdapter:
    def __init__(self, token):
        self.updater = Updater(token=token)
        self.dispatcher = self.updater.dispatcher
        
    @classmethod
    def builder(cls):
        return ApplicationBuilder()

    def add_handler(self, handler):
        self.dispatcher.add_handler(handler)
        
    def run_polling(self):
        self.updater.start_polling()
        self.updater.idle()
        
class ApplicationBuilder:
    def __init__(self):
        self._token = None
        
    def token(self, token):
        self._token = token
        return self
        
    def build(self):
        return ApplicationAdapter(self._token)

# Заменитель для get_current() в контексте
def get_current_adapter(context):
    return context.bot