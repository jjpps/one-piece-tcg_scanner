# Spec: Collection Tracker

Referência visual: https://i.redd.it/sqlavh8sp7s91.jpg (tela "Set Collection" do MTG Arena).

## Objetivo

Na tela inicial (hoje só o mega menu), mostrar quanto do total de cada coleção o usuário já possui, em %.
Coleção = prefixo do código da carta (OP17, EB03, ...).

## O que a imagem mostra

**Cabeçalho**
- Seta de voltar à esquerda e o título "Set Collection".
- Abaixo, um select de ordenação com o valor "Newest to Oldest" (mais nova primeiro).

**Grade de medalhões**
- 5 por linha, 3 linhas visíveis (15 coleções), com bastante espaço entre eles.
- Cada coleção é um medalhão: um círculo escuro com o ícone da coleção em branco no centro, e uma moldura metálica em formato de brasão/escudo, com uma pequena seta apontando para baixo na base.
- Não há texto no medalhão: nem nome, nem código, nem número.

**Indicador de progresso**
- Um anel azul brilhante ao redor do círculo é o progresso. Ele preenche no sentido horário a partir do topo, proporcional à % da coleção.
- A parte não preenchida do anel fica escura/vazia (visível no medalhão da 2ª linha, 5ª coluna, com cerca de 35% preenchido).
- A grande maioria dos medalhões está com o anel quase ou totalmente cheio. Dois estão claramente incompletos: o da 2ª linha, 5ª coluna e o da 3ª linha, 2ª coluna (cerca de 30%).

**Estado de coleção completa**
- O medalhão da 3ª linha, 1ª coluna é dourado, com anel e brasão dourados, e é visualmente maior e mais brilhante que os demais.
- Dourado = 100%. É o único destaque de "completo" e se distingue à primeira vista dos azuis.

**Fundo**
- Ilustração desfocada e escurecida com overlay, para os medalhões se destacarem.

## Adaptação para o nosso projeto

- Um medalhão por coleção, agrupando as cartas do estoque pelo prefixo do código.
- O anel de progresso = (cartas distintas que possuímos da coleção) / (total de cartas da coleção).
- Anel azul para incompleta e dourado para 100%, como na referência.
- O ícone central vira o próprio código (OP17, EB03), já que não temos ícone por coleção.
- Ordenação padrão: da coleção mais nova para a mais antiga, com o mesmo select de ordenação.
- A % em texto fica sob o medalhão ou em tooltip. A referência não mostra número, mas sem ele não dá para distinguir 91% de 99%.
- A grade é responsiva: 5 colunas no desktop e menos no mobile.

## Perguntas em aberto

1. **Total de cada coleção:** de onde vem o número de cartas que a coleção tem? O backend não parece ter esse catálogo.
2. **O que conta como "possuir":** uma carta com quantidade >= 1 (cartas distintas) ou o playset de 4 por carta?
3. **Variantes de arte:** o glossário diz que elas não são distinguidas. Isso vale para o total da coleção também?
4. **Coleções sem nenhuma carta:** aparecem com o anel vazio ou ficam ocultas?
5. **Clique no medalhão:** leva para a library filtrada pela coleção?
