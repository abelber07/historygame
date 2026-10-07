#!/usr/bin/env python3
"""
Generador de la música original de "Invasión Alienígena" (estilo chiptune / retro-synth).

Sintetiza desde cero, sólo con numpy, seis pistas y las guarda como Ogg Vorbis en assets/musica/:

    sector1.ogg        "Ruinas urbanas"          marcha militar tensa, La menor, 120 BPM
    sector4.ogg        "Órbita"                  arpegios flotantes con eco, Re dórico, 126 BPM
    sector5.ogg        "Xylos, el mundo colmena" frigio + tonos enteros, bajo pulsante, 112 BPM
    jefe.ogg           combate contra jefe       rápido e intenso, Do menor, 150 BPM
    supervivencia.ogg  modo supervivencia        acción enérgica, Mi menor, 140 BPM
    final.ogg          final / créditos          esperanzador y heroico, Re mayor, 98 BPM

No se ejecuta durante el juego; sólo hace falta volver a lanzarlo para regenerar la música:

    python3 tools/generar_musica.py            # las seis pistas
    python3 tools/generar_musica.py jefe final # sólo algunas

Cómo funciona:
  * Cada pista se escribe como una partitura: acordes por compás, melodía en notación compacta
    ("A4.3" = La4 durante 3 semicorcheas, "r.4" = silencio de negra, "-.4" = ligadura, "|" separa
    compases y se comprueba que cada compás sume 16 semicorcheas), patrones de bajo por grados
    (R, 3, 5, 7, 8, b = quinta inferior, a = nota de aproximación al acorde siguiente), arpegios por
    índice de nota del acorde y contramelodías (conducción de voces o armonía a la tercera/sexta).
  * Voces clásicas de chip: ondas de pulso de 12,5/25/50 % limitadas en banda (PolyBLEP + paso bajo),
    bajo de onda triangular, percusión de ruido moldeado y barridos senoidales, envolventes ADSR,
    vibrato suave en notas largas, paneo estéreo ligero (compatible con mono), eco ping-pong y una
    reverberación corta.
  * Bucle perfecto con pygame.mixer.music.play(-1): la duración es un número exacto de compases
    (BPM elegidos para que una negra sea un número entero de muestras) y todo lo que suena más allá
    del final (colas de notas, platillos, eco, reverberación) se suma al principio. Los filtros, el eco
    y la reverberación se aplican de forma circular (FFT), igual que sonaría el bucle infinito.
  * Volumen: se mide la sonoridad integrada (ITU-R BS.1770, ponderación K y doble puerta) y el pico
    real (sobremuestreo x4) en numpy, se normaliza a -18 LUFS y un limitador con anticipación deja el
    pico real por debajo del techo. Tras codificar se vuelve a medir con ffmpeg (ebur128) y, si el
    pico real del Ogg supera -3 dBTP, se rehace con un techo más bajo.
  * Determinista: semillas fijas y codificación bitexact.
"""
import bisect
import os
import re
import shutil
import subprocess
import sys
import time

import numpy as np

SR = 44100
ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTI = os.path.join(ARREL, "assets", "musica")
FFMPEG = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
OBJ_LUFS = -18.0
TECHO_DBTP = -4.0        # techo del limitador interno (margen para el Ogg)
MAX_DBTP_OGG = -3.0      # lo que se exige al fichero final
COLA_S = 4.0             # segundos que se renderizan después del final y se pliegan al principio

# ---------------------------------------------------------------------------
# Notación
# ---------------------------------------------------------------------------
_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_RE_NOTA = re.compile(r"^([A-G])([#b]?)(-?\d)$")


def nota(txt):
    """'A4' -> 69, 'C#5' -> 73, 'Bb3' -> 58."""
    m = _RE_NOTA.match(txt)
    if not m:
        raise ValueError(f"nota no válida: {txt!r}")
    alt = {"#": 1, "b": -1, "": 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + _SEMI[m.group(1)] + alt


CUALIDADES = {
    "": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "m7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11),
    "sus4": (0, 5, 7), "sus2": (0, 2, 7), "dim": (0, 3, 6), "dim7": (0, 3, 6, 9), "aug": (0, 4, 8),
    "m9": (0, 3, 7, 10, 14), "add9": (0, 4, 7, 14), "5": (0, 7),
}


class Acorde:
    def __init__(self, nombre):
        m = re.match(r"^([A-G][#b]?)(.*)$", nombre)
        self.nombre = nombre
        self.raiz = nota(m.group(1) + "0") % 12
        self.ints = CUALIDADES[m.group(2)]
        self.pcs = [(self.raiz + i) % 12 for i in self.ints]

    def quinta(self):
        return next((i for i in self.ints if i in (6, 7, 8)), 7)

    def tercera(self):
        return next((i for i in self.ints if i in (2, 3, 4, 5)), 4)

    def septima(self):
        return next((i for i in self.ints if i in (9, 10, 11)), 12)


def fichas(texto):
    """Convierte 'A4.3 A4.1 | -.4 r.12' en [(inicio16, dur16, símbolo)], comprobando cada compás."""
    out, pos = [], 0
    for ci, comp in enumerate(texto.split("|")):
        suma = 0
        for tok in comp.split():
            sim, d = tok.rsplit(".", 1)
            d = int(d)
            if sim == "-":
                ini, dur, s = out[-1]
                out[-1] = (ini, dur + d, s)
            elif sim != "r":
                out.append((pos, d, sim))
            pos += d
            suma += d
        if suma != 16:
            raise ValueError(f"el compás {ci + 1} suma {suma} semicorcheas: {comp.strip()!r}")
    return out, pos


# ---------------------------------------------------------------------------
# Osciladores y filtros
# ---------------------------------------------------------------------------
def polyblep(t, dt):
    out = np.zeros_like(t)
    m = t < dt
    x = t[m] / dt[m]
    out[m] = x + x - x * x - 1.0
    m = t > 1.0 - dt
    x = (t[m] - 1.0) / dt[m]
    out[m] = x * x + x + x + 1.0
    return out


def pulso(fase, dt, duty):
    """Onda de pulso limitada en banda (PolyBLEP), sin continua y con RMS ~1 para cualquier duty."""
    t = fase % 1.0
    y = np.where(t < duty, 1.0, -1.0)
    y += polyblep(t, dt)
    y -= polyblep((t - duty) % 1.0, dt)
    return (y - (2.0 * duty - 1.0)) / (2.0 * np.sqrt(duty * (1.0 - duty)))


def triangulo(fase):
    t = (fase + 0.25) % 1.0
    return 4.0 * np.abs(t - 0.5) - 1.0


def respuesta(f, lp=None, hp=None, orden=1):
    """Respuesta en frecuencia de un paso bajo / paso alto de 1 polo (en cascada según orden)."""
    h = np.ones_like(f, dtype=complex)
    for _ in range(orden):
        if lp:
            h /= 1.0 + 1j * f / lp
        if hp:
            jw = 1j * f / hp
            h *= jw / (1.0 + jw)
    return h


def filtrar(x, lp=None, hp=None, orden=1):
    """Filtra de forma circular vía FFT."""
    n = x.shape[-1]
    h = respuesta(np.fft.rfftfreq(n, 1.0 / SR), lp, hp, orden)
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * h, n=n, axis=-1)


def filtrar_corto(x, **kw):
    """Igual que filtrar() pero no circular (para muestras de percusión)."""
    n = len(x)
    return filtrar(np.concatenate([x, np.zeros(n)]), **kw)[:n]


def panear(p):
    a = (p + 1.0) * np.pi / 4.0
    return np.cos(a) * np.sqrt(2.0), np.sin(a) * np.sqrt(2.0)


def plegar(buf, n):
    out = buf[:n].copy()
    cola = buf[n:]
    out[:len(cola)] += cola
    return out


# ---------------------------------------------------------------------------
# Instrumentos
# ---------------------------------------------------------------------------
INSTRUMENTOS = {
    # melodía principal, pulso 25 %
    "lead": dict(onda="pulso", duty=0.25, a=0.004, d=0.18, s=0.72, r=0.07, vib=(5.5, 16, 0.22),
                 lp=5200, hp=120, gain=0.21, pan=0.0, eco=0.20, rev=0.10, gate=0.92),
    # melodía de contraste, pulso 50 % (más redondo)
    "lead2": dict(onda="pulso", duty=0.5, a=0.006, d=0.25, s=0.75, r=0.09, vib=(5.0, 18, 0.22),
                  lp=3800, hp=120, gain=0.19, pan=0.0, eco=0.24, rev=0.12, gate=0.94),
    # contramelodía / segunda voz
    "contra": dict(onda="pulso", duty=0.5, a=0.005, d=0.2, s=0.6, r=0.08, vib=(5.0, 10, 0.3),
                   lp=3000, hp=160, gain=0.11, pan=-0.35, eco=0.12, rev=0.10, gate=0.9),
    # arpegios, pulso 12,5 % muy corto
    "arp": dict(onda="pulso", duty=0.125, a=0.002, d=0.07, s=0.35, r=0.03, vib=None,
                lp=4300, hp=250, gain=0.075, pan=0.35, eco=0.30, rev=0.08, gate=0.7),
    "arp2": dict(onda="pulso", duty=0.25, a=0.002, d=0.09, s=0.3, r=0.04, vib=None,
                 lp=4000, hp=250, gain=0.06, pan=-0.4, eco=0.30, rev=0.08, gate=0.7),
    # campana / notas sueltas con mucho eco
    "campana": dict(onda="pulso", duty=0.125, a=0.002, d=0.45, s=0.0, r=0.35, vib=(4.5, 8, 0.3),
                    lp=5500, hp=300, gain=0.10, pan=0.2, eco=0.45, rev=0.30, gate=1.0),
    # bajo: triángulo con un poco de pulso para que se oiga en altavoces pequeños
    "bajo": dict(onda="tri", mezcla=0.22, a=0.003, d=0.25, s=0.8, r=0.03, vib=None,
                 lp=1500, hp=30, gain=0.45, pan=0.0, eco=0.0, rev=0.02, gate=0.88),
    # colchón: dos pulsos con PWM lenta, desafinados y abiertos en estéreo
    "pad": dict(onda="pad", a=0.30, d=0.6, s=0.8, r=0.5, vib=None,
                lp=1700, hp=150, gain=0.05, pan=0.45, eco=0.05, rev=0.25, gate=1.0),
}

