"""
Launcher d'Invasión Alienígena (Windows)
========================================
Programa petit que els jugadors instal·len un sol cop. Cada vegada que s'obre:

1. Llegeix el manifest de la darrera versió publicada (version.json, a les Releases de GitHub).
2. Si hi ha una versió del joc més nova, la baixa amb barra de progrés, comprova el SHA-256,
   la descomprimeix a una carpeta nova i només llavors la marca com a instal·lada
   (si alguna cosa falla, es continua jugant amb la versió anterior, que es conserva).
3. Si hi ha un launcher més nou, s'actualitza ell mateix i es torna a obrir.
4. El botó JUGAR obre el joc i el launcher es tanca.

La partida no es toca mai: el joc la desa a %APPDATA%\\InvasionAlienigena i les versions
s'instal·len a %LOCALAPPDATA%\\InvasionAlienigena\\joc\\<versió>.

Proves (sense finestra):  LAUNCHER_DIR=carpeta  LAUNCHER_MANIFEST=url  SDL_VIDEODRIVER=dummy
"""
import hashlib
import json
import locale
import math
import os
import random
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile

import pygame

VERSIO_LAUNCHER = 1
MANIFEST = "https://github.com/abelber07/historygame/releases/latest/download/version.json"
AGENT = f"InvasionAlienigena-Launcher/{VERSIO_LAUNCHER}"
W, H = 960, 540
FPS = 30

BLANC = (255, 255, 255)
NEGRE = (8, 8, 16)
GRIS = (130, 134, 160)
CIAN = (90, 230, 255)
VERD = (80, 220, 120)
VERD_FOSC = (36, 120, 70)
GROC = (255, 214, 64)
VERMELL = (235, 70, 70)
FONS_DALT, FONS_BAIX = (10, 12, 30), (26, 20, 54)


# ---------------------------------------------------------------------------
# Textos (castellà, català i anglès; l'idioma és el mateix que el del joc)
# ---------------------------------------------------------------------------
TEXTOS = {
    "es": {
        "comprovant": "Buscando actualizaciones...", "baixant": "Descargando la versión {v}...",
        "instal": "Instalando...", "llest": "Todo listo. ¡A jugar!", "nou": "¡Versión {v} instalada!",
        "jugar": "JUGAR", "sortir": "Salir", "reintentar": "Reintentar", "obrint": "Abriendo el juego...",
        "sense_xarxa": "Sin conexión: se juega con la versión instalada.",
        "sense_xarxa_res": "No se pudo conectar. Revisa tu conexión a internet.",
        "error": "Error: {e}", "corrupte": "La descarga llegó dañada. Vuelve a intentarlo.",
        "novetats": "NOVEDADES", "installada": "Instalada: {v}", "cap": "ninguna",
        "launcher_nou": "Actualizando el launcher...", "no_obre": "No se pudo abrir el juego: {e}",
        "mb": "{a} de {t} MB", "sense_novetats": "Sin novedades por ahora.",
    },
    "ca": {
        "comprovant": "Buscant actualitzacions...", "baixant": "Baixant la versió {v}...",
        "instal": "Instal·lant...", "llest": "Tot a punt. A jugar!", "nou": "Versió {v} instal·lada!",
        "jugar": "JUGAR", "sortir": "Sortir", "reintentar": "Torna-ho a provar", "obrint": "Obrint el joc...",
        "sense_xarxa": "Sense connexió: es juga amb la versió instal·lada.",
        "sense_xarxa_res": "No s'ha pogut connectar. Revisa la connexió a internet.",
        "error": "Error: {e}", "corrupte": "La baixada ha arribat malmesa. Torna-ho a provar.",
        "novetats": "NOVETATS", "installada": "Instal·lada: {v}", "cap": "cap",
        "launcher_nou": "Actualitzant el launcher...", "no_obre": "No s'ha pogut obrir el joc: {e}",
        "mb": "{a} de {t} MB", "sense_novetats": "Encara no hi ha novetats.",
    },
    "en": {
        "comprovant": "Checking for updates...", "baixant": "Downloading version {v}...",
        "instal": "Installing...", "llest": "All set. Let's play!", "nou": "Version {v} installed!",
        "jugar": "PLAY", "sortir": "Quit", "reintentar": "Try again", "obrint": "Starting the game...",
        "sense_xarxa": "Offline: playing the installed version.",
        "sense_xarxa_res": "Couldn't connect. Check your internet connection.",
        "error": "Error: {e}", "corrupte": "The download was damaged. Please try again.",
        "novetats": "WHAT'S NEW", "installada": "Installed: {v}", "cap": "none",
        "launcher_nou": "Updating the launcher...", "no_obre": "Couldn't start the game: {e}",
        "mb": "{a} of {t} MB", "sense_novetats": "Nothing new yet.",
    },
}


