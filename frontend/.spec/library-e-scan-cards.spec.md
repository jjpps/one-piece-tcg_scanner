# Spec: Correções e melhorias — `scan-cards` e `library`

Duas frentes independentes, agrupadas a pedido. Podem virar dois PRs separados sem
nenhum acoplamento entre elas.

- **Parte 1** — bug: label de erro persistente em `scan-cards` (backend, ~6 linhas).
- **Parte 2** — feature: paginação na `library` (backend + frontend).

---

# Parte 1 — Label de erro persistente na tela `scan-cards`

## Sintoma reportado
Na página `scan-cards`, o alerta **"Ocorreu erro durante o processamento"** aparece e nunca mais some — mesmo quando as cartas seguintes são processadas com sucesso, e mesmo em uploads novos feitos depois.

## Análise do comportamento

### Fluxo real (ponta a ponta)
1. `upload-cards.ts:40` → `POST /upload` envia os arquivos.
2. `upload_routes.py:43` → `processor.start_processing(IMAGES_FOLDER)` dispara uma thread que processa **a pasta inteira em paralelo** (`ThreadPoolExecutor`, `PROCESS_WORKERS`).
3. `upload-cards.ts:45` → `processingService.startPolling()` faz `GET /status` a cada 1s (`processing.service.ts:29`).
4. `processor_routes.py:9` → devolve `get_status()`, uma cópia do dict global `processing_status`.
5. `processing-bar.html:34` → `*ngIf="status.anyErrors"` renderiza o alerta.

### Causa raiz
`backend/processor.py:27-32` — `processing_status` é um **dict global de módulo**, e `anyErrors` é uma flag *sticky*:

```python
processing_status = {
    "total": 0,
    "current": 0,
    "processing": False,
    "anyErrors": False        # ← setado em processor.py:61, nunca resetado
}
```

`start_processing` reinicializa `total`, `current` e `processing` (linhas 76-85), mas **não reinicializa `anyErrors`**. Uma vez que qualquer imagem falha, a flag fica `True` pelo resto da vida do processo Flask. Todos os uploads seguintes — inclusive os 100% bem-sucedidos — chegam ao frontend com `anyErrors: true`.

O frontend está correto: ele só espelha o que a API manda. **Nenhuma correção é necessária em `processing-bar.ts`/`.html` para resolver o sintoma principal.**

### Bug secundário encontrado na mesma função
`processor.py:47-56` — quando o OCR **lê** um código mas a carta não existe na API TCG, o arquivo é movido para `images_with_errors` (linha 55) mas **`anyErrors` não é setado**. Ou seja: existe um caminho de erro silencioso. Os dois caminhos de falha devem contabilizar erro de forma consistente.

### Por que o alerta some ao final do processamento
O `*ngIf="status.anyErrors"` está aninhado dentro de `*ngIf="status.processing"` (`processing-bar.html:4`). Enquanto `processing` é `false` a barra inteira some — inclusive o alerta. Por isso o sintoma só é visível **durante** o processamento seguinte, o que reforça a leitura de "nunca some".

## Comportamento esperado
O alerta de erro deve refletir **apenas a execução de processamento corrente**. Um lote novo começa sempre limpo.

| Sequência | Resultado | Label |
|---|---|---|
| Card 1 | sucesso | não aparece |
| Card 2 | sucesso | não aparece |
| Card 3 | falha | aparece |
| Card 4 | sucesso | continua aparecendo (o lote teve 1 erro) |
| **Novo upload**, todos sucesso | — | **não aparece** |

> **Nota sobre granularidade.** O exemplo do chamado sugere um label estritamente por-carta (aparece no card 3, some no card 4). Isso **não é implementável de forma útil** na arquitetura atual: as cartas são processadas concorrentemente por um pool de threads e o frontend só faz poll a cada 1s — um label por-carta piscaria de forma imprevisível e frequentemente nem seria visto. O escopo desta spec é o **reset por lote**, que é o bug real. O contador de erros (abaixo) dá ao usuário a informação de "quantas falharam" sem depender de timing.

