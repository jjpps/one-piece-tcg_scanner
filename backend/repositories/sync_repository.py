import sqlite3

DB_PATH = 'db.sqlite'

NO_COLOR = '__no_color__'
COLOR_EXPR = f"COALESCE(NULLIF(TRIM(card_color), ''), '{NO_COLOR}')"

# Tipo da Divergência, derivado das quantidades (0 = não possui).
KIND_EXPR = '''CASE WHEN our_quantity = 0 THEN 'binder_only'
                    WHEN binder_quantity = 0 THEN 'ours_only'
                    ELSE 'both' END'''


def _dict_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_open_session():
    conn = _dict_connection()
    row = conn.execute(
        "SELECT id, status, created_at, completed_at FROM sync_sessions WHERE status = 'open'"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_session_by_id(session_id):
    conn = _dict_connection()
    row = conn.execute(
        'SELECT id, status, created_at, completed_at FROM sync_sessions WHERE id = ?', (session_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_session_with_divergences(binder_quantities):
    """Compara o CSV do Binder com `cards` e grava só as Divergências."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO sync_sessions (status) VALUES ('open')")
        session_id = c.lastrowid

        ours = {
            code: (name, image, color, quantity or 0)
            for code, name, image, color, quantity in c.execute(
                'SELECT code, card_name, image_url, card_color, quantity FROM cards'
            ).fetchall()
        }

        rows = []
        for code in sorted(set(ours) | set(binder_quantities)):
            name, image, color, our_qty = ours.get(code, (None, None, None, 0))
            binder_qty = binder_quantities.get(code, 0)
            if our_qty != binder_qty:
                rows.append((session_id, code, name, image, color, our_qty, binder_qty))

        c.executemany(
            '''INSERT INTO sync_session_items
               (session_id, code, card_name, card_image_url, card_color, our_quantity, binder_quantity)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            rows
        )
        conn.commit()
        return session_id, len(rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def discard_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE sync_sessions SET status = 'discarded', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (session_id,)
    )
    conn.commit()
    conn.close()


def get_session_summary(session_id):
    conn = _dict_connection()
    c = conn.cursor()

    row = c.execute(
        f'''SELECT COUNT(*) as total,
                   COALESCE(SUM(resolution IS NULL), 0) as pending,
                   COALESCE(SUM({KIND_EXPR} = 'binder_only'), 0) as binder_only,
                   COALESCE(SUM({KIND_EXPR} = 'ours_only'), 0) as ours_only,
                   COALESCE(SUM({KIND_EXPR} = 'both'), 0) as both
            FROM sync_session_items WHERE session_id = ?''',
        (session_id,)
    ).fetchone()

    colors = [dict(r) for r in c.execute(
        f'''SELECT {COLOR_EXPR} as card_color, COUNT(*) as total, SUM(resolution IS NULL) as pending
            FROM sync_session_items WHERE session_id = ? GROUP BY 1 ORDER BY 1''',
        (session_id,)
    ).fetchall()]

    conn.close()
    return {**dict(row), 'colors': colors}


def _filters(session_id, kind=None, color=None, status=None, search=None):
    conditions = ['session_id = ?']
    params = [session_id]
    if kind:
        conditions.append(f'{KIND_EXPR} = ?')
        params.append(kind)
    if color:
        conditions.append(f'{COLOR_EXPR} = ?')
        params.append(color)
    if status == 'pending':
        conditions.append('resolution IS NULL')
    elif status == 'resolved':
        conditions.append('resolution IS NOT NULL')
    if search:
        conditions.append('(code LIKE ? OR card_name LIKE ?)')
        params.extend([f'%{search}%', f'%{search}%'])
    return ' AND '.join(conditions), params


ITEM_COLUMNS = f'''code, card_name, card_image_url, card_color, our_quantity, binder_quantity,
                   resolution, {KIND_EXPR} as kind'''


def get_session_items(session_id, kind=None, color=None, status=None, search=None, page=1, page_size=50):
    where, params = _filters(session_id, kind, color, status, search)
    conn = _dict_connection()
    c = conn.cursor()
    total = c.execute(f'SELECT COUNT(*) FROM sync_session_items WHERE {where}', params).fetchone()[0]
    items = [dict(r) for r in c.execute(
        f'SELECT {ITEM_COLUMNS} FROM sync_session_items WHERE {where} ORDER BY code LIMIT ? OFFSET ?',
        params + [page_size, (page - 1) * page_size]
    ).fetchall()]
    conn.close()
    return items, total


def get_item(session_id, code):
    conn = _dict_connection()
    row = conn.execute(
        f'SELECT {ITEM_COLUMNS} FROM sync_session_items WHERE session_id = ? AND code = ?',
        (session_id, code)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def set_resolution(session_id, code, resolution):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        'UPDATE sync_session_items SET resolution = ? WHERE session_id = ? AND code = ?',
        (resolution, session_id, code)
    )
    conn.commit()
    conn.close()
    return get_item(session_id, code)


def set_resolution_bulk(session_id, resolution, kind=None, color=None):
    """Resolve em massa só as Divergências ainda pendentes que batem com os filtros."""
    where, params = _filters(session_id, kind, color, status='pending')
    conn = sqlite3.connect(DB_PATH)
    c = conn.execute(f'UPDATE sync_session_items SET resolution = ? WHERE {where}', [resolution] + params)
    conn.commit()
    updated = c.rowcount
    conn.close()
    return updated


def get_resolved_items(session_id, resolution):
    conn = _dict_connection()
    rows = [dict(r) for r in conn.execute(
        '''SELECT code, our_quantity, binder_quantity FROM sync_session_items
           WHERE session_id = ? AND resolution = ? ORDER BY code''',
        (session_id, resolution)
    ).fetchall()]
    conn.close()
    return rows


def existing_codes(codes):
    conn = sqlite3.connect(DB_PATH)
    found = {row[0] for row in conn.execute(
        f"SELECT code FROM cards WHERE code IN ({','.join('?' * len(codes))})", list(codes)
    ).fetchall()} if codes else set()
    conn.close()
    return found


def commit_session(session_id, quantity_updates, new_cards):
    """quantity_updates: [(code, quantity)] em cartas existentes; new_cards: [(code, Card, quantity)]."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.executemany('UPDATE cards SET quantity = ? WHERE code = ?', [(q, code) for code, q in quantity_updates])

        for code, card, quantity in new_cards:
            c.execute(
                '''INSERT INTO cards
                   (code, image_url, card_name, quantity, inventory_price, market_price,
                    set_name, card_text, set_id, rarity, card_set_id, card_color, card_type,
                    life, card_cost, card_power, sub_types, counter_amount, attribute,
                    date_scraped, card_image_id, card_image)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (code, card.card_image, card.card_name, quantity,
                 card.inventory_price, card.market_price, card.set_name, card.card_text,
                 card.set_id, card.rarity, card.card_set_id, card.card_color, card.card_type,
                 card.life, card.card_cost, card.card_power, card.sub_types,
                 card.counter_amount, card.attribute, card.date_scraped,
                 card.card_image_id, card.card_image)
            )

        c.execute(
            "UPDATE sync_sessions SET status = 'committed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
