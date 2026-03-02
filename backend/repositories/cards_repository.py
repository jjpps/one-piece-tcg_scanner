import sqlite3
DB_PATH = 'db.sqlite'
def save_to_db(code,image_url=None, card_name=None, quantity=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'INSERT INTO cards (code,image_url,card_name,quantity) VALUES (?, ?, ?, ?, ?)',
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

    c.execute('SELECT code,image_url,card_name,quantity FROM cards')
    cards = c.fetchall()

    conn.close()
    return cards
