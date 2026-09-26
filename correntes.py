import math

# Correntes de rolos padrão ASA / ANSI B29.1 (valores nominais em mm)
# passo, largura interna, diâmetro do rolo, diâmetro do pino e carga de ruptura mínima (kN)
CORRENTES_ASA = [
    {'asa': '25',  'iso': '04C', 'passo_pol': '1/4"',   'passo': 6.35,  'largura': 3.18,  'rolo': 3.30,  'pino': 2.31,  'ruptura': 3.5},
    {'asa': '35',  'iso': '06C', 'passo_pol': '3/8"',   'passo': 9.525, 'largura': 4.77,  'rolo': 5.08,  'pino': 3.58,  'ruptura': 7.9},
    {'asa': '41',  'iso': '085', 'passo_pol': '1/2"',   'passo': 12.70, 'largura': 6.38,  'rolo': 7.77,  'pino': 3.58,  'ruptura': 6.7},
    {'asa': '40',  'iso': '08A', 'passo_pol': '1/2"',   'passo': 12.70, 'largura': 7.95,  'rolo': 7.92,  'pino': 3.96,  'ruptura': 13.9},
    {'asa': '50',  'iso': '10A', 'passo_pol': '5/8"',   'passo': 15.875,'largura': 9.53,  'rolo': 10.16, 'pino': 5.08,  'ruptura': 21.8},
    {'asa': '60',  'iso': '12A', 'passo_pol': '3/4"',   'passo': 19.05, 'largura': 12.70, 'rolo': 11.91, 'pino': 5.94,  'ruptura': 31.3},
    {'asa': '80',  'iso': '16A', 'passo_pol': '1"',     'passo': 25.40, 'largura': 15.88, 'rolo': 15.88, 'pino': 7.92,  'ruptura': 55.6},
    {'asa': '100', 'iso': '20A', 'passo_pol': '1 1/4"', 'passo': 31.75, 'largura': 19.05, 'rolo': 19.05, 'pino': 9.53,  'ruptura': 86.7},
    {'asa': '120', 'iso': '24A', 'passo_pol': '1 1/2"', 'passo': 38.10, 'largura': 25.40, 'rolo': 22.23, 'pino': 11.10, 'ruptura': 124.6},
    {'asa': '140', 'iso': '28A', 'passo_pol': '1 3/4"', 'passo': 44.45, 'largura': 25.40, 'rolo': 25.40, 'pino': 12.70, 'ruptura': 169.0},
    {'asa': '160', 'iso': '32A', 'passo_pol': '2"',     'passo': 50.80, 'largura': 31.75, 'rolo': 28.58, 'pino': 14.27, 'ruptura': 222.4},
    {'asa': '180', 'iso': '36A', 'passo_pol': '2 1/4"', 'passo': 57.15, 'largura': 35.71, 'rolo': 35.71, 'pino': 17.46, 'ruptura': 280.2},
    {'asa': '200', 'iso': '40A', 'passo_pol': '2 1/2"', 'passo': 63.50, 'largura': 38.10, 'rolo': 39.68, 'pino': 19.84, 'ruptura': 347.0},
    {'asa': '240', 'iso': '48A', 'passo_pol': '3"',     'passo': 76.20, 'largura': 47.63, 'rolo': 47.63, 'pino': 23.80, 'ruptura': 500.4},
]

PASSO_POR_ASA = {c['asa']: c['passo'] for c in CORRENTES_ASA}

# Elos extras somados em cada esteira para dar a folga necessária na montagem
FOLGA_ELOS = 10


# Fórmula para engrenagens iguais: L = 2*(C/P) + Z
def corrente_engrenagens_iguais(c, p, z):
    return 2 * (c / p) + z


# Fórmula para engrenagens diferentes
def corrente_engrenagens_diferentes(c, p, z1, z2):
    return 2 * (c / p) + (z1 + z2) / 2 + ((z2 - z1) / (2 * math.pi)) ** 2 * (p / c)


# Arredonda para cima e deixa o número de elos par
def ajustar_elos(l):
    elos = math.ceil(l)
    if elos % 2 != 0:
        elos += 1
    return elos


def calcular_esteira(asa, c, z1, z2, qtd=1):
    """Calcula elos e metros de corrente para uma esteira (e para a quantidade informada)."""
    p = PASSO_POR_ASA[asa]

    if z1 == z2:
        l = corrente_engrenagens_iguais(c, p, z1)
    else:
        l = corrente_engrenagens_diferentes(c, p, z1, z2)

    elos = ajustar_elos(l) + FOLGA_ELOS
    metros = elos * p / 1000

    return {
        'passo': p,
        'elos_teoricos': l,
        'elos': elos,
        'metros': metros,
        'qtd': qtd,
        'metros_total': metros * qtd,
        'elos_total': elos * qtd,
        'tipo': 'iguais' if z1 == z2 else 'diferentes',
    }
