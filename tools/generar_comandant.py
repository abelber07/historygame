"""Genera el Comandant Suprem en alta definició (capes animades) a assets/img/comandant.png + comandant.json.

    python3 tools/generar_comandant.py

El cos es pinta per capes que el joc compon a cada fotograma:
    tentacles (fotogrames d'ondulació + postures), braços (esquerre i dret, diverses postures),
    cos (fase 1 sencer, fase 2 amb la closca trencada), banyes, cap (boca tancada, mig oberta, oberta)
    i capes de damunt (parpelles, esquerdes, venes que brillen, ulls apagats).
Totes comparteixen el mateix origen: el punt (0, 0) del llenç de LLENC_W x LLENC_H.
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame  # noqa: E402
from pintor import Figura, bezier, comprovar_paleta, empaquetar, mirall, retallar  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SORTIDA = os.path.join(AQUI, "..", "assets", "img")

LLENC_W, LLENC_H = 240, 256
CX = 120            # eix de simetria
CAP = (CX, 70)      # centre del crani

MAT = {
    "pell": [(16, 40, 30), (40, 96, 62), (66, 142, 76), (110, 186, 92), (170, 222, 128)],
    "pell_f": [(14, 32, 30), (30, 74, 58), (48, 108, 70), (78, 146, 84), (128, 190, 112)],
    "ventre": [(52, 60, 40), (150, 168, 104), (196, 208, 140), (226, 234, 176), (246, 250, 214)],
    "quitina": [(34, 24, 52), (72, 58, 102), (106, 88, 140), (148, 128, 180), (204, 188, 228)],
    "quitina_f": [(26, 18, 40), (52, 40, 76), (78, 64, 106), (110, 94, 140), (156, 140, 186)],
    "banya": [(62, 44, 38), (150, 124, 96), (200, 180, 140), (232, 218, 182), (252, 246, 222)],
    "urpa": [(20, 14, 22), (44, 34, 50), (70, 58, 78), (112, 100, 120), (176, 166, 186)],
    "ull": [(70, 36, 10), (196, 130, 20), (240, 196, 50), (255, 230, 110), (255, 248, 190)],
    "boca": [(34, 6, 16), (70, 12, 30), (112, 24, 44), (150, 44, 64), (190, 80, 96)],
    "dent": [(80, 64, 56), (176, 164, 146), (222, 214, 196), (240, 236, 224), (255, 253, 246)],
    "nucli": [(80, 10, 56), (176, 30, 120), (236, 70, 170), (255, 140, 210), (255, 222, 244)],
    "ull_mort": [(40, 34, 30), (84, 76, 66), (112, 104, 90), (136, 128, 112), (158, 150, 132)],
}
BRILLANTS = ("quitina", "quitina_f", "banya", "urpa", "dent")
VENA = [(120, 26, 96), (200, 60, 160), (255, 150, 220)]           # fosca, mitjana, clara
comprovar_paleta(MAT)


def figura():
    return Figura(LLENC_W, LLENC_H, MAT, BRILLANTS)


def sx(s, dx):
    return CX + s * dx


def simetric(punts_esquerra):
    """Polígon simètric a partir de la meitat esquerra (de dalt a baix)."""
    return punts_esquerra + mirall(punts_esquerra[::-1], CX)


# ---------------------------------------------------------------------------------------------
# Cap (coordenades relatives al centre del crani)
# ---------------------------------------------------------------------------------------------
ULL = [(-30, 6), (-22, 4), (-12, 7), (-7, 11), (-11, 15), (-21, 16), (-29, 12)]
ULLS_PETITS = ((-10, -6), (10, -6))          # ulls petits al front, com els d'una aranya
MIRADA_ULL = ((-19, 10), (19, 10))         # centre de les pupil·les dels ulls grans
SOLCS = [[(0, -44), (1, -36), (0, -28), (1, -20), (0, -14)]] + [
    [(s * x, y) for x, y in c] for s in (-1, 1)
    for c in (((6, -38), (12, -40), (20, -38), (27, -31)),
              ((5, -29), (12, -26), (18, -28), (24, -23), (31, -20)),
              ((14, -18), (19, -13), (25, -12), (31, -7)),
              ((14, -34), (16, -31)),
              ((33, -12), (35, -4)),
              ((22, -17), (26, -15)))]


def cap(f, boca="tancada", parpelles="oberts", mort=False, dx=0, dy=0):
    """Crani bombat amb solcs de cervell, celles ossudes, quatre ulls, boca de dents i mandíbules."""
    hx, hy = CAP[0] + dx, CAP[1] + dy

    def P(punts):
        return [(hx + x, hy + y) for x, y in punts]

    f.el·lipse("pell", hx - 36, hy - 46, hx + 36, hy + 22, mode="esfera", grup="cap")
    f.poli("pell", P([(-32, -4), (32, -4), (30, 14), (24, 28), (13, 38), (-13, 38), (-24, 28), (-30, 14)]),
           mode="esfera", grup="cap")

    def solc(punts):                                     # solc enfonsat: fosc i, a sota, la vora que rep la llum
        f.marca_corba(P(punts), -1)
        f.marca_corba(P([(x + 1, y + 1) for x, y in punts]), 1)
    for punts in SOLCS:
        solc(punts)
    rnd = random.Random(7)                               # taques de la pell
    for _ in range(34):
        a = rnd.uniform(0, math.tau)
        r = rnd.uniform(0.25, 0.95)
        x, y = math.cos(a) * 33 * r, -14 + math.sin(a) * 30 * r
        if y < -10:
            f.marca(hx + x, hy + y, -1)
            if rnd.random() < 0.6:
                f.marca(hx + x + 1, hy + y, -1)
    for s in (-1, 1):
        # conques fosques sota les celles
        f.marca_poli(P([(s * x, y) for x, y in ((-34, 3), (-24, 0), (-10, 3), (-4, 10), (-8, 18), (-22, 20),
                                                 (-33, 15))]), -1)
        # celles ossudes, inclinades cap al centre (enfadat): vora clara i ombra a sota
        cella = [(-35, -4), (-26, -7), (-15, -4), (-6, 3), (-3, 7)]
        f.marca_poli(P([(s * x, y) for x, y in cella + [(-5, 9), (-15, 1), (-26, -2), (-35, 1)]]), 1)
        f.marca_corba(P([(s * x, y - 1) for x, y in cella]), 1)
        f.marca_corba(P([(s * x, y + 4) for x, y in cella]), -1)
        f.marca_corba(P([(s * x, y + 5) for x, y in cella]), -1)
        # plecs de les galtes i sota els ulls
        f.marca_corba(P([(s * 31, 18), (s * 26, 27), (s * 18, 34)]), -1)
        f.marca_corba(P([(s * 30, 17), (s * 25, 25)]), 1)
        f.marca_corba(P([(s * 26, 19), (s * 18, 21), (s * 11, 19)]), -1)
    f.marca_corba(P([(0, 8), (0, 20)]), 1)               # pont del nas i narius
    f.marca_corba(P([(1, 9), (1, 20)]), -1)
    for s in (-1, 1):
        for y in (21, 22):
            f.marca(hx + s * 3, hy + y, -2)
    # ulls grans (inclinats cap al centre) i els dos petits del front
    material_ull = "ull_mort" if mort else "ull"
    for s in (-1, 1):
        f.poli(material_ull, P([(s * x, y) for x, y in ULL]), mode="vidre")
    for x, y in ULLS_PETITS:
        f.marca_poli(P([(x - 6, y - 1), (x, y - 5), (x + 6, y - 1), (x + 5, y + 5), (x - 5, y + 5)]), -1)
        f.el·lipse(material_ull, hx + x - 4, hy + y - 3, hx + x + 4, hy + y + 2, mode="vidre")
    # parpelles (de la mateixa pell que el cap): mig closes o closes del tot
    if parpelles != "oberts":
        tot = parpelles == "tancats"
        for s in (-1, 1):
            vora = 17 if tot else 10
            f.poli("pell", P([(s * x, y) for x, y in ((-32, 3), (-22, 1), (-11, 4), (-5, 11), (-9, vora - 1),
                                                       (-21, vora), (-31, vora - 3))]), mode="esfera", grup="cap")
            linia = [(-30, 11), (-21, 13), (-11, 12), (-7, 11)] if tot else [(-30, 9), (-21, 11), (-11, 11), (-7, 11)]
            f.marca_corba(P([(s * x, y) for x, y in linia]), -2)
            f.marca_corba(P([(s * x, y - 1) for x, y in linia]), 1)
        for x, y in ULLS_PETITS:
            baix = y + 3 if tot else y
            f.poli("pell", P([(x - 5, y - 4), (x + 5, y - 4), (x + 5, baix), (x - 5, baix)]), mode="esfera", grup="cap")
            f.marca_linia((hx + x - 3, hy + baix - (1 if tot else 0)), (hx + x + 3, hy + baix - (1 if tot else 0)), -2)
    # boca
    obre = {"tancada": 0.0, "mitja": 0.3, "oberta": 0.58}[boca]
    if boca == "tancada":
        f.poli("boca", P([(-15, 31), (-7, 28), (0, 27), (7, 28), (15, 31), (12, 33), (0, 31), (-12, 33)]), mode="fosc")
        for k in range(-12, 13, 3):                     # dents que s'encreuen
            f.px(hx + k, hy + 28 + (abs(k) > 6) + (abs(k) > 11), MAT["dent"][3])
            f.px(hx + k + 1, hy + 31 + (abs(k) > 8), MAT["dent"][1])
    else:
        alt = 9 if boca == "mitja" else 16
        f.el·lipse("boca", hx - 14, hy + 26, hx + 14, hy + 26 + alt, mode="fosc")
        for k in range(-11, 12, 4):                     # dents de dalt i de baix
            f.poli("dent", P([(k - 1.5, 27), (k + 1.5, 27), (k, 31 + (abs(k) < 6))]), mode="pla")
            f.poli("dent", P([(k - 1.5, 25 + alt), (k + 1.5, 25 + alt), (k, 22 + alt - (abs(k) < 6))]), mode="pla")
        if alt > 10:                                     # gola que brilla
            f.el·lipse("nucli", hx - 5, hy + 32, hx + 5, hy + 36, mode="brilla")
    # mandíbules d'os en pinça: surten de les comissures i es corben sota la barbeta
    for s in (-1, 1):
        base = (hx + s * 18, hy + 27)
        pts = [(0, 0), (s * 3, 6), (s * 2, 12), (s * -2, 17), (s * -8, 20)]
        a = s * obre
        c, sn = math.cos(a), math.sin(a)
        pts = [(base[0] + x * c - y * sn, base[1] + x * sn + y * c) for x, y in pts]
        f.membre("banya", pts[:4], [4.2, 3.8, 3.2, 2.4], grup=f"mand{s}")
        f.membre("urpa", pts[3:], [2.4, 0.8], grup=f"mand{s}")
        for k in (1, 2):
            f.marca_linia((pts[k][0] - 4, pts[k][1] - 1), (pts[k][0] + 4, pts[k][1] + 1), -1)
            f.marca_linia((pts[k][0] - 4, pts[k][1] - 2), (pts[k][0] + 4, pts[k][1]), 1)


def pupil·les(surf, mirada=(0, 0), ira=False, dx=0, dy=0):
    """Pupil·les en escletxa que segueixen el jugador (el joc les pinta a cada fotograma)."""
    hx, hy = CAP[0] + dx, CAP[1] + dy
    for ux, uy in MIRADA_ULL:
        cx = hx + ux + round(mirada[0] * 3)
        cy = hy + uy + round(mirada[1] * 2)
        alt = 8 if not ira else 6
        pygame.draw.rect(surf, (90, 10, 24), (cx - 1, cy - alt // 2, 3, alt))
        pygame.draw.line(surf, (14, 2, 6), (cx, cy - alt // 2), (cx, cy + alt // 2 - 1))
    for ux, uy in ULLS_PETITS:
        surf.set_at((hx + ux + round(mirada[0]), hy + uy + round(mirada[1] * 0.6)), (14, 2, 6))
    for ux, _ in MIRADA_ULL:                             # reflex
        surf.set_at((hx + ux - 6, hy + 8), (255, 252, 230))
        surf.set_at((hx + ux - 5, hy + 8), (255, 252, 230))


def banyes(f, trencada=False, dx=0, dy=0):
    """Corona de cinc banyes anellades que surten del crani, corbades enfora, amb la punta fosca."""
    hx, hy = CAP[0] + dx, CAP[1] + dy
    corbes = [((0, -40), (-5, -54), (5, -64), (1, -78), 7.4),
              ((-16, -36), (-26, -50), (-38, -54), (-38, -70), 6.6),
              ((16, -36), (26, -50), (38, -54), (38, -70), 6.6),
              ((-30, -22), (-46, -30), (-58, -34), (-62, -50), 6.2),
              ((30, -22), (46, -30), (58, -34), (62, -50), 6.2)]
    for k, (p0, p1, p2, p3, r0) in enumerate(corbes):
        n = 16
        pts = bezier(*[(hx + x, hy + y) for x, y in (p0, p1, p2, p3)], n)
        if trencada and k == 1:
            pts = pts[:8]
        radis = [max(0.8, r0 * (1 - i / n) ** 0.8) for i in range(len(pts))]
        punta = 11
        f.membre("banya", pts[:punta + 1], radis[:punta + 1], grup=f"banya{k}")
        if len(pts) > punta:
            f.membre("urpa", pts[punta:], radis[punta:], grup=f"banya{k}")
        for i in range(2, min(len(pts) - 2, punta), 2):  # anelles: solc fosc i vora clara
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            nx, ny = -(y1 - y0), x1 - x0
            nn = math.hypot(nx, ny) or 1
            nx, ny = nx / nn, ny / nn
            r = radis[i]
            f.marca_linia((x0 - nx * r, y0 - ny * r), (x0 + nx * r, y0 + ny * r), -1)
            f.marca_linia((x1 - nx * r, y1 - ny * r), (x1 + nx * r, y1 + ny * r), 1)


# ---------------------------------------------------------------------------------------------
# Cos
# ---------------------------------------------------------------------------------------------
ORGAN = (CX, 138)


def el·lipse_punts(cx, cy, rx, ry, osca=None, n=48):
    """Punts d'una el·lipse; osca = (angle0, angle1, fondària): hi treu un tros esmicolat."""
    pts = []
    rnd = random.Random(int(cx * 7 + cy))
    for i in range(n):
        a = math.tau * i / n
        k = 1.0
        if osca and osca[0] <= a <= osca[1]:
            mig = (a - osca[0]) / (osca[1] - osca[0])
            k = 1 - osca[2] * math.sin(mig * math.pi) * rnd.uniform(0.6, 1.2)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    return pts


