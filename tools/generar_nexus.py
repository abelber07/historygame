"""Genera els sprites del protagonista (Nexus) en alta definició.

    python tools/generar_nexus.py

El soldat es pinta per peces (casc, tors, braços, cames, botes, arma) a resolució 1:1 i després
s'ombreja i es perfila automàticament: contorn fosc, llum de dalt a l'esquerra i ombres a baix.
Les poses són articulacions (espatlla, colze, mà, maluc, genoll, turmell) i les cames es resolen amb
cinemàtica inversa, de manera que canviar d'arma o de fotograma és moure punts, no redibuixar.

Surt a assets/img:
  nexus_<arma>_<blindatge>.png  tira de fotogrames: quiet x2, corre x6, salt, caiguda
  nexus_armes.png               cada arma sola (per a la botiga)
  nexus.json                    mida dels fotogrames, ancoratge dels peus, boca de cada arma i la paleta
                                de cada material (el joc la fa servir per pintar uniformes i aspectes)
"""
import json
import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

pygame.init()

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIDA = os.path.join(ARREL, "assets", "img")
S = 1.15                                   # escala del dibuix (el soldat fa uns 66 píxels d'alt)

# Tons per material: contorn, ombra, base, llum, brillantor. Tots els colors han de ser diferents
# entre materials: el joc recolora per color exacte (uniforme, aspecte d'arma, camuflatge).
MAT = {
    "casc":    [(24, 28, 10), (74, 72, 22), (106, 102, 30), (138, 134, 44), (176, 172, 72)],
    "unif":    [(22, 28, 12), (64, 74, 26), (92, 106, 36), (120, 136, 50), (150, 166, 72)],
    "unif_f":  [(18, 22, 10), (50, 58, 20), (70, 82, 28), (93, 107, 37), (112, 126, 48)],
    "pant":    [(20, 30, 14), (60, 78, 30), (86, 110, 40), (114, 140, 56), (142, 170, 78)],
    "pant_f":  [(16, 24, 11), (46, 60, 24), (66, 86, 32), (87, 111, 41), (106, 132, 52)],
    "armilla": [(18, 20, 9), (44, 48, 18), (62, 66, 26), (82, 86, 36), (104, 108, 50)],
    "motx":    [(20, 22, 11), (56, 54, 22), (80, 76, 32), (104, 100, 44), (128, 124, 60)],
    "pell":    [(64, 34, 26), (176, 116, 88), (216, 156, 116), (236, 184, 142), (250, 210, 172)],
    "visor":   [(10, 28, 48), (24, 112, 172), (64, 196, 244), (140, 232, 255), (244, 252, 255)],
    "bota":    [(10, 10, 12), (30, 30, 34), (46, 46, 52), (66, 66, 74), (92, 92, 102)],
    "guant":   [(12, 10, 8), (30, 26, 20), (46, 40, 32), (62, 56, 44), (84, 76, 60)],
    "auric":   [(9, 10, 14), (28, 30, 36), (42, 44, 52), (60, 62, 72), (90, 92, 104)],
    "cinto":   [(14, 14, 10), (40, 38, 24), (58, 54, 34), (76, 72, 46), (98, 94, 62)],
    "acer":    [(20, 24, 34), (84, 92, 110), (124, 132, 150), (164, 172, 190), (214, 222, 236)],
    "metall":  [(12, 12, 16), (40, 42, 48), (64, 66, 74), (98, 102, 112), (150, 156, 170)],
    "negre":   [(8, 8, 10), (26, 26, 31), (38, 38, 45), (56, 56, 65), (88, 88, 99)],
    "fusta":   [(42, 20, 10), (98, 54, 24), (136, 80, 38), (170, 108, 56), (206, 144, 84)],
    "plasma":  [(14, 20, 40), (40, 70, 110), (70, 110, 160), (110, 150, 200), (170, 210, 240)],
    "energia": [(11, 29, 49), (25, 113, 173), (65, 197, 245), (141, 233, 255), (245, 253, 255)],
}
SHINY = {"casc", "visor", "metall", "negre", "bota", "acer", "energia"}
# Grups que el joc recolora
GRUPS = {"jaqueta": ["unif", "unif_f"], "casc": ["casc"], "pantalons": ["pant", "pant_f"],
         "arma": ["metall", "negre", "plasma"]}
