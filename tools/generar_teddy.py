"""Genera el Teddy Bear (mascota secreta de la secció de drons) a assets/img/teddy.png + teddy.json.

    python3 tools/generar_teddy.py [vista.png]

Osset de peluix amb morro clar, ulls de botó, galtes rosa, llaç rosa i un cor cosit a la panxa.
Postures: quiet (i parpelleig), ajupit / salt / aterra (els saltirons de la sala), cor (emoticona: s'abraça
un cor amb els ulls tancats), llança (braços amunt quan tira cors) i vola (a la partida, amb les potes penjant).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame  # noqa: E402
from pintor import Figura, comprovar_paleta, empaquetar, retallar  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SORTIDA = os.path.join(AQUI, "..", "assets", "img")

MAT = {
    "pelutx": [(44, 24, 14), (118, 70, 40), (160, 104, 60), (198, 142, 90), (230, 186, 136)],
    "pelutx_c": [(96, 64, 38), (196, 156, 108), (226, 194, 148), (242, 220, 184), (252, 240, 220)],
    "rosa": [(92, 20, 60), (200, 70, 140), (240, 120, 180), (252, 170, 210), (255, 220, 238)],
    "boto": [(8, 6, 10), (20, 16, 22), (34, 28, 36), (70, 62, 74), (230, 230, 240)],
}
comprovar_paleta(MAT)
W, H, CX, PEUS = 40, 44, 20, 42
COR = [".kk.kk.", "kaakbak", "kaaaaak", ".kaaak.", "..kak..", "...k..."]          # cor de 7x6 (a=rosa, b=reflex)


ESCALA = 0.68                                    # el Teddy fa uns 26 píxels d'alt (la sala el mostra x2)


def patro(f, x, y, files, colors):
    """Dibuix de píxels 1:1 (no s'escala) centrat al punt (x, y) del dibuix."""
    ax, ay = f.t(x, y)
    w, h = len(files[0]), len(files)
    for j, fila in enumerate(files):
        for i, ch in enumerate(fila):
            if ch in colors:
                f.detalls.append((round(ax - w / 2 + i), round(ay - h / 2 + j), colors[ch]))


COR_PANXA = [".k.k.", "kakbk", "kaaak", ".kak.", "..k.."]
LLAÇ = ["kk.kk", "kaKak", "kk.kk"]                 # llacet a l'orella


def teddy(pose="quiet", escala=ESCALA):
    f = Figura(round(W * escala) + 2, round(H * escala) + 2, MAT, ("boto",), escala)
    rosa = {"k": MAT["rosa"][1], "a": MAT["rosa"][2], "b": MAT["rosa"][4], "K": MAT["rosa"][3]}
    cap_dy = {"ajupit": 3, "salt": -2, "aterra": 2, "cor": 1}.get(pose, 0)
    cos_dy = {"ajupit": 2, "salt": -2, "aterra": 1}.get(pose, 0)
    estira = {"salt": 1, "ajupit": -1}.get(pose, 0)
    vola = pose == "vola"
    for s in (-1, 1):                                              # cames
        x = CX + s * 5
        if vola or pose == "salt":
            f.el·lipse("pelutx", x - 3.5, 33 + cos_dy, x + 3.5, 42 + cos_dy, "esfera", grup=f"cama{s}")
            f.el·lipse("pelutx_c", x - 2.5, 38 + cos_dy, x + 2.5, 42 + cos_dy, grup=f"cama{s}")
        else:
            f.el·lipse("pelutx", x - 4, 35 + cos_dy, x + 4, PEUS, "esfera", grup=f"cama{s}")
            f.el·lipse("pelutx_c", x - 2.5, 38 + cos_dy, x + 2.5, PEUS, grup=f"cama{s}")
    f.el·lipse("pelutx", CX - 9, 23 + cos_dy - estira, CX + 9, 38 + cos_dy, "esfera", grup="cos")
    f.el·lipse("pelutx_c", CX - 6, 26 + cos_dy, CX + 6, 36 + cos_dy, grup="cos")
    patro(f, CX, 31 + cos_dy, COR_PANXA, rosa)                     # cor cosit a la panxa
    angles = {"quiet": (2.2, 0.9), "parpella": (2.2, 0.9), "ajupit": (2.5, 0.6), "salt": (-2.2, -0.9),
              "aterra": (2.6, 0.5), "cor": (0.9, 2.2), "llança": (-2.0, -1.1), "vola": (2.7, 0.4)}[pose]
    for s, a in zip((-1, 1), angles):                              # braços
        esp = (CX + s * 7, 27 + cos_dy)
        ma = (CX + s * 2, 31 + cos_dy) if pose == "cor" else (esp[0] + math.cos(a) * 6, esp[1] + math.sin(a) * 6)
        f.membre("pelutx", [esp, ma], [3.0, 2.6], grup=f"braç{s}")
        f.el·lipse("pelutx_c", ma[0] - 2, ma[1] - 2, ma[0] + 2, ma[1] + 2, grup=f"braç{s}")
    hy = 4 + cap_dy
    for s in (-1, 1):                                              # orelles
        ex = CX + s * 9
        f.cercle("pelutx", ex, hy + 4, 4.5, "esfera", grup="cap")
        f.cercle("rosa", ex, hy + 4, 2.0)
    f.el·lipse("pelutx", CX - 12, hy, CX + 12, hy + 20, "esfera", grup="cap")
    f.el·lipse("pelutx_c", CX - 5, hy + 11, CX + 5, hy + 19, "esfera")      # morro
    fosc, clar = MAT["boto"][1], MAT["boto"][4]
    patro(f, CX, hy + 13, ["kkk", ".k.", "k.k"], {"k": fosc})               # nas i boqueta
    tancats = pose in ("parpella", "cor", "llança")
    for s in (-1, 1):
        ex, ey = CX + s * 6, hy + 9
        if tancats:
            patro(f, ex, ey, [".k.", "k.k"], {"k": fosc})               # ulls feliços ^ ^
        else:
            patro(f, ex, ey, ["wk", "kk"], {"k": fosc, "w": clar})      # ulls de botó
        patro(f, CX + s * 9.5, hy + 13, ["ab"], {"a": MAT["rosa"][3], "b": MAT["rosa"][2]})   # galtes
    patro(f, CX + 10.5, hy + 1.5, LLAÇ, rosa)                     # llacet a l'orella
    return f.superficie(fins_a_baix=False)


def cor(mida):
    """Cor rosa per a les emoticones (mida 1 o 2)."""
    s = pygame.Surface((7, 6), pygame.SRCALPHA)
    colors = {"k": MAT["rosa"][1], "a": MAT["rosa"][2], "b": MAT["rosa"][4]}
    for y, fila in enumerate(COR):
        for x, ch in enumerate(fila):
            if ch in colors:
                s.set_at((x, y), colors[ch])
    return pygame.transform.scale(s, (7 * mida, 6 * mida))


POSES = ("quiet", "parpella", "ajupit", "salt", "aterra", "cor", "llança", "vola")


def generar():
    pygame.display.set_mode((1, 1))
    imatges, desp = {}, {}
    for p in POSES:
        imatges[p], desp[p] = retallar(teddy(p))
    imatges["cor_1"], desp["cor_1"] = cor(1), (0, 0)
    imatges["cor_2"], desp["cor_2"] = cor(2), (0, 0)
    atles, rects = empaquetar(imatges, ample=256)
    info = {"llenç": [round(W * ESCALA) + 2, round(H * ESCALA) + 2], "ancora": [round(CX * ESCALA), round(PEUS * ESCALA) + 1],
            "imatges": {n: rects[n] + list(desp[n]) for n in rects}}
    pygame.image.save(atles, os.path.join(SORTIDA, "teddy.png"))
    with open(os.path.join(SORTIDA, "teddy.json"), "w") as fit:
        json.dump(info, fit, separators=(",", ":"))
    print("teddy.png", atles.get_size())


if __name__ == "__main__":
    generar()
