"""
Contingut desbloquejable (versió 3.5): cosmètics nous, Battle Pass per temporades, rangs militars,
maestria d'armes, bestiari, desafiaments per estrelles i reptes diaris.
Els textos són en castellà (es tradueixen amb idiomes.T). Els noms de variables, en català.
"""

# ---------------------------------------------------------------------------
# Cosmètics nous. Prefix a self.cosmetics: e: estela, k: efecte d'eliminació, m: mira, h: tema del HUD,
# c: targeta de jugador, d: dron. "preu": es pot comprar a les ofertes del dia.
# ---------------------------------------------------------------------------
ESTELES = {
    "normal": {"nom": "Estándar", "colors": [(120, 230, 255)]},
    "foc": {"nom": "Fuego", "colors": [(255, 140, 40), (255, 220, 80), (220, 60, 30)]},
    "llamp": {"nom": "Relámpago", "colors": [(190, 210, 255), (255, 255, 255), (120, 150, 255)]},
    "toxica": {"nom": "Tóxica", "colors": [(120, 255, 90), (60, 200, 60), (200, 255, 140)], "preu": 800},
    "pixels": {"nom": "Píxeles", "colors": [(255, 80, 200), (90, 230, 255), (255, 214, 64), (80, 220, 120)], "preu": 1000},
    "ombra": {"nom": "Sombra", "colors": [(90, 50, 140), (40, 26, 70), (150, 90, 220)]},
    "arc": {"nom": "Arcoíris", "colors": "arc"},
    "daurada": {"nom": "Dorada", "colors": [(255, 214, 64), (255, 245, 170), (220, 160, 40)]},
}
EFECTES_BAIXA = {
    "normal": {"nom": "Restos"},
    "pixels": {"nom": "Desintegrar"},
    "confeti": {"nom": "Confeti", "preu": 900},
    "gel": {"nom": "Congelar"},
    "electric": {"nom": "Electrocutar"},
    "forat": {"nom": "Agujero negro"},
    "daurat": {"nom": "Lluvia de oro"},
}
MIRES = {
    "blanc": {"nom": "Blanca", "color": (255, 255, 255)},
    "verd": {"nom": "Verde", "color": (110, 255, 140)},
    "cian": {"nom": "Cian", "color": (90, 230, 255)},
    "rosa": {"nom": "Rosa", "color": (255, 110, 210), "preu": 400},
    "groc": {"nom": "Amarilla", "color": (255, 220, 70), "preu": 400},
    "vermell": {"nom": "Roja", "color": (255, 80, 80)},
    "arc": {"nom": "Arcoíris", "color": "arc"},
}
TEMES_HUD = {
    "classic": {"nom": "Clásico", "vora": (90, 120, 190), "fons": (8, 10, 24)},
    "militar": {"nom": "Militar", "vora": (150, 160, 90), "fons": (14, 16, 8)},
    "neo": {"nom": "Neón", "vora": (255, 80, 200), "fons": (18, 6, 26)},
    "glacial": {"nom": "Glacial", "vora": (150, 230, 255), "fons": (6, 16, 28), "preu": 700},
    "infern": {"nom": "Infierno", "vora": (240, 100, 40), "fons": (26, 8, 6)},
    "daurat": {"nom": "Dorado", "vora": (255, 205, 60), "fons": (24, 18, 4)},
}
# fons: "estels" (cel estrellat) o la clau d'un escenari (n, e) del qual es retalla el fons; "color" tenyeix
TARGETES = {
    "estels": {"nom": "Estrellas", "fons": "estels"},
    "ruines": {"nom": "Ruinas", "fons": (0, 0)},
    "selva": {"nom": "Selva", "fons": (1, 0), "preu": 600},
    "fortalesa": {"nom": "Fortaleza", "fons": (2, 0)},
    "orbita": {"nom": "Órbita", "fons": (3, 0)},
    "xylos": {"nom": "Xylos", "fons": (4, 0)},
    "xenobio": {"nom": "Xenobiología", "fons": (4, 1)},
    "daurada": {"nom": "Dorada", "fons": "daurada"},
}
DRONS = {
    "cap": {"nom": "Ninguno"},
    "bit": {"nom": "Bit"},
    "sonda": {"nom": "Sonda"},
    "ovni": {"nom": "Mini-OVNI", "preu": 1500},
    "corb": {"nom": "Cuervo"},
    "medic": {"nom": "Médico"},
    "daurat": {"nom": "Dorado"},
}
# Dibuix dels drons (pixel art, s'amplia x2). a = color principal, b = secundari, u = ull
DIBUIX_DRONS = {
    "bit": ({"a": (90, 200, 255), "b": (40, 90, 160), "u": (255, 255, 255)}, [
        "...kkkkk...", "..kaaaaak..", ".kaaaaaaak.", "kaaauuuaaak", "kaabuubbaak", "kaaauuuaaak", ".kaaaaaaak.",
        "..kbbbbbk..", "...kk.kk..."]),
    "sonda": ({"a": (200, 205, 220), "b": (110, 116, 140), "u": (255, 90, 90)}, [
        ".....k.....", "....kak....", "...kaaak...", "..kaauaak..", ".kaaauaaak.", "kbbbbbbbbbk", ".kb.....bk.",
        ".k.......k."]),
    "ovni": ({"a": (150, 255, 150), "b": (120, 126, 150), "u": (255, 230, 120)}, [
        "....kkk....", "...kaaak...", "..kaaaaak..", "kkkkkkkkkkk", "kbbubbubbuk", ".kbbbbbbbk.", "..kkkkkkk.."]),
    "corb": ({"a": (60, 64, 90), "b": (30, 32, 48), "u": (255, 60, 60)}, [
        "..kkk......", ".kaaak.....", "kaauaak.kk.", "kaaaaaakbbk", ".kaaaaaabbk", "..kbbbbbbk.", "...kk.kk..."]),
    "medic": ({"a": (240, 240, 245), "b": (220, 60, 60), "u": (90, 230, 255)}, [
        "...kkkkk...", "..kaaaaak..", ".kaabbbaak.", "kaabbbbbaak", "kaaabbbaaak", ".kaaauaaak.", "..kkkkkkk..",
        "...k...k..."]),
    "daurat": ({"a": (255, 214, 64), "b": (200, 140, 30), "u": (255, 255, 255)}, [
        "....kkk....", "...kaaak...", "..kaauaak..", ".kaaaaaaak.", "kbaaaaaaabk", "kbbaaaaabbk", ".kbbbbbbbk.",
        "..k.k.k.k.."]),
}
# Camuflatges de la maestria d'armes (nivell que cal amb l'arma; el diamant, totes les armes en or)
CAMUFLATGES = {
    "cap": {"nom": "Sin camuflaje", "nivell": 1, "tint": None, "bala": None},
    "bronze": {"nom": "Bronce", "nivell": 4, "tint": (205, 127, 70), "bala": (240, 160, 100)},
    "plata": {"nom": "Plata", "nivell": 7, "tint": (215, 220, 235), "bala": (235, 240, 250)},
    "or": {"nom": "Oro", "nivell": 10, "tint": (255, 200, 60), "bala": (255, 220, 80)},
    "diamant": {"nom": "Diamante", "nivell": 10, "tint": (140, 225, 255), "bala": (170, 240, 255)},
}
# baixes acumulades per arribar a cada nivell de maestria (nivell 1 = 0 baixes)
MAESTRIA = [0, 10, 25, 45, 70, 100, 140, 190, 250, 320]