OR = (230, 190, 70)
OR_CLAR = (255, 220, 100)


class Figura:
    def __init__(self, w=round(92 * S), h=round(59 * S) + 1):
        self.w, self.h = w, h
        self.ids = [[-1] * w for _ in range(h)]
        self.parts = []                        # (material, mode)
        self.detalls = []                      # (x, y, color) després d'ombrejar

    @staticmethod
    def t(x, y):
        return x * S, y * S

    # --- peces -------------------------------------------------------------------------------
    def peça(self, mat, dibuix, mode="pla"):
        idx = len(self.parts)
        self.parts.append((mat, mode))
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        dibuix(s)
        r = s.get_bounding_rect()
        for y in range(r.top, r.bottom):
            fila = self.ids[y]
            for x in range(r.left, r.right):
                if s.get_at((x, y)).a:
                    fila[x] = idx
        return idx

    def poli(self, mat, punts, mode="pla"):
        pts = [tuple(round(v) for v in self.t(x, y)) for x, y in punts]
        return self.peça(mat, lambda s: pygame.draw.polygon(s, (255, 255, 255), pts), mode)

    def rect(self, mat, x0, y0, x1, y1, mode="pla"):
        return self.poli(mat, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], mode)

    def el·lipse(self, mat, x0, y0, x1, y1, mode="pla"):
        a, b = self.t(x0, y0), self.t(x1, y1)
        r = (round(a[0]), round(a[1]), round(b[0] - a[0]) + 1, round(b[1] - a[1]) + 1)
        return self.peça(mat, lambda s: pygame.draw.ellipse(s, (255, 255, 255), r), mode)

    def membre(self, mat, punts, radis, mode="cilindre"):
        """Braç o cama: càpsules entre articulacions (radis que s'aprimen)."""
        pts = [self.t(x, y) for x, y in punts]
        rs = [r * S for r in radis]

        def d(s):
            for (a, ra), (b, rb) in zip(zip(pts, rs), zip(pts[1:], rs[1:])):
                n = max(2, int(math.dist(a, b) * 3))
                for i in range(n + 1):
                    k = i / n
                    pygame.draw.circle(s, (255, 255, 255), (round(a[0] + (b[0] - a[0]) * k), round(a[1] + (b[1] - a[1]) * k)),
                                       max(1, round(ra + (rb - ra) * k)))
        return self.peça(mat, d, mode)

    def px(self, x, y, color):
        tx, ty = self.t(x, y)
        self.detalls.append((round(tx), round(ty), color))

    def linia(self, a, b, color):
        a, b = self.t(*a), self.t(*b)
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) or 1
        for i in range(n + 1):
            self.detalls.append((round(a[0] + (b[0] - a[0]) * i / n), round(a[1] + (b[1] - a[1]) * i / n), color))

    # --- ombrejat i contorn ---------------------------------------------------------------------
    def superficie(self):
        w, h, ids = self.w, self.h, self.ids
        caixes = {}
        for y in range(h):
            for x in range(w):
                i = ids[y][x]
                if i >= 0:
                    x0, y0, x1, y1 = caixes.get(i, (x, y, x, y))
                    caixes[i] = (min(x0, x), min(y0, y), max(x1, x), max(y1, y))
        s = pygame.Surface((w, h), pygame.SRCALPHA)

        def de(x, y):
            return ids[y][x] if 0 <= x < w and 0 <= y < h else -1

        for y in range(h):
            for x in range(w):
                i = ids[y][x]
                if i < 0:
                    continue
                mat, mode = self.parts[i]
                tons = MAT[mat]
                veins = [de(x + 1, y), de(x - 1, y), de(x, y + 1), de(x, y - 1)]
                if -1 in veins[:2] + veins[3:] or (veins[2] == -1 and y < h - 1):
                    s.set_at((x, y), tons[0])                 # silueta
                    continue
                if any(v > i for v in veins):
                    s.set_at((x, y), tons[0])                 # una peça de davant: línia de separació
                    continue
                t = 2
                x0, y0, x1, y1 = caixes[i]
                if mode == "cos":                            # degradat de dalt a baix
                    f = (y - y0) / max(1, y1 - y0)
                    t = 3 if f < 0.28 else (1 if f > 0.78 else 2)
                dalt = de(x, y - 1) != i
                esq = de(x - 1, y) != i
                baix = de(x, y + 1) != i
                dre = de(x + 1, y) != i
                if mode == "cilindre" and (de(x, y + 2) != i or de(x + 2, y) != i):
                    t = 1
                if baix or dre:
                    t = 1
                if dalt or esq:
                    t = 4 if (mat in SHINY and dalt) else 3
                if mode == "fosc":
                    t = max(1, t - 1)
                s.set_at((x, y), tons[t])
        for x, y, c in self.detalls:
            if 0 <= x < w and 0 <= y < h and ids[y][x] >= 0:
                s.set_at((x, y), c)
        return s


