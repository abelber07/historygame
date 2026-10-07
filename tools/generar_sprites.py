"""
Genera els sprite sheets dels enemics de terra (soldat, escut, kamikaze) i els retrats de ràdio.

No s'executa durant el joc: només cal tornar-lo a executar si es vol regenerar l'art.
    python tools/generar_sprites.py
Tot es dibuixa a la resolució nativa (el joc ja ho escala x2 sense suavitzar) i és determinista.
Cada full és una tira horitzontal de fotogrames iguals, amb fons transparent i personatges mirant
a la DRETA amb els peus tocant l'última fila del fotograma.
"""
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

pygame.init()
ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ARREL, "assets", "img")

# ---------------------------------------------------------------------------
# Paleta (tres tons per material: llum, mig, ombra; llum des de dalt a l'esquerra)
# ---------------------------------------------------------------------------
CONTORN = (22, 12, 30)
PELL = ((156, 230, 100), (96, 184, 74), (46, 116, 56))           # pell xylothiana
PELL_F = ((96, 170, 76), (62, 128, 60), (34, 84, 46))            # extremitats del darrere
ARMADURA = ((184, 128, 232), (128, 76, 186), (80, 42, 124))      # armadura lila
ARMADURA_F = ((120, 80, 166), (88, 54, 130), (56, 32, 88))
PESADA = ((150, 112, 196), (96, 66, 142), (58, 36, 92))           # armadura del portaescuts
PESADA_F = ((98, 72, 136), (70, 48, 104), (44, 28, 70))
METALL = ((182, 178, 206), (118, 112, 148), (70, 64, 96))
METALL_F = ((120, 116, 146), (84, 78, 108), (52, 46, 72))
CIAN, CIAN_C, BLANC = (90, 230, 255), (190, 250, 255), (250, 252, 255)
CIAN_F = (30, 140, 190)
MAGENTA, MAGENTA_C, MAGENTA_F = (236, 72, 200), (255, 164, 238), (150, 30, 130)
ULL_BLANC = (244, 244, 236)


