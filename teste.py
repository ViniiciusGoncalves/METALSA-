import math


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


c = float(input('Distância entre eixos (mm): '))
p = float(input('Passo da corrente (mm): '))
z1 = int(input('Dentes da engrenagem 1: '))
z2 = int(input('Dentes da engrenagem 2: '))

if z1 == z2:
    print('Engrenagens iguais')
    l = corrente_engrenagens_iguais(c, p, z1)
else:
    print('Engrenagens diferentes')
    l = corrente_engrenagens_diferentes(c, p, z1, z2)

elos = ajustar_elos(l)
dm = elos * p / 1000

print(f'Quantidade de elos: {elos}')
print(f'Vai precisar de uma corrente de {dm:.3f} m')