VENES = {   # venes que surten de l'òrgan (per a la capa que brilla, de dins cap enfora)
    1: [[(CX - 6, 145), (CX - 9, 146), (CX - 16, 154), (CX - 22, 157), (CX - 32, 158)],
        [(CX + 6, 145), (CX + 9, 146), (CX + 16, 154), (CX + 22, 157), (CX + 32, 158)],
        [(CX - 1, 146), (CX, 149), (CX - 3, 156)], [(CX + 1, 146), (CX + 3, 156)],
        [(CX - 6, 131), (CX - 8, 124), (CX - 14, 120), (CX - 22, 119)],
        [(CX + 6, 131), (CX + 8, 124), (CX + 14, 120), (CX + 22, 119)]],
}
ESQUERDES_1 = [[(CX - 30, 126), (CX - 27, 132), (CX - 31, 137), (CX - 28, 144)],
               [(CX + 60, 101), (CX + 56, 108), (CX + 60, 114), (CX + 54, 121)],
               [(CX - 8, 157), (CX - 4, 161), (CX - 6, 165)],
               [(CX - 44, 110), (CX - 48, 117), (CX - 45, 124)]]
ESQUERDES_BRILLANTS = [[(CX + 12, 127), (CX + 18, 133), (CX + 16, 140), (CX + 24, 146)],
                       [(CX - 50, 103), (CX - 54, 111), (CX - 50, 119), (CX - 53, 125)],
                       [(CX + 4, 158), (CX + 10, 162), (CX + 8, 168)],
                       [(CX + 36, 128), (CX + 31, 134), (CX + 34, 140)]]