# ------------------------------------------------------------------------------------------------
# Peces del soldat (coordenades en unitats de dibuix; Figura les escala)
# ------------------------------------------------------------------------------------------------
BOTA = [(-3, -3), (3, -3), (3, 0), (6, 1), (8, 2), (8, 4), (-4, 4), (-4, 1)]


def girar(punts, angle, origen):
    c, s = math.cos(angle), math.sin(angle)
    return [(origen[0] + x * c - y * s, origen[1] + x * s + y * c) for x, y in punts]


def cames(f, p, blindatge):
    """La bota forma part del peu: gira amb el pas (punta avall en impulsar-se, amunt en aterrar)."""
    for nom, mode, mat in (("cama_d", "fosc", "pant_f"), ("cama_f", "cilindre", "pant")):
        mal, gen, tur, angle = p[nom]
        f.membre(mat, [mal, gen, tur], [3.6, 3.0, 2.5], mode)
        if blindatge >= 3:
            f.el·lipse("acer", gen[0] - 2.5, gen[1] - 2.5, gen[0] + 2.5, gen[1] + 2.5)
        else:
            f.el·lipse("armilla" if nom == "cama_f" else "cinto", gen[0] - 2, gen[1] - 2, gen[0] + 2, gen[1] + 2)
        f.poli("bota", girar(BOTA, angle, tur), "fosc" if nom == "cama_d" else "pla")
        sola = girar([(-3, 3), (7, 3)], angle, tur)
        f.linia(sola[0], sola[1], MAT["bota"][3])
        cord = girar([(-2, -1), (2, -1)], angle, tur)
        f.linia(cord[0], cord[1], MAT["bota"][1])


def cos(f, p, blindatge):
    x, y = p["tors"]                                         # espatlla del darrere
    f.poli("motx", [(x - 5, y + 1), (x + 1, y), (x + 2, y + 13), (x - 4, y + 14), (x - 6, y + 9)])   # motxilla
    f.rect("motx", x - 5, y - 1, x, y + 2)                                # tapa de la motxilla
    f.poli("unif", [(x + 1, y), (x + 14, y), (x + 16, y + 5), (x + 14, y + 16), (x + 3, y + 16), (x + 1, y + 8)], "cos")
    if blindatge >= 2:                                       # peto d'acer
        f.poli("acer", [(x + 4, y + 2), (x + 15, y + 3), (x + 15, y + 6), (x + 13, y + 14), (x + 4, y + 14)], "cos")
    else:
        f.poli("armilla", [(x + 4, y + 2), (x + 15, y + 3), (x + 15, y + 6), (x + 13, y + 14), (x + 4, y + 14)], "cos")
    f.rect("cinto", x + 2, y + 15, x + 13, y + 17)


