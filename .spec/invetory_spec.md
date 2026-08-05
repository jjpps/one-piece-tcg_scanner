# Feature Inventarios

## Problema
- eu possuo fisicamente mais de 2000 cartas e as vezes a minha versao fisica fica desincronizada com minha versao digital.
esse sistem inteiro serve como biblioteca virtual de cartas. porem muitas vezes cartas nao entram no sistema ou nao saem.
- para isso teria fazer um inventario das minhas cartas fisica e bater elas no sistema.
- existe a situaçao cartas que estão no sistema mas nao existema mais fisicamente.
- existe a situaçao cartao que nao estao no sistema e existe fisicamente.

## Resumo da solução

Uma nova feature de **Auditoria de Inventário**: uma tela dedicada onde o usuário reconcilia a biblioteca inteira contra a coleção física, uma vez por sessão. A sessão é persistida no SQLite desde a primeira interação (o backend roda localmente, sob demanda, então nada pode depender de estado em memória), pode ser pausada e retomada, é organizada por cor (forma como a coleção física está separada), e cada carta é revisada com uma decisão binária ("mudou?") antes de pedir um número, para não forçar digitação nas milhares de cartas que não mudaram. Cartas físicas que nunca entraram no sistema são adicionadas por código, reaproveitando a busca por API já existente. No final, o usuário revisa um diff completo e aplica tudo de uma vez (tudo ou nada) — nada é escrito na tabela `cards` antes dessa confirmação final.

### Fora do escopo desta feature
- Histórico/auditoria de mudanças de quantidade (log de deltas por origem: scan/manual/inventário). Ideia registrada para o futuro, não implementada agora.
- Import/export CSV.
- Recontagem via scan/OCR (câmera) como mecanismo de auditoria.
- Melhorias no funil de erros de scan (`images_with_errors`) — feature separada, não decidida.
- Aplicação parcial/linha a linha do diff final — a aplicação é sempre tudo ou nada.
- Múltiplas sessões de auditoria simultâneas — existe no máximo uma sessão com `status = 'open'` por vez.

## Modelo de dados

Duas tabelas novas em `db.sqlite`, criadas em `database.py::init_db()` seguindo o padrão já usado para a tabela `cards` (SQL puro via `sqlite3`, sem ORM).

```sql
CREATE TABLE IF NOT EXISTS inventory_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'open',       -- 'open' | 'completed' | 'discarded'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME DEFAULT NULL
);

-- garante no máximo uma sessão aberta por vez
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_sessions_single_open
    ON inventory_sessions(status)
    WHERE status = 'open';

CREATE TABLE IF NOT EXISTS inventory_session_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES inventory_sessions(id),
    code TEXT NOT NULL,
    card_name TEXT,
    card_image_url TEXT,
    card_color TEXT,                            -- NULL/'' vira grupo "Sem cor definida" na UI
    is_new_card INTEGER NOT NULL DEFAULT 0,      -- 0/1 — carta que não existia em `cards` no início da sessão
    card_data_json TEXT DEFAULT NULL,            -- só para is_new_card=1: payload completo do Card (dataclass) buscado na API, para aplicar depois sem nova chamada de rede
    system_quantity INTEGER NOT NULL DEFAULT 0,  -- snapshot de cards.quantity no início da sessão; 0 para cartas novas
    reviewed INTEGER NOT NULL DEFAULT 0,         -- 0/1 — usuário já respondeu "mudou?" para esta linha
    changed INTEGER DEFAULT NULL,                -- NULL até revisar; 0 = "não mudou"; 1 = "mudou"
    counted_quantity INTEGER DEFAULT NULL,       -- preenchido quando changed=1 (ou sempre, para is_new_card=1)
    reviewed_at DATETIME DEFAULT NULL,
    UNIQUE(session_id, code)
);

CREATE INDEX IF NOT EXISTS idx_inventory_items_session_color
    ON inventory_session_items(session_id, card_color);
```

**Por que `system_quantity` é um snapshot e não é reconsultado:** a entrada do usuário é sempre a **quantidade final** (decisão já tomada), então aplicar uma mudança é um `UPDATE cards SET quantity = counted_quantity WHERE code = ?` — não depende de o snapshot estar "atualizado" no momento da aplicação. Isso é intencional mesmo se a Library sofrer um `+`/`-` manual enquanto a auditoria está aberta: o valor contado na auditoria vence, porque representa uma reconciliação física deliberada e mais recente.

