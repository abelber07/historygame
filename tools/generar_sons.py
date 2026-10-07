"""Genera els efectes de so nous del HUD (v3.4) a assets/so/:

    latido.ogg   batec del cor quan queda poca vida (dos cops greus: «lub-dub»)
    ting.ogg     bala que rebota contra l'escut d'energia (metàl·lic, agut)
    marca.ogg    marca d'impacte: clic sec i curt quan la bala toca un enemic

Ús:  python3 tools/generar_sons.py      (cal numpy i ffmpeg)
"""
import os
import shutil
import subprocess

import numpy as np

SR = 44100
FFMPEG = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
SORTIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "so")


def temps(segons):
    return np.arange(int(SR * segons)) / SR


def envolupant(t, atac, caiguda):
    return np.minimum(1.0, t / max(atac, 1e-4)) * np.exp(-t / caiguda)


def cop_greu(freq, durada=0.16):
    t = temps(durada)
    f = freq * (1 + 0.6 * np.exp(-t / 0.02))          # la freqüència cau ràpid: cop sord
    fase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(fase) * envolupant(t, 0.004, 0.05)


def latido():
    s = np.zeros(int(SR * 0.62))
    lub, dub = cop_greu(58), cop_greu(52) * 0.75
    s[:len(lub)] += lub
    ini = int(SR * 0.19)
    s[ini:ini + len(dub)] += dub
    return s


def ting():
    t = temps(0.42)
    s = np.zeros_like(t)
    for freq, amp, cai in ((2350, 1.0, 0.11), (3720, 0.55, 0.07), (5410, 0.3, 0.04), (1180, 0.35, 0.16)):
        s += amp * np.sin(2 * np.pi * freq * t) * envolupant(t, 0.0015, cai)
    soroll = np.random.default_rng(3).normal(0, 1, len(t)) * envolupant(t, 0.0005, 0.006) * 0.5
    return s + soroll


def marca():
    t = temps(0.07)
    s = np.sin(2 * np.pi * 1650 * t) * envolupant(t, 0.0008, 0.012)
    s += np.random.default_rng(5).normal(0, 1, len(t)) * envolupant(t, 0.0003, 0.004) * 0.6
    return s


def desar(nom, senyal, pic=0.8):
    senyal = senyal / (np.max(np.abs(senyal)) or 1) * pic
    ruta = os.path.join(SORTIDA, nom + ".ogg")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1",
                    "-i", "-", "-c:a", "libvorbis", "-q:a", "4", ruta],
                   input=senyal.astype(np.float32).tobytes(), check=True)
    print("ok", ruta)


if __name__ == "__main__":
    desar("latido", latido(), 0.9)
    desar("ting", ting(), 0.7)
    desar("marca", marca(), 0.6)
