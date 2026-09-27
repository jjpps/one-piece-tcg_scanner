# One Piece TCG Scanner

Catálogo pessoal de cartas de One Piece TCG, com escaneamento, inventário e sincronização com o Binder.

## Language

**Carta**:
Uma carta identificada unicamente pelo seu código (ex.: `EB01-001`). Idioma e arte alternativa não distinguem cartas.
_Avoid_: variante, printing

**Quantidade**:
Quantas cópias de uma **Carta** possuímos. Quantidade 0 equivale a não possuir a carta.

**Binder**:
O aplicativo externo de coleção cujo acervo exportamos como CSV e ao qual devolvemos mudanças.

**CSV do Binder**:
Arquivo exportado pelo **Binder** com o acervo dele. Só código e quantidade importam; os demais campos (nome, set, idioma, arte alternativa) são ignorados. Linhas do mesmo código são somadas. Um arquivo com qualquer linha inválida é rejeitado por inteiro.

**Sincronização**:
Processo de comparar o **CSV do Binder** com o nosso acervo, decidir cada **Divergência** e commitar o resultado. Só existe uma Sincronização aberta por vez, e nunca junto com um Inventário aberto.

**Divergência**:
Uma **Carta** cuja **Quantidade** difere entre o **Binder** e o nosso acervo (inclui ter em um lado e não no outro). Cartas com quantidades iguais não são divergências e são ignoradas.

**Resolução**:
A decisão manual, por **Divergência**, em uma **Sincronização**: **Binder vence** (nossa Quantidade passa a ser a do Binder), **nosso vence** (o delta entra na Lista para o Binder) ou **ignorar** (nada muda; a Divergência reaparece na próxima Sincronização). Toda Divergência começa pendente, e uma Sincronização só pode ser commitada com todas elas resolvidas. Uma Sincronização aberta pode ser descartada sem efeito algum.

**Lista para o Binder**:
Resultado de uma **Sincronização**: uma linha `<delta>x<código>` por **Carta** cujas mudanças devem ir para o **Binder** (ex.: `4xEB01-001`, `-4xEB01-001`). O delta é a diferença a aplicar, não a quantidade final. Exibida apenas no momento do commit; não é guardada.

## Relationships

- Uma **Sincronização** consome exatamente um **CSV do Binder**
- Uma **Sincronização** tem zero ou mais **Divergências**, cada uma com no máximo uma **Resolução**
- Commitar uma **Sincronização** atualiza o nosso acervo e produz uma **Lista para o Binder**

## Example dialogue

> **Dev:** "O Binder tem 3 da `OP07-006` e nós temos 5. É uma **Divergência**?"
> **Dono:** "Sim. Se eu resolver que o nosso lado vence, a **Lista para o Binder** ganha `2xOP07-006`. Se o Binder vencer, nossa **Quantidade** vira 3."

## Flagged ambiguities

- Direção da verdade: descartado o snapshot da última sincronização (3-way); toda **Divergência** é resolvida manualmente a cada **Sincronização**.
