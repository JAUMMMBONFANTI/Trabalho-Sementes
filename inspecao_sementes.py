from collections import deque
from pathlib import Path
import argparse
import csv
import time
import cv2
import numpy as np

PASTA_BASE = Path(__file__).resolve().parent

PARAMETROS = {
    "lado_trabalho": 1000,
    "kernel_suavizacao": (5, 5),
    "matiz_min": 18,
    "matiz_max": 40,
    "saturacao_min": 60,
    "valor_min": 60,
    "limiar_cinza_fundo": 20,
    "kernel_morfologia": 5,
    "preencher_buracos": False,
    "fracao_distancia": 0.6,
    "referencia_nucleo": "componente",
    "area_min_fracao_mediana": 0.25,
    "area_min_absoluta": 40,
}

CAMPOS_MEDICOES = [
    "imagem", "id", "x", "y", "largura", "altura", "area_px",
    "razao_aspecto", "comprimento_eixo", "largura_eixo", "alongamento",
    "centro_x", "centro_y",
]


def rotular_componentes(binaria, conectividade=8):
    if conectividade == 4:
        passos = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    elif conectividade == 8:
        passos = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                  (0, 1), (1, -1), (1, 0), (1, 1)]
    else:
        raise ValueError("A conectividade deve ser 4 ou 8.")

    altura, largura = binaria.shape
    largura_borda = largura + 2
    deslocamentos = [dy * largura_borda + dx for dy, dx in passos]

    frente = np.pad(binaria > 0, 1)
    pendentes = frente.ravel().tolist()
    rotulos = [0] * len(pendentes)
    total = 0

    for inicio in np.flatnonzero(frente).tolist():
        if not pendentes[inicio]:
            continue
        total += 1
        pendentes[inicio] = False
        rotulos[inicio] = total
        fila = deque([inicio])
        while fila:
            atual = fila.popleft()
            for deslocamento in deslocamentos:
                vizinho = atual + deslocamento
                if pendentes[vizinho]:
                    pendentes[vizinho] = False
                    rotulos[vizinho] = total
                    fila.append(vizinho)

    matriz = np.array(rotulos, dtype=np.int32).reshape(altura + 2, largura_borda)
    return total, matriz[1:-1, 1:-1]


def redimensionar(imagem, lado):
    escala = lado / max(imagem.shape[:2])
    if escala >= 1:
        return imagem.copy(), 1.0
    reduzida = cv2.resize(imagem, None, fx=escala, fy=escala,
                          interpolation=cv2.INTER_AREA)
    return reduzida, escala


def preencher_buracos(mascara):
    preenchida = cv2.copyMakeBorder(mascara, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    cv2.floodFill(preenchida, None, (0, 0), 255)
    buracos = cv2.bitwise_not(preenchida)[1:-1, 1:-1]
    return cv2.bitwise_or(mascara, buracos)


def segmentar(imagem, metodo, p):
    suave = cv2.GaussianBlur(imagem, p["kernel_suavizacao"], 0)

    if metodo == "cinza":
        cinza = cv2.cvtColor(suave, cv2.COLOR_BGR2GRAY)
        validos = cinza[cinza > p["limiar_cinza_fundo"]].reshape(-1, 1)
        limiar, _ = cv2.threshold(validos, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, mascara = cv2.threshold(cinza, limiar, 255, cv2.THRESH_BINARY)
    elif metodo == "matiz":
        hsv = cv2.cvtColor(suave, cv2.COLOR_BGR2HSV)
        mascara = cv2.inRange(
            hsv,
            (p["matiz_min"], p["saturacao_min"], p["valor_min"]),
            (p["matiz_max"], 255, 255),
        )
    else:
        raise ValueError("Segmentação deve ser 'cinza' ou 'matiz'.")

    tamanho = p["kernel_morfologia"]
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (tamanho, tamanho))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel)
    if p["preencher_buracos"]:
        mascara = preencher_buracos(mascara)
    return mascara


