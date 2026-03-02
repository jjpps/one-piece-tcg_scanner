import sqlite3

DB_PATH = 'db.sqlite'


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            image_url TEXT default NULL,
            card_name TEXT default NULL,
            quantity INTEGER default 1
        )
    ''')

    conn.commit()
    conn.close()


def save_to_db(filename, code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'INSERT INTO cards (filename, code) VALUES (?, ?)',
        (filename, code)
    )

    conn.commit()
    conn.close()

