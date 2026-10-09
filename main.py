"""
Joc Militar: Invasió Alienígena
Versió millorada, compatible amb escriptori i navegador (pygbag / GitHub Pages).

Escriptori:  python main.py
Navegador:   pygbag .        (GitHub Actions recompila index.html i historygame.apk)
"""
import asyncio
import hashlib
import json
import math
import os
import random
import sys
import time

import pygame

from idiomes import IDIOMES, T, idioma, posar_idioma
from contingut import (CODIS, BESTIARI, CAMUFLATGES, DESAFIAMENTS, DIBUIX_DRONS, DRONS, EFECTES_BAIXA, ESTELES, MAESTRIA,
                       MIRES, MONEDES_REPETICIO, PREMI_REPTE, PREMI_TOTS_REPTES, RANGS, REPTES_POOL, TARGETES, TEMES_HUD,
                       XP_LOGRO, xp_acumulada_passi, xp_nivell_passi)
from dades import (DETALL_ARMES, DETALL_MILLORES, NIVELL_TUTORIAL, PASSOS_TUTORIAL, CALOR_DISPAR, ARRENCADA, FRE_MINIGUN, APARENCES_ARMA, ARENES, NOMS_ARENES, CATEGORIES_LOGRO, LOGROS, LOGRO_PER_ID, PLAQUES, REPISES_PLACA, ARMA_PER_ID, ARMES, ARXIU, CAPS_FINALS, CAPS_NORMALS, CINEMATICA_CAP,
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
    # Reinici general: les partides desades amb un número diferent es buiden un sol cop (només es conserven
    # l'idioma i les opcions). Puja'l només si mai cal tornar a començar tothom de zero.
    REINICI = 1

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
            if not isinstance(dades, dict):
                return {}
            if dades.get("reinici") != cls.REINICI:
                opcions = dades.get("opcions")
                dades = {"opcions": opcions} if isinstance(opcions, dict) else {}
                cls.desar(dades)                         # desa-ho ja amb el número nou: no es tornarà a buidar
            return dades
        except Exception as err:
            print(f"No s'ha pogut carregar la partida: {err}")
            return {}

    @classmethod
    def desar(cls, dades):
        try:
            dades = dict(dades, reinici=cls.REINICI)
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
# La Press Start 2P encongeix les majúscules accentuades fins que semblen minúscules (COLECCIóN):
# amb aquesta font s'escriuen sense accent, que es llegeix molt millor.
FONTS_PIXEL = set()
SENSE_ACCENT = str.maketrans("ÁÀÄÂÉÈËÊÍÌÏÎÓÒÖÔÚÙÜÛ", "AAAAEEEEIIIIOOOOUUUU")


def carregar_font(nom, mida):
    try:
        f = pygame.font.Font(ruta("fonts", nom), mida)
        if nom.startswith("PressStart"):
            FONTS_PIXEL.add(id(f))
        return f
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
# El protagonista (Nexus) en alta definició. Els fotogrames els genera tools/generar_nexus.py
# (quiet x2, corre x6, salt i caiguda per a cada arma i nivell de blindatge); aquí només es pinten amb
# l'uniforme, l'aspecte d'arma i el camuflatge, canviant colors exactes de la paleta de cada material.
# ---------------------------------------------------------------------------
def _carregar_info_nexus():
    try:
        with open(ruta("img", "nexus.json"), encoding="utf-8") as fitxer:
            return json.load(fitxer)
    except (OSError, ValueError) as err:
        print(f"No s'ha pogut carregar nexus.json: {err}")
        return None


NEXUS = _carregar_info_nexus()
_TIRES_NEXUS = {}
SPR_JUGADOR_CACHE = {}


def lluminositat(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def recolorar(img, mapa):
    """Canvia colors exactes. En dues passades (primer a colors temporals) perquè un color nou
    que coincideixi amb un de vell no es torni a canviar."""
    if not mapa or img is None:
        return img
    s = img.copy()
    try:
        pa = pygame.PixelArray(s)
        temporals = []
        for k, (vell, nou) in enumerate(mapa.items()):
            temp = (0, 1 + k // 250, 1 + k % 250)
            pa.replace(vell, temp)
            temporals.append((temp, nou))
        for temp, nou in temporals:
            pa.replace(temp, nou)
        del pa
        return s
    except Exception as err:                         # sense PixelArray: píxel a píxel (més lent, però un sol cop)
        print(f"PixelArray no disponible ({err}): es recolora píxel a píxel")
    s = img.copy()
    s.lock()
    w, h = s.get_size()
    for y in range(h):
        for x in range(w):
            c = s.get_at((x, y))
            if c.a:
                nou = mapa.get((c.r, c.g, c.b))
                if nou:
                    s.set_at((x, y), (*nou, c.a))
    s.unlock()
    return s


def mapa_colors(uniforme="classic", tint=None):
    """Colors de l'uniforme (jaqueta, casc, pantalons) i tint del metall de l'arma, amb la mateixa llum relativa."""
    if not NEXUS:
        return {}
    mats, grups, mapa = NEXUS["materials"], NEXUS["grups"], {}
    colors = UNIFORMES.get(uniforme, {}).get("colors")
    if colors:
        for grup, idx, ref in (("jaqueta", 0, "unif"), ("casc", 1, "casc"), ("pantalons", 2, "pant")):
            base = max(1.0, lluminositat(mats[ref][2]))
            for mat in grups[grup]:
                for t in mats[mat]:
                    mapa[tuple(t)] = tuple(min(255, int(v * lluminositat(t) / base)) for v in colors[idx])
    if tint:
        for mat in grups["arma"]:
            for t in mats[mat]:
                mapa[tuple(t)] = tuple(min(255, int(v * lluminositat(t) / 80)) for v in tint)
    return mapa


class SpritesNexus:
    """Fotogrames del soldat a punt per dibuixar: poses[nom][i][direcció], ancoratge dels peus i boca del canó."""

    def __init__(self, tira, dades):
        w, h = dades["mida"]
        self.ample, self.alt = w, h
        self.peus_x = dades["ancora"]
        bx, by = dades["boques"][0]
        self.cano_dx = bx - self.peus_x                          # punta del canó respecte als peus
        self.cano_dy = by - h
        self.poses = {"quiet": [], "corre": [], "salt": [], "caiguda": []}
        for i, nom in enumerate(NEXUS["fotogrames"]):
            img = tira.subsurface((i * w, 0, w, h)).copy()
            self.poses[nom].append({1: img, -1: pygame.transform.flip(img, True, False)})

    def ancoratge(self, direccio):
        return self.peus_x if direccio == 1 else self.ample - self.peus_x


def tint_arma(aparenca, camo=None):
    """Tint del metall de l'arma: el camuflatge de maestria mana sobre l'aspecte d'arma."""
    if camo and camo in CAMUFLATGES and CAMUFLATGES[camo]["tint"]:
        return CAMUFLATGES[camo]["tint"]
    return APARENCES_ARMA.get(aparenca, APARENCES_ARMA["estandard"])["tint"]


def sprites_jugador(arma_id, uniforme="classic", aparenca="estandard", blindatge=0, camo=None):
    """Fotogrames del soldat amb l'arma, l'uniforme, l'aspecte i el blindatge triats (es guarden)."""
    if not NEXUS:
        return None
    arma_id = arma_id if arma_id in NEXUS["armes"] else "pistola"
    blindatge = max(0, min(3, blindatge))
    clau = (arma_id, uniforme, aparenca, blindatge, camo)
    spr = SPR_JUGADOR_CACHE.get(clau)
    if spr is None:
        if (arma_id, blindatge) not in _TIRES_NEXUS:
            _TIRES_NEXUS[(arma_id, blindatge)] = carregar_imatge(f"nexus_{arma_id}_{blindatge}.png")
        tira = _TIRES_NEXUS[(arma_id, blindatge)]
        if tira is None:
            return None
        if len(SPR_JUGADOR_CACHE) > 48:                          # no omplir la memòria amb previsualitzacions
            SPR_JUGADOR_CACHE.clear()
        tira = recolorar(tira, mapa_colors(uniforme, tint_arma(aparenca, camo)))
        spr = SPR_JUGADOR_CACHE[clau] = SpritesNexus(tira, NEXUS["armes"][arma_id])
    return spr


_ARMES_SOLES = {}


def imatge_arma(arma_id, aparenca="estandard", camo=None, escala=2):
    """L'arma sola, sense el soldat (botiga), amb l'aspecte o el camuflatge."""
    if not NEXUS or arma_id not in NEXUS["armes_soles"]:
        return None
    clau = (arma_id, aparenca, camo, escala)
    img = _ARMES_SOLES.get(clau)
    if img is None:
        if "tira" not in _ARMES_SOLES:
            _ARMES_SOLES["tira"] = carregar_imatge("nexus_armes.png")
        tira = _ARMES_SOLES["tira"]
        if tira is None:
            return None
        x, y, w, h = NEXUS["armes_soles"][arma_id]
        img = recolorar(tira.subsurface((x, y, w, h)).copy(), mapa_colors("classic", tint_arma(aparenca, camo)))
        img = _ARMES_SOLES[clau] = pygame.transform.scale(img, (w * escala, h * escala))
    return img


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


def tenyir(img, color, alfa=110):
    s = img.copy()
    capa = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    capa.fill((*color, alfa))
    mascara = silueta_blanca(img)
    capa.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(capa, (0, 0))
    return s


# ---------------------------------------------------------------------------
# El Comandant Suprem en alta definició: capes animades que es componen a cada fotograma
# (tentacles, braços, cos, banyes, cap i capes que brillen; vegeu tools/generar_comandant.py)
# ---------------------------------------------------------------------------
def _carregar_comandant():
    try:
        with open(ruta("img", "comandant.json"), encoding="utf-8") as fitxer:
            info = json.load(fitxer)
    except (OSError, ValueError) as err:
        print(f"No s'ha pogut carregar comandant.json: {err}")
        return None
    atles = carregar_imatge("comandant.png")
    if atles is None:
        return None
    info["peces"] = {n: (atles.subsurface((x, y, w, h)), (ox, oy))
                     for n, (x, y, w, h, ox, oy) in info["imatges"].items()}
    info["cervell_img"] = info["peces"]["cervell"][0].copy()        # còpia: se li canvia l'alfa
    return info


COMANDANT = _carregar_comandant()


def estat_comandant(t=0, **kw):
    """Estat de dibuix del Comandant (postures, boca, parpelles, mirada...)."""
    e = {"t": t, "tentacles": "ones", "braços": ("repos", "repos"), "cos": (1, 0), "boca": "tancada",
         "parpelles": "oberts", "mirada": (0.0, 0.0), "venes": None, "cervell": 0, "banya_trencada": False,
         "mort": False, "ira": False, "cap_dx": 0, "cap_dy": 0, "tent_dx": 0, "cos_dy": 0}
    e.update(kw)
    return e


def pupilles_comandant(surf, e, dx, dy):
    """Pupil·les en escletxa que segueixen el jugador (amb la parpella mig closa, només la meitat de baix)."""
    mx, my = e["mirada"]
    mig = e["parpelles"] == "mig"
    alt = 6 if e["ira"] else 8
    for x, y in COMANDANT["ulls"]:
        cx, cy = x + dx + round(mx * 3), y + dy + round(my * 2)
        dalt = max(cy - alt // 2, y + dy) if mig else cy - alt // 2
        baix = cy + alt // 2
        if baix > dalt:
            pygame.draw.rect(surf, (90, 10, 24), (cx - 1, dalt, 3, baix - dalt))
            pygame.draw.line(surf, (14, 2, 6), (cx, dalt), (cx, baix - 1))
    if not mig:
        for x, y in COMANDANT["ulls_petits"]:
            surf.set_at((x + dx + round(mx), y + dy + round(my * 0.6)), (14, 2, 6))
        for x, y in COMANDANT["ulls"]:                                   # reflex
            surf.fill((255, 252, 230), (x + dx - 6, y + dy - 2, 2, 1))


def compondre_comandant(e, surf=None):
    """Composa el Comandant en un llenç transparent (es pot reaprofitar el mateix llenç)."""
    info = COMANDANT
    if surf is None:
        surf = pygame.Surface(info["llenç"], pygame.SRCALPHA)
    else:
        surf.fill((0, 0, 0, 0))
    peces = info["peces"]

    def posar(nom, dx=0, dy=0):
        im, (ox, oy) = peces[nom]
        surf.blit(im, (ox + dx, oy + dy))

    t = e["t"]
    respira = round(math.sin(t * math.tau / 120)) + e["cos_dy"]
    cap_dy = round(math.sin((t - 12) * math.tau / 120) * 1.5) + e["cap_dy"] + e["cos_dy"]
    cap_dx = round(e["mirada"][0] * 2) + e["cap_dx"]
    tent = e["tentacles"]
    posar(f"tent_ones_{(t // 5) % info['n_ones']}" if tent == "ones" else f"tent_{tent}", e["tent_dx"], e["cos_dy"])
    posar(f"braç_{e['braços'][0]}_-1", 0, respira)
    posar(f"braç_{e['braços'][1]}_1", 0, respira)
    fase, esq = e["cos"]
    posar(f"cos_{fase}_{esq}", 0, respira)
    if e["venes"] == "tot":
        posar(f"venes_{fase}_{esq}_tot", 0, respira)
    else:
        posar(f"venes_{fase}_{esq}_{(t // 6) % info['n_venes']}", 0, respira)
    posar("banyes_trencades" if e["banya_trencada"] else "banyes", cap_dx, cap_dy)
    if e["mort"]:
        posar("cap_mort", cap_dx, cap_dy)
    else:
        posar(f"cap_{e['boca']}_{e['parpelles']}", cap_dx, cap_dy)
        if e["parpelles"] != "tancats":
            pupilles_comandant(surf, e, cap_dx, cap_dy)
        if e["cervell"]:
            im = info["cervell_img"]
            _, (ox, oy) = peces["cervell"]
            im.set_alpha(int(e["cervell"]))
            surf.blit(im, (ox + cap_dx, oy + cap_dy))
    return surf


if COMANDANT:
    # imatge fixa per al bestiari i les cinemàtiques; el retrat de la barra del cap és només el cap
    _cx, _cy = COMANDANT["cap"]
    SPR_ENEMIC["final_comandant"] = retallar(compondre_comandant(estat_comandant(30, mirada=(-0.8, 0.5))).subsurface(
        (_cx - 84, 0, 168, 206)))
    RETRAT_COMANDANT = compondre_comandant(estat_comandant(30, mirada=(-0.6, 0.4))).subsurface(
        (_cx - 40, _cy - 50, 80, 92)).copy()
    COMANDANT_MORT = retallar(compondre_comandant(estat_comandant(0, tentacles="flonjos", cos=(2, 1),
                                                                  banya_trencada=True, mort=True)))
else:
    RETRAT_COMANDANT = COMANDANT_MORT = None


# ---------------------------------------------------------------------------
# Enemics normals en alta definició (vegeu tools/generar_enemics.py): fotogrames per animació, també
# girats per mirar a l'esquerra, amb el punt d'ancoratge (els peus o el centre) i les boques dels canons.
# ---------------------------------------------------------------------------
MIDES_ENEMIC = {"soldat": (36, 52), "escut": (44, 56), "kamikaze": (28, 20),     # caixes de sempre
                "dron": (68, 58), "lloctinent": (102, 87), "cacador": (44, 24)}
VOLADORS_HD = ("dron", "lloctinent", "cacador")


def _carregar_enemics_hd():
    try:
        with open(ruta("img", "enemics_hd.json"), encoding="utf-8") as fitxer:
            info = json.load(fitxer)
    except (OSError, ValueError) as err:
        print(f"No s'ha pogut carregar enemics_hd.json: {err}")
        return {}
    atles = carregar_imatge("enemics_hd.png")
    if atles is None:
        return {}
    for tipus, e in info.items():
        W, H = e["llenç"]
        ax, ay = e["ancora"]
        e["fr"] = {}
        for nom, (x, y, w, h, ox, oy) in e["imatges"].items():
            img = atles.subsurface((x, y, w, h))
            # (imatge, desplaçament respecte de l'ancoratge) mirant a la dreta (1) i a l'esquerra (-1)
            e["fr"][nom] = {1: (img, (ox - ax, oy - ay)),
                            -1: (pygame.transform.flip(img, True, False), (ax - ox - w, oy - ay))}
        if tipus in VOLADORS_HD:                  # els voladors fan servir el llenç sencer (centrat)
            e["sencers"] = []
            for nom in e["anims"]["vola"]:
                x, y, w, h, ox, oy = e["imatges"][nom]
                s = pygame.Surface((W, H), pygame.SRCALPHA)
                s.blit(atles, (ox, oy), (x, y, w, h))
                e["sencers"].append(s)
    return info


ENEMICS_HD = _carregar_enemics_hd()


def frame_hd(tipus, anim, k, sentit=1):
    """(imatge, desplaçament des de l'ancoratge) del fotograma k d'una animació (es repeteix si cal)."""
    e = ENEMICS_HD[tipus]
    noms = e["anims"][anim]
    return e["fr"][noms[k % len(noms)]][sentit]


def punt_hd(tipus, clau, anim, k, sentit=1):
    """Punt guardat d'un fotograma (boca del canó o emissor de l'escut), relatiu a l'ancoratge."""
    e = ENEMICS_HD[tipus]
    noms = e["anims"][anim]
    p = e.get(clau, {}).get(noms[k % len(noms)])
    if p is None:
        return None
    return (p[0] - e["ancora"][0]) * sentit, p[1] - e["ancora"][1]


for _t in ENEMICS_HD:                             # bestiari, menús i restes: el primer fotograma retallat
    SPR_ENEMIC[_t] = frame_hd(_t, "vola" if _t in VOLADORS_HD else ("corre" if _t == "kamikaze" else "camina"), 0)[0]

# ---------------------------------------------------------------------------
# Caps de sector en alta definició (vegeu tools/generar_caps.py): fotogrames sencers per animació
# ---------------------------------------------------------------------------
def _carregar_caps_hd():
    try:
        with open(ruta("img", "caps_hd.json"), encoding="utf-8") as fitxer:
            info = json.load(fitxer)
    except (OSError, ValueError) as err:
        print(f"No s'ha pogut carregar caps_hd.json: {err}")
        return {}
    atles = carregar_imatge("caps_hd.png")
    if atles is None:
        return {}
    return {int(n): {anim: [atles.subsurface(e["imatges"][nom]) for nom in noms] for anim, noms in e["anims"].items()}
            for n, e in info.items()}


CAPS_HD = _carregar_caps_hd()
for _n, _c in CAPS_HD.items():
    SPR_ENEMIC[("boss", _n)] = retallar(_c["repos"][0])
# ---------------------------------------------------------------------------
# Nau Mare i Nucli de Xylos en alta definició (vegeu tools/generar_finals.py)
# ---------------------------------------------------------------------------
def _carregar_finals_hd():
    try:
        with open(ruta("img", "finals_hd.json"), encoding="utf-8") as fitxer:
            info = json.load(fitxer)
    except (OSError, ValueError) as err:
        print(f"No s'ha pogut carregar finals_hd.json: {err}")
        return None
    atles = carregar_imatge("finals_hd.png")
    if atles is None:
        return None
    info["peces"] = {n: (atles.subsurface((x, y, w, h)), (ox, oy)) for n, (x, y, w, h, ox, oy) in info["imatges"].items()}
    return info


FINALS_HD = _carregar_finals_hd()


def peça_final(nom):
    return FINALS_HD["peces"][nom]


def imatge_nucli(tent=0, dany=0, iris=True):
    """Nucli compost (per al bestiari i les cinemàtiques)."""
    W, H = FINALS_HD["nucli"]["llenç"]
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    for nom in ([f"nucli_tent_{tent}"] if tent is not None else []) + [f"nucli_cos_{dany}"]:
        im, (ox, oy) = peça_final(nom)
        s.blit(im, (ox, oy))
    if iris:
        cx, cy = FINALS_HD["nucli"]["ull"]
        pygame.draw.circle(s, (85, 25, 105), (cx - 5, cy + 4), 18)
        pygame.draw.circle(s, (170, 50, 210), (cx - 5, cy + 4), 15)
        pygame.draw.ellipse(s, (20, 0, 20), (cx - 8, cy - 7, 6, 22))
        s.fill((255, 255, 255), (cx - 11, cy - 4, 2, 2))
    return s


if FINALS_HD:
    _im, _ = peça_final("nau_000")
    SPR_ENEMIC["final_nau"] = _im.copy()
    SPR_ENEMIC["final_nucli"] = retallar(imatge_nucli(0))
    NUCLI_CINE = retallar(imatge_nucli(None))              # sense tentacles: la cinemàtica el fa gran
else:
    NUCLI_CINE = None

ESPECIAL_CAP = {0: "escotilla", 1: "beines", 2: "punteria", 3: "escombrada", 4: "eixam"}
PUNTS_CAP = {0: {"canons": ((12, 96), (148, 96)), "escotilla": (80, 14)},      # coordenades del llenç de cada cap
             1: {"beines": ((54, 110), (80, 118), (106, 110))},
             2: {"sensor": (86, 15)},
             3: {"torreta": (84, 86)},
             4: {"fibló": (90, 132)}}

_CACHE_ESCUT = {}


def imatge_escut(alt):
    """Barrera hexagonal de l'escuder (mirant a la dreta): s'abomba endavant i té cel·les d'energia."""
    s = _CACHE_ESCUT.get(alt)
    if s is None:
        w = 18
        s = pygame.Surface((w, alt), pygame.SRCALPHA)
        forma = [(1, 1), (9, alt * 0.12), (15, alt * 0.34), (17, alt * 0.5), (15, alt * 0.66), (9, alt * 0.88),
                 (1, alt - 2), (5, alt * 0.5)]
        pygame.draw.polygon(s, (90, 230, 255, 90), forma)
        cel = pygame.Surface((w, alt), pygame.SRCALPHA)
        for fila, y in enumerate(range(0, alt + 6, 6)):
            for x in range(-3 + (fila % 2) * 4, w + 4, 8):
                hexa = [(x + 3 * math.cos(a), y + 3 * math.sin(a)) for a in (i * math.pi / 3 for i in range(6))]
                pygame.draw.polygon(cel, (170, 250, 255, 120), hexa, 1)
        mascara = pygame.Surface((w, alt), pygame.SRCALPHA)
        pygame.draw.polygon(mascara, (255, 255, 255, 255), forma)
        cel.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(cel, (0, 0))
        pygame.draw.lines(s, (16, 70, 100, 220), False, [(x + 1, y) for x, y in forma[1:6]], 3)   # vora fosca
        pygame.draw.lines(s, (210, 252, 255, 240), False, forma[:7], 2)
        _CACHE_ESCUT[alt] = s
    return s
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
        self.pausada = False
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
        if not AUDIO_OK:
            return
        self.reprendre()
        if nom == self.musica_actual:
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
            if self.pausada:                     # ha arribat una descàrrega amb el joc en pausa
                pygame.mixer.music.pause()
        except (OSError, pygame.error) as err:
            print(f"No s'ha pogut reproduir la música {fitxer}: {err}")

    def pausar(self):
        """Pausa la música (menú de pausa); reprendre() la continua des del mateix punt."""
        if AUDIO_OK and not self.pausada:
            self.pausada = True
            try:
                pygame.mixer.music.pause()
            except pygame.error:
                pass

    def reprendre(self):
        if AUDIO_OK and self.pausada:
            self.pausada = False
            try:
                pygame.mixer.music.unpause()
            except pygame.error:
                pass

    def aturar_musica(self):
        self.musica_actual = None
        self.pausada = False
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
        if id(font) in FONTS_PIXEL:
            txt = txt.translate(SENSE_ACCENT)
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


TEMA_HUD = [{"vora": (90, 120, 190), "fons": (8, 10, 24)}]     # tema del HUD equipat (cosmètic)


def panell_hud(surf, rect, vora=None, alfa=165):
    """Panell semitransparent amb vora pixelada i cantonades marcades (es guarda per mida)."""
    r = pygame.Rect(rect)
    vora = vora or TEMA_HUD[0]["vora"]
    fons = TEMA_HUD[0]["fons"]
    clau = (r.w, r.h, vora, alfa, fons)
    s = _CACHE_PANELL.get(clau)
    if s is None:
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        s.fill((*fons, alfa))
        fosc = tuple(c // 2 for c in vora)
        pygame.draw.rect(s, (*fosc, 230), s.get_rect(), 1)
        for cx, cy, sx, sy in ((0, 0, 1, 1), (r.w - 1, 0, -1, 1), (0, r.h - 1, 1, -1), (r.w - 1, r.h - 1, -1, -1)):
            pygame.draw.line(s, (*vora, 255), (cx, cy), (cx + sx * 5, cy), 1)
            pygame.draw.line(s, (*vora, 255), (cx, cy), (cx, cy + sy * 5), 1)
        s.fill((0, 0, 0, 0), (0, 0, 1, 1))
        _CACHE_PANELL[clau] = s
    surf.blit(s, r)
    return r


def dibuixar_calculadora(surf, cx, cy, k=1.0):
    """Icona de calculadora (codis, a la Botiga)."""
    w, h = int(22 * k), int(28 * k)
    cos = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
    pygame.draw.rect(surf, NEGRE, cos.move(0, 2), border_radius=int(4 * k))
    pygame.draw.rect(surf, (200, 204, 216), cos, border_radius=int(4 * k))
    pygame.draw.rect(surf, (90, 94, 110), cos, 1, border_radius=int(4 * k))
    pygame.draw.rect(surf, (60, 140, 90), (cos.x + 3 * k, cos.y + 3 * k, w - 6 * k, 7 * k))
    for fila in range(3):
        for col in range(3):
            color = (255, 150, 60) if (fila, col) == (2, 2) else (70, 74, 92)
            pygame.draw.rect(surf, color, (cos.x + (3 + col * 6) * k, cos.y + (13 + fila * 5) * k, 4 * k, 3 * k))


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

    def __init__(self, ample=600, escala=None):
        k = escala if escala is not None else ample / 600
        self.k = k
        self.w = int(ample)
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
        if self.hover():                                   # vora que batega quan hi passes el ratolí
            k = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.012)
            pygame.draw.rect(surf, tuple(int(c + (255 - c) * k) for c in aclarir(color, 60)), r, 2, border_radius=8)
        else:
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
    W, H = 28, 66
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
            cols = colors_estela(getattr(self, "estela", "normal"), self.temps)
            fantasma.fill((*cols[(self.temps // 2) % len(cols)], 255), special_flags=pygame.BLEND_RGBA_MULT)
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
        # atacs propis dels caps de sector
        "beina": (7, (220, 236, 60)),
        "espora": (4, (190, 240, 70)),
        "eixam": (5, (230, 196, 60)),
        "elit": (5, (255, 70, 70)),
        "torreta": (5, (110, 220, 255)),
    }

    __slots__ = ("x", "y", "vx", "vy", "dany", "radi", "color", "vida", "perfora", "tocats", "estil", "t", "k",
                 "gravetat")

    def __init__(self, x, y, vx, vy, dany, estil, color=None, vida=None, perfora=False, k=0, gravetat=0.0):
        self.gravetat = gravetat
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
        self.vy += self.gravetat
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
        elif e == "beina":                                     # beina d'espores que cau
            l = llum(14, (200, 240, 60))
            surf.blit(l, (ix - 14, iy - 14))
            pygame.draw.line(surf, (40, 110, 40), (ix, iy - 6), (ix - int(self.vx * 2), iy - 11), 2)
            pygame.draw.ellipse(surf, (60, 70, 10), (ix - 6, iy - 8, 12, 16))
            pygame.draw.ellipse(surf, c, (ix - 5, iy - 7, 10, 14))
            pygame.draw.ellipse(surf, (250, 255, 200), (ix - 3, iy - 5, 4, 6))
        elif e == "eixam":                                     # insecte de l'eixam: cos, ales que baten i ulls
            a = math.atan2(self.vy, self.vx)
            ca, sa = math.cos(a), math.sin(a)
            obre = 6 if (self.t // 2) % 2 else 3
            l = llum(10, (240, 200, 60))
            surf.blit(l, (ix - 10, iy - 10))
            for s_ in (-1, 1):
                pygame.draw.line(surf, (226, 226, 252), (ix, iy), (int(x - ca * 3 - sa * obre * s_), int(y - sa * 3 + ca * obre * s_)), 3)
            pygame.draw.line(surf, (24, 18, 34), (int(x - ca * 6), int(y - sa * 6)), (int(x + ca * 4), int(y + sa * 4)), 6)
            pygame.draw.line(surf, c, (int(x - ca * 5), int(y - sa * 5)), (int(x - ca), int(y - sa)), 3)
            pygame.draw.circle(surf, (255, 60, 60), (int(x + ca * 4), int(y + sa * 4)), 2)
        elif e == "elit":                                      # traçador vermell del Comandant d'Elit
            pygame.draw.line(surf, (90, 10, 20), (x - ux * 18, y - uy * 18), (x, y), 6)
            pygame.draw.line(surf, c, (x - ux * 14, y - uy * 14), (x, y), 4)
            pygame.draw.line(surf, (255, 220, 220), (x - ux * 8, y - uy * 8), (x, y), 2)
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
        self.hd_e = tipus in ENEMICS_HD                # enemic normal en alta definició
        if self.hd_e:
            self.w, self.h = MIDES_ENEMIC[tipus]
        self.hd_nau = tipus == "final_nau" and FINALS_HD is not None
        self.hd_nucli = tipus == "final_nucli" and FINALS_HD is not None
        if self.hd_nau:
            self.w, self.h = 220, 108
        elif self.hd_nucli:
            self.w, self.h = 152, 152
        self.hd_cap = tipus == "boss" and nivell in CAPS_HD   # cap de sector en alta definició
        if self.hd_cap:
            self.w, self.h = 120, 118
            self.especial, self.t_especial = None, 0
            self.mira = None
            self.angle_torreta = math.pi / 2
            self.arc = (0.0, 0.0)
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
        # atacs especials que el joc ha de recollir (ones, impactes, tremolor, làser) i mort animada
        self.laser = None
        self.impacte = False
        self.ones_noves = []
        self.tremolor_nou = 0
        self.morint = 0
        self.hd = tipus == "final_comandant" and COMANDANT is not None
        if self.hd:
            self._iniciar_comandant()

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
        if self.hd:
            return 0.0
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
        if self.hd:
            return self._actualitzar_comandant(jugador, altres, efectes, plataformes)
        if self.tipus == "final_nau":
            self._moure_ruta(320, 100, 0.4, 18)
        elif self.tipus == "final_nucli":
            self._moure_ruta(290, 140, 0.35, 45)
            return self._atacar_nucli(jugador)
        elif self.tipus == "cacador":
            bales = self._actualitzar_cacador(jugador, altres)
            if self.hd_e and self.mode == "envestida":            # estela del motor
                cx, cy = self.centre
                dx, dy = self.dir_envestida
                for _ in range(2):
                    efectes.append(Particula(cx - dx * 26 + random.uniform(-3, 3), cy - dy * 26 + random.uniform(-3, 3),
                                             -dx * random.uniform(0.5, 2), -dy * random.uniform(0.5, 2),
                                             random.choice(((90, 226, 255), (255, 172, 82), (236, 255, 255))),
                                             vida=random.randint(8, 16), mida=random.uniform(2, 4)))
            return bales
        else:
            self._vagar(jugador, altres)
        if self.hd_cap:
            if self.nivell == 3 and self.especial != "escombrada":    # la torreta segueix el jugador
                jx, jy = jugador.centre
                px, py = self.punt_cap(PUNTS_CAP[3]["torreta"])
                d = (math.atan2(jy - py, jx - px) - self.angle_torreta + math.pi) % math.tau - math.pi
                self.angle_torreta += d * 0.1
            if self.especial:
                return self._especial_cap(jugador, altres)

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
        if self.hd_e:
            p = punt_hd(self.tipus, "boques", "apunta", 0, 1 if self.dir > 0 else -1)
            if p:
                return self.x + self.w / 2 + p[0], self.y + self.h + p[1]
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
        if self.hd_e:
            self._dibuixar_terra_hd(surf, desplaçament, forçar_flash)
            return
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
        if self.tipus == "boss" and self.hd_cap:
            torn = self.atacs % 3
            if torn == 0:                                  # l'atac propi de cada cap (amb avís)
                self.especial, self.t_especial = ESPECIAL_CAP[self.nivell], 0
                return []
            if self.nivell == 0 and torn == 2:             # General: els dos canons laterals
                bales = []
                for p in PUNTS_CAP[0]["canons"]:
                    x, y = self.punt_cap(p)
                    bales += ventall(x, y, math.atan2(jy - y, jx - x), 1, 0, v * 1.15, d, "boss")
                return bales
            if self.nivell >= 2 and torn == 2:
                return anell_bales(cx, cy, 12, v * 0.8, d, "boss", gir=self.atacs * 0.3)
            if self.nivell >= 1 and torn == 1:
                return ventall(cx, cy, angle, 5, math.radians(60), v, d, "boss")
            return ventall(cx, cy, angle, 3, math.radians(24), v * 1.1, d, "boss")
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
        if self.hd_nau:
            W, H = FINALS_HD["nau"]["llenç"]
            cx, cy = self.centre
            return [(cx - W / 2 + x + (x - W / 2) * 0.06, cy - H / 2 + y + 14) for x, y in FINALS_HD["nau"]["canons"]]
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
        if self.hd:
            return compondre_comandant(self.estat_dibuix(), self.llenç), None
        if self.hd_nau:
            return SPR_ENEMIC["final_nau"], "nau_hd"
        if self.hd_nucli:
            return SPR_ENEMIC["final_nucli"], "nucli_hd"
        if self.hd_cap:
            fr = CAPS_HD[self.nivell]
            anim, t = "repos", int(self.t * 20)
            esp, te = self.especial, self.t_especial
            if esp == "escotilla" and te < 56:
                anim, k = "escotilla", (0 if te < 16 else 1)
            elif esp == "beines" and te < 30:
                anim, k = "plenes", 0
            elif esp == "punteria":
                anim, k = "apunta", (t // 3) % 2
            elif self.nivell == 4:                         # ales que baten (més de pressa amb l'eixam)
                k = (t // (2 if esp == "eixam" else 4)) % 4
            else:
                k = (t // (4 if self.nivell == 2 else 10)) % 2
            frames = fr[anim]
            k %= len(frames)
            return frames[k], ("cap", self.nivell, anim, k)
        if self.hd_e:
            if self.tipus in VOLADORS_HD:
                fr = ENEMICS_HD[self.tipus]["sencers"]
                k = (int(self.t * 20) // {"dron": 6, "lloctinent": 7}.get(self.tipus, 3)) % len(fr)
                return fr[k], (self.tipus, k)
            anim, k = self.anim_terra()
            return frame_hd(self.tipus, anim, k, 1 if self.dir > 0 else -1)[0], None
        return self.sprite, self.clau

    def dibuixar(self, surf, desplaçament=(0, 0), forçar_flash=False):
        rx, ry = getattr(self, "recul", (0.0, 0.0))
        if rx or ry:
            desplaçament = (desplaçament[0] + round(rx), desplaçament[1] + round(ry))
            self.recul = (rx * 0.6, ry * 0.6) if abs(rx) + abs(ry) > 0.3 else (0.0, 0.0)
        if self.terrestre:
            self._dibuixar_terra(surf, desplaçament, forçar_flash)
            return
        if self.hd:
            self._dibuixar_comandant(surf, desplaçament, forçar_flash)
            return
        if self.hd_nau:
            self._dibuixar_nau_hd(surf, desplaçament, forçar_flash)
            return
        if self.hd_nucli:
            self._dibuixar_nucli_hd(surf, desplaçament, forçar_flash)
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
        surf.blit(img, rect)
        if self.hd_cap:
            self._extres_cap(surf, rect)
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
        rs = FINALS_HD["nucli"]["radi_ull"] if escala is None else 22 * 1.9 * escala
        ix, iy = cx + self.mirada[0] * rs * 0.32, cy + self.mirada[1] * rs * 0.32
        ira = self.fase == 2 and self.temps_fase < 60
        color_iris = (255, 60, 90) if ira or self.furia else (170, 50, 210)
        pygame.draw.circle(surf, tuple(c // 2 for c in color_iris), (int(ix), int(iy)), int(rs * 0.5))
        pygame.draw.circle(surf, color_iris, (int(ix), int(iy)), int(rs * 0.42))
        pygame.draw.circle(surf, (250, 160, 255), (int(ix), int(iy)), int(rs * 0.42), 2)
        amp_pupil = rs * (0.12 if not ira else 0.06)
        pygame.draw.ellipse(surf, (20, 0, 20), (ix - amp_pupil, iy - rs * 0.32, amp_pupil * 2, rs * 0.64))
        pygame.draw.circle(surf, BLANC, (int(ix - rs * 0.15), int(iy - rs * 0.16)), max(2, int(rs * 0.07)))
        if self.parpelleig and escala is not None:             # (en alta definició, les parpelles són una capa)
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

    def _iniciar_comandant(self):
        """Comandant Suprem en alta definició: estat de les accions i de les capes."""
        info = COMANDANT
        self.w, self.h = 150, 160
        x0, y0, x1, y1 = info["cos"]
        self.org = (self.w / 2 - (x0 + x1) / 2, self.h / 2 - (y0 + y1) / 2)   # on cau el llenç respecte de (x, y)
        self.llenç = pygame.Surface(info["llenç"], pygame.SRCALPHA)
        im, (_, oy) = info["peces"]["tent_estesos"]
        self.peus_cop = oy + im.get_height()           # punta dels tentacles estesos, en coordenades del llenç
        self.accio, self.t_accio = None, 0
        self.seq = 0
        self.costat_garra = -1
        self.trencat = False                           # fase 2: la closca ja s'ha trencat
        self.banya_rota = False
        self.objectiu_x = 0.0
        self.t_terra = 0                               # fotograma en què el cop ha tocat terra
        self.avis_laser = None
        self.laser_x = (0.0, 0.0)
        self.parlant = False
        self.cadencia = int(80 * self.k_cadencia)
        self.y = float(-self.h - 30)                   # entra des de just a sobre de la pantalla

    def punt_llenç(self, p):
        """Punt del llenç del Comandant -> coordenades de la pantalla."""
        return self.x + self.org[0] + p[0], self.y + self.org[1] + p[1]

    def _actualitzar_comandant(self, jugador, altres, efectes, plataformes):
        """Comandant Suprem: flota i encadena atacs amb avís (garra, anell, cop de terra, crida mental i,
        a la fase 2, el làser dels ulls). Cada atac té la seva postura."""
        if self.furia and not self.trencat:            # mitja vida: la closca es trenca
            self.trencat = True
            self.accio, self.t_accio = "trencar", 0
            self.laser = self.avis_laser = None
            self.t_terra = 0
            self._esmicolar(efectes)
        if self.vida < self.vida_max * 0.25 and not self.banya_rota:
            self.banya_rota = True
            self._saltar_banya(efectes)
        self.t_accio += 1
        if self.accio is None:
            self._vagar(jugador, altres)
            self.temps_atac += 1
            if self.temps_atac >= self.cadencia:
                self._triar_atac(jugador, altres)
            return []
        if self.accio not in ("cop", "laser"):         # mentre carrega, gairebé quiet
            self.vx *= 0.9
            self.vy *= 0.9
            self.x += self.vx
            self.y += self.vy + math.sin(self.t * 2) * 0.3
            self._limits()
        return getattr(self, "_accio_" + self.accio)(jugador, efectes, plataformes)

    SEQ_COMANDANT = (("garra", "anell", "garra", "cop", "crida"),
                     ("garra", "laser", "anell", "cop", "garra", "crida", "laser"))

    def _triar_atac(self, jugador, altres):
        seq = self.SEQ_COMANDANT[1 if self.trencat else 0]
        accio = seq[self.seq % len(seq)]
        self.seq += 1
        if accio == "crida" and sum(1 for o in altres if not o.es_boss) >= 3:
            accio = "anell"
        self.accio, self.t_accio = accio, 0
        self.atacs += 1
        self.costat_garra = -1 if jugador.centre[0] < self.centre[0] else 1

    def _acabar_accio(self, pausa=0):
        self.accio, self.t_accio = None, 0
        self.temps_atac = -pausa
        self.cadencia = int((60 if self.trencat else 80) * self.k_cadencia)

    def _accio_garra(self, jugador, efectes, plataformes):
        """Ràfega des de la urpa: alça el braç (la urpa s'encén) i dispara cap al jugador."""
        if self.t_accio == 30:
            x, y = self.punt_llenç(COMANDANT["urpes"]["mig"][str(self.costat_garra)])
            jx, jy = jugador.centre
            self.flash_cano = 8
            AUDIO.so("boss", 60)
            efectes.append(Anell(x, y, ROSA, r=4, creix=2.5, vida=10))
            return ventall(x, y, math.atan2(jy - y, jx - x), 5 if self.trencat else 3, math.radians(30),
                           self.vel_bala * 1.4, self.dany, "final")
        if self.t_accio >= 46:
            self._acabar_accio()
        return []

    def _accio_anell(self, jugador, efectes, plataformes):
        """Anell de bales que surt de l'òrgan del pit (abans s'encén)."""
        if self.t_accio == 32:
            x, y = self.punt_llenç(COMANDANT["organ"])
            AUDIO.so("boss", 60)
            efectes.append(Anell(x, y, ROSA, r=10, creix=4, vida=14))
            return anell_bales(x, y, 30 if self.trencat else 24, self.vel_bala, self.dany, "final", gir=self.atacs * 0.13)
        if self.t_accio >= 44:
            self._acabar_accio()
        return []

    def _accio_crida(self, jugador, efectes, plataformes):
        """Crida mental: alça els braços, el cervell s'encén i arriben soldats."""
        t = self.t_accio
        if t in (18, 30, 42, 54):
            x, y = self.punt_llenç(COMANDANT["cap"])
            efectes.append(Anell(x, y - 8, (255, 90, 210), r=34, creix=5, vida=22))
        if t == 18:
            AUDIO.so("boss")
        if t == 40:
            self.invocacions = [("soldat", 70), ("soldat", 70)] + ([("kamikaze", 45)] if self.trencat else [])
        if t >= 78:
            self._acabar_accio(20)
        return []

    def _accio_cop(self, jugador, efectes, plataformes):
        """Cop de terra: s'enlaira (una ombra marca on caurà), cau en picat i fa ones que s'han de saltar."""
        t = self.t_accio
        if self.t_terra == 0:
            if t <= 36:                                # s'enlaira i apunta (deixa d'apuntar una mica abans)
                if t <= 26:
                    self.objectiu_x = max(self.w / 2 + 10, min(WIDTH - self.w / 2 - 10, jugador.centre[0]))
                self.x += (self.objectiu_x - self.w / 2 - self.x) * 0.12
                self.y += (50 - self.y) * 0.1
                self.vy = 0.0
                if t == 1:
                    AUDIO.so("buit", 120)
                return []
            self.vy = min(self.vy + 1.4, 22)           # en picat
            self.y += self.vy
            terra = TERRA_Y + 6 - self.peus_cop - self.org[1]
            if self.y >= terra:
                self.y = terra
                self.t_terra = t
                self.impacte = True
                self.tremolor_nou = 16
                AUDIO.so("explosio")
                cx = self.centre[0]
                self.ones_noves = [(cx - 40, -1), (cx + 40, 1)]
                for _ in range(30):
                    efectes.append(Particula(cx + random.uniform(-100, 100), TERRA_Y - 2, random.uniform(-3, 3),
                                             random.uniform(-4.5, -1),
                                             random.choice(((236, 240, 250), (200, 206, 220), (255, 140, 220))),
                                             vida=random.randint(20, 40), mida=random.uniform(3, 6), gravetat=0.2))
                efectes.append(Anell(cx, TERRA_Y, (255, 120, 220), r=20, creix=7, vida=16))
            return []
        quiet = t - self.t_terra
        if self.trencat and quiet == 18:               # a la fase 2, una segona ona
            cx = self.centre[0]
            self.ones_noves = [(cx - 40, -1), (cx + 40, 1)]
            self.tremolor_nou = 8
            AUDIO.so("impacte")
        if quiet > 42:                                 # torna a enlairar-se
            self.y += (self.y_destinacio - self.y) * 0.08
            if quiet > 90 or abs(self.y - self.y_destinacio) < 3:
                self.t_terra = 0
                self._acabar_accio(30)
        return []

    def ulls_mon(self):
        """Posició dels dos ulls grans a la pantalla."""
        return [self.punt_llenç(p) for p in COMANDANT["ulls"]]

    def _raig(self, xt, plataformes):
        """Raig dels ulls fins a terra o fins a la primera plataforma que el talli."""
        (ax, ay), (bx, by) = self.ulls_mon()
        ox, oy = (ax + bx) / 2, (ay + by) / 2
        fi_x, fi_y = xt, float(TERRA_Y)
        for p in plataformes:
            if p.terra or p.rect.top <= oy + 8:
                continue
            k = (p.rect.top - oy) / (TERRA_Y - oy)
            x = ox + (xt - ox) * k
            if p.rect.left <= x <= p.rect.right and p.rect.top < fi_y:
                fi_x, fi_y = x, float(p.rect.top)
        return (ox, oy), (fi_x, fi_y)

    def _accio_laser(self, jugador, efectes, plataformes):
        """Làser dels ulls (fase 2): primer una línia d'avís; després el raig escombra l'escenari."""
        t = self.t_accio
        avis, durada = 50, 84
        if t == 1:
            x0 = 36 if jugador.centre[0] < WIDTH / 2 else WIDTH - 36
            self.laser_x = (x0, WIDTH - x0)
            AUDIO.so("buit", 120)
        x0, x1 = self.laser_x
        if t < avis:
            self.avis_laser = (x0, t / avis)
        elif t < avis + durada:
            self.avis_laser = None
            k = (t - avis) / durada
            k = k * k * (3 - 2 * k)
            self.laser = self._raig(x0 + (x1 - x0) * k, plataformes)
            if t == avis:
                AUDIO.so("explosio", 80)
            if t % 2 == 0:
                ix, iy = self.laser[1]
                efectes.append(Particula(ix + random.uniform(-4, 4), iy - 2, random.uniform(-2.5, 2.5),
                                         random.uniform(-4, -1.5),
                                         random.choice(((255, 120, 90), (255, 230, 170), (255, 70, 130))),
                                         vida=random.randint(10, 22), mida=random.uniform(2, 4), gravetat=0.25))
        else:
            self.laser = None
            if t >= avis + durada + 18:
                self._acabar_accio(20)
        return []

    def _accio_trencar(self, jugador, efectes, plataformes):
        """La closca es trenca (mitja vida): rugit, trossos que salten i el nucli a la vista."""
        if self.t_accio == 1:
            self.tremolor_nou = 14
            AUDIO.so("explosio")
        if self.t_accio >= 58:
            self._acabar_accio(10)
        return []

    def _esmicolar(self, efectes):
        """Trossos de la closca que salten quan es trenca."""
        for k in range(10):
            px, py = random.choice(((96, 136), (104, 128), (170, 106), (178, 116), (120, 138), (92, 146)))
            x, y = self.punt_llenç((px + random.uniform(-6, 6), py + random.uniform(-6, 6)))
            img = COMANDANT["peces"][f"tros_{k % 4}"][0]
            efectes.append(TrosClosca(img, x, y, random.uniform(-4.5, 4.5), random.uniform(-7, -2.5)))
        x, y = self.punt_llenç(COMANDANT["organ"])
        esclat(efectes, x, y, 40, [ROSA, BLANC, (255, 140, 220), MORAT], vel=(2, 8), mida=(2, 5), vida=(15, 40))
        efectes.append(Anell(x, y, ROSA, r=12, creix=6, vida=18))
        efectes.append(Anell(x, y, BLANC, r=8, creix=4, vida=12))

    def _saltar_banya(self, efectes):
        """Al 25% de vida li salta una banya."""
        cx, cy = COMANDANT["cap"]
        x, y = self.punt_llenç((cx - 30, cy - 52))
        efectes.append(TrosClosca(COMANDANT["peces"]["tros_1"][0], x, y, -2.5, -6))
        esclat(efectes, x, y, 18, [(232, 218, 182), BLANC, (150, 124, 96)], vel=(1.5, 5), mida=(2, 4), vida=(12, 28))
        self.tremolor_nou = 8
        AUDIO.so("impacte")

    def estat_dibuix(self):
        """Postures i expressió del Comandant segons el que fa."""
        a, t = self.accio, self.t_accio
        anim = int(self.t * 20)
        e = estat_comandant(anim, mirada=self.mirada, ira=self.trencat,
                            cos=(2 if self.trencat else 1,
                                 1 if (self.vida < self.vida_max * (0.25 if self.trencat else 0.75)) else 0),
                            banya_trencada=self.banya_rota,
                            tent_dx=max(-3, min(3, round(-self.vx * 2))), cap_dx=max(-2, min(2, round(self.vx))))
        if self.parpelleig and a in (None, "anell"):
            e["parpelles"] = "tancats" if 4 < self.parpelleig <= 10 else "mig"
        if self.morint:
            e.update(tentacles="flonjos", boca="oberta", mort=self.morint > 50, braços=("repos", "repos"),
                     tent_dx=0, cap_dx=random.randint(-1, 1))
            return e
        costat = 0 if self.costat_garra < 0 else 1
        if a is None and self.parlant:
            e["boca"] = ("mitja", "tancada", "oberta", "tancada")[(anim // 5) % 4]
        if a == "garra":
            braços = ["repos", "repos"]
            braços[costat] = "mig" if 6 < t < 42 else "repos"
            e.update(braços=tuple(braços), boca="mitja" if 10 < t < 36 else "tancada")
        elif a == "anell":
            e.update(braços=("mig", "mig") if 8 < t < 38 else ("repos", "repos"))
        elif a == "crida":
            if t < 14 or t >= 66:
                e.update(braços=("mig", "mig"), boca="mitja")
            else:
                e.update(braços=("alçat", "alçat"), boca="oberta", venes="tot",
                         cervell=255 * min(1.0, (t - 14) / 10, (66 - t) / 8))
        elif a == "cop":
            if self.t_terra == 0:
                e.update(braços=("cop", "cop"), tentacles="recollits", boca="mitja")
            else:
                quiet = t - self.t_terra
                if quiet < 34:
                    e.update(braços=("terra", "terra"), tentacles="estesos", boca="oberta" if quiet < 16 else "mitja")
                else:
                    e.update(braços=("mig", "mig") if quiet < 50 else ("repos", "repos"))
        elif a == "laser":
            e.update(boca="mitja", parpelles="oberts")
            if self.laser:
                (ox, oy), (ix, iy) = self.laser
                d = math.hypot(ix - ox, iy - oy) or 1
                e["mirada"] = ((ix - ox) / d, (iy - oy) / d)
            elif self.avis_laser:
                ox, oy = self.punt_llenç(COMANDANT["cap"])
                d = math.hypot(self.avis_laser[0] - ox, TERRA_Y - oy) or 1
                e["mirada"] = ((self.avis_laser[0] - ox) / d, (TERRA_Y - oy) / d)
        elif a == "trencar":
            e.update(braços=("mig", "mig"), boca="oberta", venes="tot", cervell=255 * max(0.0, 1 - t / 58),
                     cap_dx=random.randint(-1, 1))
        elif a == "rugit":                             # presentació: alça els braços i rugeix
            if t < 8 or t >= 52:
                e.update(braços=("mig", "mig"), boca="mitja")
            else:
                e.update(braços=("alçat", "alçat"), boca="oberta", venes="tot", cervell=255 * min(1.0, (t - 8) / 8),
                         cap_dx=random.randint(-1, 1) if 12 < t < 40 else 0)
        return e

    def _dibuixar_comandant(self, surf, desp, forçar_flash):
        info = COMANDANT
        a, t = self.accio, self.t_accio
        img = compondre_comandant(self.estat_dibuix(), self.llenç)
        ox = int(self.x + self.org[0] + desp[0])
        oy = int(self.y + self.org[1] + desp[1])
        if a == "trencar" and t < 24:
            ox += random.randint(-2, 2)
        if a == "cop" and self.t_terra == 0:          # ombra que marca on caurà
            k = min(1.0, t / 30)
            amp = int(40 + 50 * k)
            marca = pygame.Surface((amp * 2, 16), pygame.SRCALPHA)
            pygame.draw.ellipse(marca, (20, 0, 20, int(60 + 80 * k)), marca.get_rect())
            pygame.draw.ellipse(marca, (255, 60, 120, 230 if (t // 4) % 2 else 110), marca.get_rect(), 2)
            surf.blit(marca, marca.get_rect(center=(int(self.objectiu_x), TERRA_Y + 1)))
        org = info["organ"]
        if self.trencat and not self.morint:           # aura de la fase 2
            aura = llum(110, (255, 40, 90))
            aura.set_alpha(int(80 + 40 * math.sin(self.t * 6)))
            surf.blit(aura, aura.get_rect(center=(ox + org[0], oy + org[1] - 34)))
            aura.set_alpha(255)
        surf.blit(img, (ox, oy))
        if self.flash >= 4 or forçar_flash:            # un parpelleig curt a cada cop: no tapa el detall
            blanc = silueta_blanca(img)
            blanc.set_alpha(200 if forçar_flash else 70)
            surf.blit(blanc, (ox, oy))
        if self.morint:
            return
        resp = round(math.sin(int(self.t * 20) * math.tau / 120))
        # l'òrgan batega (i s'encén abans de l'anell)
        intens = 0.0
        if a == "anell":
            intens = min(1.0, t / 32) if t <= 32 else max(0.0, 1 - (t - 32) / 10)
        elif a in ("crida", "trencar", "rugit"):
            intens = 0.8
        r = int(14 + 3 * math.sin(self.t * 5) + 24 * intens)
        l = llum(r, (255, 80, 200))
        l.set_alpha(int(140 + 110 * intens))
        centre = (ox + org[0], oy + org[1] + resp)
        surf.blit(l, l.get_rect(center=centre))
        l.set_alpha(255)
        if a == "anell" and t <= 32:
            pygame.draw.circle(surf, ROSA, centre, int(12 + 30 * (1 - intens)), 1)
        # urpes que carreguen
        urpes = []
        if a == "garra" and 6 < t <= 32:
            urpes = [(info["urpes"]["mig"][str(self.costat_garra)], min(1.0, (t - 6) / 24))]
        elif (a == "crida" and 14 <= t < 66) or (a == "rugit" and 8 <= t < 52):
            urpes = [(info["urpes"]["alçat"][s], 0.8) for s in ("-1", "1")]
        for (x, y), k in urpes:
            g = llum(int(6 + 14 * k), (255, 90, 210))
            surf.blit(g, g.get_rect(center=(ox + x, oy + y + resp)))
            if a == "garra":
                pygame.draw.circle(surf, ROSA, (ox + x, oy + y + resp), int(4 + 18 * (1 - k)), 1)
        # làser: els ulls s'encenen, línia d'avís i raig
        if a == "laser":
            k = min(1.0, t / 50)
            for x, y in self.ulls_mon():
                g = llum(int(5 + 12 * k), (255, 60, 60))
                surf.blit(g, g.get_rect(center=(int(x + desp[0]), int(y + desp[1]))))
            if self.avis_laser and (t // 3) % 2 == 0:
                (ax, ay), (bx, by) = self.ulls_mon()
                pygame.draw.line(surf, (255, 70, 70), ((ax + bx) / 2, (ay + by) / 2), (self.avis_laser[0], TERRA_Y), 1)
                pygame.draw.circle(surf, (255, 70, 70), (int(self.avis_laser[0]), TERRA_Y), 6, 1)
            if self.laser:
                (_, _), (ix, iy) = self.laser
                vibra = random.randint(-1, 1)
                for ux, uy in self.ulls_mon():
                    pygame.draw.line(surf, (150, 10, 50), (ux, uy), (ix, iy), 7 + vibra)
                    pygame.draw.line(surf, (255, 60, 100), (ux, uy), (ix, iy), 4 + vibra)
                    pygame.draw.line(surf, (255, 230, 235), (ux, uy), (ix, iy), 2)
                g = llum(22, (255, 70, 110))
                surf.blit(g, g.get_rect(center=(int(ix), int(iy))))
                pygame.draw.circle(surf, BLANC, (int(ix), int(iy)), 4)

    def presentar(self, t, jugador):
        """Durant la presentació del cap: respira, mira el jugador i rugeix quan surt el nom."""
        self.t += 0.05
        self.parpelleig = max(0, self.parpelleig - 1)
        jx, jy = jugador.centre
        cx, cy = self.centre
        d = math.hypot(jx - cx, jy - cy) or 1
        self.mirada = ((jx - cx) / d, (jy - cy) / d)
        if 100 <= t < 160:
            self.accio, self.t_accio = "rugit", t - 100
        elif self.accio == "rugit":
            self.accio, self.t_accio = None, 0

    def anim_terra(self):
        """Animació i fotograma dels enemics de terra en alta definició."""
        camina = int(self.pas_anim * 1.5) if abs(self.vx) > 0.1 and not self.entrant else 0
        if self.tipus == "kamikaze":
            if self.armat and (self.armat // (3 if self.armat < 20 else 6)) % 2 == 0:
                return "armat", 0
            return "corre", camina
        if self.flash > 2:
            return "ferit", 0
        if self.tipus == "soldat" and self.flash_cano:
            return "dispara", 0
        if self.apuntant or self.flash_cano:
            return "apunta", 0
        return "camina", camina

    def _dibuixar_terra_hd(self, surf, desp, forçar_flash):
        sentit = 1 if self.dir > 0 else -1
        anim, k = self.anim_terra()
        img, (dx, dy) = frame_hd(self.tipus, anim, k, sentit)
        ax, ay = self.x + self.w / 2 + desp[0], self.y + self.h + desp[1]
        pos = (int(ax + dx), int(ay + dy))
        if self.tipus == "kamikaze" and self.armat:
            l = llum(int(18 + 30 * (1 - self.armat / 45)), (255, 60, 40))
            surf.blit(l, l.get_rect(center=(int(ax), int(ay - 12))))
        surf.blit(img, pos)
        if self.flash or forçar_flash:
            blanc = silueta_blanca(img)
            blanc.set_alpha(200 if forçar_flash else 30 * self.flash)
            surf.blit(blanc, pos)
        if self.tipus == "escut" and not self.entrant:          # barrera hexagonal davant de l'emissor
            em = punt_hd("escut", "emissors", anim, k, sentit) or (sentit * 14, -34)
            alt = int(self.h * 1.08)
            barrera = imatge_escut(alt)
            if sentit < 0:
                barrera = pygame.transform.flip(barrera, True, False)
            br = 1.0 if self.cop_escut else min(1.0, 0.62 + 0.22 * math.sin(self.t * 9) + random.uniform(-0.06, 0.06))
            barrera.set_alpha(int(255 * br))
            bx = ax + em[0] + 1 if sentit > 0 else ax + em[0] - 1 - barrera.get_width()
            by = ay + em[1] - alt / 2
            surf.blit(barrera, (int(bx), int(by)))
            barrera.set_alpha(255)
            if self.cop_escut:                                    # esquerdes que s'encenen en aturar una bala
                for _ in range(2):
                    x0 = bx + random.uniform(4, 14)
                    y0 = by + random.uniform(6, alt - 6)
                    punts = [(x0, y0)]
                    for _ in range(3):
                        punts.append((punts[-1][0] + random.uniform(-4, 4), punts[-1][1] + random.uniform(-7, 7)))
                    pygame.draw.lines(surf, (230, 255, 255), False, punts, 1)
        carrega = self.carregant
        if carrega > 0 and self.tipus != "kamikaze":
            px, py = self.canó_terra()
            l = llum(int(5 + 12 * carrega), (120, 230, 255))
            surf.blit(l, l.get_rect(center=(int(px + desp[0]), int(py + desp[1]))))
        if self.vida < self.vida_max:
            pygame.draw.rect(surf, NEGRE, (self.x - 1, self.y - 9, self.w + 2, 6))
            pygame.draw.rect(surf, VERD, (self.x, self.y - 8, self.w * max(0, self.vida) / self.vida_max, 4))

    def punt_cap(self, p):
        """Punt del llenç d'un cap de sector -> pantalla (el llenç va centrat a la caixa)."""
        w, h = CAPS_HD[self.nivell]["repos"][0].get_size()
        cx, cy = self.centre
        return cx + p[0] - w / 2, cy + p[1] - h / 2

    def _fi_especial(self):
        self.especial, self.t_especial = None, 0
        self.mira = None
        self.temps_atac = 0

    def _especial_cap(self, jugador, altres):
        """Atac propi de cada cap de sector, amb avís. Torna les bales d'aquest fotograma."""
        self.t_especial += 1
        t = self.t_especial
        jx, jy = jugador.centre
        cx, cy = self.centre
        d = self.dany
        bales = []
        if self.especial == "escotilla":                   # General: obre l'escotilla i en surten drons
            if t == 36:
                lliures = 3 - sum(1 for o in altres if not o.es_boss)
                if lliures > 0:
                    self.invocacions = [("dron", 30)] * min(lliures, 2 if self.furia else 1)
                AUDIO.so("boss", 80)
            if t >= 64:
                self._fi_especial()
        elif self.especial == "beines":                    # Mestre: beines que cauen i esclaten en espores
            if t == 30:
                for p in PUNTS_CAP[1]["beines"]:
                    x, y = self.punt_cap(p)
                    bales.append(Bala(x, y, random.uniform(-1.4, 1.4) + (jx - x) * 0.004, -1.6, d, "beina", gravetat=0.16))
                AUDIO.so("boss", 70)
            if t >= 46:
                self._fi_especial()
        elif self.especial == "punteria":                  # Elit: mira làser i ràfega en línia recta
            if t <= 28:
                self.mira = (jx, jy)
            if 40 <= t < 64 and (t - 40) % 4 == 0:
                x, y = self.punt_cap(PUNTS_CAP[2]["sensor"])
                a = math.atan2(self.mira[1] - y, self.mira[0] - x)
                bales.append(Bala(x, y, math.cos(a) * 9.5, math.sin(a) * 9.5, d, "elit"))
                AUDIO.so("enemic", 70)
            if t >= 70:
                self._fi_especial()
        elif self.especial == "escombrada":                # Capità: la torreta escombra un arc de bales
            px, py = self.punt_cap(PUNTS_CAP[3]["torreta"])
            if t == 1:
                base = math.atan2(jy - py, jx - px)
                gir = 1 if random.random() < 0.5 else -1
                self.arc = (base - gir * 1.05, base + gir * 1.05)
            a0, a1 = self.arc
            if t < 24:                                     # gira cap a l'inici de l'arc (avís: la boca brilla)
                dd = (a0 - self.angle_torreta + math.pi) % math.tau - math.pi
                self.angle_torreta += dd * 0.2
            elif t < 84:
                self.angle_torreta = a0 + (a1 - a0) * (t - 24) / 60
                if t % 4 == 0:
                    a = self.angle_torreta
                    bales.append(Bala(px + math.cos(a) * 33, py + math.sin(a) * 33, math.cos(a) * self.vel_bala * 1.1,
                                      math.sin(a) * self.vel_bala * 1.1, d, "torreta"))
                    if t % 8 == 0:
                        AUDIO.so("enemic", 50)
            if t >= 96:
                self._fi_especial()
        elif self.especial == "eixam":                     # Guardià: eixam d'insectes que persegueixen
            if t == 30:
                x, y = self.punt_cap(PUNTS_CAP[4]["fibló"])
                n = 6 if self.furia else 4
                for k in range(n):
                    a = -math.pi / 2 + (k - (n - 1) / 2) * 0.55
                    bales.append(Bala(x, y, math.cos(a) * 3.2, math.sin(a) * 3.2, d, "eixam", vida=200))
                AUDIO.so("boss", 80)
            if t >= 46:
                self._fi_especial()
        return bales

    def _extres_cap(self, surf, rect):
        """Torreta del capità, mira làser de l'Elit i avisos dels atacs propis."""
        esp, t = self.especial, self.t_especial
        w, h = CAPS_HD[self.nivell]["repos"][0].get_size()
        ang = math.radians(self.angle)

        def punt(p):                                       # punt del llenç -> pantalla, amb la inclinació
            dx, dy = p[0] - w / 2, p[1] - h / 2
            return (rect.centerx + dx * math.cos(ang) + dy * math.sin(ang),
                    rect.centery - dx * math.sin(ang) + dy * math.cos(ang))
        if self.nivell == 3:
            px, py = punt(PUNTS_CAP[3]["torreta"])
            a = self.angle_torreta
            img = rotat(CAPS_HD[3]["torreta"][0], -math.degrees(a), ("torreta",))
            surf.blit(img, img.get_rect(center=(int(px + math.cos(a) * 6), int(py + math.sin(a) * 6))))
            if esp == "escombrada" and t < 24:
                l = llum(int(6 + t * 0.6), (110, 220, 255))
                surf.blit(l, l.get_rect(center=(int(px + math.cos(a) * 33), int(py + math.sin(a) * 33))))
        elif self.nivell == 2 and esp == "punteria" and self.mira and t < 40:
            if t < 28 or (t // 3) % 2 == 0:
                sx, sy = punt(PUNTS_CAP[2]["sensor"])
                pygame.draw.line(surf, (255, 40, 40), (sx, sy), self.mira, 1)
                pygame.draw.circle(surf, (255, 40, 40), (int(self.mira[0]), int(self.mira[1])), 8 if t < 28 else 5, 1)
        elif self.nivell == 1 and esp == "beines" and t < 30:
            for p in PUNTS_CAP[1]["beines"]:
                l = llum(int(8 + 8 * t / 30), (220, 240, 60))
                bx, by = punt(p)
                surf.blit(l, l.get_rect(center=(int(bx), int(by))))
        elif self.nivell == 0 and esp == "escotilla" and t < 40 and (t // 4) % 2 == 0:
            l = llum(14, (255, 220, 80))
            ex, ey = punt(PUNTS_CAP[0]["escotilla"])
            surf.blit(l, l.get_rect(center=(int(ex), int(ey))))
        elif self.nivell == 4 and esp == "eixam" and t < 30:
            l = llum(int(6 + t * 0.5), (240, 200, 60))
            fx, fy = punt(PUNTS_CAP[4]["fibló"])
            surf.blit(l, l.get_rect(center=(int(fx), int(fy))))

    def _dibuixar_nau_hd(self, surf, desp, forçar_flash):
        """Nau Mare: canons que surten abans de disparar, hangar que s'obre, anella de llums i cervell que brilla."""
        info = FINALS_HD["nau"]
        W, H = info["llenç"]
        cx, cy = self.centre
        ox, oy = int(cx - W / 2 + desp[0]), int(cy - H / 2 + desp[1])
        carrega = self.carregant
        seguent = (self.atacs + 1) % 4
        canons = int(self.flash_cano > 0 or (carrega > 0.25 and seguent == 1))
        hangar = int((carrega > 0.2 and seguent == 3) or (self.atacs % 4 == 3 and self.temps_atac < 30))
        pols = 0.5 + 0.5 * math.sin(self.t * 6)
        l = llum(int(30 + 10 * pols), (200, 120, 255))
        surf.blit(l, l.get_rect(center=(int(cx + desp[0]), int(cy + H * 0.36 + desp[1]))))
        img, (dx, dy) = peça_final(f"nau_{canons}{hangar}{int(self.furia)}")
        surf.blit(img, (ox + dx, oy + dy))
        if self.flash or forçar_flash:
            blanc = silueta_blanca(img)
            blanc.set_alpha(200 if forçar_flash else 18 * self.flash)
            surf.blit(blanc, (ox + dx, oy + dy))
        bx, by = info["cervell"]                                 # el cervell de la nau batega
        g = llum(int(20 + 6 * pols + 14 * carrega), (255, 90, 200))
        g.set_alpha(int(120 + 80 * pols))
        surf.blit(g, g.get_rect(center=(ox + bx, oy + by)))
        g.set_alpha(255)
        n = len(info["llums"])                                   # anella de llums que gira
        for i, (x, y) in enumerate(info["llums"]):
            if self.furia:
                encesa = (int(self.t * 20) // 6 + i) % 2 == 0
                color = (255, 70, 60) if encesa else (90, 30, 40)
            else:
                encesa = (int(self.t * 12) - i) % n < 4
                color = (255, 230, 120) if encesa else (110, 90, 60)
            pygame.draw.circle(surf, color, (ox + x, oy + y), 2)
            if encesa:
                surf.set_at((ox + x - 1, oy + y - 1), (255, 255, 230))
        if self.flash_cano:
            for px, py in self.canons_nau():
                g = llum(14, (255, 90, 120))
                surf.blit(g, g.get_rect(center=(int(px + desp[0]), int(py + desp[1]))))
        if carrega > 0:                                          # avís genèric de l'atac
            r = int(10 + 40 * carrega)
            g = llum(max(4, r), ROSA[:3])
            g.set_alpha(int(120 + 120 * carrega))
            surf.blit(g, g.get_rect(center=(int(cx + desp[0]), int(cy + desp[1]))))
            g.set_alpha(255)

    def _dibuixar_nucli_hd(self, surf, desp, forçar_flash):
        """Nucli: tentacles que ondulen, esquerdes segons la vida, ull que segueix el jugador, venes que s'encenen
        cap a l'ull abans d'atacar i parpelles de carn."""
        info = FINALS_HD["nucli"]
        W, H = info["llenç"]
        cx, cy = self.centre
        ox, oy = int(cx - W / 2 + desp[0]), int(cy - H / 2 + desp[1])
        anim = int(self.t * 20)
        fr = self.vida / self.vida_max
        dany = 0 if fr > 0.66 else (1 if fr > 0.33 else 2)
        peces = [f"nucli_tent_{(anim // 5) % info['n_tent']}", f"nucli_cos_{dany}"]
        compost = pygame.Surface((W, H), pygame.SRCALPHA) if self.flash or forçar_flash else None
        for nom in peces:
            im, (dx, dy) = peça_final(nom)
            surf.blit(im, (ox + dx, oy + dy))
            if compost:
                compost.blit(im, (dx, dy))
        ux, uy = info["ull"]
        self._dibuixar_ull(surf, (ox + ux, oy + uy), None)
        ira = self.fase == 2 and self.temps_fase < 60
        if ira or self.furia:                                    # venes: pols cap a l'ull (totes enceses abans de mirar)
            im, (dx, dy) = peça_final("nucli_venes_tot" if ira and (anim // 3) % 2 else f"nucli_venes_{(anim // 3) % 6}")
        else:
            im, (dx, dy) = peça_final(f"nucli_venes_{(anim // 5) % 6}")
        surf.blit(im, (ox + dx, oy + dy))
        if self.parpelleig:
            nom = "nucli_parp_tancat" if 4 < self.parpelleig <= 10 else "nucli_parp_mig"
            im, (dx, dy) = peça_final(nom)
            surf.blit(im, (ox + dx, oy + dy))
        if compost:
            blanc = silueta_blanca(compost)
            blanc.set_alpha(200 if forçar_flash else 18 * self.flash)
            surf.blit(blanc, (ox, oy))
        carrega = self.carregant
        if carrega > 0:                                          # la mirada: l'avís surt de la pupil·la
            punt = (int(ox + ux + self.mirada[0] * 14), int(oy + uy + self.mirada[1] * 14))
            r = int(10 + 40 * carrega)
            g = llum(max(4, r), (230, 90, 255))
            g.set_alpha(int(120 + 120 * carrega))
            surf.blit(g, g.get_rect(center=punt))
            g.set_alpha(255)
            pygame.draw.circle(surf, (230, 90, 255), punt, int(r * (1.6 - carrega)) + 2, 1)


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


class MortTerra:
    """Soldat abatut en alta definició: cau d'esquena, queda estès a terra i s'esvaeix."""

    def __init__(self, e):
        self.tipus = e.tipus
        self.sentit = 1 if e.dir > 0 else -1
        self.x, self.peus = e.x + e.w / 2, e.y + e.h
        self.vx = -self.sentit * 1.8                  # el cop l'empeny enrere
        self.vy = 0.0
        self.sup = None
        self.t = 0

    def actualitzar(self, joc):
        if self.sup is None:                          # on caurà (si s'ha mort a l'aire)
            self.sup = min((p.rect.top for p in joc.solides()
                            if p.rect.left - 4 <= self.x <= p.rect.right + 4 and p.rect.top >= self.peus - 6),
                           default=TERRA_Y)
        self.t += 1
        self.x += self.vx
        self.vx *= 0.86
        if self.peus < self.sup:
            self.vy += 0.6
            self.peus = min(self.sup, self.peus + self.vy)
        return self.t >= 120

    def dibuixar(self, surf):
        img, (dx, dy) = frame_hd(self.tipus, "mort", min(2, self.t // 6), self.sentit)
        if self.t > 90:
            img = img.copy()
            img.set_alpha(int(255 * (120 - self.t) / 30))
        pos = (int(self.x + dx), int(self.peus + dy))
        surf.blit(img, pos)
        if self.t < 6:
            blanc = silueta_blanca(img)
            blanc.set_alpha(150 - self.t * 25)
            surf.blit(blanc, pos)


class TrosClosca:
    """Tros de la closca del Comandant que salta, gira, rebota a terra i s'apaga."""
    __slots__ = ("img", "x", "y", "vx", "vy", "angle", "gir", "t", "vida")

    def __init__(self, img, x, y, vx, vy):
        self.img, self.x, self.y, self.vx, self.vy = img, x, y, vx, vy
        self.angle = random.uniform(0, 360)
        self.gir = random.choice((-1, 1)) * random.uniform(6, 14)
        self.t = 0
        self.vida = random.randint(70, 100)

    def actualitzar(self):
        self.t += 1
        self.vy += 0.35
        self.x += self.vx
        self.y += self.vy
        self.angle += self.gir
        if self.y > TERRA_Y - 4 and self.vy > 0:
            self.y = TERRA_Y - 4
            self.vy *= -0.35
            self.vx *= 0.6
            self.gir *= 0.5
        return self.t >= self.vida

    def dibuixar(self, surf):
        img = pygame.transform.rotate(self.img, int(self.angle) // 15 * 15)
        if self.t > self.vida - 20:
            img.set_alpha(int(255 * (self.vida - self.t) / 20))
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


class OnaXoc:
    """Ona del cop de terra del Comandant: corre arran de terra cap a un costat i s'ha de saltar."""
    ALT = 40
    ESTELES = {}

    def __init__(self, x, sentit, dany):
        self.x, self.sentit, self.dany = float(x), sentit, dany
        self.t = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 13, TERRA_Y - self.ALT + 10, 26, self.ALT - 10)

    def actualitzar(self, efectes):
        self.t += 1
        self.x += self.sentit * 6.2
        if self.t % 2 == 0:
            efectes.append(Particula(self.x - random.uniform(0, 14) * self.sentit, TERRA_Y - 3,
                                     -self.sentit * random.uniform(0.3, 1.8), random.uniform(-3.5, -1),
                                     random.choice(((236, 240, 250), (196, 204, 222), (255, 130, 215))),
                                     vida=random.randint(14, 26), mida=random.uniform(2.5, 4.5), gravetat=0.2))
        return self.x < -60 or self.x > WIDTH + 60

    @classmethod
    def estela(cls, sentit):
        """Rastre d'energia arran de terra (es fa un cop per a cada sentit)."""
        if sentit not in cls.ESTELES:
            e = pygame.Surface((80, 16), pygame.SRCALPHA)
            for i in range(80):
                k = i / 79
                alt = int(2 + 12 * k * k)
                pygame.draw.line(e, (255, 80, 200, int(170 * k)), (i, 16 - alt), (i, 15))
            cls.ESTELES[sentit] = e if sentit > 0 else pygame.transform.flip(e, True, False)
        return cls.ESTELES[sentit]

    def dibuixar(self, surf):
        x, s, T = self.x, self.sentit, TERRA_Y + 2
        a = self.ALT + 3 * math.sin(self.t * 0.7)
        e = self.estela(s)
        surf.blit(e, (x - 80 if s > 0 else x, T - 16))
        l = llum(32, (255, 70, 200))
        surf.blit(l, l.get_rect(center=(int(x), int(T - a * 0.45))))
        cresta = [(x - s * 22, T), (x - s * 12, T - a * 0.45), (x - s * 3, T - a * 0.86), (x + s * 6, T - a),
                  (x + s * 14, T - a * 0.84), (x + s * 13, T - a * 0.62), (x + s * 8, T - a * 0.68),
                  (x + s * 7, T - a * 0.4), (x + s * 13, T)]
        pygame.draw.polygon(surf, (120, 26, 104), cresta)
        dins = [(px - s * 2, py + (T - py) * 0.3) for px, py in cresta]
        pygame.draw.polygon(surf, (236, 80, 190), dins)
        pygame.draw.lines(surf, (255, 225, 248), False, [(px - s, py + 2) for px, py in cresta[1:5]], 2)
        pygame.draw.polygon(surf, (44, 8, 44), cresta, 1)
        for k in range(3):                              # escuma a la cresta
            fx = x + s * (8 + 3 * k) + random.randint(-1, 1)
            fy = T - a * (0.92 - 0.1 * k) + random.randint(-1, 1)
            surf.fill((255, 255, 255), (int(fx), int(fy), 2, 2))


class MortCap:
    """Seqüència de mort dels caps: explosions encadenades i una gran explosió final."""

    def __init__(self, enemic):
        self.e = enemic
        self.t = 0
        self.durada = 150 if enemic.es_final else 90

    def actualitzar(self, joc):
        self.t += 1
        e = self.e
        e.morint = self.t
        e.laser = None
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

    def parla(self, qui):
        """Cert mentre `qui` diu el missatge actual (encara surten lletres)."""
        a = self.actual
        return a is not None and a[0] == qui and 0 < a[2] and int(a[2] * 1.3) < len(T(a[1]))

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
        img = COMANDANT_MORT or SPR_ENEMIC.get("final_comandant")
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
            rect = gran.get_rect(center=(WIDTH // 2, int(y + 110)))
            surf.blit(gran, rect)
            if alfa > 200 and FINALS_HD:
                llums = FINALS_HD["nau"]["llums"]
                for i, (lx, ly) in enumerate(llums):                # l'anella de llums s'encén
                    encesa = (self.t // 4 - i) % len(llums) < 4
                    pygame.draw.circle(surf, (255, 230, 120) if encesa else (110, 90, 60),
                                       (rect.x + lx * 2, rect.y + ly * 2), 4)
            elif alfa > 200:
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
        nucli = NUCLI_CINE or SPR_ENEMIC.get("final_nucli")
        if nucli:
            gran = pygame.transform.scale(nucli, (nucli.get_width() * 2, nucli.get_height() * 2))
            centre = (WIDTH // 2, 230)
            surf.blit(gran, gran.get_rect(center=centre))
            rs = FINALS_HD["nucli"]["radi_ull"] * 2 if NUCLI_CINE else gran.get_width() * 0.29
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


def mostra_soldat(arma_id, uniforme="classic", aparenca="estandard", camo=None):
    """Imatge estàtica del soldat (botiga, passi, revelacions...)."""
    spr = sprites_jugador(arma_id, uniforme, aparenca, 0, camo)
    return spr.poses["quiet"][0][1] if spr else None


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
    """Placa d'identificació recolzada a terra o en una repisa (la base toca y + 10). És petita, fosca i
    gairebé del color de l'escenari: costa de veure. Només un brillantor molt de tant en tant la delata."""
    x, y = int(x), int(y)
    pygame.draw.ellipse(surf, (14, 14, 20), (x - 6, y + 8, 12, 3))                       # ombra
    pygame.draw.lines(surf, (74, 76, 84), False, [(x - 5, y + 9), (x - 2, y + 6), (x + 1, y + 9),
                                                  (x + 4, y + 7), (x + 6, y + 9)], 1)       # cadeneta caiguda
    cos = pygame.Rect(x - 3, y - 1, 7, 10)                                              # placa petita i fosca
    pygame.draw.rect(surf, (96, 98, 106), cos, border_radius=2)
    pygame.draw.rect(surf, (58, 60, 68), cos, 1, border_radius=2)
    pygame.draw.line(surf, (70, 72, 80), (x - 1, y + 3), (x + 2, y + 3))
    if t % 360 < 8:                                    # brillantor fugaç, cada sis segons
        k = 1 - abs(t % 360 - 4) / 4
        pygame.draw.line(surf, (230, 232, 240), (x - 4 * k, y + 2), (x + 4 * k, y + 2))
        pygame.draw.line(surf, (230, 232, 240), (x, y + 2 - 4 * k), (x, y + 2 + 4 * k))


def panell(surf, rect, vora=BLAU_CLAR, alfa=215):
    capa = pygame.Surface(rect.size, pygame.SRCALPHA)
    capa.fill((10, 12, 28, alfa))
    surf.blit(capa, rect)
    pygame.draw.rect(surf, vora, rect, 2, border_radius=8)



# ---------------------------------------------------------------------------
# Contingut desbloquejable (v3.5): cosmètics, rangs, drons, efectes d'eliminació, targetes
# ---------------------------------------------------------------------------
PREFIX_COSMETIC = {"uniforme": "u:", "arma": "a:", "titol": "t:", "estela": "e:", "efecte": "k:", "mira": "m:",
                   "tema": "h:", "targeta": "c:", "dron": "d:"}
CATALEG_COSMETIC = {"uniforme": UNIFORMES, "arma": APARENCES_ARMA, "titol": TITOLS, "estela": ESTELES,
                    "efecte": EFECTES_BAIXA, "mira": MIRES, "tema": TEMES_HUD, "targeta": TARGETES, "dron": DRONS}
COSMETICS_INICIALS = {"u:classic", "a:estandard", "t:recluta", "e:normal", "k:normal", "m:blanc", "h:classic",
                      "c:estels", "d:cap"}
ACUM_PASSI = [xp_acumulada_passi(n) for n in range(len(PASSI) + 1)]


def nom_cosmetic(tipus, valor):
    d = CATALEG_COSMETIC[tipus][valor]
    return T(d if isinstance(d, str) else d["nom"])


def nom_premi(tipus, valor):
    """Nom d'una recompensa (Battle Pass, rangs, desafiaments) en l'idioma actual."""
    if tipus == "monedes":
        return T("{n} monedas").format(n=valor)
    etiqueta = {"uniforme": "Uniforme", "arma": "Aspecto de arma", "titol": "Título", "estela": "Estela",
                "efecte": "Eliminación", "mira": "Punto de mira", "tema": "HUD", "targeta": "Tarjeta", "dron": "Dron"}[tipus]
    return f"{T(etiqueta)}: {nom_cosmetic(tipus, valor)}"


def color_arc(t, s=70):
    c = pygame.Color(0)
    c.hsva = ((t * 6) % 360, s, 100, 100)
    return (c.r, c.g, c.b)


def color_mira(ident, t):
    c = MIRES.get(ident, MIRES["blanc"])["color"]
    return color_arc(t, 55) if c == "arc" else c


def colors_estela(ident, t):
    c = ESTELES.get(ident, ESTELES["normal"])["colors"]
    return [color_arc(t + k * 20) for k in range(3)] if c == "arc" else c


# --- insígnies de rang -------------------------------------------------------------
def dibuixar_insignia(surf, cx, cy, idx, mida=30):
    """Insígnia militar del rang `idx` (0-14) dins d'un escut."""
    m = mida
    tiers = [(90, 96, 110), (70, 110, 70), (70, 110, 70), (70, 110, 70), (60, 90, 150), (60, 90, 150), (60, 90, 150),
             (130, 80, 160), (130, 80, 160), (130, 80, 160), (170, 70, 60), (170, 70, 60), (40, 40, 52), (40, 40, 52),
             (30, 26, 60)]
    fons = tiers[max(0, min(14, idx))]
    escut = [(cx - m // 2, cy - m // 2), (cx + m // 2, cy - m // 2), (cx + m // 2, cy + m // 6), (cx, cy + m // 2 + 4),
             (cx - m // 2, cy + m // 6)]
    pygame.draw.polygon(surf, NEGRE, [(x, y + 2) for x, y in escut])
    pygame.draw.polygon(surf, fons, escut)
    or_ = (255, 210, 70) if idx < 12 else (255, 230, 120)
    pygame.draw.polygon(surf, or_ if idx >= 7 else (200, 205, 220), escut, 2)
    def galó(y, ample=m * 0.32):
        pygame.draw.lines(surf, or_, False, [(cx - ample, y - ample * 0.5), (cx, y), (cx + ample, y - ample * 0.5)], 3)
    def estrella(x, y, r):
        dibuixar_estrella(surf, int(x), int(y), r, True, or_)
    if idx == 0:
        pygame.draw.line(surf, (200, 205, 220), (cx - m * 0.25, cy), (cx + m * 0.25, cy), 3)
    elif idx <= 3:                                       # galons
        for k in range(idx):
            galó(cy - m * 0.08 + k * m * 0.18)
    elif idx <= 6:                                       # galons i arcs
        for k in range(3):
            galó(cy - m * 0.2 + k * m * 0.14, m * 0.28)
        for k in range(idx - 3):
            y = cy + m * 0.26 + k * 4
            pygame.draw.arc(surf, or_, (cx - m * 0.28, y - 6, m * 0.56, 10), math.pi, math.tau, 2)
    elif idx <= 9:                                       # barres
        n = idx - 6
        for k in range(n):
            y = cy - (n - 1) * 5 + k * 10
            pygame.draw.rect(surf, or_, (cx - m * 0.26, y - 2, m * 0.52, 5))
    elif idx <= 11:                                      # estrelles de vuit puntes
        n = idx - 9
        for k in range(n):
            x = cx + (k - (n - 1) / 2) * m * 0.36
            estrella(x, cy, max(4, m // 5))
    else:                                                # generals: estrelles daurades
        n = idx - 11
        for k in range(n):
            x = cx + (k - (n - 1) / 2) * m * 0.3
            estrella(x, cy - 1, max(4, m // 6))
        if idx == 14:
            pygame.draw.circle(surf, or_, (cx, cy), int(m * 0.46), 1)


# --- drons ----------------------------------------------------------------------------
_CACHE_DRONS = {}


def _carregar_teddy():
    """Teddy Bear (vegeu tools/generar_teddy.py): postura -> (imatge, desplaçament des del punt dels peus)."""
    try:
        with open(ruta("img", "teddy.json"), encoding="utf-8") as fitxer:
            info = json.load(fitxer)
    except (OSError, ValueError) as err:
        print(f"No s'ha pogut carregar teddy.json: {err}")
        return {}
    atles = carregar_imatge("teddy.png")
    if atles is None:
        return {}
    ax, ay = info["ancora"]
    return {n: (atles.subsurface((x, y, w, h)), (ox - ax, oy - ay)) for n, (x, y, w, h, ox, oy) in info["imatges"].items()}


TEDDY = _carregar_teddy()
ROSA_TEDDY = (255, 150, 210)
CURA_TEDDY, CADA_CURA_TEDDY = 5, 480                # +5 de vida cada 8 s mentre el soldat està ferit
SALT_TEDDY = (-4, -9, -13, -16, -18, -19, -19, -18, -16, -13, -10, -6, -3, 0)   # alçada del saltiró (píxels del dibuix)
_CACHE_TEDDY = {}


def imatge_teddy(nom, esc=1):
    """(imatge, desplaçament) d'una postura del Teddy ampliada `esc` vegades sense suavitzar."""
    if nom not in TEDDY:
        return None, (0, 0)
    img, (dx, dy) = TEDDY[nom]
    if esc == 1:
        return img, (dx, dy)
    s = _CACHE_TEDDY.get((nom, esc))
    if s is None:
        s = _CACHE_TEDDY[(nom, esc)] = pygame.transform.scale(img, (img.get_width() * esc, img.get_height() * esc))
    return s, (dx * esc, dy * esc)


def posar_teddy(surf, nom, x, peus, esc=1):
    """Dibuixa el Teddy amb els peus al punt (x, peus)."""
    img, (dx, dy) = imatge_teddy(nom, esc)
    if img is not None:
        surf.blit(img, (round(x + dx), round(peus + dy)))


def cor_teddy(mida, color=None):
    """Cor rosa del Teddy (7x6 píxels) ampliat `mida` vegades; amb `color`, la silueta plana d'aquest color."""
    clau = ("cor", mida, color)
    s = _CACHE_TEDDY.get(clau)
    if s is None and "cor_1" in TEDDY:
        base = TEDDY["cor_1"][0]
        if color is not None:
            base = pygame.mask.from_surface(base).to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
        s = _CACHE_TEDDY[clau] = pygame.transform.scale(base, (7 * mida, 6 * mida))
    return s


def cicle_teddy(t):
    """Animació en bucle del Teddy quiet (vistes prèvies): (postura, alçada del saltiró en píxels del dibuix)."""
    c = t % 260
    if 150 <= c < 156:
        return "ajupit", 0
    if 156 <= c < 170:
        return "salt", SALT_TEDDY[c - 156]
    if 170 <= c < 175:
        return "aterra", 0
    if 205 <= c < 245:
        return "cor", 0
    return ("parpella" if c % 110 < 6 else "quiet"), 0


def sprite_dron(ident):
    s = _CACHE_DRONS.get(ident)
    if s is None and ident in DIBUIX_DRONS:
        paleta, files = DIBUIX_DRONS[ident]
        s = _CACHE_DRONS[ident] = pixmap(files, dict(PALETA_ICONA, **paleta), 2)
    elif s is None and ident == "teddy" and "quiet" in TEDDY:
        s = _CACHE_DRONS[ident] = TEDDY["quiet"][0]
    return s


class DronCompany:
    """Dron cosmètic que segueix el soldat, mira cap on apuntes i fa espurnes quan elimines un enemic."""

    def __init__(self, ident, jugador):
        self.ident = ident
        self.x, self.y = jugador.centre
        self.t = random.uniform(0, 10)
        self.alegria = 0

    def actualitzar(self, jugador, mira_x):
        self.t += 1
        jx, jy = jugador.centre
        ox = -jugador.direccio * 34
        objectiu = (jx + ox, jy - 48 + math.sin(self.t * 0.07) * 5 - (6 if self.alegria else 0))
        self.x += (objectiu[0] - self.x) * 0.1
        self.y += (objectiu[1] - self.y) * 0.1
        self.mira = 1 if mira_x >= self.x else -1
        self.alegria = max(0, self.alegria - 1)

    def celebrar(self, efectes):
        self.alegria = 30
        for _ in range(5):
            efectes.append(Particula(self.x, self.y, random.uniform(-1.5, 1.5), random.uniform(-2, -0.5),
                                     random.choice((GROC, BLANC, CIAN)), vida=18, mida=2.5))

    def dibuixar(self, surf):
        img = sprite_dron(self.ident)
        if img is None:
            return
        if getattr(self, "mira", 1) < 0:
            img = pygame.transform.flip(img, True, False)
        l = llum(9, (120, 210, 255))
        l.set_alpha(random.randint(100, 170))
        surf.blit(l, l.get_rect(center=(int(self.x), int(self.y) + img.get_height() // 2 + 2)))
        l.set_alpha(255)
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
        if self.ident == "daurat" and self.t % 9 == 0:
            pygame.draw.circle(surf, BLANC, (int(self.x + random.uniform(-10, 10)), int(self.y + random.uniform(-8, 8))), 1)


def crear_dron(ident, jugador):
    return TeddyCompany(ident, jugador) if ident == "teddy" and TEDDY else DronCompany(ident, jugador)


class CorTeddy:
    """Cor rosa que surt del Teddy Bear (emoticones, saltirons i cures)."""
    __slots__ = ("x", "y", "vx", "vy", "t", "vida", "mida", "gravetat", "fase")

    def __init__(self, x, y, vx, vy, vida=40, mida=1, gravetat=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.t, self.vida, self.mida, self.gravetat = 0, vida, mida, gravetat
        self.fase = random.uniform(0, math.tau)

    def actualitzar(self):
        self.x += self.vx + math.sin(self.t * 0.15 + self.fase) * 0.3 * self.mida     # es gronxa mentre puja
        self.y += self.vy
        self.vy += self.gravetat
        self.t += 1
        return self.t >= self.vida

    def dibuixar(self, surf):
        img = cor_teddy(self.mida - 1 if self.t < 4 and self.mida > 1 else self.mida)     # «pop» en sortir
        if img is None:
            return
        queda = self.vida - self.t
        if queda < 12:
            img.set_alpha(int(255 * queda / 12))
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
        img.set_alpha(255)


class TeddyCompany(DronCompany):
    """El Teddy Bear vola al costat del soldat, fa emoticones de cors i, si està ferit, cada 8 s li envia
    un cor que el cura una mica (vegeu Game.cura_teddy)."""

    def __init__(self, ident, jugador):
        super().__init__(ident, jugador)
        self.pose, self.t_pose = "vola", 0
        self.cors = []
        self.proper_emote = random.randint(200, 360)
        self.cura_t = 0
        self.cor_cura = None                     # [x, y, t] del cor que vola cap al soldat
        self.desti = jugador.centre

    def fer(self, pose, durada):
        self.pose, self.t_pose = pose, durada

    def afegir_cor(self, cor):
        if len(self.cors) < 24:
            self.cors.append(cor)

    def actualitzar(self, jugador, mira_x):
        self.t += 1
        jx, jy = jugador.centre
        self.desti = (jx, jy)
        objectiu = (jx - jugador.direccio * 34, jy - 44 + math.sin(self.t * 0.07) * 5 - (6 if self.alegria else 0))
        self.x += (objectiu[0] - self.x) * 0.1
        self.y += (objectiu[1] - self.y) * 0.1
        self.mira = 1 if mira_x >= self.x else -1
        self.alegria = max(0, self.alegria - 1)
        if self.t_pose:
            self.t_pose -= 1
            if self.t_pose == 0:
                self.pose = "vola"
        elif self.t % 170 == 0:
            self.fer("vola_parpella", 6)
        self.proper_emote -= 1
        if self.proper_emote <= 0 and not self.t_pose:
            self.proper_emote = random.randint(300, 480)
            self.fer("vola_cor", 54)
        if self.pose == "vola_cor" and self.t_pose % 12 == 6:
            self.afegir_cor(CorTeddy(self.x + random.uniform(-5, 5), self.y - 16, random.uniform(-0.2, 0.2), -0.75, 44))
        for c in self.cors[:]:
            if c.actualitzar():
                self.cors.remove(c)

    def vigilar(self, ferit):
        """Compta el temps que el soldat està ferit i cada 8 s li envia un cor. Torna True quan el cor arriba."""
        if ferit:
            self.cura_t += 1
            if self.cura_t >= CADA_CURA_TEDDY and self.cor_cura is None:
                self.cura_t = 0
                self.fer("vola_cor", 36)
                self.cor_cura = [self.x, self.y - 4, 0]
        c = self.cor_cura
        if c is None:
            return False
        c[2] += 1
        k = min(1.0, 0.08 + c[2] * 0.02)
        c[0] += (self.desti[0] - c[0]) * k
        c[1] += (self.desti[1] - c[1]) * k - (2.2 if c[2] < 8 else 0)          # primer salta amunt, després hi va
        if c[2] >= 10 and math.hypot(self.desti[0] - c[0], self.desti[1] - c[1]) < 8 or c[2] > 40:
            self.cor_cura = None
            return True
        return False

    def celebrar(self, efectes):
        self.alegria = 30
        if self.pose != "vola_cor":
            self.fer("vola_llança", 18)
        for _ in range(2):
            self.afegir_cor(CorTeddy(self.x + random.uniform(-6, 6), self.y - 12, random.uniform(-1.4, 1.4),
                                     random.uniform(-2.2, -1.2), 34, gravetat=0.07))

    def dibuixar(self, surf):
        l = llum(16, ROSA_TEDDY)
        l.set_alpha(int(80 + 30 * math.sin(self.t * 0.08)))
        surf.blit(l, l.get_rect(center=(int(self.x), int(self.y))))
        l.set_alpha(255)
        posar_teddy(surf, self.pose, self.x, self.y + 14)
        for c in self.cors:
            c.dibuixar(surf)
        if self.cor_cura:
            x, y, _ = self.cor_cura
            img = cor_teddy(2)
            if img:
                surf.blit(img, img.get_rect(center=(int(x), int(y))))


class TeddySala:
    """El Teddy Bear a la sala (menú): dret al pedestal al costat de Nexus; parpelleja, fa saltirons,
    tira cors rosa i s'abraça el seu cor. Quan Nexus abat el dron de pràctica, també tira cors."""
    ident = "teddy"
    ESC = 2
    DURADA = {"salt": 25, "llança": 20, "cor": 52}

    def __init__(self):
        self.t = 0
        self.x, self.peus = 0, 0
        self.accio, self.t_accio, self.n = None, 0, 0
        self.cors = []

    def tirar(self, n, dy=0):
        for _ in range(n):
            self.cors.append(CorTeddy(self.x + random.uniform(-12, 12), self.peus - 46 + dy, random.uniform(-1.8, 1.8),
                                      random.uniform(-3.4, -1.8), random.randint(40, 52), random.choice((1, 2, 2)),
                                      gravetat=0.07))

    def actualitzar(self, x, peus):
        self.t += 1
        self.x, self.peus = x, peus
        if self.accio:
            self.t_accio += 1
            if self.accio == "salt" and self.t_accio == 12:          # dalt de tot del saltiró
                self.tirar(4, SALT_TEDDY[6] * self.ESC)
            elif self.accio == "llança" and self.t_accio == 3:
                self.tirar(6)
            elif self.accio == "cor" and self.t_accio % 10 == 6 and self.t_accio < 44:
                self.cors.append(CorTeddy(self.x + random.uniform(-8, 8), self.peus - 62, random.uniform(-0.3, 0.3), -0.9,
                                          44, 2))
            if self.t_accio >= self.DURADA[self.accio]:
                self.accio = None
        elif self.t % 230 == 140:
            self.accio, self.t_accio = ("salt", "llança", "salt", "cor")[self.n % 4], 0
            self.n += 1
        for c in self.cors[:]:
            if c.actualitzar():
                self.cors.remove(c)

    def pose(self):
        a, k = self.accio, self.t_accio
        if a == "salt":
            if k < 6:
                return "ajupit", 0
            if k < 20:
                return "salt", SALT_TEDDY[k - 6]
            return "aterra", 0
        if a == "llança" and k < 18:
            return "llança", 0
        if a == "cor" and k < 48:
            return "cor", 0
        return ("parpella" if self.t % 170 < 6 else "quiet"), 0

    def celebrar(self, efectes):
        if self.accio is None:
            self.accio, self.t_accio = "llança", 0

    def dibuixar(self, surf):
        pose, h = self.pose()
        w = max(16, 34 + h)                                       # l'ombra s'encongeix quan salta
        pygame.draw.ellipse(surf, (4, 6, 14), (int(self.x - w / 2), self.peus - 4, w, 8))
        posar_teddy(surf, pose, self.x, self.peus + h * self.ESC, self.ESC)

    def dibuixar_cors(self, surf):
        for c in self.cors:
            c.dibuixar(surf)


# --- efectes d'eliminació --------------------------------------------------------------
def sprite_enemic(e):
    img, _ = e.imatge() if hasattr(e, "imatge") else (e.sprite, None)
    return img or e.sprite


class EfecteBaixa:
    """Com desapareix un enemic abatut, segons el cosmètic d'eliminació equipat."""

    def __init__(self, enemic, tipus, efectes):
        self.tipus = tipus
        self.img = sprite_enemic(enemic)
        self.x, self.y = enemic.centre
        self.t = 0
        self.durada = {"gel": 26, "forat": 30, "electric": 22}.get(tipus, 1)
        if tipus == "gel" and self.img is not None:
            gel = self.img.copy()
            gel.fill((140, 210, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
            blanc = silueta_blanca(self.img)
            blanc.set_alpha(90)
            gel.blit(blanc, (0, 0))
            self.img_gel = gel
        if tipus in ("pixels", "confeti", "daurat"):
            self.esclatar(efectes)

    def esclatar(self, efectes):
        x, y = self.x, self.y
        if self.tipus == "pixels" and self.img is not None:
            w, h = self.img.get_size()
            pas = max(3, int(math.sqrt(w * h / 70)))
            for py in range(0, h, pas):
                for px in range(0, w, pas):
                    c = self.img.get_at((px, py))
                    if c.a > 100:
                        dx, dy = px - w / 2, py - h / 2
                        efectes.append(Particula(x + dx, y + dy, dx * 0.06 + random.uniform(-0.6, 0.6),
                                                 dy * 0.04 - random.uniform(0.8, 2.2), (c.r, c.g, c.b),
                                                 vida=random.randint(26, 46), mida=pas * 0.7, gravetat=0.12))
        elif self.tipus == "confeti":
            for _ in range(36):
                a = random.uniform(0, math.tau)
                v = random.uniform(1.5, 5)
                efectes.append(Particula(x, y, math.cos(a) * v, math.sin(a) * v - 2,
                                         random.choice(((255, 80, 200), (90, 230, 255), GROC, VERD, (255, 140, 60))),
                                         vida=random.randint(30, 55), mida=random.uniform(2.5, 4), gravetat=0.1))
            efectes.append(Anell(x, y, BLANC, r=4, creix=3, vida=10))
        elif self.tipus == "daurat":
            for _ in range(14):
                efectes.append(Particula(x, y, random.uniform(-3, 3), random.uniform(-5, -2), GROC, vida=40, mida=4,
                                         gravetat=0.25))
            esclat(efectes, x, y, 10, [BLANC, (255, 245, 170)], vel=(1, 3), mida=(1.5, 2.5), vida=(10, 20))
            efectes.append(Anell(x, y, GROC, r=4, creix=3, vida=12))
        elif self.tipus == "gel":
            for _ in range(22):
                a = random.uniform(0, math.tau)
                v = random.uniform(1.5, 4.5)
                efectes.append(Particula(x, y, math.cos(a) * v, math.sin(a) * v - 1,
                                         random.choice(((200, 240, 255), (140, 210, 255), BLANC)),
                                         vida=random.randint(20, 36), mida=random.uniform(2, 4), gravetat=0.2))
        elif self.tipus == "forat":
            efectes.append(Anell(x, y, (190, 90, 255), r=4, creix=4, vida=14))
            esclat(efectes, x, y, 14, [(190, 90, 255), BLANC, (90, 40, 140)], vel=(1, 4), mida=(2, 3), vida=(10, 20))
        elif self.tipus == "electric":
            esclat(efectes, x, y, 18, [(80, 80, 90), (120, 120, 130), (40, 40, 48)], vel=(0.5, 2), mida=(3, 5),
                   vida=(20, 36), gravetat=-0.02)

    def actualitzar(self, joc):
        self.t += 1
        if self.t >= self.durada:
            if self.tipus in ("gel", "forat", "electric"):
                self.esclatar(joc.efectes)
                AUDIO.so("impacte", 60)
            return True
        return False

    def dibuixar(self, surf):
        if self.img is None or self.t >= self.durada:
            return
        if self.tipus == "gel":
            img = self.img_gel
            surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
            if self.t > 12:                                      # s'esquerda
                k = (self.t - 12) / (self.durada - 12)
                for i in range(4):
                    a = i * 1.6 + 0.4
                    pygame.draw.line(surf, BLANC, (self.x, self.y),
                                     (self.x + math.cos(a) * 20 * k, self.y + math.sin(a) * 16 * k), 1)
        elif self.tipus == "forat":
            k = 1 - self.t / self.durada
            r = int(10 + 22 * (1 - k))
            pygame.draw.circle(surf, (20, 6, 30), (int(self.x), int(self.y)), r)
            pygame.draw.circle(surf, (190, 90, 255), (int(self.x), int(self.y)), r, 2)
            if k > 0.05:
                img = pygame.transform.rotozoom(self.img, self.t * 24, max(0.05, k))
                surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
        elif self.tipus == "electric":
            img = silueta_blanca(self.img) if self.t % 4 < 2 else self.img
            surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
            for _ in range(3):
                punts = [(self.x + random.uniform(-20, 20), self.y + random.uniform(-18, 18)) for _ in range(4)]
                pygame.draw.lines(surf, (180, 220, 255), False, punts, 2)


# --- fons de les targetes de jugador -------------------------------------------------------
_CACHE_TARGETA = {}


def fons_targeta(ident, w, h):
    clau = (ident, w, h)
    s = _CACHE_TARGETA.get(clau)
    if s is not None:
        return s
    info = TARGETES.get(ident, TARGETES["estels"])
    s = pygame.Surface((w, h))
    fons = info["fons"]
    if fons == "estels":
        s.fill((14, 16, 36))
        rnd = random.Random(7)
        for _ in range(w * h // 120):
            b = rnd.randint(120, 255)
            s.set_at((rnd.randrange(w), rnd.randrange(h)), (b, b, min(255, b + 30)))
    elif fons == "daurada":
        for y in range(h):
            k = y / max(1, h - 1)
            s.fill((int(150 + 90 * (1 - k)), int(100 + 70 * (1 - k)), int(20 + 20 * (1 - k))), (0, y, w, 1))
        rnd = random.Random(3)
        for _ in range(w * h // 200):
            s.set_at((rnd.randrange(w), rnd.randrange(h)), (255, 250, 210))
    else:
        img = FONS_NIVELLS.get(tuple(fons))
        if img is not None:
            iw, ih = img.get_size()
            alt = int(iw * h / w)
            tros = img.subsurface((0, max(0, (ih - alt) // 2), iw, min(ih, alt)))
            s = pygame.transform.smoothscale(tros, (w, h))
        else:
            s.fill((30, 34, 60))
    fosc = pygame.Surface((w, h), pygame.SRCALPHA)               # més fosc a l'esquerra (on va el text)
    for x in range(w):
        fosc.fill((0, 0, 10, int(170 * (1 - x / w) ** 1.2)), (x, 0, 1, h))
    s = s.copy()
    s.blit(fosc, (0, 0))
    _CACHE_TARGETA[clau] = s
    return s


def dibuixar_targeta(surf, rect, ident, titol, rang, temporada, nivell_passi, prestigi, monedes=None, estrelles=None):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, NEGRE, r.move(0, 3), border_radius=8)
    surf.blit(fons_targeta(ident, r.w, r.h), r)
    pygame.draw.rect(surf, (255, 205, 60) if ident == "daurada" else (90, 120, 190), r, 2, border_radius=6)
    dibuixar_insignia(surf, r.x + 30, r.centery - 2, rang, 34)
    x = r.x + 58
    text(surf, T(TITOLS.get(titol, "")), F_MINI, (255, 200, 255), (x, r.y + 16), ancora="midleft")
    text(surf, T(RANGS[rang]["nom"]).upper(), F_HUD, BLANC, (x, r.y + 34), ancora="midleft")
    text(surf, T("Temporada {t} · BP {n}").format(t=temporada, n=nivell_passi), F_MINI, (200, 205, 225),
         (x, r.y + 54), ancora="midleft")
    for k in range(min(prestigi, 5)):
        dibuixar_estrella(surf, x + 6 + k * 14, r.y + 72, 6, True, (190, 140, 255))
    if monedes is not None:
        rm = text(surf, str(monedes), F_HUD, GROC, (r.right - 10, r.y + 16), ancora="midright")
        dibuixar_moneda(surf, rm.left - 12, r.y + 16)
    if estrelles is not None:
        re = text(surf, f"{estrelles}/45", F_MINI, (255, 220, 120), (r.right - 10, r.bottom - 14), ancora="midright")
        dibuixar_estrella(surf, re.left - 10, re.centery, 6, True)



# ---------------------------------------------------------------------------
# Menú principal (v3.6): icones, aparador amb el soldat i revelacions
# ---------------------------------------------------------------------------
def dibuixar_icona_menu(surf, clau, cx, cy, t=0, color=BLANC):
    """Icones dels botons grans i de la barra superior del menú."""
    if clau == "jugar":
        k = 1 + 0.08 * math.sin(t * 0.12)
        p = [(cx - 9 * k, cy - 12 * k), (cx + 13 * k, cy), (cx - 9 * k, cy + 12 * k)]
        pygame.draw.polygon(surf, NEGRE, [(x + 2, y + 2) for x, y in p])
        pygame.draw.polygon(surf, color, p)
    elif clau == "botiga":                                    # bossa de la compra amb una moneda
        dy = int(math.sin(t * 0.1))
        pygame.draw.arc(surf, (230, 200, 120), (cx - 7, cy - 15 + dy, 14, 14), 0, math.pi, 3)
        cos = pygame.Rect(cx - 13, cy - 8 + dy, 26, 21)
        pygame.draw.rect(surf, NEGRE, cos.move(0, 2), border_radius=4)
        pygame.draw.rect(surf, (210, 120, 60), cos, border_radius=4)
        pygame.draw.rect(surf, (250, 170, 100), (cos.x + 2, cos.y + 2, cos.w - 4, 4), border_radius=2)
        dibuixar_moneda(surf, cx, cy + 4 + dy, 6)
    elif clau == "passi":
        r = pygame.Rect(cx - 17, cy - 12, 34, 24)
        pygame.draw.rect(surf, NEGRE, r.move(0, 2), border_radius=5)
        pygame.draw.rect(surf, (200, 80, 200), r, border_radius=5)
        pygame.draw.rect(surf, (255, 170, 255), r, 2, border_radius=5)
        text(surf, "BP", F_MINI, BLANC, r.center)
    elif clau == "colleccio":
        for k, dx in enumerate((-9, 0, 9)):
            col = ((205, 127, 70), (215, 220, 235), (255, 205, 60))[k]
            y = cy + 3 - (4 if k == 1 else 0) + int(1.5 * math.sin(t * 0.1 + k))
            pygame.draw.circle(surf, NEGRE, (cx + dx, y + 2), 8)
            pygame.draw.circle(surf, col, (cx + dx, y), 7)
            pygame.draw.circle(surf, BLANC, (cx + dx - 2, y - 2), 2)
    elif clau == "diari":
        pygame.draw.rect(surf, NEGRE, (cx - 13, cy - 11, 28, 26), border_radius=3)
        pygame.draw.rect(surf, (235, 232, 215), (cx - 14, cy - 13, 28, 26), border_radius=3)
        pygame.draw.rect(surf, VERMELL, (cx - 14, cy - 13, 28, 8), border_top_left_radius=3, border_top_right_radius=3)
        text(surf, str(time.localtime().tm_mday), F_MINI, NEGRE, (cx, cy + 4), ombra=False)
    elif clau == "guia":
        pygame.draw.rect(surf, (235, 230, 210), (cx - 13, cy - 10, 12, 20))
        pygame.draw.rect(surf, (235, 230, 210), (cx + 1, cy - 10, 12, 20))
        pygame.draw.line(surf, (120, 90, 60), (cx, cy - 10), (cx, cy + 10), 2)
        for k in range(3):
            pygame.draw.line(surf, GRIS, (cx - 10, cy - 5 + k * 5), (cx - 4, cy - 5 + k * 5))
            pygame.draw.line(surf, GRIS, (cx + 4, cy - 5 + k * 5), (cx + 10, cy - 5 + k * 5))
    elif clau == "opcions":
        a0 = t * 0.02
        for k in range(8):
            a = a0 + k * math.tau / 8
            pygame.draw.line(surf, (190, 196, 214), (cx, cy), (cx + math.cos(a) * 12, cy + math.sin(a) * 12), 5)
        pygame.draw.circle(surf, (190, 196, 214), (cx, cy), 9)
        pygame.draw.circle(surf, (30, 34, 66), (cx, cy), 4)
    elif clau == "credits":
        dibuixar_estrella(surf, cx, cy, 12, True, (255, 214, 64))
    elif clau == "sortir":
        pygame.draw.arc(surf, (255, 120, 120), (cx - 11, cy - 10, 22, 22), math.radians(125), math.radians(415), 3)
        pygame.draw.line(surf, (255, 120, 120), (cx, cy - 13), (cx, cy - 1), 3)


class AparadorMenu:
    """El soldat del jugador en gran al menú, amb tot el que porta equipat. De tant en tant fa una
    tombarella (amb l'estela) o dispara a un dron de pràctica (amb el camuflatge i l'efecte d'eliminació)."""

    ESCALA = 2                    # sobre els fotogrames del soldat (que ja són x2): x4 en total

    def __init__(self):
        self.t = 0
        self.efectes = []
        self.restes = []
        self.bales = []
        self.accio = None
        self.t_accio = 0
        self.diana = None
        self.n_accions = 0
        self.dron = None
        self.cache = {}

    def imatge(self, img):
        clau = id(img)
        s = self.cache.get(clau)
        if s is None:
            if len(self.cache) > 40:
                self.cache.clear()
            s = self.cache[clau] = pygame.transform.scale(img, (img.get_width() * self.ESCALA, img.get_height() * self.ESCALA))
        return s

    def actualitzar(self, joc, cx, peus):
        self.t += 1
        if self.accio is None and self.t % 300 == 120:
            self.accio = ("dispar", "voltereta")[self.n_accions % 2]
            self.n_accions += 1
            self.t_accio = 0
            if self.accio == "dispar":
                self.diana = {"x": cx + 330.0, "y": peus - 110.0, "viva": True}
        if self.accio:
            self.t_accio += 1
            if self.accio == "voltereta":
                if self.t_accio < 28:
                    cols = colors_estela(joc.estela, self.t)
                    for _ in range(2):
                        self.efectes.append(Particula(cx + random.uniform(-30, 30), peus - 60 + random.uniform(-26, 26),
                                                      random.uniform(-0.6, 0.6), random.uniform(-0.8, 0.2),
                                                      random.choice(cols), vida=random.randint(14, 24), mida=random.uniform(3, 6)))
                if self.t_accio >= 40:
                    self.accio = None
            else:
                d = self.diana
                if d and d["viva"]:
                    d["x"] += (cx + 140 - d["x"]) * 0.06
                if self.t_accio in (50, 58, 66) and d and d["viva"]:
                    spr = self.spr(joc)
                    bx, by = self.canó(spr, cx, peus)
                    ang = math.atan2(d["y"] - by, d["x"] - bx)
                    estil = ARMES[joc.arma_actual]["estil"]
                    b = Bala(bx, by, math.cos(ang) * 12, math.sin(ang) * 12, 1, estil, color=joc.color_bala(), k=self.t_accio)
                    self.bales.append(b)
                    self.flash = 4
                    AUDIO.tret(ARMES[joc.arma_actual]["so"])
                for b in self.bales[:]:
                    b.actualitzar()
                    if d and d["viva"] and math.hypot(b.x - d["x"], b.y - d["y"]) < 22:
                        self.bales.remove(b)
                        esclat(self.efectes, b.x, b.y, 6, [b.color[:3], BLANC], vel=(1, 3), vida=(6, 12))
                        if self.t_accio >= 66:
                            d["viva"] = False
                            enemic = type("DianaMenu", (), {})()
                            enemic.sprite = SPR_ENEMIC.get("dron")
                            enemic.centre = (d["x"], d["y"])
                            if joc.efecte != "normal":
                                self.restes.append(EfecteBaixa(enemic, joc.efecte, self.efectes))
                            else:
                                esclat(self.efectes, d["x"], d["y"], 22, [TARONJA, VERMELL, GROC, BLANC], vel=(2, 6),
                                       vida=(14, 30))
                                self.efectes.append(Anell(d["x"], d["y"], TARONJA, creix=3.5, vida=18))
                            if self.dron:
                                self.dron.celebrar(self.efectes)
                    elif b.x > WIDTH + 20:
                        self.bales.remove(b)
                if self.t_accio >= 130:
                    self.accio, self.diana, self.bales = None, None, []
        for r in self.restes[:]:
            if r.actualitzar(self):
                self.restes.remove(r)
        for fx in self.efectes[:]:
            if fx.actualitzar():
                self.efectes.remove(fx)
        self.flash = max(0, getattr(self, "flash", 0) - 1)
        # dron company (el Teddy Bear, en canvi, es queda dret al pedestal al costat de Nexus)
        if joc.dron != "cap":
            jug = type("JugadorMenu", (), {})()
            jug.centre = (cx + 10, peus - 60)
            jug.direccio = 1
            if self.dron is None or self.dron.ident != joc.dron:
                self.dron = TeddySala() if joc.dron == "teddy" and TEDDY else DronCompany(joc.dron, jug)
            if isinstance(self.dron, TeddySala):
                self.dron.actualitzar(cx - 86, peus - 4)
            else:
                self.dron.actualitzar(jug, cx + 300)
        else:
            self.dron = None

    @staticmethod
    def spr(joc):
        i = joc.arma_actual
        return sprites_jugador(ARMES[i]["id"], joc.uniforme, joc.aparenca, joc.nivell_millora("blindatge"), joc.camo_actual(i))

    def canó(self, spr, cx, peus):
        return cx + spr.cano_dx * self.ESCALA, peus + spr.cano_dy * self.ESCALA

    def dibuixar(self, surf, joc, cx, peus):
        # pedestal
        pygame.draw.ellipse(surf, (10, 12, 26), (cx - 110, peus - 14, 220, 34))
        pygame.draw.ellipse(surf, (40, 56, 110), (cx - 104, peus - 12, 208, 26), 3)
        l = llum(70, (90, 140, 255))
        l.set_alpha(70)
        surf.blit(l, l.get_rect(center=(cx, peus)))
        l.set_alpha(255)
        teddy = self.dron if isinstance(self.dron, TeddySala) else None
        if teddy:
            teddy.dibuixar(surf)
        spr = self.spr(joc)
        if not spr:
            return
        if self.accio == "voltereta" and self.t_accio < 28:
            k = self.t_accio / 28
            img = self.imatge(spr.poses["salt"][0][1])
            rot = pygame.transform.rotate(img, -360 * k)
            surf.blit(rot, rot.get_rect(center=(cx, int(peus - img.get_height() / 2 - math.sin(k * math.pi) * 40))))
        else:
            img = self.imatge(spr.poses["quiet"][(self.t // 35) % 2][1])
            ancora = spr.ancoratge(1) * self.ESCALA
            surf.blit(img, (int(cx - ancora), int(peus - img.get_height())))
            if getattr(self, "flash", 0):
                tx, ty = self.canó(spr, cx, peus)
                fogonazo(surf, tx, ty, 0.0, 26, 9, (255, 210, 70))
            if joc.camo_actual() == "diamant" and self.t % 6 == 0:
                tx, ty = self.canó(spr, cx, peus)
                self.efectes.append(Particula(tx - random.uniform(0, 60), ty + random.uniform(-6, 6), 0, -0.3,
                                              random.choice((BLANC, (170, 240, 255))), vida=16, mida=3))
        d = self.diana
        if d and d["viva"]:
            img = SPR_ENEMIC.get("dron")
            if img:
                surf.blit(img, img.get_rect(center=(int(d["x"]), int(d["y"] + 4 * math.sin(self.t * 0.1)))))
        for b in self.bales:
            b.dibuixar(surf)
        for r in self.restes:
            r.dibuixar(surf)
        for fx in self.efectes:
            fx.dibuixar(surf)
        if teddy:
            teddy.dibuixar_cors(surf)
        elif self.dron:
            self.dron.dibuixar(surf)


def raigs(surf, cx, cy, t, color, n=12, r=420):
    """Raigs de llum que giren darrere d'una recompensa (es pinten directament: no cal cap capa)."""
    for k in range(n):
        a = t * 0.01 + k * math.tau / n
        punts = [(cx, cy), (cx + math.cos(a - 0.11) * r, cy + math.sin(a - 0.11) * r),
                 (cx + math.cos(a + 0.11) * r, cy + math.sin(a + 0.11) * r)]
        pygame.draw.polygon(surf, color, punts)


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
        self.pestanya = "diaria"
        self.entrada_arxiu = 0
        self.avisos = []
        self.flaix = 0
        self.carregar_progres()
        self.reiniciar_partida_estat()

    # ----- Progrés -----------------------------------------------------------
    def carregar_progres(self):
        self.carregant_partida = True              # el que es doni mentre es carrega no es «revela»
        try:
            self._carregar_progres()
        finally:
            self.carregant_partida = False
        self.revelacions = []

    def _carregar_progres(self):
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
                            if d.get("ordre_estrelles") != 2:     # abans: completat, sense mal, temps
                                est_ne = self.estrelles[n][e]
                                est_ne[1], est_ne[2] = est_ne[2], est_ne[1]
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
        self.carregar_contingut(d)

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
            "equipat": self.equipament(),
            "intro_vista": self.intro_vista,
            "tutorial_vist": self.tutorial_vist,
            "novetats_vistes": self.novetats_vistes,
            "estrelles": self.estrelles, "ordre_estrelles": 2,
            "records": self.records,
            "logros": sorted(self.logros),
            "estadistiques": self.estadistiques,
            "plaques": sorted(self.plaques),
            **self.dades_contingut(),
            "opcions": {"musica": round(AUDIO.vol_musica, 2), "efectes": round(AUDIO.vol_efectes, 2),
                        "completa": PANTALLA.completa, "suau": PANTALLA.suau,
                        "dificultat": self.nivell_dificultat, "idioma": idioma(), "numeros": self.numeros_dany},
        })

    def esborrar_progres(self):
        if not self.confirmar_reinici:
            self.confirmar_reinici = True
            self.entrar_opcions(self.entrar_menu)
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
        if self.mode in ("supervivencia", "tutorial", "desafiament"):
            return 5
        return POTENCIA_MAX.get((self.nivell_actual, self.escenari_actual), 5)

    def armes_usables(self):
        if self.mode == "tutorial":     # a l'entrenament: només la pistola fins al pas de canviar d'arma
            ja_pot = [c for c, _ in PASSOS_TUTORIAL].index("arma") <= getattr(self, "tut", {}).get("pas", 0)
            return [ARMA_PER_ID["pistola"]] + ([ARMA_PER_ID["fusell"]] if ja_pot else [])
        pm = self.potencia_max()
        return [i for i, a in enumerate(ARMES) if a["id"] in self.armes_propies and a["potencia"] <= pm]

    def spr_jugador(self, i=None):
        idx = self.arma_actual if i is None else i
        return sprites_jugador(ARMES[idx]["id"], self.uniforme, self.aparenca, self.nivell_millora("blindatge"),
                               self.camo_actual(idx))

    def nivell_passi(self):
        n = 0
        while n < len(PASSI) and self.xp_passi >= ACUM_PASSI[n + 1]:
            n += 1
        return n

    def afegir_xp(self, quantitat):
        self.xp += quantitat
        self.xp_passi += quantitat
        while self.passi_reclamat < self.nivell_passi():
            for tipus, valor in PASSI[self.passi_reclamat]:
                if not self.atorgar(tipus, valor):               # ja el tenies (temporada 2 o més): monedes
                    self.monedes += 100 + 10 * self.passi_reclamat
                self.avis(f"BATTLE PASS {self.passi_reclamat + 1}: {nom_premi(tipus, valor)}", (255, 200, 255), 260)
            self.passi_reclamat += 1
            AUDIO.so("passi")
        if self.passi_reclamat >= len(PASSI) and self.xp_passi >= ACUM_PASSI[-1]:
            self.xp_passi -= ACUM_PASSI[-1]                      # temporada nova: el passi torna a començar
            self.temporada += 1
            self.passi_reclamat = 0
            self.revelar("temporada", self.temporada)
            self.avis(T("¡Temporada {t}! El Battle Pass vuelve a empezar. Ganas una estrella de prestigio.").format(
                t=self.temporada), (190, 140, 255), 320)
        self.revisar_rangs()

    def nivell_passi_de(self, tipus, valor):
        for i, recompenses in enumerate(PASSI):
            if (tipus, valor) in recompenses:
                return i + 1
        return None

    # ----- Canvis d'estat ---------------------------------------------------
    ESTATS_SENSE_FOS = ("joc", "intro", "loading", "quit", "pausa")

    ESTATS_MUSICA_MENU = ("menu", "jugar", "selector", "supervivencia", "botiga", "passi", "colleccio", "diari",
                          "desafiaments", "guia", "arxiu", "logros", "novetats", "revelacio", "idioma_inicial", "ajuda", "codis",
                          "arma", "personalitzar")

    def canviar_estat(self, estat):
        if estat != self.estat:
            self.missatge = ""
            self.temps_missatge = 0
            if self.estat not in self.ESTATS_SENSE_FOS and estat not in self.ESTATS_SENSE_FOS:
                self.transicio = [screen.copy(), 12]          # fos encadenat entre pantalles
        self.estat = estat
        self.temps_estat = 0
        pygame.mouse.set_visible(estat != "joc")
        # música: en pausa s'atura; tornant a jugar continua; a qualsevol pantalla de menú, la del menú
        if estat == "pausa":
            AUDIO.pausar()
        elif estat == "joc":
            AUDIO.reprendre()
        elif estat in self.ESTATS_MUSICA_MENU:
            AUDIO.musica("menu")

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
        self.confirmar_reinici = False
        self.revisar_rangs()
        self.desar_progres()
        accions = {"jugar": self.entrar_jugar, "botiga": self.entrar_botiga, "passi": self.entrar_passi,
                   "colleccio": self.entrar_colleccio, "diari": self.entrar_diari}
        b = []
        for k, (ident, _) in enumerate(self.BOTONS_MENU):
            b.append(Boto(self.rect_boto_menu(k), "", accions[ident], invisible=True))
        barra = {"idioma": self.obrir_menu_idioma, "logros": self.entrar_logros,
                 "novetats": lambda: self.entrar_novetats(0, self.entrar_menu), "guia": self.entrar_guia,
                 "opcions": self.entrar_opcions, "credits": self.entrar_credits,
                 "sortir": lambda: self.canviar_estat("quit")}
        for k, ident in enumerate(self.icones_barra()):
            b.append(Boto(self.rect_icona_barra(k), "", barra[ident], invisible=True))
        b.append(Boto(self.rect_destacat(), "", self.obrir_destacat, invisible=True))
        b.append(Boto(self.rect_nexus_menu(), "", self.entrar_personalitzar, invisible=True))   # clic a Nexus
        self.botons = b
        if getattr(self, "aparador", None) is None:
            self.aparador = AparadorMenu()
        self.canviar_estat("menu")
        self.revisar_logros()
        if self.revelacions:
            self.entrar_revelacio(self.entrar_menu)

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
        b.append(Boto((30, HEIGHT - 62, 140, 42), "< Volver", self.entrar_jugar, GRIS_FOSC))
        b.append(Boto((WIDTH - 250, HEIGHT - 66, 226, 42), "Desafíos", self.entrar_desafiaments, TARONJA))
        self.botons = b
        self.canviar_estat("selector")

    def entrar_botiga(self, pestanya=None):
        self.confirmar_reinici = False
        if pestanya:
            self.pestanya = pestanya
        if self.pestanya not in ("diaria", "armes", "millores"):
            self.pestanya = "diaria"
        b = []
        for k, (ident, nom) in enumerate((("diaria", "Diaria"), ("armes", "Armas"), ("millores", "Mejoras"))):
            b.append(Boto((WIDTH // 2 - 265 + k * 180, 74, 170, 38), nom, lambda i=ident: self.entrar_botiga(i),
                          VERD if self.pestanya == ident else (TARONJA if ident == "diaria" else BLAU), font=F_HUD))
        b.append(Boto(self.RECT_CALCULADORA, "", self.entrar_codis, invisible=True))
        if self.pestanya == "armes":
            for i in range(len(ARMES)):
                b.append(Boto(self.rect_carta_arma(i), "", lambda i=i: self.entrar_arma(i), invisible=True))
        elif self.pestanya == "millores":
            for k, m in enumerate(MILLORES):
                nivell = self.nivell_millora(m["id"])
                rect = (734, 128 + k * 56 + 7, 156, 36)
                if nivell >= len(m["costos"]):
                    b.append(Boto(rect, "Máximo", None, font=F_MINI))
                elif not self.completat(m["req"][nivell]):
                    b.append(Boto(rect, T("Completa {e}").format(e=nom_escenari(m['req'][nivell])), None, font=F_MINI))
                elif self.estrelles_totals() < m.get("estrelles", [0] * 3)[nivell]:
                    b.append(Boto(rect, T("Necesitas {n} ★").format(n=m["estrelles"][nivell]), None, font=F_MINI))
                else:
                    cost = m["costos"][nivell]
                    color = TARONJA if self.monedes >= cost else VERMELL_FOSC
                    b.append(Boto(rect, T("Comprar {c}").format(c=cost), lambda m=m: self.comprar_millora(m), color, font=F_MINI))
        else:
            b += self.botons_ofertes()
            self.marcar_vist("ofertes")
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
        self.entrar_arma(i) if self.estat == "arma" else self.entrar_botiga()

    def equipar_arma(self, i):
        self.arma_actual = i
        AUDIO.so("item")
        self.desar_progres()
        self.entrar_arma(i) if self.estat == "arma" else self.entrar_botiga()

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
        if PREFIX_COSMETIC[tipus] + valor not in self.cosmetics:
            self.mostrar_missatge(self.origen_cosmetic(tipus, valor))
            AUDIO.so("buit")
            return
        if tipus == "uniforme":
            self.uniforme = valor
        elif tipus == "arma":
            self.aparenca = valor
        elif tipus == "titol":
            self.titol = valor
        else:
            setattr(self, tipus, valor)
            if tipus == "tema":
                TEMA_HUD[0] = TEMES_HUD[valor]
        AUDIO.so("item")
        self.desar_progres()
        self.revisar_logros()

    def entrar_passi(self, pagina=None):
        self.confirmar_reinici = False
        if pagina is None:
            pagina = min(self.nivell_passi(), len(PASSI) - 1) // 20
        self.pagina_passi = max(0, min((len(PASSI) - 1) // 20, pagina))
        self.marcar_vist("passi")
        b = [self.boto_tornar()]
        if self.pagina_passi > 0:
            b.append(Boto((WIDTH // 2 - 130, 468, 60, 40), "<", lambda: self.entrar_passi(self.pagina_passi - 1)))
        if self.pagina_passi < (len(PASSI) - 1) // 20:
            b.append(Boto((WIDTH // 2 + 70, 468, 60, 40), ">", lambda: self.entrar_passi(self.pagina_passi + 1)))
        self.botons = b
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
        b.append(Boto((30, HEIGHT - 62, 140, 42), "< Volver", self.entrar_jugar, GRIS_FOSC))
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
        if self.tornada_opcions == self.entrar_menu:
            b.append(Boto((WIDTH - 210, HEIGHT - 44, 190, 30), "Borrar progreso", self.esborrar_progres,
                          color=VERMELL_FOSC if not self.confirmar_reinici else VERMELL, font=F_MINI))
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
        if self.mode == "desafiament":
            self.iniciar_desafiament(self.mode_desafiament)
            return
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
        if self.mode == "desafiament":
            d = DESAFIAMENTS[self.mode_desafiament]
            dades = {"plataformes": d["plataformes"], "onades": d["onades"]}
        self.repeticio = self.mode == "historia" and self.completats[clau[0]][clau[1]]
        reflexos = self.nivell_millora("reflexos")
        self.jugador = Jugador(self.vida_max(), 1 + 0.06 * reflexos, 1 if self.nivell_millora("doble_salt") else 0,
                               40 + 12 * reflexos)
        self.bales, self.bales_enemics, self.items, self.efectes, self.textos, self.restes = [], [], [], [], [], []
        self.ones_xoc = []
        self.bales_armes = [self.bales_max(i) for i in range(len(ARMES))]
        mobils, fragils = dades.get("mobils", {}), dades.get("fragils", ())
        self.plataformes = [Plataforma(0, TERRA_Y, WIDTH, HEIGHT - TERRA_Y, terra=True)]
        self.plataformes += [Plataforma(x, y, w, mov=mobils.get(i), fragil=i in fragils)
                             for i, (x, y, w) in enumerate(dades["plataformes"])]
        if self.mode == "historia" and clau in REPISES_PLACA:           # repisa on descansa la placa
            x, y, w = REPISES_PLACA[clau]
            self.plataformes.append(Plataforma(x, y, w, h=14))
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
        self.jugador.estela = self.estela
        self.dron_company = crear_dron(self.dron, self.jugador) if self.dron != "cap" else None
        if self.repeticio:
            self.avis("Escenario repetido: las monedas valen la mitad", GRIS, 200)
        if self.mode == "supervivencia":
            self.onades = None
            self.punts = 0
            self.baixes = 0
            self.onades_superades = 0
            self.nom_cap = "JEFE DE OLEADA"
            self.llançar_onada_supervivencia(1)
        else:
            self.nivell_enemics = self.nivell_actual
            if self.mode == "desafiament":
                self.nivell_enemics = DESAFIAMENTS[self.mode_desafiament]["nivell"]
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
        camo = self.camo_actual()
        if camo:
            return CAMUFLATGES[camo]["bala"]
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

    def efectes_cosmetics(self, j, mx):
        """Estela de la voltereta, espurnes del camuflatge diamant i el dron company."""
        if j.esquiva and self.estela != "normal":
            cols = colors_estela(self.estela, self.t_global)
            jx, jy = j.centre
            for _ in range(2):
                self.efectes.append(Particula(jx - j.dir_esquiva * random.uniform(4, 16), jy + random.uniform(-14, 14),
                                              -j.dir_esquiva * random.uniform(0.3, 1.2), random.uniform(-0.6, 0.6),
                                              random.choice(cols), vida=random.randint(12, 22), mida=random.uniform(2.5, 4.5)))
        if self.camo_actual() == "diamant" and self.t_global % 7 == 0:
            cx, cy = j.canons(self.spr_jugador())
            self.efectes.append(Particula(cx - j.direccio * random.uniform(0, 26), cy + random.uniform(-4, 4), 0,
                                          -0.3, random.choice((BLANC, (170, 240, 255))), vida=14, mida=2))
        if self.dron_company:
            self.dron_company.actualitzar(j, mx)
            if isinstance(self.dron_company, TeddyCompany):
                self.cura_teddy(j)

    def cura_teddy(self, j):
        """El Teddy Bear cura +5 de vida cada 8 s mentre el soldat està ferit (un cor vola del Teddy fins a ell)."""
        ferit = self.fase == "jugant" and 0 < j.vida < j.vida_max
        if not self.dron_company.vigilar(ferit) or not ferit:
            return
        guany = min(CURA_TEDDY, j.vida_max - j.vida)
        j.vida += guany
        jx, jy = j.centre
        self.textos.append(TextFlotant(jx, j.y - 16, f"+{round(guany)}", ROSA_TEDDY))
        for k in range(10):
            a = k * math.tau / 10
            self.efectes.append(Particula(jx + math.cos(a) * 18, jy + math.sin(a) * 22, math.cos(a) * 0.8,
                                          math.sin(a) * 0.8 - 0.4, random.choice((ROSA_TEDDY, (255, 220, 240), BLANC)),
                                          vida=22, mida=3))
        AUDIO.so("ting")

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
        factor = 0.5 if supervivencia else (MONEDES_REPETICIO if getattr(self, "repeticio", False) else 1)
        monedes = max(1, round(e.monedes * self.dificultat()["monedes"] * factor))
        xp = max(1, e.xp // 2) if supervivencia else e.xp
        self.monedes += monedes
        self.monedes_nivell += monedes
        self.xp_nivell += xp
        self.afegir_xp(xp)
        self.comptar("baixes", "baixes", 500)
        arma_id = ARMES[self.arma_actual]["id"]
        self.afegir_baixa_arma(arma_id)
        self.registrar_baixa(e)
        self.progres_repte("baixes")
        self.progres_repte("baixes_arma", a=arma_id)
        self.progres_repte("baixes_tipus", a=self.clau_bestiari(e))
        if e.es_boss:
            self.progres_repte("caps")
        if self.dron_company:
            self.dron_company.celebrar(self.efectes)
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
            if e.hd:                                           # sense la seva veu, els seus soldats cauen
                for o in self.enemics:
                    if not o.es_boss:
                        o.vida = 0
                self.efectes.append(Anell(cx, cy, ROSA, r=20, creix=9, vida=24))
            self.flaix = max(self.flaix, 10)                   # sense congelar: flaix i sacseig
            self.tremolor = max(self.tremolor, 12)
            return
        self.aturada = max(self.aturada, 2)
        if e.tipus == "kamikaze":
            self.explosio_kamikaze(e, ferir_jugador=False)
        if self.efecte != "normal" and e.tipus != "kamikaze":     # cosmètic d'eliminació
            self.restes.append(EfecteBaixa(e, self.efecte, self.efectes))
        else:
            if e.hd_e and e.tipus in ("soldat", "escut"):
                self.restes.append(MortTerra(e))
            elif not (e.hd_e and e.tipus == "kamikaze"):
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
            self.efectes_cosmetics(j, mx)
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
                if e.hd:
                    self.atacs_comandant(e, j, rj)
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
            if b.estil == "eixam" and 8 < b.t < 80:          # l'eixam del Guardià persegueix el jugador
                jx, jy = j.centre
                a = math.atan2(b.vy, b.vx)
                gir = (math.atan2(jy - b.y, jx - b.x) - a + math.pi) % math.tau - math.pi
                a += max(-0.07, min(0.07, gir))
                vel = min(4.4, math.hypot(b.vx, b.vy) + 0.05)
                b.vx, b.vy = math.cos(a) * vel, math.sin(a) * vel
            if b.actualitzar():
                self.bales_enemics.remove(b)
                continue
            if b.y >= TERRA_Y + 2 and b.vy > 0:
                if b.estil == "beina":                        # la beina esclata en espores
                    for k in range(6):
                        a = math.radians(-160 + k * 28)
                        self.bales_enemics.append(Bala(b.x, TERRA_Y - 4, math.cos(a) * 3.6, math.sin(a) * 3.6, b.dany,
                                                       "espora"))
                    esclat(self.efectes, b.x, TERRA_Y - 4, 16, [(220, 236, 60), (150, 200, 40), (250, 255, 200)],
                           vel=(1, 4), mida=(2, 4), vida=(14, 30))
                    AUDIO.so("impacte", 70)
                self.pols_impacte(b)
                self.bales_enemics.remove(b)
                continue
            if self.fase == "jugant" and not j.intocable and rj.colliderect(b.rect):
                self.bales_enemics.remove(b)
                self.ferir_jugador(b.dany)
        for o in self.ones_xoc[:]:                         # ones del cop de terra del Comandant
            if o.actualitzar(self.efectes):
                self.ones_xoc.remove(o)
            elif self.fase == "jugant" and not j.intocable and rj.colliderect(o.rect):
                self.ferir_jugador(o.dany)

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
                self.progres_repte("objectes")

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
                self.progres_repte("onada", self.onada + 1, maxim=True)
                self.punts += 100 * self.onada
                self.espera_onada = 150
                j.vida = min(j.vida_max, j.vida + 10)
                AUDIO.so("passi")
            elif self.onada + 1 < len(self.onades):
                self.espera_onada = 110
                if self.mode == "desafiament":               # entre jefe y jefe: vida y munición
                    j.vida = min(j.vida_max, j.vida + 40)
                    self.bales_armes = [self.bales_max(i) for i in range(len(ARMES))]
                AUDIO.so("boss")
            else:
                self.fase, self.temps_fase = "net", 0
                self.bales_enemics.clear()
                self.radio.buidar()
                if self.mode == "desafiament":
                    self.completar_desafiament()
                else:
                    self.completar_escenari()
        elif self.fase == "mort" and self.temps_fase > 75:
            if self.mode == "supervivencia":
                self.mostrar_fi_supervivencia()
            else:
                self.mostrar_derrota()
        elif self.fase == "net" and self.temps_fase > 220 and self.mode == "desafiament":
            self.entrar_desafiaments()
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
        # estrelles: completar, abans del temps i sense rebre mal (la més difícil, l'última)
        noves = [True, self.temps_joc <= TEMPS_ESTRELLA[(n, e)] * FPS, self.dany_rebut == 0]
        self.progres_repte("escenaris")
        if self.dany_rebut == 0:
            self.progres_repte("sense_dany")
        if all(noves):
            self.progres_repte("tres_estrelles")
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
        if self.mode == "desafiament" and "dificultat" in DESAFIAMENTS[self.mode_desafiament]:
            return DESAFIAMENTS[self.mode_desafiament]["dificultat"]
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
        for i, item in enumerate(llista):
            tipus, vida = item[0], item[1]
            e = self.crear_enemic(tipus, vida, nivell=item[2] if len(item) > 2 else None)
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
            if self.mode == "desafiament":
                noms = DESAFIAMENTS[self.mode_desafiament]["noms"]
                self.nom_cap = noms[min(self.onada, len(noms) - 1)]
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
            self.progres_repte("voltes")

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
        if e.hd:
            e.presentar(pr["t"], self.jugador)
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
        b.append(Boto((30, HEIGHT - 62, 140, 42), "< Volver", self.entrar_jugar, GRIS_FOSC))
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
        """Desbloqueja un logro: avís a la pantalla, monedes i XP de premi i desat."""
        if ident in self.logros or ident not in LOGRO_PER_ID:
            return
        self.logros.add(ident)
        logro = LOGRO_PER_ID[ident]
        self.monedes += CATEGORIES_LOGRO[logro["cat"]]["monedes"]
        self.avisos_logro.append([logro, 0])
        AUDIO.so("passi")
        self.afegir_xp(XP_LOGRO.get(logro["cat"], 0))
        if ident != "plati" and all(l["id"] in self.logros for l in LOGROS if l["id"] != "plati"):
            self.desbloquejar("plati")
        self.desar_progres()

    # ----- Desafiaments --------------------------------------------------------------------------------

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

    def caixa_idioma(self):
        r = self.rect_icona_barra(0)
        return pygame.Rect(r.x, r.y - 154, 216, 146)

    def rects_idioma(self):
        c = self.caixa_idioma()
        return {codi: pygame.Rect(c.x + 8, c.y + 8 + k * 44, 200, 38) for k, codi in enumerate(IDIOMES)}

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
        for k, tipus in enumerate(self.icones_barra()):
            r = self.rect_icona_barra(k)
            hover = r.collidepoint(pos) or (tipus == "idioma" and self.menu_idioma)
            pygame.draw.rect(surf, NEGRE, r.move(0, 3), border_radius=8)
            pygame.draw.rect(surf, (52, 60, 110) if hover else (30, 34, 66), r, border_radius=8)
            pygame.draw.rect(surf, BLAU_CLAR if hover else (80, 90, 140), r, 2, border_radius=8)
            if tipus in ("guia", "opcions", "credits", "sortir"):
                dibuixar_icona_menu(surf, tipus, r.centerx, r.centery, self.t_global if hover else 0)
                if hover:
                    etiqueta = {"guia": "Guía", "opcions": "Opciones", "credits": "Créditos", "sortir": "Salir"}[tipus]
                    text(surf, T(etiqueta), F_MINI, BLANC, (r.centerx, r.y - 12))
            elif tipus == "idioma":
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
            caixa = self.caixa_idioma()
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
        self.iniciar_tutorial(lambda: self.entrar_ajuda(despres=self.entrar_menu, pagines=range(4)))

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
    def entrar_ajuda(self, pagina=0, despres=None, pagines=None):
        if despres is not None:
            self.ajuda_despres = despres
            self.pagines_ajuda = list(pagines) if pagines is not None else list(range(len(self.PAGINES_AJUDA)))
        elif pagines is not None:
            self.pagines_ajuda = list(pagines)
        llista = getattr(self, "pagines_ajuda", None) or list(range(len(self.PAGINES_AJUDA)))
        self.pagines_ajuda = llista
        pagina = max(0, min(len(llista) - 1, pagina))
        self.pagina_ajuda = pagina
        ultima = pagina == len(llista) - 1
        final = "¡A jugar!" if self.ajuda_despres == self.entrar_menu else "Entendido"
        b = [Boto((WIDTH // 2 + 20, HEIGHT - 62, 220, 46), final if ultima else "Siguiente  >",
                  self.ajuda_despres if ultima else (lambda: self.entrar_ajuda(pagina + 1)), VERD if ultima else BLAU)]
        if pagina > 0:
            b.append(Boto((WIDTH // 2 - 240, HEIGHT - 62, 220, 46), "<  Anterior", lambda: self.entrar_ajuda(pagina - 1),
                          GRIS_FOSC))
        if len(llista) > 1:
            b.append(Boto((WIDTH - 126, 16, 110, 30), "Saltar  >>", self.ajuda_despres, GRIS_FOSC, font=F_MINI))
        self.botons = b
        self.canviar_estat("ajuda")

    PAGINES_AJUDA = ("BATTLE PASS", "MEJORAS", "ARMAS Y POTENCIA", "ESTRELLAS, LOGROS Y SUPERVIVENCIA",
                     "MAESTRÍA Y CAMUFLAJES", "RANGOS", "BESTIARIO", "DESAFÍOS", "DIARIO")

    def dibuixar_ajuda(self, surf):
        self.fons_menu.dibuixar(surf)
        llista = self.pagines_ajuda
        p = llista[self.pagina_ajuda]
        text(surf, T(self.PAGINES_AJUDA[p]), F_SUBTITOL, GROC, (WIDTH // 2, 40))
        if len(llista) > 1:
            x0 = WIDTH // 2 - (len(llista) - 1) * 10
            for k in range(len(llista)):
                pygame.draw.circle(surf, BLANC if k == self.pagina_ajuda else GRIS_FOSC, (x0 + k * 20, 72), 5)
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
            "Son 50 niveles por temporada y cada uno pide un poco más de XP.",
            "Cada nivel da monedas o algo exclusivo: aspectos, estelas, drones, tarjetas y más.",
            "Lo conseguido se equipa en Personalizar: haz clic en Nexus en el menú.",
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
            noms = ["Completado", "A tiempo", "Sin recibir daño"]
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
            "Estrellas: cada escenario da tres, por completarlo, por acabarlo a tiempo y por no recibir daño.",
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
        self.dron_company = None
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
        elif self.mode == "desafiament":
            linia1 = T(DESAFIAMENTS[self.mode_desafiament]["nom"]).upper() + " · " + \
                T("Oleada {o} de {n}").format(o=self.onada + 1, n=len(self.onades))
            linia2 = self.format_temps(self.temps_joc)
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
            dibuixar_estrella(surf, r2.left - 26, 58, 6, a_temps)                  # mateix ordre que al final:
            dibuixar_estrella(surf, r2.left - 10, 58, 6, self.dany_rebut == 0, (255, 140, 140))   # temps, sense mal

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
            panell_hud(surf, rr, VERD if actual else (None if usable else (200, 60, 70)), 210 if actual else 150)
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
            base, _ = (RETRAT_COMANDANT, None) if cap.hd else cap.imatge()
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
        col = VERMELL if self.avis_bales else color_mira(self.mira, self.t_global)
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
            base = color_mira(self.mira, self.t_global)
            c = tuple(int(base[k] + ((255, 115, 40)[k] - base[k]) * q) for k in range(3)) if not self.sobreescalfat else VERMELL
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
            pygame.draw.polygon(surf, col, punts, 2)
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
        elif clau == "comandant":
            img = self.imatge_novetat("comandant", RETRAT_COMANDANT or SPR_ENEMIC.get("final_comandant"), 46)
            if img:
                l = llum(26, (255, 80, 200))
                l.set_alpha(int(110 + 60 * math.sin(t * 0.1)))
                surf.blit(l, l.get_rect(center=(cx, cy + 6)))
                l.set_alpha(255)
                surf.blit(img, img.get_rect(center=(cx, cy)))
        elif clau in ("nau", "nucli"):
            img = self.imatge_novetat(clau, SPR_ENEMIC.get("final_" + clau), 50)
            if img:
                surf.blit(img, img.get_rect(center=(cx, cy)))
        elif clau == "jefe":
            img = self.imatge_novetat("jefe", SPR_ENEMIC.get(("boss", 0)), 40)
            if img:
                surf.blit(img, img.get_rect(center=(cx, cy)))
        elif clau == "enemic" and "soldat" in ENEMICS_HD:
            img, (dx, dy) = frame_hd("soldat", "camina", t // 6)
            surf.blit(img, (cx + dx, cy + 26 + dy))
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
        elif clau == "rang":
            dibuixar_insignia(surf, cx, cy, 4 + (t // 60) % 10, 30)
        elif clau == "dron":
            img = sprite_dron(("bit", "ovni", "medic", "daurat")[(t // 60) % 4])
            if img:
                surf.blit(img, img.get_rect(center=(cx, cy)))
        elif clau == "diari":                        # full de calendari
            pygame.draw.rect(surf, NEGRE, (cx - 15, cy - 13, 32, 30), border_radius=3)
            pygame.draw.rect(surf, (235, 232, 215), (cx - 16, cy - 15, 32, 30), border_radius=3)
            pygame.draw.rect(surf, VERMELL, (cx - 16, cy - 15, 32, 9), border_top_left_radius=3, border_top_right_radius=3)
            text(surf, str(time.localtime().tm_mday), F_HUD, NEGRE, (cx, cy + 4), ombra=False)
        elif clau == "moneda":
            dibuixar_moneda(surf, cx, cy, 13)
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

    def carregar_contingut(self, d):
        """Camps del contingut desbloquejable (v3.5). Les partides antigues no perden res."""
        self.cosmetics |= COSMETICS_INICIALS
        equip = d.get("equipat", {}) if isinstance(d.get("equipat"), dict) else {}
        def equipat(tipus, defecte):
            v = equip.get(tipus)
            return v if v in CATALEG_COSMETIC[tipus] and PREFIX_COSMETIC[tipus] + str(v) in self.cosmetics else defecte
        self.estela = equipat("estela", "normal")
        self.efecte = equipat("efecte", "normal")
        self.mira = equipat("mira", "blanc")
        self.tema = equipat("tema", "classic")
        self.targeta = equipat("targeta", "estels")
        self.dron = equipat("dron", "cap")
        camos = equip.get("camos") if isinstance(equip.get("camos"), dict) else {}
        self.camos = {a: c for a, c in camos.items() if a in ARMA_PER_ID and c in CAMUFLATGES}
        ba = d.get("baixes_arma") if isinstance(d.get("baixes_arma"), dict) else {}
        self.baixes_arma = {a["id"]: int(ba.get(a["id"], 0)) if isinstance(ba.get(a["id"], 0), int) else 0 for a in ARMES}
        self.temporada = d.get("temporada") if isinstance(d.get("temporada"), int) and d.get("temporada") > 0 else 1
        if isinstance(d.get("xp_passi"), int):
            self.xp_passi = d["xp_passi"]
        else:                                    # partida antiga: es manté el nivell que ja tenia
            antic = min(20, self.xp // 200)
            parcial = self.xp % 200 if antic < 20 else 0
            self.xp_passi = ACUM_PASSI[antic] + min(parcial, xp_nivell_passi(antic) - 1)
        self.passi_reclamat = max(0, min(len(PASSI), self.passi_reclamat))
        self.rang_reclamat = d.get("rang_reclamat") if isinstance(d.get("rang_reclamat"), int) else None
        des = d.get("desafiaments") if isinstance(d.get("desafiaments"), dict) else {}
        self.desafiaments = {k: v for k, v in des.items() if k in DESAFIAMENTS and isinstance(v, dict)}
        rep = d.get("reptes") if isinstance(d.get("reptes"), dict) else {}
        self.reptes = rep if isinstance(rep.get("llista"), list) else {}
        self.mode_desafiament = None
        TEMA_HUD[0] = TEMES_HUD.get(self.tema, TEMES_HUD["classic"])
        self.revelacions = []
        vistos = d.get("vistos") if isinstance(d.get("vistos"), dict) else None
        if vistos is None:                       # primera vegada amb la v3.6: tot el que ja tenies compta com a vist
            vistos = {"inicial": True, "ajudes": []}
        self.vistos = vistos
        cu = d.get("codis")
        self.codis_usats = [c for c in cu if isinstance(c, str)] if isinstance(cu, list) else []

    def dades_contingut(self):
        return {"xp_passi": self.xp_passi, "temporada": self.temporada, "baixes_arma": self.baixes_arma,
                "rang_reclamat": self.rang_reclamat, "desafiaments": self.desafiaments, "reptes": self.reptes,
                "vistos": self.vistos, "codis": self.codis_usats}

    def equipament(self):
        return {"uniforme": self.uniforme, "arma": self.aparenca, "titol": self.titol, "estela": self.estela,
                "efecte": self.efecte, "mira": self.mira, "tema": self.tema, "targeta": self.targeta, "dron": self.dron,
                "camos": self.camos}

    # ----- Battle Pass per temporades ------------------------------------------------------

    def progres_passi(self):
        """(nivell, XP dins del nivell, XP que cal per al següent)."""
        n = self.nivell_passi()
        if n >= len(PASSI):
            return n, 1, 1
        return n, self.xp_passi - ACUM_PASSI[n], xp_nivell_passi(n)

    def atorgar(self, tipus, valor, revelar=True):
        """Dona una recompensa. Torna False si era un cosmètic que ja tenies."""
        if tipus == "monedes":
            self.monedes += valor
            return True
        clau = PREFIX_COSMETIC[tipus] + valor
        if clau in self.cosmetics:
            return False
        self.cosmetics.add(clau)
        if revelar:
            self.revelar("cosmetic", (tipus, valor))
        return True

    # ----- Rangs ---------------------------------------------------------------------------

    def rang_actual(self):
        return max(i for i, r in enumerate(RANGS) if self.xp >= r["xp"])

    def revisar_rangs(self):
        rang = self.rang_actual()
        if self.rang_reclamat is None:           # partida antiga: es reclamen en silenci els rangs ja assolits
            self.rang_reclamat = 0
        while self.rang_reclamat < rang:
            self.rang_reclamat += 1
            self.revelar("rang", self.rang_reclamat)
            r = RANGS[self.rang_reclamat]
            for tipus, valor in r["premi"]:
                self.atorgar(tipus, valor)
            premis = ", ".join(nom_premi(t, v) for t, v in r["premi"])
            self.avis(T("¡Ascenso a {r}!").format(r=T(r["nom"])) + (f" {premis}" if premis else ""), GROC, 300)
            AUDIO.so("passi")

    # ----- Maestria d'armes ------------------------------------------------------------------

    def nivell_mestria(self, arma_id):
        b = self.baixes_arma.get(arma_id, 0)
        return max(i + 1 for i, cal in enumerate(MAESTRIA) if b >= cal)

    def tot_or(self):
        return all(self.nivell_mestria(a["id"]) >= 10 for a in ARMES)

    def camo_obert(self, arma_id, camo):
        if camo == "diamant":
            return self.tot_or()
        return self.nivell_mestria(arma_id) >= CAMUFLATGES[camo]["nivell"]

    def afegir_baixa_arma(self, arma_id):
        abans = self.nivell_mestria(arma_id)
        diamant_abans = self.tot_or()
        self.baixes_arma[arma_id] = self.baixes_arma.get(arma_id, 0) + 1
        ara = self.nivell_mestria(arma_id)
        if ara > abans:
            self.monedes += 50 * ara
            nom = T(ARMES[ARMA_PER_ID[arma_id]]["nom"])
            camo = next((c for c, d in CAMUFLATGES.items() if d["nivell"] == ara and c not in ("cap", "diamant")), None)
            txt = T("¡{a}: maestría nivel {n}! +{m} monedas").format(a=nom, n=ara, m=50 * ara)
            if camo:
                txt += " · " + T("Camuflaje {c} desbloqueado").format(c=T(CAMUFLATGES[camo]["nom"]))
                self.revelar("camo", (arma_id, camo))
            self.avis(txt, (255, 200, 120), 280)
            AUDIO.so("passi")
        if not diamant_abans and self.tot_or():
            self.revelar("camo", (arma_id, "diamant"))
            self.atorgar("titol", "mestre")
            self.avis(T("¡Todas las armas en oro! Camuflaje Diamante y título «Maestro de armas»"), (150, 230, 255), 360)

    def camo_actual(self, i=None):
        arma = ARMES[self.arma_actual if i is None else i]["id"]
        c = self.camos.get(arma)
        return c if c and c != "cap" and self.camo_obert(arma, c) else None

    # ----- Bestiari ----------------------------------------------------------------------------
    @staticmethod

    def clau_bestiari(e):
        if e.tipus == "boss":
            return f"boss_{max(0, min(4, e.nivell))}"
        return e.tipus

    def baixes_bestiari(self, clau):
        return self.estadistiques.get("k_" + clau, 0)

    def bestiari_complet(self):
        return all(self.baixes_bestiari(b["clau"]) >= b["cal"] for b in BESTIARI)

    def registrar_baixa(self, e):
        clau = self.clau_bestiari(e)
        abans = self.baixes_bestiari(clau)
        self.estadistiques["k_" + clau] = abans + 1
        entrada = next((b for b in BESTIARI if b["clau"] == clau), None)
        if entrada is None:
            return
        if abans == 0:
            self.avis(T("Bestiario: nueva ficha · {n}").format(n=T(entrada["nom"])), CIAN, 220)
        elif abans + 1 == entrada["cal"]:
            self.avis(T("Bestiario: historia desbloqueada · {n}").format(n=T(entrada["nom"])), CIAN, 220)
            if self.bestiari_complet():
                self.atorgar("targeta", "xenobio")
                self.atorgar("titol", "xenobioleg")
                self.avis(T("¡Bestiario completo! Tarjeta Xenobiología y título «Xenobiólogo»"), CIAN, 360)

    # ----- Reptes diaris ---------------------------------------------------------------------------
    @staticmethod

    def data_avui():
        return time.strftime("%Y-%m-%d")

    def generar_reptes(self):
        avui = self.data_avui()
        if self.reptes.get("data") == avui:
            return
        rnd = random.Random("reptes-" + avui)
        tipus_enemics = ["dron", "soldat", "lloctinent"]
        if self.nivells_desbloquejats[1][0]:
            tipus_enemics.append("kamikaze")
        if self.nivells_desbloquejats[2][0]:
            tipus_enemics.append("escut")
        if self.nivells_desbloquejats[3][0]:
            tipus_enemics.append("cacador")
        pool = [r for r in REPTES_POOL if r[0] != "onada" or self.completats[0][2]]
        triats, vistos = [], set()
        while len(triats) < 3 and pool:
            r = rnd.choice(pool)
            if r[0] in vistos:
                pool.remove(r)
                continue
            vistos.add(r[0])
            a = None
            if r[0] == "baixes_arma":
                a = rnd.choice(sorted(self.armes_propies))
            elif r[0] == "baixes_tipus":
                a = rnd.choice(tipus_enemics)
            triats.append({"tipus": r[0], "objectiu": r[1], "text": r[2], "a": a, "progres": 0, "fet": False})
        self.reptes = {"data": avui, "llista": triats, "bonus": False}

    def text_repte(self, r):
        a = r.get("a")
        if r["tipus"] == "baixes_arma" and a in ARMA_PER_ID:
            a = T(ARMES[ARMA_PER_ID[a]]["nom"])
        elif r["tipus"] == "baixes_tipus":
            entrada = next((b for b in BESTIARI if b["clau"] == a), None)
            a = T(entrada["nom"]) if entrada else a
        return T(r["text"]).format(n=r["objectiu"], a=a)

    def progres_repte(self, tipus, quantitat=1, a=None, maxim=False):
        if self.mode in ("tutorial",):
            return
        self.generar_reptes()
        for r in self.reptes.get("llista", []):
            if r["fet"] or r["tipus"] != tipus or (r.get("a") is not None and r.get("a") != a):
                continue
            r["progres"] = max(r["progres"], quantitat) if maxim else r["progres"] + quantitat
            if r["progres"] >= r["objectiu"]:
                r["progres"] = r["objectiu"]
                r["fet"] = True
                self.monedes += PREMI_REPTE[0]
                self.afegir_xp(PREMI_REPTE[1])
                self.avis(T("¡Reto diario completado! +{m} monedas · +{x} XP").format(m=PREMI_REPTE[0], x=PREMI_REPTE[1]),
                          VERD, 280)
                AUDIO.so("passi")
        if not self.reptes.get("bonus") and self.reptes.get("llista") and all(r["fet"] for r in self.reptes["llista"]):
            self.reptes["bonus"] = True
            self.monedes += PREMI_TOTS_REPTES
            self.avis(T("¡Los tres retos de hoy! +{m} monedas extra").format(m=PREMI_TOTS_REPTES), VERD, 300)

    def ofertes_del_dia(self):
        """Quatre cosmètics de la botiga que canvien cada dia (només els que encara no tens)."""
        avui = self.data_avui()
        pool = [(tipus, ident, info["preu"]) for tipus, cat in CATALEG_COSMETIC.items() if isinstance(cat, dict)
                for ident, info in cat.items() if isinstance(info, dict) and info.get("preu")]
        rnd = random.Random("ofertes-" + avui)
        rnd.shuffle(pool)
        pendents = [p for p in pool if PREFIX_COSMETIC[p[0]] + p[1] not in self.cosmetics]
        tinguts = [p for p in pool if PREFIX_COSMETIC[p[0]] + p[1] in self.cosmetics]
        return (pendents + tinguts)[:4]

    def comprar_oferta(self, tipus, ident, preu):
        if PREFIX_COSMETIC[tipus] + ident in self.cosmetics:
            return
        if self.monedes < preu:
            self.mostrar_missatge(T("¡Te faltan {n} monedas!").format(n=preu - self.monedes))
            AUDIO.so("buit")
            return
        self.monedes -= preu
        self.atorgar(tipus, ident, revelar=False)
        self.mostrar_missatge(T("¡{c} desbloqueado! Equípalo en Personalizar (clic en Nexus en el menú).").format(c=nom_premi(tipus, ident)), ok=True)
        AUDIO.so("moneda")
        self.desar_progres()
        self.entrar_botiga("diaria")

    def segons_fins_dema(self):
        t = time.localtime()
        return max(0, 86400 - (t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec))

    # ----- D'on surt cada cosmètic -------------------------------------------------------------------

    def origen_cosmetic(self, tipus, valor):
        for i, recompenses in enumerate(PASSI):
            if (tipus, valor) in recompenses:
                return T("Battle Pass · nivel {n}").format(n=i + 1)
        for r in RANGS:
            if (tipus, valor) in r["premi"]:
                return T("Rango: {r}").format(r=T(r["nom"]))
        for d in DESAFIAMENTS.values():
            if (tipus, valor) in d["premi"]:
                return T("Desafío: {d}").format(d=T(d["nom"]))
        info = CATALEG_COSMETIC[tipus].get(valor)
        if isinstance(info, dict) and info.get("ocult"):
            return T("Código secreto")
        if isinstance(info, dict) and info.get("preu"):
            return T("Ofertas del día · {p} monedas").format(p=info["preu"])
        if (tipus, valor) in (("targeta", "xenobio"), ("titol", "xenobioleg")):
            return T("Completa el bestiario")
        if (tipus, valor) == ("titol", "mestre"):
            return T("Todas las armas en oro")
        return T("Bloqueado")

    def equipar_camo(self, arma_id, camo):
        if not self.camo_obert(arma_id, camo):
            if camo == "diamant":
                self.mostrar_missatge(T("Diamante: pon todas las armas en oro (maestría 10)"))
            else:
                self.mostrar_missatge(T("Llega a maestría {n} con esta arma").format(n=CAMUFLATGES[camo]["nivell"]))
            AUDIO.so("buit")
            return
        self.camos[arma_id] = camo
        AUDIO.so("item")
        self.desar_progres()

    def estrelles_totals(self):
        return sum(sum(e) for fila in self.estrelles for e in fila)

    def iniciar_desafiament(self, ident):
        d = DESAFIAMENTS[ident]
        if self.estrelles_totals() < d["estrelles"]:
            self.mostrar_missatge(T("Necesitas {n} estrellas").format(n=d["estrelles"]))
            AUDIO.so("buit")
            return
        self.mode = "desafiament"
        self.mode_desafiament = ident
        self.nivell_actual, self.escenari_actual = d["fons"]
        AUDIO.musica(d["musica"])
        self.preparar_nivell()
        self.botons = []
        self.canviar_estat("joc")

    def completar_desafiament(self):
        ident = self.mode_desafiament
        d = DESAFIAMENTS[ident]
        reg = self.desafiaments.setdefault(ident, {})
        primera = not reg.get("fet")
        reg["fet"] = True
        if not reg.get("millor") or self.temps_joc < reg["millor"]:
            reg["millor"] = self.temps_joc
            if not primera:
                self.avis(T("¡Nuevo récord: {t}!").format(t=self.format_temps(self.temps_joc)), GROC, 260)
        if primera:
            for tipus, valor in d["premi"]:
                self.atorgar(tipus, valor)
            self.afegir_xp(d["xp"])
            self.xp_nivell += d["xp"]
            premis = ", ".join(nom_premi(t, v) for t, v in d["premi"])
            self.avis(T("¡Desafío superado! {p}").format(p=premis), GROC, 360)
        else:
            self.afegir_xp(d["xp"] // 4)
            self.xp_nivell += d["xp"] // 4
        self.desar_progres()

    @staticmethod

    def format_temps(fotogrames):
        s = fotogrames // FPS
        return f"{s // 60}:{s % 60:02d}"

    def dibuixar_recompensa(self, surf, tipus, valor, centre, t=0):
        """Icona petita d'una recompensa (Battle Pass, rangs, desafiaments)."""
        cx, cy = centre
        if tipus == "monedes":
            dibuixar_moneda(surf, cx, cy - 6, 12)
            text(surf, str(valor), F_MINI, GROC, (cx, cy + 20))
        elif tipus == "uniforme":
            img = mostra_soldat("pistola", valor, "estandard")
            if img:
                surf.blit(img, img.get_rect(center=centre))
        elif tipus == "arma":
            img = mostra_soldat(ARMES[self.arma_actual]["id"], "classic", valor)
            if img:
                surf.blit(img, img.get_rect(center=centre))
        elif tipus == "titol":
            pygame.draw.rect(surf, (230, 210, 160), (cx - 18, cy - 14, 36, 28), border_radius=3)
            pygame.draw.rect(surf, (150, 110, 60), (cx - 18, cy - 14, 36, 28), 2, border_radius=3)
            text(surf, "T", F_UI, (120, 80, 40), centre, ombra=False)
        elif tipus == "estela":
            cols = colors_estela(valor, t)
            for k in range(5):
                pygame.draw.circle(surf, cols[k % len(cols)], (cx - 16 + k * 7, cy + 4 - k * 2), 2 + k)
            pygame.draw.circle(surf, BLANC, (cx + 14, cy - 4), 5)
        elif tipus == "efecte":
            self._icona_efecte(surf, valor, cx, cy, t)
        elif tipus == "mira":
            c = color_mira(valor, t)
            pygame.draw.circle(surf, NEGRE, (cx, cy), 12, 3)
            pygame.draw.circle(surf, c, (cx, cy), 11, 2)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pygame.draw.line(surf, c, (cx + dx * 5, cy + dy * 5), (cx + dx * 15, cy + dy * 15), 2)
        elif tipus == "tema":
            info = TEMES_HUD[valor]
            r = pygame.Rect(cx - 24, cy - 15, 48, 30)
            pygame.draw.rect(surf, info["fons"], r)
            pygame.draw.rect(surf, info["vora"], r, 2)
            for k in range(3):
                dibuixar_cor(surf, r.x + 4 + k * 14, r.y + 5, 12, 1)
            pygame.draw.rect(surf, info["vora"], (r.x + 5, r.bottom - 7, 36, 3))
        elif tipus == "targeta":
            r = pygame.Rect(cx - 28, cy - 17, 56, 34)
            surf.blit(fons_targeta(valor, r.w, r.h), r)
            pygame.draw.rect(surf, BLANC, r, 1)
        elif tipus == "dron":
            img = sprite_dron(valor)
            if img:
                surf.blit(img, img.get_rect(center=(cx, cy + int(2 * math.sin(t * 0.08)))))
            else:
                text(surf, "—", F_UI, GRIS, centre)

    def _icona_efecte(self, surf, ident, cx, cy, t, gran=False):
        """Animació en bucle de l'efecte d'eliminació (sobre un dron)."""
        base = SPR_ENEMIC.get("dron")
        if base is None:
            return
        esc = 0.9 if gran else 0.55
        img = Game.IMATGES_NOVETAT.get(("dron_ef", esc))
        if img is None:
            img = Game.IMATGES_NOVETAT[("dron_ef", esc)] = pygame.transform.scale(
                base, (int(base.get_width() * esc), int(base.get_height() * esc)))
        cicle = t % 90
        if cicle < 30:
            surf.blit(img, img.get_rect(center=(cx, cy)))
            return
        k = (cicle - 30) / 60
        rnd = random.Random(int(t // 90))
        if ident == "normal":
            rot = pygame.transform.rotate(img, -k * 200)
            rot.fill((150, 140, 140, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(rot, rot.get_rect(center=(cx + k * 10, cy + k * k * 30)))
            for i in range(3):
                pygame.draw.circle(surf, (90, 90, 100), (int(cx - i * 4), int(cy - 6 - k * 12 - i * 3)), 3)
        elif ident == "pixels":
            w, h = img.get_size()
            for py in range(0, h, 4):
                for px in range(0, w, 4):
                    c = img.get_at((px, py))
                    if c.a > 100:
                        dx, dy = px - w / 2, py - h / 2
                        x = cx + dx * (1 + k * 1.5)
                        y = cy + dy * (1 + k) - k * 12 + k * k * 30
                        pygame.draw.rect(surf, c, (int(x), int(y), 3, 3))
        elif ident == "confeti":
            for i in range(24):
                a = rnd.uniform(0, math.tau)
                v = rnd.uniform(10, 34)
                x = cx + math.cos(a) * v * k
                y = cy + math.sin(a) * v * k + k * k * 20
                c = rnd.choice(((255, 80, 200), (90, 230, 255), GROC, VERD))
                pygame.draw.rect(surf, c, (int(x), int(y), 3, 2))
        elif ident == "gel":
            if k < 0.5:
                gel = img.copy()
                gel.fill((140, 210, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(gel, gel.get_rect(center=(cx, cy)))
                for i in range(3):
                    a = i * 2.1
                    pygame.draw.line(surf, BLANC, (cx, cy), (cx + math.cos(a) * 14 * k * 2, cy + math.sin(a) * 10 * k * 2))
            else:
                for i in range(14):
                    a = rnd.uniform(0, math.tau)
                    v = rnd.uniform(8, 26) * (k - 0.5) * 2
                    pygame.draw.rect(surf, (190, 235, 255), (int(cx + math.cos(a) * v), int(cy + math.sin(a) * v), 3, 3))
        elif ident == "electric":
            if k < 0.5:
                surf.blit(silueta_blanca(img) if int(t) % 4 < 2 else img, img.get_rect(center=(cx, cy)))
                for _ in range(2):
                    punts = [(cx + rnd.uniform(-16, 16), cy + rnd.uniform(-12, 12)) for _ in range(4)]
                    pygame.draw.lines(surf, (180, 220, 255), False, punts, 2)
            else:
                for i in range(10):
                    pygame.draw.circle(surf, (90, 90, 100), (int(cx + rnd.uniform(-12, 12)),
                                                             int(cy + rnd.uniform(-8, 8) - (k - 0.5) * 20)), 2)
        elif ident == "forat":
            r = int(4 + 14 * k)
            pygame.draw.circle(surf, (20, 6, 30), (cx, cy), r)
            pygame.draw.circle(surf, (190, 90, 255), (cx, cy), r, 2)
            if k < 0.7:
                rot = pygame.transform.rotozoom(img, k * 500, max(0.05, 1 - k / 0.7))
                surf.blit(rot, rot.get_rect(center=(cx, cy)))
        elif ident == "daurat":
            for i in range(8):
                a = -math.pi / 2 + (i - 3.5) * 0.3
                v = 30 * k
                x = cx + math.cos(a) * v
                y = cy + math.sin(a) * v + k * k * 40
                dibuixar_moneda(surf, int(x), int(y), 4)

    def previsualitzar(self, surf, tipus, ident, r, t):
        """Vista prèvia gran d'un cosmètic (Personalitzar)."""
        centre = (r.centerx, r.top + 4 + (r.height - 22) // 2)
        arma_id = ARMES[self.arma_actual]["id"]
        if tipus == "uniforme":
            img = mostra_soldat(arma_id, ident, self.aparenca)
            surf.blit(img, img.get_rect(center=centre))
        elif tipus == "arma":
            img = mostra_soldat(arma_id, self.uniforme, ident)
            surf.blit(img, img.get_rect(center=centre))
            color = APARENCES_ARMA[ident]["bala"] or Bala.ESTILS[ARMES[self.arma_actual]["estil"]][1]
            pygame.draw.circle(surf, color_arc(t) if color == "arc" else color, (r.right - 14, r.top + 14), 6)
        elif tipus == "titol":
            for k, linia in enumerate(ajustar_linies(T(TITOLS[ident]), F_TEXT_P, r.w - 16)[:2]):
                text(surf, linia, F_TEXT_P, BLANC, (r.centerx, centre[1] - 6 + k * 22))
        elif tipus == "estela":
            cols = colors_estela(ident, t)
            clip = surf.get_clip()
            surf.set_clip(r.inflate(-6, -6).clip(clip))
            x = r.x + 20 + (t * 2) % (r.w - 40)
            for k in range(8):
                pygame.draw.circle(surf, cols[k % len(cols)], (int(x - k * 9), centre[1] + int(3 * math.sin((t - k * 3) * 0.2))),
                                   max(1, 8 - k))
            pygame.draw.circle(surf, BLANC, (int(x), centre[1]), 6)
            surf.set_clip(clip)
        elif tipus == "efecte":
            self._icona_efecte(surf, ident, centre[0], centre[1], t, gran=True)
        elif tipus == "mira":
            c = color_mira(ident, t)
            cx, cy = centre
            pygame.draw.circle(surf, NEGRE, (cx, cy), 18, 4)
            pygame.draw.circle(surf, c, (cx, cy), 17, 2)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pygame.draw.line(surf, NEGRE, (cx + dx * 7, cy + dy * 7), (cx + dx * 24, cy + dy * 24), 5)
                pygame.draw.line(surf, c, (cx + dx * 7, cy + dy * 7), (cx + dx * 24, cy + dy * 24), 3)
        elif tipus == "tema":
            info = TEMES_HUD[ident]
            p = pygame.Rect(r.x + 14, r.y + 14, r.w - 28, r.h - 44)
            pygame.draw.rect(surf, info["fons"], p)
            pygame.draw.rect(surf, info["vora"], p, 2)
            for k in range(4):
                dibuixar_cor(surf, p.x + 8 + k * 24, p.y + 8, 18, 1 if k < 3 else 0.5)
            pygame.draw.rect(surf, (40, 40, 60), (p.x + 8, p.bottom - 14, p.w - 16, 6))
            pygame.draw.rect(surf, info["vora"], (p.x + 8, p.bottom - 14, int((p.w - 16) * 0.6), 6))
        elif tipus == "targeta":
            p = pygame.Rect(r.x + 8, r.y + 8, r.w - 16, r.h - 34)
            surf.blit(fons_targeta(ident, p.w, p.h), p)
            dibuixar_insignia(surf, p.x + 20, p.centery, self.rang_actual(), 24)
            pygame.draw.rect(surf, BLANC, p, 1)
        elif tipus == "dron" and ident == "teddy" and TEDDY:
            pose, h = cicle_teddy(t)
            clip = surf.get_clip()
            surf.set_clip(r.inflate(-4, -4).clip(clip))
            posar_teddy(surf, pose, centre[0], centre[1] + 28 + h, 2)
            surf.set_clip(clip)
        elif tipus == "dron":
            img = sprite_dron(ident)
            if img:
                img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
                surf.blit(img, img.get_rect(center=(centre[0], centre[1] + int(3 * math.sin(t * 0.08)))))
            else:
                text(surf, T("Sin dron"), F_TEXT_P, GRIS, centre)

    # ----- Personalitzar (abans Tienda > Aspecto) -------------------------------------------------------
    CATEGORIES_ASPECTE = (("uniforme", "Uniforme"), ("arma", "Aspecto de arma"), ("camo", "Camuflaje"),
                          ("titol", "Título"), ("estela", "Estela"), ("efecte", "Eliminación"), ("mira", "Punto de mira"),
                          ("tema", "HUD"), ("targeta", "Tarjeta"), ("dron", "Dron"))

    def botons_aspecte(self):
        b = []
        cat = getattr(self, "cat_aspecte", "uniforme")
        for k, (ident, nom) in enumerate(self.CATEGORIES_ASPECTE):
            b.append(Boto((30, 124 + k * 34, 150, 30), nom, lambda i=ident: self.triar_cat_aspecte(i),
                          VERD if cat == ident else BLAU, font=F_MINI))
        if cat == "camo":
            arma_id = getattr(self, "arma_camo", ARMES[self.arma_actual]["id"])
            for k, a in enumerate(ARMES):
                b.append(Boto((236 + k * 140, 124, 130, 36), "", lambda i=a["id"]: self.triar_arma_camo(i), invisible=True))
            for k, camo in enumerate(CAMUFLATGES):
                b.append(Boto((236 + k * 140, 170, 130, 170), "", lambda c=camo, a=arma_id: self.equipar_camo(a, c),
                              invisible=True))
        else:
            for k, ident in enumerate(self.cosmetics_visibles(cat)):
                r = self.rect_cosmetic(k)
                b.append(Boto(r, "", lambda v=ident, c=cat: self.equipar_cosmetic(c, v), invisible=True))
        return b

    def cosmetics_visibles(self, cat):
        """Els cosmètics d'una categoria que surten a Personalitzar: els ocults (codis secrets), només si ja els tens."""
        pre = PREFIX_COSMETIC[cat]
        return [i for i, info in CATALEG_COSMETIC[cat].items()
                if not (isinstance(info, dict) and info.get("ocult")) or pre + i in self.cosmetics]

    @staticmethod
    def rect_cosmetic(k):
        col, fila = k % 4, k // 4
        return pygame.Rect(236 + col * 174, 124 + fila * 112, 166, 104)

    def triar_cat_aspecte(self, ident):
        self.cat_aspecte = ident
        if ident == "camo":
            self.arma_camo = ARMES[self.arma_actual]["id"]
        self.entrar_personalitzar()

    def triar_arma_camo(self, arma_id):
        self.arma_camo = arma_id
        self.entrar_personalitzar()

    def equipat_de(self, tipus):
        return {"uniforme": self.uniforme, "arma": self.aparenca, "titol": self.titol}.get(tipus) or getattr(self, tipus)

    def entrar_colleccio(self, pestanya=None):
        self.confirmar_reinici = False
        if self.ajuda_primera_vegada("colleccio", (4, 5, 6), self.entrar_colleccio):
            return
        if pestanya:
            self.pestanya_col = pestanya
        self.pestanya_col = getattr(self, "pestanya_col", "mestria")
        self.marcar_vist("colleccio")
        b = []
        for k, (ident, nom) in enumerate((("mestria", "Maestría"), ("rangs", "Rangos"), ("bestiari", "Bestiario"))):
            b.append(Boto((WIDTH // 2 - 265 + k * 180, 70, 170, 38), nom, lambda i=ident: self.entrar_colleccio(i),
                          VERD if self.pestanya_col == ident else BLAU, font=F_HUD))
        if self.pestanya_col == "bestiari":
            self.sel_bestiari = getattr(self, "sel_bestiari", 0)
            for k in range(len(BESTIARI)):
                b.append(Boto(self.rect_bestiari(k), "", lambda i=k: self.triar_bestiari(i), invisible=True))
        b.append(self.boto_tornar())
        self.botons = b
        self.canviar_estat("colleccio")

    @staticmethod

    def rect_bestiari(k):
        col, fila = k % 7, k // 7
        return pygame.Rect(40 + col * 126, 120 + fila * 104, 118, 96)

    def triar_bestiari(self, k):
        self.sel_bestiari = k
        AUDIO.so("click")

    def sprite_bestiari(self, clau):
        if clau.startswith("boss_"):
            return SPR_ENEMIC.get(("boss", int(clau[5:])))
        return SPR_ENEMIC.get(clau)

    def dibuixar_colleccio(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "COLECCIÓN", F_SUBTITOL, BLANC, (WIDTH // 2, 34))
        getattr(self, "_col_" + self.pestanya_col)(surf)

    def _col_mestria(self, surf):
        for k, arma in enumerate(ARMES):
            fila = pygame.Rect(60, 122 + k * 68, 840, 60)
            propia = arma["id"] in self.armes_propies
            nivell = self.nivell_mestria(arma["id"])
            panell(surf, fila, GROC if nivell >= 10 else (BLAU_CLAR if propia else GRIS_FOSC))
            ic = ICONES_ARMA[arma["id"]][2 if propia else "off"]
            if not propia:
                ic = pygame.transform.scale(ic, (ic.get_width() * 2, ic.get_height() * 2))
            surf.blit(ic, ic.get_rect(center=(fila.x + 50, fila.centery)))
            text(surf, T(arma["nom"]).upper(), F_HUD, BLANC if propia else GRIS, (fila.x + 100, fila.y + 18), ancora="midleft")
            text(surf, T("Nivel {n}/10").format(n=nivell), F_MINI, GROC, (fila.x + 100, fila.y + 40), ancora="midleft")
            b = self.baixes_arma.get(arma["id"], 0)
            barra = pygame.Rect(fila.x + 230, fila.centery - 5, 330, 10)
            pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=5)
            if nivell < 10:
                ini, fi = MAESTRIA[nivell - 1], MAESTRIA[nivell]
                pygame.draw.rect(surf, (255, 200, 120), (barra.x, barra.y, int(barra.w * (b - ini) / (fi - ini)), barra.h),
                                 border_radius=5)
                text(surf, f"{b}/{fi}", F_MINI, BLANC, (barra.centerx, barra.y - 9))
            else:
                pygame.draw.rect(surf, GROC, barra, border_radius=5)
                text(surf, T("{b} bajas").format(b=b), F_MINI, BLANC, (barra.centerx, barra.y - 9))
            for j, camo in enumerate(("bronze", "plata", "or", "diamant")):
                cx, cy = fila.x + 610 + j * 56, fila.centery
                obert = self.camo_obert(arma["id"], camo)
                color = CAMUFLATGES[camo]["tint"]
                pygame.draw.circle(surf, NEGRE, (cx, cy + 2), 17)
                pygame.draw.circle(surf, color if obert else (50, 52, 70), (cx, cy), 16)
                pygame.draw.circle(surf, BLANC if obert else GRIS_FOSC, (cx, cy), 16, 2)
                if obert:
                    pygame.draw.lines(surf, NEGRE, False, [(cx - 7, cy), (cx - 2, cy + 6), (cx + 8, cy - 6)], 3)
        text(surf, "Sube cada arma eliminando enemigos: bronce (4), plata (7), oro (10). Todas en oro: diamante.",
             F_TEXT_PP, CIAN, (WIDTH // 2 + 80, 499))

    def _col_rangs(self, surf):
        rang = self.rang_actual()
        cap = pygame.Rect(60, 118, 840, 96)
        panell(surf, cap, GROC)
        dibuixar_insignia(surf, cap.x + 54, cap.centery, rang, 62)
        text(surf, T(RANGS[rang]["nom"]).upper(), F_GRAN, BLANC, (cap.x + 110, cap.y + 30), ancora="midleft")
        text(surf, T("{x} XP en total").format(x=self.xp), F_HUD, GROC, (cap.x + 110, cap.y + 58), ancora="midleft")
        if rang < len(RANGS) - 1:
            seg = RANGS[rang + 1]
            barra = pygame.Rect(cap.x + 470, cap.y + 52, 340, 12)
            pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=5)
            fr = (self.xp - RANGS[rang]["xp"]) / (seg["xp"] - RANGS[rang]["xp"])
            pygame.draw.rect(surf, GROC, (barra.x, barra.y, int(barra.w * fr), barra.h), border_radius=5)
            text(surf, T("Siguiente: {r} ({x} XP)").format(r=T(seg["nom"]), x=seg["xp"]), F_MINI, BLANC,
                 (barra.centerx, barra.y - 12))
        else:
            text(surf, T("¡Rango máximo!"), F_HUD, GROC, (cap.x + 640, cap.centery))
        pos = ratoli()
        info = None
        for i, r in enumerate(RANGS):
            col, fila = i % 5, i // 5
            cel = pygame.Rect(60 + col * 170, 226 + fila * 82, 160, 74)
            assolit = i <= rang
            panell(surf, cel, VERD if i == rang else (BLAU_CLAR if assolit else GRIS_FOSC))
            dibuixar_insignia(surf, cel.x + 24, cel.centery - 2, i, 28)
            for k, linia in enumerate(ajustar_linies(T(r["nom"]), F_TEXT_PP, 112)[:2]):
                text(surf, linia, F_TEXT_PP, BLANC if assolit else GRIS, (cel.x + 46, cel.y + 18 + k * 17), ancora="midleft")
            text(surf, f"{r['xp']} XP", F_MINI, GRIS, (cel.x + 46, cel.bottom - 12), ancora="midleft")
            if cel.collidepoint(pos):
                info = T(r["nom"]) + ": " + (", ".join(nom_premi(t, v) for t, v in r["premi"]) or T("sin recompensa"))
        text(surf, info or "Toda la XP que ganas cuenta para tu rango. Cada ascenso da una recompensa.",
             F_TEXT_PP, CIAN, (WIDTH // 2 + 80, 499))

    def _col_bestiari(self, surf):
        fitxes = sum(self.baixes_bestiari(b["clau"]) > 0 for b in BESTIARI)
        histories = sum(self.baixes_bestiari(b["clau"]) >= b["cal"] for b in BESTIARI)
        text(surf, T("Fichas {a}/{t} · Historias {b}/{t}").format(a=fitxes, b=histories, t=len(BESTIARI)), F_HUD,
             CIAN, (WIDTH // 2 + 80, 499))
        for k, entrada in enumerate(BESTIARI):
            r = self.rect_bestiari(k)
            n = self.baixes_bestiari(entrada["clau"])
            sel = k == self.sel_bestiari
            panell(surf, r, VERD if sel else (GROC if n >= entrada["cal"] else (BLAU_CLAR if n else GRIS_FOSC)))
            img = self.imatge_novetat(("best", entrada["clau"]), self.sprite_bestiari(entrada["clau"]), 54)
            if img is not None:
                if not n:
                    img = Game.IMATGES_NOVETAT.get(("ombra", entrada["clau"]))
                    if img is None:
                        base = self.imatge_novetat(("best", entrada["clau"]), self.sprite_bestiari(entrada["clau"]), 54)
                        img = base.copy()
                        img.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
                        Game.IMATGES_NOVETAT[("ombra", entrada["clau"])] = img
                surf.blit(img, img.get_rect(center=(r.centerx, r.y + 34)))
            if not n:
                text(surf, "???", F_HUD, GRIS, (r.centerx, r.bottom - 14))
            else:
                linies = ajustar_linies(T(entrada["nom"]), F_TEXT_PP, r.w - 8)[:2]
                for j, linia in enumerate(linies):
                    text(surf, linia, F_TEXT_PP, BLANC, (r.centerx, r.bottom - 12 - (len(linies) - 1 - j) * 16))
        e = BESTIARI[self.sel_bestiari]
        n = self.baixes_bestiari(e["clau"])
        det = pygame.Rect(40, 334, 880, 128)
        panell(surf, det, BLAU_CLAR)
        img = self.imatge_novetat(("best_g", e["clau"]), self.sprite_bestiari(e["clau"]), 100)
        if img is not None:
            if not n:
                img = img.copy()
                img.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(img, img.get_rect(center=(det.x + 70, det.centery)))
        x = det.x + 140
        if not n:
            text(surf, "???", F_GRAN, GRIS, (x, det.y + 26), ancora="midleft")
            text(surf, "Elimina a este enemigo para descubrir su ficha.", F_TEXT_P, GRIS, (x, det.y + 64), ancora="midleft")
            return
        text(surf, T(e["nom"]).upper(), F_UI, BLANC, (x, det.y + 20), ancora="midleft")
        for k in range(5):
            dibuixar_estrella(surf, x + 8 + k * 18, det.y + 42, 7, k < e["perill"], (255, 110, 90))
        text(surf, T("Eliminados: {n}").format(n=n), F_MINI, GROC, (det.right - 16, det.y + 20), ancora="midright")
        y = det.y + 58
        for linia in ajustar_linies(T(e["desc"]), F_TEXT_PP, det.right - x - 16)[:2]:
            text(surf, linia, F_TEXT_PP, (210, 215, 235), (x, y), ancora="midleft")
            y += 18
        if n >= e["cal"]:
            for linia in ajustar_linies(T(e["lore"]), F_TEXT_PP, det.right - x - 16)[:2]:
                text(surf, linia, F_TEXT_PP, CIAN, (x, y), ancora="midleft")
                y += 18
        else:
            text(surf, T("Historia: elimina {f} más ({n}/{c})").format(f=e["cal"] - n, n=n, c=e["cal"]), F_TEXT_PP,
                 (255, 170, 120), (x, y), ancora="midleft")

    # ----- Desafíos -------------------------------------------------------------------------------

    def entrar_desafiaments(self):
        self.confirmar_reinici = False
        if self.ajuda_primera_vegada("desafiaments", (7,), self.entrar_desafiaments):
            return
        self.mode = "historia"
        b = [Boto((30, HEIGHT - 62, 140, 42), "< Volver", self.entrar_jugar, GRIS_FOSC)]
        estrelles = self.estrelles_totals()
        for k, (ident, d) in enumerate(DESAFIAMENTS.items()):
            r = pygame.Rect(40 + k * 300, 92, 280, 380)
            obert = estrelles >= d["estrelles"]
            b.append(Boto((r.x + 40, r.bottom - 50, 200, 40), "Jugar" if obert else f"{d['estrelles']} ★",
                          (lambda i=ident: self.iniciar_desafiament(i)), VERD if obert else GRIS_FOSC))
        self.botons = b
        self.canviar_estat("desafiaments")

    def dibuixar_desafiaments(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "DESAFÍOS", F_SUBTITOL, GROC, (WIDTH // 2, 40))
        estrelles = self.estrelles_totals()
        r0 = text(surf, f"{estrelles}/45", F_UI, (255, 220, 120), (WIDTH - 24, 40), ancora="midright")
        dibuixar_estrella(surf, r0.left - 18, r0.centery, 11, True)
        t = self.t_global
        for k, (ident, d) in enumerate(DESAFIAMENTS.items()):
            r = pygame.Rect(40 + k * 300, 92, 280, 380)
            obert = estrelles >= d["estrelles"]
            reg = self.desafiaments.get(ident, {})
            panell(surf, r, GROC if reg.get("fet") else (BLAU_CLAR if obert else GRIS_FOSC))
            text(surf, T(d["nom"]).upper(), F_UI, BLANC if obert else GRIS, (r.centerx, r.y + 22))
            text(surf, T(d["sub"]), F_TEXT_PP, CIAN if obert else GRIS, (r.centerx, r.y + 44))
            # il·lustració
            if ident == "rush":
                for j in range(5):
                    img = self.imatge_novetat(("des_b", j), SPR_ENEMIC.get(("boss", j)), 44)
                    if img:
                        surf.blit(img, img.get_rect(center=(r.x + 40 + j * 50, r.y + 96 + int(4 * math.sin(t * 0.06 + j)))))
            else:
                clau = ("boss", 3) if ident == "secret" else "final_nucli"
                img = self.imatge_novetat(("des", ident), SPR_ENEMIC.get(clau), 84)
                if img:
                    if ident == "malson":
                        l = llum(54, (255, 40, 60))
                        surf.blit(l, l.get_rect(center=(r.centerx, r.y + 100)))
                    surf.blit(img, img.get_rect(center=(r.centerx, r.y + 100 + int(3 * math.sin(t * 0.05)))))
            if not obert:
                capa = pygame.Surface((r.w - 4, 100), pygame.SRCALPHA)
                capa.fill((0, 0, 0, 150))
                surf.blit(capa, (r.x + 2, r.y + 52))
                dibuixar_cadenat(surf, r.centerx, r.y + 100)
            y = r.y + 158
            for linia in ajustar_linies(T(d["desc"]), F_TEXT_PP, r.w - 24)[:4]:
                text(surf, linia, F_TEXT_PP, (210, 215, 235) if obert else GRIS, (r.centerx, y))
                y += 17
            y += 6
            text(surf, T("Premio la primera vez:"), F_MINI, GROC, (r.centerx, y))
            y += 18
            for tipus, valor in d["premi"]:
                text(surf, nom_premi(tipus, valor), F_TEXT_PP, BLANC if obert else GRIS, (r.centerx, y))
                y += 17
            if reg.get("millor"):
                text(surf, T("Mejor tiempo: {t}").format(t=self.format_temps(reg["millor"])), F_MINI, VERD,
                     (r.centerx, y + 6))
        if not self.missatge:
            text(surf, "Los desafíos se abren con las estrellas de la historia.", F_TEXT_PP, CIAN, (WIDTH // 2 + 80, 499))

    # ----- Diario: retos de hoy y ofertas del día --------------------------------------------------------

    def entrar_diari(self):
        self.confirmar_reinici = False
        if self.ajuda_primera_vegada("diari", (8,), self.entrar_diari):
            return
        self.generar_reptes()
        self.marcar_vist("diari")
        self.botons = [self.boto_tornar()]
        self.canviar_estat("diari")

    def rect_oferta(self, k):
        return pygame.Rect(54 + k * 218, 128, 202, 300)

    def dibuixar_diari(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "DIARIO", F_SUBTITOL, BLANC, (WIDTH // 2, 36))
        r = text(surf, str(self.monedes), F_UI, GROC, (WIDTH - 24, 36), ancora="midright")
        dibuixar_moneda(surf, r.left - 14, 36)
        esq = pygame.Rect(WIDTH // 2 - 300, 84, 600, 382)
        panell(surf, esq, BLAU_CLAR)
        text(surf, "RETOS DE HOY", F_UI, VERD, (esq.x + 18, esq.y + 22), ancora="midleft")
        s = self.segons_fins_dema()
        text(surf, T("Nuevos retos en {h} h {m} min").format(h=s // 3600, m=s % 3600 // 60), F_MINI, GRIS,
             (esq.x + 4, esq.y - 10), ancora="midleft")
        for k, rep in enumerate(self.reptes.get("llista", [])):
            fila = pygame.Rect(esq.x + 14, esq.y + 46 + k * 100, esq.w - 28, 90)
            panell(surf, fila, VERD if rep["fet"] else GRIS_FOSC)
            for j, linia in enumerate(ajustar_linies(self.text_repte(rep), F_TEXT_P, fila.w - 150)[:2]):
                text(surf, linia, F_TEXT_P, BLANC, (fila.x + 14, fila.y + 18 + j * 22), ancora="midleft")
            barra = pygame.Rect(fila.x + 14, fila.bottom - 22, fila.w - 170, 10)
            pygame.draw.rect(surf, (40, 42, 60), barra, border_radius=5)
            pygame.draw.rect(surf, VERD, (barra.x, barra.y, int(barra.w * rep["progres"] / rep["objectiu"]), barra.h),
                             border_radius=5)
            text(surf, f"{rep['progres']}/{rep['objectiu']}", F_MINI, BLANC, (barra.right + 10, barra.centery),
                 ancora="midleft")
            rm = text(surf, f"+{PREMI_REPTE[0]}", F_HUD, GROC, (fila.right - 14, fila.y + 22), ancora="midright")
            dibuixar_moneda(surf, rm.left - 12, fila.y + 22)
            text(surf, f"+{PREMI_REPTE[1]} XP", F_MINI, (255, 200, 255), (fila.right - 14, fila.y + 46), ancora="midright")
            if rep["fet"]:
                pygame.draw.lines(surf, VERD, False, [(fila.right - 46, fila.bottom - 24), (fila.right - 38, fila.bottom - 15),
                                                      (fila.right - 20, fila.bottom - 34)], 5)
        bonus = self.reptes.get("bonus")
        text(surf, T("Haz los tres: +{m} monedas extra").format(m=PREMI_TOTS_REPTES) + ("  ✓" if bonus else ""), F_TEXT_P,
             VERD if bonus else GROC, (esq.centerx, esq.bottom - 18))
        if not self.missatge:
            text(surf, "Las ofertas del día están en Tienda > Diaria.", F_TEXT_PP, CIAN, (WIDTH // 2, 499))

    FONS_DESAFIAMENT = {}

    def fons_desafiament(self, fons):
        ident = self.mode_desafiament
        f = Game.FONS_DESAFIAMENT.get(ident)
        if f is None:
            if ident == "secret":                     # el laboratori, amb uns altres colors
                f = permutar_canals(fons, (2, 0, 1))
            elif ident == "malson":
                f = fons.copy()
                f.fill((255, 140, 150), special_flags=pygame.BLEND_RGB_MULT)
            else:
                f = fons
            Game.FONS_DESAFIAMENT[ident] = f
        return f

    def rect_boto_menu(self, k):
        return pygame.Rect(36, 262 + k * 48, 316, 42)

    BOTONS_MENU = (("jugar", "JUGAR"), ("botiga", "TIENDA"), ("passi", "BATTLE PASS"), ("colleccio", "COLECCIÓN"),
                   ("diari", "DIARIO"))
    ICONES_BARRA = ("idioma", "logros", "novetats", "guia", "opcions", "credits", "sortir")

    def icones_barra(self):
        return [i for i in self.ICONES_BARRA if i != "sortir" or not WEB]

    def rect_icona_barra(self, k):
        n = len(self.icones_barra())
        return pygame.Rect(WIDTH - 16 - 44 - (n - 1 - k) * 52, HEIGHT - 54, 44, 40)

    @staticmethod

    def rect_destacat():
        return pygame.Rect(WIDTH - 316, 118, 300, 206)

    # ----- Punts vermells de novetat ---------------------------------------------------------------

    def novetats_menu(self):
        v = self.vistos
        if v.pop("inicial", False):
            for que in ("personalitzar", "passi", "colleccio"):
                self.marcar_vist(que)
        camos = sum(self.camo_obert(a["id"], c) for a in ARMES for c in CAMUFLATGES if c != "cap")
        fitxes = sum(self.baixes_bestiari(b["clau"]) > 0 for b in BESTIARI)
        reptes = self.reptes.get("llista", []) if self.reptes.get("data") == self.data_avui() else []
        ofertes = v.get("ofertes") != self.data_avui() and any(
            PREFIX_COSMETIC[t] + i not in self.cosmetics for t, i, _ in self.ofertes_del_dia())
        return {"nexus": bool(self.cosmetics - set(v.get("cosmetics", []))) or camos > v.get("camos", 0),
                "botiga": ofertes,
                "passi": self.passi_reclamat > v.get("passi", 0) and self.temporada == v.get("temporada", 1)
                or self.temporada > v.get("temporada", 1),
                "colleccio": fitxes > v.get("bestiari", 0) or self.rang_actual() > v.get("rang", 0),
                "diari": v.get("diari") != self.data_avui() or any(r["fet"] for r in reptes) and not v.get("diari_fets"),
                "jugar": False}

    def marcar_vist(self, que):
        v = self.vistos
        if que == "personalitzar":
            v["cosmetics"] = sorted(self.cosmetics)
            v["camos"] = sum(self.camo_obert(a["id"], c) for a in ARMES for c in CAMUFLATGES if c != "cap")
        elif que == "passi":
            v["passi"], v["temporada"] = self.passi_reclamat, self.temporada
        elif que == "colleccio":
            v["bestiari"] = sum(self.baixes_bestiari(b["clau"]) > 0 for b in BESTIARI)
            v["rang"] = self.rang_actual()
        elif que == "ofertes":
            v["ofertes"] = self.data_avui()
        elif que == "diari":
            v["diari"] = self.data_avui()
            v["diari_fets"] = True

    # ----- Dibuix del menú ---------------------------------------------------------------------------
    FONS_VIUS = {}

    def fons_viu(self, surf):
        """Fons del menú: els escenaris ja desbloquejats, foscos i desenfocats, que es fonen l'un amb l'altre."""
        oberts = [(n, e) for n in range(NUM_SECTORS) for e in range(3) if self.nivells_desbloquejats[n][e] and e == 0] or [(0, 0)]
        cicle = 600
        i = (self.t_global // cicle) % len(oberts)
        k = (self.t_global % cicle) / 120
        def fons(clau):
            f = Game.FONS_VIUS.get(clau)
            if f is None:
                img = FONS_NIVELLS.get(clau)
                if img is None:
                    return None
                petit = pygame.transform.smoothscale(img, (img.get_width() // 4, img.get_height() // 4))
                f = pygame.transform.smoothscale(petit, (WIDTH + 40, HEIGHT + 20))
                f.fill((95, 95, 120), special_flags=pygame.BLEND_RGB_MULT)
                Game.FONS_VIUS[clau] = f
            return f
        actual = fons(oberts[i])
        desp = int((self.t_global % cicle) / cicle * 40)
        if actual is None:
            self.fons_menu.dibuixar(surf)
            return
        surf.blit(actual, (-desp, -10))
        if k < 1 and len(oberts) > 1:
            anterior = fons(oberts[(i - 1) % len(oberts)])
            anterior.set_alpha(int(255 * (1 - k)))
            surf.blit(anterior, (-40, -10))
            anterior.set_alpha(255)
        surf.blit(DEGRADAT_MENU, (0, 0))
        for x, y, c in self.fons_menu.estrelles[:40]:
            pygame.draw.rect(surf, (150, 150, 190), (int(x), int(y), c, c))

    def actualitzar_menu(self):
        if self.estat == "menu" and getattr(self, "aparador", None):
            self.aparador.actualitzar(self, 506, 450)

    # ----- Panell «Destacat» ---------------------------------------------------------------------------

    def diapositives_destacat(self):
        d = []
        nivell = self.nivell_passi()
        if nivell < len(PASSI):
            d.append("passi")
        self.generar_reptes()
        d.append("repte")
        if any(PREFIX_COSMETIC[t] + i not in self.cosmetics for t, i, _ in self.ofertes_del_dia()):
            d.append("oferta")
        if self.rang_actual() < len(RANGS) - 1:
            d.append("rang")
        d.append("mestria")
        d.append("desafiament")
        return d

    def obrir_destacat(self):
        dia = self.diapositives_destacat()
        actual = dia[(self.t_global // 300) % len(dia)]
        {"passi": self.entrar_passi, "repte": self.entrar_diari, "oferta": lambda: self.entrar_botiga("diaria"),
         "rang": lambda: self.entrar_colleccio("rangs"), "mestria": lambda: self.entrar_colleccio("mestria"),
         "desafiament": self.entrar_desafiaments}[actual]()

    def dibuixar_destacat(self, surf, r):
        dia = self.diapositives_destacat()
        t = self.t_global
        idx = (t // 300) % len(dia)
        f = t % 300
        hover = r.collidepoint(ratoli())
        panell(surf, r, GROC if hover else BLAU_CLAR, 225)
        text(surf, T("DESTACADO"), F_MINI, GROC, (r.x + 14, r.y + 14), ancora="midleft")
        for k in range(len(dia)):
            pygame.draw.circle(surf, BLANC if k == idx else GRIS_FOSC, (r.right - 16 - (len(dia) - 1 - k) * 12, r.y + 14), 3)
        # entrada lliscant
        dx = int(40 * (1 - min(1.0, f / 14)) ** 2)
        clip = surf.get_clip()
        surf.set_clip(r.inflate(-4, -4))
        zona = pygame.Rect(r.x + 12 + dx, r.y + 28, r.w - 24, r.h - 40)
        getattr(self, "_dest_" + dia[idx])(surf, zona, f)
        surf.set_clip(clip)

    def _dest_titol(self, surf, zona, txt, color=BLANC):
        txt = T(txt)
        font = F_HUD if F_HUD.size(txt)[0] <= zona.w - 16 else F_MINI
        text(surf, txt, font, color, (zona.centerx, zona.y + 10))

    def _barra_dest(self, surf, zona, fr, txt, color):
        barra = pygame.Rect(zona.x + 10, zona.bottom - 30, zona.w - 20, 10)
        pygame.draw.rect(surf, (40, 42, 60), barra, border_radius=5)
        pygame.draw.rect(surf, color, (barra.x, barra.y, int(barra.w * max(0.0, min(1.0, fr))), barra.h), border_radius=5)
        text(surf, txt, F_MINI, BLANC, (barra.centerx, barra.bottom + 10))

    def _dest_passi(self, surf, zona, f):
        nivell, fet, cal = self.progres_passi()
        self._dest_titol(surf, zona, T("PRÓXIMA RECOMPENSA · NIVEL {n}").format(n=nivell + 1), (255, 200, 255))
        tipus, valor = PASSI[nivell][0]
        cx, cy = zona.centerx, zona.y + 72
        l = llum(44, (255, 130, 255))
        l.set_alpha(int(120 + 60 * math.sin(f * 0.08)))
        surf.blit(l, l.get_rect(center=(cx, cy)))
        l.set_alpha(255)
        if tipus in ("estela", "efecte", "mira", "tema", "targeta", "dron"):
            self.previsualitzar(surf, tipus, valor, pygame.Rect(cx - 70, cy - 50, 140, 110), f)
        else:
            self.dibuixar_recompensa(surf, tipus, valor, (cx, cy), f)
        text(surf, nom_premi(tipus, valor), F_TEXT_PP, BLANC, (cx, zona.bottom - 50))
        self._barra_dest(surf, zona, fet / cal, f"{fet}/{cal} XP", (255, 130, 255))

    def _dest_repte(self, surf, zona, f):
        self._dest_titol(surf, zona, "RETO DE HOY", VERD)
        reptes = self.reptes.get("llista", [])
        pendents = [r for r in reptes if not r["fet"]]
        if not pendents:
            dibuixar_estrella(surf, zona.centerx, zona.y + 76, 26 + int(3 * math.sin(f * 0.1)), True)
            text(surf, T("¡Retos de hoy completados!"), F_TEXT_P, VERD, (zona.centerx, zona.y + 124))
            return
        rep = pendents[0]
        for j, linia in enumerate(ajustar_linies(self.text_repte(rep), F_TEXT_P, zona.w - 10)[:3]):
            text(surf, linia, F_TEXT_P, BLANC, (zona.centerx, zona.y + 46 + j * 22))
        rm = text(surf, f"+{PREMI_REPTE[0]}", F_HUD, GROC, (zona.centerx + 10, zona.y + 116))
        dibuixar_moneda(surf, rm.left - 12, zona.y + 116)
        self._barra_dest(surf, zona, rep["progres"] / rep["objectiu"], f"{rep['progres']}/{rep['objectiu']}", VERD)

    def _dest_oferta(self, surf, zona, f):
        self._dest_titol(surf, zona, "OFERTA DEL DÍA", (255, 190, 110))
        ofertes = [o for o in self.ofertes_del_dia() if PREFIX_COSMETIC[o[0]] + o[1] not in self.cosmetics]
        tipus, ident, preu = ofertes[(f // 100) % len(ofertes)]
        self.previsualitzar(surf, tipus, ident, pygame.Rect(zona.centerx - 80, zona.y + 24, 160, 110), f)
        text(surf, nom_premi(tipus, ident), F_TEXT_PP, BLANC, (zona.centerx, zona.bottom - 40))
        rm = text(surf, str(preu), F_HUD, GROC, (zona.centerx + 10, zona.bottom - 16))
        dibuixar_moneda(surf, rm.left - 12, zona.bottom - 16)

    def _dest_rang(self, surf, zona, f):
        rang = self.rang_actual()
        self._dest_titol(surf, zona, "PRÓXIMO RANGO", GROC)
        dibuixar_insignia(surf, zona.centerx - 60, zona.y + 76, rang, 44)
        pygame.draw.polygon(surf, BLANC, [(zona.centerx - 12, zona.y + 70), (zona.centerx + 4, zona.y + 78),
                                          (zona.centerx - 12, zona.y + 86)])
        k = 1 + 0.08 * math.sin(f * 0.12)
        dibuixar_insignia(surf, zona.centerx + 60, zona.y + 76, rang + 1, int(48 * k))
        seg = RANGS[rang + 1]
        text(surf, T(seg["nom"]), F_TEXT_P, BLANC, (zona.centerx, zona.y + 124))
        fr = (self.xp - RANGS[rang]["xp"]) / (seg["xp"] - RANGS[rang]["xp"])
        self._barra_dest(surf, zona, fr, f"{self.xp}/{seg['xp']} XP", GROC)

    def _dest_mestria(self, surf, zona, f):
        self._dest_titol(surf, zona, "MAESTRÍA", (255, 200, 120))
        candidats = [a for a in ARMES if a["id"] in self.armes_propies and self.nivell_mestria(a["id"]) < 10] or \
            [a for a in ARMES if a["id"] in self.armes_propies]
        arma = max(candidats, key=lambda a: self.baixes_arma.get(a["id"], 0))
        nivell = self.nivell_mestria(arma["id"])
        seg = next((c for c in ("bronze", "plata", "or") if CAMUFLATGES[c]["nivell"] > nivell), None)
        img = mostra_soldat(arma["id"], self.uniforme, self.aparenca, seg if (f // 40) % 2 and seg else self.camo_actual(ARMA_PER_ID[arma["id"]]))
        surf.blit(img, img.get_rect(center=(zona.centerx, zona.y + 70)))
        text(surf, T(arma["nom"]) + " · " + T("Nivel {n}/10").format(n=nivell), F_TEXT_PP, BLANC, (zona.centerx, zona.y + 118))
        b = self.baixes_arma.get(arma["id"], 0)
        if nivell < 10:
            ini, fi = MAESTRIA[nivell - 1], MAESTRIA[nivell]
            txt = f"{b}/{fi}" + (f" → {T(CAMUFLATGES[seg]['nom'])}" if seg else "")
            self._barra_dest(surf, zona, (b - ini) / (fi - ini), txt, (255, 200, 120))
        else:
            self._barra_dest(surf, zona, 1, T("¡Oro!"), GROC)

    def _dest_desafiament(self, surf, zona, f):
        self._dest_titol(surf, zona, "DESAFÍOS", GROC)
        estrelles = self.estrelles_totals()
        seg = next(((i, d) for i, d in DESAFIAMENTS.items() if not self.desafiaments.get(i, {}).get("fet")), None)
        if seg is None:
            dibuixar_trofeu(surf, zona.centerx, zona.y + 72, 50)
            text(surf, T("¡Todos superados!"), F_TEXT_P, GROC, (zona.centerx, zona.y + 124))
            return
        ident, d = seg
        clau = {"secret": ("boss", 3), "rush": ("boss", 1), "malson": "final_nucli"}[ident]
        img = self.imatge_novetat(("dest_des", ident), SPR_ENEMIC.get(clau), 70)
        if img:
            surf.blit(img, img.get_rect(center=(zona.centerx, zona.y + 68 + int(3 * math.sin(f * 0.08)))))
            if estrelles < d["estrelles"]:
                dibuixar_cadenat(surf, zona.centerx + 34, zona.y + 46)
        text(surf, T(d["nom"]), F_TEXT_P, BLANC, (zona.centerx, zona.y + 118))
        self._barra_dest(surf, zona, estrelles / d["estrelles"], f"{min(estrelles, d['estrelles'])}/{d['estrelles']} ★", GROC)

    # ----- Pantalla JUGAR ---------------------------------------------------------------------------------

    def seguent_escenari(self):
        for n in range(NUM_SECTORS):
            for e in range(3):
                if self.nivells_desbloquejats[n][e] and not self.completats[n][e]:
                    return n, e
        return NUM_SECTORS - 1, 2

    def entrar_jugar(self):
        self.confirmar_reinici = False
        self.mode = "historia"
        n, e = self.seguent_escenari()
        oberta = self.completats[0][2]
        b = [self.boto_tornar(),
             Boto((52, 380, 256, 40), T("Continuar {s}").format(s=f"{n + 1}-{e + 1}"), lambda: self.mostrar_narrativa(n, e), VERD),
             Boto((52, 426, 125, 30), "Elegir nivel", self.entrar_selector, BLAU, font=F_MINI),
             Boto((183, 426, 125, 30), "Archivo", self.entrar_arxiu, (90, 70, 140), font=F_MINI),
             Boto((360, 404, 240, 46), "Jugar" if oberta else "Completa el sector 1",
                  self.entrar_supervivencia if oberta else None, TARONJA, font=F_HUD if oberta else F_MINI),
             Boto((660, 404, 240, 46), "Ver desafíos", self.entrar_desafiaments, GROC, font=F_HUD)]
        self.botons = b
        self.canviar_estat("jugar")

    def dibuixar_jugar(self, surf):
        self.fons_viu(surf)
        t = self.temps_estat
        text(surf, "JUGAR", F_SUBTITOL, BLANC, (WIDTH // 2, 40))
        n, e = self.seguent_escenari()
        cartes = [pygame.Rect(40 + k * 300, 84, 280, 382) for k in range(3)]
        for k, r in enumerate(cartes):
            entrada = max(0.0, min(1.0, (t - k * 5) / 16))
            r.y += int(40 * (1 - entrada) ** 2)
            panell(surf, r, (VERD, TARONJA, GROC)[k], 220)
            vista = pygame.Rect(r.x + 10, r.y + 44, r.w - 20, 170)
            if k == 0:
                text(surf, "HISTORIA", F_UI, BLANC, (r.centerx, r.y + 22))
                fons = FONS_NIVELLS.get((n, e))
                if fons:
                    x = int((t * 0.3) % max(1, fons.get_width() - vista.w * 2))
                    tros = fons.subsurface((min(x, fons.get_width() - vista.w * 2), 140, vista.w * 2, vista.h * 2))
                    surf.blit(pygame.transform.scale(tros, vista.size), vista)
                self._soldat_demo(surf, vista.x + 60 + (t * 2) % (vista.w - 80), vista.bottom - 8, "corre",
                                  ARMES[self.arma_actual]["id"], t)
                text(surf, f"{T('SECTOR')} {n + 1}-{e + 1}", F_HUD, CIAN, (r.centerx, vista.bottom + 18))
                text(surf, T(NOMS_SECTORS[n]), F_TEXT_P, BLANC, (r.centerx, vista.bottom + 40))
                for j, ple in enumerate(self.estrelles[n][e]):
                    dibuixar_estrella(surf, r.centerx - 22 + j * 22, vista.bottom + 63, 8, ple)
            elif k == 1:
                text(surf, "SUPERVIVENCIA", F_UI, BLANC, (r.centerx, r.y + 22))
                pygame.draw.rect(surf, (20, 10, 30), vista)
                clip = surf.get_clip()
                surf.set_clip(vista)
                for j in range(4):
                    img = SPR_ENEMIC.get(("dron", "soldat", "cacador", "kamikaze")[j])
                    if img:
                        x = vista.x + ((t * (1.2 + j * 0.4) + j * 70) % (vista.w + 60)) - 30
                        surf.blit(img, img.get_rect(center=(int(x), vista.y + 40 + j * 36)))
                surf.set_clip(clip)
                onada = 1 + (t // 60) % 20
                text(surf, T("OLEADA {o}").format(o=onada), F_GRAN, TARONJA, (r.centerx, vista.centery))
                millor = max((rr["punts"] for rr in self.records), default=0)
                text(surf, T("Récord: {p} puntos").format(p=millor), F_HUD, GROC, (r.centerx, vista.bottom + 30))
                text(surf, "Oleadas sin fin", F_TEXT_P, BLANC, (r.centerx, vista.bottom + 56))
            else:
                text(surf, "DESAFÍOS", F_UI, BLANC, (r.centerx, r.y + 22))
                pygame.draw.rect(surf, (24, 8, 16), vista)
                for j, (ident, d) in enumerate(DESAFIAMENTS.items()):
                    clau = {"secret": ("boss", 3), "rush": ("boss", 1), "malson": "final_nucli"}[ident]
                    img = self.imatge_novetat(("jug_des", ident), SPR_ENEMIC.get(clau), 58)
                    if img:
                        cx = vista.x + 44 + j * 86
                        surf.blit(img, img.get_rect(center=(cx, vista.centery - 10 + int(4 * math.sin(t * 0.07 + j)))))
                        obert = self.estrelles_totals() >= d["estrelles"]
                        if not obert:
                            dibuixar_cadenat(surf, cx, vista.centery + 30)
                        text(surf, f"{d['estrelles']}★", F_MINI, VERD if obert else GRIS, (cx, vista.bottom - 14))
                text(surf, f"{self.estrelles_totals()}/45 ★", F_HUD, GROC, (r.centerx, vista.bottom + 30))
                text(surf, "Premios exclusivos", F_TEXT_P, BLANC, (r.centerx, vista.bottom + 56))

    # ----- Revelacions de premis ---------------------------------------------------------------------------

    def revelar(self, tipus, valor=None):
        if getattr(self, "carregant_partida", False):
            return
        if len(self.revelacions) < 8:
            self.revelacions.append((tipus, valor))
        elif self.revelacions[-1][0] != "mes":
            self.revelacions.append(("mes", 1))
        else:
            self.revelacions[-1] = ("mes", self.revelacions[-1][1] + 1)

    def entrar_revelacio(self, despres):
        self.despres_revelacio = despres
        self.revelacio = self.revelacions.pop(0)
        self.particules_rev = []
        self.botons = [Boto((WIDTH // 2 - 110, HEIGHT - 70, 220, 46), "Continuar", self.seguent_revelacio, VERD)]
        if self.revelacions:
            self.botons.append(Boto((WIDTH - 170, HEIGHT - 50, 150, 30), T("Saltar todo ({n})").format(n=len(self.revelacions) + 1),
                                    self.saltar_revelacions, GRIS_FOSC, font=F_MINI))
        AUDIO.so("passi")
        self.canviar_estat("revelacio")

    def seguent_revelacio(self):
        if self.revelacions:
            self.entrar_revelacio(self.despres_revelacio)
        else:
            self.despres_revelacio()

    def saltar_revelacions(self):
        self.revelacions.clear()
        self.despres_revelacio()

    def dibuixar_revelacio(self, surf):
        if self.revelacio[0] == "teddy":
            self.dibuixar_revelacio_teddy(surf)
            return
        t = self.temps_estat
        surf.fill((10, 8, 24))
        tipus, valor = self.revelacio
        color = {"rang": (70, 56, 20), "camo": (60, 46, 20), "temporada": (50, 30, 70)}.get(tipus, (34, 30, 70))
        cx, cy = WIDTH // 2, 214
        raigs(surf, cx, cy, t, color)
        l = llum(150, (255, 220, 140) if tipus in ("rang", "camo") else (190, 140, 255))
        l.set_alpha(int(110 + 40 * math.sin(t * 0.08)))
        surf.blit(l, l.get_rect(center=(cx, cy)))
        l.set_alpha(255)
        # entrada amb rebot
        k = min(1.0, t / 22)
        escala = 0.2 + 0.8 * k + (0.18 * math.sin(k * math.pi) if k < 1 else 0.03 * math.sin(t * 0.1))
        capa = pygame.Surface((240, 170), pygame.SRCALPHA)
        etiqueta, nom = "", ""
        if tipus == "rang":
            dibuixar_insignia(capa, 120, 80, valor, 110)
            etiqueta, nom = T("¡ASCENSO!"), T(RANGS[valor]["nom"])
        elif tipus == "camo":
            arma, camo = valor
            img = mostra_soldat(arma, self.uniforme, self.aparenca, camo)
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            capa.blit(img, img.get_rect(center=(120, 85)))
            etiqueta = T("CAMUFLAJE DESBLOQUEADO")
            nom = f"{T(CAMUFLATGES[camo]['nom'])} · {T(ARMES[ARMA_PER_ID[arma]]['nom'])}"
        elif tipus == "temporada":
            r = pygame.Rect(40, 40, 160, 90)
            pygame.draw.rect(capa, (200, 80, 200), r, border_radius=12)
            pygame.draw.rect(capa, (255, 170, 255), r, 3, border_radius=12)
            text(capa, "BP", F_GRAN, BLANC, (120, 74))
            dibuixar_estrella(capa, 120, 132, 18, True, (190, 140, 255))
            etiqueta, nom = T("¡NUEVA TEMPORADA!"), T("Temporada {t}").format(t=valor)
        elif tipus == "mes":
            dibuixar_trofeu(capa, 120, 80, 90)
            etiqueta, nom = T("¡Y MÁS!"), T("{n} recompensas más").format(n=valor)
        else:
            cat, ident = valor
            if cat in ("uniforme", "arma", "titol", "estela", "efecte", "mira", "tema", "targeta", "dron"):
                self.previsualitzar(capa, cat, ident, capa.get_rect(), t)
            etiqueta = T("¡NUEVO!") + "  " + T({"uniforme": "Uniforme", "arma": "Aspecto de arma", "titol": "Título",
                                                 "estela": "Estela", "efecte": "Eliminación", "mira": "Punto de mira",
                                                 "tema": "HUD", "targeta": "Tarjeta", "dron": "Dron"}[cat]).upper()
            nom = nom_cosmetic(cat, ident)
        img = pygame.transform.scale(capa, (int(240 * escala * 1.5), int(170 * escala * 1.5)))
        surf.blit(img, img.get_rect(center=(cx, cy)))
        # espurnes
        if t % 3 == 0:
            a = random.uniform(0, math.tau)
            self.particules_rev.append(Particula(cx + math.cos(a) * 60, cy + math.sin(a) * 50, math.cos(a) * 2.5,
                                                 math.sin(a) * 2.5, random.choice((GROC, BLANC, (255, 170, 255))), 40, 3))
        for p in self.particules_rev[:]:
            if p.actualitzar():
                self.particules_rev.remove(p)
            else:
                p.dibuixar(surf)
        if t > 10:
            text(surf, etiqueta, F_HUD, GROC, (cx, 368))
            text(surf, nom, F_SUBTITOL, BLANC, (cx, 404))
        if tipus not in ("rang", "temporada", "mes", "camo"):
            text(surf, self.origen_cosmetic(*valor), F_TEXT_PP, GRIS, (cx, 436))
        if self.revelacions:
            text(surf, T("Quedan {n}").format(n=len(self.revelacions)), F_MINI, GRIS, (cx, HEIGHT - 86))

    # ----- Teddy Bear: animació en reclamar-lo amb el seu codi secret -------------------------------------
    TERRA_TEDDY, ESC_TEDDY, ESCLAT_TEDDY = 300, 5, 40

    def entrar_teddy(self, despres):
        """Fons de cors en mirall, un cor gran que batega i esclata, i el Teddy saludant amb el seu nom."""
        self.despres_revelacio = despres
        self.revelacio = ("teddy", None)
        self.cors_rev, self.espurnes_rev = [], []
        self.botons = [Boto((WIDTH // 2 - 232, HEIGHT - 64, 220, 46), "¡Equipar!", self.equipar_teddy, (206, 70, 150)),
                       Boto((WIDTH // 2 + 12, HEIGHT - 64, 220, 46), "Continuar", self.seguent_revelacio, GRIS_FOSC)]
        AUDIO.so("passi")
        self.canviar_estat("revelacio")

    def equipar_teddy(self):
        self.equipar_cosmetic("dron", "teddy")
        self.entrar_menu()

    def pose_revelacio_teddy(self, u):
        """(postura, alçada del saltiró) del Teddy `u` fotogrames després que esclati el cor."""
        if u < 26:
            return "llança", 0                       # ta-ta!
        v = (u - 26) % 300
        for ini in (46, 166):
            if ini <= v < ini + 14:
                return "salt", SALT_TEDDY[v - ini]
        for ini, fi, pose in ((40, 46, "ajupit"), (60, 65, "aterra"), (100, 120, "llança"), (160, 166, "ajupit"),
                              (180, 185, "aterra"), (215, 270, "cor")):
            if ini <= v < fi:
                return pose, 0
        return ("parpella" if 30 <= v % 120 < 36 else "quiet"), 0

    def actualitzar_revelacio_teddy(self):
        t = self.temps_estat
        cx, terra, e = WIDTH // 2, self.TERRA_TEDDY, self.ESC_TEDDY
        if 10 <= t < self.ESCLAT_TEDDY - 4 and t % 2 == 0:          # cors que hi conflueixen abans de l'esclat
            a = random.uniform(0, math.tau)
            self.cors_rev.append(CorTeddy(cx + math.cos(a) * 330, terra - 70 + math.sin(a) * 260, -math.cos(a) * 330 / 18,
                                          -math.sin(a) * 260 / 18, 18, 2))
        if t == self.ESCLAT_TEDDY:                                  # el cor gran esclata en cors petits
            for k in range(28):
                a = k * math.tau / 28 + random.uniform(-0.1, 0.1)
                v = random.uniform(3, 7)
                self.cors_rev.append(CorTeddy(cx + math.cos(a) * 30, terra - 70 + math.sin(a) * 26, math.cos(a) * v,
                                              math.sin(a) * v - 1.5, random.randint(50, 70), random.choice((2, 3, 4)), 0.1))
            AUDIO.so("ting")
        u = t - self.ESCLAT_TEDDY
        if u >= 0:
            v = (u - 26) % 300 if u >= 26 else None
            if u == 3 or v in (52, 102, 172):                       # llança cors (també dalt de tot dels saltirons)
                _, h = self.pose_revelacio_teddy(u)
                for _ in range(7):
                    self.cors_rev.append(CorTeddy(cx + random.uniform(-30, 30), terra + h * e - 118,
                                                  random.uniform(-3.2, 3.2), random.uniform(-5.5, -3),
                                                  random.randint(56, 70), random.choice((2, 3, 3, 4)), 0.12))
            if v is not None and 215 <= v < 262 and (v - 215) % 9 == 0:   # s'abraça el cor: en surten de petits
                self.cors_rev.append(CorTeddy(cx + random.uniform(-26, 26), terra - 150, random.uniform(-0.4, 0.4), -1.3,
                                              60, 3))
        if t % 4 == 0:
            self.espurnes_rev.append([random.uniform(cx - 300, cx + 300), random.uniform(70, 330), 0, random.randint(18, 30)])
        for c in self.cors_rev[:]:
            if c.actualitzar():
                self.cors_rev.remove(c)
        for sp in self.espurnes_rev[:]:
            sp[2] += 1
            if sp[2] >= sp[3]:
                self.espurnes_rev.remove(sp)

    def fons_cors_mirall(self, surf, t):
        """Fons rosa amb una trama de cors inclinats que pugen i es gronxen: la meitat dreta és el reflex
        exacte de l'esquerra (en mirall), i els cors de cada banda s'inclinen al revés."""
        cache = getattr(Game, "_FONS_TEDDY", None)
        if cache is None:
            degradat = pygame.Surface((WIDTH, HEIGHT))
            for y in range(HEIGHT):
                k = y / (HEIGHT - 1)
                degradat.fill(tuple(int(a + (b - a) * k) for a, b in zip((44, 10, 54), (150, 42, 118))), (0, y, WIDTH, 1))
            rajola = pygame.Surface((120, 104), pygame.SRCALPHA)
            gran, petit = (255, 120, 196, 64), (255, 214, 236, 72)
            for x, y, mida, angle, color in ((30, 26, 4, 16, gran), (90, 78, 4, 16, gran), (90, 24, 2, -12, petit),
                                             (30, 76, 2, -12, petit)):
                cor = pygame.transform.rotate(cor_teddy(mida, color), angle)
                rajola.blit(cor, cor.get_rect(center=(x, y)))
            tw, th = rajola.get_size()
            meitat = pygame.Surface((WIDTH // 2, HEIGHT + th), pygame.SRCALPHA)
            for y in range(0, HEIGHT + th, th):
                for x in range(0, WIDTH // 2, tw):
                    meitat.blit(rajola, (x, y))
            patro = pygame.Surface((WIDTH, HEIGHT + th), pygame.SRCALPHA)
            patro.blit(meitat, (0, 0))
            patro.blit(pygame.transform.flip(meitat, True, False), (WIDTH // 2, 0))
            cache = Game._FONS_TEDDY = (degradat, patro, th)
        degradat, patro, th = cache
        surf.blit(degradat, (0, 0))
        ox, oy = round(7 * math.sin(t * 0.03)), int(t * 0.6) % th     # cap al centre i enfora alhora, i amunt
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(0, 0, WIDTH // 2, HEIGHT).clip(clip))
        surf.blit(patro, (ox, -oy))
        surf.set_clip(pygame.Rect(WIDTH // 2, 0, WIDTH // 2, HEIGHT).clip(clip))
        surf.blit(patro, (-ox, -oy))
        surf.set_clip(clip)

    @staticmethod
    def punts_cor(n):
        """`n` punts repartits per igual sobre el contorn d'un cor (x de -16 a 16, y de -12 a 17)."""
        mostres = []
        for i in range(721):
            a = i / 720 * math.tau
            mostres.append((16 * math.sin(a) ** 3,
                            -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))))
        llarg = [0.0]
        for (x0, y0), (x1, y1) in zip(mostres, mostres[1:]):
            llarg.append(llarg[-1] + math.hypot(x1 - x0, y1 - y0))
        punts, j = [], 0
        for k in range(n):
            objectiu = llarg[-1] * k / n
            while llarg[j + 1] < objectiu:
                j += 1
            punts.append(mostres[j])
        return punts

    def anell_cors(self, surf, cx, cy, t, batec):
        """Cors petits que dibuixen un cor gran al voltant del Teddy, amb llums que hi corren i el batec."""
        punts = getattr(Game, "_PUNTS_COR", None)
        if punts is None:
            punts = Game._PUNTS_COR = self.punts_cor(30)
        n, k = len(punts), 1 + 0.05 * batec
        for i, (x, y) in enumerate(punts):
            encès = (i - t // 3) % n < 4
            img = cor_teddy(3 if encès else 2)
            if img:
                surf.blit(img, img.get_rect(center=(round(cx + x * 8.2 * k), round(cy + y * 7.0 * k))))

    def reflex_teddy(self, surf, pose, x, peus, terra):
        """El Teddy reflectit al terra de mirall (cap per avall, rosat i esvaint-se)."""
        img, (dx, dy) = imatge_teddy(pose, self.ESC_TEDDY)
        if img is None:
            return
        ref = _CACHE_TEDDY.get(("reflex", pose))
        if ref is None:
            ref = pygame.transform.flip(img, False, True)
            grad = pygame.Surface(ref.get_size(), pygame.SRCALPHA)
            alt = ref.get_height()
            for y in range(alt):
                grad.fill((255, 205, 235, int(130 * max(0.0, 1 - y / (alt * 0.6)) ** 1.5)), (0, y, ref.get_width(), 1))
            ref.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            _CACHE_TEDDY[("reflex", pose)] = ref
        clip = surf.get_clip()
        surf.set_clip(pygame.Rect(0, terra, WIDTH, HEIGHT - terra).clip(clip))
        surf.blit(ref, (round(x + dx), round(2 * terra - (peus + dy + img.get_height()))))
        surf.set_clip(clip)

    def dibuixar_revelacio_teddy(self, surf):
        t = self.temps_estat
        cx, terra, e = WIDTH // 2, self.TERRA_TEDDY, self.ESC_TEDDY
        u = t - self.ESCLAT_TEDDY
        self.fons_cors_mirall(surf, t)
        c = t % 60                                                  # batec: «pum-pum» cada segon
        batec = math.exp(-c / 6) + (0.6 * math.exp(-(c - 12) / 6) if c >= 12 else 0)
        l = llum(200, (255, 120, 200))
        l.set_alpha(int(110 + 60 * batec))
        surf.blit(l, l.get_rect(center=(cx, terra - 70)))
        l.set_alpha(255)
        # terra de mirall: vidre fosc i una línia de llum que s'esvaeix cap als costats
        terra_img = getattr(Game, "_TERRA_TEDDY", None)
        if terra_img is None:
            terra_img = pygame.Surface((WIDTH, HEIGHT - terra), pygame.SRCALPHA)
            terra_img.fill((40, 6, 40, 110))
            for x in range(WIDTH):
                f = max(0.0, 1 - abs(x - WIDTH / 2) / (WIDTH / 2)) ** 1.4
                for k, a in enumerate((190, 80, 34)):
                    terra_img.set_at((x, k), (255, 215, 238, int(a * f)))
            Game._TERRA_TEDDY = terra_img
        surf.blit(terra_img, (0, terra))
        if u < 0:                                                   # el cor tancat creix, batega i tremola
            k = min(1.0, t / 20)
            mida = max(1, round(16 * (1 - (1 - k) ** 3) + (1.5 * batec if t >= 20 else 0)))
            tremola = max(0, (t - 20) / 5)
            img = cor_teddy(mida)
            if img:
                surf.blit(img, img.get_rect(center=(cx + random.uniform(-tremola, tremola),
                                                    terra - 70 + random.uniform(-tremola, tremola))))
        else:
            self.anell_cors(surf, cx, terra - 121, u, batec)
            pose, h = self.pose_revelacio_teddy(u)
            peus = terra + h * e - max(0, 8 - u) * 4                # en sortir cau una mica
            self.reflex_teddy(surf, pose, cx, peus, terra)
            posar_teddy(surf, pose, cx, peus, e)
        for cor in self.cors_rev:
            cor.dibuixar(surf)
        for x, y, k, vida in self.espurnes_rev:
            r = int(1 + 3 * math.sin(math.pi * k / vida))
            col = BLANC if int(x) % 2 else (255, 220, 240)
            pygame.draw.line(surf, col, (x - r, y), (x + r, y))
            pygame.draw.line(surf, col, (x, y - r), (x, y + r))
        if 0 <= u < 14:                                             # flaix de l'esclat
            capa = getattr(Game, "_FLAIX_TEDDY", None)
            if capa is None:
                capa = Game._FLAIX_TEDDY = pygame.Surface((WIDTH, HEIGHT))
                capa.fill((255, 236, 246))
            capa.set_alpha(int(210 * (1 - u / 14)))
            surf.blit(capa, (0, 0))
        if t > 12:
            r = text(surf, "¡MASCOTA SECRETA DESBLOQUEADA!", F_HUD, BLANC, (cx, 40))
            cor = cor_teddy(2)
            for x in (r.left - 18, r.right + 18):
                if cor:
                    surf.blit(cor, cor.get_rect(center=(x, 40 + int(2 * math.sin(t * 0.1)))))
        if u >= 8:
            self.titol_teddy(surf, u, cx, 384)
        if u >= 34:
            text(surf, "Te acompaña en combate y te cura +5 de vida cada 8 s si estás herido", F_TEXT_PP,
                 (255, 226, 242), (cx, 432))

    def titol_teddy(self, surf, u, cx, y):
        """«Teddy Bear» amb lletres grosses que surten d'una en una i fan onades."""
        lletres = getattr(Game, "_LLETRES_TEDDY", None)
        if lletres is None:
            lletres = []
            for ch in "Teddy Bear":
                base = text_contorn(ch, F_GRAN, (255, 176, 218), (84, 14, 62))
                im = pygame.transform.scale(base, (base.get_width() * 2, base.get_height() * 2))
                ombra = im.copy()
                ombra.fill((40, 0, 30, 140), special_flags=pygame.BLEND_RGBA_MULT)
                lletres.append((im, ombra))
            Game._LLETRES_TEDDY = lletres
        total = sum(im.get_width() - 4 for im, _ in lletres)
        x = cx - total / 2
        for i, (im, ombra) in enumerate(lletres):
            w = im.get_width() - 4
            k = (u - 8 - i * 3) / 7
            if k > 0:
                if k < 1:                                       # «pop» en sortir
                    esc = 1 + 0.45 * math.sin(k * math.pi)
                    mida = (int(im.get_width() * esc), int(im.get_height() * esc))
                    im, ombra = pygame.transform.scale(im, mida), pygame.transform.scale(ombra, mida)
                yy = y + 4 * math.sin(u * 0.12 - i * 0.6)
                surf.blit(ombra, ombra.get_rect(center=(int(x + w / 2), int(yy) + 5)))
                surf.blit(im, im.get_rect(center=(int(x + w / 2), int(yy))))
            x += w

    def ajuda_primera_vegada(self, clau, pagines, tornada):
        """La primera vegada que entres a una pantalla nova, abans t'explica com funciona."""
        vistes = self.vistos.setdefault("ajudes", [])
        if clau in vistes:
            return False
        vistes.append(clau)
        self.desar_progres()
        self.entrar_ajuda(0, tornada, pagines)
        return True

    def _ajuda_4(self, surf, r):
        """Maestria: les baixes amb una arma la pugen de nivell i el camuflatge canvia de color."""
        caixa = pygame.Rect(r.x + 20, r.y + 20, 300, 330)
        self._caixa_demo(surf, caixa)
        cicle = 420
        f = self.temps_estat % cicle
        baixes = min(320, int(f * 1.05))
        nivell = sum(baixes >= m for m in MAESTRIA)
        camo = "cap"
        for c in ("bronze", "plata", "or"):
            if nivell >= CAMUFLATGES[c]["nivell"]:
                camo = c
        if f > 330:
            camo = "diamant"
        img = mostra_soldat("fusell", self.uniforme, "estandard", None if camo == "cap" else camo)
        if img:
            img = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            surf.blit(img, img.get_rect(midbottom=(caixa.centerx, caixa.bottom - 34)))
        if camo == "diamant" and (self.temps_estat // 4) % 2:
            for k in range(3):
                a = self.temps_estat * 0.07 + k * 2.1
                dibuixar_estrella(surf, int(caixa.centerx + math.cos(a) * 70), int(caixa.y + 200 + math.sin(a) * 50), 5,
                                  True, (190, 245, 255))
        barra = pygame.Rect(caixa.x + 30, caixa.y + 52, caixa.w - 60, 12)
        ant = MAESTRIA[nivell - 1]
        seg = MAESTRIA[nivell] if nivell < len(MAESTRIA) else ant + 1
        k = 1.0 if nivell >= len(MAESTRIA) else (baixes - ant) / (seg - ant)
        pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=6)
        pygame.draw.rect(surf, (120, 200, 255), (barra.x, barra.y, int(barra.w * k), barra.h), border_radius=6)
        text(surf, T("Nivel {n}").format(n=nivell) + f" · {baixes} " + T("bajas"), F_HUD, BLANC, (barra.centerx, barra.y - 16))
        nom = T(CAMUFLATGES[camo]["nom"])
        color = CAMUFLATGES[camo]["tint"] or GRIS
        text(surf, nom, F_UI, color, (caixa.centerx, caixa.y + 92))
        for i, c in enumerate(("bronze", "plata", "or", "diamant")):
            x = caixa.x + 60 + i * 60
            obert = c == camo or ("bronze", "plata", "or", "diamant").index(c) < \
                ("cap", "bronze", "plata", "or", "diamant").index(camo)
            pygame.draw.circle(surf, CAMUFLATGES[c]["tint"] if obert else GRIS_FOSC, (x, caixa.y + 126), 10)
            pygame.draw.circle(surf, NEGRE, (x, caixa.y + 126), 10, 2)
        self._punts(surf, r.x + 340, r.y + 22, r.w - 360, [
            "Cada arma sube de nivel de maestría con las bajas que consigues con ella.",
            "En los niveles 4, 7 y 10 desbloqueas los camuflajes de Bronce, Plata y Oro.",
            "Con todas las armas en Oro consigues el camuflaje Diamante para todas.",
            "Los camuflajes se equipan en Personalizar (clic en Nexus en el menú) y cambian el color de las balas.",
        ], salt=18)

    def _ajuda_5(self, surf, r):
        """Rangs: la insígnia puja amb l'XP total."""
        caixa = pygame.Rect(r.x + 20, r.y + 20, 300, 330)
        self._caixa_demo(surf, caixa)
        cicle = 150
        idx, f = (self.temps_estat // cicle) % min(6, len(RANGS)), self.temps_estat % cicle
        centre = (caixa.centerx, caixa.y + 150)
        if f < 40:
            clip = surf.get_clip()
            surf.set_clip(caixa.inflate(-4, -4))
            raigs(surf, centre[0], centre[1], self.temps_estat, (40, 46, 90), n=10, r=220)
            surf.set_clip(clip)
            l = llum(90, (255, 220, 120))
            surf.blit(l, l.get_rect(center=centre))
        mida = 60 + (int(20 * (1 - f / 40)) if f < 40 else 0)
        dibuixar_insignia(surf, centre[0], centre[1], idx, mida)
        text(surf, T(RANGS[idx]["nom"]), F_SUBTITOL, GROC, (caixa.centerx, caixa.y + 230))
        if f < 60 and idx > 0:
            text(surf, "¡ASCENSO!", F_UI, (255, 220, 120), (caixa.centerx, caixa.y + 40 - max(0, 20 - f)))
        barra = pygame.Rect(caixa.x + 40, caixa.y + 268, caixa.w - 80, 10)
        pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=5)
        pygame.draw.rect(surf, GROC, (barra.x, barra.y, int(barra.w * f / cicle), barra.h), border_radius=5)
        self._punts(surf, r.x + 340, r.y + 22, r.w - 360, [
            "Toda la XP que ganas suma a tu rango, y nunca se reinicia.",
            "Hay 15 rangos, desde Recluta hasta General.",
            "Cada ascenso da un premio: monedas, miras, temas del HUD, tarjetas y más.",
            "Tu rango sale en la tarjeta del menú, al lado de tu nombre.",
        ], salt=18)

    def _ajuda_6(self, surf, r):
        """Bestiari: una fitxa que es descobreix a mesura que abats aquell enemic."""
        caixa = pygame.Rect(r.x + 20, r.y + 20, 300, 330)
        self._caixa_demo(surf, caixa)
        cicle = 260
        n, f = (self.temps_estat // cicle) % 3, self.temps_estat % cicle
        e = BESTIARI[n]
        baixes = min(e["cal"], f // 8)
        base = self.sprite_bestiari(e["clau"])
        img = self.imatge_novetat(("best_g", e["clau"]), base, 100) if base is not None else None
        if img is not None:
            if baixes == 0:
                img = Game.IMATGES_NOVETAT.get(("ombra_g", e["clau"]))
                if img is None:
                    img = self.imatge_novetat(("best_g", e["clau"]), base, 100).copy()
                    img.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    Game.IMATGES_NOVETAT[("ombra_g", e["clau"])] = img
            surf.blit(img, img.get_rect(center=(caixa.centerx, caixa.y + 78 + int(4 * math.sin(self.temps_estat * 0.08)))))
        text(surf, T(e["nom"]) if baixes else "???", F_UI, BLANC, (caixa.centerx, caixa.y + 146))
        barra = pygame.Rect(caixa.x + 40, caixa.y + 166, caixa.w - 80, 10)
        pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=5)
        pygame.draw.rect(surf, VERD, (barra.x, barra.y, int(barra.w * baixes / e["cal"]), barra.h), border_radius=5)
        text(surf, f"{baixes}/{e['cal']}", F_MINI, BLANC, (caixa.centerx, barra.bottom + 12))
        if baixes >= e["cal"]:
            linies = ajustar_linies(T(e["lore"]), F_MINI, caixa.w - 30)[:4]
            for i, l in enumerate(linies):
                text(surf, l, F_MINI, (200, 220, 255), (caixa.centerx, caixa.y + 212 + i * 18))
        else:
            dibuixar_cadenat(surf, caixa.centerx, caixa.y + 236, GRIS)
        self._punts(surf, r.x + 340, r.y + 22, r.w - 360, [
            "Al eliminar por primera vez un tipo de enemigo se abre su ficha.",
            "Con suficientes bajas descubres su historia secreta.",
            "Completar todas las fichas da un título especial.",
            "En Colección también tienes la maestría de tus armas y los rangos.",
        ], salt=18)

    def _ajuda_7(self, surf, r):
        """Desafiaments: les estrelles obren el cadenat."""
        caixa = pygame.Rect(r.x + 20, r.y + 20, 300, 330)
        self._caixa_demo(surf, caixa)
        cicle = 240
        f = self.temps_estat % cicle
        estrelles = min(15, f // 8)
        obert = estrelles >= 15
        c = pygame.Rect(caixa.x + 50, caixa.y + 60, caixa.w - 100, 200)
        fons = Game.IMATGES_NOVETAT.get(("ajuda_desaf", c.size))
        if fons is None and FONS_NIVELLS.get((1, 1)) is not None:
            fons = pygame.transform.smoothscale(FONS_NIVELLS[(1, 1)], c.size)
            Game.IMATGES_NOVETAT[("ajuda_desaf", c.size)] = fons
        if fons is not None:
            surf.blit(fons, c)
        else:
            pygame.draw.rect(surf, (40, 20, 30), c, border_radius=8)
        if not obert:
            capa = pygame.Surface(c.size, pygame.SRCALPHA)
            capa.fill((0, 0, 0, 150))
            surf.blit(capa, c)
            dibuixar_cadenat(surf, c.centerx, c.centery - int(max(0, f - 110) * 0.3))
        else:
            k = min(1.0, (f - 120) / 20)
            l = llum(int(60 + 40 * k), (255, 160, 80))
            surf.blit(l, l.get_rect(center=c.center))
            text(surf, "¡ABIERTO!", F_UI, TARONJA, c.center)
        pygame.draw.rect(surf, TARONJA if obert else GRIS, c, 2, border_radius=8)
        dibuixar_estrella(surf, caixa.centerx - 30, caixa.y + 290, 12)
        text(surf, f"{estrelles}/15", F_UI, GROC, (caixa.centerx + 10, caixa.y + 290), ancora="midleft")
        self._punts(surf, r.x + 340, r.y + 22, r.w - 360, [
            "Los desafíos son niveles especiales que se abren con estrellas.",
            "Hay tres: el nivel secreto, un combate contra todos los jefes seguidos y el modo Pesadilla.",
            "Cada uno da premios exclusivos que no salen en ningún otro sitio.",
            "Entra desde Jugar > Ver desafíos.",
        ], salt=18)

    def _ajuda_8(self, surf, r):
        """Diari: tres reptes que s'omplen, monedes i l'oferta del dia."""
        caixa = pygame.Rect(r.x + 20, r.y + 20, 300, 330)
        self._caixa_demo(surf, caixa)
        cicle = 300
        f = self.temps_estat % cicle
        reptes = (("Elimina {n} enemigos", 40), ("Haz {n} volteretas", 25), ("Derrota a un jefe", 1))
        for i, (txt, n) in enumerate(reptes):
            inici = i * 70
            k = max(0.0, min(1.0, (f - inici) / 60))
            fila = pygame.Rect(caixa.x + 14, caixa.y + 24 + i * 76, caixa.w - 28, 64)
            fet = k >= 1
            panell(surf, fila, VERD if fet else (80, 90, 140), 210)
            text(surf, T(txt).format(n=n), F_MINI, BLANC, (fila.x + 10, fila.y + 16), ancora="midleft")
            b = pygame.Rect(fila.x + 10, fila.y + 34, fila.w - 80, 10)
            pygame.draw.rect(surf, GRIS_FOSC, b, border_radius=5)
            pygame.draw.rect(surf, VERD if fet else GROC, (b.x, b.y, int(b.w * k), b.h), border_radius=5)
            text(surf, f"{int(n * k)}/{n}", F_MINI, BLANC, (b.centerx, b.bottom + 9))
            dibuixar_moneda(surf, fila.right - 46, fila.centery, 8)
            text(surf, "200", F_MINI, GROC, (fila.right - 34, fila.centery), ancora="midleft")
            if fet and f - inici - 60 < 24:
                h = (f - inici - 60) / 24
                dibuixar_moneda(surf, int(fila.right - 46 + 20 * h), int(fila.centery - 60 * h), 8)
        if f > 220 and (f // 10) % 2:
            text(surf, "+300", F_UI, GROC, (caixa.centerx, caixa.bottom - 40))
        self._punts(surf, r.x + 340, r.y + 22, r.w - 360, [
            "Cada día tienes tres retos nuevos. Cada uno da monedas y XP.",
            "Si completas los tres, te llevas un premio extra.",
            "Las ofertas del día (cosméticos que van cambiando) están en Tienda > Diaria.",
            "Los retos se renuevan a medianoche.",
        ], salt=18)

    def botons_ofertes(self):
        b = []
        for k, (tipus, ident, preu) in enumerate(self.ofertes_del_dia()):
            r = self.rect_oferta(k)
            tingut = PREFIX_COSMETIC[tipus] + ident in self.cosmetics
            b.append(Boto((r.x + 14, r.bottom - 44, r.w - 28, 32), "Comprado" if tingut else T("Comprar {c}").format(c=preu),
                          None if tingut else (lambda t=tipus, i=ident, p=preu: self.comprar_oferta(t, i, p)),
                          GRIS_FOSC if tingut else (TARONJA if self.monedes >= preu else VERMELL_FOSC), font=F_MINI))
        return b

    def dibuixar_botiga_ofertes(self, surf):
        s = self.segons_fins_dema()
        text(surf, T("Nuevas ofertas en {h} h {m} min").format(h=s // 3600, m=s % 3600 // 60), F_TEXT_PP, GRIS,
             (WIDTH // 2, 446))
        pos = ratoli()
        info = None
        for k, (tipus, ident, preu) in enumerate(self.ofertes_del_dia()):
            r = self.rect_oferta(k)
            tingut = PREFIX_COSMETIC[tipus] + ident in self.cosmetics
            panell(surf, r, VERD if tingut else (255, 170, 80))
            text(surf, T(self.ETIQUETA_TIPUS.get(tipus, tipus)).upper(), F_MINI, (255, 190, 110), (r.centerx, r.y + 16))
            zona = pygame.Rect(r.x + 6, r.y + 30, r.w - 12, r.h - 120)
            self.previsualitzar(surf, tipus, ident, zona, self.t_global + k * 17)
            for j, linia in enumerate(ajustar_linies(nom_cosmetic(tipus, ident), F_TEXT_P, r.w - 16)[:2]):
                text(surf, linia, F_TEXT_P, BLANC, (r.centerx, r.bottom - 80 + j * 20))
            if r.collidepoint(pos):
                info = nom_premi(tipus, ident)
        if not self.missatge:
            text(surf, info or "Lo que compres se equipa en Personalizar: haz clic en Nexus en el menú.", F_TEXT_PP, CIAN, (WIDTH // 2 + 80, 499))

    ETIQUETA_TIPUS = {"estela": "Estela", "efecte": "Efecto de eliminación", "mira": "Punto de mira",
                      "tema": "Tema del HUD", "targeta": "Tarjeta", "dron": "Dron", "uniforme": "Uniforme",
                      "arma": "Aspecto de arma", "titol": "Título"}

    # ----- Codis -------------------------------------------------------------------------------------
    RECT_CALCULADORA = pygame.Rect(24, 18, 44, 44)

    def entrar_codis(self, resultat=None):
        self.codi_text = ""
        self.codi_resultat = resultat
        self.botons = [Boto((WIDTH // 2 - 110, 336, 220, 46), "Canjear", self.bescanviar_codi, VERD),
                       Boto((30, HEIGHT - 62, 140, 42), "< Volver", self.entrar_botiga, GRIS_FOSC)]
        self.canviar_estat("codis")

    @staticmethod

    def empremta_codi(codi):
        net = "".join(str(codi).split()).upper()
        return hashlib.sha256(("invasio:" + net).encode("utf-8")).hexdigest()

    def tecla_codi(self, ev):
        """Escriure el codi amb el teclat (aquí la M no silencia ni la G torna al menú)."""
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.bescanviar_codi()
        elif ev.key == pygame.K_ESCAPE:
            self.entrar_botiga()
        elif ev.key == pygame.K_BACKSPACE:
            self.codi_text = self.codi_text[:-1]
        else:
            c = (ev.unicode or "").upper()
            if len(c) == 1 and (c.isalnum() or c == "-") and len(self.codi_text) < 24:
                self.codi_text += c
                self.codi_resultat = None

    def bescanviar_codi(self):
        if not self.codi_text.strip():
            return
        clau = self.empremta_codi(self.codi_text)
        codi = CODIS.get(clau)
        if codi is None:
            self.codi_resultat = (False, T("Código no válido"))
            AUDIO.so("buit")
        elif clau in self.codis_usats:
            self.codi_resultat = (False, T("Ya has usado este código"))
            AUDIO.so("buit")
        else:
            self.codis_usats.append(clau)
            for tipus, valor in codi["premis"]:
                self.donar_premi_codi(tipus, valor)
            self.revisar_rangs()
            self.revisar_logros()
            self.desar_progres()
            self.codi_resultat = (True, T("¡Código canjeado! {n}").format(n=T(codi["nom"])))
            if ("dron", "teddy") in codi["premis"] and TEDDY:      # el Teddy Bear té la seva pròpia animació
                if ("cosmetic", ("dron", "teddy")) in self.revelacions:
                    self.revelacions.remove(("cosmetic", ("dron", "teddy")))
                self.codi_text = ""
                resultat = self.codi_resultat
                self.entrar_teddy(lambda: self.entrar_codis(resultat))
                return
            AUDIO.so("passi")
        self.codi_text = ""

    def donar_premi_codi(self, tipus, valor):
        if tipus == "tot":
            self.desbloquejar_tot()
        elif tipus == "monedes":
            self.monedes += int(valor)
        elif tipus == "xp":
            self.afegir_xp(int(valor))
        elif tipus == "arma_joc" and valor in ARMA_PER_ID:
            self.armes_propies.add(valor)
        elif tipus == "millora":
            m = next((m for m in MILLORES if m["id"] == valor), None)
            if m:
                self.millores[valor] = len(m["costos"])
        elif tipus in PREFIX_COSMETIC and valor in CATALEG_COSMETIC[tipus]:
            self.atorgar(tipus, valor)

    def desbloquejar_tot(self):
        """Mode administrador: totes les armes, millores, nivells, estrelles, cosmètics, camuflatges, rangs,
        el Battle Pass sencer i el bestiari. Els logros no: aquests s'han de guanyar (alguns surten sols)."""
        self.monedes += 100000
        self.armes_propies = {a["id"] for a in ARMES}
        for m in MILLORES:
            self.millores[m["id"]] = len(m["costos"])
        for n in range(NUM_SECTORS):
            for e in range(3):
                self.nivells_desbloquejats[n][e] = True
                self.completats[n][e] = True
                self.estrelles[n][e] = [True, True, True]
        for tipus, cataleg in CATALEG_COSMETIC.items():
            for ident in cataleg:
                self.cosmetics.add(PREFIX_COSMETIC[tipus] + ident)
        for a in ARMES:
            self.baixes_arma[a["id"]] = max(self.baixes_arma.get(a["id"], 0), MAESTRIA[-1])
        for b in BESTIARI:
            clau = "k_" + b["clau"]
            self.estadistiques[clau] = max(self.estadistiques.get(clau, 0), b["cal"])
        self.xp = max(self.xp, RANGS[-1]["xp"])
        self.rang_reclamat = len(RANGS) - 1
        # Battle Pass: la temporada es dona per acabada (com quan arribes al nivell 50 jugant) i comença la següent
        if self.temporada == 1:
            self.temporada = 2
            self.xp_passi, self.passi_reclamat = 0, 0
        self.revelacions = []
        for que in ("personalitzar", "passi", "colleccio"):
            self.marcar_vist(que)

    def dibuixar_codis(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "CÓDIGOS", F_SUBTITOL, BLANC, (WIDTH // 2, 60))
        caixa = pygame.Rect(WIDTH // 2 - 260, 120, 520, 290)
        panell(surf, caixa, BLAU_CLAR)
        dibuixar_calculadora(surf, caixa.centerx, caixa.y + 46, 1.3)
        text(surf, "Escribe un código y pulsa Enter", F_TEXT_P, GRIS, (caixa.centerx, caixa.y + 104))
        camp = pygame.Rect(caixa.x + 40, caixa.y + 128, caixa.w - 80, 56)
        pygame.draw.rect(surf, (8, 10, 22), camp, border_radius=8)
        pygame.draw.rect(surf, CIAN, camp, 2, border_radius=8)
        r = text(surf, self.codi_text, F_UI, BLANC, (camp.centerx, camp.centery), ombra=False)
        if (self.t_global // 30) % 2:                                    # cursor que parpelleja
            x = r.right + 4 if self.codi_text else camp.centerx
            pygame.draw.rect(surf, BLANC, (x, camp.centery - 10, 3, 20))
        if self.codi_resultat:
            ok, msg = self.codi_resultat
            text(surf, msg, F_HUD, VERD if ok else VERMELL, (caixa.centerx, caixa.bottom + 100))

    def rect_carta_arma(self, i):
        return pygame.Rect(31 + i * 182, 126, 170, 318)

    def estat_arma(self, i):
        """("equipada" | "propia" | "bloquejada" | "venda", text del botó)."""
        arma = ARMES[i]
        if arma["id"] in self.armes_propies:
            return ("equipada", "Equipada") if self.arma_actual == i else ("propia", "Equipar")
        if not self.completat(arma["req"]):
            return "bloquejada", T("Completa {e}").format(e=nom_escenari(arma['req']))
        return "venda", T("Comprar {c}").format(c=arma["cost"])

    def entrar_arma(self, i):
        self.confirmar_reinici = False
        self.arma_detall = i % len(ARMES)
        i = self.arma_detall
        estat, txt = self.estat_arma(i)
        accio = {"propia": lambda: self.equipar_arma(i), "venda": lambda: self.comprar_arma(i)}.get(estat)
        color = {"equipada": VERD, "propia": BLAU, "venda": TARONJA if self.monedes >= ARMES[i]["cost"] else VERMELL_FOSC}
        b = [Boto((30, HEIGHT - 62, 140, 42), "< Volver", lambda: self.entrar_botiga("armes"), GRIS_FOSC),
             Boto((WIDTH - 300, HEIGHT - 66, 270, 46), txt, accio, color.get(estat, GRIS_FOSC),
                  font=F_HUD if estat != "bloquejada" else F_MINI),
             Boto((WIDTH // 2 - 290, 22, 48, 40), "<", lambda: self.entrar_arma(i - 1), BLAU),
             Boto((WIDTH // 2 + 242, 22, 48, 40), ">", lambda: self.entrar_arma(i + 1), BLAU)]
        if estat == "equipada":
            b[1].actiu = False
        self.botons = b
        self.canviar_estat("arma")

    def dibuixar_arma(self, surf):
        self.fons_menu.dibuixar(surf)
        i = self.arma_detall
        arma = ARMES[i]
        t = self.temps_estat
        text(surf, T(arma["nom"]).upper(), F_SUBTITOL, BLANC, (WIDTH // 2, 42))
        r = text(surf, str(self.monedes), F_UI, GROC, (WIDTH - 24, 42), ancora="midright")
        dibuixar_moneda(surf, r.left - 14, 42)
        # el teu Nexus amb l'arma, gran i en moviment
        esq = pygame.Rect(30, 82, 430, 380)
        panell(surf, esq, BLAU_CLAR, 200)
        peus = esq.bottom - 40
        l = llum(150, (90, 140, 255))
        l.set_alpha(60)
        surf.blit(l, l.get_rect(center=(esq.centerx, peus - 70)))
        pygame.draw.ellipse(surf, (10, 12, 26), (esq.centerx - 120, peus - 16, 240, 38))
        pygame.draw.ellipse(surf, (40, 56, 110), (esq.centerx - 112, peus - 13, 224, 30), 3)
        spr = sprites_jugador(arma["id"], self.uniforme, self.aparenca, self.nivell_millora("blindatge"), self.camo_actual(i))
        if spr:
            k = 3
            cicle = t % 150
            dispara = cicle < 24 and cicle % 8 < 3
            fr = (t // 35) % 2
            clau = (arma["id"], self.uniforme, self.aparenca, self.nivell_millora("blindatge"), self.camo_actual(i), fr)
            img = Game.IMATGE_FITXA.get(clau)
            if img is None:
                if len(Game.IMATGE_FITXA) > 20:
                    Game.IMATGE_FITXA.clear()
                base = spr.poses["quiet"][fr][1]
                img = Game.IMATGE_FITXA[clau] = pygame.transform.scale(base, (base.get_width() * k, base.get_height() * k))
            cx = esq.centerx - (spr.cano_dx * k) // 3
            recul = 3 if dispara else 0
            x = int(cx - spr.peus_x * k - recul)
            surf.blit(img, (x, peus - img.get_height()))
            if dispara:
                bx, by = x + (spr.peus_x + spr.cano_dx) * k, peus + spr.cano_dy * k
                fogonazo(surf, bx, by, 0.0, 34, 12, COLOR_ARMA.get(arma["id"], (255, 210, 70)))
        estat, _ = self.estat_arma(i)
        etiqueta = {"equipada": ("EQUIPADA", VERD), "propia": ("EN TU ARSENAL", BLAU_CLAR),
                    "venda": ("A LA VENTA", TARONJA), "bloquejada": ("BLOQUEADA", GRIS)}[estat]
        text(surf, etiqueta[0], F_HUD, etiqueta[1], (esq.centerx, esq.y + 22))
        # dades
        dre = pygame.Rect(480, 82, 450, 380)
        panell(surf, dre, BLAU_CLAR, 200)
        x0, y = dre.x + 22, dre.y + 26
        maxims = {"dany": max(a["dany"] * a["perdigons"] for a in ARMES), "cad": max(FPS / a["cadencia"] for a in ARMES)}
        bmax = self.bales_max(i)
        dany = round(arma["dany"] * self.multiplicador_dany())
        files = [
            ("Daño", f"{dany}" + (f" x{arma['perdigons']}" if arma["perdigons"] > 1 else ""),
             arma["dany"] * arma["perdigons"] / maxims["dany"]),
            ("Disparos por segundo", str(round(FPS / arma["cadencia"], 1)), (FPS / arma["cadencia"]) / maxims["cad"]),
            ("Cargador", T("Sin límite (se calienta)") if bmax is None else str(bmax),
             1.0 if bmax is None else min(1.0, bmax / 40)),
            ("Precisión", ["", "Muy alta", "Alta", "Media", "Baja", "Muy baja"][min(5, max(1, round(arma["dispersio"] / 1.5) + 1))],
             max(0.1, 1 - arma["dispersio"] / 8)),
        ]
        for nom_f, valor, fr in files:
            text(surf, nom_f, F_TEXT_P, GRIS, (x0, y), ancora="midleft", ombra=False)
            text(surf, valor, F_TEXT_P, BLANC, (dre.right - 22, y), ancora="midright", ombra=False)
            barra = pygame.Rect(x0, y + 14, dre.w - 44, 6)
            pygame.draw.rect(surf, (40, 42, 60), barra, border_radius=3)
            pygame.draw.rect(surf, TARONJA, (barra.x, barra.y, int(barra.w * max(0.0, min(1.0, fr))), barra.h), border_radius=3)
            y += 40
        extres = [("Modo", T("Automática") if arma["auto"] else T("Semiautomática")),
                  ("Alcance", T("Corto") if arma["vida_bala"] else T("Largo")),
                  ("Atraviesa enemigos", T("Sí") if arma["perfora"] else T("No"))]
        for nom_f, valor in extres:
            text(surf, nom_f, F_TEXT_P, GRIS, (x0, y), ancora="midleft", ombra=False)
            text(surf, valor, F_TEXT_P, BLANC, (dre.right - 22, y), ancora="midright", ombra=False)
            y += 24
        text(surf, "Potencia", F_TEXT_P, GRIS, (x0, y + 4), ancora="midleft", ombra=False)
        dibuixar_pips(surf, dre.right - 22 - 5 * 15, y - 1, arma["potencia"], color=TARONJA, mida=12)
        y += 30
        linies = ajustar_linies(T(DETALL_ARMES.get(arma["id"], arma["desc"])), F_TEXT_P, dre.w - 44)[:3]
        for j, linia in enumerate(linies):
            text(surf, linia, F_TEXT_P, CIAN, (x0, y + j * 22), ancora="midleft")
        y += 22 * len(linies) + 8
        nivell = self.nivell_mestria(arma["id"])
        camo = self.camo_actual(i)
        txt = T("Maestría {n}/10").format(n=nivell)
        if camo:
            txt += " · " + T(CAMUFLATGES[camo]["nom"])
        text(surf, txt, F_TEXT_PP, (255, 200, 120), (x0, y), ancora="midleft")
        if not self.missatge:
            info = "La potencia decide en qué escenarios se puede usar cada arma."
            if estat == "bloquejada":
                info = T("Disponible al completar {e}.").format(e=nom_escenari(arma["req"]))
            text(surf, info, F_TEXT_PP, GRIS, (WIDTH // 2 - 40, HEIGHT - 20))

    IMATGE_FITXA = {}

    # ----- Personalitzar (clic a Nexus al menú) ---------------------------------------------------------

    def entrar_personalitzar(self):
        self.confirmar_reinici = False
        self.botons = self.botons_aspecte() + [self.boto_tornar()]
        self.marcar_vist("personalitzar")
        self.canviar_estat("personalitzar")

    def dibuixar_personalitzar(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "PERSONALIZAR", F_SUBTITOL, BLANC, (WIDTH // 2, 40))
        r = text(surf, str(self.monedes), F_UI, GROC, (WIDTH - 24, 40), ancora="midright")
        dibuixar_moneda(surf, r.left - 14, 40)
        self.dibuixar_botiga_aparenca(surf)

    def rect_nexus_menu(self):
        return pygame.Rect(426, 296, 160, 172)

    def atacs_comandant(self, e, j, rj):
        """Ones, impacte del cop de terra, tremolor i raig làser del Comandant Suprem."""
        e.parlant = self.radio.parla("ment")                 # mou la boca quan parla per la ràdio
        for x, sentit in e.ones_noves:
            self.ones_xoc.append(OnaXoc(x, sentit, e.dany))
        e.ones_noves = []
        if e.tremolor_nou:
            self.tremolor = max(self.tremolor, e.tremolor_nou)
            e.tremolor_nou = 0
        jugant = self.fase == "jugant" and not j.intocable
        if e.impacte:
            e.impacte = False
            if jugant and abs(j.centre[0] - e.centre[0]) < 90 and j.y + j.H > TERRA_Y - 70:
                self.ferir_jugador(round(e.dany * 1.5))
        if e.laser and jugant and rj.clipline(e.laser[0], e.laser[1]):
            self.ferir_jugador(e.dany)

    def dibuixar_joc(self, surf):
        c = self.capa
        fons = FONS_NIVELLS.get((self.nivell_actual, self.escenari_actual))
        if fons and self.mode == "desafiament":
            fons = self.fons_desafiament(fons)
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
        for o in self.ones_xoc:
            o.dibuixar(c)
        for r in self.restes:
            r.dibuixar(c)
        spr = self.spr_jugador()
        if self.fase != "mort":
            self.dibuixar_iman(c)
            self.jugador.dibuixar(c, spr)
            if self.dron_company:
                self.dron_company.dibuixar(c)
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
                noms = [T("Completado"), T("En menos de {s} s").format(s=limit), T("Sin recibir daño")]
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

    def dibuixar_avisos(self, surf, y, x=WIDTH // 2, font=F_HUD, ample=WIDTH - 20, pas=26):
        k = 0
        for txt, color, temps in self.avisos:
            linies = ajustar_linies(T(txt), font, ample - 18) if font.size(T(txt))[0] > ample - 18 else [T(txt)]
            for linia in linies[:2]:
                self._avis_linia(surf, linia, color, font, (x, y + k * pas))
                k += 1

    def _avis_linia(self, surf, txt, color, font, centre):
        img = render(txt, font, color)
        caixa = img.get_rect(center=centre).inflate(18, 10)
        capa = pygame.Surface(caixa.size, pygame.SRCALPHA)
        capa.fill((10, 8, 24, 200))
        surf.blit(capa, caixa)
        pygame.draw.rect(surf, color, caixa, 1, border_radius=4)
        surf.blit(img, img.get_rect(center=caixa.center))

    def dibuixar_menu(self, surf):
        self.fons_viu(surf)
        t = self.t_global
        LOGO_PETIT.dibuixar(surf, 311, 16, t)
        pos = ratoli()
        nous = self.novetats_menu()
        for k, (ident, nom) in enumerate(self.BOTONS_MENU):
            r = self.rect_boto_menu(k)
            hover = r.collidepoint(pos)
            entrada = max(0.0, min(1.0, (self.temps_estat - k * 4) / 14))
            r = r.move(int(-60 * (1 - entrada) ** 2) + (8 if hover else 0), 0)
            principal = ident == "jugar"
            base = (40, 150, 80) if principal else (34, 44, 92)
            color = aclarir(base, 40) if hover else base
            pygame.draw.rect(surf, NEGRE, r.move(0, 4), border_radius=8)
            pygame.draw.rect(surf, color, r, border_radius=8)
            pygame.draw.rect(surf, aclarir(color, 80) if hover else aclarir(color, 40), r, 2, border_radius=8)
            if hover:
                pygame.draw.rect(surf, BLANC, (r.x, r.y + 6, 4, r.h - 12))
            dibuixar_icona_menu(surf, ident, r.x + 34, r.centery, t if hover else 0)
            text(surf, T(nom), F_UI if principal else F_HUD, BLANC, (r.x + 70, r.centery), ancora="midleft")
            if nous.get(ident):
                cx, cy = r.right - 14, r.y + 10
                pygame.draw.circle(surf, NEGRE, (cx, cy + 1), 7)
                pygame.draw.circle(surf, VERMELL, (cx, cy), 6 + (1 if (t // 20) % 2 else 0))
                pygame.draw.circle(surf, (255, 180, 180), (cx - 2, cy - 2), 2)
        self.dibuixar_icones_menu(surf)
        # soldat: clic per personalitzar
        cx, peus = 506, 450
        hover_nexus = self.rect_nexus_menu().collidepoint(pos)
        if hover_nexus:
            l = llum(110, (120, 200, 255))
            l.set_alpha(90)
            surf.blit(l, l.get_rect(center=(cx, peus - 60)))
        self.aparador.dibuixar(surf, self, cx, peus)
        etiqueta = text(surf, "PERSONALIZAR", F_MINI, BLANC if hover_nexus else (150, 160, 200), (cx, peus + 27))
        if hover_nexus:
            pygame.draw.rect(surf, BLAU_CLAR, etiqueta.inflate(14, 8), 1, border_radius=4)
        if nous.get("nexus"):
            bx, by = etiqueta.right + 10, etiqueta.centery
            pygame.draw.circle(surf, NEGRE, (bx, by + 1), 7)
            pygame.draw.circle(surf, VERMELL, (bx, by), 6 + (1 if (t // 20) % 2 else 0))
            pygame.draw.circle(surf, (255, 180, 180), (bx - 2, by - 2), 2)
        # targeta i destacat
        dibuixar_targeta(surf, (WIDTH - 316, 14, 300, 90), self.targeta, self.titol, self.rang_actual(), self.temporada,
                         self.nivell_passi(), self.temporada - 1, self.monedes, self.estrelles_totals())
        self.dibuixar_destacat(surf, self.rect_destacat())
        estat_so = "M: sonido OFF" if AUDIO.silenci else "M: sonido ON"
        text(surf, estat_so, F_MINI, GRIS, (20, HEIGHT - 20), ancora="midleft")
        self.dibuixar_avisos(surf, 346, x=WIDTH - 166, font=F_MINI, ample=300, pas=20)

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
             (WIDTH // 2 - 20, HEIGHT - 16))

    def dibuixar_botiga(self, surf):
        self.fons_menu.dibuixar(surf)
        text(surf, "TIENDA", F_SUBTITOL, BLANC, (WIDTH // 2, 40))
        r = text(surf, str(self.monedes), F_UI, GROC, (WIDTH - 24, 40), ancora="midright")
        dibuixar_moneda(surf, r.left - 14, 40)
        rc = self.RECT_CALCULADORA                              # codis
        hover = rc.collidepoint(ratoli())
        pygame.draw.rect(surf, NEGRE, rc.move(0, 3), border_radius=8)
        pygame.draw.rect(surf, (52, 60, 110) if hover else (30, 34, 66), rc, border_radius=8)
        pygame.draw.rect(surf, BLAU_CLAR if hover else (80, 90, 140), rc, 2, border_radius=8)
        dibuixar_calculadora(surf, rc.centerx, rc.centery)
        if hover:
            text(surf, T("Códigos"), F_MINI, BLANC, (rc.centerx, rc.bottom + 12))
        if self.pestanya == "armes":
            self.dibuixar_botiga_armes(surf)
        elif self.pestanya == "millores":
            self.dibuixar_botiga_millores(surf)
        else:
            self.dibuixar_botiga_ofertes(surf)

    def dibuixar_botiga_armes(self, surf):
        pos = ratoli()
        t = self.t_global
        for i, arma in enumerate(ARMES):
            carta = self.rect_carta_arma(i)
            estat, txt = self.estat_arma(i)
            hover = carta.collidepoint(pos)
            vora = {"equipada": VERD, "propia": BLAU_CLAR, "venda": TARONJA}.get(estat, GRIS_FOSC)
            panell(surf, carta.move(0, -3 if hover else 0), aclarir(vora, 60) if hover else vora)
            c = carta.move(0, -3 if hover else 0)
            text(surf, T(arma["nom"]).upper(), F_TEXT_P, BLANC, (c.centerx, c.top + 20))
            # l'arma sola, sobre un focus de llum
            zona = pygame.Rect(c.x + 8, c.y + 40, c.w - 16, 110)
            l = llum(52, (255, 200, 120) if estat != "bloquejada" else (90, 90, 110))
            l.set_alpha(110)
            surf.blit(l, l.get_rect(center=zona.center))
            ample = NEXUS["armes_soles"][arma["id"]][2] if NEXUS else 40
            img = imatge_arma(arma["id"], self.aparenca, self.camo_actual(i), max(1, min(4, zona.w // max(1, ample))))
            if img:
                if estat == "bloquejada":
                    img = img.copy()
                    img.fill((60, 60, 70, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(img, img.get_rect(center=(zona.centerx, zona.centery + int(math.sin(t * 0.06 + i) * 3))))
            if estat == "bloquejada":
                dibuixar_cadenat(surf, zona.centerx, zona.centery)
            text(surf, "Potencia", F_TEXT_PP, GRIS, (c.left + 12, c.top + 170), ancora="midleft", ombra=False)
            dibuixar_pips(surf, c.left + 14, c.top + 184, arma["potencia"], color=TARONJA)
            nivell = self.nivell_mestria(arma["id"])
            text(surf, T("Maestría {n}").format(n=nivell), F_TEXT_PP, (255, 200, 120), (c.left + 12, c.top + 212),
                 ancora="midleft", ombra=False)
            caixa = pygame.Rect(c.x + 12, c.bottom - 48, c.w - 24, 34)
            color = {"equipada": VERD, "propia": BLAU, "venda": TARONJA}.get(estat, GRIS_FOSC)
            if estat == "venda" and self.monedes < arma["cost"]:
                color = VERMELL_FOSC
            pygame.draw.rect(surf, color, caixa, border_radius=8)
            pygame.draw.rect(surf, aclarir(color, 60), caixa, 2, border_radius=8)
            text(surf, txt, F_MINI, BLANC if estat != "bloquejada" else GRIS, caixa.center)
        if self.missatge:
            return
        text(surf, "Haz clic en un arma para verla en tus manos con todos sus datos.", F_TEXT_PP, CIAN,
             (WIDTH // 2 + 80, 499))

    # ----- Fitxa d'una arma: el teu Nexus amb l'arma i les dades ----------------------------------------

    def dibuixar_botiga_millores(self, surf):
        for k, m in enumerate(MILLORES):
            fila = pygame.Rect(60, 128 + k * 56, 840, 50)
            nivell = self.nivell_millora(m["id"])
            panell(surf, fila, VERD if nivell >= len(m["costos"]) else BLAU_CLAR)
            text(surf, m["nom"], F_UI, BLANC, (fila.left + 16, fila.top + 15), ancora="midleft")
            text(surf, m["desc"], F_TEXT_P, GRIS, (fila.left + 16, fila.top + 36), ancora="midleft", ombra=False)
            dibuixar_pips(surf, 604, fila.top + 18, nivell, total=len(m["costos"]), color=VERD, mida=14)
        if not self.missatge:
            text(surf, "Las mejoras se abren al avanzar en la historia; el último nivel pide estrellas.", F_TEXT_P, CIAN,
                 (WIDTH // 2 + 80, 499))

    def dibuixar_botiga_aparenca(self, surf):
        t = self.t_global
        cat = getattr(self, "cat_aspecte", "uniforme")
        pos = ratoli()
        info = None
        # comptador de cada categoria al costat del botó
        for k, (ident, _) in enumerate(self.CATEGORIES_ASPECTE):
            if ident == "camo":
                fets = sum(self.camo_obert(a["id"], c) for a in ARMES for c in CAMUFLATGES if c != "cap")
                total = len(ARMES) * (len(CAMUFLATGES) - 1)
            else:
                visibles = self.cosmetics_visibles(ident)
                fets = sum(PREFIX_COSMETIC[ident] + i in self.cosmetics for i in visibles)
                total = len(visibles)
            text(surf, f"{fets}/{total}", F_MINI, GRIS, (186, 139 + k * 34), ancora="midleft")
        if cat == "camo":
            arma_id = getattr(self, "arma_camo", ARMES[self.arma_actual]["id"])
            for k, a in enumerate(ARMES):
                r = pygame.Rect(236 + k * 140, 124, 130, 36)
                panell(surf, r, VERD if a["id"] == arma_id else GRIS_FOSC)
                ic = ICONES_ARMA[a["id"]][1]
                surf.blit(ic, ic.get_rect(center=(r.x + 26, r.centery)))
                text(surf, T("Nv {n}").format(n=self.nivell_mestria(a["id"])), F_MINI, BLANC, (r.right - 8, r.centery),
                     ancora="midright")
            for k, (camo, dades) in enumerate(CAMUFLATGES.items()):
                r = pygame.Rect(236 + k * 140, 170, 130, 170)
                obert = self.camo_obert(arma_id, camo)
                equipat = (self.camos.get(arma_id) or "cap") == camo
                hover = r.collidepoint(pos)
                panell(surf, r, VERD if equipat else (BLAU_CLAR if obert and hover else (GRIS if obert else GRIS_FOSC)))
                img = mostra_soldat(arma_id, self.uniforme, self.aparenca, None if camo == "cap" else camo)
                if not obert:
                    img = img.copy()
                    img.fill((60, 60, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(img, img.get_rect(center=(r.centerx, r.y + 70)))
                if camo == "diamant" and obert and (t // 6) % 4 == 0:
                    pygame.draw.circle(surf, BLANC, (r.centerx + random.randint(-20, 20), r.y + random.randint(40, 100)), 2)
                text(surf, T(dades["nom"]), F_MINI, BLANC if obert else GRIS, (r.centerx, r.bottom - 34))
                req = T("Todas en oro") if camo == "diamant" else T("Maestría {n}").format(n=dades["nivell"])
                text(surf, req, F_MINI, VERD if obert else (255, 170, 120), (r.centerx, r.bottom - 16))
                if hover:
                    info = T("Sube de nivel de maestría eliminando enemigos con esta arma.")
            nivell = self.nivell_mestria(arma_id)
            b = self.baixes_arma.get(arma_id, 0)
            barra = pygame.Rect(236, 362, 690, 12)
            pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=5)
            if nivell < 10:
                ini, fi = MAESTRIA[nivell - 1], MAESTRIA[nivell]
                pygame.draw.rect(surf, (255, 200, 120), (barra.x, barra.y, int(barra.w * (b - ini) / (fi - ini)), barra.h),
                                 border_radius=5)
                txt = T("Maestría {a}: nivel {n}/10 · {b}/{f} bajas para el siguiente").format(
                    a=T(ARMES[ARMA_PER_ID[arma_id]]["nom"]), n=nivell, b=b, f=fi)
            else:
                pygame.draw.rect(surf, GROC, barra, border_radius=5)
                txt = T("Maestría {a}: nivel máximo ({b} bajas)").format(a=T(ARMES[ARMA_PER_ID[arma_id]]["nom"]), b=b)
            text(surf, txt, F_TEXT_P, BLANC, (barra.centerx, barra.bottom + 20))
        else:
            equipat = self.equipat_de(cat)
            for k, ident in enumerate(self.cosmetics_visibles(cat)):
                r = self.rect_cosmetic(k)
                obert = PREFIX_COSMETIC[cat] + ident in self.cosmetics
                hover = r.collidepoint(pos)
                panell(surf, r, VERD if equipat == ident else (BLAU_CLAR if obert and hover else (GRIS if obert else GRIS_FOSC)))
                self.previsualitzar(surf, cat, ident, r, t + k * 13)
                if not obert:
                    capa = pygame.Surface((r.w - 4, r.h - 4), pygame.SRCALPHA)
                    capa.fill((0, 0, 0, 120))
                    surf.blit(capa, (r.x + 2, r.y + 2))
                    dibuixar_cadenat(surf, r.right - 14, r.y + 14)
                if cat != "titol":
                    text(surf, nom_cosmetic(cat, ident), F_MINI, BLANC if obert else GRIS, (r.centerx, r.bottom - 12))
                if hover:
                    info = (T("Equipado") if equipat == ident else T("Clic para equipar")) if obert else self.origen_cosmetic(cat, ident)
        if not self.missatge:
            text(surf, info or T("Consigue más en el Battle Pass, los rangos, los desafíos y las ofertas del día."),
                 F_TEXT_PP, CIAN, (WIDTH // 2 + 80, 499))

    # ----- Battle Pass per pàgines ------------------------------------------------------------------

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
        text(surf, f"BATTLE PASS · {T('TEMPORADA')} {self.temporada}", F_SUBTITOL, (255, 200, 255), (WIDTH // 2, 34))
        for k in range(min(self.temporada - 1, 8)):
            dibuixar_estrella(surf, WIDTH // 2 + 250 + k * 16, 36, 7, True, (190, 140, 255))
        nivell, fet, cal = self.progres_passi()
        barra = pygame.Rect(WIDTH // 2 - 350, 84, 700, 10)
        pygame.draw.rect(surf, GRIS_FOSC, barra, border_radius=6)
        fr = 1.0 if nivell >= len(PASSI) else fet / cal
        pygame.draw.rect(surf, (255, 130, 255), (barra.x, barra.y, int(barra.w * fr), barra.h), border_radius=6)
        txt = (T("Nivel {n}/{t} · {x}/{m} XP").format(n=nivell, t=len(PASSI), x=fet, m=cal)
               if nivell < len(PASSI) else T("Nivel máximo · {x} XP").format(x=self.xp_passi))
        text(surf, txt, F_HUD, BLANC, (barra.centerx, barra.top - 12))
        pos_ratoli = ratoli()
        descripcio = None
        inici = self.pagina_passi * 20
        for k, recompenses in enumerate(PASSI[inici:inici + 20]):
            i = inici + k
            fila, col = divmod(k, 10)
            r = pygame.Rect(44 + col * 88, 106 + fila * 140, 80, 130)
            aconseguit = i < self.passi_reclamat
            panell(surf, r, VERD if aconseguit else ((255, 130, 255) if i == nivell else GRIS_FOSC))
            text(surf, str(i + 1), F_HUD, BLANC if aconseguit else GRIS, (r.centerx, r.top + 14))
            tipus, valor = recompenses[0]
            self.dibuixar_recompensa(surf, tipus, valor, (r.centerx, r.top + 62), self.t_global + i * 7)
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
                descripcio = T("Nivel {n}").format(n=i + 1) + ": " + " + ".join(nom_premi(t, v) for t, v in recompenses)
        text(surf, descripcio or "Cada nivel pide un poco más de XP. Al llegar al 50 empieza una temporada nueva.",
             F_TEXT_P, CIAN if descripcio else GRIS, (WIDTH // 2, 400))
        text(surf, T("Página {p}/{t}").format(p=self.pagina_passi + 1, t=(len(PASSI) - 1) // 20 + 1), F_HUD, BLANC,
             (WIDTH // 2, 488))
        text(surf, "Equipa lo que consigas en Personalizar: haz clic en Nexus en el menú.", F_TEXT_PP, GRIS, (WIDTH // 2, 430))

    # ----- Colección: maestría, rangos y bestiario ---------------------------------------------------

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
        if self.estat == "codis" and ev.type == pygame.KEYDOWN:
            self.tecla_codi(ev)
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
        elif self.estat == "desafiaments":
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_g):
                self.entrar_jugar()
        elif self.estat == "revelacio":
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                self.seguent_revelacio()
        elif self.estat == "jugar":
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_g):
                self.entrar_menu()
        elif self.estat in ("selector", "arxiu", "supervivencia"):
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_g):
                self.entrar_jugar()
        elif self.estat == "arma":
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_g):
                self.entrar_botiga("armes")
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_LEFT, pygame.K_a):
                self.entrar_arma(self.arma_detall - 1)
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RIGHT, pygame.K_d):
                self.entrar_arma(self.arma_detall + 1)
        elif self.estat in ("botiga", "guia", "credits", "passi", "logros", "colleccio", "diari", "personalitzar"):
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_g):
                self.entrar_menu()

    # ----- Bucle principal --------------------------------------------------
    def actualitzar(self):
        self.temps_estat += 1
        self.t_global += 1
        self.actualitzar_menu()
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
        elif self.estat == "revelacio" and self.revelacio[0] == "teddy":
            self.actualitzar_revelacio_teddy()

    def dibuixar(self, surf):
        dibuix = {
            "loading": self.dibuixar_loading, "menu": self.dibuixar_menu, "selector": self.dibuixar_selector,
            "botiga": self.dibuixar_botiga, "codis": self.dibuixar_codis, "arma": self.dibuixar_arma,
            "personalitzar": self.dibuixar_personalitzar, "guia": self.dibuixar_guia, "credits": self.dibuixar_credits,
            "joc": self.dibuixar_joc, "pausa": self.dibuixar_pausa, "passi": self.dibuixar_passi,
            "arxiu": self.dibuixar_arxiu, "intro": lambda s: self.intro.dibuixar(s), "opcions": self.dibuixar_opcions,
            "supervivencia": self.dibuixar_supervivencia, "logros": self.dibuixar_logros,
            "idioma_inicial": self.dibuixar_idioma_inicial, "ajuda": self.dibuixar_ajuda,
            "novetats": self.dibuixar_novetats, "colleccio": self.dibuixar_colleccio,
            "desafiaments": self.dibuixar_desafiaments, "diari": self.dibuixar_diari,
            "jugar": self.dibuixar_jugar, "revelacio": self.dibuixar_revelacio,
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
            if self.estat in ("botiga", "personalitzar"):
                text(surf, self.missatge, F_HUD, col, (WIDTH // 2 + 80, 499))
            elif self.estat == "arma":
                text(surf, self.missatge, F_HUD, col, (WIDTH // 2 - 40, HEIGHT - 20))
            else:
                text(surf, self.missatge, F_HUD, col, (WIDTH // 2 - 60, HEIGHT - 28))
        if self.avisos_logro and self.estat != "loading":
            self.dibuixar_avisos_logro(surf)
        trans = getattr(self, "transicio", None)
        if trans:
            trans[0].set_alpha(int(255 * (trans[1] / 12) ** 1.5))
            surf.blit(trans[0], (0, -int((12 - trans[1]) * 1.5)))
            trans[1] -= 1
            if trans[1] <= 0:
                self.transicio = None

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
MIDA_LOGO_MENU = (606, 0.64)               # logo del menú: planeta de 606 px d'ample i text a escala 0.66
LOGO_PETIT = Logo(*MIDA_LOGO_MENU)


def canviar_idioma(codi):
    """Canvia l'idioma i torna a dibuixar els logotips (tenen el títol del joc)."""
    global LOGO_MENU, LOGO_GRAN, LOGO_PETIT
    posar_idioma(codi)
    LOGO_MENU = Logo(440)
    LOGO_GRAN = Logo(560)
    LOGO_PETIT = Logo(*MIDA_LOGO_MENU)
VINYETA = crear_vinyeta()


def crear_degradat(alt, cap_avall):
    s = pygame.Surface((WIDTH, alt), pygame.SRCALPHA)
    for y in range(alt):
        k = (1 - y / alt) if cap_avall else (y / alt)
        pygame.draw.line(s, (*FONS, int(255 * k ** 1.3)), (0, y), (WIDTH, y))
    return s


DEGRADAT_DALT = crear_degradat(70, True)


def crear_degradat_menu():
    """Enfosqueix el fons viu del menú (més a l'esquerra, on hi ha els botons)."""
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for x in range(WIDTH):
        k = 1 - x / WIDTH
        s.fill((6, 8, 20, int(110 + 110 * k ** 1.5)), (x, 0, 1, HEIGHT))
    return s


DEGRADAT_MENU = crear_degradat_menu()
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
