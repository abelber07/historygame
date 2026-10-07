"""
Genera el pixel art del joc: fons dels cinc sectors, caps finals nous, caçador i armes noves.

No s'executa durant el joc: només cal tornar-lo a executar si es vol regenerar l'art.
    python tools/generar_assets.py
Totes les imatges es dibuixen a baixa resolució i s'escalen sense suavitzar.
"""
import math
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))
ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ARREL, "assets", "img")
# Los fondos se dibujan a la mitad (500x303), se recortan 23 filas de cielo (500x280) y se escalan x2:
# 1000x560, el tamaño exacto con el que el juego los pinta (960x540 + margen para el paralaje).
W, H = 500, 303
RETALL = 23


def desar(s, nom, escala=1, retall=0):
    if retall:
        s = s.subsurface((0, retall, s.get_width(), s.get_height() - retall)).copy()
    if escala != 1:
        s = pygame.transform.scale(s, (s.get_width() * escala, s.get_height() * escala))
    pygame.image.save(s, os.path.join(IMG, nom))
    print("  ", nom, s.get_size())


def degradat(s, dalt, baix, y0=0, y1=None):
    y1 = s.get_height() if y1 is None else y1
    for y in range(y0, y1):
        k = (y - y0) / max(1, y1 - y0 - 1)
        pygame.draw.line(s, [int(dalt[i] + (baix[i] - dalt[i]) * k) for i in range(3)], (0, y), (s.get_width(), y))


def estrelles(s, rnd, n, y_max=None, colors=((255, 255, 255), (180, 200, 255), (255, 230, 200))):
    y_max = y_max or s.get_height()
    for _ in range(n):
        x, y = rnd.randrange(s.get_width()), rnd.randrange(y_max)
        c = rnd.choice(colors)
        if rnd.random() < 0.08:
            pygame.draw.line(s, c, (x - 1, y), (x + 1, y))
            pygame.draw.line(s, c, (x, y - 1), (x, y + 1))
        else:
            s.set_at((x, y), [int(v * rnd.uniform(0.4, 1)) for v in c])


def planeta_terra(s, cx, cy, r, rnd, nit_dreta=True):
    for i in range(6, 0, -1):
        pygame.draw.circle(s, (60 + 10 * i, 140 + 10 * i, 255), (cx, cy), r + i * 2, 1)
    pygame.draw.circle(s, (28, 84, 180), (cx, cy), r)
    capa = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    for _ in range(int(r * 0.6)):
        a = rnd.uniform(0, math.tau)
        d = rnd.uniform(0, r * 0.95)
        bx, by = cx + math.cos(a) * d, cy + math.sin(a) * d
        for _ in range(rnd.randint(2, 5)):
            pygame.draw.circle(capa, rnd.choice(((60, 140, 70), (85, 160, 75), (150, 135, 80))),
                               (int(bx + rnd.uniform(-8, 8)), int(by + rnd.uniform(-5, 5))), rnd.randint(2, 7))
    for _ in range(int(r * 0.25)):
        a = rnd.uniform(0, math.tau)
        d = rnd.uniform(0, r * 0.95)
        pygame.draw.ellipse(capa, (240, 245, 255, 200),
                            (cx + math.cos(a) * d, cy + math.sin(a) * d, rnd.randint(8, 22), 2))
    mascara = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(mascara, (255, 255, 255, 255), (cx, cy), r - 1)
    capa.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(capa, (0, 0))
    ombra = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    for x in range(cx - r, cx + r):
        k = (x - (cx - r)) / (2 * r)
        k = k if nit_dreta else 1 - k
        a = int(200 * max(0.0, (k - 0.45) / 0.55) ** 1.4)
        pygame.draw.line(ombra, (0, 0, 15, a), (x, cy - r), (x, cy + r))
    ombra.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(ombra, (0, 0))


# ---------------------------------------------------------------------------
# Sector 4: Òrbita i la Nau Mare
# ---------------------------------------------------------------------------
def fons_orbita():
    rnd = random.Random(41)
    s = pygame.Surface((W, H))
    degradat(s, (4, 6, 18), (16, 20, 46))
    estrelles(s, rnd, 260)
    planeta_terra(s, 70, 430, 270, rnd, nit_dreta=True)
    # lluna
    pygame.draw.circle(s, (170, 170, 180), (420, 64), 20)
    for _ in range(9):
        pygame.draw.circle(s, (130, 130, 142), (420 + rnd.randint(-14, 14), 64 + rnd.randint(-14, 14)), rnd.randint(2, 5))
    pygame.draw.circle(s, (210, 210, 220), (420, 64), 20, 1)
    # ombra de la Nau Mare a l'horitzó
    pygame.draw.ellipse(s, (22, 22, 38), (250, 96, 230, 50))
    pygame.draw.ellipse(s, (30, 30, 50), (320, 80, 90, 34))
    for i in range(14):
        s.set_at((265 + i * 15, 122), (255, 120, 80) if i % 3 else (120, 220, 255))
    # deixalles
    for _ in range(14):
        x, y = rnd.randint(0, W), rnd.randint(30, 250)
        w, h = rnd.randint(3, 10), rnd.randint(2, 4)
        pygame.draw.rect(s, rnd.choice(((80, 84, 100), (110, 110, 125), (60, 62, 80))), (x, y, w, h))
    return s


