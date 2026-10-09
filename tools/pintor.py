"""Pintor de pixel art per peces, compartit pels generadors de sprites (enemics, caps...).

Cada figura es pinta per peces (polígons, el·lipses, membres fets de càpsules) a resolució 1:1 i després
s'ombreja i es perfila automàticament:
  * contorn de silueta i línies de separació on una peça tapa una altra (amb el to fosc de cada material);
  * volum: cada píxel mira quant li falta per arribar a la vora il·luminada (dalt a l'esquerra) i a la
    vora fosca (baix a la dreta) de la seva peça i en treu el to, amb un tramat suau entre tons;
  * ombra projectada: una peça de davant enfosqueix un parell de píxels de la de darrere;
  * marques relatives (arrugues, taques, juntes) que pugen o baixen el to que ja hi havia.
Cada material té cinc tons: contorn, ombra, base, llum i brillantor.
"""
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import numpy as np  # noqa: E402
import pygame  # noqa: E402

pygame.init()


def _camins(m):
    """Píxels seguits dins la màscara en cada direcció (comptant-hi el mateix píxel)."""
    mi = m.astype(np.int32)
    h, w = mi.shape
    up = mi.copy()
    dn = mi.copy()
    lf = mi.copy()
    rt = mi.copy()
    ul = mi.copy()
    dr = mi.copy()
    for y in range(1, h):
        up[y] = (up[y - 1] + 1) * mi[y]
        ul[y, 1:] = (ul[y - 1, :-1] + 1) * mi[y, 1:]
    for y in range(h - 2, -1, -1):
        dn[y] = (dn[y + 1] + 1) * mi[y]
        dr[y, :-1] = (dr[y + 1, 1:] + 1) * mi[y, :-1]
    for x in range(1, w):
        lf[:, x] = (lf[:, x - 1] + 1) * mi[:, x]
    for x in range(w - 2, -1, -1):
        rt[:, x] = (rt[:, x + 1] + 1) * mi[:, x]
    return up, dn, lf, rt, ul, dr


