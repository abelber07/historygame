"""Genera la Nau Mare i el Nucli de Xylos en alta definició a assets/img/finals_hd.png + finals_hd.json.

    python3 tools/generar_finals.py [vista.png]

Nau Mare: casc de quitina amb un cervell viu dins d'una cúpula de vidre (la ment fosa amb el metall), anella
de llums (les encén el joc), tres canons que surten abans de disparar, dues portes de hangar que s'obren per
treure drons i una versió malmesa (fase de fúria).
Nucli: esfera de carn amb venes i un ull enorme (l'iris i la pupil·la els pinta el joc), corona d'urpes de
quitina, tentacles que ondulen, parpelles, esquerdes i venes que s'encenen amb un pols cap a l'ull.
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame  # noqa: E402
from pintor import Figura, comprovar_paleta, empaquetar, retallar  # noqa: E402
from generar_enemics import MAT as MAT_ENEMICS  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SORTIDA = os.path.join(AQUI, "..", "assets", "img")

MAT = dict(MAT_ENEMICS)
MAT.update({
    "carn": [(60, 10, 46), (130, 30, 98), (184, 62, 140), (222, 112, 180), (248, 176, 220)],
    "carn_f": [(36, 8, 32), (84, 22, 70), (122, 40, 104), (160, 70, 140), (204, 120, 186)],
    "escl": [(96, 60, 70), (200, 170, 170), (236, 214, 210), (250, 236, 232), (255, 250, 248)],
    "cervell": [(70, 20, 50), (180, 70, 130), (230, 120, 176), (250, 170, 210), (255, 220, 236)],
})
BRILLANTS = ("quitina", "quitina_f", "negre", "metall", "ovni", "vidre", "banya", "escl")
VENA = [(110, 20, 90), (210, 70, 180), (255, 170, 240)]
comprovar_paleta(MAT)


def figura(w, h):
    return Figura(w, h, MAT, BRILLANTS)


# ---------------------------------------------------------------------------------------------
# Nau Mare
# ---------------------------------------------------------------------------------------------
NAU_W, NAU_H, NAU_CX = 272, 146, 136
CANONS = [(61, 106), (136, 108), (211, 106)]
HANGARS = [(98, 104), (174, 104)]
LLUMS_NAU = [(round(NAU_CX + 128 * math.cos(a)), round(74 + 9 * math.sin(a)))
             for a in (math.pi * (0.06 + 0.88 * i / 15) for i in range(16))]


def nau(canons=0, hangar=0, dany=0):
    f = figura(NAU_W, NAU_H)
    cx = NAU_CX
    f.el·lipse("ovni_f", 30, 64, 242, 120, "esfera")                       # panxa
    for hx, hy in HANGARS:                                                 # portes del hangar
        if hangar:
            f.rect("negre", hx - 13, hy - 6, hx + 13, hy + 8, "pla")
            f.el·lipse("ovni", hx - 7, hy - 3, hx + 7, hy + 5, "esfera")    # un dron a punt de sortir
            f.el·lipse("energia", hx - 2, hy, hx + 2, hy + 3, "brilla")
        else:
            f.rect("metall", hx - 13, hy - 6, hx + 13, hy + 8)
            for k in range(-9, 10, 6):
                f.linia((hx + k, hy - 4), (hx + k + 3, hy + 6), MAT["metall"][1])
    f.el·lipse("quitina", 6, 38, 266, 100, "esfera")                       # casc
    for k in range(-6, 7):                                                 # panells radials
        x0 = cx + k * 16
        f.marca_linia((x0, 50), (cx + k * 21, 92), -1)
        f.marca_linia((x0 + 1, 50), (cx + k * 21 + 1, 92), 1)
    f.el·lipse("quitina_f", 4, 62, 268, 84)                                # anella de llums
    f.marca_linia((12, 70), (260, 70), 1)
    for x, y in LLUMS_NAU:
        f.el·lipse("negre", x - 2.5, y - 2, x + 2.5, y + 2, "pla")
    f.el·lipse("quitina", 60, 22, 212, 64, "esfera")                       # coberta
    for s in (-1, 1):                                                      # torres amb punxa
        tx = cx + s * 58
        f.poli("quitina_f", [(tx - 8, 44), (tx + 8, 44), (tx + 4, 22), (tx - 4, 22)])
        f.poli("negre", [(tx - 3, 23), (tx + 3, 23), (tx + s * 2, 6)])
        f.el·lipse("brasa", tx - 2, 30, tx + 2, 34, "brilla")
    for s in (-1, 1):                                                      # tubs que alimenten el cervell
        f.membre("negre", [(cx + s * 34, 40), (cx + s * 26, 30), (cx + s * 18, 28)], [2.4, 2.0, 1.6])
    f.el·lipse("vidre", 102, 0, 170, 46, "esfera")                         # cúpula
    f.el·lipse("cervell", 112, 8, 160, 40, "esfera", grup="cervell")        # el cervell de la nau
    for c in (((122, 14), (128, 20), (126, 28), (132, 34)), ((136, 10), (138, 20), (136, 30), (138, 38)),
              ((150, 14), (146, 22), (150, 30)), ((116, 26), (124, 30)), ((152, 26), (156, 32))):
        f.marca_corba(list(c), -1)
        f.marca_corba([(x + 1, y + 1) for x, y in c], 1)
    for x, y in ((110, 8), (111, 7), (112, 6), (113, 5), (108, 11)):
        f.px(x, y, MAT["vidre"][4])
    for k, (x, y) in enumerate(CANONS):                                    # canons
        if canons:
            f.membre("negre", [(x, y), (x + (x - cx) * 0.06, y + 14)], [3.6, 3.0])
            f.el·lipse("brasa", x + (x - cx) * 0.06 - 3, y + 12, x + (x - cx) * 0.06 + 3, y + 18, "brilla")
        f.el·lipse("ovni_f", x - 11, y - 9, x + 11, y + 7, "esfera")
        f.linia((x - 6, y - 1), (x + 6, y - 1), MAT["negre"][1])
    if dany:                                                               # danys de la fase de fúria
        for (x0, y0), (x1, y1) in (((52, 54), (78, 74)), ((180, 46), (206, 66)), ((110, 72), (128, 92)),
                                   ((226, 60), (240, 82))):
            mig = ((x0 + x1) / 2 + 3, (y0 + y1) / 2 - 2)
            f.corba([(x0, y0), mig, (x1, y1)], MAT["quitina"][0])
            f.corba([(x0 + 1, y0), (mig[0] + 1, mig[1]), (x1 + 1, y1)], MAT["brasa"][2])
        for x, y in ((70, 64), (196, 56)):
            f.el·lipse("negre", x - 6, y - 4, x + 6, y + 4, "pla")
            f.el·lipse("brasa", x - 3, y - 2, x + 3, y + 2, "brilla")
        for _ in range(40):
            rx, ry = random.uniform(30, 240), random.uniform(46, 92)
            f.marca(rx, ry, -1)
    return f.superficie()


# ---------------------------------------------------------------------------------------------
# Nucli de Xylos
# ---------------------------------------------------------------------------------------------
NUC_W = NUC_H = 220
NUC_C = 110
ULL_R = 36
N_TENT = 8
VENES_NUCLI = []                       # línies (des de fora cap a l'ull) per a la capa que brilla
for _k in range(10):
    _a = math.tau * _k / 10 + 0.2
    _p = [(NUC_C + math.cos(_a) * 52, NUC_C + math.sin(_a) * 52)]
    for _r in (46, 42, 38):
        _a += random.Random(_k * 7 + _r).uniform(-0.12, 0.12)
        _p.append((NUC_C + math.cos(_a) * _r, NUC_C + math.sin(_a) * _r))
    VENES_NUCLI.append(_p)


def tentacles_nucli(f, fase):
    for k in range(10):
        a = math.tau * k / 10 + 0.32
        pts = []
        for i in range(13):
            t = i / 12
            r = 44 + 62 * t
            aa = a + 0.28 * math.sin(fase + k * 1.7 - t * 3.4) * t
            pts.append((NUC_C + math.cos(aa) * r, NUC_C + math.sin(aa) * r))
        f.membre("carn_f", pts, [max(0.8, 7.5 * (1 - i / 12) ** 1.1 + 0.4) for i in range(13)], grup=f"t{k}")
        for i in range(4, 11, 2):
            x, y = pts[i]
            f.px(x, y, MAT["carn_f"][4])


def cos_nucli(f, dany=0):
    c = NUC_C
    f.cercle("quitina_f", c, c, 60)
    for k in range(12):                                                    # corona d'urpes
        a = math.tau * k / 12
        b = a + 0.16
        base1 = (c + math.cos(a - 0.16) * 54, c + math.sin(a - 0.16) * 54)
        base2 = (c + math.cos(a + 0.16) * 54, c + math.sin(a + 0.16) * 54)
        punta = (c + math.cos(b) * 80, c + math.sin(b) * 80)
        f.poli("quitina", [base1, punta, base2], grup=f"urpa{k}")
        f.marca_linia(base1, punta, 1)
    f.cercle("carn", c, c, 54, "esfera")                                   # esfera de carn
    for vena in VENES_NUCLI:
        f.corba(vena, VENA[0])
    f.cercle("carn_f", c, c, ULL_R + 5, "fosc")                            # conca
    f.cercle("escl", c, c, ULL_R, "esfera")                                # blanc de l'ull
    rnd = random.Random(3)
    for k in range(12):                                                    # capil·lars
        a = rnd.uniform(0, math.tau)
        pts = [(c + math.cos(a) * (ULL_R - 1), c + math.sin(a) * (ULL_R - 1))]
        for _ in range(3):
            a += rnd.uniform(-0.25, 0.25)
            r = math.dist(pts[-1], (c, c)) - rnd.uniform(4, 7)
            pts.append((c + math.cos(a) * r, c + math.sin(a) * r))
        f.corba(pts, (200, 40, 60))
    if dany:                                                               # esquerdes que brillen
        for k in range(3 if dany == 1 else 6):
            a = math.tau * k / 6 + 0.5
            pts = [(c + math.cos(a) * 60, c + math.sin(a) * 60)]
            for r in (56, 50, 45):
                a += rnd.uniform(-0.15, 0.15)
                pts.append((c + math.cos(a) * r, c + math.sin(a) * r))
            f.corba(pts, VENA[1])
            f.corba(pts[1:-1], VENA[2])


def parpelles_nucli(tancat):
    """Parpelles de carn: mig closes o closes del tot (es pinten damunt de l'ull)."""
    f = figura(NUC_W, NUC_H)
    c = NUC_C
    r = ULL_R + 1
    tall = 0 if tancat else 16
    f.poli("carn", [(c + math.cos(a) * r, c + math.sin(a) * r) for a in (math.pi + math.pi * i / 16 for i in range(17))]
           + [(c + r, c - tall), (c - r, c - tall)], "esfera", grup="p")
    f.poli("carn", [(c + math.cos(a) * r, c + math.sin(a) * r) for a in (math.pi * i / 16 for i in range(17))]
           + [(c - r, c + tall), (c + r, c + tall)], "esfera", grup="p")
    f.marca_linia((c - r + 2, c - tall), (c + r - 2, c - tall), -2)
    f.marca_linia((c - r + 2, c + tall), (c + r - 2, c + tall), -2)
    return f.superficie()


def capa_venes_nucli(k=None, n=6):
    """Venes que s'encenen amb un pols que corre cap a l'ull (k=None: totes enceses)."""
    s = pygame.Surface((NUC_W, NUC_H), pygame.SRCALPHA)
    for vena in VENES_NUCLI:
        dist = 0.0
        for a, b in zip(vena, vena[1:]):
            passos = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) or 1
            for i in range(passos + 1):
                x = round(a[0] + (b[0] - a[0]) * i / passos)
                y = round(a[1] + (b[1] - a[1]) * i / passos)
                d = dist + math.dist(a, (x, y))
                if k is None:
                    s.set_at((x, y), VENA[2])
                else:
                    fase = (d / 2.5 - k) % n
                    if fase < 1.2:
                        s.set_at((x, y), VENA[2])
                    elif fase < 2.4:
                        s.set_at((x, y), VENA[1])
            dist += math.dist(a, b)
    return s