# Uniformes, aspectes d'arma i títols nous (s'afegeixen als de dades.py)
UNIFORMES_NOUS = {
    "selva": {"nom": "Camuflaje selva", "colors": ((60, 100, 40), (96, 140, 60), (44, 70, 34))},
    "xylos": {"nom": "Xylothian", "colors": ((110, 50, 140), (170, 90, 210), (80, 34, 100))},
}
APARENCES_NOVES = {
    "neo": {"nom": "Neón", "tint": (255, 90, 210), "bala": (255, 120, 220)},
}
TITOLS_NOUS = {
    "temporada": "Veterano de temporada",
    "cacacaps": "Cazajefes",
    "malson": "Superviviente de la Pesadilla",
    "xenobioleg": "Xenobiólogo",
    "general": "General de Galaxia",
    "mestre": "Maestro de armas",
    "infiltrat": "Infiltrado",
}

# ---------------------------------------------------------------------------
# Battle Pass: 50 nivells per temporada. Els 20 primers són els de sempre.
# XP per pujar del nivell n al n+1 (n comença a 0): 200 + 10·n  ->  ~22.000 XP la temporada sencera
# ---------------------------------------------------------------------------
PASSI_50 = [
    [("monedes", 100)], [("uniforme", "desert")], [("arma", "toxic")], [("titol", "vetera")], [("monedes", 200)],
    [("uniforme", "artic")], [("arma", "plasma")], [("monedes", 300)], [("uniforme", "nocturn")], [("titol", "cacador")],
    [("arma", "infern")], [("monedes", 400)], [("uniforme", "elit")], [("monedes", 500)], [("arma", "arc")],
    [("uniforme", "ciber")], [("monedes", 600)], [("titol", "heroi")], [("arma", "daurat")],
    [("uniforme", "daurat"), ("titol", "llegenda")],
    # 21-30
    [("mira", "verd")], [("efecte", "pixels")], [("monedes", 300)], [("estela", "foc")], [("monedes", 350)],
    [("targeta", "ruines")], [("monedes", 400)], [("mira", "vermell")], [("dron", "bit")], [("monedes", 500)],
    # 31-40
    [("efecte", "gel")], [("monedes", 400)], [("tema", "neo")], [("monedes", 450)], [("targeta", "orbita")],
    [("monedes", 500)], [("estela", "ombra")], [("monedes", 500)], [("uniforme", "selva")], [("tema", "infern")],
    # 41-50
    [("monedes", 550)], [("monedes", 600)], [("efecte", "forat")], [("monedes", 600)], [("dron", "medic")],
    [("estela", "arc")], [("monedes", 700)], [("arma", "neo")], [("monedes", 800)],
    [("targeta", "daurada"), ("titol", "temporada")],
]


