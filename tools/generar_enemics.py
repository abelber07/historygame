"""Genera els enemics normals en alta definició a assets/img/enemics_hd.png + enemics_hd.json.

    python3 tools/generar_enemics.py [vista.png]

Soldat, escuder i kamikaze (de terra, mirant a la dreta: el joc els gira) i dron, lloctinent i caçador
(voladors). Cada tipus té el seu llenç i una llista de fotogrames per animació; el JSON guarda on va
el punt d'ancoratge (els peus o el centre) i les boques dels canons.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame  # noqa: E402
from pintor import Figura, comprovar_paleta, empaquetar, girar, retallar  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SORTIDA = os.path.join(AQUI, "..", "assets", "img")

MAT = {
    "pell": [(16, 40, 30), (40, 96, 62), (66, 142, 76), (110, 186, 92), (170, 222, 128)],
    "pell_f": [(14, 32, 30), (30, 74, 58), (48, 108, 70), (78, 146, 84), (128, 190, 112)],
    "quitina": [(34, 24, 52), (72, 58, 102), (106, 88, 140), (148, 128, 180), (204, 188, 228)],
    "quitina_f": [(26, 18, 40), (52, 40, 76), (78, 64, 106), (110, 94, 140), (156, 140, 186)],
    "banya": [(62, 44, 38), (150, 124, 96), (200, 180, 140), (232, 218, 182), (252, 246, 222)],
    "negre": [(10, 8, 16), (28, 26, 38), (46, 44, 60), (74, 72, 94), (122, 120, 144)],
    "energia": [(10, 56, 78), (36, 160, 204), (90, 226, 255), (168, 248, 255), (236, 255, 255)],
    "visor": [(70, 10, 50), (170, 30, 120), (240, 70, 170), (255, 150, 215), (255, 225, 245)],
    "metall": [(26, 28, 40), (70, 76, 96), (110, 118, 140), (156, 164, 186), (210, 216, 232)],
    "ovni": [(30, 34, 46), (88, 96, 114), (132, 142, 160), (178, 188, 204), (228, 234, 242)],
    "ovni_f": [(18, 20, 30), (50, 56, 72), (72, 80, 98), (100, 108, 128), (140, 148, 168)],
    "vidre": [(28, 56, 74), (86, 140, 168), (134, 190, 214), (186, 226, 242), (236, 250, 255)],
    "ull_n": [(4, 4, 8), (12, 10, 18), (22, 20, 32), (54, 52, 74), (196, 196, 228)],
    "taronja": [(64, 24, 10), (170, 70, 22), (232, 122, 42), (255, 172, 82), (255, 222, 152)],
    "vermell": [(60, 12, 16), (148, 30, 40), (206, 58, 58), (244, 108, 98), (255, 188, 168)],
    "bronze": [(60, 40, 14), (148, 108, 40), (204, 158, 60), (238, 202, 100), (255, 238, 178)],
    "rosa": [(70, 16, 50), (168, 50, 120), (224, 96, 170), (248, 150, 206), (255, 212, 236)],
    "brasa": [(92, 20, 10), (200, 60, 22), (255, 122, 42), (255, 192, 102), (255, 242, 202)],
}
BRILLANTS = ("quitina", "quitina_f", "negre", "metall", "ovni", "vidre", "banya", "bronze", "vermell", "taronja")
comprovar_paleta(MAT)


def figura(w, h):
    return Figura(w, h, MAT, BRILLANTS)


def rot(punts, angle, origen):
    """Gira punts absoluts al voltant d'origen."""
    if not angle:
        return list(punts)
    c, s = math.cos(angle), math.sin(angle)
    ox, oy = origen
    return [(ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c) for x, y in punts]


# ---------------------------------------------------------------------------------------------
# Esquelet dels soldats (mirant a la dreta; y creix cap avall)
# ---------------------------------------------------------------------------------------------
CUIXA, TIBIA = 10.0, 10.0


def genoll(maluc, garró):
    """Genoll endavant entre el maluc i el garró (cames d'alien: el garró queda enlaire, darrere)."""
    dx, dy = garró[0] - maluc[0], garró[1] - maluc[1]
    d = max(0.1, min(math.hypot(dx, dy), CUIXA + TIBIA - 0.05))
    a = math.atan2(dy, dx)
    t = math.acos(max(-1.0, min(1.0, (CUIXA ** 2 + d * d - TIBIA ** 2) / (2 * CUIXA * d))))
    return maluc[0] + CUIXA * math.cos(a - t), maluc[1] + CUIXA * math.sin(a - t)