# ---------------------------------------------------------------------------
# Carpetes i fitxers
# ---------------------------------------------------------------------------
def carpeta_dades():
    """On el joc desa la partida (la fem servir per llegir l'idioma triat)."""
    if os.environ.get("LAUNCHER_DIR"):
        return os.path.join(os.environ["LAUNCHER_DIR"], "dades")
    if os.name == "nt":
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "InvasionAlienigena")
    return os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "InvasionAlienigena")


def carpeta_instal():
    """On s'instal·len les versions del joc."""
    if os.environ.get("LAUNCHER_DIR"):
        return os.path.join(os.environ["LAUNCHER_DIR"], "instal")
    if os.name == "nt":
        arrel = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(arrel, "InvasionAlienigena")
    return os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"),
                        "InvasionAlienigena-launcher")


def recurs(*parts):
    """Fitxers del launcher (fonts, logotip): al costat del .py o dins del .exe compilat."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    for base in (aqui, os.path.dirname(aqui)):
        p = os.path.join(base, *parts)
        if os.path.exists(p):
            return p
    alt = {"fonts": ("assets", "fonts")}.get(parts[0])
    if alt:
        return os.path.join(os.path.dirname(aqui), *alt, *parts[1:])
    return os.path.join(aqui, *parts)


def llegir_json(ruta, defecte=None):
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else (defecte or {})
    except (OSError, ValueError):
        return defecte or {}


def escriure_json(ruta, dades):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dades, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def versio_tupla(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


def idioma_inicial():
    partida = llegir_json(os.path.join(carpeta_dades(), "partida.json"))
    triat = (partida.get("opcions") or {}).get("idioma") if isinstance(partida.get("opcions"), dict) else None
    if triat in TEXTOS:
        return triat
    try:
        loc = (locale.getlocale()[0] or "").lower()
    except (ValueError, TypeError):
        loc = ""
    if loc.startswith("ca") or "catal" in loc:
        return "ca"
    if loc.startswith("en") or "english" in loc:
        return "en"
    return "es"


# ---------------------------------------------------------------------------
# Xarxa
# ---------------------------------------------------------------------------
def obrir_url(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Cache-Control": "no-cache"})
    return urllib.request.urlopen(req, timeout=timeout)


def baixar_manifest(url):
    with obrir_url(url, timeout=12) as r:
        dades = json.loads(r.read().decode("utf-8"))
    if not isinstance(dades, dict) or "versio" not in dades or "joc" not in dades:
        raise ValueError("manifest incorrecte")
    return dades


def baixar_fitxer(url, desti, sha256, progres, cancelat=lambda: False):
    """Baixa `url` a `desti` comprovant el SHA-256. `progres(fets, total)` es crida mentre baixa."""
    os.makedirs(os.path.dirname(desti), exist_ok=True)
    tmp = desti + ".part"
    h = hashlib.sha256()
    with obrir_url(url, timeout=30) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        fets = 0
        while True:
            bloc = r.read(256 * 1024)
            if not bloc:
                break
            if cancelat():
                raise InterruptedError("cancelat")
            f.write(bloc)
            h.update(bloc)
            fets += len(bloc)
            progres(fets, total)
    if sha256 and h.hexdigest().lower() != sha256.lower():
        os.remove(tmp)
        raise ValueError("sha256")
    os.replace(tmp, desti)


# ---------------------------------------------------------------------------
# Actualitzador (va en un fil a part: la finestra no es congela mentre baixa)
# ---------------------------------------------------------------------------
class Actualitzador:
    def __init__(self):
        self.inst = carpeta_instal()
        self.config = llegir_json(os.path.join(self.inst, "launcher.json"))
        self.installada = llegir_json(os.path.join(self.inst, "installada.json"))
        self.estat = "comprovant"         # comprovant, baixant, instal, llest, sense_xarxa, error, launcher
        self.detall = ""
        self.progres = (0, 0)
        self.manifest = None
        self.versio_nova = None
        self.acabat_ara = False           # s'acaba d'instal·lar una versió nova
        self.fil = None

    @property
    def url_manifest(self):
        return os.environ.get("LAUNCHER_MANIFEST") or self.config.get("manifest") or MANIFEST

    def executable(self):
        """Ruta de l'executable del joc instal·lat (o None)."""
        carpeta, exe = self.installada.get("carpeta"), self.installada.get("executable")
        if not carpeta or not exe:
            return None
        ruta = os.path.join(self.inst, "joc", carpeta, exe)
        return ruta if os.path.exists(ruta) else None

    def començar(self):
        self.estat, self.detall, self.progres = "comprovant", "", (0, 0)
        self.fil = threading.Thread(target=self._treballar, daemon=True)
        self.fil.start()

    def _treballar(self):
        try:
            self.manifest = m = baixar_manifest(self.url_manifest)
            # el manifest pot indicar una adreça nova (si les versions es publiquen en un altre lloc)
            nou_origen = m.get("manifest")
            if nou_origen and nou_origen != self.url_manifest and not os.environ.get("LAUNCHER_MANIFEST"):
                self.config["manifest"] = nou_origen
                escriure_json(os.path.join(self.inst, "launcher.json"), self.config)
                self.manifest = m = baixar_manifest(nou_origen)
            if self._actualitzar_launcher(m):
                return
            joc = m["joc"]
            if versio_tupla(m["versio"]) > versio_tupla(self.installada.get("versio", "0")) or not self.executable():
                self._instalar(m["versio"], joc)
            self.estat = "llest"
        except InterruptedError:
            pass
        except ValueError as err:
            self.estat, self.detall = "error", "corrupte" if str(err) == "sha256" else str(err)
        except Exception as err:          # sense xarxa, servidor caigut, disc ple...
            xarxa = isinstance(err, (OSError, TimeoutError)) and not isinstance(err, PermissionError)
            if xarxa and self.executable():
                self.estat = "sense_xarxa"
            else:
                self.estat = "error" if self.executable() or not xarxa else "sense_xarxa_res"
                self.detall = str(err)[:120]

    def _instalar(self, versio, joc):
        self.versio_nova = versio
        self.estat = "baixant"
        zip_ruta = os.path.join(self.inst, "baixades", f"joc-{versio}.zip")
        baixar_fitxer(joc["url"], zip_ruta, joc.get("sha256"), self._progres)
        self.estat = "instal"
        desti = os.path.join(self.inst, "joc", versio)
        tmp = desti + ".tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        with zipfile.ZipFile(zip_ruta) as z:
            z.extractall(tmp)
        shutil.rmtree(desti, ignore_errors=True)
        os.replace(tmp, desti)
        anterior = self.installada.get("carpeta")
        self.installada = {"versio": versio, "carpeta": versio, "executable": joc.get("executable", "Juego.exe"),
                           "anterior": anterior, "data": time.strftime("%Y-%m-%d %H:%M")}
        escriure_json(os.path.join(self.inst, "installada.json"), self.installada)
        os.remove(zip_ruta)
        # només es conserven la versió actual i l'anterior
        for nom in os.listdir(os.path.join(self.inst, "joc")):
            if nom not in (versio, anterior):
                shutil.rmtree(os.path.join(self.inst, "joc", nom), ignore_errors=True)
        self.acabat_ara = True

    def _progres(self, fets, total):
        self.progres = (fets, total)

    def _actualitzar_launcher(self, m):
        """Si hi ha un launcher més nou (i som l'.exe compilat), el baixa, es substitueix i es reobre."""
        info = m.get("launcher") or {}
        if not COMPILAT or int(info.get("versio", 0)) <= VERSIO_LAUNCHER or not info.get("url"):
            return False
        exe = os.path.abspath(sys.argv[0])
        self.estat = "launcher"
        nou, vell = exe + ".nou", exe + ".vell"
        baixar_fitxer(info["url"], nou, info.get("sha256"), self._progres)
        if os.path.exists(vell):
            os.remove(vell)
        os.replace(exe, vell)              # Windows deixa canviar el nom d'un .exe obert, però no esborrar-lo
        os.replace(nou, exe)
        subprocess.Popen([exe], cwd=os.path.dirname(exe), close_fds=True)
        self.estat = "reiniciar"
        return True