NUCLI_EXPOSAT = [(CX - 31, 128), (CX - 18, 121), (CX - 6, 125), (CX + 5, 128), (CX + 9, 140), (CX + 5, 152),
                 (CX - 8, 156), (CX - 22, 152), (CX - 31, 142)]


def cos(f, fase=1, esquerdes=0):
    """Coll alt i punxegut, espatlleres, pit amb l'òrgan de control, ventre segmentat i venes.
    fase 2: la closca s'ha trencat i el nucli queda a la vista. esquerdes: 0 o 1."""
    # coll de quitina amb punxes que emmarquen el cap
    f.poli("quitina_f", simetric([(CX - 44, 132), (CX - 54, 90), (CX - 40, 104), (CX - 42, 74), (CX - 30, 100),
                                  (CX - 24, 96), (CX - 14, 112), (CX, 114)]))
    # tors de pell
    f.poli("pell", simetric([(CX - 46, 122), (CX - 42, 146), (CX - 34, 166), (CX - 24, 180)]), grup="tors")
    if fase == 2:                                        # nucli a la vista sota la closca trencada
        f.poli("nucli", NUCLI_EXPOSAT, mode="brilla")
        for fil in ([(CX - 4, 132), (CX - 12, 128), (CX - 20, 126)], [(CX - 8, 140), (CX - 18, 141), (CX - 27, 138)],
                    [(CX - 5, 146), (CX - 12, 150), (CX - 19, 151)], [(CX - 9, 135), (CX - 16, 134)]):
            f.corba(fil, MAT["nucli"][1])                # membranes fosques dins del nucli
        for x, y in ((CX - 15, 131), (CX - 23, 133), (CX - 13, 145), (CX - 22, 146), (CX + 4, 134)):
            f.px(x, y, MAT["nucli"][4])
            f.px(x + 1, y, MAT["nucli"][3])
    # ventre: segments corbats de quitina
    for y0, y1, a0, a1 in ((154, 164, 31, 27), (163, 172, 27, 23), (171, 180, 23, 17)):
        mig = (y0 + y1) / 2
        f.poli("quitina_f", [(CX - a0, y0), (CX, y0 + 2), (CX + a0, y0), (CX + (a0 + a1) / 2 + 1, mig), (CX + a1, y1),
                             (CX, y1 + 2), (CX - a1, y1), (CX - (a0 + a1) / 2 - 1, mig)])
        f.marca_corba([(CX - a0 + 4, y0 + 2), (CX, y0 + 4), (CX + a0 - 4, y0 + 2)], 1)
    # pectorals de quitina, amb estries (a la fase 2 l'esquerre està esmicolat)
    for s in (-1, 1):
        pts = [(CX - 42, 126), (CX - 26, 121), (CX - 9, 126), (CX - 7, 136), (CX - 12, 150), (CX - 24, 156),
               (CX - 36, 152), (CX - 43, 140)]
        if fase == 2 and s < 0:
            pts = [(CX - 42, 126), (CX - 35, 122), (CX - 31, 128), (CX - 27, 126), (CX - 28, 134), (CX - 22, 138),
                   (CX - 26, 144), (CX - 19, 150), (CX - 24, 156), (CX - 36, 152), (CX - 43, 140)]
        f.poli("quitina", pts if s < 0 else mirall(pts, CX))
        f.marca_corba([(sx(s, 38), 132), (sx(s, 30 if fase == 2 and s < 0 else 26), 128), (sx(s, 12), 131)][:2 if fase == 2 and s < 0 else 3], 1)
        f.marca_corba([(sx(s, 39), 143), (sx(s, 30), 146)] if fase == 2 and s < 0 else
                      [(sx(s, 39), 143), (sx(s, 26), 147), (sx(s, 14), 143)], -1)
        f.marca_corba([(sx(s, 36), 148), (sx(s, 26), 152), (sx(s, 16 if not (fase == 2 and s < 0) else 22), 149)], -1)
    # òrgan de control encastat en una anella (a la fase 2, l'anella ha saltat i l'òrgan s'ha inflat)
    if fase == 1:
        f.cercle("quitina_f", ORGAN[0], ORGAN[1], 11)
        f.cercle("nucli", ORGAN[0], ORGAN[1], 7, mode="brilla")
    else:
        f.cercle("nucli", ORGAN[0], ORGAN[1], 9, mode="brilla")
    # espatlleres de làmines de quitina (com closques apilades) amb dues punxes
    for s in (-1, 1):
        trencada = fase == 2 and s > 0
        for x0, y0, x1, y1, mode in ((70, 118, 36, 148, "volum"), (75, 110, 32, 140, "volum"), (74, 99, 30, 129, "esfera")):
            a, b = sorted((sx(s, x0), sx(s, x1)))
            if trencada and y0 == 99:                    # la làmina de dalt ha perdut un tros
                f.poli("quitina", el·lipse_punts((a + b) / 2, (y0 + y1) / 2, (b - a) / 2, (y1 - y0) / 2,
                                                 osca=(4.3, 5.6, 0.55)), mode=mode)
            else:
                f.el·lipse("quitina", a, y0, b, y1, mode=mode)
        f.marca_corba([(sx(s, 68), 112), (sx(s, 56), 106), (sx(s, 44), 105)], 1)
        f.marca_corba([(sx(s, 62), 121), (sx(s, 52), 124), (sx(s, 40), 122)], -1)
        for k, (bx, by, tx, ty) in enumerate(((sx(s, 44), 103, sx(s, 51), 82), (sx(s, 58), 105, sx(s, 72), 88))):
            if trencada and k == 0:
                continue                                  # aquesta punxa ha saltat amb el tros
            if trencada and k == 1:                       # punxa partida
                tx, ty = (bx + tx) / 2 + 1, (by + ty) / 2
                f.poli("banya", [(bx - 5, by + 1), (bx + 5, by + 1), (tx + 3, ty), (tx - 2, ty + 2)], grup=f"punxa{bx}")
            else:
                f.poli("banya", [(bx - 5, by + 1), (bx + 5, by + 1), (tx, ty)], grup=f"punxa{bx}")
            f.marca_linia((bx - 3, by - 3), (bx + 3, by - 3), -1)
    # venes que surten de l'òrgan per la pell
    for vena in VENES[1]:
        f.corba(vena, VENA[0])
    # esquerdes
    if esquerdes or fase == 2:
        for e in ESQUERDES_1[:4 if esquerdes else 2]:
            f.corba(e, MAT["quitina"][0])
            f.corba([(x + 1, y) for x, y in e], MAT["quitina"][3])
    if fase == 2:
        for e in ESQUERDES_BRILLANTS[:4 if esquerdes else 2]:
            f.corba(e, VENA[1])
            f.corba(e[1:-1], VENA[2])


