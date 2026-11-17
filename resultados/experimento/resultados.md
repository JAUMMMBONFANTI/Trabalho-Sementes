# Resultados da investigação experimental
- Conectividade 4: 14/14 imagens idênticas ao OpenCV; tempo médio próprio 67.7 ms, OpenCV 2.12 ms
- Conectividade 8: 14/14 imagens idênticas ao OpenCV; tempo médio próprio 81.7 ms, OpenCV 1.70 ms

## Ajuste na validação

| matiz_min | fracao_distancia | precisao | recall | f1 | mae_contagem |
|---|---|---|---|---|---|
| 17 | 0.500 | 0.861 | 0.641 | 0.734 | 7.214 |
| 17 | 0.600 | 0.899 | 0.696 | 0.785 | 6.357 |
| 17 | 0.700 | 0.907 | 0.691 | 0.784 | 6.714 |
| 18 | 0.500 | 0.867 | 0.658 | 0.748 | 6.786 |
| 18 | 0.600 | 0.905 | 0.724 | 0.805 | 5.643 |
| 18 | 0.700 | 0.885 | 0.719 | 0.793 | 5.286 |
| 19 | 0.500 | 0.848 | 0.651 | 0.736 | 6.571 |
| 19 | 0.600 | 0.855 | 0.714 | 0.778 | 4.643 |
| 19 | 0.700 | 0.787 | 0.653 | 0.714 | 4.786 |

Escolhido: matiz_min=18, fracao_distancia=0.6

## Validação

| configuracao | n_referencia | n_previsto | precisao | recall | f1 | mae_contagem | erro_contagem_rel | iou_medio | tempo_rotulagem_ms | tempo_total_ms |
|---|---|---|---|---|---|---|---|---|---|---|
| cinza_c4_simples | 395 | 739 | 0.173 | 0.324 | 0.226 | 31.000 | 6.623 | 0.832 | 89.379 | 116.843 |
| cinza_c8_simples | 395 | 727 | 0.176 | 0.324 | 0.228 | 30.571 | 6.488 | 0.832 | 121.308 | 148.793 |
| cinza_c4_sep | 395 | 595 | 0.210 | 0.316 | 0.253 | 21.714 | 3.784 | 0.760 | 157.825 | 180.496 |
| cinza_c8_sep | 395 | 571 | 0.221 | 0.319 | 0.261 | 20.286 | 3.692 | 0.756 | 189.301 | 211.502 |
| matiz_c4_simples | 395 | 220 | 0.773 | 0.430 | 0.553 | 12.500 | 0.326 | 0.895 | 59.346 | 80.204 |
| matiz_c8_simples | 395 | 220 | 0.773 | 0.430 | 0.553 | 12.500 | 0.326 | 0.895 | 72.098 | 95.506 |
| matiz_c4_sep | 395 | 318 | 0.896 | 0.722 | 0.799 | 5.500 | 0.165 | 0.819 | 117.205 | 137.296 |
| matiz_c8_sep | 395 | 316 | 0.905 | 0.724 | 0.805 | 5.643 | 0.168 | 0.822 | 135.134 | 155.126 |

Configuração escolhida pela validação: **matiz_c8_sep**

## Teste (avaliação final)

| configuracao | n_referencia | n_previsto | precisao | recall | f1 | mae_contagem | erro_contagem_rel | iou_medio | tempo_rotulagem_ms | tempo_total_ms |
|---|---|---|---|---|---|---|---|---|---|---|
| cinza_c4_simples | 432 | 340 | 0.400 | 0.315 | 0.352 | 8.267 | 0.304 | 0.806 | 86.240 | 111.166 |
| cinza_c8_simples | 432 | 332 | 0.416 | 0.319 | 0.361 | 8.800 | 0.317 | 0.807 | 110.618 | 134.987 |
| cinza_c4_sep | 432 | 332 | 0.452 | 0.347 | 0.393 | 7.067 | 0.230 | 0.747 | 146.103 | 166.870 |
| cinza_c8_sep | 432 | 323 | 0.455 | 0.340 | 0.389 | 7.533 | 0.240 | 0.748 | 180.708 | 201.431 |
| matiz_c4_simples | 432 | 206 | 0.655 | 0.312 | 0.423 | 15.067 | 0.451 | 0.902 | 63.888 | 85.123 |
| matiz_c8_simples | 432 | 203 | 0.660 | 0.310 | 0.422 | 15.267 | 0.455 | 0.902 | 84.164 | 106.106 |
| matiz_c4_sep | 432 | 351 | 0.835 | 0.678 | 0.748 | 5.400 | 0.177 | 0.832 | 128.194 | 149.516 |
| matiz_c8_sep | 432 | 346 | 0.853 | 0.683 | 0.758 | 5.733 | 0.188 | 0.835 | 147.920 | 168.499 |

## Erro de medição no teste (pares casados)

| configuracao | iou_medio | erro_largura_rel | erro_altura_rel |
|---|---|---|---|
| cinza_c4_simples | 0.806 | 0.102 | 0.104 |
| cinza_c8_simples | 0.807 | 0.101 | 0.105 |
| cinza_c4_sep | 0.747 | 0.151 | 0.129 |
| cinza_c8_sep | 0.748 | 0.151 | 0.128 |
| matiz_c4_simples | 0.902 | 0.059 | 0.049 |
| matiz_c8_simples | 0.902 | 0.059 | 0.050 |
| matiz_c4_sep | 0.832 | 0.101 | 0.081 |
| matiz_c8_sep | 0.835 | 0.098 | 0.080 |

## Teste por imagem (matiz_c8_sep)

| imagem | n_referencia | n_previsto | vp | fp | fn | f1 | erro_contagem | tempo_total_ms |
|---|---|---|---|---|---|---|---|---|
| pumpkin_0005.jpg | 47 | 38 | 33 | 5 | 14 | 0.776 | -9 | 251.395 |
| pumpkin_0012.jpg | 9 | 8 | 8 | 0 | 1 | 0.941 | -1 | 143.863 |
| pumpkin_0015.jpg | 29 | 23 | 22 | 1 | 7 | 0.846 | -6 | 160.414 |
| pumpkin_0020.jpg | 22 | 19 | 19 | 0 | 3 | 0.927 | -3 | 141.413 |
| pumpkin_0037.jpg | 23 | 11 | 0 | 11 | 23 | 0.000 | -12 | 114.550 |
| pumpkin_0038.jpg | 18 | 15 | 13 | 2 | 5 | 0.788 | -3 | 174.305 |
| pumpkin_0043.jpg | 12 | 11 | 11 | 0 | 1 | 0.957 | -1 | 103.104 |
| pumpkin_0057.jpg | 4 | 3 | 2 | 1 | 2 | 0.571 | -1 | 129.727 |
| pumpkin_0067.jpg | 55 | 41 | 33 | 8 | 22 | 0.688 | -14 | 271.035 |
| pumpkin_0074.jpg | 23 | 20 | 18 | 2 | 5 | 0.837 | -3 | 185.545 |
| pumpkin_0080.jpg | 90 | 75 | 67 | 8 | 23 | 0.812 | -15 | 127.132 |
| pumpkin_0099.jpg | 13 | 12 | 11 | 1 | 2 | 0.880 | -1 | 154.327 |
| pumpkin_0101.jpg | 31 | 23 | 19 | 4 | 12 | 0.704 | -8 | 204.215 |
| pumpkin_0104.jpg | 15 | 14 | 13 | 1 | 2 | 0.897 | -1 | 138.287 |
| pumpkin_0110.jpg | 41 | 33 | 26 | 7 | 15 | 0.703 | -8 | 228.170 |
