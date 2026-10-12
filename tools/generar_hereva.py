"""Genera la Hereva (cap final del DLC «Ecos de Xylos») a assets/img/hereva_hd.png + hereva_hd.json.

    python3 tools/generar_hereva.py [vista.png]

La Hereva és una llavor del Nucli que creix dins d'un capoll de cristall, alimentada pel cant dels orfes.
  * capoll: ou de plaques de cristall turquesa amb una costura daurada que brilla i corona de pètals d'or;
    dues versions (sencer i esquerdat). Mentre és dins, el joc hi pinta l'ull tancat que batega.
  * nascuda (a mitja vida el capoll esclata): esfera de carn verda, ull gran (l'iris el pinta el joc, daurat),
    banyes de cristall que fan de corona, tentacles prims que ondulen i la meitat de baix del capoll trencat
    davant del cos. Esquerdes que brillen segons la vida.
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
    "carn_v": [(12, 42, 32), (28, 98, 68), (52, 148, 94), (106, 198, 128), (186, 238, 186)],
    "carn_vf": [(10, 30, 26), (22, 70, 54), (36, 104, 72), (62, 140, 92), (120, 186, 136)],
    "crist": [(10, 48, 62), (36, 126, 146), (76, 196, 208), (156, 238, 244), (232, 255, 255)],
    "crist_f": [(8, 34, 46), (24, 88, 106), (46, 136, 152), (90, 184, 196), (170, 230, 236)],
    "or": [(68, 44, 10), (158, 108, 28), (218, 168, 58), (248, 212, 116), (255, 244, 198)],
    "escl_v": [(70, 90, 70), (196, 214, 190), (230, 240, 222), (246, 252, 240), (254, 255, 250)],
})
BRILLANTS = ("crist", "crist_f", "or", "escl_v", "quitina", "negre")
COSTURA = [(140, 100, 20), (255, 210, 90), (255, 250, 210)]
comprovar_paleta(MAT)

W = H = 230
C = 115
ULL_R = 26
N_TENT = 8


def figura():
    return Figura(W, H, MAT, BRILLANTS)


def ou(f, mat, cx, cy, rx, ry, mode="volum", grup=None):
    """Ou (més punxegut per dalt) com a polígon."""
    pts = []
    for i in range(40):
        a = math.tau * i / 40
        r = 1 - 0.18 * max(0.0, -math.sin(a))
        pts.append((cx + math.cos(a) * rx * r, cy + math.sin(a) * ry))
    return f.poli(mat, pts, mode, grup=grup)


def petals(f, n=7, obert=0.0):
    """Corona de pètals d'or darrere del capoll (obert: com s'obren quan neix)."""
    for k in range(n):
        a = math.pi + math.pi * (k + 0.5) / n
        a = a + (a - 1.5 * math.pi) * 0.35 * obert
        r0, r1 = 46, 78 + 10 * obert
        base1 = (C + math.cos(a - 0.2) * r0, C + 6 + math.sin(a - 0.2) * r0)
        base2 = (C + math.cos(a + 0.2) * r0, C + 6 + math.sin(a + 0.2) * r0)
        punta = (C + math.cos(a) * r1, C + 6 + math.sin(a) * r1)
        f.poli("or", [base1, (C + math.cos(a - 0.12) * (r1 - 14), C + 6 + math.sin(a - 0.12) * (r1 - 14)), punta,
                      (C + math.cos(a + 0.12) * (r1 - 14), C + 6 + math.sin(a + 0.12) * (r1 - 14)), base2], grup=f"pet{k}")
        f.marca_linia(((base1[0] + base2[0]) / 2, (base1[1] + base2[1]) / 2), punta, 1)


def arrels(f):
    """Arrels de cristall fosc que subjecten el capoll per baix."""
    for k, (dx, llarg) in enumerate(((-34, 40), (-16, 46), (16, 46), (34, 40))):
        pts = [(C + dx * 0.6, C + 44), (C + dx, C + 60), (C + dx * 1.5, C + 44 + llarg)]
        f.membre("crist_f", pts, [5, 3.5, 1.2], grup=f"arrel{k}")


def capoll(esquerdat):
    f = figura()
    petals(f)
    arrels(f)
    ou(f, "crist", C, C + 4, 50, 56, grup="ou")
    rnd = random.Random(7)
    for k in range(9):                                                     # plaques del capoll
        a = -math.pi / 2 + math.tau * k / 9
        p0 = (C + math.cos(a) * 14, C + 4 + math.sin(a) * 16)
        p1 = (C + math.cos(a) * 46, C + 4 + math.sin(a) * 50)
        f.marca_linia(p0, p1, -1)
    for y in (C - 26, C + 6, C + 34):                                      # juntes horitzontals
        f.marca_corba([(C - 44, y + 6), (C - 20, y), (C + 20, y), (C + 44, y + 6)], -1)
    costura = [(C, C - 50)]                                                # costura daurada (per on es trencarà)
    y = C - 50
    while y < C + 56:
        y += rnd.uniform(6, 10)
        costura.append((C + rnd.uniform(-5, 5), y))
    f.corba(costura, COSTURA[1])
    f.corba([(x + 1, y) for x, y in costura[1:-1]], COSTURA[2])
    f.el·lipse("crist_f", C - 18, C - 6, C + 18, C + 18, "fosc")          # finestra a l'ull de dins
    if esquerdat:
        for k in range(5):
            a = rnd.uniform(0, math.tau)
            pts = [(C + math.cos(a) * 48, C + 4 + math.sin(a) * 52)]
            for r in (40, 32, 26):
                a += rnd.uniform(-0.25, 0.25)
                pts.append((C + math.cos(a) * r, C + 4 + math.sin(a) * r * 1.08))
            f.corba(pts, COSTURA[1])
            f.corba(pts[1:-1], COSTURA[2])
    return f.superficie()


def tentacles(fase):
    f = figura()
    for k in range(8):
        a = math.tau * k / 8 + 0.4
        pts = []
        for i in range(12):
            t = i / 11
            r = 34 + 76 * t
            aa = a + 0.34 * math.sin(fase + k * 1.9 - t * 3.8) * t
            pts.append((C + math.cos(aa) * r, C + 10 + math.sin(aa) * r * 0.9))
        f.membre("carn_vf", pts, [max(0.8, 6.2 * (1 - i / 11) ** 1.1 + 0.4) for i in range(12)], grup=f"t{k}")
        for i in range(3, 10, 2):
            x, y = pts[i]
            f.px(x, y, MAT["or"][3])
    return f.superficie()


def banyes(f):
    """Corona de banyes de cristall (la Hereva vol ser la nova reina)."""
    for k, (a, llarg, gruix) in enumerate(((-2.2, 46, 6), (-1.9, 58, 7), (-1.5708, 40, 5), (-1.24, 58, 7), (-0.94, 46, 6))):
        b = (C + math.cos(a) * 30, C - 4 + math.sin(a) * 30)
        m = (C + math.cos(a) * (30 + llarg * 0.55) + math.cos(a + 1.57) * 4, C - 4 + math.sin(a) * (30 + llarg * 0.55))
        p = (C + math.cos(a) * (30 + llarg), C - 4 + math.sin(a) * (30 + llarg))
        f.membre("crist", [b, m, p], [gruix, gruix * 0.6, 0.8], grup=f"banya{k}")
        f.marca_linia(b, p, 1)


def cos_nascuda(dany):
    f = figura()
    petals(f, obert=1.0)
    banyes(f)
    c = (C, C - 4)
    f.cercle("carn_v", c[0], c[1], 38, "esfera")
    rnd = random.Random(11)
    for k in range(8):                                                     # venes daurades cap a l'ull
        a = math.tau * k / 8 + 0.3
        pts = [(c[0] + math.cos(a) * 37, c[1] + math.sin(a) * 37)]
        for r in (33, 30):
            a += rnd.uniform(-0.2, 0.2)
            pts.append((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r))
        f.corba(pts, COSTURA[0])
    f.cercle("carn_vf", c[0], c[1], ULL_R + 4, "fosc")                     # conca
    f.cercle("escl_v", c[0], c[1], ULL_R, "esfera")                        # blanc de l'ull
    if dany:
        for k in range(2 if dany == 1 else 5):
            a = math.tau * k / 5 + 0.9
            pts = [(c[0] + math.cos(a) * 38, c[1] + math.sin(a) * 38)]
            for r in (35, 32):
                a += rnd.uniform(-0.2, 0.2)
                pts.append((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r))
            f.corba(pts, COSTURA[1])
    return f.superficie()


def closca_trencada():
    """La meitat de baix del capoll, trencada en punxes (es pinta davant del cos nascut)."""
    f = figura()
    arrels(f)
    rnd = random.Random(5)
    vora = []
    n = 11
    for i in range(n + 1):
        x = C - 50 + 100 * i / n
        vora.append((x, C + 20 + (rnd.uniform(-14, -4) if i % 2 else rnd.uniform(2, 8))))
    pts = vora + [(C + 50, C + 26)]
    for i in range(16):
        a = math.pi * i / 15
        pts.append((C + math.cos(a) * 50 * 0.98, C + 4 + math.sin(a) * 56))
    pts.append((C - 50, C + 26))
    f.poli("crist", pts, grup="closca")
    f.marca_corba([(x, y + 4) for x, y in vora], 2)
    for k in range(5):
        x = C - 36 + k * 18
        f.marca_linia((x, C + 30), (C + (x - C) * 0.6, C + 56), -1)
    return f.superficie()


def parpelles(tancat):
    f = figura()
    c = (C, C - 4)
    r = ULL_R + 1
    tall = 0 if tancat else 11
    f.poli("carn_v", [(c[0] + math.cos(a) * r, c[1] + math.sin(a) * r) for a in (math.pi + math.pi * i / 16 for i in range(17))]
           + [(c[0] + r, c[1] - tall), (c[0] - r, c[1] - tall)], "esfera", grup="p")
    f.poli("carn_v", [(c[0] + math.cos(a) * r, c[1] + math.sin(a) * r) for a in (math.pi * i / 16 for i in range(17))]
           + [(c[0] - r, c[1] + tall), (c[0] + r, c[1] + tall)], "esfera", grup="p")
    f.marca_linia((c[0] - r + 2, c[1] - tall), (c[0] + r - 2, c[1] - tall), -2)
    f.marca_linia((c[0] - r + 2, c[1] + tall), (c[0] + r - 2, c[1] + tall), -2)
    return f.superficie()


def tots():
    im = {}
    for d in (0, 1):
        im[f"hereva_capoll_{d}"] = capoll(d)
    for k in range(N_TENT):
        im[f"hereva_tent_{k}"] = tentacles(math.tau * k / N_TENT)
    for d in (0, 1, 2):
        im[f"hereva_cos_{d}"] = cos_nascuda(d)
    im["hereva_closca"] = closca_trencada()
    im["hereva_parp_mig"] = parpelles(False)
    im["hereva_parp_tancat"] = parpelles(True)
    return im


def generar():
    pygame.display.set_mode((1, 1))
    retalls, desp = {}, {}
    for nom, s in tots().items():
        retalls[nom], desp[nom] = retallar(s)
    atles, rects = empaquetar(retalls, ample=512)
    info = {"imatges": {n: rects[n] + list(desp[n]) for n in rects},
            "llenç": [W, H], "ull": [C, C - 4], "ull_capoll": [C, C + 6], "radi_ull": ULL_R, "n_tent": N_TENT}
    pygame.image.save(atles, os.path.join(SORTIDA, "hereva_hd.png"))
    with open(os.path.join(SORTIDA, "hereva_hd.json"), "w") as fit:
        json.dump(info, fit, separators=(",", ":"))
    print("hereva_hd.png", atles.get_size(), len(rects), "imatges")


def vista(sortida, k=3):
    pygame.display.set_mode((1, 1))
    im = tots()

    def iris(s, c):
        pygame.draw.circle(s, (130, 90, 20), (c[0] - 4, c[1] + 3), 13)
        pygame.draw.circle(s, (240, 190, 60), (c[0] - 4, c[1] + 3), 11)
        pygame.draw.ellipse(s, (20, 10, 0), (c[0] - 6, c[1] - 5, 4, 16))
    comp1 = pygame.Surface((W, H), pygame.SRCALPHA)
    comp1.blit(im["hereva_capoll_0"], (0, 0))
    comp2 = pygame.Surface((W, H), pygame.SRCALPHA)
    comp2.blit(im["hereva_capoll_1"], (0, 0))
    comp3 = pygame.Surface((W, H), pygame.SRCALPHA)
    comp3.blit(im["hereva_tent_0"], (0, 0))
    comp3.blit(im["hereva_cos_0"], (0, 0))
    iris(comp3, (C, C - 4))
    comp3.blit(im["hereva_closca"], (0, 0))
    comp4 = pygame.Surface((W, H), pygame.SRCALPHA)
    comp4.blit(im["hereva_tent_3"], (0, 0))
    comp4.blit(im["hereva_cos_2"], (0, 0))
    iris(comp4, (C, C - 4))
    comp4.blit(im["hereva_parp_mig"], (0, 0))
    comp4.blit(im["hereva_closca"], (0, 0))
    fila = [comp1, comp2, comp3, comp4]
    out = pygame.Surface((len(fila) * (W * k + 8) + 8, H * k + 16))
    out.fill((20, 34, 26))
    for i, s in enumerate(fila):
        out.blit(pygame.transform.scale(s, (W * k, H * k)), (8 + i * (W * k + 8), 8))
    pygame.image.save(out, sortida)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        vista(sys.argv[1])
    else:
        generar()
