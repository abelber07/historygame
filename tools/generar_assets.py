"""
Genera el pixel art nou del joc (fons dels sectors 4 i 5, caps finals, caçador i armes noves).

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
W, H = 400, 300   # els fons es dibuixen a la meitat i s'escalen a 800x600


def desar(s, nom, escala=1):
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
    pygame.draw.circle(s, (170, 170, 180), (330, 58), 20)
    for _ in range(9):
        pygame.draw.circle(s, (130, 130, 142), (330 + rnd.randint(-14, 14), 58 + rnd.randint(-14, 14)), rnd.randint(2, 5))
    pygame.draw.circle(s, (210, 210, 220), (330, 58), 20, 1)
    # ombra de la Nau Mare a l'horitzó
    pygame.draw.ellipse(s, (22, 22, 38), (190, 92, 230, 50))
    pygame.draw.ellipse(s, (30, 30, 50), (250, 76, 90, 34))
    for i in range(14):
        s.set_at((205 + i * 15, 118), (255, 120, 80) if i % 3 else (120, 220, 255))
    # deixalles
    for _ in range(14):
        x, y = rnd.randint(0, W), rnd.randint(20, 240)
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
    fin = pygame.Rect(110, 36, 180, 104)
    pygame.draw.rect(s, (6, 8, 20), fin)
    estr = pygame.Surface(fin.size)
    estr.fill((6, 8, 20))
    estrelles(estr, rnd, 70)
    s.blit(estr, fin.topleft)
    for i, (ux, uy) in enumerate(((150, 96), (215, 70), (255, 112))):
        pygame.draw.ellipse(s, (60, 64, 90), (ux - 16, uy - 3, 32, 8))
        pygame.draw.ellipse(s, (90, 140, 180), (ux - 6, uy - 8, 12, 8))
        s.set_at((ux, uy + 4), (255, 200, 80))
    pygame.draw.rect(s, (74, 78, 102), fin, 5)
    pygame.draw.line(s, (74, 78, 102), (fin.centerx, fin.top), (fin.centerx, fin.bottom), 4)
    pygame.draw.rect(s, (110, 116, 145), fin, 1)
    # tires de llum morada
    for x in range(0, W, 8):
        pygame.draw.rect(s, (150, 70, 220) if (x // 8) % 2 else (190, 110, 255), (x, 14, 6, 3))
    glow = pygame.Surface((W, 20), pygame.SRCALPHA)
    for y in range(20):
        pygame.draw.line(glow, (170, 90, 255, int(70 * (1 - y / 20))), (0, y), (W, y))
    s.blit(glow, (0, 17))
    # canonades
    for y in (176, 188):
        pygame.draw.rect(s, (70, 72, 88), (0, y, W, 6))
        pygame.draw.line(s, (110, 112, 130), (0, y), (W, y))
        for x in range(20, W, 64):
            pygame.draw.rect(s, (95, 98, 118), (x, y - 1, 6, 8))
    # franja de perill i contenidors
    for x in range(-10, W, 16):
        pygame.draw.polygon(s, (200, 160, 40), [(x, 236), (x + 8, 236), (x + 14, 244), (x + 6, 244)])
    for cx, w, h, c in ((20, 46, 30, (70, 90, 70)), (300, 60, 36, (110, 60, 50)), (350, 40, 22, (60, 70, 100))):
        pygame.draw.rect(s, c, (cx, 275 - h, w, h))
        pygame.draw.rect(s, [v + 30 for v in c], (cx, 275 - h, w, h), 1)
        for xx in range(cx + 6, cx + w - 2, 8):
            pygame.draw.line(s, [max(0, v - 20) for v in c], (xx, 277 - h), (xx, 273))
    return s


def fons_pont():
    rnd = random.Random(43)
    s = pygame.Surface((W, H))
    s.fill((20, 18, 30))
    fin = pygame.Rect(30, 26, 340, 160)
    vista = pygame.Surface(fin.size)
    degradat(vista, (2, 4, 14), (10, 14, 34))
    estrelles(vista, rnd, 110)
    planeta_terra(vista, 170, 330, 230, rnd, nit_dreta=False)
    s.blit(vista, fin.topleft)
    for x in range(fin.left, fin.right + 1, 68):                    # muntants de la finestra
        pygame.draw.polygon(s, (46, 40, 62), [(x - 5, fin.top), (x + 5, fin.top), (x + 3, fin.bottom), (x - 3, fin.bottom)])
    pygame.draw.rect(s, (52, 46, 70), fin, 6)
    pygame.draw.rect(s, (90, 80, 120), fin, 1)
    # consoles
    pygame.draw.polygon(s, (36, 32, 50), [(0, 214), (W, 214), (W, 300), (0, 300)])
    for x in range(10, W - 30, 54):
        pygame.draw.polygon(s, (54, 48, 76), [(x, 236), (x + 44, 236), (x + 40, 212), (x + 4, 212)])
        for _ in range(8):
            px, py = x + rnd.randint(8, 36), rnd.randint(216, 232)
            s.set_at((px, py), rnd.choice(((90, 255, 140), (255, 90, 90), (90, 220, 255), (255, 210, 80))))
        pygame.draw.rect(s, (20, 60, 70), (x + 10, 218, 24, 8))
        pygame.draw.line(s, (90, 230, 255), (x + 12, 222), (x + 30, 222))
    # llums d'alarma
    for x in (14, W - 22):
        pygame.draw.rect(s, (90, 20, 20), (x, 8, 8, 6))
        pygame.draw.rect(s, (255, 60, 60), (x + 2, 9, 4, 3))
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
    for cx, cy, r, c in ((300, 96, 30, (255, 170, 110)), (348, 58, 11, (255, 245, 210))):
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
        for col in range(-1, 18):
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
    for x in (30, 360):                                             # columnes orgàniques
        pygame.draw.rect(s, (70, 40, 30), (x, 0, 18, H))
        for y in range(0, H, 12):
            pygame.draw.ellipse(s, (90, 52, 36), (x - 2, y, 22, 8))
    return s


def fons_nucli():
    rnd = random.Random(53)
    s = pygame.Surface((W, H))
    s.fill((10, 5, 18))
    cx, cy = 200, 110
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
    for x, h in ((22, 150), (52, 100), (340, 130), (372, 170)):     # pilars de cristall
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


if __name__ == "__main__":
    print("Generant fons:")
    for nom, f in (("fons_nivell_3_0.png", fons_orbita), ("fons_nivell_3_1.png", fons_hangar),
                   ("fons_nivell_3_2.png", fons_pont), ("fons_nivell_4_0.png", fons_xylos),
                   ("fons_nivell_4_1.png", fons_rusc), ("fons_nivell_4_2.png", fons_nucli)):
        desar(f(), nom, 2)
    print("Generant personatges:")
    desar(nau_mare(), "boss_nau_mare.png")
    desar(nucli(), "boss_nucli.png")
    desar(cacador(), "enemic_cacador.png")
    desar(soldat_escopeta(), "jugador_escopeta.png")
    desar(soldat_plasma(), "jugador_plasma.png")