def capa_venes(fase, esquerdes, k=None, n=6):
    """Capa que brilla per damunt del cos: venes (i esquerdes de la fase 2) amb un pols que surt de
    l'òrgan. k=None: tot encès (crida mental)."""
    s = pygame.Surface((LLENC_W, LLENC_H), pygame.SRCALPHA)
    linies = list(VENES[1])
    if fase == 2:
        linies += ESQUERDES_BRILLANTS[:4 if esquerdes else 2]
    for vena in linies:
        dist = 0.0
        for a, b in zip(vena, vena[1:]):
            passos = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) or 1
            for i in range(passos + 1):
                x = round(a[0] + (b[0] - a[0]) * i / passos)
                y = round(a[1] + (b[1] - a[1]) * i / passos)
                d = dist + math.dist(a, (x, y))
                if k is None:
                    s.set_at((x, y), VENA[2] if int(d) % 5 else VENA[1])
                else:
                    fase_pols = (d / 3.0 - k) % n
                    if fase_pols < 1.2:
                        s.set_at((x, y), VENA[2])
                    elif fase_pols < 2.4:
                        s.set_at((x, y), VENA[1])
            dist += math.dist(a, b)
    return s


def capa_cervell():
    """Els solcs del cervell s'encenen (crida mental)."""
    s = pygame.Surface((LLENC_W, LLENC_H), pygame.SRCALPHA)
    hx, hy = CAP
    for punts in SOLCS:
        for a, b in zip(punts, punts[1:]):
            pygame.draw.line(s, VENA[1], (hx + a[0], hy + a[1]), (hx + b[0], hy + b[1]))
        for x, y in punts[1:-1]:
            s.set_at((hx + x, hy + y), VENA[2])
    return s