## Escopo
- `backend/processor.py` (correção principal)
- `frontend/src/app/pages/processing-bar/processing-bar.html` (melhoria de mensagem)
- Teste: `backend/test_processor_status.py` (novo)

## Alterações necessárias

### 1. `backend/processor.py` — resetar o estado de erro a cada lote

Trocar a flag booleana por um contador (`errorCount`), mantendo `anyErrors` derivado para não quebrar o contrato atual da API.

**a)** Estado inicial (linhas 27-32):
```python
processing_status = {
    "total": 0,
    "current": 0,
    "processing": False,
    "anyErrors": False,
    "errorCount": 0,
}
```

**b)** Nova helper, usada pelos dois caminhos de falha:
```python
def _registrar_erro():
    with status_lock:
        processing_status["errorCount"] += 1
        processing_status["anyErrors"] = True
```

**c)** `_processar_um_arquivo` (linhas 43-62) — chamar `_registrar_erro()` nos **dois** returns `None`:
- linha 54-56 (código lido, carta não encontrada na API) → **adicionar** a chamada (bug secundário);
- linha 58-62 (nenhum código lido) → substituir o bloco `with status_lock` inline pela helper.

**d)** `start_processing` → `worker()` — resetar junto com os outros campos, nos **dois** blocos de inicialização:
- linhas 76-79 (early return, pasta vazia): adicionar `anyErrors = False` e `errorCount = 0`;
- linhas 82-85 (início do lote): adicionar `anyErrors = False` e `errorCount = 0`.

O reset **precisa** acontecer antes de qualquer `executor.submit`, para não haver janela em que o frontend faça poll e leia a flag do lote anterior.

### 2. `frontend/src/app/pages/processing-bar/processing-bar.html` — mensagem informativa

Linhas 34-36:
```html
<div *ngIf="status.anyErrors" class="alert alert-danger mt-2">
  {{ status.errorCount }} carta(s) não puderam ser processadas neste lote.
  Consulte <a routerLink="/scan-errors">Check Errors</a>.
</div>
```
Requer `RouterLink` nos `imports` de `processing-bar.ts`. Se preferir evitar a dependência de rota, manter só o texto com o contador.

## Critérios de aceitação
1. Após um lote com falha, um novo upload 100% bem-sucedido **não** exibe o alerta.
2. Um lote com ao menos uma falha exibe o alerta enquanto `processing` for `true`.
3. O alerta informa a quantidade de cartas que falharam no lote corrente.
4. Uma carta cujo código foi lido mas não existe na API TCG passa a contar como erro (hoje é silenciosa).
5. `GET /status` continua devolvendo `anyErrors` (compatibilidade), agora acompanhado de `errorCount`.
6. Reiniciar o backend não é mais necessário para "limpar" o alerta.

## Verificação
Um teste `backend/test_processor_status.py` baseado em `assert`, sem framework:

```python
import processor

def test_reset_por_lote():
    processor.processing_status.update({"anyErrors": True, "errorCount": 3})
    processor.start_processing("pasta_inexistente_ou_vazia")   # early return path
    # aguardar a thread terminar
    assert processor.get_status()["anyErrors"] is False
    assert processor.get_status()["errorCount"] == 0
```

Cobre exatamente a regressão: estado sujo do lote anterior sobrevivendo ao lote novo.

## Fora de escopo
- Erro por-carta em tempo real (exigiria stream/SSE ou um id de lote no status).
- Isolamento multiusuário: `processing_status` é global ao processo, então dois usuários simultâneos compartilham o mesmo estado. É um problema real, mas pré-existente e independente deste bug.

---

# Parte 2 — Paginação na tela `library`

## Sintoma reportado
A página `library` está demorando cada vez mais para carregar conforme a quantidade de cartas cresce.

## Análise do comportamento

### Fluxo real
1. `library.ts:30` → `getLibrary()` → `GET /library`.
2. `library_routes.py:12` → `get_all_cards()`.
3. `cards_repository.py:80` → `SELECT ... FROM cards ORDER BY processed_at DESC` — **sem `LIMIT`**, devolve a tabela inteira.
4. `library.ts:51-74` → filtro de cor e busca aplicados **no cliente**, sobre o array completo.
5. `library.html:55` → `*ngFor` renderiza **um card por linha da tabela**, cada um com um `<img>`.

