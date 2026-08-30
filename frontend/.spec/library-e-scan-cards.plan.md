# Plano de implementação — `scan-cards` e `library`

Referência: [`library-e-scan-cards.spec.md`](./library-e-scan-cards.spec.md)

Ambiente verificado:
- Frontend: Angular `^21.0.0`, testes com **vitest** (`vi.fn()`), comando `npm test` (`ng test`).
- Backend: Flask + SQLite. **Não há pytest** em `backend/requirements.txt` e não existe nenhum
  `test_*.py` no projeto. Os testes abaixo são scripts `assert` puros, rodados com `python3`.

## Ordem de execução

Três etapas independentes. Fazer nesta ordem — do menor risco para o maior:

| Etapa | O que | Arquivos | Risco |
|---|---|---|---|
| 1 | Badge "Repetidas" com altura fixa | 2 (frontend) | Nenhum, só CSS/HTML |
| 2 | Reset do `anyErrors` por lote | 1 (backend) | Baixo, contrato da API preservado |
| 3 | Paginação da `library` | 6 (backend + frontend) | Alto, muda contrato de `GET /library` |

Etapas 1 e 2 podem ir juntas num PR. A etapa 3 deve ser um PR próprio.

---

# Etapa 1 — Badge "Repetidas" com altura fixa

## 1.1 `frontend/src/app/pages/library/library.html`

**Localizar** (linhas 84-89):
```html
            <span
              *ngIf="card.quantity > 4"
              class="badge text-bg-danger d-inline-flex justify-content-center align-items-center w-100 h-100"
            >
              Repetidas
            </span>
```

**Substituir por:**
```html
            <span
              class="badge text-bg-danger d-flex justify-content-center align-items-center repeat-badge"
              [class.invisible]="card.quantity <= 4"
            >
              Repetidas
            </span>
```

O que mudou e por quê:

- **`h-100` removido** — é a causa raiz. O `.card-body` é `display:flex; flex-direction:column`
  (`library.css:1-5`), então o badge é um flex item de coluna. `height:100%` faz ele pedir a
  altura inteira do container e depois ser encolhido pelo `flex-shrink:1` padrão. Como a altura
  do `.card-body` varia com o título (`h6` de 1 ou 2 linhas), a altura do badge acompanha.
- **`w-100` removido** — desnecessário. Flex item de coluna já estica na horizontal por
  `align-items: stretch` (padrão do flex container).
- **`d-inline-flex` → `d-flex`** — como flex item, `inline-flex` não agrega nada.
- **`*ngIf` → `[class.invisible]`** — `.invisible` do Bootstrap é `visibility:hidden`, que
  **mantém a caixa no layout**. Assim cards repetidos e não repetidos têm a mesma composição
  vertical. Se você preferir não reservar o espaço, mantenha o `*ngIf` — o resto do fix continua
  válido e resolve a variação de altura.
- **`repeat-badge`** — classe própria, porque as regras atuais não pegam (ver 1.2).

## 1.2 `frontend/src/app/pages/library/library.css`

**Adicionar ao final do arquivo:**
```css
.repeat-badge {
  flex: none;
  min-height: 3rem;
  white-space: nowrap;
}
```

`flex: none` (= `flex: 0 0 auto`) é o que realmente blinda o item: sem ele o container continua
livre para encolher/esticar o badge, e qualquer altura definida volta a ser negociável.

**Por que uma classe nova em vez de reaproveitar o que existe:** as regras atuais estão mortas.

```css
/* library.css:7-11 — NÃO se aplica ao badge */
.card-actions .btn,
.card-actions .quantity-box,
.card-actions .badge { min-height: 3rem; }

/* library.css:23-25 — NÃO se aplica ao badge */
.card-actions .badge { white-space: nowrap; }
```

Os dois seletores exigem um ancestral `.card-actions`. No HTML, a `div.card-actions` **fecha na
linha 83** e o `<span>` do badge **abre na 84** — são irmãos, não pai/filho. O `min-height: 3rem`
que deveria estabilizar o componente nunca chegou a valer.

Opcional: remover `.card-actions .badge` das duas regras, já que não casa com nada. Não é
obrigatório e não muda comportamento.

## 1.3 Verificação

Visual, é mudança de layout. Abrir `/library` e comparar na **mesma linha da grade** uma carta de
título curto com uma de título longo, ambas com `quantity > 4`. Os badges devem ter altura idêntica.