class Figura:
    def __init__(self, w, h, materials, brillants=(), escala=1.0):
        self.w, self.h = w, h
        self.mat = materials
        self.brillants = set(brillants)
        self.S = escala
        self.parts = []                        # dicts: mat, mode, mascara, grup, ombra
        self.marques = []                      # (x, y, delta de to)
        self.detalls = []                      # (x, y, color) després d'ombrejar
        self.forats = []                       # màscares que s'esborren al final
        self.ox = self.oy = 0                  # desplaçament de tot el que es pinta (per moure peces)

    def t(self, x, y):
        return (x + self.ox) * self.S, (y + self.oy) * self.S

    def moure(self, ox, oy):
        """Tot el que es pinti a partir d'ara queda desplaçat (ox, oy)."""
        self.ox, self.oy = ox, oy

    # --- peces -------------------------------------------------------------------------------
    def _mascara(self, dibuix):
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        dibuix(s)
        return pygame.surfarray.array_alpha(s).T > 0

    def peça(self, mat, dibuix, mode="volum", grup=None, ombra=True):
        """mode: volum, esfera, pla, fosc o brilla. Les peces del mateix grup no fan línia entre elles
        i s'ombregen com un sol volum. ombra=False: no projecta ombra sobre les de darrere."""
        assert mat in self.mat, mat
        m = self._mascara(dibuix)
        self.parts.append({"mat": mat, "mode": mode, "m": m, "grup": grup, "ombra": ombra})
        return len(self.parts) - 1

    def poli(self, mat, punts, mode="volum", **kw):
        pts = [tuple(round(v) for v in self.t(x, y)) for x, y in punts]
        return self.peça(mat, lambda s: pygame.draw.polygon(s, (255, 255, 255), pts), mode, **kw)

    def rect(self, mat, x0, y0, x1, y1, mode="volum", **kw):
        return self.poli(mat, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], mode, **kw)

    def el·lipse(self, mat, x0, y0, x1, y1, mode="volum", **kw):
        a, b = self.t(x0, y0), self.t(x1, y1)
        r = (round(a[0]), round(a[1]), max(1, round(b[0] - a[0]) + 1), max(1, round(b[1] - a[1]) + 1))
        return self.peça(mat, lambda s: pygame.draw.ellipse(s, (255, 255, 255), r), mode, **kw)

    def cercle(self, mat, cx, cy, r, mode="volum", **kw):
        return self.el·lipse(mat, cx - r, cy - r, cx + r, cy + r, mode, **kw)

    def membre(self, mat, punts, radis, mode="volum", **kw):
        """Braç, banya o tentacle: càpsules entre punts (cada punt amb el seu radi)."""
        pts = [self.t(x, y) for x, y in punts]
        if not isinstance(radis, (list, tuple)):
            radis = [radis] * len(punts)
        rs = [r * self.S for r in radis]

        def d(s):
            for (a, ra), (b, rb) in zip(zip(pts, rs), zip(pts[1:], rs[1:])):
                n = max(2, int(math.dist(a, b) * 3))
                for i in range(n + 1):
                    k = i / n
                    r = ra + (rb - ra) * k
                    c = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
                    if r < 0.9:
                        s.set_at((round(c[0]), round(c[1])), (255, 255, 255))
                    else:
                        pygame.draw.circle(s, (255, 255, 255), (round(c[0]), round(c[1])), max(1, round(r)))
        return self.peça(mat, d, mode, **kw)

    def forat(self, punts):
        """Esborra una zona (polígon) de tot el que hi hagi pintat."""
        pts = [tuple(round(v) for v in self.t(x, y)) for x, y in punts]
        self.forats.append(self._mascara(lambda s: pygame.draw.polygon(s, (255, 255, 255), pts)))

    # --- detalls --------------------------------------------------------------------------------
    def px(self, x, y, color):
        tx, ty = self.t(x, y)
        self.detalls.append((round(tx), round(ty), color))

    def _traç(self, a, b):
        a, b = self.t(*a), self.t(*b)
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) or 1
        return [(round(a[0] + (b[0] - a[0]) * i / n), round(a[1] + (b[1] - a[1]) * i / n)) for i in range(n + 1)]

    def linia(self, a, b, color):
        for x, y in self._traç(a, b):
            self.detalls.append((x, y, color))

    def corba(self, punts, color):
        for a, b in zip(punts, punts[1:]):
            self.linia(a, b, color)

    def marca(self, x, y, delta):
        tx, ty = self.t(x, y)
        self.marques.append((round(tx), round(ty), delta))

    def marca_linia(self, a, b, delta):
        for x, y in self._traç(a, b):
            self.marques.append((x, y, delta))

    def marca_corba(self, punts, delta):
        for a, b in zip(punts, punts[1:]):
            self.marca_linia(a, b, delta)

    def marca_poli(self, punts, delta):
        """Ombreja (o aclareix) tota una zona sense crear cap peça nova."""
        pts = [tuple(round(v) for v in self.t(x, y)) for x, y in punts]
        m = self._mascara(lambda s: pygame.draw.polygon(s, (255, 255, 255), pts))
        ys, xs = np.nonzero(m)
        self.marques += [(int(x), int(y), delta) for x, y in zip(xs, ys)]

    # --- ombrejat i contorn ---------------------------------------------------------------------
    def _tons(self, i, mascara, ids):
        """To (0-4, amb decimals) de cada píxel de la peça i segons el seu mode."""
        p = self.parts[i]
        mode = p["mode"]
        ys, xs = np.nonzero(ids == i)
        if len(xs) == 0:
            return ys, xs, np.zeros(0)
        if mode == "esfera":
            yy, xx = np.nonzero(mascara)
            x0, x1, y0, y1 = xx.min(), xx.max(), yy.min(), yy.max()
            rx, ry = max(1.0, (x1 - x0) / 2), max(1.0, (y1 - y0) / 2)
            nx = (xs - (x0 + x1) / 2) / rx
            ny = (ys - (y0 + y1) / 2) / ry
            d = np.hypot(nx + 0.36, ny + 0.42)
            to = np.select([d < 0.24, d < 0.62, d < 1.12], [4.0, 3.0, 2.0], 1.0)
            frontera = np.abs(d - 0.62) < 0.06
            to = np.where(frontera & ((xs + ys) % 2 == 0), 2.0, to)
            frontera = np.abs(d - 1.12) < 0.07
            to = np.where(frontera & ((xs + ys) % 2 == 0), 1.0, to)
            return ys, xs, to
        up, dn, lf, rt, ul, dr = p["camins"]
        u, dd, l, r, a, b = (c[ys, xs].astype(float) for c in (up, dn, lf, rt, ul, dr))
        if mode == "vidre":                          # ulls: l'ombra de la cella a dalt, la llum a baix
            yy = np.nonzero(mascara)[0]
            fy = (ys - yy.min()) / max(1, yy.max() - yy.min())
            return ys, xs, np.select([fy < 0.3, fy < 0.55], [1.0, 2.0], 3.0)
        if mode == "brilla":                         # llum pròpia: més clar com més endins
            d = np.minimum(np.minimum(u, dd), np.minimum(l, r))
            return ys, xs, np.select([d <= 1, d <= 2, d <= 4], [1.0, 2.0, 3.0], 4.0)
        if mode == "pla":
            to = np.full(len(xs), 2.0)
            to = np.where((u <= 1) | (l <= 1), 3.0, to)
            to = np.where((dd <= 1) | (r <= 1), 1.0, to)
            return ys, xs, to
        clar = 1.25 * u + 0.75 * l + 1.2 * a
        fosc = 1.25 * dd + 0.75 * r + 1.2 * b
        f = clar / (clar + fosc)
        gruix = (u + dd + l + r) / 2
        llindar_llum, llindar_ombra = 0.24, 0.6
        to = np.select([f < llindar_llum, f > llindar_ombra], [3.0, 1.0], 2.0)
        tram = gruix > 9                           # tramat entre tons (només a les peces grosses)
        par = (xs + ys) % 2 == 0
        to = np.where(tram & par & (np.abs(f - llindar_llum) < 0.035), 2.0, to)
        to = np.where(tram & par & (np.abs(f - llindar_ombra) < 0.04), 1.0, to)
        if p["mat"] in self.brillants:               # brillantor a tocar de la vora il·luminada
            to = np.where((f < 0.11) & (gruix > 5), 4.0, to)
        reflex = (gruix > 18) & (np.minimum(dd, r) == 2)   # llum rebotada a la vora fosca
        to = np.where(reflex & (to <= 1), 2.0, to)
        if mode == "fosc":
            to = np.maximum(1.0, to - 1)
        return ys, xs, to

    def superficie(self, fins_a_baix=False):
        """fins_a_baix: la fila de baix no fa contorn (peus que toquen a terra)."""
        w, h = self.w, self.h
        ids = np.full((h, w), -1, dtype=np.int32)
        for i, p in enumerate(self.parts):
            ids[p["m"]] = i
        for f in self.forats:
            ids[f] = -1
        grups = {}
        for i, p in enumerate(self.parts):
            if p["grup"] is not None:
                grups.setdefault(p["grup"], np.zeros((h, w), bool))
                grups[p["grup"]] |= p["m"]
        mascares = {}
        for i, p in enumerate(self.parts):
            m = grups[p["grup"]] if p["grup"] is not None else p["m"]
            if self.forats:
                m = m.copy()
                for f in self.forats:
                    m &= ~f
            clau = p["grup"] if p["grup"] is not None else ("peça", i)
            if clau not in mascares:
                mascares[clau] = (m, _camins(m))
            p["mascara"], p["camins"] = mascares[clau]
        to = np.full((h, w), -1.0)
        for i in range(len(self.parts)):
            ys, xs, t = self._tons(i, self.parts[i]["mascara"], ids)
            to[ys, xs] = t

        grup_de = np.array([hash(p["grup"]) if p["grup"] is not None else -1 - i for i, p in enumerate(self.parts)] + [0])
        ombra_de = np.array([p["ombra"] for p in self.parts] + [False])
        ple = ids >= 0
        pad = np.pad(ids, 2, constant_values=-1)

        def vei(dx, dy):
            return pad[2 + dy:2 + dy + h, 2 + dx:2 + dx + w]

        # silueta
        buit = np.zeros((h, w), bool)
        for dx, dy in ((1, 0), (-1, 0), (0, -1), (0, 1)):
            v = vei(dx, dy)
            if dy == 1 and fins_a_baix:
                v = v.copy()
                v[h - 1] = 0
            buit |= v < 0
        contorn = ple & buit
        # línies de separació: una peça de davant (índex més alt, d'un altre grup) toca aquest píxel
        g_ids = grup_de[ids]
        for dx, dy in ((1, 0), (-1, 0), (0, -1), (0, 1)):
            v = vei(dx, dy)
            contorn |= ple & (v > ids) & (grup_de[v] != g_ids)
        # ombra projectada (la llum ve de dalt a l'esquerra)
        ombra = np.zeros((h, w), bool)
        for dx, dy in ((-1, -1), (-2, -2), (-1, -2), (0, -2)):
            v = vei(dx, dy)
            ombra |= ple & (v > ids) & (grup_de[v] != g_ids) & ombra_de[v]
        to = np.where(ombra & ~contorn, np.maximum(1.0, to - 1), to)
        for x, y, d in self.marques:
            if 0 <= x < w and 0 <= y < h and ple[y, x] and not contorn[y, x]:
                to[y, x] = min(4.0, max(0.0 if d <= -2 else 1.0, to[y, x] + d))     # -2: línia de contorn
        to = np.where(contorn, 0, to)

        s = pygame.Surface((w, h), pygame.SRCALPHA)
        rgba = np.zeros((h, w, 4), np.uint8)
        for i, p in enumerate(self.parts):
            sel = ids == i
            if not sel.any():
                continue
            tons = np.array([(*c, 255) for c in self.mat[p["mat"]]], np.uint8)
            rgba[sel] = tons[to[sel].astype(int)]
        for x, y, c in self.detalls:
            if 0 <= x < w and 0 <= y < h and ple[y, x]:
                rgba[y, x] = (*c[:3], 255)
        px = pygame.surfarray.pixels3d(s)
        px[:] = rgba[:, :, :3].transpose(1, 0, 2)
        del px
        al = pygame.surfarray.pixels_alpha(s)
        al[:] = rgba[:, :, 3].T
        del al
        return s