### Medição no banco atual
```
cards: 689 linhas
avg(length(image_url)): ~67 bytes
```
O JSON de `/library` dá algo em torno de **140 KB**. Isso não é lento.

### Causa raiz do "demora para carregar"
Não é o payload nem a query — é a **renderização**. As 689 `<img>` apontam para um CDN externo:

```
https://www.optcgapi.com/media/static/Card_Images/OP12-095_o52Jkiu.jpg
```

O navegador dispara 689 requisições cross-origin de uma vez, limitadas a ~6 conexões
simultâneas por host. A página só "termina" depois de ~115 rodadas sequenciais de download,
todas contra um servidor de terceiros. O tempo de resposta cresce linearmente com o
tamanho da biblioteca e **não está sob nosso controle**.

Ou seja: o gargalo é o número de imagens renderizadas por vez. Paginar resolve o problema
certo. A query sem `LIMIT` é uma dívida real também, mas nesta escala ainda não é o que dói.

### Ganho barato antes da paginação
`library.html:57` não usa lazy loading. Adicionar o atributo nativo:
```html
<img [src]="card.image_url" loading="lazy" decoding="async" ... />
```
Um atributo faz o navegador só baixar as imagens que entram na viewport. Isso sozinho
resolve a maior parte do sintoma percebido, sem tocar em backend. **Deve entrar de qualquer
forma**, com ou sem paginação — as duas coisas se somam.

### Pegadinha que a paginação introduz
Hoje o filtro de cor e a busca rodam no cliente (`library.ts:51-74`), sobre o array completo.
Se paginarmos o backend sem mover os filtros para lá, a busca passa a filtrar **apenas a
página atual** — uma regressão funcional silenciosa e pior que o problema original.
**Os filtros têm que ir para o SQL junto com a paginação.** Não é opcional.

### Padrão já existente no repositório
`inventory` já resolve exatamente isso e deve ser copiado, não reinventado:

| Camada | Arquivo existente |
|---|---|
| Repository (WHERE dinâmico + COUNT + LIMIT/OFFSET) | `repositories/inventory_repository.py:124` `get_session_items` |
| Route (lê `page`/`page_size` de query params) | `routes/inventory_routes.py:48-59` |
| Service Angular (`HttpParams`) | `services/inventory.service.ts:44` `getItems` |
| Componente (`page` signal, `nextPage`/`prevPage`) | `pages/inventory-audit/inventory-audit.ts:190-203` |
| UI de paginação | `pages/inventory-audit/inventory-audit.html:127-129` |

## Escopo
- `backend/repositories/cards_repository.py`
- `backend/routes/library_routes.py`
- `frontend/src/app/services/library.service.ts`
- `frontend/src/app/pages/library/library.ts`
- `frontend/src/app/pages/library/library.html`
- `frontend/src/app/pages/library/library.spec.ts`

## Alterações necessárias

### 1. `backend/repositories/cards_repository.py` — `get_all_cards` paginado

Assinatura nova, com defaults que preservam o comportamento atual para qualquer outro chamador:

```python
def get_all_cards(color=None, search=None, search_by='code', page=None, page_size=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    conditions = []
    params = []

    if color:
        conditions.append('LOWER(card_color) = LOWER(?)')
        params.append(color)

    if search:
        column = 'card_name' if search_by == 'name' else 'code'
        conditions.append(f'{column} LIKE ?')
        params.append(f'%{search}%')

    where = f'WHERE {" AND ".join(conditions)}' if conditions else ''

    c.execute(f'SELECT COUNT(*) FROM cards {where}', params)
    total = c.fetchone()[0]

    sql = (f'SELECT code, image_url, card_name, quantity, '
           f'date(processed_at) as processed_at, card_color '
           f'FROM cards {where} ORDER BY processed_at DESC')
    if page is not None:
        sql += ' LIMIT ? OFFSET ?'
        params = params + [page_size, (page - 1) * page_size]

    c.execute(sql, params)
    cards = c.fetchall()
    conn.close()
    return cards, total
```