def colze(espatlla, mà, braç=7.0, avantbraç=7.0):
    """Colze cap avall i enrere per arribar a la mà."""
    dx, dy = mà[0] - espatlla[0], mà[1] - espatlla[1]
    d = max(0.1, min(math.hypot(dx, dy), braç + avantbraç - 0.05))
    a = math.atan2(dy, dx)
    t = math.acos(max(-1.0, min(1.0, (braç ** 2 + d * d - avantbraç ** 2) / (2 * braç * d))))
    return espatlla[0] + braç * math.cos(a + t), espatlla[1] + braç * math.sin(a + t)


TERRA = 64          # fila on reposen les puntes dels peus


def cama(f, maluc, punta, angle, darrere):
    """Cama digitígrada: cuixa (armadura), tíbia cap enrere, garró enlaire i peu amb urpes."""
    garró = (punta[0] - 5 * math.cos(angle) + 1, punta[1] - 6 - 5 * math.sin(angle))
    gen = genoll(maluc, garró)
    mode = "fosc" if darrere else "volum"
    g = f"cama{darrere}"
    f.membre("quitina_f", [maluc, gen], [3.8, 3.0], mode, grup=g)
    f.membre("pell_f", [gen, garró], [2.6, 2.0], mode, grup=g)
    f.membre("pell_f", [garró, punta], [2.0, 1.6], mode, grup=g)
    f.el·lipse("quitina", gen[0] - 2.5, gen[1] - 2.5, gen[0] + 2.5, gen[1] + 2.5, mode)       # genollera
    for k in (-1, 1):                                                                       # urpes
        dx = 3 * math.cos(angle) + k * 0.6
        f.membre("banya", [punta, (punta[0] + dx + 1, punta[1] + 1 + k * 0.4)], [1.0, 0.5], "pla")
    return gen, garró


def fusell_alien(f, x, y, angle=0.0):
    """Fusell de plasma xylothian: carcassa orgànica i cèl·lules que brillen. (x, y) = empunyadura."""
    def P(punts):
        return girar(punts, angle, (x, y))
    f.poli("quitina", P([(-7, -5), (2, -6), (4, -3), (2, 0), (-5, 1), (-8, -1)]))            # culata
    f.poli("negre", P([(0, -6), (16, -6), (18, -4), (16, -1), (0, -1)]))                    # cos
    f.poli("negre", P([(1, -1), (4, -1), (3, 4), (0, 4)]))                                  # empunyadura
    f.poli("quitina", P([(6, -8), (14, -8), (16, -6), (5, -6)]))                            # carcassa de dalt
    f.poli("energia", P([(6, -4), (9, -4), (9, -2), (6, -2)]), "brilla")                    # cèl·lules
    f.poli("energia", P([(11, -4), (14, -4), (14, -2), (11, -2)]), "brilla")
    f.poli("negre", P([(16, -5), (25, -5), (25, -2), (16, -2)]))                            # canó
    f.poli("quitina", P([(18, -6), (23, -6), (23, -5), (18, -5)]))
    f.poli("energia", P([(25, -6), (27, -6), (27, -1), (25, -1)]), "brilla")               # emissor
    return girar([(28, -3.5)], angle, (x, y))[0]


def cap_soldat(f, hx, hy, angle=0.0):
    """Casc de quitina allargat cap enrere amb visor magenta; cara verda amb mandíbules."""
    def P(punts):
        return rot([(hx + px, hy + py) for px, py in punts], angle, (hx + 6, hy + 14))
    f.poli("pell", P([(4, 9), (13, 9), (15, 12), (13, 16), (8, 17), (4, 15)]), grup="cara")   # cara
    f.poli("quitina", P([(-6, 4), (-2, 0), (6, -2), (12, 0), (16, 4), (16, 8), (8, 10), (2, 12), (-4, 10)]))  # casc
    f.poli("visor", P([(8, 5), (16, 5), (16, 8), (9, 8)]), "brilla")
    f.marca_linia(*P([(-3, 3), (8, 0)]), 1)
    f.marca_linia(*P([(-4, 7), (6, 8)]), -1)
    for a, b in ((P([(12, 13)])[0], P([(15, 15)])[0]), (P([(10, 14)])[0], P([(11, 17)])[0])):
        f.linia(a, b, MAT["pell"][0])                                                     # mandíbules
    px, py = P([(14, 6)])[0]
    f.px(px, py, MAT["visor"][4])


