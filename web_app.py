from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import secrets
import datetime
import pytz

# Importy z istniejącego bota
from config import BOT_NAME, CREDIT_PACKAGES
from database.credits_client import get_user_credits, add_user_credits, get_credit_packages, purchase_credits

# Inicjalizacja aplikacji Flask
app = Flask(__name__, 
    template_folder='web/templates',
    static_folder='web/static'
)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(16))
app.config['ADMIN_USERNAME'] = os.environ.get('ADMIN_USERNAME', 'admin')
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'password')  # Zmień to w produkcji!

# Middleware do sprawdzania, czy użytkownik jest zalogowany jako admin
def admin_required(func):
    def wrapper(*args, **kwargs):
        if session.get('admin_logged_in'):
            return func(*args, **kwargs)
        else:
            flash('Wymagane logowanie administratora!')
            return redirect(url_for('admin_login'))
    wrapper.__name__ = func.__name__
    return wrapper

# Strona główna - sklep
@app.route('/')
def index():
    packages = get_credit_packages()
    return render_template('shop.html', bot_name=BOT_NAME, packages=packages)

# Strona zakupu kredytów
@app.route('/buy/<int:package_id>', methods=['GET', 'POST'])
def buy_credits(package_id):
    if request.method == 'POST':
        telegram_id = request.form.get('telegram_id')
        if not telegram_id or not telegram_id.isdigit():
            flash('Proszę podać prawidłowy identyfikator Telegram!')
            return redirect(url_for('buy_credits', package_id=package_id))
        
        telegram_id = int(telegram_id)
        
        # Symulowany proces płatności - w rzeczywistości tutaj byłaby integracja z bramką płatności
        success, package = purchase_credits(telegram_id, package_id)
        
        if success:
            flash(f'Zakup zakończony pomyślnie! Dodano {package["credits"]} kredytów do konta {telegram_id}.')
            return redirect(url_for('purchase_success'))
        else:
            flash('Wystąpił błąd podczas przetwarzania zakupu. Spróbuj ponownie.')
    
    # Pobierz informacje o pakiecie
    package = None
    packages = get_credit_packages()
    for pkg in packages:
        if pkg['id'] == package_id:
            package = pkg
            break
    
    if not package:
        flash('Nieprawidłowy pakiet!')
        return redirect(url_for('index'))
    
    return render_template('buy.html', package=package, bot_name=BOT_NAME)

@app.route('/success')
def purchase_success():
    return render_template('success.html', bot_name=BOT_NAME)

# Panel logowania administratora
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Nieprawidłowa nazwa użytkownika lub hasło!')
    
    return render_template('admin_login.html', bot_name=BOT_NAME)

# Dashboard administratora
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', bot_name=BOT_NAME)

# Zarządzanie licencjami
@app.route('/admin/licenses', methods=['GET', 'POST'])
@admin_required
def admin_licenses():
    if request.method == 'POST':
        duration = int(request.form.get('duration'))
        count = int(request.form.get('count'))
        credits = int(request.form.get('credits'))
        
        # Generowanie licencji
        from utils.activation_codes import create_multiple_codes
        codes = create_multiple_codes(credits, count)
        
        return render_template('admin_licenses.html', bot_name=BOT_NAME, 
                               generated_codes=codes, credits=credits)
    
    # Pobierz istniejące licencje z bazy danych
    conn = sqlite3.connect('bot_database.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, credits, is_used, used_by, used_at, created_at FROM activation_codes ORDER BY created_at DESC LIMIT 20")
    licenses = []
    for row in cursor.fetchall():
        licenses.append({
            'id': row[0],
            'code': row[1],
            'credits': row[2],
            'is_used': bool(row[3]),
            'used_by': row[4],
            'used_at': row[5],
            'created_at': row[6]
        })
    conn.close()
    
    return render_template('admin_licenses.html', bot_name=BOT_NAME, licenses=licenses)

# Zarządzanie użytkownikami
@app.route('/admin/users')
@admin_required
def admin_users():
    # Pobierz listę użytkowników
    conn = sqlite3.connect('bot_database.sqlite')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.username, u.first_name, u.last_name, uc.credits_amount, 
               u.created_at, uc.total_credits_purchased 
        FROM users u 
        LEFT JOIN user_credits uc ON u.id = uc.user_id
        ORDER BY u.id DESC
        LIMIT 100
    """)
    users = []
    for row in cursor.fetchall():
        users.append({
            'id': row[0],
            'username': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'credits': row[4] or 0,
            'created_at': row[5],
            'total_credits': row[6] or 0
        })
    conn.close()
    
    return render_template('admin_users.html', bot_name=BOT_NAME, users=users)

# Dodawanie kredytów użytkownikowi ręcznie
@app.route('/admin/add_credits', methods=['POST'])
@admin_required
def admin_add_credits():
    user_id = int(request.form.get('user_id'))
    credits = int(request.form.get('credits'))
    
    if credits > 0:
        # Dodaj kredyty
        add_user_credits(user_id, credits, "Dodano przez administratora przez panel web")
        flash(f'Dodano {credits} kredytów dla użytkownika {user_id}')
    
    return redirect(url_for('admin_users'))

# Wylogowanie z panelu administratora
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Wylogowano pomyślnie!')
    return redirect(url_for('admin_login'))

# Uruchomienie aplikacji
if __name__ == '__main__':
    app.run(debug=True, port=5000)