# ganancia, paneo, envío a eco, envío a reverberación
MEZCLA_BATERIA = {
    "k": (0.50, 0.0, 0.0, 0.02), "s": (0.42, 0.05, 0.04, 0.16), "h": (0.11, 0.30, 0.0, 0.03),
    "o": (0.09, 0.30, 0.02, 0.06), "c": (0.10, -0.30, 0.0, 0.10),
    "t1": (0.30, -0.35, 0.0, 0.10), "t2": (0.30, 0.0, 0.0, 0.10), "t3": (0.32, 0.35, 0.0, 0.10),
}
VEL = {"X": 1.0, "x": 0.72, "o": 0.38, "r": 0.5}


def sintetizar(ins, midi, dur, vel, desde=None, detune=0.0, fase_pwm=0.0):
    a, d, s, r = max(ins["a"], 0.002), max(ins["d"], 1e-3), ins["s"], max(ins["r"], 0.004)
    hold = max(dur, a)
    n = int(np.ceil((hold + r) * SR)) + 1
    t = np.arange(n) / SR
    m = np.full(n, float(midi) + detune / 100.0)
    if ins.get("vib"):
        rate, cents, delay = ins["vib"]
        m += cents / 100.0 * np.clip((t - delay) / 0.25, 0, 1) * np.sin(2 * np.pi * rate * t)
    if desde is not None:
        m += (desde - midi) * np.exp(-t / ins["glide"])
    dt = 440.0 * 2.0 ** ((m - 69.0) / 12.0) / SR
    fase = np.cumsum(dt) - dt[0]
    onda = ins["onda"]
    if onda == "pulso":
        y = pulso(fase, dt, ins["duty"])
    elif onda == "tri":
        y = triangulo(fase)
        if ins.get("mezcla"):
            y = y + ins["mezcla"] * pulso(fase, dt, 0.5)
    else:  # pad
        duty = 0.5 - 0.17 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.3 * t + fase_pwm))
        y = pulso(fase, dt, duty)
    env = np.where(t < a, t / a, s + (1.0 - s) * np.exp(-(t - a) / d))
    nh = min(int(hold * SR), n - 1)
    env[nh:] = env[nh] * np.clip(1.0 - (t[nh:] - t[nh]) / r, 0.0, 1.0)
    env[-1] = 0.0
    return y * env * vel


def muestras_bateria(rng):
    def tt(dur):
        return np.arange(int(dur * SR)) / SR

    def norm(x):
        x = x / np.max(np.abs(x))
        n = len(x)
        x[:44] *= np.linspace(0, 1, 44)          # 1 ms de entrada
        x[n - 132:] *= np.linspace(1, 0, 132)    # 3 ms de salida
        return x

    def metal(t, freqs, hp):
        acc = np.zeros_like(t)
        for f in freqs:
            dt = np.full_like(t, f / SR)
            acc += pulso(np.cumsum(dt), dt, 0.5)
        return filtrar_corto(acc, hp=hp, orden=2)

    m = {}
    t = tt(0.45)
    f = 44 + 115 * np.exp(-t / 0.032) + 60 * np.exp(-t / 0.004)
    k = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.20)
    k += 0.35 * filtrar_corto(rng.standard_normal(len(t)), lp=3500) * np.exp(-t / 0.003)
    m["k"] = norm(np.tanh(1.8 * k))

    t = tt(0.32)
    cuerpo = np.sin(2 * np.pi * np.cumsum(180 + 70 * np.exp(-t / 0.015)) / SR) * np.exp(-t / 0.06)
    ruido = filtrar_corto(rng.standard_normal(len(t)), hp=1400, lp=8500)
    ruido = ruido / np.max(np.abs(ruido)) * np.exp(-t / 0.095)
    m["s"] = norm(0.6 * cuerpo + 0.9 * ruido)

    frec_metal = [317, 409, 543, 612, 789, 1067]
    t = tt(0.09)
    h = 0.7 * filtrar_corto(rng.standard_normal(len(t)), hp=7000, orden=2) + 0.5 * metal(t, frec_metal, 6500)
    m["h"] = norm(filtrar_corto(h, lp=14000) * np.exp(-t / 0.022))
    t = tt(0.45)
    o = 0.7 * filtrar_corto(rng.standard_normal(len(t)), hp=6500, orden=2) + 0.5 * metal(t, frec_metal, 6000)
    m["o"] = norm(filtrar_corto(o, lp=13000) * np.exp(-t / 0.14))
    t = tt(2.4)
    c = filtrar_corto(rng.standard_normal(len(t)), hp=3000, orden=2) + 0.6 * metal(t, [f * 1.37 for f in frec_metal], 3500)
    m["c"] = norm(filtrar_corto(c, lp=12000) * np.exp(-t / 0.75))

    for i, f0 in enumerate((185, 140, 104), 1):
        t = tt(0.5)
        fr = f0 * (1 + 0.55 * np.exp(-t / 0.04))
        tom = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.17)
        tom += 0.15 * filtrar_corto(rng.standard_normal(len(t)), lp=3000) * np.exp(-t / 0.03)
        m[f"t{i}"] = norm(tom)
    return m