Para forçar o cenário sem mexer no banco:
```bash
curl -X POST http://localhost:5000/library/addCard -H 'Content-Type: application/json' -d '{"code":"OP12-095"}'
```
(repetir até `quantity > 4`)

Teste opcional em `frontend/src/app/pages/library/library.spec.ts` — protege contra alguém
reintroduzir o `*ngIf`:
```ts
it('reserva o espaço do badge mesmo quando a carta não é repetida', () => {
  const badge = fixture.nativeElement.querySelector('.repeat-badge');
  expect(badge).toBeTruthy();
  expect(badge.classList.contains('invisible')).toBe(true);
});
```

---

# Etapa 2 — Reset do `anyErrors` por lote

Arquivo único: `backend/processor.py`.

## 2.1 Estado inicial

**Localizar** (linhas 27-32):
```python
processing_status = {
    "total": 0,
    "current": 0,
    "processing": False,
    "anyErrors": False
}
```

**Substituir por:**
```python
processing_status = {
    "total": 0,
    "current": 0,
    "processing": False,
    "anyErrors": False,
    "errorCount": 0,
}
```

`anyErrors` é mantido para não quebrar `processing-bar.html:34`, que já o consome. `errorCount`
é novo e alimenta a mensagem melhorada.

## 2.2 Helper de registro de erro

**Adicionar** logo depois de `get_status()` (após a linha 39):
```python
def _registrar_erro():
    with status_lock:
        processing_status["errorCount"] += 1
        processing_status["anyErrors"] = True
```

Centraliza o registro. Hoje a escrita está inline num só dos dois caminhos de falha, que é
justamente o bug secundário.

## 2.3 `_processar_um_arquivo` — cobrir os dois caminhos de falha

**Localizar** (linhas 43-62):
```python
def _processar_um_arquivo(file_path):
    """Roda o pipeline de detecção pra um arquivo e devolve o LocalCard (ou None em erro)."""
    code, ocr_text, cropped_path = ocr_processor.process_image(file_path)

    if code:
        if card_exists(code):
            card_data = get_card_data_by_code(code)
            return LocalCard(file_path, card_data['image_url'], card_data['card_name'], code, True, cropped_path or "")
        card = get_card_by_code(code)
        if card:
            return LocalCard(file_path, card.card_image, card.card_name, code, False, cropped_path or "")
        _descartar_recorte(cropped_path)
        _mover_para_erro(file_path)
        return None

    _descartar_recorte(cropped_path)
    _mover_para_erro(file_path)
    with status_lock:
        processing_status["anyErrors"] = True
    return None
```

**Substituir por:**
```python
def _processar_um_arquivo(file_path):
    """Roda o pipeline de detecção pra um arquivo e devolve o LocalCard (ou None em erro)."""
    code, ocr_text, cropped_path = ocr_processor.process_image(file_path)

    if code:
        if card_exists(code):
            card_data = get_card_data_by_code(code)
            return LocalCard(file_path, card_data['image_url'], card_data['card_name'], code, True, cropped_path or "")
        card = get_card_by_code(code)
        if card:
            return LocalCard(file_path, card.card_image, card.card_name, code, False, cropped_path or "")
        _descartar_recorte(cropped_path)
        _mover_para_erro(file_path)
        _registrar_erro()
        return None

    _descartar_recorte(cropped_path)
    _mover_para_erro(file_path)
    _registrar_erro()
    return None
```

Duas mudanças:
- A chamada `_registrar_erro()` no **primeiro** caminho de falha (código lido, mas carta não
  existe na API TCG) é **nova**. Hoje esse caminho move o arquivo para `images_with_errors`
  sem sinalizar nada — falha silenciosa.
- No segundo caminho, o bloco `with status_lock` inline vira a chamada da helper.

## 2.4 `start_processing` — resetar nos dois pontos de inicialização

Dentro de `worker()`.

**Localizar** (linhas 75-80):
```python
        if not files:
            with status_lock:
                processing_status["total"] = 0
                processing_status["current"] = 0
                processing_status["processing"] = False            
            return
```

**Substituir por:**
```python
        if not files:
            with status_lock:
                processing_status["total"] = 0
                processing_status["current"] = 0
                processing_status["processing"] = False
                processing_status["anyErrors"] = False
                processing_status["errorCount"] = 0
            return
```