def separar_sementes(imagem, mascara, conectividade, p):
    total, rotulos = rotular_componentes(mascara, conectividade)
    distancia = cv2.distanceTransform(mascara, cv2.DIST_L2, 5)

    maximo = np.zeros(total + 1, dtype=np.float32)
    frente = rotulos > 0
    np.maximum.at(maximo, rotulos[frente], distancia[frente])
    if p["referencia_nucleo"] == "componente":
        referencia = maximo[rotulos]
    elif p["referencia_nucleo"] == "raio_tipico":
        referencia = np.median(maximo[1:]) if total else 0.0
    else:
        raise ValueError("referencia_nucleo deve ser 'componente' ou 'raio_tipico'.")
    nucleos = (distancia > p["fracao_distancia"] * referencia).astype(np.uint8)

    total_nucleos, marcadores = rotular_componentes(nucleos, conectividade)
    marcadores = marcadores + 1
    marcadores[(mascara > 0) & (nucleos == 0)] = 0
    marcadores = cv2.watershed(imagem, marcadores)
    rotulos = np.where(marcadores > 1, marcadores - 1, 0).astype(np.int32)
    return total_nucleos, rotulos


def medir_regioes(rotulos, total, escala, p):
    ys, xs = np.nonzero(rotulos)
    ids = rotulos[ys, xs]
    area = np.bincount(ids, minlength=total + 1)
    x_min = np.full(total + 1, rotulos.shape[1])
    y_min = np.full(total + 1, rotulos.shape[0])
    x_max = np.zeros(total + 1, dtype=np.int64)
    y_max = np.zeros(total + 1, dtype=np.int64)
    np.minimum.at(x_min, ids, xs)
    np.minimum.at(y_min, ids, ys)
    np.maximum.at(x_max, ids, xs)
    np.maximum.at(y_max, ids, ys)

    areas = area[1:]
    candidatas = areas[areas >= p["area_min_absoluta"]]
    if len(candidatas) == 0:
        return []
    area_minima = max(p["area_min_absoluta"],
                      p["area_min_fracao_mediana"] * np.median(candidatas))

    objetos = []
    for rotulo in range(1, total + 1):
        if area[rotulo] < area_minima:
            continue
        x0, y0 = int(x_min[rotulo]), int(y_min[rotulo])
        x1, y1 = int(x_max[rotulo]) + 1, int(y_max[rotulo]) + 1
        recorte = (rotulos[y0:y1, x0:x1] == rotulo).astype(np.uint8)
        contornos, _ = cv2.findContours(recorte, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        contorno = max(contornos, key=cv2.contourArea) + (x0, y0)
        (cx, cy), (lado_a, lado_b), _ = cv2.minAreaRect(contorno)
        comprimento, largura_eixo = max(lado_a, lado_b), min(lado_a, lado_b)
        largura, altura = (x1 - x0) / escala, (y1 - y0) / escala
        objetos.append({
            "x": x0 / escala,
            "y": y0 / escala,
            "largura": largura,
            "altura": altura,
            "area_px": area[rotulo] / escala ** 2,
            "razao_aspecto": largura / altura,
            "comprimento_eixo": comprimento / escala,
            "largura_eixo": largura_eixo / escala,
            "alongamento": comprimento / largura_eixo if largura_eixo > 0 else 0.0,
            "centro_x": cx / escala,
            "centro_y": cy / escala,
            "contorno": (contorno / escala).astype(np.int32),
        })
    return objetos


def processar_imagem(imagem, segmentacao="matiz", conectividade=8,
                     separacao=True, p=PARAMETROS):
    inicio = time.perf_counter()
    reduzida, escala = redimensionar(imagem, p["lado_trabalho"])
    mascara = segmentar(reduzida, segmentacao, p)
    fim_segmentacao = time.perf_counter()

    if separacao:
        total, rotulos = separar_sementes(reduzida, mascara, conectividade, p)
    else:
        total, rotulos = rotular_componentes(mascara, conectividade)
    fim_rotulagem = time.perf_counter()

    objetos = medir_regioes(rotulos, total, escala, p)
    fim = time.perf_counter()

    for indice, objeto in enumerate(objetos, start=1):
        objeto["id"] = indice

    return {
        "objetos": objetos,
        "mascara": mascara,
        "componentes": total,
        "tempo_segmentacao_ms": (fim_segmentacao - inicio) * 1000,
        "tempo_rotulagem_ms": (fim_rotulagem - fim_segmentacao) * 1000,
        "tempo_medicao_ms": (fim - fim_rotulagem) * 1000,
        "tempo_total_ms": (fim - inicio) * 1000,
    }


def desenhar(imagem, objetos):
    saida = imagem.copy()
    espessura = max(2, max(imagem.shape[:2]) // 500)
    fonte = max(0.6, max(imagem.shape[:2]) / 1500)
    for objeto in objetos:
        x, y = int(objeto["x"]), int(objeto["y"])
        largura, altura = int(objeto["largura"]), int(objeto["altura"])
        cv2.drawContours(saida, [objeto["contorno"]], -1, (0, 255, 0), espessura)
        cv2.rectangle(saida, (x, y), (x + largura, y + altura), (0, 0, 255), espessura)
        cv2.putText(saida, str(objeto["id"]), (x, max(0, y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, fonte, (255, 255, 0), espessura)
    texto = f"Sementes de abobora: {len(objetos)}"
    cv2.putText(saida, texto, (10, int(40 * fonte)),
                cv2.FONT_HERSHEY_SIMPLEX, fonte * 1.2, (0, 255, 255), espessura + 1)
    return saida


def salvar(caminho, imagem):
    if not cv2.imwrite(str(caminho), imagem):
        raise OSError(f"Falha ao salvar: {caminho}")


def listar_imagens(pasta):
    return sorted(c for c in Path(pasta).iterdir()
                  if c.suffix.lower() in (".jpg", ".jpeg", ".png"))


def main():
    parser = argparse.ArgumentParser(
        description="Inspeção e quantificação de sementes de abóbora.")
    parser.add_argument("--split", default="test", choices=["val", "test"])
    parser.add_argument("--entrada", type=Path, default=None)
    parser.add_argument("--saida", type=Path, default=None)
    parser.add_argument("--segmentacao", default="matiz", choices=["matiz", "cinza"])
    parser.add_argument("--conectividade", type=int, default=8, choices=[4, 8])
    parser.add_argument("--sem-separacao", action="store_true")
    args = parser.parse_args()

    entrada = args.entrada or PASTA_BASE / "dados" / "photos" / args.split
    saida = args.saida or PASTA_BASE / "resultados" / args.split
    (saida / "anotadas").mkdir(parents=True, exist_ok=True)
    (saida / "mascaras").mkdir(parents=True, exist_ok=True)

    imagens = listar_imagens(entrada)
    if not imagens:
        raise FileNotFoundError(f"Nenhuma imagem encontrada em: {entrada}")

    medicoes, resumo = [], []
    for caminho in imagens:
        imagem = cv2.imread(str(caminho))
        if imagem is None:
            raise FileNotFoundError(f"Não foi possível abrir a imagem: {caminho}")

        resultado = processar_imagem(imagem, args.segmentacao, args.conectividade,
                                     not args.sem_separacao)
        objetos = resultado["objetos"]

        salvar(saida / "anotadas" / caminho.name, desenhar(imagem, objetos))
        salvar(saida / "mascaras" / (caminho.stem + ".png"), resultado["mascara"])

        for objeto in objetos:
            linha = {campo: objeto.get(campo) for campo in CAMPOS_MEDICOES}
            linha["imagem"] = caminho.name
            medicoes.append(linha)

        areas = [o["area_px"] for o in objetos]
        resumo.append({
            "imagem": caminho.name,
            "largura_imagem": imagem.shape[1],
            "altura_imagem": imagem.shape[0],
            "quantidade": len(objetos),
            "area_media_px": float(np.mean(areas)) if areas else 0.0,
            "area_mediana_px": float(np.median(areas)) if areas else 0.0,
            "alongamento_medio": float(np.mean([o["alongamento"] for o in objetos])) if objetos else 0.0,
            "tempo_total_ms": resultado["tempo_total_ms"],
        })
        print(f"{caminho.name}: {len(objetos)} sementes "
              f"({resultado['tempo_total_ms']:.0f} ms)")

    with open(saida / "medicoes.csv", "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_MEDICOES)
        escritor.writeheader()
        for linha in medicoes:
            escritor.writerow({k: round(v, 2) if isinstance(v, float) else v
                               for k, v in linha.items()})

    with open(saida / "resumo_imagens.csv", "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(resumo[0].keys()))
        escritor.writeheader()
        for linha in resumo:
            escritor.writerow({k: round(v, 2) if isinstance(v, float) else v
                               for k, v in linha.items()})

    total = sum(linha["quantidade"] for linha in resumo)
    print(f"Total: {total} sementes em {len(resumo)} imagens. Resultados em {saida}")


if __name__ == "__main__":
    main()
