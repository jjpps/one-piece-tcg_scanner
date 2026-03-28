import sqlite3
DB_PATH = 'db.sqlite'
def save_to_db(code,image_url=None, card_name=None, quantity=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'INSERT INTO cards (code,image_url,card_name,quantity) VALUES (?, ?, ?, ?)',
        (code, image_url, card_name, quantity)
    )

    conn.commit()
    conn.close()

def card_exists(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'SELECT id FROM cards WHERE code = ?',
        (code,)
    )

    result = c.fetchone()
    conn.close()
    return result is not None

def get_card_by_code(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'SELECT code,image_url,card_name FROM cards WHERE code = ?',
        (code,)
    )

    result = c.fetchone()
    conn.close()
    return result is not None

def add_card_quantity(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'UPDATE cards SET quantity = quantity + 1 WHERE code = ?',
        (code,)
    )

    conn.commit()
    conn.close()

def get_all_cards():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT code,image_url,card_name,quantity,date(processed_at) as processed_at FROM cards order by processed_at desc')
    cards = c.fetchall()

    conn.close()
    return cards


def save_card_hash(code, hash_value):    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'INSERT OR REPLACE INTO CARDS_HASH (code, hash) VALUES (?, ?)',
        (code, hash_value)
    )

    conn.commit()
    conn.close()


def save_processing_history(set_code):   
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # use INSERT OR IGNORE to avoid integrity errors when the set has already been recorded
    c.execute(
        'INSERT OR IGNORE INTO CARDS_PROCESSING_HISTORY (set_code) VALUES (?)',
        (set_code,)
    )

    conn.commit()
    conn.close()


def is_set_processed(set_code):
    """Return True if the given set_code has an entry in the history table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'SELECT 1 FROM CARDS_PROCESSING_HISTORY WHERE set_code = ?',
        (set_code,)
    )

    result = c.fetchone()
    conn.close()
    return result is not None

def delete_card_by_code(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'DELETE FROM cards WHERE code = ?',
        (code,)
    )

    conn.commit()
    conn.close()

def remove_card_quantity(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'UPDATE cards SET quantity = quantity - 1 WHERE code = ? AND quantity > 0',
        (code,)
    )

    conn.commit()
    conn.close()