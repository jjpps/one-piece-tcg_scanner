import sqlite3
from dtos.card_dto import Card

DB_PATH = 'db.sqlite'

def save_to_db(card: Card, quantity=1):
    """Save a Card object to the database with all fields."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        '''INSERT INTO cards 
        (code, image_url, card_name, quantity, inventory_price, market_price, 
         set_name, card_text, set_id, rarity, card_set_id, card_color, card_type, 
         life, card_cost, card_power, sub_types, counter_amount, attribute, 
         date_scraped, card_image_id, card_image)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (card.card_set_id, card.card_image, card.card_name, quantity, 
         card.inventory_price, card.market_price, card.set_name, card.card_text,
         card.set_id, card.rarity, card.card_set_id, card.card_color, card.card_type,
         card.life, card.card_cost, card.card_power, card.sub_types, 
         card.counter_amount, card.attribute, card.date_scraped, 
         card.card_image_id, card.card_image)
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
        'SELECT code,image_url,card_name,quantity FROM cards WHERE code = ?',
        (code,)
    )

    result = c.fetchone()
    conn.close()
    return result is not None


def get_card_data_by_code(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'SELECT code,image_url,card_name,quantity FROM cards WHERE code = ?',
        (code,)
    )

    row = c.fetchone()
    conn.close()

    if row:
        return {
            'code': row[0],
            'image_url': row[1],
            'card_name': row[2],
            'quantity': row[3]
        }

    return None

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

    c.execute('SELECT code,image_url,card_name,quantity,date(processed_at) as processed_at, card_color FROM cards order by processed_at desc')
    cards = c.fetchall()

    conn.close()
    return cards


def get_distinct_card_colors():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT DISTINCT card_color FROM cards WHERE card_color IS NOT NULL AND TRIM(card_color) <> '' ORDER BY card_color")
    colors = [row[0] for row in c.fetchall()]

    conn.close()
    return colors


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