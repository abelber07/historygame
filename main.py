"""
Joc Militar: Invasió Alienígena
Versió millorada, compatible amb escriptori i navegador (pygbag / GitHub Pages).

Escriptori:  python main.py
Navegador:   pygbag .        (o el workflow de GitHub Actions del repositori)
"""
import asyncio
import json
import math
import os
import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Configuració general
# ---------------------------------------------------------------------------
WEB = sys.platform == "emscripten"
BASE = os.path.dirname(os.path.abspath(__file__))

WIDTH, HEIGHT = 800, 600
FPS = 60
TERRA_Y = HEIGHT - 50          # alçada (y) de la part superior del terra
VIDA_MAX = 100

FONS = (18, 20, 38)
NEGRE = (8, 8, 16)
BLANC = (255, 255, 255)
GRIS = (120, 122, 140)
GRIS_FOSC = (48, 50, 72)
VERMELL = (235, 64, 64)
VERMELL_FOSC = (110, 20, 32)
VERD = (80, 220, 120)
BLAU = (52, 104, 214)
BLAU_CLAR = (120, 180, 255)
GROC = (255, 214, 64)
TARONJA = (255, 150, 40)
MORAT = (190, 90, 255)
ROSA = (255, 80, 200)
CIAN = (90, 230, 255)


def ruta(*parts):
    return os.path.join(BASE, "assets", *parts)


try:
    pygame.mixer.pre_init(44100, -16, 2, 512)
except Exception:
    pass
pygame.init()

AUDIO_OK = True
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.set_num_channels(24)
    pygame.mixer.set_reserved(1)      # canal 0: trets del jugador
except pygame.error as err:
    print(f"Àudio no disponible: {err}")
    AUDIO_OK = False

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Joc Militar: Invasió Alienígena")


# ---------------------------------------------------------------------------
# Recursos (cada recurs es carrega per separat: si en falla un, la resta funciona)
# ---------------------------------------------------------------------------
def carregar_font(nom, mida):
    try:
        return pygame.font.Font(ruta("fonts", nom), mida)
    except (OSError, pygame.error):
        return pygame.font.Font(None, int(mida * 1.5))


F_TITOL = carregar_font("VT323-Regular.ttf", 68)        # la VT323 té bones majúscules accentuades
F_SUBTITOL = carregar_font("VT323-Regular.ttf", 44)
F_GRAN = carregar_font("PressStart2P-Regular.ttf", 20)
F_UI = carregar_font("PressStart2P-Regular.ttf", 14)
F_HUD = carregar_font("PressStart2P-Regular.ttf", 12)
F_MINI = carregar_font("PressStart2P-Regular.ttf", 9)
F_TEXT = carregar_font("VT323-Regular.ttf", 32)
F_TEXT_P = carregar_font("VT323-Regular.ttf", 26)


def carregar_imatge(nom, alpha=True):
    try:
        img = pygame.image.load(ruta("img", nom))
        return img.convert_alpha() if alpha else img.convert()
    except (OSError, pygame.error) as err:
        print(f"No s'ha pogut carregar {nom}: {err}")
        return None


def escalar(img, factor=None, mida=None):
    if img is None:
        return None
    if mida is None:
        mida = (max(1, round(img.get_width() * factor)), max(1, round(img.get_height() * factor)))
    return pygame.transform.scale(img, mida)


def retallar(img):
    """Elimina els marges transparents d'un sprite."""
    if img is None:
        return None
    return img.subsurface(img.get_bounding_rect()).copy()


def permutar_canals(img, ordre):
    """Crea una variant de color intercanviant els canals RGB (per diferenciar caps)."""
    if img is None:
        return None
    nova = img.copy()
    nova.lock()
    w, h = nova.get_size()
    for x in range(w):
        for y in range(h):
            c = nova.get_at((x, y))
            if c.a:
                rgb = (c.r, c.g, c.b)
                nova.set_at((x, y), (rgb[ordre[0]], rgb[ordre[1]], rgb[ordre[2]], c.a))
    nova.unlock()
    return nova


def silueta_blanca(img):
    if img is None:
        return None
    s = img.copy()
    s.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    return s


def centre_peus(img):
    """Posició x mitjana dels píxels opacs de la part inferior (on són les cames)."""
    w, h = img.get_size()
    xs = [x for y in range(int(h * 0.75), h) for x in range(w) if img.get_at((x, y)).a]
    return sum(xs) / len(xs) if xs else w / 2


# Jugador (s'escala x2 amb proporcions correctes i es guarda també la versió girada)
SPR_JUGADOR = {}
for _nom, _fitxer in (("Pistola", "jugador_pistola.png"),
                      ("Fusell", "jugador_fusell.png"),
                      ("Minigun", "jugador_minigun.png")):
    _img = escalar(retallar(carregar_imatge(_fitxer)), 2)
    if _img:
        _cx = centre_peus(_img)
        SPR_JUGADOR[_nom] = {
            1: (_img, _cx),
            -1: (pygame.transform.flip(_img, True, False), _img.get_width() - _cx),
        }

_dron = retallar(carregar_imatge("enemic.png"))
_boss = retallar(carregar_imatge("enemic_boss.png"))
SPR_ENEMIC = {
    "dron": escalar(_dron, 1.5),
    "lloctinent": escalar(permutar_canals(_dron, (2, 1, 0)), 2.0),
    ("boss", 0): escalar(_boss, mida=(84, 84)) if _boss else None,
    ("boss", 1): escalar(permutar_canals(_boss, (0, 2, 1)), mida=(90, 90)) if _boss else None,
    ("boss", 2): escalar(permutar_canals(_boss, (2, 1, 0)), mida=(96, 96)) if _boss else None,
    "boss_final": escalar(retallar(carregar_imatge("enemic_boss_final.png")), 0.8),
}
SPR_ENEMIC_BLANC = {k: silueta_blanca(v) for k, v in SPR_ENEMIC.items()}

FONS_NIVELLS = {}
for _n in range(3):
    for _e in range(3):
        _f = carregar_imatge(f"fons_nivell_{_n}_{_e}.png", alpha=False)
        FONS_NIVELLS[(_n, _e)] = escalar(_f, mida=(WIDTH, HEIGHT)) if _f else None

_logo = carregar_imatge("logo.png")
LOGO = escalar(_logo, 300 / _logo.get_height()) if _logo else None


class Audio:
    """Efectes amb pygame.mixer.Sound i música en streaming amb pygame.mixer.music."""

    VOLUMS = {
        "click": 0.6, "pistola": 0.55, "fusell": 0.5, "minigun": 0.35, "enemic": 0.45,
        "boss": 0.5, "impacte": 0.45, "eliminat": 0.8, "item": 0.6, "moneda": 0.5,
        "buit": 0.7, "ferit": 0.7,
    }
    VOL_MUSICA = 0.45

    def __init__(self):
        self.sons = {}
        self.musica_actual = None
        self.silenci = False
        self.ultim = {}
        if not AUDIO_OK:
            return
        for nom, vol in self.VOLUMS.items():
            try:
                so = pygame.mixer.Sound(ruta("so", nom + ".ogg"))
                so.set_volume(vol)
                self.sons[nom] = so
            except (OSError, pygame.error) as err:
                print(f"No s'ha pogut carregar el so {nom}: {err}")

    def so(self, nom, interval_ms=0):
        if self.silenci or nom not in self.sons:
            return
        ara = pygame.time.get_ticks()
        if interval_ms and ara - self.ultim.get(nom, -99999) < interval_ms:
            return
        self.ultim[nom] = ara
        self.sons[nom].play()

    def tret(self, nom):
        """Els trets del jugador van a un canal propi: el nou talla l'anterior (foc automàtic net)."""
        if self.silenci or nom not in self.sons:
            return
        pygame.mixer.Channel(0).play(self.sons[nom])

    def musica(self, nom):
        if not AUDIO_OK or nom == self.musica_actual:
            return
        self.musica_actual = nom
        try:
            pygame.mixer.music.load(ruta("musica", nom + ".ogg"))
            pygame.mixer.music.set_volume(0 if self.silenci else self.VOL_MUSICA)
            pygame.mixer.music.play(-1)
        except (OSError, pygame.error) as err:
            print(f"No s'ha pogut reproduir la música {nom}: {err}")

    def aturar_musica(self):
        self.musica_actual = None
        if AUDIO_OK:
            pygame.mixer.music.stop()

    def commutar_silenci(self):
        self.silenci = not self.silenci
        if AUDIO_OK:
            pygame.mixer.music.set_volume(0 if self.silenci else self.VOL_MUSICA)
            if self.silenci:
                for i in range(pygame.mixer.get_num_channels()):
                    pygame.mixer.Channel(i).stop()


AUDIO = Audio()


class Desat:
    """Desa el progrés: localStorage al navegador, fitxer JSON a l'escriptori."""

    CLAU = "invasio_alienigena_v1"
    FITXER = os.path.join(BASE, "partida.json")

    @staticmethod
    def _storage():
        try:
            return __import__("platform").window.localStorage
        except Exception:
            return None

    @classmethod
    def carregar(cls):
        try:
            if WEB:
                st = cls._storage()
                txt = st.getItem(cls.CLAU) if st is not None else None
            elif os.path.exists(cls.FITXER):
                with open(cls.FITXER, encoding="utf-8") as f:
                    txt = f.read()
            else:
                txt = None
            if not txt or str(txt) in ("null", "undefined"):
                return {}
            dades = json.loads(str(txt))
            return dades if isinstance(dades, dict) else {}
        except Exception as err:
            print(f"No s'ha pogut carregar la partida: {err}")
            return {}

    @classmethod
    def desar(cls, dades):
        try:
            txt = json.dumps(dades)
            if WEB:
                st = cls._storage()
                if st is not None:
                    st.setItem(cls.CLAU, txt)
            else:
                with open(cls.FITXER, "w", encoding="utf-8") as f:
                    f.write(txt)
        except Exception as err:
            print(f"No s'ha pogut desar la partida: {err}")

    @classmethod
    def esborrar(cls):
        try:
            if WEB:
                st = cls._storage()
                if st is not None:
                    st.removeItem(cls.CLAU)
            elif os.path.exists(cls.FITXER):
                os.remove(cls.FITXER)
        except Exception as err:
            print(f"No s'ha pogut esborrar la partida: {err}")