# ---------------------------------------------------------------------------
# Pista: partitura + render
# ---------------------------------------------------------------------------
class Pista:
    def __init__(self, nombre, titulo, bpm, compases, semilla, eco_tiempos=0.5, eco_fb=0.32,
                 rev_rt60=1.3, instrumentos=None, bateria=None):
        self.nombre, self.titulo, self.bpm, self.compases, self.semilla = nombre, titulo, bpm, compases, semilla
        spb = 60.0 * SR / bpm
        assert abs(spb - round(spb)) < 1e-9, "el BPM debe dar un número entero de muestras por negra"
        self.spb = int(round(spb))
        self.L = compases * 4 * self.spb
        self.eco_tiempos, self.eco_fb, self.rev_rt60 = eco_tiempos, eco_fb, rev_rt60
        self.ins = {k: dict(v) for k, v in INSTRUMENTOS.items()}
        for k, v in (instrumentos or {}).items():
            self.ins.setdefault(k, {}).update(v)
        self.mezcla_bat = dict(MEZCLA_BATERIA)
        for k, v in (bateria or {}).items():
            self.mezcla_bat[k] = v
        self.notas = {}
        self.golpes = []
        self._ac_beats, self._ac = [], []

    # --- armonía -----------------------------------------------------------
    def acordes(self, c0, lista):
        for i, s in enumerate(lista):
            partes = s.split()
            for j, ch in enumerate(partes):
                b = (c0 + i) * 4 + j * 4.0 / len(partes)
                k = bisect.bisect_left(self._ac_beats, b)
                self._ac_beats.insert(k, b)
                self._ac.insert(k, Acorde(ch))

    def acorde_en(self, b):
        k = bisect.bisect_right(self._ac_beats, b + 1e-6) - 1
        return self._ac[max(k, 0)]

    def acorde_siguiente(self, b):
        k = bisect.bisect_right(self._ac_beats, b + 1e-6)
        return self._ac[k % len(self._ac)]

    # --- notas -------------------------------------------------------------
    def add(self, voz, b, dur, midi, vel=1.0):
        self.notas.setdefault(voz, []).append((b, dur, midi, vel))

    def melodia(self, voz, c0, texto, transp=0, vel=1.0):
        evs, tot = fichas(texto)
        out = []
        for ini, d, s in evs:
            b = c0 * 4 + ini / 4.0
            m = nota(s) + transp
            acento = 1.0 if ini % 4 == 0 else 0.9
            self.add(voz, b, d / 4.0, m, vel * acento)
            out.append((b, d / 4.0, m))
        return out

    def bajo(self, c0, n, patron, lo=33, vel=1.0, voz="bajo"):
        compases = patron.split("|")
        prev = None
        for i in range(n):
            c = c0 + i
            evs, _ = fichas(compases[i % len(compases)])
            for ini, d, s in evs:
                b = c * 4 + ini / 4.0
                ac = self.acorde_en(b)
                raiz = self._raiz_cerca(ac.raiz, prev, lo)
                prev = raiz
                if s == "R":
                    m = raiz
                elif s == "3":
                    m = raiz + ac.tercera()
                elif s == "5":
                    m = raiz + ac.quinta()
                elif s == "7":
                    m = raiz + ac.septima()
                elif s == "8":
                    m = raiz + 12
                elif s == "b":
                    m = raiz + ac.quinta() - 12
                elif s == "a":
                    sig = self.acorde_siguiente(b)
                    obj = self._raiz_cerca(sig.raiz, raiz, lo)
                    m = raiz + ac.quinta() if obj == raiz else (obj - 1 if obj > raiz else obj + 1)
                else:
                    raise ValueError(s)
                acento = 1.0 if ini % 8 == 0 else 0.88
                self.add(voz, b, d / 4.0, m, vel * acento)

    @staticmethod
    def _raiz_cerca(pc, prev, lo):
        cands = [m for m in range(lo - 3, lo + 11) if m % 12 == pc]
        if prev is None:
            return next(m for m in cands if m >= lo)
        return min(cands, key=lambda m: (abs(m - prev), m))

    def arpegio(self, voz, c0, n, patron, lo=60, vel=1.0, paso=1):
        toks = patron.split()
        for i in range(n):
            for k, tk in enumerate(toks):
                if tk == ".":
                    continue
                b = (c0 + i) * 4 + k * paso / 4.0
                ac = self.acorde_en(b)
                tonos = sorted(next(m for m in range(lo, lo + 12) if m % 12 == pc) for pc in ac.pcs[:4])
                idx = int(tk)
                m = tonos[idx % len(tonos)] + 12 * (idx // len(tonos))
                self.add(voz, b, paso / 4.0, m, vel * (1.0 if k % 4 == 0 else 0.85))

    def contra_guia(self, voz, c0, n, ritmo, lo, hi, mel=(), vel=0.85):
        """Línea de notas del acorde con conducción de voces suave, por debajo de la melodía."""
        prev = (lo + hi) // 2
        for i in range(n):
            for ini, d in ritmo:
                b = (c0 + i) * 4 + ini / 4.0
                ac = self.acorde_en(b)
                mm = next((m for (mb, md, m) in mel if mb <= b + 1e-6 < mb + md), None)

                def coste(m):
                    c = abs(m - prev)
                    if m % 12 == ac.raiz:
                        c += 1.5
                    if mm is not None:
                        iv = (mm - m) % 12
                        if iv in (1, 2, 10, 11):
                            c += 6
                        if iv == 0:
                            c += 3
                        if m >= mm:
                            c += 8
                    return c

                cands = [m for m in range(lo, hi + 1) if m % 12 in ac.pcs]
                m = min(cands, key=coste)
                self.add(voz, b, d / 4.0, m, vel)
                prev = m

    def contra_tercera(self, voz, mel, vel=0.8):
        """Armonía paralela: la nota del acorde 3-9 semitonos por debajo, prefiriendo 3as y 6as."""
        pref = {3: 0, 4: 0, 8: 1, 9: 1, 5: 2, 7: 3, 6: 4}
        for b, d, m in mel:
            ac = self.acorde_en(b)
            cands = [x for x in range(m - 9, m - 2) if x % 12 in ac.pcs]
            if cands:
                x = min(cands, key=lambda x: (pref[m - x], -x))
                self.add(voz, b, d, x, vel)

    def pad(self, c0, n, lo=53, hi=69, vel=1.0):
        prev = None
        b, fin = c0 * 4.0, (c0 + n) * 4.0
        while b < fin - 1e-6:
            ac = self.acorde_en(b)
            k = bisect.bisect_right(self._ac_beats, b + 1e-6)
            b2 = min(self._ac_beats[k] if k < len(self._ac_beats) else fin, fin)
            centro = (lo + hi) / 2 if prev is None else np.mean(prev)
            voz = []
            for pc in ac.pcs[:4]:
                cands = [m for m in range(lo, hi + 1) if m % 12 == pc]
                voz.append(min(cands, key=lambda m: abs(m - centro)))
            for m in voz:
                self.add("pad", b, b2 - b, m, vel)
            prev = voz
            b = b2

    # --- batería -----------------------------------------------------------
    def bateria(self, c0, n, patron, relleno=None, platillo=True, vol=1.0):
        for i in range(n):
            c = c0 + i
            comp = dict(patron)
            if relleno and i == n - 1:
                comp.update(relleno)
            for clave, s in comp.items():
                s = s.replace(" ", "")
                nb = len(s) // 16
                s = s[(i % nb) * 16:(i % nb + 1) * 16]
                for k, ch in enumerate(s):
                    if ch == ".":
                        continue
                    b = c * 4 + k / 4.0
                    if clave == "t":
                        self.golpes.append((b, "t" + ch, 0.85 * vol))
                    elif ch == "r":
                        self.golpes.append((b, clave, 0.45 * vol))
                        self.golpes.append((b + 0.125, clave, 0.55 * vol))
                    else:
                        self.golpes.append((b, clave, VEL[ch] * vol))
            if platillo and i == 0:
                self.golpes.append((c * 4.0, "c", vol))

    def redoble(self, b0, beats, v0, v1, sub=8):
        n = int(beats * sub)
        for i in range(n):
            self.golpes.append((b0 + i / sub, "s", v0 + (v1 - v0) * i / max(n - 1, 1)))

    def golpe(self, b, clave, v=1.0):
        self.golpes.append((b, clave, v))

    # --- render ------------------------------------------------------------
    def render(self):
        """Devuelve la mezcla estéreo (2, L) del bucle. Todo el proceso posterior al plegado es
        circular: las voces se filtran y se mezclan en el dominio de la frecuencia."""
        L, spb = self.L, self.spb
        N = L + int(COLA_S * SR)
        f = np.fft.rfftfreq(L, 1.0 / SR)
        rng = np.random.default_rng(self.semilla)
        espectro = np.zeros((4, len(f)), dtype=complex)   # izquierda, derecha, envío eco, envío rev
        temporal = np.zeros((4, L))                          # lo mismo para la batería (sin filtrar)
        self.rms_voces = {}

        def rms(x):
            return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)

        for voz, notas in sorted(self.notas.items()):
            ins = self.ins[voz]
            if ins["onda"] == "pad":   # dos osciladores desafinados, uno a cada lado
                copias = [(-7.0, -ins["pan"], 0.0), (7.0, ins["pan"], 2.1)]
            else:
                copias = [(0.0, ins["pan"], 0.0)]
            h = respuesta(f, lp=ins["lp"], hp=ins.get("hp"))
            for detune, pan, fpwm in copias:
                buf = np.zeros(N)
                prev_m, prev_fin = None, -1.0
                for b, d, m, v in sorted(notas):
                    s0 = int(round(b * spb))
                    desde = None
                    if ins.get("glide") and prev_m is not None and abs(b - prev_fin) < 0.05:
                        desde = prev_m
                    dur = d * spb / SR
                    # articulación: las notas cortas se acortan según gate; las largas quedan casi ligadas
                    dur = max(dur * ins["gate"], dur - 0.06)
                    y = sintetizar(ins, m, dur, v, desde, detune, fpwm)
                    buf[s0:s0 + len(y)] += y[:N - s0]
                    prev_m, prev_fin = m, b + d
                g = ins["gain"] / np.sqrt(len(copias))
                buf = plegar(buf, L) * g
                self.rms_voces[voz + (f"{detune:+.0f}" if detune else "")] = rms(buf)
                X = np.fft.rfft(buf) * h
                gl, gr = panear(pan)
                espectro += np.outer([gl, gr, ins["eco"], ins["rev"]], X)

        muestras = muestras_bateria(np.random.default_rng(self.semilla + 1000))
        bufs = {}
        for b, clave, v in self.golpes:
            if clave not in bufs:
                bufs[clave] = np.zeros(N)
            buf = bufs[clave]
            if clave == "h":
                v *= 1.0 + rng.uniform(-0.08, 0.08)
            s0 = int(round(b * spb))
            x = muestras[clave]
            buf[s0:s0 + len(x)] += x[:N - s0] * v
        for clave, buf in sorted(bufs.items()):
            gain, pan, eco, rev = self.mezcla_bat[clave]
            buf = plegar(buf, L) * gain
            self.rms_voces["bat_" + clave] = rms(buf)
            gl, gr = panear(pan)
            temporal += np.outer([gl, gr, eco, rev], buf)
        espectro += np.fft.rfft(temporal, axis=1)

        # eco ping-pong (respuesta impulsional circular)
        d = int(round(self.eco_tiempos * spb))
        ir = np.zeros((2, L))
        for k in range(1, 12):
            g = self.eco_fb ** (k - 1)
            lado = (k + 1) % 2
            ir[lado, k * d % L] += g
            ir[1 - lado, k * d % L] += 0.25 * g
        eco = espectro[2] * np.fft.rfft(ir, axis=1) * respuesta(f, lp=3800, hp=220)

        # reverberación: ruido con caída exponencial, distinto en cada canal
        n_ir = int(2.0 * SR)
        t = np.arange(n_ir) / SR
        r_rng = np.random.default_rng(self.semilla + 2000)
        ir = np.zeros((2, L))
        for ch in range(2):
            x = r_rng.standard_normal(n_ir) * np.exp(-6.9 * t / self.rev_rt60)
            x[: int(0.012 * SR)] = 0.0
            ir[ch, :n_ir] = x / np.sqrt(np.sum(x ** 2))
        rev = espectro[3] * np.fft.rfft(ir, axis=1) * respuesta(f, lp=5000, hp=300)

        total = (espectro[:2] + eco + rev) * respuesta(f, hp=25)
        return np.fft.irfft(total, n=L, axis=1)


