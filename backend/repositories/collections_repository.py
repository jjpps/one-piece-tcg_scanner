import sqlite3

DB_PATH = 'db.sqlite'


def totals() -> dict[str, int]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT prefix, total FROM collection_totals').fetchall()
    conn.close()
    return dict(rows)


def save_totals(new_totals: dict[str, int]) -> None:
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.executemany(
            'INSERT OR REPLACE INTO collection_totals (prefix, total) VALUES (?, ?)',
            new_totals.items(),
        )
    conn.close()


def owned_codes() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT code FROM cards WHERE quantity > 0').fetchall()
    conn.close()
    return [r[0] for r in rows]
