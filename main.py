"""
Joc Militar: Invasió Alienígena
Versió millorada, compatible amb escriptori i navegador (pygbag / GitHub Pages).

Escriptori:  python main.py
Navegador:   pygbag .        (GitHub Actions recompila index.html i historygame.apk)
"""
import asyncio
import json
import math
import os
import random
import sys

import pygame

from idiomes import IDIOMES, T, idioma, posar_idioma
from dades import (DETALL_ARMES, DETALL_MILLORES, NIVELL_TUTORIAL, PASSOS_TUTORIAL, CALOR_DISPAR, ARRENCADA, FRE_MINIGUN, APARENCES_ARMA, ARENES, NOMS_ARENES, CATEGORIES_LOGRO, LOGROS, LOGRO_PER_ID, PLAQUES, ARMA_PER_ID, ARMES, ARXIU, CAPS_FINALS, CAPS_NORMALS, CINEMATICA_CAP,
                   CINEMATIQUES, DIFICULTATS, ENEMICS_TERRA, INTRO, MILLORES, MOTIUS_RESTRICCIO, MUSICA_SECTOR,
                   NIVELLS, NOMS_CAPS, NOMS_RADIO, NOMS_SECTORS, NUM_SECTORS, PASSI, POTENCIA_MAX, PRESENTACIO_CAPS,
                   RADIO, TEMPS_ESTRELLA, TEXT_DERROTA, TEXTOS_NARRATIVA, TIPUS_ENEMIC, TITOLS, UNIFORMES,
                   XP_ESCENARI, XP_ESTRELLA, XP_PER_NIVELL, XP_PRIMERA_VEGADA, VERSIO, NOVETATS, nom_escenari, nom_recompensa)

# ---------------------------------------------------------------------------
# Configuració general
# ---------------------------------------------------------------------------
WEB = sys.platform == "emscripten"
BASE = os.path.dirname(os.path.abspath(__file__))

WIDTH, HEIGHT = 960, 540       # 16:9; x2 = 1920x1080 exactos (cada píxel del juego son 2x2 de pantalla)
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
                os.makedirs(os.path.dirname(cls.FITXER), exist_ok=True)
                temporal = cls.FITXER + ".tmp"           # primer a un fitxer temporal: mai queda a mitges
                with open(temporal, "w", encoding="utf-8") as f:
                    f.write(txt)
                os.replace(temporal, cls.FITXER)
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


OPCIONS_INICIALS = Desat.carregar().get("opcions", {})
if not isinstance(OPCIONS_INICIALS, dict):
    OPCIONS_INICIALS = {}
posar_idioma(OPCIONS_INICIALS.get("idioma", "es"))

try:
    # búfer gran: evita els talls i espetecs del so en ordinadors lents i al navegador
    pygame.mixer.pre_init(44100, -16, 2, 2048)
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



class Pantalla:
    """El joc es dibuixa sempre a 960x540 (`screen`) i aquí s'escala a la resolució de la finestra o del
    monitor. Si l'escala és entera (1920x1080 = x2, 2880x1620 = x3...) es fa píxel a píxel, sense suavitzar:
    nitidesa total. Si el monitor no és 16:9, les bandes s'omplen amb una versió difuminada de la imatge."""

    MIDA_WEB = (WIDTH, HEIGHT)      # al navegador el CSS l'amplia a tota la finestra (vegeu nitidesa_web)

    def __init__(self, completa=True, suau=True):
        info = pygame.display.Info()
        self.monitor = (info.current_w or 1920, info.current_h or 1080)
        self.completa = completa
        self.suau = suau
        self.ambient = None
        self.temps = 0
        self.aplicar()

    def mida_finestra(self):
        forcada = os.environ.get("JOC_FINESTRA")          # p. ex. "960x540" per a les proves
        if forcada:
            w, h = forcada.lower().split("x")
            return int(w), int(h)
        mw, mh = self.monitor
        alt = min(1080, int(mh * 0.85))
        return int(alt * 16 / 9), alt

    def aplicar(self):
        if WEB:
            self.surf = pygame.display.set_mode(self.MIDA_WEB)
        elif self.completa and not os.environ.get("JOC_FINESTRA"):
            self.surf = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.surf = pygame.display.set_mode(self.mida_finestra(), pygame.RESIZABLE)
        pygame.display.set_caption("Juego Militar: Invasión Alienígena")
        self.recalcular()

    def recalcular(self):
        self.surf = pygame.display.get_surface()
        w, h = self.surf.get_size()
        self.escala = min(w / WIDTH, h / HEIGHT)
        # escala entera (o gairebé): píxels exactes de 2x2, 3x3... sense cap suavitzat
        self.entera = abs(self.escala - round(self.escala)) < 0.01 and round(self.escala) >= 1
        if self.entera:
            self.escala = float(round(self.escala))
        mida = (int(WIDTH * self.escala), int(HEIGHT * self.escala))
        self.rect = pygame.Rect(0, 0, *mida)
        self.rect.center = (w // 2, h // 2)
        self.ambient = None
        self.nitidesa_web()

    def nitidesa_web(self):
        """Al navegador el llenç de 960x540 l'amplia el CSS: sense suavitzar si l'escala és entera o si
        s'ha triat «Nítido»."""
        if not WEB:
            return
        try:
            canvas = __import__("platform").document.getElementById("canvas")
            ample = float(canvas.getBoundingClientRect().width) or WIDTH
            k = ample / WIDTH
            nitid = (not self.suau) or abs(k - round(k)) < 0.01
            canvas.style.imageRendering = "pixelated" if nitid else "auto"
        except Exception:
            pass

    def commutar_completa(self):
        if WEB:
            try:
                __import__("platform").window.document.documentElement.requestFullscreen()
            except Exception as err:
                print(f"No s'ha pogut posar a pantalla completa: {err}")
            return
        self.completa = not self.completa
        self.aplicar()

    def a_virtual(self, pos):
        """Coordenades de la finestra -> coordenades del joc (960x540)."""
        x = (pos[0] - self.rect.x) / self.escala
        y = (pos[1] - self.rect.y) / self.escala
        return int(max(0, min(WIDTH - 1, x))), int(max(0, min(HEIGHT - 1, y)))

    def presentar(self, virtual):
        self.temps += 1
        if WEB and self.temps % 60 == 0:
            self.nitidesa_web()          # la finestra del navegador pot haver canviat de mida
        if self.rect.size == (WIDTH, HEIGHT) and self.rect.topleft == (0, 0):
            self.surf.blit(virtual, (0, 0))
        else:
            w, h = self.surf.get_size()
            if self.rect.width < w or self.rect.height < h:
                # bandes laterals: la mateixa imatge, molt difuminada i fosca (s'actualitza cada 6 fotogrames)
                if self.ambient is None or self.temps % 6 == 0:
                    petit = pygame.transform.smoothscale(virtual, (24, 18))
                    self.ambient = pygame.transform.smoothscale(petit, (w, h))
                    self.ambient.fill((135, 135, 150), special_flags=pygame.BLEND_RGB_MULT)
                if self.rect.left > 0:
                    self.surf.blit(self.ambient, (0, 0), pygame.Rect(0, 0, self.rect.left, h))
                    self.surf.blit(self.ambient, (self.rect.right, 0), pygame.Rect(self.rect.right, 0, w - self.rect.right, h))
                if self.rect.top > 0:
                    self.surf.blit(self.ambient, (0, 0), pygame.Rect(0, 0, w, self.rect.top))
                    self.surf.blit(self.ambient, (0, self.rect.bottom), pygame.Rect(0, self.rect.bottom, w, h - self.rect.bottom))
            suau = self.suau and not self.entera
            escalat = (pygame.transform.smoothscale if suau else pygame.transform.scale)(virtual, self.rect.size)
            self.surf.blit(escalat, self.rect)
        pygame.display.flip()


PANTALLA = Pantalla(bool(OPCIONS_INICIALS.get("completa", True)), bool(OPCIONS_INICIALS.get("suau", True)))
screen = pygame.Surface((WIDTH, HEIGHT))       # llenç virtual on es dibuixa tot el joc


def ratoli():
    """Posició del ratolí en coordenades del joc, sigui quina sigui la resolució."""
    return PANTALLA.a_virtual(pygame.mouse.get_pos())



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
F_TEXT_PP = carregar_font("VT323-Regular.ttf", 21)


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


# ---------------------------------------------------------------------------
# Animació del jugador: a partir de cada sprite original es generen fotogrames
# separant les cames del cos (córrer, repòs, salt i caiguda).
# ---------------------------------------------------------------------------
# Per a cada arma: cames com (x_inici, x_final, y_inici) en coordenades del sprite retallat
CAMES_JUGADOR = {
    "pistola": [(2, 5, 22), (8, 11, 22)],
    "escopeta": [(2, 5, 22), (8, 11, 22)],
    "fusell": [(2, 5, 22), (8, 11, 22)],
    "minigun": [(2, 5, 22), (10, 13, 26)],
    "plasma": [(2, 5, 22), (8, 11, 22)],
}


class SpritesJugador:
    ESCALA = 2
    MARGE = 3
    FOTOGRAMES_CORRER = 6

    def __init__(self, img, cames):
        self.w, self.h = img.get_size()
        w, h = self.w, self.h
        self.cames = []
        mascara = set()
        for x0, x1, y0 in cames:
            px = [(x, y, tuple(img.get_at((x, y)))) for x in range(x0, min(x1, w - 1) + 1)
                  for y in range(y0, h) if img.get_at((x, y)).a]
            self.cames.append((y0, px))
            mascara.update((x, y) for x, y, _ in px)
        self.cos = img.copy()
        for x, y in mascara:
            self.cos.set_at((x, y), (0, 0, 0, 0))
        totes = [x for _, px in self.cames for x, _, _ in px]
        peus = (sum(totes) / len(totes)) if totes else w / 2
        # punta del canó: el píxel opac més a la dreta de la zona del tors
        punts = [(x, y) for y in range(8, h - 4) for x in range(w) if img.get_at((x, y)).a]
        xmax = max(x for x, _ in punts)
        ys = [y for x, y in punts if x == xmax]
        canó = (xmax + 1, sum(ys) / len(ys))

        e, m = self.ESCALA, self.MARGE
        self.peus_x = (m + peus + 0.5) * e                      # ancoratge horitzontal (dreta)
        self.ample = (w + 2 * m) * e
        self.alt = h * e
        self.cano_dx = (m + canó[0]) * e - self.peus_x           # punta del canó respecte als peus
        self.cano_dy = canó[1] * e - self.alt + e

        self.poses = {
            "quiet": [self._fotograma(0, 0, 0, 0, 0), self._fotograma(0, 0, 0, 0, 1)],
            "salt": [self._fotograma(-1.5, 1, 2.5, 3, 0)],
            "caiguda": [self._fotograma(-2, 0, 1.5, 1, 0)],
            "corre": [],
        }
        n = self.FOTOGRAMES_CORRER
        for i in range(n):
            fase = math.tau * i / n
            s = 2.6 * math.sin(fase)
            self.poses["corre"].append(self._fotograma(
                -s, max(0.0, 2 * math.cos(fase)), s, max(0.0, -2 * math.cos(fase)),
                1 if i % 3 == 1 else 0))

    def _fotograma(self, swing_darrere, aixecar_darrere, swing_davant, aixecar_davant, bob):
        m = self.MARGE
        out = pygame.Surface((self.w + 2 * m, self.h), pygame.SRCALPHA)
        params = ((swing_darrere, aixecar_darrere, 0.78), (swing_davant, aixecar_davant, 1.0))
        for (y0, px), (swing, aixecar, llum) in zip(self.cames, params):
            llarg = max(1, self.h - 1 - y0)
            for x, y, c in px:
                t = (y - y0) / llarg
                nx = m + x + round(swing * t)
                ny = y - round(aixecar * t)
                if 0 <= nx < out.get_width() and 0 <= ny < self.h:
                    out.set_at((nx, ny), (int(c[0] * llum), int(c[1] * llum), int(c[2] * llum), c[3]))
        out.blit(self.cos, (m, bob))
        dreta = pygame.transform.scale(out, (out.get_width() * self.ESCALA, self.h * self.ESCALA))
        return {1: dreta, -1: pygame.transform.flip(dreta, True, False)}

    def ancoratge(self, direccio):
        return self.peus_x if direccio == 1 else self.ample - self.peus_x


SPR_JUGADOR_CACHE = {}
FITXERS_JUGADOR = {"pistola": "jugador_pistola.png", "escopeta": "jugador_escopeta.png",
                   "fusell": "jugador_fusell.png", "minigun": "jugador_minigun.png", "plasma": "jugador_plasma.png"}
BASE_JUGADOR = {k: retallar(carregar_imatge(f)) for k, f in FITXERS_JUGADOR.items()}
# colors originals de l'uniforme (fosc, clar, pantalons) i variants properes
COLORS_UNIFORME = {(130, 119, 23): 0, (146, 131, 35): 0, (158, 157, 36): 1, (85, 139, 47): 2}


def es_metall(c):
    """Els grisos de les armes (no inclou les botes ni el negre de la cara)."""
    return abs(c[0] - c[1]) < 14 and abs(c[1] - c[2]) < 14 and 36 <= c[0] <= 140


def recolorar_soldat(img, colors_uniforme, tint_arma):
    s = img.copy()
    if not colors_uniforme and not tint_arma:
        return s
    s.lock()
    w, h = s.get_size()
    for x in range(w):
        for y in range(h):
            c = s.get_at((x, y))
            if not c.a:
                continue
            rgb = (c.r, c.g, c.b)
            if colors_uniforme and rgb in COLORS_UNIFORME:
                s.set_at((x, y), (*colors_uniforme[COLORS_UNIFORME[rgb]], c.a))
            elif tint_arma and es_metall(rgb):
                k = c.r / 105
                s.set_at((x, y), tuple(min(255, int(v * k)) for v in tint_arma) + (c.a,))
    s.unlock()
    return s


ACER = {"f": (58, 66, 88), "m": (112, 124, 150), "l": (182, 194, 216)}
# plaques de blindatge (millora «Blindaje») per nivell: (fila, x_inici, x_final, to) sobre el sprite retallat
PLAQUES_BLINDATGE = {
    1: [(11, 1, 4, "f"), (12, 0, 4, "l"), (13, 0, 4, "m"), (14, 0, 3, "f")],              # musclera
    2: [(12, 5, 10, "l"), (13, 5, 10, "m"), (14, 5, 10, "m"), (15, 5, 10, "m"), (16, 5, 10, "f")],   # pitet
    3: [(0, 1, 11, "l"), (1, 1, 11, "m"), (22, 2, 4, "m"), (22, 8, 10, "m")],              # casc i genolleres
}


def blindar(img, nivell):
    """Pinta plaques d'acer sobre el soldat segons el nivell de blindatge (només on hi ha píxels)."""
    if not nivell:
        return img
    s = img.copy()
    w, h = s.get_size()
    for n in range(1, min(3, nivell) + 1):
        for y, x0, x1, to in PLAQUES_BLINDATGE[n]:
            for x in range(x0, x1 + 1):
                if 0 <= x < w and 0 <= y < h:
                    c = s.get_at((x, y))
                    pell = c.r > 200 and c.g > 140 and c.b > 100           # cara i mans: no es tapen
                    if c.a and not pell and c.r + c.g + c.b > 90:
                        s.set_at((x, y), ACER[to])
    return s


def sprites_jugador(arma_id, uniforme="classic", aparenca="estandard", blindatge=0):
    """Fotogrames del soldat amb l'arma i l'aparença triades (es generen un cop i es guarden)."""
    clau = (arma_id, uniforme, aparenca, blindatge)
    spr = SPR_JUGADOR_CACHE.get(clau)
    if spr is None:
        base = BASE_JUGADOR.get(arma_id) or BASE_JUGADOR.get("pistola")
        if base is None:
            return None
        img = blindar(recolorar_soldat(base, UNIFORMES[uniforme]["colors"], APARENCES_ARMA[aparenca]["tint"]),
                      blindatge)
        spr = SPR_JUGADOR_CACHE[clau] = SpritesJugador(img, CAMES_JUGADOR.get(arma_id, CAMES_JUGADOR["pistola"]))
    return spr


def tires(nom, ample, escala=2):
    """Full de fotogrames horitzontal -> llista de fotogrames escalats (escala entera: píxels nets)."""
    img = carregar_imatge(nom)
    if img is None:
        return []
    alt = img.get_height()
    return [escalar(img.subsurface((x, 0, ample, alt)).copy(), escala) for x in range(0, img.get_width(), ample)]


# Tots els sprites s'amplien a escales enteres (x1, x2, x3): cada píxel de l'art és un quadrat igual.
_dron = retallar(carregar_imatge("enemic.png"))
_boss = retallar(carregar_imatge("enemic_boss.png"))
SPR_ENEMIC = {
    "dron": escalar(_dron, 2),
    "lloctinent": escalar(permutar_canals(_dron, (2, 1, 0)), 3),
    "cacador": escalar(carregar_imatge("enemic_cacador.png"), 2),
    ("boss", 0): escalar(_boss, 2),
    ("boss", 1): escalar(permutar_canals(_boss, (0, 2, 1)), 2),
    ("boss", 2): escalar(permutar_canals(_boss, (2, 1, 0)), 2),
    ("boss", 3): escalar(permutar_canals(_boss, (1, 0, 2)), 2),
    ("boss", 4): escalar(permutar_canals(_boss, (1, 2, 0)), 2),
    "final_comandant": retallar(carregar_imatge("enemic_boss_final.png")),
    "final_nau": escalar(carregar_imatge("boss_nau_mare.png"), 2),
    "final_nucli": escalar(carregar_imatge("boss_nucli.png"), 2),
}
# enemics de terra: fotogrames (vegeu tools/generar_sprites.py)
FRAMES_TERRA = {"soldat": tires("enemic_soldat.png", 18), "escut": tires("enemic_escut.png", 22),
                "kamikaze": tires("enemic_kamikaze.png", 14)}
for _t, _fr in FRAMES_TERRA.items():
    SPR_ENEMIC[_t] = _fr[0] if _fr else None
# retrats de la ràdio (2 fotogrames: boca tancada / oberta)
RETRATS = {q: tires(f"retrat_{q}.png", 32) for q in ("comandant", "doctora", "nexus", "ment")}


def frames_tentacles(img, n=8):
    """El Comandant Suprem: la meitat inferior (tentacles) ondula."""
    if img is None:
        return []
    w, h = img.get_size()
    frames = []
    for f in range(n):
        s = pygame.Surface((w + 16, h), pygame.SRCALPHA)
        for y in range(h):
            k = max(0.0, (y - h * 0.42) / (h * 0.58))
            dx = math.sin(f / n * math.tau + y * 0.11) * 6 * k
            s.blit(img, (8 + round(dx), y), pygame.Rect(0, y, w, 1))
        frames.append(s)
    return frames


def tenyir(img, color, alfa=110):
    s = img.copy()
    capa = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    capa.fill((*color, alfa))
    mascara = silueta_blanca(img)
    capa.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(capa, (0, 0))
    return s


FRAMES_COMANDANT = frames_tentacles(SPR_ENEMIC["final_comandant"])
FRAMES_COMANDANT_FURIA = [tenyir(f, (255, 40, 40), 90) for f in FRAMES_COMANDANT]
_CACHE_ROTACIO = {}


def rotat(img, angle, clau):
    """Sprite girat (els angles s'arrodoneixen per poder reaprofitar-los)."""
    a = int(round(angle / 3.0) * 3)
    if a == 0:
        return img
    k = (clau, a)
    r = _CACHE_ROTACIO.get(k)
    if r is None:
        if len(_CACHE_ROTACIO) > 600:
            _CACHE_ROTACIO.clear()
        r = _CACHE_ROTACIO[k] = pygame.transform.rotate(img, a)
    return r


FONS_NIVELLS = {}
for _n in range(NUM_SECTORS):
    for _e in range(3):
        _f = carregar_imatge(f"fons_nivell_{_n}_{_e}.png", alpha=False)
        # una mica més gran que la pantalla per poder fer paral·laxi
        FONS_NIVELLS[(_n, _e)] = escalar(_f, mida=(WIDTH + 40, HEIGHT + 20)) if _f else None


class Audio:
    """Efectes amb pygame.mixer.Sound i música en streaming amb pygame.mixer.music."""

    VOLUMS = {
        "click": 0.6, "pistola": 0.55, "fusell": 0.5, "minigun": 0.35, "enemic": 0.45,
        "boss": 0.5, "impacte": 0.45, "eliminat": 0.8, "item": 0.6, "moneda": 0.5,
        "buit": 0.7, "ferit": 0.7, "escopeta": 0.6, "plasma": 0.5, "envestida": 0.5, "explosio": 0.8,
        "passi": 0.6, "latido": 0.75, "ting": 0.45, "marca": 0.3,
    }
    def __init__(self, vol_musica=0.3, vol_efectes=0.8):
        self.sons = {}
        self.musica_actual = None
        self.silenci = False
        self.ultim = {}
        self.vol_musica = vol_musica          # 0-1, ho tria el jugador a Opciones
        self.vol_efectes = vol_efectes
        if not AUDIO_OK:
            return
        for nom, vol in self.VOLUMS.items():
            try:
                so = pygame.mixer.Sound(ruta("so", nom + ".ogg"))
                so.set_volume(vol * self.vol_efectes)
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
        fitxer = ruta("musica", nom + ".ogg")
        if not os.path.exists(fitxer):
            # Al navegador només el menú ve dins del paquet: la resta es descarrega en segon pla
            # i sona quan arriba (mentrestant continua la música d'abans).
            DESCARREGUES.prioritzar(nom)
            return
        self._reproduir(fitxer)

    def arribada(self, nom):
        """Una pista acaba de descarregar-se: si és la que toca ara, comença a sonar."""
        if nom == self.musica_actual:
            self._reproduir(ruta("musica", nom + ".ogg"))

    def _reproduir(self, fitxer):
        try:
            pygame.mixer.music.load(fitxer)
            pygame.mixer.music.set_volume(0 if self.silenci else self.vol_musica)
            pygame.mixer.music.play(-1)
        except (OSError, pygame.error) as err:
            print(f"No s'ha pogut reproduir la música {fitxer}: {err}")

    def aturar_musica(self):
        self.musica_actual = None
        if AUDIO_OK:
            pygame.mixer.music.stop()

    def commutar_silenci(self):
        self.silenci = not self.silenci
        if AUDIO_OK:
            pygame.mixer.music.set_volume(0 if self.silenci else self.vol_musica)
            if self.silenci:
                for i in range(pygame.mixer.get_num_channels()):
                    pygame.mixer.Channel(i).stop()


    def canviar_volums(self, musica=None, efectes=None):
        if musica is not None:
            self.vol_musica = max(0.0, min(1.0, musica))
            if AUDIO_OK:
                pygame.mixer.music.set_volume(0 if self.silenci else self.vol_musica)
        if efectes is not None:
            self.vol_efectes = max(0.0, min(1.0, efectes))
            for nom, so in self.sons.items():
                so.set_volume(self.VOLUMS[nom] * self.vol_efectes)


AUDIO = Audio(float(OPCIONS_INICIALS.get("musica", 0.3)), float(OPCIONS_INICIALS.get("efectes", 0.8)))


class DescarregaMusica:
    """Al navegador el paquet inicial només porta la música del menú (càrrega molt més ràpida).
    Les altres pistes es descarreguen d'una en una en segon pla, en l'ordre en què es necessiten."""

    ORDRE = ["sector1", "jefe", "sector2", "sector3", "boss_final", "sector4", "sector5", "final", "supervivencia"]

    def __init__(self):
        self.cua = [n for n in self.ORDRE if not os.path.exists(ruta("musica", n + ".ogg"))]
        self.fallides = set()

    def prioritzar(self, nom):
        if nom in self.cua:
            self.cua.remove(nom)
            self.cua.insert(0, nom)

    async def executar(self):
        if not WEB:
            return
        try:
            import platform as plataforma
            base = str(plataforma.window.location.href).split("#")[0].split("?")[0].rsplit("/", 1)[0]
        except Exception as err:
            print(f"Descàrrega de música no disponible: {err}")
            return
        while self.cua:
            nom = self.cua.pop(0)
            desti = ruta("musica", nom + ".ogg")
            try:
                async with plataforma.fopen(f"{base}/assets/musica/{nom}.ogg", "rb") as f:
                    dades_ogg = f.read()
                if len(dades_ogg) < 1000:
                    raise OSError("fitxer buit")
                with open(desti, "wb") as sortida:
                    sortida.write(dades_ogg)
                AUDIO.arribada(nom)
            except Exception as err:
                print(f"No s'ha pogut descarregar la música {nom}: {err}")
                self.fallides.add(nom)
            await asyncio.sleep(0)


DESCARREGUES = DescarregaMusica()


def musica_escenari(nivell, escenari):
    if (nivell, escenari) in CAPS_FINALS:
        return "boss_final"
    if (nivell, escenari) in CAPS_NORMALS:
        return "jefe"
    return MUSICA_SECTOR[nivell]


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
    txt = T(txt)
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


def dibuixar_cor(surf, x, y, mida, fraccio, perduda=0.0):
    """Dibuixa un cor (fraccio 1 = ple, 0.5 = mig, 0 = buit). `perduda`: vida que s'acaba de perdre (en blanc)."""
    r = mida // 4
    def forma(color, gruix=0):
        pygame.draw.circle(surf, color, (x + r, y + r), r, gruix)
        pygame.draw.circle(surf, color, (x + 3 * r, y + r), r, gruix)
        pygame.draw.polygon(surf, color, [(x, y + r + 1), (x + mida, y + r + 1), (x + mida // 2, y + mida)], gruix)
    forma(GRIS_FOSC)
    if perduda > fraccio:
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(x, y, int(mida * perduda), mida + 1).clip(clip) if clip else None)
        forma((255, 236, 236))
        surf.set_clip(clip)
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
        self.img = text_contorn(T(txt), font, color)

    def actualitzar(self):
        self.y -= 0.8
        self.t += 1
        return self.t >= self.vida

    def dibuixar(self, surf):
        img = self.img
        if self.t < 6:                                   # «pop» en aparèixer
            k = 1.45 - 0.075 * self.t
            img = pygame.transform.scale(img, (int(img.get_width() * k), int(img.get_height() * k)))
        else:
            img.set_alpha(int(255 * min(1.0, 2 * (1 - self.t / self.vida))))
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


def esclat(efectes, x, y, n, colors, vel=(2, 6), mida=(3, 6), vida=(15, 35), gravetat=0.0):
    for _ in range(n):
        a = random.uniform(0, math.tau)
        v = random.uniform(*vel)
        efectes.append(Particula(x, y, math.cos(a) * v, math.sin(a) * v, random.choice(colors),
                                 random.randint(*vida), random.uniform(*mida), gravetat))


def espurnes(efectes, x, y, angle, n, colors, obertura=0.9, vel=(2, 5), vida=(7, 14)):
    """Espurnes dirigides (p. ex. cap enrere des d'on ha impactat una bala)."""
    for _ in range(n):
        a = angle + random.uniform(-obertura, obertura)
        v = random.uniform(*vel)
        efectes.append(Particula(x, y, math.cos(a) * v, math.sin(a) * v, random.choice(colors),
                                 random.randint(*vida), random.uniform(1.5, 2.8), 0.15))


class Beina:
    """Beina expulsada per l'arma: gira, rebota un parell de cops a terra i s'esvaeix."""
    __slots__ = ("x", "y", "vx", "vy", "rot", "vrot", "color", "punta", "llarg", "t", "terra", "bots")

    def __init__(self, x, y, vx, vy, terra, color=(230, 190, 70), punta=(150, 110, 40), llarg=2.5):
        self.x, self.y, self.vx, self.vy, self.terra = x, y, vx, vy, terra
        self.rot = random.uniform(0, math.tau)
        self.vrot = random.uniform(0.25, 0.5) * (1 if vx > 0 else -1)
        self.color, self.punta, self.llarg = color, punta, llarg
        self.t = 0
        self.bots = 0

    def actualitzar(self):
        self.t += 1
        self.vy = min(self.vy + 0.35, 9)
        self.x += self.vx
        self.y += self.vy
        self.rot += self.vrot
        if self.y >= self.terra - 2 and self.vy > 0:
            self.y = self.terra - 2
            if self.bots < 2 and self.vy > 1.5:
                self.vy *= -0.42
                self.vx *= 0.6
                self.vrot *= 0.6
                self.bots += 1
            else:
                self.vy, self.vrot = 0.0, 0.0
                self.vx *= 0.75
                self.rot = 0.0
        return self.t >= 75

    def dibuixar(self, surf):
        if self.t > 58 and self.t % 4 < 2:
            return
        dx, dy = math.cos(self.rot) * self.llarg, math.sin(self.rot) * self.llarg
        a, b = (self.x - dx, self.y - dy), (self.x + dx, self.y + dy)
        pygame.draw.line(surf, self.color, a, b, 2)
        pygame.draw.line(surf, self.punta, b, (self.x + dx * 1.3, self.y + dy * 1.3), 2)


class NumDany:
    """Número de dany que surt d'un enemic. Els cops seguits al mateix enemic se sumen."""

    def __init__(self, x, y, valor):
        self.x, self.y, self.valor, self.t, self.vida = x, y, valor, 0, 42
        self.desv = random.uniform(-0.5, 0.5)
        self.img = None
        self._preparar()

    def sumar(self, valor, x, y):
        self.valor += valor
        self.x, self.y = x, y
        self.t = min(self.t, 4)
        self._preparar()

    def _preparar(self):
        gran = self.valor >= 40
        self.img = text_contorn(str(self.valor), F_HUD if gran else F_MINI, (255, 230, 90) if gran else BLANC)

    def actualitzar(self):
        self.t += 1
        self.y -= 1.4 * max(0.0, 1 - self.t / 24)
        self.x += self.desv
        return self.t >= self.vida

    def dibuixar(self, surf):
        img = self.img
        if self.t < 5:                                   # «pop» en aparèixer
            k = 1.5 - 0.1 * self.t
            img = pygame.transform.scale(img, (int(img.get_width() * k), int(img.get_height() * k)))
        elif self.t > self.vida - 12:
            img.set_alpha(int(255 * (self.vida - self.t) / 12))
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


def text_contorn(txt, font, color, vora=NEGRE):
    """Text amb contorn negre d'1 píxel (llegible sobre qualsevol fons)."""
    base = render(txt, font, vora)
    davant = render(txt, font, color)
    s = pygame.Surface((base.get_width() + 2, base.get_height() + 2), pygame.SRCALPHA)
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2), (0, 0), (2, 2), (0, 2), (2, 0)):
        s.blit(base, (dx, dy))
    s.blit(davant, (1, 1))
    return s


# ---------------------------------------------------------------------------
# HUD: icones pixel art (armes i millores) i panells
# ---------------------------------------------------------------------------
PALETA_ICONA = {"k": (14, 14, 22), "d": (70, 74, 92), "m": (132, 138, 158), "l": (214, 220, 234),
                "w": (120, 74, 40), "W": (166, 108, 60), "g": (54, 44, 40), "r": (214, 52, 52),
                "R": (255, 120, 110), "o": (255, 150, 40), "y": (255, 214, 64), "c": (90, 230, 255)}
DIBUIX_ARMES = {
    "pistola": [
        "..kkkkkkkkkkkkkk",
        ".kllllllllllllak",
        ".kmmmmmmmmmmmmmk",
        ".kddddddddkkkkk.",
        ".kdggkkdk.......",
        "..kggk.kk.......",
        "..kggkkk........",
        ".kgggk..........",
        ".kgggk..........",
        ".kkkkk..........",
    ],
    "escopeta": [
        "........................kk",
        "kkkk.....kkkkkkkkkkkkkkkkk",
        "kWWWkkkkkmmmmmmmmmmmmmmmlk",
        "kwwwwwwwkddddddddddddddddk",
        "kwwwwwwwkkkkkWWWWWWWWkkkk.",
        ".kwwwkkgkk..kwwwwwwwwk....",
        "..kwwk.kk...kkkkkkkkkk....",
        "...kkk....................",
    ],
    "fusell": [
        "...........kkkkkk.........",
        "..........kdaaaadk........",
        "kkkkk.....kkkkkkkk........",
        "kWWWWkkkkkmmmmmmmmmmmmmmlk",
        "kwwwwwwwwkddddddddddkkkkk.",
        "kwwwwkkkkkdkkkkkkkkk......",
        "kkkkk..kgk.kdk............",
        ".......kgk..kdk...........",
        ".......kkk...kkk..........",
    ],
    "minigun": [
        "..kkkkkk..................",
        ".kddddddkkkkkkkkkkkkkkkkk.",
        "kdmmmmmdkmmmmmmmmmmmmmmllk",
        "kdddddddkkkkkkkkkkkkkkkkk.",
        "kdmmmmmdkmmmmmmmmmmmmmmllk",
        "kdddddddkkkkkkkkkkkkkkkkk.",
        "kdmmmmmdkmmmmmmmmmmmmmmllk",
        ".kddaaddkkkkkkkkkkkkkkkkk.",
        "..kkkgk...................",
        "....kgk...................",
        "....kkk...................",
    ],
    "plasma": [
        "......kkkkkkkkkk..........",
        "....kkmmmmmmmmmmkkkk......",
        "..kkddaaaaaaaaaaddmmkkkk..",
        "kkdddalllllllllladdmmmmlk.",
        "kddddaaaaaaaaaaaaddmmmmlk.",
        ".kkddddddddddddddddkkkk...",
        "...kkgkk.kkkkkkk..........",
        "....kgk...................",
        "....kkk...................",
    ],
}
COLOR_ARMA = {"pistola": GROC, "escopeta": (255, 190, 90), "fusell": CIAN, "minigun": TARONJA,
              "plasma": (120, 240, 255)}
DIBUIX_MILLORES = {
    "blindatge": ((110, 170, 255), [
        "kkkkkkkkk", "kllllllmk", "klmmmmmdk", "klmmmmmdk", "klmmmmmdk",
        ".kmmmmmk.", ".kdmmmdk.", "..kdddk..", "...kkk..."]),
    "potencia": (GROC, [
        "....kkkk.", "...kllk..", "..kllk...", ".kllkkkk.", "kllllllk.",
        "kkkkmlk..", "...kmk...", "..kmk....", "..kk....."]),
    "carregadors": ((230, 190, 70), [
        ".k.k.k...", "klklklk..", "kmkmkmk..", "kkkkkkkk.", "kdddddddk",
        "kdlllddk.", "kdddddk..", "kdddddk..", "kkkkkkk.."]),
    "iman": ((214, 52, 52), [
        "kkk...kkk", "klk...klk", "kmk...kmk", "kmk...kmk", "kmmk.kmmk",
        "kmmmkmmmk", ".kmmmmmk.", "..kkkkk..", "........."]),
    "reflexos": (CIAN, [
        "kk..kk...", "klk.klk..", ".klk.klk.", "..klk.klk", "..klk.klk",
        ".klk.klk.", "klk.klk..", "kk..kk...", "........."]),
    "doble_salt": ((170, 176, 196), [
        "..kkkk...", "..kmmk...", "..kmmk...", "..kmmkkk.", ".kmmmmmmk",
        ".kkkkkkkk", "..kokok..", "...kok...", "....k...."]),
}


def pixmap(files, paleta, escala=1):
    w, h = max(len(f) for f in files), len(files)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, f in enumerate(files):
        for x, ch in enumerate(f):
            if ch in paleta:
                s.set_at((x, y), paleta[ch])
    return pygame.transform.scale(s, (w * escala, h * escala)) if escala != 1 else s


def apagar(img, alfa=110, gris=True):
    """Còpia apagada d'una icona (arma bloquejada, millora gastada)."""
    s = img.copy()
    if gris:
        s.fill((90, 90, 110, 255), special_flags=pygame.BLEND_RGBA_MULT)
    s.set_alpha(alfa)
    return s


def crear_icones():
    armes, millores = {}, {}
    for ident, files in DIBUIX_ARMES.items():
        paleta = dict(PALETA_ICONA, a=COLOR_ARMA[ident])
        armes[ident] = {1: pixmap(files, paleta, 1), 2: pixmap(files, paleta, 2)}
        armes[ident]["off"] = apagar(armes[ident][1], 150)
        armes[ident]["blanc"] = silueta_blanca(armes[ident][2])
    for ident, (color, files) in DIBUIX_MILLORES.items():
        paleta = dict(PALETA_ICONA, m=color, l=aclarir(color, 80), d=tuple(c * 6 // 10 for c in color))
        img = pixmap(files, paleta, 2)
        millores[ident] = {"on": img, "off": apagar(img, 120)}
    return armes, millores


_CACHE_PANELL = {}


def panell_hud(surf, rect, vora=(90, 120, 190), alfa=165):
    """Panell semitransparent amb vora pixelada i cantonades marcades (es guarda per mida)."""
    r = pygame.Rect(rect)
    clau = (r.w, r.h, vora, alfa)
    s = _CACHE_PANELL.get(clau)
    if s is None:
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        s.fill((8, 10, 24, alfa))
        fosc = tuple(c // 2 for c in vora)
        pygame.draw.rect(s, (*fosc, 230), s.get_rect(), 1)
        for cx, cy, sx, sy in ((0, 0, 1, 1), (r.w - 1, 0, -1, 1), (0, r.h - 1, 1, -1), (r.w - 1, r.h - 1, -1, -1)):
            pygame.draw.line(s, (*vora, 255), (cx, cy), (cx + sx * 5, cy), 1)
            pygame.draw.line(s, (*vora, 255), (cx, cy), (cx, cy + sy * 5), 1)
        s.fill((0, 0, 0, 0), (0, 0, 1, 1))
        _CACHE_PANELL[clau] = s
    surf.blit(s, r)
    return r


def dibuixar_cadenat(surf, cx, cy, color=(230, 90, 90)):
    pygame.draw.rect(surf, NEGRE, (cx - 5, cy - 2, 11, 9), border_radius=1)
    pygame.draw.rect(surf, color, (cx - 4, cy - 1, 9, 7), border_radius=1)
    pygame.draw.arc(surf, NEGRE, (cx - 4, cy - 8, 9, 10), 0, math.pi, 3)
    pygame.draw.arc(surf, color, (cx - 3, cy - 7, 7, 8), 0, math.pi, 1)
    pygame.draw.rect(surf, NEGRE, (cx, cy + 1, 1, 3))


def fogonazo(surf, x, y, a, llarg, ample, color, nucli=BLANC):
    """Flamarada del canó orientada cap on apunta l'arma."""
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux
    punts = [(x + ux * llarg, y + uy * llarg), (x + ux * llarg * 0.35 + px * ample, y + uy * llarg * 0.35 + py * ample),
             (x - ux * 2, y - uy * 2), (x + ux * llarg * 0.35 - px * ample, y + uy * llarg * 0.35 - py * ample)]
    pygame.draw.polygon(surf, color, punts)
    pygame.draw.circle(surf, nucli, (int(x + ux * llarg * 0.25), int(y + uy * llarg * 0.25)), max(1, int(ample * 0.6)))


ICONES_ARMA, ICONES_MILLORA = crear_icones()


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
# Ambient animat dels escenaris
# ---------------------------------------------------------------------------
AMBIENTS = {
    (0, 0): ("cendra", "ovnis"),
    (0, 1): ("pluja", "ovnis"),
    (0, 2): ("brases", "foc", "explosions"),
    (1, 0): ("espores", "fulles"),
    (1, 1): ("pluja", "espores"),
    (1, 2): ("brases", "foc", "fulles"),
    (2, 0): ("reflectors", "ovnis"),
    (2, 1): ("energia", "espores"),
    (2, 2): ("neu", "llamps"),
    (3, 0): ("estels", "deixalles"),
    (3, 1): ("alarma", "espurnes"),
    (3, 2): ("alarma", "estels", "deixalles"),
    (4, 0): ("espores", "estels"),
    (4, 1): ("espores", "pulsacio"),
    (4, 2): ("espores", "pulsacio", "llamps"),
}
COLOR_ESPORES = {(4, 0): (255, 150, 255), (4, 1): (255, 190, 90), (4, 2): (220, 120, 255)}

_CACHE_LLUM = {}


def llum(radi, color):
    """Cercle de llum difusa (pre-renderitzat i reutilitzat)."""
    clau = (radi, color)
    s = _CACHE_LLUM.get(clau)
    if s is None:
        s = pygame.Surface((radi * 2, radi * 2), pygame.SRCALPHA)
        for r in range(radi, 0, -1):
            a = int(255 * (1 - r / radi) ** 2)
            pygame.draw.circle(s, (*color, a), (radi, radi), r)
        _CACHE_LLUM[clau] = s
    return s


def crear_vinyeta():
    petit = pygame.Surface((80, 60), pygame.SRCALPHA)
    for x in range(80):
        for y in range(60):
            d = math.hypot((x - 39.5) / 40, (y - 29.5) / 30)
            petit.set_at((x, y), (0, 0, 10, int(min(1.0, max(0.0, d - 0.55) / 0.6) ** 1.6 * 150)))
    return pygame.transform.smoothscale(petit, (WIDTH, HEIGHT))


def crear_vinyeta_color(color):
    petit = pygame.Surface((80, 60), pygame.SRCALPHA)
    for x in range(80):
        for y in range(60):
            d = math.hypot((x - 39.5) / 40, (y - 29.5) / 30)
            petit.set_at((x, y), (*color, int(min(1.0, max(0.0, d - 0.35) / 0.7) * 255)))
    return pygame.transform.smoothscale(petit, (WIDTH, HEIGHT))


def crear_resplendor_foc():
    s = pygame.Surface((WIDTH, 220), pygame.SRCALPHA)
    for y in range(220):
        a = int(120 * (y / 220) ** 2)
        pygame.draw.line(s, (255, 110, 30, a), (0, y), (WIDTH, y))
    return s


def crear_ovni_llunya():
    s = pygame.Surface((30, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (40, 46, 70, 210), (0, 4, 30, 7))
    pygame.draw.ellipse(s, (70, 80, 110, 210), (9, 0, 12, 8))
    return s


class Ambient:
    """Efectes de fons i de primer pla que fan que cada escenari sembli viu."""

    def __init__(self, nivell, escenari):
        self.tipus = AMBIENTS.get((nivell, escenari), ())
        self.t = 0
        self.part = []       # partícules: [x, y, vx, vy, vida, mida, fase]
        self.ovnis = []
        self.flaix = 0
        self.llamp = None
        self.explosions = []
        if "pluja" in self.tipus:
            self.pluja = [[random.uniform(0, WIDTH + 100), random.uniform(-HEIGHT, HEIGHT), random.uniform(11, 15)]
                          for _ in range(130)]
        if "neu" in self.tipus:
            self.neu = [[random.uniform(0, WIDTH), random.uniform(0, HEIGHT), random.uniform(0.5, 1.5),
                         random.choice((1, 2, 2, 3)), random.uniform(0, math.tau)] for _ in range(120)]
        self.color_espores = COLOR_ESPORES.get((nivell, escenari), (190, 255, 120))
        self.estels = []
        self.deixalles = [[random.uniform(0, WIDTH), random.uniform(60, 420), random.uniform(-0.4, 0.4),
                           random.uniform(-0.15, 0.15), random.uniform(0, 360), random.uniform(-1.5, 1.5),
                           random.randint(6, 16), random.randint(3, 7)] for _ in range(8)] if "deixalles" in self.tipus else []
        if "espores" in self.tipus:
            self.espores = [[random.uniform(0, WIDTH), random.uniform(80, TERRA_Y), random.uniform(0, math.tau),
                             random.uniform(0.3, 0.8)] for _ in range(26)]

    def actualitzar(self):
        self.t += 1
        t = self.t
        tp = self.tipus
        if "pluja" in tp:
            for g in self.pluja:
                g[0] -= 3
                g[1] += g[2]
                if g[1] > TERRA_Y:
                    if random.random() < 0.25:
                        self.part.append([g[0], TERRA_Y - 1, random.uniform(-1, 1), -random.uniform(1, 2), 8, 1, 0,
                                          (180, 200, 235)])
                    g[0], g[1] = random.uniform(0, WIDTH + 150), random.uniform(-80, -10)
        if "neu" in tp:
            for f in self.neu:
                f[1] += f[2]
                f[0] += math.sin(t * 0.02 + f[4]) * 0.5 - 0.2
                if f[1] > TERRA_Y:
                    f[0], f[1] = random.uniform(0, WIDTH + 40), -5
        if "espores" in tp:
            for e in self.espores:
                e[2] += 0.02
                e[0] += math.cos(e[2] * 1.3) * e[3]
                e[1] += math.sin(e[2]) * e[3] * 0.6 - 0.1
                if e[1] < 60:
                    e[1] = TERRA_Y - 10
                e[0] %= WIDTH
        if "brases" in tp and t % 2 == 0:
            x = random.choice((random.uniform(0, 140), random.uniform(WIDTH - 140, WIDTH), random.uniform(0, WIDTH)))
            self.part.append([x, TERRA_Y, random.uniform(-0.4, 0.4), -random.uniform(0.8, 2.2),
                              random.randint(60, 140), random.choice((2, 2, 3)), random.uniform(0, 6),
                              random.choice(((255, 170, 60), (255, 120, 40), (255, 220, 120)))])
        if "cendra" in tp and t % 5 == 0:
            self.part.append([random.uniform(-50, WIDTH), -5, random.uniform(0.3, 0.9), random.uniform(0.4, 0.9),
                              random.randint(300, 600), random.choice((1, 2)), random.uniform(0, 6), (200, 200, 205)])
        if "fulles" in tp and t % 14 == 0:
            self.part.append([random.uniform(0, WIDTH), -5, random.uniform(-0.3, 0.6), random.uniform(0.6, 1.2),
                              random.randint(400, 700), 3, random.uniform(0, 6),
                              random.choice(((90, 170, 70), (140, 190, 60), (200, 160, 50)))])
        if "ovnis" in tp and (t % 420 == 60 or (not self.ovnis and t % 240 == 0)):
            d = random.choice((-1, 1))
            self.ovnis.append([WIDTH + 40 if d < 0 else -40, random.uniform(30, 150), d * random.uniform(0.6, 1.3),
                               random.uniform(0.6, 1.0)])
        for o in self.ovnis[:]:
            o[0] += o[2]
            if o[0] < -60 or o[0] > WIDTH + 60:
                self.ovnis.remove(o)
        if "explosions" in tp and random.random() < 0.012:
            self.explosions.append([random.uniform(60, WIDTH - 60), random.uniform(250, 470), 0])
        for ex in self.explosions[:]:
            ex[2] += 1
            if ex[2] > 30:
                self.explosions.remove(ex)
        if "llamps" in tp:
            if random.random() < 0.006 and not self.llamp:
                x = random.uniform(100, WIDTH - 100)
                punts = [(x, 0)]
                y = 0
                while y < random.uniform(220, 380):
                    y += random.uniform(20, 45)
                    x += random.uniform(-30, 30)
                    punts.append((x, y))
                self.llamp = [punts, 10]
                self.flaix = 10
            if self.llamp:
                self.llamp[1] -= 1
                if self.llamp[1] <= 0:
                    self.llamp = None
        if "estels" in tp and random.random() < 0.008:
            self.estels.append([random.uniform(100, WIDTH + 200), random.uniform(-20, 160), 0])
        for e in self.estels[:]:
            e[0] -= 9
            e[1] += 4
            e[2] += 1
            if e[2] > 50:
                self.estels.remove(e)
        for d in self.deixalles:
            d[0] = (d[0] + d[2]) % (WIDTH + 40)
            d[1] += d[3]
            d[4] += d[5]
        if "espurnes" in tp and random.random() < 0.03:
            x, y = random.choice((random.uniform(0, WIDTH), random.uniform(0, WIDTH))), random.uniform(60, 380)
            for _ in range(10):
                a = random.uniform(0, math.tau)
                v = random.uniform(1, 4)
                self.part.append([x, y, math.cos(a) * v, math.sin(a) * v, random.randint(8, 18), 2, 0, (255, 255, 160)])
        self.flaix = max(0, self.flaix - 1)
        for p in self.part[:]:
            p[0] += p[2] + (math.sin(t * 0.05 + p[6]) * 0.6 if p[5] == 3 else 0)
            p[1] += p[3]
            p[4] -= 1
            if p[4] <= 0 or p[1] > TERRA_Y + 2 or p[1] < -20:
                self.part.remove(p)

    def dibuixar_fons(self, surf):
        """Darrere de les plataformes i els personatges."""
        t = self.t
        if "reflectors" in self.tipus:
            capa = CAPA_TRANSPARENT
            capa.fill((0, 0, 0, 0))
            for base_x, fase in ((140, 0.0), (WIDTH - 140, 2.1)):
                a = -math.pi / 2 + math.sin(t * 0.012 + fase) * 0.55
                for obertura, alfa in ((0.13, 34), (0.07, 46)):
                    p1 = (base_x + math.cos(a - obertura) * 700, TERRA_Y + math.sin(a - obertura) * 700)
                    p2 = (base_x + math.cos(a + obertura) * 700, TERRA_Y + math.sin(a + obertura) * 700)
                    pygame.draw.polygon(capa, (255, 250, 200, alfa), [(base_x, TERRA_Y), p1, p2])
            surf.blit(capa, (0, 0))
        if "energia" in self.tipus:
            y = (t * 3) % (HEIGHT + 200) - 100
            surf.blit(BANDA_ENERGIA, (0, int(y)))
            if (t // 4) % 50 == 0:                  # petita interferència
                for _ in range(3):
                    gy = random.randint(0, HEIGHT - 10)
                    tira = surf.subsurface(pygame.Rect(0, gy, WIDTH, random.randint(2, 6))).copy()
                    surf.blit(tira, (random.randint(-8, 8), gy))
        for ex in self.explosions:
            k = ex[2] / 30
            radi = int(10 + 50 * k)
            l = llum(max(4, radi), (255, 150, 60))
            l.set_alpha(int(220 * (1 - k)))
            surf.blit(l, l.get_rect(center=(int(ex[0]), int(ex[1]))))
            l.set_alpha(255)
        for e in self.estels:
            k = 1 - e[2] / 50
            pygame.draw.line(surf, (int(200 * k) + 55, int(200 * k) + 55, 255), (e[0], e[1]), (e[0] + 36, e[1] - 16), 2)
            pygame.draw.circle(surf, BLANC, (int(e[0]), int(e[1])), 2)
        for d in self.deixalles:
            pz = pygame.Surface((d[6], d[7]), pygame.SRCALPHA)
            pz.fill((90, 94, 116))
            pygame.draw.line(pz, (140, 144, 165), (0, 0), (d[6], 0))
            pz = pygame.transform.rotate(pz, d[4])
            surf.blit(pz, (int(d[0]) - 20, int(d[1])))
        for o in self.ovnis:
            img = OVNI_LLUNYA
            surf.blit(img, (int(o[0]), int(o[1])))
            if (t // 15) % 2:
                pygame.draw.circle(surf, (255, 90, 90), (int(o[0]) + 15, int(o[1]) + 11), 1)
        if "espores" in self.tipus:
            for e in self.espores:
                br = 0.6 + 0.4 * math.sin(t * 0.08 + e[2] * 3)
                l = llum(9, self.color_espores)
                l.set_alpha(int(170 * br))
                surf.blit(l, (int(e[0]) - 9, int(e[1]) - 9))
                l.set_alpha(255)
                pygame.draw.circle(surf, (230, 255, 190), (int(e[0]), int(e[1])), 1)

    def dibuixar_davant(self, surf):
        """Per sobre de tot (pluja, neu, guspires, llamps) abans de l'HUD."""
        t = self.t
        if "foc" in self.tipus:
            RESPLENDOR_FOC.set_alpha(150 + int(60 * math.sin(t * 0.3)) + random.randint(-25, 25))
            surf.blit(RESPLENDOR_FOC, (0, HEIGHT - 220))
        for p in self.part:
            x, y, mida, color = int(p[0]), int(p[1]), p[5], p[7]
            if color[0] == 255:                       # guspira: amb llum
                l = llum(6, (255, 140, 50))
                surf.blit(l, (x - 6, y - 6))
                pygame.draw.circle(surf, color, (x, y), max(1, mida - 1))
            elif mida == 3:                           # fulla
                ang = math.sin(t * 0.08 + p[6])
                pygame.draw.ellipse(surf, color, (x, y, 5, 3 if ang > 0 else 2))
            else:
                pygame.draw.rect(surf, color, (x, y, mida, mida))
        if "pluja" in self.tipus:
            for g in self.pluja:
                pygame.draw.line(surf, (190, 205, 240), (g[0], g[1]), (g[0] + 3, g[1] - 14), 1)
        if "neu" in self.tipus:
            for f in self.neu:
                pygame.draw.circle(surf, (240, 245, 255), (int(f[0]), int(f[1])), f[3] // 2 + 1 if f[3] > 1 else 1)
        if self.llamp:
            punts = self.llamp[0]
            pygame.draw.lines(surf, (180, 200, 255), False, punts, 5)
            pygame.draw.lines(surf, BLANC, False, punts, 2)
        if "alarma" in self.tipus:
            k = max(0.0, math.sin(t * 0.07))
            if k > 0.05:
                ALARMA.set_alpha(int(110 * k))
                surf.blit(ALARMA, (0, 0))
            for bx in (24, WIDTH - 24):
                a = t * 0.08 + (0 if bx < 100 else math.pi)
                p1 = (bx + math.cos(a - 0.25) * 260, 20 + abs(math.sin(a - 0.25)) * 260)
                p2 = (bx + math.cos(a + 0.25) * 260, 20 + abs(math.sin(a + 0.25)) * 260)
                # el focus es dibuixa en una capa just de la mida del triangle (abans era tota la pantalla)
                punts = [(bx, 20), p1, p2]
                x0, y0 = int(min(p[0] for p in punts)), int(min(p[1] for p in punts))
                x1, y1 = int(max(p[0] for p in punts)) + 2, int(max(p[1] for p in punts)) + 2
                capa = pygame.Surface((max(1, x1 - x0), max(1, y1 - y0)), pygame.SRCALPHA)
                pygame.draw.polygon(capa, (255, 40, 40, 34), [(px - x0, py - y0) for px, py in punts])
                surf.blit(capa, (x0, y0))
                pygame.draw.circle(surf, (255, 80, 80), (bx, 20), 5)
        if "pulsacio" in self.tipus:
            PULSACIO.set_alpha(int(70 + 70 * math.sin(t * 0.05)))
            surf.blit(PULSACIO, (0, 0))
        if self.flaix:
            vel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            vel.fill((220, 230, 255, int(14 * self.flaix)))
            surf.blit(vel, (0, 0))
        surf.blit(VINYETA, (0, 0))


# ---------------------------------------------------------------------------
# Logotip animat (dibuixat amb codi: platet volant, raig tractor i planeta)
# ---------------------------------------------------------------------------
def text_estilitzat(txt, font, dalt, baix, extrusio, vora, profunditat):
    """Text amb degradat, vora fosca i relleu 3D. Retorna (superfície, màscara, desplaçament)."""
    mascara = font.render(txt, False, BLANC).convert_alpha()   # 32 bits: el degradat no es quantitza
    caixa = mascara.get_bounding_rect()
    mascara = mascara.subsurface(caixa).copy()
    w, h = mascara.get_size()
    marge = vora + 2
    out = pygame.Surface((w + 2 * marge, h + 2 * marge + profunditat), pygame.SRCALPHA)
    fosc = font.render(txt, False, (12, 14, 26)).convert_alpha().subsurface(caixa).copy()
    for dx in range(-vora, vora + 1):
        for dy in range(-vora, vora + profunditat + 1):
            if dx * dx + min(dy, 0) ** 2 <= vora * vora + 1:
                out.blit(fosc, (marge + dx, marge + dy))
    ext = font.render(txt, False, extrusio).convert_alpha().subsurface(caixa).copy()
    for i in range(profunditat, 0, -1):
        out.blit(ext, (marge, marge + i))
    degradat = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        k = y / max(1, h - 1)
        pygame.draw.line(degradat, [int(dalt[i] + (baix[i] - dalt[i]) * k) for i in range(3)] + [255], (0, y), (w, y))
    ple = mascara.copy()
    ple.blit(degradat, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(ple, (marge, marge))
    # reflex a la part superior de les lletres
    reflex = pygame.Surface((w, max(1, h // 7)), pygame.SRCALPHA)
    reflex.fill((255, 255, 255, 90))
    brillant = mascara.subsurface((0, 0, w, reflex.get_height())).copy()
    brillant.blit(reflex, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(brillant, (marge, marge))
    return out, mascara, (marge, marge)


def crear_platet(escala):
    """Platet volant en pixel art (48x22) i escalat sense suavitzar."""
    fotos = []
    for encesa in range(3):
        s = pygame.Surface((48, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (60, 200, 255, 90), (14, 0, 20, 14))
        pygame.draw.ellipse(s, (150, 225, 255), (16, 1, 16, 12))
        pygame.draw.ellipse(s, (90, 200, 120), (21, 5, 6, 6))           # l'alienígena
        pygame.draw.rect(s, (20, 60, 30), (22, 7, 1, 1))
        pygame.draw.rect(s, (20, 60, 30), (25, 7, 1, 1))
        pygame.draw.line(s, (235, 250, 255), (19, 3), (22, 2))
        pygame.draw.ellipse(s, (70, 76, 100), (0, 9, 48, 11))
        pygame.draw.ellipse(s, (160, 168, 192), (0, 7, 48, 10))
        pygame.draw.line(s, (220, 225, 240), (6, 9), (42, 9))
        pygame.draw.line(s, (40, 44, 64), (2, 15), (46, 15))
        for i, x in enumerate((7, 15, 24, 33, 41)):
            on = (i + encesa) % 3 == 0
            color = (255, 230, 90) if on else (130, 110, 50)
            pygame.draw.rect(s, color, (x - 1, 12, 3, 2))
        pygame.draw.ellipse(s, (130, 255, 160), (18, 18, 12, 4))
        fotos.append(pygame.transform.scale(s, (48 * escala, 22 * escala)))
    return fotos


_CACHE_PLATET = {}


def crear_platet_cache(escala):
    if escala not in _CACHE_PLATET:
        _CACHE_PLATET[escala] = crear_platet(escala)
    return _CACHE_PLATET[escala]


def crear_planeta(ample, alt):
    """Casquet del planeta Terra vist des de l'espai, en baixa resolució i escalat x2."""
    w, h = ample // 2, alt // 2
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy, r = w // 2, h + int(w * 1.15), int(w * 1.25)
    for i in range(5, 0, -1):                                       # atmosfera
        pygame.draw.circle(s, (80, 170, 255, 18 * i), (cx, cy), r + i * 2)
    pygame.draw.circle(s, (30, 90, 190), (cx, cy), r)
    rnd = random.Random(7)
    terra = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(26):
        bx, by = rnd.uniform(0, w), rnd.uniform(cy - r, cy - r + 40)
        for _ in range(rnd.randint(3, 7)):
            pygame.draw.circle(terra, rnd.choice(((60, 150, 70), (90, 170, 80), (150, 140, 80))),
                               (int(bx + rnd.uniform(-9, 9)), int(by + rnd.uniform(-4, 4))), rnd.randint(2, 6))
    for _ in range(12):                                             # núvols
        bx, by = rnd.uniform(0, w), rnd.uniform(cy - r, cy - r + 40)
        pygame.draw.ellipse(terra, (240, 245, 255, 200), (bx, by, rnd.randint(10, 26), 2))
    clip = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.circle(clip, BLANC, (cx, cy), r - 1)
    terra.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(terra, (0, 0))
    ombra = pygame.Surface((w, h), pygame.SRCALPHA)               # costat nocturn
    for x in range(w):
        a = int(150 * max(0.0, 1 - x / (w * 0.55)) ** 1.5)
        pygame.draw.line(ombra, (0, 0, 20, a), (x, 0), (x, h))
    ombra.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(ombra, (0, 0))
    pygame.draw.circle(s, (170, 220, 255), (cx, cy), r, 1)          # vora il·luminada
    return pygame.transform.scale(s, (w * 2, h * 2))


class Logo:
    """INVASIÓ ALIENÍGENA: platet que abdueix el títol sobre el planeta."""

    def __init__(self, ample=600):
        k = ample / 600
        self.k = k
        self.w = int(600 * k)
        f_gran = carregar_font("VT323-Regular.ttf", max(12, int(132 * k)))
        f_mitja = carregar_font("VT323-Regular.ttf", max(10, int(86 * k)))
        self.titol = text_estilitzat(T("INVASIÓN"), f_gran, (215, 255, 90), (25, 150, 70), (15, 70, 40),
                                     max(2, int(5 * k)), max(2, int(8 * k)))
        self.subtitol = text_estilitzat(T("ALIENÍGENA"), f_mitja, (255, 255, 255), (90, 190, 255), (25, 60, 130),
                                        max(2, int(4 * k)), max(2, int(6 * k)))
        self.lema = carregar_font("PressStart2P-Regular.ttf", max(8, int(13 * k)))
        self.platet = crear_platet(max(1, round(3 * k)))
        # disposició vertical calculada a partir de la mida real dels textos
        self.y_titol = int(64 * k)
        self.y_sub = self.y_titol + self.titol[0].get_height() - int(12 * k)
        self.y_lema = self.y_sub + self.subtitol[0].get_height() + int(10 * k)
        self.y_planeta = self.y_lema + int(10 * k)
        self.planeta = crear_planeta(self.w, int(80 * k))
        self.h = self.y_planeta + self.planeta.get_height()
        self.capa_raig = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.estrelles = [(random.uniform(0, self.w), random.uniform(0, self.h * 0.7), random.uniform(0, 6))
                          for _ in range(14)]

    def _brillantor(self, surf, info, pos, t, retard):
        """Franja de llum que recorre les lletres de tant en tant."""
        _, mascara, (mx, my) = info
        w, h = mascara.get_size()
        cicle = (t + retard) % 300
        x = cicle * (w + 200) / 90 - 100
        if x > w + 100:
            return
        banda = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(banda, (255, 255, 255, 150), [(x, 0), (x + 26 * self.k + 8, 0),
                                                        (x + 26 * self.k + 8 - h * 0.4, h), (x - h * 0.4, h)])
        banda.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(banda, (pos[0] + mx, pos[1] + my))

    def dibuixar(self, surf, centre_x, dalt, t):
        k = self.k
        x0 = int(centre_x - self.w / 2)
        for sx, sy, f in self.estrelles:                          # estrelles que parpellegen
            a = 0.5 + 0.5 * math.sin(t * 0.06 + f)
            if a > 0.55:
                c = int(150 + 105 * a)
                px, py = int(x0 + sx), int(dalt + sy)
                pygame.draw.line(surf, (c, c, 255), (px - 2, py), (px + 2, py))
                pygame.draw.line(surf, (c, c, 255), (px, py - 2), (px, py + 2))
        surf.blit(self.planeta, (x0, int(dalt + self.y_planeta)))
        # platet i raig tractor
        bob = math.sin(t * 0.05) * 5 * k
        plat = self.platet[(t // 10) % 3]
        px = int(centre_x - plat.get_width() / 2 + math.sin(t * 0.021) * 18 * k)
        py = int(dalt + 4 * k + bob)
        raig = self.capa_raig
        raig.fill((0, 0, 0, 0))
        bx = px + plat.get_width() / 2 - x0
        by = py + plat.get_height() - dalt - 4 * k
        fons = self.y_planeta + 22 * k
        pols = 0.5 + 0.5 * math.sin(t * 0.09)
        pygame.draw.polygon(raig, (120, 255, 160, int(34 + 26 * pols)),
                            [(bx - 12 * k, by), (bx + 12 * k, by), (bx + 170 * k, fons), (bx - 170 * k, fons)])
        for i in range(6):                                         # anells que baixen pel raig
            f = ((t * 1.5 + i * 40 * k) % (fons - by)) / (fons - by)
            yy = by + f * (fons - by)
            amp = 12 * k + f * 158 * k
            pygame.draw.line(raig, (190, 255, 210, int(90 * (1 - f))), (bx - amp, yy), (bx + amp, yy), max(1, int(2 * k)))
        surf.blit(raig, (x0, int(dalt)))
        img_t = self.titol[0]
        pos_t = (int(centre_x - img_t.get_width() / 2), int(dalt + self.y_titol))
        surf.blit(img_t, pos_t)
        self._brillantor(surf, self.titol, pos_t, t, 0)
        img_s = self.subtitol[0]
        pos_s = (int(centre_x - img_s.get_width() / 2), int(dalt + self.y_sub))
        surf.blit(img_s, pos_s)
        self._brillantor(surf, self.subtitol, pos_s, t, 150)
        text(surf, T("· JUEGO MILITAR ·"), self.lema, GROC, (int(centre_x), int(dalt + self.y_lema)))
        surf.blit(plat, (px, py))
        l = llum(max(4, int(10 * k)), (130, 255, 160))
        surf.blit(l, l.get_rect(center=(px + plat.get_width() // 2, py + plat.get_height() - int(2 * k))))


# ---------------------------------------------------------------------------
# Interfície
# ---------------------------------------------------------------------------
class Boto:
    def __init__(self, rect, txt, accio, color=BLAU, actiu=True, font=None, color_text=BLANC, invisible=False):
        self.invisible = invisible          # àrea clicable sense dibuix propi (caselles de la botiga)
        self.rect = pygame.Rect(rect)
        self.txt = txt
        self.accio = accio
        self.color = color
        self.actiu = actiu and accio is not None
        self.font = font or F_UI
        self.color_text = color_text

    def hover(self):
        return self.actiu and self.rect.collidepoint(ratoli())

    def dibuixar(self, surf):
        if self.invisible:
            return
        base = self.color if self.actiu else GRIS_FOSC
        color = aclarir(base, 45) if self.hover() else base
        desp = -2 if self.hover() else 0
        r = self.rect.move(0, desp)
        pygame.draw.rect(surf, NEGRE, self.rect.move(0, 4), border_radius=8)
        pygame.draw.rect(surf, color, r, border_radius=8)
        pygame.draw.rect(surf, aclarir(color, 60), r, 2, border_radius=8)
        text(surf, T(self.txt), self.font, self.color_text if self.actiu else GRIS, r.center)

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
class Lliscador:
    """Barra lliscant (0-100%) per als volums."""

    def __init__(self, x, y, amp, valor, en_canvi, en_deixar=None):
        self.rect = pygame.Rect(x, y, amp, 14)
        self.valor = valor
        self.en_canvi = en_canvi
        self.en_deixar = en_deixar
        self.arrossegant = False

    def _posar(self, x):
        self.valor = max(0.0, min(1.0, (x - self.rect.x) / self.rect.width))
        self.en_canvi(self.valor)

    def gestionar(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.inflate(20, 26).collidepoint(ev.pos):
            self.arrossegant = True
            self._posar(ev.pos[0])
            return True
        if ev.type == pygame.MOUSEMOTION and self.arrossegant:
            self._posar(ev.pos[0])
            return True
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.arrossegant:
            self.arrossegant = False
            if self.en_deixar:
                self.en_deixar()
            return True
        return False

    def dibuixar(self, surf):
        pygame.draw.rect(surf, NEGRE, self.rect.move(0, 3), border_radius=7)
        pygame.draw.rect(surf, GRIS_FOSC, self.rect, border_radius=7)
        ple = self.rect.copy()
        ple.width = int(self.rect.width * self.valor)
        if ple.width > 0:
            pygame.draw.rect(surf, CIAN, ple, border_radius=7)
        x = self.rect.x + int(self.rect.width * self.valor)
        hover = self.rect.inflate(20, 26).collidepoint(ratoli()) or self.arrossegant
        pygame.draw.circle(surf, NEGRE, (x, self.rect.centery + 2), 13)
        pygame.draw.circle(surf, BLANC if hover else (210, 220, 240), (x, self.rect.centery), 12)
        pygame.draw.circle(surf, CIAN, (x, self.rect.centery), 6)


class Plataforma:
    """Plataforma fixa, mòbil (`mov` = (amplitud_x, amplitud_y, període)) o fràgil (es trenca si t'hi quedes)."""

    TEMPS_TRENCAR = 50          # fotogrames dret a sobre abans que es trenqui
    TEMPS_TORNAR = 360          # fotogrames fins que torna a aparèixer

    def __init__(self, x, y, w, h=18, terra=False, mov=None, fragil=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.terra = terra
        self.base = (x, y)
        self.mov = mov
        self.fragil = fragil
        self.t = 0
        self.dx = self.dy = 0
        self.esquerda = 0.0
        self.trencada = 0
        self.apareix = 0
        self.surf = self._crear_superficie()

    @property
    def solida(self):
        return self.trencada == 0

    def actualitzar(self, trepitjada):
        """Mou la plataforma i retorna "trencada" el fotograma en què es trenca."""
        self.dx = self.dy = 0
        if self.mov:
            # Anada i tornada a velocitat constant (1 píxel per fotograma) amb una pausa a cada extrem.
            # Abans era un sinus arrodonit a píxels: avançava a batzegades (0 o 1 píxel segons el fotograma)
            # i semblava que el joc anés a menys FPS.
            self.t += 1
            ax, ay = self.mov[0], self.mov[1]
            recorregut = 2 * max(abs(ax), abs(ay))
            pausa = 24
            cicle = 2 * (recorregut + pausa)
            u = (self.t + pausa + recorregut // 2) % cicle     # comença al centre (com abans)
            if u < pausa:
                d = 0
            elif u < pausa + recorregut:
                d = u - pausa
            elif u < 2 * pausa + recorregut:
                d = recorregut
            else:
                d = recorregut - (u - 2 * pausa - recorregut)
            fase = d / recorregut * 2 - 1 if recorregut else 0.0
            nx, ny = round(self.base[0] + ax * fase), round(self.base[1] + ay * fase)
            self.dx, self.dy = nx - self.rect.x, ny - self.rect.y
            self.rect.topleft = (nx, ny)
        if self.fragil:
            self.apareix = max(0, self.apareix - 1)
            if self.trencada:
                self.trencada -= 1
                if self.trencada == 0:
                    self.esquerda = 0.0
                    self.apareix = 30
            elif trepitjada:
                self.esquerda += 1
                if self.esquerda >= self.TEMPS_TRENCAR:
                    self.trencada = self.TEMPS_TORNAR
                    return "trencada"
        return None

    def _crear_superficie(self):
        w, h = self.rect.size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        if self.terra:
            s.fill((28, 30, 44, 235))
            for i in range(-20, w + 20, 24):          # franges de perill
                pygame.draw.polygon(s, (230, 180, 40), [(i, 0), (i + 12, 0), (i + 4, 8), (i - 8, 8)])
            pygame.draw.line(s, (255, 230, 120), (0, 0), (w, 0), 2)
            pygame.draw.line(s, (60, 62, 84), (0, 9), (w, 9), 1)
        elif self.fragil:                             # pedra vella i esquerdada
            pygame.draw.rect(s, (92, 74, 70), (0, 0, w, h), border_radius=3)
            pygame.draw.rect(s, (140, 116, 100), (0, 0, w, 5), border_top_left_radius=3, border_top_right_radius=3)
            pygame.draw.line(s, (40, 30, 30), (0, h - 2), (w, h - 2), 2)
            rnd = random.Random(w * 7 + self.base[0])
            for _ in range(w // 22):
                x0 = rnd.randint(6, w - 6)
                pygame.draw.lines(s, (50, 38, 36), False, [(x0, 1), (x0 + rnd.randint(-4, 4), h // 2),
                                                           (x0 + rnd.randint(-6, 6), h - 3)], 1)
        else:
            pygame.draw.rect(s, (52, 56, 82), (0, 0, w, h), border_radius=4)
            pygame.draw.rect(s, (230, 180, 40), (0, 0, w, 5), border_top_left_radius=4, border_top_right_radius=4)
            pygame.draw.line(s, (255, 230, 120), (2, 0), (w - 3, 0), 1)
            pygame.draw.line(s, (28, 30, 44), (0, h - 2), (w, h - 2), 2)
            for rx in range(10, w - 5, 30):
                pygame.draw.circle(s, (110, 116, 150), (rx, h // 2 + 2), 2)
        return s

    def dibuixar(self, surf):
        if self.trencada:
            return
        if self.mov:                                    # propulsors de les plataformes que suren
            for fx in (0.2, 0.8):
                l = llum(9, (120, 210, 255))
                l.set_alpha(random.randint(120, 200))
                surf.blit(l, l.get_rect(center=(int(self.rect.x + self.rect.w * fx), self.rect.bottom + 3)))
                l.set_alpha(255)
        if self.fragil and (self.esquerda or self.apareix):
            img = self.surf.copy()
            k = self.esquerda / self.TEMPS_TRENCAR
            if k:
                img.fill((255, int(255 - 120 * k), int(255 - 140 * k)), special_flags=pygame.BLEND_RGB_MULT)
            if self.apareix:
                img.set_alpha(int(255 * (1 - self.apareix / 30)))
            tremolor = random.randint(-1, 1) * (k > 0.4)
            surf.blit(img, self.rect.move(tremolor, 0))
            return
        surf.blit(self.surf, self.rect)


class Jugador:
    W, H = 26, 60
    VELOCITAT = 5.0
    SALT = -14.5
    GRAVETAT = 0.75
    CAIGUDA_MAX = 15.0
    DURADA_ESQUIVA = 16         # voltereta: fotogrames que dura (invulnerable)
    RECARREGA_ESQUIVA = 42      # fotogrames fins que es pot tornar a fer
    VEL_ESQUIVA = 10.0

    def __init__(self, vida_max=VIDA_MAX, vel_mult=1.0, salts_extra=0, invulnerabilitat=40):
        self.x = 60.0
        self.y = float(TERRA_Y - self.H)
        self.vx = 0.0
        self.vy = 0.0
        self.vida_max = vida_max
        self.vida = vida_max
        self.velocitat = self.VELOCITAT * vel_mult
        self.salts_extra = salts_extra
        self.salts_restants = salts_extra
        self.temps_invulnerable = invulnerabilitat
        self.terra = True
        self.direccio = 1
        self.coyote = 0          # marge per saltar just després de sortir d'una plataforma
        self.buffer_salt = 0     # salt premut una mica abans d'aterrar
        self.baixar = 0          # travessar plataformes cap avall
        self.invulnerable = 0
        self.pas = 0.0
        self.temps = 0
        self.ombra_y = float(TERRA_Y)
        # estat d'animació
        self.aterratge = 0       # aixafament en tocar terra
        self.retroces = 0        # retrocés del tret
        self.flash_cano = 0      # flamarada del canó
        self.mort_t = 0
        self.events = set()      # "salt", "aterrar", "pas": per crear pols des del joc
        self.suport = None       # plataforma on està (per moure'l amb les plataformes mòbils)
        self.esquiva = 0
        self.recarrega_esquiva = 0
        self.dir_esquiva = 1
        self.esquiva_aire = False
        self.esquiva_nova = False
        self.empenta = 0.0       # retrocés de les armes pesades
        self.factor_vel = 1.0    # la minigun alenteix el soldat mentre dispara
        self.fantasmes = []      # estela de la voltereta
        self.reflexos = vel_mult > 1.0      # millora «Reflejos»: estela en córrer
        self.flash_arma, self.angle_tret, self.flash_max = "pistola", 0.0, 3

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    @property
    def centre(self):
        return self.x + self.W / 2, self.y + self.H / 2

    def canons(self, spr):
        """Posició real de la punta del canó de l'arma (d'allà surten les bales)."""
        cx, peus = self.x + self.W / 2, self.y + self.H
        if not spr:
            return cx + self.direccio * 14, self.y + self.H * 0.38
        return cx + self.direccio * spr.cano_dx, peus + spr.cano_dy

    @property
    def intocable(self):
        return self.invulnerable > 0 or self.esquiva > 0

    def disparat(self, empenta=0.0, arma="pistola", angle=None):
        self.retroces = 4 + (2 if empenta > 1 else 0)
        self.flash_max = 5 if arma in ("escopeta", "plasma") else 3
        self.flash_cano = self.flash_max
        self.flash_arma = arma
        self.angle_tret = angle if angle is not None else (0.0 if self.direccio > 0 else math.pi)
        self.empenta -= self.direccio * empenta

    def esquivar(self, sentit):
        """Voltereta ràpida en la direcció en què et mous (o cap on mires), invulnerable mentre dura."""
        if self.esquiva or self.recarrega_esquiva or (not self.terra and self.esquiva_aire):
            return False
        self.dir_esquiva = sentit or self.direccio
        self.esquiva = self.DURADA_ESQUIVA
        self.recarrega_esquiva = self.RECARREGA_ESQUIVA
        self.esquiva_nova = True
        if not self.terra:
            self.esquiva_aire = True
            self.vy = min(self.vy, -2.5)
        return True

    def demanar_salt(self):
        self.buffer_salt = 8

    def actualitzar(self, esquerra, dreta, salt_mantingut, avall, plataformes, mirar_x):
        self.temps += 1
        self.events.clear()
        if self.esquiva_nova:
            self.events.add("esquiva")
            self.esquiva_nova = False
        if self.esquiva:
            k = self.esquiva / self.DURADA_ESQUIVA
            self.vx = self.dir_esquiva * self.VEL_ESQUIVA * (0.45 + 0.55 * k)
            self.esquiva -= 1
            if not self.terra:
                self.vy = min(self.vy, 1.5)          # a l'aire, la voltereta planeja una mica
        else:
            objectiu = (dreta - esquerra) * self.velocitat * self.factor_vel
            self.vx += (objectiu - self.vx) * 0.35
        if abs(self.vx) < 0.05:
            self.vx = 0.0
        self.recarrega_esquiva = max(0, self.recarrega_esquiva - 1)
        self.direccio = 1 if mirar_x >= self.x + self.W / 2 else -1

        self.coyote = 7 if self.terra else max(0, self.coyote - 1)
        if self.buffer_salt > 0 and self.coyote > 0:
            self.vy = self.SALT
            self.buffer_salt = 0
            self.coyote = 0
            self.terra = False
            self.events.add("salt")
        elif self.buffer_salt > 0 and not self.terra and self.salts_restants > 0 and self.vy > -6:
            self.vy = self.SALT * 0.88                    # doble salt amb els propulsors
            self.buffer_salt = 0
            self.salts_restants -= 1
            self.events.add("doble_salt")
        self.buffer_salt = max(0, self.buffer_salt - 1)
        if not salt_mantingut and self.vy < -4:     # salt variable: deixar anar = salt més curt
            self.vy = -4
        if avall and self.terra and self.y + self.H < TERRA_Y - 1:
            self.baixar = 14
            self.terra = False
        self.baixar = max(0, self.baixar - 1)

        self.x = max(0.0, min(WIDTH - self.W, self.x + self.vx + self.empenta))
        self.empenta *= 0.8
        if abs(self.empenta) < 0.05:
            self.empenta = 0.0
        bottom_abans = self.y + self.H
        estava_a_terra = self.terra
        vy_impacte = self.vy + self.GRAVETAT
        self.vy = min(self.vy + self.GRAVETAT, self.CAIGUDA_MAX)
        self.y += self.vy

        self.terra = False
        self.suport = None
        if self.vy >= 0:
            for p in plataformes:
                if self.baixar and not p.terra:
                    continue
                if (self.x + self.W > p.rect.left and self.x < p.rect.right
                        and bottom_abans <= p.rect.top + 1 and self.y + self.H >= p.rect.top):
                    self.y = float(p.rect.top - self.H)
                    self.vy = 0.0
                    self.terra = True
                    self.suport = p
                    break
        if self.y + self.H > TERRA_Y:                # seguretat: mai per sota del terra
            self.y = float(TERRA_Y - self.H)
            self.vy = 0.0
            self.terra = True
        if self.terra:
            self.salts_restants = self.salts_extra
            self.esquiva_aire = False
        if self.terra and not estava_a_terra and vy_impacte > 3:
            self.aterratge = 7
            self.events.add("aterrar")

        # Superfície que hi ha just a sota (per a l'ombra)
        cx, peus = self.x + self.W / 2, self.y + self.H
        self.ombra_y = min((p.rect.top for p in plataformes
                            if p.rect.left <= cx <= p.rect.right and p.rect.top >= peus - 1),
                           default=float(TERRA_Y))

        if self.terra and abs(self.vx) > 0.6:
            pas_abans = int(self.pas)
            self.pas += abs(self.vx) * 0.055
            if int(self.pas) != pas_abans and int(self.pas) % 3 == 0:
                self.events.add("pas")
        self.invulnerable = max(0, self.invulnerable - 1)
        self.aterratge = max(0, self.aterratge - 1)
        self.retroces = max(0, self.retroces - 1)
        self.flash_cano = max(0, self.flash_cano - 1)

    def fotograma(self, spr):
        if not self.terra:
            return spr.poses["salt" if self.vy < 0 else "caiguda"][0]
        if abs(self.vx) > 0.6:
            n = len(spr.poses["corre"])
            i = int(self.pas) % n
            if (self.vx > 0) != (self.direccio > 0):   # caminar enrere: animació al revés
                i = (n - i) % n
            return spr.poses["corre"][i]
        return spr.poses["quiet"][(self.temps // 35) % 2]

    def dibuixar_ombra(self, surf):
        dist = self.ombra_y - (self.y + self.H)
        if dist > 260:
            return
        f = 1 - max(0.0, dist) / 260
        amp = max(6, int(34 * f))
        ombra = pygame.Surface((amp, max(3, int(8 * f))), pygame.SRCALPHA)
        pygame.draw.ellipse(ombra, (0, 0, 0, int(110 * f)), ombra.get_rect())
        surf.blit(ombra, ombra.get_rect(center=(int(self.x + self.W / 2), int(self.ombra_y) + 1)))

    def dibuixar(self, surf, spr):
        self.dibuixar_ombra(surf)
        if not spr:
            pygame.draw.rect(surf, VERD, self.rect, border_radius=4)
            return
        for img_f, centre_f, vida_f in self.fantasmes:          # estela de la voltereta
            img_f.set_alpha(int(110 * vida_f / 6))
            surf.blit(img_f, img_f.get_rect(center=centre_f))
        self.fantasmes = [(i, c, v - 1) for i, c, v in self.fantasmes if v > 1]
        if self.esquiva:
            img = spr.poses["salt"][0][self.dir_esquiva]
            progres = 1 - self.esquiva / self.DURADA_ESQUIVA
            rot = pygame.transform.rotate(img, -self.dir_esquiva * 360 * progres)
            centre = (int(self.x + self.W / 2), int(self.y + self.H / 2 + 8))
            surf.blit(rot, rot.get_rect(center=centre))
            fantasma = silueta_blanca(rot)
            fantasma.fill((120, 230, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.fantasmes.append((fantasma, centre, 6))
            return
        if self.recarrega_esquiva:                              # indicador de recàrrega de la voltereta
            fr = 1 - self.recarrega_esquiva / self.RECARREGA_ESQUIVA
            pygame.draw.rect(surf, NEGRE, (int(self.x) - 1, int(self.y + self.H) + 5, self.W + 2, 4))
            pygame.draw.rect(surf, CIAN, (int(self.x), int(self.y + self.H) + 6, int(self.W * fr), 2))
        img = self.fotograma(spr)[self.direccio]
        ancora = spr.ancoratge(self.direccio)
        if self.aterratge:                           # aixafament en aterrar
            k = self.aterratge / 7
            nw, nh = int(img.get_width() * (1 + 0.14 * k)), int(img.get_height() * (1 - 0.12 * k))
            ancora *= nw / img.get_width()
            img = pygame.transform.scale(img, (nw, nh))
        cx = self.x + self.W / 2 - self.direccio * (2 if self.retroces > 1 else 0)
        pos = (int(cx - ancora), int(self.y + self.H - img.get_height()))
        if self.invulnerable and (self.invulnerable // 3) % 2 == 0:
            ferit = img.copy()
            ferit.fill((255, 70, 70, 0), special_flags=pygame.BLEND_RGBA_MAX)
            ferit.set_alpha(200)
            surf.blit(ferit, pos)
        else:
            surf.blit(img, pos)
        if self.salts_extra and not self.terra and self.salts_restants > 0:     # propulsors a punt
            for s in (-5, 5):
                fx, fy = self.x + self.W / 2 + s, self.y + self.H + 1
                llarg = 4 + (self.temps % 3)
                pygame.draw.polygon(surf, (120, 220, 255), [(fx - 2, fy), (fx + 2, fy), (fx, fy + llarg)])
                pygame.draw.line(surf, BLANC, (fx, fy), (fx, fy + llarg // 2))
        if self.reflexos and self.terra and abs(self.vx) > 3.5 and self.temps % 4 == 0:     # estela dels reflexos
            fantasma = silueta_blanca(img)
            fantasma.fill((90, 200, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
            self.fantasmes.append((fantasma, (pos[0] + img.get_width() // 2, pos[1] + img.get_height() // 2), 4))
        if self.flash_cano:
            self.dibuixar_fogonazo(surf, *self.canons(spr))

    def dibuixar_fogonazo(self, surf, tx, ty):
        k = self.flash_cano / self.flash_max
        a = self.angle_tret
        arma = self.flash_arma
        if arma == "escopeta":
            l = llum(18, (255, 160, 60))
            surf.blit(l, l.get_rect(center=(int(tx + math.cos(a) * 8), int(ty + math.sin(a) * 8))))
            for d in (-0.38, 0.0, 0.38):
                fogonazo(surf, tx, ty, a + d, 18 * k + 4, 4 * k + 1, (255, 170, 60) if d else (255, 220, 120))
        elif arma == "fusell":
            fogonazo(surf, tx, ty, a, 24 * k + 4, 3, (170, 240, 255))
            fogonazo(surf, tx + math.cos(a) * 6, ty + math.sin(a) * 6, a + math.pi / 2, 6 * k + 2, 1.5, BLANC)
            fogonazo(surf, tx + math.cos(a) * 6, ty + math.sin(a) * 6, a - math.pi / 2, 6 * k + 2, 1.5, BLANC)
        elif arma == "minigun":
            fogonazo(surf, tx, ty, a + random.uniform(-0.15, 0.15), random.uniform(10, 18), random.uniform(3, 5),
                     (255, 170, 50))
        elif arma == "plasma":
            l = llum(16, (120, 240, 255))
            surf.blit(l, l.get_rect(center=(int(tx), int(ty))))
            pygame.draw.circle(surf, (170, 250, 255), (int(tx), int(ty)), int(5 + (1 - k) * 10), 2)
            pygame.draw.circle(surf, BLANC, (int(tx), int(ty)), max(2, int(5 * k)))
        else:
            fogonazo(surf, tx, ty, a, 12 * k + 3, 4 * k + 1, (255, 210, 70))

    def dibuixar_mort(self, surf, spr):
        """El soldat cau d'esquena i s'esvaeix."""
        self.mort_t += 1
        if not spr:
            return
        img = spr.poses["quiet"][0][self.direccio]
        angle = min(90, self.mort_t * 7) * self.direccio
        rot = pygame.transform.rotate(img, angle)
        rot.set_alpha(max(0, 255 - max(0, self.mort_t - 30) * 8))
        surf.blit(rot, rot.get_rect(midbottom=(int(self.x + self.W / 2), int(self.y + self.H) + 4)))


class Bala:
    ESTILS = {
        # radi, color principal
        "pistola": (4, GROC),
        "escopeta": (3, (255, 190, 90)),
        "fusell": (4, CIAN),
        "minigun": (3, TARONJA),
        "plasma": (7, (120, 240, 255)),
        "enemic": (5, VERMELL),
        "boss": (6, MORAT),
        "final": (6, ROSA),
        "nucli": (6, (230, 90, 255)),
    }

    __slots__ = ("x", "y", "vx", "vy", "dany", "radi", "color", "vida", "perfora", "tocats", "estil", "t", "k")

    def __init__(self, x, y, vx, vy, dany, estil, color=None, vida=None, perfora=False, k=0):
        self.x, self.y, self.vx, self.vy, self.dany = x, y, vx, vy, dany
        self.radi, c = self.ESTILS[estil]
        self.color = color or c
        self.vida = vida
        self.perfora = perfora
        self.tocats = set() if perfora else None
        self.estil = estil
        self.t = 0
        self.k = k                 # número de tret (la minigun fa un traçador més brillant cada tres)

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.radi), int(self.y - self.radi), self.radi * 2, self.radi * 2)

    def actualitzar(self):
        self.x += self.vx
        self.y += self.vy
        self.t += 1
        if self.vida is not None:
            self.vida -= 1
            if self.vida <= 0:
                return True
        return self.x < -20 or self.x > WIDTH + 20 or self.y < -20 or self.y > HEIGHT + 20

    def dibuixar(self, surf):
        x, y, c, e = self.x, self.y, self.color, self.estil
        v = math.hypot(self.vx, self.vy) or 1.0
        ux, uy = self.vx / v, self.vy / v
        ix, iy = int(x), int(y)
        fosc = tuple(q // 2 for q in c[:3])
        if e in ("pistola", "fusell", "minigun"):              # traçadors
            if e == "pistola":
                llarg, gruix = 12, 4
            elif e == "fusell":
                llarg, gruix = 26, 3
            else:
                brillant = self.k % 3 == 0
                llarg, gruix = (22, 3) if brillant else (13, 2)
                if brillant:
                    c = aclarir(c, 70)
            cua = (x - ux * llarg, y - uy * llarg)
            pygame.draw.line(surf, fosc, cua, (x, y), gruix + 2)
            pygame.draw.line(surf, c, (x - ux * llarg * 0.7, y - uy * llarg * 0.7), (x, y), gruix)
            pygame.draw.line(surf, BLANC, (x - ux * llarg * 0.35, y - uy * llarg * 0.35), (x, y), 1)
            pygame.draw.circle(surf, BLANC, (ix, iy), 2 if e == "pistola" else 1)
        elif e == "escopeta":                                  # perdigons que s'apaguen
            k = min(1.0, (self.vida or 30) / 12)
            pygame.draw.line(surf, fosc, (x - self.vx * 0.9, y - self.vy * 0.9), (x, y), 2)
            pygame.draw.circle(surf, c, (ix, iy), max(1, round(3 * k)))
            if k > 0.5:
                pygame.draw.circle(surf, BLANC, (ix, iy), 1)
        elif e == "plasma":                                    # bola que batega amb llampecs
            pols = 1 + 0.18 * math.sin(self.t * 0.6)
            l = llum(20, c[:3])
            surf.blit(l, (ix - 20, iy - 20))
            pygame.draw.line(surf, fosc, (x - ux * 16, y - uy * 16), (x, y), 6)
            pygame.draw.circle(surf, c, (ix, iy), int(7 * pols))
            pygame.draw.circle(surf, BLANC, (ix, iy), int(4 * pols))
            for _ in range(2):
                a = random.uniform(0, math.tau)
                punts = [(x, y)]
                for r in (5, 8, 12):
                    a += random.uniform(-0.5, 0.5)
                    punts.append((x + math.cos(a) * r, y + math.sin(a) * r))
                pygame.draw.lines(surf, (200, 250, 255), False, punts, 1)
        else:                                                  # bales enemigues: vora fosca i pols
            r = self.radi
            pols = (self.t // 4) % 2
            l = llum(r + 6, c[:3])
            surf.blit(l, (ix - r - 6, iy - r - 6))
            pygame.draw.line(surf, fosc, (x - ux * r * 2.2, y - uy * r * 2.2), (x, y), r)
            if e == "boss":                                    # rombe que gira
                a = self.t * 0.25
                punts = [(x + math.cos(a + i * math.pi / 2) * (r + 2), y + math.sin(a + i * math.pi / 2) * (r + 2))
                         for i in range(4)]
                pygame.draw.polygon(surf, NEGRE, [(px + (px - x) * 0.25, py + (py - y) * 0.25) for px, py in punts])
                pygame.draw.polygon(surf, c, punts)
                pygame.draw.circle(surf, BLANC, (ix, iy), 2)
            elif e == "final":                                 # anell buit
                pygame.draw.circle(surf, NEGRE, (ix, iy), r + 2)
                pygame.draw.circle(surf, c, (ix, iy), r + 1, 3)
                pygame.draw.circle(surf, BLANC if pols else aclarir(c, 60), (ix, iy), 2)
            elif e == "nucli":                                 # estrella de quatre puntes
                a = -self.t * 0.2
                punts = []
                for i in range(8):
                    rr = (r + 3) if i % 2 == 0 else r * 0.45
                    punts.append((x + math.cos(a + i * math.pi / 4) * rr, y + math.sin(a + i * math.pi / 4) * rr))
                pygame.draw.polygon(surf, NEGRE, punts, 3)
                pygame.draw.polygon(surf, c, punts)
                pygame.draw.circle(surf, BLANC, (ix, iy), 2)
            else:
                pygame.draw.circle(surf, NEGRE, (ix, iy), r + 2)
                pygame.draw.circle(surf, c, (ix, iy), r)
                pygame.draw.circle(surf, (255, 210, 210) if pols else BLANC, (ix, iy), max(1, r // 2))


def ventall(cx, cy, angle, n, obertura, vel, dany, estil):
    if n == 1:
        angles = [angle]
    else:
        angles = [angle - obertura / 2 + obertura * i / (n - 1) for i in range(n)]
    return [Bala(cx, cy, math.cos(a) * vel, math.sin(a) * vel, dany, estil) for a in angles]


def anell_bales(cx, cy, n, vel, dany, estil, gir=0.0, forat=None):
    """Anell de bales; `forat` = (angle, mida) deixa un buit per on es pot esquivar."""
    bales = []
    for i in range(n):
        a = gir + math.tau * i / n
        if forat and abs((a - forat[0] + math.pi) % math.tau - math.pi) < forat[1]:
            continue
        bales.append(Bala(cx, cy, math.cos(a) * vel, math.sin(a) * vel, dany, estil))
    return bales


# fotogrames mirant a l'esquerra (es generen un cop)
FRAMES_TERRA_ESQ = {t: [pygame.transform.flip(f, True, False) for f in fr] for t, fr in FRAMES_TERRA.items()}
COLOR_CARREGA = {"dron": VERMELL, "lloctinent": VERMELL, "cacador": TARONJA, "boss": MORAT, "soldat": CIAN,
                 "escut": CIAN, "kamikaze": VERMELL,
                 "final_comandant": ROSA, "final_nau": ROSA, "final_nucli": (230, 90, 255)}


class Enemic:
    def __init__(self, tipus, vida, nivell, x, y_destinacio, dificultat=None):
        cfg = TIPUS_ENEMIC[tipus]
        dif = dificultat or DIFICULTATS["normal"]
        self.k_cadencia = dif["cadencia"]
        self.tipus = tipus
        self.nivell = nivell
        self.clau = ("boss", nivell) if tipus == "boss" else tipus
        self.sprite = SPR_ENEMIC.get(self.clau)
        if self.sprite:
            self.w, self.h = self.sprite.get_size()
        else:
            self.w, self.h = {"dron": (50, 40), "lloctinent": (66, 54), "cacador": (52, 28), "boss": (84, 84)}.get(tipus, (128, 136))
        self.x = float(x)
        self.y = float(-self.h - random.randint(0, 80))
        self.y_destinacio = y_destinacio
        self.entrant = True
        self.vida = self.vida_max = vida
        self.vmax = cfg["vel"]
        self.vx = random.choice((-1, 1)) * random.uniform(0.8, max(0.9, self.vmax))
        self.vy = random.uniform(-0.5, 0.5)
        self.cadencia = max(45, cfg["cadencia"] - 6 * nivell) if not self.es_final else cfg["cadencia"]
        self.dany = cfg["dany"] + cfg["dany_nivell"] * nivell
        self.vel_bala = cfg["vel_bala"] + (0.4 * nivell if not self.es_final else 0)
        self.monedes = cfg["monedes"]
        self.xp = cfg["xp"]
        self.temps_atac = -random.randint(30, 90)      # no disparen tots alhora
        self.temps_dir = random.randint(0, 60)
        self.atacs = 0
        self.flash = 0
        self.t = random.uniform(0, math.tau)
        self.angle = 0.0
        self.flash_cano = 0
        self.invocacions = []
        # caçador
        self.mode = "patrulla"
        self.temps_mode = 0
        self.dir_envestida = (0.0, 0.0)
        # Nucli de Xylos
        self.fase = 0
        self.temps_fase = 0
        self.gir = 0.0
        self.parpelleig = 0
        self.proper_parpelleig = random.randint(120, 260)
        self.mirada = (0.0, 0.0)
        # enemics de terra (soldat, escut, kamikaze)
        self.terrestre = tipus in ENEMICS_TERRA
        self.dir = random.choice((-1, 1))
        self.suport = None
        self.pas_anim = 0.0
        self.apuntant = 0          # soldat i escut: fotogrames d'avís abans de disparar
        self.durada_apuntar = 1
        self.cop_escut = 0         # escut: el camp d'energia brilla quan atura una bala
        self.armat = 0             # kamikaze: compte enrere de l'explosió
        self.esclatar = False
        self.temps_gir = 0
        self.cop_esquena = False
        if self.terrestre:
            self.vy = 0.0
        # dificultat
        self.dany = max(1, round(self.dany * dif["dany"]))
        if not self.es_final:
            self.cadencia = max(30, int(self.cadencia * self.k_cadencia))

    @property
    def es_final(self):
        return self.tipus.startswith("final_")

    @property
    def es_boss(self):
        return self.tipus == "boss" or self.es_final

    @property
    def furia(self):
        return self.vida < self.vida_max / 2

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x + self.w * 0.1), int(self.y + self.h * 0.12),
                           int(self.w * 0.8), int(self.h * 0.76))

    @property
    def centre(self):
        return self.x + self.w / 2, self.y + self.h / 2

    @property
    def carregant(self):
        """Fracció (0-1) de la càrrega abans d'atacar, per avisar el jugador."""
        if self.tipus == "cacador":
            return min(1.0, self.temps_mode / 35) if self.mode == "carrega" else 0.0
        if self.terrestre:
            if self.tipus == "kamikaze":
                return 1 - self.armat / 45 if self.armat else 0.0
            return 1 - self.apuntant / self.durada_apuntar if self.apuntant else 0.0
        if self.tipus == "final_nucli":
            return min(1.0, self.temps_fase / 50) if self.fase == 2 and self.temps_fase < 50 else 0.0
        falta = self.cadencia - self.temps_atac
        return 1 - falta / 28 if 0 <= falta <= 28 and self.temps_atac > 0 else 0.0

    def ferir(self, dany, empenta=(0.0, 0.0)):
        self.vida -= dany
        self.flash = 5
        # retrocés visual (només el dibuix: la caixa de col·lisió no es mou)
        self.recul = (getattr(self, "recul", (0.0, 0.0))[0] + empenta[0], getattr(self, "recul", (0.0, 0.0))[1] + empenta[1])

    # ----- moviment ---------------------------------------------------------
    def actualitzar(self, jugador, altres, efectes, plataformes=()):
        self.t += 0.05
        self.flash = max(0, self.flash - 1)
        self.flash_cano = max(0, self.flash_cano - 1)
        jx, jy = jugador.centre
        cx, cy = self.centre
        d = math.hypot(jx - cx, jy - cy) or 1
        self.mirada = ((jx - cx) / d, (jy - cy) / d)
        self.parpelleig = max(0, self.parpelleig - 1)
        self.proper_parpelleig -= 1
        if self.proper_parpelleig <= 0:
            self.parpelleig = 14
            self.proper_parpelleig = random.randint(150, 300)
        if self.terrestre:
            return self._actualitzar_terra(jugador, plataformes)
        if self.entrant:
            self.y += 3
            if self.y >= self.y_destinacio:
                self.entrant = False
            return []
        if self.es_final and self.furia and random.random() < 0.25:     # fum dels danys
            efectes.append(Particula(self.x + random.uniform(0.2, 0.8) * self.w, self.y + random.uniform(0.2, 0.7) * self.h,
                                     random.uniform(-0.4, 0.4), random.uniform(-1.4, -0.6),
                                     random.choice(((70, 70, 80), (100, 96, 104), (255, 140, 60))),
                                     vida=random.randint(20, 40), mida=random.uniform(3, 6)))
        if self.tipus == "final_nau":
            self._moure_ruta(320, 100, 0.4, 18)
        elif self.tipus == "final_nucli":
            self._moure_ruta(290, 140, 0.35, 45)
            return self._atacar_nucli(jugador)
        elif self.tipus == "cacador":
            return self._actualitzar_cacador(jugador, altres)
        else:
            self._vagar(jugador, altres)

        self.temps_atac += 1
        if self.temps_atac >= self.cadencia:
            self.temps_atac = 0
            self.atacs += 1
            self.flash_cano = 8
            return self.atacar(jugador)
        return []

    def _moure_ruta(self, amplitud, y_base, vel, alt):
        objectiu_x = WIDTH / 2 - self.w / 2 + math.sin(self.t * vel) * amplitud
        objectiu_y = y_base + math.sin(self.t * vel * 2) * alt
        vx_abans = self.x
        self.x += (objectiu_x - self.x) * 0.05
        self.y += (objectiu_y - self.y) * 0.05
        self.vx = self.x - vx_abans

    def _vagar(self, jugador, altres, separar=True):
        self.temps_dir += 1
        if self.temps_dir > 60:
            self.temps_dir = 0
            self.vx += random.uniform(-1, 1)
            self.vy += random.uniform(-1, 1)
        cx, cy = self.centre
        jx, jy = jugador.centre
        dist = math.hypot(cx - jx, cy - jy)
        if 0 < dist < (170 if self.es_final else 120):
            self.vx += (cx - jx) / dist * 0.12
            self.vy += (cy - jy) / dist * 0.12
        if separar:
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
        self._limits()

    def _limits(self, y_max=None):
        # Sempre dins de la pantalla: abans podien quedar fora on les bales no arribaven
        min_x, max_x = 8, WIDTH - self.w - 8
        min_y, max_y = 40, (y_max if y_max is not None else TERRA_Y - self.h - 110)
        if self.x < min_x:
            self.x, self.vx = min_x, abs(self.vx)
        elif self.x > max_x:
            self.x, self.vx = max_x, -abs(self.vx)
        if self.y < min_y:
            self.y, self.vy = min_y, abs(self.vy)
        elif self.y > max_y:
            self.y, self.vy = max_y, -abs(self.vy)

    def _actualitzar_cacador(self, jugador, altres):
        """Caçador: patrulla, es carrega (avís) i envesteix cap al jugador."""
        self.temps_mode += 1
        if self.mode == "patrulla":
            self._vagar(jugador, altres)
            self.temps_atac += 1
            if self.temps_atac >= self.cadencia:
                self.mode, self.temps_mode = "carrega", 0
                cx, cy = self.centre
                jx, jy = jugador.centre
                d = math.hypot(jx - cx, jy - cy) or 1
                self.dir_envestida = ((jx - cx) / d, (jy - cy) / d)
        elif self.mode == "carrega":
            self.vx *= 0.85
            self.vy *= 0.85
            self.x += self.vx + random.uniform(-1.5, 1.5)
            self.y += self.vy
            if self.temps_mode >= 35:
                self.mode, self.temps_mode = "envestida", 0
                AUDIO.so("envestida", 100)
        elif self.mode == "envestida":
            self.vx, self.vy = self.dir_envestida[0] * 10, self.dir_envestida[1] * 10
            self.x += self.vx
            self.y += self.vy
            self._limits(TERRA_Y - self.h)
            if self.temps_mode >= 26:
                self.mode, self.temps_mode = "patrulla", 0
                self.temps_atac = -random.randint(0, 50)
                self.vx *= 0.25
                self.vy = -abs(self.vy) * 0.3
        return []

    # ----- enemics de terra ---------------------------------------------------
    def _fisica_terra(self, plataformes):
        bottom_abans = self.y + self.h
        self.vy = min(self.vy + 0.6, 12.0)
        self.y += self.vy
        self.x += self.vx
        self.suport = None
        if self.vy >= 0:
            for p in plataformes:
                if (self.x + self.w * 0.75 > p.rect.left and self.x + self.w * 0.25 < p.rect.right
                        and bottom_abans <= p.rect.top + 2 and self.y + self.h >= p.rect.top):
                    self.y = float(p.rect.top - self.h)
                    self.vy = 0.0
                    self.suport = p
                    break
        if self.y + self.h > TERRA_Y:
            self.y, self.vy = float(TERRA_Y - self.h), 0.0
        if self.x < 4:
            self.x, self.dir = 4.0, 1
        elif self.x > WIDTH - self.w - 4:
            self.x, self.dir = float(WIDTH - self.w - 4), -1

    def _vora(self):
        """Cert si el pas següent cauria de la plataforma on és."""
        p = self.suport
        if p is None or p.terra:
            return False
        peu = self.x + self.w / 2 + self.dir * self.w * 0.45
        return peu < p.rect.left or peu > p.rect.right

    def _actualitzar_terra(self, jugador, plataformes):
        jx, jy = jugador.centre
        cx, cy = self.centre
        self.cop_escut = max(0, self.cop_escut - 1)
        mateixa_alcada = abs((jugador.y + jugador.H) - (self.y + self.h)) < 90
        if self.entrant:                           # cauen del cel fins que toquen terra
            self.vx = 0.0
            self._fisica_terra(plataformes)
            if self.suport is not None:
                self.entrant = False
            return []
        bales = []
        if self.tipus == "kamikaze":
            if self.armat:
                self.armat -= 1
                self.vx *= 0.7
                if self.armat == 0:
                    self.esclatar = True
            else:
                if abs(jx - cx) > 6:
                    self.dir = 1 if jx > cx else -1
                # només gira a la vora si el jugador és a la mateixa alçada o més amunt
                if self._vora() and (jugador.y + jugador.H) <= self.y + self.h + 4:
                    self.dir = -self.dir
                self.vx = self.dir * self.vmax
                if math.hypot(jx - cx, jy - cy) < 70:
                    self.armat = 45
                    AUDIO.so("buit", 200)
        else:
            if self.apuntant:
                self.apuntant -= 1
                self.vx = 0.0
                if self.apuntant == 0:
                    bales = self._disparar_terra(jugador)
            else:
                self.temps_atac += 1
                if self.tipus == "escut":
                    self.temps_gir += 1        # es gira a poc a poc: el pots rodejar
                    if self.temps_gir > 80 and (jx > cx) != (self.dir > 0):
                        self.dir, self.temps_gir = -self.dir, 0
                else:
                    self.temps_dir += 1
                    if self.temps_dir > random.randint(140, 260):
                        self.temps_dir = 0
                        self.dir = -self.dir
                if self._vora():
                    self.dir = -self.dir
                self.vx = self.dir * self.vmax
                if self.temps_atac >= self.cadencia and mateixa_alcada and self.suport is not None:
                    if self.tipus == "soldat":
                        self.dir = 1 if jx > cx else -1
                    if (jx > cx) == (self.dir > 0):
                        self.durada_apuntar = self.apuntant = 32 if self.tipus == "soldat" else 40
                        self.temps_atac = 0
        self.pas_anim += abs(self.vx) * 0.09
        self._fisica_terra(plataformes)
        return bales

    def canó_terra(self):
        return (self.x + self.w / 2 + self.dir * self.w * 0.5, self.y + self.h * (0.42 if self.tipus == "soldat" else 0.4))

    def _disparar_terra(self, jugador):
        px, py = self.canó_terra()
        jx, jy = jugador.centre
        angle = math.atan2(jy - py, jx - px)
        base = 0 if self.dir > 0 else math.pi
        dif = (angle - base + math.pi) % math.tau - math.pi
        angle = base + max(-0.3, min(0.3, dif))             # disparen gairebé en horitzontal
        self.flash_cano = 6
        AUDIO.so("enemic", 60)
        if self.tipus == "escut":
            return ventall(px, py, angle, 3, math.radians(14), self.vel_bala, self.dany, "enemic")
        return ventall(px, py, angle, 1, 0, self.vel_bala, self.dany, "enemic")

    def bloqueja(self, bala):
        """L'escut atura les bales que li arriben de cara (el plasma el travessa)."""
        if self.tipus != "escut" or self.entrant or bala.perfora:
            return False
        cx = self.x + self.w / 2
        if (bala.x - cx) * self.dir > 0 and bala.vx * self.dir < 0:
            self.cop_escut = 10
            return True
        return False

    def _dibuixar_terra(self, surf, desplaçament, forçar_flash):
        frames = (FRAMES_TERRA if self.dir > 0 else FRAMES_TERRA_ESQ).get(self.tipus) or []
        cx = self.x + self.w / 2 + desplaçament[0]
        peus = self.y + self.h + desplaçament[1]
        if not frames:
            pygame.draw.rect(surf, MORAT, (self.x, self.y, self.w, self.h))
            return
        camina = int(self.pas_anim) % 4 if abs(self.vx) > 0.1 and not self.entrant else 0
        if self.tipus == "soldat":
            i = 5 if self.flash > 2 else (4 if self.apuntant or self.flash_cano else camina)
        elif self.tipus == "escut":
            i = 4 if self.apuntant or self.flash_cano else camina
        else:
            i = 4 if self.armat and (self.armat // (3 if self.armat < 20 else 6)) % 2 == 0 else camina
        img = frames[min(i, len(frames) - 1)]
        rect = img.get_rect(midbottom=(int(cx), int(peus)))
        if self.tipus == "kamikaze" and self.armat:
            l = llum(int(18 + 30 * (1 - self.armat / 45)), (255, 60, 40))
            surf.blit(l, l.get_rect(center=rect.center))
        surf.blit(img, rect)
        if self.flash or forçar_flash:
            blanc = silueta_blanca(img)
            blanc.set_alpha(200 if forçar_flash else 30 * self.flash)
            surf.blit(blanc, rect)
        if self.tipus == "escut" and not self.entrant:       # camp d'energia frontal
            alt = int(self.h * 1.08)
            camp = pygame.Surface((16, alt), pygame.SRCALPHA)
            br = 1.0 if self.cop_escut else 0.55 + 0.2 * math.sin(self.t * 9)
            pygame.draw.ellipse(camp, (90, 230, 255, int(90 * br)), camp.get_rect())
            pygame.draw.ellipse(camp, (200, 250, 255, int(200 * br)), camp.get_rect(), 2)
            if self.dir < 0:
                camp = pygame.transform.flip(camp, True, False)
            x = rect.right - 6 if self.dir > 0 else rect.left - 10
            surf.blit(camp, (x, int(peus) - alt))
        carrega = self.carregant
        if carrega > 0 and self.tipus != "kamikaze":
            px, py = self.canó_terra()
            l = llum(int(5 + 12 * carrega), (120, 230, 255))
            surf.blit(l, l.get_rect(center=(int(px + desplaçament[0]), int(py + desplaçament[1]))))
        if self.vida < self.vida_max:
            amp = self.w
            pygame.draw.rect(surf, NEGRE, (self.x - 1, self.y - 9, amp + 2, 6))
            pygame.draw.rect(surf, VERD, (self.x, self.y - 8, amp * max(0, self.vida) / self.vida_max, 4))

    def rebotar(self):
        """Després de tocar el jugador, el caçador es retira."""
        self.mode, self.temps_mode = "patrulla", 0
        self.temps_atac = -40
        self.vx, self.vy = -self.vx * 0.4, -abs(self.vy) * 0.4 - 2

    # ----- atacs ------------------------------------------------------------
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
                return anell_bales(cx, cy, 12, v * 0.8, d, "boss", gir=self.atacs * 0.3)
            return ventall(cx, cy, angle, 3, math.radians(24), v * 1.1, d, "boss")
        if self.tipus == "final_nau":
            return self._atacar_nau(jugador, angle)
        # Comandant Suprem: anells giratoris i ràfegues dirigides, més agressiu a mitja vida
        self.cadencia = int((68 if self.furia else 90) * self.k_cadencia)
        if self.atacs % 2 == 1:
            return anell_bales(cx, cy, 30 if self.furia else 24, v, d, "final", gir=self.atacs * 0.13)
        return ventall(cx, cy, angle, 5 if self.furia else 3, math.radians(30), v * 1.4, d, "final")

    def canons_nau(self):
        return [(self.x + self.w * f, self.y + self.h * 0.8) for f in (0.16, 0.5, 0.84)]

    def _atacar_nau(self, jugador, angle):
        """Nau Mare: cortines de bales, canons dirigits i drons de reforç."""
        self.cadencia = int((58 if self.furia else 75) * self.k_cadencia)
        v, d = self.vel_bala, self.dany
        torn = self.atacs % 4
        if torn in (0, 2):
            n = 13 if self.furia else 9
            desplaçament = 0.5 if torn == 2 else 0
            bales = []
            for i in range(n):
                x = self.x + self.w * (i + 0.5 + desplaçament) / (n + 1)
                bales.append(Bala(x, self.y + self.h * 0.75, random.uniform(-0.6, 0.6), v * 0.9, d, "final"))
            return bales
        if torn == 1:
            bales = []
            jx, jy = jugador.centre
            for px, py in self.canons_nau():
                a = math.atan2(jy - py, jx - px)
                bales += ventall(px, py, a, 2 if self.furia else 1, math.radians(10), v * 1.3, d, "final")
            return bales
        if len(self.invocacions) == 0 and (self.furia or self.atacs % 8 == 3):
            self.invocacions = [("dron", 60), ("cacador", 50)] if self.furia else [("dron", 60)]
        cx, cy = self.centre
        return ventall(cx, cy, angle, 7, math.radians(70), v * 1.2, d, "final")

    def _atacar_nucli(self, jugador):
        """Nucli de Xylos: espiral, anells amb buits i la mirada (ràfega dirigida)."""
        self.temps_fase += 1
        cx, cy = self.centre
        v, d = self.vel_bala, self.dany
        bales = []
        if self.fase == 0:                                       # espiral
            if self.temps_fase % 7 == 0:
                braços = 3 if self.furia else 2
                self.gir += 0.23
                for b in range(braços):
                    a = self.gir + b * math.tau / braços
                    bales.append(Bala(cx, cy, math.cos(a) * v, math.sin(a) * v, d, "nucli"))
                AUDIO.so("boss", 120)
            if self.temps_fase >= 240:
                self.fase, self.temps_fase = 1, 0
        elif self.fase == 1:                                     # anells amb un buit
            if self.temps_fase in (1, 50, 100):
                buit = math.atan2(jugador.centre[1] - cy, jugador.centre[0] - cx) + random.uniform(-0.6, 0.6)
                bales = anell_bales(cx, cy, 26 if self.furia else 20, v * 1.1, d, "nucli",
                                    gir=random.uniform(0, 1), forat=(buit, 0.42 if self.furia else 0.55))
                AUDIO.so("boss")
            if self.temps_fase >= 150:
                self.fase, self.temps_fase = 2, 0
        else:                                                    # la mirada
            if self.temps_fase == 50:
                a = math.atan2(jugador.centre[1] - cy, jugador.centre[0] - cx)
                bales = ventall(cx, cy, a, 9, math.radians(50), 6.5, d, "nucli")
                self.flash_cano = 10
                AUDIO.so("explosio")
                if self.furia and not self.invocacions:
                    self.invocacions = [("cacador", 80), ("cacador", 80)]
            if self.temps_fase >= 120:
                self.fase, self.temps_fase = 0, 0
        return bales

    # ----- dibuix -----------------------------------------------------------
    def imatge(self):
        """Sprite d'aquest fotograma (amb animació) i clau per a la memòria cau."""
        if self.tipus == "final_comandant" and FRAMES_COMANDANT:
            i = int(self.t * 20) % len(FRAMES_COMANDANT)
            frames = FRAMES_COMANDANT_FURIA if self.furia and (int(self.t * 20) // 4) % 2 else FRAMES_COMANDANT
            return frames[i], ("comandant", i, frames is FRAMES_COMANDANT_FURIA)
        return self.sprite, self.clau

    def dibuixar(self, surf, desplaçament=(0, 0), forçar_flash=False):
        rx, ry = getattr(self, "recul", (0.0, 0.0))
        if rx or ry:
            desplaçament = (desplaçament[0] + round(rx), desplaçament[1] + round(ry))
            self.recul = (rx * 0.6, ry * 0.6) if abs(rx) + abs(ry) > 0.3 else (0.0, 0.0)
        if self.terrestre:
            self._dibuixar_terra(surf, desplaçament, forçar_flash)
            return
        cx, cy = self.centre
        cx += desplaçament[0]
        cy += desplaçament[1]
        if self.tipus in ("dron", "lloctinent", "cacador", "boss"):           # propulsors
            l = llum(max(8, int(self.w * 0.32)), (120, 210, 255) if self.tipus != "cacador" else (255, 160, 60))
            l.set_alpha(random.randint(110, 190))
            surf.blit(l, l.get_rect(center=(int(cx), int(self.y + self.h * 0.85 + desplaçament[1]))))
            l.set_alpha(255)
        if self.tipus == "final_nau":
            pols = 0.5 + 0.5 * math.sin(self.t * 6)
            l = llum(int(30 + 10 * pols), (200, 120, 255))
            surf.blit(l, l.get_rect(center=(int(cx), int(self.y + self.h * 0.9))))
        img, clau = self.imatge()
        if img is None:
            color = BLANC if self.flash else (VERMELL_FOSC if self.es_boss else MORAT)
            pygame.draw.ellipse(surf, color, (self.x, self.y, self.w, self.h))
            return
        # inclinació segons la velocitat (o la direcció de l'envestida)
        if self.tipus == "cacador":
            objectiu = -math.degrees(math.atan2(self.vy, self.vx)) if abs(self.vx) + abs(self.vy) > 0.5 else 0
            if abs(objectiu) > 90:
                objectiu = objectiu - 180 if objectiu > 0 else objectiu + 180
        elif self.tipus in ("final_nucli", "final_nau"):
            objectiu = 0
        else:
            objectiu = max(-14, min(14, -self.vx * 5))
        self.angle += (objectiu - self.angle) * 0.15
        if self.tipus == "final_nucli":                                      # batec
            k = 1 + 0.035 * math.sin(self.t * 5)
            img = pygame.transform.scale(img, (int(self.w * k), int(self.h * k)))
        elif self.tipus == "final_nau":                                     # sense girar: es mou sencera i neta
            pass
        else:
            img = rotat(img, self.angle, clau)
        if self.tipus == "cacador" and self.vx < -0.5:
            img = pygame.transform.flip(img, True, False)
        rect = img.get_rect(center=(int(cx), int(cy)))
        if self.tipus == "final_comandant" and self.furia:
            aura = llum(int(self.w * 0.75), (255, 40, 60))
            aura.set_alpha(int(110 + 60 * math.sin(self.t * 8)))
            surf.blit(aura, aura.get_rect(center=rect.center))
            aura.set_alpha(255)
        surf.blit(img, rect)
        if self.tipus == "final_nucli":
            self._dibuixar_ull(surf, rect.center, img.get_width() / self.w)
        if self.tipus == "final_nau":
            self._dibuixar_llums_nau(surf, desplaçament)
        if self.flash or forçar_flash:
            blanc = silueta_blanca(img)
            blanc.set_alpha(200 if forçar_flash else (18 if self.es_boss else 30) * self.flash)
            surf.blit(blanc, rect)
        carrega = self.carregant
        if carrega > 0:                                                       # avís abans d'atacar
            color = COLOR_CARREGA.get(self.tipus, VERMELL)
            punt = rect.center
            if self.tipus == "final_nucli":
                punt = (int(rect.centerx + self.mirada[0] * 14), int(rect.centery + self.mirada[1] * 14))
            r = int(6 + 18 * carrega) if not self.es_final else int(10 + 40 * carrega)
            l = llum(max(4, r), color[:3])
            l.set_alpha(int(120 + 120 * carrega))
            surf.blit(l, l.get_rect(center=punt))
            l.set_alpha(255)
            pygame.draw.circle(surf, color, punt, int(r * (1.6 - carrega)) + 2, 1)
        if not self.es_boss and self.vida < self.vida_max:
            amp = self.w
            pygame.draw.rect(surf, NEGRE, (self.x - 1, self.y - 9, amp + 2, 6))
            pygame.draw.rect(surf, VERD, (self.x, self.y - 8, amp * max(0, self.vida) / self.vida_max, 4))

    def _dibuixar_ull(self, surf, centre, escala):
        """L'iris del Nucli segueix el jugador i de tant en tant parpelleja."""
        cx, cy = centre
        rs = 22 * 1.9 * escala
        ix, iy = cx + self.mirada[0] * rs * 0.32, cy + self.mirada[1] * rs * 0.32
        ira = self.fase == 2 and self.temps_fase < 60
        color_iris = (255, 60, 90) if ira or self.furia else (170, 50, 210)
        pygame.draw.circle(surf, tuple(c // 2 for c in color_iris), (int(ix), int(iy)), int(rs * 0.5))
        pygame.draw.circle(surf, color_iris, (int(ix), int(iy)), int(rs * 0.42))
        pygame.draw.circle(surf, (250, 160, 255), (int(ix), int(iy)), int(rs * 0.42), 2)
        amp_pupil = rs * (0.12 if not ira else 0.06)
        pygame.draw.ellipse(surf, (20, 0, 20), (ix - amp_pupil, iy - rs * 0.32, amp_pupil * 2, rs * 0.64))
        pygame.draw.circle(surf, BLANC, (int(ix - rs * 0.15), int(iy - rs * 0.16)), max(2, int(rs * 0.07)))
        if self.parpelleig:
            k = 1 - abs(self.parpelleig - 7) / 7
            alt = rs * 2 * k
            pygame.draw.ellipse(surf, (110, 50, 130), (cx - rs - 1, cy - rs - 1, rs * 2 + 2, max(2, alt)))
            pygame.draw.ellipse(surf, (60, 20, 70), (cx - rs - 1, cy - rs - 1, rs * 2 + 2, max(2, alt)), 2)

    def _dibuixar_llums_nau(self, surf, desplaçament):
        n = 9
        for i in range(n):
            x = self.x + self.w * (i + 1) / (n + 1) + desplaçament[0]
            y = self.y + self.h * 0.6 + desplaçament[1]
            encesa = (int(self.t * 12) - i) % n < 2
            pygame.draw.circle(surf, (255, 230, 120) if encesa else (110, 90, 60), (int(x), int(y)), 2)
        if self.flash_cano:
            for px, py in self.canons_nau():
                l = llum(14, (255, 90, 120))
                surf.blit(l, l.get_rect(center=(int(px + desplaçament[0]), int(py + desplaçament[1]))))


class Resta:
    """Restes d'un enemic abatut: cauen girant amb fum i esclaten a terra."""

    def __init__(self, enemic):
        self.img = enemic.sprite
        self.x, self.y = enemic.centre
        self.vx = enemic.vx * 0.5 + random.uniform(-1.2, 1.2)
        self.vy = -2.5
        self.angle = 0.0
        self.gir = random.choice((-1, 1)) * random.uniform(6, 12)
        self.t = 0

    def actualitzar(self, joc):
        self.t += 1
        self.vy += 0.35
        self.x += self.vx
        self.y += self.vy
        self.angle += self.gir
        if self.t % 3 == 0:
            joc.efectes.append(Particula(self.x, self.y, random.uniform(-0.3, 0.3), random.uniform(-1.2, -0.4),
                                         random.choice(((60, 60, 66), (95, 92, 100))), vida=24, mida=4))
        if self.y >= TERRA_Y - 8 or self.t > 70:
            esclat(joc.efectes, self.x, min(self.y, TERRA_Y - 8), 22, [TARONJA, VERMELL, GROC, BLANC],
                   vel=(2, 6), mida=(3, 6), vida=(15, 35))
            joc.efectes.append(Anell(self.x, min(self.y, TERRA_Y - 8), TARONJA, creix=3.5, vida=20))
            joc.tremolor = max(joc.tremolor, 5)
            AUDIO.so("impacte", 60)
            return True
        return False

    def dibuixar(self, surf):
        if not self.img:
            return
        img = pygame.transform.rotate(self.img, self.angle)
        img.fill((150, 140, 140, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


class MortCap:
    """Seqüència de mort dels caps: explosions encadenades i una gran explosió final."""

    def __init__(self, enemic):
        self.e = enemic
        self.t = 0
        self.durada = 150 if enemic.es_final else 90

    def actualitzar(self, joc):
        self.t += 1
        e = self.e
        if self.t % 6 == 0:
            x = e.x + random.uniform(0.1, 0.9) * e.w
            y = e.y + random.uniform(0.1, 0.9) * e.h
            esclat(joc.efectes, x, y, 14, [TARONJA, VERMELL, GROC, BLANC], vel=(1.5, 5), mida=(3, 6), vida=(12, 28))
            joc.efectes.append(Anell(x, y, BLANC, creix=3, vida=14))
            joc.tremolor = max(joc.tremolor, 6)
            AUDIO.so("impacte", 80)
        e.y += 0.25
        if self.t >= self.durada:
            cx, cy = e.centre
            esclat(joc.efectes, cx, cy, 110, [TARONJA, VERMELL, GROC, BLANC, MORAT], vel=(2, 11), mida=(3, 8), vida=(25, 60))
            for creix, vida in ((5, 26), (8, 30), (11, 34)):
                joc.efectes.append(Anell(cx, cy, BLANC if creix == 8 else TARONJA, creix=creix, vida=vida))
            joc.tremolor = 20
            joc.flaix = 14
            AUDIO.so("explosio")
            return True
        return False

    def dibuixar(self, surf):
        sacseig = (random.randint(-4, 4), random.randint(-3, 3))
        self.e.dibuixar(surf, sacseig, forçar_flash=(self.t // 5) % 2 == 0)


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

    def actualitzar(self, plataformes, iman=None):
        self.anim += 0.1
        atret = False
        if iman:                                   # millora "Imant": l'ítem vola cap al jugador
            (jx, jy), radi = iman
            dx, dy = jx - (self.x + 12), jy - (self.y + 12)
            d = math.hypot(dx, dy)
            if 0 < d < radi:
                atret = True
                self.caient = False
                self.x += dx / d * 5
                self.y += dy / d * 5
        if getattr(self, "atret", False) and not atret:
            self.caient, self.vy = True, 0.0       # si deixa d'atreure'l (ja no el necessites), torna a caure
        self.atret = atret
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
# Perills dels escenaris
# ---------------------------------------------------------------------------
class Zona:
    """Toll d'àcid (sempre actiu), terra electrificat o sortida de gas (s'activen per torns, amb avís)."""

    DANY = {"acid": 6, "electric": 10, "gas": 8}
    ACTIU = {"electric": 100, "gas": 130}       # fotogrames actius de cada cicle
    AVIS = 60

    def __init__(self, tipus, x, w, periode=0, desfase=0):
        self.tipus, self.x, self.w = tipus, x, w
        self.periode = periode
        self.desfase = desfase
        alt = 230 if tipus == "gas" else 10
        self.rect = pygame.Rect(x, TERRA_Y - alt + (4 if tipus != "gas" else 0), w, alt)
        self.t = 0

    def _fase(self):
        return (self.t + self.desfase) % self.periode if self.periode else 0

    @property
    def actiu(self):
        if self.tipus == "acid":
            return True
        return self._fase() >= self.periode - self.ACTIU[self.tipus]

    @property
    def avis(self):
        if self.tipus == "acid":
            return False
        f = self._fase()
        inici = self.periode - self.ACTIU[self.tipus]
        return inici - self.AVIS <= f < inici

    def toca(self, jugador):
        if self.tipus == "gas":
            return jugador.rect.inflate(-8, -8).colliderect(self.rect)
        peus = jugador.y + jugador.H
        cx = jugador.x + jugador.W / 2
        return peus >= TERRA_Y - 2 and self.x + 4 < cx < self.x + self.w - 4

    def dibuixar(self, surf, t, efectes):
        x, w = self.x, self.w
        if self.tipus == "acid":
            ona = math.sin(t * 0.08) * 2
            pygame.draw.ellipse(surf, (40, 120, 30), (x - 4, TERRA_Y - 6 + ona * 0.3, w + 8, 14))
            pygame.draw.ellipse(surf, (110, 230, 60), (x, TERRA_Y - 5, w, 10))
            pygame.draw.ellipse(surf, (200, 255, 140), (x + w * 0.2, TERRA_Y - 4, w * 0.35, 3))
            if random.random() < 0.12:
                efectes.append(Particula(x + random.uniform(6, w - 6), TERRA_Y - 3, 0, random.uniform(-1.2, -0.5),
                                         random.choice(((150, 255, 90), (90, 200, 50))), vida=22, mida=3))
        elif self.tipus == "electric":
            actiu, avis = self.actiu, self.avis
            color = (90, 96, 130) if not actiu else (150, 220, 255)
            pygame.draw.rect(surf, (36, 38, 56), (x, TERRA_Y - 3, w, 10))
            for k in range(x + 4, x + w - 8, 16):                    # plaques metàl·liques amb ratlles
                pygame.draw.line(surf, (70, 64, 30) if not actiu else (120, 200, 255), (k, TERRA_Y + 6), (k + 8, TERRA_Y - 2), 3)
            pygame.draw.rect(surf, color, (x, TERRA_Y - 3, w, 10), 2)
            if not actiu:
                for k in range(x + 10, x + w - 6, 40):
                    pygame.draw.polygon(surf, GROC, [(k, TERRA_Y - 1), (k + 5, TERRA_Y - 10), (k + 10, TERRA_Y - 1)])
                    pygame.draw.line(surf, NEGRE, (k + 5, TERRA_Y - 7), (k + 5, TERRA_Y - 4))
            if avis and (t // 6) % 2 == 0:
                pygame.draw.rect(surf, GROC, (x, TERRA_Y - 3, w, 10), 2)
            if actiu:
                l = llum(16, (120, 200, 255))
                for k in range(3):                                  # arcs elèctrics
                    px = x + random.uniform(0, w)
                    punts = [(px, TERRA_Y)]
                    for _ in range(4):
                        punts.append((punts[-1][0] + random.uniform(-9, 9), punts[-1][1] - random.uniform(5, 11)))
                    pygame.draw.lines(surf, (210, 245, 255), False, punts, 2)
                    surf.blit(l, l.get_rect(center=(int(px), TERRA_Y - 10)))
        else:                                                      # gas
            pygame.draw.rect(surf, (50, 56, 50), (x + w // 2 - 22, TERRA_Y - 6, 44, 8), border_radius=2)
            for k in range(4):
                pygame.draw.line(surf, (20, 24, 20), (x + w // 2 - 16 + k * 10, TERRA_Y - 5), (x + w // 2 - 16 + k * 10, TERRA_Y))
            if self.avis and random.random() < 0.3:
                efectes.append(Particula(x + w / 2 + random.uniform(-14, 14), TERRA_Y - 8, random.uniform(-0.3, 0.3),
                                         random.uniform(-1.5, -0.6), (150, 210, 120), vida=20, mida=4))

    def dibuixar_davant(self, surf, t):
        if self.tipus != "gas" or not self.actiu:
            return
        capa = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        for k in range(9):
            y = (self.rect.h - (t * 3 + k * 37) % self.rect.h)
            r = int(self.w * 0.45 + 8 * math.sin(t * 0.1 + k))
            pygame.draw.circle(capa, (140, 220, 110, 70), (self.w // 2 + int(10 * math.sin(t * 0.05 + k * 2)), y), r)
        surf.blit(capa, self.rect)


class Caiguda:
    """Runa o obús de morter: primer surt una marca a terra i després cau."""

    AVIS = 70

    def __init__(self, tipus, x, superficie):
        self.tipus, self.x, self.sup = tipus, x, superficie
        self.t = 0
        self.y = -30.0
        self.vy = 4.0
        self.angle = random.uniform(0, 360)

    def actualitzar(self):
        self.t += 1
        if self.t > self.AVIS:
            self.vy += 0.5
            self.y += self.vy
            self.angle += 9
        return self.t > self.AVIS and self.y >= self.sup - 6

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 12, int(self.y) - 12, 24, 24)

    def dibuixar(self, surf):
        k = min(1.0, self.t / self.AVIS)
        if (self.t // 5) % 2 == 0 or self.t > self.AVIS:             # marca a terra
            amp = int(16 + 24 * k)
            marca = pygame.Surface((amp * 2, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(marca, (255, 60, 40, 150), marca.get_rect(), 2)
            pygame.draw.ellipse(marca, (0, 0, 0, int(60 + 60 * k)), marca.get_rect().inflate(-amp, -4))
            surf.blit(marca, marca.get_rect(center=(int(self.x), int(self.sup) + 1)))
        if self.t <= self.AVIS:
            return
        if self.tipus == "runa":
            punts = []
            for i in range(6):
                a = math.radians(self.angle + i * 60)
                r = 13 if i % 2 else 9
                punts.append((self.x + math.cos(a) * r, self.y + math.sin(a) * r))
            pygame.draw.polygon(surf, (120, 108, 100), punts)
            pygame.draw.polygon(surf, (60, 54, 50), punts, 2)
        else:
            pygame.draw.line(surf, (255, 160, 60), (self.x, self.y - 26), (self.x, self.y - 8), 3)
            pygame.draw.ellipse(surf, (50, 50, 60), (self.x - 7, self.y - 12, 14, 24))
            pygame.draw.circle(surf, (255, 60, 40), (int(self.x), int(self.y) + 6), 3)


class Perills:
    """Peligros de cada escenario (vegeu "perills" a dades.py)."""

    DANY_CAIGUDA = {"runa": 10, "morter": 14}

    def __init__(self, specs):
        self.zones = []
        self.caigudes = []
        self.generadors = []          # [tipus, interval, compte enrere]
        self.t = 0
        for spec in specs or ():
            tipus = spec[0]
            if tipus in ("runa", "morter"):
                self.generadors.append([tipus, spec[1], random.randint(80, spec[1])])
            elif tipus == "acid":
                self.zones += [Zona("acid", x, w) for x, w in spec[1]]
            else:
                n = len(spec[1])
                self.zones += [Zona(tipus, x, w, spec[2], i * spec[2] // n) for i, (x, w) in enumerate(spec[1])]

    def actualitzar(self, joc):
        self.t += 1
        for z in self.zones:
            z.t = self.t
        j = joc.jugador
        if joc.fase == "jugant":
            for g in self.generadors:
                g[2] -= 1
                if g[2] <= 0:
                    g[2] = int(g[1] * random.uniform(0.7, 1.3))
                    x = max(30, min(WIDTH - 30, j.x + j.W / 2 + random.uniform(-170, 170)))
                    sup = min((p.rect.top for p in joc.solides() if p.rect.left <= x <= p.rect.right), default=TERRA_Y)
                    self.caigudes.append(Caiguda(g[0], x, sup))
            for z in self.zones:
                if z.actiu and not j.intocable and z.toca(j):
                    joc.ferir_jugador(joc.dany_dificultat(Zona.DANY[z.tipus]))
        for c in self.caigudes[:]:
            impacte = c.actualitzar()
            if c.t > c.AVIS and joc.fase == "jugant" and not j.intocable and c.rect.colliderect(j.rect):
                impacte = True
            if impacte:
                self.caigudes.remove(c)
                radi = 40 if c.tipus == "runa" else 58
                colors = [(150, 140, 130), (110, 100, 96), BLANC] if c.tipus == "runa" else [TARONJA, VERMELL, GROC, BLANC]
                esclat(joc.efectes, c.x, c.y, 18, colors, vel=(1.5, 5), mida=(3, 6), vida=(14, 30), gravetat=0.2)
                joc.efectes.append(Anell(c.x, min(c.y, c.sup), colors[0], creix=3, vida=16))
                joc.tremolor = max(joc.tremolor, 5)
                AUDIO.so("impacte" if c.tipus == "runa" else "explosio", 80)
                jx, jy = j.x + j.W / 2, j.y + j.H - 10
                if joc.fase == "jugant" and not j.intocable and math.hypot(jx - c.x, jy - min(c.y, c.sup)) < radi:
                    joc.ferir_jugador(joc.dany_dificultat(self.DANY_CAIGUDA[c.tipus]))

    def dibuixar(self, surf, efectes):
        for z in self.zones:
            z.dibuixar(surf, self.t, efectes)

    def dibuixar_davant(self, surf):
        for z in self.zones:
            z.dibuixar_davant(surf, self.t)
        for c in self.caigudes:
            c.dibuixar(surf)


# ---------------------------------------------------------------------------
# Ràdio: missatges amb retrat durant els escenaris
# ---------------------------------------------------------------------------
class Radio:
    def __init__(self):
        self.cua = []
        self.actual = None          # [qui, text, t]

    def afegir(self, missatges, retard=0):
        for qui, txt in missatges:
            self.cua.append([qui, txt, -retard])
            retard = 0

    def buidar(self):
        self.cua.clear()
        self.actual = None

    def actualitzar(self):
        if self.actual is None and self.cua:
            self.actual = self.cua.pop(0)
        if self.actual is None:
            return
        self.actual[2] += 1
        if self.actual[2] == 1:
            AUDIO.so("click")
        if self.actual[2] > len(self.actual[1]) * 1.3 + 150:
            self.actual = None

    def dibuixar(self, surf):
        if self.actual is None or self.actual[2] <= 0:
            return
        qui, txt, t = self.actual
        txt = T(txt)
        entrada = min(1.0, t / 10)
        caixa = pygame.Rect(12, 80, 500, 76)
        caixa.x = int(-caixa.w + (caixa.w + 12) * entrada)
        capa = pygame.Surface(caixa.size, pygame.SRCALPHA)
        capa.fill((6, 10, 22, 205))
        surf.blit(capa, caixa)
        color = MORAT if qui == "ment" else CIAN
        pygame.draw.rect(surf, color, caixa, 2, border_radius=4)
        frames = RETRATS.get(qui) or []
        mostrats = int(t * 1.3)
        parlant = mostrats < len(txt)
        if frames:
            img = frames[1 if parlant and (t // 5) % 2 else 0]
            surf.blit(img, (caixa.x + 6, caixa.y + 6))
            if (t // 40) % 2 == 0 or qui == "ment":                 # interferències
                for k in range(2):
                    y = caixa.y + 6 + random.randint(0, 60)
                    pygame.draw.line(surf, (255, 255, 255, 40), (caixa.x + 6, y), (caixa.x + 69, y))
        text(surf, T(NOMS_RADIO.get(qui, qui)).upper(), F_MINI, color, (caixa.x + 80, caixa.y + 12), ancora="midleft")
        restants = mostrats                       # les línies es calculen amb el text sencer: no salten
        for k, linia in enumerate(ajustar_linies(txt, F_TEXT_PP, caixa.w - 92)[:3]):
            if restants <= 0:
                break
            text(surf, linia[:restants], F_TEXT_PP, BLANC, (caixa.x + 80, caixa.y + 22 + k * 18), ancora="topleft")
            restants -= len(linia) + 1


# ---------------------------------------------------------------------------
# Pantalles de text (narrativa, victòria i derrota)
# ---------------------------------------------------------------------------
class PantallaText:
    def __init__(self, titol, cos, color_titol, botons, fons, pista=None, peu=()):
        self.pista = T(pista) if pista else None
        self.peu = [(T(l), c) for l, c in peu]      # línies extra sota el text: [(text, color), ...]
        self.titol = T(titol)
        cos = T(cos)
        self.color_titol = color_titol
        self.linies = ajustar_linies(cos, F_TEXT, WIDTH - 180)   # es calcula una vegada: el text no "salta"
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
        text(surf, self.titol, F_SUBTITOL, self.color_titol, (WIDTH // 2, 62))
        alt = len(self.linies) * 34 + 36
        panell = pygame.Rect(60, 100, WIDTH - 120, alt)
        capa = pygame.Surface(panell.size, pygame.SRCALPHA)
        capa.fill((8, 10, 24, 200))
        surf.blit(capa, panell)
        pygame.draw.rect(surf, self.color_titol, panell, 2, border_radius=6)
        restants = int(self.mostrats)
        y = panell.top + 18
        cursor = (90, y)
        for linia in self.linies:
            if restants <= 0:
                break
            tros = linia[:restants]
            restants -= len(linia)
            text(surf, tros, F_TEXT, BLANC, (90, y), ancora="topleft")
            cursor = (90 + F_TEXT.size(tros)[0] + 4, y + 4)
            y += 34
        if not self.complet and (pygame.time.get_ticks() // 300) % 2:
            pygame.draw.rect(surf, CIAN, (cursor[0], cursor[1], 10, 24))
        for i, (linia, color) in enumerate(self.peu):
            text(surf, linia, F_TEXT_P, color, (WIDTH // 2, panell.bottom + 22 + i * 26))
        for b in self.botons:
            b.dibuixar(surf)
        pista = self.pista or ("Clic / ESPACIO para continuar" if self.complet else "Clic / ESPACIO para ver todo el texto")
        text(surf, pista, F_MINI, GRIS, (WIDTH // 2, HEIGHT - 22))


# ---------------------------------------------------------------------------
# Joc
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Animación inicial: cuenta la historia en cinco escenas dibujadas con código
# ---------------------------------------------------------------------------
def silueta_ciutat(ample, alt, rnd, color, finestres=True, trencada=False, color_finestra=(255, 220, 140)):
    """Silueta de edificios; si está 'trencada', los techos quedan rotos e irregulares."""
    s = pygame.Surface((ample, alt), pygame.SRCALPHA)
    x = -10
    while x < ample:
        w = rnd.randint(34, 80)
        h = rnd.randint(int(alt * 0.35), alt - 6)
        top = alt - h
        if trencada:
            punts = [(x, alt), (x, top + rnd.randint(0, 30))]
            for k in range(1, 5):
                punts.append((x + w * k / 5, top + rnd.randint(0, 45)))
            punts += [(x + w, top + rnd.randint(0, 30)), (x + w, alt)]
            pygame.draw.polygon(s, color, punts)
        else:
            pygame.draw.rect(s, color, (x, top, w, h))
            if rnd.random() < 0.3:
                pygame.draw.rect(s, color, (x + w // 2 - 2, top - 18, 4, 18))
        if finestres:
            for fy in range(top + 10, alt - 8, 12):
                for fx in range(x + 6, x + w - 6, 10):
                    if rnd.random() < (0.35 if not trencada else 0.08):
                        s.set_at((fx, fy), color_finestra)
                        s.set_at((fx + 1, fy), color_finestra)
                        s.set_at((fx, fy + 1), color_finestra)
                        s.set_at((fx + 1, fy + 1), color_finestra)
        x += w + rnd.randint(-4, 6)
    return s


def cel_degradat(dalt, baix, alt=HEIGHT):
    s = pygame.Surface((WIDTH, alt))
    for y in range(alt):
        k = y / (alt - 1)
        pygame.draw.line(s, [int(dalt[i] + (baix[i] - dalt[i]) * k) for i in range(3)], (0, y), (WIDTH, y))
    return s


class Intro:
    """Cinemàtica dibuixada amb codi: la introducció i les escenes que segueixen cada cap final."""

    ETIQUETES = {"terra": "AÑO 2139", "invasio": "LA INVASIÓN", "ruines": "2139 - 2147",
                 "nexus": "PROYECTO NEXUS", "despertar": "AÑO 2147", "caiguda": "LA CIMA",
                 "senyal": "LA SEÑAL", "llancament": "DESPEGUE", "explosio_nau": "ÓRBITA", "portal": "EL PORTAL",
                 "apagada": "XYLOS", "portals": "LA TIERRA", "retorn": "EL REGRESO"}

    def __init__(self, en_acabar, escenes=None):
        self.en_acabar = en_acabar
        self.escenes = escenes or INTRO
        self.i = 0
        self.saltada = False
        self.boto_saltar = Boto((WIDTH - 156, HEIGHT - 40, 140, 30), "Saltar  >>", self.saltar, GRIS_FOSC, font=F_MINI)
        rnd = random.Random(21)
        self.estrelles = [(rnd.uniform(0, WIDTH), rnd.uniform(0, 300), rnd.uniform(0, 6)) for _ in range(160)]
        self.cel_nit = cel_degradat((4, 6, 22), (40, 26, 70))
        self.cel_alba = cel_degradat((70, 30, 40), (240, 130, 70))
        self.cel_sortida = cel_degradat((40, 60, 110), (255, 190, 120))
        self.ciutat = silueta_ciutat(WIDTH + 40, 230, rnd, (16, 16, 30))
        self.ciutat_lluny = silueta_ciutat(WIDTH + 40, 260, rnd, (34, 28, 52), finestres=False)
        self.runes = silueta_ciutat(WIDTH + 200, 240, rnd, (30, 18, 22), trencada=True, color_finestra=(255, 140, 60))
        self.runes_lluny = silueta_ciutat(WIDTH + 200, 280, rnd, (90, 44, 44), finestres=False, trencada=True)
        self.platets = crear_platet(1)
        self.foc = [(rnd.uniform(40, WIDTH - 40), rnd.uniform(HEIGHT - 210, HEIGHT - 165)) for _ in range(8)]
        self.portals = [(220, 110, 64, 0), (610, 78, 86, 45), (830, 160, 46, 90)]
        self.preparar_escena()

    # ----- control ------------------------------------------------------
    def preparar_escena(self):
        self.t = 0
        self.escena, cos = self.escenes[self.i]
        cos = T(cos)
        self.linies = ajustar_linies(cos, F_TEXT, WIDTH - 120)
        self.total = sum(len(l) for l in self.linies)
        self.mostrats = 0.0
        self.particules = []
        self.ovnis = []
        # temps per llegir-ho tot amb calma: el text no es pot accelerar, només saltar la cinemàtica
        self.durada = max(360, int(self.total / 0.9) + max(170, int(self.total * 2.2)))

    def seguent(self):
        if self.i < len(self.escenes) - 1:
            self.i += 1
            self.preparar_escena()
        else:
            self.en_acabar()

    def saltar(self):
        self.saltada = True
        self.en_acabar()

    def actualitzar(self):
        self.t += 1
        self.mostrats = min(self.total, self.mostrats + 0.9)
        getattr(self, "_act_" + self.escena, lambda: None)()
        for p in self.particules[:]:
            if p.actualitzar():
                self.particules.remove(p)
        if self.t >= self.durada and self.mostrats >= self.total:
            self.seguent()

    # ----- escenas -------------------------------------------------------
    def _estrelles(self, surf):
        for x, y, f in self.estrelles:
            a = 0.5 + 0.5 * math.sin(self.t * 0.05 + f)
            c = int(120 + 135 * a)
            surf.set_at((int(x), int(y)), (c, c, min(255, c + 30)))

    def _portal(self, surf, x, y, r, gir):
        if r < 2:
            return
        l = llum(int(r * 1.9), (170, 70, 255))
        surf.blit(l, l.get_rect(center=(x, y)))
        for k in range(4):
            rr = r * (1 - k * 0.18)
            caixa = pygame.Rect(0, 0, rr * 2, rr * 0.7)
            caixa.center = (x, y)
            color = (220, 150, 255) if k % 2 == 0 else (120, 50, 210)
            inici = gir * (1 if k % 2 else -1) + k
            pygame.draw.arc(surf, color, caixa, inici, inici + 4.2, max(1, int(3 - k * 0.5)))
        nucli = pygame.Rect(0, 0, r * 1.1, r * 0.34)
        nucli.center = (x, y)
        pygame.draw.ellipse(surf, (20, 0, 40), nucli)

    def _dibuixar_terra(self, surf):
        surf.blit(self.cel_nit, (0, 0))
        self._estrelles(surf)
        pygame.draw.circle(surf, (225, 225, 235), (90, 80), 26)
        pygame.draw.circle(surf, (190, 190, 205), (98, 74), 7)
        for x, y, rmax, retard in self.portals:
            r = rmax * max(0.0, min(1.0, (self.t - retard) / 110))
            if r > 6:
                raig = CAPA_TRANSPARENT
                raig.fill((0, 0, 0, 0))
                pygame.draw.polygon(raig, (190, 110, 255, 30), [(x - r * 0.4, y), (x + r * 0.4, y),
                                                                (x + r * 1.4, HEIGHT - 130), (x - r * 1.4, HEIGHT - 130)])
                surf.blit(raig, (0, 0))
            self._portal(surf, x, y, r, self.t * 0.05)
        surf.blit(self.ciutat_lluny, (-20, HEIGHT - 300))
        surf.blit(self.ciutat, (-20 + math.sin(self.t * 0.01) * 4, HEIGHT - 230))

    def _act_invasio(self):
        if self.t % 7 == 0 and self.t < self.durada - 40:
            x, y, r, _ = random.choice(self.portals)
            ang = random.uniform(0.3, 2.8)
            self.ovnis.append([x, y, math.cos(ang) * random.uniform(1.5, 3.5), math.sin(ang) * random.uniform(0.5, 2.2),
                               random.uniform(0.5, 1.0)])
        for o in self.ovnis[:]:
            o[0] += o[2]
            o[1] += o[3]
            if o[0] < -60 or o[0] > WIDTH + 60 or o[1] > HEIGHT:
                self.ovnis.remove(o)
        if self.t % 13 == 0:
            x = random.uniform(20, WIDTH - 20)
            y = random.uniform(HEIGHT - 220, HEIGHT - 120)
            esclat(self.particules, x, y, 16, [TARONJA, VERMELL, GROC, BLANC], vel=(1, 4), mida=(2, 5), vida=(15, 35))
            self.particules.append(Anell(x, y, TARONJA, creix=3, vida=16))

    def _dibuixar_invasio(self, surf):
        surf.blit(self.cel_nit, (0, 0))
        self._estrelles(surf)
        vermell = CAPA_TRANSPARENT
        vermell.fill((160, 30, 30, min(90, self.t // 3)))
        surf.blit(vermell, (0, 0))
        for x, y, r, _ in self.portals:
            self._portal(surf, x, y, r, self.t * 0.08)
        surf.blit(self.ciutat_lluny, (-20, HEIGHT - 300))
        for o in self.ovnis:
            img = pygame.transform.scale(self.platets[(self.t // 8) % 3], (int(48 * o[4]), int(22 * o[4])))
            if o[1] > 220 and int(o[0]) % 3 == 0:
                raig = CAPA_TRANSPARENT
                raig.fill((0, 0, 0, 0))
                pygame.draw.polygon(raig, (120, 255, 160, 40), [(o[0] - 4, o[1] + 8), (o[0] + 4, o[1] + 8),
                                                                (o[0] + 30, HEIGHT), (o[0] - 30, HEIGHT)])
                surf.blit(raig, (0, 0))
            surf.blit(img, img.get_rect(center=(int(o[0]), int(o[1]))))
        surf.blit(self.ciutat, (-20, HEIGHT - 230))
        for p in self.particules:
            p.dibuixar(surf)

    def _act_ruines(self):
        if self.t % 3 == 0:
            x, y = random.choice(self.foc)
            self.particules.append(Particula(x + random.uniform(-6, 6), y, random.uniform(0.2, 0.7), random.uniform(-1.4, -0.6),
                                             random.choice(((60, 52, 56), (84, 74, 76), (40, 34, 38))),
                                             vida=random.randint(80, 140), mida=random.uniform(8, 16)))

    def _dibuixar_ruines(self, surf):
        surf.blit(self.cel_alba, (0, 0))
        pygame.draw.circle(surf, (255, 200, 150), (720, 215), 44)
        surf.blit(self.runes_lluny, (-60 - (self.t * 0.15) % 60, HEIGHT - 330))
        for p in self.particules:
            p.dibuixar(surf)
        surf.blit(self.runes, (-80 - (self.t * 0.3) % 80, HEIGHT - 240))
        for x, y in self.foc:
            l = llum(26 + random.randint(-3, 3), (255, 120, 40))
            surf.blit(l, l.get_rect(center=(int(x), int(y))))
        for k in range(3):                                   # drones buscando supervivientes
            x = (self.t * (0.8 + k * 0.3) + k * 260) % (WIDTH + 100) - 50
            y = 120 + k * 40 + math.sin(self.t * 0.04 + k) * 10
            cono = CAPA_TRANSPARENT
            cono.fill((0, 0, 0, 0))
            a = math.sin(self.t * 0.03 + k) * 0.4
            pygame.draw.polygon(cono, (255, 255, 200, 40), [(x, y + 6), (x + math.sin(a) * 300 - 50, HEIGHT),
                                                            (x + math.sin(a) * 300 + 50, HEIGHT)])
            surf.blit(cono, (0, 0))
            surf.blit(self.platets[(self.t // 8 + k) % 3], (int(x) - 24, int(y) - 11))

    def _act_nexus(self):
        if self.t % 4 == 0:
            self.particules.append(Particula(random.uniform(WIDTH // 2 - 60, WIDTH // 2 + 60), 330, random.uniform(-0.2, 0.2), -random.uniform(1, 2.2),
                                             (170, 255, 200), vida=110, mida=random.uniform(2, 4)))

    def _dibuixar_nexus(self, surf):
        surf.fill((10, 14, 26))
        for x in range(0, WIDTH, 80):
            pygame.draw.rect(surf, (18, 24, 40), (x + 4, 0, 72, 380))
            pygame.draw.line(surf, (30, 40, 66), (x + 4, 0), (x + 4, 380))
        pygame.draw.rect(surf, (24, 28, 44), (0, 380, WIDTH, HEIGHT - 380))
        pygame.draw.line(surf, (60, 70, 110), (0, 380), (WIDTH, 380), 2)
        # cápsula
        caps = pygame.Rect(WIDTH // 2 - 80, 64, 160, 276)
        verd = self.t > self.durada * 0.6
        color_liquid = (40, 200, 120) if not verd else (90, 255, 160)
        liquid = pygame.Surface(caps.size, pygame.SRCALPHA)
        liquid.fill((*color_liquid, 70))
        surf.blit(liquid, caps)
        spr = sprites_jugador("pistola")
        if spr:
            img = spr.poses["quiet"][0][1]
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            surf.blit(img, img.get_rect(center=(caps.centerx, caps.centery + math.sin(self.t * 0.05) * 6)))
        for p in self.particules:
            p.dibuixar(surf)
        y_scan = caps.top + (self.t * 2) % caps.height
        pygame.draw.line(surf, (160, 255, 220), (caps.left + 4, y_scan), (caps.right - 4, y_scan), 2)
        pygame.draw.rect(surf, (120, 140, 170), caps, 4, border_radius=26)
        pygame.draw.rect(surf, (70, 80, 110), (caps.left - 14, caps.bottom - 6, caps.width + 28, 30), border_radius=6)
        pygame.draw.rect(surf, (70, 80, 110), (caps.left - 14, caps.top - 20, caps.width + 28, 26), border_radius=6)
        # monitores
        for mx, titol in ((110, "INMUNIDAD NEURAL"), (WIDTH - 290, "SINCRONIZACIÓN")):
            mon = pygame.Rect(mx, 110, 180, 120)
            pygame.draw.rect(surf, (8, 20, 24), mon)
            pygame.draw.rect(surf, (60, 120, 130), mon, 2)
            text(surf, titol, F_TEXT_PP, (120, 255, 200), (mon.centerx, mon.top + 16), ombra=False)
            if mx < WIDTH // 2:
                valor = "100%"
            else:
                valor = f"{min(100, int(self.t / (self.durada * 0.6) * 100))}%"
            text(surf, valor, F_TITOL, (120, 255, 200) if valor == "100%" else GROC, (mon.centerx, mon.centery + 16), ombra=False)
        punts = []
        for k in range(60):                                   # pulso cardiaco
            x = 110 + k * 3
            fase = (k + self.t // 2) % 30
            y = 280 - (26 if fase == 10 else -14 if fase == 12 else 0)
            punts.append((x, y))
        pygame.draw.lines(surf, (90, 255, 140), False, punts, 2)

    def _dibuixar_despertar(self, surf):
        surf.blit(self.cel_sortida, (0, 0))
        y_sol = 300 - min(120, self.t * 0.5)
        l = llum(110, (255, 200, 120))
        surf.blit(l, l.get_rect(center=(700, int(y_sol))))
        pygame.draw.circle(surf, (255, 230, 170), (700, int(y_sol)), 40)
        surf.blit(self.runes_lluny, (-60, HEIGHT - 330))
        sol = HEIGHT - 172
        pygame.draw.rect(surf, (40, 30, 34), (0, sol, WIDTH, HEIGHT - sol))
        for x in range(0, WIDTH, 22):
            pygame.draw.polygon(surf, (56, 42, 44), [(x, sol), (x + 12, sol - 8 - (x * 7) % 9), (x + 22, sol)])
        # escotilla del búnker
        pygame.draw.rect(surf, (60, 64, 70), (40, sol - 40, 120, 44))
        obert = min(1.0, self.t / 60)
        pygame.draw.rect(surf, (20, 22, 26), (52, sol - 32, 96 * obert, 30))
        spr = sprites_jugador("pistola")
        if spr:
            x = min(WIDTH // 2 - 10, -40 + self.t * 2.2)
            if x < WIDTH // 2 - 10:
                frame = spr.poses["corre"][(self.t // 5) % len(spr.poses["corre"])][1]
                if self.t % 8 == 0:
                    self.particules.append(Particula(x, sol - 2, -1, -0.6, (120, 100, 90), vida=20, mida=3))
            else:
                frame = spr.poses["quiet"][(self.t // 35) % 2][1]
            surf.blit(frame, frame.get_rect(midbottom=(int(x), sol + 2)))
        for p in self.particules:
            p.dibuixar(surf)
        if self.t > 130:
            LOGO_MENU.dibuixar(surf, WIDTH // 2, 8, self.t)

    # ----- escenes de després dels caps finals -----------------------------
    def _fons(self, surf, clau):
        fons = FONS_NIVELLS.get(clau)
        if fons:
            surf.blit(fons, (-20, -10))
        else:
            surf.blit(self.cel_nit, (0, 0))

    def _soldat(self, surf, x, peus, pose="quiet", direccio=1):
        spr = sprites_jugador("pistola")
        if not spr:
            return
        if pose == "corre":
            img = spr.poses["corre"][(self.t // 5) % len(spr.poses["corre"])][direccio]
        else:
            img = spr.poses["quiet"][(self.t // 35) % 2][direccio]
        surf.blit(img, img.get_rect(midbottom=(int(x), int(peus))))

    def _explosio(self, x, y, mida=1.0):
        esclat(self.particules, x, y, int(14 * mida), [TARONJA, VERMELL, GROC, BLANC], vel=(1, 4 * mida),
               mida=(2, 5), vida=(15, 35))
        self.particules.append(Anell(x, y, BLANC if mida > 1 else TARONJA, creix=2.5 * mida, vida=16))

    def _act_caiguda(self):
        if 20 < self.t < 110 and self.t % 9 == 0:
            self._explosio(WIDTH * 0.62 + random.uniform(-60, 60), 250 + random.uniform(-60, 60))

    def _dibuixar_caiguda(self, surf):
        self._fons(surf, (2, 2))
        img = FRAMES_COMANDANT[(self.t // 3) % len(FRAMES_COMANDANT)] if FRAMES_COMANDANT else None
        cx, base = int(WIDTH * 0.62), 420
        if self.t > 120:                                   # raig cap al cel
            k = min(1.0, (self.t - 120) / 40)
            amp = int(10 + 26 * k + 4 * math.sin(self.t * 0.4))
            raig = CAPA_TRANSPARENT
            raig.fill((0, 0, 0, 0))
            pygame.draw.rect(raig, (255, 90, 220, 90), (cx - amp, 0, amp * 2, int(base - 60)))
            pygame.draw.rect(raig, (255, 220, 250, 200), (cx - amp // 4, 0, amp // 2, int(base - 60)))
            surf.blit(raig, (0, 0))
            l = llum(70, (255, 100, 230))
            surf.blit(l, l.get_rect(center=(cx, int(base - 90))))
        if img:
            enfonsar = min(1.0, max(0.0, (self.t - 60) / 80))
            alt = max(4, int(img.get_height() * (1 - 0.55 * enfonsar)))
            cos = pygame.transform.scale(img, (img.get_width(), alt))
            if self.t < 110 and (self.t // 6) % 2 == 0:
                cos = tenyir(cos, (255, 255, 255), 120)
            surf.blit(cos, cos.get_rect(midbottom=(cx + random.randint(-2, 2) * (self.t < 110), base)))
        self._soldat(surf, WIDTH * 0.25, 492)
        for p in self.particules:
            p.dibuixar(surf)

    def _dibuixar_senyal(self, surf):
        self._fons(surf, (3, 0))
        k = min(1.0, self.t / 60)
        raig = CAPA_TRANSPARENT
        raig.fill((0, 0, 0, 0))
        pygame.draw.polygon(raig, (255, 100, 230, 110), [(150, HEIGHT), (190, HEIGHT), (WIDTH // 2 + 20, 150),
                                                          (WIDTH // 2 - 20, 150)])
        surf.blit(raig, (0, 0))
        nau = SPR_ENEMIC.get("final_nau")
        if nau and self.t > 50:
            gran = pygame.transform.scale(nau, (nau.get_width() * 2, nau.get_height() * 2))
            alfa = min(255, (self.t - 50) * 4)
            gran.set_alpha(alfa)
            y = 70 + math.sin(self.t * 0.03) * 6
            surf.blit(gran, gran.get_rect(center=(WIDTH // 2, int(y + 110))))
            if alfa > 200:
                for i in range(9):                                  # llums que s'encenen
                    x = WIDTH // 2 - 200 + 400 * (i + 1) / 10
                    encesa = (self.t // 6 - i) % 9 < 3
                    pygame.draw.circle(surf, (255, 230, 120) if encesa else (110, 90, 60), (int(x), int(y + 140)), 3)
        if self.t < 60:
            vel = CAPA_TRANSPARENT
            vel.fill((0, 0, 0, int(200 * (1 - k))))
            surf.blit(vel, (0, 0))

    def _act_llancament(self):
        if self.t > 150 and self.t % 2 == 0:
            x, y = self._pos_nau_robada()
            self.particules.append(Particula(x + random.uniform(-16, 16), y + 30, random.uniform(-0.6, 0.6),
                                             random.uniform(1.5, 3.5), random.choice((CIAN, BLANC, (130, 255, 160))),
                                             vida=30, mida=random.uniform(3, 6)))

    def _pos_nau_robada(self):
        x, y = 690, 452
        if self.t > 150:
            k = (self.t - 150) / 60
            y -= 40 * k + 60 * k * k
            x += 30 * k * k
        return x, y

    def _dibuixar_llancament(self, surf):
        self._fons(surf, (2, 0))
        plat = crear_platet_cache(3)[(self.t // 8) % 3]
        x, y = self._pos_nau_robada()
        if self.t < 150:
            sx = min(640, 80 + self.t * 4.2)
            self._soldat(surf, sx, 492, "corre" if sx < 640 else "quiet")
        for p in self.particules:
            p.dibuixar(surf)
        if self.t > 140:
            l = llum(40, (130, 255, 160))
            surf.blit(l, l.get_rect(center=(int(x), int(y + 28))))
        surf.blit(plat, plat.get_rect(center=(int(x), int(y))))

    def _act_explosio_nau(self):
        if self.t < 170 and self.t % 5 == 0:
            self._explosio(WIDTH // 2 + random.uniform(-200, 200), 230 + random.uniform(-60, 60), 1.6)
        if self.t == 170:
            for _ in range(5):
                self._explosio(WIDTH // 2 + random.uniform(-60, 60), 230 + random.uniform(-40, 40), 2.2)

    def _dibuixar_explosio_nau(self, surf):
        self._fons(surf, (3, 0))
        nau = SPR_ENEMIC.get("final_nau")
        if nau:
            gran = pygame.transform.scale(nau, (nau.get_width() * 2, nau.get_height() * 2))
            w, h = gran.get_size()
            cx, cy = WIDTH // 2, 230
            if self.t < 170:
                sac = (random.randint(-3, 3), random.randint(-3, 3))
                surf.blit(gran, gran.get_rect(center=(cx + sac[0], cy + sac[1])))
            else:
                k = (self.t - 170) / 60
                for meitat, sentit in ((gran.subsurface((0, 0, w // 2, h)).copy(), -1),
                                       (gran.subsurface((w // 2, 0, w - w // 2, h)).copy(), 1)):
                    rot = pygame.transform.rotate(meitat.convert_alpha(), -sentit * 12 * k)
                    rot.set_alpha(max(0, 255 - int(60 * k)))
                    surf.blit(rot, rot.get_rect(center=(int(cx + sentit * (w // 4 + 50 * k)), int(cy + 40 * k * k))))
        for p in self.particules:
            p.dibuixar(surf)
        if 168 < self.t < 190:
            vel = CAPA_TRANSPARENT
            vel.fill((255, 255, 255, int(255 * (1 - (self.t - 168) / 22))))
            surf.blit(vel, (0, 0))

    def _dibuixar_portal(self, surf):
        surf.blit(self.cel_nit, (0, 0))
        self._estrelles(surf)
        r = min(150, self.t * 1.6)
        self._portal(surf, WIDTH // 2 + 120, 220, r, self.t * 0.06)
        plat = crear_platet_cache(2)[(self.t // 8) % 3]
        if self.t > 90:
            k = min(1.0, (self.t - 90) / 150)
            escala = max(0.05, 1 - k)
            img = pygame.transform.scale(plat, (max(1, int(plat.get_width() * escala)), max(1, int(plat.get_height() * escala))))
            x = 60 + (WIDTH // 2 + 120 - 60) * k
            y = 330 - (330 - 220) * k
            if k < 1:
                surf.blit(img, img.get_rect(center=(int(x), int(y))))
        if 235 < self.t < 265:
            vel = CAPA_TRANSPARENT
            vel.fill((230, 200, 255, int(220 * (1 - abs(self.t - 250) / 15))))
            surf.blit(vel, (0, 0))

    def _dibuixar_apagada(self, surf):
        self._fons(surf, (4, 2))
        k = min(1.0, self.t / 200)
        nucli = SPR_ENEMIC.get("final_nucli")
        if nucli:
            gran = pygame.transform.scale(nucli, (nucli.get_width() * 2, nucli.get_height() * 2))
            centre = (WIDTH // 2, 230)
            surf.blit(gran, gran.get_rect(center=centre))
            rs = gran.get_width() * 0.29
            alt = rs * 2 * k                                       # la parpella es tanca
            pygame.draw.ellipse(surf, (110, 50, 130), (centre[0] - rs - 2, centre[1] - rs - 2, rs * 2 + 4, max(2, alt)))
            pygame.draw.ellipse(surf, (110, 50, 130), (centre[0] - rs - 2, centre[1] + rs + 2 - max(2, alt), rs * 2 + 4,
                                                       max(2, alt)))
        vel = CAPA_TRANSPARENT
        vel.fill((0, 0, 8, int(200 * k)))
        surf.blit(vel, (0, 0))

    def _dibuixar_portals(self, surf):
        surf.blit(self.cel_alba, (0, 0))
        surf.blit(self.ciutat_lluny, (-20, HEIGHT - 300))
        for i, (x, y, r, _) in enumerate(self.portals):
            tanca = 40 + i * 70
            rr = r * max(0.0, min(1.0, 1 - (self.t - tanca) / 40))
            if rr > 2:
                self._portal(surf, x, y, rr, self.t * 0.08)
            elif self.t - tanca < 60:
                l = llum(int(50 * (1 - (self.t - tanca - 40) / 20)) + 4, (230, 200, 255))
                surf.blit(l, l.get_rect(center=(x, y)))
        surf.blit(self.ciutat, (-20, HEIGHT - 230))

    def _dibuixar_retorn(self, surf):
        surf.blit(self.cel_sortida, (0, 0))
        y_sol = 320 - min(140, self.t * 0.6)
        l = llum(130, (255, 210, 140))
        surf.blit(l, l.get_rect(center=(WIDTH // 2 + 160, int(y_sol))))
        pygame.draw.circle(surf, (255, 235, 180), (WIDTH // 2 + 160, int(y_sol)), 44)
        surf.blit(self.runes_lluny, (-60, HEIGHT - 330))
        sol = HEIGHT - 172
        pygame.draw.rect(surf, (40, 30, 34), (0, sol, WIDTH, HEIGHT - sol))
        pygame.draw.rect(surf, (60, 64, 70), (40, sol - 40, 120, 44))
        pygame.draw.rect(surf, (20, 22, 26), (52, sol - 32, 96, 30))
        plat = crear_platet_cache(3)[(self.t // 8) % 3]
        y_plat = min(sol - 34, 60 + self.t * 2.2)
        surf.blit(plat, plat.get_rect(center=(WIDTH // 2 + 60, int(y_plat))))
        if y_plat >= sol - 34:
            temps = self.t - (sol - 34 - 60) / 2.2
            self._soldat(surf, WIDTH // 2 + 20 - min(60, temps * 1.2), sol + 2, "corre" if temps < 50 else "quiet", -1)
            for k in range(5):                                     # supervivents que surten del búnker
                x = 100 + min(WIDTH // 2 - 200, max(0, temps - 30 - k * 22) * 1.6) - k * 4
                if temps > 30 + k * 22:
                    pygame.draw.rect(surf, (30, 26, 30), (int(x), sol - 30, 10, 30))
                    pygame.draw.circle(surf, (30, 26, 30), (int(x) + 5, sol - 35), 6)

    def _dibuixar_fi(self, surf):
        surf.blit(self.cel_nit, (0, 0))
        self._estrelles(surf)
        LOGO_MENU.dibuixar(surf, WIDTH // 2, 16, self.t)
        if self.t > 60:
            text(surf, "FIN", F_TITOL, GROC, (WIDTH // 2, 330))

    def dibuixar(self, surf):
        getattr(self, "_dibuixar_" + self.escena)(surf)
        etiqueta = self.ETIQUETES.get(self.escena)
        if etiqueta and not (self.escena == "despertar" and self.t > 130):
            text(surf, etiqueta, F_SUBTITOL, BLANC, (30, 36), ancora="midleft")
        # subtítulos
        alt = len(self.linies) * 34 + 26
        caixa = pygame.Rect(30, HEIGHT - alt - 40, WIDTH - 60, alt)
        capa = pygame.Surface(caixa.size, pygame.SRCALPHA)
        capa.fill((0, 0, 0, 170))
        surf.blit(capa, caixa)
        restants = int(self.mostrats)
        y = caixa.top + 12
        for linia in self.linies:
            if restants <= 0:
                break
            text(surf, linia[:restants], F_TEXT, BLANC, (caixa.left + 20, y), ancora="topleft")
            restants -= len(linia)
            y += 34
        self.boto_saltar.dibuixar(surf)
        n = len(self.escenes)
        for k in range(n):
            pygame.draw.circle(surf, BLANC if k == self.i else GRIS_FOSC, (WIDTH - 30 - (n - 1 - k) * 14, 26), 4)
        # fundido de entrada
        if self.t < 25:
            negre = CAPA_TRANSPARENT
            negre.fill((0, 0, 0, int(255 * (1 - self.t / 25))))
            surf.blit(negre, (0, 0))


_CACHE_MOSTRA = {}


def mostra_soldat(arma_id, uniforme="classic", aparenca="estandard"):
    """Imatge estàtica del soldat per a la botiga i el passi (més ràpida que generar tota l'animació)."""
    clau = (arma_id, uniforme, aparenca)
    img = _CACHE_MOSTRA.get(clau)
    if img is None:
        base = BASE_JUGADOR.get(arma_id) or BASE_JUGADOR.get("pistola")
        if base is None:
            return None
        img = recolorar_soldat(base, UNIFORMES[uniforme]["colors"], APARENCES_ARMA[aparenca]["tint"])
        img = _CACHE_MOSTRA[clau] = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
    return img


def dibuixar_pips(surf, x, y, n, total=5, color=GROC, mida=8):
    for i in range(total):
        r = pygame.Rect(x + i * (mida + 3), y, mida, mida)
        pygame.draw.rect(surf, color if i < n else GRIS_FOSC, r)
        pygame.draw.rect(surf, NEGRE, r, 1)


def dibuixar_estrella(surf, cx, cy, r, plena=True, color=(255, 214, 64)):
    punts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        punts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    if plena:
        pygame.draw.polygon(surf, NEGRE, [(x + 1, y + 2) for x, y in punts])
        pygame.draw.polygon(surf, color, punts)
        pygame.draw.polygon(surf, aclarir(color, 60), punts, 1)
    else:
        pygame.draw.polygon(surf, (40, 42, 60), punts)
        pygame.draw.polygon(surf, (90, 92, 120), punts, 1)


def dibuixar_trofeu(surf, cx, cy, mida, color=(255, 205, 60)):
    """Copa en pixel art (els logros)."""
    k = mida / 20
    fosc = tuple(max(0, c - 70) for c in color)
    pygame.draw.rect(surf, fosc, (cx - 7 * k, cy + 6 * k, 14 * k, 4 * k))                  # peu
    pygame.draw.rect(surf, color, (cx - 2 * k, cy + 1 * k, 4 * k, 6 * k))
    pygame.draw.polygon(surf, color, [(cx - 8 * k, cy - 9 * k), (cx + 8 * k, cy - 9 * k), (cx + 5 * k, cy + 2 * k),
                                      (cx - 5 * k, cy + 2 * k)])
    pygame.draw.arc(surf, color, (cx - 12 * k, cy - 8 * k, 8 * k, 8 * k), 1.5, 4.8, max(1, int(2 * k)))
    pygame.draw.arc(surf, color, (cx + 4 * k, cy - 8 * k, 8 * k, 8 * k), -1.7, 1.6, max(1, int(2 * k)))
    pygame.draw.line(surf, aclarir(color, 70), (cx - 5 * k, cy - 7 * k), (cx - 3 * k, cy - 1 * k), max(1, int(k)))


def dibuixar_globus(surf, cx, cy, r):
    """Icona d'idioma: un planeta amb meridians."""
    pygame.draw.circle(surf, (40, 110, 200), (cx, cy), r)
    pygame.draw.circle(surf, (90, 200, 120), (cx - r // 3, cy - r // 4), r // 2)
    pygame.draw.circle(surf, (90, 200, 120), (cx + r // 2, cy + r // 3), r // 3)
    pygame.draw.ellipse(surf, (220, 240, 255), (cx - r // 2, cy - r, r, r * 2), 1)
    pygame.draw.line(surf, (220, 240, 255), (cx - r, cy), (cx + r, cy), 1)
    pygame.draw.circle(surf, (220, 240, 255), (cx, cy), r, 2)


def dibuixar_bandera(surf, codi, rect):
    """Banderes en pixel art: castellà (Espanya), català (senyera) i anglès (Regne Unit)."""
    r = pygame.Rect(rect)
    clip_abans = surf.get_clip()
    surf.set_clip(r.clip(clip_abans) if clip_abans else r)     # les diagonals no surten de la bandera
    if codi == "es":
        pygame.draw.rect(surf, (198, 11, 30), r)
        pygame.draw.rect(surf, (255, 196, 0), (r.x, r.y + r.h // 4, r.w, r.h // 2))
    elif codi == "ca":
        pygame.draw.rect(surf, (252, 221, 9), r)
        franja = r.h / 9
        for i in (1, 3, 5, 7):
            pygame.draw.rect(surf, (218, 18, 26), (r.x, r.y + round(i * franja), r.w, round(franja)))
    else:
        pygame.draw.rect(surf, (1, 33, 105), r)
        for gruix, color in ((max(3, r.h // 5), BLANC), (max(1, r.h // 12), (200, 16, 46))):
            pygame.draw.line(surf, color, r.topleft, (r.right - 1, r.bottom - 1), gruix)
            pygame.draw.line(surf, color, (r.x, r.bottom - 1), (r.right - 1, r.y), gruix)
        pygame.draw.rect(surf, BLANC, (r.x, r.centery - r.h // 6, r.w, r.h // 3))
        pygame.draw.rect(surf, BLANC, (r.centerx - r.h // 6, r.y, r.h // 3, r.h))
        pygame.draw.rect(surf, (200, 16, 46), (r.x, r.centery - r.h // 10, r.w, r.h // 5 + 1))
        pygame.draw.rect(surf, (200, 16, 46), (r.centerx - r.h // 10, r.y, r.h // 5 + 1, r.h))
    surf.set_clip(clip_abans)
    pygame.draw.rect(surf, NEGRE, r, 1)


def dibuixar_medalla(surf, cx, cy, r, cat, obert=True):
    color = CATEGORIES_LOGRO[cat]["color"] if obert else (70, 72, 92)
    pygame.draw.circle(surf, NEGRE, (cx + 1, cy + 2), r + 1)
    pygame.draw.circle(surf, tuple(max(0, c - 60) for c in color), (cx, cy), r)
    pygame.draw.circle(surf, color, (cx, cy), r - 3)
    dibuixar_trofeu(surf, cx, cy, int(r * 1.15), tuple(max(0, c - 90) for c in color) if obert else (50, 52, 70))


def dibuixar_placa(surf, x, y, t):
    """Placa d'identificació d'un soldat: petita i mig amagada, brilla de tant en tant."""
    placa = pygame.Surface((14, 20), pygame.SRCALPHA)
    pygame.draw.line(placa, (150, 150, 160, 200), (7, 0), (7, 4), 1)
    pygame.draw.rect(placa, (170, 172, 184, 255), (2, 4, 10, 15), border_radius=3)
    pygame.draw.rect(placa, (110, 112, 124, 255), (2, 4, 10, 15), 1, border_radius=3)
    for k in range(3):
        pygame.draw.line(placa, (90, 92, 104, 255), (4, 8 + k * 3), (9, 8 + k * 3))
    placa.set_alpha(150)
    surf.blit(placa, (int(x) - 7, int(y) - 10 + int(math.sin(t * 0.05) * 2)))
    if t % 120 < 12:                                   # brillantor fugaç
        k = 1 - abs(t % 120 - 6) / 6
        pygame.draw.line(surf, BLANC, (x - 6 * k, y - 6), (x + 6 * k, y - 6))
        pygame.draw.line(surf, BLANC, (x, y - 12 * k), (x, y))


def panell(surf, rect, vora=BLAU_CLAR, alfa=215):
    capa = pygame.Surface(rect.size, pygame.SRCALPHA)
    capa.fill((10, 12, 28, alfa))
    surf.blit(capa, rect)
    pygame.draw.rect(surf, vora, rect, 2, border_radius=8)


class Game:
    def __init__(self):
        self.clock = pygame.time.Clock()
        self.estat = "loading"
        self.temps_estat = 0
        self.t_global = 0
        self.fons_menu = FonsAnimat()
        self.fons_derrota = FonsAnimat((80, 24, 36), (24, 10, 16))
        self.capa = pygame.Surface((WIDTH, HEIGHT))
        self.botons = []
        self.missatge = ""
        self.temps_missatge = 0
        self.confirmar_reinici = False
        self.pantalla_text = None
        self.pestanya = "armes"
        self.entrada_arxiu = 0
        self.avisos = []
        self.flaix = 0
        self.carregar_progres()
        self.reiniciar_partida_estat()

    # ----- Progrés -----------------------------------------------------------
    def carregar_progres(self):
        d = Desat.carregar()
        self.monedes = d.get("monedes", 0) if isinstance(d.get("monedes"), int) else 0
        armes = d.get("armes")
        propies = {"pistola"}
        if isinstance(armes, list):
            if armes and all(isinstance(v, bool) for v in armes):          # desat de la versió 1
                for nom, v in zip(("pistola", "fusell", "minigun"), armes):
                    if v:
                        propies.add(nom)
            else:
                propies.update(a for a in armes if a in ARMA_PER_ID)
        self.armes_propies = propies
        arma = d.get("arma", "pistola")
        if isinstance(arma, int):                                         # versió 1: índex
            arma = ("pistola", "fusell", "minigun")[arma] if 0 <= arma < 3 else "pistola"
        self.arma_actual = ARMA_PER_ID.get(arma, 0) if arma in propies else 0

        def graella(clau, defecte):
            g = d.get(clau)
            res = [list(f) for f in defecte]
            if isinstance(g, list):
                for n, fila in enumerate(g[:NUM_SECTORS]):
                    if isinstance(fila, list):
                        for e, v in enumerate(fila[:3]):
                            res[n][e] = bool(v)
            return res
        self.nivells_desbloquejats = graella("nivells", [[n == 0 and e == 0 for e in range(3)] for n in range(NUM_SECTORS)])
        self.nivells_desbloquejats[0][0] = True
        self.completats = graella("completats", [[False] * 3 for _ in range(NUM_SECTORS)])
        if self.completats[2][2]:                     # partides antigues que ja havien acabat el joc original
            self.nivells_desbloquejats[3][0] = True
        self.xp = d.get("xp", 0) if isinstance(d.get("xp"), int) else 0
        self.passi_reclamat = d.get("passi", 0) if isinstance(d.get("passi"), int) else 0
        mill = d.get("millores", {})
        self.millores = {m["id"]: max(0, min(len(m["costos"]), int(mill.get(m["id"], 0))))
                         for m in MILLORES} if isinstance(mill, dict) else {m["id"]: 0 for m in MILLORES}
        desb = d.get("cosmetics", [])
        self.cosmetics = {"u:classic", "a:estandard", "t:recluta"}
        if isinstance(desb, list):
            self.cosmetics.update(c for c in desb if isinstance(c, str))
        equip = d.get("equipat", {}) if isinstance(d.get("equipat"), dict) else {}
        self.uniforme = equip.get("uniforme") if f"u:{equip.get('uniforme')}" in self.cosmetics else "classic"
        self.aparenca = equip.get("arma") if f"a:{equip.get('arma')}" in self.cosmetics else "estandard"
        self.titol = equip.get("titol") if f"t:{equip.get('titol')}" in self.cosmetics else "recluta"
        self.intro_vista = bool(d.get("intro_vista", False))
        self.tutorial_vist = bool(d.get("tutorial_vist", False))
        self.novetats_vistes = d.get("novetats_vistes") if isinstance(d.get("novetats_vistes"), str) else None
        self.estrelles = [[[False] * 3 for _ in range(3)] for _ in range(NUM_SECTORS)]
        est = d.get("estrelles")
        if isinstance(est, list):
            for n, fila in enumerate(est[:NUM_SECTORS]):
                if isinstance(fila, list):
                    for e, v in enumerate(fila[:3]):
                        if isinstance(v, list):
                            self.estrelles[n][e] = [bool(x) for x in (list(v) + [False] * 3)[:3]]
        for n in range(NUM_SECTORS):                  # partides antigues: completat = primera estrella
            for e in range(3):
                if self.completats[n][e]:
                    self.estrelles[n][e][0] = True
        recs = d.get("records")
        self.records = [r for r in recs if isinstance(r, dict) and isinstance(r.get("punts"), int)][:5] \
            if isinstance(recs, list) else []
        opcions = d.get("opcions") if isinstance(d.get("opcions"), dict) else {}
        self.nivell_dificultat = opcions.get("dificultat") if opcions.get("dificultat") in DIFICULTATS else "normal"
        self.numeros_dany = bool(opcions.get("numeros", True))
        self.arena = 0
        self.nivell_enemics = 0
        self.logros = {x for x in d.get("logros", []) if isinstance(x, str)} if isinstance(d.get("logros"), list) else set()
        est = d.get("estadistiques")
        self.estadistiques = {k: v for k, v in est.items() if isinstance(v, int)} if isinstance(est, dict) else {}
        self.plaques = {x for x in d.get("plaques", []) if isinstance(x, str)} if isinstance(d.get("plaques"), list) else set()
        self.avisos_logro = getattr(self, "avisos_logro", [])
        self.menu_idioma = False
        self.pagina_logros = 0
        self.konami = []

    def desar_progres(self):
        Desat.desar({
            "versio": 2,
            "monedes": self.monedes,
            "armes": sorted(self.armes_propies),
            "arma": ARMES[self.arma_actual]["id"],
            "nivells": self.nivells_desbloquejats,
            "completats": self.completats,
            "xp": self.xp,
            "passi": self.passi_reclamat,
            "millores": self.millores,
            "cosmetics": sorted(self.cosmetics),
            "equipat": {"uniforme": self.uniforme, "arma": self.aparenca, "titol": self.titol},
            "intro_vista": self.intro_vista,
            "tutorial_vist": self.tutorial_vist,
            "novetats_vistes": self.novetats_vistes,
            "estrelles": self.estrelles,
            "records": self.records,
            "logros": sorted(self.logros),
            "estadistiques": self.estadistiques,
            "plaques": sorted(self.plaques),
            "opcions": {"musica": round(AUDIO.vol_musica, 2), "efectes": round(AUDIO.vol_efectes, 2),
                        "completa": PANTALLA.completa, "suau": PANTALLA.suau,
                        "dificultat": self.nivell_dificultat, "idioma": idioma(), "numeros": self.numeros_dany},
        })

    def esborrar_progres(self):
        if not self.confirmar_reinici:
            self.confirmar_reinici = True
            self.entrar_menu()
            self.mostrar_missatge("Vuelve a hacer clic para confirmar")
            return
        Desat.esborrar()
        self.carregar_progres()
        self.confirmar_reinici = False
        self.entrar_menu()
        self.mostrar_missatge("Progreso borrado", ok=True)

    def mostrar_missatge(self, txt, temps=150, ok=False):
        self.missatge = txt
        self.missatge_ok = ok
        self.temps_missatge = temps

    def avis(self, txt, color=GROC, temps=200):
        self.avisos.append([txt, color, temps])
        self.avisos = self.avisos[-4:]

    # ----- Regles: història, millores, armes ---------------------------------
    def completat(self, index):
        return index < 0 or self.completats[index // 3][index % 3]

    def nivell_millora(self, ident):
        return self.millores.get(ident, 0)

    def vida_max(self):
        return VIDA_MAX + 20 * self.nivell_millora("blindatge")

    def multiplicador_dany(self):
        return 1 + 0.15 * self.nivell_millora("potencia")

    def bales_max(self, i):
        base = ARMES[i]["bales_max"]
        if base is None:
            return None
        return int(round(base * (1 + 0.3 * self.nivell_millora("carregadors"))))

    def radi_iman(self):
        n = self.nivell_millora("iman")
        return 40 + 55 * n if n else 0

    def potencia_max(self):
        if self.mode in ("supervivencia", "tutorial"):
            return 5
        return POTENCIA_MAX.get((self.nivell_actual, self.escenari_actual), 5)

    def armes_usables(self):
        if self.mode == "tutorial":     # a l'entrenament: només la pistola fins al pas de canviar d'arma
            ja_pot = [c for c, _ in PASSOS_TUTORIAL].index("arma") <= getattr(self, "tut", {}).get("pas", 0)
            return [ARMA_PER_ID["pistola"]] + ([ARMA_PER_ID["fusell"]] if ja_pot else [])
        pm = self.potencia_max()
        return [i for i, a in enumerate(ARMES) if a["id"] in self.armes_propies and a["potencia"] <= pm]

    def spr_jugador(self, i=None):
        return sprites_jugador(ARMES[self.arma_actual if i is None else i]["id"], self.uniforme, self.aparenca,
                               self.nivell_millora("blindatge"))

    def nivell_passi(self):
        return min(len(PASSI), self.xp // XP_PER_NIVELL)

    def afegir_xp(self, quantitat):
        self.xp += quantitat
        while self.passi_reclamat < self.nivell_passi():
            for tipus, valor in PASSI[self.passi_reclamat]:
                if tipus == "monedes":
                    self.monedes += valor
                else:
                    self.cosmetics.add({"uniforme": "u:", "arma": "a:", "titol": "t:"}[tipus] + valor)
                self.avis(f"BATTLE PASS {self.passi_reclamat + 1}: {nom_recompensa(tipus, valor)}", (255, 200, 255), 260)
            self.passi_reclamat += 1
            AUDIO.so("passi")

    def nivell_passi_de(self, tipus, valor):
        for i, recompenses in enumerate(PASSI):
            if (tipus, valor) in recompenses:
                return i + 1
        return None

    # ----- Canvis d'estat ---------------------------------------------------
    def canviar_estat(self, estat):
        if estat != self.estat:
            self.missatge = ""
            self.temps_missatge = 0
        self.estat = estat
        self.temps_estat = 0
        pygame.mouse.set_visible(estat != "joc")

    def boto_tornar(self):
        return Boto((30, HEIGHT - 62, 140, 42), "< Menú", self.entrar_menu, GRIS_FOSC)

    def sortir_carrega(self):
        """Primera vegada: tria d'idioma, introducció, entrenament i com funciona. Després, directament el menú."""
        if self.intro_vista and self.novetats_vistes != NOVETATS[0]["versio"]:
            self.entrar_novetats(0, self.entrar_menu)          # ja havies jugat: primer, les novetats
        elif self.intro_vista:
            self.entrar_menu()
        else:
            self.entrar_idioma_inicial()

    def entrar_menu(self):
        AUDIO.musica("menu")
        self.mode = "historia"
        self.desar_progres()
        c = 700                                         # columna de botons (el logo va a l'esquerra)
        b = [Boto((c - 170, 150, 340, 50), "Jugar", self.entrar_selector, VERD)]
        oberta = self.completats[0][2]
        graella = [("Supervivencia", self.entrar_supervivencia if oberta else
                    (lambda: self.mostrar_missatge("Supervivencia: completa el sector 1")), ),
                   ("Tienda", self.entrar_botiga), ("Battle Pass", self.entrar_passi),
                   ("Historia", self.entrar_arxiu), ("Guía", self.entrar_guia),
                   ("Opciones", self.entrar_opcions), ("Créditos", self.entrar_credits)]
        if not WEB:
            graella.append(("Salir", lambda: self.canviar_estat("quit")))
        for k, (nom, accio) in enumerate(graella):
            fila, col = divmod(k, 2)
            ample = 165
            x = c - ample - 5 if col == 0 else c + 5
            if k == len(graella) - 1 and col == 0:          # l'últim, sol, centrat
                x = c - ample // 2
            color = (TARONJA if oberta else GRIS_FOSC) if k == 0 else BLAU
            b.append(Boto((x, 214 + fila * 54, ample, 46), nom, accio, color,
                          font=F_HUD if len(T(nom)) > 8 else None))
        b.append(Boto((WIDTH - 210, HEIGHT - 44, 190, 30), "Borrar progreso", self.esborrar_progres,
                      color=VERMELL_FOSC if not self.confirmar_reinici else VERMELL, font=F_MINI))
        b.append(Boto((16, 12, 44, 40), "", self.obrir_menu_idioma, invisible=True))     # icona d'idioma
        b.append(Boto((68, 12, 44, 40), "", self.entrar_logros, invisible=True))         # icona de logros
        b.append(Boto((120, 12, 44, 40), "", lambda: self.entrar_novetats(0, self.entrar_menu), invisible=True))
        self.botons = b
        self.canviar_estat("menu")
        self.revisar_logros()

    # ----- Supervivència ------------------------------------------------------

    def entrar_selector(self):
        self.confirmar_reinici = False
        b = []
        for n in range(NUM_SECTORS):
            for e in range(3):
                obert = self.nivells_desbloquejats[n][e]
                txt = f"{n + 1}-{e + 1}" if obert else "?"
                color = VERD if self.completats[n][e] else BLAU
                b.append(Boto((470 + e * 150, 94 + n * 76, 100, 44), txt,
                              (lambda n=n, e=e: self.mostrar_narrativa(n, e)) if obert else None, color))
        b.append(self.boto_tornar())
        self.botons = b
        self.canviar_estat("selector")

    def entrar_botiga(self, pestanya=None):
        self.confirmar_reinici = False
        if pestanya:
            self.pestanya = pestanya
        b = []
        for k, (ident, nom) in enumerate((("armes", "Armas"), ("millores", "Mejoras"), ("aparenca", "Aspecto"))):
            b.append(Boto((WIDTH // 2 - 265 + k * 180, 74, 170, 38), nom, lambda i=ident: self.entrar_botiga(i),
                          VERD if self.pestanya == ident else BLAU, font=F_HUD))
        if self.pestanya == "armes":
            for i, arma in enumerate(ARMES):
                x = 31 + i * 182
                rect = (x + 12, 398, 146, 36)
                if arma["id"] in self.armes_propies:
                    if self.arma_actual == i:
                        b.append(Boto(rect, "Equipada", lambda: None, VERD, font=F_MINI))
                    else:
                        b.append(Boto(rect, "Equipar", lambda i=i: self.equipar_arma(i), BLAU, font=F_MINI))
                elif not self.completat(arma["req"]):
                    b.append(Boto(rect, T("Completa {e}").format(e=nom_escenari(arma['req'])), None, font=F_MINI))
                else:
                    color = TARONJA if self.monedes >= arma["cost"] else VERMELL_FOSC
                    b.append(Boto(rect, T("Comprar {c}").format(c=arma['cost']), lambda i=i: self.comprar_arma(i), color, font=F_MINI))
        elif self.pestanya == "millores":
            for k, m in enumerate(MILLORES):
                nivell = self.nivell_millora(m["id"])
                rect = (734, 128 + k * 56 + 7, 156, 36)
                if nivell >= len(m["costos"]):
                    b.append(Boto(rect, "Máximo", None, font=F_MINI))
                elif not self.completat(m["req"][nivell]):
                    b.append(Boto(rect, T("Completa {e}").format(e=nom_escenari(m['req'][nivell])), None, font=F_MINI))
                else:
                    cost = m["costos"][nivell]
                    color = TARONJA if self.monedes >= cost else VERMELL_FOSC
                    b.append(Boto(rect, T("Comprar {c}").format(c=cost), lambda m=m: self.comprar_millora(m), color, font=F_MINI))
        else:
            for k, ident in enumerate(UNIFORMES):
                b.append(Boto((80 + k * 116, 138, 106, 96), "", lambda v=ident: self.equipar_cosmetic("uniforme", v),
                              invisible=True))
            for k, ident in enumerate(APARENCES_ARMA):
                b.append(Boto((80 + k * 135, 268, 125, 84), "", lambda v=ident: self.equipar_cosmetic("arma", v),
                              invisible=True))
            for k, ident in enumerate(TITOLS):
                b.append(Boto((80 + k * 162, 384, 152, 46), "", lambda v=ident: self.equipar_cosmetic("titol", v),
                              invisible=True))
        b.append(self.boto_tornar())
        self.botons = b
        self.canviar_estat("botiga")

    def comprar_arma(self, i):
        arma = ARMES[i]
        if self.monedes < arma["cost"]:
            self.mostrar_missatge(T("¡Te faltan {n} monedas!").format(n=arma['cost'] - self.monedes))
            AUDIO.so("buit")
            return
        self.monedes -= arma["cost"]
        self.armes_propies.add(arma["id"])
        self.arma_actual = i
        self.mostrar_missatge(T("¡{a} desbloqueada!").format(a=T(arma['nom'])), ok=True)
        self.revisar_logros()
        AUDIO.so("moneda")
        self.desar_progres()
        self.entrar_botiga()

    def equipar_arma(self, i):
        self.arma_actual = i
        self.desar_progres()
        self.entrar_botiga()

    def comprar_millora(self, m):
        nivell = self.nivell_millora(m["id"])
        cost = m["costos"][nivell]
        if self.monedes < cost:
            self.mostrar_missatge(T("¡Te faltan {n} monedas!").format(n=cost - self.monedes))
            AUDIO.so("buit")
            return
        self.monedes -= cost
        self.millores[m["id"]] = nivell + 1
        self.mostrar_missatge(T("¡{m} nivel {n} desbloqueado!").format(m=T(m['nom']), n=nivell + 1), ok=True)
        self.revisar_logros()
        AUDIO.so("moneda")
        self.desar_progres()
        self.entrar_botiga()

    def equipar_cosmetic(self, tipus, valor):
        prefix = {"uniforme": "u:", "arma": "a:", "titol": "t:"}[tipus]
        if prefix + valor not in self.cosmetics:
            nivell = self.nivell_passi_de(tipus, valor)
            self.mostrar_missatge(T("Se consigue en el nivel {n} del Battle Pass").format(n=nivell) if nivell else T("Bloqueado"))
            AUDIO.so("buit")
            return
        if tipus == "uniforme":
            self.uniforme = valor
        elif tipus == "arma":
            self.aparenca = valor
        else:
            self.titol = valor
        AUDIO.so("item")
        self.desar_progres()
        self.revisar_logros()

    def entrar_passi(self):
        self.confirmar_reinici = False
        self.botons = [self.boto_tornar()]
        self.canviar_estat("passi")

    def entrar_arxiu(self):
        self.confirmar_reinici = False
        AUDIO.musica("menu")
        b = []
        for i, (titol, _) in enumerate(ARXIU):
            obert = self.completats[i][2]
            b.append(Boto((40, 96 + i * 60, 250, 48), titol if obert else "? ? ?",
                          (lambda i=i: self.triar_arxiu(i)) if obert else None,
                          VERD if i == self.entrada_arxiu and obert else BLAU, font=F_MINI))
        b.append(Boto((40, 96 + len(ARXIU) * 60, 250, 48), "Ver introducción",
                      lambda: self.entrar_intro(self.entrar_arxiu), VERD, font=F_MINI))
        escena = {2: "comandant", 3: "nau", 4: "final"}.get(self.entrada_arxiu)
        if escena and self.completats[self.entrada_arxiu][2]:
            b.append(Boto((730, 390, 176, 40), "Ver escena", lambda: self.veure_cinematica(escena, self.entrar_arxiu),
                          TARONJA, font=F_HUD))
        b.append(self.boto_tornar())
        self.botons = b
        self.canviar_estat("arxiu")

    def entrar_intro(self, despres=None):
        """Animación inicial; al acabar (o saltarla) vuelve a `despres` (por defecto, el menú)."""
        despres = despres or self.entrar_menu

        def fi():
            self.intro_vista = True
            self.desar_progres()
            despres()
        AUDIO.musica("menu")
        self.intro = Intro(fi)
        self.botons = []
        self.canviar_estat("intro")

    def triar_arxiu(self, i):
        self.entrada_arxiu = i
        self.entrar_arxiu()

    def entrar_guia(self):
        self.confirmar_reinici = False
        self.botons = [self.boto_tornar(),
                       Boto((WIDTH - 370, HEIGHT - 62, 170, 42), "Tutorial", lambda: self.iniciar_tutorial(self.entrar_guia),
                            VERD, font=F_HUD),
                       Boto((WIDTH - 190, HEIGHT - 62, 170, 42), "Cómo funciona",
                            lambda: self.entrar_ajuda(despres=self.entrar_guia), BLAU, font=F_HUD)]
        self.canviar_estat("guia")

    def entrar_credits(self):
        self.confirmar_reinici = False
        AUDIO.musica("menu")
        self.credits_y = float(HEIGHT - 40)
        self.botons = [self.boto_tornar()]
        self.canviar_estat("credits")

    def mostrar_narrativa(self, nivell, escenari):
        self.mode = "historia"
        self.nivell_actual = nivell
        self.escenari_actual = escenari
        AUDIO.musica(musica_escenari(nivell, escenari))
        titol = f"{T('SECTOR')} {nivell + 1} · {T(NOMS_SECTORS[nivell]).upper()}"
        boto = Boto((WIDTH // 2 - 110, HEIGHT - 100, 220, 50), "Continuar", self.avancar_narrativa)
        pm = self.potencia_max()
        permeses = [T(a["nom"]) for a in ARMES if a["potencia"] <= pm]
        llista = T("todas") if pm >= 5 else ", ".join(permeses)
        peu = [(T("Potencia máxima {p}/5 · Armas: {l}").format(p=pm, l=llista), CIAN)]
        motiu = MOTIUS_RESTRICCIO.get((nivell, escenari))
        if motiu:
            peu.append((T(motiu), GROC))
        est = self.estrelles[nivell][escenari]
        peu.append((T("Estrellas: {e}/3 · récord de tiempo: {s} s").format(e=sum(est), s=TEMPS_ESTRELLA[(nivell, escenari)]),
                    (255, 220, 120)))
        self.pantalla_text = PantallaText(titol, TEXTOS_NARRATIVA[(nivell, escenari)], CIAN, [boto], self.fons_menu,
                                          peu=peu)
        self.botons = [boto]
        self.canviar_estat("narrativa")

    def avancar_narrativa(self):
        if not self.pantalla_text.complet:
            self.pantalla_text.completar()
        else:
            self.iniciar_joc()

    def mostrar_derrota(self):
        self.desar_progres()
        AUDIO.aturar_musica()
        AUDIO.so("eliminat")
        botons = [Boto((WIDTH // 2 - 230, HEIGHT - 110, 200, 50), "Menú", self.entrar_menu, GRIS_FOSC),
                  Boto((WIDTH // 2 + 30, HEIGHT - 110, 200, 50), "Reintentar", self.iniciar_joc, VERMELL)]
        self.pantalla_text = PantallaText("HAS CAÍDO", TEXT_DERROTA, VERMELL, botons, self.fons_derrota,
                                          pista="R / ENTER: reintentar  ·  ESC: menú")
        self.botons = botons
        self.canviar_estat("derrota")

    def pausar(self):
        self.botons = [
            Boto((WIDTH // 2 - 120, 180, 240, 50), "Continuar", self.reprendre, VERD),
            Boto((WIDTH // 2 - 120, 242, 240, 50), "Reiniciar", self.iniciar_joc, BLAU),
            Boto((WIDTH // 2 - 120, 304, 240, 50), "Opciones", lambda: self.entrar_opcions(self.pausar), BLAU),
            Boto((WIDTH // 2 - 120, 366, 240, 50), "Menú", self.entrar_menu, GRIS_FOSC),
        ]
        self.canviar_estat("pausa")

    # ----- Opciones ---------------------------------------------------------
    def entrar_opcions(self, tornada=None):
        self.tornada_opcions = tornada or self.entrar_menu
        self.lliscadors = [
            Lliscador(400, 105, 320, AUDIO.vol_musica, lambda v: AUDIO.canviar_volums(musica=v), self.desar_progres),
            Lliscador(400, 157, 320, AUDIO.vol_efectes, lambda v: AUDIO.canviar_volums(efectes=v),
                      lambda: (AUDIO.so("moneda"), self.desar_progres())),
        ]
        b = []
        if WEB:
            b.append(Boto((400, 196, 320, 40), "Pantalla completa (F11)", PANTALLA.commutar_completa, BLAU, font=F_HUD))
        else:
            b.append(Boto((400, 196, 155, 40), "Completa", lambda: self.posar_pantalla(True),
                          VERD if PANTALLA.completa else BLAU, font=F_HUD))
            b.append(Boto((565, 196, 155, 40), "Ventana", lambda: self.posar_pantalla(False),
                          VERD if not PANTALLA.completa else BLAU, font=F_HUD))
        b.append(Boto((400, 248, 155, 40), "Suave", lambda: self.posar_suau(True), VERD if PANTALLA.suau else BLAU,
                      font=F_HUD))
        b.append(Boto((565, 248, 155, 40), "Nítido", lambda: self.posar_suau(False),
                      VERD if not PANTALLA.suau else BLAU, font=F_HUD))
        for k, (ident, d) in enumerate(DIFICULTATS.items()):
            b.append(Boto((400 + k * 110, 300, 100, 40), d["nom"], lambda i=ident: self.posar_dificultat(i),
                          VERD if self.nivell_dificultat == ident else BLAU, font=F_HUD))
        for k, (ident, nom) in enumerate(IDIOMES.items()):
            b.append(Boto((400 + k * 110, 352, 100, 40), nom, lambda i=ident: self.posar_idioma(i),
                          VERD if idioma() == ident else BLAU, font=F_HUD))
        for k, (valor, nom) in enumerate(((True, "Sí"), (False, "No"))):
            b.append(Boto((450 + k * 110, 406, 100, 34), nom, lambda v=valor: self.posar_numeros(v),
                          VERD if self.numeros_dany == valor else BLAU, font=F_HUD))
        b.append(Boto((30, HEIGHT - 62, 140, 42), "< Volver", lambda: self.tornada_opcions(), GRIS_FOSC))
        self.botons = b
        self.canviar_estat("opcions")

    def posar_numeros(self, valor):
        self.numeros_dany = valor
        self.desar_progres()
        self.entrar_opcions(self.tornada_opcions)

    def posar_pantalla(self, completa):
        if PANTALLA.completa != completa:
            PANTALLA.completa = completa
            PANTALLA.aplicar()
            self.desar_progres()
        self.entrar_opcions(self.tornada_opcions)

    def posar_suau(self, suau):
        PANTALLA.suau = suau
        PANTALLA.nitidesa_web()
        self.desar_progres()
        self.entrar_opcions(self.tornada_opcions)

    def dibuixar_opcions(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, T("OPCIONES"), F_SUBTITOL, BLANC, (WIDTH // 2, 46))
        files = [("Música", 112), ("Efectos", 164), ("Pantalla", 216), ("Escalado", 268), ("Dificultad", 320),
                 ("Idioma", 372), ("Números de daño", 423)]
        for nom, y in files:
            text(surf, T(nom), F_TEXT, BLANC, (210, y), ancora="midleft")
        for l in self.lliscadors:
            l.dibuixar(surf)
            text(surf, f"{round(l.valor * 100)}%", F_UI, CIAN, (l.rect.right + 30, l.rect.centery), ancora="midleft")
        w, h = PANTALLA.surf.get_size()
        if PANTALLA.entera:
            detall = T("escala x{n}, píxel perfecto").format(n=int(PANTALLA.escala))
        else:
            detall = T("suavizado") if PANTALLA.suau else T("píxeles nítidos")
        text(surf, T("Resolución actual: {w}x{h} ({d})").format(w=w, h=h, d=detall), F_TEXT_P, GRIS, (WIDTH // 2, 458))
        text(surf, T("La dificultad se aplica al empezar el siguiente escenario."), F_TEXT_PP, GRIS, (WIDTH // 2, 479))
        text(surf, T("F11: pantalla completa  ·  M: silenciar"), F_TEXT_PP, GRIS, (WIDTH // 2 + 80, 499))

    def reprendre(self):
        self.botons = [self.boto_saltar_tutorial()] if self.mode == "tutorial" else []
        self.canviar_estat("joc")
        self.esperar_alliberar = True

    # ----- Partida ----------------------------------------------------------
    def reiniciar_partida_estat(self):
        self.calor, self.gir, self.sobreescalfat = 0.0, 0.0, False
        self.nivell_actual = 0
        self.escenari_actual = 0
        self.mode = "historia"
        self.jugador = Jugador()
        self.enemics, self.bales, self.bales_enemics, self.restes = [], [], [], []
        self.items, self.efectes, self.textos, self.plataformes = [], [], [], []
        self.bales_armes = [a["bales_max"] for a in ARMES]
        self.fase = "jugant"
        self.perills = Perills(())
        self.radio = Radio()
        self.presentacio = None
        self.aturada = 0
        self.ultima_aturada = 0
        self.onades, self.onada, self.espera_onada = [], 0, 0
        self.cap = None
        self.reiniciar_hud()

    def iniciar_joc(self):
        if self.mode == "supervivencia":
            AUDIO.musica("supervivencia")
        else:
            AUDIO.musica(musica_escenari(self.nivell_actual, self.escenari_actual))
        self.preparar_nivell()
        self.botons = [self.boto_saltar_tutorial()] if self.mode == "tutorial" else []
        self.canviar_estat("joc")

    def crear_enemic(self, tipus, vida, x=None, y=None, nivell=None):
        if nivell is None:
            nivell = self.nivell_enemics
        vida = max(1, round(vida * self.dificultat()["vida"]))
        e = Enemic(tipus, vida, nivell, 0, random.randint(60, 220), self.dificultat())
        if x is None:
            x = random.uniform(220, WIDTH - e.w - 10)
        e.x = max(10.0, min(WIDTH - e.w - 10.0, x))
        if y is not None and not e.terrestre:
            e.y = y
            e.y_destinacio = y + 30
        return e

    def preparar_nivell(self):
        clau = (self.nivell_actual, self.escenari_actual)
        dades = NIVELL_TUTORIAL if self.mode == "tutorial" else NIVELLS[clau]
        reflexos = self.nivell_millora("reflexos")
        self.jugador = Jugador(self.vida_max(), 1 + 0.06 * reflexos, 1 if self.nivell_millora("doble_salt") else 0,
                               40 + 12 * reflexos)
        self.bales, self.bales_enemics, self.items, self.efectes, self.textos, self.restes = [], [], [], [], [], []
        self.bales_armes = [self.bales_max(i) for i in range(len(ARMES))]
        mobils, fragils = dades.get("mobils", {}), dades.get("fragils", ())
        self.plataformes = [Plataforma(0, TERRA_Y, WIDTH, HEIGHT - TERRA_Y, terra=True)]
        self.plataformes += [Plataforma(x, y, w, mov=mobils.get(i), fragil=i in fragils)
                             for i, (x, y, w) in enumerate(dades["plataformes"])]
        self.perills = Perills(dades.get("perills"))
        self.radio = Radio()
        self.presentacio = None
        self.presentat = False
        self.radio_cap = False
        self.enemics = []
        self.cap = None
        self.aturada = 0
        self.ultima_aturada = 0
        self.onada = 0
        self.espera_onada = 0
        self.dany_rebut = 0
        self.temps_joc = 0
        self.estrelles_noves = None
        self.armes_usades = set()
        self.calor, self.gir, self.sobreescalfat = 0.0, 0.0, False
        clau_placa = f"{clau[0]}_{clau[1]}"
        self.placa = PLAQUES.get(clau) if self.mode == "historia" and clau_placa not in self.plaques else None
        self.ull_vida = 15 if self.mode == "historia" and clau == (0, 0) else 0
        self.ull_destruit = False
        self.fons_off = (-20, -10)
        self.ambient = Ambient(*clau)
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
        self.xp_nivell = 0
        self.flaix = 0
        self.reiniciar_hud()
        if self.mode == "supervivencia":
            self.onades = None
            self.punts = 0
            self.baixes = 0
            self.onades_superades = 0
            self.nom_cap = "JEFE DE OLEADA"
            self.llançar_onada_supervivencia(1)
        else:
            self.nivell_enemics = self.nivell_actual
            self.onades = dades["onades"]
            self.nom_cap = NOMS_CAPS.get(clau, "")
            self.llançar_onada(self.onades[0])
            if self.mode == "historia":
                self.radio.afegir(RADIO.get(clau, {}).get("inici", []), retard=40 if not self.presentacio else 200)
        if self.mode == "tutorial":
            self.nom_cap = ""
            self.tut = {"pas": 0, "t": 0, "fet": 0, "comptador": 0}
            self.començar_pas_tutorial()
        usables = self.armes_usables()
        for i in usables:                     # genera ara els fotogrames: canviar d'arma no s'encallarà
            self.spr_jugador(i)
        if self.arma_actual not in usables:
            antiga = ARMES[self.arma_actual]["nom"]
            self.arma_actual = max(usables, key=lambda i: ARMES[i]["potencia"])
            self.avis(T("Arma bloqueada aquí: {a} · Equipada: {b}").format(a=T(antiga), b=T(ARMES[self.arma_actual]['nom'])), GROC, 240)

    def canviar_arma(self, i):
        usables = self.armes_usables()
        if i in usables and i != self.arma_actual:
            self.arma_actual = i
            self.cooldown = max(self.cooldown, 12)
            self.canvi_arma_t = 12
            AUDIO.so("click")
        elif ARMES[i]["id"] in self.armes_propies and i not in usables:
            self.avis(T("{a}: demasiado potente para este escenario").format(a=T(ARMES[i]['nom'])), VERMELL, 120)

    def seguent_arma(self, sentit=1):
        usables = self.armes_usables()
        if len(usables) > 1:
            k = usables.index(self.arma_actual) if self.arma_actual in usables else 0
            self.canviar_arma(usables[(k + sentit) % len(usables)])

    def tipus_item_necessari(self):
        bales = self.bales_armes[self.arma_actual]
        bales_max = self.bales_max(self.arma_actual)
        poca_municio = bales_max is not None and bales < bales_max * 0.4
        if poca_municio and self.jugador.vida > 40:
            return "bales"
        if self.jugador.vida <= self.jugador.vida_max * 0.6:
            return "vida"
        if bales_max is None:
            return "vida"
        self.items_generats += 1
        return "vida" if self.items_generats % 2 else "bales"

    def generar_item(self):
        if len(self.items) >= 3:
            return
        p = random.choice([p for p in self.plataformes if p.rect.width > 50])
        x = random.randint(p.rect.x + 10, p.rect.right - Item.W - 10)
        self.items.append(Item(x, p.rect.top - Item.H - 4, self.tipus_item_necessari()))

    def color_bala(self):
        bala = APARENCES_ARMA[self.aparenca]["bala"]
        if bala == "arc":
            c = pygame.Color(0)
            c.hsva = ((self.t_global * 9) % 360, 70, 100, 100)
            return (c.r, c.g, c.b)
        return bala

    def disparar(self):
        i = self.arma_actual
        arma = ARMES[i]
        if arma["bales_max"] is not None and self.bales_armes[i] <= 0:
            AUDIO.so("buit", 150)
            self.avis_bales = 90
            self.cooldown = 18
            return
        spr = self.spr_jugador()
        cx, cy = self.jugador.canons(spr)
        mx, my = ratoli()
        base = math.atan2(my - cy, mx - cx)
        dany = max(1, round(arma["dany"] * self.multiplicador_dany()))
        color = self.color_bala()
        for k in range(arma["perdigons"]):
            obertura = math.radians(arma["obertura"])
            desv = (-obertura / 2 + obertura * k / (arma["perdigons"] - 1)) if arma["perdigons"] > 1 else 0
            angle = base + desv + math.radians(random.uniform(-arma["dispersio"], arma["dispersio"]))
            vel = arma["vel"] * (random.uniform(0.85, 1.1) if arma["perdigons"] > 1 else 1)
            self.bales.append(Bala(cx, cy, math.cos(angle) * vel, math.sin(angle) * vel, dany, arma["estil"],
                                   color=color, vida=arma["vida_bala"], perfora=arma["perfora"], k=self.n_tret))
        self.n_tret += 1
        self.mira_obertura = min(14.0, self.mira_obertura + {"pistola": 4, "escopeta": 9, "fusell": 3, "minigun": 1.2,
                                                              "plasma": 8}.get(arma["id"], 3))
        if arma["bales_max"] is not None:
            self.bales_armes[i] -= 1
        self.armes_usades.add(arma["id"])
        self.cooldown = arma["cadencia"]
        if arma["id"] == "minigun":                  # arrenca lenta i s'escalfa
            self.cooldown = round(arma["cadencia"] + 11 * (1 - self.gir))
            self.calor = min(100.0, self.calor + CALOR_DISPAR)
            if self.calor >= 100:
                self.sobreescalfat = True
                AUDIO.so("buit")
                self.avis("¡Minigun sobrecalentada! Espera a que se enfríe o cambia de arma.", TARONJA, 120)
        esclat(self.efectes, cx + math.cos(base) * 8, cy + math.sin(base) * 8, 4 + 4 * (arma["perdigons"] > 1),
               [color or GROC, BLANC, TARONJA], vel=(1, 3), mida=(2, 3), vida=(5, 10))
        j = self.jugador
        jx = j.x + j.W / 2
        if arma["id"] == "escopeta":                  # cartutx vermell i fum
            self.efectes.append(Beina(jx, cy + 2, -j.direccio * random.uniform(1.5, 2.5), random.uniform(-4.5, -3),
                                      j.ombra_y, (200, 50, 40), (230, 190, 70), 3.5))
        elif arma["id"] == "plasma":                  # el canó deixa anar vapor
            for _ in range(4):
                self.efectes.append(Particula(jx - j.direccio * 4, cy - 4, random.uniform(-0.6, 0.6), random.uniform(-1.6, -0.6),
                                              random.choice(((170, 240, 255), (210, 230, 240))), vida=22, mida=3.5))
        elif arma["id"] != "minigun" or self.n_tret % 2:      # beina expulsada cap enrere
            self.efectes.append(Beina(jx, cy + 2, -j.direccio * random.uniform(1.5, 3), random.uniform(-4, -2.5),
                                      j.ombra_y))
        if arma["id"] in ("escopeta", "plasma"):
            for _ in range(3):
                self.efectes.append(Particula(cx + math.cos(base) * 10, cy + math.sin(base) * 10, random.uniform(-0.4, 0.4),
                                              random.uniform(-0.9, -0.3), random.choice(((120, 120, 130), (90, 90, 100))),
                                              vida=30, mida=random.uniform(3, 5)))
        # retrocés: les armes pesades empenyen el soldat i sacsegen la pantalla
        empenta, sacseig = {"escopeta": (4.5, 4), "plasma": (2.4, 3), "minigun": (0.35, 1.2),
                            "fusell": (0.25, 0)}.get(arma["id"], (0.0, 0))
        self.tremolor = max(self.tremolor, sacseig)
        self.jugador.disparat(empenta, arma["id"], base)
        AUDIO.tret(arma["so"])

    def pols_jugador(self):
        """Pols als peus en córrer, saltar i aterrar; flamarada dels propulsors en el doble salt."""
        j = self.jugador
        ev = j.events
        if not ev:
            return
        px, py = j.x + j.W / 2, j.y + j.H
        color = [(170, 160, 140), (130, 125, 115), (200, 195, 180)]
        if "aterrar" in ev:
            for s in (-1, 1):
                for _ in range(6):
                    self.efectes.append(Particula(px + s * 6, py - 2, s * random.uniform(1, 3.5), random.uniform(-1.6, -0.3),
                                                  random.choice(color), vida=random.randint(14, 24), mida=random.uniform(2, 4)))
        if "salt" in ev:
            esclat(self.efectes, px, py - 2, 6, color, vel=(0.5, 2), mida=(2, 3.5), vida=(10, 18))
        if "doble_salt" in ev:
            for _ in range(12):
                self.efectes.append(Particula(px + random.uniform(-6, 6), py, random.uniform(-1, 1), random.uniform(2, 4),
                                              random.choice((CIAN, (255, 255, 255), (120, 200, 255))), vida=16, mida=3))
            self.efectes.append(Anell(px, py, CIAN, r=6, creix=2.5, vida=12))
        if "esquiva" in ev:
            for _ in range(10):
                self.efectes.append(Particula(px - j.dir_esquiva * random.uniform(0, 12), py - 2,
                                              -j.dir_esquiva * random.uniform(0.5, 2.5), random.uniform(-1.8, -0.3),
                                              random.choice(color), vida=random.randint(12, 22), mida=random.uniform(2, 4)))
        if "pas" in ev:
            self.efectes.append(Particula(px - j.direccio * 6, py - 2, -math.copysign(1, j.vx) * random.uniform(0.5, 1.5),
                                          random.uniform(-1, -0.3), random.choice(color), vida=16, mida=2.5))

    def ferir_jugador(self, dany):
        j = self.jugador
        j.vida -= dany
        j.invulnerable = j.temps_invulnerable
        self.dany_rebut += dany
        self.cop_hud = 14
        if self.nivell_millora("blindatge"):
            self.escut_t = 12
        self.tremolor = max(self.tremolor, 7)
        self.aturada = max(self.aturada, 3)
        jx, jy = j.centre
        esclat(self.efectes, jx, jy, 12, [VERMELL, (255, 140, 140)], vel=(2, 5), vida=(10, 22))
        self.textos.append(TextFlotant(jx, jy - 40, f"-{dany}", VERMELL))
        AUDIO.so("ferit")

    def matar_enemic(self, e):
        self.enemics.remove(e)
        self.marca_mort_t = 14
        cx, cy = e.centre
        if self.mode == "tutorial":                     # els blancs de l'entrenament no donen premis
            self.restes.append(Resta(e))
            esclat(self.efectes, cx, cy, 10, [TARONJA, GROC, BLANC], vel=(1, 4), mida=(2, 4), vida=(10, 20))
            AUDIO.so("impacte")
            return
        supervivencia = self.mode == "supervivencia"
        monedes = max(1, round(e.monedes * self.dificultat()["monedes"] * (0.5 if supervivencia else 1)))
        xp = max(1, e.xp // 2) if supervivencia else e.xp
        self.monedes += monedes
        self.monedes_nivell += monedes
        self.xp_nivell += xp
        self.afegir_xp(xp)
        self.comptar("baixes", "baixes", 500)
        if e.tipus == "escut" and e.cop_esquena:
            self.desbloquejar("esquena")
        if supervivencia:
            self.punts += e.xp * 10
            self.baixes += 1
        self.textos.append(TextFlotant(cx, cy - 10, f"+{monedes}", GROC))
        self.textos.append(TextFlotant(cx, cy + 6, f"+{xp} XP", (255, 200, 255), F_MINI))
        AUDIO.so("moneda")
        if e.es_boss:
            self.restes.append(MortCap(e))
            self.flaix = max(self.flaix, 10)                   # sense congelar: flaix i sacseig
            self.tremolor = max(self.tremolor, 12)
            return
        self.aturada = max(self.aturada, 2)
        if e.tipus == "kamikaze":
            self.explosio_kamikaze(e, ferir_jugador=False)
        self.restes.append(Resta(e))
        esclat(self.efectes, cx, cy, 10, [TARONJA, GROC, BLANC], vel=(1, 4), mida=(2, 4), vida=(10, 20))
        if random.random() < 0.3 and len(self.items) < 4:
            self.items.append(Item(cx - Item.W / 2, cy, self.tipus_item_necessari(), caure=True, vida=600))

    def actualitzar_joc(self):
        self.tremolor *= 0.85
        self.actualitzar_hud()
        if self.aturada > 0:                  # pausa d'impacte: tot es congela un instant
            self.aturada -= 1
            return
        self.flaix = max(0, self.flaix - 1)
        self.ambient.actualitzar()
        if self.presentacio:                  # presentació del cap: el joc s'espera
            self._actualitzar_presentacio()
            for fx in self.efectes[:]:
                if fx.actualitzar():
                    self.efectes.remove(fx)
            return
        self.temps_fase += 1
        if self.fase == "jugant":
            self.temps_joc += 1
        self.radio.actualitzar()
        teclat = pygame.key.get_pressed()
        esq = teclat[pygame.K_a] or teclat[pygame.K_LEFT]
        dre = teclat[pygame.K_d] or teclat[pygame.K_RIGHT]
        salt = teclat[pygame.K_SPACE] or teclat[pygame.K_w] or teclat[pygame.K_UP]
        avall = teclat[pygame.K_s] or teclat[pygame.K_DOWN]
        premut = pygame.mouse.get_pressed()[0]
        mx, _ = ratoli()
        j = self.jugador
        clau = (self.nivell_actual, self.escenari_actual)

        # Plataformes: les mòbils s'emporten el que tenen a sobre; les fràgils es trenquen
        for p in self.plataformes:
            res = p.actualitzar(j.terra and j.suport is p and self.fase != "mort")
            if p.dx or p.dy:
                if j.suport is p:
                    j.x += p.dx
                    j.y += p.dy
                for e in self.enemics:
                    if e.terrestre and e.suport is p:
                        e.x += p.dx
                        e.y += p.dy
            if res == "trencada":
                for _ in range(16):
                    self.efectes.append(Particula(p.rect.x + random.uniform(0, p.rect.w), p.rect.y + random.uniform(0, 12),
                                                  random.uniform(-1.5, 1.5), random.uniform(-2, 0.5),
                                                  random.choice(((92, 74, 70), (140, 116, 100), (60, 48, 46))),
                                                  vida=random.randint(25, 45), mida=random.uniform(3, 6), gravetat=0.3))
                AUDIO.so("impacte")
        solides = self.solides()

        if self.fase != "mort":
            j.actualitzar(esq, dre, salt, avall, solides, mx)
            self.pols_jugador()
        if self.mode == "tutorial":
            j.vida = max(j.vida, 1)
            self.actualitzar_tutorial()
            if self.estat != "joc":
                return
        self.perills.actualitzar(self)

        # Trets (fent la voltereta no es pot disparar)
        if self.esperar_alliberar and not premut:
            self.esperar_alliberar = False
        self.cooldown = max(0, self.cooldown - 1)
        self.clic_pendent = max(0, self.clic_pendent - 1)
        arma = ARMES[self.arma_actual]
        minigun = arma["id"] == "minigun"
        pot_disparar = self.fase == "jugant" and not self.esperar_alliberar and not j.esquiva
        disparant_minigun = minigun and premut and pot_disparar and not self.sobreescalfat
        # minigun: gira (arrencada), s'escalfa i alenteix el soldat
        self.gir = min(1.0, self.gir + 1 / ARRENCADA) if disparant_minigun else max(0.0, self.gir - 1 / 20)
        if not disparant_minigun:
            self.calor = max(0.0, self.calor - (0.9 if self.sobreescalfat else 1.1))
            if self.sobreescalfat and self.calor == 0:
                self.sobreescalfat = False
        j.factor_vel = FRE_MINIGUN if disparant_minigun else 1.0
        if self.sobreescalfat and self.t_global % 4 == 0 and minigun:
            cx, cy = j.canons(self.spr_jugador())
            self.efectes.append(Particula(cx, cy, random.uniform(-0.5, 0.5), random.uniform(-1.6, -0.8),
                                          random.choice(((210, 210, 220), (170, 170, 185))), vida=26, mida=random.uniform(3, 5)))
        if pot_disparar and self.cooldown == 0 and not (minigun and self.sobreescalfat):
            if (arma["auto"] and premut) or self.clic_pendent:
                self.clic_pendent = 0
                self.disparar()
        self.avis_bales = max(0, self.avis_bales - 1)

        # Enemics (i reforços que criden els caps)
        rj = j.rect.inflate(-4, -6)
        if self.fase == "jugant":
            for e in self.enemics[:]:
                self.bales_enemics.extend(e.actualitzar(j, self.enemics, self.efectes, solides))
                if e.invocacions:
                    cx, cy = e.centre
                    for tipus, vida in e.invocacions:
                        if len(self.enemics) < 7:
                            nou = self.crear_enemic(tipus, vida, cx + random.uniform(-60, 60), cy)
                            self.enemics.append(nou)
                            self.efectes.append(Anell(cx, cy, MORAT, creix=4, vida=18))
                    e.invocacions = []
                if e.tipus == "cacador" and not e.entrant and not j.intocable and e.hitbox.colliderect(rj):
                    self.ferir_jugador(e.dany)
                    e.rebotar()
                if e.esclatar:
                    self.enemics.remove(e)
                    self.explosio_kamikaze(e, ferir_jugador=True)
            if (self.cap and self.cap in self.enemics and not self.radio_cap
                    and self.cap.vida < self.cap.vida_max / 2):
                self.radio_cap = True                     # el cap s'enfurisma
                self.radio.afegir(RADIO.get(clau, {}).get("cap", []))
                self.flaix = max(self.flaix, 8)                    # fúria: flaix i sacseig, sense congelar
                self.tremolor = max(self.tremolor, 10)

        # Bales del jugador
        pesada = ARMES[self.arma_actual]["id"] in ("escopeta", "plasma")
        for b in self.bales[:]:
            if b.actualitzar():
                self.bales.remove(b)
                continue
            if b.y >= TERRA_Y + 2 and b.vy > 0:          # la bala toca el terra: pols i espurnes
                self.pols_impacte(b)
                self.bales.remove(b)
                continue
            if self.tocar_secrets(b):
                self.bales.remove(b)
                continue
            rb = b.rect
            for e in self.enemics:
                if b.perfora and id(e) in b.tocats:
                    continue
                if e.hitbox.colliderect(rb):
                    rebot = math.atan2(-b.vy, -b.vx)
                    if e.bloqueja(b):               # l'escut fa rebotar la bala: «ting»
                        espurnes(self.efectes, b.x, b.y, rebot, 9, [CIAN, BLANC, (180, 240, 255)], 0.7, (3, 6))
                        self.efectes.append(Anell(b.x, b.y, CIAN, r=3, creix=2, vida=7))
                        AUDIO.so("ting", 90)
                        self.bales.remove(b)
                        break
                    v = math.hypot(b.vx, b.vy) or 1.0
                    k = (2.5 if pesada else 1.0) * (0.6 if e.es_final else 1.0)
                    e.ferir(b.dany, (b.vx / v * k, b.vy / v * k))
                    e.cop_esquena = (b.x - (e.x + e.w / 2)) * e.dir < 0
                    espurnes(self.efectes, b.x, b.y, rebot, 6, [b.color[:3], BLANC, GROC])
                    self.efectes.append(Anell(b.x, b.y, BLANC, r=2, creix=1.6, vida=5))
                    self.marca_t = 8
                    self.mostrar_dany(e, b.dany)
                    AUDIO.so("impacte", 70)
                    AUDIO.so("marca", 70)
                    if e.es_boss and pesada and self.t_global - self.ultima_aturada > 14:
                        self.tremolor = max(self.tremolor, 2.5)    # els trets pesats "pesen" (sense congelar)
                        self.ultima_aturada = self.t_global
                    if b.perfora:
                        b.tocats.add(id(e))
                    else:
                        self.bales.remove(b)
                        break

        for e in self.enemics[:]:
            if e.vida <= 0:
                self.matar_enemic(e)
        for r in self.restes[:]:
            if r.actualitzar(self):
                self.restes.remove(r)

        # Bales enemigues
        for b in self.bales_enemics[:]:
            if b.actualitzar():
                self.bales_enemics.remove(b)
                continue
            if b.y >= TERRA_Y + 2 and b.vy > 0:
                self.pols_impacte(b)
                self.bales_enemics.remove(b)
                continue
            if self.fase == "jugant" and not j.intocable and rj.colliderect(b.rect):
                self.bales_enemics.remove(b)
                self.ferir_jugador(b.dany)

        # Ítems
        radi = self.radi_iman()
        iman = (j.centre, radi) if radi and self.fase != "mort" else None
        bmax_actual = self.bales_max(self.arma_actual)
        for it in self.items[:]:
            util = (j.vida < j.vida_max) if it.tipus == "vida" else (
                it.tipus != "bales" or (bmax_actual is not None and self.bales_armes[self.arma_actual] < bmax_actual))
            if it.actualitzar(solides, iman if util else None):
                self.items.remove(it)
                continue
            if self.fase == "mort" or not j.rect.colliderect(it.rect):
                continue
            i = self.arma_actual
            agafat = False
            bmax = self.bales_max(i)
            if it.tipus == "vida" and j.vida < j.vida_max:
                guany = min(20, j.vida_max - j.vida)
                j.vida = min(j.vida_max, j.vida + 20)
                agafat, etiqueta, color = True, T("+{n} VIDA").format(n=guany), VERD
            elif it.tipus == "bales" and bmax is not None and self.bales_armes[i] < bmax:
                guany = bmax - self.bales_armes[i]
                self.bales_armes[i] = bmax
                self.municio_t = 30
                agafat, etiqueta, color = True, T("+{n} BALAS").format(n=guany), GROC
            if agafat:
                self.items.remove(it)
                esclat(self.efectes, it.x + 12, it.y + 12, 12, [color, BLANC], vel=(1, 4), vida=(10, 25))
                self.textos.append(TextFlotant(it.x + 12, it.y - 10, etiqueta, color))
                AUDIO.so("item")

        if self.placa and self.fase != "mort" and j.rect.inflate(8, 8).collidepoint(self.placa):
            self.recollir_placa()
        if self.fase == "jugant" and self.mode != "tutorial":
            self.temps_spawn_items += 1
            if self.temps_spawn_items >= 300:
                self.temps_spawn_items = 0
                self.generar_item()

        for llista in (self.efectes, self.textos):
            for fx in llista[:]:
                if fx.actualitzar():
                    llista.remove(fx)

        # Fases: mort, onades, escenari net
        mort_de_cap = any(isinstance(r, MortCap) for r in self.restes)
        if self.fase == "jugant" and j.vida <= 0:
            self.fase, self.temps_fase = "mort", 0
            jx, jy = j.centre
            esclat(self.efectes, jx, jy, 50, [VERMELL, TARONJA, BLANC], vel=(2, 8), vida=(25, 50))
            self.tremolor = 16
            self.radio.buidar()
            AUDIO.aturar_musica()
        elif self.fase == "jugant" and not self.enemics and not mort_de_cap and self.mode != "tutorial":
            if self.espera_onada:
                self.espera_onada -= 1
                if self.espera_onada == 0:
                    self.seguent_onada()
            elif self.mode == "supervivencia":
                self.onades_superades += 1
                self.punts += 100 * self.onada
                self.espera_onada = 150
                j.vida = min(j.vida_max, j.vida + 10)
                AUDIO.so("passi")
            elif self.onada + 1 < len(self.onades):
                self.espera_onada = 110
                AUDIO.so("boss")
            else:
                self.fase, self.temps_fase = "net", 0
                self.bales_enemics.clear()
                self.radio.buidar()
                self.completar_escenari()
        elif self.fase == "mort" and self.temps_fase > 75:
            if self.mode == "supervivencia":
                self.mostrar_fi_supervivencia()
            else:
                self.mostrar_derrota()
        elif self.fase == "net" and self.temps_fase > 220:
            n, e = clau
            if (n, e) == (NUM_SECTORS - 1, 2):
                seguent = self.entrar_credits_finals
            elif e < 2:
                seguent = lambda: self.mostrar_narrativa(n, e + 1)  # noqa: E731
            else:
                seguent = lambda: self.mostrar_narrativa(n + 1, 0)  # noqa: E731
            if clau in CINEMATICA_CAP:
                self.veure_cinematica(CINEMATICA_CAP[clau], seguent)
            else:
                seguent()

    def completar_escenari(self):
        n, e = self.nivell_actual, self.escenari_actual
        primera = not self.completats[n][e]
        self.completats[n][e] = True
        if e < 2:
            self.nivells_desbloquejats[n][e + 1] = True
        elif n < NUM_SECTORS - 1:
            self.nivells_desbloquejats[n + 1][0] = True
        # estrelles: completar, sense rebre mal, i abans del temps
        noves = [True, self.dany_rebut == 0, self.temps_joc <= TEMPS_ESTRELLA[(n, e)] * FPS]
        abans = self.estrelles[n][e]
        guanyades = [nv and not ab for nv, ab in zip(noves, abans)]
        self.estrelles[n][e] = [a or b for a, b in zip(abans, noves)]
        self.estrelles_noves = (noves, guanyades)
        if (n, e) in PRESENTACIO_CAPS and self.dany_rebut == 0:       # un cap sense cap cop
            self.desbloquejar("intocable")
        if (n, e) == (4, 2):
            if self.nivell_dificultat == "dificil":
                self.desbloquejar("dificil")
            if self.armes_usades <= {"pistola"}:
                self.desbloquejar("pistola")
        self.revisar_logros()
        xp = XP_ESCENARI + (XP_PRIMERA_VEGADA if primera else 0) + XP_ESTRELLA * sum(guanyades)
        self.xp_nivell += xp
        self.afegir_xp(xp)
        if primera and e == 2:
            self.avis(T("Historia desbloqueada: {h}").format(h=T(ARXIU[n][0])), CIAN, 260)
        self.desar_progres()

    # ----- Dibuix -----------------------------------------------------------
    def dificultat(self):
        return DIFICULTATS.get(self.nivell_dificultat, DIFICULTATS["normal"])

    def dany_dificultat(self, dany):
        return max(1, round(dany * self.dificultat()["dany"]))

    def solides(self):
        return [p for p in self.plataformes if p.solida]

    def llançar_onada(self, llista, reforç=False):
        """Fa aparèixer una onada d'enemics repartits per la pantalla (lluny del jugador)."""
        n = len(llista)
        if not n:
            return
        franja = (WIDTH - 260) / n
        jx = self.jugador.x + self.jugador.W / 2
        nous = []
        for i, (tipus, vida) in enumerate(llista):
            e = self.crear_enemic(tipus, vida)
            x = 220 + franja * i + random.uniform(0, max(1, franja - e.w))
            if reforç and abs(x + e.w / 2 - jx) < 130:            # que no caiguin damunt del jugador
                x = (x + 300) % (WIDTH - e.w - 20) + 10
            e.x = max(10.0, min(WIDTH - e.w - 10.0, x))
            nous.append(e)
        self.enemics += nous
        cap = next((e for e in nous if e.es_boss), None)
        if cap:
            self.cap = cap
            self.radio_cap = False
            clau = (self.nivell_actual, self.escenari_actual)
            if self.mode == "historia" and clau in PRESENTACIO_CAPS and not self.presentat:
                self.presentat = True
                nom, sub = PRESENTACIO_CAPS[clau]
                self.presentacio = {"e": cap, "t": 0, "nom": nom, "sub": sub}
                AUDIO.so("boss")

    def llançar_onada_supervivencia(self, k):
        """Supervivència: cada onada té més enemics i més forts; cada cinc, un cap."""
        self.onada = k
        self.nivell_enemics = min(4, k // 3)
        if k >= 10:
            self.desbloquejar("onada10")
        if k >= 20:
            self.desbloquejar("onada20")
        base = {"dron": 30, "soldat": 30, "kamikaze": 25, "lloctinent": 60, "cacador": 50, "escut": 90}
        tipus = ["dron", "soldat"] + (["kamikaze", "lloctinent"] if k >= 3 else []) + (["cacador", "escut"] if k >= 5 else [])
        n = min(9, 2 + k // 2 + (k > 3))
        llista = []
        if k % 5 == 0:
            llista.append(("boss", 80 + 25 * k))
            n = max(2, n - 3)
        llista += [(t, base[t] + 7 * k) for t in (random.choice(tipus) for _ in range(n))]
        self.llançar_onada(llista, reforç=k > 1)

    def seguent_onada(self):
        if self.mode == "supervivencia":
            self.llançar_onada_supervivencia(self.onada + 1)
            return
        self.onada += 1
        self.llançar_onada(self.onades[self.onada], reforç=True)
        self.radio.afegir(RADIO.get((self.nivell_actual, self.escenari_actual), {}).get("onada", []))

    def esquivar(self):
        teclat = pygame.key.get_pressed()
        sentit = (1 if teclat[pygame.K_d] or teclat[pygame.K_RIGHT] else 0) - \
                 (1 if teclat[pygame.K_a] or teclat[pygame.K_LEFT] else 0)
        if self.jugador.esquivar(sentit or None):
            AUDIO.so("envestida", 100)
            self.comptar("voltes", "voltes", 100)

    def explosio_kamikaze(self, e, ferir_jugador):
        cx, cy = e.centre
        esclat(self.efectes, cx, cy, 40, [TARONJA, VERMELL, GROC, BLANC], vel=(2, 8), mida=(3, 7), vida=(15, 40))
        self.efectes.append(Anell(cx, cy, TARONJA, creix=5, vida=18))
        self.efectes.append(Anell(cx, cy, BLANC, creix=3, vida=12))
        self.tremolor = max(self.tremolor, 9)
        AUDIO.so("explosio", 80)
        radi = 85
        j = self.jugador
        jx, jy = j.centre
        if ferir_jugador and self.fase == "jugant" and not j.intocable and math.hypot(jx - cx, jy - cy) < radi:
            self.ferir_jugador(e.dany)
            if j.vida <= 0:
                self.desbloquejar("suicida")
        for o in self.enemics:                        # l'explosió també fa mal als altres aliens
            if o is not e and math.hypot(o.centre[0] - cx, o.centre[1] - cy) < radi:
                o.ferir(30)
                if o.vida <= 0:
                    self.desbloquejar("carambola")

    def pos_ull(self):
        """Posició a la pantalla de l'ull de la torre de vigilància del fons de l'1-1."""
        return 840 + self.fons_off[0], 134 + self.fons_off[1]

    def tocar_secrets(self, b):
        """Secrets que es poden disparar: l'ull de la torre (1-1) i els ovnis que creuen el cel del fons."""
        if self.ull_vida > 0:
            ux, uy = self.pos_ull()
            if math.hypot(b.x - ux, b.y - uy) < 14:
                self.ull_vida -= 1
                esclat(self.efectes, b.x, b.y, 6, [MORAT, ROSA, BLANC], vel=(1, 3), vida=(8, 16))
                if self.ull_vida == 0:
                    self.ull_destruit = True
                    esclat(self.efectes, ux, uy, 40, [MORAT, ROSA, BLANC, TARONJA], vel=(2, 7), mida=(3, 6), vida=(20, 45))
                    self.efectes.append(Anell(ux, uy, ROSA, creix=4, vida=20))
                    AUDIO.so("explosio")
                    self.desbloquejar("ull")
                return True
        for o in self.ambient.ovnis[:]:
            if pygame.Rect(int(o[0]), int(o[1]), 30, 12).collidepoint(b.x, b.y):
                self.ambient.ovnis.remove(o)
                esclat(self.efectes, o[0] + 15, o[1] + 6, 24, [TARONJA, GROC, BLANC], vel=(1, 5), vida=(15, 35))
                self.efectes.append(Anell(o[0] + 15, o[1] + 6, BLANC, creix=3, vida=14))
                AUDIO.so("explosio", 80)
                self.desbloquejar("ovni")
                return True
        return False

    def recollir_placa(self):
        x, y = self.placa
        self.placa = None
        self.plaques.add(f"{self.nivell_actual}_{self.escenari_actual}")
        esclat(self.efectes, x, y, 18, [BLANC, (200, 200, 210), GROC], vel=(1, 4), vida=(15, 30))
        self.textos.append(TextFlotant(x, y - 20, T("Placa {n}/{t}").format(n=len(self.plaques), t=len(PLAQUES)),
                                       (220, 225, 240)))
        AUDIO.so("item")
        self.desbloquejar("placa")
        if len(self.plaques) >= len(PLAQUES):
            self.desbloquejar("placas")
        self.desar_progres()

    def _actualitzar_presentacio(self):
        pr = self.presentacio
        pr["t"] += 1
        e = pr["e"]
        if e.entrant and not e.terrestre:
            e.y = min(e.y + 3, e.y_destinacio)
            if e.y >= e.y_destinacio:
                e.entrant = False
        if pr["t"] == 120:
            self.flaix = 8
            self.tremolor = 10
        if pr["t"] >= 170:
            self.presentacio = None

    def veure_cinematica(self, clau, despres):
        AUDIO.musica({"comandant": "sector4", "nau": "sector5", "final": "final"}.get(clau, "menu"))

        def fi():
            if clau == "final" and not self.intro.saltada:
                self.desbloquejar("fins_final")
            despres()
        self.intro = Intro(fi, CINEMATIQUES[clau])
        self.botons = []
        self.canviar_estat("intro")

    def entrar_credits_finals(self):
        self.entrar_credits()
        AUDIO.musica("final")

    def entrar_supervivencia(self):
        self.confirmar_reinici = False
        AUDIO.musica("menu")
        b = []
        for i, (n, e) in enumerate(ARENES):
            oberta = any(self.nivells_desbloquejats[n])
            b.append(Boto((60, 150 + i * 50, 300, 42), NOMS_ARENES[i] if oberta else "? ? ?",
                          (lambda i=i: self.triar_arena(i)) if oberta else None,
                          VERD if i == self.arena else BLAU, font=F_HUD))
        b.append(Boto((60, 412, 300, 48), "¡A luchar!", self.iniciar_supervivencia, TARONJA))
        b.append(self.boto_tornar())
        self.botons = b
        self.canviar_estat("supervivencia")

    def triar_arena(self, i):
        self.arena = i
        self.entrar_supervivencia()

    def iniciar_supervivencia(self):
        self.mode = "supervivencia"
        self.nivell_actual, self.escenari_actual = ARENES[self.arena]
        self.onades_superades = 0
        self.iniciar_joc()

    def mostrar_fi_supervivencia(self):
        rec = {"punts": self.punts, "onada": self.onades_superades, "arena": self.arena,
               "dificultat": self.nivell_dificultat}
        nou = not self.records or self.punts > max(r["punts"] for r in self.records)
        self.records = sorted(self.records + [rec], key=lambda r: -r["punts"])[:5]
        self.desar_progres()
        AUDIO.aturar_musica()
        AUDIO.so("eliminat")
        botons = [Boto((WIDTH // 2 - 230, HEIGHT - 110, 200, 50), "Menú", self.entrar_supervivencia, GRIS_FOSC),
                  Boto((WIDTH // 2 + 30, HEIGHT - 110, 200, 50), "Reintentar", self.iniciar_supervivencia, VERMELL)]
        cos = T("Has superado {o} oleadas y eliminado a {b} enemigos.").format(o=self.onades_superades, b=self.baixes)
        peu = [(T("Puntos: {p}").format(p=self.punts), GROC)]
        if nou and self.punts > 0:
            peu.append((T("¡NUEVO RÉCORD!"), VERD))
        self.pantalla_text = PantallaText("FIN DE LA PARTIDA", cos, VERMELL, botons, self.fons_derrota,
                                          pista="R / ENTER: reintentar  ·  ESC: menú", peu=peu)
        self.botons = botons
        self.canviar_estat("derrota")

    def dibuixar_supervivencia(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, T("SUPERVIVENCIA"), F_SUBTITOL, TARONJA, (WIDTH // 2, 44))
        text(surf, T("Oleadas sin fin. Cada cinco, un jefe. ¿Cuánto aguantarás?"), F_TEXT_P, BLANC, (WIDTH // 2, 92))
        text(surf, T("ARENA"), F_HUD, CIAN, (60, 132), ancora="midleft")
        r = pygame.Rect(410, 128, 510, 268)
        panell(surf, r, TARONJA)
        text(surf, T("RÉCORDS"), F_TEXT, TARONJA, (r.centerx, r.top + 22))
        cols = [(r.left + 30, "#"), (r.left + 70, T("Puntos")), (r.left + 200, T("Oleadas")),
                (r.left + 300, T("Arena")), (r.left + 400, T("Dificultad"))]
        for x, nom in cols:
            text(surf, nom, F_MINI, GRIS, (x, r.top + 52), ancora="midleft")
        if not self.records:
            text(surf, T("Todavía no hay récords."), F_TEXT_P, GRIS, (r.centerx, r.top + 140))
        for i, rec in enumerate(self.records):
            y = r.top + 84 + i * 36
            valors = [str(i + 1), str(rec["punts"]), str(rec.get("onada", 0)),
                      T(NOMS_ARENES[rec.get("arena", 0) % len(ARENES)]),
                      T(DIFICULTATS.get(rec.get("dificultat"), DIFICULTATS["normal"])["nom"])]
            for (x, _), v in zip(cols, valors):
                text(surf, v, F_TEXT_P, GROC if i == 0 else BLANC, (x, y), ancora="midleft")
        text(surf, T("Dificultad: {d} (se cambia en Opciones)").format(d=T(self.dificultat()["nom"])), F_TEXT_PP,
             GRIS, (r.centerx, r.bottom + 22))
        text(surf, T("Monedas y XP a la mitad · todas tus armas permitidas"), F_TEXT_PP, GRIS, (r.centerx, r.bottom + 46))

    # ----- Opcions --------------------------------------------------------------

    def posar_dificultat(self, ident):
        self.nivell_dificultat = ident
        self.desar_progres()
        self.entrar_opcions(self.tornada_opcions)

    def posar_idioma(self, ident):
        canviar_idioma(ident)
        self.desar_progres()
        self.entrar_opcions(self.tornada_opcions)

    def dibuixar_presentacio(self, surf):
        """Entrada del cap: franges de cine, el nom en gran i un cop de llum."""
        pr = self.presentacio
        t = pr["t"]
        k = min(1.0, t / 18) if t < 150 else max(0.0, (170 - t) / 20)
        alt = int(78 * k)
        pygame.draw.rect(surf, NEGRE, (0, 0, WIDTH, alt))
        pygame.draw.rect(surf, NEGRE, (0, HEIGHT - alt, WIDTH, alt))
        if t > 14 and t < 160:
            e = pr["e"]
            l = llum(int(max(e.w, e.h) * 0.9), (255, 80, 80))
            l.set_alpha(int(90 + 40 * math.sin(t * 0.2)))
            surf.blit(l, l.get_rect(center=(int(e.centre[0]), int(e.centre[1]))))
            l.set_alpha(255)
            x_nom = WIDTH // 2 + max(0, 40 - t) * 28
            x_sub = WIDTH // 2 - max(0, 52 - t) * 24
            text(surf, pr["nom"], F_TITOL, (255, 225, 225), (x_nom, HEIGHT - 132))
            pygame.draw.line(surf, VERMELL, (x_nom - 260, HEIGHT - 104), (x_nom + 260, HEIGHT - 104), 2)
            text(surf, pr["sub"], F_TEXT, (255, 190, 190), (x_sub, HEIGHT - 80))
            text(surf, "ESPACIO / clic: saltar", F_MINI, GRIS, (WIDTH - 14, HEIGHT - 14), ancora="midright")

    def desbloquejar(self, ident):
        """Desbloqueja un logro: avís a la pantalla, monedes de premi i desat."""
        if ident in self.logros or ident not in LOGRO_PER_ID:
            return
        self.logros.add(ident)
        logro = LOGRO_PER_ID[ident]
        premi = CATEGORIES_LOGRO[logro["cat"]]["monedes"]
        self.monedes += premi
        self.avisos_logro.append([logro, 0])
        AUDIO.so("passi")
        if ident != "plati" and all(l["id"] in self.logros for l in LOGROS if l["id"] != "plati"):
            self.desbloquejar("plati")
        self.desar_progres()

    def revisar_logros(self):
        """Logros que depenen de l'estat (també serveix per a partides antigues)."""
        c = self.completats
        for (n, e), ident in (((0, 0), "primer"), ((0, 2), "sector1"), ((1, 2), "sector2"), ((2, 2), "comandant"),
                              ((3, 2), "nau"), ((4, 2), "final")):
            if c[n][e]:
                self.desbloquejar(ident)
        if sum(e[2] for fila in self.estrelles for e in fila) >= 5:
            self.desbloquejar("rellotge")
        if all(all(e) for fila in self.estrelles for e in fila):
            self.desbloquejar("estrelles")
        if all(a["id"] in self.armes_propies for a in ARMES):
            self.desbloquejar("arsenal")
        if all(self.nivell_millora(m["id"]) >= len(m["costos"]) for m in MILLORES):
            self.desbloquejar("millores")
        if self.uniforme == "daurat" and self.aparenca == "daurat":
            self.desbloquejar("daurat")
        if self.estadistiques.get("baixes", 0) >= 500:
            self.desbloquejar("baixes")
        if self.estadistiques.get("voltes", 0) >= 100:
            self.desbloquejar("voltes")
        if self.plaques:
            self.desbloquejar("placa")
        if len(self.plaques) >= len(PLAQUES):
            self.desbloquejar("placas")

    def comptar(self, clau, logro=None, objectiu=None):
        self.estadistiques[clau] = self.estadistiques.get(clau, 0) + 1
        if logro and self.estadistiques[clau] >= objectiu:
            self.desbloquejar(logro)

    def dibuixar_avisos_logro(self, surf):
        """Avís de logro desbloquejat (com els trofeus de les consoles), a dalt a la dreta."""
        for k, av in enumerate(self.avisos_logro[:3]):
            logro, t = av
            entrada = min(1.0, t / 14) if t < 220 else max(0.0, (240 - t) / 20)
            caixa = pygame.Rect(0, 84 + k * 60, 340, 54)
            caixa.x = int(WIDTH - 12 - caixa.w * entrada)
            capa = pygame.Surface(caixa.size, pygame.SRCALPHA)
            capa.fill((8, 10, 24, 225))
            surf.blit(capa, caixa)
            cat = CATEGORIES_LOGRO[logro["cat"]]
            pygame.draw.rect(surf, cat["color"], caixa, 2, border_radius=6)
            dibuixar_medalla(surf, caixa.x + 28, caixa.centery, 20, logro["cat"])
            text(surf, "LOGRO DESBLOQUEADO", F_MINI, cat["color"], (caixa.x + 56, caixa.y + 13), ancora="midleft")
            text(surf, logro["nom"], F_TEXT_P, BLANC, (caixa.x + 56, caixa.y + 34), ancora="midleft")
            r = text(surf, f"+{cat['monedes']}", F_MINI, GROC, (caixa.right - 10, caixa.y + 13), ancora="midright")
            dibuixar_moneda(surf, r.left - 10, r.centery, 5)

    def entrar_logros(self, pagina=None):
        self.confirmar_reinici = False
        self.menu_idioma = False
        if pagina is not None:
            self.pagina_logros = pagina
        pagines = (len(LOGROS) + 11) // 12
        self.pagina_logros = max(0, min(pagines - 1, self.pagina_logros))
        b = [self.boto_tornar()]
        if self.pagina_logros > 0:
            b.append(Boto((WIDTH // 2 - 130, 470, 60, 40), "<", lambda: self.entrar_logros(self.pagina_logros - 1)))
        if self.pagina_logros < pagines - 1:
            b.append(Boto((WIDTH // 2 + 70, 470, 60, 40), ">", lambda: self.entrar_logros(self.pagina_logros + 1)))
        self.botons = b
        self.canviar_estat("logros")

    def dibuixar_logros(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "LOGROS", F_SUBTITOL, GROC, (WIDTH // 2, 34))
        fets = len(self.logros & set(LOGRO_PER_ID))
        barra = pygame.Rect(WIDTH // 2 - 220, 74, 440, 10)
        pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=5)
        pygame.draw.rect(surf, GROC, (barra.x, barra.y, int(barra.w * fets / len(LOGROS)), barra.h), border_radius=5)
        text(surf, f"{fets}/{len(LOGROS)} · {round(100 * fets / len(LOGROS))}%", F_HUD, BLANC, (barra.right + 70, barra.centery))
        dibuixar_trofeu(surf, barra.x - 24, barra.centery, 20)
        inici = self.pagina_logros * 12
        for k, logro in enumerate(LOGROS[inici:inici + 12]):
            fila, col = divmod(k, 3)
            r = pygame.Rect(24 + col * 308, 98 + fila * 90, 296, 82)
            obert = logro["id"] in self.logros
            secret = logro.get("secret") and not obert
            panell(surf, r, CATEGORIES_LOGRO[logro["cat"]]["color"] if obert else GRIS_FOSC)
            dibuixar_medalla(surf, r.x + 32, r.centery, 22, logro["cat"], obert)
            nom = T("Logro secreto") if secret else T(logro["nom"])
            font_nom = F_TEXT_P if F_TEXT_P.size(nom)[0] <= r.w - 72 else F_TEXT_PP
            text(surf, nom, font_nom, BLANC if obert else GRIS, (r.x + 64, r.y + 16), ancora="midleft")
            desc = T(logro.get("pista", "")) if secret else T(logro["desc"])
            for i, linia in enumerate(ajustar_linies(desc, F_TEXT_PP, r.w - 76)[:3]):
                text(surf, linia, F_TEXT_PP, (200, 205, 225) if obert else (110, 112, 134), (r.x + 64, r.y + 34 + i * 17),
                     ancora="topleft", ombra=False)
        pagines = (len(LOGROS) + 11) // 12
        text(surf, f"{self.pagina_logros + 1}/{pagines}", F_UI, BLANC, (WIDTH // 2, 490))
        text(surf, "Bronce 50 · Plata 150 · Oro 400 · Platino 1000 monedas", F_MINI, GRIS, (WIDTH - 20, 520),
             ancora="midright")

    def rects_idioma(self):
        return {codi: pygame.Rect(22, 66 + k * 44, 200, 38) for k, codi in enumerate(IDIOMES)}

    def gestionar_menu_idioma(self, ev):
        """Amb el desplegable d'idiomes obert, el clic tria una bandera o el tanca."""
        if ev.type != pygame.MOUSEBUTTONDOWN or ev.button != 1:
            return False
        for codi, r in self.rects_idioma().items():
            if r.collidepoint(ev.pos):
                AUDIO.so("click")
                canviar_idioma(codi)
                break
        self.menu_idioma = False
        self.desar_progres()
        self.entrar_menu()
        return True

    def obrir_menu_idioma(self):
        self.menu_idioma = not self.menu_idioma

    def dibuixar_icones_menu(self, surf):
        pos = ratoli()
        for r, tipus in ((pygame.Rect(16, 12, 44, 40), "idioma"), (pygame.Rect(68, 12, 44, 40), "logros"),
                         (pygame.Rect(120, 12, 44, 40), "novetats")):
            hover = r.collidepoint(pos) or (tipus == "idioma" and self.menu_idioma)
            pygame.draw.rect(surf, NEGRE, r.move(0, 3), border_radius=8)
            pygame.draw.rect(surf, (52, 60, 110) if hover else (30, 34, 66), r, border_radius=8)
            pygame.draw.rect(surf, BLAU_CLAR if hover else (80, 90, 140), r, 2, border_radius=8)
            if tipus == "idioma":
                dibuixar_globus(surf, r.centerx, r.centery, 13)
            elif tipus == "novetats":                      # full de notícies
                full = pygame.Rect(r.centerx - 10, r.centery - 13, 20, 26)
                pygame.draw.rect(surf, (235, 232, 215), full, border_radius=2)
                pygame.draw.rect(surf, NEGRE, full, 1, border_radius=2)
                pygame.draw.rect(surf, VERMELL, (full.x + 3, full.y + 3, 14, 4))
                for k in range(4):
                    pygame.draw.line(surf, GRIS, (full.x + 3, full.y + 11 + k * 4), (full.right - 4, full.y + 11 + k * 4))
            else:
                dibuixar_trofeu(surf, r.centerx, r.centery + 1, 22)
                fets = len(self.logros & set(LOGRO_PER_ID))
                text(surf, str(fets), F_MINI, GROC, (r.right - 4, r.bottom - 4), ancora="bottomright")
        if self.menu_idioma:
            caixa = pygame.Rect(14, 58, 216, 146)
            panell(surf, caixa, BLAU_CLAR, 235)
            for codi, r in self.rects_idioma().items():
                actiu = idioma() == codi
                if r.collidepoint(pos) or actiu:
                    pygame.draw.rect(surf, (60, 90, 160) if not actiu else (40, 120, 70), r, border_radius=6)
                dibuixar_bandera(surf, codi, (r.x + 8, r.y + 7, 36, 24))
                text(surf, IDIOMES[codi], F_TEXT_P, BLANC, (r.x + 56, r.centery), ancora="midleft")

    def contingut_credits(self):
        return [
            ("logo",), ("espai", 26), ("petit", "UN JUEGO DE"), ("gran", "ABEL"), ("espai", 46),
            ("seccio", "PROGRAMACIÓN"), ("nom", "Abel"),
            ("seccio", "DISEÑO DE JUEGO Y NIVELES"), ("nom", "Abel"),
            ("seccio", "HISTORIA Y GUION"), ("nom", "Abel"),
            ("seccio", "GRÁFICOS Y ANIMACIONES"), ("nom", "Abel"),
            ("text", "Fondos, sprites y cinemáticas en pixel art"),
            ("seccio", "MÚSICA"), ("nom", "Abel"),
            ("text", "Temas chiptune creados para el juego y pistas libres de derechos"),
            ("seccio", "EFECTOS DE SONIDO"), ("text", "Sonidos libres de derechos"),
            ("seccio", "TIPOGRAFÍAS"), ("text", "Press Start 2P · VT323 (SIL Open Font License)"),
            ("seccio", "HECHO CON"), ("text", "Python · pygame-ce · pygbag"),
            ("seccio", "AGRADECIMIENTOS"), ("text", "A todos los que juegan y prueban el juego"),
            ("espai", 70), ("gracies", "¡Gracias por jugar!"), ("text", f"{T('Versión')} {VERSIO}"), ("espai", 60),
        ]

    def entrar_idioma_inicial(self):
        AUDIO.musica("menu")
        self.novetats_vistes = NOVETATS[0]["versio"]           # qui juga per primer cop no les necessita
        b = []
        for k, codi in enumerate(IDIOMES):
            b.append(Boto(self.rect_idioma_inicial(k), "", lambda c=codi: self.triar_idioma_inicial(c), invisible=True))
        self.botons = b
        self.canviar_estat("idioma_inicial")

    def rect_idioma_inicial(self, k):
        return pygame.Rect(WIDTH // 2 - 345 + k * 240, 170, 210, 200)

    def triar_idioma_inicial(self, codi):
        canviar_idioma(codi)
        self.desar_progres()
        self.entrar_intro(self.entrar_tutorial_inicial)

    def entrar_tutorial_inicial(self):
        self.iniciar_tutorial(lambda: self.entrar_ajuda(despres=self.entrar_menu))

    def dibuixar_idioma_inicial(self, surf):
        self.fons_menu.dibuixar(surf)
        for k, (txt, font) in enumerate((("Elige tu idioma", F_TEXT), ("Tria el teu idioma", F_TEXT_P),
                                         ("Choose your language", F_TEXT_P))):
            img = render(txt, font, BLANC if k == 0 else GRIS)
            surf.blit(img, img.get_rect(center=(WIDTH // 2, 70 + k * 32)))
        pos = ratoli()
        for k, codi in enumerate(IDIOMES):
            r = self.rect_idioma_inicial(k)
            hover = r.collidepoint(pos)
            panell(surf, r.move(0, -4 if hover else 0), GROC if hover else BLAU_CLAR)
            bandera = pygame.Rect(0, 0, 150, 96)
            bandera.center = (r.centerx, r.y + 78 - (4 if hover else 0))
            dibuixar_bandera(surf, codi, bandera)
            img = render(IDIOMES[codi], F_TEXT, BLANC)
            surf.blit(img, img.get_rect(center=(r.centerx, r.bottom - 36 - (4 if hover else 0))))
        img = render("ESP / CAT / ENG", F_MINI, GRIS)
        surf.blit(img, img.get_rect(center=(WIDTH // 2, HEIGHT - 40)))

    # ----- Entrenament ------------------------------------------------------------

    def iniciar_tutorial(self, despres=None):
        self.tut_despres = despres or self.entrar_menu
        self.mode = "tutorial"
        self.arma_abans_tutorial = self.arma_actual
        self.arma_actual = ARMA_PER_ID["pistola"]
        self.nivell_actual, self.escenari_actual = 0, 0
        self.iniciar_joc()

    def boto_saltar_tutorial(self):
        return Boto((WIDTH - 176, HEIGHT - 44, 160, 32), "Saltar tutorial", self.acabar_tutorial, GRIS_FOSC, font=F_MINI)

    def acabar_tutorial(self):
        self.mode = "historia"
        self.arma_actual = getattr(self, "arma_abans_tutorial", self.arma_actual)
        self.tutorial_vist = True
        self.desar_progres()
        self.tut_despres()

    def començar_pas_tutorial(self):
        t = self.tut
        t["t"], t["fet"], t["comptador"] = 0, 0, 0
        clau = PASSOS_TUTORIAL[t["pas"]][0]
        j = self.jugador
        if clau == "disparar":
            for x, y in ((380, 150), (560, 110), (760, 170)):
                e = self.crear_enemic("dron", 12, x, y)
                e.temps_atac = -10 ** 9                   # són blancs: no disparen
                e.vmax = 0.6
                self.enemics.append(e)
        elif clau == "arma":
            self.armes_usades = set()
        elif clau == "items":
            j.vida = 60
            self.bales_armes[self.arma_actual] = min(3, self.bales_armes[self.arma_actual] or 3)
            self.items = [Item(460, TERRA_Y - 30, "vida"), Item(700, TERRA_Y - 30, "bales")]

    def actualitzar_tutorial(self):
        t = self.tut
        if t["pas"] >= len(PASSOS_TUTORIAL):
            return
        t["t"] += 1
        j = self.jugador
        if t["fet"]:
            t["fet"] += 1
            if t["fet"] > 70:
                t["pas"] += 1
                if t["pas"] >= len(PASSOS_TUTORIAL):
                    self.acabar_tutorial()
                    return
                self.començar_pas_tutorial()
            return
        clau = PASSOS_TUTORIAL[t["pas"]][0]
        plats = self.plataformes
        if clau != "items":                           # a l'entrenament no s'acaben les bales
            self.bales_armes = [self.bales_max(i) for i in range(len(ARMES))]
        if clau == "moure":
            t["comptador"] += abs(j.vx)
            fet = t["comptador"] > 320
        elif clau == "saltar":
            fet = j.terra and j.suport is not None and j.suport is not plats[0]
        elif clau == "alt":
            fet = j.terra and j.suport is plats[2]
        elif clau == "baixar":
            fet = j.baixar > 0
        elif clau == "voltereta":
            if "esquiva" in j.events:
                t["comptador"] += 1
            fet = t["comptador"] >= 2
        elif clau == "disparar":
            fet = not self.enemics and not self.restes
        elif clau == "arma":
            fet = ARMES[self.arma_actual]["id"] == "fusell"
        elif clau == "items":
            fet = not self.items
        else:
            fet = t["t"] > 240
        if fet:
            t["fet"] = 1
            if clau != "fi":
                AUDIO.so("item")
                jx, jy = j.centre
                esclat(self.efectes, jx, jy - 20, 16, [VERD, BLANC, GROC], vel=(1, 4), vida=(15, 30))

    def dibuixar_tutorial(self, surf):
        t = self.tut
        pas = min(t["pas"], len(PASSOS_TUTORIAL) - 1)
        caixa = pygame.Rect(WIDTH // 2 - 310, 84, 620, 78)
        capa = pygame.Surface(caixa.size, pygame.SRCALPHA)
        capa.fill((6, 10, 22, 215))
        surf.blit(capa, caixa)
        fet = t["fet"] > 0
        pygame.draw.rect(surf, VERD if fet else CIAN, caixa, 2, border_radius=6)
        text(surf, T("ENTRENAMIENTO · PASO {n}/{t}").format(n=pas + 1, t=len(PASSOS_TUTORIAL)), F_MINI,
             VERD if fet else CIAN, (caixa.x + 14, caixa.y + 14), ancora="midleft")
        for k in range(len(PASSOS_TUTORIAL)):
            color = VERD if k < pas or (k == pas and fet) else (CIAN if k == pas else GRIS_FOSC)
            pygame.draw.circle(surf, color, (caixa.right - 16 - (len(PASSOS_TUTORIAL) - 1 - k) * 14, caixa.y + 14), 4)
        for i, linia in enumerate(ajustar_linies(T(PASSOS_TUTORIAL[pas][1]), F_TEXT_P, caixa.w - 28)[:2]):
            text(surf, linia, F_TEXT_P, BLANC, (caixa.x + 14, caixa.y + 28 + i * 22), ancora="topleft")
        if fet and PASSOS_TUTORIAL[pas][0] != "fi":
            text(surf, "¡Bien!", F_TITOL, VERD, (WIDTH // 2, caixa.bottom + 46))

    # ----- Com funciona (Battle Pass, millores, armes, logros) ---------------------------
    PAGINES_AJUDA = ("BATTLE PASS", "MEJORAS", "ARMAS Y POTENCIA", "ESTRELLAS, LOGROS Y SUPERVIVENCIA")

    def entrar_ajuda(self, pagina=0, despres=None):
        if despres is not None:
            self.ajuda_despres = despres
        self.pagina_ajuda = pagina
        ultima = pagina == len(self.PAGINES_AJUDA) - 1
        b = [Boto((WIDTH // 2 + 20, HEIGHT - 62, 220, 46), "¡A jugar!" if ultima else "Siguiente  >",
                  self.ajuda_despres if ultima else (lambda: self.entrar_ajuda(pagina + 1)), VERD if ultima else BLAU)]
        if pagina > 0:
            b.append(Boto((WIDTH // 2 - 240, HEIGHT - 62, 220, 46), "<  Anterior", lambda: self.entrar_ajuda(pagina - 1),
                          GRIS_FOSC))
        b.append(Boto((WIDTH - 126, 16, 110, 30), "Saltar  >>", self.ajuda_despres, GRIS_FOSC, font=F_MINI))
        self.botons = b
        self.canviar_estat("ajuda")

    def dibuixar_ajuda(self, surf):
        self.fons_menu.dibuixar(surf)
        p = self.pagina_ajuda
        text(surf, self.PAGINES_AJUDA[p], F_SUBTITOL, GROC, (WIDTH // 2, 40))
        for k in range(len(self.PAGINES_AJUDA)):
            pygame.draw.circle(surf, BLANC if k == p else GRIS_FOSC, (WIDTH // 2 - 30 + k * 20, 72), 5)
        r = pygame.Rect(40, 92, WIDTH - 80, 370)
        panell(surf, r, BLAU_CLAR, 200)
        getattr(self, f"_ajuda_{p}")(surf, r)

    def _punts(self, surf, x, y, ample, linies, salt=8):
        for linia in linies:
            parts = ajustar_linies(T(linia), F_TEXT_P, ample - 24)
            pygame.draw.rect(surf, GROC, (x, y + 8, 8, 8))
            for i, tros in enumerate(parts):
                text(surf, tros, F_TEXT_P, BLANC, (x + 20, y + i * 24), ancora="topleft")
            y += len(parts) * 24 + salt
        return y

    def _ajuda_0(self, surf, r):
        """Battle Pass animat: el soldat abat drons, l'XP vola a la barra i es desbloquegen recompenses."""
        cicle = 50
        t = self.temps_estat % (25 * cicle + 120)
        baixes, f = t // cicle, t % cicle
        if baixes >= 25:                                   # nivell 5: una pausa abans de tornar a començar
            baixes, f = 25, 0
        nivell = min(5, baixes // 5)
        xp = (baixes % 5) * 40 + (min(40, (f - 38) * 4) if f >= 38 else 0)
        barra = pygame.Rect(r.x + 30, r.y + 34, 330, 12)
        pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=6)
        pygame.draw.rect(surf, (255, 130, 255), (barra.x, barra.y, int(barra.w * min(1, xp / 200)), barra.h), border_radius=6)
        text(surf, T("Nivel {n}").format(n=nivell) + f" · {min(xp, 200)}/200 XP", F_HUD, BLANC, (barra.centerx, barra.y - 14))
        puja = baixes % 5 == 4 and f >= 48 and baixes < 25
        if puja:
            l = llum(60, (255, 140, 255))
            surf.blit(l, l.get_rect(center=barra.center))
        for k, recompenses in enumerate(PASSI[:5]):
            c = pygame.Rect(r.x + 30 + k * 68, r.y + 64, 60, 96)
            obert = k < nivell
            nou = obert and k == nivell - 1 and baixes % 5 == 0 and f < 30 and baixes > 0
            if nou:
                c = c.inflate(int(14 * (1 - f / 30)), int(14 * (1 - f / 30)))
                l = llum(46, (130, 255, 160))
                surf.blit(l, l.get_rect(center=c.center))
            panell(surf, c, VERD if obert else GRIS_FOSC)
            text(surf, str(k + 1), F_MINI, BLANC if obert else GRIS, (c.centerx, c.y + 12))
            tipus, valor = recompenses[0]
            centre = (c.centerx, c.y + 54)
            if tipus == "monedes":
                dibuixar_moneda(surf, centre[0], centre[1], 11)
            elif tipus in ("uniforme", "arma"):
                img = mostra_soldat("pistola", valor if tipus == "uniforme" else "classic",
                                    valor if tipus == "arma" else "estandard")
                if img:
                    surf.blit(img, img.get_rect(center=centre))
            else:
                text(surf, "T", F_UI, (230, 210, 160), centre)
            if not obert:
                capa = pygame.Surface(c.size, pygame.SRCALPHA)
                capa.fill((0, 0, 0, 120))
                surf.blit(capa, c)
            else:
                pygame.draw.lines(surf, VERD, False, [(c.centerx - 8, c.bottom - 16), (c.centerx - 2, c.bottom - 10),
                                                      (c.centerx + 10, c.bottom - 24)], 3)
        # escena: el soldat dispara a un dron
        esc = pygame.Rect(r.x + 20, r.y + 184, 360, 170)
        self._caixa_demo(surf, esc)
        peus = esc.bottom - 30
        cano = self._soldat_demo(surf, esc.x + 50, peus, "quiet", t=t)
        dx = esc.right - 50 - min(f, 38) * 1.4
        dy = esc.y + 50 + math.sin(t * 0.1) * 6
        if f < 38 and SPR_ENEMIC.get("dron"):
            dron = SPR_ENEMIC["dron"]
            surf.blit(dron, dron.get_rect(center=(int(dx), int(dy))))
        if cano and 18 <= f < 38:
            for k in range(3):                                   # bales
                p = ((f - 18) * 3 + k * 7) % 20 / 20
                bx = cano[0] + (dx - cano[0]) * p
                by = cano[1] + (dy - cano[1]) * p
                pygame.draw.line(surf, GROC, (bx, by), (bx - 6, by - (dy - cano[1]) * 0.02), 3)
        if f >= 38:                                              # explosió i XP que vola a la barra
            k = (f - 38) / 12
            pygame.draw.circle(surf, TARONJA, (int(dx), int(dy)), int(6 + 26 * k), 3)
            pygame.draw.circle(surf, GROC, (int(dx), int(dy)), int(4 + 12 * k))
            tx = dx + (barra.right - 30 - dx) * k
            ty = dy + (barra.y - dy) * k
            text(surf, "+40 XP", F_HUD, (255, 200, 255), (int(tx), int(ty)))
        if puja:
            text(surf, T("¡NIVEL {n}!").format(n=nivell + 1), F_TITOL, (255, 200, 255), (esc.centerx, esc.y + 46))
        self._punts(surf, r.x + 400, r.y + 26, r.w - 420, [
            "Ganas XP eliminando enemigos y completando escenarios (+60 XP la primera vez).",
            "Cada estrella nueva da +30 XP.",
            "Cada 200 XP subes un nivel del Battle Pass, hasta el 20.",
            "Cada nivel da monedas o algo exclusivo: uniformes, aspectos de arma y títulos.",
            "Lo conseguido se equipa en Tienda > Aspecto. No hay que pagar nada.",
        ])

    def _ajuda_1(self, surf, r):
        """Millores animades: a l'esquerra es veu què fa la millora marcada a la llista."""
        cicle = 160
        actual, f = (self.temps_estat // cicle) % len(MILLORES), self.temps_estat % cicle
        caixa = pygame.Rect(r.x + 20, r.y + 20, 300, 330)
        self._caixa_demo(surf, caixa)
        m = MILLORES[actual]
        text(surf, m["nom"], F_UI, GROC, (caixa.centerx, caixa.y + 22))
        peus = caixa.bottom - 30
        cx = caixa.centerx
        ident = m["id"]
        if ident == "blindatge":
            for i in range(6):
                if i < 5 or f > 30:
                    mida = 26 if i < 5 else int(26 * min(1, (f - 30) / 20))
                    dibuixar_cor(surf, caixa.x + 34 + i * 40, caixa.y + 56, max(2, mida), 1)
            if f > 50:
                text(surf, "+20", F_UI, VERD, (caixa.x + 34 + 5 * 40 + 13, caixa.y + 100 - min(20, (f - 50) // 2)))
            aura = llum(50, (90, 180, 255))
            aura.set_alpha(int(110 + 60 * math.sin(f * 0.15)))
            surf.blit(aura, aura.get_rect(center=(cx, peus - 30)))
            aura.set_alpha(255)
            self._soldat_demo(surf, cx, peus, t=f)
        elif ident == "potencia":
            cano = self._soldat_demo(surf, caixa.x + 60, peus, t=f)
            dron = SPR_ENEMIC.get("dron")
            if dron:
                surf.blit(dron, dron.get_rect(center=(caixa.right - 60, peus - 40)))
            fort = f > 80
            if cano:
                p = (f % 20) / 20
                bx = cano[0] + (caixa.right - 90 - cano[0]) * p
                pygame.draw.circle(surf, TARONJA if fort else GROC, (int(bx), int(cano[1])), 5 if fort else 3)
            valor = "17" if fort else "15"
            text(surf, valor, F_TITOL if fort else F_SUBTITOL, TARONJA if fort else BLANC,
                 (caixa.right - 60, peus - 100 - (f % 20)))
            text(surf, "+15%" if fort else "", F_UI, VERD, (caixa.centerx, caixa.y + 70))
        elif ident == "carregadors":
            maxim = 20 if f < 60 else min(26, 20 + (f - 60) // 6)
            text(surf, f"{maxim}/{maxim}", F_TITOL, GROC if f >= 60 else BLANC, (cx, caixa.y + 90))
            for i in range(maxim):
                fila, col = divmod(i, 13)
                pygame.draw.rect(surf, GROC, (caixa.x + 30 + col * 19, caixa.y + 140 + fila * 26, 8, 18))
                pygame.draw.rect(surf, TARONJA, (caixa.x + 30 + col * 19, caixa.y + 140 + fila * 26, 8, 6))
            self._soldat_demo(surf, cx, peus, t=f)
        elif ident == "iman":
            self._soldat_demo(surf, cx, peus, t=f)
            k = min(1.0, f / 90)
            for i, (x0, tipus) in enumerate(((caixa.x + 30, "vida"), (caixa.right - 54, "bales"))):
                x = x0 + (cx - 12 - x0) * k
                y = caixa.y + 90 + (peus - 50 - caixa.y - 90) * k
                if k < 1:
                    Item(x, y, tipus).dibuixar(surf)
                for a in range(3):
                    rr = 30 + ((f * 2 + a * 20) % 60)
                    pygame.draw.circle(surf, (120, 180, 255), (int(cx), int(peus - 40)), rr, 1)
            if k >= 1:
                text(surf, "+20 VIDA", F_HUD, VERD, (cx, peus - 90))
        elif ident == "reflexos":
            x = caixa.x + 30 + (f * 2.2) % (caixa.w - 40)
            for g in range(1, 4):
                self._soldat_demo(surf, x - g * 22, peus, "corre", t=f, alfa=110 - g * 30)
            self._soldat_demo(surf, x, peus, "corre", t=f)
            for k in range(4):
                y = peus - 20 - k * 12
                pygame.draw.line(surf, CIAN, (x - 70 - k * 8, y), (x - 40 - k * 8, y), 1)
            text(surf, "+6%", F_UI, VERD, (cx, caixa.y + 70))
        else:                                                  # propulsors: doble salt
            if f < 34:
                h = 14 * f - 0.4 * f * f
            elif f < 80:
                u = f - 34
                h = (14 * 34 - 0.4 * 34 * 34) + 12 * u - 0.4 * u * u
            else:
                h = 0
            h = max(0, h)
            if 34 <= f < 46:
                for k in range(8):
                    pygame.draw.circle(surf, random.choice((CIAN, BLANC)), (int(cx + random.uniform(-8, 8)),
                                       int(peus - h + random.uniform(0, 14))), 3)
                pygame.draw.circle(surf, CIAN, (int(cx), int(peus - h)), 10 + (f - 34) * 2, 2)
            self._soldat_demo(surf, cx, peus - min(h, caixa.h - 120), "salt" if 0 < h else "quiet", t=f)
        # llista de millores
        for k, mi in enumerate(MILLORES):
            fila = pygame.Rect(r.x + 340, r.y + 18 + k * 55, r.right - r.x - 360, 50)
            if k == actual:
                pygame.draw.rect(surf, (40, 50, 90), fila, border_radius=6)
                pygame.draw.rect(surf, GROC, fila, 2, border_radius=6)
            text(surf, mi["nom"], F_UI, CIAN if k != actual else GROC, (fila.x + 12, fila.y + 13), ancora="midleft")
            costos = " / ".join(str(c) for c in mi["costos"])
            text(surf, T("Precio: {c} monedas").format(c=costos), F_TEXT_PP, GRIS, (fila.right - 10, fila.y + 13),
                 ancora="midright")
            detall = ajustar_linies(T(DETALL_MILLORES[mi["id"]]), F_TEXT_PP, fila.w - 24)[0]
            text(surf, detall, F_TEXT_PP, BLANC, (fila.x + 12, fila.y + 34), ancora="midleft")
        text(surf, "Se compran en Tienda > Mejoras. Cada nivel se abre al avanzar en la historia.", F_TEXT_PP, GROC,
             (r.centerx, r.bottom - 10))

    def _ajuda_2(self, surf, r):
        """Armes animades: el soldat dispara l'arma marcada contra dos drons."""
        cicle = 170
        actual, f = (self.temps_estat // cicle) % len(ARMES), self.temps_estat % cicle
        for k, a in enumerate(ARMES):
            fila = pygame.Rect(r.x + 20, r.y + 18 + k * 64, 300, 58)
            if k == actual:
                pygame.draw.rect(surf, (40, 50, 90), fila, border_radius=6)
                pygame.draw.rect(surf, GROC, fila, 2, border_radius=6)
            img = mostra_soldat(a["id"], self.uniforme, self.aparenca)
            if img:
                surf.blit(img, img.get_rect(center=(fila.x + 34, fila.centery)))
            text(surf, T(a["nom"]).upper(), F_TEXT, GROC if k == actual else BLANC, (fila.x + 76, fila.y + 18),
                 ancora="midleft")
            dibuixar_pips(surf, fila.x + 80, fila.y + 38, a["potencia"], color=TARONJA)
        a = ARMES[actual]
        caixa = pygame.Rect(r.x + 340, r.y + 18, r.right - r.x - 360, 220)
        self._caixa_demo(surf, caixa)
        peus = caixa.bottom - 30
        cano = self._soldat_demo(surf, caixa.x + 70, peus, "quiet", arma=a["id"], t=f)
        drons = [(caixa.x + caixa.w * 0.62, peus - 40), (caixa.x + caixa.w * 0.85, peus - 40)]
        radi, color = Bala.ESTILS[a["estil"]]
        tocats = [False, False]
        if cano:
            # trets: moments en què dispara (la minigun arrenca a poc a poc i s'escalfa)
            trets, tt, calor = [], 20, 0.0
            while tt < 150:
                trets.append(tt)
                if a["id"] == "minigun":
                    gir = min(1.0, (tt - 20) / 30)
                    tt += round(a["cadencia"] + 11 * (1 - gir))
                    calor += CALOR_DISPAR * 1.6
                    if calor >= 100:
                        break
                else:
                    tt += max(a["cadencia"], 8)
            for t0 in trets:
                if t0 > f:
                    break
                vida = f - t0
                n = a["perdigons"]
                for p in range(n):
                    ang = (p - (n - 1) / 2) * math.radians(a["obertura"]) / max(1, n - 1)
                    x = cano[0] + vida * a["vel"] * 0.8 * math.cos(ang)
                    y = cano[1] + vida * a["vel"] * 0.8 * math.sin(ang)
                    limit = caixa.right - 8 if a["perfora"] else drons[0][0] - 10
                    if x > limit:
                        for i, (dx, _) in enumerate(drons):
                            if x - a["vel"] < dx and (a["perfora"] or i == 0) and vida < 60:
                                tocats[i] = True
                        continue
                    pygame.draw.line(surf, tuple(c // 2 for c in color), (x - 8, y), (x, y), radi)
                    pygame.draw.circle(surf, color, (int(x), int(y)), radi)
            if a["id"] == "minigun":
                fr = min(1.0, len([t0 for t0 in trets if t0 <= f]) * CALOR_DISPAR * 1.6 / 100)
                barra = pygame.Rect(caixa.x + 30, caixa.y + 16, 120, 10)
                pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=3)
                pygame.draw.rect(surf, VERMELL if fr >= 1 else (TARONJA if fr > 0.7 else GROC),
                                 (barra.x, barra.y, int(barra.w * fr), barra.h), border_radius=3)
                text(surf, "¡CALOR!" if fr >= 1 else "CALOR", F_MINI, VERMELL if fr >= 1 else BLANC,
                     (barra.right + 10, barra.centery), ancora="midleft")
                if fr >= 1:
                    for k in range(3):
                        pygame.draw.circle(surf, (200, 200, 210), (int(cano[0] + random.uniform(-4, 4)),
                                           int(cano[1] - 8 - (f * 2 + k * 9) % 30)), 4)
        dron = SPR_ENEMIC.get("dron")
        for i, (dx, dy) in enumerate(drons):
            if dron:
                img = tenyir(dron, (255, 255, 255), 160) if tocats[i] and (f // 3) % 2 else dron
                surf.blit(img, img.get_rect(center=(int(dx + (random.randint(-2, 2) if tocats[i] else 0)),
                                                    int(dy + math.sin(self.t_global * 0.08 + i) * 5))))
        linies = ajustar_linies(T(DETALL_ARMES[a["id"]]), F_TEXT_P, caixa.w)
        for i, tros in enumerate(linies[:3]):
            text(surf, tros, F_TEXT_P, BLANC, (caixa.x, caixa.bottom + 14 + i * 24), ancora="topleft")
        text(surf, "Cada escenario tiene una potencia máxima: las armas más fuertes no siempre se pueden usar.",
             F_TEXT_PP, GROC, (r.centerx, r.bottom - 10))

    def _ajuda_3(self, surf, r):
        """Estrelles, logros i supervivència, en tres petites escenes que es van alternant."""
        cicle = 210
        escena, f = (self.temps_estat // cicle) % 3, self.temps_estat % cicle
        caixa = pygame.Rect(r.x + 20, r.y + 20, 300, 330)
        self._caixa_demo(surf, caixa)
        peus = caixa.bottom - 30
        if escena == 0:                                       # estrelles
            text(surf, "¡SECTOR LIMPIO!", F_SUBTITOL, VERD, (caixa.centerx, caixa.y + 40))
            noms = ["Completado", "Sin recibir daño", "A tiempo"]
            for i in range(3):
                inici = 25 + i * 30
                if f < inici:
                    continue
                k = min(1.0, (f - inici) / 10)
                x, y = caixa.centerx, caixa.y + 100 + i * 64
                dibuixar_estrella(surf, x - 90, y, int(8 + 14 * k), True)
                text(surf, noms[i], F_TEXT_P, BLANC, (x - 66, y), ancora="midleft")
                if k < 1:
                    l = llum(30, (255, 220, 120))
                    surf.blit(l, l.get_rect(center=(x - 90, y)))
        elif escena == 1:                                     # logro: una placa amagada
            placa_x = caixa.x + 220
            agafada = f > 80
            if not agafada:
                dibuixar_placa(surf, placa_x, peus - 24, self.t_global)
            x = min(placa_x, caixa.x + 40 + f * 2.4)
            self._soldat_demo(surf, x, peus, "corre" if x < placa_x else "quiet", t=f)
            if agafada:
                k = min(1.0, (f - 80) / 14)
                toast = pygame.Rect(caixa.x + 10, caixa.y + 20 - int(70 * (1 - k)), caixa.w - 20, 56)
                logro = LOGRO_PER_ID["placa"]
                capa = pygame.Surface(toast.size, pygame.SRCALPHA)
                capa.fill((8, 10, 24, 235))
                surf.blit(capa, toast)
                pygame.draw.rect(surf, CATEGORIES_LOGRO[logro["cat"]]["color"], toast, 2, border_radius=6)
                dibuixar_medalla(surf, toast.x + 28, toast.centery, 20, logro["cat"])
                text(surf, "LOGRO DESBLOQUEADO", F_MINI, CATEGORIES_LOGRO[logro["cat"]]["color"],
                     (toast.x + 56, toast.y + 14), ancora="midleft")
                text(surf, logro["nom"], F_TEXT_P, BLANC, (toast.x + 56, toast.y + 36), ancora="midleft")
                if f > 100:
                    text(surf, "+50", F_UI, GROC, (placa_x, peus - 90 - min(40, f - 100)))
            dibuixar_trofeu(surf, caixa.centerx, caixa.y + 140, 60)
        else:                                                 # supervivència: les onades pugen
            onada = min(10, 1 + f // 18)
            text(surf, T("OLEADA {o}").format(o=onada), F_TITOL, TARONJA, (caixa.centerx, caixa.y + 50))
            dron = SPR_ENEMIC.get("dron")
            if dron:
                petit = pygame.transform.scale(dron, (30, 26))
                for i in range(min(onada, 9)):
                    fila, col = divmod(i, 3)
                    surf.blit(petit, (caixa.x + 70 + col * 60, caixa.y + 100 + fila * 44 + int(math.sin(f * 0.1 + i) * 4)))
            self._soldat_demo(surf, caixa.x + 40, peus, t=f)
            if onada >= 10 and (f // 8) % 2:
                text(surf, "¡NUEVO RÉCORD!", F_UI, VERD, (caixa.centerx, peus - 20))
        self._punts(surf, r.x + 340, r.y + 22, r.w - 360, [
            "Estrellas: cada escenario da tres, por completarlo, por no recibir daño y por acabarlo a tiempo.",
            "Logros: hay 28, y algunos son secretos. Busca placas escondidas y cosas raras en los escenarios.",
            "Supervivencia: oleadas sin fin para batir tus récords (se abre al completar el sector 1).",
            "El planeta del menú cambia el idioma; en Opciones eliges dificultad, volumen y pantalla.",
        ], salt=18)

    def _caixa_demo(self, surf, rect):
        capa = pygame.Surface(rect.size, pygame.SRCALPHA)
        capa.fill((4, 6, 16, 230))
        surf.blit(capa, rect)
        pygame.draw.rect(surf, (60, 70, 120), rect, 2, border_radius=6)
        pygame.draw.line(surf, (70, 64, 50), (rect.x + 4, rect.bottom - 30), (rect.right - 4, rect.bottom - 30), 3)

    def _soldat_demo(self, surf, x, peus, pose="quiet", arma="pistola", t=0, direccio=1, alfa=255):
        spr = sprites_jugador(arma, self.uniforme, self.aparenca)
        if not spr:
            return None
        llista = spr.poses[pose]
        img = llista[(t // 5) % len(llista) if pose == "corre" else (t // 35) % len(llista)][direccio]
        if alfa < 255:
            img = img.copy()
            img.set_alpha(alfa)
        surf.blit(img, (int(x - spr.ancoratge(direccio)), int(peus - img.get_height())))
        return x + direccio * spr.cano_dx, peus + spr.cano_dy

    def reiniciar_hud(self):
        j = getattr(self, "jugador", None)
        self.vida_mostrada = float(j.vida) if j else 0.0
        self.cop_hud = 0
        self.canvi_arma_t = 0
        self.cap_mostrada = None
        self.mira_obertura = 0.0
        self.gir_mira = 0.0
        self.marca_t = 0
        self.marca_mort_t = 0
        self.batec_t = 0
        self.escut_t = 0
        self.esquiva_llesta_t = 0
        self.recarrega_abans = 0
        self.doble_salt_t = 0
        self.municio_t = 0
        self.nums_dany = {}
        self.n_tret = 0
        self.monedes_mostrades = getattr(self, "monedes", 0)

    def actualitzar_hud(self):
        j = self.jugador
        if j.vida > self.vida_mostrada:
            self.vida_mostrada = float(j.vida)
        elif self.cop_hud <= 4:                         # la vida perduda es buida a poc a poc
            self.vida_mostrada = max(float(j.vida), self.vida_mostrada - 0.7)
        if self.cap and self.cap in self.enemics:
            v = float(max(0, self.cap.vida))
            if self.cap_mostrada is None or v > self.cap_mostrada:
                self.cap_mostrada = v
            else:
                self.cap_mostrada = max(v, self.cap_mostrada - self.cap.vida_max * 0.004)
        for nom in ("cop_hud", "canvi_arma_t", "marca_t", "marca_mort_t", "escut_t", "esquiva_llesta_t",
                    "doble_salt_t", "municio_t"):
            setattr(self, nom, max(0, getattr(self, nom) - 1))
        if self.recarrega_abans and not j.recarrega_esquiva:
            self.esquiva_llesta_t = 12
        self.recarrega_abans = j.recarrega_esquiva
        if "doble_salt" in j.events:
            self.doble_salt_t = 14
        self.mira_obertura *= 0.82
        self.gir_mira += 0.04 + 0.35 * self.gir
        dif = self.monedes - self.monedes_mostrades
        if dif:
            self.monedes_mostrades += max(1, abs(dif) // 8) * (1 if dif > 0 else -1)
        poca = 0 < j.vida <= max(20, j.vida_max * 0.25) and self.fase == "jugant" and self.mode != "tutorial"
        if poca:
            if self.batec_t % 60 == 0:
                AUDIO.so("latido")
            self.batec_t += 1
        else:
            self.batec_t = 0

    def mostrar_dany(self, e, dany):
        """Números de dany (es poden apagar a Opciones); els cops seguits al mateix enemic se sumen."""
        if not self.numeros_dany:
            return
        x, y = e.x + e.w / 2, e.y - 6
        n = self.nums_dany.get(id(e))
        if n is not None and n.t < 16 and n in self.textos:
            n.sumar(dany, x, y)
            return
        if len(self.nums_dany) > 30:
            self.nums_dany = {k: v for k, v in self.nums_dany.items() if v in self.textos}
        n = NumDany(x + random.uniform(-6, 6), y, dany)
        self.nums_dany[id(e)] = n
        self.textos.append(n)

    def _hud_vida(self, surf, j):
        """Panell de dalt a l'esquerra: cors, voltereta, millores actives i Battle Pass."""
        cors = j.vida_max // 20
        ample = max(206, 18 + cors * 28)
        panell_hud(surf, (6, 6, ample, 66))
        ultim = max(0, math.ceil(j.vida / 20) - 1)
        p = self.batec_t % 60
        batec = self.batec_t > 0 and (p < 8 or 12 <= p < 20)
        for i in range(cors):
            fr = math.ceil(max(0.0, min(1.0, (j.vida - i * 20) / 20)) * 2) / 2
            fb = max(0.0, min(1.0, (self.vida_mostrada - i * 20) / 20))
            x, y, mida = 14 + i * 28, 12, 22
            if self.cop_hud:                                  # els cors tremolen amb el cop
                a = self.cop_hud / 4
                x += random.uniform(-a, a)
                y += random.uniform(-a, a)
            if batec and i == ultim and j.vida > 0:
                x, y, mida = x - 2, y - 2, 26
            dibuixar_cor(surf, int(x), int(y), mida, fr, fb)
        # voltereta: es recarrega com un rellotge
        cx, cy = 22, 46
        fr = 1 - j.recarrega_esquiva / j.RECARREGA_ESQUIVA
        pygame.draw.circle(surf, NEGRE, (cx, cy), 11)
        llesta = fr >= 1 and not j.esquiva
        pygame.draw.circle(surf, (36, 130, 170) if llesta else (24, 34, 52), (cx, cy), 10)
        if not llesta:
            pygame.draw.arc(surf, CIAN, (cx - 10, cy - 10, 20, 20), math.pi / 2, math.pi / 2 + math.tau * fr, 3)
        else:
            pygame.draw.circle(surf, CIAN, (cx, cy), 10, 2)
        col = BLANC if llesta else GRIS
        pygame.draw.arc(surf, col, (cx - 5, cy - 5, 11, 11), 0.7, 5.4, 2)
        pygame.draw.polygon(surf, col, [(cx + 2, cy - 7), (cx + 7, cy - 4), (cx + 2, cy - 1)])
        if self.esquiva_llesta_t:
            r = int(11 + (12 - self.esquiva_llesta_t) * 1.3)
            pygame.draw.circle(surf, BLANC, (cx, cy), r, 1)
        # millores actives
        x = 40
        atret = any(getattr(it, "atret", False) for it in self.items)
        for m in MILLORES:
            n = self.nivell_millora(m["id"])
            if not n:
                continue
            ident = m["id"]
            actiu = {"iman": atret, "doble_salt": self.doble_salt_t > 0, "blindatge": self.cop_hud > 0,
                     "reflexos": j.invulnerable > 0 or (j.terra and abs(j.vx) > 3.5),
                     "potencia": self.marca_t > 0, "carregadors": self.municio_t > 0}[ident]
            apagat = ident == "doble_salt" and not j.terra and j.salts_restants == 0
            ic = ICONES_MILLORA[ident]
            if actiu:
                l = llum(14, DIBUIX_MILLORES[ident][0])
                surf.blit(l, (x + 9 - 14, 46 - 14))
            surf.blit(ic["off" if apagat else "on"], (x, 37))
            if len(m["costos"]) > 1:
                for k in range(len(m["costos"])):
                    pygame.draw.rect(surf, GROC if k < n else GRIS_FOSC, (x + 2 + k * 5, 57, 4, 2))
            x += 22
        # Battle Pass
        nivell = self.nivell_passi()
        fr = 1.0 if nivell >= len(PASSI) else (self.xp % XP_PER_NIVELL) / XP_PER_NIVELL
        amp = ample - 62
        pygame.draw.rect(surf, NEGRE, (13, 63, amp + 2, 5))
        pygame.draw.rect(surf, GRIS_FOSC, (14, 64, amp, 3))
        pygame.draw.rect(surf, (255, 150, 255), (14, 64, int(amp * fr), 3))
        text(surf, f"BP{nivell}", F_MINI, (255, 200, 255), (amp + 22, 66), ancora="midleft")

    def _hud_info(self, surf):
        """Panell de dalt a la dreta: monedes, sector i onada, enemics i cronòmetre."""
        if self.mode == "tutorial":
            linia1, linia2 = T("ENTRENAMIENTO"), ""
        elif self.mode == "supervivencia":
            linia1 = T("SUPERVIVENCIA · OLEADA {o}").format(o=self.onada)
            linia2 = T("PUNTOS: {p}").format(p=self.punts)
        else:
            linia1 = T("SECTOR {s} · OLEADA {o}/{n}").format(s=f"{self.nivell_actual + 1}-{self.escenari_actual + 1}",
                                                            o=self.onada + 1, n=len(self.onades))
            linia2 = T("ENEMIGOS: {n}").format(n=len(self.enemics))
        rellotge = None
        if self.mode == "historia" and self.fase == "jugant":
            segons = self.temps_joc // FPS
            rellotge = f"{segons // 60}:{segons % 60:02d}"
        w1 = render(linia1, F_MINI, BLANC).get_width()
        w2 = render(linia2, F_MINI, BLANC).get_width() + (render(rellotge, F_MINI, BLANC).get_width() + 52 if rellotge else 0)
        ample = max(150, w1, w2) + 22
        r = panell_hud(surf, (WIDTH - 6 - ample, 6, ample, 66))
        puja = self.monedes_mostrades != self.monedes
        rm = text(surf, str(self.monedes_mostrades), F_UI, GROC if not puja else (255, 245, 170),
                  (r.right - 10, 19 - (1 if puja and self.t_global % 4 < 2 else 0)), ancora="midright")
        dibuixar_moneda(surf, rm.left - 14, 19, 8 if puja else 7)
        text(surf, linia1, F_MINI, BLANC, (r.right - 10, 40), ancora="midright")
        if linia2:
            text(surf, linia2, F_MINI, (200, 205, 225), (r.x + 10, 58), ancora="midleft")
        if rellotge:
            limit = TEMPS_ESTRELLA[(self.nivell_actual, self.escenari_actual)]
            a_temps = self.temps_joc // FPS <= limit
            r2 = text(surf, rellotge, F_MINI, (255, 220, 120) if a_temps else GRIS, (r.right - 10, 58), ancora="midright")
            dibuixar_estrella(surf, r2.left - 10, 58, 6, a_temps)
            dibuixar_estrella(surf, r2.left - 26, 58, 6, self.dany_rebut == 0, (255, 140, 140))

    def _hud_arma(self, surf):
        """Panell de baix a l'esquerra: icona de l'arma, munició en bales o barra de calor."""
        i = self.arma_actual
        arma = ARMES[i]
        ident = arma["id"]
        color = COLOR_ARMA[ident]
        r = panell_hud(surf, (6, HEIGHT - 46, 274, 40), color)
        ic = ICONES_ARMA[ident]
        t = self.canvi_arma_t
        ix, iy = r.x + 8 - t * 2, r.centery - ic[2].get_height() // 2
        surf.blit(ic[2], (ix, iy))
        if t > 6:                                           # canvi d'arma: entra amb un flaix blanc
            b = ic["blanc"]
            b.set_alpha(int(255 * (t - 6) / 6))
            surf.blit(b, (ix, iy))
        x0, x1 = r.x + 68, r.right - 8
        text(surf, T(arma["nom"]).upper(), F_MINI, color, (x0, r.y + 10), ancora="midleft")
        if ident == "minigun":
            calent = self.sobreescalfat and (self.t_global // 8) % 2 == 0
            text(surf, "¡CALOR!" if self.sobreescalfat else "CALOR", F_MINI, VERMELL if calent else BLANC,
                 (x1, r.y + 10), ancora="midright")
            barra = pygame.Rect(x0, r.y + 21, x1 - x0, 10)
            pygame.draw.rect(surf, NEGRE, barra.inflate(4, 4))
            pygame.draw.rect(surf, (36, 38, 56), barra)
            fr = self.calor / 100
            for sx in range(0, int(barra.w * fr), 3):
                q = sx / barra.w
                if self.sobreescalfat:
                    c = VERMELL if calent else (255, 120, 90)
                elif q < 0.5:
                    c = tuple(int(GROC[k] + (TARONJA[k] - GROC[k]) * q * 2) for k in range(3))
                else:
                    c = tuple(int(TARONJA[k] + (VERMELL[k] - TARONJA[k]) * (q - 0.5) * 2) for k in range(3))
                pygame.draw.rect(surf, c, (barra.x + sx, barra.y, min(2, barra.w - sx), barra.h))
            for k in range(3):                              # rotació dels canons
                encesa = self.gir > (k + 0.5) / 3
                pygame.draw.rect(surf, color if encesa else GRIS_FOSC, (barra.x + k * 6, barra.bottom + 4, 4, 2))
            return
        bmax = self.bales_max(i)
        if bmax is None:
            text(surf, "∞", F_UI, BLANC, (x0 + 10, r.y + 26))
            return
        b = self.bales_armes[i]
        poca = b <= bmax * 0.25
        parpella = poca and (self.t_global // 8) % 2 == 0
        text(surf, f"{b}/{bmax}", F_MINI, (VERMELL if parpella else TARONJA) if poca else BLANC, (x1, r.y + 10),
             ancora="midright")
        files = 1 if bmax <= 34 else 2
        per = math.ceil(bmax / files)
        pas = max(3, min(7, (x1 - x0) // per))
        alt = 9 if files == 1 else 6
        for k in range(bmax):
            f, c = divmod(k, per)
            px, py = x0 + c * pas, r.y + 20 + f * (alt + 2)
            plena = k < b
            col = ((VERMELL if parpella else TARONJA) if poca else color) if plena else (42, 44, 64)
            pygame.draw.rect(surf, col, (px, py, pas - 1, alt))
            if plena:
                pygame.draw.rect(surf, aclarir(col, 80), (px, py, pas - 1, 2))
        if b == 0 and (self.t_global // 10) % 2 == 0:
            text(surf, "¡SIN BALAS!", F_MINI, VERMELL, ((x0 + x1) // 2, r.y + 27))

    def _hud_ranures(self, surf):
        """Ranures d'armes (1-5) a baix a la dreta, amb icona, munició i cadenat si no es pot fer servir."""
        usables = self.armes_usables()
        mostrar = [i for i, a in enumerate(ARMES) if a["id"] in self.armes_propies or i in usables]
        w, h, sep = 42, 34, 4
        x = WIDTH - 6 - len(mostrar) * (w + sep) + sep
        for i in mostrar:
            ident = ARMES[i]["id"]
            actual, usable = i == self.arma_actual, i in usables
            rr = pygame.Rect(x, HEIGHT - 6 - h - (4 if actual else 0), w, h)
            panell_hud(surf, rr, VERD if actual else ((90, 120, 190) if usable else (200, 60, 70)), 210 if actual else 150)
            ic = ICONES_ARMA[ident]
            img = ic[1] if usable else ic["off"]
            surf.blit(img, img.get_rect(center=(rr.centerx + 3, rr.centery + 2)))
            text(surf, str(i + 1), F_MINI, BLANC if usable else GRIS, (rr.x + 7, rr.y + 8), ombra=False)
            if not usable:
                dibuixar_cadenat(surf, rr.right - 9, rr.y + 11)
            else:
                bmax = self.bales_max(i)
                fr = (self.calor / 100) if bmax is None else self.bales_armes[i] / max(1, bmax)
                col = (VERMELL if self.sobreescalfat else TARONJA) if bmax is None else (
                    VERMELL if fr <= 0.25 else COLOR_ARMA[ident])
                pygame.draw.rect(surf, (40, 42, 60), (rr.x + 5, rr.bottom - 5, w - 10, 2))
                pygame.draw.rect(surf, col, (rr.x + 5, rr.bottom - 5, int((w - 10) * fr), 2))
            x += w + sep

    RETRATS_CAP = {}

    def retrat_cap(self, cap):
        img = Game.RETRATS_CAP.get(cap.clau)
        if img is None:
            base, _ = cap.imatge()
            if base is None:
                img = pygame.Surface((30, 30), pygame.SRCALPHA)
                pygame.draw.circle(img, VERMELL_FOSC, (15, 15), 13)
            else:
                bw, bh = base.get_size()
                k = min(30 / bw, 30 / bh)
                img = pygame.transform.smoothscale(base, (max(1, int(bw * k)), max(1, int(bh * k))))
            Game.RETRATS_CAP[cap.clau] = img
        return img

    def _hud_cap(self, surf):
        """Barra del cap: retrat, vida perduda en blanc, segments i marca de la fase de fúria (50%)."""
        cap = self.cap
        furia = cap.furia
        r = panell_hud(surf, (286, HEIGHT - 46, 420, 40), (220, 80, 100))
        pr = pygame.Rect(r.x + 5, r.y + 5, 30, 30)
        pygame.draw.rect(surf, (40, 12, 24), pr)
        img = self.retrat_cap(cap)
        d = (random.randint(-1, 1), random.randint(-1, 1)) if (furia and self.t_global % 6 < 3) or cap.flash else (0, 0)
        surf.blit(img, img.get_rect(center=(pr.centerx + d[0], pr.centery + d[1])))
        if cap.flash:
            pygame.draw.rect(surf, BLANC, pr, 1)
        else:
            pygame.draw.rect(surf, VERMELL if furia else (220, 80, 100), pr, 1)
        text(surf, self.nom_cap, F_MINI, (255, 200, 200), (pr.right + 8, r.y + 11), ancora="midleft")
        parpella = (self.t_global // 10) % 2 == 0
        if furia:
            text(surf, "¡FURIA!", F_MINI, VERMELL if parpella else (255, 150, 150), (r.right - 10, r.y + 11), ancora="midright")
        barra = pygame.Rect(pr.right + 8, r.y + 20, r.right - 10 - (pr.right + 8), 12)
        fr = max(0, cap.vida) / cap.vida_max
        fb = (self.cap_mostrada if self.cap_mostrada is not None else max(0, cap.vida)) / cap.vida_max
        pygame.draw.rect(surf, NEGRE, barra.inflate(4, 4))
        pygame.draw.rect(surf, VERMELL_FOSC, barra)
        pygame.draw.rect(surf, (255, 236, 236), (barra.x, barra.y, int(barra.w * fb), barra.h))
        col = ((255, 70, 70) if parpella else (210, 40, 50)) if furia else (232, 96, 60)
        pygame.draw.rect(surf, col, (barra.x, barra.y, int(barra.w * fr), barra.h))
        pygame.draw.rect(surf, aclarir(col, 70), (barra.x, barra.y, int(barra.w * fr), 3))
        for k in range(1, 10):
            sx = barra.x + barra.w * k // 10
            pygame.draw.line(surf, (60, 10, 20), (sx, barra.y + 3), (sx, barra.bottom - 1))
        mx = barra.x + barra.w // 2
        pygame.draw.line(surf, GROC if not furia else GRIS, (mx, barra.y - 3), (mx, barra.bottom + 2), 2)

    def dibuixar_mira(self, surf):
        """Punt de mira propi de cada arma, que s'obre amb el retrocés, i marca d'impacte."""
        mx, my = ratoli()
        arma = ARMES[self.arma_actual]
        ident = arma["id"]
        col = VERMELL if self.avis_bales else BLANC
        ob = self.mira_obertura

        def linia(a, b, c=None, g=2):
            pygame.draw.line(surf, NEGRE, a, b, g + 2)
            pygame.draw.line(surf, c or col, a, b, g)

        if ident == "escopeta":                     # cercle discontinu = on arriben els perdigons
            cx, cy = self.jugador.canons(self.spr_jugador())
            obertura = math.radians(arma["obertura"] / 2 + arma["dispersio"])
            r = int(max(12, min(90, math.hypot(mx - cx, my - cy) * math.tan(obertura))) + ob)
            for k in range(12):
                a0 = k * math.tau / 12 + self.t_global * 0.01
                pygame.draw.arc(surf, NEGRE, (mx - r - 1, my - r - 1, 2 * r + 2, 2 * r + 2), a0, a0 + 0.3, 4)
                pygame.draw.arc(surf, col, (mx - r, my - r, 2 * r, 2 * r), a0, a0 + 0.3, 2)
            pygame.draw.circle(surf, NEGRE, (mx, my), 3)
            pygame.draw.circle(surf, col, (mx, my), 2)
        elif ident == "fusell":                     # creu fina amb cantonades
            g = 4 + ob
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                linia((mx + dx * g, my + dy * g), (mx + dx * (g + 9), my + dy * (g + 9)), g=1)
            s = int(13 + ob)
            for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                pts = [(mx + sx * s, my + sy * (s - 5)), (mx + sx * s, my + sy * s), (mx + sx * (s - 5), my + sy * s)]
                pygame.draw.lines(surf, NEGRE, False, pts, 3)
                pygame.draw.lines(surf, col, False, pts, 1)
            pygame.draw.rect(surf, col, (mx, my, 1, 1))
        elif ident == "minigun":                    # tres arcs que giren amb els canons i s'escalfen
            q = self.calor / 100
            c = (255, int(255 - 140 * q), int(255 - 215 * q)) if not self.sobreescalfat else VERMELL
            r = int(13 + ob)
            for k in range(3):
                a0 = self.gir_mira + k * math.tau / 3
                pygame.draw.arc(surf, NEGRE, (mx - r - 1, my - r - 1, 2 * r + 2, 2 * r + 2), a0, a0 + 1.0, 5)
                pygame.draw.arc(surf, c, (mx - r, my - r, 2 * r, 2 * r), a0, a0 + 1.0, 3)
            pygame.draw.circle(surf, NEGRE, (mx, my), 3)
            pygame.draw.circle(surf, c, (mx, my), 2)
        elif ident == "plasma":                     # rombe que batega
            r = 11 + ob + 2 * math.sin(self.t_global * 0.15)
            punts = [(mx + r, my), (mx, my + r), (mx - r, my), (mx, my - r)]
            pygame.draw.polygon(surf, NEGRE, punts, 4)
            pygame.draw.polygon(surf, (150, 245, 255) if col == BLANC else col, punts, 2)
            pygame.draw.circle(surf, NEGRE, (mx, my), 4, 3)
            pygame.draw.circle(surf, (150, 245, 255), (mx, my), 3, 1)
        else:                                       # pistola
            g = 5 + ob
            pygame.draw.circle(surf, NEGRE, (mx, my), int(10 + ob * 0.5), 3)
            pygame.draw.circle(surf, col, (mx, my), int(9 + ob * 0.5), 1)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                linia((mx + dx * g, my + dy * g), (mx + dx * (g + 8), my + dy * (g + 8)))
        # marca d'impacte (blanca) i de baixa (vermella, més gran)
        if self.marca_t or self.marca_mort_t:
            mort = self.marca_mort_t > 0
            k = self.marca_mort_t / 14 if mort else self.marca_t / 8
            c = VERMELL if mort else BLANC
            g0 = 7 + (1 - k) * 3
            g1 = g0 + (9 if mort else 6)
            for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                linia((mx + sx * g0, my + sy * g0), (mx + sx * g1, my + sy * g1), c, 3 if mort else 2)

    def pols_impacte(self, b):
        """Bala que toca el terra: pols i un parell d'espurnes del seu color."""
        x, y = b.x, TERRA_Y
        for _ in range(4):
            self.efectes.append(Particula(x + random.uniform(-3, 3), y - 1, random.uniform(-1.5, 1.5),
                                          random.uniform(-2.2, -0.6), random.choice(((170, 160, 140), (130, 125, 115), (200, 195, 180))),
                                          vida=random.randint(10, 20), mida=random.uniform(2, 3.5), gravetat=0.12))
        espurnes(self.efectes, x, y - 1, -math.pi / 2 - math.copysign(0.6, b.vx), 2, [b.color[:3], BLANC], 0.5, (2, 4), (6, 10))

    def dibuixar_iman(self, surf):
        """Millora «Imán»: camp blau al voltant del soldat i línies cap als objectes que atrau."""
        atrets = [it for it in self.items if getattr(it, "atret", False)]
        if not atrets:
            return
        jx, jy = self.jugador.centre
        t = self.t_global
        r = 34 + 3 * math.sin(t * 0.2)
        for k in range(8):
            a0 = k * math.tau / 8 + t * 0.06
            pygame.draw.arc(surf, (110, 180, 255), (jx - r, jy - r, 2 * r, 2 * r), a0, a0 + 0.4, 2)
        for it in atrets:
            ix, iy = it.x + 12, it.y + 12
            for q in range(4):
                f = ((t * 0.05) + q / 4) % 1.0
                px, py = ix + (jx - ix) * f, iy + (jy - iy) * f
                pygame.draw.circle(surf, (150, 210, 255), (int(px), int(py)), 2)

    def entrar_novetats(self, pagina=0, despres=None):
        """«Últimas actualizaciones»: surt abans del menú quan ja has jugat i hi ha una versió que no has vist."""
        if despres is not None:
            self.novetats_despres = despres
            self.novetat_sense_veure = self.novetats_vistes != NOVETATS[0]["versio"]
        if self.novetats_vistes != NOVETATS[0]["versio"]:
            self.novetats_vistes = NOVETATS[0]["versio"]
            self.desar_progres()
        p = self.pagina_novetats = max(0, min(len(NOVETATS) - 1, pagina))
        b = []
        if p > 0:
            b.append(Boto((70, 478, 200, 42), f"<  {T('Versión')} {NOVETATS[p - 1]['versio']}",
                          lambda: self.entrar_novetats(p - 1), BLAU, font=F_HUD))
        if p < len(NOVETATS) - 1:
            b.append(Boto((280, 478, 200, 42), f"{T('Versión')} {NOVETATS[p + 1]['versio']}  >",
                          lambda: self.entrar_novetats(p + 1), BLAU, font=F_HUD))
        b.append(Boto((WIDTH - 70 - 220, 478, 220, 42), "Continuar", self.sortir_novetats, VERD))
        self.botons = b
        self.canviar_estat("novetats")

    def sortir_novetats(self):
        AUDIO.so("click")
        getattr(self, "novetats_despres", self.entrar_menu)()

    def dibuixar_novetats(self, surf):
        self.fons_menu.dibuixar(surf)
        t = self.temps_estat
        nov = NOVETATS[self.pagina_novetats]
        text(surf, T("ÚLTIMAS ACTUALIZACIONES"), F_SUBTITOL, BLANC, (WIDTH // 2, 40))
        r = pygame.Rect(70, 76, WIDTH - 140, 390)
        panell(surf, r, BLAU_CLAR, 225)
        # capçalera: insígnia amb la versió i títol
        img_v = render(f"{T('Versión')} {nov['versio']}".upper(), F_HUD, NEGRE)
        ins = pygame.Rect(r.x + 18, r.y + 16, img_v.get_width() + 24, 32)
        pygame.draw.rect(surf, NEGRE, ins.move(0, 3), border_radius=6)
        pygame.draw.rect(surf, GROC, ins, border_radius=6)
        pygame.draw.rect(surf, (255, 240, 170), ins, 2, border_radius=6)
        surf.blit(img_v, img_v.get_rect(center=ins.center))
        text(surf, T(nov["titol"]), F_TEXT, CIAN, (ins.right + 16, ins.centery), ancora="midleft")
        if self.pagina_novetats == 0 and getattr(self, "novetat_sense_veure", False):
            k = 1 + 0.07 * math.sin(t * 0.18)
            img = render(T("¡NUEVO!"), F_HUD, BLANC)
            caixa = img.get_rect(center=(r.right - 72, ins.centery)).inflate(22, 14)
            caixa = caixa.inflate(int(caixa.w * (k - 1)), int(caixa.h * (k - 1)))
            pygame.draw.rect(surf, NEGRE, caixa.move(0, 3), border_radius=6)
            pygame.draw.rect(surf, VERMELL, caixa, border_radius=6)
            pygame.draw.rect(surf, (255, 150, 150), caixa, 2, border_radius=6)
            surf.blit(img, img.get_rect(center=caixa.center))
        pygame.draw.line(surf, (70, 90, 150), (r.x + 16, r.y + 62), (r.right - 16, r.y + 62))
        # punts: entren un darrere l'altre lliscant des de la dreta
        punts = nov["punts"]
        y0 = r.y + 70
        alt = min(44, (r.bottom - 8 - y0) // max(1, len(punts)))
        for i, (icona, txt) in enumerate(punts):
            k = max(0.0, min(1.0, (t - 8 - i * 6) / 12))
            if k <= 0:
                continue
            suau = 1 - (1 - k) ** 3
            x = r.x + 18 + int((1 - suau) * 70)
            y = y0 + i * alt
            if i % 2 == 0:
                fila = pygame.Surface((r.w - 32, alt - 4), pygame.SRCALPHA)
                fila.fill((40, 60, 120, int(70 * suau)))
                surf.blit(fila, (r.x + 16, y + 2))
            self.icona_novetat(surf, icona, x + 30, y + alt // 2, t + i * 11)
            linies = ajustar_linies(T(txt), F_TEXT_PP, r.right - 24 - (x + 70))[:2]
            for j, l in enumerate(linies):
                text(surf, l, F_TEXT_PP, BLANC, (x + 70, y + alt // 2 - (len(linies) - 1) * 9 + j * 18), ancora="midleft")
        # indicador de pàgines (una per versió)
        for k in range(len(NOVETATS)):
            cx = 575 + (k - (len(NOVETATS) - 1) / 2) * 16
            actual = k == self.pagina_novetats
            pygame.draw.circle(surf, NEGRE, (int(cx), 501), 6 if actual else 5)
            pygame.draw.circle(surf, GROC if actual else GRIS_FOSC, (int(cx), 500), 5 if actual else 4)

    IMATGES_NOVETAT = {}

    def imatge_novetat(self, clau, img, mida):
        """Imatge reduïda a `mida` (es guarda per no reescalar a cada fotograma)."""
        s = Game.IMATGES_NOVETAT.get(clau)
        if s is None and img is not None:
            k = min(mida / img.get_width(), mida / img.get_height())
            s = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
            Game.IMATGES_NOVETAT[clau] = s
        return s

    def icona_novetat(self, surf, clau, cx, cy, t):
        cy += int(2 * math.sin(t * 0.08))
        if clau.startswith("arma:"):
            img = ICONES_ARMA[clau[5:]][2]
            surf.blit(img, img.get_rect(center=(cx, cy)))
        elif clau.startswith("millora:"):
            img = Game.IMATGES_NOVETAT.get(clau)
            if img is None:
                base = ICONES_MILLORA[clau[8:]]["on"]
                img = Game.IMATGES_NOVETAT[clau] = pygame.transform.scale(base, (base.get_width() * 2, base.get_height() * 2))
            if (t // 30) % 3 == 0:
                l = llum(22, DIBUIX_MILLORES[clau[8:]][0])
                surf.blit(l, (cx - 22, cy - 22))
            surf.blit(img, img.get_rect(center=(cx, cy)))
        elif clau == "vida":
            fr = 1.0 if (t // 40) % 2 else 0.5
            dibuixar_cor(surf, cx - 13, cy - 12, 26, fr, 1.0)
        elif clau == "estrella":
            dibuixar_estrella(surf, cx, cy, int(14 + math.sin(t * 0.1)), True)
        elif clau == "trofeu":
            dibuixar_trofeu(surf, cx, cy, 30)
        elif clau == "globus":
            dibuixar_globus(surf, cx, cy, 15)
        elif clau == "bandera":
            dibuixar_bandera(surf, "en", (cx - 21, cy - 13, 42, 26))
        elif clau == "hud":
            panell_hud(surf, (cx - 26, cy - 17, 52, 34))
            for k in range(3):
                dibuixar_cor(surf, cx - 21 + k * 13, cy - 12, 11, 1 if k < 2 or (t // 25) % 2 else 0.5)
            pygame.draw.rect(surf, (42, 44, 64), (cx - 21, cy + 6, 40, 5))
            pygame.draw.rect(surf, GROC, (cx - 21, cy + 6, int(40 * (0.3 + 0.7 * ((t % 90) / 90))), 5))
        elif clau == "bala":
            d = (t * 2) % 40
            b = Bala(cx - 20 + d, cy - 7, 6, 0, 1, "fusell")
            b.dibuixar(surf)
            b = Bala(cx - 6 + d * 0.5, cy + 8, 4, 0, 1, "plasma")
            b.t = t
            b.dibuixar(surf)
        elif clau == "mira":
            pygame.draw.circle(surf, NEGRE, (cx, cy), 13, 3)
            pygame.draw.circle(surf, BLANC, (cx, cy), 12, 1)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pygame.draw.line(surf, BLANC, (cx + dx * 6, cy + dy * 6), (cx + dx * 16, cy + dy * 16), 2)
            if (t // 20) % 2:
                for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                    pygame.draw.line(surf, VERMELL, (cx + sx * 8, cy + sy * 8), (cx + sx * 15, cy + sy * 15), 3)
        elif clau == "jefe":
            img = self.imatge_novetat("jefe", SPR_ENEMIC.get(("boss", 0)), 40)
            if img:
                surf.blit(img, img.get_rect(center=(cx, cy)))
        elif clau == "enemic":
            frames = FRAMES_TERRA.get("soldat") or []
            if frames:
                img = frames[(t // 8) % min(4, len(frames))]
                surf.blit(img, img.get_rect(center=(cx, cy)))
        elif clau == "radio":
            frames = RETRATS.get("doctora") or []
            if frames:
                img = self.imatge_novetat(("radio", (t // 10) % 2), frames[(t // 10) % 2], 38)
                surf.blit(img, img.get_rect(center=(cx, cy)))
                pygame.draw.rect(surf, CIAN, img.get_rect(center=(cx, cy)).inflate(4, 4), 1)
        elif clau == "opcions":                       # engranatge que gira
            a0 = t * 0.03
            for k in range(8):
                a = a0 + k * math.tau / 8
                pygame.draw.line(surf, (170, 176, 196), (cx, cy), (cx + math.cos(a) * 15, cy + math.sin(a) * 15), 6)
            pygame.draw.circle(surf, (170, 176, 196), (cx, cy), 11)
            pygame.draw.circle(surf, (30, 34, 66), (cx, cy), 5)
        elif clau == "pase":
            caixa = pygame.Rect(cx - 22, cy - 14, 44, 28)
            pygame.draw.rect(surf, NEGRE, caixa.move(0, 2), border_radius=6)
            pygame.draw.rect(surf, (200, 80, 200), caixa, border_radius=6)
            pygame.draw.rect(surf, (255, 170, 255), caixa, 2, border_radius=6)
            text(surf, "BP", F_HUD, BLANC, caixa.center)
        elif clau == "llibre":
            pygame.draw.rect(surf, NEGRE, (cx - 18, cy - 12, 38, 28), border_radius=3)
            pygame.draw.rect(surf, (235, 230, 210), (cx - 17, cy - 13, 16, 26))
            pygame.draw.rect(surf, (235, 230, 210), (cx + 1, cy - 13, 16, 26))
            pygame.draw.line(surf, (120, 90, 60), (cx, cy - 13), (cx, cy + 12), 2)
            for k in range(4):
                pygame.draw.line(surf, GRIS, (cx - 14, cy - 8 + k * 5), (cx - 4, cy - 8 + k * 5))
                pygame.draw.line(surf, GRIS, (cx + 4, cy - 8 + k * 5), (cx + 14, cy - 8 + k * 5))
        elif clau == "cine":                          # claqueta
            pygame.draw.rect(surf, NEGRE, (cx - 18, cy - 6, 36, 22), border_radius=2)
            pygame.draw.rect(surf, (60, 64, 80), (cx - 17, cy - 5, 34, 20))
            a = -0.28 * max(0.0, math.sin(t * 0.12))       # la tapa s'obre i es tanca
            p0 = (cx - 17, cy - 7)
            ux, uy, px, py = math.cos(a), math.sin(a), math.sin(a), -math.cos(a)
            punts = [p0, (p0[0] + ux * 34, p0[1] + uy * 34), (p0[0] + ux * 34 + px * 6, p0[1] + uy * 34 + py * 6),
                     (p0[0] + px * 6, p0[1] + py * 6)]
            pygame.draw.polygon(surf, BLANC, punts)
            for k in range(1, 5):                             # ratlles de la claqueta
                q = k * 7
                pygame.draw.line(surf, NEGRE, (p0[0] + ux * q, p0[1] + uy * q),
                                 (p0[0] + ux * (q + 3) + px * 6, p0[1] + uy * (q + 3) + py * 6), 2)
            pygame.draw.polygon(surf, NEGRE, punts, 1)
        elif clau == "plataforma":                     # plataforma flotant que va i ve
            d = int(8 * (((t // 2) % 32) / 16 - 1 if (t // 2) % 32 < 16 else 1 - ((t // 2) % 32 - 16) / 16))
            r = pygame.Rect(cx - 22 + d, cy - 4, 44, 9)
            pygame.draw.rect(surf, (52, 56, 82), r, border_radius=3)
            pygame.draw.rect(surf, (230, 180, 40), (r.x, r.y, r.w, 3), border_radius=2)
            for fx in (0.25, 0.75):
                l = llum(6, (120, 210, 255))
                surf.blit(l, (r.x + int(r.w * fx) - 6, r.bottom - 3))
        elif clau == "musica":
            for k, (dx, fase) in enumerate(((-9, 0), (7, 1.5))):
                y = cy + 6 + int(2 * math.sin(t * 0.15 + fase))
                pygame.draw.circle(surf, CIAN, (cx + dx, y), 5)
                pygame.draw.line(surf, CIAN, (cx + dx + 4, y), (cx + dx + 4, y - 18), 2)
            pygame.draw.line(surf, CIAN, (cx - 5, cy - 12 + int(2 * math.sin(t * 0.15))),
                             (cx + 11, cy - 14 + int(2 * math.sin(t * 0.15 + 1.5))), 4)

    def dibuixar_joc(self, surf):
        c = self.capa
        fons = FONS_NIVELLS.get((self.nivell_actual, self.escenari_actual))
        if fons:
            # paral·laxi: el fons es desplaça una mica segons la posició del jugador
            jx, jy = self.jugador.centre
            ox = -20 - (jx / WIDTH - 0.5) * 36
            oy = -10 - (jy / HEIGHT - 0.7) * 16
            self.fons_off = (int(max(-40, min(0, ox))), int(max(-20, min(0, oy))))
            c.blit(fons, self.fons_off)
            if self.ull_destruit:                         # l'ull de la torre, rebentat
                ux, uy = self.pos_ull()
                pygame.draw.circle(c, (30, 10, 36), (ux, uy), 12)
                pygame.draw.circle(c, (80, 40, 60), (ux, uy), 12, 2)
        else:
            c.fill(FONS)
        self.ambient.dibuixar_fons(c)
        for p in self.plataformes:
            p.dibuixar(c)
        self.perills.dibuixar(c, self.efectes)
        for it in self.items:
            it.dibuixar(c)
        if self.placa:
            dibuixar_placa(c, self.placa[0], self.placa[1], self.temps_fase)
        for e in self.enemics:
            e.dibuixar(c)
        for r in self.restes:
            r.dibuixar(c)
        spr = self.spr_jugador()
        if self.fase != "mort":
            self.dibuixar_iman(c)
            self.jugador.dibuixar(c, spr)
            if self.escut_t:                          # el blindatge aguanta el cop: escut hexagonal
                jx, jy = self.jugador.centre
                k = self.escut_t / 12
                r = 30 + (1 - k) * 10
                punts = [(jx + math.cos(i * math.pi / 3 + math.pi / 6) * r, jy + math.sin(i * math.pi / 3 + math.pi / 6) * r * 1.15)
                         for i in range(6)]
                pygame.draw.polygon(c, (120, 200, 255) if self.escut_t % 4 < 2 else BLANC, punts, 2)
                for px, py in punts[::2]:
                    pygame.draw.line(c, (90, 160, 230), (jx, jy), (px, py), 1)
        else:
            self.jugador.dibuixar_mort(c, spr)
        for b in self.bales:
            b.dibuixar(c)
        for b in self.bales_enemics:
            b.dibuixar(c)
        for fx in self.efectes:
            fx.dibuixar(c)
        self.perills.dibuixar_davant(c)
        self.ambient.dibuixar_davant(c)
        for t in self.textos:
            t.dibuixar(c)
        if self.flaix:
            vel = CAPA_TRANSPARENT
            vel.fill((255, 255, 255, int(16 * self.flaix)))
            c.blit(vel, (0, 0))
        if self.batec_t:                              # poca vida: la pantalla batega en vermell
            p = self.batec_t % 60
            k = max(0.0, 1 - p / 12, 0.75 * (1 - abs(p - 15) / 8))
            ALARMA.set_alpha(int(35 + 90 * k))
            c.blit(ALARMA, (0, 0))

        if self.tremolor > 0.5:
            ox = random.randint(-int(self.tremolor), int(self.tremolor))
            oy = random.randint(-int(self.tremolor), int(self.tremolor))
            surf.fill(NEGRE)
            surf.blit(c, (ox, oy))
        else:
            surf.blit(c, (0, 0))
        self.dibuixar_hud(surf)

    def dibuixar_hud(self, surf):
        j = self.jugador
        self._hud_vida(surf, j)
        self._hud_info(surf)
        self._hud_arma(surf)
        self._hud_ranures(surf)
        if self.cap and self.cap in self.enemics:
            self._hud_cap(surf)
        # Avisos
        if self.avis_bales and (self.avis_bales // 10) % 2 == 0:
            text(surf, "¡SIN BALAS! Recoge munición o cambia de arma (Q)", F_HUD, VERMELL, (WIDTH // 2, 110))
        if self.fase == "jugant" and self.temps_fase < 120 and self.estat == "joc" and not self.presentacio:
            if self.mode == "tutorial":
                nom = ""
            elif self.mode == "supervivencia":
                nom = T("Supervivencia")
            else:
                nom = f"{T(NOMS_SECTORS[self.nivell_actual])} · {self.escenari_actual + 1}/3"
            text(surf, nom, F_UI, CIAN, (WIDTH // 2, 176))
        if self.espera_onada and self.fase == "jugant":
            k = (self.espera_onada // 8) % 2
            if self.mode == "supervivencia":
                text(surf, T("OLEADA {o}").format(o=self.onada + 1), F_TITOL, TARONJA if k else GROC,
                     (WIDTH // 2, HEIGHT // 2 - 50))
                text(surf, T("+10 vida · ¡prepárate!"), F_UI, VERD, (WIDTH // 2, HEIGHT // 2 - 6))
            else:
                text(surf, "¡REFUERZOS!", F_TITOL, TARONJA if k else VERMELL, (WIDTH // 2, HEIGHT // 2 - 50))
                text(surf, T("Oleada {o} de {n}").format(o=self.onada + 2, n=len(self.onades)), F_UI, BLANC,
                     (WIDTH // 2, HEIGHT // 2 - 6))
        if self.fase == "net":
            text(surf, "¡SECTOR LIMPIO!", F_TITOL, VERD, (WIDTH // 2, HEIGHT // 2 - 70))
            text(surf, T("+{m} monedas · +{x} XP").format(m=self.monedes_nivell, x=self.xp_nivell), F_UI, GROC,
                 (WIDTH // 2, HEIGHT // 2 - 26))
            if self.estrelles_noves:
                noves, guanyades = self.estrelles_noves
                limit = TEMPS_ESTRELLA[(self.nivell_actual, self.escenari_actual)]
                noms = [T("Completado"), T("Sin recibir daño"), T("En menos de {s} s").format(s=limit)]
                for i in range(3):
                    if self.temps_fase < 30 + i * 22:
                        continue
                    x, y = WIDTH // 2 + (i - 1) * 190, HEIGHT // 2 + 40
                    creix = min(1.0, (self.temps_fase - 30 - i * 22) / 10)
                    dibuixar_estrella(surf, x, y, int(26 * (0.6 + 0.4 * creix)), noves[i])
                    text(surf, noms[i], F_TEXT_PP, BLANC if noves[i] else GRIS, (x, y + 40))
                    if guanyades[i]:
                        text(surf, f"+{XP_ESTRELLA} XP", F_MINI, (255, 200, 255), (x, y + 62))
        self.dibuixar_avisos(surf, 204)
        self.radio.dibuixar(surf)
        if self.mode == "tutorial" and self.estat in ("joc", "pausa"):
            self.dibuixar_tutorial(surf)
        if self.presentacio:
            self.dibuixar_presentacio(surf)
        if self.estat == "joc" and not self.presentacio:
            self.dibuixar_mira(surf)

    def dibuixar_avisos(self, surf, y):
        for k, (txt, color, temps) in enumerate(self.avisos):
            img = render(T(txt), F_HUD, color)
            caixa = img.get_rect(center=(WIDTH // 2, y + k * 26)).inflate(18, 10)
            capa = pygame.Surface(caixa.size, pygame.SRCALPHA)
            capa.fill((10, 8, 24, 200))
            surf.blit(capa, caixa)
            pygame.draw.rect(surf, color, caixa, 1, border_radius=4)
            surf.blit(img, img.get_rect(center=caixa.center))

    def dibuixar_menu(self, surf):
        self.fons_menu.dibuixar(surf)
        LOGO_MENU.dibuixar(surf, 268, 112, self.t_global)
        # informació del jugador, a dalt a la dreta
        r = text(surf, str(self.monedes), F_UI, GROC, (WIDTH - 22, 26), ancora="midright")
        dibuixar_moneda(surf, r.left - 16, 25)
        text(surf, TITOLS[self.titol], F_MINI, (255, 200, 255), (WIDTH - 22, 50), ancora="midright")
        text(surf, T("Battle Pass nivel {n}").format(n=self.nivell_passi()), F_MINI, GRIS, (WIDTH - 22, 66),
             ancora="midright")
        total = sum(sum(e) for fila in self.estrelles for e in fila)
        r = text(surf, f"{total}/45", F_MINI, (255, 220, 120), (WIDTH - 22, 84), ancora="midright")
        dibuixar_estrella(surf, r.left - 12, r.centery, 7, True)
        estat_so = "M: sonido OFF" if AUDIO.silenci else "M: sonido ON"
        text(surf, estat_so, F_MINI, GRIS, (20, HEIGHT - 28), ancora="midleft")
        self.dibuixar_avisos(surf, HEIGHT - 104)
        self.dibuixar_icones_menu(surf)

    def dibuixar_selector(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "SELECCIONA NIVEL", F_SUBTITOL, BLANC, (WIDTH // 2, 44))
        total = sum(sum(e) for fila in self.estrelles for e in fila)
        r = text(surf, f"{total}/45", F_UI, (255, 220, 120), (WIDTH - 24, 44), ancora="midright")
        dibuixar_estrella(surf, r.left - 18, r.centery, 11, True)
        for n in range(NUM_SECTORS):
            y = 116 + n * 76
            obert = any(self.nivells_desbloquejats[n])
            text(surf, f"{T('SECTOR')} {n + 1}", F_HUD, CIAN if obert else GRIS, (90, y - 14), ancora="midleft")
            text(surf, NOMS_SECTORS[n], F_TEXT_P, BLANC if obert else GRIS, (90, y + 10), ancora="midleft")
            for e in range(3):
                if self.nivells_desbloquejats[n][e]:
                    x = 470 + e * 150
                    dibuixar_pips(surf, x + 2, y + 28, POTENCIA_MAX[(n, e)], mida=6, color=TARONJA)
                    for k, ple in enumerate(self.estrelles[n][e]):
                        dibuixar_estrella(surf, x + 66 + k * 14, y + 31, 6, ple)
        text(surf, "Verde = completado · Cuadros = potencia · Estrellas: completar, sin daño, rápido", F_MINI, GRIS,
             (WIDTH - 24, HEIGHT - 40), ancora="midright")

    def dibuixar_botiga(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "TIENDA", F_SUBTITOL, BLANC, (WIDTH // 2, 40))
        r = text(surf, str(self.monedes), F_UI, GROC, (WIDTH - 24, 40), ancora="midright")
        dibuixar_moneda(surf, r.left - 14, 40)
        if self.pestanya == "armes":
            self.dibuixar_botiga_armes(surf)
        elif self.pestanya == "millores":
            self.dibuixar_botiga_millores(surf)
        else:
            self.dibuixar_botiga_aparenca(surf)

    def dibuixar_botiga_armes(self, surf):
        pos_ratoli = ratoli()
        info_hover = None
        for i, arma in enumerate(ARMES):
            carta = pygame.Rect(31 + i * 182, 126, 170, 318)
            propia = arma["id"] in self.armes_propies
            disponible = self.completat(arma["req"])
            vora = VERD if self.arma_actual == i else (BLAU_CLAR if propia else (GRIS if disponible else GRIS_FOSC))
            panell(surf, carta, vora)
            text(surf, T(arma["nom"]).upper(), F_TEXT_P, BLANC, (carta.centerx, carta.top + 20))
            img = mostra_soldat(arma["id"], self.uniforme, self.aparenca)
            if img:
                if not propia:
                    img = img.copy()
                    img.fill((70, 70, 70, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(img, img.get_rect(center=(carta.centerx, carta.top + 76)))
            bmax = self.bales_max(i)
            files = [("Daño", str(round(arma["dany"] * self.multiplicador_dany()))
                      + (f"x{arma['perdigons']}" if arma["perdigons"] > 1 else "")),
                     ("Balas", "∞" if bmax is None else str(bmax)),
                     ("Disp/s", str(round(FPS / arma["cadencia"], 1))),
                     ("Modo", "Auto" if arma["auto"] else "Semi")]
            for k, (nom_f, valor) in enumerate(files):
                y = carta.top + 130 + k * 24
                text(surf, nom_f, F_TEXT_P, GRIS, (carta.left + 12, y), ancora="midleft", ombra=False)
                text(surf, valor, F_TEXT_P, BLANC, (carta.right - 12, y), ancora="midright", ombra=False)
            text(surf, "Potencia", F_TEXT_P, GRIS, (carta.left + 12, carta.top + 228), ancora="midleft", ombra=False)
            dibuixar_pips(surf, carta.left + 14, carta.top + 242, arma["potencia"], color=TARONJA)
            if carta.collidepoint(pos_ratoli):
                info_hover = T(arma["desc"]) + ("" if disponible else " " + T("Disponible al completar {e}.").format(e=nom_escenari(arma['req'])))
        if self.missatge:
            return
        text(surf, info_hover or "La potencia decide dónde puedes usar cada arma.",
             F_TEXT_PP, CIAN, (WIDTH // 2 + 80, 499))

    def dibuixar_botiga_millores(self, surf):
        for k, m in enumerate(MILLORES):
            fila = pygame.Rect(60, 128 + k * 56, 840, 50)
            nivell = self.nivell_millora(m["id"])
            panell(surf, fila, VERD if nivell >= len(m["costos"]) else BLAU_CLAR)
            text(surf, m["nom"], F_UI, BLANC, (fila.left + 16, fila.top + 15), ancora="midleft")
            text(surf, m["desc"], F_TEXT_P, GRIS, (fila.left + 16, fila.top + 36), ancora="midleft", ombra=False)
            dibuixar_pips(surf, 604, fila.top + 18, nivell, total=len(m["costos"]), color=VERD, mida=14)
        if not self.missatge:
            text(surf, "Algunas mejoras se abren al avanzar en la historia.", F_TEXT_P, CIAN,
                 (WIDTH // 2 + 80, 499))

    def dibuixar_botiga_aparenca(self, surf):
        arma_id = ARMES[self.arma_actual]["id"]
        text(surf, "UNIFORME", F_HUD, CIAN, (80, 126), ancora="midleft")
        for k, (ident, dades) in enumerate(UNIFORMES.items()):
            r = pygame.Rect(80 + k * 116, 138, 106, 96)
            self._casella_cosmetic(surf, r, "uniforme", ident, self.uniforme == ident,
                                   mostra_soldat(arma_id, ident, self.aparenca), dades["nom"])
        text(surf, "ARMA", F_HUD, CIAN, (80, 256), ancora="midleft")
        for k, (ident, dades) in enumerate(APARENCES_ARMA.items()):
            r = pygame.Rect(80 + k * 135, 268, 125, 84)
            self._casella_cosmetic(surf, r, "arma", ident, self.aparenca == ident,
                                   mostra_soldat(arma_id, self.uniforme, ident), dades["nom"])
        text(surf, "TÍTULO", F_TEXT_P, CIAN, (80, 370), ancora="midleft")
        for k, (ident, nom) in enumerate(TITOLS.items()):
            r = pygame.Rect(80 + k * 162, 384, 152, 46)
            self._casella_cosmetic(surf, r, "titol", ident, self.titol == ident, None, nom)
        if not self.missatge:
            text(surf, "Consigue más subiendo de nivel en el Battle Pass.", F_TEXT_P, CIAN,
                 (WIDTH // 2 + 80, 499))

    def _casella_cosmetic(self, surf, r, tipus, ident, equipat, img, nom):
        prefix = {"uniforme": "u:", "arma": "a:", "titol": "t:"}[tipus]
        obert = prefix + ident in self.cosmetics
        hover = r.collidepoint(ratoli())
        panell(surf, r, VERD if equipat else (BLAU_CLAR if obert and hover else (GRIS if obert else GRIS_FOSC)))
        if img:
            if not obert:
                img = img.copy()
                img.fill((60, 60, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(img, img.get_rect(center=(r.centerx, r.top + 4 + (r.height - 22) // 2)))
            if tipus == "arma":
                color = APARENCES_ARMA[ident]["bala"] or Bala.ESTILS[ARMES[self.arma_actual]["estil"]][1]
                if color == "arc":
                    c = pygame.Color(0)
                    c.hsva = ((self.t_global * 6) % 360, 70, 100, 100)
                    color = (c.r, c.g, c.b)
                pygame.draw.circle(surf, color, (r.right - 14, r.top + 14), 6)
                pygame.draw.circle(surf, BLANC, (r.right - 14, r.top + 14), 2)
            text(surf, nom if F_MINI.size(nom)[0] < r.width - 6 else nom.split()[0], F_MINI,
                 BLANC if obert else GRIS, (r.centerx, r.bottom - 10))
        else:
            text(surf, nom, F_TEXT_PP, BLANC if obert else GRIS, (r.centerx, r.bottom - 15))
        if not obert:
            nivell = self.nivell_passi_de(tipus, ident)
            if nivell:
                text(surf, f"BP {nivell}", F_MINI, (255, 170, 255), (r.centerx, r.top + 10))

    def dibuixar_passi(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "BATTLE PASS", F_SUBTITOL, (255, 200, 255), (WIDTH // 2, 34))
        nivell = self.nivell_passi()
        barra = pygame.Rect(WIDTH // 2 - 350, 84, 700, 10)
        pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=6)
        fr = 1.0 if nivell >= len(PASSI) else (self.xp % XP_PER_NIVELL) / XP_PER_NIVELL
        pygame.draw.rect(surf, (255, 130, 255), (barra.x, barra.y, int(barra.w * fr), barra.h), border_radius=6)
        txt = (T("Nivel {n}/{t} · {x}/{m} XP").format(n=nivell, t=len(PASSI), x=self.xp % XP_PER_NIVELL, m=XP_PER_NIVELL)
               if nivell < len(PASSI) else T("Nivel máximo · {x} XP").format(x=self.xp))
        text(surf, txt, F_HUD, BLANC, (barra.centerx, barra.top - 12))
        pos_ratoli = ratoli()
        descripcio = None
        for i, recompenses in enumerate(PASSI):
            fila, col = divmod(i, 10)
            r = pygame.Rect(44 + col * 88, 106 + fila * 140, 80, 130)
            aconseguit = i < self.passi_reclamat
            panell(surf, r, VERD if aconseguit else ((255, 130, 255) if i == nivell else GRIS_FOSC))
            text(surf, str(i + 1), F_HUD, BLANC if aconseguit else GRIS, (r.centerx, r.top + 14))
            tipus, valor = recompenses[0]
            centre = (r.centerx, r.top + 62)
            if tipus == "monedes":
                dibuixar_moneda(surf, centre[0], centre[1] - 6, 12)
                text(surf, str(valor), F_MINI, GROC, (centre[0], centre[1] + 20))
            elif tipus == "uniforme":
                img = mostra_soldat("pistola", valor, "estandard")
                if img:
                    surf.blit(img, img.get_rect(center=centre))
            elif tipus == "arma":
                img = mostra_soldat(ARMES[self.arma_actual]["id"], "classic", valor)
                if img:
                    surf.blit(img, img.get_rect(center=centre))
            else:
                pygame.draw.rect(surf, (230, 210, 160), (centre[0] - 18, centre[1] - 14, 36, 28), border_radius=3)
                pygame.draw.rect(surf, (150, 110, 60), (centre[0] - 18, centre[1] - 14, 36, 28), 2, border_radius=3)
                text(surf, "T", F_UI, (120, 80, 40), centre, ombra=False)
            if len(recompenses) > 1:
                text(surf, "+1", F_MINI, (255, 200, 255), (r.right - 12, r.top + 14))
            if aconseguit:
                pygame.draw.lines(surf, VERD, False, [(r.centerx - 10, r.bottom - 22), (r.centerx - 3, r.bottom - 14),
                                                      (r.centerx + 11, r.bottom - 30)], 4)
            elif i > nivell:
                capa = pygame.Surface(r.size, pygame.SRCALPHA)
                capa.fill((0, 0, 0, 110))
                surf.blit(capa, r)
            if r.collidepoint(pos_ratoli):
                descripcio = T("Nivel {n}").format(n=i + 1) + ": " + " + ".join(nom_recompensa(t, v) for t, v in recompenses)
        text(surf, descripcio or "Gana XP eliminando enemigos y completando escenarios (más XP la primera vez).",
             F_TEXT_P, CIAN if descripcio else GRIS, (WIDTH // 2, 410))
        text(surf, "Equipa los aspectos en Tienda > Aspecto.", F_TEXT_P, GRIS, (WIDTH // 2, 438))

    def dibuixar_arxiu(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "HISTORIA", F_SUBTITOL, BLANC, (WIDTH // 2, 44))
        r = pygame.Rect(310, 96, 610, 348)
        panell(surf, r, CIAN)
        i = self.entrada_arxiu
        if self.completats[i][2]:
            titol, cos = ARXIU[i]
            text(surf, T(titol).upper(), F_UI, CIAN, (r.left + 20, r.top + 26), ancora="midleft")
            for k, linia in enumerate(ajustar_linies(T(cos), F_TEXT_P, r.width - 40)):
                text(surf, linia, F_TEXT_P, BLANC, (r.left + 20, r.top + 56 + k * 28), ancora="topleft")
        else:
            text(surf, "Expediente bloqueado", F_UI, GRIS, (r.centerx, r.centery - 20))
            text(surf, T("Completa el sector {n} para leerlo.").format(n=i + 1), F_TEXT_P, GRIS, (r.centerx, r.centery + 14))

    def dibuixar_guia(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "GUÍA", F_SUBTITOL, BLANC, (WIDTH // 2, 42))
        controls = [
            ("A / D  o  flechas", "Moverse"),
            ("ESPACIO / W / arriba", "Saltar (doble salto con Propulsores)"),
            ("S / abajo", "Bajar de una plataforma"),
            ("MAYÚS / clic derecho", "Voltereta: esquiva sin recibir daño"),
            ("Clic izquierdo", "Disparar (mantén: armas automáticas)"),
            ("1-5 / Q / rueda", "Cambiar de arma"),
            ("P / ESC", "Pausa"),
            ("G", "Volver al menú"),
            ("M", "Activar / silenciar el sonido"),
            ("F11", "Pantalla completa (volumen y vídeo en Opciones)"),
        ]
        for i, (tecla, accio) in enumerate(controls):
            y = 86 + i * 27
            text(surf, tecla, F_TEXT_P, GROC, (130, y), ancora="midleft")
            text(surf, accio, F_TEXT_P, BLANC, (400, y), ancora="midleft")
        consells = [
            "Cada escenario limita la potencia de las armas que puedes usar.",
            "Cuando un enemigo brilla, va a atacar: ¡apártate o rueda!",
            "Los escudos solo paran lo que les llega de frente: rodéalos.",
            "Estrellas: completa el escenario, sin recibir daño y a tiempo.",
        ]
        for i, c in enumerate(consells):
            text(surf, "· " + T(c), F_TEXT_P, CIAN, (130, 366 + i * 25), ancora="midleft")

    def dibuixar_credits(self, surf):
        """Crèdits que pugen sols (ESPAI o fletxa avall per anar més de pressa)."""
        self.fons_menu.dibuixar(surf)
        teclat = pygame.key.get_pressed()
        rapid = teclat[pygame.K_SPACE] or teclat[pygame.K_DOWN] or pygame.mouse.get_pressed()[0]
        enrere = teclat[pygame.K_UP]
        self.credits_y += 2.5 if enrere else -(4.0 if rapid else 0.75)
        alts = {"logo": LOGO_MENU.h, "petit": 26, "gran": 70, "seccio": 40, "nom": 34, "text": 28, "gracies": 60}
        y = self.credits_y
        for item in self.contingut_credits():
            tipus = item[0]
            alt = item[1] if tipus == "espai" else alts[tipus]
            if -alt < y < HEIGHT + 10:
                if tipus == "logo":
                    LOGO_MENU.dibuixar(surf, WIDTH // 2, y, self.t_global)
                elif tipus == "petit":
                    text(surf, item[1], F_HUD, GRIS, (WIDTH // 2, y + 12))
                elif tipus == "gran":
                    text(surf, item[1], F_TITOL, GROC, (WIDTH // 2, y + 34))
                elif tipus == "seccio":
                    text(surf, item[1], F_HUD, CIAN, (WIDTH // 2, y + 26))
                elif tipus == "nom":
                    text(surf, item[1], F_TEXT, BLANC, (WIDTH // 2, y + 16))
                elif tipus == "text":
                    text(surf, item[1], F_TEXT_PP, (200, 205, 225), (WIDTH // 2, y + 13))
                elif tipus == "gracies":
                    text(surf, item[1], F_GRAN, GROC, (WIDTH // 2, y + 30))
            y += alt
        if y < 0:                                       # torna a començar
            self.credits_y = float(HEIGHT)
        # franges que esvaeixen el text a dalt i a baix
        surf.blit(DEGRADAT_DALT, (0, 0))
        surf.blit(DEGRADAT_BAIX, (0, HEIGHT - DEGRADAT_BAIX.get_height()))
        # Nexus corrent i un dron que el persegueix, a sota
        spr = sprites_jugador("pistola", self.uniforme, self.aparenca)
        if spr:
            frame = spr.poses["corre"][(self.t_global // 5) % len(spr.poses["corre"])][1]
            surf.blit(frame, frame.get_rect(midbottom=(110, HEIGHT - 52)))
        dron = SPR_ENEMIC.get("dron")
        if dron:
            surf.blit(dron, dron.get_rect(center=(WIDTH - 120, HEIGHT - 120 + math.sin(self.t_global * 0.05) * 10)))
        text(surf, "ESPACIO / flecha abajo: más rápido", F_MINI, GRIS, (WIDTH - 20, HEIGHT - 20), ancora="midright")

    def dibuixar_loading(self, surf):
        self.fons_menu.dibuixar(surf)
        LOGO_GRAN.dibuixar(surf, WIDTH // 2, 18, self.t_global)
        text(surf, "UN JUEGO DE ABEL", F_UI, BLANC, (WIDTH // 2, 394))
        progres = min(1.0, self.temps_estat / (FPS * 2.5))
        barra = pygame.Rect(WIDTH // 2 - 160, 420, 320, 14)
        pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=4)
        pygame.draw.rect(surf, CIAN, (barra.x, barra.y, int(barra.w * progres), barra.h), border_radius=4)
        if progres >= 1 and (pygame.time.get_ticks() // 400) % 2:
            text(surf, "Haz clic para empezar", F_HUD, GROC, (WIDTH // 2, 462))

    def dibuixar_pausa(self, surf):
        self.dibuixar_joc(surf)
        vel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        vel.fill((0, 0, 0, 160))
        surf.blit(vel, (0, 0))
        text(surf, "PAUSA", F_TITOL, BLANC, (WIDTH // 2, 120))

    # ----- Esdeveniments ----------------------------------------------------
    def gestionar_event(self, ev):
        if ev.type == pygame.QUIT:
            self.canviar_estat("quit")
            return
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_m:
            AUDIO.commutar_silenci()
            return
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
            PANTALLA.commutar_completa()
            self.desar_progres()
            if self.estat == "opcions":
                self.entrar_opcions(self.tornada_opcions)
            return
        if ev.type == getattr(pygame, "VIDEORESIZE", -1):
            PANTALLA.recalcular()
            return
        if self.estat == "opcions":
            if any(l.gestionar(ev) for l in self.lliscadors):
                return
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.tornada_opcions()
                return
        if ev.type == getattr(pygame, "WINDOWFOCUSLOST", -1) and self.estat == "joc" and self.fase == "jugant":
            self.pausar()
            return

        if self.estat == "loading":
            if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                self.sortir_carrega()
            return
        if self.estat == "intro":                  # només es pot saltar amb el botó (o ESC); no s'accelera
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.intro.saltar()
            else:
                self.intro.boto_saltar.gestionar(ev)
            return

        if self.estat == "menu" and self.menu_idioma and self.gestionar_menu_idioma(ev):
            return
        if self.estat == "menu" and ev.type == pygame.KEYDOWN:          # codi Konami
            self.konami = (self.konami + [ev.key])[-10:]
            if self.konami == [pygame.K_UP, pygame.K_UP, pygame.K_DOWN, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                               pygame.K_LEFT, pygame.K_RIGHT, pygame.K_b, pygame.K_a]:
                self.desbloquejar("konami")
        if self.estat == "joc" and self.presentacio:            # saltar la presentació del cap
            if ((ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN))
                    or (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1)):
                self.presentacio["t"] = max(self.presentacio["t"], 150)
                return

        if gestionar_botons(self.botons, ev):
            return

        if self.estat == "joc":
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_LSHIFT, pygame.K_RSHIFT) and self.fase == "jugant":
                self.esquivar()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3 and self.fase == "jugant":
                self.esquivar()
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    self.jugador.demanar_salt()
                elif ev.key in (pygame.K_p, pygame.K_ESCAPE) and self.fase == "jugant":
                    self.pausar()
                elif ev.key == pygame.K_g:
                    self.entrar_menu()
                elif ev.key == pygame.K_q:
                    self.seguent_arma(1)
                elif pygame.K_1 <= ev.key <= pygame.K_5:
                    self.canviar_arma(ev.key - pygame.K_1)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.esperar_alliberar = False
                self.clic_pendent = 12
            elif ev.type == pygame.MOUSEWHEEL and ev.y:
                self.seguent_arma(-1 if ev.y > 0 else 1)
        elif self.estat == "pausa":
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_p, pygame.K_ESCAPE):
                self.reprendre()
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_g:
                self.entrar_menu()
        elif self.estat == "narrativa":
            if ((ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER))
                    or (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1)):
                self.avancar_narrativa()
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.entrar_menu()
        elif self.estat == "derrota":
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                    if self.pantalla_text.complet:
                        self.iniciar_supervivencia() if self.mode == "supervivencia" else self.iniciar_joc()
                    else:
                        self.pantalla_text.completar()
                elif ev.key in (pygame.K_ESCAPE, pygame.K_g):
                    self.entrar_supervivencia() if self.mode == "supervivencia" else self.entrar_menu()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.pantalla_text.completar()
        elif self.estat == "ajuda":
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.ajuda_despres()
        elif self.estat == "novetats" and ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.sortir_novetats()
            elif ev.key == pygame.K_LEFT and self.pagina_novetats > 0:
                self.entrar_novetats(self.pagina_novetats - 1)
            elif ev.key == pygame.K_RIGHT and self.pagina_novetats < len(NOVETATS) - 1:
                self.entrar_novetats(self.pagina_novetats + 1)
        elif self.estat in ("selector", "botiga", "guia", "credits", "passi", "arxiu", "supervivencia", "logros"):
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_g):
                self.entrar_menu()

    # ----- Bucle principal --------------------------------------------------
    def actualitzar(self):
        self.temps_estat += 1
        self.t_global += 1
        if self.temps_missatge > 0:
            self.temps_missatge -= 1
            if self.temps_missatge == 0:
                self.missatge = ""
        for a in self.avisos[:]:
            a[2] -= 1
            if a[2] <= 0:
                self.avisos.remove(a)
        for av in self.avisos_logro[:3]:
            av[1] += 1
        self.avisos_logro = [av for av in self.avisos_logro if av[1] < 240]
        if self.estat in ("loading", "menu", "selector", "botiga", "guia", "credits", "passi", "arxiu", "opcions",
                          "supervivencia", "logros", "idioma_inicial", "ajuda"):
            self.fons_menu.actualitzar()
        if self.estat == "loading" and self.temps_estat > FPS * 6:
            self.sortir_carrega()
        elif self.estat == "intro":
            self.intro.actualitzar()
        elif self.estat == "joc":
            self.actualitzar_joc()
        elif self.estat in ("narrativa", "derrota"):
            self.pantalla_text.actualitzar()

    def dibuixar(self, surf):
        dibuix = {
            "loading": self.dibuixar_loading, "menu": self.dibuixar_menu, "selector": self.dibuixar_selector,
            "botiga": self.dibuixar_botiga, "guia": self.dibuixar_guia, "credits": self.dibuixar_credits,
            "joc": self.dibuixar_joc, "pausa": self.dibuixar_pausa, "passi": self.dibuixar_passi,
            "arxiu": self.dibuixar_arxiu, "intro": lambda s: self.intro.dibuixar(s), "opcions": self.dibuixar_opcions,
            "supervivencia": self.dibuixar_supervivencia, "logros": self.dibuixar_logros,
            "idioma_inicial": self.dibuixar_idioma_inicial, "ajuda": self.dibuixar_ajuda,
            "novetats": self.dibuixar_novetats,
        }.get(self.estat)
        if dibuix:
            dibuix(surf)
        elif self.pantalla_text:
            self.pantalla_text.dibuixar(surf)
        if self.estat not in ("narrativa", "derrota"):
            for b in self.botons:
                b.dibuixar(surf)
        if self.missatge and self.estat != "joc":
            col = VERD if getattr(self, "missatge_ok", False) else VERMELL
            if self.estat == "botiga":
                text(surf, self.missatge, F_HUD, col, (WIDTH // 2 + 80, 499))
            else:
                text(surf, self.missatge, F_HUD, col, (WIDTH // 2 - 60, HEIGHT - 28))
        if self.avisos_logro and self.estat != "loading":
            self.dibuixar_avisos_logro(surf)

    def pas(self):
        """Un fotograma complet (també l'utilitzen les proves automàtiques)."""
        for ev in pygame.event.get():
            if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and hasattr(ev, "pos"):
                ev = pygame.event.Event(ev.type, {**ev.dict, "pos": PANTALLA.a_virtual(ev.pos)})
            self.gestionar_event(ev)
        if self.estat == "quit":
            return False
        self.actualitzar()
        if self.estat == "quit":
            return False
        self.dibuixar(screen)
        PANTALLA.presentar(screen)
        return True

    async def main(self):
        if not AUDIO.silenci:
            AUDIO.musica("menu")
        if WEB:
            self.descarrega = asyncio.create_task(DESCARREGUES.executar())    # música en segon pla
        while self.pas():
            self.clock.tick(FPS)
            await asyncio.sleep(0)      # imprescindible al navegador: retorna el control al bucle d'esdeveniments
        pygame.quit()
        if not WEB:
            sys.exit()


LOGO_MENU = Logo(440)
LOGO_GRAN = Logo(560)


def canviar_idioma(codi):
    """Canvia l'idioma i torna a dibuixar els logotips (tenen el títol del joc)."""
    global LOGO_MENU, LOGO_GRAN
    posar_idioma(codi)
    LOGO_MENU = Logo(440)
    LOGO_GRAN = Logo(560)
VINYETA = crear_vinyeta()


def crear_degradat(alt, cap_avall):
    s = pygame.Surface((WIDTH, alt), pygame.SRCALPHA)
    for y in range(alt):
        k = (1 - y / alt) if cap_avall else (y / alt)
        pygame.draw.line(s, (*FONS, int(255 * k ** 1.3)), (0, y), (WIDTH, y))
    return s


DEGRADAT_DALT = crear_degradat(70, True)
DEGRADAT_BAIX = crear_degradat(90, False)
ALARMA = crear_vinyeta_color((255, 20, 20))
PULSACIO = crear_vinyeta_color((190, 40, 255))
CAPA_TRANSPARENT = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
BANDA_ENERGIA = pygame.Surface((WIDTH, 40), pygame.SRCALPHA)
for _i in range(40):
    pygame.draw.line(BANDA_ENERGIA, (90, 230, 255, int(50 * math.sin(math.pi * _i / 40))), (0, _i), (WIDTH, _i))
RESPLENDOR_FOC = crear_resplendor_foc()
OVNI_LLUNYA = crear_ovni_llunya()
FRANJA_HUD = pygame.Surface((WIDTH, 72), pygame.SRCALPHA)
for _y in range(72):
    pygame.draw.line(FRANJA_HUD, (0, 0, 0, int(140 * (1 - _y / 72))), (0, _y), (WIDTH, _y))


if __name__ == "__main__":
    asyncio.run(Game().main())
