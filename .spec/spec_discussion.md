# Discussão: Feature de Inventário/Reconciliação

> Rascunho de discussão. Nada aqui é definitivo — depois de alinharmos, o resultado vai para `invetory_spec.md`.

## Como o sistema funciona hoje (para dar contexto à discussão)

**Modelo de dados**: tabela `cards` no SQLite, uma linha por código único de carta (`card_set_id`), com uma coluna `quantity` (inteiro). Não existe registro por unidade/exemplar, nem histórico de alterações de quantidade.

**Formas de a quantidade mudar:**
1. **Scan (fluxo principal)** — usuário fotografa cartas físicas → OCR extrai o código (`processor.py`) → se o código é lido e a API/DB reconhece a carta, ela vai para uma fila de revisão (`processed_cards.json`) → na tela de revisão o usuário aprova (`+1` ou insere nova linha) ou reprova (a imagem vai para `images_with_errors`).
2. **Erros de scan** — quando o OCR não lê o código, ou a carta não é encontrada na API, a imagem cai em `images_with_errors`. Na tela de "scan-errors" o usuário digita o código manualmente para salvar, ou a carta fica perdida ali até alguém tratar.
3. **Botões manuais na Library** (`+`/`-`) — incrementam/decrementam a quantidade em 1, um card por vez, sem qualquer registro de por quê (`library_routes.py`, `cards_repository.add_card_quantity/remove_card_quantity`).
4. **Deck building** — só *consulta* `quantity`, nunca altera. Não é fonte de desincronização.

**Onde a desincronização provavelmente nasce:**
- Erros de OCR/leitura de código fazem cartas físicas ficarem "perdidas" em `images_with_errors` sem que o usuário perceba ou trate todas.
- O ajuste manual (+/-) é de 1 em 1 clique, sem log — fácil errar, esquecer de repetir N vezes, ou clicar na carta errada em uma lista grande.
- Não existe nenhum mecanismo de conferência: nada compara "o que o app diz que eu tenho" com "o que eu realmente tenho na mão". Hoje, a única forma de descobrir divergência é o usuário perceber "de olho".
- Não há trilha de auditoria (quando/por quê uma quantidade mudou), então quando uma divergência é percontrada, não dá pra saber se foi um scan falho, um clique errado, etc.
- Não há operação em lote — corrigir uma divergência em uma coleção de 2000+ cartas no esquema atual (um clique = uma unidade) é inviável na prática.

Isso confirma o problema descrito na spec: a "verdade física" e a "verdade do sistema" divergem com o tempo, e não existe um jeito estruturado de trazer as duas de volta ao mesmo lugar.

## O que a feature de inventário precisa resolver

Da seção Problema, os dois casos que a reconciliação tem que cobrir:
- **Sistema tem, físico não tem** → precisa reduzir/zerar no sistema.
- **Físico tem, sistema não tem** → precisa adicionar no sistema.

E fazer isso para uma coleção grande (2000+ cartas) sem forçar o usuário a caçar carta por carta manualmente.

## Opções de solução

> Descartada: uma opção baseada em re-scan (recontar fisicamente com a câmera/OCR) foi cogitada, mas eliminada — o scan é lento para 2000+ cartas e o OCR não é 100% preciso, exigindo validação manual de boa parte das cartas depois. Isso tornaria a reconciliação mais lenta que o problema que ela resolve.

### Opção B — Contagem manual assistida (tela de auditoria), vencedora
Uma tela de "auditoria" que lista **toda** a biblioteca (2000+ cartas, com busca/filtro por cor reaproveitados da Library) e permite ao usuário digitar a **quantidade final** que ele tem fisicamente de cada carta (ex: "tenho 3"), em vez de +/- de 1 em 1. O sistema calcula o diff internamente (`quantity_atual` vs. `quantidade_informada`) e só aplica no banco depois de o usuário confirmar.

- Prós: mais rápido que +/- clique a clique; não depende de scan/OCR (sem lentidão nem falso-negativo de leitura); usuário informa o número que já sabe de cabeça/olhando a carta, sem fazer conta de delta.
- Contras: cobre bem o caso "sistema tem, físico não tem" (ajustar/zerar quantidade de uma carta já cadastrada). **Não cobre sozinha** o caso "físico tem, sistema não tem" — ver nota abaixo.

