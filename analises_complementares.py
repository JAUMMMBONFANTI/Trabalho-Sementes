from pathlib import Path
import csv
import cv2
import numpy as np
from inspecao_sementes import PASTA_BASE, PARAMETROS, listar_imagens
from experimento import (
    PASTA_DADOS, carregar_referencias, avaliar, resumir, salvar_csv, tabela_markdown,
)

PASTA_SAIDA = PASTA_BASE / "resultados" / "analises"
PASTA_EXPERIMENTO = PASTA_BASE / "resultados" / "experimento"
LARGURA_FOTO_MADEIRA = 4080
MARGEM_MIOLO = 0.25
IMAGEM_ANOTACAO_DEFEITUOSA = "pumpkin_0037.jpg"
CAIXAS_FORA_DAS_SEMENTES_VAL = {"pumpkin_0010.jpg"}

CONFIGURACAO_FINAL = {"nome": "matiz_c8_sep", "segmentacao": "matiz",
                      "conectividade": 8, "separacao": True}

VARIANTES = [
    ("pipeline final (núcleo relativo ao máximo do componente)", {}),
    ("núcleo relativo ao raio típico da foto (mediana dos máximos)",
     {"referencia_nucleo": "raio_tipico"}),
    ("preenchimento de buracos antes da separação", {"preencher_buracos": True}),
]


def cenario(imagem):
    return "madeira" if imagem.shape[1] == LARGURA_FOTO_MADEIRA else "prato"


def estatisticas_canais(split):
    referencias = carregar_referencias(split)
    linhas = []
    for caminho in listar_imagens(PASTA_DADOS / "photos" / split):
        imagem = cv2.imread(str(caminho))
        cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(imagem, cv2.COLOR_BGR2HSV)
        canais = {"cinza": cinza, "h": hsv[..., 0], "s": hsv[..., 1], "v": hsv[..., 2]}

        semente = np.zeros(cinza.shape, dtype=bool)
        dentro_caixas = np.zeros(cinza.shape, dtype=bool)
        for x, y, w, h in referencias[caminho.name]:
            x0, y0, x1, y1 = int(x), int(y), int(np.ceil(x + w)), int(np.ceil(y + h))
            dentro_caixas[y0:y1, x0:x1] = True
            mx, my = int(w * MARGEM_MIOLO), int(h * MARGEM_MIOLO)
            semente[y0 + my:y1 - my, x0 + mx:x1 - mx] = True
        fundo = ~dentro_caixas & (cinza > PARAMETROS["limiar_cinza_fundo"])

        for regiao, mascara in (("semente", semente), ("fundo", fundo)):
            if not mascara.any():
                continue
            if regiao == "semente" and caminho.name in CAIXAS_FORA_DAS_SEMENTES_VAL:
                continue
            linha = {"imagem": caminho.name, "cenario": cenario(imagem), "regiao": regiao}
            linha.update({nome: float(np.median(canal[mascara])) for nome, canal in canais.items()})
            linhas.append(linha)
    return linhas


def resumir_canais(linhas):
    resumo = []
    for cenario_atual in ("prato", "madeira"):
        for regiao in ("semente", "fundo"):
            grupo = [l for l in linhas if l["cenario"] == cenario_atual and l["regiao"] == regiao]
            linha = {"cenario": cenario_atual, "regiao": regiao, "imagens": len(grupo)}
            for canal in ("cinza", "h", "s", "v"):
                valores = [l[canal] for l in grupo]
                linha[canal] = f"{min(valores):.0f}-{max(valores):.0f}"
            resumo.append(linha)
    return resumo


def avaliar_variantes():
    linhas = []
    for descricao, ajuste in VARIANTES:
        p = dict(PARAMETROS, **ajuste)
        resumo = resumir(avaliar("val", CONFIGURACAO_FINAL, p))
        linhas.append({"variante": descricao, **{k: resumo[k] for k in (
            "n_previsto", "precisao", "recall", "f1", "mae_contagem")}})
        print(f"   {descricao}: F1 {resumo['f1']:.3f}")
    return linhas


