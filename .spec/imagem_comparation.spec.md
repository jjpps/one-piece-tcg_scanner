# Imagem Comparation Spec

## Feature as is today

- Temos a tela de `frontend/src/app/pages/cards-review/cards-review.html` nela fazemos a comparaçao da `local_image_url` e da `card_image`, sendo a `local_image_url` uma foto da carta e a `card_image` a imagem oficial da carta.
- essa tela como intuido permitir que o usuario veja a foto tirada da carta e identificada pelo OCR e a imagem oficial da carta, para realizar uma validação manual. alem disso se o usuario decidir que a imamge esta aprovada ela é enviada a biblioteca, se o usuario decide que a imagem identificada nao bate com a imagem oficial ele envia a carta para correçao manual.
- usamos uma ia local atraves do ollama para identificar o codigo das cartas `backend/image_tools/llm_processor.py`

## Problemas
1. hoje essa tela esta muito mal estruturada, sendo a foto da imagem em proporções muito diferentes da imagem oficial da carta, fazendo com que o usuario aprove cartas que deveria ser enviadas para correçao manual.
2. O metodo `_extrair_id_via_llm` esse metodo ou prompt possui um problema as vezes quando o modelo nao consegue identificar a carta ou algum outro problema de identifica interno ocorre ele sempre lança de retorno o codigo "EB03-021". fazendo com que varias cartas seja relacionadas a esse codigo. 
2. Atualmente o metodo  `_extrair_id_via_llm` só permite identificaçao de cartas do tipo OP e EB porem possuimos outras prefixos que precisam ser adicionados (OP/ST/EB/PRB/P). Exemplo de cartas com cada um dos prefixos
    - OP01-001
    - ST01-005
    - EB03-021
    - PRB02-001
    - P-041

## Desejo

1. Para a tela de `frontend/src/app/pages/cards-review/cards-review.html` gostaria que ambas as imagens ficassem do mesmo tamanho e se possivel fazer um comparassion Slider.
2. TBD
3. TBD