# ---------------------------------------------------------------------------
# Sonoridad (BS.1770) y limitador
# ---------------------------------------------------------------------------
def _biquad(b, a, z):
    return (b[0] + b[1] / z + b[2] / z ** 2) / (a[0] + a[1] / z + a[2] / z ** 2)


def lufs(x):
    n = x.shape[1]
    f = np.fft.rfftfreq(n, 1.0 / SR)
    z = np.exp(1j * 2 * np.pi * f / SR)
    G, Q, fc = 3.999843853973347, 0.7071752369554196, 1681.974450955533
    K = np.tan(np.pi * fc / SR)
    vh, vb = 10 ** (G / 20), (10 ** (G / 20)) ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    h1 = _biquad([(vh + vb * K / Q + K * K) / a0, 2 * (K * K - vh) / a0, (vh - vb * K / Q + K * K) / a0],
                 [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0], z)
    Q, fc = 0.5003270373238773, 38.13547087602444
    K = np.tan(np.pi * fc / SR)
    a0 = 1 + K / Q + K * K
    h2 = _biquad([1, -2, 1], [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0], z)
    y = np.fft.irfft(np.fft.rfft(x, axis=1) * h1 * h2, n=n, axis=1)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    cs = np.concatenate([np.zeros((2, 1)), np.cumsum(y ** 2, axis=1)], axis=1)
    ini = np.arange(0, n - blk + 1, hop)
    ms = ((cs[:, ini + blk] - cs[:, ini]) / blk).sum(0)
    lb = -0.691 + 10 * np.log10(ms + 1e-20)
    g1 = lb > -70
    rel = -0.691 + 10 * np.log10(np.mean(ms[g1])) - 10
    return -0.691 + 10 * np.log10(np.mean(ms[g1 & (lb > rel)]))


def picos_os(x, os_=4):
    """Pico absoluto por muestra tras sobremuestreo x4 (máximo de los dos canales)."""
    n = x.shape[1]
    p = np.zeros(n)
    for ch in range(x.shape[0]):
        y = np.fft.irfft(np.fft.rfft(x[ch].astype(np.float32)), n=n * os_) * os_
        p = np.maximum(p, np.abs(y).reshape(n, os_).max(axis=1))
    return p


def _min_deslizante(x, w):
    h = w // 2
    xe = np.concatenate([x[-h:], x, x[:h]])
    pad = (-len(xe)) % w
    xp = np.concatenate([xe, np.full(pad, np.inf)]).reshape(-1, w)
    pre = np.minimum.accumulate(xp, axis=1).ravel()
    suf = np.minimum.accumulate(xp[:, ::-1], axis=1)[:, ::-1].ravel()
    i = np.arange(len(x))
    return np.minimum(suf[i], pre[i + w - 1])


def _media_deslizante(x, w):
    h = w // 2
    xe = np.concatenate([x[-h:], x, x[:h]])
    cs = np.concatenate([[0.0], np.cumsum(xe)])
    return (cs[w:] - cs[:-w])[: len(x)] / w


def limitar(x, techo_db, picos=None):
    c = 10 ** (techo_db / 20)
    g = np.minimum(1.0, c / np.maximum(picos_os(x) if picos is None else picos, 1e-9))
    if g.min() >= 1.0:
        return x, 0.0
    w = int(0.004 * SR) | 1
    g = _media_deslizante(_min_deslizante(g, w), w)
    return x * g, 20 * np.log10(g.min())


def masterizar(x, techo_db):
    """Normaliza a OBJ_LUFS y limita el pico real (x4) a techo_db. Devuelve (x, reducción máx.)."""
    x = x * 10 ** ((OBJ_LUFS - lufs(x)) / 20)
    picos = picos_os(x)
    gr_max = 0.0
    for _ in range(5):
        if picos.max() <= 10 ** (techo_db / 20):
            break
        x, gr = limitar(x, techo_db, picos)
        gr_max = min(gr_max, gr)
        x = x * 10 ** ((OBJ_LUFS - lufs(x)) / 20)
        picos = picos_os(x)
    tp = 20 * np.log10(picos.max())
    if tp > techo_db:   # red de seguridad: nunca por encima del techo
        x = x * 10 ** ((techo_db - tp) / 20)
    return x, gr_max


def medir_ffmpeg(ruta):
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", ruta, "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    i = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])
    p = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", r.stderr)[-1]
    return i, float(p)


def codificar(x, ruta, titulo):
    tmp = ruta + ".tmp.ogg"
    datos = np.ascontiguousarray(x.T, dtype="<f4").tobytes()
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "f32le", "-ar", str(SR),
                    "-ac", "2", "-i", "pipe:0", "-map_metadata", "-1", "-c:a", "libvorbis", "-q:a", "3",
                    "-fflags", "+bitexact", "-flags:a", "+bitexact",
                    "-metadata", f"title={titulo}", "-metadata", "artist=Invasión Alienígena",
                    tmp], input=datos, check=True)
    os.replace(tmp, ruta)


# ---------------------------------------------------------------------------
# Composiciones
# ---------------------------------------------------------------------------
def sector1():
    """Ruinas urbanas: marcha militar en La menor. Intro(4) A(16) B(8) Ruptura(4) A'(16) = 48 compases."""
    p = Pista("sector1", "Ruinas urbanas", 120, 48, 11, eco_tiempos=0.75, eco_fb=0.28)
    A = ["Am", "Dm", "G", "E", "Am", "C", "Dm E", "Am"]
    p.acordes(0, ["Am", "Am", "F", "E"])
    p.acordes(4, A + A[:7] + ["E"])
    p.acordes(20, ["F", "G", "Em", "Am", "F", "G", "E", "E7"])
    p.acordes(28, ["Am", "Am", "F", "E"])
    p.acordes(32, A + ["Am", "Dm", "G", "E", "F", "G", "E", "E"])

    tema = ("A4.3 A4.1 C5.3 A4.1 E5.4 E5.4 | F5.3 E5.1 D5.3 C5.1 D5.8 | B4.3 B4.1 D5.3 B4.1 G5.4 F5.2 E5.2 |"
            " E5.6 D5.1 C5.1 B4.8 | A4.3 A4.1 C5.3 A4.1 E5.4 A5.4 | G5.3 F5.1 E5.3 D5.1 C5.4 E5.4 |"
            " F5.3 E5.1 D5.3 C5.1 B4.4 G#4.4 |")
    tema_a = tema + " A4.10 E4.2 A4.2 B4.2"
    tema_b = tema + " B4.6 C5.1 B4.1 G#4.4 B4.4"
    MARCHA = {"k": "X.......x.......", "s": "....X.oo....X.oo", "h": "x.x.x.x.x.x.x.x."}
    MARCHA2 = {"k": "X...x...X...x...", "s": "o..oX.oo.o.oX.oo", "h": "x.x.x.x.x.x.x.x."}
    RELLENO = {"s": "....X...rrrrX.XX"}
    RELLENO_TOM = {"s": "....X...........", "t": "........1.1.2.33"}
    MARCHA_BAJO = "R.3 R.1 5.4 R.3 R.1 5.4"
    BAJO_8 = "R.2 R.2 5.2 R.2 8.2 R.2 5.2 a.2"

    # Intro: llamada de trompeta (contra) sobre marcha de caja
    p.melodia("contra", 0, "r.8 E4.3 E4.1 A4.4 | r.8 E4.3 E4.1 C5.4 | r.8 F4.3 A4.1 C5.4 | B4.8 G#4.4 E4.4", vel=1.1)
    p.bajo(0, 4, MARCHA_BAJO)
    p.bateria(0, 3, {"k": "X.......X.......", "s": "....x.o.....x.o."}, platillo=False, vol=0.85)
    p.bateria(3, 1, {"k": "X.......X......."}, platillo=False)
    p.redoble(3 * 4 + 1, 3, 0.15, 0.95)

    # A: tema dos veces; la segunda con arpegio y contramelodía
    p.melodia("lead", 4, tema_a)
    m2 = p.melodia("lead", 12, tema_b)
    p.bajo(4, 16, MARCHA_BAJO)
    p.arpegio("arp", 12, 8, "0 . 2 . 1 . 2 . 0 . 2 . 1 . 2 .", lo=57)
    p.contra_guia("contra", 12, 8, [(0, 8), (8, 8)], 55, 67, m2)
    p.bateria(4, 8, MARCHA, RELLENO)
    p.bateria(12, 8, MARCHA, RELLENO_TOM, platillo=False)

    # B: más lírico, relativo mayor, pulso 50 %, colchón y batería a medio tiempo
    mb = p.melodia("lead2", 20, "C5.4 F5.4 A5.6 G5.2 | G5.4 D5.4 B4.6 C5.2 | B4.4 E5.4 G5.4 B5.4 | A5.8 E5.4 C5.4 |"
                                " F5.4 A5.4 C6.6 B5.2 | D6.4 B5.4 G5.6 A5.2 | B5.6 A5.2 G#5.8 |"
                                " E5.4 F5.2 E5.2 D5.2 C5.2 B4.4")
    p.contra_guia("contra", 20, 8, [(0, 6), (6, 6), (12, 4)], 55, 69, mb, vel=0.7)
    p.arpegio("arp", 20, 8, "0 1 2 3 2 1 0 1 2 3 2 1 0 1 2 3", lo=60, vel=0.8)
    p.pad(20, 8)
    p.bajo(20, 8, "R.6 5.2 8.4 5.4")
    p.bateria(20, 8, {"k": "X.........x.....", "s": "........X.......", "h": "x.x.x.x.x.x.x...",
                      "o": "..............x."}, RELLENO)

    # Ruptura: el motivo en el registro grave y redoble en crescendo
    p.melodia("contra", 28, "A3.3 A3.1 C4.3 A3.1 E4.4 E4.4 | r.8 E4.3 E4.1 A4.4 |"
                            " F3.3 F3.1 A3.3 F3.1 C4.4 C4.4 | E3.3 E3.1 G#3.3 E3.1 B3.4 B3.4", vel=1.15)
    p.bajo(28, 4, MARCHA_BAJO)
    p.arpegio("arp", 28, 4, "0 . . 0 . . 0 . 1 . . 1 . . 2 .", lo=69, vel=0.8)
    p.bateria(28, 2, {"k": "X...x...X...x...", "s": "o.o.o.o.o.o.o.o."})
    p.bateria(30, 2, {"k": "X...x...X...x..."}, platillo=False)
    p.redoble(30 * 4, 8, 0.12, 1.0)

    # A': tema con armonía paralela y luego clímax una octava arriba
    m3 = p.melodia("lead", 32, tema_a)
    p.contra_tercera("contra", m3)
    m4 = p.melodia("lead", 40, "A5.3 A5.1 C6.3 A5.1 E6.4 E6.4 | F6.3 E6.1 D6.3 C6.1 D6.8 |"
                               " B5.3 B5.1 D6.3 B5.1 G6.4 F6.2 E6.2 | E6.6 D6.1 C6.1 B5.8 |"
                               " A5.3 A5.1 C6.3 A5.1 F5.4 A5.4 | B5.3 B5.1 D6.3 B5.1 G5.4 B5.4 |"
                               " G#5.3 G#5.1 B5.3 G#5.1 E5.4 D5.4 | E5.12 r.4", vel=0.92)
    p.contra_guia("contra", 40, 8, [(0, 4), (4, 4), (8, 8)], 57, 72, m4)
    p.arpegio("arp", 32, 16, "0 . 2 . 1 . 2 . 0 . 2 . 1 . 2 .", lo=57)
    p.bajo(32, 16, BAJO_8)
    p.pad(40, 8, vel=0.8)
    p.bateria(32, 8, MARCHA2, RELLENO_TOM)
    p.bateria(40, 7, MARCHA2, RELLENO)
    p.bateria(47, 1, {"k": "X.......X.......", "s": "X..............."}, platillo=False)
    p.redoble(47 * 4 + 1, 3, 0.2, 1.0)
    return p