OX = 36             # els soldats es dibuixen desplaçats: hi ha lloc per caure d'esquena


def soldat(p):
    """p: diccionari de pose (vegeu poses_soldat). Torna (superfície, boca del canó)."""
    W, H = 104, 68
    f = figura(W, H)
    f.moure(OX, 0)
    gir = p.get("gir", 0.0)
    if gir:
        f.girar_tot(gir, p.get("eix", (24, TERRA)))
    mal = p["maluc"]
    tx, ty = mal[0] - 6, mal[1] - 18                     # tors (racó de dalt a l'esquerra)
    lean = p.get("inclina", 0.0)
    # motxilla amb antena (la veu de la Ment)
    f.poli("quitina_f", rot([(tx - 6, ty + 2), (tx + 1, ty + 1), (tx + 2, ty + 13), (tx - 5, ty + 14)], lean, mal))
    ax, ay = rot([(tx - 4, ty + 1)], lean, mal)[0]
    bx, by = rot([(tx - 7, ty - 8)], lean, mal)[0]
    f.membre("negre", [(ax, ay), (bx, by)], [0.7, 0.5], "pla")
    f.cercle("visor", bx, by, 1.4, "brilla")
    # braç del darrere (darrere del cos), cames, tors
    esp_d = rot([(tx + 5, ty + 4)], lean, mal)[0]
    esp_f = rot([(tx + 8, ty + 4)], lean, mal)[0]
    gx, gy = p["arma"]
    angle_arma = p.get("angle_arma", 0.0)
    suport = rot([(gx + 11, gy - 1)], angle_arma, (gx, gy))[0]
    col_d = colze(esp_d, suport, 7.5, 8.0)
    f.membre("quitina_f", [esp_d, col_d], [2.4, 2.0], "fosc", grup="braç_d")
    cama(f, mal, *p["peu_d"], darrere=1)
    cama(f, mal, *p["peu_f"], darrere=0)
    f.poli("quitina_f", rot([(tx + 1, ty + 15), (tx + 12, ty + 15), (tx + 12, ty + 19), (tx + 1, ty + 19)], lean, mal))
    f.poli("quitina", rot([(tx, ty), (tx + 11, ty + 1), (tx + 14, ty + 7), (tx + 12, ty + 16), (tx + 2, ty + 17),
                              (tx - 1, ty + 8)], lean, mal))
    for a, b, d in (((tx + 2, ty + 6), (tx + 11, ty + 7), -1), ((tx + 2, ty + 5), (tx + 11, ty + 6), 1),
                    ((tx + 3, ty + 12), (tx + 11, ty + 12), -1)):
        f.marca_linia(*rot([a, b], lean, mal), d)
    f.membre("pell", rot([(tx + 9, ty + 1), (tx + 10, ty - 3)], lean, mal), [2.0, 1.8], grup="coll")
    hx, hy = rot([(tx + 5, ty - 15)], lean, mal)[0]
    cap_soldat(f, hx + p.get("cap_dx", 0), hy + p.get("cap_dy", 0), p.get("angle_cap", 0.0))
    # arma i braços
    boca = fusell_alien(f, gx, gy, angle_arma)
    f.membre("pell", [col_d, suport], [1.9, 1.6], "fosc", grup="braç_d")
    f.el·lipse("pell", suport[0] - 1.5, suport[1] - 1.5, suport[0] + 1.5, suport[1] + 1.5, "fosc", grup="braç_d")
    col_f = colze(esp_f, (gx + 1, gy), 7.0, 7.0)
    f.membre("quitina_f", [esp_f, col_f], [2.6, 2.2], grup="braç_f")
    f.membre("pell", [col_f, (gx + 1, gy)], [2.0, 1.7], grup="braç_f")
    f.el·lipse("pell", gx - 0.5, gy - 1.5, gx + 2.5, gy + 1.5, grup="braç_f")
    f.el·lipse("quitina", esp_f[0] - 3.5, esp_f[1] - 3, esp_f[0] + 3.5, esp_f[1] + 3)         # espatllera
    s = f.superficie(fins_a_baix=not gir)
    bx, by = f.t(*boca)
    return s, (round(bx), round(by))