def tros(k):
    """Trossos de closca que salten quan es trenca (fase 2)."""
    f = Figura(24, 24, MAT, BRILLANTS)
    rnd = random.Random(k * 13 + 5)
    pts = []
    n = 6
    for i in range(n):
        a = math.tau * i / n + rnd.uniform(-0.3, 0.3)
        r = rnd.uniform(5, 10)
        pts.append((12 + math.cos(a) * r, 12 + math.sin(a) * r * 0.8))
    f.poli("quitina", pts)
    if k % 2:
        f.poli("banya", [(10, 11), (16, 10), (13, 3)])
    return f.superficie()


# ---------------------------------------------------------------------------------------------
# Braços
# ---------------------------------------------------------------------------------------------
POSES_BRAÇ = {
    # espatlla, colze, canell, obertura de les urpes, angle de la mà (costat esquerre)
    "repos": ((54, 124), (76, 152), (72, 180), 0.22, 1.85),
    "mig": ((54, 124), (84, 136), (90, 112), 0.5, -1.2),
    "alçat": ((54, 122), (84, 108), (94, 78), 0.75, -1.55),
    "cop": ((54, 122), (66, 92), (58, 64), 0.3, -1.75),
    "terra": ((54, 124), (84, 150), (98, 176), 0.6, 1.3),
}