def sector4():
    """Órbita: Re dórico. Intro(8) A(16) B(8) A'(16) Coda(4) = 52 compases."""
    p = Pista("sector4", "Órbita", 126, 52, 44, eco_tiempos=0.75, eco_fb=0.45, rev_rt60=2.0,
              instrumentos={"lead2": dict(eco=0.38, rev=0.2), "arp": dict(eco=0.45, gain=0.07)})
    A1 = ["Dm7", "Em7", "F", "G", "Dm7", "Em7", "F", "Am7"]
    A2 = ["Dm7", "Em7", "F", "G", "Dm7", "Em7", "F", "G"]
    B = ["Bbmaj7", "C", "Dm7", "Dm7", "Bbmaj7", "C", "Asus4", "A"]
    p.acordes(0, A1)
    p.acordes(8, A1 + A2)
    p.acordes(24, B)
    p.acordes(32, A1 + A2)
    p.acordes(48, ["Bbmaj7", "C", "Bbmaj7", "Asus4 A"])

    tema = ("A4.2 D5.2 E5.2 F5.6 E5.2 D5.2 | G5.8 E5.4 B4.4 | A4.2 C5.2 E5.2 F5.6 G5.2 A5.2 | B5.12 A5.2 G5.2 |"
            " D5.2 F5.2 G5.2 A5.6 G5.2 F5.2 | E5.8 D5.4 B4.4 | C5.2 E5.2 F5.2 A5.6 G5.2 E5.2 | A5.10 r.6 |"
            " A4.2 D5.2 E5.2 F5.6 E5.2 D5.2 | G5.8 E5.4 B4.4 | A4.2 C5.2 E5.2 F5.6 G5.2 A5.2 | B5.12 A5.2 G5.2 |"
            " F5.2 A5.2 C6.2 D6.6 C6.2 A5.2 | B5.8 G5.4 E5.4 | A5.4 G5.4 F5.4 E5.4 | D5.12 r.4")
    ARP = "0 1 2 3 4 3 2 1 0 1 2 3 4 5 4 3"
    FLOTA = "R.6 R.2 5.6 8.2"
    LIGERA = {"k": "X.........X.....", "s": "........x.......", "h": "..x...x...x...x."}
    PLENA = {"k": "X.....X...X.....", "s": "....X.......X...", "h": "x.xxx.xxx.xxx.xx", "o": "......x.......x."}
    RELL = {"s": "....X.......XoXX", "t": "........1.2....."}

    # Intro: arpegio, colchón y campanas con eco; la batería entra a mitad
    p.arpegio("arp", 0, 8, ARP, lo=62, vel=0.9)
    p.pad(0, 8, lo=50, hi=67)
    p.melodia("campana", 0, "A5.8 r.8 | B5.8 r.8 | C6.8 r.8 | D6.8 r.8 | A5.6 D6.2 r.8 | B5.6 E6.2 r.8 |"
                            " C6.6 F6.2 r.8 | E6.16")
    p.bajo(4, 4, "R.16", lo=38, vel=0.8)
    p.bateria(4, 4, {"h": "..x...x...x...x.", "k": "X..............."}, platillo=False, vol=0.8)

    # A: melodía flotante en pulso 50 %
    m1 = p.melodia("lead2", 8, tema)
    p.arpegio("arp", 8, 16, ARP, lo=62)
    p.pad(8, 16, lo=50, hi=67, vel=0.8)
    p.bajo(8, 16, FLOTA, lo=38)
    p.bateria(8, 8, LIGERA, RELL)
    p.bateria(16, 8, LIGERA, RELL, platillo=False)
    p.contra_guia("contra", 16, 8, [(0, 16)], 57, 69, m1[len(m1) // 2:], vel=0.7)

    # B: cambio de color (Sib, Do, modo eólico), pulso 25 % y batería completa
    mb = p.melodia("lead", 24, "D5.6 F5.2 A5.8 | G5.6 E5.2 C5.8 | F5.4 E5.4 D5.4 C5.4 | D5.12 A4.2 C5.2 |"
                               " F5.6 A5.2 D6.8 | E6.6 D6.2 C6.4 G5.4 | D6.8 E5.8 | E5.4 A5.4 C#6.8")
    p.contra_guia("contra", 24, 8, [(0, 8), (8, 8)], 57, 70, mb)
    p.arpegio("arp", 24, 8, "0 . 1 . 2 . 3 . 4 . 3 . 2 . 1 .", lo=62)
    p.arpegio("arp2", 24, 8, ". . . 4 . . 5 . . . 6 . . 5 . .", lo=62, vel=0.8)
    p.pad(24, 8, lo=50, hi=67)
    p.bajo(24, 8, "R.2 R.2 8.2 R.2 R.2 R.2 8.2 5.2", lo=34)
    p.bateria(24, 8, PLENA, RELL)

    # A': el tema con contramelodía y doble arpegio
    m2 = p.melodia("lead2", 32, tema)
    p.contra_guia("contra", 32, 16, [(0, 8), (8, 8)], 55, 69, m2)
    p.arpegio("arp", 32, 16, ARP, lo=62)
    p.arpegio("arp2", 32, 16, "4 . 2 . 3 . 1 . 4 . 2 . 3 . 1 .", lo=69, vel=0.8)
    p.pad(32, 16, lo=50, hi=67, vel=0.8)
    p.bajo(32, 16, FLOTA, lo=38)
    p.bateria(32, 8, PLENA, RELL)
    p.bateria(40, 8, PLENA, RELL, platillo=False)

    # Coda: vuelve a flotar y enlaza con la intro (La -> Rem)
    p.melodia("campana", 48, "D6.8 r.8 | E6.8 r.8 | F6.8 r.8 | E6.8 C#6.8")
    p.arpegio("arp", 48, 4, ARP, lo=62, vel=0.9)
    p.pad(48, 4, lo=50, hi=67)
    p.bajo(48, 4, "R.16", lo=34, vel=0.85)
    p.bateria(48, 4, {"h": "..x...x...x...x.", "k": "X..............."}, vol=0.8)
    return p


def sector5():
    """Xylos: Mi frigio con tonos enteros. Intro(4) A(16) B(8) Puente(2) A'(16) = 46 compases."""
    p = Pista("sector5", "Xylos, el mundo colmena", 112, 46, 55, eco_tiempos=0.75, eco_fb=0.4, rev_rt60=1.8,
              instrumentos={"lead": dict(glide=0.035, vib=(4.2, 30, 0.15), duty=0.25, eco=0.28),
                            "campana": dict(gain=0.11)})
    A = ["Em", "F", "Em", "Dm", "Em", "F", "G", "F", "Em", "F", "Em", "Dm", "C", "Dm", "F", "F"]
    p.acordes(0, ["Em", "F", "Em", "F"])
    p.acordes(4, A)
    p.acordes(20, ["Caug", "Daug", "Caug", "Daug", "Bbaug", "Caug", "F", "F"])
    p.acordes(28, ["Em", "F"])
    p.acordes(30, A)

    tema1 = ("E5.6 F5.2 E5.4 B4.4 | C5.6 B4.2 A4.4 F4.4 | G4.4 B4.4 E5.4 G5.4 | F5.6 E5.2 D5.8 |"
             " E5.6 F5.2 E5.4 B4.4 | C5.6 D5.2 E5.4 F5.4 | G5.6 F5.2 D5.4 B4.4 | A4.4 C5.4 F5.8")
    PULSO = "R.2 R.2 R.2 8.2 R.2 R.2 b.2 R.2"
    COLMENA = {"k": "X..x..x...X..x..", "s": "........X.......", "h": "xoxoxoxoxoxoxoxo"}
    COLMENA2 = {"k": "X..x..x...X..x..", "s": "....o...X..o..o.", "h": "xoxoxoxoxoxoxoxo",
                "t": "..............3."}
    RELL = {"t": "........1.2.3.33", "s": "........X..o...."}
    ARP = "0 2 1 3 0 2 1 3 4 2 3 1 4 2 3 1"

    # Intro: pulso de bajo, tambores tribales y la llamada de la colmena (semitono Mi-Fa)
    p.melodia("campana", 0, "E6.6 F6.2 E6.8 | r.16 | E6.6 F6.2 E6.8 | D6.4 C6.4 A5.8")
    p.bajo(0, 4, PULSO, lo=40)
    p.bateria(0, 4, {"t": "3..3..3...2..3..", "h": "..x...x...x...x."}, platillo=False, vol=0.8)

    # A
    m1 = p.melodia("lead", 4, tema1 + " | B5.6 C6.2 B5.4 G5.4 | A5.6 G5.2 F5.4 C5.4 | E5.4 G5.4 B5.4 E6.4 |"
                                      " D6.6 C6.2 A5.8 | G5.6 E5.2 C5.8 | F5.6 E5.2 D5.4 A4.4 | C5.8 F5.8 |"
                                      " G5.4 F5.4 E5.8")
    p.bajo(4, 16, PULSO, lo=40)
    p.arpegio("arp", 12, 8, ARP, lo=64, vel=0.85)
    p.contra_guia("contra", 12, 8, [(0, 6), (6, 10)], 52, 64, m1[len(m1) // 2:], vel=0.75)
    p.bateria(4, 8, COLMENA, RELL)
    p.bateria(12, 8, COLMENA, RELL, platillo=False)

    # B: tonos enteros (acordes aumentados), colchón inquietante y tambores dispersos
    mb = p.melodia("lead2", 20, "E5.4 G#5.4 C6.8 | A#5.4 F#5.4 D5.8 | C5.2 D5.2 E5.2 F#5.2 G#5.8 | A#5.12 r.4 |"
                                " D6.4 A#5.4 F#5.8 | E5.4 C5.4 G#4.8 | A4.4 C5.4 F5.8 | C5.4 D5.4 E5.4 F5.4", vel=0.9)
    p.contra_tercera("contra", mb, vel=0.65)
    p.pad(20, 8, lo=52, hi=68)
    p.arpegio("arp", 20, 8, "0 . 1 . 2 . 3 . 2 . 1 . 0 . 1 .", lo=64, vel=0.8)
    p.bajo(20, 8, "R.4 R.2 8.2 R.4 R.2 b.2", lo=34)
    p.bateria(20, 8, {"k": "X.........X.....", "t": "......3.....2...", "h": "..x...x...x...x."}, RELL)

    # Puente: sólo el pulso y un redoble de tambores que crece
    p.melodia("campana", 28, "E6.6 F6.2 E6.8 | r.16")
    p.bajo(28, 2, "R.1 R.1 R.1 R.1 R.1 R.1 R.1 R.1 R.1 R.1 R.1 R.1 R.1 R.1 R.1 R.1", lo=40, vel=0.9)
    p.bateria(28, 2, {"t": "3.3.3.3.2.2.2.2. 1.1.1.1.11111111"}, platillo=False, vol=0.9)
    p.redoble(29 * 4 + 2, 2, 0.2, 0.9)

    # A': tema con armonía paralela y variación aguda
    m2 = p.melodia("lead", 30, tema1)
    p.contra_tercera("contra", m2)
    m3 = p.melodia("lead", 38, "E6.6 F6.2 E6.4 B5.4 | C6.6 B5.2 A5.4 F5.4 | G5.2 B5.2 E6.4 D6.4 B5.4 |"
                               " A5.6 G5.2 F5.4 D5.4 | E5.4 G5.4 C6.4 E6.4 | F6.6 E6.2 D6.4 A5.4 | C6.6 A5.2 F5.8 |"
                               " G5.4 F5.4 E5.8", vel=0.92)
    p.contra_guia("contra", 38, 8, [(0, 8), (8, 8)], 55, 67, m3)
    p.arpegio("arp", 30, 16, ARP, lo=64)
    p.pad(38, 8, lo=52, hi=68, vel=0.7)
    p.bajo(30, 16, PULSO, lo=40)
    p.bateria(30, 8, COLMENA2, RELL)
    p.bateria(38, 8, COLMENA2, RELL, platillo=False)
    return p


def jefe():
    """Combate contra jefe: Do menor armónico. Intro(2) A(16) B(8) C(8) A'(16) = 50 compases."""
    p = Pista("jefe", "Jefe", 150, 50, 77, eco_tiempos=0.75, eco_fb=0.22, rev_rt60=1.0,
              instrumentos={"lead": dict(eco=0.12, vib=(6.0, 14, 0.18)), "arp": dict(eco=0.15)},
              bateria={"k": (0.36, 0.0, 0.0, 0.02)})
    A = ["Cm", "Ab", "Bb", "G", "Cm", "Ab", "Fm", "G", "Cm", "Ab", "Bb", "Eb", "Fm", "Ab", "G", "G"]
    p.acordes(0, ["Cm", "G"])
    p.acordes(2, A)
    p.acordes(18, ["Fm", "Gm", "Ab", "Bb", "Fm", "Ab", "Bdim", "G"])
    p.acordes(26, ["Cm", "Cm", "Db", "Db", "Cm", "Cm", "Ab", "G"])
    p.acordes(34, A)

    tema = ("C5.2 Eb5.2 G5.4 Eb5.2 G5.2 C6.4 | C6.2 Bb5.2 Ab5.4 Eb5.4 C5.4 | D5.2 F5.2 Bb5.4 F5.2 Bb5.2 D6.4 |"
            " D6.2 C6.2 B5.4 G5.4 D5.4 | C5.2 Eb5.2 G5.4 Eb5.2 G5.2 C6.4 | Eb6.2 D6.2 C6.4 Ab5.4 Eb5.4 |"
            " F5.2 Ab5.2 C6.4 Ab5.4 F5.4 | G5.2 B5.2 D6.4 F6.4 D6.2 B5.2 | G5.2 G5.2 C6.4 Bb5.2 Ab5.2 G5.4 |"
            " Ab5.2 Ab5.2 C6.4 Eb6.4 C6.4 | Bb5.2 Bb5.2 D6.4 F6.4 D6.4 | Eb6.6 D6.2 Bb5.4 G5.4 |"
            " Ab5.6 G5.2 F5.4 C5.4 | Eb5.6 F5.2 Ab5.4 C6.4 | B5.6 C6.2 D6.4 F6.4 | D6.8 B5.4 G5.4")
    GALOPE = "R.2 R.1 R.1 R.2 R.1 R.1 R.2 R.1 R.1 8.2 R.1 R.1"
    BOSS = {"k": "X...x...X...x.x.", "s": "....X.......X...", "h": "xxXxxxXxxxXxxxXx"}
    BOSS_B = {"k": "X...X...X...X...", "s": "....X.......X...", "h": "x...x...x...x...", "o": "..x...x...x...x."}
    BOSS_C = {"k": "X.X.X.x.X.X.X.x.", "s": "....X.......X..o", "h": "x.x.x.x.x.x.x.x."}
    RELL = {"s": "....X...XoXoXXXX"}
    RELL_TOM = {"s": "....X...........", "t": "........11223333"}
    ARP = "0 1 2 3 0 1 2 3 4 3 2 1 0 1 2 3"

    # Intro: golpes de orquesta en Do menor y escala armónica ascendente
    golpes = "C5.2 r.1 C5.2 r.1 C5.2 r.2 C5.2 r.4"
    p.melodia("lead", 0, golpes + " | G4.2 Ab4.2 B4.2 C5.2 D5.2 Eb5.2 F5.2 G5.2")
    p.melodia("contra", 0, "G4.2 r.1 G4.2 r.1 G4.2 r.2 G4.2 r.4 | r.16")
    p.melodia("arp2", 0, "Eb4.2 r.1 Eb4.2 r.1 Eb4.2 r.2 Eb4.2 r.4 | r.16")
    p.bajo(0, 2, "R.2 r.1 R.2 r.1 R.2 r.2 R.2 r.4 | R.2 R.2 R.2 R.2 R.2 R.2 R.2 R.2", lo=36)
    p.bateria(0, 1, {"k": "X..X..X...X.....", "t": "............1233"})
    p.bateria(1, 1, {"k": "X...X...X...X..."}, platillo=False)
    p.redoble(4, 4, 0.15, 1.0)

    # A
    m1 = p.melodia("lead", 2, tema)
    p.bajo(2, 16, GALOPE, lo=36)
    p.arpegio("arp", 10, 8, ARP, lo=60, vel=0.85)
    p.contra_guia("contra", 10, 8, [(0, 4), (4, 4), (8, 4), (12, 4)], 55, 67, m1[len(m1) // 2:], vel=0.7)
    p.bateria(2, 8, BOSS, RELL)
    p.bateria(10, 8, BOSS, RELL_TOM, platillo=False)

    # B: notas largas en pulso 50 %, colchón y bombo a negras
    mb = p.melodia("lead2", 18, "C6.8 Ab5.8 | D6.8 Bb5.8 | C6.8 Eb6.8 | D6.12 C6.4 | Ab5.6 G5.2 F5.8 |"
                                " Eb5.6 F5.2 Ab5.8 | B4.4 D5.4 F5.4 Ab5.4 | G5.4 F5.4 D5.4 B4.4")
    p.contra_guia("contra", 18, 8, [(0, 4), (4, 4), (8, 4), (12, 4)], 55, 69, mb, vel=0.8)
    p.arpegio("arp", 18, 8, ARP, lo=60)
    p.pad(18, 8, lo=55, hi=70, vel=0.9)
    p.bajo(18, 8, "R.2 8.2 R.2 8.2 R.2 8.2 R.2 8.2", lo=36)
    p.bateria(18, 8, BOSS_B, RELL)

    # C: riff amenazador con napolitana (Reb) y bajo machacón
    riff = ("C5.1 r.1 C5.1 r.1 Eb5.2 C5.1 r.1 G5.2 F#5.2 F5.2 Eb5.2 | C5.1 r.1 C5.1 r.1 Eb5.2 C5.1 r.1 Bb4.2 B4.2 C5.4 |"
            " Db5.1 r.1 Db5.1 r.1 F5.2 Db5.1 r.1 Ab5.2 G5.2 F5.2 Eb5.2 | Db5.1 r.1 Db5.1 r.1 F5.2 Db5.1 r.1 C5.2 Db5.2 Eb5.4 |")
    mc = p.melodia("lead", 26, riff + " C5.1 r.1 C5.1 r.1 Eb5.2 C5.1 r.1 G5.2 F#5.2 F5.2 Eb5.2 |"
                                      " C5.1 r.1 C5.1 r.1 Eb5.2 C5.1 r.1 Bb4.2 B4.2 C5.4 |"
                                      " Ab4.2 C5.2 Eb5.2 Ab5.2 C6.2 Eb6.2 C6.2 Ab5.2 |"
                                      " G5.2 B5.2 D6.2 G6.2 F6.2 D6.2 B5.2 G5.2")
    p.contra_tercera("contra", [n for n in mc if n[0] >= 30 * 4], vel=0.75)
    p.bajo(26, 6, "R.1 r.1 R.1 r.1 R.2 R.1 r.1 R.2 R.2 R.2 R.2", lo=36, vel=1.05)
    p.bajo(32, 2, "R.2 R.2 R.2 R.2 R.2 R.2 R.2 R.2", lo=36)
    p.arpegio("arp2", 30, 2, "0 1 2 3 4 3 2 1 0 1 2 3 4 3 2 1", lo=60, vel=0.8)
    p.bateria(26, 8, BOSS_C, RELL_TOM)

    # A': el tema con armonía paralela y arpegio continuo
    m2 = p.melodia("lead", 34, tema)
    p.contra_tercera("contra", m2)
    p.bajo(34, 16, GALOPE, lo=36)
    p.arpegio("arp", 34, 16, ARP, lo=60)
    p.pad(42, 8, lo=55, hi=70, vel=0.7)
    p.bateria(34, 8, BOSS, RELL_TOM)
    p.bateria(42, 8, BOSS, {"s": "....X...rrrrXXXX", "t": "........1.2.3..."}, platillo=False)
    return p


def supervivencia():
    """Modo supervivencia: Mi menor. Intro(4) A(16) B(8) C(8) A'(16) B'(8) = 60 compases."""
    p = Pista("supervivencia", "Supervivencia", 140, 60, 140, eco_tiempos=0.5, eco_fb=0.25, rev_rt60=1.1,
              bateria={"k": (0.40, 0.0, 0.0, 0.02)})
    A = ["Em", "C", "D", "Bm", "Em", "C", "Am", "B", "C", "D", "Bm", "Em", "Am", "C", "D", "B"]
    B = ["G", "D", "Am", "C", "G", "D", "C", "D"]
    p.acordes(0, ["Em", "C", "D", "B"])
    p.acordes(4, A)
    p.acordes(20, B)
    p.acordes(28, ["Am", "Bm", "C", "D", "Am", "Bm", "C", "B7"])
    p.acordes(36, A)
    p.acordes(52, B)

    tema = ("E5.3 E5.1 G5.2 B5.2 E6.4 D6.2 B5.2 | C6.4 B5.2 G5.2 E5.4 G5.4 | A5.3 A5.1 F#5.2 A5.2 D6.4 C6.2 A5.2 |"
            " B5.6 A5.2 F#5.8 | E5.3 E5.1 G5.2 B5.2 E6.4 F#6.2 G6.2 | E6.4 D6.2 C6.2 G5.4 E5.4 |"
            " C6.3 B5.1 A5.2 E5.2 A5.2 B5.2 C6.4 | B5.4 F#5.2 D#5.2 B4.4 r.4 |"
            " G5.3 G5.1 C6.2 E6.2 G6.4 E6.2 C6.2 | F#6.4 E6.2 D6.2 A5.4 D6.4 | B5.3 B5.1 D6.2 F#6.2 B5.8 |"
            " G5.4 F#5.2 E5.2 B4.8 | A5.3 A5.1 C6.2 E6.2 A5.4 G5.4 | E5.3 E5.1 G5.2 C6.2 E6.4 D6.2 C6.2 |"
            " D6.4 C6.2 B5.2 A5.4 F#5.4 | D#6.4 B5.4 F#5.4 D#5.4")
    tema_b = ("B5.6 A5.2 G5.4 D5.4 | F#5.6 E5.2 D5.4 A5.4 | C6.6 B5.2 A5.4 E5.4 | G5.8 E5.4 G5.4 |"
              " B5.4 D6.4 G6.8 | F#6.4 E6.4 D6.4 A5.4 | E6.6 D6.2 C6.4 G5.4 | A5.4 B5.4 C6.4 D6.4")
    ROCK = {"k": "X.....x.X.......", "s": "....X.......X...", "h": "x.x.x.x.x.x.x.x."}
    ROCK16 = {"k": "X.....x.X.x.....", "s": "....X.......X..o", "h": "xxXxxxXxxxXxxxXx"}
    DISCO = {"k": "X...X...X...X...", "s": "....X.......X...", "h": "x...x...x...x...", "o": "..x...x...x...x."}
    SINCO = {"k": "X..X..X...X..X..", "s": "....X.......X.X.", "h": "x.x.x.x.x.x.x.x."}
    RELL = {"s": "....X...XXoXXXXX"}
    RELL_TOM = {"s": "....X...........", "t": "........1122.3.3"}
    OCTAVAS = "R.2 8.2 R.2 8.2 R.2 8.2 R.2 8.2"
    ARP = "0 1 2 0 1 2 0 1 2 0 1 2 3 2 1 0"

    # Intro: arpegio 3 contra 4 y la batería que va entrando
    p.arpegio("arp", 0, 4, ARP, lo=64)
    p.bajo(0, 4, OCTAVAS, lo=36)
    p.bateria(0, 2, {"k": "X.......X.......", "h": "x.x.x.x.x.x.x.x."}, platillo=False, vol=0.85)
    p.bateria(2, 2, ROCK, {"s": "....X...XoXoXXXX"}, platillo=False)

    # A
    m1 = p.melodia("lead", 4, tema)
    p.bajo(4, 16, OCTAVAS, lo=36)
    p.arpegio("arp", 12, 8, ARP, lo=64, vel=0.85)
    p.contra_guia("contra", 12, 8, [(0, 6), (6, 6), (12, 4)], 55, 67, m1[len(m1) // 2:], vel=0.75)
    p.bateria(4, 8, ROCK, RELL)
    p.bateria(12, 8, ROCK, RELL_TOM, platillo=False)

    # B: Sol mayor, pulso 50 %, bombo a negras y charles abierto
    mb = p.melodia("lead2", 20, tema_b)
    p.contra_guia("contra", 20, 8, [(0, 8), (8, 8)], 55, 69, mb)
    p.arpegio("arp", 20, 8, "0 1 2 3 2 1 0 1 2 3 2 1 0 1 2 3", lo=62, vel=0.85)
    p.pad(20, 8, lo=55, hi=69, vel=0.9)
    p.bajo(20, 8, "R.2 R.2 5.2 R.2 R.2 8.2 5.2 a.2", lo=36)
    p.bateria(20, 8, DISCO, RELL)

    # C: puente sincopado que sube por grados hasta Si7
    mc = p.melodia("lead", 28, "A5.3 E5.3 A5.2 C6.4 B5.2 A5.2 | B5.3 F#5.3 B5.2 D6.4 E6.2 D6.2 |"
                               " C6.3 G5.3 C6.2 E6.4 D6.2 C6.2 | D6.3 A5.3 D6.2 F#6.4 E6.2 D6.2 |"
                               " E6.4 C6.4 A5.4 C6.4 | F#6.4 D6.4 B5.4 D6.4 | G6.4 E6.4 C6.4 E6.4 |"
                               " F#6.4 D#6.4 B5.4 A5.4")
    p.contra_tercera("contra", mc[len(mc) // 2:], vel=0.75)
    p.bajo(28, 8, "R.3 R.3 R.2 R.3 R.3 8.2", lo=36)
    p.arpegio("arp2", 28, 8, "0 . 1 . 2 . 1 . 0 . 1 . 2 . 3 .", lo=67, vel=0.8)
    p.bateria(28, 8, SINCO, RELL_TOM)

    # A': tema con armonía paralela y charles a semicorcheas
    m2 = p.melodia("lead", 36, tema)
    p.contra_tercera("contra", m2)
    p.bajo(36, 16, OCTAVAS, lo=36)
    p.arpegio("arp", 36, 16, ARP, lo=64)
    p.bateria(36, 8, ROCK16, RELL)
    p.bateria(44, 8, ROCK16, RELL_TOM, platillo=False)

    # B': reexposición del tema B, con la contramelodía más activa; acaba en Re -> Mim (intro)
    mb2 = p.melodia("lead2", 52, tema_b)
    p.contra_guia("contra", 52, 8, [(0, 4), (4, 4), (8, 4), (12, 4)], 55, 69, mb2)
    p.arpegio("arp", 52, 8, ARP, lo=62)
    p.pad(52, 8, lo=55, hi=69, vel=0.9)
    p.bajo(52, 8, "R.2 R.2 5.2 R.2 R.2 8.2 5.2 a.2", lo=36)
    p.bateria(52, 8, DISCO, RELL)
    return p


def final():
    """Final y créditos: Re mayor; el motivo de la marcha del sector 1 convertido en himno.
    Intro(4) A(8) B(8) A'(8) = 28 compases."""
    p = Pista("final", "Final", 98, 28, 98, eco_tiempos=0.75, eco_fb=0.35, rev_rt60=2.2,
              instrumentos={"lead": dict(eco=0.26, rev=0.18), "lead2": dict(eco=0.3, rev=0.2)})
    A = ["D", "G", "Bm", "A", "D", "G", "Em A", "D"]
    p.acordes(0, ["G", "D", "Em", "Asus4 A"])
    p.acordes(4, A)
    p.acordes(12, ["Bm", "G", "D", "A", "Bm", "G", "Em", "Asus4 A"])
    p.acordes(20, A)

    tema = ("D5.3 D5.1 F#5.3 D5.1 A5.4 A5.4 | B5.3 A5.1 G5.3 F#5.1 G5.8 | F#5.3 F#5.1 B5.3 F#5.1 D6.4 C#6.2 B5.2 |"
            " C#6.6 B5.1 A5.1 E5.8 | D5.3 D5.1 F#5.3 D5.1 A5.4 D6.4 | D6.3 C#6.1 B5.3 A5.1 G5.4 B5.4 |"
            " G5.3 F#5.1 E5.3 D5.1 C#5.4 E5.4 |")
    SUAVE = {"k": "X.......X.......", "s": "....x.......x...", "h": "x.x.x.x.x.x.x.x."}
    HIMNO = {"k": "X.......X.x.....", "s": "....X.oo....X.oo", "h": "x.x.x.x.x.x.x.x."}

    # Intro: colchón, arpegio suave y campanas
    p.pad(0, 4, lo=54, hi=69)
    p.arpegio("arp", 0, 4, "0 . 1 . 2 . 3 . 4 . 3 . 2 . 1 .", lo=62, vel=0.85)
    p.melodia("campana", 0, "B5.16 | A5.16 | G5.16 | A5.8 C#6.8")
    p.bajo(0, 4, "R.12 5.4", lo=38, vel=0.85)

    # A: el himno en pulso 50 %
    p.melodia("lead2", 4, tema + " D5.10 A4.2 B4.2 C#5.2")
    p.pad(4, 8, lo=54, hi=69, vel=0.8)
    p.arpegio("arp", 4, 8, "0 . 1 . 2 . 3 . 4 . 3 . 2 . 1 .", lo=62)
    p.bajo(4, 8, "R.4 5.4 8.4 5.4", lo=38)
    p.bateria(4, 8, SUAVE, {"s": "....x.......XoXX"}, vol=0.85)

    # B: desarrollo lírico (Sim, Sol) con suspensión final 4-3
    mb = p.melodia("lead", 12, "D5.4 F#5.4 B5.8 | B5.6 A5.2 G5.4 D5.4 | A5.6 F#5.2 D5.8 | E5.6 F#5.2 E5.4 C#5.4 |"
                               " D5.4 F#5.4 B5.6 C#6.2 | D6.6 B5.2 G5.8 | E6.6 D6.2 B5.4 G5.4 | D6.8 C#6.8")
    p.contra_guia("contra", 12, 8, [(0, 8), (8, 8)], 54, 69, mb)
    p.pad(12, 8, lo=54, hi=69)
    p.arpegio("arp", 12, 8, "0 1 2 3 2 1 0 1 2 3 2 1 0 1 2 3", lo=62, vel=0.75)
    p.bajo(12, 8, "R.6 R.2 5.4 8.4", lo=35)
    p.bateria(12, 8, {"k": "X.........X.....", "s": "........X.......", "t": "..............3.",
                      "h": "x.x.x.x.x.x.x.x."}, {"t": "........1.1.2.3.", "s": "....X..........."})

    # A': himno completo, la melodía doblada a la octava grave y la caja de marcha del sector 1
    m3 = p.melodia("lead", 20, tema + " D5.12 r.4")
    p.melodia("contra", 20, tema + " D5.12 r.4", transp=-12, vel=0.75)
    p.contra_guia("arp2", 20, 8, [(0, 4), (4, 4), (8, 4), (12, 4)], 57, 69, m3, vel=0.8)
    p.pad(20, 8, lo=54, hi=69, vel=0.8)
    p.arpegio("arp", 20, 8, "0 1 2 3 4 3 2 1 0 1 2 3 4 3 2 1", lo=62, vel=0.8)
    p.bajo(20, 8, "R.3 R.1 5.4 R.3 R.1 8.4", lo=38)
    p.bateria(20, 7, HIMNO, {"s": "....X...rrrrX.XX"})
    p.bateria(27, 1, {"k": "X.......X.......", "s": "X...............", "h": "x.x.x.x........."},
              platillo=False)
    p.redoble(27 * 4 + 2, 2, 0.12, 0.6)
    return p


PISTAS = {"sector1": sector1, "sector4": sector4, "sector5": sector5, "jefe": jefe,
          "supervivencia": supervivencia, "final": final}


def generar(nombre):
    t0 = time.time()
    p = PISTAS[nombre]()
    mezcla = p.render()
    ruta = os.path.join(DESTI, nombre + ".ogg")
    techo = TECHO_DBTP
    for intento in range(4):
        x, gr = masterizar(mezcla, techo)
        assert np.max(np.abs(x)) < 1.0, "recorte digital"
        codificar(x, ruta, p.titulo)
        i_ogg, tp_ogg = medir_ffmpeg(ruta)
        if tp_ogg <= MAX_DBTP_OGG - 0.1:
            break
        techo -= tp_ogg - MAX_DBTP_OGG + 0.3
    voces = ", ".join(f"{k} {v:.0f}" for k, v in sorted(p.rms_voces.items(), key=lambda kv: -kv[1]))
    print(f"{nombre + '.ogg':18s} {p.bpm:3d} BPM  {p.compases:2d} compases  {p.L / SR:6.2f} s  "
          f"{os.path.getsize(ruta) / 1e6:5.2f} MB  {i_ogg:6.1f} LUFS  {tp_ogg:5.1f} dBTP  "
          f"limitador {gr:5.1f} dB  ({time.time() - t0:4.1f} s)")
    print(f"    RMS por voz (dBFS antes de normalizar): {voces}")


def main():
    nombres = sys.argv[1:] or list(PISTAS)
    for n in nombres:
        if n not in PISTAS:
            sys.exit(f"pista desconocida: {n} (opciones: {', '.join(PISTAS)})")
    os.makedirs(DESTI, exist_ok=True)
    for n in nombres:
        generar(n)


if __name__ == "__main__":
    main()
