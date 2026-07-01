# Spec: Efeito de Lupa na tela `scan-errors`

## Objetivo
Adicionar um efeito de zoom sobre a imagem na tela `scan-errors.html`, semelhante ao comportamento de vitrines de e-commerce. Ao passar o mouse sobre a imagem da carta, o usuário deve ver uma área ampliada da imagem em um painel de visualização ou lente de zoom.

## Escopo
- Página: `src/app/pages/scan-errors/scan-errors.html`
- Componente: `src/app/pages/scan-errors/scan-errors.ts`
- Estilos: `src/app/pages/scan-errors/scan-errors.css`
- Testes: `src/app/pages/scan-errors/scan-errors.spec.ts`

## User Story
Como usuário do scanner de cartas,
quero ver um zoom na imagem da carta ao passar o mouse,
para inspecionar detalhes da arte sem precisar abrir a imagem em nova aba.

## Critérios de aceitação
1. Cada imagem exibida na lista de cartas deve mostrar um efeito de zoom ao passar o mouse.
2. O zoom deve ser exibido de forma clara e responsiva, sem quebrar o layout da grade.
3. O painel de zoom pode ser:
   - uma lente diretamente sobre a imagem, ou
   - um painel lateral/externo que mostra a área ampliada.
4. O efeito deve seguir a posição do cursor sobre a imagem.
5. Ao remover o cursor da imagem, o zoom deve desaparecer.
6. O comportamento deve funcionar em navegadores de desktop modernos.
7. O efeito não deve impedir o usuário de interagir com o botão "Salvar Carta".

## Design de implementação
### UX proposto
- A imagem principal permanece visível no cartão.
- Ao entrar com o cursor sobre a imagem, um elemento de zoom aparece.
- O elemento de zoom deve mostrar a região da imagem com escala aumentada (por exemplo, 2x ou 3x).
- A posição do zoom atualiza conforme o mouse se move.
- O zoom desaparece ao sair da imagem.

### Comportamento esperado
- `mouseenter` na imagem ativa o zoom.
- `mousemove` atualiza as coordenadas no componente e define o fundo do painel de zoom.
- `mouseleave` desativa o zoom e oculta a visualização.

## Alterações necessárias
### 1. `src/app/pages/scan-errors/scan-errors.html`
- Envolver a imagem em um contêiner com classes que permitam posicionamento relativo.
- Adicionar atributos de evento ao `img`:
  - `(mouseenter)="onImageMouseEnter(card.image_url, $event)"`
  - `(mousemove)="onImageMouseMove($event)"`
  - `(mouseleave)="onImageMouseLeave()"`
- Adicionar template condicional para o painel de zoom:
  - `*ngIf="zoomActive && zoomImageSrc"
  - usar `zoomBackgroundStyle` ou equivalente para aplicar `background-image` e posição.
- Se optar por uma lente interna, inserir um elemento `.zoom-lens` sobre a imagem.

### 2. `src/app/pages/scan-errors/scan-errors.ts`
- Criar novos campos/propriedades:
  - `zoomActive = false`
  - `zoomImageSrc: string | null = null`
  - `zoomX = 0`
  - `zoomY = 0`
  - `zoomBackgroundStyle: { [klass: string]: string } = {}`
  - `zoomScale = 2` (ou `3`)
- Criar métodos novos:
  - `onImageMouseEnter(imageUrl: string, event: MouseEvent): void`
    - ativa o zoom e define `zoomImageSrc`
    - chama `updateZoomStyle(event)`
  - `onImageMouseMove(event: MouseEvent): void`
    - atualiza `zoomX` e `zoomY`
    - recalcula `zoomBackgroundStyle`
  - `onImageMouseLeave(): void`
    - desativa o zoom (`zoomActive = false`, `zoomImageSrc = null`)
  - `updateZoomStyle(event: MouseEvent): void`
    - calcula a posição do cursor relativa ao tamanho da imagem
    - define `background-position` e `background-size`
    - mantém `background-image` apontando para `zoomImageSrc`
- Poderá ser necessário usar `event.currentTarget` para obter a largura/altura da imagem.

### 3. `src/app/pages/scan-errors/scan-errors.css`
- Estilos para o contêiner da imagem:
  - `position: relative;`
  - `overflow: hidden;`
- Estilos para a lente ou painel de zoom:
  - `position: absolute;` ou `position: fixed`/`absolute` para painel externo
  - `width` e `height` definidas (por exemplo `200px x 200px`)
  - `border: 1px solid rgba(0,0,0,0.15);`
  - `box-shadow` suave
  - `background-repeat: no-repeat;`
  - `pointer-events: none;` se a lente for sobreposta
- Estilos de transição suave para aparecer/desaparecer.
- Se o zoom for externo, definir posição fixa ou alinhada ao card.

### 4. `src/app/pages/scan-errors/scan-errors.spec.ts`
- Adicionar testes de unidade para validar o novo comportamento.
- Exemplos de casos de teste:
  1. `should create` mantém válido.
  2. `should activate zoom on image enter`:
     - chamar `onImageMouseEnter(url, event)`
     - esperar `zoomActive === true`
     - `zoomImageSrc` deve ser igual a `url`
  3. `should update zoom style on mouse move`:
     - inicializar `zoomActive` e `zoomImageSrc`
     - chamar `onImageMouseMove(event)` com coordenadas de mouse
     - verificar se `zoomBackgroundStyle['background-position']` está definido
  4. `should deactivate zoom on image leave`:
     - definir `zoomActive = true`
     - chamar `onImageMouseLeave()`
     - verificar desativação
  5. `should render zoom panel when active`:
     - no template, forçar `zoomActive = true` e `zoomImageSrc`
     - `fixture.detectChanges()` e validar `querySelector('.zoom-panel')` ou `.zoom-lens`
- Se a aplicação usar `ngMocks` ou `TestBed`, ajustar o teste para acessar os elementos do DOM e eventos.

## Estrutura de comportamento esperada
### Visual
- O zoom surge sobre a imagem ou ao lado.
- O usuário vê uma área ampliada da carta sem distrações.
- O efeito tem desempenho suave e não adiciona elementos duplicados além do necessário.

### Técnica
- Não recarregar a imagem do servidor em cada movimento do mouse.
- Usar a mesma URL da imagem principal como `background-image` no painel de zoom.
- Calcular `background-position` com base nas coordenadas relativas do mouse sobre a imagem.
- Usar `background-size` igual a `imageWidth * zoomScale` e `imageHeight * zoomScale`.

## Possíveis melhorias futuras
- Suportar toque em dispositivos móveis com toque longo para ativar o zoom.
- Alternar entre `zoom-lens` e painel externo via configuração do componente.
- Ajustar escala automaticamente com base no tamanho do contêiner.
- Suportar zoom em modo de teclado focado para acessibilidade.

## Resultado final esperado
- Arquivo de spec criado: `src/app/pages/scan-errors/scan-errors-zoom-effect.spec.md`
- Alterações descritas claramente para os arquivos:
  - `scan-errors.html`
  - `scan-errors.ts`
  - `scan-errors.css`
  - `scan-errors.spec.ts`
- Métodos novos descritos:
  - `onImageMouseEnter`
  - `onImageMouseMove`
  - `onImageMouseLeave`
  - `updateZoomStyle`
- Detalhamento suficiente para que a tarefa seja implementada a partir do spec.