**Localizar** (linhas 82-85):
```python
        with status_lock:
            processing_status["total"] = len(files)
            processing_status["current"] = 0
            processing_status["processing"] = True
```

**Substituir por:**
```python
        with status_lock:
            processing_status["total"] = len(files)
            processing_status["current"] = 0
            processing_status["processing"] = True
            processing_status["anyErrors"] = False
            processing_status["errorCount"] = 0
```

**Atenção ao posicionamento:** o reset precisa acontecer **antes** de qualquer
`executor.submit` (linha 88). Se ficar depois, existe uma janela em que o frontend faz poll
(a cada 1s, `processing.service.ts:29`) e lê a flag suja do lote anterior. Esse é o bug inteiro
— não vale a pena reintroduzi-lo de outro jeito.

## 2.5 `frontend/src/app/pages/processing-bar/processing-bar.html`

**Localizar** (linhas 34-36):
```html
    <div *ngIf="status.anyErrors" class="alert alert-danger mt-2">
      Ocorreu erro durante o processamento
    </div>
```

**Substituir por:**
```html
    <div *ngIf="status.anyErrors" class="alert alert-danger mt-2">
      {{ status.errorCount }} carta(s) não puderam ser processadas neste lote.
    </div>
```

Opcional — link para a tela de erros. Exige adicionar `RouterLink` aos `imports` de
`processing-bar.ts`:
```html
      {{ status.errorCount }} carta(s) não puderam ser processadas neste lote.
      Consulte <a routerLink="/scan-errors">Check Errors</a>.
```
Se não quiser a dependência de rota, ficar só com o texto.

## 2.6 Verificação

Criar `backend/test_processor_status.py`:
```python
import time
import processor


def test_reset_por_lote():
    # simula estado sujo deixado por um lote anterior
    processor.processing_status.update({"anyErrors": True, "errorCount": 3})

    processor.start_processing("pasta_que_nao_existe_ou_vazia")
    time.sleep(0.5)  # start_processing roda numa thread

    status = processor.get_status()
    assert status["anyErrors"] is False, "anyErrors vazou do lote anterior"
    assert status["errorCount"] == 0, "errorCount vazou do lote anterior"


if __name__ == "__main__":
    test_reset_por_lote()
    print("ok")
```

Rodar (a partir de `backend/`, para os imports resolverem):
```bash
cd backend && python3 test_processor_status.py
```

Cuidado: `start_processing` faz `os.listdir(folder_path)`, que levanta `FileNotFoundError`
dentro da thread se a pasta não existir. Use uma pasta **vazia** de verdade:
```bash
mkdir -p /tmp/lote_vazio
```
e passe `/tmp/lote_vazio` no teste.

Teste manual de ponta a ponta — é o que reproduz o bug relatado:
1. Subir o backend, fazer upload de um lote com pelo menos uma imagem ilegível → alerta aparece.
2. Esperar o processamento terminar.
3. Fazer upload de um lote **100% válido**, sem reiniciar o Flask.
4. O alerta **não** deve aparecer. Antes do fix, aparecia.

---

# Etapa 3 — Paginação da `library`

Seis arquivos. Fazer na ordem abaixo: backend primeiro, para o frontend já ter o endpoint pronto.

> **Antes de começar:** aplicar `loading="lazy"` (passo 3.7) sozinho já resolve boa parte do
> sintoma percebido, sem tocar em backend. Vale medir o ganho com ele antes de decidir a
> urgência do resto.

## 3.1 `backend/repositories/cards_repository.py`

**Localizar** (linhas 76-84):
```python
def get_all_cards():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT code,image_url,card_name,quantity,date(processed_at) as processed_at, card_color FROM cards order by processed_at desc')
    cards = c.fetchall()

    conn.close()
    return cards
```