Notas:
- `search_by` é whitelist (`'name'` → `card_name`, qualquer outra coisa → `code`). Nunca interpolar
  o valor do usuário direto no SQL.
- `ORDER BY processed_at DESC` sem desempate torna a paginação instável quando várias cartas
  têm a mesma data. Usar `ORDER BY processed_at DESC, code ASC` para tornar a ordem determinística —
  senão a mesma carta pode aparecer em duas páginas.
- Chamador único verificado: só `library_routes.py:12` usa `get_all_cards`. Mudar o retorno para
  tupla `(cards, total)` é seguro.

### 2. `backend/routes/library_routes.py` — expor os parâmetros

```python
@library_bp.route('/library', methods=['GET'])
def get_library():
    color = request.args.get('color')
    search = request.args.get('search')
    search_by = request.args.get('search_by', 'code')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 50))

    cards, total = get_all_cards(color=color, search=search, search_by=search_by,
                                 page=page, page_size=page_size)
    items = [
        {"code": c[0], "image_url": c[1], "card_name": c[2],
         "quantity": c[3], "date": c[4], "card_color": c[5]}
        for c in cards
    ]
    return jsonify({"items": items, "total": total, "page": page, "page_size": page_size})
```

**Breaking change:** a resposta deixa de ser um array e passa a ser um objeto. `/library` só é
consumido por `library.service.ts:13` → `library.ts:30`, verificado. Blast radius = o componente
`library` apenas.

`GET /library/colors` continua como está: precisa listar as cores da biblioteca **inteira**,
não da página.

### 3. `frontend/src/app/services/library.service.ts`

```ts
getLibrary(query: LibraryQuery = {}): Observable<LibraryPage> {
  let params = new HttpParams()
    .set('page', String(query.page ?? 1))
    .set('page_size', String(query.pageSize ?? PAGE_SIZE));
  if (query.color) params = params.set('color', query.color);
  if (query.search) {
    params = params.set('search', query.search).set('search_by', query.searchBy ?? 'code');
  }
  return this.http.get<LibraryPage>(this.apiUrl, { params });
}
```

Nova interface em `src/app/interfaces/` (espelhando `InventoryItemsPage`):
```ts
export interface LibraryPage {
  items: LibraryCard[];
  total: number;
  page: number;
  page_size: number;
}
```

### 4. `frontend/src/app/pages/library/library.ts`

Remover o bloco de filtro client-side (`library.ts:51-74`) — o `combineLatest` com `map` de
filtro deixa de existir, porque quem filtra agora é o SQL.

Manter o pipeline reativo com `switchMap`, adicionando `page$` às dependências:
```ts
this.libraryState$ = combineLatest([
  this.refresh$.pipe(startWith(void 0)),
  this.searchBy$, this.searchTerm$, this.selectedColor$, this.page$,
]).pipe(
  switchMap(([, searchBy, searchTerm, color, page]) =>
    this.libraryService.getLibrary({ searchBy, search: searchTerm, color, page })
      .pipe(catchError(err => {
        console.error('Erro ao carregar biblioteca', err);
        return of({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
      }))
  )
);
```

Regras de estado:
- `search()` e `onColorChange()` devem **resetar `page` para 1** antes de emitir. Sem isso o
  usuário filtra e cai numa página vazia (mesma regra de `inventory-audit.ts:144,179,185`).
- `addCard()`/`removeCard()` disparam `refresh$` e devem **manter a página atual** — o usuário
  está mexendo na quantidade de uma carta visível, não quer voltar para o começo.
- Métodos `nextPage()`/`prevPage()` copiados de `inventory-audit.ts:190-203`.

### 5. `frontend/src/app/pages/library/library.html`

