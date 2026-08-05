import sqlite3

DB_PATH = 'db.sqlite'

# Colunas exigidas por cards_repository.save_to_db além das já criadas no CREATE TABLE
# original. Mantidas numa lista separada para permitir migrar bancos já existentes
# (criados antes destas colunas existirem) via ALTER TABLE, sem perder dados.
CARDS_EXTRA_COLUMNS = [
    ('inventory_price', 'REAL'),
    ('market_price', 'REAL'),
    ('set_name', 'TEXT'),
    ('card_text', 'TEXT'),
    ('set_id', 'TEXT'),
    ('rarity', 'TEXT'),
    ('card_set_id', 'TEXT'),
    ('card_color', 'TEXT'),
    ('card_type', 'TEXT'),
    ('life', 'TEXT'),
    ('card_cost', 'TEXT'),
    ('card_power', 'TEXT'),
    ('sub_types', 'TEXT'),
    ('counter_amount', 'INTEGER'),
    ('attribute', 'TEXT'),
    ('date_scraped', 'TEXT'),
    ('card_image_id', 'TEXT'),
    ('card_image', 'TEXT'),
]


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
            quantity INTEGER default 1,
            inventory_price REAL default NULL,
            market_price REAL default NULL,
            set_name TEXT default NULL,
            card_text TEXT default NULL,
            set_id TEXT default NULL,
            rarity TEXT default NULL,
            card_set_id TEXT default NULL,
            card_color TEXT default NULL,
            card_type TEXT default NULL,
            life TEXT default NULL,
            card_cost TEXT default NULL,
            card_power TEXT default NULL,
            sub_types TEXT default NULL,
            counter_amount INTEGER default NULL,
            attribute TEXT default NULL,
            date_scraped TEXT default NULL,
            card_image_id TEXT default NULL,
            card_image TEXT default NULL
        )
    ''')

    # Migra bancos criados antes destas colunas existirem (idempotente: só adiciona o que faltar).
    existing_columns = {row[1] for row in c.execute('PRAGMA table_info(cards)').fetchall()}
    for column_name, column_type in CARDS_EXTRA_COLUMNS:
        if column_name not in existing_columns:
            c.execute(f'ALTER TABLE cards ADD COLUMN {column_name} {column_type}')

    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL DEFAULT 'open',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME DEFAULT NULL
        )
    ''')

    c.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_sessions_single_open
        ON inventory_sessions(status)
        WHERE status = 'open'
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_session_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES inventory_sessions(id),
            code TEXT NOT NULL,
            card_name TEXT,
            card_image_url TEXT,
            card_color TEXT,
            is_new_card INTEGER NOT NULL DEFAULT 0,
            card_data_json TEXT DEFAULT NULL,
            system_quantity INTEGER NOT NULL DEFAULT 0,
            reviewed INTEGER NOT NULL DEFAULT 0,
            changed INTEGER DEFAULT NULL,
            counted_quantity INTEGER DEFAULT NULL,
            reviewed_at DATETIME DEFAULT NULL,
            UNIQUE(session_id, code)
        )
    ''')

    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_inventory_items_session_color
        ON inventory_session_items(session_id, card_color)
    ''')

    conn.commit()
    conn.close()

