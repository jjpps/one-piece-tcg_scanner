# Multi Input card errors

- Atualmente a tela `scan-errors.html` permite aplicar o código de uma carta por vez, exigindo operações repetidas pelo usuário.

## Descrição da feature
O usuário deve poder selecionar várias cartas na lista e aplicar um único código a cada uma delas, sem qualquer alteração nas APIs do backend.

## Restrições e premissas
- Não haverá mudanças nas rotas, payloads ou comportamentos das APIs do backend.
- Não existe endpoint de lote: para cada carta selecionada deve ser feita UMA chamada individual à mesma API já existente.

## Fluxo do usuário (detalhado)
1. O usuário seleciona visualmente várias cartas na lista. A seleção pode ser feita clicando em cada `div` da carta; checkboxes podem ser exibidos como auxílio visual.
2. Ao haver pelo menos uma carta selecionada, um input global é exibido (por exemplo no topo ou rodapé da lista) permitindo digitar o código da carta.
3. O usuário digita o código e confirma (botão `Aplicar` ou tecla Enter).
4. Para cada carta selecionada o frontend executa, de forma unitária, a mesma chamada à API usada atualmente para corrigir/atualizar o código daquela carta (uma requisição por carta).
5. O frontend exibe o resultado por carta (sucesso/erro) e um resumo ao final (quantas atualizadas, quantas falharam).

## Regras de chamada à API (front-end)
- Usar os endpoints e payloads existentes sem modificações.
- Executar uma requisição por carta selecionada — não implementar agregação, nem mudança no backend.
- Tratar resposta de cada requisição individualmente e exibir o status correspondente na UI.

## UI / Comportamento visual
- Seleção: clicar na `div` da carta marca/desmarca a seleção; opcionalmente mostrar checkbox para clareza.
- Input global: aparece apenas quando houver seleção; contém validação simples do formato do código.
- Ação: botão `Aplicar código às selecionadas` ou confirmação via Enter.
- Feedback: mostrar status por carta (ícone ou badge) e resumo agregado ao final.

## Validações e UX importantes
- Validar localmente o formato mínimo do código antes de enviar (definir formato com o time se necessário).
- Se nenhuma carta estiver selecionada, o input global não deve aparecer ou o botão deve estar desabilitado.
- Se uma carta já tiver código populado, o comportamento padrão é sobrescrever com o novo código (ou opcionalmente exibir aviso de sobrescrita — especificar se necessário).

## Critérios de aceitação
- O usuário seleciona múltiplas cartas e aplica um código único que resulta em uma chamada API por carta.
- Cada carta exibe seu estado individual (sucesso ou erro) após a chamada.
- Um resumo final apresenta contagem de sucessos e falhas.

## Testes sugeridos
- Teste manual: selecionar N cartas e aplicar código; verificar N requisições no frontend e status por item.
- Teste unitário: componente de seleção e ação disparando chamadas individuais por carta (mockando o serviço de API).

## Observações técnicas
- Integrar a lógica no arquivo `src/app/pages/scan-errors/scan-errors.ts` sem alterar endpoints backend.
- Reaproveitar serviços existentes (`processing.service.ts`, `review.service.ts` ou `library.service.ts`) que façam chamadas unitárias por carta.

---

Se quiser, eu já adapto o `scan-errors.ts` e o template `scan-errors.html` com um protótipo simples que implemente exatamente esse fluxo (frontend apenas). Quer que eu faça isso agora?

## Spec de Implementação (detalhado)

Objetivo:
- Implementar no frontend a capacidade de selecionar múltiplas cartas e aplicar um código, realizando UMA chamada individual à API por carta, sem alterar nada no backend.

Arquivos a serem criados/alterados:
- `src/app/pages/scan-errors/scan-errors.html`: atualizar template para suportar seleção (checkbox ou click na div), exibir input global e botão `Aplicar código às selecionadas`, e indicadores de status por item.
- `src/app/pages/scan-errors/scan-errors.ts`: adicionar lógica de seleção, validação do input global, método que itera sobre as cartas selecionadas e chama a API para cada uma, atualizar estados por carta e gerar resumo final.
- `src/app/pages/scan-errors/scan-errors.css` (ou `scan-errors.css` existente): estilos para seleção, badges de status e input global.
- `src/app/pages/scan-errors/scan-errors.spec.ts`: adicionar/atualizar testes unitários para a nova lógica.
- `src/app/services/<relevant>.service.ts` (por exemplo `library.service.ts` ou `review.service.ts`): verificar existência de método para atualizar o código de uma carta; se não existir, adicionar `updateCardCode(cardId: string, code: string): Promise<any>` que faça a chamada HTTP existente.