def braç(f, s, pose="repos"):
    (ex, ey), (cx_, cy_), (mx, my), obre, angle_ma = POSES_BRAÇ[pose]
    E, C, M = (sx(s, ex), ey), (sx(s, cx_), cy_), (sx(s, mx), my)
    g = f"braç{s}"
    f.membre("pell", [E, C], [11, 9], grup=g)
    f.membre("pell", [C, M], [9, 7.5], grup=g)
    # braçal de quitina a l'avantbraç
    a0 = (C[0] + (M[0] - C[0]) * 0.32, C[1] + (M[1] - C[1]) * 0.32)
    a1 = (C[0] + (M[0] - C[0]) * 0.86, C[1] + (M[1] - C[1]) * 0.86)
    f.membre("quitina", [a0, a1], [10, 8.6])
    dx, dy = a1[0] - a0[0], a1[1] - a0[1]
    n = math.hypot(dx, dy) or 1
    ux, uy = dx / n, dy / n
    f.marca_linia((a0[0] + ux * 6 - uy * 8, a0[1] + uy * 6 + ux * 8), (a0[0] + ux * 6 + uy * 8, a0[1] + uy * 6 - ux * 8), -1)
    # punxa del colze
    dx, dy = C[0] - E[0], C[1] - E[1]
    n = math.hypot(dx, dy) or 1
    ux, uy = dx / n, dy / n
    px, py = -uy * s, ux * s
    if px * s < 0:
        px, py = -px, -py
    f.poli("banya", [(C[0] - ux * 5, C[1] - uy * 5), (C[0] + ux * 6, C[1] + uy * 6),
                     (C[0] + px * 15 + ux * 4, C[1] + py * 15 + uy * 4)])
    # mà i tres urpes llargues
    a = angle_ma if s < 0 else math.pi - angle_ma
    mx2, my2 = M[0] + math.cos(a) * 6, M[1] + math.sin(a) * 6
    f.el·lipse("pell", mx2 - 8, my2 - 7, mx2 + 8, my2 + 7, grup=g)
    for k in (-1, 0, 1):
        b = a + k * obre
        p0 = (mx2 + math.cos(b) * 5, my2 + math.sin(b) * 5)
        p1 = (p0[0] + math.cos(b) * 9, p0[1] + math.sin(b) * 9)
        p2 = (p1[0] + math.cos(b + s * 0.8) * 8, p1[1] + math.sin(b + s * 0.8) * 8)
        f.membre("banya", [p0, p1], [3.4, 2.5], grup=f"urpa{s}{k}")
        f.membre("urpa", [p1, p2], [2.5, 0.7], grup=f"urpa{s}{k}")


# ---------------------------------------------------------------------------------------------
# Tentacles
# ---------------------------------------------------------------------------------------------
TENTACLES = [  # arrel x, arrel y, angle, llargada, radi, desfasament
    (-24, 172, 2.2, 74, 9.4, 0.0), (24, 172, 0.94, 74, 9.4, 2.1),
    (-14, 176, 1.9, 80, 10.0, 4.2), (14, 176, 1.24, 80, 10.0, 1.0),
    (-5, 178, 1.68, 70, 9.6, 3.1), (5, 178, 1.46, 70, 9.6, 5.3),
]


