import sqlite3
import imagehash
DB_PATH = 'db.sqlite'
def load_hashes_from_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT code, hash FROM CARDS_HASH')
    rows = c.fetchall()

    conn.close()
    hashes_db = []

    for code, hash_str in rows:
        hashes_db.append(
            (code, imagehash.hex_to_hash(hash_str))
        )

    return hashes_db