def fons_hangar():
    rnd = random.Random(42)
    s = pygame.Surface((W, H))
    s.fill((30, 32, 46))
    for x in range(0, W, 40):                                     # panells de paret
        pygame.draw.rect(s, (40, 43, 60), (x + 2, 0, 36, H))
        pygame.draw.line(s, (56, 60, 82), (x + 2, 0), (x + 2, H))
        pygame.draw.line(s, (18, 19, 28), (x + 38, 0), (x + 38, H))
        for y in range(14, H, 46):
            s.set_at((x + 6, y), (80, 85, 110))
            s.set_at((x + 34, y), (80, 85, 110))
    # finestral a l'espai amb plats volants aparcats
    fin = pygame.Rect(160, 46, 180, 104)
    pygame.draw.rect(s, (6, 8, 20), fin)
    estr = pygame.Surface(fin.size)
    estr.fill((6, 8, 20))
    estrelles(estr, rnd, 70)
    s.blit(estr, fin.topleft)
    for i, (ux, uy) in enumerate(((200, 106), (265, 80), (305, 122))):
        pygame.draw.ellipse(s, (60, 64, 90), (ux - 16, uy - 3, 32, 8))
        pygame.draw.ellipse(s, (90, 140, 180), (ux - 6, uy - 8, 12, 8))
        s.set_at((ux, uy + 4), (255, 200, 80))
    pygame.draw.rect(s, (74, 78, 102), fin, 5)
    pygame.draw.line(s, (74, 78, 102), (fin.centerx, fin.top), (fin.centerx, fin.bottom), 4)
    pygame.draw.rect(s, (110, 116, 145), fin, 1)
    # tires de llum morada
    for x in range(0, W, 8):
        pygame.draw.rect(s, (150, 70, 220) if (x // 8) % 2 else (190, 110, 255), (x, 28, 6, 3))
    glow = pygame.Surface((W, 20), pygame.SRCALPHA)
    for y in range(20):
        pygame.draw.line(glow, (170, 90, 255, int(70 * (1 - y / 20))), (0, y), (W, y))
    s.blit(glow, (0, 31))
    # canonades
    for y in (176, 188):
        pygame.draw.rect(s, (70, 72, 88), (0, y, W, 6))
        pygame.draw.line(s, (110, 112, 130), (0, y), (W, y))
        for x in range(20, W, 64):
            pygame.draw.rect(s, (95, 98, 118), (x, y - 1, 6, 8))
    # franja de perill i contenidors
    for x in range(-10, W, 16):
        pygame.draw.polygon(s, (200, 160, 40), [(x, 236), (x + 8, 236), (x + 14, 244), (x + 6, 244)])
    for cx, w, h, c in ((20, 46, 30, (70, 90, 70)), (74, 34, 20, (90, 80, 60)), (380, 60, 36, (110, 60, 50)), (440, 40, 22, (60, 70, 100))):
        pygame.draw.rect(s, c, (cx, 275 - h, w, h))
        pygame.draw.rect(s, [v + 30 for v in c], (cx, 275 - h, w, h), 1)
        for xx in range(cx + 6, cx + w - 2, 8):
            pygame.draw.line(s, [max(0, v - 20) for v in c], (xx, 277 - h), (xx, 273))
    return s


def fons_pont():
    rnd = random.Random(43)
    s = pygame.Surface((W, H))
    s.fill((20, 18, 30))
    fin = pygame.Rect(40, 40, 420, 150)
    vista = pygame.Surface(fin.size)
    degradat(vista, (2, 4, 14), (10, 14, 34))
    estrelles(vista, rnd, 110)
    planeta_terra(vista, 210, 320, 230, rnd, nit_dreta=False)
    s.blit(vista, fin.topleft)
    for x in range(fin.left, fin.right + 1, 70):                    # muntants de la finestra
        pygame.draw.polygon(s, (46, 40, 62), [(x - 5, fin.top), (x + 5, fin.top), (x + 3, fin.bottom), (x - 3, fin.bottom)])
    pygame.draw.rect(s, (52, 46, 70), fin, 6)
    pygame.draw.rect(s, (90, 80, 120), fin, 1)
    # consoles
    pygame.draw.polygon(s, (36, 32, 50), [(0, 214), (W, 214), (W, H), (0, H)])
    for x in range(10, W - 30, 54):
        pygame.draw.polygon(s, (54, 48, 76), [(x, 236), (x + 44, 236), (x + 40, 212), (x + 4, 212)])
        for _ in range(8):
            px, py = x + rnd.randint(8, 36), rnd.randint(216, 232)
            s.set_at((px, py), rnd.choice(((90, 255, 140), (255, 90, 90), (90, 220, 255), (255, 210, 80))))
        pygame.draw.rect(s, (20, 60, 70), (x + 10, 218, 24, 8))
        pygame.draw.line(s, (90, 230, 255), (x + 12, 222), (x + 30, 222))
    # llums d'alarma
    for x in (14, W - 22):
        pygame.draw.rect(s, (90, 20, 20), (x, 28, 8, 6))
        pygame.draw.rect(s, (255, 60, 60), (x + 2, 29, 4, 3))
    return s


# ---------------------------------------------------------------------------
# Sector 5: Xylos, el món rusc
# ---------------------------------------------------------------------------
def silueta_agulles(s, rnd, color, base, alt_max, n):
    for _ in range(n):
        x = rnd.randint(-10, W)
        w = rnd.randint(8, 22)
        h = rnd.randint(alt_max // 3, alt_max)
        pygame.draw.polygon(s, color, [(x, base), (x + w, base), (x + w // 2 + rnd.randint(-3, 3), base - h)])
        if rnd.random() < 0.6:
            pygame.draw.ellipse(s, color, (x + w // 2 - 7, base - h * 0.65, 14, 9))


def fons_xylos():
    rnd = random.Random(51)
    s = pygame.Surface((W, H))
    degradat(s, (40, 12, 70), (210, 90, 140), 0, 210)
    degradat(s, (210, 90, 140), (120, 40, 90), 210, H)
    estrelles(s, rnd, 50, y_max=90, colors=((255, 220, 255),))
    for cx, cy, r, c in ((380, 100, 30, (255, 170, 110)), (430, 62, 11, (255, 245, 210))):
        halo = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(8, 0, -1):
            pygame.draw.circle(halo, (*c, 18), (cx, cy), r + i * 4)
        s.blit(halo, (0, 0))
        pygame.draw.circle(s, c, (cx, cy), r)
    silueta_agulles(s, rnd, (130, 60, 120), 230, 120, 18)
    silueta_agulles(s, rnd, (90, 36, 96), 250, 150, 14)
    silueta_agulles(s, rnd, (52, 20, 64), 280, 120, 10)
    for _ in range(5):                                              # roques flotants amb cristalls
        x, y = rnd.randint(20, W - 40), rnd.randint(40, 150)
        pygame.draw.polygon(s, (70, 34, 80), [(x, y), (x + 28, y), (x + 20, y + 14), (x + 8, y + 12)])
        pygame.draw.polygon(s, (190, 120, 255), [(x + 10, y), (x + 14, y - 10), (x + 18, y)])
    return s


def fons_rusc():
    rnd = random.Random(52)
    s = pygame.Surface((W, H))
    degradat(s, (34, 18, 16), (58, 30, 20))
    r = 14
    for fila in range(-1, 14):
        for col in range(-1, 22):
            cx = col * r * 1.75 + (r * 0.87 if fila % 2 else 0)
            cy = fila * r * 1.5
            punts = [(cx + r * math.cos(math.pi / 6 + i * math.pi / 3), cy + r * math.sin(math.pi / 6 + i * math.pi / 3))
                     for i in range(6)]
            if rnd.random() < 0.12:
                pygame.draw.polygon(s, (200, 130, 40), punts)
                pygame.draw.circle(s, (255, 200, 90), (int(cx), int(cy)), 4)
            elif rnd.random() < 0.3:
                pygame.draw.polygon(s, (52, 28, 22), punts)
            pygame.draw.polygon(s, (96, 58, 28), punts, 2)
    for _ in range(9):                                              # venes
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        for _ in range(30):
            nx, ny = x + rnd.randint(-8, 8), y + rnd.randint(-2, 9)
            pygame.draw.line(s, (120, 40, 60), (x, y), (nx, ny), 2)
            x, y = nx, ny
    for x in (30, 450):                                             # columnes orgàniques
        pygame.draw.rect(s, (70, 40, 30), (x, 0, 18, H))
        for y in range(0, H, 12):
            pygame.draw.ellipse(s, (90, 52, 36), (x - 2, y, 22, 8))
    return s


def fons_nucli():
    rnd = random.Random(53)
    s = pygame.Surface((W, H))
    s.fill((10, 5, 18))
    cx, cy = 250, 120
    for i in range(60, 0, -1):
        pygame.draw.circle(s, (20 + i, 6 + i // 4, 40 + i * 2), (cx, cy), 160 - i * 2)
    for _ in range(26):                                             # venes que convergeixen al centre
        a = rnd.uniform(0, math.tau)
        x, y = cx + math.cos(a) * 260, cy + math.sin(a) * 260
        punts = [(x, y)]
        for k in range(18):
            x += (cx - x) * 0.12 + rnd.uniform(-6, 6)
            y += (cy - y) * 0.12 + rnd.uniform(-6, 6)
            punts.append((x, y))
        pygame.draw.lines(s, (150, 40, 170), False, punts, 3)
        pygame.draw.lines(s, (230, 110, 255), False, punts, 1)
    for x, h in ((22, 150), (52, 100), (430, 130), (462, 170)):     # pilars de cristall
        pygame.draw.polygon(s, (40, 160, 190), [(x, 275), (x + 16, 275), (x + 12, 275 - h), (x + 4, 275 - h - 14)])
        pygame.draw.line(s, (170, 250, 255), (x + 4, 270), (x + 5, 275 - h - 10))
    for r in (70, 96, 124):
        pygame.draw.circle(s, (120, 50, 150), (cx, cy), r, 1)
    return s


# ---------------------------------------------------------------------------
# Caps finals nous i enemic nou
# ---------------------------------------------------------------------------
def nau_mare():
    s = pygame.Surface((110, 54), pygame.SRCALPHA)
    pygame.draw.polygon(s, (70, 62, 96), [(2, 30), (24, 16), (86, 16), (108, 30), (86, 44), (24, 44)])
    pygame.draw.ellipse(s, (120, 110, 150), (0, 18, 110, 24))
    pygame.draw.ellipse(s, (76, 68, 104), (4, 30, 102, 16))
    pygame.draw.line(s, (170, 160, 200), (12, 22), (98, 22))
    pygame.draw.ellipse(s, (60, 30, 90), (36, 4, 38, 24))
    pygame.draw.ellipse(s, (160, 90, 230), (39, 6, 32, 20))
    for x in (46, 55, 64):                                          # siluetes al pont
        pygame.draw.ellipse(s, (60, 140, 80), (x - 2, 12, 5, 6))
    pygame.draw.line(s, (230, 200, 255), (43, 9), (50, 8))
    for x in (18, 55, 92):                                          # canons
        pygame.draw.circle(s, (40, 36, 56), (x, 42), 6)
        pygame.draw.circle(s, (200, 40, 60), (x, 43), 3)
    for x in range(8, 104, 8):
        s.set_at((x, 31), (120, 100, 70))
    pygame.draw.polygon(s, (90, 80, 120), [(0, 30), (10, 26), (10, 34)])
    pygame.draw.polygon(s, (90, 80, 120), [(110, 30), (100, 26), (100, 34)])
    return s


def nucli():
    s = pygame.Surface((76, 76), pygame.SRCALPHA)
    c = 38
    for i in range(10):                                             # punxes
        a = i * math.tau / 10
        p1 = (c + math.cos(a - 0.18) * 28, c + math.sin(a - 0.18) * 28)
        p2 = (c + math.cos(a + 0.18) * 28, c + math.sin(a + 0.18) * 28)
        p3 = (c + math.cos(a) * 37, c + math.sin(a) * 37)
        pygame.draw.polygon(s, (110, 50, 130), [p1, p2, p3])
        pygame.draw.line(s, (200, 120, 230), p1, p3)
    pygame.draw.circle(s, (64, 40, 84), (c, c), 30)
    for i in range(12):                                             # segments metàl·lics
        a = i * math.tau / 12
        pygame.draw.line(s, (40, 24, 56), (c + math.cos(a) * 24, c + math.sin(a) * 24),
                         (c + math.cos(a) * 30, c + math.sin(a) * 30), 2)
    pygame.draw.circle(s, (150, 90, 180), (c, c), 30, 1)
    pygame.draw.circle(s, (232, 216, 200), (c, c), 22)
    rnd = random.Random(9)
    for _ in range(9):                                              # venes de l'ull
        a = rnd.uniform(0, math.tau)
        x, y = c + math.cos(a) * 21, c + math.sin(a) * 21
        for _ in range(4):
            nx = x + (c - x) * 0.2 + rnd.uniform(-2, 2)
            ny = y + (c - y) * 0.2 + rnd.uniform(-2, 2)
            pygame.draw.line(s, (200, 70, 80), (x, y), (nx, ny))
            x, y = nx, ny
    pygame.draw.circle(s, (180, 150, 150), (c, c), 22, 1)
    return s


def cacador():
    s = pygame.Surface((22, 12), pygame.SRCALPHA)
    pygame.draw.polygon(s, (140, 200, 255, 120), [(6, 1), (12, 5), (4, 5)])          # ales
    pygame.draw.polygon(s, (140, 200, 255, 120), [(6, 11), (12, 7), (4, 7)])
    pygame.draw.polygon(s, (220, 120, 30), [(0, 6), (6, 2), (17, 4), (21, 6), (17, 8), (6, 10)])
    for x in (7, 10):
        pygame.draw.line(s, (60, 30, 10), (x, 3), (x, 9))
    pygame.draw.ellipse(s, (120, 230, 255), (13, 4, 5, 4))
    s.set_at((1, 6), (255, 240, 120))
    return s


# ---------------------------------------------------------------------------
# Armes noves del jugador (a partir del sprite de la pistola)
# ---------------------------------------------------------------------------
def soldat_sense_arma():
    base = pygame.image.load(os.path.join(IMG, "jugador_pistola.png")).convert_alpha()
    base = base.subsurface(base.get_bounding_rect()).copy()
    s = pygame.Surface((36, base.get_height()), pygame.SRCALPHA)
    s.blit(base, (0, 0))
    for x in range(15, 36):
        for y in range(11, 19):
            s.set_at((x, y), (0, 0, 0, 0))
    return s


def soldat_escopeta():
    s = soldat_sense_arma()
    pygame.draw.rect(s, (110, 70, 40), (12, 15, 5, 3))          # culata
    pygame.draw.rect(s, (66, 66, 66), (15, 13, 6, 4))           # recambra
    pygame.draw.rect(s, (97, 97, 97), (18, 13, 15, 2))          # canons
    pygame.draw.line(s, (117, 117, 117), (18, 13), (32, 13))
    pygame.draw.rect(s, (130, 85, 50), (21, 15, 6, 2))          # corredissa
    s.set_at((15, 16), (0, 0, 0))
    s.set_at((15, 17), (0, 0, 0))
    s.set_at((22, 16), (0, 0, 0))
    return s


def soldat_plasma():
    s = soldat_sense_arma()
    pygame.draw.rect(s, (63, 63, 64), (14, 12, 15, 5))          # cos
    pygame.draw.rect(s, (97, 97, 97), (15, 12, 12, 1))
    pygame.draw.line(s, (90, 230, 255), (17, 14), (27, 14))     # nucli de plasma
    pygame.draw.rect(s, (109, 109, 109), (29, 13, 3, 3))        # emissor
    s.set_at((32, 14), (180, 250, 255))
    pygame.draw.rect(s, (72, 72, 71), (18, 17, 3, 2))           # empunyadura
    s.set_at((15, 16), (0, 0, 0))
    s.set_at((15, 17), (0, 0, 0))
    return s



# ---------------------------------------------------------------------------
# Sectores 1, 2 y 3 (redibujados a partir de la idea original de Nacho y Abel)
# ---------------------------------------------------------------------------
def nuvols(s, rnd, n, color, y0, y1, mida=(18, 50)):
    for _ in range(n):
        x, y = rnd.randint(-20, W), rnd.randint(y0, y1)
        w = rnd.randint(*mida)
        for k in range(5):
            pygame.draw.ellipse(s, color, (x + k * w * 0.18, y - rnd.randint(0, w // 4), w * 0.5, w * 0.3))


def boira(s, y, alt, color, alfa):
    capa = pygame.Surface((W, alt), pygame.SRCALPHA)
    for k in range(alt):
        a = int(alfa * math.sin(math.pi * k / alt))
        pygame.draw.line(capa, (*color, a), (0, k), (W, k))
    s.blit(capa, (0, y))


def edifici(s, rnd, x, base, w, h, color, finestra, llum=0.25, danyat=0.0, forats=0):
    """Edificio con ventanas; `danyat` rompe el tejado y `forats` le hace agujeros de impactos."""
    top = base - h
    if danyat:
        punts = [(x, base), (x, top + rnd.randint(0, 8))]
        for k in range(1, 6):
            punts.append((x + w * k / 6, top + rnd.randint(0, int(30 * danyat))))
        punts += [(x + w, top + rnd.randint(0, 10)), (x + w, base)]
        pygame.draw.polygon(s, color, punts)
    else:
        pygame.draw.rect(s, color, (x, top, w, h))
    fosc = [max(0, c - 18) for c in color]
    clar = [min(255, c + 16) for c in color]
    pygame.draw.line(s, clar, (x, top + 6), (x, base))
    pygame.draw.line(s, fosc, (x + w - 1, top + 6), (x + w - 1, base))
    for fy in range(top + 12, base - 6, 10):
        for fx in range(x + 4, x + w - 5, 8):
            if fx + 4 >= W or fx < 0:
                continue
            if danyat and s.get_at((fx, fy - 4))[:3] != tuple(color):
                continue
            encesa = rnd.random() < llum
            c = finestra if encesa else fosc
            pygame.draw.rect(s, c, (fx, fy, 4, 5))
            if encesa:
                s.set_at((fx, fy), [min(255, v + 40) for v in finestra])
    for _ in range(forats):
        fx, fy = rnd.randint(x + 4, x + w - 10), rnd.randint(top + 10, base - 20)
        r = rnd.randint(3, 7)
        pygame.draw.circle(s, fosc, (fx, fy), r)
        pygame.draw.circle(s, [max(0, c - 40) for c in color], (fx, fy), r - 2)


def runa(s, rnd, base, n, colors):
    for _ in range(n):
        x = rnd.randint(-10, W)
        w, h = rnd.randint(8, 30), rnd.randint(4, 14)
        pygame.draw.polygon(s, rnd.choice(colors), [(x, base), (x + w * 0.3, base - h), (x + w * 0.7, base - h * 0.7), (x + w, base)])


def torre_alien(s, x, base, h, color, ull=(200, 80, 255)):
    pygame.draw.polygon(s, color, [(x - 10, base), (x - 4, base - h * 0.6), (x - 7, base - h), (x + 7, base - h),
                                   (x + 4, base - h * 0.6), (x + 10, base)])
    for k in range(4):
        y = base - h * 0.2 * (k + 1)
        pygame.draw.line(s, [min(255, c + 30) for c in color], (x - 8 + k, y), (x + 8 - k, y - 4))
    pygame.draw.circle(s, (40, 10, 50), (x, int(base - h)), 9)
    pygame.draw.circle(s, ull, (x, int(base - h)), 6)
    pygame.draw.circle(s, (255, 230, 255), (x - 1, int(base - h) - 1), 2)


def tentacles(s, rnd, x, y, n, color, llarg=40):
    for _ in range(n):
        a = rnd.uniform(0, math.tau)
        px, py = x, y
        for k in range(8):
            a += rnd.uniform(-0.5, 0.5)
            nx, ny = px + math.cos(a) * llarg / 8, py + math.sin(a) * llarg / 8
            pygame.draw.line(s, color, (px, py), (nx, ny), max(1, 4 - k // 2))
            px, py = nx, ny


def arbre_jungla(s, rnd, x, base, h, tronc, fulles, cables=None):
    pygame.draw.polygon(s, tronc, [(x - 6, base), (x - 3, base - h), (x + 3, base - h), (x + 6, base)])
    for _ in range(4):                                             # arrels
        pygame.draw.line(s, tronc, (x, base - 8), (x + rnd.randint(-16, 16), base), 3)
    for _ in range(9):
        cx = x + rnd.randint(-26, 26)
        cy = base - h + rnd.randint(-16, 12)
        pygame.draw.ellipse(s, rnd.choice(fulles), (cx - 18, cy - 9, 36, 18))
    if cables:
        for _ in range(3):
            y0 = base - rnd.randint(int(h * 0.3), h)
            pygame.draw.lines(s, cables, False, [(x, y0), (x + rnd.randint(-30, 30), y0 + rnd.randint(10, 30)),
                                                  (x + rnd.randint(-40, 40), y0 + rnd.randint(30, 60))], 1)
            s.set_at((x, y0), (120, 255, 200))


def pagoda(s, x, base, plantes, color_teulada, color_mur, ruina=False, rnd=None):
    amp = 60
    y = base
    for k in range(plantes):
        alt = 22
        w = amp - k * 10
        pygame.draw.rect(s, color_mur, (x - w // 2 + 6, y - alt, w - 12, alt))
        for fx in range(x - w // 2 + 10, x + w // 2 - 10, 7):
            pygame.draw.rect(s, (60, 30, 30), (fx, y - alt + 6, 3, 8))
        pygame.draw.polygon(s, color_teulada, [(x - w // 2 - 8, y - alt), (x + w // 2 + 8, y - alt),
                                               (x + w // 2 - 2, y - alt - 8), (x - w // 2 + 2, y - alt - 8)])
        pygame.draw.line(s, [min(255, c + 40) for c in color_teulada], (x - w // 2 - 8, y - alt), (x - w // 2 - 12, y - alt - 4))
        pygame.draw.line(s, [min(255, c + 40) for c in color_teulada], (x + w // 2 + 8, y - alt), (x + w // 2 + 12, y - alt - 4))
        y -= alt + 8
        if ruina and k == plantes - 2:
            break
    pygame.draw.line(s, color_teulada, (x, y), (x, y - 14), 2)


def fons_ciutat_dia():
    """1-1: barrio norte de día, con el puesto de vigilancia alienígena."""
    rnd = random.Random(101)
    s = pygame.Surface((W, H))
    degradat(s, (120, 170, 210), (210, 200, 180))
    nuvols(s, rnd, 7, (235, 238, 245), 20, 90)
    for _ in range(3):                                             # columnas de humo lejanas
        x = rnd.randint(30, W - 30)
        for k in range(12):
            pygame.draw.circle(s, (150, 150, 160), (x + k * 2 + rnd.randint(-3, 3), 190 - k * 12), 8 + k)
    for x in range(-10, W, 34):                                    # skyline lejano
        h = rnd.randint(60, 130)
        pygame.draw.rect(s, (150, 160, 180), (x, 240 - h, 30, h))
    boira(s, 150, 100, (220, 215, 205), 120)
    torre_alien(s, 420, 240, 150, (90, 40, 110))
    tentacles(s, rnd, 420, 238, 6, (110, 50, 130), 50)
    edifici(s, rnd, 10, 275, 70, 170, (200, 150, 100), (255, 230, 150), 0.15, danyat=0.6, forats=3)
    edifici(s, rnd, 90, 275, 60, 120, (180, 120, 90), (255, 230, 150), 0.1, danyat=0.9, forats=2)
    edifici(s, rnd, 160, 275, 80, 200, (215, 170, 110), (255, 230, 150), 0.2, danyat=0.4, forats=4)
    edifici(s, rnd, 255, 275, 50, 90, (170, 130, 100), (255, 230, 150), 0.1, danyat=1.0)
    edifici(s, rnd, 318, 275, 70, 130, (190, 140, 105), (255, 230, 150), 0.15, danyat=0.7, forats=3)
    edifici(s, rnd, 434, 275, 60, 150, (200, 160, 120), (255, 230, 150), 0.15, danyat=0.5, forats=2)
    runa(s, rnd, 276, 26, ((120, 100, 90), (150, 130, 110), (100, 84, 80)))
    pygame.draw.rect(s, (160, 40, 40), (250, 262, 26, 10))                     # coche volcado
    pygame.draw.circle(s, (30, 30, 30), (256, 262), 4)
    pygame.draw.circle(s, (30, 30, 30), (270, 262), 4)
    pygame.draw.line(s, (60, 60, 70), (226, 276), (238, 236), 2)                # farola doblada
    pygame.draw.line(s, (60, 60, 70), (238, 236), (252, 232), 2)
    return s


def fons_ciutat_pluja():
    """1-2: las ruinas bajo la lluvia, al atardecer."""
    rnd = random.Random(102)
    s = pygame.Surface((W, H))
    degradat(s, (30, 44, 64), (90, 110, 120))
    nuvols(s, rnd, 14, (50, 62, 80), 0, 70, (30, 70))
    for x in range(-10, W, 26):
        h = rnd.randint(70, 150)
        pygame.draw.rect(s, (54, 66, 84), (x, 250 - h, 24, h))
    boira(s, 170, 90, (110, 130, 140), 110)
    colors = [(70, 84, 96), (62, 74, 90), (78, 90, 100)]
    x = -5
    while x < W:
        w = rnd.randint(40, 70)
        edifici(s, rnd, x, 275, w, rnd.randint(100, 210), rnd.choice(colors), (255, 210, 120), 0.18,
                danyat=rnd.uniform(0.2, 0.9), forats=rnd.randint(0, 3))
        x += w + rnd.randint(4, 14)
    # letrero de neón
    pygame.draw.rect(s, (20, 20, 30), (120, 150, 46, 14))
    for k, c in enumerate(((255, 60, 120), (255, 60, 120), (80, 230, 255))):
        pygame.draw.rect(s, c, (124 + k * 14, 154, 10, 6), 1)
    # charcos con reflejos
    for _ in range(8):
        x = rnd.randint(0, W - 40)
        pygame.draw.ellipse(s, (120, 150, 170), (x, 268 + rnd.randint(0, 6), rnd.randint(20, 46), 4))
    for _ in range(140):
        x, y = rnd.randint(0, W), rnd.randint(0, 270)
        pygame.draw.line(s, (130, 150, 170), (x, y), (x - 2, y + 6))
    return s


def fons_ciutat_nit():
    """1-3: el centro de la ciudad convertido en base del General, de noche."""
    rnd = random.Random(103)
    s = pygame.Surface((W, H))
    degradat(s, (8, 6, 24), (50, 20, 60))
    estrelles(s, rnd, 120, y_max=150)
    aurora = pygame.Surface((W, 120), pygame.SRCALPHA)               # aurora violeta del portal
    for x in range(W):
        y = 40 + math.sin(x * 0.03) * 18
        pygame.draw.line(aurora, (170, 80, 255, 50), (x, y - 20), (x, y + 30))
    s.blit(aurora, (0, 10))
    for x in range(-10, W, 30):
        h = rnd.randint(80, 160)
        pygame.draw.rect(s, (30, 20, 46), (x, 260 - h, 28, h))
    # cúpula de la colmena en el centro
    pygame.draw.ellipse(s, (70, 30, 90), (180, 150, 140, 130))
    for k in range(6):
        pygame.draw.arc(s, (120, 60, 150), (188 + k * 4, 156 + k * 6, 124 - k * 8, 120), 0.2, 2.9, 2)
    for _ in range(14):
        x, y = rnd.randint(190, 310), rnd.randint(160, 260)
        pygame.draw.circle(s, (255, 120, 220), (x, y), 3)
        pygame.draw.circle(s, (255, 220, 250), (x, y), 1)
    for x, h in ((20, 190), (100, 140), (372, 170), (440, 210)):
        edifici(s, rnd, x, 275, 50, h, (40, 34, 56), (255, 150, 80), 0.12, danyat=0.8, forats=3)
        tentacles(s, rnd, x + 25, 275 - h + 20, 5, (120, 50, 150), 60)
    for x in (85, 345):
        torre_alien(s, x, 275, 120, (80, 30, 100), (255, 80, 160))
    runa(s, rnd, 276, 20, ((50, 40, 60), (70, 50, 70)))
    for x in (10, 480):                                            # incendios (las chispas las anima el juego)
        for k in range(10):
            pygame.draw.circle(s, rnd.choice(((255, 120, 30), (255, 200, 60), (230, 60, 20))),
                               (x + rnd.randint(-12, 12), 270 - rnd.randint(0, 30)), rnd.randint(3, 8))
    return s


def fons_selva_dia():
    """2-1: la Selva Tecnológica, con una pagoda en ruinas devorada por la máquina."""
    rnd = random.Random(201)
    s = pygame.Surface((W, H))
    degradat(s, (110, 200, 190), (210, 240, 200))
    for x in range(-20, W, 30):                                    # bosque lejano
        pygame.draw.ellipse(s, (90, 160, 140), (x, 150 + rnd.randint(-10, 10), 50, 80))
    boira(s, 170, 70, (230, 250, 240), 140)
    pagoda(s, 380, 270, 4, (40, 120, 70), (190, 80, 60), ruina=True)
    for _ in range(5):                                             # cables que trepan por la pagoda
        pygame.draw.lines(s, (40, 60, 70), False, [(rnd.randint(350, 410), 270), (rnd.randint(360, 400), 200),
                                                    (rnd.randint(365, 395), 160)], 2)
    for x, h in ((40, 200), (130, 160), (215, 220), (300, 170), (472, 190)):
        arbre_jungla(s, rnd, x, 275, h, (70, 50, 40), ((40, 130, 60), (60, 160, 70), (30, 110, 60)), (50, 70, 80))
    for _ in range(12):                                            # setas luminosas
        x = rnd.randint(0, W)
        pygame.draw.rect(s, (220, 220, 200), (x, 266, 2, 8))
        pygame.draw.ellipse(s, rnd.choice(((120, 255, 200), (255, 120, 220))), (x - 4, 262, 10, 6))
    # cascada
    pygame.draw.rect(s, (200, 240, 255), (258, 120, 10, 150))
    for y in range(120, 270, 6):
        pygame.draw.line(s, (255, 255, 255), (259, y), (259, y + 3))
    return s


def fons_selva_laboratori():
    """2-2: el laboratorio alienígena escondido en la selva, bajo la lluvia."""
    rnd = random.Random(202)
    s = pygame.Surface((W, H))
    degradat(s, (40, 70, 70), (80, 110, 100))
    for x in range(-20, W, 26):
        pygame.draw.ellipse(s, (40, 80, 70), (x, 110 + rnd.randint(-10, 20), 46, 120))
    boira(s, 140, 80, (120, 150, 140), 100)
    # módulo del laboratorio
    pygame.draw.rect(s, (60, 70, 80), (80, 120, 340, 155))
    pygame.draw.rect(s, (90, 100, 110), (80, 120, 340, 155), 2)
    pygame.draw.ellipse(s, (70, 80, 92), (80, 90, 340, 60))
    for k, x in enumerate(range(105, 400, 50)):                     # tanques con criaturas
        pygame.draw.rect(s, (30, 40, 50), (x, 160, 34, 100))
        liq = (60, 220, 140) if k % 2 == 0 else (190, 90, 230)
        pygame.draw.rect(s, liq, (x + 3, 166, 28, 90))
        pygame.draw.ellipse(s, [c // 2 for c in liq], (x + 8, 190, 18, 26))
        pygame.draw.circle(s, (255, 255, 200), (x + 13, 198), 2)
        pygame.draw.rect(s, (140, 150, 160), (x, 160, 34, 100), 1)
        for b in range(4):
            s.set_at((x + 6 + b * 6, 240 - b * 14), (230, 255, 240))
    for y in (132, 144):                                           # tuberías
        pygame.draw.line(s, (110, 120, 130), (80, y), (420, y), 3)
    pygame.draw.rect(s, (255, 200, 40), (230, 124, 40, 8))         # señal de peligro
    for x in range(234, 268, 8):
        pygame.draw.line(s, (20, 20, 20), (x, 131), (x + 4, 124), 2)
    for x, h in ((20, 200), (472, 210)):
        arbre_jungla(s, rnd, x, 275, h, (50, 40, 34), ((30, 90, 60), (40, 110, 70)), (40, 60, 70))
    for _ in range(160):
        x, y = rnd.randint(0, W), rnd.randint(0, 270)
        pygame.draw.line(s, (120, 150, 150), (x, y), (x - 2, y + 6))
    return s


def fons_selva_cor():
    """2-3: el corazón de la selva en llamas, guarida del Maestro de la Selva."""
    rnd = random.Random(203)
    s = pygame.Surface((W, H))
    degradat(s, (10, 10, 20), (60, 24, 30))
    estrelles(s, rnd, 50, y_max=100)
    # árbol-máquina gigante
    pygame.draw.polygon(s, (50, 36, 40), [(200, 275), (225, 120), (275, 120), (300, 275)])
    for k in range(7):
        a = -math.pi / 2 + (k - 3) * 0.35
        pygame.draw.line(s, (50, 36, 40), (250, 125), (250 + math.cos(a) * 160, 125 + math.sin(a) * 90), 6)
    pygame.draw.ellipse(s, (40, 70, 50), (90, 32, 320, 112))
    for _ in range(30):
        pygame.draw.ellipse(s, rnd.choice(((30, 60, 44), (50, 90, 60))), (rnd.randint(90, 370), rnd.randint(34, 116), 40, 20))
    pygame.draw.circle(s, (120, 255, 160), (250, 190), 16)          # núcleo del árbol
    pygame.draw.circle(s, (220, 255, 230), (250, 190), 7)
    for k in range(8):
        a = k * math.tau / 8
        pygame.draw.line(s, (90, 220, 140), (250, 190), (250 + math.cos(a) * 34, 190 + math.sin(a) * 34), 1)
    for x in (30, 100, 400, 470):                                  # árboles en llamas
        arbre_jungla(s, rnd, x, 275, rnd.randint(140, 200), (30, 22, 20), ((60, 30, 20), (90, 40, 20)))
        for k in range(14):
            pygame.draw.circle(s, rnd.choice(((255, 120, 30), (255, 200, 60), (230, 60, 20))),
                               (x + rnd.randint(-20, 20), 275 - rnd.randint(40, 170)), rnd.randint(3, 7))
    runa(s, rnd, 276, 16, ((40, 30, 30), (60, 40, 34)))
    return s


def fons_fortalesa_muralla():
    """3-1: las murallas exteriores de la fortaleza, con su cohete en la rampa."""
    rnd = random.Random(301)
    s = pygame.Surface((W, H))
    degradat(s, (60, 70, 110), (220, 140, 120))
    for k, (col, alt) in enumerate((((90, 90, 120), 120), ((70, 66, 96), 80))):     # montañas
        punts = [(0, 230)]
        x = 0
        while x < W:
            x += rnd.randint(30, 60)
            punts.append((x, 230 - rnd.randint(alt // 2, alt)))
        punts += [(W, 230), (W, H), (0, H)]
        pygame.draw.polygon(s, col, punts)
    # muralla
    pygame.draw.rect(s, (52, 50, 66), (0, 160, W, 120))
    for x in range(0, W, 24):
        pygame.draw.rect(s, (62, 60, 78), (x + 1, 162, 22, 116))
        pygame.draw.rect(s, (52, 50, 66), (x, 150, 12, 12))
    pygame.draw.line(s, (90, 240, 255), (0, 158), (W, 158), 2)     # barrera de energía
    barrera = pygame.Surface((W, 30), pygame.SRCALPHA)
    for k in range(30):
        pygame.draw.line(barrera, (90, 240, 255, int(60 * (1 - k / 30))), (0, 158 - k), (W, 158 - k))
    s.blit(barrera, (0, 128))
    for x in (40, 460):                                            # torres con reflector
        pygame.draw.rect(s, (44, 42, 58), (x - 12, 90, 24, 190))
        pygame.draw.rect(s, (70, 66, 90), (x - 16, 84, 32, 10))
        pygame.draw.circle(s, (255, 250, 200), (x, 82), 5)
    # puerta del hangar
    pygame.draw.rect(s, (30, 30, 40), (190, 200, 100, 76))
    for y in range(204, 276, 8):
        pygame.draw.line(s, (50, 50, 64), (192, y), (288, y))
    for x in range(190, 290, 12):
        pygame.draw.polygon(s, (220, 180, 40), [(x, 196), (x + 6, 196), (x + 10, 200), (x + 4, 200)])
    # cohete en la rampa (como en el escenario original)
    pygame.draw.rect(s, (90, 90, 100), (360, 120, 6, 156))
    pygame.draw.rect(s, (200, 200, 210), (370, 140, 22, 110))
    pygame.draw.polygon(s, (190, 40, 50), [(370, 140), (381, 112), (392, 140)])
    pygame.draw.polygon(s, (190, 40, 50), [(370, 230), (360, 256), (370, 250)])
    pygame.draw.polygon(s, (190, 40, 50), [(392, 230), (402, 256), (392, 250)])
    pygame.draw.circle(s, (90, 200, 255), (381, 165), 5)
    return s


def fons_fortalesa_pati():
    """3-2: el patio interior, con el suelo de baldosas de energía (homenaje al tablero original)."""
    s = pygame.Surface((W, H))
    degradat(s, (20, 14, 34), (60, 30, 80))
    # paredes con arcos
    for x in range(0, W, 66):
        pygame.draw.rect(s, (46, 30, 64), (x, 40, 60, 160))
        pygame.draw.ellipse(s, (24, 14, 36), (x + 10, 70, 40, 60))
        pygame.draw.rect(s, (24, 14, 36), (x + 10, 100, 40, 100))
        for k in range(5):
            s.set_at((x + 30, 60 + k * 4), (220, 120, 255))
    # suelo de baldosas en perspectiva
    horitzo, base = 200, H
    for fila in range(10):
        y0 = horitzo + (base - horitzo) * (fila / 10) ** 1.6
        y1 = horitzo + (base - horitzo) * ((fila + 1) / 10) ** 1.6
        for col in range(-11, 12):
            def px(c, y):
                return W / 2 + c * 30 * (0.35 + 0.65 * (y - horitzo) / (base - horitzo)) * 1.6
            punts = [(px(col, y0), y0), (px(col + 1, y0), y0), (px(col + 1, y1), y1), (px(col, y1), y1)]
            color = (70, 110, 160) if (fila + col) % 2 else (34, 26, 52)
            pygame.draw.polygon(s, color, punts)
    # obeliscos con runas
    for x in (80, 420):
        pygame.draw.polygon(s, (30, 22, 46), [(x - 14, 240), (x - 8, 70), (x, 56), (x + 8, 70), (x + 14, 240)])
        for k in range(6):
            pygame.draw.rect(s, (200, 110, 255), (x - 3, 90 + k * 22, 6, 8))
    # conductos de energía
    for y in (36, 206):
        pygame.draw.line(s, (90, 230, 255), (0, y), (W, y), 2)
    return s


def fons_fortalesa_cim():
    """3-3: la cima nevada de la fortaleza, con el trono del Comandante Supremo."""
    rnd = random.Random(303)
    s = pygame.Surface((W, H))
    degradat(s, (6, 8, 20), (40, 40, 70))
    estrelles(s, rnd, 80, y_max=120)
    nuvols(s, rnd, 10, (30, 32, 56), 10, 90, (40, 80))
    # anillo del portal detrás del trono
    for r, c in ((70, (90, 40, 140)), (62, (170, 80, 255)), (56, (60, 20, 100))):
        pygame.draw.circle(s, c, (250, 140), r, 4)
    halo = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.circle(halo, (170, 80, 255, 40), (250, 140), 54)
    s.blit(halo, (0, 0))
    # trono / plataforma
    pygame.draw.polygon(s, (50, 50, 70), [(200, 260), (220, 220), (280, 220), (300, 260)])
    pygame.draw.rect(s, (70, 70, 96), (226, 180, 48, 42))
    pygame.draw.polygon(s, (70, 70, 96), [(226, 180), (250, 150), (274, 180)])
    # torres de tejado rojo (como en el original)
    for x in (50, 450):
        pygame.draw.rect(s, (110, 110, 120), (x - 16, 90, 32, 190))
        for y in range(100, 270, 16):
            pygame.draw.rect(s, (60, 60, 70), (x - 4, y, 8, 8))
        pygame.draw.polygon(s, (170, 40, 40), [(x - 22, 92), (x, 30), (x + 22, 92)])
        pygame.draw.line(s, (220, 80, 70), (x - 22, 92), (x, 30))
    # nieve
    pygame.draw.rect(s, (230, 236, 250), (0, 255, W, H - 255))
    for x in range(0, W, 14):
        pygame.draw.ellipse(s, (240, 244, 255), (x, 250 + rnd.randint(-2, 2), 20, 10))
    for x in (140, 360):                                           # braseros
        pygame.draw.rect(s, (60, 50, 50), (x - 6, 238, 12, 16))
        for k in range(8):
            pygame.draw.circle(s, rnd.choice(((255, 120, 30), (255, 200, 60))), (x + rnd.randint(-5, 5), 234 - rnd.randint(0, 12)), 3)
    return s


if __name__ == "__main__":
    print("Generant fons:")
    for nom, f in (("fons_nivell_0_0.png", fons_ciutat_dia), ("fons_nivell_0_1.png", fons_ciutat_pluja),
                   ("fons_nivell_0_2.png", fons_ciutat_nit), ("fons_nivell_1_0.png", fons_selva_dia),
                   ("fons_nivell_1_1.png", fons_selva_laboratori), ("fons_nivell_1_2.png", fons_selva_cor),
                   ("fons_nivell_2_0.png", fons_fortalesa_muralla), ("fons_nivell_2_1.png", fons_fortalesa_pati),
                   ("fons_nivell_2_2.png", fons_fortalesa_cim),
                   ("fons_nivell_3_0.png", fons_orbita), ("fons_nivell_3_1.png", fons_hangar),
                   ("fons_nivell_3_2.png", fons_pont), ("fons_nivell_4_0.png", fons_xylos),
                   ("fons_nivell_4_1.png", fons_rusc), ("fons_nivell_4_2.png", fons_nucli)):
        desar(f(), nom, 2, RETALL)
    print("Generant personatges:")
    desar(nau_mare(), "boss_nau_mare.png")
    desar(nucli(), "boss_nucli.png")
    desar(cacador(), "enemic_cacador.png")
    desar(soldat_escopeta(), "jugador_escopeta.png")
    desar(soldat_plasma(), "jugador_plasma.png")
