# Inspeção e quantificação de sementes de abóbora

Trabalho de Processamento de Imagens com OpenCV - Grau B.

**Integrantes:** João Pedro Bonfanti, Laura Pinzon e Matheus Viegas.

O sistema localiza, conta e mede sementes de abóbora em fotografias usando apenas processamento clássico de imagens (Python, OpenCV e NumPy). Ele gera imagens anotadas e tabelas CSV com as medições, além de uma investigação experimental com 8 configurações do pipeline.

---

## 1. Combinação sorteada

| Item | Valor |
|---|---|
| Combinação sorteada | **3** |
| Tema | 1 - Inspeção e quantificação de grãos e sementes |
| Subtema | Semente de abóbora: detectar, contar e medir os objetos da classe *pumpkin seeds* |
| Classe na base | `pumpkin` (`category_id = 3` nas anotações COCO) |
| Componente algorítmico | Rotulagem de componentes conexos por busca em largura (BFS), com conectividade 4 ou 8: função `rotular_componentes` em `inspecao_sementes.py` |

## 2. Parte da base utilizada

**Base:** Grain Detection Dataset, `niru-5/manama_course_dataset_grain_detection` (Hugging Face), licença CC BY-NC 4.0.
https://huggingface.co/datasets/niru-5/manama_course_dataset_grain_detection

| Conjunto | Arquivos | Fotos | Caixas de referência | Uso |
|---|---|---|---|---|
| Validação | `photos/val/pumpkin_*.jpg` + `annotations/val_photos.json` | 14 | 395 | ajuste de parâmetros e escolha da configuração |
| Teste | `photos/test/pumpkin_*.jpg` + `annotations/test_photos.json` | 15 | 432 | avaliação final, executada uma única vez |

- **Validação:** pumpkin_0004, 0009, 0010, 0028, 0056, 0061, 0075, 0076, 0082, 0091, 0092, 0096, 0103 e 0107.
- **Teste:** pumpkin_0005, 0012, 0015, 0020, 0037, 0038, 0043, 0057, 0067, 0074, 0080, 0099, 0101, 0104 e 0110.

Observações:

- São usadas as **fotografias completas**. Os recortes anotados (`coco/*/images`), o conjunto de treino e as demais classes da base não são usados.
- As anotações servem **somente como referência de avaliação** e nunca entram na detecção.
- Os 29 arquivos de foto e os 2 de anotação em `dados/` estão sem modificação: conferem com os checksums SHA-256 da base (`dados/checksums.sha256`).
- Nenhuma imagem foi criada ou alterada artificialmente.

---

## 3. Instalação

Requer **Python 3.10 ou mais recente** (testado com Python 3.14.2, NumPy 2.5.5 e OpenCV 5.0.0).

Dentro da pasta do trabalho, siga os comandos do seu sistema.

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Se o PowerShell bloquear a ativação, rode antes `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`. No Prompt de Comando (cmd), use `.venv\Scripts\activate.bat`.

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

O `requirements.txt` instala apenas `numpy` e `opencv-python`.

## 4. Dados

A pasta `dados/` já acompanha o trabalho, então não é preciso baixar nada. Para baixá-la novamente da base original:

```bash
pip install huggingface_hub
hf download niru-5/manama_course_dataset_grain_detection --repo-type dataset --include "photos/*/pumpkin_*" "annotations/*" --local-dir dados
```

Estrutura esperada:

```
dados/
  photos/val/pumpkin_*.jpg
  photos/test/pumpkin_*.jpg
  annotations/val_photos.json
  annotations/test_photos.json
```

---

## 5. Execução

Com o ambiente ativado, rode os comandos na ordem abaixo para reproduzir todos os resultados:

```bash
python inspecao_sementes.py --split test     # relatório de inspeção do teste
python inspecao_sementes.py --split val      # relatório de inspeção da validação
python experimento.py                        # investigação experimental (alguns minutos)
python analises_complementares.py            # análises complementares (depois do experimento)
```

> Sem ativar o ambiente, troque `python` por `.venv\Scripts\python.exe` (Windows) ou `.venv/bin/python` (Linux/macOS).

### 5.1 Relatório de inspeção - `inspecao_sementes.py`

Processa automaticamente todas as fotos de uma pasta. Para cada foto, ele encontra as sementes, conta, mede, desenha as regiões e grava as tabelas.

| Opção | Padrão | Descrição |
|---|---|---|
| `--split` | `test` | conjunto da base a processar (`val` ou `test`) |
| `--entrada` | `dados/photos/<split>` | qualquer outra pasta com fotos `.jpg`/`.png` |
| `--saida` | `resultados/<split>` | pasta de saída |
| `--segmentacao` | `matiz` | `matiz` (HSV) ou `cinza` (Otsu em tons de cinza) |
| `--conectividade` | `8` | `4` ou `8` |
| `--sem-separacao` | desligado | desliga a separação de sementes encostadas |

Exemplo com fotos próprias:

```bash
python inspecao_sementes.py --entrada minhas_fotos --saida resultados/minhas_fotos
```

Saídas em `resultados/<split>/`:

| Arquivo | Conteúdo |
|---|---|
| `anotadas/*.jpg` | foto com contorno (verde), caixa (vermelho) e número de cada semente, mais a contagem total |
| `mascaras/*.png` | máscara binária objeto/fundo |
| `medicoes.csv` | uma linha por semente: `x, y, largura, altura, area_px, razao_aspecto, comprimento_eixo, largura_eixo, alongamento, centro_x, centro_y` (em pixels da foto original) |
| `resumo_imagens.csv` | uma linha por foto: dimensões, quantidade, área média e mediana, alongamento médio e tempo |

### 5.2 Investigação experimental - `experimento.py`

Executa, em ordem:

1. verificação da BFS própria contra `cv2.connectedComponents`;
2. grade de ajuste de parâmetros, somente na validação;
3. as 8 configurações ({cinza, matiz} × {sem, com separação} × {c4, c8}) na validação, com escolha da melhor pelo F1;
4. as 8 configurações no teste (avaliação final).

Saídas em `resultados/experimento/`:

| Arquivo | Conteúdo |
|---|---|
| `verificacao_rotulagem.csv` | componentes e tempos da BFS própria × OpenCV |
| `ajuste_validacao.csv` | resultados da grade de parâmetros (validação) |
| `avaliacao_por_imagem.csv` | métricas de cada foto em cada configuração |
| `avaliacao_resumo.csv` | métricas agregadas por configuração e conjunto |
| `resultados.md` | tabelas-resumo |
| `comparacao_teste/*.jpg` | referência (azul), detecções casadas (verde) e sem par (vermelho) da configuração escolhida |

### 5.3 Análises complementares - `analises_complementares.py`

Deve ser rodado depois de `experimento.py`. Gera em `resultados/analises/`:

| Arquivo | Conteúdo |
|---|---|
| `canais_validacao.csv`, `canais_resumo.csv` | mediana de cinza, H, S e V dentro e fora das caixas da validação (justifica a segmentação por matiz) |
| `variantes_validacao.csv` | as duas variantes da separação testadas e descartadas na validação |
| `teste_sem_anotacao_defeituosa.csv` | métricas do teste com e sem `pumpkin_0037.jpg`, que tem anotação defeituosa na base |
| `analises.md` | tabelas-resumo |

---

## 6. Resultado principal

Configuração escolhida na validação: **matiz (HSV), conectividade 8, com separação** (`matiz_c8_sep`).

| Conjunto | Precisão | Revocação | F1 (IoU ≥ 0,5) | Erro médio de contagem | Tempo médio por foto |
|---|---|---|---|---|---|
| Validação | 0,905 | 0,724 | 0,805 | 5,6 sementes | 126 ms |
| Teste | 0,853 | 0,683 | 0,758 | 5,7 sementes | 130 ms |

A análise completa está em `Relatorio_Trabalho_Sementes_Abobora.pdf`, e os dados de cada amostra estão em `Apendice_Resultados_Experimentos.pdf`.

## 7. Estrutura do projeto

```
trabalho_sementes_abobora/
  inspecao_sementes.py          pipeline: segmentação, rotulagem (BFS), separação, medição, desenho e CSV
  experimento.py                investigação experimental (validação e teste)
  analises_complementares.py    análise dos canais, variantes descartadas e teste sem pumpkin_0037
  requirements.txt              dependências (numpy, opencv-python)
  README.md                     este arquivo
  Relatorio_Trabalho_Sementes_Abobora.pdf    relatório técnico
  Apendice_Resultados_Experimentos.pdf       apêndice: fotos de comparação e CSVs de cada amostra
  dados/                        fotos e anotações da classe pumpkin (originais da base)
  resultados/
    val/  test/                 anotadas/, mascaras/, medicoes.csv, resumo_imagens.csv
    experimento/                CSVs da investigação, resultados.md, comparacao_teste/
    analises/                   CSVs e analises.md das análises complementares
```

## 8. Referências

- KUKKALA, N. *Grain Detection Dataset (course release)*. Hugging Face. Disponível em: https://huggingface.co/datasets/niru-5/manama_course_dataset_grain_detection. Licença CC BY-NC 4.0. Acesso em: 15 nov. 2026.
- Exemplos das Aulas 7 e 8 da disciplina (filtragem espacial, HSV, limiarização, morfologia, contornos, medição de tempo).
- GONZALEZ, R. C.; WOODS, R. E. *Processamento Digital de Imagens*. 3. ed. São Paulo: Pearson, 2010.
- ROSENFELD, A.; PFALTZ, J. L. Sequential operations in digital picture processing. *Journal of the ACM*, v. 13, n. 4, p. 471-494, 1966.
- OTSU, N. A threshold selection method from gray-level histograms. *IEEE Transactions on Systems, Man, and Cybernetics*, v. 9, n. 1, p. 62-66, 1979.
- BEUCHER, S.; MEYER, F. The morphological approach to segmentation: the watershed transformation. In: DOUGHERTY, E. (ed.). *Mathematical Morphology in Image Processing*. New York: Marcel Dekker, 1993.
- OPENCV. *OpenCV documentation*. Disponível em: https://docs.opencv.org/.