def poses_soldat():
    """{animació: [poses]} del soldat."""
    poses = {"camina": []}
    for i in range(6):
        fase = math.tau * i / 6
        peus = []
        for base, ph in ((20, fase + math.pi), (27, fase)):
            x = base + 6 * math.sin(ph)
            enlaire = max(0.0, math.cos(ph))
            peus.append(((x, TERRA - 4 * enlaire), 0.5 * enlaire))
        bob = -1 if i % 3 == 1 else 0
        poses["camina"].append({"maluc": (24, 41 + bob), "peu_d": peus[0], "peu_f": peus[1],
                                "arma": (33, 33 + bob), "angle_arma": 0.06})
    base = {"maluc": (23, 41), "peu_d": ((16, TERRA), 0.0), "peu_f": ((30, TERRA), 0.0)}
    poses["apunta"] = [dict(base, arma=(33, 27), angle_arma=-0.04, inclina=0.08, cap_dx=1, cap_dy=1)]
    poses["dispara"] = [dict(base, arma=(31, 27), angle_arma=-0.18, inclina=0.0, cap_dx=0, cap_dy=0)]
    poses["ferit"] = [dict(base, maluc=(21, 41), arma=(29, 32), angle_arma=0.35, inclina=-0.25, angle_cap=-0.3,
                           peu_f=((28, TERRA - 2), 0.3))]
    poses["mort"] = [dict(base, maluc=(20, 41), arma=(27, 30), angle_arma=0.6, inclina=-0.35, angle_cap=-0.4,
                          peu_f=((30, TERRA - 3), 0.4), gir=-0.4, eix=(16, TERRA)),
                     dict(base, maluc=(20, 41), arma=(27, 30), angle_arma=0.9, inclina=-0.3, angle_cap=-0.5,
                          peu_f=((31, TERRA - 3), 0.5), gir=-1.0, eix=(15, TERRA - 1)),
                     dict(base, maluc=(20, 41), arma=(27, 33), angle_arma=1.2, inclina=-0.2, angle_cap=-0.2,
                          peu_f=((30, TERRA - 2), 0.4), gir=-1.5, eix=(13, TERRA - 5))]
    return poses


# ---------------------------------------------------------------------------------------------
# Escuder: soldat pesant amb armadura de metall i un emissor d'escut al braç del davant
# ---------------------------------------------------------------------------------------------
def blaster(f, x, y, angle=0.0):
    """Escopeta de plasma curta de l'escuder: (x, y) = empunyadura."""
    def P(punts):
        return rot([(x + px, y + py) for px, py in punts], angle, (x, y))
    f.poli("negre", P([(-5, -6), (12, -7), (14, -4), (12, 0), (-4, 0), (-6, -3)]))
    f.poli("negre", P([(0, 0), (3, 0), (2, 4), (-1, 4)]))
    f.poli("metall", P([(2, -9), (11, -9), (12, -7), (1, -7)]))
    for k in range(3):
        f.poli("energia", P([(14, -6 + k * 2), (18, -6 + k * 2), (18, -5 + k * 2), (14, -5 + k * 2)]), "brilla")
    f.poli("energia", P([(3, -5), (9, -5), (9, -3), (3, -3)]), "brilla")
    return rot([(x + 19, y - 3.5)], angle, (x, y))[0]