- `library.html:5` → `*ngIf="libraryState$ | async as state"`, e o `*ngFor` passa a iterar `state.items`.
- `library.html:57` → adicionar `loading="lazy" decoding="async"` no `<img>`.
- `library.html:54` → mensagem de vazio: distinguir "biblioteca vazia" de "nenhum resultado para
  o filtro", usando `state.total`.
- Adicionar os controles de paginação no rodapé da grade, no mesmo formato de
  `inventory-audit.html:127-129`.
- **Bug morto encontrado:** `library.html:7` tem `*ngIf="cards === null"` como estado de loading,
  mas está dentro de `*ngIf="... | async as cards"` — o `as` só entra quando o valor é truthy,
  então essa div **nunca** renderiza. Ou remover, ou trocar por um `*ngIf="!state"` no nível de fora.

## Critérios de aceitação
1. `GET /library` devolve no máximo `page_size` cartas (default 50).
2. A busca por código/nome e o filtro de cor consideram a **biblioteca inteira**, não apenas a
   página exibida.
3. Trocar filtro ou termo de busca volta para a página 1.
4. Adicionar/remover quantidade de uma carta mantém o usuário na página em que estava.
5. O total de cartas do resultado é exibido junto aos controles de paginação.
6. Os botões Anterior/Próxima ficam desabilitados nos limites.
7. Imagens usam `loading="lazy"`.
8. O dropdown de cores continua listando todas as cores da biblioteca, não só as da página.
9. Nenhuma carta aparece em duas páginas diferentes (ordenação determinística).

## Verificação
Backend — um teste `assert` cobrindo a regressão que importa (filtro atravessa a paginação):
```python
def test_filtro_considera_biblioteca_inteira():
    _, total_sem_filtro = get_all_cards(page=1, page_size=10)
    pagina, total_filtrado = get_all_cards(color='Red', page=1, page_size=10)
    assert len(pagina) <= 10
    assert total_filtrado <= total_sem_filtro
    assert all((c[5] or '').lower() == 'red' for c in pagina)

def test_paginas_nao_repetem_carta():
    p1, _ = get_all_cards(page=1, page_size=10)
    p2, _ = get_all_cards(page=2, page_size=10)
    assert not ({c[0] for c in p1} & {c[0] for c in p2})
```

Frontend — estender `library.spec.ts` com um caso: aplicar filtro estando na página 3 e
verificar que a requisição sai com `page=1`.

## Fora de escopo
- Scroll infinito. Paginação numerada é menos código e resolve o problema; trocar depois se a UX pedir.
- Cache/proxy local das imagens do `optcgapi.com`. É a correção definitiva para o custo de rede,
  mas exige storage e invalidação — vale abrir separado se `loading="lazy"` + paginação não bastarem.
- Índices no SQLite. Com 689 linhas o full scan é irrelevante; revisitar se passar de ~50k cartas.

---

# Parte 3 — Badge "Repetidas" com altura variável na `library`

## Sintoma reportado
Na tela `library`, o badge vermelho **"Repetidas"** muda de tamanho conforme o comprimento do
título da carta. Deveria ocupar sempre o mesmo espaço.

## Análise do comportamento

### Estrutura relevante
`library.html:84-89`:
```html
<span
  *ngIf="card.quantity > 4"
  class="badge text-bg-danger d-inline-flex justify-content-center align-items-center w-100 h-100"
>
  Repetidas
</span>
```

`library.css:1-5`:
```css
.card-body { display: flex; flex-direction: column; gap: 0.75rem; }
```

### Causa raiz: `h-100` num flex item de coluna
O `.card-body` é um **flex container em coluna**, e o badge é um **flex item direto** dele
(o `.card-actions` fecha em `library.html:83`; o `<span>` começa em `84` — são irmãos).

`h-100` aplica `height: 100%`. Num container flex-column, isso faz o badge pedir a altura
inteira do `.card-body` e depois ser encolhido pelo `flex-shrink: 1` padrão, proporcionalmente
ao espaço livre. Como a altura do `.card-body` depende do título (`h6` com 1 ou 2 linhas), a
altura final do badge acompanha o título. É exatamente o sintoma relatado.