# --- geometria ---------------------------------------------------------------------------------
def girar(punts, angle, origen):
    c, s = math.cos(angle), math.sin(angle)
    return [(origen[0] + x * c - y * s, origen[1] + x * s + y * c) for x, y in punts]


def mirall(punts, cx):
    return [(2 * cx - x, y) for x, y in punts]


def bezier(p0, p1, p2, p3, n=12):
    pts = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


def comprovar_paleta(materials):
    vist = {}
    for mat, tons in materials.items():
        for c in tons:
            assert c not in vist or vist[c] == mat, f"color repetit {c}: {mat} i {vist[c]}"
            vist[c] = mat


def retallar(s):
    """Retalla els marges transparents; torna (superfície, desplaçament)."""
    r = s.get_bounding_rect()
    if r.w == 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA), (0, 0)
    return s.subsurface(r).copy(), (r.x, r.y)


def empaquetar(imatges, ample=1024, marge=1):
    """Atles d'imatges per files. imatges: {nom: superfície}. Torna (atles, {nom: [x, y, w, h]})."""
    noms = sorted(imatges, key=lambda n: -imatges[n].get_height())
    x = y = alt_fila = 0
    rects = {}
    for n in noms:
        im = imatges[n]
        w, h = im.get_size()
        if x + w > ample:
            x, y = 0, y + alt_fila + marge
            alt_fila = 0
        rects[n] = [x, y, w, h]
        x += w + marge
        alt_fila = max(alt_fila, h)
    atles = pygame.Surface((ample, y + alt_fila), pygame.SRCALPHA)
    for n, (x, y, w, h) in rects.items():
        atles.blit(imatges[n], (x, y))
    return atles, rects
