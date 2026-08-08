import sqlite3
import json
from dtos.card_dto import Card

DB_PATH = 'db.sqlite'


def _dict_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_open_session():
    conn = _dict_connection()
    c = conn.cursor()

    c.execute(
        'SELECT id, status, created_at, updated_at, completed_at FROM inventory_sessions WHERE status = ?',
        ('open',)
    )

    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_session_by_id(session_id):
    conn = _dict_connection()
    c = conn.cursor()

    c.execute(
        'SELECT id, status, created_at, updated_at, completed_at FROM inventory_sessions WHERE id = ?',
        (session_id,)
    )

    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def create_session_with_snapshot():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        c.execute("UPDATE inventory_sessions SET status = 'discarded', updated_at = CURRENT_TIMESTAMP WHERE status = 'open'")
        c.execute("INSERT INTO inventory_sessions (status) VALUES ('open')")
        session_id = c.lastrowid

        c.execute('SELECT code, card_name, image_url, card_color, quantity FROM cards')
        cards = c.fetchall()

        rows = [
            (session_id, code, card_name, image_url, card_color, quantity)
            for code, card_name, image_url, card_color, quantity in cards
        ]

        c.executemany(
            '''INSERT INTO inventory_session_items
               (session_id, code, card_name, card_image_url, card_color, is_new_card, system_quantity, reviewed, changed, counted_quantity)
               VALUES (?, ?, ?, ?, ?, 0, ?, 0, NULL, NULL)''',
            rows
        )

        conn.commit()
        return session_id, len(rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_session_summary(session_id):
    conn = _dict_connection()
    c = conn.cursor()

    c.execute(
        '''SELECT
               COUNT(*) as total_items,
               COALESCE(SUM(reviewed), 0) as reviewed_count,
               COALESCE(SUM(CASE WHEN changed = 1 AND is_new_card = 0 THEN 1 ELSE 0 END), 0) as changed_count,
               COALESCE(SUM(is_new_card), 0) as new_count
           FROM inventory_session_items WHERE session_id = ?''',
        (session_id,)
    )

    row = c.fetchone()
    conn.close()

    total = row['total_items']
    reviewed = row['reviewed_count']
    return {
        'total_items': total,
        'reviewed_count': reviewed,
        'pending_count': total - reviewed,
        'changed_count': row['changed_count'],
        'new_count': row['new_count'],
    }


def get_session_colors(session_id):
    conn = _dict_connection()
    c = conn.cursor()

    c.execute(
        '''SELECT
               COALESCE(NULLIF(TRIM(card_color), ''), '__no_color__') as card_color,
               COUNT(*) as total,
               COALESCE(SUM(reviewed), 0) as reviewed
           FROM inventory_session_items
           WHERE session_id = ?
           GROUP BY 1
           ORDER BY 1''',
        (session_id,)
    )

    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_session_items(session_id, color=None, status='pending', search=None, page=1, page_size=50):
    conn = _dict_connection()
    c = conn.cursor()

    conditions = ['session_id = ?']
    params = [session_id]

    if color:
        if color == '__no_color__':
            conditions.append("COALESCE(NULLIF(TRIM(card_color), ''), '__no_color__') = '__no_color__'")
        else:
            conditions.append('card_color = ?')
            params.append(color)

    if status == 'pending':
        conditions.append('reviewed = 0')
    elif status == 'reviewed':
        conditions.append('reviewed = 1')

    if search:
        conditions.append('(code LIKE ? OR card_name LIKE ?)')
        like_term = f'%{search}%'
        params.extend([like_term, like_term])

    where_clause = ' AND '.join(conditions)

    c.execute(f'SELECT COUNT(*) as total FROM inventory_session_items WHERE {where_clause}', params)
    total = c.fetchone()['total']

    offset = (page - 1) * page_size
    c.execute(
        f'''SELECT code, card_name, card_image_url, card_color, system_quantity,
                   is_new_card, reviewed, changed, counted_quantity
            FROM inventory_session_items
            WHERE {where_clause}
            ORDER BY code
            LIMIT ? OFFSET ?''',
        params + [page_size, offset]
    )

    items = [dict(r) for r in c.fetchall()]
    conn.close()
    return items, total


def get_item(session_id, code):
    conn = _dict_connection()
    c = conn.cursor()

    c.execute(
        '''SELECT code, card_name, card_image_url, card_color, system_quantity,
                  is_new_card, reviewed, changed, counted_quantity
           FROM inventory_session_items WHERE session_id = ? AND code = ?''',
        (session_id, code)
    )

    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def item_exists(session_id, code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'SELECT 1 FROM inventory_session_items WHERE session_id = ? AND code = ?',
        (session_id, code)
    )

    result = c.fetchone()
    conn.close()
    return result is not None


def mark_item_reviewed(session_id, code, changed, counted_quantity=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        '''UPDATE inventory_session_items
           SET reviewed = 1, changed = ?, counted_quantity = ?, reviewed_at = CURRENT_TIMESTAMP
           WHERE session_id = ? AND code = ?''',
        (1 if changed else 0, counted_quantity, session_id, code)
    )

    conn.commit()
    conn.close()
    return get_item(session_id, code)


def add_new_card_item(session_id, code, card: Card, counted_quantity):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        '''INSERT INTO inventory_session_items
               (session_id, code, card_name, card_image_url, card_color,
                is_new_card, card_data_json, system_quantity, reviewed, changed, counted_quantity, reviewed_at)
           VALUES (?, ?, ?, ?, ?, 1, ?, 0, 1, 1, ?, CURRENT_TIMESTAMP)''',
        (session_id, code, card.card_name, card.card_image, card.card_color,
         json.dumps(card.__dict__), counted_quantity)
    )

    conn.commit()
    conn.close()
    return get_item(session_id, code)