def cap(f, p, blindatge):
    x, y = p["cap"]                                          # racó de dalt a l'esquerra del casc
    f.rect("pell", x + 7, y + 13, x + 11, y + 17, "fosc")    # coll
    f.el·lipse("casc", x, y, x + 17, y + 12)
    f.poli("casc", [(x, y + 6), (x + 6, y + 6), (x + 7, y + 13), (x + 1, y + 13)])   # part de darrere i orella
    if blindatge >= 3:                                       # casc reforçat
        f.poli("acer", [(x + 1, y + 3), (x + 16, y + 2), (x + 17, y + 5), (x + 1, y + 6)])
    f.poli("pell", [(x + 8, y + 8), (x + 16, y + 8), (x + 18, y + 11), (x + 17, y + 13), (x + 16, y + 15),
                    (x + 10, y + 16), (x + 8, y + 13)])      # cara (per davant del casc)
    f.poli("visor", [(x + 8, y + 6), (x + 19, y + 6), (x + 19, y + 9), (x + 9, y + 9)])
    f.el·lipse("auric", x + 3, y + 8, x + 6, y + 12)         # auricular
    for i in range(3):
        f.px(x + 15 + i, y + 7, MAT["visor"][4])             # reflex del visor
    f.px(x + 12, y + 7, MAT["visor"][3])
    if blindatge < 3:
        f.linia((x + 2, y + 5), (x + 14, y + 4), MAT["casc"][1])      # cinta del casc
    f.px(x + 2, y + 3, (255, 214, 80)); f.px(x + 2, y + 4, (200, 150, 40))    # llumeta
    f.px(x + 17, y + 11, MAT["pell"][1])                     # nas
    f.linia((x + 13, y + 13), (x + 15, y + 13), MAT["pell"][1])   # boca
    f.linia((x + 10, y + 15), (x + 14, y + 15), MAT["pell"][1])   # barbeta
    f.linia((x + 7, y + 11), (x + 9, y + 15), MAT["cinto"][0])    # barbuquejo


def detalls_cos(f, p, blindatge):
    x, y = p["tors"]
    if blindatge < 2:
        for bx in (x + 5, x + 9):                            # butxaques de l'armilla
            f.linia((bx, y + 8), (bx + 2, y + 8), MAT["armilla"][0])
            f.linia((bx, y + 9), (bx + 2, y + 9), MAT["armilla"][3])
    else:
        f.linia((x + 5, y + 8), (x + 12, y + 8), MAT["acer"][1])     # reblons del peto
    f.px(x + 7, y + 16, OR); f.px(x + 8, y + 16, OR_CLAR)   # sivella
    f.linia((x + 2, y + 1), (x + 4, y + 12), MAT["motx"][0])        # corretja de la motxilla
    f.linia((x - 4, y + 2), (x, y + 2), MAT["motx"][0])


# ------------------------------------------------------------------------------------------------
# Armes (totes horitzontals, la boca a la dreta). (x, y) = empunyadura, on va la mà del gallet.
# ------------------------------------------------------------------------------------------------
def fusell(f, x, y):
    f.poli("fusta", [(x - 14, y - 4), (x - 4, y - 5), (x - 1, y - 5), (x - 1, y + 1), (x - 5, y + 1), (x - 12, y + 4),
                     (x - 14, y + 4)])                            # culata
    f.rect("metall", x - 1, y - 6, x + 14, y)                     # caixa de mecanismes
    f.poli("negre", [(x + 8, y), (x + 12, y), (x + 15, y + 8), (x + 11, y + 9)])       # carregador
    f.poli("negre", [(x, y), (x + 3, y), (x + 2, y + 6), (x - 1, y + 6)])              # empunyadura
    f.rect("fusta", x + 14, y - 5, x + 26, y - 1)                 # guardamà
    f.rect("negre", x + 14, y - 7, x + 27, y - 6)                 # tub de gas
    f.rect("metall", x + 26, y - 4, x + 38, y - 2)                # canó
    f.rect("negre", x + 34, y - 7, x + 35, y - 5)                 # punt de mira
    f.rect("negre", x + 38, y - 5, x + 40, y - 1)                 # bocana
    f.rect("negre", x + 2, y - 8, x + 9, y - 7)                   # carril / alça
    for i in range(3):
        f.px(x + 16 + i * 3, y - 3, MAT["fusta"][1])              # veta de la fusta
        f.px(x - 11 + i * 3, y - 1, MAT["fusta"][1])
    f.px(x + 3, y - 4, MAT["metall"][4]); f.px(x + 6, y - 3, MAT["metall"][1]); f.px(x + 7, y - 3, MAT["metall"][1])
    f.linia((x + 3, y + 1), (x + 5, y + 2), MAT["negre"][3])      # guardamonte
    return (x + 41, y - 3)


