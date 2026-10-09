"""Genera els cinc caps de sector en alta definició a assets/img/caps_hd.png + caps_hd.json.

    python3 tools/generar_caps.py [vista.png]

0 General Xylothian: platet-tanc blindat amb canons laterals i una escotilla que llança drons.
1 Mestre de la Selva: nau orgànica embolicada de lianes, amb un ull i beines d'espores.
2 Comandant d'Elit: caça vermell amb ales de fulla i un sensor que apunta.
3 Capità orbital: canonera d'acer amb una torreta que gira (es dibuixa a part i el joc la fa girar).
4 Guardià del Rusc: insecte gegant amb closca, ulls compostos, ales que baten i fibló.
Tots es dibuixen de cara, centrats al llenç (el joc els inclina segons la velocitat).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame  # noqa: E402
from pintor import Figura, bezier, comprovar_paleta, empaquetar, mirall, retallar  # noqa: E402
from generar_enemics import MAT as MAT_ENEMICS  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SORTIDA = os.path.join(AQUI, "..", "assets", "img")

MAT = dict(MAT_ENEMICS)
MAT.update({
    "oliva": [(22, 30, 16), (60, 76, 40), (92, 112, 60), (128, 150, 86), (180, 200, 130)],
    "oliva_f": [(16, 22, 12), (44, 56, 30), (66, 82, 44), (92, 112, 62), (134, 154, 98)],
    "escorça": [(34, 22, 14), (82, 54, 32), (118, 80, 48), (154, 110, 70), (196, 154, 108)],
    "fulla": [(10, 36, 18), (30, 90, 40), (52, 136, 56), (92, 180, 80), (150, 220, 120)],
    "pol·len": [(70, 70, 10), (170, 180, 30), (220, 236, 60), (244, 255, 130), (252, 255, 214)],
    "flor": [(80, 14, 54), (176, 46, 118), (228, 92, 168), (250, 150, 206), (255, 214, 238)],
    "acer": [(20, 28, 42), (52, 72, 104), (82, 108, 148), (124, 152, 192), (186, 208, 236)],
    "groc": [(70, 50, 6), (186, 140, 20), (236, 196, 40), (255, 228, 100), (255, 246, 190)],
    "ala": [(70, 64, 96), (150, 146, 190), (190, 188, 226), (220, 220, 246), (246, 246, 255)],
    "ull_v": [(70, 6, 10), (170, 20, 30), (230, 50, 50), (255, 120, 100), (255, 210, 190)],
})
BRILLANTS = ("quitina", "quitina_f", "negre", "metall", "ovni", "vidre", "banya", "bronze", "vermell", "taronja",
             "oliva", "acer", "groc", "ull_v")
comprovar_paleta(MAT)


def figura(w, h):
    return Figura(w, h, MAT, BRILLANTS)


def simetric(punts, cx):
    return punts + mirall(punts[::-1], cx)


# ---------------------------------------------------------------------------------------------
# 0 · General Xylothian
# ---------------------------------------------------------------------------------------------
def general(llum=0, escotilla=0):
    """escotilla: 0 tancada, 1 mig oberta, 2 oberta (surt un dron)."""
    W, H, cx = 160, 124, 80
    f = figura(W, H)
    # canons laterals (darrere del casc)
    for s in (-1, 1):
        x = cx + s * 60
        f.membre("negre", [(x, 72), (x + s * 8, 94)], [4.2, 3.6], grup=f"canó{s}")
        f.el·lipse("brasa", x + s * 8 - 3, 92, x + s * 8 + 3, 98, "brilla")
        f.el·lipse("metall", x - 12, 58, x + 12, 80, "esfera")
        f.marca_linia((x - 9, 69), (x + 9, 69), -1)
    # anella de llums de sota
    f.el·lipse("ovni_f", 26, 72, 134, 94)
    for k in range(7):
        x = 38 + k * 14
        enc = (k + llum) % 3 == 0
        f.el·lipse("groc" if enc else "negre", x - 2.5, 84, x + 2.5, 88, "brilla" if enc else "pla")
    # casc blindat
    f.el·lipse("oliva", 8, 50, 152, 86, "esfera")
    for k in range(-3, 4):                                   # plaques i reblons
        x = cx + k * 20
        f.marca_linia((x, 56), (x + k * 2, 82), -1)
        f.marca_linia((x + 1, 56), (x + k * 2 + 1, 82), 1)
        f.px(x + 6, 76, MAT["oliva"][4])
    f.marca_linia((14, 68), (146, 68), -1)
    f.marca_linia((14, 67), (146, 67), 1)
    f.poli("groc", [(cx - 10, 72), (cx, 78), (cx + 10, 72), (cx + 10, 75), (cx, 81), (cx - 10, 75)], "pla")   # galó
    # coberta i torreta
    f.el·lipse("oliva_f", 32, 36, 128, 62, "esfera")
    f.el·lipse("metall", 50, 16, 110, 52, "esfera")
    f.poli("visor", [(58, 36), (102, 36), (100, 42), (60, 42)], "brilla")
    for k in range(5):
        f.px(62 + k * 8, 38, MAT["visor"][4])
    # antena amb llum vermella
    f.membre("negre", [(54, 26), (44, 6)], [1.0, 0.7], "pla")
    f.cercle("brasa" if llum % 2 == 0 else "vermell", 44, 6, 2.2, "brilla")
    # escotilla
    if escotilla == 0:
        f.poli("oliva", [(68, 15), (92, 15), (94, 22), (66, 22)])
        f.marca_linia((70, 18), (90, 18), -1)
    else:
        f.el·lipse("negre", 66, 14, 94, 24, "pla")
        if escotilla == 2:
            f.el·lipse("ovni", 72, 10, 88, 20, "esfera")         # el dron que surt
            f.el·lipse("energia", 77, 13, 83, 17, "brilla")
        alt = 10 if escotilla == 1 else 16
        f.poli("oliva", [(66, 15), (94, 15), (92, 15 - alt), (68, 15 - alt)])   # tapa alçada
        f.marca_linia((70, 15 - alt // 2), (90, 15 - alt // 2), -1)
    s = f.superficie()
    return s


# ---------------------------------------------------------------------------------------------
# 1 · Mestre de la Selva
# ---------------------------------------------------------------------------------------------
BEINES = [(54, 110), (80, 118), (106, 110)]


def mestre(pols=0, plenes=False):
    W, H, cx = 160, 136, 80
    f = figura(W, H)
    # arrels i tiges de les beines (darrere)
    for k, (bx, by) in enumerate(BEINES):
        f.membre("fulla", bezier((bx + (cx - bx) * 0.4, 86), (bx, 92), (bx + 4, 100), (bx, by - 6), 6),
                 [2.2, 2.0, 1.8, 1.6, 1.4, 1.2, 1.0], grup=f"tija{k}")
    for x0, dx in ((40, -10), (62, -4), (98, 4), (120, 10)):
        f.membre("escorça", bezier((x0, 84), (x0 + dx, 96), (x0 + dx * 2, 104), (x0 + dx * 2.5, 118), 6),
                 [2.6, 2.3, 2.0, 1.6, 1.2, 0.9, 0.6])
    # pètals de dalt
    for k in range(5):
        a = math.pi + k * math.pi / 4
        px, py = cx + math.cos(a) * 22, 30 + math.sin(a) * 18
        f.poli("flor", [(cx + math.cos(a - 0.35) * 10, 32 + math.sin(a - 0.35) * 8), (px, py - 4),
                        (cx + math.cos(a + 0.35) * 10, 32 + math.sin(a + 0.35) * 8)], grup="flor")
    # cos d'escorça
    f.el·lipse("escorça", 28, 26, 132, 98, "esfera")
    for k in range(-4, 5):                                    # solcs de l'escorça
        x = cx + k * 11
        f.marca_corba([(x, 32 + abs(k) * 3), (x + k, 60), (x - k * 0.5, 92 - abs(k) * 3)], -1)
    # lianes amb fulles
    for (x0, y0), (x1, y1) in (((30, 50), (128, 86)), ((34, 84), (122, 40)), ((60, 28), (100, 98))):
        pts = bezier((x0, y0), ((x0 + x1) / 2, y0 - 8), ((x0 + x1) / 2, y1 + 8), (x1, y1), 10)
        f.membre("fulla", pts, 2.4, grup="lianes")
        for i in (2, 5, 8):
            lx, ly = pts[i]
            f.poli("fulla", [(lx, ly), (lx + 7, ly - 4), (lx + 4, ly + 2)])
    # ull central
    f.el·lipse("escorça", 60, 44, 100, 76, "fosc")
    f.el·lipse("pol·len", 64, 48, 96, 72, "vidre")
    f.el·lipse("negre", 77, 50, 83, 70, "pla")
    f.px(70, 52, MAT["pol·len"][4])
    f.px(71, 52, MAT["pol·len"][4])
    # centre de la flor
    f.el·lipse("pol·len", cx - 6, 22, cx + 6, 32, "brilla")
    # beines d'espores
    r = 7 + (2 if plenes else pols)
    for bx, by in BEINES:
        f.el·lipse("pol·len", bx - r * 0.8, by - r, bx + r * 0.8, by + r, "brilla")
        for k in (-1, 1):
            f.linia((bx + k * r * 0.4, by - r + 2), (bx + k * r * 0.4, by + r - 2), MAT["pol·len"][1])
    return f.superficie()


# ---------------------------------------------------------------------------------------------
# 2 · Comandant d'Elit
# ---------------------------------------------------------------------------------------------
def elit(flama=0, apunta=False):
    W, H, cx = 172, 112, 86
    f = figura(W, H)
    for s in (-1, 1):                                          # motors (darrere de les ales)
        x = cx + s * 22
        f.el·lipse("negre", x - 7, 70, x + 7, 92)
        f.el·lipse("brasa", x - 4, 86 + flama, x + 4, 96 + flama * 2, "brilla")
    for s in (-1, 1):                                          # ales de fulla
        ala = [(cx + s * 14, 46), (cx + s * 82, 70), (cx + s * 84, 78), (cx + s * 70, 80), (cx + s * 16, 68)]
        f.poli("vermell", ala)
        f.poli("bronze", [(cx + s * 74, 68), (cx + s * 86, 72), (cx + s * 84, 80), (cx + s * 70, 80)])
        for k in range(3):
            x = cx + s * (30 + k * 14)
            f.linia((x, 54 + k * 5), (x + s * 6, 70 + k * 2), MAT["negre"][1])
        f.marca_linia((cx + s * 18, 50), (cx + s * 78, 70), 1)
    # fuselatge
    f.el·lipse("vermell", 62, 18, 110, 96, "esfera")
    f.poli("negre", [(cx - 10, 60), (cx + 10, 60), (cx + 6, 94), (cx - 6, 94)])
    for k in range(3):
        f.marca_linia((cx - 8 + k, 66 + k * 9), (cx + 8 - k, 66 + k * 9), 1)
    # cabina amb el pilot
    f.el·lipse("vidre", 70, 22, 102, 50, "esfera")
    f.el·lipse("pell", 76, 28, 96, 48, "esfera")
    f.poli("vermell", [(74, 32), (86, 22), (98, 32), (96, 36), (76, 36)])         # casc del pilot
    for x0 in (79, 87):
        f.el·lipse("ull_n", x0, 37, x0 + 5, 42, "pla")
    for x, y in ((73, 30), (74, 28), (75, 27)):
        f.px(x, y, MAT["vidre"][4])
    # emblema i sensor
    f.poli("bronze", [(cx - 7, 54), (cx, 50), (cx + 7, 54), (cx, 60)], "pla")
    f.el·lipse("ull_v" if apunta else "negre", cx - 3, 12, cx + 3, 18, "brilla" if apunta else "pla")
    return f.superficie()


# ---------------------------------------------------------------------------------------------
# 3 · Capità orbital
# ---------------------------------------------------------------------------------------------
def capita(llum=0):
    W, H, cx = 168, 116, 84
    f = figura(W, H)
    for s in (-1, 1):                                          # propulsors laterals
        x = cx + s * 70
        f.poli("acer", [(x - 9, 40), (x + 9, 40), (x + 7, 78), (x - 7, 78)])
        f.el·lipse("energia", x - 5, 76, x + 5, 84, "brilla")
        f.marca_linia((x - 7, 50), (x + 7, 50), -1)
    casc = [(22, 44), (40, 28), (128, 28), (146, 44), (146, 74), (128, 88), (40, 88), (22, 74)]
    f.poli("acer", casc)
    for x in range(30, 140, 16):                               # panells
        f.marca_linia((x, 32), (x, 84), -1)
        f.marca_linia((x + 1, 32), (x + 1, 84), 1)
    for k in range(6):                                         # franges d'avís
        x = 26 + k * 4
        f.linia((x, 66), (x + 4, 58), MAT["groc"][2])
        f.linia((W - x, 66), (W - x - 4, 58), MAT["groc"][2])
    f.poli("acer", [(56, 28), (64, 12), (104, 12), (112, 28)])  # pont
    f.poli("energia", [(66, 17), (102, 17), (104, 22), (64, 22)], "brilla")
    for x in (72, 84, 96):
        f.linia((x, 17), (x, 22), MAT["acer"][1])
    for x in (60, 108):                                        # antenes
        f.membre("negre", [(x, 14), (x + (x - cx) * 0.2, 0)], [0.9, 0.6], "pla")
    f.cercle("vermell" if llum else "brasa", 52, 2, 1.8, "brilla")
    f.el·lipse("negre", cx - 18, 76, cx + 18, 96)              # anell de la torreta
    for k in range(5):
        x = 42 + k * 21
        f.el·lipse("energia" if (k + llum) % 2 else "negre", x - 2, 80, x + 2, 84, "brilla")
    return f.superficie()


def torreta():
    """Torreta del capità, amb el doble canó mirant a la dreta (el joc la gira)."""
    W, H = 56, 36
    f = figura(W, H)
    for dy in (-5, 5):
        f.membre("negre", [(24, 18 + dy), (52, 18 + dy)], [2.6, 2.2])
        f.el·lipse("energia", 50, 15 + dy, 55, 21 + dy, "brilla")
    f.el·lipse("acer", 8, 4, 36, 32, "esfera")
    f.el·lipse("negre", 16, 12, 28, 24)
    f.el·lipse("ull_v", 19, 15, 25, 21, "brilla")
    return f.superficie()


# ---------------------------------------------------------------------------------------------
# 4 · Guardià del Rusc
# ---------------------------------------------------------------------------------------------
def guardia(ala=0):
    """ala: 0 amunt, 1 al mig, 2 avall (batec de les ales)."""
    W, H, cx = 180, 140, 90
    f = figura(W, H)
    angles = (-0.55, -0.1, 0.35)[ala]
    for s in (-1, 1):                                          # ales (darrere de tot)
        for k, (llarg, ample, da) in enumerate(((78, 22, 0.0), (60, 16, 0.42))):
            a = angles + da
            base = (cx + s * 16, 44 + k * 8)
            punta = (base[0] + s * math.cos(a) * llarg, base[1] + math.sin(a) * llarg)
            n = (-math.sin(a) * ample / 2, math.cos(a) * ample / 2)
            f.poli("ala", [base, (base[0] + s * math.cos(a) * llarg * 0.45 - n[0] * s, base[1] + math.sin(a) * llarg * 0.45 - n[1]),
                           punta, (base[0] + s * math.cos(a) * llarg * 0.55 + n[0] * s, base[1] + math.sin(a) * llarg * 0.55 + n[1])],
                   "pla", grup=f"ala{s}{k}")
            f.linia(base, punta, MAT["ala"][0])                # nervi
            mx, my = (base[0] + punta[0]) / 2, (base[1] + punta[1]) / 2
            f.linia((mx, my), (mx + s * 8, my + 6), MAT["ala"][1])
    for s in (-1, 1):                                          # potes penjant
        for k in range(3):
            x0 = cx + s * (10 + k * 6)
            f.membre("negre", [(x0, 70), (x0 + s * 14, 82 + k * 4), (x0 + s * 10, 100 + k * 4)], [2.0, 1.6, 0.8])
    # abdomen amb anelles i fibló
    f.el·lipse("quitina_f", cx - 22, 66, cx + 22, 118, "esfera", grup="abdomen")
    for k in range(4):
        y = 76 + k * 10
        f.el·lipse("groc", cx - 20 + k * 2, y, cx + 20 - k * 2, y + 4, grup="abdomen")
    f.poli("banya", [(cx - 4, 116), (cx + 4, 116), (cx, 134)])
    # tòrax de closca
    f.el·lipse("quitina", cx - 32, 34, cx + 32, 80, "esfera")
    f.marca_corba([(cx, 38), (cx, 76)], -1)
    f.marca_corba([(cx + 1, 38), (cx + 1, 76)], 1)
    f.poli("groc", [(cx - 6, 46), (cx + 6, 46), (cx, 56)], "pla")
    # cap amb ulls compostos, mandíbules i antenes
    f.el·lipse("quitina_f", cx - 22, 8, cx + 22, 42, "esfera")
    for s in (-1, 1):
        ex = cx + s * 12
        f.el·lipse("ull_v", ex - 9, 12, ex + 9, 32, "esfera")
        for y in range(15, 31, 3):                             # facetes
            f.marca_linia((ex - 7, y), (ex + 7, y), -1)
        f.membre("banya", [(cx + s * 8, 38), (cx + s * 12, 46), (cx + s * 5, 52)], [2.4, 2.0, 0.8])
        f.membre("negre", [(cx + s * 6, 10), (cx + s * 14, -2), (cx + s * 26, -4)], [1.2, 0.9, 0.6], "pla")
    return f.superficie()


# ---------------------------------------------------------------------------------------------
# Exportació i previsualització
# ---------------------------------------------------------------------------------------------
def tots():
    """{nivell: {"anims": {anim: [superfícies]}}}."""
    return {
        0: {"repos": [general(0), general(1)], "escotilla": [general(0, 1), general(1, 2)]},
        1: {"repos": [mestre(0), mestre(1)], "plenes": [mestre(0, True)]},
        2: {"repos": [elit(0), elit(1)], "apunta": [elit(0, True), elit(1, True)]},
        3: {"repos": [capita(0), capita(1)], "torreta": [torreta()]},
        4: {"repos": [guardia(0), guardia(1), guardia(2), guardia(1)]},
    }


def generar():
    pygame.display.set_mode((1, 1))
    imatges, info = {}, {}
    for n, anims in tots().items():
        e = {"anims": {}, "mides": {}}
        for anim, frames in anims.items():
            noms = []
            for k, s in enumerate(frames):
                nom = f"cap{n}_{anim}_{k}"
                imatges[nom] = s                                  # sencer: el joc el dibuixa centrat
                e["mides"][nom] = list(s.get_size())
                noms.append(nom)
            e["anims"][anim] = noms
        info[str(n)] = e
    atles, rects = empaquetar(imatges, ample=1024)
    for e in info.values():
        e["imatges"] = {nom: rects[nom] for nom in e.pop("mides")}
    pygame.image.save(atles, os.path.join(SORTIDA, "caps_hd.png"))
    with open(os.path.join(SORTIDA, "caps_hd.json"), "w") as fit:
        json.dump(info, fit, separators=(",", ":"))
    print("caps_hd.png", atles.get_size(), len(rects), "imatges")


def vista(sortida, k=3):
    pygame.display.set_mode((1, 1))
    files = [[s for frames in anims.values() for s in frames] for anims in tots().values()]
    W = max(sum(s.get_width() * k + 8 for s in fila) for fila in files) + 8
    H = sum(max(s.get_height() for s in fila) * k + 8 for fila in files) + 8
    out = pygame.Surface((W, H))
    out.fill((40, 42, 60))
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