def get_session_diff(session_id):
    conn = _dict_connection()
    c = conn.cursor()

    c.execute(
        '''SELECT code, card_name, system_quantity, counted_quantity
           FROM inventory_session_items
           WHERE session_id = ? AND is_new_card = 0 AND changed = 1 AND counted_quantity != system_quantity
           ORDER BY code''',
        (session_id,)
    )
    updates = [dict(r) for r in c.fetchall()]

    c.execute(
        '''SELECT code, card_name, counted_quantity
           FROM inventory_session_items
           WHERE session_id = ? AND is_new_card = 1
           ORDER BY code''',
        (session_id,)
    )
    new_cards = [dict(r) for r in c.fetchall()]

    c.execute(
        'SELECT COUNT(*) as total FROM inventory_session_items WHERE session_id = ? AND reviewed = 0',
        (session_id,)
    )
    pending_count = c.fetchone()['total']

    c.execute(
        '''SELECT code, card_name, card_color
           FROM inventory_session_items
           WHERE session_id = ? AND reviewed = 0
           ORDER BY code
           LIMIT 20''',
        (session_id,)
    )
    pending_preview = [dict(r) for r in c.fetchall()]

    conn.close()
    return {
        'updates': updates,
        'new_cards': new_cards,
        'pending_count': pending_count,
        'pending_preview': pending_preview,
    }


def apply_session(session_id):
    diff = get_session_diff(session_id)
    left_pending = diff['pending_count']

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        for item in diff['updates']:
            c.execute('UPDATE cards SET quantity = ? WHERE code = ?', (item['counted_quantity'], item['code']))
            if c.rowcount == 0:
                raise ValueError(f"Carta {item['code']} não foi encontrada em cards durante a aplicação")

        for item in diff['new_cards']:
            c.execute(
                'SELECT card_data_json, counted_quantity FROM inventory_session_items WHERE session_id = ? AND code = ?',
                (session_id, item['code'])
            )
            row = c.fetchone()
            if row is None:
                raise ValueError(f"Item de sessão não encontrado para {item['code']}")

            card = Card(**json.loads(row[0]))
            quantity = row[1]

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

        c.execute(
            "UPDATE inventory_sessions SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,)
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        'updated': len(diff['updates']),
        'added': len(diff['new_cards']),
        'left_pending': left_pending,
    }