**Substituir por:**
```python
def get_all_cards(color=None, search=None, search_by='code', page=None, page_size=50):
    """Devolve (linhas, total). `total` é a contagem com os filtros aplicados,
    ignorando a paginação — é o que a UI usa para saber quantas páginas existem."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    conditions = []
    params = []

    if color:
        conditions.append('LOWER(card_color) = LOWER(?)')
        params.append(color)

    if search:
        # whitelist: nunca interpolar valor vindo do usuário direto no SQL
        column = 'card_name' if search_by == 'name' else 'code'
        conditions.append(f'{column} LIKE ?')
        params.append(f'%{search}%')

    where = f'WHERE {" AND ".join(conditions)}' if conditions else ''

    c.execute(f'SELECT COUNT(*) FROM cards {where}', params)
    total = c.fetchone()[0]

    sql = (
        'SELECT code, image_url, card_name, quantity, '
        'date(processed_at) as processed_at, card_color '
        f'FROM cards {where} '
        'ORDER BY processed_at DESC, code ASC'
    )
    if page is not None:
        sql += ' LIMIT ? OFFSET ?'
        params = params + [page_size, (page - 1) * page_size]

    c.execute(sql, params)
    cards = c.fetchall()

    conn.close()
    return cards, total
```

Pontos de atenção:

- **`search_by` é whitelist**, não interpolação livre. `'name'` mapeia para `card_name`,
  qualquer outro valor cai em `code`. O termo em si sempre vai como parâmetro `?`.
- **`ORDER BY processed_at DESC, code ASC`** — o `code ASC` é desempate e **não é opcional**.
  `processed_at` é `date(...)`, ou seja, granularidade de dia: várias cartas compartilham o
  mesmo valor. Sem desempate o SQLite não garante ordem estável entre queries, e a mesma carta
  pode aparecer na página 1 e na 2 (ou sumir das duas).
- **Retorno vira tupla** `(cards, total)`. Chamador único verificado:
  `backend/routes/library_routes.py:12`. Confirme com `grep -rn "get_all_cards" backend/`.
- `page=None` mantém o comportamento sem `LIMIT`, caso algum código futuro precise da lista inteira.

## 3.2 `backend/routes/library_routes.py`

**Localizar** (linhas 10-25):
```python
@library_bp.route('/library', methods=['GET'])
def get_library():
    cards = get_all_cards()
    library = [
        {
            "code": card[0],
            "image_url": card[1],
            "card_name": card[2],
            "quantity": card[3],
            "date": card[4],
            "card_color": card[5]
        }
        for card in cards
    ]

    return jsonify(library)
```

**Substituir por:**
```python
@library_bp.route('/library', methods=['GET'])
def get_library():
    color = request.args.get('color')
    search = request.args.get('search')
    search_by = request.args.get('search_by', 'code')

    try:
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(200, max(1, int(request.args.get('page_size', 50))))
    except ValueError:
        return jsonify({'error': 'page e page_size precisam ser inteiros'}), 400

    cards, total = get_all_cards(
        color=color, search=search, search_by=search_by,
        page=page, page_size=page_size,
    )

    items = [
        {
            "code": card[0],
            "image_url": card[1],
            "card_name": card[2],
            "quantity": card[3],
            "date": card[4],
            "card_color": card[5]
        }
        for card in cards
    ]

    return jsonify({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })
```

Pontos de atenção:

- **`int()` sem guarda derruba a request com 500** se alguém mandar `?page=abc`. O `try/except`
  devolve 400, que é a resposta correta. `page` e `page_size` vêm da URL: é fronteira de
  confiança, valida.
- **`page_size` limitado a 200** — sem teto, `?page_size=999999` anula a paginação inteira.
- **Mudança de contrato:** a resposta deixa de ser um array e vira um objeto. Consumidor único
  verificado: `library.service.ts:13` → `library.ts:30`. Nada mais no frontend chama `/library`.
- **`GET /library/colors` fica como está.** Ele precisa listar as cores da biblioteca inteira,
  não as da página atual — senão o dropdown encolhe conforme o usuário navega.

## 3.3 `frontend/src/app/services/library.service.ts`

**Localizar** (linhas 1-15):
```ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, interval, Observable, Subscription } from 'rxjs';
import { LibraryCard } from '../interfaces/LibraryCard';
import { API_BASE_URL } from './api-url';

@Injectable({
  providedIn: 'root',
})
export class LibraryService {
  private apiUrl = `${API_BASE_URL}/library`;
  constructor(private http: HttpClient) {}
  getLibrary(): Observable<LibraryCard[]> {
    return this.http.get<LibraryCard[]>(this.apiUrl);
  }
```