def punts_tentacle(k, fase=0.0, pose="ones"):
    ax, ay, angle, llarg, r0, desf = TENTACLES[k]
    s = -1 if ax < 0 else 1
    n = 20
    x, y = CX + ax, ay
    a = angle
    if pose == "estesos":                            # cop de terra: oberts com una estrella
        a = angle + (angle - math.pi / 2) * 1.3
    elif pose == "flonjos":                          # mort: pengen rectes
        a = math.pi / 2 + (angle - math.pi / 2) * 0.3
    elif pose == "recollits":                        # abans del cop: s'arrauleixen cap amunt
        a = angle + (angle - math.pi / 2) * 2.2
        llarg *= 0.82
    pts = [(x, y)]
    for i in range(1, n + 1):
        t = i / n
        if pose == "ones":
            corba = 0.36 * math.sin(fase + desf - t * 3.6) * (0.35 + t) + s * 0.04 * t
        elif pose == "estesos":
            corba = -s * 0.12 * (1 + t) + 0.05 * math.sin(fase + desf - t * 4)
        elif pose == "recollits":
            corba = -s * 0.5 * t
        else:
            corba = 0.04 * math.sin(fase + desf - t * 3)
        if i > n * 0.68 and pose not in ("flonjos", "recollits"):     # la punta s'enrotlla cap a dins
            corba += -s * 0.36 * (t - 0.68) / 0.32
        a += corba * 6.6 / n
        x += math.cos(a) * llarg / n
        y += math.sin(a) * llarg / n
        pts.append((x, y))
    radis = [max(0.9, r0 * (1 - (i / n) ** 1.25) + 0.4) for i in range(n + 1)]
    return pts, radis, s


def tentacles(f, fase=0.0, pose="ones"):
    """Sis tentacles que pengen del ventre. fase: 0..2π del cicle d'ondulació."""
    for k in range(len(TENTACLES)):
        pts, radis, s = punts_tentacle(k, fase, pose)
        g = f"tentacle{k}"
        f.membre("pell_f", pts, radis, grup=g)
        n = len(pts) - 1
        for i in range(int(n * 0.35), n - 2, 2):        # ventoses a la cara interior
            (x0, y0), (x1, y1) = pts[i - 1], pts[i + 1]
            nx, ny = -(y1 - y0), x1 - x0
            nn = math.hypot(nx, ny) or 1
            nx, ny = nx / nn, ny / nn
            if nx * -s < 0:
                nx, ny = -nx, -ny
            r = radis[i]
            x, y = pts[i][0] + nx * (r - 2), pts[i][1] + ny * (r - 2)
            f.px(x, y, MAT["ventre"][2] if r > 3 else MAT["ventre"][1])
            if r > 4:
                f.px(x + 1, y, MAT["ventre"][1])
        for i in range(2, n - 4, 3):                    # plecs de la pell
            (x0, y0), (x1, y1) = pts[i - 1], pts[i + 1]
            nx, ny = -(y1 - y0), x1 - x0
            nn = math.hypot(nx, ny) or 1
            nx, ny = nx / nn, ny / nn
            r = radis[i] * 0.7
            f.marca_linia((pts[i][0] - nx * r, pts[i][1] - ny * r), (pts[i][0] + nx * r * 0.2, pts[i][1] + ny * r * 0.2), -1)


# ---------------------------------------------------------------------------------------------
# Exportació
# ---------------------------------------------------------------------------------------------
N_ONES = 16          # fotogrames del cicle dels tentacles
N_VENES = 6          # fotogrames del pols de les venes
POSES = list(POSES_BRAÇ)
BOQUES = ("tancada", "mitja", "oberta")
PARPELLES = ("oberts", "mig", "tancats")


def renderitzar(pintar):
    f = figura()
    pintar(f)
    return f.superficie()


def totes_les_capes():
    """{nom: superfície del llenç sencer} de totes les peces del Comandant."""
    capes = {}
    for k in range(N_ONES):
        capes[f"tent_ones_{k}"] = renderitzar(lambda f: tentacles(f, math.tau * k / N_ONES, "ones"))
    for pose in ("recollits", "estesos", "flonjos"):
        capes[f"tent_{pose}"] = renderitzar(lambda f: tentacles(f, 0.8, pose))
    for pose in POSES:
        for s in (-1, 1):
            capes[f"braç_{pose}_{s}"] = renderitzar(lambda f: braç(f, s, pose))
    for fase in (1, 2):
        for esq in (0, 1):
            capes[f"cos_{fase}_{esq}"] = renderitzar(lambda f: cos(f, fase, esq))
            for k in range(N_VENES):
                capes[f"venes_{fase}_{esq}_{k}"] = capa_venes(fase, esq, k, N_VENES)
            capes[f"venes_{fase}_{esq}_tot"] = capa_venes(fase, esq)
    capes["banyes"] = renderitzar(lambda f: banyes(f))
    capes["banyes_trencades"] = renderitzar(lambda f: banyes(f, trencada=True))
    for boca in BOQUES:
        for parp in PARPELLES:
            capes[f"cap_{boca}_{parp}"] = renderitzar(lambda f: cap(f, boca, parp))
    capes["cap_mort"] = renderitzar(lambda f: cap(f, "oberta", "mig", mort=True))
    capes["cervell"] = capa_cervell()
    return capes


