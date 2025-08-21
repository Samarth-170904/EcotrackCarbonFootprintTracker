from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime
import logging

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Configure logging for white box testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This is the emission factor we will use for calculations.
# Example: 0.37 kg CO2e per kWh for the US grid.
EMISSION_FACTOR_KWH = 0.37
DATABASE = 'ecotrack.db'

def _get_database_uri():
    """Return the configured database URI/path, falling back to default."""
    return app.config.get('DATABASE', DATABASE)


def _connect_db():
    """Create a SQLite connection honoring URI strings (e.g., in-memory shared)."""
    db_uri = _get_database_uri()
    use_uri = isinstance(db_uri, str) and db_uri.startswith('file:')
    conn = sqlite3.connect(db_uri, uri=use_uri)
    return conn


def init_db():
    """Initialize the database with users and calculations tables."""
    conn = _connect_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Calculations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            kwh_input REAL NOT NULL,
            co2_result REAL NOT NULL,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection."""
    conn = _connect_db()
    conn.row_factory = sqlite3.Row
    return conn

def validate_kwh_input(kwh_input_str):
    """
    Validate kWh input with comprehensive error handling.
    Returns: (is_valid, error_message, kwh_value)
    """
    logger.info(f"Validating kWh input: '{kwh_input_str}'")

    # Path 1: Empty input check
    if not kwh_input_str or kwh_input_str.strip() == '':
        logger.warning("Empty input provided")
        return False, "Please enter a value.", None

    # Only allow plain decimal numbers (no commas or scientific notation). Allow optional leading '-'
    import re
    trimmed = kwh_input_str.strip()
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", trimmed):
        logger.error(f"Invalid numeric format: {kwh_input_str}")
        return False, "Please enter a valid number.", None

    try:
        # Path 2: Convert to float after format validation
        kwh = float(trimmed)
        logger.info(f"Successfully parsed kWh value: {kwh}")

        # Path 3: Check for negative or zero values
        if kwh <= 0:
            logger.warning(f"Invalid kWh value (<=0): {kwh}")
            return False, "Value must be greater than 0.", None

        # Path 4: Check for upper boundary
        if kwh > 99999:
            logger.warning(f"Invalid kWh value (>99999): {kwh}")
            return False, "Value cannot exceed 99,999.", None

        # Path 5: Valid input
        logger.info(f"Valid kWh input: {kwh}")
        return True, None, kwh

    except (ValueError, TypeError) as e:
        # Path 6: Invalid numeric input
        logger.error(f"Invalid numeric input: {kwh_input_str}, Error: {e}")
        return False, "Please enter a valid number.", None

def calculate_co2_emission(kwh):
    """Calculate CO2 emission from kWh consumption."""
    logger.info(f"Calculating CO2 emission for {kwh} kWh")
    result = kwh * EMISSION_FACTOR_KWH
    logger.info(f"CO2 emission calculated: {result} kg CO2e")
    return result

def save_calculation(user_id, kwh_input, co2_result):
    """Save calculation to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO calculations (user_id, kwh_input, co2_result) VALUES (?, ?, ?)',
            (user_id, kwh_input, co2_result)
        )
        conn.commit()
        conn.close()
        logger.info(f"Calculation saved for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving calculation: {e}")
        return False

@app.route('/')
def index():
    """Home page route."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('calculator'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
            existing_user = cursor.fetchone()
            
            if existing_user:
                flash('Username or email already exists. Please log in.', 'error')
                conn.close()
                return redirect(url_for('login'))
            
            # Create new user
            password_hash = generate_password_hash(password)
            cursor.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            conn.commit()
            conn.close()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            conn.close()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash(f'Welcome back, {user["username"]}!', 'success')
                return redirect(url_for('calculator'))
            else:
                flash('Invalid username or password.', 'error')
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout route."""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    """Main calculator route."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    error = None
    result = None
    kwh_input = ''

    if request.method == 'POST':
        kwh_input = request.form.get('kwh', '').strip()
        
        # Use the validation function
        is_valid, error_message, kwh_value = validate_kwh_input(kwh_input)
        
        if not is_valid:
            error = error_message
        else:
            # Calculate CO2 emission
            result = calculate_co2_emission(kwh_value)
            
            # Save calculation to database
            if save_calculation(session['user_id'], kwh_value, result):
                flash('Calculation saved to your history!', 'success')
            else:
                flash('Calculation completed but could not be saved to history.', 'warning')

    return render_template('calculator.html', error=error, result=result, kwh_input=kwh_input)

@app.route('/history')
def history():
    """User calculation history route."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT kwh_input, co2_result, calculated_at 
            FROM calculations 
            WHERE user_id = ? 
            ORDER BY calculated_at DESC 
            LIMIT 50
        ''', (session['user_id'],))
        calculations = cursor.fetchall()
        conn.close()
        
        return render_template('history.html', calculations=calculations)
        
    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        flash('Error retrieving calculation history.', 'error')
        return redirect(url_for('calculator'))

# Initialize database on startup
with app.app_context():
    init_db()

if __name__ == '__main__':
    # Setting debug=False to see the standard "Internal Server Error" page
    app.run(debug=True, port=5001)