# ---------------------------------------------------------------------------
# Dades del joc
# ---------------------------------------------------------------------------
ARMES = [
    {"nom": "Pistola", "dany": 5, "bales_max": 20, "cost": 0, "cadencia": 10, "auto": False,
     "vel": 12, "dispersio": 1.0, "so": "pistola", "estil": "pistola"},
    {"nom": "Fusell", "dany": 15, "bales_max": 30, "cost": 700, "cadencia": 9, "auto": True,
     "vel": 15, "dispersio": 2.0, "so": "fusell", "estil": "fusell"},
    {"nom": "Minigun", "dany": 25, "bales_max": None, "cost": 1400, "cadencia": 6, "auto": True,
     "vel": 14, "dispersio": 5.0, "so": "minigun", "estil": "minigun"},
]

TIPUS_ENEMIC = {
    #             cadència, dany, +dany/nivell, vel. bala, monedes, velocitat
    "dron":       {"cadencia": 100, "dany": 5, "dany_nivell": 2, "vel_bala": 6.5, "monedes": 50, "vel": 2.6},
    "lloctinent": {"cadencia": 85, "dany": 8, "dany_nivell": 2, "vel_bala": 7.0, "monedes": 100, "vel": 2.2},
    "boss":       {"cadencia": 66, "dany": 10, "dany_nivell": 2, "vel_bala": 7.0, "monedes": 250, "vel": 2.0},
    "boss_final": {"cadencia": 90, "dany": 10, "dany_nivell": 0, "vel_bala": 5.5, "monedes": 500, "vel": 1.5},
}

NOMS_SECTORS = ["Ruïnes Urbanes", "Selva Tecnològica", "Fortalesa Xylothian"]
NOMS_CAPS = {
    (0, 2): "GENERAL XYLOTHIAN",
    (1, 2): "MESTRE DE LA SELVA",
    (2, 1): "COMANDANT D'ELIT",
    (2, 2): "COMANDANT SUPREM",
}

# Plataformes: (x, y_superior, amplada). Enemics: (tipus, vida)
NIVELLS = {
    (0, 0): {"plataformes": [(100, 450, 150), (300, 350, 150), (500, 250, 150)],
             "enemics": [("dron", 30)] * 2},
    (0, 1): {"plataformes": [(150, 450, 150), (350, 350, 150), (550, 400, 150)],
             "enemics": [("dron", 30)] * 3 + [("lloctinent", 60)]},
    (0, 2): {"plataformes": [(100, 450, 150), (300, 350, 150), (500, 250, 150)],
             "enemics": [("boss", 100)]},
    (1, 0): {"plataformes": [(150, 450, 150), (350, 350, 200), (550, 250, 150)],
             "enemics": [("dron", 50)] * 2},
    (1, 1): {"plataformes": [(100, 450, 150), (300, 350, 150), (500, 250, 150)],
             "enemics": [("dron", 50)] * 3 + [("lloctinent", 100)]},
    (1, 2): {"plataformes": [(150, 450, 150), (350, 350, 150), (550, 250, 150)],
             "enemics": [("boss", 200)]},
    (2, 0): {"plataformes": [(100, 450, 150), (300, 350, 150), (500, 250, 150)],
             "enemics": [("dron", 80)] * 2},
    (2, 1): {"plataformes": [(150, 450, 150), (350, 350, 150), (550, 250, 150)],
             "enemics": [("dron", 80)] * 2 + [("boss", 250)]},
    (2, 2): {"plataformes": [(100, 450, 150), (300, 350, 150), (500, 250, 150)],
             "enemics": [("boss_final", 1200)]},
}

TEXTOS_NARRATIVA = {
    (0, 0): "Any 2147. Els Xylothians han envaït la Terra, deixant només ruïnes. Ets Nexus, l'últim soldat "
            "cibernètic. La teva missió: infiltrar-te a les bases alienígenes. Comences a les ruïnes urbanes. Sobreviu.",
    (0, 1): "Has destruït una base Xylothian, però n'hi ha més. Els aliens reforcen les seves defenses. "
            "Avances per les ruïnes, on els drons patrullen. Troba i elimina els seus lloctinents.",
    (0, 2): "Un General Xylothian guarda l'última base urbana. La seva derrota obrirà el camí al següent sector. "
            "Les teves armes són limitades, però la teva determinació és infinita. Endavant, Nexus.",
    (1, 0): "Has sortit de les ruïnes i entres a la Selva Tecnològica, un bioma alienígena ple de màquines "
            "orgàniques. Els Xylothians experimenten aquí. Descobreix els seus secrets i destrueix-los.",
    (1, 1): "La selva és viva, amb trampes biològiques i criatures Xylothians. Has trobat un laboratori alienígena. "
            "Destrueix les seves creacions abans que siguin alliberades contra la humanitat.",
    (1, 2): "El Mestre de la Selva, un bio-constructor Xylothian, controla aquest sector. "
            "Derrota'l per desactivar les defenses de la selva i apropar-te al bastió final.",
    (2, 0): "La Fortalesa Xylothian és el bastió final. Muralles d'energia i legions d'elit et barraran el pas. "
            "Infiltra't i debilita les seves defenses. El temps s'acaba, Nexus.",
    (2, 1): "Has trencat les defenses externes, però els Xylothians es reagrupen. Un comandant d'elit lidera "
            "la segona línia. Elimina'l per accedir al cor de la fortalesa.",
    (2, 2): "El Comandant Suprem Xylothian protegeix el cor de la fortalesa. Derrota'l per salvar la Terra. "
            "Aquest és l'últim enfrontament, Nexus. La humanitat depèn de tu.",
}
TEXT_VICTORIA = ("Has derrotat el Comandant Suprem Xylothian! La Fortalesa Xylothian cau en ruïnes, tancant "
                 "l'últim portal alienígena. La Terra està salvada gràcies a tu, Nexus. La humanitat pot "
                 "reconstruir-se i viure en pau... almenys per ara.")
TEXT_DERROTA = "Has caigut en combat. Els Xylothians avancen. Què faràs, Nexus?"


def musica_escenari(nivell, escenari):
    if (nivell, escenari) == (2, 2):
        return "boss_final"
    return ("menu", "sector2", "sector3")[nivell]


# ---------------------------------------------------------------------------
# Utilitats de dibuix
# ---------------------------------------------------------------------------
_CACHE_TEXT = {}


def render(txt, font, color):
    clau = (txt, id(font), tuple(color))
    s = _CACHE_TEXT.get(clau)
    if s is None:
        if len(_CACHE_TEXT) > 800:
            _CACHE_TEXT.clear()
        s = _CACHE_TEXT[clau] = font.render(txt, True, color)
    return s