def escuder(p):
    W, H = 104, 68
    f = figura(W, H)
    f.moure(OX, 0)
    gir = p.get("gir", 0.0)
    if gir:
        f.girar_tot(gir, p.get("eix", (24, TERRA)))
    mal = p["maluc"]
    tx, ty = mal[0] - 9, mal[1] - 21
    lean = p.get("inclina", 0.0)

    def R(punts):
        return rot(punts, lean, mal)
    # bateria a l'esquena
    f.poli("negre", R([(tx - 6, ty + 3), (tx + 2, ty + 2), (tx + 3, ty + 15), (tx - 5, ty + 16), (tx - 7, ty + 10)]))
    for k in range(3):
        f.poli("energia", R([(tx - 5, ty + 5 + k * 3), (tx - 1, ty + 5 + k * 3), (tx - 1, ty + 6 + k * 3),
                             (tx - 5, ty + 6 + k * 3)]), "brilla")
    esp_d = R([(tx + 7, ty + 4)])[0]
    esp_f = R([(tx + 12, ty + 5)])[0]
    gx, gy = p["arma"]
    angle_arma = p.get("angle_arma", 0.0)
    col_d = colze(esp_d, (gx, gy), 8.0, 8.0)
    f.membre("metall", [esp_d, col_d], [3.4, 2.8], "fosc", grup="braç_d")
    f.membre("pell_f", [col_d, (gx, gy)], [2.4, 2.0], "fosc", grup="braç_d")
    boca = blaster(f, gx, gy, angle_arma)
    # cames gruixudes amb gamberes de metall
    for darrere, (punta, angle) in ((1, p["peu_d"]), (0, p["peu_f"])):
        garró = (punta[0] - 5 * math.cos(angle) + 1, punta[1] - 6 - 5 * math.sin(angle))
        gen = genoll(mal, garró)
        mode = "fosc" if darrere else "volum"
        g = f"cama{darrere}"
        f.membre("metall", [mal, gen], [4.8, 3.8], mode, grup=g)
        f.membre("pell_f", [gen, garró], [3.0, 2.4], mode, grup=g)
        f.membre("pell_f", [garró, punta], [2.4, 1.8], mode, grup=g)
        f.membre("metall", [(gen[0] * 0.7 + garró[0] * 0.3, gen[1] * 0.7 + garró[1] * 0.3), garró], [3.2, 2.6], mode)
        f.el·lipse("quitina", gen[0] - 3, gen[1] - 3, gen[0] + 3, gen[1] + 3, mode)
        for k in (-1, 1):
            f.membre("banya", [punta, (punta[0] + 3.5 * math.cos(angle) + 1, punta[1] + 1 + k * 0.4)], [1.1, 0.5], "pla")
    # tors: peto de metall amb vores de quitina
    f.poli("quitina_f", R([(tx + 1, ty + 18), (tx + 16, ty + 18), (tx + 15, ty + 23), (tx + 2, ty + 23)]))
    f.poli("metall", R([(tx - 2, ty - 1), (tx + 14, ty), (tx + 18, ty + 7), (tx + 16, ty + 19), (tx + 1, ty + 20),
                        (tx - 3, ty + 9)]))
    f.poli("quitina", R([(tx + 3, ty + 3), (tx + 14, ty + 4), (tx + 15, ty + 9), (tx + 3, ty + 9)]))
    for a, b, d in (((tx + 1, ty + 13), (tx + 15, ty + 13), -1), ((tx + 1, ty + 12), (tx + 15, ty + 12), 1),
                    ((tx + 6, ty + 1), (tx + 6, ty + 18), -1)):
        f.marca_linia(*R([a, b]), d)
    for k in range(3):
        rx, ry = R([(tx + 4 + k * 4, ty + 16)])[0]
        f.px(rx, ry, MAT["metall"][4])
    # cap: casc pesant amb cresta i visor estret
    hx, hy = R([(tx + 6, ty - 12)])[0]
    hx += p.get("cap_dx", 0)
    hy += p.get("cap_dy", 0)
    a_cap = p.get("angle_cap", 0.0)

    def C(punts):
        return rot([(hx + px, hy + py) for px, py in punts], a_cap, (hx + 6, hy + 12))
    f.poli("pell", C([(5, 8), (13, 8), (14, 11), (12, 14), (6, 14)]))
    f.poli("metall", C([(-4, 4), (0, -1), (8, -2), (13, 1), (15, 5), (14, 8), (6, 9), (0, 11), (-3, 9)]))
    f.poli("quitina", C([(-3, 2), (4, -5), (10, -3), (8, -1), (2, 1)]))                         # cresta
    f.poli("visor", C([(8, 4), (15, 4), (15, 6), (8, 6)]), "brilla")
    f.marca_linia(*C([(-2, 6), (6, 7)]), -1)
    # braç del davant amb l'emissor de l'escut
    em = p.get("emissor", (tx + 22, ty + 11))
    col_f = colze(esp_f, em, 8.0, 7.5)
    f.membre("metall", [esp_f, col_f], [3.4, 3.0], grup="braç_f")
    f.membre("metall", [col_f, em], [3.0, 2.8], grup="braç_f")
    f.el·lipse("negre", em[0] - 2.5, em[1] - 4, em[0] + 2.5, em[1] + 4)
    f.el·lipse("energia", em[0] - 1, em[1] - 3, em[0] + 2, em[1] + 3, "brilla")
    f.el·lipse("metall", esp_f[0] - 4.5, esp_f[1] - 4, esp_f[0] + 4.5, esp_f[1] + 4, "esfera")    # espatllera
    s = f.superficie(fins_a_baix=not gir)
    bx, by = f.t(*boca)
    ex, ey = f.t(*em)
    return s, (round(bx), round(by)), (round(ex), round(ey))


