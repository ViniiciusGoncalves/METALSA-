import re
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from flask import Flask, render_template, request, send_file
from io import BytesIO

app = Flask(__name__)


def processar_gcode(conteudo, espessura, limite_vezes):
    if espessura == '8mm':
        novo_feed = "F800.0"
    elif espessura == '5mm':
        novo_feed = "F1000.0"
    else:
        novo_feed = "F1500.0"

    linhas = conteudo.splitlines()
    linhas_modificadas = []

    total_m03_no_arquivo = 0
    for linha in linhas:
        if "M03" in linha:
            total_m03_no_arquivo += 1

    contador_m03_global = 0
    contador_ciclo = 0
    modificar_bloco_atual = False
    padrao_feed = re.compile(r"F1500(\.0+)?")

    for linha in linhas:
        if "M03" in linha:
            contador_m03_global += 1
            if contador_m03_global == total_m03_no_arquivo:
                modificar_bloco_atual = False
            else:
                contador_ciclo += 1
                if contador_ciclo <= limite_vezes:
                    modificar_bloco_atual = True
                else:
                    modificar_bloco_atual = False
                    contador_ciclo = 0

        if modificar_bloco_atual:
            if padrao_feed.search(linha):
                linha = padrao_feed.sub(novo_feed, linha)

        linhas_modificadas.append(linha)

    return "\n".join(linhas_modificadas)


def gerar_preview_gcode(conteudo):
    x_coords = []
    y_coords = []

    current_x = 0.0
    current_y = 0.0

    x_coords.append(current_x)
    y_coords.append(current_y)

    linhas = conteudo.splitlines()

    # Regex simples para achar X e Y (case insensitive)
    # Procura por X seguido de números (inteiros ou decimais)
    regex_x = re.compile(r'[Xx]([-+]?\d*\.?\d+)')
    regex_y = re.compile(r'[Yy]([-+]?\d*\.?\d+)')

    for linha in linhas:
        # Ignora comentários
        if linha.startswith(';') or linha.startswith('('):
            continue

        # Verifica se é uma linha de movimento (G0, G1, G2, G3)
        # Simplificação: Vamos plotar todos os movimentos como linhas retas
        if 'G0' in linha or 'G1' in linha or 'G2' in linha or 'G3' in linha or 'X' in linha or 'Y' in linha:
            match_x = regex_x.search(linha)
            match_y = regex_y.search(linha)

            has_movement = False

            if match_x:
                current_x = float(match_x.group(1))
                has_movement = True

            if match_y:
                current_y = float(match_y.group(1))
                has_movement = True

            if has_movement:
                x_coords.append(current_x)
                y_coords.append(current_y)

    # Criar o Gráfico
    plt.figure(figsize=(12, 8))  # Antes era (6,6), agora é maior e retangular
    plt.plot(x_coords, y_coords, marker='', linestyle='-', color='blue', linewidth=1)
    plt.title('Visualização do Caminho (XY)')
    plt.xlabel('X (mm)')
    plt.ylabel('Y (mm)')
    plt.grid(True)
    plt.axis('equal')

    # Salvar em memória (buffer)
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    plt.close()
    img_buffer.seek(0)

    # Converter para Base64 para enviar ao HTML
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    return img_base64


@app.route('/', methods=['GET', 'POST'])
def index():
    preview_img = None

    if request.method == 'POST':
        if 'arquivo' not in request.files:
            return "Erro", 400
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return "Erro", 400

        espessura = request.form.get('espessura')
        try:
            quantidade = int(request.form.get('quantidade'))
        except ValueError:
            quantidade = 0

        conteudo_original = arquivo.read().decode('utf-8', errors='ignore')

        conteudo_novo = processar_gcode(conteudo_original, espessura, quantidade)

        acao = request.form.get('acao')

        if acao == 'visualizar':
            preview_img = gerar_preview_gcode(conteudo_original)
            return render_template('index.html', preview_img=preview_img,
                                   espessura_selecionada=espessura,
                                   qtd_selecionada=quantidade)

        else:
            # Lógica de Download (Padrão)
            buffer = BytesIO()
            buffer.write(conteudo_novo.encode('utf-8'))
            buffer.seek(0)
            nome_novo = f"modificado_{arquivo.filename}"
            return send_file(buffer, as_attachment=True, download_name=nome_novo, mimetype='text/plain')

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)