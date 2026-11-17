# Análises complementares

Executadas somente sobre a validação, exceto o item 3, que apenas relê os resultados de teste já gravados por `experimento.py`.

## 1. Mediana dos canais por foto (faixa mínima-máxima entre as fotos)

Semente: miolo das caixas de referência (margem de 25% em cada lado). Fundo: pixels fora de todas as caixas com cinza > 20 (exclui os cantos pretos do prato). H na escala 0-179 do OpenCV. pumpkin_0010.jpg fica fora da linha de semente porque suas caixas de referência estão sobre o fundo.

| cenario | regiao | imagens | cinza | h | s | v |
|---|---|---|---|---|---|---|
| prato | semente | 7 | 113-136 | 20-21 | 157-173 | 142-167 |
| prato | fundo | 8 | 77-86 | 14-15 | 105-114 | 95-104 |
| madeira | semente | 6 | 139-164 | 20-21 | 137-159 | 171-193 |
| madeira | fundo | 6 | 139-147 | 14-15 | 163-177 | 193-201 |

## 2. Variantes da separação (validação, matiz + c8 + separação)

| variante | n_previsto | precisao | recall | f1 | mae_contagem |
|---|---|---|---|---|---|
| pipeline final (núcleo relativo ao máximo do componente) | 316 | 0.905 | 0.724 | 0.805 | 5.643 |
| núcleo relativo ao raio típico da foto (mediana dos máximos) | 294 | 0.861 | 0.641 | 0.734 | 7.214 |
| preenchimento de buracos antes da separação | 280 | 0.900 | 0.638 | 0.747 | 8.214 |

## 3. Teste com e sem pumpkin_0037.jpg (matiz_c8_sep)

| conjunto | imagens | precisao | recall | f1 |
|---|---|---|---|---|
| todas as fotos do teste | 15 | 0.853 | 0.683 | 0.758 |
| sem pumpkin_0037.jpg | 14 | 0.881 | 0.721 | 0.793 |