COMPILAT = "__compiled__" in globals() or bool(getattr(sys, "frozen", False))


def netejar_launcher_vell():
    if COMPILAT:
        vell = os.path.abspath(sys.argv[0]) + ".vell"
        try:
            if os.path.exists(vell):
                os.remove(vell)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Finestra
# ---------------------------------------------------------------------------
class Boto:
    def __init__(self, rect, clau, accio, color, font):
        self.rect, self.clau, self.accio, self.color, self.font = pygame.Rect(rect), clau, accio, color, font
        self.actiu = True

    def dibuixar(self, surf, txt, ratoli, t):
        sobre = self.actiu and self.rect.collidepoint(ratoli)
        color = self.color if self.actiu else (60, 62, 80)
        if sobre:
            color = tuple(min(255, c + 30) for c in color)
        r = self.rect.move(0, -2 if sobre else 0)
        pygame.draw.rect(surf, NEGRE, self.rect.move(0, 4), border_radius=8)
        pygame.draw.rect(surf, color, r, border_radius=8)
        pygame.draw.rect(surf, tuple(min(255, c + 70) for c in color), r, 2, border_radius=8)
        img = self.font.render(txt, False, BLANC if self.actiu else GRIS)
        surf.blit(self.font.render(txt, False, NEGRE), img.get_rect(center=(r.centerx + 2, r.centery + 2)))
        surf.blit(img, img.get_rect(center=r.center))