def poses_escuder():
    poses = {"camina": []}
    for i in range(6):
        fase = math.tau * i / 6
        peus = []
        for base, ph in ((18, fase + math.pi), (28, fase)):
            x = base + 5 * math.sin(ph)
            enlaire = max(0.0, math.cos(ph))
            peus.append(((x, TERRA - 3 * enlaire), 0.4 * enlaire))
        bob = -1 if i % 3 == 1 else 0
        poses["camina"].append({"maluc": (23, 40 + bob), "peu_d": peus[0], "peu_f": peus[1],
                                "arma": (28, 34 + bob), "angle_arma": 0.05})
    base = {"maluc": (22, 40), "peu_d": ((15, TERRA), 0.0), "peu_f": ((30, TERRA), 0.0)}
    poses["apunta"] = [dict(base, arma=(30, 24), angle_arma=-0.05, cap_dx=1)]
    poses["ferit"] = [dict(base, maluc=(20, 40), arma=(26, 33), angle_arma=0.3, inclina=-0.2, angle_cap=-0.3)]
    poses["mort"] = [dict(base, maluc=(20, 40), arma=(25, 32), angle_arma=0.5, inclina=-0.3, angle_cap=-0.3,
                          gir=-0.4, eix=(14, TERRA)),
                     dict(base, maluc=(20, 40), arma=(25, 32), angle_arma=0.8, inclina=-0.25, angle_cap=-0.4,
                          gir=-1.0, eix=(13, TERRA - 1)),
                     dict(base, maluc=(20, 40), arma=(25, 34), angle_arma=1.1, inclina=-0.2, angle_cap=-0.2,
                          gir=-1.5, eix=(11, TERRA - 6))]
    return poses


# ---------------------------------------------------------------------------------------------
# Kamikaze: paparra inflada amb un nucli que brilla
# ---------------------------------------------------------------------------------------------
TERRA_K = 26


def kamikaze(fase=0.0, armat=False):
    W, H = 42, 30
    f = figura(W, H)
    infla = 2 if armat else 0
    for k, bx in enumerate((10, 17, 24)):                                  # potes del costat de darrere
        d = 3 * math.sin(fase + k * 2.1 + math.pi)
        f.membre("pell_f", [(bx, 18), (bx - 3 + d * 0.5, 14 - infla), (bx - 5 + d, TERRA_K)], [1.4, 1.1, 0.6], "fosc")
    f.el·lipse("rosa", 5 - infla, 4 - infla * 1.5, 30 + infla, 22, "esfera", grup="sac")
    f.el·lipse("brasa", 12 - infla, 8 - infla, 23 + infla, 17 + infla * 0.5, "brilla")
    for a, b in (((13, 10), (18, 13)), ((22, 9), (19, 14)), ((14, 16), (19, 14))):
        f.linia(a, b, MAT["rosa"][1])                                       # membranes
    f.marca_linia((8, 9), (14, 6), 1)
    f.el·lipse("pell_f", 27 + infla * 0.5, 11, 36 + infla * 0.5, 20)       # cap
    f.px(33 + infla * 0.5, 14, MAT["visor"][3])
    f.px(31 + infla * 0.5, 13, MAT["visor"][2])
    f.membre("banya", [(35 + infla * 0.5, 17), (39 + infla * 0.5, 19), (37 + infla * 0.5, 21)], [1.0, 0.8, 0.4], "pla")
    for k, bx in enumerate((11, 18, 25)):                                  # potes del davant
        d = 3 * math.sin(fase + k * 2.1)
        f.membre("pell_f", [(bx, 19), (bx + 3 + d * 0.5, 15 - infla), (bx + 4 + d, TERRA_K)], [1.6, 1.2, 0.7])
    return f.superficie(fins_a_baix=True)