def nucli_cos(dany):
    f = figura(NUC_W, NUC_H)
    cos_nucli(f, dany)
    return f.superficie()


def nucli_tentacles(k):
    f = figura(NUC_W, NUC_H)
    tentacles_nucli(f, math.tau * k / N_TENT)
    return f.superficie()


# ---------------------------------------------------------------------------------------------
# Exportació i previsualització
# ---------------------------------------------------------------------------------------------
def tots():
    imatges = {}
    for c in (0, 1):
        for h in (0, 1):
            for d in (0, 1):
                imatges[f"nau_{c}{h}{d}"] = nau(c, h, d)
    for k in range(N_TENT):
        imatges[f"nucli_tent_{k}"] = nucli_tentacles(k)
    for d in (0, 1, 2):
        imatges[f"nucli_cos_{d}"] = nucli_cos(d)
    imatges["nucli_parp_mig"] = parpelles_nucli(False)
    imatges["nucli_parp_tancat"] = parpelles_nucli(True)
    for k in range(6):
        imatges[f"nucli_venes_{k}"] = capa_venes_nucli(k)
    imatges["nucli_venes_tot"] = capa_venes_nucli()
    return imatges


def generar():
    pygame.display.set_mode((1, 1))
    retalls, desp = {}, {}
    for nom, s in tots().items():
        retalls[nom], desp[nom] = retallar(s)
    atles, rects = empaquetar(retalls, ample=1024)
    info = {"imatges": {n: rects[n] + list(desp[n]) for n in rects},
            "nau": {"llenç": [NAU_W, NAU_H], "canons": CANONS, "hangars": HANGARS, "llums": LLUMS_NAU,
                    "cervell": [NAU_CX, 24]},
            "nucli": {"llenç": [NUC_W, NUC_H], "ull": [NUC_C, NUC_C], "radi_ull": ULL_R, "n_tent": N_TENT}}
    pygame.image.save(atles, os.path.join(SORTIDA, "finals_hd.png"))
    with open(os.path.join(SORTIDA, "finals_hd.json"), "w") as fit:
        json.dump(info, fit, separators=(",", ":"))
    print("finals_hd.png", atles.get_size(), len(rects), "imatges")


