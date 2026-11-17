from itertools import product
from pathlib import Path
import csv
import json
import time
import cv2
import numpy as np
from inspecao_sementes import (
    PASTA_BASE, PARAMETROS, processar_imagem, rotular_componentes,
    redimensionar, segmentar, salvar, listar_imagens,
)

PASTA_DADOS = PASTA_BASE / "dados"
PASTA_SAIDA = PASTA_BASE / "resultados" / "experimento"
CATEGORIA_ABOBORA = 3
LIMIAR_IOU = 0.5

GRADE_AJUSTE = {
    "matiz_min": [17, 18, 19],
    "fracao_distancia": [0.5, 0.6, 0.7],
}

CONFIGURACOES = [
    {"nome": f"{seg}_c{con}_{'sep' if sep else 'simples'}",
     "segmentacao": seg, "conectividade": con, "separacao": sep}
    for seg, sep, con in product(["cinza", "matiz"], [False, True], [4, 8])
]


def carregar_referencias(split):
    with open(PASTA_DADOS / "annotations" / f"{split}_photos.json", encoding="utf-8") as arquivo:
        coco = json.load(arquivo)
    nomes = {img["id"]: img["file_name"] for img in coco["images"]
             if img["file_name"].startswith("pumpkin")}
    referencias = {nome: [] for nome in nomes.values()}
    for anotacao in coco["annotations"]:
        if anotacao["image_id"] in nomes and anotacao["category_id"] == CATEGORIA_ABOBORA:
            referencias[nomes[anotacao["image_id"]]].append(anotacao["bbox"])
    return referencias


def iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    return inter / (aw * ah + bw * bh - inter)


def comparar(previstas, referencias):
    candidatos = sorted(
        ((iou(p, r), i, j) for i, p in enumerate(previstas)
         for j, r in enumerate(referencias)),
        reverse=True,
    )
    usadas_p, usadas_r, pares = set(), set(), []
    for valor, i, j in candidatos:
        if valor < LIMIAR_IOU:
            break
        if i in usadas_p or j in usadas_r:
            continue
        usadas_p.add(i)
        usadas_r.add(j)
        pares.append((i, j, valor))
    return pares


