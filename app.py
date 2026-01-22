import re
from flask import Flask, render_template, request, send_file
from io import BytesIO

app = Flask(__name__)


def processar_gcode(conteudo, espessura, limite_vezes):
    """
    Lógica de Ciclo:
    - Se limite_vezes = 2:
      - Altera M03 #1 e #2
      - Pula M03 #3 (Mantém F1500)
      - Altera M03 #4 e #5
      - Pula M03 #6... e assim por diante.
    - EXCEÇÃO: O último M03 do arquivo SEMPRE mantém F1500.
    """

    if espessura == '8mm':
        novo_feed = "F800.0"
    elif espessura == '5mm':
        novo_feed = "F1000.0"
    else:
        novo_feed = "F1500.0"

    linhas = conteudo.splitlines()
    linhas_modificadas = []

    # 1. Contar TOTAL de M03 no arquivo para identificar o último
    total_m03_no_arquivo = 0
    for linha in linhas:
        if "M03" in linha:
            total_m03_no_arquivo += 1

    contador_m03_global = 0  # Conta qual número de M03 é esse no total (1º, 2º, 50º...)
    contador_ciclo = 0  # Conta de 1 até o limite_vezes e depois reseta
    modificar_bloco_atual = False  # Flag que diz se devemos alterar o F1500 atual

    # Padrão Regex para encontrar F1500 ou F1500.0
    padrao_feed = re.compile(r"F1500(\.0+)?")

    for linha in linhas:
        # Verifica se a linha inicia um novo bloco de corte
        if "M03" in linha:
            contador_m03_global += 1

            # REGRA 1: Se for o ÚLTIMO M03 do arquivo, nunca altera.
            if contador_m03_global == total_m03_no_arquivo:
                modificar_bloco_atual = False
            else:
                # Incrementa o contador do ciclo atual
                contador_ciclo += 1

                # REGRA 2: Lógica do Ciclo
                if contador_ciclo <= limite_vezes:
                    # Estamos dentro da quantidade (ex: 1 ou 2) -> Altera
                    modificar_bloco_atual = True
                else:
                    # Passou da quantidade (ex: é o 3º) -> Não altera e Reseta ciclo
                    modificar_bloco_atual = False
                    contador_ciclo = 0  # Reseta para que o próximo conte como 1 novamente

        # Se a flag estiver ativa, procuramos e substituímos o F1500
        if modificar_bloco_atual:
            if padrao_feed.search(linha):
                # Substitui F1500 pelo novo valor
                linha = padrao_feed.sub(novo_feed, linha)

        linhas_modificadas.append(linha)

    return "\n".join(linhas_modificadas)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            return "Nenhum arquivo enviado", 400

        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return "Nenhum arquivo selecionado", 400

        espessura = request.form.get('espessura')
        try:
            quantidade = int(request.form.get('quantidade'))
        except ValueError:
            quantidade = 0

        conteudo_original = arquivo.read().decode('utf-8', errors='ignore')

        # Processa o G-code com a nova lógica cíclica
        conteudo_novo = processar_gcode(conteudo_original, espessura, quantidade)

        buffer = BytesIO()
        buffer.write(conteudo_novo.encode('utf-8'))
        buffer.seek(0)

        nome_original = arquivo.filename
        nome_novo = f"modificado_{nome_original}"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=nome_novo,
            mimetype='text/plain'
        )

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)