def text(surf, txt, font, color, pos, ancora="center", ombra=True):
    img = render(txt, font, color)
    rect = img.get_rect(**{ancora: pos})
    if ombra:
        surf.blit(render(txt, font, NEGRE), rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def ajustar_linies(txt, font, ample):
    linies, actual = [], ""
    for paraula in txt.split():
        prova = f"{actual} {paraula}" if actual else paraula
        if font.size(prova)[0] <= ample:
            actual = prova
        else:
            if actual:
                linies.append(actual)
            actual = paraula
    if actual:
        linies.append(actual)
    return linies


def aclarir(color, q=40):
    return tuple(min(255, c + q) for c in color[:3])


def dibuixar_cor(surf, x, y, mida, fraccio):
    """Dibuixa un cor (fraccio 1 = ple, 0.5 = mig, 0 = buit)."""
    r = mida // 4
    def forma(color, gruix=0):
        pygame.draw.circle(surf, color, (x + r, y + r), r, gruix)
        pygame.draw.circle(surf, color, (x + 3 * r, y + r), r, gruix)
        pygame.draw.polygon(surf, color, [(x, y + r + 1), (x + mida, y + r + 1), (x + mida // 2, y + mida)], gruix)
    forma(GRIS_FOSC)
    if fraccio > 0:
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(x, y, int(mida * fraccio), mida + 1))
        forma(VERMELL)
        pygame.draw.circle(surf, (255, 170, 170), (x + r, y + r - 1), max(1, r // 2))
        surf.set_clip(clip)


def dibuixar_moneda(surf, x, y, r=7):
    pygame.draw.circle(surf, (170, 120, 20), (x, y + 1), r)
    pygame.draw.circle(surf, GROC, (x, y), r)
    pygame.draw.circle(surf, (255, 245, 170), (x - 2, y - 2), max(1, r // 3))


# ---------------------------------------------------------------------------
# Efectes visuals
# ---------------------------------------------------------------------------
class Particula:
    __slots__ = ("x", "y", "vx", "vy", "color", "vida", "t", "mida", "gravetat")

    def __init__(self, x, y, vx, vy, color, vida=25, mida=4.0, gravetat=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.color, self.vida, self.t, self.mida, self.gravetat = color, vida, 0, mida, gravetat

    def actualitzar(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravetat
        self.vx *= 0.96
        self.vy *= 0.96
        self.t += 1
        return self.t >= self.vida

    def dibuixar(self, surf):
        r = self.mida * (1 - self.t / self.vida)
        if r >= 0.5:
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), max(1, int(r)))


class Anell:
    __slots__ = ("x", "y", "r", "creix", "color", "vida", "t")

    def __init__(self, x, y, color, r=8, creix=3.0, vida=18):
        self.x, self.y, self.r, self.creix, self.color, self.vida, self.t = x, y, r, creix, color, vida, 0

    def actualitzar(self):
        self.r += self.creix
        self.t += 1
        return self.t >= self.vida

    def dibuixar(self, surf):
        gruix = max(1, int(4 * (1 - self.t / self.vida)))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), int(self.r), gruix)


class TextFlotant:
    def __init__(self, x, y, txt, color, font=F_HUD):
        self.x, self.y, self.t, self.vida = x, y, 0, 50
        self.img = render(txt, font, color).copy()

    def actualitzar(self):
        self.y -= 0.8
        self.t += 1
        return self.t >= self.vida

    def dibuixar(self, surf):
        self.img.set_alpha(int(255 * min(1.0, 2 * (1 - self.t / self.vida))))
        surf.blit(self.img, self.img.get_rect(center=(int(self.x), int(self.y))))


def esclat(efectes, x, y, n, colors, vel=(2, 6), mida=(3, 6), vida=(15, 35), gravetat=0.0):
    for _ in range(n):
        a = random.uniform(0, math.tau)
        v = random.uniform(*vel)
        efectes.append(Particula(x, y, math.cos(a) * v, math.sin(a) * v, random.choice(colors),
                                 random.randint(*vida), random.uniform(*mida), gravetat))


class FonsAnimat:
    """Fons de menús: graella en moviment i estrelles en paral·laxi."""

    def __init__(self, color_graella=(34, 44, 92), color_fons=FONS):
        self.color_graella = color_graella
        self.color_fons = color_fons
        self.desp = 0.0
        self.estrelles = [[random.uniform(0, WIDTH), random.uniform(0, HEIGHT), random.choice((1, 1, 2, 3))]
                          for _ in range(90)]

    def actualitzar(self):
        self.desp = (self.desp + 0.4) % 50
        for e in self.estrelles:
            e[0] -= 0.25 * e[2]
            if e[0] < 0:
                e[0] += WIDTH
                e[1] = random.uniform(0, HEIGHT)

    def dibuixar(self, surf):
        surf.fill(self.color_fons)
        for i in range(-50, WIDTH + 50, 50):
            pygame.draw.line(surf, self.color_graella, (i + self.desp, 0), (i + self.desp, HEIGHT), 1)
        for j in range(-50, HEIGHT + 50, 50):
            pygame.draw.line(surf, self.color_graella, (0, j + self.desp), (WIDTH, j + self.desp), 1)
        for x, y, c in self.estrelles:
            col = (90 + 50 * c, 90 + 50 * c, 120 + 45 * c)
            pygame.draw.rect(surf, col, (int(x), int(y), c, c))


# ---------------------------------------------------------------------------
# Interfície
# ---------------------------------------------------------------------------
class Boto:
    def __init__(self, rect, txt, accio, color=BLAU, actiu=True, font=None, color_text=BLANC):
        self.rect = pygame.Rect(rect)
        self.txt = txt
        self.accio = accio
        self.color = color
        self.actiu = actiu and accio is not None
        self.font = font or F_UI
        self.color_text = color_text

    def hover(self):
        return self.actiu and self.rect.collidepoint(pygame.mouse.get_pos())

    def dibuixar(self, surf):
        base = self.color if self.actiu else GRIS_FOSC
        color = aclarir(base, 45) if self.hover() else base
        desp = -2 if self.hover() else 0
        r = self.rect.move(0, desp)
        pygame.draw.rect(surf, NEGRE, self.rect.move(0, 4), border_radius=8)
        pygame.draw.rect(surf, color, r, border_radius=8)
        pygame.draw.rect(surf, aclarir(color, 60), r, 2, border_radius=8)
        text(surf, self.txt, self.font, self.color_text if self.actiu else GRIS, r.center)

    def gestionar(self, event):
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.actiu
                and self.rect.collidepoint(event.pos)):
            AUDIO.so("click")
            self.accio()
            return True
        return False


def gestionar_botons(botons, event):
    for b in botons:
        if b.gestionar(event):
            return True
    return False


# ---------------------------------------------------------------------------
# Entitats del joc
# ---------------------------------------------------------------------------
class Plataforma:
    def __init__(self, x, y, w, h=18, terra=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.terra = terra
        self.surf = self._crear_superficie()

    def _crear_superficie(self):
        w, h = self.rect.size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        if self.terra:
            s.fill((28, 30, 44, 235))
            for i in range(-20, w + 20, 24):          # franges de perill
                pygame.draw.polygon(s, (230, 180, 40), [(i, 0), (i + 12, 0), (i + 4, 8), (i - 8, 8)])
            pygame.draw.line(s, (255, 230, 120), (0, 0), (w, 0), 2)
            pygame.draw.line(s, (60, 62, 84), (0, 9), (w, 9), 1)
        else:
            pygame.draw.rect(s, (52, 56, 82), (0, 0, w, h), border_radius=4)
            pygame.draw.rect(s, (230, 180, 40), (0, 0, w, 5), border_top_left_radius=4, border_top_right_radius=4)
            pygame.draw.line(s, (255, 230, 120), (2, 0), (w - 3, 0), 1)
            pygame.draw.line(s, (28, 30, 44), (0, h - 2), (w, h - 2), 2)
            for rx in range(10, w - 5, 30):
                pygame.draw.circle(s, (110, 116, 150), (rx, h // 2 + 2), 2)
        return s

    def dibuixar(self, surf):
        surf.blit(self.surf, self.rect)


class Jugador:
    W, H = 26, 60
    VELOCITAT = 5.0
    SALT = -14.5
    GRAVETAT = 0.75
    CAIGUDA_MAX = 15.0

    def __init__(self):
        self.x = 60.0
        self.y = float(TERRA_Y - self.H)
        self.vx = 0.0
        self.vy = 0.0
        self.vida = VIDA_MAX
        self.terra = True
        self.direccio = 1
        self.coyote = 0          # marge per saltar just després de sortir d'una plataforma
        self.buffer_salt = 0     # salt premut una mica abans d'aterrar
        self.baixar = 0          # travessar plataformes cap avall
        self.invulnerable = 0
        self.pas = 0.0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    @property
    def centre(self):
        return self.x + self.W / 2, self.y + self.H / 2

    def canons(self):
        return self.x + self.W / 2 + self.direccio * 14, self.y + self.H * 0.38

    def demanar_salt(self):
        self.buffer_salt = 8

    def actualitzar(self, esquerra, dreta, salt_mantingut, avall, plataformes, mirar_x):
        objectiu = (dreta - esquerra) * self.VELOCITAT
        self.vx += (objectiu - self.vx) * 0.35
        if abs(self.vx) < 0.05:
            self.vx = 0.0
        self.direccio = 1 if mirar_x >= self.x + self.W / 2 else -1

        self.coyote = 7 if self.terra else max(0, self.coyote - 1)
        if self.buffer_salt > 0 and self.coyote > 0:
            self.vy = self.SALT
            self.buffer_salt = 0
            self.coyote = 0
            self.terra = False
        self.buffer_salt = max(0, self.buffer_salt - 1)
        if not salt_mantingut and self.vy < -4:     # salt variable: deixar anar = salt més curt
            self.vy = -4
        if avall and self.terra and self.y + self.H < TERRA_Y - 1:
            self.baixar = 14
            self.terra = False
        self.baixar = max(0, self.baixar - 1)

        self.x = max(0.0, min(WIDTH - self.W, self.x + self.vx))
        bottom_abans = self.y + self.H
        self.vy = min(self.vy + self.GRAVETAT, self.CAIGUDA_MAX)
        self.y += self.vy

        self.terra = False
        if self.vy >= 0:
            for p in plataformes:
                if self.baixar and not p.terra:
                    continue
                if (self.x + self.W > p.rect.left and self.x < p.rect.right
                        and bottom_abans <= p.rect.top + 1 and self.y + self.H >= p.rect.top):
                    self.y = float(p.rect.top - self.H)
                    self.vy = 0.0
                    self.terra = True
                    break
        if self.y + self.H > TERRA_Y:                # seguretat: mai per sota del terra
            self.y = float(TERRA_Y - self.H)
            self.vy = 0.0
            self.terra = True

        if self.terra and abs(self.vx) > 0.5:
            self.pas += 0.3
        self.invulnerable = max(0, self.invulnerable - 1)

    def dibuixar(self, surf, arma):
        if self.invulnerable and (self.invulnerable // 4) % 2 == 0:
            return
        cx = self.x + self.W / 2
        dades = SPR_JUGADOR.get(arma)
        if dades:
            img, peus = dades[self.direccio]
            bob = int(abs(math.sin(self.pas)) * 2) if self.terra and abs(self.vx) > 0.5 else 0
            pygame.draw.ellipse(surf, (0, 0, 0), (cx - 16, self.y + self.H - 4, 32, 7))
            surf.blit(img, (int(cx - peus), int(self.y + self.H - img.get_height() - bob)))
        else:
            pygame.draw.rect(surf, VERD, self.rect, border_radius=4)


class Bala:
    ESTILS = {
        # radi, color principal, de_jugador
        "pistola": (4, GROC),
        "fusell": (4, CIAN),
        "minigun": (3, TARONJA),
        "enemic": (5, VERMELL),
        "boss": (6, MORAT),
        "final": (6, ROSA),
    }

    __slots__ = ("x", "y", "vx", "vy", "dany", "radi", "color")

    def __init__(self, x, y, vx, vy, dany, estil):
        self.x, self.y, self.vx, self.vy, self.dany = x, y, vx, vy, dany
        self.radi, self.color = self.ESTILS[estil]

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.radi), int(self.y - self.radi), self.radi * 2, self.radi * 2)

    def actualitzar(self):
        self.x += self.vx
        self.y += self.vy
        return self.x < -20 or self.x > WIDTH + 20 or self.y < -20 or self.y > HEIGHT + 20

    def dibuixar(self, surf):
        cua = (self.x - self.vx * 1.6, self.y - self.vy * 1.6)
        fosc = tuple(c // 2 for c in self.color)
        pygame.draw.line(surf, fosc, cua, (self.x, self.y), self.radi * 2)
        pygame.draw.circle(surf, NEGRE, (int(self.x), int(self.y)), self.radi + 1)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radi)
        pygame.draw.circle(surf, BLANC, (int(self.x), int(self.y)), max(1, self.radi // 2))


def ventall(cx, cy, angle, n, obertura, vel, dany, estil):
    if n == 1:
        angles = [angle]
    else:
        angles = [angle - obertura / 2 + obertura * i / (n - 1) for i in range(n)]
    return [Bala(cx, cy, math.cos(a) * vel, math.sin(a) * vel, dany, estil) for a in angles]


class Enemic:
    def __init__(self, tipus, vida, nivell, x, y_destinacio):
        cfg = TIPUS_ENEMIC[tipus]
        self.tipus = tipus
        self.nivell = nivell
        clau = ("boss", nivell) if tipus == "boss" else tipus
        self.sprite = SPR_ENEMIC.get(clau)
        self.sprite_blanc = SPR_ENEMIC_BLANC.get(clau)
        if self.sprite:
            self.w, self.h = self.sprite.get_size()
        else:
            self.w, self.h = {"dron": (50, 40), "lloctinent": (66, 54), "boss": (84, 84)}.get(tipus, (128, 136))
        self.x = float(x)
        self.y = float(-self.h - random.randint(0, 80))
        self.y_destinacio = y_destinacio
        self.entrant = True
        self.vida = self.vida_max = vida
        self.vmax = cfg["vel"]
        self.vx = random.choice((-1, 1)) * random.uniform(0.8, self.vmax)
        self.vy = random.uniform(-0.5, 0.5)
        self.cadencia = max(45, cfg["cadencia"] - 6 * nivell)
        self.dany = cfg["dany"] + cfg["dany_nivell"] * nivell
        self.vel_bala = cfg["vel_bala"] + 0.4 * nivell
        self.monedes = cfg["monedes"]
        self.temps_atac = -random.randint(30, 90)      # no disparen tots alhora
        self.temps_dir = random.randint(0, 60)
        self.atacs = 0
        self.flash = 0
        self.t = random.uniform(0, math.tau)

    @property
    def es_boss(self):
        return self.tipus in ("boss", "boss_final")

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x + self.w * 0.1), int(self.y + self.h * 0.12),
                           int(self.w * 0.8), int(self.h * 0.76))

    @property
    def centre(self):
        return self.x + self.w / 2, self.y + self.h / 2

    def ferir(self, dany):
        self.vida -= dany
        self.flash = 5

    def actualitzar(self, jugador, altres):
        self.t += 0.05
        self.flash = max(0, self.flash - 1)
        if self.entrant:
            self.y += 3
            if self.y >= self.y_destinacio:
                self.entrant = False
            return []

        self.temps_dir += 1
        if self.temps_dir > 60:
            self.temps_dir = 0
            self.vx += random.uniform(-1, 1)
            self.vy += random.uniform(-1, 1)

        cx, cy = self.centre
        jx, jy = jugador.centre
        dist = math.hypot(cx - jx, cy - jy)
        if 0 < dist < (170 if self.tipus == "boss_final" else 120):
            self.vx += (cx - jx) / dist * 0.12
            self.vy += (cy - jy) / dist * 0.12
        for altre in altres:
            if altre is not self:
                ox, oy = altre.centre
                d = math.hypot(cx - ox, cy - oy)
                if 0 < d < 90:
                    self.vx += (cx - ox) / d * 0.06
                    self.vy += (cy - oy) / d * 0.06

        vel = math.hypot(self.vx, self.vy)
        if vel > self.vmax:
            self.vx, self.vy = self.vx / vel * self.vmax, self.vy / vel * self.vmax

        self.x += self.vx
        self.y += self.vy + math.sin(self.t * 2) * 0.4

        # Sempre dins de la pantalla: abans podien quedar fora on les bales no arribaven
        min_x, max_x = 8, WIDTH - self.w - 8
        min_y, max_y = 40, TERRA_Y - self.h - 110
        if self.x < min_x:
            self.x, self.vx = min_x, abs(self.vx)
        elif self.x > max_x:
            self.x, self.vx = max_x, -abs(self.vx)
        if self.y < min_y:
            self.y, self.vy = min_y, abs(self.vy)
        elif self.y > max_y:
            self.y, self.vy = max_y, -abs(self.vy)

        self.temps_atac += 1
        if self.temps_atac >= self.cadencia:
            self.temps_atac = 0
            self.atacs += 1
            return self.atacar(jugador)
        return []

    def atacar(self, jugador):
        cx, cy = self.centre
        jx, jy = jugador.centre
        angle = math.atan2(jy - cy, jx - cx)
        v, d = self.vel_bala, self.dany
        if self.tipus == "dron":
            AUDIO.so("enemic", 60)
            return ventall(cx, cy, angle, 1, 0, v, d, "enemic")
        if self.tipus == "lloctinent":
            AUDIO.so("enemic", 60)
            return ventall(cx, cy, angle, 2, math.radians(16), v, d, "enemic")
        AUDIO.so("boss", 60)
        if self.tipus == "boss":
            if self.nivell >= 1 and self.atacs % 3 == 0:
                return ventall(cx, cy, angle, 5, math.radians(60), v, d, "boss")
            if self.nivell >= 2 and self.atacs % 4 == 2:
                return ventall(cx, cy, angle, 12, math.tau * 11 / 12, v * 0.8, d, "boss")
            return ventall(cx, cy, angle, 3, math.radians(24), v * 1.1, d, "boss")
        # Comandant Suprem: anells giratoris i ràfegues dirigides, més agressiu a mitja vida
        furia = self.vida < self.vida_max / 2
        self.cadencia = 68 if furia else 90
        if self.atacs % 2 == 1:
            n = 30 if furia else 24
            gir = self.atacs * 0.13
            return [Bala(cx, cy, math.cos(gir + math.tau * i / n) * v, math.sin(gir + math.tau * i / n) * v, d, "final")
                    for i in range(n)]
        return ventall(cx, cy, angle, 5 if furia else 3, math.radians(30), v * 1.4, d, "final")

    def dibuixar(self, surf):
        if self.sprite:
            surf.blit(self.sprite, (int(self.x), int(self.y)))
            if self.flash and self.sprite_blanc:
                self.sprite_blanc.set_alpha(45 * self.flash)
                surf.blit(self.sprite_blanc, (int(self.x), int(self.y)))
        else:
            color = BLANC if self.flash else (VERMELL_FOSC if self.es_boss else MORAT)
            pygame.draw.ellipse(surf, color, (self.x, self.y, self.w, self.h))
        if not self.es_boss and self.vida < self.vida_max:
            amp = self.w
            pygame.draw.rect(surf, NEGRE, (self.x - 1, self.y - 9, amp + 2, 6))
            pygame.draw.rect(surf, VERD, (self.x, self.y - 8, amp * max(0, self.vida) / self.vida_max, 4))


class Item:
    W, H = 24, 24

    def __init__(self, x, y, tipus, caure=False, vida=None):
        self.x, self.y = float(x), float(y)
        self.tipus = tipus
        self.vy = -3.0 if caure else 0.0
        self.caient = caure
        self.anim = random.uniform(0, math.tau)
        self.vida = vida          # None = permanent

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def actualitzar(self, plataformes):
        self.anim += 0.1
        if self.caient:
            bottom_abans = self.y + self.H
            self.vy = min(self.vy + 0.4, 10)
            self.y += self.vy
            for p in plataformes:
                if (self.x + self.W > p.rect.left and self.x < p.rect.right
                        and bottom_abans <= p.rect.top + 1 and self.y + self.H >= p.rect.top and self.vy >= 0):
                    self.y = float(p.rect.top - self.H - 4)
                    self.caient = False
                    break
        if self.vida is not None:
            self.vida -= 1
            return self.vida <= 0
        return False

    def dibuixar(self, surf):
        if self.vida is not None and self.vida < 120 and (self.vida // 6) % 2 == 0:
            return
        oy = 0 if self.caient else math.sin(self.anim) * 4
        x, y = int(self.x), int(self.y + oy)
        color_halo = (255, 90, 90) if self.tipus == "vida" else (255, 220, 90)
        pygame.draw.circle(surf, tuple(c // 3 for c in color_halo), (x + 12, y + 12), 15 + int(2 * math.sin(self.anim * 2)))
        if self.tipus == "vida":
            dibuixar_cor(surf, x + 1, y + 2, 22, 1)
            pygame.draw.rect(surf, BLANC, (x + 10, y + 7, 3, 9))
            pygame.draw.rect(surf, BLANC, (x + 7, y + 10, 9, 3))
        else:
            pygame.draw.rect(surf, (70, 80, 40), (x + 1, y + 6, 22, 16), border_radius=3)
            pygame.draw.rect(surf, (120, 135, 70), (x + 1, y + 6, 22, 16), 2, border_radius=3)
            for i in range(3):
                bx = x + 5 + i * 6
                pygame.draw.rect(surf, GROC, (bx, y, 4, 9))
                pygame.draw.rect(surf, TARONJA, (bx, y, 4, 3))


# ---------------------------------------------------------------------------
# Pantalles de text (narrativa, victòria i derrota)
# ---------------------------------------------------------------------------
class PantallaText:
    def __init__(self, titol, cos, color_titol, botons, fons, pista=None):
        self.pista = pista
        self.titol = titol
        self.color_titol = color_titol
        self.linies = ajustar_linies(cos, F_TEXT, WIDTH - 160)   # es calcula una vegada: el text no "salta"
        self.total = sum(len(l) for l in self.linies)
        self.mostrats = 0.0
        self.botons = botons
        self.fons = fons

    @property
    def complet(self):
        return self.mostrats >= self.total

    def completar(self):
        self.mostrats = self.total

    def actualitzar(self):
        self.fons.actualitzar()
        if not self.complet:
            self.mostrats = min(self.total, self.mostrats + 0.8)

    def dibuixar(self, surf):
        self.fons.dibuixar(surf)
        text(surf, self.titol, F_SUBTITOL, self.color_titol, (WIDTH // 2, 84))
        alt = len(self.linies) * 36 + 40
        panell = pygame.Rect(50, 130, WIDTH - 100, alt)
        capa = pygame.Surface(panell.size, pygame.SRCALPHA)
        capa.fill((8, 10, 24, 200))
        surf.blit(capa, panell)
        pygame.draw.rect(surf, self.color_titol, panell, 2, border_radius=6)
        restants = int(self.mostrats)
        y = panell.top + 20
        cursor = (80, y)
        for linia in self.linies:
            if restants <= 0:
                break
            tros = linia[:restants]
            restants -= len(linia)
            text(surf, tros, F_TEXT, BLANC, (80, y), ancora="topleft")
            cursor = (80 + F_TEXT.size(tros)[0] + 4, y + 4)
            y += 36
        if not self.complet and (pygame.time.get_ticks() // 300) % 2:
            pygame.draw.rect(surf, CIAN, (cursor[0], cursor[1], 10, 24))
        for b in self.botons:
            b.dibuixar(surf)
        pista = self.pista or ("Clic / ESPAI per continuar" if self.complet else "Clic / ESPAI per mostrar tot el text")
        text(surf, pista, F_MINI, GRIS, (WIDTH // 2, HEIGHT - 22))


# ---------------------------------------------------------------------------
# Joc
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.clock = pygame.time.Clock()
        self.estat = "loading"
        self.temps_estat = 0
        self.fons_menu = FonsAnimat()
        self.fons_derrota = FonsAnimat((80, 24, 36), (24, 10, 16))
        self.capa = pygame.Surface((WIDTH, HEIGHT))
        self.botons = []
        self.missatge = ""
        self.temps_missatge = 0
        self.confirmar_reinici = False
        self.pantalla_text = None
        self.carregar_progres()
        self.reiniciar_partida_estat()

    # ----- Progrés -----------------------------------------------------------
    def carregar_progres(self):
        d = Desat.carregar()
        self.monedes = d.get("monedes", 0) if isinstance(d.get("monedes"), int) else 0
        desb = d.get("armes")
        self.armes_desbloquejades = ([bool(v) for v in desb][:3] if isinstance(desb, list) and len(desb) == 3
                                     else [True, False, False])
        self.armes_desbloquejades[0] = True
        arma = d.get("arma", 0)
        self.arma_actual = arma if isinstance(arma, int) and 0 <= arma < 3 and self.armes_desbloquejades[arma] else 0

        def graella(clau, defecte):
            g = d.get(clau)
            if isinstance(g, list) and len(g) == 3 and all(isinstance(f, list) and len(f) == 3 for f in g):
                return [[bool(v) for v in f] for f in g]
            return defecte
        self.nivells_desbloquejats = graella("nivells", [[True, False, False], [False] * 3, [False] * 3])
        self.nivells_desbloquejats[0][0] = True
        self.completats = graella("completats", [[False] * 3 for _ in range(3)])

    def desar_progres(self):
        Desat.desar({
            "monedes": self.monedes,
            "armes": self.armes_desbloquejades,
            "arma": self.arma_actual,
            "nivells": self.nivells_desbloquejats,
            "completats": self.completats,
        })

    def esborrar_progres(self):
        if not self.confirmar_reinici:
            self.confirmar_reinici = True
            self.entrar_menu()
            self.mostrar_missatge("Torna a clicar per confirmar")
            return
        Desat.esborrar()
        self.carregar_progres()
        self.confirmar_reinici = False
        self.entrar_menu()
        self.mostrar_missatge("Progrés esborrat")

    def mostrar_missatge(self, txt, temps=150):
        self.missatge = txt
        self.temps_missatge = temps

    # ----- Canvis d'estat ---------------------------------------------------
    def canviar_estat(self, estat):
        if estat != self.estat:
            self.missatge = ""
            self.temps_missatge = 0
        self.estat = estat
        self.temps_estat = 0
        pygame.mouse.set_visible(estat != "joc")

    def entrar_menu(self):
        AUDIO.musica("menu")
        self.desar_progres()
        b = []
        y = 230
        opcions = [("Jugar", self.entrar_selector), ("Botiga", self.entrar_botiga),
                   ("Guia", self.entrar_guia), ("Crèdits", self.entrar_credits)]
        if not WEB:
            opcions.append(("Sortir", lambda: self.canviar_estat("quit")))
        for nom, accio in opcions:
            b.append(Boto((WIDTH // 2 - 120, y, 240, 50), nom, accio))
            y += 64
        b.append(Boto((WIDTH - 210, HEIGHT - 44, 190, 30), "Esborrar progrés", self.esborrar_progres,
                      color=VERMELL_FOSC if not self.confirmar_reinici else VERMELL, font=F_MINI))
        self.botons = b
        self.canviar_estat("menu")

    def entrar_selector(self):
        self.confirmar_reinici = False
        b = []
        for n in range(3):
            for e in range(3):
                obert = self.nivells_desbloquejats[n][e]
                txt = f"{n + 1}-{e + 1}" if obert else "?"
                color = VERD if self.completats[n][e] else BLAU
                b.append(Boto((340 + e * 140, 170 + n * 110, 110, 54), txt,
                              (lambda n=n, e=e: self.mostrar_narrativa(n, e)) if obert else None, color))
        b.append(Boto((30, HEIGHT - 70, 150, 44), "< Menú", self.entrar_menu, GRIS_FOSC))
        self.botons = b
        self.canviar_estat("selector")

    def entrar_botiga(self):
        self.confirmar_reinici = False
        b = []
        for i, arma in enumerate(ARMES):
            x = 40 + i * 245
            if not self.armes_desbloquejades[i]:
                txt, color = f"Comprar {arma['cost']}", (TARONJA if self.monedes >= arma["cost"] else VERMELL_FOSC)
            elif self.arma_actual == i:
                txt, color = "Equipada", VERD
            else:
                txt, color = "Equipar", BLAU
            b.append(Boto((x + 20, 440, 185, 44), txt, lambda i=i: self.seleccionar_arma(i), color, font=F_HUD))
        b.append(Boto((30, HEIGHT - 70, 150, 44), "< Menú", self.entrar_menu, GRIS_FOSC))
        self.botons = b
        self.canviar_estat("botiga")

    def entrar_guia(self):
        self.confirmar_reinici = False
        self.botons = [Boto((30, HEIGHT - 70, 150, 44), "< Menú", self.entrar_menu, GRIS_FOSC)]
        self.canviar_estat("guia")

    def entrar_credits(self):
        self.confirmar_reinici = False
        AUDIO.musica("menu")
        self.botons = [Boto((30, HEIGHT - 70, 150, 44), "< Menú", self.entrar_menu, GRIS_FOSC)]
        self.canviar_estat("credits")

    def seleccionar_arma(self, i):
        arma = ARMES[i]
        if not self.armes_desbloquejades[i]:
            if self.monedes < arma["cost"]:
                self.mostrar_missatge(f"Et falten {arma['cost'] - self.monedes} monedes!")
                AUDIO.so("buit")
                return
            self.monedes -= arma["cost"]
            self.armes_desbloquejades[i] = True
            self.mostrar_missatge(f"{arma['nom']} desbloquejat!")
            AUDIO.so("moneda")
        self.arma_actual = i
        self.desar_progres()
        self.entrar_botiga()

    def mostrar_narrativa(self, nivell, escenari):
        self.nivell_actual = nivell
        self.escenari_actual = escenari
        AUDIO.musica(musica_escenari(nivell, escenari))
        titol = f"SECTOR {nivell + 1} · {NOMS_SECTORS[nivell].upper()}"
        boto = Boto((WIDTH // 2 - 110, HEIGHT - 110, 220, 50), "Continuar", self.avancar_narrativa)
        self.pantalla_text = PantallaText(titol, TEXTOS_NARRATIVA[(nivell, escenari)], CIAN, [boto], self.fons_menu)
        self.botons = [boto]
        self.canviar_estat("narrativa")

    def avancar_narrativa(self):
        if not self.pantalla_text.complet:
            self.pantalla_text.completar()
        elif self.estat == "victoria":
            self.entrar_credits()
        else:
            self.iniciar_joc()

    def mostrar_victoria(self):
        AUDIO.musica("menu")
        boto = Boto((WIDTH // 2 - 110, HEIGHT - 110, 220, 50), "Continuar", self.avancar_narrativa, VERD)
        self.pantalla_text = PantallaText("VICTÒRIA!", TEXT_VICTORIA, GROC, [boto], self.fons_menu)
        self.botons = [boto]
        self.canviar_estat("victoria")

    def mostrar_derrota(self):
        self.desar_progres()
        AUDIO.aturar_musica()
        AUDIO.so("eliminat")
        botons = [Boto((WIDTH // 2 - 230, HEIGHT - 110, 200, 50), "Menú", self.entrar_menu, GRIS_FOSC),
                  Boto((WIDTH // 2 + 30, HEIGHT - 110, 200, 50), "Reintentar", self.iniciar_joc, VERMELL)]
        self.pantalla_text = PantallaText("HAS CAIGUT", TEXT_DERROTA, VERMELL, botons, self.fons_derrota,
                                          pista="R / ENTER: reintentar  ·  ESC: menú")
        self.botons = botons
        self.canviar_estat("derrota")

    def pausar(self):
        self.botons = [
            Boto((WIDTH // 2 - 120, 230, 240, 50), "Continuar", self.reprendre, VERD),
            Boto((WIDTH // 2 - 120, 294, 240, 50), "Reiniciar", self.iniciar_joc, BLAU),
            Boto((WIDTH // 2 - 120, 358, 240, 50), "Menú", self.entrar_menu, GRIS_FOSC),
        ]
        self.canviar_estat("pausa")

    def reprendre(self):
        self.botons = []
        self.canviar_estat("joc")
        self.esperar_alliberar = True

    # ----- Partida ----------------------------------------------------------
    def reiniciar_partida_estat(self):
        self.nivell_actual = 0
        self.escenari_actual = 0
        self.jugador = Jugador()
        self.enemics, self.bales, self.bales_enemics = [], [], []
        self.items, self.efectes, self.textos, self.plataformes = [], [], [], []
        self.bales_armes = [a["bales_max"] for a in ARMES]

    def iniciar_joc(self):
        AUDIO.musica(musica_escenari(self.nivell_actual, self.escenari_actual))
        self.reiniciar_partida_estat_nivell()
        self.botons = []
        self.canviar_estat("joc")

    def reiniciar_partida_estat_nivell(self):
        dades = NIVELLS[(self.nivell_actual, self.escenari_actual)]
        self.jugador = Jugador()
        self.bales, self.bales_enemics, self.items, self.efectes, self.textos = [], [], [], [], []
        self.bales_armes = [a["bales_max"] for a in ARMES]
        self.plataformes = [Plataforma(0, TERRA_Y, WIDTH, HEIGHT - TERRA_Y, terra=True)]
        self.plataformes += [Plataforma(x, y, w) for x, y, w in dades["plataformes"]]
        self.enemics = []
        n = len(dades["enemics"])
        for i, (tipus, vida) in enumerate(dades["enemics"]):
            ample = TIPUS_W.get(tipus, 60)
            franja = (WIDTH - 260) / n                 # lluny del jugador, que comença a l'esquerra
            x = 220 + franja * i + random.uniform(0, max(1, franja - ample))
            y_dest = random.randint(60, 220)
            self.enemics.append(Enemic(tipus, vida, self.nivell_actual, min(x, WIDTH - ample - 10), y_dest))
        self.cap = next((e for e in self.enemics if e.es_boss), None)
        self.nom_cap = NOMS_CAPS.get((self.nivell_actual, self.escenari_actual), "")
        self.fase = "jugant"
        self.temps_fase = 0
        self.cooldown = 0
        self.clic_pendent = 0
        self.esperar_alliberar = True
        self.temps_spawn_items = 0
        self.items_generats = 0
        self.tremolor = 0.0
        self.avis_bales = 0
        self.monedes_nivell = 0

    def tipus_item_necessari(self):
        bales = self.bales_armes[self.arma_actual]
        bales_max = ARMES[self.arma_actual]["bales_max"]
        poca_municio = bales_max is not None and bales < bales_max * 0.4
        if poca_municio and self.jugador.vida > 40:
            return "bales"
        if self.jugador.vida <= 60:
            return "vida"
        if bales_max is None:
            return "vida"
        self.items_generats += 1
        return "vida" if self.items_generats % 2 else "bales"

    def generar_item(self):
        if len(self.items) >= 3:
            return
        candidates = [p for p in self.plataformes if p.rect.width > 50]
        p = random.choice(candidates)
        x = random.randint(p.rect.x + 10, p.rect.right - Item.W - 10)
        self.items.append(Item(x, p.rect.top - Item.H - 4, self.tipus_item_necessari()))

    def disparar(self):
        i = self.arma_actual
        arma = ARMES[i]
        if arma["bales_max"] is not None and self.bales_armes[i] <= 0:
            AUDIO.so("buit", 150)
            self.avis_bales = 90
            self.cooldown = 18
            return
        cx, cy = self.jugador.canons()
        mx, my = pygame.mouse.get_pos()
        angle = math.atan2(my - cy, mx - cx) + math.radians(random.uniform(-arma["dispersio"], arma["dispersio"]))
        self.bales.append(Bala(cx, cy, math.cos(angle) * arma["vel"], math.sin(angle) * arma["vel"],
                               arma["dany"], arma["estil"]))
        if arma["bales_max"] is not None:
            self.bales_armes[i] -= 1
        self.cooldown = arma["cadencia"]
        esclat(self.efectes, cx + math.cos(angle) * 8, cy + math.sin(angle) * 8, 4, [GROC, BLANC, TARONJA],
               vel=(1, 3), mida=(2, 3), vida=(5, 10))
        AUDIO.tret(arma["so"])

    def actualitzar_joc(self):
        self.temps_fase += 1
        self.tremolor *= 0.85
        teclat = pygame.key.get_pressed()
        esq = teclat[pygame.K_a] or teclat[pygame.K_LEFT]
        dre = teclat[pygame.K_d] or teclat[pygame.K_RIGHT]
        salt = teclat[pygame.K_SPACE] or teclat[pygame.K_w] or teclat[pygame.K_UP]
        avall = teclat[pygame.K_s] or teclat[pygame.K_DOWN]
        ratoli = pygame.mouse.get_pressed()[0]
        mx, _ = pygame.mouse.get_pos()

        if self.fase != "mort":
            self.jugador.actualitzar(esq, dre, salt, avall, self.plataformes, mx)

        # Trets
        if self.esperar_alliberar and not ratoli:
            self.esperar_alliberar = False
        self.cooldown = max(0, self.cooldown - 1)
        self.clic_pendent = max(0, self.clic_pendent - 1)
        if self.fase == "jugant" and not self.esperar_alliberar and self.cooldown == 0:
            arma = ARMES[self.arma_actual]
            if (arma["auto"] and ratoli) or self.clic_pendent:
                self.clic_pendent = 0
                self.disparar()
        self.avis_bales = max(0, self.avis_bales - 1)

        # Enemics
        if self.fase == "jugant":
            for e in self.enemics:
                self.bales_enemics.extend(e.actualitzar(self.jugador, self.enemics))

        # Bales del jugador
        for b in self.bales[:]:
            if b.actualitzar():
                self.bales.remove(b)
                continue
            rb = b.rect
            for e in self.enemics:
                if e.hitbox.colliderect(rb):
                    e.ferir(b.dany)
                    self.bales.remove(b)
                    esclat(self.efectes, b.x, b.y, 6, [b.color, BLANC], vel=(1, 4), mida=(2, 4), vida=(8, 16))
                    AUDIO.so("impacte", 70)
                    break

        # Enemics eliminats
        for e in self.enemics[:]:
            if e.vida <= 0:
                self.enemics.remove(e)
                cx, cy = e.centre
                gran = e.es_boss
                esclat(self.efectes, cx, cy, 60 if gran else 24, [TARONJA, VERMELL, GROC, BLANC],
                       vel=(2, 9 if gran else 6), mida=(3, 7), vida=(20, 45))
                self.efectes.append(Anell(cx, cy, TARONJA, creix=6 if gran else 3.5, vida=22))
                if gran:
                    self.efectes.append(Anell(cx, cy, BLANC, creix=9, vida=26))
                self.tremolor = max(self.tremolor, 14 if gran else 5)
                self.monedes += e.monedes
                self.monedes_nivell += e.monedes
                self.textos.append(TextFlotant(cx, cy - 10, f"+{e.monedes}", GROC))
                AUDIO.so("moneda")
                if not gran and random.random() < 0.3 and len(self.items) < 4:
                    self.items.append(Item(cx - Item.W / 2, cy, self.tipus_item_necessari(), caure=True, vida=600))

        # Bales enemigues
        rj = self.jugador.rect.inflate(-4, -6)
        for b in self.bales_enemics[:]:
            if b.actualitzar():
                self.bales_enemics.remove(b)
                continue
            if self.fase == "jugant" and not self.jugador.invulnerable and rj.colliderect(b.rect):
                self.bales_enemics.remove(b)
                self.jugador.vida -= b.dany
                self.jugador.invulnerable = 40
                self.tremolor = max(self.tremolor, 7)
                jx, jy = self.jugador.centre
                esclat(self.efectes, jx, jy, 12, [VERMELL, (255, 140, 140)], vel=(2, 5), vida=(10, 22))
                self.textos.append(TextFlotant(jx, jy - 40, f"-{b.dany}", VERMELL))
                AUDIO.so("ferit")

        # Ítems
        for it in self.items[:]:
            if it.actualitzar(self.plataformes):
                self.items.remove(it)
                continue
            if self.fase == "mort" or not self.jugador.rect.colliderect(it.rect):
                continue
            i = self.arma_actual
            agafat = False
            if it.tipus == "vida" and self.jugador.vida < VIDA_MAX:
                self.jugador.vida = min(VIDA_MAX, self.jugador.vida + 20)
                agafat, etiqueta, color = True, "+20 VIDA", VERD
            elif (it.tipus == "bales" and ARMES[i]["bales_max"] is not None
                  and self.bales_armes[i] < ARMES[i]["bales_max"]):
                self.bales_armes[i] = ARMES[i]["bales_max"]
                agafat, etiqueta, color = True, "Munició!", GROC
            if agafat:
                self.items.remove(it)
                esclat(self.efectes, it.x + 12, it.y + 12, 12, [color, BLANC], vel=(1, 4), vida=(10, 25))
                self.textos.append(TextFlotant(it.x + 12, it.y - 10, etiqueta, color))
                AUDIO.so("item")

        if self.fase == "jugant":
            self.temps_spawn_items += 1
            if self.temps_spawn_items >= 300:
                self.temps_spawn_items = 0
                self.generar_item()

        for llista in (self.efectes, self.textos):
            for fx in llista[:]:
                if fx.actualitzar():
                    llista.remove(fx)

        # Fases: mort, escenari net
        if self.fase == "jugant" and self.jugador.vida <= 0:
            self.fase, self.temps_fase = "mort", 0
            jx, jy = self.jugador.centre
            esclat(self.efectes, jx, jy, 50, [VERMELL, TARONJA, BLANC], vel=(2, 8), vida=(25, 50))
            self.tremolor = 16
            AUDIO.aturar_musica()
        elif self.fase == "jugant" and not self.enemics:
            self.fase, self.temps_fase = "net", 0
            self.bales_enemics.clear()
            self.completar_escenari()
        elif self.fase == "mort" and self.temps_fase > 75:
            self.mostrar_derrota()
        elif self.fase == "net" and self.temps_fase > 110:
            if (self.nivell_actual, self.escenari_actual) == (2, 2):
                self.mostrar_victoria()
            elif self.escenari_actual < 2:
                self.mostrar_narrativa(self.nivell_actual, self.escenari_actual + 1)
            else:
                self.mostrar_narrativa(self.nivell_actual + 1, 0)

    def completar_escenari(self):
        n, e = self.nivell_actual, self.escenari_actual
        self.completats[n][e] = True
        if e < 2:
            self.nivells_desbloquejats[n][e + 1] = True
        elif n < 2:
            self.nivells_desbloquejats[n + 1][0] = True
        self.desar_progres()

    # ----- Dibuix -----------------------------------------------------------
    def dibuixar_joc(self, surf):
        c = self.capa
        fons = FONS_NIVELLS.get((self.nivell_actual, self.escenari_actual))
        if fons:
            c.blit(fons, (0, 0))
        else:
            c.fill(FONS)
        for p in self.plataformes:
            p.dibuixar(c)
        for it in self.items:
            it.dibuixar(c)
        for e in self.enemics:
            e.dibuixar(c)
        if self.fase != "mort":
            self.jugador.dibuixar(c, ARMES[self.arma_actual]["nom"])
        for b in self.bales:
            b.dibuixar(c)
        for b in self.bales_enemics:
            b.dibuixar(c)
        for fx in self.efectes:
            fx.dibuixar(c)
        for t in self.textos:
            t.dibuixar(c)

        if self.tremolor > 0.5:
            ox = random.randint(-int(self.tremolor), int(self.tremolor))
            oy = random.randint(-int(self.tremolor), int(self.tremolor))
            surf.fill(NEGRE)
            surf.blit(c, (ox, oy))
        else:
            surf.blit(c, (0, 0))
        self.dibuixar_hud(surf)

    def dibuixar_hud(self, surf):
        surf.blit(FRANJA_HUD, (0, 0))
        # Vida
        for i in range(5):
            fr = max(0.0, min(1.0, (self.jugador.vida - i * 20) / 20))
            fr = math.ceil(fr * 2) / 2
            dibuixar_cor(surf, 14 + i * 30, 12, 24, fr)
        # Arma i bales
        arma = ARMES[self.arma_actual]
        text(surf, arma["nom"].upper(), F_GRAN, BLANC, (WIDTH // 2, 24))
        if arma["bales_max"] is None:
            txt_bales, col = "BALES: ∞", BLANC
        else:
            b = self.bales_armes[self.arma_actual]
            txt_bales = f"BALES: {b}/{arma['bales_max']}"
            col = VERMELL if b <= arma["bales_max"] * 0.25 else BLANC
        text(surf, txt_bales, F_HUD, col, (WIDTH // 2, 50))
        # Monedes, sector i enemics
        r = text(surf, str(self.monedes), F_UI, GROC, (WIDTH - 14, 18), ancora="midright")
        dibuixar_moneda(surf, r.left - 14, 18)
        text(surf, f"SECTOR {self.nivell_actual + 1}-{self.escenari_actual + 1}", F_MINI, BLANC,
             (WIDTH - 14, 42), ancora="midright")
        text(surf, f"ENEMICS: {len(self.enemics)}", F_MINI, BLANC, (WIDTH - 14, 58), ancora="midright")
        # Barra del cap
        if self.cap and self.cap in self.enemics:
            amp = 420
            x, y = WIDTH // 2 - amp // 2, HEIGHT - 20
            text(surf, self.nom_cap, F_HUD, (255, 200, 200), (WIDTH // 2, y - 10))
            pygame.draw.rect(surf, NEGRE, (x - 3, y - 3, amp + 6, 18), border_radius=4)
            pygame.draw.rect(surf, VERMELL_FOSC, (x, y, amp, 12), border_radius=3)
            fr = max(0, self.cap.vida) / self.cap.vida_max
            pygame.draw.rect(surf, VERMELL if fr < 0.5 else (230, 90, 60), (x, y, int(amp * fr), 12), border_radius=3)
        # Avisos
        if self.avis_bales and (self.avis_bales // 10) % 2 == 0:
            text(surf, "SENSE BALES! Recull munició", F_UI, VERMELL, (WIDTH // 2, 110))
        if self.fase == "jugant" and self.temps_fase < 120 and self.estat == "joc":
            nom = NOMS_SECTORS[self.nivell_actual]
            text(surf, f"{nom} · {self.escenari_actual + 1}/3", F_UI, CIAN, (WIDTH // 2, 150))
        if self.fase == "net":
            text(surf, "SECTOR NET!", F_TITOL, VERD, (WIDTH // 2, HEIGHT // 2 - 40))
            text(surf, f"+{self.monedes_nivell} monedes", F_UI, GROC, (WIDTH // 2, HEIGHT // 2 + 4))
        # Punt de mira
        if self.estat == "joc":
            mx, my = pygame.mouse.get_pos()
            col = VERMELL if self.avis_bales else BLANC
            pygame.draw.circle(surf, NEGRE, (mx, my), 10, 3)
            pygame.draw.circle(surf, col, (mx, my), 9, 1)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pygame.draw.line(surf, col, (mx + dx * 5, my + dy * 5), (mx + dx * 13, my + dy * 13), 2)

    def dibuixar_menu(self, surf):
        self.fons_menu.dibuixar(surf)
        if LOGO:
            petit = LOGO_MENU
            surf.blit(petit, petit.get_rect(center=(WIDTH // 2, 75)))
            text(surf, "INVASIÓ ALIENÍGENA", F_TITOL, BLANC, (WIDTH // 2, 175))
        else:
            text(surf, "INVASIÓ ALIENÍGENA", F_TITOL, BLANC, (WIDTH // 2, 120))
        text(surf, str(self.monedes), F_UI, GROC, (44, 26), ancora="midleft")
        dibuixar_moneda(surf, 28, 25)
        estat_so = "M: so OFF" if AUDIO.silenci else "M: so ON"
        text(surf, estat_so, F_MINI, GRIS, (20, HEIGHT - 28), ancora="midleft")

    def dibuixar_selector(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "SELECCIONA NIVELL", F_TITOL, BLANC, (WIDTH // 2, 70))
        for n in range(3):
            y = 197 + n * 110
            obert = any(self.nivells_desbloquejats[n])
            text(surf, f"SECTOR {n + 1}", F_HUD, CIAN if obert else GRIS, (40, y - 12), ancora="midleft")
            text(surf, NOMS_SECTORS[n], F_TEXT_P, BLANC if obert else GRIS, (40, y + 12), ancora="midleft")
        text(surf, "Verd = completat", F_MINI, GRIS, (WIDTH - 30, HEIGHT - 48), ancora="midright")

    def dibuixar_botiga(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "BOTIGA", F_TITOL, BLANC, (WIDTH // 2, 60))
        r = text(surf, str(self.monedes), F_GRAN, GROC, (WIDTH // 2 + 14, 110))
        dibuixar_moneda(surf, r.left - 22, 110, 9)
        for i, arma in enumerate(ARMES):
            x = 40 + i * 245
            carta = pygame.Rect(x, 150, 225, 345)
            desb = self.armes_desbloquejades[i]
            vora = VERD if self.arma_actual == i else (BLAU_CLAR if desb else GRIS)
            capa = pygame.Surface(carta.size, pygame.SRCALPHA)
            capa.fill((10, 12, 28, 215))
            surf.blit(capa, carta)
            pygame.draw.rect(surf, vora, carta, 2, border_radius=8)
            text(surf, arma["nom"].upper(), F_UI, BLANC, (carta.centerx, carta.top + 26))
            dades = SPR_JUGADOR.get(arma["nom"])
            if dades:
                img = dades[1][0]
                if not desb:
                    img = img.copy()
                    img.fill((60, 60, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(img, img.get_rect(center=(carta.centerx, carta.top + 100)))
            bales = "∞" if arma["bales_max"] is None else str(arma["bales_max"])
            tirs = round(FPS / arma["cadencia"], 1)
            info = [("Dany", str(arma["dany"])), ("Bales", bales),
                    ("Tirs/s", str(tirs)), ("Mode", "Automàtic" if arma["auto"] else "Semi")]
            for k, (nom, valor) in enumerate(info):
                y = carta.top + 160 + k * 28
                text(surf, nom, F_TEXT_P, GRIS, (carta.left + 18, y), ancora="midleft", ombra=False)
                text(surf, valor, F_TEXT_P, BLANC, (carta.right - 18, y), ancora="midright", ombra=False)
        text(surf, "La munició es recarga al començar cada nivell", F_MINI, GRIS, (WIDTH // 2 + 80, HEIGHT - 48))

    def dibuixar_guia(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "GUIA", F_TITOL, BLANC, (WIDTH // 2, 60))
        controls = [
            ("A / D  o  fletxes", "Moure's"),
            ("ESPAI / W / amunt", "Saltar (mantén per saltar més)"),
            ("S / avall", "Baixar d'una plataforma"),
            ("Clic esquerre", "Disparar (mantén: armes automàtiques)"),
            ("P / ESC", "Pausa"),
            ("G", "Tornar al menú"),
            ("M", "Activar / silenciar el so"),
        ]
        for i, (tecla, accio) in enumerate(controls):
            y = 130 + i * 38
            text(surf, tecla, F_TEXT_P, GROC, (60, y), ancora="midleft")
            text(surf, accio, F_TEXT_P, BLANC, (330, y), ancora="midleft")
        consells = [
            "Elimina enemics per guanyar monedes i compra armes a la Botiga.",
            "Recull cors per curar-te i caixes per recarregar munició.",
            "Els enemics de vegades deixen ítems en morir. Afanya't!",
            "El progrés es desa automàticament.",
        ]
        for i, c in enumerate(consells):
            text(surf, "· " + c, F_TEXT_P, CIAN, (60, 410 + i * 28), ancora="midleft")

    def dibuixar_credits(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "CRÈDITS", F_TITOL, BLANC, (WIDTH // 2, 70))
        llista = [
            ("Joc creat per", "Nacho i Abel"),
            ("Programació", "Nacho i Abel"),
            ("Disseny de joc", "Nacho i Abel"),
            ("Gràfics", "Nacho i Abel"),
            ("Música i efectes", "YouTube, lliure de drets"),
            ("Producció", "Nacho i Abel"),
            ("Tipografies", "Press Start 2P i VT323 (SIL OFL)"),
        ]
        for i, (a, b) in enumerate(llista):
            y = 140 + i * 44
            text(surf, a, F_TEXT_P, GRIS, (WIDTH // 2 - 20, y), ancora="midright")
            text(surf, b, F_TEXT_P, BLANC, (WIDTH // 2 + 20, y), ancora="midleft")
        text(surf, "Gràcies per jugar!", F_GRAN, GROC, (WIDTH // 2, 470))

    def dibuixar_loading(self, surf):
        self.fons_menu.dibuixar(surf)
        if LOGO:
            surf.blit(LOGO, LOGO.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 70)))
        text(surf, "FET PER NACHO I ABEL", F_UI, BLANC, (WIDTH // 2, HEIGHT // 2 + 120))
        progres = min(1.0, self.temps_estat / (FPS * 2.5))
        barra = pygame.Rect(WIDTH // 2 - 160, HEIGHT // 2 + 160, 320, 14)
        pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=4)
        pygame.draw.rect(surf, CIAN, (barra.x, barra.y, int(barra.w * progres), barra.h), border_radius=4)
        if progres >= 1 and (pygame.time.get_ticks() // 400) % 2:
            text(surf, "Clica per començar", F_HUD, GROC, (WIDTH // 2, HEIGHT // 2 + 200))

    def dibuixar_pausa(self, surf):
        self.dibuixar_joc(surf)
        vel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        vel.fill((0, 0, 0, 160))
        surf.blit(vel, (0, 0))
        text(surf, "PAUSA", F_TITOL, BLANC, (WIDTH // 2, 170))

    # ----- Esdeveniments ----------------------------------------------------
    def gestionar_event(self, ev):
        if ev.type == pygame.QUIT:
            self.canviar_estat("quit")
            return
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_m:
            AUDIO.commutar_silenci()
            return
        if ev.type == getattr(pygame, "WINDOWFOCUSLOST", -1) and self.estat == "joc" and self.fase == "jugant":
            self.pausar()
            return

        if self.estat == "loading":
            if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                self.entrar_menu()
            return

        if gestionar_botons(self.botons, ev):
            return

        if self.estat == "joc":
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    self.jugador.demanar_salt()
                elif ev.key in (pygame.K_p, pygame.K_ESCAPE) and self.fase == "jugant":
                    self.pausar()
                elif ev.key == pygame.K_g:
                    self.entrar_menu()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.esperar_alliberar = False
                self.clic_pendent = 12
        elif self.estat == "pausa":
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_p, pygame.K_ESCAPE):
                self.reprendre()
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_g:
                self.entrar_menu()
        elif self.estat in ("narrativa", "victoria"):
            if ((ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER))
                    or (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1)):
                self.avancar_narrativa()
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.entrar_menu()
        elif self.estat == "derrota":
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                    if self.pantalla_text.complet:
                        self.iniciar_joc()
                    else:
                        self.pantalla_text.completar()
                elif ev.key in (pygame.K_ESCAPE, pygame.K_g):
                    self.entrar_menu()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.pantalla_text.completar()
        elif self.estat in ("selector", "botiga", "guia", "credits"):
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_g):
                self.entrar_menu()

    # ----- Bucle principal --------------------------------------------------
    def actualitzar(self):
        self.temps_estat += 1
        if self.temps_missatge > 0:
            self.temps_missatge -= 1
            if self.temps_missatge == 0:
                self.missatge = ""
        if self.estat in ("loading", "menu", "selector", "botiga", "guia", "credits"):
            self.fons_menu.actualitzar()
        if self.estat == "loading" and self.temps_estat > FPS * 6:
            self.entrar_menu()
        elif self.estat == "joc":
            self.actualitzar_joc()
        elif self.estat in ("narrativa", "victoria", "derrota"):
            self.pantalla_text.actualitzar()

    def dibuixar(self, surf):
        dibuix = {
            "loading": self.dibuixar_loading, "menu": self.dibuixar_menu, "selector": self.dibuixar_selector,
            "botiga": self.dibuixar_botiga, "guia": self.dibuixar_guia, "credits": self.dibuixar_credits,
            "joc": self.dibuixar_joc, "pausa": self.dibuixar_pausa,
        }.get(self.estat)
        if dibuix:
            dibuix(surf)
        elif self.pantalla_text:
            self.pantalla_text.dibuixar(surf)
        if self.estat not in ("narrativa", "victoria", "derrota"):
            for b in self.botons:
                b.dibuixar(surf)
        if self.missatge and self.estat != "joc":
            col = VERD if "desbloquejat" in self.missatge or "esborrat" in self.missatge else VERMELL
            if self.estat == "botiga":
                text(surf, self.missatge, F_UI, col, (WIDTH // 2, 520))
            else:
                text(surf, self.missatge, F_HUD, col, (WIDTH // 2 - 60, HEIGHT - 28))

    def pas(self):
        """Un fotograma complet (també l'utilitzen les proves automàtiques)."""
        for ev in pygame.event.get():
            self.gestionar_event(ev)
        if self.estat == "quit":
            return False
        self.actualitzar()
        if self.estat == "quit":
            return False
        self.dibuixar(screen)
        pygame.display.flip()
        return True

    async def main(self):
        if not AUDIO.silenci:
            AUDIO.musica("menu")
        while self.pas():
            self.clock.tick(FPS)
            await asyncio.sleep(0)      # imprescindible al navegador: retorna el control al bucle d'esdeveniments
        pygame.quit()
        if not WEB:
            sys.exit()


TIPUS_W = {k: (SPR_ENEMIC.get(k) or SPR_ENEMIC.get(("boss", 0)) or pygame.Surface((60, 60))).get_width()
           for k in ("dron", "lloctinent", "boss_final")}
TIPUS_W["boss"] = 96
LOGO_MENU = escalar(LOGO, 110 / LOGO.get_height()) if LOGO else None
FRANJA_HUD = pygame.Surface((WIDTH, 72), pygame.SRCALPHA)
for _y in range(72):
    pygame.draw.line(FRANJA_HUD, (0, 0, 0, int(140 * (1 - _y / 72))), (0, _y), (WIDTH, _y))


if __name__ == "__main__":
    asyncio.run(Game().main())
