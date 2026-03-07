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
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS CARDS_HASH(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL
        )
        '''
    )
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS CARDS_PROCESSING_HISTORY(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_code TEXT NOT NULL UNIQUE,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )


    conn.commit()
    conn.close()

