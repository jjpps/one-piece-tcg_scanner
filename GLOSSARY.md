# Glossário

**Lista de compras**
A única lista de cartas que o usuário ainda precisa adquirir. Colar um novo texto descarta a lista anterior e cria uma nova. Existe uma ação explícita de limpar.

**Item da lista**
Uma carta (identificada pelo código) com a quantidade que ainda falta comprar.

**Faltante**
Quantas unidades de uma carta ainda faltam comprar. Nasce como o pedido menos o que já existe no estoque, e só diminui quando uma carta entra. Retirar cartas do estoque depois não aumenta o faltante. Quando chega a zero, o item deixa de existir.

**Entrada**
O momento em que uma carta passa a existir no estoque: aprovação na revisão ou cadastro manual. Aplicar um inventário não é entrada, é ajuste de contagem.

**Estoque**
As cartas que o usuário possui, com quantidade por código. Variantes de arte não são distinguidas: o código é a identidade da carta.

**Coleção**
O conjunto de cartas que compartilham o mesmo prefixo de código (OP17, EB03). Uma carta pertence a exatamente uma coleção.

**Possuir**
Ter pelo menos uma unidade da carta no estoque. A quantidade acima de um não muda nada.

**Completude**
A porcentagem de uma coleção que o usuário possui: cartas possuídas dividido pelo total de cartas da coleção.
