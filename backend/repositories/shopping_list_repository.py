import sqlite3

DB_PATH = 'db.sqlite'


def list_items() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        'SELECT code, card_name, remaining FROM shopping_list_items ORDER BY code'
    ).fetchall()
    conn.close()
    return [{'code': r[0], 'card_name': r[1], 'remaining': r[2]} for r in rows]


def replace_all(items: list[dict]) -> None:
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute('DELETE FROM shopping_list_items')
        conn.executemany(
            'INSERT INTO shopping_list_items (code, card_name, remaining) VALUES (?, ?, ?)',
            [(i['code'], i['card_name'], i['remaining']) for i in items],
        )
    conn.close()


def add_or_sum(code: str, card_name: str, remaining: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute(
            '''INSERT INTO shopping_list_items (code, card_name, remaining) VALUES (?, ?, ?)
               ON CONFLICT(code) DO UPDATE SET remaining = remaining + excluded.remaining''',
            (code, card_name, remaining),
        )
    conn.close()


def clear() -> None:
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute('DELETE FROM shopping_list_items')
    conn.close()


def abater(cursor, code: str, qtd: int = 1) -> None:
    """Baixa o faltante dentro da transação do chamador; apaga o item ao chegar a zero.

    O DELETE vem antes do UPDATE para o CHECK (remaining > 0) nunca ser violado.
    """
    cursor.execute(
        'DELETE FROM shopping_list_items WHERE code = ? AND remaining <= ?', (code, qtd)
    )
    cursor.execute(
        'UPDATE shopping_list_items SET remaining = remaining - ? WHERE code = ?', (qtd, code)
    )