def avaliar(split, configuracao, p, pasta_comparacao=None):
    referencias = carregar_referencias(split)
    linhas = []
    for caminho in listar_imagens(PASTA_DADOS / "photos" / split):
        imagem = cv2.imread(str(caminho))
        if imagem is None:
            raise FileNotFoundError(f"Não foi possível abrir a imagem: {caminho}")

        resultado = processar_imagem(imagem, configuracao["segmentacao"],
                                     configuracao["conectividade"],
                                     configuracao["separacao"], p)
        objetos = resultado["objetos"]
        previstas = [[o["x"], o["y"], o["largura"], o["altura"]] for o in objetos]
        gt = referencias[caminho.name]
        pares = comparar(previstas, gt)

        tp = len(pares)
        erro_largura = [abs(previstas[i][2] - gt[j][2]) / gt[j][2] for i, j, _ in pares]
        erro_altura = [abs(previstas[i][3] - gt[j][3]) / gt[j][3] for i, j, _ in pares]
        linhas.append({
            "configuracao": configuracao["nome"],
            "split": split,
            "imagem": caminho.name,
            "n_referencia": len(gt),
            "n_previsto": len(previstas),
            "vp": tp,
            "fp": len(previstas) - tp,
            "fn": len(gt) - tp,
            "precisao": tp / len(previstas) if previstas else 0.0,
            "recall": tp / len(gt) if gt else 0.0,
            "f1": 2 * tp / (len(previstas) + len(gt)) if (previstas or gt) else 1.0,
            "erro_contagem": len(previstas) - len(gt),
            "iou_medio": float(np.mean([v for _, _, v in pares])) if pares else 0.0,
            "erro_largura_rel": float(np.mean(erro_largura)) if pares else 0.0,
            "erro_altura_rel": float(np.mean(erro_altura)) if pares else 0.0,
            "tempo_segmentacao_ms": resultado["tempo_segmentacao_ms"],
            "tempo_rotulagem_ms": resultado["tempo_rotulagem_ms"],
            "tempo_total_ms": resultado["tempo_total_ms"],
        })

        if pasta_comparacao is not None:
            saida = imagem.copy()
            espessura = max(2, max(imagem.shape[:2]) // 500)
            for x, y, w, h in gt:
                cv2.rectangle(saida, (int(x), int(y)), (int(x + w), int(y + h)),
                              (255, 0, 0), espessura)
            casadas = {i for i, _, _ in pares}
            for indice, (x, y, w, h) in enumerate(previstas):
                cor = (0, 255, 0) if indice in casadas else (0, 0, 255)
                cv2.rectangle(saida, (int(x), int(y)), (int(x + w), int(y + h)),
                              cor, espessura)
            salvar(pasta_comparacao / caminho.name, saida)
    return linhas


def resumir(linhas):
    vp = sum(l["vp"] for l in linhas)
    n_prev = sum(l["n_previsto"] for l in linhas)
    n_ref = sum(l["n_referencia"] for l in linhas)
    com_pares = [l for l in linhas if l["vp"] > 0]
    return {
        "configuracao": linhas[0]["configuracao"],
        "split": linhas[0]["split"],
        "imagens": len(linhas),
        "n_referencia": n_ref,
        "n_previsto": n_prev,
        "precisao": vp / n_prev if n_prev else 0.0,
        "recall": vp / n_ref if n_ref else 0.0,
        "f1": 2 * vp / (n_prev + n_ref) if (n_prev + n_ref) else 0.0,
        "mae_contagem": float(np.mean([abs(l["erro_contagem"]) for l in linhas])),
        "erro_contagem_rel": float(np.mean([abs(l["erro_contagem"]) / l["n_referencia"]
                                            for l in linhas if l["n_referencia"]])),
        "iou_medio": float(np.mean([l["iou_medio"] for l in com_pares])) if com_pares else 0.0,
        "erro_largura_rel": float(np.mean([l["erro_largura_rel"] for l in com_pares])) if com_pares else 0.0,
        "erro_altura_rel": float(np.mean([l["erro_altura_rel"] for l in com_pares])) if com_pares else 0.0,
        "tempo_rotulagem_ms": float(np.mean([l["tempo_rotulagem_ms"] for l in linhas])),
        "tempo_total_ms": float(np.mean([l["tempo_total_ms"] for l in linhas])),
    }


def verificar_rotulagem(split, p):
    linhas = []
    for caminho in listar_imagens(PASTA_DADOS / "photos" / split):
        imagem = cv2.imread(str(caminho))
        reduzida, _ = redimensionar(imagem, p["lado_trabalho"])
        mascara = segmentar(reduzida, "matiz", p)
        for conectividade in (4, 8):
            inicio = time.perf_counter()
            total, rotulos = rotular_componentes(mascara, conectividade)
            tempo_proprio = (time.perf_counter() - inicio) * 1000

            inicio = time.perf_counter()
            total_cv, rotulos_cv = cv2.connectedComponents(mascara, connectivity=conectividade)
            tempo_opencv = (time.perf_counter() - inicio) * 1000

            areas = np.sort(np.bincount(rotulos.ravel())[1:])
            areas_cv = np.sort(np.bincount(rotulos_cv.ravel())[1:])
            linhas.append({
                "imagem": caminho.name,
                "conectividade": conectividade,
                "componentes_proprio": total,
                "componentes_opencv": total_cv - 1,
                "areas_identicas": bool(np.array_equal(areas, areas_cv)),
                "tempo_proprio_ms": tempo_proprio,
                "tempo_opencv_ms": tempo_opencv,
            })
    return linhas


def salvar_csv(caminho, linhas):
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0].keys()))
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({k: round(v, 4) if isinstance(v, float) else v
                               for k, v in linha.items()})


def tabela_markdown(linhas, campos):
    texto = "| " + " | ".join(campos) + " |\n"
    texto += "|" + "---|" * len(campos) + "\n"
    for linha in linhas:
        valores = [f"{linha[c]:.3f}" if isinstance(linha[c], float) else str(linha[c])
                   for c in campos]
        texto += "| " + " | ".join(valores) + " |\n"
    return texto


