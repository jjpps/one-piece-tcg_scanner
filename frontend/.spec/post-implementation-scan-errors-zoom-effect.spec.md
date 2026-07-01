# Post-Implementation: Efeito de Lupa em `scan-errors`

## Objetivo
Corrigir o bug do zoom no componente `scan-errors` de modo que o preview de zoom seja exibido apenas no card atualmente hovered.

## Arquivos a alterar
- `src/app/pages/scan-errors/scan-errors.html`
- `src/app/pages/scan-errors/scan-errors.ts`
- `src/app/pages/scan-errors/scan-errors.css`
- `src/app/pages/scan-errors/scan-errors.spec.ts`

## Descrição da feature desejada
No componente `scan-errors`, cada carta deve ter uma imagem com efeito de lupa.
Ao passar o mouse sobre a imagem de um card, um painel de preview de zoom deve aparecer apenas naquele card e acompanhar o movimento do cursor.
Quando o mouse sair da imagem, o painel deve desaparecer.
O zoom não deve ser replicado em outros cards simultaneamente.

## Critérios de aceitação
1. Apenas o card atualmente hovered exibe `.zoom-preview`.
2. Outros cards não mostram painel de zoom enquanto não estiverem sendo hoverados.
3. O preview de zoom deve usar a URL da imagem do card ativo.
4. O preview deve atualizar a posição de fundo com base no cursor.
5. O preview deve desaparecer no `mouseleave`.
6. A interação com o botão `Salvar Carta` deve continuar normal.

## Problema observado
A implementação atual compartilha um estado global de zoom para todos os cards no componente:
- `zoomActive`
- `zoomImageSrc`
- `zoomStyle`

Isso faz com que o mesmo preview apareça em todos os cards, pois o `*ngIf="zoomActive && zoomImageSrc"` é avaliado em cada item do `*ngFor` com o mesmo estado.

## Causa raiz
O estado do zoom não está vinculado ao card individual. O componente precisa saber qual card deve renderizar o preview ativo.

## Solução proposta
### 1. `scan-errors.ts`
Adicionar um identificador do card ativo.
- novo campo:
  - `activeZoomCardId: string | number | null = null;`

Manter os campos existentes de zoom:
- `zoomActive = false;`
- `zoomImageSrc: string | null = null;`
- `zoomStyle: { [klass: string]: string } = {};
- `zoomScale = 3;`

Alterar métodos:
- `onImageMouseEnter(imageUrl: string, cardId: string | number, event: MouseEvent): void`
  - `this.activeZoomCardId = cardId;`
  - `this.zoomActive = true;`
  - `this.zoomImageSrc = imageUrl;`
  - `this.updateZoomStyle(event);`

- `onImageMouseMove(event: MouseEvent): void`
  - se `!this.zoomActive || !this.zoomImageSrc` retornar
  - chamar `this.updateZoomStyle(event);`

- `onImageMouseLeave(): void`
  - `this.zoomActive = false;`
  - `this.activeZoomCardId = null;`
  - `this.zoomImageSrc = null;`
  - `this.zoomStyle = {};`

- `private updateZoomStyle(event: MouseEvent): void`
  - obter `event.currentTarget` e `getBoundingClientRect()`
  - calcular `positionX` e `positionY` em porcentagem
  - definir `background-image` com `this.zoomImageSrc`
  - definir `background-position` como `${positionX}% ${positionY}%`
  - definir `background-size` com `rect.width * this.zoomScale` e `rect.height * this.zoomScale`

### 2. `scan-errors.html`
Modificar o template do card para passar `card.id` ou outro identificador único para `onImageMouseEnter`.
- `(mouseenter)="onImageMouseEnter(card.image_url, card.id, $event)"`
- `(mousemove)="onImageMouseMove($event)"`
- `(mouseleave)="onImageMouseLeave()"`

Alterar o `*ngIf` do preview para renderizar somente no card ativo:
- `*ngIf="zoomActive && zoomImageSrc && activeZoomCardId === card.id"`

### 3. `scan-errors.css`
Manter a estilização do preview e do contêiner.
Apenas certificar que a classe `.zoom-preview` está posicionada dentro do card correto e não afeta outros cards.

Exemplo de estilo:
- `.image-zoom-container { position: relative; overflow: hidden; }`
- `.zoom-preview { position: absolute; top: 0.5rem; right: 0.5rem; width: 230px; height: 230px; ... }`

### 4. `scan-errors.spec.ts`
Adicionar/ajustar cenários de teste para validar o escopo do card:
- `should create` mantém válido.
- `should activate zoom only for hovered card`
  - simular hover em um card e garantir `activeZoomCardId` correto.
- `should not render preview on non-hovered cards`
  - assegurar que `activeZoomCardId` evita renderização em outros cards.
- `should deactivate zoom on mouse leave`
  - limpar `activeZoomCardId`, `zoomActive`, `zoomImageSrc`, `zoomStyle`.

### 5. Comportamento esperado do preview
- Apenas um preview ativo por vez.
- O preview segue o cursor no card atual.
- A imagem de fundo no preview corresponde à imagem do card hovered.
- O preview desaparece imediatamente ao sair do card.
- O preview fica alinhado ao próprio card, não em todos os cards.

## Notas adicionais
- Se `card.id` não for único ou não estiver disponível, usar `card.image_url` como identificador secundário.
- O estado global do componente deve ser limitado ao card ativo.
- O `*ngFor` permanece inalterado; apenas a condição de exibição do preview muda.

## Resultado final
A tarefa deve resultar em um comportamento de zoom correto em `scan-errors` onde:
- o preview de lupa aparece somente no card hovered;
- o preview não é replicado em outros cards;
- a feature mantém os eventos existentes de salvar carta e não altera a usabilidade da grade.