# ---------------------------------------------------------------------------
# Eines de dibuix
# ---------------------------------------------------------------------------
def nova(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def ple(s, x, y):
    return 0 <= x < s.get_width() and 0 <= y < s.get_height() and s.get_at((x, y))[3] > 0


def px(s, x, y, c):
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        s.set_at((x, y), c)


def el_lipse(s, c, x0, y0, w, h):
    """El·lipse plena que encaixa exactament al rectangle (x0, y0, w, h)."""
    cx, cy, rx, ry = x0 + w / 2, y0 + h / 2, w / 2, h / 2
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0:
                px(s, x, y, c)


def linia(s, c, p0, p1, gruix=1):
    """Línia de Bresenham amb un pinzell quadrat de gruix x gruix."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    o = (gruix - 1) // 2
    while True:
        for yy in range(gruix):
            for xx in range(gruix):
                px(s, x0 - o + xx, y0 - o + yy, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def dibuixar(m, formes):
    """Formes: ('r',x,y,w,h) rectangle, ('e',x,y,w,h) el·lipse, ('l',x0,y0,x1,y1,gruix) línia,
    ('p',[punts]) polígon, ('x',x,y) píxel, ('cam',[punts],gruix) línia trencada."""
    B = (255, 255, 255)
    for f in formes:
        k = f[0]
        if k == "r":
            pygame.draw.rect(m, B, f[1:5])
        elif k == "e":
            el_lipse(m, B, *f[1:5])
        elif k == "l":
            linia(m, B, (f[1], f[2]), (f[3], f[4]), f[5] if len(f) > 5 else 1)
        elif k == "cam":
            for a, b in zip(f[1], f[1][1:]):
                linia(m, B, a, b, f[2])
        elif k == "p":
            pygame.draw.polygon(m, B, f[1])
        elif k == "x":
            px(m, f[1], f[2], B)


def ombrejar(m, tons):
    """Pinta la màscara amb tres tons: vores de dalt/esquerra clares i de baix/dreta fosques."""
    llum, mig, fosc = tons
    w, h = m.get_size()
    r = nova(w, h)
    for y in range(h):
        for x in range(w):
            if not ple(m, x, y):
                continue
            if not ple(m, x, y - 1) or not ple(m, x - 1, y) and ple(m, x + 1, y):
                c = llum
            elif not ple(m, x, y + 1) or not ple(m, x + 1, y):
                c = fosc
            else:
                c = mig
            r.set_at((x, y), c)
    return r


def contornejar(s, color=CONTORN, fora_de=None):
    """Contorn d'1 px (veïnatge 4). Amb fora_de, només on aquella superfície encara és transparent."""
    w, h = s.get_size()
    punts = [(x, y) for y in range(h) for x in range(w)
             if not ple(s, x, y) and any(ple(s, x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
             and (fora_de is None or not ple(fora_de, x, y))]
    for p in punts:
        s.set_at(p, color)
    return s


def capa(dest, formes, tons, contorn=CONTORN, exterior=False):
    """Dibuixa una peça (màscara -> ombrejat -> contorn) i l'enganxa sobre dest.
    exterior=True: el contorn no trepitja el que ja hi ha dibuixat (unions netes)."""
    m = nova(*dest.get_size())
    dibuixar(m, formes)
    c = ombrejar(m, tons) if isinstance(tons[0], tuple) else _pla(m, tons)
    if contorn:
        # contorn selectiu: negre contra el buit, i un to enfosquit del que hi ha a sota a dins de la figura
        w, h = c.get_size()
        punts = [(x, y) for y in range(h) for x in range(w) if not ple(c, x, y)
                 and any(ple(c, x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        for x, y in punts:
            if not ple(dest, x, y):
                c.set_at((x, y), contorn)
            elif not exterior:
                r, g, b, _ = dest.get_at((x, y))
                c.set_at((x, y), (int(r * 0.55), int(g * 0.55), int(b * 0.6)))
    dest.blit(c, (0, 0))
    return m


def _pla(m, color):
    r = nova(*m.get_size())
    for y in range(m.get_height()):
        for x in range(m.get_width()):
            if ple(m, x, y):
                r.set_at((x, y), color)
    return r


def plantilla(dest, x0, y0, files, colors):
    for j, fila in enumerate(files):
        for i, ch in enumerate(fila):
            if ch in colors:
                px(dest, x0 + i, y0 + j, colors[ch])


def tira(fotogrames):
    w, h = fotogrames[0].get_size()
    s = nova(w * len(fotogrames), h)
    for i, f in enumerate(fotogrames):
        assert f.get_size() == (w, h)
        s.blit(f, (i * w, 0))
    return s


def desar(s, nom):
    pygame.image.save(s, os.path.join(IMG, nom))
    print("  ", nom, s.get_size())


# ---------------------------------------------------------------------------
# Cames (comunes al soldat i al portaescuts)
# ---------------------------------------------------------------------------
def cama(f, maluc, genoll, turmell, gruix, tons_cuixa, tons_bota, llarg_bota):
    """Cama de dues peces fins al turmell i bota de 2 files que acaba a turmell_y + 2."""
    capa(f, [("cam", [maluc, genoll, turmell], gruix)], tons_cuixa)
    tx, ty = turmell
    o = (gruix - 1) // 2
    capa(f, [("r", tx - o, ty + gruix - o - 1, llarg_bota, 2)], tons_bota)


# ---------------------------------------------------------------------------
# 1. Soldat xylothià: 18x26, 6 fotogrames (0-3 caminar, 4 disparar, 5 ferit)
# ---------------------------------------------------------------------------
SW, SH = 18, 26
VESTIT = ((112, 96, 140), (78, 64, 104), (50, 40, 72))           # malla fosca de les cames
VESTIT_F = ((84, 70, 110), (60, 48, 84), (40, 30, 58))

FUSELL = [
    "...aaaaaa...",
    "smmcccccmmbt",
    "ssmmmmmmmb..",
    "s....gg.....",
]


def fusell(f, x, y, actiu=False):
    colors = {"a": METALL[0], "m": METALL[1], "s": ARMADURA_F[2], "g": METALL[2],
              "c": CIAN if actiu else CIAN_F, "b": METALL[2], "t": BLANC if actiu else CIAN}
    c = nova(*f.get_size())
    plantilla(c, x, y, FUSELL, colors)
    contornejar(c)
    f.blit(c, (0, 0))
    if actiu:
        px(f, x + 5, y + 1, CIAN_C)
        px(f, x + 6, y + 1, CIAN_C)


def cap_soldat(f, x, y, ferit=False):
    """Cap d'alien: crani en cúpula, mandíbula endavant i un sol ull gran. (x, y) = cantonada del crani."""
    capa(f, [("e", x, y, 9, 6), ("e", x + 4, y + 3, 5, 4)], PELL, exterior=True)
    capa(f, [("e", x, y - 1, 6, 3), ("r", x, y, 2, 3)], ARMADURA, exterior=True)    # casquet i auricular
    px(f, x, y + 1, CIAN)
    px(f, x + 2, y - 1, ARMADURA[0])
    if ferit:
        for p in ((5, 2), (6, 3), (7, 3), (8, 2)):                                   # ull aclucat
            px(f, x + p[0], y + p[1], CONTORN)
        px(f, x + 7, y + 5, CONTORN)                                                 # boca oberta
        px(f, x + 8, y + 5, (120, 20, 60))
    else:
        for i in range(3):                                                           # ull
            px(f, x + 5 + i, y + 2, ULL_BLANC)
            px(f, x + 5 + i, y + 3, ULL_BLANC)
        px(f, x + 7, y + 2, MAGENTA)
        px(f, x + 7, y + 3, MAGENTA_F)
        px(f, x + 5, y + 1, PELL[2])                                                 # cella
        px(f, x + 6, y + 1, PELL[2])
        px(f, x + 7, y + 5, PELL[2])                                                 # boca


def soldat(fot):
    f = nova(SW, SH)
    # (bot del cos, (maluc, genoll, turmell) cama del darrere, idem cama del davant)
    poses = {
        0: (0, ((7, 16), (6, 19), (4, 22)), ((8, 16), (10, 19), (12, 22))),
        1: (-1, ((7, 15), (9, 18), (7, 20)), ((8, 15), (8, 18), (8, 22))),
        2: (0, ((8, 16), (10, 19), (12, 22)), ((7, 16), (6, 19), (4, 22))),
        3: (-1, ((7, 15), (8, 18), (8, 22)), ((8, 15), (9, 18), (7, 20))),
        4: (0, ((7, 16), (5, 19), (4, 22)), ((8, 16), (10, 19), (11, 22))),
        5: (0, ((6, 16), (4, 19), (2, 22)), ((7, 16), (9, 19), (9, 22))),
    }
    b, darrere, davant = poses[fot]
    dx = -1 if fot == 5 else 0
    cama(f, *darrere, 2, VESTIT_F, METALL_F, 3)
    # braç del darrere
    if fot == 4:
        capa(f, [("cam", [(7, 11), (10, 12), (12, 12)], 2)], PELL_F)
    elif fot == 5:
        capa(f, [("cam", [(5, 11), (3, 9), (2, 7)], 2)], PELL_F)
    else:
        capa(f, [("cam", [(6, 11 + b), (6, 13 + b), (8, 14 + b)], 2)], PELL_F)
    # tors: peto lila, pelvis de malla
    capa(f, [("r", 6 + dx, 15 + b, 4, 2)], VESTIT)
    capa(f, [("r", 5 + dx, 10 + b, 6, 5), ("e", 4 + dx, 9 + b, 8, 4), ("r", 6 + dx, 14 + b, 4, 1)], ARMADURA)
    px(f, 7 + dx, 12 + b, MAGENTA)                                                    # gemma del pit
    px(f, 7 + dx, 11 + b, MAGENTA_C)
    for x in range(6 + dx, 10 + dx):                                                  # cinturó
        px(f, x, 15 + b, METALL[2])
    px(f, 8 + dx, 15 + b, CIAN)
    cama(f, *davant, 2, VESTIT, METALL, 3)
    if fot == 5:
        cap_soldat(f, 3, 3, ferit=True)
    else:
        cap_soldat(f, 5, 3 + b)
    if fot == 4:                                                                      # apuntant
        fusell(f, 5, 10, actiu=True)
        capa(f, [("e", 6, 9, 4, 3)], ARMADURA)
        capa(f, [("cam", [(8, 11), (11, 11)], 2)], PELL)
        for p, c in (((17, 10), CIAN), ((17, 11), CIAN_C), ((17, 12), CIAN), ((16, 9), CIAN_F), ((16, 13), CIAN_F)):
            px(f, p[0], p[1], c)                                                      # fogonada
    elif fot == 5:                                                                    # ferit: fusell desviat
        c = nova(SW, SH)
        linia(c, METALL[1], (8, 12), (13, 7), 2)
        linia(c, METALL[0], (9, 11), (13, 7))
        contornejar(c)
        f.blit(c, (0, 0))
        px(f, 11, 10, CIAN_F)
        px(f, 12, 9, CIAN_F)
        capa(f, [("e", 5, 9, 4, 3)], ARMADURA)
        capa(f, [("cam", [(6, 11), (8, 12)], 2)], PELL)
    else:                                                                             # caminant
        fusell(f, 5, 12 + b)
        capa(f, [("e", 6, 9 + b, 4, 3)], ARMADURA)
        capa(f, [("cam", [(7, 11 + b), (8, 13 + b), (10, 13 + b)], 2)], PELL)
    return f


# ---------------------------------------------------------------------------
# 2. Portaescuts: 22x28, 5 fotogrames (0-3 caminar feixuc, 4 parapetat)
# ---------------------------------------------------------------------------
EW, EH = 22, 28
ACER = ((176, 182, 204), (116, 122, 152), (70, 74, 102))          # blindatge d'acer
ACER_F = ((118, 122, 150), (82, 86, 114), (50, 52, 76))


def escut(fot):
    f = nova(EW, EH)
    # (bot, inclinació, cama del darrere, cama del davant)
    poses = {
        0: (0, 0, ((8, 18), (7, 21), (6, 24)), ((11, 18), (13, 21), (13, 24))),
        1: (-1, 0, ((9, 17), (11, 20), (9, 22)), ((10, 17), (10, 20), (10, 24))),
        2: (0, 0, ((10, 18), (12, 21), (12, 24)), ((9, 18), (7, 21), (7, 24))),
        3: (-1, 0, ((9, 17), (10, 20), (10, 24)), ((10, 17), (12, 20), (10, 22))),
        4: (2, 1, ((8, 20), (5, 22), (4, 24)), ((11, 20), (14, 21), (14, 24))),
    }
    b, ax, darrere, davant = poses[fot]
    braced = fot == 4
    cama(f, *darrere, 3, ACER_F, METALL_F, 5)
    capa(f, [("r", 2 + ax, 9 + b, 4, 8), ("x", 3 + ax, 8 + b)], ARMADURA_F)           # motxilla d'energia
    for y in (11, 13, 15):
        px(f, 2 + ax, y + b, CIAN if braced else CIAN_F)
    capa(f, [("r", 6 + ax, 17 + b, 8, 2)], PESADA_F)                                   # pelvis
    capa(f, [("r", 5 + ax, 9 + b, 10, 8), ("e", 4 + ax, 7 + b, 12, 6)], ACER)        # tors massís
    for x in range(6 + ax, 14 + ax):
        px(f, x, 13 + b, ACER[2])
    for x in range(5 + ax, 15 + ax):                                                   # cinturó lila
        px(f, x, 16 + b, ARMADURA[1])
    px(f, 9 + ax, 16 + b, MAGENTA)
    px(f, 8 + ax, 11 + b, ACER[0])
    cama(f, *davant, 3, ACER, METALL, 5)
    # cap: casc tancat amb visera magenta, tentacles verds sota
    capa(f, [("l", 10 + ax, 8 + b, 10 + ax, 10 + b), ("l", 12 + ax, 8 + b, 12 + ax, 9 + b)], PELL)
    capa(f, [("e", 6 + ax, 2 + b, 8, 4), ("r", 6 + ax, 4 + b, 8, 3), ("r", 8 + ax, 6 + b, 6, 2)], ARMADURA)
    for x in range(10, 14):
        px(f, x + ax, 5 + b, MAGENTA)
    px(f, 13 + ax, 5 + b, MAGENTA_C)
    px(f, 9 + ax, 5 + b, MAGENTA_F)
    for x in range(7, 10):                                                            # cresta
        px(f, x + ax, 3 + b, ARMADURA[0])
    capa(f, [("e", 11 + ax, 7 + b, 7, 6)], ACER)                                      # espatllera gran
    px(f, 13 + ax, 8 + b, ACER[0])
    # braç del davant i emissor d'escut (placa vertical)
    e = -2 if braced else 0
    capa(f, [("cam", [(14 + ax, 12 + b), (15 + ax, 15 + b), (17, 15 + b + e)], 3)], PELL)
    capa(f, [("r", 17, 4 + b + e, 3, 17), ("r", 20, 5 + b + e, 1, 3), ("r", 20, 16 + b + e, 1, 3)], METALL)
    nodes = (7, 12, 17)
    for y in range(5, 20):                                                             # ranura de l'emissor
        px(f, 18, y + b + e, METALL[2])
    for n in nodes:
        px(f, 19, n + b + e, BLANC if braced else CIAN)
        px(f, 18, n + b + e, CIAN if braced else CIAN_F)
    px(f, 20, 6 + b + e, CIAN if braced else CIAN_F)
    px(f, 20, 17 + b + e, CIAN if braced else CIAN_F)
    return f


# ---------------------------------------------------------------------------
# 3. Kamikaze: 14x10, 5 fotogrames (0-3 correr, 4 armat)
# ---------------------------------------------------------------------------
KW, KH = 14, 10
SAC = ((255, 170, 240), (220, 70, 200), (140, 30, 140))
SAC_ARMAT = ((255, 255, 240), (255, 90, 70), (190, 20, 30))
CLOSCA = ((120, 96, 150), (78, 58, 104), (48, 34, 70))


def kamikaze(fot):
    f = nova(KW, KH)
    armat = fot == 4
    b = 0 if fot in (0, 2) else -1                       # el cos puja en els passos intermedis
    # tres potes visibles (línies fosques) amb la punta a l'última fila; trípode alternat
    potes = {0: (1, -1, 1), 1: (0, 0, 0), 2: (-1, 1, -1), 3: (0, 0, 0), 4: (-2, 0, 2)}[fot]
    for bx, d in zip((4, 7, 10), potes):
        linia(f, CONTORN, (bx, 7 + b), (bx + d, 9))
    capa(f, [("e", 3, 5 + b, 8, 3)], CLOSCA)                                        # cos
    capa(f, [("e", 9, 4 + b, 4, 4)], CLOSCA)                                        # cap
    px(f, 12, 5 + b, CIAN_C if armat else CIAN)                                     # ulls
    px(f, 11, 5 + b, CIAN_F)
    px(f, 13, 7 + b, CONTORN)                                                       # mandíbules
    px(f, 13, 6 + b, CLOSCA[2])
    if armat:
        capa(f, [("e", 1, 1, 9, 7)], SAC_ARMAT)                                     # sac a punt d'esclatar
        for p in ((4, 3), (5, 3), (6, 3), (4, 4), (5, 4), (6, 4), (5, 2), (3, 4)):
            px(f, p[0], p[1], BLANC)
        for p in ((3, 3), (7, 3), (4, 5), (6, 5), (5, 5)):
            px(f, p[0], p[1], (255, 230, 120))
        for p in ((0, 2), (10, 1), (0, 6)):                                         # guspires
            px(f, p[0], p[1], (255, 240, 160))
    else:
        gran = 1 if fot in (1, 3) else 0                                            # el sac batega
        sy = 2 + b
        capa(f, [("e", 1, sy, 8 + gran, 6)], SAC)
        px(f, 3, sy + 1, SAC[0])
        px(f, 4, sy + 1, BLANC)
        for p in ((6, 2), (5, 3), (6, 4), (3, 4), (7, 3 + gran)):                    # venes
            px(f, p[0], sy + p[1], SAC[2])
        px(f, 5 + gran, sy + 3, MAGENTA_C)
    return f


# ---------------------------------------------------------------------------
# 4. Retrats de ràdio: 32x32, 2 fotogrames (boca tancada, boca oberta)
# ---------------------------------------------------------------------------
RW = 32
MARC = (12, 10, 18)
CARA = ((252, 214, 168), (232, 180, 132), (184, 128, 96))
CARA_R = ((232, 184, 140), (204, 148, 108), (150, 98, 74))
OLIVA = ((168, 166, 52), (130, 119, 23), (86, 78, 18))
DENTS = (232, 226, 214)
FOSC_BOCA = (70, 22, 28)


def fons_retrat(color):
    """Fons opac tintat amb un halo suau i línies de ràdio, dins d'un marc d'1 px."""
    f = pygame.Surface((RW, RW), pygame.SRCALPHA)
    f.fill(MARC)
    clar = tuple(min(255, c + 16) for c in color)
    fosc = tuple(max(0, c - 10) for c in color)
    for y in range(1, RW - 1):
        for x in range(1, RW - 1):
            d = math.hypot(x - 15.5, y - 13) / 22
            base = clar if d < 0.55 else color if d < 0.9 else fosc
            if y % 2 == 0:
                base = tuple(max(0, c - 6) for c in base)
            f.set_at((x, y), base)
    return f


def compondre(fons, figura):
    fons.blit(figura, (0, 0))
    pygame.draw.rect(fons, MARC, (0, 0, RW, RW), 1)
    return fons


def boca(f, oberta, llavi, y=19, x0=14, ample=4):
    if oberta:
        for x in range(x0, x0 + ample):
            px(f, x, y, FOSC_BOCA)
        for x in range(x0 + 1, x0 + ample - 1):
            px(f, x, y, DENTS)
            px(f, x, y + 1, FOSC_BOCA)
        px(f, x0 + 1, y + 2, llavi)
        px(f, x0 + 2, y + 2, llavi)
    else:
        for x in range(x0, x0 + ample):
            px(f, x, y, llavi)


def cap_huma(f, tons):
    """Coll, cara i orelles d'un bust frontal; la cara no deixa línia negra sobre el coll."""
    capa(f, [("r", 13, 18, 6, 7)], tons)
    for x in range(13, 19):                                                         # ombra de la barbeta
        px(f, x, 22, tons[2])
    capa(f, [("e", 10, 6, 12, 16), ("e", 9, 12, 2, 4), ("e", 21, 12, 2, 4)], tons, exterior=True)
    px(f, 16, 14, tons[2])                                                          # nas
    px(f, 16, 15, tons[2])
    px(f, 15, 16, tons[2])
    px(f, 16, 16, tons[2])
    px(f, 15, 15, tons[0])


def ulls(f, y=13, pupil=(30, 24, 30)):
    px(f, 12, y, ULL_BLANC)
    px(f, 13, y, pupil)
    px(f, 18, y, pupil)
    px(f, 19, y, ULL_BLANC)


def retrat_comandant(obert):
    g = nova(RW, RW)
    capa(g, [("e", 2, 23, 28, 14)], OLIVA)                                          # espatlles
    capa(g, [("p", [(11, 22), (16, 28), (21, 22), (21, 25), (16, 31), (11, 25)])],
         ((110, 102, 30), (92, 84, 20), (66, 60, 12)))                              # coll de la guerrera
    cap_huma(g, CARA_R)
    for x0 in (6, 23):                                                              # insígnies
        for p in ((0, 0), (2, 0)):
            px(g, x0 + p[0], 26 + p[1], (255, 213, 79))
            px(g, x0 + p[0], 27 + p[1], (190, 150, 40))
    px(g, 16, 29, (255, 213, 79))
    capa(g, [("r", 11, 4, 10, 2), ("r", 10, 5, 12, 4), ("r", 10, 9, 2, 3), ("r", 20, 9, 2, 3)],
         ((222, 222, 222), (168, 168, 172), (112, 112, 120)), exterior=True)        # cabell gris rapat
    cella = (96, 96, 104)
    for p in ((12, 11), (13, 11), (14, 12), (17, 12), (18, 11), (19, 11)):          # celles arrufades
        px(g, p[0], p[1], cella)
    ulls(g)
    for p in ((19, 10), (19, 12), (20, 14), (20, 15), (21, 16)):                     # cicatriu
        px(g, p[0], p[1], (160, 64, 64))
    px(g, 20, 11, (236, 160, 150))
    px(g, 13, 17, CARA_R[2])                                                        # arrugues
    px(g, 18, 17, CARA_R[2])
    for p in ((12, 19), (19, 19), (13, 20), (18, 20), (15, 21), (17, 21)):           # barba d'uns dies
        px(g, p[0], p[1], CARA_R[2])
    boca(g, obert, (120, 64, 54))
    # auriculars amb micròfon
    diadema = (44, 44, 50)
    for x in range(11, 21):
        px(g, x, 3, diadema)
    for p in ((10, 4), (9, 5), (9, 6), (9, 7), (9, 8), (9, 9), (9, 10), (21, 4), (22, 5), (22, 6), (22, 7), (22, 8),
              (22, 9), (22, 10)):
        px(g, p[0], p[1], diadema)
    gris = ((100, 100, 108), (66, 66, 72), (38, 38, 44))
    capa(g, [("r", 7, 11, 3, 5)], gris)
    capa(g, [("r", 22, 11, 3, 5)], gris)
    linia(g, diadema, (9, 16), (11, 19))
    px(g, 12, 19, (90, 90, 96))
    px(g, 12, 20, diadema)
    px(g, 8, 12, (120, 240, 140) if obert else (50, 110, 60))                       # llum de transmissió
    return compondre(fons_retrat((52, 60, 38)), g)


def retrat_doctora(obert):
    g = nova(RW, RW)
    bata = ((252, 252, 255), (216, 222, 232), (150, 160, 178))
    capa(g, [("e", 2, 23, 28, 14)], bata)                                           # bata blanca
    capa(g, [("p", [(12, 22), (16, 29), (20, 22), (20, 25), (16, 31), (12, 25)])],
         ((90, 140, 160), (60, 108, 130), (40, 78, 98)))                            # camisa
    linia(g, bata[2], (11, 24), (15, 31))                                           # solapes
    linia(g, bata[2], (21, 24), (17, 31))
    capa(g, [("r", 22, 26, 3, 4)], ((140, 236, 255), (60, 176, 214), (30, 110, 150)))  # credencial
    px(g, 23, 27, BLANC)
    px(g, 8, 26, (60, 90, 200))                                                     # bolígraf a la butxaca
    px(g, 8, 27, (60, 90, 200))
    cabell = ((104, 70, 58), (64, 40, 34), (38, 22, 22))
    capa(g, [("e", 12, 1, 8, 6)], cabell)                                           # monyo
    px(g, 14, 2, (140, 96, 80))
    cap_huma(g, CARA)
    capa(g, [("e", 9, 4, 14, 7), ("r", 9, 8, 2, 9), ("r", 21, 8, 2, 9), ("r", 11, 9, 3, 1)], cabell,
         exterior=True)                                                             # cabell recollit
    px(g, 13, 6, (140, 96, 80))
    px(g, 16, 5, (140, 96, 80))
    for x in (12, 13, 18, 19):                                                      # celles
        px(g, x, 11, cabell[1])
    ulls(g, 13, (50, 34, 30))
    montura = (70, 36, 48)
    for x0 in (11, 17):                                                             # ulleres rodones
        for p in ((1, 0), (2, 0), (0, 1), (3, 1), (1, 2), (2, 2)):
            px(g, x0 + p[0], 12 + p[1], montura)
        px(g, x0 + 1, 12, (236, 200, 210))                                          # reflex
    px(g, 15, 13, montura)
    px(g, 16, 13, montura)
    px(g, 10, 13, montura)                                                          # patilles
    px(g, 21, 13, montura)
    boca(g, obert, (196, 96, 100))
    capa(g, [("r", 22, 12, 2, 3)], ((160, 160, 170), (110, 110, 120), (66, 66, 76)))  # auricular
    px(g, 23, 12, CIAN_C if obert else CIAN_F)
    return compondre(fons_retrat((28, 52, 72)), g)


def retrat_nexus(obert):
    g = nova(RW, RW)
    verd = ((120, 170, 70), (85, 139, 47), (56, 96, 30))
    capa(g, [("e", 2, 23, 28, 14)], OLIVA)                                          # uniforme
    capa(g, [("r", 8, 26, 16, 6)], ((64, 64, 66), (42, 42, 44), (26, 26, 28)))      # armilla
    capa(g, [("r", 4, 27, 4, 5), ("r", 24, 27, 4, 5)], verd)
    px(g, 18, 28, (255, 213, 79))
    px(g, 19, 28, (255, 213, 79))
    cap_huma(g, CARA)
    capa(g, [("e", 8, 2, 16, 12), ("r", 8, 8, 3, 8), ("r", 21, 8, 3, 8)], OLIVA)   # casc
    for x in range(9, 23):                                                          # franja del casc
        px(g, x, 6, (33, 33, 33))
    px(g, 11, 4, OLIVA[0])
    capa(g, [("r", 10, 11, 12, 3)], (CIAN_C, CIAN, CIAN_F))                         # visor
    px(g, 12, 11, BLANC)
    px(g, 13, 11, BLANC)
    px(g, 11, 12, BLANC)
    for x in (13, 18):                                                              # ulls darrere el visor
        px(g, x, 12, (40, 150, 200) if not obert else (30, 120, 170))
    capa(g, [("r", 22, 9, 2, 2)], METALL)                                           # implant a la templa
    px(g, 22, 10, CIAN_C if obert else CIAN)
    px(g, 24, 10, CIAN if obert else CIAN_F)
    px(g, 24, 9, CIAN_F if obert else (30, 60, 90))
    tira_casc = (33, 33, 33)
    linia(g, tira_casc, (10, 16), (12, 20))                                         # barboquet
    linia(g, tira_casc, (21, 16), (19, 20))
    boca(g, obert, (176, 104, 84))
    return compondre(fons_retrat((20, 30, 60)), g)


def retrat_ment(obert):
    f = fons_retrat((52, 18, 52))
    carn = ((150, 70, 140), (104, 40, 104), (64, 22, 68))
    plec = (40, 12, 44)
    # teixit orgànic: plecs ondulats generats amb sinus (deterministes)
    for y in range(1, RW - 1):
        for x in range(1, RW - 1):
            v = math.sin(x * 0.55 + 1.8 * math.sin(y * 0.33)) + math.sin(y * 0.5 + 1.4 * math.sin(x * 0.27))
            vora = math.hypot(x - 15.5, y - 15.5) / 16
            v -= vora * 0.9
            if abs(v - 0.1) < 0.18:
                c = plec
            elif v > 0.75:
                c = carn[0]
            elif v > 0.1:
                c = carn[1]
            else:
                c = carn[2]
            f.set_at((x, y), c)
    venes = [[(1, 5), (4, 8), (6, 12)], [(30, 3), (27, 7), (25, 11)], [(1, 27), (5, 23), (7, 20)],
             [(30, 28), (26, 24), (24, 21)], [(14, 1), (15, 4), (14, 7)], [(17, 30), (16, 27), (17, 24)],
             [(4, 8), (2, 11)], [(27, 7), (29, 11)]]
    for v in venes:
        for a, b in zip(v, v[1:]):
            linia(f, MAGENTA if obert else MAGENTA_F, a, b)
        px(f, *v[-1], MAGENTA_C if obert else MAGENTA)
    # ull
    h = 15 if obert else 9
    y0 = 16 - h // 2
    blanc = ((248, 236, 224), (230, 212, 200), (186, 150, 160))
    m = capa(f, [("e", 4, y0, 24, h)], blanc, contorn=(26, 4, 28))
    for x in range(5, 27):                                                          # parpella de dalt
        for y in range(y0 - 2, y0 + h):
            if ple(m, x, y):
                px(f, x, y - 2, carn[0])
                break
    for v in (((5, 16), (7, 16), (9, 15)), ((6, 18), (9, 17)), ((26, 15), (24, 16), (22, 16)),
              ((25, 18), (22, 17)), ((7, 14), (9, 14))):                             # venetes de l'ull
        for a, b in zip(v, v[1:]):
            c = nova(RW, RW)
            linia(c, (214, 90, 110), a, b)
            for y in range(RW):
                for x in range(RW):
                    if ple(c, x, y) and ple(m, x, y) and ple(m, x, y - 1) and ple(m, x, y + 1):
                        px(f, x, y, (214, 90, 110))
    r = 6 if obert else 5
    for y in range(16 - r, 17 + r):
        for x in range(16 - r, 17 + r):
            d = math.hypot(x + 0.5 - 16.5, y + 0.5 - 16.5)
            if d <= r + 0.3 and ple(m, x, y) and ple(m, x, y - 1) and ple(m, x, y + 1):
                if d > r - 1.1:
                    c = (90, 20, 120)
                elif d > r / 2:
                    c = (210, 70, 230) if obert else (176, 60, 200)
                else:
                    c = (150, 40, 180)
                px(f, x, y, c)
    for y in range(16 - r + 1, 17 + r - 1):                                          # pupil·la en escletxa
        if ple(m, 16, y - 1) and ple(m, 16, y + 1):
            if obert:
                px(f, 16, y, BLANC if abs(y - 16) < 3 else MAGENTA_C)
                px(f, 15, y, MAGENTA_C)
                px(f, 17, y, MAGENTA_C)
            else:
                px(f, 16, y, (20, 4, 24))
    px(f, 13, 13 if obert else 14, BLANC)                                           # reflex
    pygame.draw.rect(f, MARC, (0, 0, RW, RW), 1)
    return f


def main():
    print("Generant sprites:")
    desar(tira([soldat(i) for i in range(6)]), "enemic_soldat.png")
    desar(tira([escut(i) for i in range(5)]), "enemic_escut.png")
    desar(tira([kamikaze(i) for i in range(5)]), "enemic_kamikaze.png")
    for nom, fn in (("comandant", retrat_comandant), ("doctora", retrat_doctora),
                    ("nexus", retrat_nexus), ("ment", retrat_ment)):
        desar(tira([fn(False), fn(True)]), "retrat_%s.png" % nom)


if __name__ == "__main__":
    main()