# ---------------------------------------------------------------------------------------------
# Voladors
# ---------------------------------------------------------------------------------------------
def dron(llum):
    """Platet amb cúpula de vidre i el pilot a dins; llum = quina de les sis llums és encesa."""
    W, H = 72, 56
    f = figura(W, H)
    f.el·lipse("negre", 27, 38, 45, 46)
    f.el·lipse("energia", 31, 40, 41, 45, "brilla")
    f.el·lipse("ovni", 3, 22, 69, 43, "esfera")
    f.el·lipse("ovni_f", 2, 29, 70, 38, grup="anella")
    f.marca_linia((6, 33), (66, 33), 1)
    for k in range(6):
        x = 9 + k * 10.8
        enc = k == llum or k == (llum + 3) % 6
        f.el·lipse("energia" if enc else "negre", x - 2, 32, x + 2, 35, "brilla" if enc else "pla")
    f.el·lipse("vidre", 20, 6, 52, 30, "esfera")
    f.el·lipse("pell", 28, 11, 44, 28, "esfera")                          # pilot
    for x0 in (30, 37):
        f.el·lipse("ull_n", x0, 16, x0 + 5, 22, "pla")
        f.px(x0 + 1, 17, MAT["ull_n"][4])
    f.linia((34, 25), (38, 25), MAT["pell"][0])
    for x, y in ((24, 13), (25, 12), (26, 11), (27, 10), (23, 15), (46, 24), (47, 23)):
        f.px(x, y, MAT["vidre"][4])                                      # reflex de la cúpula
    return f.superficie()


def lloctinent(llum):
    """Platet blindat del lloctinent: casc vermell i bronze, dos canons i el pilot amb cresta."""
    W, H = 104, 78
    f = figura(W, H)
    f.el·lipse("negre", 38, 54, 66, 66)
    f.el·lipse("energia", 44, 57, 60, 64, "brilla")
    for s in (-1, 1):                                                      # canons laterals
        cx = 52 + s * 34
        f.poli("negre", [(cx - 5, 50), (cx + 5, 50), (cx + 3 + s * 2, 62), (cx - 3 + s * 2, 62)])
        f.poli("energia", [(cx - 3 + s * 2, 62), (cx + 3 + s * 2, 62), (cx + 2 + s * 2, 65), (cx - 2 + s * 2, 65)],
               "brilla")
    f.el·lipse("quitina", 4, 34, 100, 58, "esfera")
    f.el·lipse("bronze", 3, 42, 101, 51, grup="anella")
    f.el·lipse("vermell", 18, 26, 86, 46, "esfera")
    for k in range(8):
        x = 10 + k * 12
        enc = k % 4 == llum
        f.el·lipse("brasa" if enc else "quitina_f", x - 2, 45, x + 2, 48, "brilla" if enc else "pla")
    f.el·lipse("vidre", 34, 8, 70, 34, "esfera")
    f.el·lipse("pell", 42, 14, 62, 32, "esfera")                          # pilot
    f.poli("bronze", [(44, 16), (52, 8), (60, 16), (52, 13)])             # cresta
    for x0 in (45, 53):
        f.el·lipse("ull_n", x0, 19, x0 + 6, 25, "pla")
        f.px(x0 + 1, 20, MAT["ull_n"][4])
    for s in (-1, 1):                                                      # reixa de la cúpula
        f.linia((52 + s * 9, 10), (52 + s * 13, 30), MAT["vermell"][1])
    for x, y in ((38, 15), (39, 14), (40, 13), (41, 12), (37, 17)):
        f.px(x, y, MAT["vidre"][4])
    return f.superficie()


def cacador(flama):
    """Interceptor taronja vist de costat (mirant a la dreta)."""
    W, H = 62, 32
    f = figura(W, H)
    f.poli("taronja", [(16, 12), (26, 12), (12, 2), (7, 2)])               # ala de darrere
    f.poli("negre", [(1, 12), (8, 11), (8, 20), (1, 19)])                  # tovera
    f.el·lipse("energia", -1 - flama, 13, 3, 18, "brilla")
    f.poli("taronja", [(6, 11), (20, 9), (40, 9), (52, 12), (60, 16), (52, 19), (40, 22), (20, 22), (6, 20)])
    f.poli("vidre", [(34, 9), (44, 10), (49, 13), (36, 13)], "esfera")
    for x in (14, 20, 26):                                                 # galons
        f.linia((x, 12), (x + 3, 16), MAT["negre"][1])
        f.linia((x + 3, 16), (x, 20), MAT["negre"][1])
    f.poli("taronja", [(16, 20), (28, 20), (14, 30), (9, 30)])             # ala de davant
    f.linia((12, 29), (24, 21), MAT["negre"][1])
    f.marca_linia((22, 11), (46, 11), 1)
    return f.superficie()