def pistola(f, x, y):
    f.poli("negre", [(x, y), (x + 3, y), (x + 2, y + 5), (x - 1, y + 5)])              # empunyadura
    f.rect("metall", x - 1, y - 4, x + 10, y - 1)                 # corredissa
    f.rect("negre", x + 9, y - 5, x + 9, y - 5)                   # mira
    f.px(x + 1, y - 3, MAT["metall"][4])
    for i in range(3):
        f.px(x + 3 + i * 2, y - 2, MAT["metall"][1])
    return (x + 11, y - 3)


def escopeta(f, x, y):
    f.poli("fusta", [(x - 13, y - 3), (x - 5, y - 4), (x - 1, y - 3), (x - 1, y + 1), (x - 6, y + 1), (x - 13, y + 4)])
    f.rect("negre", x - 1, y - 5, x + 10, y)                      # caixa
    f.poli("negre", [(x, y), (x + 3, y), (x + 2, y + 5), (x - 1, y + 5)])
    f.rect("metall", x + 10, y - 5, x + 34, y - 3)                # canó
    f.rect("metall", x + 10, y - 2, x + 30, y - 1)                # dipòsit
    f.rect("fusta", x + 16, y - 3, x + 25, y + 1)                 # corredora
    for i in range(4):
        f.px(x + 17 + i * 2, y, MAT["fusta"][1])
    f.rect("negre", x + 34, y - 6, x + 36, y - 2)
    return (x + 37, y - 4)


def minigun(f, x, y):
    """Minigun a l'alçada del maluc: x, y = empunyadura de darrere."""
    f.rect("negre", x - 1, y - 7, x + 3, y + 1)                   # empunyadura de darrere
    f.poli("metall", [(x + 2, y - 8), (x + 16, y - 8), (x + 18, y - 6), (x + 18, y + 2), (x + 2, y + 2)])   # motor
    f.rect("negre", x + 6, y - 11, x + 14, y - 9)                 # nansa de dalt
    f.poli("cinto", [(x + 4, y + 2), (x + 12, y + 2), (x + 12, y + 7), (x + 4, y + 7)])   # caixa de munició
    for k in range(3):                                            # tres canons
        f.rect("metall", x + 18, y - 6 + k * 3, x + 38, y - 5 + k * 3)
    for bx in (x + 24, x + 34):
        f.rect("negre", bx, y - 7, bx + 1, y + 1)                 # anelles
    f.rect("negre", x + 38, y - 7, x + 40, y + 1)                 # bocana
    f.px(x + 5, y - 6, MAT["metall"][4]); f.px(x + 6, y - 6, MAT["metall"][4])
    for k in range(3):
        f.px(x + 6 + k * 2, y + 4, OR)                            # bales a la caixa
    return (x + 41, y - 3)


def plasma(f, x, y):
    """Canó de plasma: cos arrodonit i bobines que brillen."""
    f.poli("plasma", [(x - 12, y - 4), (x - 3, y - 6), (x - 1, y - 6), (x - 1, y + 1), (x - 10, y + 3), (x - 12, y + 2)])
    f.poli("plasma", [(x - 1, y - 8), (x + 18, y - 8), (x + 22, y - 5), (x + 22, y - 1), (x - 1, y)])
    f.poli("negre", [(x, y), (x + 3, y), (x + 2, y + 6), (x - 1, y + 6)])
    f.rect("negre", x + 7, y, x + 11, y + 5)                      # cèl·lula d'energia
    f.rect("energia", x + 8, y + 1, x + 10, y + 4)
    for k in range(3):
        f.rect("energia", x + 5 + k * 5, y - 6, x + 7 + k * 5, y - 3)   # bobines
    f.rect("plasma", x + 22, y - 5, x + 33, y - 2)                # canó
    f.rect("energia", x + 33, y - 6, x + 35, y - 1)               # emissor
    f.px(x + 2, y - 7, MAT["plasma"][4]); f.px(x + 3, y - 7, MAT["plasma"][4])
    return (x + 36, y - 3)