**Substituir por:**
```ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { LibraryCard } from '../interfaces/LibraryCard';
import { API_BASE_URL } from './api-url';

export const LIBRARY_PAGE_SIZE = 50;

export interface LibraryPage {
  items: LibraryCard[];
  total: number;
  page: number;
  page_size: number;
}

export interface LibraryQuery {
  color?: string;
  search?: string;
  searchBy?: string;
  page?: number;
  pageSize?: number;
}

@Injectable({
  providedIn: 'root',
})
export class LibraryService {
  private apiUrl = `${API_BASE_URL}/library`;
  constructor(private http: HttpClient) {}

  getLibrary(query: LibraryQuery = {}): Observable<LibraryPage> {
    let params = new HttpParams()
      .set('page', String(query.page ?? 1))
      .set('page_size', String(query.pageSize ?? LIBRARY_PAGE_SIZE));

    if (query.color) {
      params = params.set('color', query.color);
    }
    if (query.search) {
      params = params
        .set('search', query.search)
        .set('search_by', query.searchBy ?? 'code');
    }

    return this.http.get<LibraryPage>(this.apiUrl, { params });
  }
```

Notas:
- Estrutura espelha `InventoryItemsPage`/`InventoryItemsQuery` em `services/inventory.service.ts:10-23`.
  Mesmo padrão, mesmo lugar (interface no próprio service, não em `interfaces/`) — é o que já se faz aqui.
- `BehaviorSubject`, `interval` e `Subscription` estavam importados e **não eram usados**.
  Aproveite e remova.
- `HttpParams` é imutável: `params.set(...)` devolve uma instância nova. O `params = params.set(...)`
  não é redundância, é obrigatório.
- O resto do service (`getCardColors`, `getScanErrors`, `saveCardManually`, `addCardQuantity`,
  `removeCardQuantity`) fica intocado.

## 3.4 `frontend/src/app/pages/library/library.ts`

Reescrita do construtor. **Substituir o arquivo inteiro por:**

```ts
import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LibraryService, LibraryPage, LIBRARY_PAGE_SIZE } from '../../services/library.service';
import { catchError, combineLatest, Observable, of, startWith, Subject, BehaviorSubject, switchMap, tap } from 'rxjs';

const EMPTY_PAGE: LibraryPage = { items: [], total: 0, page: 1, page_size: LIBRARY_PAGE_SIZE };

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './library.html',
  styleUrl: './library.css',
})
export class Library {
  libraryState$!: Observable<LibraryPage>;
  cardColors$!: Observable<string[]>;
  searchBy = 'code';
  searchTerm = '';
  selectedColor = '';
  page = 1;
  total = 0;
  readonly pageSize = LIBRARY_PAGE_SIZE;

  private refresh$ = new Subject<void>();
  private searchBy$ = new BehaviorSubject<string>(this.searchBy);
  private searchTerm$ = new BehaviorSubject<string>(this.searchTerm);
  private selectedColor$ = new BehaviorSubject<string>(this.selectedColor);
  private page$ = new BehaviorSubject<number>(this.page);

  constructor(private libraryService: LibraryService) {
    this.libraryState$ = combineLatest([
      this.refresh$.pipe(startWith(void 0)),
      this.searchBy$,
      this.searchTerm$,
      this.selectedColor$,
      this.page$,
    ]).pipe(
      switchMap(([, searchBy, searchTerm, color, page]) =>
        this.libraryService
          .getLibrary({ searchBy, search: searchTerm, color, page })
          .pipe(
            catchError((err) => {
              console.error('Erro ao carregar biblioteca', err);
              return of(EMPTY_PAGE);
            })
          )
      ),
      tap((result) => (this.total = result.total))
    );

    this.cardColors$ = this.refresh$.pipe(
      startWith(void 0),
      switchMap(() =>
        this.libraryService.getCardColors().pipe(
          catchError((err) => {
            console.error('Erro ao carregar cores da biblioteca', err);
            return of([]);
          })
        )
      )
    );
  }

  search() {
    this.goToPage(1);
    this.searchBy$.next(this.searchBy);
    this.searchTerm$.next(this.searchTerm);
  }

  onColorChange(color: string) {
    this.selectedColor = color;
    this.goToPage(1);
    this.selectedColor$.next(this.selectedColor);
  }

  get hasNextPage(): boolean {
    return this.page * this.pageSize < this.total;
  }

  nextPage() {
    if (!this.hasNextPage) return;
    this.goToPage(this.page + 1);
  }

  prevPage() {
    if (this.page <= 1) return;
    this.goToPage(this.page - 1);
  }

  private goToPage(page: number) {
    if (this.page === page) return;
    this.page = page;
    this.page$.next(page);
  }

  addCard(code: string) {
    this.libraryService.addCardQuantity(code).subscribe({
      next: () => this.refresh$.next(),
      error: (err) => console.error('Erro ao adicionar carta', err),
    });
  }

  removeCard(code: string) {
    this.libraryService.removeCardQuantity(code).subscribe({
      next: () => this.refresh$.next(),
      error: (err) => console.error('Erro ao remover carta', err),
    });
  }
}
```