O efeito é amplificado por `class="card h-100"` (`library.html:56`): o Bootstrap iguala a altura
de todos os cards da linha, então cards de título curto ganham folga vertical extra — e o badge
com `h-100` é quem absorve essa folga.

### Achado secundário: as regras de CSS do badge estão mortas
`library.css:7-11` e `library.css:23-25`:
```css
.card-actions .btn,
.card-actions .quantity-box,
.card-actions .badge { min-height: 3rem; }

.card-actions .badge { white-space: nowrap; }
```

Ambos os seletores exigem um ancestral `.card-actions`. O badge está **fora** dele
(irmão, não descendente), então **nem `min-height: 3rem` nem `white-space: nowrap` são
aplicados hoje**. A altura mínima que deveria estabilizar o componente nunca entrou em vigor.

### Terceiro efeito: o espaço não é reservado
O `*ngIf` remove o elemento do DOM quando `quantity <= 4`. Cards com e sem badge têm composições
verticais diferentes; combinado com o `h-100` do `.card`, a folga se redistribui de forma
diferente em cada card da mesma linha.

## Comportamento esperado
O badge "Repetidas" tem altura fixa, idêntica em todos os cards, independente do comprimento do
título e da quantidade. O espaço que ele ocupa é reservado mesmo quando a carta não é repetida,
para que todos os cards da grade tenham a mesma composição vertical.

## Alterações necessárias

### 1. `frontend/src/app/pages/library/library.html`
Trocar `*ngIf` por alternância de visibilidade (reserva o espaço), remover `h-100` e `w-100`,
e adicionar uma classe própria:

```html
<span
  class="badge text-bg-danger d-flex justify-content-center align-items-center repeat-badge"
  [class.invisible]="card.quantity <= 4"
>
  Repetidas
</span>
```

- `h-100` **removido** — é a causa raiz.
- `d-inline-flex` → `d-flex`: como flex item de coluna, `inline-flex` não traz benefício e
  `d-flex` deixa o `justify-content` explícito.
- `w-100` deixa de ser necessário: flex item em coluna já estica na transversal por
  `align-items: stretch` (padrão).
- `.invisible` do Bootstrap é `visibility: hidden` — o elemento continua ocupando a caixa.

### 2. `frontend/src/app/pages/library/library.css`
Adicionar a regra que fixa a altura e corrige os seletores mortos:

```css
.repeat-badge {
  flex: none;          /* impede que o flex container estique/encolha o badge */
  min-height: 3rem;    /* mesma altura dos botões de ação */
  white-space: nowrap;
}
```

`flex: none` (= `flex: 0 0 auto`) é o que realmente blinda o item contra o `flex-shrink` do
container. Sem ele, qualquer altura futura volta a ser negociável.

As regras antigas em `library.css:7-11` e `23-25` podem manter a menção a `.card-actions .badge`
ou removê-la — hoje ela não casa com nenhum elemento.

## Critérios de aceitação
1. O badge "Repetidas" tem a mesma altura em todos os cards, com título de 1 ou 2 linhas.
2. A altura do badge não muda quando cards da mesma linha têm títulos de comprimentos diferentes.
3. Cards com `quantity <= 4` reservam o mesmo espaço vertical, sem exibir o badge.
4. O texto "Repetidas" não quebra em duas linhas.
5. A grade permanece alinhada em todos os breakpoints (`row-cols-1` até `row-cols-lg-5`).

## Verificação
Manual, é mudança visual: abrir a `library` com um filtro que traga na mesma linha uma carta de
título curto e repetida (ex.: "Nami", quantity > 4) e uma de título longo e repetida. Os dois
badges devem ter altura idêntica.

Opcionalmente, um caso em `library.spec.ts` afirmando que o `<span.repeat-badge>` existe no DOM
mesmo com `quantity = 1` e carrega a classe `invisible` — protege contra alguém reintroduzir o
`*ngIf` e voltar a quebrar a reserva de espaço.

## Fora de escopo
- Truncar títulos longos com ellipsis para forçar `h6` de 1 linha. Resolveria o sintoma por
  tabela, mas esconde informação; a correção do `h-100` já basta.