ARMES = {"pistola": pistola, "escopeta": escopeta, "fusell": fusell, "minigun": minigun, "plasma": plasma}

# ------------------------------------------------------------------------------------------------
# Poses
# ------------------------------------------------------------------------------------------------
CUIXA, TIBIA = 10.0, 9.5
TURMELL = 55                     # alçada del turmell amb el peu a terra (la sola toca la fila 59)


def genoll(maluc, peu):
    """Cinemàtica inversa de dues peces: on va el genoll perquè el peu arribi al punt (genoll endavant)."""
    dx, dy = peu[0] - maluc[0], peu[1] - maluc[1]
    d = max(0.1, min(math.hypot(dx, dy), CUIXA + TIBIA - 0.05))
    a = math.atan2(dy, dx)
    t = math.acos(max(-1.0, min(1.0, (CUIXA ** 2 + d * d - TIBIA ** 2) / (2 * CUIXA * d))))
    return (maluc[0] + CUIXA * math.cos(a - t), maluc[1] + CUIXA * math.sin(a - t))


def pose(bob=0, peus=((19, TURMELL, 0.0), (31, TURMELL, 0.0))):
    tx, ty = 17, 19 + bob
    mal_d, mal_f = (tx + 5, 36 + bob), (tx + 10, 36 + bob)
    p = {"tors": (tx, ty), "cap": (tx, 2 + bob)}
    for nom, mal, (px, py, ang) in (("cama_d", mal_d, peus[0]), ("cama_f", mal_f, peus[1])):
        p[nom] = [mal, genoll(mal, (px, py)), (px, py), ang]
    return p


def pose_corre(i, n=6):
    fase = math.tau * i / n
    peus = []
    for base, ph in ((22, fase + math.pi), (27, fase)):
        x = base + 7 * math.sin(ph)
        enlaire = max(0.0, math.cos(ph))                  # >0: el peu va endavant per l'aire
        alca = 5 * enlaire
        angle = 0.55 * enlaire * -math.sin(ph) if enlaire else 0.0   # punta avall en sortir, amunt en arribar
        peus.append((x, TURMELL - alca, angle))
    bob = -1 if i % 3 == 1 else 0
    return pose(bob, peus)


POSES = [("quiet", pose(0)), ("quiet", pose(1)), *[("corre", pose_corre(i)) for i in range(6)],
         ("salt", pose(-2, ((20, 49, 0.45), (31, 51, 0.15)))),
         ("caiguda", pose(0, ((19, 56, 0.25), (30, 54, -0.25))))]