def vista(sortida, k=3):
    pygame.display.set_mode((1, 1))
    im = tots()
    files = [[im["nau_000"], im["nau_110"], im["nau_001"]],
             [im["nucli_tent_0"], im["nucli_cos_0"], im["nucli_cos_2"]]]
    # composició del nucli (tentacles + cos + iris de prova + venes)
    comp = pygame.Surface((NUC_W, NUC_H), pygame.SRCALPHA)
    comp.blit(im["nucli_tent_2"], (0, 0))
    comp.blit(im["nucli_cos_1"], (0, 0))
    pygame.draw.circle(comp, (120, 40, 150), (NUC_C - 6, NUC_C + 4), 18)
    pygame.draw.circle(comp, (190, 70, 220), (NUC_C - 6, NUC_C + 4), 15)
    pygame.draw.ellipse(comp, (20, 0, 20), (NUC_C - 9, NUC_C - 8, 6, 24))
    comp.blit(im["nucli_venes_2"], (0, 0))
    files[1].append(comp)
    mig = comp.copy()
    mig.blit(im["nucli_parp_mig"], (0, 0))
    files[1].append(mig)
    W = max(sum(s.get_width() * k + 8 for s in fila) for fila in files) + 8
    H = sum(max(s.get_height() for s in fila) * k + 8 for fila in files) + 8
    out = pygame.Surface((W, H))
    out.fill((36, 34, 52))
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