## Backend

### `backend/repositories/inventory_repository.py` (novo)
Funções de acesso a dado, seguindo o mesmo estilo de `cards_repository.py` (conexão `sqlite3` por chamada, sem pool):
- `get_open_session()` → linha de `inventory_sessions` com `status='open'`, ou `None`.
- `discard_open_session()` → `UPDATE inventory_sessions SET status='discarded', updated_at=CURRENT_TIMESTAMP WHERE status='open'`.
- `create_session_with_snapshot()` → dentro de uma transação: descarta sessão aberta (se houver), insere nova sessão, faz `SELECT code, card_name, image_url, card_color, quantity FROM cards`, e insere um `inventory_session_item` por carta via `executemany`. Retorna o `session_id` e a contagem total.
- `get_session_summary(session_id)` → contagens agregadas (`total`, `reviewed`, `pending`, `changed`, `new`).
- `get_session_colors(session_id)` → `SELECT COALESCE(NULLIF(TRIM(card_color), ''), '__no_color__') as card_color, COUNT(*), SUM(reviewed) ... GROUP BY 1`.
- `get_session_items(session_id, color=None, status='pending', search=None, page=1, page_size=50)` → lista paginada.
- `get_item(session_id, code)` / `mark_item_reviewed(session_id, code, changed, counted_quantity)` → usado pelo `PATCH`.
- `add_new_card_item(session_id, code, card, counted_quantity)` → insere linha com `is_new_card=1`, `card_data_json=json.dumps(card.__dict__)`.
- `get_session_diff(session_id)` → separa `updates` (`is_new_card=0 AND changed=1 AND counted_quantity != system_quantity`), `new_cards` (`is_new_card=1`), `pending` (`reviewed=0`).
- `apply_session(session_id)` → ver lógica de aplicação abaixo.

### `backend/services/inventory_service.py` (novo)
Regras de negócio que não são só SQL: validação de código, chamada à API externa (`get_card_by_code`), montagem das respostas para as rotas, orquestração da transação de `apply`.