O que mudou, item a item:

- **O bloco de filtro client-side sumiu.** As antigas linhas 51-74 (`map` com
  `filteredCards.filter(...)`) não existem mais — quem filtra agora é o SQL. Manter aquele
  `map` seria a pior das hipóteses: filtraria só a página atual e o usuário acharia que a carta
  não existe na biblioteca.
- **`page$` entra no `combineLatest`**, então trocar de página refaz a request. Como o operador é
  `switchMap`, cliques rápidos em "Próxima" cancelam a request anterior automaticamente — sem
  race condition de resposta fora de ordem.
- **`search()` e `onColorChange()` resetam para a página 1** via `goToPage(1)`. Sem isso o usuário
  na página 7 aplica um filtro que devolve 20 resultados e vê uma tela vazia. Mesma regra usada em
  `inventory-audit.ts:144,179,185`.
- **`goToPage` tem guarda `if (this.page === page) return`** — evita que `search()` na página 1
  dispare uma emissão redundante no `page$` (o `combineLatest` já vai emitir por causa do
  `searchTerm$`), o que geraria duas requests para a mesma busca.
- **`addCard`/`removeCard` NÃO resetam a página.** Disparam só `refresh$`, que recarrega a página
  atual. O usuário está ajustando a quantidade de uma carta que está vendo; jogá-lo de volta para
  o começo da lista seria hostil.
- **`tap` guarda `total`** para o template usar nos controles de paginação. Alternativa sem `tap`:
  ler `state.total` direto no HTML, já que o `async` expõe o objeto inteiro — nesse caso remova o
  campo `total` e o `tap`, e ajuste `hasNextPage` para receber o total como argumento.
- `map` sai dos imports do rxjs; `tap` entra.

## 3.5 `frontend/src/app/pages/library/library.html` — container

**Localizar** (linha 5):
```html
  <ng-container *ngIf="libraryState$ | async as cards">
```
**Substituir por:**
```html
  <ng-container *ngIf="libraryState$ | async as state">
```

**Localizar** (linha 7) — remover, é código morto:
```html
    <div *ngIf="cards === null" class="text-center mt-4">Carregando biblioteca...</div>
```

Motivo: essa div está dentro de `*ngIf="... | async as cards"`. O `as` só entra no bloco quando o
valor é **truthy**, então `cards === null` nunca é verdadeiro ali dentro. A div nunca renderizou.

Se quiser um loading state de verdade, ele tem que ficar **fora** do `ng-container`:
```html
  <div *ngIf="!(libraryState$ | async)" class="text-center mt-4">Carregando biblioteca...</div>
```

## 3.6 `frontend/src/app/pages/library/library.html` — grade

**Localizar** (linhas 50-55):
```html
    <div
      *ngIf="cards !== null"
      class="row row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-5 g-4"
    >
      <p *ngIf="cards.length === 0" class="text-center w-100">Nenhuma carta na biblioteca.</p>
      <div class="col" *ngFor="let card of cards">
```

**Substituir por:**
```html
    <div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-5 g-4">
      <p *ngIf="state.items.length === 0" class="text-center w-100">
        {{ searchTerm || selectedColor
            ? 'Nenhuma carta encontrada para este filtro.'
            : 'Nenhuma carta na biblioteca.' }}
      </p>
      <div class="col" *ngFor="let card of state.items; trackBy: trackByCode">
```

- `*ngIf="cards !== null"` sai — sempre foi verdadeiro dentro do `as`.
- A mensagem de vazio passa a distinguir "biblioteca vazia" de "filtro sem resultado". São
  situações diferentes e a mensagem atual mente na segunda.