def main():
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    relatorio = ["# Resultados da investigação experimental\n"]

    print("1) Verificando a rotulagem própria contra cv2.connectedComponents (validação)...")
    verificacao = verificar_rotulagem("val", PARAMETROS)
    salvar_csv(PASTA_SAIDA / "verificacao_rotulagem.csv", verificacao)
    for conectividade in (4, 8):
        grupo = [l for l in verificacao if l["conectividade"] == conectividade]
        iguais = sum(l["areas_identicas"] for l in grupo)
        relatorio.append(
            f"- Conectividade {conectividade}: {iguais}/{len(grupo)} imagens idênticas ao OpenCV; "
            f"tempo médio próprio {np.mean([l['tempo_proprio_ms'] for l in grupo]):.1f} ms, "
            f"OpenCV {np.mean([l['tempo_opencv_ms'] for l in grupo]):.2f} ms\n")
    print("".join(relatorio[1:]))

    print("2) Ajuste de parâmetros somente na validação...")
    referencia_ajuste = {"nome": "matiz_c8_sep", "segmentacao": "matiz",
                         "conectividade": 8, "separacao": True}
    ajuste = []
    for valores in product(*GRADE_AJUSTE.values()):
        p = dict(PARAMETROS, **dict(zip(GRADE_AJUSTE.keys(), valores)))
        resumo = resumir(avaliar("val", referencia_ajuste, p))
        ajuste.append(dict(zip(GRADE_AJUSTE.keys(), valores), **{
            k: resumo[k] for k in ("precisao", "recall", "f1", "mae_contagem")}))
        print(f"   {dict(zip(GRADE_AJUSTE.keys(), valores))} -> F1 {resumo['f1']:.3f}")
    salvar_csv(PASTA_SAIDA / "ajuste_validacao.csv", ajuste)
    melhor = max(ajuste, key=lambda l: l["f1"])
    parametros = dict(PARAMETROS, **{k: melhor[k] for k in GRADE_AJUSTE})
    relatorio.append("\n## Ajuste na validação\n\n")
    relatorio.append(tabela_markdown(ajuste, list(ajuste[0].keys())))
    relatorio.append(f"\nEscolhido: {', '.join(f'{k}={melhor[k]}' for k in GRADE_AJUSTE)}\n")

    print("3) Comparação das configurações na validação...")
    resumo_val, por_imagem = [], []
    for configuracao in CONFIGURACOES:
        linhas = avaliar("val", configuracao, parametros)
        por_imagem += linhas
        resumo_val.append(resumir(linhas))
        print(f"   {configuracao['nome']}: F1 {resumo_val[-1]['f1']:.3f}")
    escolhida = max(resumo_val, key=lambda l: l["f1"])["configuracao"]

    print(f"4) Avaliação final no teste (configuração escolhida na validação: {escolhida})...")
    resumo_teste = []
    for configuracao in CONFIGURACOES:
        pasta = None
        if configuracao["nome"] == escolhida:
            pasta = PASTA_SAIDA / "comparacao_teste"
            pasta.mkdir(exist_ok=True)
        linhas = avaliar("test", configuracao, parametros, pasta)
        por_imagem += linhas
        resumo_teste.append(resumir(linhas))
        print(f"   {configuracao['nome']}: F1 {resumo_teste[-1]['f1']:.3f}")

    salvar_csv(PASTA_SAIDA / "avaliacao_por_imagem.csv", por_imagem)
    salvar_csv(PASTA_SAIDA / "avaliacao_resumo.csv", resumo_val + resumo_teste)

    campos = ["configuracao", "n_referencia", "n_previsto", "precisao", "recall", "f1",
              "mae_contagem", "erro_contagem_rel", "iou_medio", "tempo_rotulagem_ms",
              "tempo_total_ms"]
    relatorio.append("\n## Validação\n\n" + tabela_markdown(resumo_val, campos))
    relatorio.append(f"\nConfiguração escolhida pela validação: **{escolhida}**\n")
    relatorio.append("\n## Teste (avaliação final)\n\n" + tabela_markdown(resumo_teste, campos))
    relatorio.append("\n## Erro de medição no teste (pares casados)\n\n" + tabela_markdown(
        resumo_teste, ["configuracao", "iou_medio", "erro_largura_rel", "erro_altura_rel"]))
    detalhe = [l for l in por_imagem if l["split"] == "test" and l["configuracao"] == escolhida]
    relatorio.append(f"\n## Teste por imagem ({escolhida})\n\n" + tabela_markdown(
        detalhe, ["imagem", "n_referencia", "n_previsto", "vp", "fp", "fn", "f1",
                  "erro_contagem", "tempo_total_ms"]))

    with open(PASTA_SAIDA / "resultados.md", "w", encoding="utf-8") as arquivo:
        arquivo.write("".join(relatorio))
    print(f"Resultados salvos em {PASTA_SAIDA}")


if __name__ == "__main__":
    main()