def metricas_sem_anotacao_defeituosa():
    caminho = PASTA_EXPERIMENTO / "avaliacao_por_imagem.csv"
    if not caminho.exists():
        return None
    with open(caminho, encoding="utf-8") as arquivo:
        linhas = [l for l in csv.DictReader(arquivo)
                  if l["split"] == "test" and l["configuracao"] == CONFIGURACAO_FINAL["nome"]]
    resultado = []
    for descricao, grupo in (
        ("todas as fotos do teste", linhas),
        (f"sem {IMAGEM_ANOTACAO_DEFEITUOSA}",
         [l for l in linhas if l["imagem"] != IMAGEM_ANOTACAO_DEFEITUOSA]),
    ):
        vp = sum(int(l["vp"]) for l in grupo)
        previsto = sum(int(l["n_previsto"]) for l in grupo)
        referencia = sum(int(l["n_referencia"]) for l in grupo)
        resultado.append({
            "conjunto": descricao,
            "imagens": len(grupo),
            "precisao": vp / previsto,
            "recall": vp / referencia,
            "f1": 2 * vp / (previsto + referencia),
        })
    return resultado


def main():
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    relatorio = ["# Análises complementares\n\n"
                 "Executadas somente sobre a validação, exceto o item 3, que apenas "
                 "relê os resultados de teste já gravados por `experimento.py`.\n"]

    print("1) Estatísticas dos canais dentro e fora das caixas de referência (validação)...")
    canais = estatisticas_canais("val")
    salvar_csv(PASTA_SAIDA / "canais_validacao.csv", canais)
    resumo_canais = resumir_canais(canais)
    salvar_csv(PASTA_SAIDA / "canais_resumo.csv", resumo_canais)
    relatorio.append(
        "\n## 1. Mediana dos canais por foto (faixa mínima-máxima entre as fotos)\n\n"
        f"Semente: miolo das caixas de referência (margem de {MARGEM_MIOLO:.0%} em cada lado). "
        "Fundo: pixels fora de todas as caixas com cinza > "
        f"{PARAMETROS['limiar_cinza_fundo']} (exclui os cantos pretos do prato). "
        "H na escala 0-179 do OpenCV. "
        f"{', '.join(sorted(CAIXAS_FORA_DAS_SEMENTES_VAL))} fica fora da linha de semente "
        "porque suas caixas de referência estão sobre o fundo.\n\n")
    relatorio.append(tabela_markdown(resumo_canais, list(resumo_canais[0].keys())))

    print("2) Variantes da separação descartadas (validação)...")
    variantes = avaliar_variantes()
    salvar_csv(PASTA_SAIDA / "variantes_validacao.csv", variantes)
    relatorio.append("\n## 2. Variantes da separação (validação, matiz + c8 + separação)\n\n")
    relatorio.append(tabela_markdown(variantes, list(variantes[0].keys())))

    print("3) Métricas do teste sem a foto com anotação defeituosa...")
    exclusao = metricas_sem_anotacao_defeituosa()
    if exclusao is None:
        print("   avaliacao_por_imagem.csv não encontrado; execute experimento.py antes.")
    else:
        salvar_csv(PASTA_SAIDA / "teste_sem_anotacao_defeituosa.csv", exclusao)
        relatorio.append(f"\n## 3. Teste com e sem {IMAGEM_ANOTACAO_DEFEITUOSA} "
                         f"({CONFIGURACAO_FINAL['nome']})\n\n")
        relatorio.append(tabela_markdown(exclusao, list(exclusao[0].keys())))
        for linha in exclusao:
            print(f"   {linha['conjunto']}: F1 {linha['f1']:.3f}")

    with open(PASTA_SAIDA / "analises.md", "w", encoding="utf-8") as arquivo:
        arquivo.write("".join(relatorio))
    print(f"Resultados salvos em {PASTA_SAIDA}")


if __name__ == "__main__":
    main()