- `trackBy` evita que o Angular destrua e recrie as 50 `<img>` a cada `refresh$` (que dispara em
  todo add/remove). Sem ele, cada clique no `+` reconstrói a página inteira e as imagens piscam.
  Adicionar em `library.ts`:
  ```ts
  trackByCode(_: number, card: LibraryCard) {
    return card.code;
  }
  ```
  (importar `LibraryCard` de `../../interfaces/LibraryCard`)

## 3.7 `frontend/src/app/pages/library/library.html` — imagem

**Localizar** (linha 57):
```html
          <img [src]="card.image_url" class="card-img-top" [alt]="card.card_name" />
```

**Substituir por:**
```html
          <img
            [src]="card.image_url"
            class="card-img-top"
            [alt]="card.card_name"
            loading="lazy"
            decoding="async"
          />
```

**Este é o passo de maior retorno por linha do plano.** O gargalo medido não é o payload
(689 cartas ≈ 140 KB de JSON) — são as 689 `<img>` apontando para `optcgapi.com`. O navegador
limita a ~6 conexões simultâneas por host, então a página faz ~115 rodadas sequenciais de
download contra um CDN de terceiros. `loading="lazy"` faz o browser só baixar o que entra na
viewport; `decoding="async"` tira a decodificação da thread principal.

Vale aplicar mesmo que a paginação seja adiada.

## 3.8 `frontend/src/app/pages/library/library.html` — controles de paginação

**Adicionar** logo após o fechamento da div da grade (atual linha 93), ainda dentro do
`ng-container`:

```html
    <div class="d-flex justify-content-center align-items-center gap-3 my-4">
      <button
        type="button"
        class="btn btn-outline-secondary"
        [disabled]="page <= 1"
        (click)="prevPage()"
      >
        Anterior
      </button>
      <span>Página {{ page }} ({{ state.total }} carta(s) no total)</span>
      <button
        type="button"
        class="btn btn-outline-secondary"
        [disabled]="!hasNextPage"
        (click)="nextPage()"
      >
        Próxima
      </button>
    </div>
```

Mesmo formato de `inventory-audit.html:127-129`, para as duas telas ficarem consistentes.

## 3.9 Testes

### `frontend/src/app/pages/library/library.spec.ts` — **o teste atual vai quebrar**

O teste existente (linhas 31-40) valida a filtragem **client-side**, que deixa de existir:
```ts
  it('should filter cards by selected color', () => {
    component.onColorChange('Blue');
    let result: any[] = [];
    component.libraryState$.subscribe((cards) => { result = cards; });
    expect(result.map((card) => card.code)).toEqual(['AAA']);
  });
```

Ele precisa ser **reescrito**, não corrigido: a responsabilidade migrou para o backend. O que faz
sentido testar agora é que o componente **repassa o filtro para o service** e **reseta a página**.

**Substituir o arquivo por:**
```ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { Library } from './library';
import { LibraryService } from '../../services/library.service';

describe('Library', () => {
  let fixture: ComponentFixture<Library>;
  let component: Library;
  let getLibrary: any;

  beforeEach(async () => {
    getLibrary = vi.fn().mockReturnValue(
      of({
        items: [{ code: 'AAA', image_url: '', card_name: 'Alpha', quantity: 1, card_color: 'Blue' }],
        total: 1,
        page: 1,
        page_size: 50,
      } as any)
    );

    const libraryServiceSpy = {
      getLibrary,
      getCardColors: vi.fn().mockReturnValue(of(['Blue', 'Black'])),
      addCardQuantity: vi.fn().mockReturnValue(of({})),
      removeCardQuantity: vi.fn().mockReturnValue(of({})),
    };

    await TestBed.configureTestingModule({
      imports: [Library],
      providers: [{ provide: LibraryService, useValue: libraryServiceSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(Library);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('repassa o filtro de cor para o backend', () => {
    component.onColorChange('Blue');
    fixture.detectChanges();

    expect(getLibrary).toHaveBeenCalledWith(
      expect.objectContaining({ color: 'Blue' })
    );
  });

  it('volta para a página 1 ao aplicar um filtro', () => {
    component.nextPage = () => { (component as any).page = 3; (component as any).page$.next(3); };
    (component as any).page = 3;
    (component as any).page$.next(3);
    fixture.detectChanges();

    component.searchTerm = 'luffy';
    component.search();
    fixture.detectChanges();

    expect(getLibrary).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 1, search: 'luffy' })
    );
  });
});
```