> **Gap identificado**: como CSV foi descartado (não existe nenhum registro da coleção fora do sistema — a única fonte para uma carta que "falta" no app é a carta física em si) e re-scan também foi descartado, a única forma de o usuário informar uma carta que existe fisicamente mas nunca entrou no sistema continua sendo digitar o código dela manualmente (fluxo parecido com o que já existe hoje em "scan-errors" / `addCard` por código). A tela de auditoria (Opção B) precisa incluir essa ação de "adicionar carta nova por código" dentro do mesmo fluxo de inventário, senão o caso 2 do problema (físico tem, sistema não tem) fica sem solução.

### Opção D — Trilha de auditoria e correção do funil de erros (adiada)
Ideias estruturais que ficam fora do escopo atual, mas registradas para o futuro:
1. ~~Histórico de alterações de quantidade~~ — **descartado por enquanto** (não aplicável no momento).
2. **Reduzir a perda no funil de erro de scan** — hoje `images_with_errors` é uma "gaveta" que o usuário precisa lembrar de abrir; um badge/alerta persistente enquanto houver itens pendentes lá reduziria o motivo #1 de desincronização. Não decidido se entra nesta feature.
3. **Confirmação antes de aplicar diffs grandes** — continua válido: mostrar "vou alterar X cartas, Y para mais, Z para menos, W novas" antes de tocar no banco.

## Decisões já tomadas

1. **Escopo da conferência: coleção inteira**, não parcial por set/cor/lote. Toda vez que o usuário abrir o fluxo de inventário, ele reconcilia a biblioteca completa de uma vez.
2. **Entrada por carta: decisão binária primeiro, depois quantidade final** (não delta). Cada linha pergunta "Essa quantidade mudou?" — se **não**, a linha é marcada como revisada sem exigir nenhum número (mantém a quantidade atual, evita digitação desnecessária nas 2000+ cartas que provavelmente não mudaram). Se **sim**, abre um campo para o usuário digitar "tenho X", e o sistema calcula a diferença sozinho.
3. **Nada é aplicado sem confirmação explícita.** Cartas não revisadas na sessão **não** são zeradas automaticamente — o usuário sempre confirma manualmente cada mudança antes de ela ser persistida.
4. **Sem histórico/auditoria de mudanças nesta feature** — fica de fora do escopo por ora ([[Opção D]] registra a ideia para depois).
5. **Sem import/export CSV** — descartado porque não existe hoje nenhum registro da coleção fora do sistema; uma planilha externa não ajudaria a encontrar cartas que só existem fisicamente. A única fonte de verdade para "físico tem, sistema não tem" é a carta em mãos, então essas entram por código digitado manualmente (ver gap na Opção B acima).
6. **Carta nova por código reaproveita a busca já existente** — ao digitar o código de uma carta ausente do sistema na tela de auditoria, o preenchimento de nome/imagem/preço etc. usa a mesma lógica de busca por API já usada em `save_error_card`/`get_card_by_code`. Não é preciso criar um novo mecanismo de lookup.
7. **Sessão de auditoria é persistente e retomável — gravada no SQLite, não em memória.** Como o backend roda localmente e só existe enquanto o processo está de pé (não é um serviço sempre online, é iniciado por linha de comando quando o usuário quer usar), a sessão não pode depender de estado em memória do processo Flask nem só do estado do Angular no navegador. Cada entrada (decisão "mudou?"/quantidade nova/carta adicionada) é persistida imediatamente numa tabela real (ex: `inventory_session` / `inventory_session_items`), via chamada à API no momento em que o usuário confirma a linha. Assim, fechar o terminal, reiniciar o processo ou o computador dormir no meio de uma auditoria de 2000+ cartas não perde progresso — ao reabrir, a sessão está exatamente onde parou porque está no arquivo do banco.
8. **Aplicação final do diff é tudo ou nada.** Um único "Confirmar e aplicar" grava todas as linhas revisadas de uma vez. Se uma linha estiver errada, o usuário precisa voltar à tela de auditoria e corrigi-la antes de confirmar novamente — não existe aplicação parcial/linha a linha.
9. **Iniciar uma nova auditoria descarta a sessão em aberto**, sem arquivar nem perguntar — é uma ação direta que substitui qualquer progresso não aplicado. (Vale a pena um aviso/confirmação simples do tipo "isso vai descartar sua auditoria em andamento, continuar?" na UI, mas sem fluxo de arquivamento.)

