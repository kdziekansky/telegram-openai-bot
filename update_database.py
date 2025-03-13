import sqlite3
import logging

# Konfiguracja loggera
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ścieżka do pliku bazy danych
DB_PATH = "bot_database.sqlite"

def update_database_schema():
    """
    Aktualizuje schemat bazy danych, dodając pola potrzebne do obsługi
    systemu licencji opartego na liczbie wiadomości.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Sprawdź, czy kolumna message_limit już istnieje w tabeli licenses
        cursor.execute("PRAGMA table_info(licenses)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'message_limit' not in column_names:
            logger.info("Dodawanie kolumny message_limit do tabeli licenses")
            cursor.execute("ALTER TABLE licenses ADD COLUMN message_limit INTEGER DEFAULT 0")
        
        # Sprawdź, czy kolumna messages_used już istnieje w tabeli users
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'messages_used' not in column_names:
            logger.info("Dodawanie kolumny messages_used do tabeli users")
            cursor.execute("ALTER TABLE users ADD COLUMN messages_used INTEGER DEFAULT 0")
        
        if 'messages_limit' not in column_names:
            logger.info("Dodawanie kolumny messages_limit do tabeli users")
            cursor.execute("ALTER TABLE users ADD COLUMN messages_limit INTEGER DEFAULT 0")
        
        # Zatwierdzenie zmian
        conn.commit()
        logger.info("Aktualizacja schematu bazy danych zakończona pomyślnie")
        
        # Wyświetl informacje o aktualnym schemacie
        logger.info("Aktualny schemat tabeli licenses:")
        cursor.execute("PRAGMA table_info(licenses)")
        for column in cursor.fetchall():
            logger.info(f" - {column[1]} ({column[2]})")
        
        logger.info("Aktualny schemat tabeli users:")
        cursor.execute("PRAGMA table_info(users)")
        for column in cursor.fetchall():
            logger.info(f" - {column[1]} ({column[2]})")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji schematu bazy danych: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    print("Rozpoczynam aktualizację schematu bazy danych...")
    result = update_database_schema()
    if result:
        print("Aktualizacja zakończona pomyślnie!")
    else:
        print("Wystąpił błąd podczas aktualizacji. Sprawdź logi.")