def soldat(arma="fusell", p=None, blindatge=0):
    p = p or pose()
    f = Figura()
    tx, ty = p["tors"]
    if arma == "minigun":
        empu = (tx + 11, ty + 15)
        braç_d = [(tx + 9, ty + 3), (tx + 17, ty + 12), (tx + 24, ty + 9)]
        braç_f = [(tx + 10, ty + 3), (tx + 7, ty + 11), (tx + 11, ty + 15)]
    elif arma in ("fusell", "escopeta", "plasma"):
        empu = (tx + 15, ty + 9)                                  # mà del gallet (a l'empunyadura)
        braç_d = [(tx + 9, ty + 3), (tx + 19, ty + 13), (tx + 31, ty + 8)]   # el de suport, cap al guardamà
        braç_f = [(tx + 10, ty + 3), (tx + 10, ty + 11), (tx + 15, ty + 10)]
    else:
        empu = (tx + 25, ty + 7)
        braç_d = [(tx + 6, ty + 3), (tx + 14, ty + 8), (tx + 24, ty + 7)]
        braç_f = [(tx + 11, ty + 3), (tx + 17, ty + 8), (tx + 25, ty + 7)]
    f.membre("unif_f", braç_d[:2], [3.0, 2.6], "fosc")             # braç del darrere (darrere del cos)
    cames(f, p, blindatge)
    cos(f, p, blindatge)
    cap(f, p, blindatge)
    boca = ARMES[arma](f, *empu)
    f.membre("unif_f", braç_d[1:], [2.6, 2.2], "fosc")             # avantbraç de suport
    f.el·lipse("guant", braç_d[2][0] - 2, braç_d[2][1] - 1, braç_d[2][0] + 2, braç_d[2][1] + 2)
    f.membre("unif", braç_f, [3.2, 2.8, 2.4])                      # braç del davant
    ex, ey = braç_f[0]
    f.el·lipse("acer" if blindatge >= 1 else "unif", ex - 3, ey - 2, ex + 3, ey + 3)   # espatlla / espatllera
    f.el·lipse("guant", empu[0] - 2, empu[1] - 2, empu[0] + 2, empu[1] + 2)
    detalls_cos(f, p, blindatge)
    if blindatge >= 1:
        f.px(ex - 1, ey - 1, MAT["acer"][4]); f.px(ex, ey - 1, MAT["acer"][4])
    return f.superficie(), tuple(round(v) for v in Figura.t(*boca))


def arma_sola(arma):
    f = Figura()
    boca = ARMES[arma](f, 30, 30)
    s = f.superficie()
    r = s.get_bounding_rect()
    return s.subsurface(r).copy(), (round(Figura.t(*boca)[0]) - r.x, round(Figura.t(*boca)[1]) - r.y)


def comprovar_paleta():
    vist = {}
    for mat, tons in MAT.items():
        for c in tons:
            assert c not in vist or vist[c] == mat, f"color repetit {c}: {mat} i {vist[c]}"
            vist[c] = mat


def generar(armes=None, nivells=(0, 1, 2, 3)):
    comprovar_paleta()
    armes = armes or list(ARMES)
    ancora = round(25 * S)                                      # els peus, al mig del cos
    info = {"escala": S, "ancora": ancora, "fotogrames": [n for n, _ in POSES], "materials": MAT,
            "grups": GRUPS, "armes": {}}
    for arma in armes:
        for b in nivells:
            fulls, boques = [], []
            for _, p in POSES:
                s, boca = soldat(arma, p, b)
                fulls.append(s)
                boques.append(boca)
            # tots els fotogrames de l'arma comparteixen el mateix requadre
            r = fulls[0].get_bounding_rect()
            for s in fulls[1:]:
                r = r.union(s.get_bounding_rect())
            r.height = fulls[0].get_height() - r.y                 # fins a terra
            tira = pygame.Surface((r.w * len(fulls), r.h), pygame.SRCALPHA)
            for i, s in enumerate(fulls):
                tira.blit(s, (i * r.w, 0), r)
            pygame.image.save(tira, os.path.join(SORTIDA, f"nexus_{arma}_{b}.png"))
            if b == 0:
                info["armes"][arma] = {"mida": [r.w, r.h], "ancora": ancora - r.x,
                                       "boques": [[bx - r.x, by - r.y] for bx, by in boques]}
            print(arma, b, r.size)
    imgs = [(a, *arma_sola(a)) for a in ARMES]
    w = sum(i.get_width() + 2 for _, i, _ in imgs)
    h = max(i.get_height() for _, i, _ in imgs)
    tira = pygame.Surface((w, h), pygame.SRCALPHA)
    x = 0
    info["armes_soles"] = {}
    for a, i, boca in imgs:
        tira.blit(i, (x, 0))
        info["armes_soles"][a] = [x, 0, i.get_width(), i.get_height()]
        x += i.get_width() + 2
    pygame.image.save(tira, os.path.join(SORTIDA, "nexus_armes.png"))
    with open(os.path.join(SORTIDA, "nexus.json"), "w") as fit:
        json.dump(info, fit, separators=(",", ":"))


if __name__ == "__main__":
    generar(sys.argv[1:] or None)