### `backend/routes/inventory_routes.py` (novo)
Blueprint `inventory_bp`, registrado em `routes/__init__.py` com `url_prefix='/api'` (mesmo padrão de `library_bp`, `upload_bp` etc.), então as rotas finais ficam sob `/api/inventory/...`.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/inventory/session` | Sessão aberta atual (ou `null`) + resumo de progresso |
| `POST` | `/inventory/session` | Descarta sessão aberta (se houver) e cria uma nova com snapshot da coleção inteira |
| `GET` | `/inventory/session/<id>/colors` | Lista de cores presentes na sessão, com contagem revisado/pendente por cor |
| `GET` | `/inventory/session/<id>/items` | Itens paginados, filtráveis por `color`, `status`, `search` |
| `PATCH` | `/inventory/session/<id>/items/<code>` | Registra a resposta "mudou?" (e quantidade, se sim) para uma linha |
| `GET` | `/inventory/lookup/<code>` | Busca uma carta na API por código, sem persistir nada (preview para "adicionar carta nova") |
| `POST` | `/inventory/session/<id>/items` | Adiciona uma carta nova (não cadastrada) à sessão, com a quantidade contada |
| `GET` | `/inventory/session/<id>/diff` | Diff completo: atualizações, cartas novas, pendências |
| `POST` | `/inventory/session/<id>/apply` | Aplica o diff inteiro na tabela `cards`, tudo ou nada, e encerra a sessão |

Detalhamento de cada rota:

**`GET /inventory/session`**
- 200: `{ "session": null }` quando não há sessão aberta.
- 200: `{ "session": { "id": 5, "status": "open", "created_at": "...", "total_items": 2043, "reviewed_count": 412, "pending_count": 1631, "changed_count": 37, "new_count": 5 } }`.

**`POST /inventory/session`**
- Sem corpo obrigatório.
- Sempre descarta qualquer sessão `open` existente antes de criar a nova (decisão: "iniciar nova auditoria descarta a sessão em aberto", sem perguntar no backend — a confirmação "tem certeza?" é responsabilidade do frontend, antes de chamar este endpoint).
- 201: `{ "session_id": 6, "total_items": 2043 }`.
- 500 se a snapshot falhar no meio — toda a operação (descartar + criar + snapshot) roda em uma única transação, então falha parcial não deixa lixo.

**`GET /inventory/session/<id>/colors`**
- 200: `[{ "card_color": "Red", "label": "Red", "total": 210, "reviewed": 84, "pending": 126 }, { "card_color": "__no_color__", "label": "Sem cor definida", "total": 3, "reviewed": 0, "pending": 3 }, ...]`.
- 404 se `id` não corresponder a nenhuma sessão.

**`GET /inventory/session/<id>/items?color=&status=pending&search=&page=1&page_size=50`**
- `status` aceita `pending` (padrão), `reviewed`, `all`.
- `color` usa o mesmo valor retornado por `/colors` (incluindo `__no_color__`); omitido = todas as cores.
- `search` faz `LIKE` em `code` e `card_name` (mesmo comportamento de busca já existente na Library).
- 200: `{ "items": [ { "code": "OP01-001", "card_name": "...", "card_image_url": "...", "card_color": "Red", "system_quantity": 4, "is_new_card": false, "reviewed": true, "changed": true, "counted_quantity": 2 } ], "total": 210, "page": 1, "page_size": 50 }`.

**`PATCH /inventory/session/<id>/items/<code>`**
- Corpo (não mudou): `{ "changed": false }`.
- Corpo (mudou): `{ "changed": true, "counted_quantity": 3 }`.
- Validações: sessão precisa estar `open` (409 caso contrário, ex. já foi aplicada/descartada em outra aba); item precisa existir (404); se `changed=true`, `counted_quantity` é obrigatório, inteiro `>= 0` (400 caso inválido).
- Efeito: `reviewed=1`, `reviewed_at=now`, grava `changed`/`counted_quantity`.
- 200 com o item atualizado. Esta é a chamada de autosave-por-linha (persistência imediata em SQLite, decisão sobre não depender de memória do processo).

**`GET /inventory/lookup/<code>`**
- Não toca em nenhuma tabela de sessão. Só normaliza o código (`strip().upper()`) e chama `get_card_by_code` (o mesmo client já usado em `save_error_card`).
- 200: dados da carta (`card_name`, `card_image`, `card_color`, etc.) para o usuário confirmar visualmente antes de registrar a quantidade.
- 404: `{ "error": "Carta não encontrada para o código informado" }`.

**`POST /inventory/session/<id>/items`**
- Corpo: `{ "code": "OP01-016", "counted_quantity": 2 }`.
- Validações, nesta ordem:
  1. Sessão precisa estar `open` (409).
  2. `counted_quantity` inteiro `>= 1` (400) — não faz sentido "adicionar" uma carta nova com quantidade 0.
  3. Código não pode já existir como item desta sessão (400: "esta carta já está na lista de auditoria — edite a linha existente").
  4. Código não pode já existir na tabela `cards` principal (409: "esta carta já foi cadastrada na biblioteca depois que a auditoria começou — recarregue a sessão"). Esse é o caso de uma carta ter entrado no sistema por outro caminho (scan aprovado, botão manual da Library) *depois* que a sessão de auditoria tirou seu retrato inicial.
  5. Busca via `get_card_by_code`; se não encontrar, 404 igual ao `/lookup`.
- Efeito: insere `inventory_session_item` com `is_new_card=1`, `system_quantity=0`, `reviewed=1`, `changed=1`, `card_data_json` com o payload completo do `Card` retornado pela API.
- 201 com o item criado.

**`GET /inventory/session/<id>/diff`**
- 200: `{ "updates": [{ "code", "card_name", "system_quantity", "counted_quantity" }], "new_cards": [{ "code", "card_name", "counted_quantity" }], "pending_count": 1631, "pending_preview": [{ "code", "card_name", "card_color" }] }` (o `pending_preview` pode ser limitado, ex. 20 itens, só para dar contexto na UI — o número que importa é `pending_count`).
- Itens onde `changed=1` mas `counted_quantity == system_quantity` (usuário disse "mudou" e digitou o mesmo número por engano) contam como revisados, mas **não** entram em `updates` — não há nada a aplicar ali.

**`POST /inventory/session/<id>/apply`**
- Não exige `pending_count == 0` — o usuário pode aplicar o que já revisou e deixar o resto pendente para uma futura sessão (mas note: aplicar sempre encerra a sessão atual, ver "Suposições" abaixo).
- Lógica, dentro de **uma única transação SQLite**:
  1. Recalcula o diff no servidor (não confia em nada que o cliente mandou — só usa o `session_id` da URL).
  2. Para cada item em `updates`: `UPDATE cards SET quantity = ? WHERE code = ?`. Se `cursor.rowcount == 0` (carta sumiu da tabela `cards` entre o início da sessão e agora), aborta a transação inteira e retorna erro citando o código problemático.
  3. Para cada item em `new_cards`: reconstrói o `Card` a partir de `card_data_json` (`Card(**json.loads(...))`) e chama a lógica equivalente a `save_to_db(card, quantity=counted_quantity)`.
  4. Marca a sessão como `status='completed'`, `completed_at=now`.
  5. Commit.
- Se qualquer passo falhar: rollback total (tudo ou nada), sessão continua `open`, resposta 500/409 com detalhes.
- 200: `{ "updated": 12, "added": 3, "left_pending": 1631 }`.

### Alterações em arquivos existentes
- `backend/database.py`: adicionar as duas `CREATE TABLE IF NOT EXISTS` (+ índice) dentro de `init_db()`.
- `backend/routes/__init__.py`: importar `inventory_bp` e registrar com `url_prefix='/api'`.

## Frontend (Angular)

### Novos arquivos
- `frontend/src/app/pages/inventory-audit/inventory-audit.ts|html|css` — componente principal, standalone, seguindo o padrão de `library.ts`.
- `frontend/src/app/services/inventory.service.ts` — espelha `library.service.ts`: `apiUrl = `${API_BASE_URL}/inventory``, métodos para cada rota acima (`getOpenSession`, `startSession`, `getColors`, `getItems`, `reviewItem`, `lookupCard`, `addNewCard`, `getDiff`, `applySession`).
- `frontend/src/app/interfaces/InventorySession.ts`, `InventorySessionItem.ts`, `InventoryDiff.ts` — tipagem dos payloads acima.
- Nova rota `/inventory` (ou `/auditoria`) registrada nas rotas do app, com um link de navegação a partir da tela principal (ex. ao lado do link para "Library").

### Estados de tela

**1. Landing (entrada na feature)**
- Ao entrar, chama `GET /inventory/session`.
- Sessão existente → card de resumo "Auditoria em andamento: 412/2043 revisadas, iniciada em 01/08" com dois botões: **Continuar auditoria** e **Iniciar nova auditoria**.
  - "Iniciar nova auditoria" abre uma confirmação (`confirm()` ou modal simples): *"Isso vai descartar o progresso não aplicado da auditoria atual. Continuar?"* — só chama `POST /inventory/session` após confirmar.
- Sem sessão → botão único **Iniciar auditoria** → chama `POST /inventory/session` direto (nada a descartar).

**2. Seletor de cor**
- `GET /inventory/session/<id>/colors` renderiza uma lista/grade de cores como botões, cada um mostrando `"{label} — {reviewed}/{total} revisadas"`, incluindo "Sem cor definida" quando aplicável.
- Barra de progresso geral no topo: `{reviewed_count}/{total_items}` (vindo do resumo da sessão).
- Ação sempre visível nesta tela, independente da cor escolhida: **"+ Adicionar carta não cadastrada"** (ver fluxo 4 abaixo) — não fica atrelada a uma cor porque a cor da carta só é conhecida depois da busca por código.
- Botão **"Revisar e aplicar"** sempre acessível (não exige ter passado por todas as cores).

**3. Grade de revisão (por cor)**
- `GET /inventory/session/<id>/items?color=X&status=pending` alimenta a lista (paginada; usar scroll infinito ou paginação numérica simples dado o volume).
- Cada linha: miniatura, nome, código, "Quantidade no sistema: N", e dois botões — **Não mudou** / **Mudou**.
  - **Não mudou** → `PATCH .../items/<code> {changed:false}` (otimista: some da lista de pendentes imediatamente) → some da lista.
  - **Mudou** → revela um input numérico pré-preenchido com o valor atual (`system_quantity`, ajustável para cima/baixo) + botão **Confirmar** → `PATCH .../items/<code> {changed:true, counted_quantity}`.
- Toggle **"Mostrar já revisadas"** alterna `status=pending` ↔ `status=reviewed`, permitindo reabrir e corrigir uma linha já respondida antes da aplicação final (nada foi escrito em `cards` ainda, então é seguro).
- Campo de busca (`search`) reaproveita o padrão já usado na Library.

**4. Adicionar carta não cadastrada**
- Modal/seção com campo de código.
- Passo 1 — **Buscar**: chama `GET /inventory/lookup/<code>`; mostra preview (nome, imagem, cor) ou erro "carta não encontrada".
- Passo 2 — usuário digita a quantidade contada e confirma **Adicionar**: chama `POST /inventory/session/<id>/items {code, counted_quantity}`.
- Em caso de 409 (carta já existe em `cards`, adicionada por outro caminho depois do início da sessão): mensagem clara pedindo para recarregar a auditoria.

**5. Revisão do diff / aplicação final**
- `GET /inventory/session/<id>/diff` alimenta três seções:
  - **Quantidades alteradas (N)** — tabela `código / nome / atual → nova`.
  - **Cartas novas (M)** — tabela `código / nome / quantidade`.
  - **Ainda não revisadas (P)** — aviso não bloqueante (ex. banner amarelo) com contagem e uma amostra; não impede aplicar.
- Botão **Confirmar e aplicar**: se `N + M == 0`, confirma explicitamente ("nenhuma mudança será aplicada, mesmo assim encerrar a auditoria?"); senão aplica direto.
- Chama `POST /inventory/session/<id>/apply` → sucesso: toast com o resumo (`"12 atualizadas, 3 novas"`) e redireciona para a Library (que já reflete os novos números).

## Fluxo ponta a ponta (sistema ↔ físico)

1. **Sistema** — usuário abre "Auditoria de Inventário"; sem sessão aberta, `POST /inventory/session` cria uma nova com snapshot da coleção inteira organizada por cor.
2. **Sistema** — usuário escolhe uma cor; a tela mostra a lista de cartas daquela cor com a pergunta "Essa quantidade mudou?" por linha.
3. **Físico** — usuário pega a pilha física daquela cor e conta as cópias de cada carta.
4. **Sistema** — para cada carta identificada: "Não mudou" (um clique, sem número) ou "Mudou" (digita a quantidade final). Cada resposta é gravada imediatamente via `PATCH` no SQLite.
5. **Físico** — aparece uma carta que não está na lista do sistema.
6. **Sistema** — usuário busca o código em "Adicionar carta não cadastrada" (`GET /lookup`), confirma os dados, digita a quantidade e adiciona (`POST /items`).
7. **Físico → Sistema** — repete os passos 2–6 para cada pilha de cor, podendo fechar o app e retomar depois (a sessão está no SQLite, não em memória).
8. **Sistema** — a qualquer momento, "Revisar e aplicar" mostra o diff completo e sinaliza pendências sem bloquear.
9. **Sistema** — "Confirmar e aplicar" grava tudo em uma transação (tudo ou nada) e encerra a sessão.
10. **Sistema** — a Library reflete os números atualizados.

## Suposições assumidas (a confirmar)

Pontos que precisaram de uma decisão de implementação específica para a spec ficar completa, mas que não foram debatidos explicitamente antes — sinalizando aqui para revisão:

1. **Aplicar sempre encerra a sessão**, mesmo que existam pendências (`pending_count > 0`). Não existe hoje um conceito de "aplicar parcialmente e continuar a mesma sessão depois" — para continuar reconciliando o resto, o usuário inicia uma auditoria nova (que tira um novo retrato, incluindo os itens que ficaram pendentes). Se o desejo for poder aplicar em ondas dentro da **mesma** sessão (sem reiniciar o snapshot), isso muda o design do `apply` (ele passaria a limpar só os itens aplicados, mantendo a sessão `open`).
2. **Cartas novas armazenam o payload completo da API** (`card_data_json`) no momento em que são adicionadas à sessão, para o `apply` não depender de uma segunda chamada de rede (que poderia falhar ou trazer dados diferentes). Alternativa seria rebuscar no momento de aplicar.
3. **Não há endpoint para descartar uma sessão sem iniciar outra** — descartar só acontece como efeito colateral de `POST /inventory/session`. Se for útil poder "sair sem aplicar nem começar de novo", precisaria de um endpoint dedicado.
4. **Cartas que entram no sistema por outros caminhos (scan aprovado, botão manual da Library) enquanto uma auditoria está aberta não aparecem na sessão em andamento** — elas só entrarão no retrato da próxima auditoria (nova sessão). Isso é uma limitação aceita, não um bug.