def punt_urpa(pose, s):
    (ex, ey), (cx_, cy_), (mx, my), obre, angle_ma = POSES_BRAÇ[pose]
    a = angle_ma if s < 0 else math.pi - angle_ma
    return round(sx(s, mx) + math.cos(a) * 20), round(my + math.sin(a) * 20)


def generar():
    pygame.display.set_mode((1, 1))
    capes = totes_les_capes()
    retalls = {}
    desp = {}
    for nom, sup in capes.items():
        retalls[nom], desp[nom] = retallar(sup)
    for k in range(4):
        retalls[f"tros_{k}"], desp[f"tros_{k}"] = retallar(tros(k))
    atles, rects = empaquetar(retalls, ample=1024)
    info = {
        "llenç": [LLENC_W, LLENC_H],
        "imatges": {n: rects[n] + list(desp[n]) for n in sorted(rects)},
        "n_ones": N_ONES, "n_venes": N_VENES,
        "organ": list(ORGAN),
        "cap": list(CAP),
        "ulls": [[CAP[0] + x, CAP[1] + y] for x, y in MIRADA_ULL],
        "ulls_petits": [[CAP[0] + x, CAP[1] + y] for x, y in ULLS_PETITS],
        "boca": [CAP[0], CAP[1] + 31],
        "urpes": {pose: {str(s): list(punt_urpa(pose, s)) for s in (-1, 1)} for pose in POSES},
        "cos": [CX - 70, 30, CX + 70, 184],         # caixa del cap i el tors (sense banyes ni tentacles)
    }
    pygame.image.save(atles, os.path.join(SORTIDA, "comandant.png"))
    with open(os.path.join(SORTIDA, "comandant.json"), "w") as fit:
        json.dump(info, fit, separators=(",", ":"))
    print("comandant.png", atles.get_size(), len(rects), "imatges")
    return atles, info


# ---------------------------------------------------------------------------------------------
# Composició (la mateixa que fa el joc a cada fotograma)
# ---------------------------------------------------------------------------------------------
class Peces:
    def __init__(self, atles, info):
        self.info = info
        self.img = {}
        for nom, (x, y, w, h, ox, oy) in info["imatges"].items():
            self.img[nom] = (atles.subsurface((x, y, w, h)), (ox, oy))

    def posar(self, surf, nom, dx=0, dy=0):
        im, (ox, oy) = self.img[nom]
        surf.blit(im, (ox + dx, oy + dy))


def compondre(peces, e):
    """e: diccionari d'estat (vegeu estat_repos)."""
    W, H = peces.info["llenç"]
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    t = e["t"]
    respira = round(math.sin(t * math.tau / 120))
    cap_dy = round(math.sin((t - 12) * math.tau / 120) * 1.5) + e.get("cap_dy", 0)
    cap_dx = round(e["mirada"][0] * 2) + e.get("cap_dx", 0)
    tent = e["tentacles"]
    peces.posar(s, f"tent_ones_{(t // 5) % N_ONES}" if tent == "ones" else f"tent_{tent}", e.get("tent_dx", 0), 0)
    for k, sgn in ((0, -1), (1, 1)):
        peces.posar(s, f"braç_{e['braços'][k]}_{sgn}", 0, respira)
    fase, esq = e["cos"]
    peces.posar(s, f"cos_{fase}_{esq}", 0, respira)
    if e.get("venes") == "tot":
        peces.posar(s, f"venes_{fase}_{esq}_tot", 0, respira)
    else:
        peces.posar(s, f"venes_{fase}_{esq}_{(t // 6) % N_VENES}", 0, respira)
    peces.posar(s, "banyes_trencades" if e.get("banya_trencada") else "banyes", cap_dx, cap_dy)
    if e.get("mort"):
        peces.posar(s, "cap_mort", cap_dx, cap_dy)
    else:
        peces.posar(s, f"cap_{e['boca']}_{e['parpelles']}", cap_dx, cap_dy)
        if e["parpelles"] != "tancats":
            pupil·les(s, e["mirada"], e.get("ira", False), cap_dx, cap_dy)
        if e.get("cervell"):
            im, (ox, oy) = peces.img["cervell"]
            im = im.copy()
            im.set_alpha(e["cervell"])
            s.blit(im, (ox + cap_dx, oy + cap_dy))
    return s


def estat_repos(t, **kw):
    e = {"t": t, "tentacles": "ones", "braços": ("repos", "repos"), "cos": (1, 0), "boca": "tancada",
         "parpelles": "oberts", "mirada": (0.0, 0.0)}
    e.update(kw)
    return e


if __name__ == "__main__":
    generar()