def ajustar(txt, font, ample):
    linies, actual = [], ""
    for paraula in txt.split():
        prova = (actual + " " + paraula).strip()
        if font.size(prova)[0] <= ample:
            actual = prova
        else:
            if actual:
                linies.append(actual)
            actual = paraula
    if actual:
        linies.append(actual)
    return linies


class Launcher:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Invasión Alienígena · Launcher")
        try:
            pygame.display.set_icon(pygame.image.load(recurs("favicon.png")))
        except (pygame.error, FileNotFoundError):
            pass
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        def font(nom, mida):
            try:
                return pygame.font.Font(recurs("fonts", nom), mida)
            except (OSError, FileNotFoundError):
                return pygame.font.Font(None, mida + 6)
        self.f_gran = font("PressStart2P-Regular.ttf", 22)
        self.f_ui = font("PressStart2P-Regular.ttf", 12)
        self.f_mini = font("PressStart2P-Regular.ttf", 9)
        self.f_text = font("VT323-Regular.ttf", 24)
        try:
            logo = pygame.image.load(recurs("logo.png")).convert()
            logo.set_colorkey(logo.get_at((0, 0)))          # el fons fosc del logotip es fa transparent
            self.logo = pygame.transform.scale(logo, (448, 279))
        except (pygame.error, FileNotFoundError):
            self.logo = None
        self.fons = self._crear_fons()
        self.estrelles = [(random.randrange(W), random.randrange(H), random.random() * math.tau) for _ in range(90)]
        self.idioma = idioma_inicial()
        self.act = Actualitzador()
        self.act.començar()
        self.t = 0
        self.scroll = self.scroll_max = 0
        self.sortir = False
        self.missatge_error = ""
        self.b_jugar = Boto((690, 412, 240, 70), "jugar", self.jugar, (40, 150, 80), self.f_gran)
        self.b_sortir = Boto((30, 488, 120, 34), "sortir", self.tancar, (60, 64, 96), self.f_mini)
        self.b_reintentar = Boto((690, 412, 240, 70), "reintentar", self.act.començar, (190, 120, 40), self.f_ui)
        self.b_idiomes = [Boto((W - 30 - (3 - k) * 52, 14, 46, 26), codi, lambda c=codi: self.posar_idioma(c),
                               (60, 64, 96), self.f_mini) for k, codi in enumerate(("es", "ca", "en"))]

    def _crear_fons(self):
        s = pygame.Surface((W, H))
        for y in range(H):
            k = y / H
            s.fill(tuple(int(a + (b - a) * k) for a, b in zip(FONS_DALT, FONS_BAIX)), (0, y, W, 1))
        return s

    def tr(self, clau, **kw):
        return TEXTOS[self.idioma].get(clau, clau).format(**kw)

    def posar_idioma(self, codi):
        self.idioma = codi

    def botons(self):
        estat = self.act.estat
        pot_jugar = self.act.executable() is not None and estat in ("llest", "sense_xarxa", "error")
        if estat in ("error", "sense_xarxa_res") and not pot_jugar:
            principal = [self.b_reintentar]
        else:
            self.b_jugar.actiu = pot_jugar
            principal = [self.b_jugar]
        return principal + [self.b_sortir] + self.b_idiomes

    def jugar(self):
        exe = self.act.executable()
        if not exe:
            return
        try:
            subprocess.Popen([exe], cwd=os.path.dirname(exe), close_fds=True)
            self.sortir = True
        except OSError as err:
            self.missatge_error = self.tr("no_obre", e=str(err)[:80])

    def tancar(self):
        self.sortir = True

    def pas(self):
        """Un fotograma (també el fan servir les proves). Torna False quan s'ha de tancar."""
        self.t += 1
        ratoli = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for b in self.botons():
                    if b.actiu and b.rect.collidepoint(ev.pos):
                        b.accio()
                        break
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE) and self.b_jugar.actiu:
                self.jugar()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return False
            if ev.type == pygame.MOUSEWHEEL:
                self.scroll = max(0, min(self.scroll_max, self.scroll - ev.y * 30))
        if self.act.estat == "reiniciar":
            return False
        self.dibuixar(ratoli)
        pygame.display.flip()
        return not self.sortir

    def dibuixar(self, ratoli):
        s = self.screen
        s.blit(self.fons, (0, 0))
        for x, y, f in self.estrelles:
            b = int(140 + 110 * math.sin(f + self.t * 0.05))
            s.fill((b, b, min(255, b + 30)), (x, y, 2, 2))
        if self.logo:
            s.blit(self.logo, (12, 34 + int(3 * math.sin(self.t * 0.05))))
        self.dibuixar_novetats(s)
        self.dibuixar_estat(s)
        for b in self.botons():
            clau = b.clau if b not in self.b_idiomes else b.clau.upper()
            if b in self.b_idiomes:
                b.color = (40, 150, 80) if b.clau == self.idioma else (60, 64, 96)
            b.dibuixar(s, self.tr(clau) if b not in self.b_idiomes else clau, ratoli, self.t)
        peu = f"{self.tr('installada', v=self.act.installada.get('versio') or self.tr('cap'))}  ·  launcher v{VERSIO_LAUNCHER}"
        img = self.f_mini.render(peu, False, GRIS)
        s.blit(img, (W - 30 - img.get_width(), H - 24))

    def dibuixar_novetats(self, s):
        r = pygame.Rect(480, 56, 450, 330)
        capa = pygame.Surface(r.size, pygame.SRCALPHA)
        capa.fill((8, 10, 24, 200))
        s.blit(capa, r)
        pygame.draw.rect(s, (90, 120, 190), r, 2, border_radius=4)
        m = self.act.manifest or {}
        versio = m.get("versio") or self.act.installada.get("versio") or ""
        titol = self.f_ui.render(f"{self.tr('novetats')}  {versio}", False, CIAN)
        s.blit(titol, (r.x + 16, r.y + 16))
        nov = m.get("novetats")
        if isinstance(nov, dict):
            nov = nov.get(self.idioma) or nov.get("es") or []
        if not nov:
            nov = [self.tr("sense_novetats")] if self.act.estat not in ("comprovant",) else []
        files = []                                   # (text, és la primera línia d'un punt)
        for linia in nov:
            for k, p in enumerate(ajustar(str(linia), self.f_text, r.w - 60)):
                files.append((p, k == 0))
            files.append(("", False))
        zona = pygame.Rect(r.x + 4, r.y + 42, r.w - 8, r.h - 50)
        alt_total = len(files) * 21
        self.scroll_max = max(0, alt_total - zona.h)
        self.scroll = max(0, min(self.scroll, self.scroll_max))
        clip = s.get_clip()
        s.set_clip(zona)
        y = zona.y - self.scroll
        for p, primera in files:
            if zona.y - 21 < y < zona.bottom:
                if primera:
                    pygame.draw.rect(s, GROC, (r.x + 18, y + 9, 6, 6))
                if p:
                    s.blit(self.f_text.render(p, False, BLANC), (r.x + 34, y))
            y += 21
        s.set_clip(clip)
        if self.scroll_max:                          # barra de desplaçament (roda del ratolí)
            h = max(20, int(zona.h * zona.h / alt_total))
            yb = zona.y + int((zona.h - h) * self.scroll / self.scroll_max)
            pygame.draw.rect(s, (60, 70, 110), (r.right - 10, zona.y, 4, zona.h))
            pygame.draw.rect(s, CIAN, (r.right - 10, yb, 4, h))

    def dibuixar_estat(self, s):
        a = self.act
        estat = a.estat
        x, y, ample = 30, 410, 620
        if estat == "comprovant":
            txt, color = self.tr("comprovant"), BLANC
        elif estat in ("baixant", "launcher"):
            txt = self.tr("baixant", v=a.versio_nova) if estat == "baixant" else self.tr("launcher_nou")
            color = BLANC
        elif estat == "instal":
            txt, color = self.tr("instal"), BLANC
        elif estat == "llest":
            txt = self.tr("nou", v=a.installada.get("versio")) if a.acabat_ara else self.tr("llest")
            color = VERD
        elif estat == "sense_xarxa":
            txt, color = self.tr("sense_xarxa"), GROC
        elif estat == "sense_xarxa_res":
            txt, color = self.tr("sense_xarxa_res"), VERMELL
        else:
            txt = self.tr("corrupte") if a.detall == "corrupte" else self.tr("error", e=a.detall)
            color = VERMELL
        if self.missatge_error:
            txt, color = self.missatge_error, VERMELL
        for k, linia in enumerate(ajustar(txt, self.f_ui, ample)[:2]):
            s.blit(self.f_ui.render(linia, False, NEGRE), (x + 2, y + 2 + k * 18))
            s.blit(self.f_ui.render(linia, False, color), (x, y + k * 18))
        barra = pygame.Rect(x, y + 40, ample, 18)
        pygame.draw.rect(s, NEGRE, barra.inflate(6, 6), border_radius=4)
        pygame.draw.rect(s, (36, 38, 60), barra, border_radius=3)
        fets, total = a.progres
        if estat in ("baixant", "launcher") and total:
            fr = fets / total
            info = self.tr("mb", a=f"{fets / 1048576:.1f}", t=f"{total / 1048576:.1f}")
            s.blit(self.f_mini.render(info, False, GRIS), (x, y + 66))
        elif estat in ("comprovant", "instal") or (estat in ("baixant", "launcher") and not total):
            fr = None
        else:
            fr = 1.0 if a.executable() else 0.0
        if fr is None:                                   # sense percentatge: franja que va i ve
            p = (self.t * 8) % (barra.w + 120) - 120
            franja = pygame.Rect(barra.x + max(0, p), barra.y, min(120, barra.right - barra.x - max(0, p)), barra.h)
            if franja.w > 0:
                pygame.draw.rect(s, CIAN, franja, border_radius=3)
        elif fr > 0:
            pygame.draw.rect(s, VERD if estat == "llest" else CIAN, (barra.x, barra.y, int(barra.w * fr), barra.h),
                             border_radius=3)
            pygame.draw.rect(s, BLANC, (barra.x + 2, barra.y + 2, max(0, int(barra.w * fr) - 4), 3))

    def executar(self):
        prova = int(os.environ.get("LAUNCHER_PROVA_FOTOGRAMES", "0") or 0)
        while self.pas():
            self.clock.tick(FPS)
            if prova and self.t >= prova:
                print(f"PROVA OK launcher v{VERSIO_LAUNCHER}: estat {self.act.estat}")
                break
        pygame.quit()


if __name__ == "__main__":
    netejar_launcher_vell()
    Launcher().executar()