# ---------------------------------------------------------------------------------------------
# Exportació i previsualització
# ---------------------------------------------------------------------------------------------
def tots():
    """{tipus: {"llenç", "ancora", "anims": {anim: [(superfície, boca)]}}}."""
    t = {}
    t["soldat"] = {"llenç": (104, 68), "ancora": (OX + 23, TERRA),
                   "anims": {anim: [soldat(p) for p in poses] for anim, poses in poses_soldat().items()}}
    an, emissors = {}, {}
    for anim, poses in poses_escuder().items():
        fr = []
        for p in poses:
            s, boca, em = escuder(p)
            fr.append((s, boca))
            emissors.setdefault(anim, []).append(em)
        an[anim] = fr
    t["escut"] = {"llenç": (104, 68), "ancora": (OX + 22, TERRA), "anims": an, "emissors": emissors}
    t["kamikaze"] = {"llenç": (42, 30), "ancora": (20, TERRA_K),
                     "anims": {"corre": [(kamikaze(math.tau * i / 4), None) for i in range(4)],
                               "armat": [(kamikaze(0.0, True), None)]}}
    # voladors: l'ancoratge és el centre del llenç (el joc els dibuixa centrats i els inclina)
    t["dron"] = {"llenç": (72, 56), "ancora": (36, 28), "anims": {"vola": [(dron(i), None) for i in range(3)]}}
    t["lloctinent"] = {"llenç": (104, 78), "ancora": (52, 39),
                       "anims": {"vola": [(lloctinent(i), None) for i in range(4)]}}
    t["cacador"] = {"llenç": (62, 32), "ancora": (31, 16), "anims": {"vola": [(cacador(i), None) for i in range(2)]}}
    return t


def generar():
    pygame.display.set_mode((1, 1))
    t = tots()
    imatges, info = {}, {}
    for tipus, d in t.items():
        e = {"llenç": list(d["llenç"]), "ancora": list(d["ancora"]), "anims": {}, "boques": {}, "desp": {}}
        for anim, frames in d["anims"].items():
            noms = []
            for k, (s, boca) in enumerate(frames):
                nom = f"{tipus}_{anim}_{k}"
                imatges[nom], desp = retallar(s)
                e["desp"][nom] = list(desp)
                if boca:
                    e["boques"][nom] = list(boca)
                noms.append(nom)
            e["anims"][anim] = noms
        if "emissors" in d:
            e["emissors"] = {f"{tipus}_{anim}_{k}": list(p) for anim, ps in d["emissors"].items()
                             for k, p in enumerate(ps)}
        info[tipus] = e
    atles, rects = empaquetar(imatges, ample=512)
    for e in info.values():
        e["imatges"] = {n: rects[n] + d for n, d in e.pop("desp").items()}
    pygame.image.save(atles, os.path.join(SORTIDA, "enemics_hd.png"))
    with open(os.path.join(SORTIDA, "enemics_hd.json"), "w") as fit:
        json.dump(info, fit, separators=(",", ":"))
    print("enemics_hd.png", atles.get_size(), len(rects), "imatges")
    return atles, info


def vista(sortida, k=4):
    pygame.display.set_mode((1, 1))
    files = [[s for frames in d["anims"].values() for s, _ in frames] for d in tots().values()]
    W = max(sum(s.get_width() * k + 8 for s in fila) for fila in files) + 8
    H = sum(max(s.get_height() for s in fila) * k + 8 for fila in files) + 8
    out = pygame.Surface((W, H))
    out.fill((58, 60, 78))
    y = 8
    for fila in files:
        x = 8
        for s in fila:
            out.blit(pygame.transform.scale(s, (s.get_width() * k, s.get_height() * k)), (x, y))
            x += s.get_width() * k + 8
        y += max(s.get_height() for s in fila) * k + 8
    pygame.image.save(out, sortida)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        vista(sys.argv[1])
    else:
        generar()