Novos métodos / funções a implementar (sugestão de nomes e responsabilidades):
- Em `scan-errors.ts` (componente/controller):
	- `toggleSelection(cardId: string): void` — marca/desmarca a carta selecionada.
	- `getSelectedCards(): Card[]` — retorna array das cartas atualmente selecionadas.
	- `applyCodeToSelected(code: string): Promise<void>` — método acionado pelo botão; valida input e chama `applyCodeToCard` para cada carta selecionada.
	- `applyCodeToCard(card: Card, code: string): Promise<void>` — chama o serviço que faz a requisição ao backend e atualiza o estado da carta (`pending`, `success`, `error`, `message`).
	- `resetSelection(): void` — limpa seleção e input após sucesso (opcional).

- Em `library.service.ts` ou `review.service.ts` (service existente):
	- `updateCardCode(cardId: string, code: string): Promise<any>` — faz a requisição HTTP usando o endpoint/contract atual (reaproveitar rota existente). Deve retornar a Promise com resposta do servidor para tratamento individual.

Detalhamento do comportamento e UI:
- Seleção:
	- Cada carta exibe visualmente se está selecionada (checkbox ou borda/overlay).
	- Clique na `div` da carta alterna seleção; Shift/Ctrl multi-select não é obrigatório (opcional).
- Input global e Ação:
	- Se nenhuma carta estiver selecionada, o input global e o botão permanecem ocultos ou desabilitados.
	- Ao selecionar >=1 cartas, o input global aparece no topo/rodapé da lista com placeholder `Digite o código e pressione Enter ou Aplicar`.
	- Ao confirmar, `applyCodeToSelected` é executado.
- Requisições e feedback por carta:
	- Para cada carta selecionada, o componente chama `updateCardCode(card.id, code)`.
	- Antes de cada chamada, marcar estado local da carta como `pending` e mostrar spinner/badge.
	- Ao receber sucesso: marcar como `success` e mostrar mensagem curta (ex.: `Atualizado`).
	- Ao receber erro: marcar como `error`, armazenar mensagem do servidor e permitir que o usuário tente novamente (botão `Re-tentar` por item ou re-aplicar para as selecionadas).
- Resumo final:
	- Ao finalizar todas as chamadas (promises resolvidas/rejeitadas), mostrar resumo agregado: `X atualizadas, Y falharam` e habilitar ação para re-tentar apenas as falhas.

Regras de UX/Validação:
- Validar formato do código antes de iniciar (padrão mínimo; se necessário, confirmar com backend). Se inválido, exibir erro e não iniciar requisições.
- Sobrescrita: comportamento padrão é sobrescrever código existente; se desejar confirmação, adicionar opção de confirmação (não obrigatório agora).
- Bloqueio parcial: não bloquear a lista inteira — apenas desabilitar o botão enquanto as operações estiverem em andamento.

Erros e re-tentativa:
- Cada carta mantém seu próprio estado de erro com a mensagem retornada.
- O usuário pode re-tentar apenas as cartas com erro através do botão `Re-tentar falhas` ou pela re-seleção e reaplicação do código.

Testes e QA:
- Unit tests (`scan-errors.spec.ts`):
	- Verificar que `toggleSelection` adiciona/remove cards do estado de seleção.
	- Verificar que `applyCodeToSelected` chama `updateCardCode` N vezes quando N cartas estão selecionadas (mock do service).
	- Verificar tratamento de respostas de sucesso e erro por carta.
- Manual QA:
	- Selecionar 1, N e muitas cartas; aplicar código; conferir N chamadas no console/network e estados por item.
	- Verificar UX quando código inválido e quando backend retorna erro por item.

Checklist de entrega (do front-end):
- [ ] Atualizar template `scan-errors.html` com seleção e input global.
- [ ] Implementar lógica de seleção e `applyCodeToSelected` em `scan-errors.ts`.
- [ ] Adicionar/usar `updateCardCode` em serviço existente.
- [ ] Estilos visuais em `scan-errors.css` para seleção e badges.
- [ ] Testes unitários básicos atualizados/criados.
- [ ] Documentar no `CHANGELOG` ou commit message que a feature não altera backend.

Notas técnicas / sugestões de implementação:
- Use `Promise.allSettled` ou iterações `for..of` com `await` para controlar o fluxo de chamadas e coletar resultados por item (cada chamada é unitária). Não implementar lógica de agregação no backend.
- Manter feedback visual imediato: atualizar estado por carta assim que cada resposta chegar.
- Reaproveitar métodos e serviços existentes para não duplicar lógica HTTP.

Próximo passo (se autorizado):
- Posso implementar um protótipo mínimo alterando os arquivos mencionados (`scan-errors.html`, `scan-errors.ts`, `scan-errors.css`) e adicionar testes básicos. Deseja que eu implemente esse protótipo agora?