O segundo teste é o que importa: cobre exatamente a regressão mais provável desta etapa
(filtrar estando numa página alta e cair numa tela vazia).

Rodar:
```bash
cd frontend && npm test
```

### `backend/test_library_pagination.py`

```python
from repositories.cards_repository import get_all_cards


def test_pagina_respeita_o_limite():
    cards, total = get_all_cards(page=1, page_size=10)
    assert len(cards) <= 10
    assert total >= len(cards)


def test_filtro_considera_biblioteca_inteira():
    _, total_geral = get_all_cards(page=1, page_size=10)
    cards, total_filtrado = get_all_cards(color='Red', page=1, page_size=10)
    assert total_filtrado <= total_geral
    assert all((c[5] or '').lower() == 'red' for c in cards)


def test_paginas_nao_repetem_carta():
    p1, _ = get_all_cards(page=1, page_size=10)
    p2, _ = get_all_cards(page=2, page_size=10)
    assert not ({c[0] for c in p1} & {c[0] for c in p2}), "carta apareceu em duas páginas"


def test_busca_por_nome_usa_a_coluna_certa():
    cards, _ = get_all_cards(search='Luffy', search_by='name', page=1, page_size=50)
    assert all('luffy' in (c[2] or '').lower() for c in cards)


if __name__ == "__main__":
    test_pagina_respeita_o_limite()
    test_filtro_considera_biblioteca_inteira()
    test_paginas_nao_repetem_carta()
    test_busca_por_nome_usa_a_coluna_certa()
    print("ok")
```

`test_paginas_nao_repetem_carta` é o que justifica o `ORDER BY ... , code ASC`. Sem o desempate,
ele falha de forma intermitente — que é o pior tipo de bug de paginação.

Rodar:
```bash
cd backend && python3 test_library_pagination.py
```

Ajuste `'Red'` e `'Luffy'` para valores que existam no `db.sqlite` local:
```bash
cd backend && python3 -c "
import sqlite3; c = sqlite3.connect('db.sqlite')
print(c.execute('select distinct card_color from cards limit 10').fetchall())
print(c.execute('select card_name from cards limit 5').fetchall())
"
```

## 3.10 Checklist de aceite da etapa 3

- [ ] `GET /library` devolve no máximo `page_size` cartas (default 50).
- [ ] `GET /library?page=abc` responde 400, não 500.
- [ ] `GET /library?page_size=999999` é limitado a 200.
- [ ] Busca e filtro de cor consideram a biblioteca inteira, não só a página exibida.
- [ ] Trocar filtro ou termo de busca volta para a página 1.
- [ ] Adicionar/remover quantidade mantém o usuário na página atual.
- [ ] Total de cartas aparece junto aos controles de paginação.
- [ ] Anterior/Próxima desabilitados nos limites.
- [ ] Imagens com `loading="lazy"`.
- [ ] Dropdown de cores lista todas as cores da biblioteca, não só as da página.
- [ ] Nenhuma carta aparece em duas páginas.
- [ ] `npm test` e os dois scripts `python3` passam.

---

# Resumo dos arquivos tocados

| Arquivo | Etapa | Natureza |
|---|---|---|
| `frontend/src/app/pages/library/library.html` | 1, 3 | Badge, container, grade, imagem, paginação |
| `frontend/src/app/pages/library/library.css` | 1 | Classe `.repeat-badge` |
| `backend/processor.py` | 2 | Reset de `anyErrors`, helper `_registrar_erro` |
| `frontend/src/app/pages/processing-bar/processing-bar.html` | 2 | Mensagem com contador |
| `backend/repositories/cards_repository.py` | 3 | `get_all_cards` paginado |
| `backend/routes/library_routes.py` | 3 | Query params + envelope de resposta |
| `frontend/src/app/services/library.service.ts` | 3 | `LibraryPage`, `LibraryQuery`, `HttpParams` |
| `frontend/src/app/pages/library/library.ts` | 3 | Filtro server-side, estado de página |
| `frontend/src/app/pages/library/library.spec.ts` | 3 | Teste reescrito (o atual quebra) |
| `backend/test_processor_status.py` | 2 | Novo |
| `backend/test_library_pagination.py` | 3 | Novo |
