import re
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from flask import Flask, render_template, request, send_file
from io import BytesIO

app = Flask(__name__)

def limpar_nome_peca(linha_part):
    """
    Normaliza o nome da peça.
    Ex: 'N0070 (Part: Copiar de fixacao[2])' -> 'fixacao'
    """
    match = re.search(r'\(Part:\s*(.*?)\)', linha_part, re.IGNORECASE)
    if match:
        conteudo = match.group(1)
    else:
        conteudo = linha_part.replace('(Part:', '').replace(')', '')

    conteudo = re.sub(r'copiar de', '', conteudo, flags=re.IGNORECASE)
    conteudo = re.sub(r'\[\d+\]', '', conteudo)
    return conteudo.strip()


def contar_totais_por_peca(conteudo):
    """
    Conta quantos M03 existem no total para cada tipo de peça.
    """
    totais = {}
    peca_atual = "DESCONHECIDA"

    for linha in conteudo.splitlines():
        if "(Part:" in linha:
            peca_atual = limpar_nome_peca(linha)

        if "M03" in linha:
            if peca_atual not in totais:
                totais[peca_atual] = 0
            totais[peca_atual] += 1

    return totais


def processar_gcode_avancado(conteudo, espessura, regras_por_peca):
    """
    Lógica Principal:
    1. Ciclo: Altera X vezes, Pula 1, Zera.
    2. Regra Final: Nunca altera o último M03 da peça.
    """
    if espessura == '8mm':
        novo_feed = "F800.0"
    elif espessura == '5mm':
        novo_feed = "F1000.0"
    else:
        novo_feed = "F1500.0"

    linhas = conteudo.splitlines()
    linhas_modificadas = []
    padrao_feed = re.compile(r"F1500(\.0+)?")

    totais_m03 = contar_totais_por_peca(conteudo)
    contagem_global_peca = {}
    contagem_ciclo_peca = {}

    peca_atual = "DESCONHECIDA"
    aplicar_mudanca = False

    for linha in linhas:
        # Troca de Peça
        if "(Part:" in linha:
            peca_atual = limpar_nome_peca(linha)
            linhas_modificadas.append(linha)
            aplicar_mudanca = False
            continue

        # Lógica M03
        if "M03" in linha:
            if peca_atual not in contagem_global_peca:
                contagem_global_peca[peca_atual] = 0
                contagem_ciclo_peca[peca_atual] = 0

            contagem_global_peca[peca_atual] += 1

            total_desta_peca = totais_m03.get(peca_atual, 0)
            limite_desta_peca = regras_por_peca.get(peca_atual, 0)
            numero_atual_m03 = contagem_global_peca[peca_atual]

            # REGRA: Se é o último, não mexe. Se não, aplica ciclo.
            if numero_atual_m03 == total_desta_peca:
                aplicar_mudanca = False
            else:
                contagem_ciclo_peca[peca_atual] += 1
                if contagem_ciclo_peca[peca_atual] <= limite_desta_peca:
                    aplicar_mudanca = True
                else:
                    aplicar_mudanca = False
                    contagem_ciclo_peca[peca_atual] = 0  # Reseta ciclo

        # Aplica mudança
        if aplicar_mudanca:
            if padrao_feed.search(linha):
                linha = padrao_feed.sub(novo_feed, linha)

        linhas_modificadas.append(linha)

    return "\n".join(linhas_modificadas)