## Detalhe adicional: organização física da coleção

O usuário organiza as cartas fisicamente **por cor**, mas dentro de cada cor as cartas de coleções/sets diferentes ficam **misturadas**. Ou seja, ao contar fisicamente, o usuário percorre uma pilha de uma cor por vez, e dentro dela encontra cartas de vários `set_name`/`set_id` fora de ordem.

Implicação direta para a tela de auditoria: o **filtro/agrupamento por cor** (que já existe na Library via `get_distinct_card_colors`) não é só um "nice to have", é o eixo principal de navegação da tela — o fluxo natural do usuário é abrir a auditoria já filtrada/agrupada por cor e ir cartel a carta dentro daquele grupo. Agrupar ou ordenar por set/coleção não ajuda em nada, já que fisicamente essas cartas estão misturadas dentro da pilha de cor.

10. **Auditoria organizada por cor como eixo principal.** A tela de auditoria deve permitir (e possivelmente sugerir/abrir por padrão) a navegação filtrando por uma cor de cada vez, refletindo a organização física real da coleção. Ordenação por set/coleção não é prioridade para esse fluxo.

## Fluxo do processo na prática (sistema ↔ físico)

Passo a passo alternando ação de sistema e ação física, juntando todas as decisões acima:

1. **Sistema — iniciar auditoria.** Usuário abre "Auditoria de Inventário". Se não há sessão em aberto, o sistema cria uma nova sessão: tira um retrato da coleção inteira (código, nome, quantidade atual no banco) e organiza por cor.
2. **Sistema — escolher uma cor.** Usuário seleciona uma cor (ex: "Vermelho"). O sistema mostra a lista de cartas vermelhas cadastradas, cada uma com a pergunta "Essa quantidade mudou?" (Sim/Não) — o campo de quantidade só aparece se a resposta for "Sim" (ver passo 4).
3. **Físico — contar a pilha.** Usuário pega a pilha física de cartas daquela cor e conta quantas cópias tem de cada carta, olhando código/nome impresso.
4. **Sistema — registrar a contagem.** Para cada carta identificada na lista, o sistema pergunta "Essa quantidade mudou?". Se **não**, um clique marca a linha como "revisada" sem digitar número nenhum. Se **sim**, o usuário digita a quantidade final (ex: "tenho 3"). Em ambos os casos, a resposta é gravada imediatamente na sessão (tabela no SQLite, não em memória — decisão 7), não no banco principal ainda.
5. **Físico — carta não reconhecida.** Se aparecer na pilha uma carta que não está na lista do sistema (nunca foi cadastrada)...
6. **Sistema — adicionar carta nova.** ...o usuário digita o código dela na própria tela de auditoria. O sistema busca os dados via API (reaproveitando a lógica existente de `get_card_by_code`/`save_error_card`), preenche nome/imagem/preço, e adiciona essa carta como uma linha nova na sessão, com a quantidade informada.
7. **Físico → Sistema — repetir por cor.** Usuário passa para a próxima pilha de cor, repetindo os passos 2–6, até esgotar todas as pilhas físicas — ou até parar e retomar depois, já que a sessão fica salva (decisão 7).
8. **Sistema — revisar o diff.** Quando o usuário considera a contagem completa (ou quer conferir o progresso), abre a tela de revisão: lista tudo que vai mudar (`quantidade atual → quantidade informada`), cartas novas, e sinaliza cartas que **ainda não foram revisadas** nessa sessão.
9. **Sistema — aplicar.** Usuário confirma uma única vez ("Confirmar e aplicar"). Tudo ou nada (decisão 8): todas as mudanças revisadas são gravadas no banco de uma vez (`quantity` atualizada nas existentes, novas linhas inseridas). A sessão de auditoria é encerrada.
10. **Sistema — reflexo final.** A tela de Library passa a mostrar os números atualizados, já sincronizados com o que foi contado fisicamente.

**Caso de interrupção**: se o usuário sair no meio (passos 3–7), ao reabrir "Auditoria" o sistema detecta a sessão salva e oferece "Continuar" ou "Iniciar nova" — que descarta o progresso não aplicado (decisão 9).

## Discussão concluída

Todas as perguntas em aberto foram respondidas. As decisões acima (1–10) e a Opção B com o gap resolvido (cartas novas entram por código, reaproveitando a busca existente) formam a base suficiente para escrever a spec final em `invetory_spec.md`.