def xp_nivell_passi(n):
    """XP que cal per passar del nivell n al n+1 del Battle Pass (n = 0..49)."""
    return 200 + 10 * n


def xp_acumulada_passi(n):
    """XP total per arribar al nivell n."""
    return sum(xp_nivell_passi(k) for k in range(n))


# ---------------------------------------------------------------------------
# Rangs militars (XP total de tota la vida; no s'acaben mai)
# ---------------------------------------------------------------------------
RANGS = [
    {"nom": "Recluta", "xp": 0, "premi": []},
    {"nom": "Soldado", "xp": 300, "premi": [("monedes", 200), ("tema", "militar")]},
    {"nom": "Cabo", "xp": 800, "premi": [("mira", "cian")]},
    {"nom": "Cabo primero", "xp": 1500, "premi": [("monedes", 300)]},
    {"nom": "Sargento", "xp": 2500, "premi": [("estela", "llamp")]},
    {"nom": "Sargento primero", "xp": 4000, "premi": [("targeta", "fortalesa")]},
    {"nom": "Brigada", "xp": 6000, "premi": [("monedes", 500)]},
    {"nom": "Teniente", "xp": 8500, "premi": [("efecte", "electric")]},
    {"nom": "Capitán", "xp": 11500, "premi": [("targeta", "xylos")]},
    {"nom": "Comandante", "xp": 15000, "premi": [("dron", "corb")]},
    {"nom": "Teniente coronel", "xp": 19000, "premi": [("uniforme", "xylos")]},
    {"nom": "Coronel", "xp": 24000, "premi": [("mira", "arc")]},
    {"nom": "General de brigada", "xp": 30000, "premi": [("monedes", 1000)]},
    {"nom": "General", "xp": 37000, "premi": [("tema", "daurat")]},
    {"nom": "General de Galaxia", "xp": 45000, "premi": [("estela", "daurada"), ("titol", "general")]},
]

