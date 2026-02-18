import sqlite3
import base64
import pandas as pd
import io
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage

DB_PATH = 'db.sqlite'


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            code TEXT NOT NULL,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            croped_image TEXT default NULL
        )
    ''')

    conn.commit()
    conn.close()


def save_to_db(filename, code, croped_image=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'INSERT INTO cards (filename, code, croped_image) VALUES (?, ?, ?)',
        (filename, code, croped_image)
    )

    conn.commit()
    conn.close()


def view_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT id, filename, code, processed_at, croped_image FROM cards')
    rows = c.fetchall()

    conn.close()

    if not rows:
        print('Banco de dados vazio.')
    else:
        print('\nBanco de Dados:')
        for row in rows:
            print(
                f'ID: {row[0]}, Arquivo: {row[1]}, Código: {row[2]}, '
                f'Processado em: {row[3]}, Crop: {row[4]}'
            )


def export_to_excel():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('SELECT * FROM cards', conn)
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = 'Cartas'

    # Cabeçalhos
    headers = list(df.columns)
    ws.append(headers)

    for idx, row in df.iterrows():
        values = list(row.values)

        # Remove base64 da coluna imagem (temporário)
        if isinstance(values[-1], str) and values[-1].strip():
            values[-1] = ''

        ws.append(values)

    # Inserir imagens
    for idx, row in df.iterrows():
        crop_val = row['croped_image']

        if isinstance(crop_val, str) and crop_val.strip():
            try:
                img_data = base64.b64decode(crop_val)
                img_stream = io.BytesIO(img_data)
                img = XLImage(img_stream)

                cell = f'F{idx + 2}'
                ws.add_image(img, cell)

            except Exception as e:
                print(f'Erro ao inserir imagem do id {row["id"]}: {e}')

    wb.save('cartas_export.xlsx')
    print('Exportação concluída: cartas_export.xlsx (com imagens embutidas)')