def gerar_preview_gcode(conteudo):
    x_coords = []
    y_coords = []
    current_x, current_y = 0.0, 0.0
    x_coords.append(current_x)
    y_coords.append(current_y)
    regex_x = re.compile(r'[Xx]([-+]?\d*\.?\d+)')
    regex_y = re.compile(r'[Yy]([-+]?\d*\.?\d+)')

    for linha in conteudo.splitlines():
        if linha.startswith(';') or linha.startswith('('): continue
        if any(c in linha for c in ['G0', 'G1', 'G2', 'G3', 'X', 'Y']):
            match_x = regex_x.search(linha)
            match_y = regex_y.search(linha)
            moved = False
            if match_x: current_x = float(match_x.group(1)); moved = True
            if match_y: current_y = float(match_y.group(1)); moved = True
            if moved: x_coords.append(current_x); y_coords.append(current_y)

    plt.figure(figsize=(12, 8))
    plt.plot(x_coords, y_coords, marker='', linestyle='-', color='blue', linewidth=1)
    plt.title('Visualização do Caminho (XY)')
    plt.grid(True);
    plt.axis('equal')

    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    plt.close()
    img_buffer.seek(0)
    return base64.b64encode(img_buffer.getvalue()).decode('utf-8')


# --- ROTA PRINCIPAL ---

@app.route('/', methods=['GET', 'POST'])
def index():
    step = 'upload'
    pecas_encontradas = []
    conteudo_arquivo = ""
    preview_img = None
    nome_arquivo_original = "arquivo.tap"

    if request.method == 'POST':
        acao = request.form.get('acao')

        # --- ETAPA 1: Upload ---
        if acao == 'analisar':
            if 'arquivo' not in request.files: return "Erro: Nenhum arquivo", 400
            arquivo = request.files['arquivo']
            if arquivo.filename == '': return "Erro: Nome vazio", 400
            if not arquivo.filename.lower().endswith('.tap'):
                return "Erro: Apenas arquivos .tap são permitidos!", 400

            nome_arquivo_original = arquivo.filename
            conteudo_arquivo = arquivo.read().decode('utf-8', errors='ignore')

            # Identifica peças
            nomes_unicos = set()
            for linha in conteudo_arquivo.splitlines():
                if "(Part:" in linha:
                    nomes_unicos.add(limpar_nome_peca(linha))

            pecas_encontradas = sorted(list(nomes_unicos))
            if not pecas_encontradas: pecas_encontradas = ["GENERICA"]
            step = 'config'

        # --- ETAPA 1.5: Reconfigurar (Voltar da Visualização) ---
        elif acao == 'reconfigurar':
            conteudo_arquivo = request.form.get('conteudo_oculto')
            nome_form = request.form.get('nome_arquivo_original')
            if nome_form: nome_arquivo_original = nome_form

            # Re-identifica as peças (já que estamos recarregando a página)
            nomes_unicos = set()
            for linha in conteudo_arquivo.splitlines():
                if "(Part:" in linha:
                    nomes_unicos.add(limpar_nome_peca(linha))

            pecas_encontradas = sorted(list(nomes_unicos))
            if not pecas_encontradas: pecas_encontradas = ["GENERICA"]
            step = 'config'

        # --- ETAPA 2: Processar ou Visualizar ---
        elif acao == 'processar' or acao == 'visualizar':
            conteudo_arquivo = request.form.get('conteudo_oculto')
            espessura = request.form.get('espessura')

            nome_form = request.form.get('nome_arquivo_original')
            if nome_form: nome_arquivo_original = nome_form

            regras = {}
            for key in request.form:
                if key.startswith('limite_'):
                    regras[key.replace('limite_', '')] = int(request.form[key])

            if "GENERICA" in regras: regras = {k: regras["GENERICA"] for k in ["DESCONHECIDA"]}

            if acao == 'visualizar':
                preview_img = gerar_preview_gcode(conteudo_arquivo)
                step = 'visual'
            else:
                conteudo_novo = processar_gcode_avancado(conteudo_arquivo, espessura, regras)
                buffer = BytesIO()
                buffer.write(conteudo_novo.encode('utf-8'))
                buffer.seek(0)

                nome_base = nome_arquivo_original.replace('.tap', '').replace('.TAP', '')
                return send_file(buffer, as_attachment=True, download_name=f"modificado_{nome_base}.tap",
                                 mimetype='text/plain')

    return render_template('index.html', step=step, pecas=pecas_encontradas, conteudo=conteudo_arquivo,
                           preview_img=preview_img, nome_arquivo=nome_arquivo_original)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)