# ---------------------------------------------------------------------------
# Bestiari: clau = clau de l'enemic (tipus o "boss_N"). "lore" es desbloqueja amb "cal" baixes.
# perill: 1-5 estrelles
# ---------------------------------------------------------------------------
BESTIARI = [
    {"clau": "dron", "nom": "Dron explorador", "perill": 1, "cal": 15,
     "desc": "Vuela en círculos y dispara ráfagas lentas. Débil, pero nunca viene solo.",
     "lore": "Los xylothian los fabrican por millones en las fábricas orbitales. Cada uno transmite lo que ve a la colmena."},
    {"clau": "soldat", "nom": "Soldado xylothian", "perill": 2, "cal": 15,
     "desc": "Patrulla el suelo y apunta antes de disparar: cuando brilla, salta o rueda.",
     "lore": "Criados en cubas de la colmena. No sienten miedo, solo la voz de la Mente que les ordena avanzar."},
    {"clau": "kamikaze", "nom": "Kamikaze", "perill": 2, "cal": 12,
     "desc": "Corre hacia ti y explota. Mátalo de lejos o esquívalo con una voltereta.",
     "lore": "Llevan en el pecho un saco de plasma inestable. Para ellos, explotar cerca del enemigo es un honor."},
    {"clau": "escut", "nom": "Escudero", "perill": 3, "cal": 12,
     "desc": "Su escudo de energía para las balas de frente. Dispárale por la espalda.",
     "lore": "Los escudos se cargan con el latido del portador. Por eso solo protegen lo que tienen delante."},
    {"clau": "cacador", "nom": "Cazador", "perill": 3, "cal": 12,
     "desc": "Se queda quieto, carga y embiste en línea recta. Apártate cuando lo veas brillar.",
     "lore": "Antes eran bestias salvajes de Xylos. La colmena las domesticó y les injertó propulsores."},
    {"clau": "lloctinent", "nom": "Dron lugarteniente", "perill": 3, "cal": 10,
     "desc": "Un dron más grande y resistente que dispara en abanico y coordina a los demás.",
     "lore": "Cada lugarteniente dirige un enjambre. Si cae, los drones de su escuadra dudan un instante."},
    {"clau": "boss_0", "nom": "General Xylothian", "perill": 4, "cal": 3,
     "desc": "Jefe de las ruinas. Lanza ráfagas en abanico y llama a drones cuando se enfada.",
     "lore": "Dirigió la primera oleada de la invasión. Se ganó el rango arrasando tres ciudades en una noche."},
    {"clau": "boss_1", "nom": "Maestro de la Selva", "perill": 4, "cal": 3,
     "desc": "Jefe de la selva tecnológica. Más rápido y con más vida que el General.",
     "lore": "Biólogo de la colmena. Fue él quien convirtió la selva en un laboratorio lleno de esporas."},
    {"clau": "boss_2", "nom": "Comandante de Élite", "perill": 4, "cal": 3,
     "desc": "Guardián del patio de la fortaleza. Sus ráfagas cubren media pantalla.",
     "lore": "Guardaespaldas personal del Comandante Supremo. Nunca ha perdido un duelo... hasta ahora."},
    {"clau": "boss_3", "nom": "Capitán orbital", "perill": 4, "cal": 3,
     "desc": "Aparece en Supervivencia y en Jefes seguidos. Muy resistente.",
     "lore": "Patrulla el casco exterior de la Nave Nodriza. Sus tripulantes dicen que nunca duerme."},
    {"clau": "boss_4", "nom": "Guardián de la Colmena", "perill": 5, "cal": 3,
     "desc": "Vigila la entrada a la cámara del Núcleo bajo el campo supresor.",
     "lore": "Nació dentro de la colmena y nunca ha salido de ella. Conoce cada túnel de Xylos."},
    {"clau": "final_comandant", "nom": "Comandante Supremo", "perill": 5, "cal": 2,
     "desc": "Jefe final del sector 3. Anillos de balas, invocaciones y una furia que da miedo.",
     "lore": "La voz de la Mente en la Tierra. Sus tentáculos controlan a cientos de soldados a la vez."},
    {"clau": "final_nau", "nom": "Nave Nodriza", "perill": 5, "cal": 2,
     "desc": "Cortinas de balas desde tres cañones. Cuando se enfada llama a drones y cazadores.",
     "lore": "Una conciencia viva fundida con el metal. Ha devorado cien mundos antes que la Tierra."},
    {"clau": "final_nucli", "nom": "Núcleo de Xylos", "perill": 5, "cal": 2,
     "desc": "El corazón de la colmena. Sus anillos de balas tienen un hueco: búscalo.",
     "lore": "El origen de todo. Mientras el Núcleo late, cada xylothian del universo oye su voz."},
]

# ---------------------------------------------------------------------------
# Desafiaments que s'obren amb estrelles
# ---------------------------------------------------------------------------
DESAFIAMENTS = {
    "secret": {"nom": "Sector secreto", "sub": "Laboratorio X-0", "estrelles": 15, "fons": (1, 1), "nivell": 4,
               "desc": "Un laboratorio escondido donde la colmena prueba sus prototipos. Tres oleadas y un jefe.",
               "premi": [("dron", "sonda"), ("titol", "infiltrat"), ("monedes", 1000)], "xp": 400,
               "onades": [[("soldat", 120), ("soldat", 120), ("escut", 180), ("dron", 130), ("dron", 130)],
                          [("lloctinent", 220), ("cacador", 100), ("cacador", 100), ("kamikaze", 60), ("kamikaze", 60)],
                          [("boss", 900, 3), ("escut", 180), ("kamikaze", 60)]],
               "noms": ["PROTOTIPO X-0"], "plataformes": [(108, 390, 192), (360, 300, 240), (672, 390, 192), (420, 200, 120)],
               "musica": "jefe"},
    "rush": {"nom": "Jefes seguidos", "sub": "Todos los jefes, uno tras otro", "estrelles": 30, "fons": (3, 2), "nivell": 4,
             "desc": "Ocho jefes seguidos sin salir. Entre jefe y jefe recuperas 40 de vida y la munición.",
             "premi": [("efecte", "daurat"), ("titol", "cacacaps"), ("monedes", 1500)], "xp": 800,
             "onades": [[("boss", 500, 0)], [("boss", 650, 1)], [("boss", 800, 2)], [("boss", 900, 3)], [("boss", 1000, 4)],
                        [("final_comandant", 1300)], [("final_nau", 1800)], [("final_nucli", 2200)]],
             "noms": ["GENERAL XYLOTHIAN", "MAESTRO DE LA SELVA", "COMANDANTE DE ÉLITE", "CAPITÁN ORBITAL",
                      "GUARDIÁN DE LA COLMENA", "COMANDANTE SUPREMO", "NAVE NODRIZA XYLOTHIAN", "NÚCLEO DE XYLOS"],
             "plataformes": [(84, 380, 168), (312, 300, 144), (528, 230, 168), (756, 360, 144)], "musica": "boss_final"},
    "malson": {"nom": "Pesadilla", "sub": "El Núcleo, más fuerte que nunca", "estrelles": 45, "fons": (4, 2),
               "nivell": 4, "desc": "El Núcleo con el doble de vida, más daño y más balas. Solo para quien tiene las 45 estrellas.",
               "premi": [("dron", "daurat"), ("titol", "malson"), ("monedes", 2500)], "xp": 1200,
               "onades": [[("final_nucli", 4400)]], "noms": ["NÚCLEO DE XYLOS · PESADILLA"],
               "plataformes": [(132, 400, 180), (384, 320, 180), (648, 240, 192)], "musica": "boss_final",
               "dificultat": {"nom": "Pesadilla", "vida": 1.0, "dany": 1.6, "cadencia": 0.75, "monedes": 1.5}},
}

# ---------------------------------------------------------------------------
# Reptes diaris: (tipus, objectiu, text). {n} = objectiu, {a} = arma o enemic
# ---------------------------------------------------------------------------
REPTES_POOL = [
    ("baixes", 40, "Elimina {n} enemigos"),
    ("baixes", 80, "Elimina {n} enemigos"),
    ("baixes_arma", 25, "Elimina {n} enemigos con {a}"),
    ("baixes_tipus", 10, "Elimina {n} enemigos del tipo: {a}"),
    ("escenaris", 3, "Completa {n} escenarios"),
    ("sense_dany", 1, "Completa un escenario sin recibir daño"),
    ("tres_estrelles", 1, "Completa un escenario consiguiendo las 3 estrellas"),
    ("onada", 6, "Llega a la oleada {n} en Supervivencia"),
    ("voltes", 25, "Haz {n} volteretas"),
    ("caps", 1, "Derrota a un jefe"),
    ("objectes", 8, "Recoge {n} objetos (vida o munición)"),
]
PREMI_REPTE = (200, 150)          # monedes, XP per repte
PREMI_TOTS_REPTES = 300           # monedes extra si fas els tres

# Logros: XP segons la categoria
XP_LOGRO = {"bronze": 50, "plata": 150, "or": 300, "plati": 600}

# Repetir un escenari ja completat dona aquesta fracció de monedes
MONEDES_REPETICIO = 0.5
