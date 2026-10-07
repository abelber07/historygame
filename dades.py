"""
Dades del joc: armes, enemics, nivells, història, millores i passi de batalla.
Aquest mòdul no depèn de pygame, així es pot llegir i equilibrar fàcilment.

Els requisits d'història ("req") són l'índex de l'escenari que cal haver completat:
0 = 1-1, 1 = 1-2, 2 = 1-3, 3 = 2-1 ... 14 = 5-3. El valor -1 vol dir sense requisit.
"""

NUM_SECTORS = 5


def nom_escenari(index):
    return f"{index // 3 + 1}-{index % 3 + 1}"


# ---------------------------------------------------------------------------
# Armes. "potencia" (1-5) decideix en quins escenaris es poden fer servir.
# ---------------------------------------------------------------------------
ARMES = [
    {"id": "pistola", "nom": "Pistola", "dany": 5, "bales_max": 20, "cost": 0, "req": -1, "potencia": 1,
     "cadencia": 10, "auto": False, "vel": 12, "dispersio": 1.0, "perdigons": 1, "obertura": 0,
     "vida_bala": None, "perfora": False, "so": "pistola", "estil": "pistola",
     "desc": "Lleugera i fiable."},
    {"id": "escopeta", "nom": "Escopeta", "dany": 6, "bales_max": 12, "cost": 500, "req": 1, "potencia": 2,
     "cadencia": 34, "auto": False, "vel": 12, "dispersio": 3.0, "perdigons": 6, "obertura": 26,
     "vida_bala": 30, "perfora": False, "so": "escopeta", "estil": "escopeta",
     "desc": "Sis perdigons. Devastadora a prop."},
    {"id": "fusell", "nom": "Fusell", "dany": 15, "bales_max": 30, "cost": 900, "req": 2, "potencia": 3,
     "cadencia": 9, "auto": True, "vel": 15, "dispersio": 2.0, "perdigons": 1, "obertura": 0,
     "vida_bala": None, "perfora": False, "so": "fusell", "estil": "fusell",
     "desc": "Automàtic i precís."},
    {"id": "minigun", "nom": "Minigun", "dany": 25, "bales_max": None, "cost": 1800, "req": 6, "potencia": 4,
     "cadencia": 6, "auto": True, "vel": 14, "dispersio": 5.0, "perdigons": 1, "obertura": 0,
     "vida_bala": None, "perfora": False, "so": "minigun", "estil": "minigun",
     "desc": "Munició infinita. Arma pesada."},
    {"id": "plasma", "nom": "Canó de plasma", "dany": 40, "bales_max": 24, "cost": 3000, "req": 10, "potencia": 5,
     "cadencia": 16, "auto": True, "vel": 16, "dispersio": 0.5, "perdigons": 1, "obertura": 0,
     "vida_bala": None, "perfora": True, "so": "plasma", "estil": "plasma",
     "desc": "Travessa els enemics. Tecnologia Xylothian."},
]
ARMA_PER_ID = {a["id"]: i for i, a in enumerate(ARMES)}

# Potència màxima permesa a cada escenari i el motiu (si n'hi ha) que es mostra al jugador
POTENCIA_MAX = {
    (0, 0): 2, (0, 1): 2, (0, 2): 3,
    (1, 0): 3, (1, 1): 2, (1, 2): 3,
    (2, 0): 4, (2, 1): 3, (2, 2): 4,
    (3, 0): 4, (3, 1): 4, (3, 2): 5,
    (4, 0): 5, (4, 1): 3, (4, 2): 5,
}
MOTIUS_RESTRICCIO = {
    (0, 0): "Ruïnes inestables: les armes pesades farien caure els edificis.",
    (0, 1): "Ruïnes inestables: les armes pesades farien caure els edificis.",
    (1, 1): "Gas inflamable al laboratori: res més potent que l'escopeta.",
    (2, 1): "Infiltració: cal avançar sense fer soroll.",
    (4, 1): "Camp supressor del rusc: les armes pesades no funcionen.",
}

# ---------------------------------------------------------------------------
# Enemics
# ---------------------------------------------------------------------------
TIPUS_ENEMIC = {
    "dron":            {"cadencia": 100, "dany": 5, "dany_nivell": 2, "vel_bala": 6.5, "monedes": 50, "vel": 2.6, "xp": 10},
    "lloctinent":      {"cadencia": 85, "dany": 8, "dany_nivell": 2, "vel_bala": 7.0, "monedes": 100, "vel": 2.2, "xp": 20},
    "cacador":         {"cadencia": 150, "dany": 12, "dany_nivell": 1, "vel_bala": 0, "monedes": 70, "vel": 3.2, "xp": 15},
    "boss":            {"cadencia": 66, "dany": 10, "dany_nivell": 2, "vel_bala": 7.0, "monedes": 250, "vel": 2.0, "xp": 60},
    "final_comandant": {"cadencia": 90, "dany": 10, "dany_nivell": 0, "vel_bala": 5.5, "monedes": 500, "vel": 1.5, "xp": 150},
    "final_nau":       {"cadencia": 75, "dany": 12, "dany_nivell": 0, "vel_bala": 5.0, "monedes": 800, "vel": 1.2, "xp": 200},
    "final_nucli":     {"cadencia": 7, "dany": 14, "dany_nivell": 0, "vel_bala": 3.6, "monedes": 1200, "vel": 0, "xp": 300},
}

NOMS_SECTORS = ["Ruïnes Urbanes", "Selva Tecnològica", "Fortalesa Xylothian",
                "Òrbita: la Nau Mare", "Xylos, el Món Rusc"]
NOMS_CAPS = {
    (0, 2): "GENERAL XYLOTHIAN",
    (1, 2): "MESTRE DE LA SELVA",
    (2, 1): "COMANDANT D'ELIT",
    (2, 2): "COMANDANT SUPREM",
    (3, 2): "NAU MARE XYLOTHIAN",
    (4, 1): "GUARDIÀ DEL RUSC",
    (4, 2): "NUCLI DE XYLOS",
}

# Plataformes: (x, y_superior, amplada). Enemics: (tipus, vida)
_P1 = [(100, 450, 150), (300, 350, 150), (500, 250, 150)]
_P2 = [(150, 450, 150), (350, 350, 150), (550, 250, 150)]
_P_ORBITA = [(70, 440, 140), (260, 360, 120), (440, 290, 140), (630, 420, 120)]
_P_XYLOS = [(110, 460, 150), (320, 380, 150), (540, 300, 160)]
NIVELLS = {
    (0, 0): {"plataformes": _P1, "enemics": [("dron", 30)] * 2},
    (0, 1): {"plataformes": [(150, 450, 150), (350, 350, 150), (550, 400, 150)],
             "enemics": [("dron", 30)] * 3 + [("lloctinent", 60)]},
    (0, 2): {"plataformes": _P1, "enemics": [("boss", 100)]},
    (1, 0): {"plataformes": [(150, 450, 150), (350, 350, 200), (550, 250, 150)], "enemics": [("dron", 50)] * 2},
    (1, 1): {"plataformes": _P1, "enemics": [("dron", 50)] * 3 + [("lloctinent", 100)]},
    (1, 2): {"plataformes": _P2, "enemics": [("boss", 200)]},
    (2, 0): {"plataformes": _P1, "enemics": [("dron", 80)] * 2},
    (2, 1): {"plataformes": _P2, "enemics": [("dron", 80)] * 2 + [("boss", 250)]},
    (2, 2): {"plataformes": _P1, "enemics": [("final_comandant", 1200)]},
    (3, 0): {"plataformes": _P_ORBITA, "enemics": [("dron", 100)] * 2 + [("cacador", 60)] * 2},
    (3, 1): {"plataformes": [(90, 450, 160), (300, 340, 200), (560, 420, 160)],
             "enemics": [("cacador", 70)] * 3 + [("dron", 100), ("lloctinent", 160)]},
    (3, 2): {"plataformes": _P_ORBITA, "enemics": [("final_nau", 1800)]},
    (4, 0): {"plataformes": _P_XYLOS, "enemics": [("dron", 120)] * 2 + [("cacador", 80)] * 2 + [("lloctinent", 180)]},
    (4, 1): {"plataformes": [(140, 450, 140), (340, 360, 120), (520, 450, 140)],
             "enemics": [("boss", 450), ("cacador", 80), ("cacador", 80)]},
    (4, 2): {"plataformes": _P_XYLOS, "enemics": [("final_nucli", 2400)]},
}

MUSICA_SECTOR = ["menu", "sector2", "sector3", "sector3", "sector2"]
CAPS_FINALS = {(2, 2), (3, 2), (4, 2)}

# ---------------------------------------------------------------------------
# Història
# ---------------------------------------------------------------------------
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
            "Aquest és l'últim enfrontament, Nexus. La humanitat depèn de tu... o això creus.",
    (3, 0): "El Comandant Suprem ha caigut, però abans de morir ha enviat un senyal a l'òrbita. Sobre la Terra "
            "s'ha obert una ombra immensa: la Nau Mare Xylothian. Amb una llançadora robada de la fortalesa, "
            "Nexus s'enlaira cap a les estrelles.",
    (3, 1): "Els hangars de la Nau Mare bullen de caçadors, drons que ataquen en picat. Els enginyers Xylothians "
            "preparen un raig capaç de convertir ciutats senceres en cendra. Atura'ls abans que estigui carregat.",
    (3, 2): "Al pont de comandament t'espera la Nau Mare en persona: una consciència viva fusionada amb el metall. "
            "Si cau, la flota quedarà sense ordres... i el camí cap al seu món quedarà obert.",
    (4, 0): "Les restes de la Nau Mare revelen la veritat: tots els Xylothians obeeixen una sola ment, el Nucli de "
            "Xylos. Nexus creua l'últim portal i arriba a un planeta de cel violeta i dos sols moribunds.",
    (4, 1): "Al cor del rusc, un camp supressor bloqueja les armes més potents. El Guardià del Rusc vigila "
            "l'entrada a la cambra del Nucli. Només els teus reflexos et poden portar més enllà.",
    (4, 2): "El Nucli de Xylos obre el seu ull immens. Milers d'anys de conquestes, centenars de mons absorbits. "
            "Avui, per primera vegada, algú ha arribat fins aquí. Acaba-ho, Nexus.",
}
TEXT_VICTORIA = ("El Nucli de Xylos s'apaga i el rusc sencer cau en silenci. Sense la seva ment, els Xylothians de "
                 "tota la galàxia deixen de lluitar. Nexus torna a la Terra a bord d'una nau alienígena: l'heroi que "
                 "va tancar els portals per sempre. La humanitat pot reconstruir-se... i, aquesta vegada, mirar les "
                 "estrelles sense por.")
TEXT_DERROTA = "Has caigut en combat. Els Xylothians avancen. Què faràs, Nexus?"

# Arxiu: una entrada per sector, es desbloqueja en completar-lo
ARXIU = [
    ("Els Xylothians",
     "Espècie col·lectiva originària del planeta Xylos. Cap individu pensa per si mateix: tots són extensions "
     "d'una sola ment. Van arribar a la Terra l'any 2139 a través de portals de plegament i en vuit anys van "
     "fer caure totes les capitals."),
    ("La tecnologia viva",
     "Els Xylothians no construeixen: fan créixer. Les seves màquines són organismes modificats que s'alimenten "
     "de la biosfera dels mons que envaeixen. La Selva Tecnològica era una granja: estaven convertint la Terra "
     "en una peça més del rusc."),
    ("Projecte NEXUS",
     "Última iniciativa de l'Exèrcit Unificat. Un soldat voluntari amb implants que el fan immune al senyal "
     "mental Xylothian. Era l'únic que podia acostar-se als seus caps sense ser dominat. Ningú no esperava que "
     "tornés."),
    ("La Nau Mare",
     "Vaixell-ciutat de dotze quilòmetres que fa de pont entre el Nucli i les colònies. Sense ella, els "
     "Xylothians de la Terra no podien rebre ordres: per això el Comandant Suprem la va cridar quan es va "
     "veure perdut."),
    ("El Nucli de Xylos",
     "Una consciència nascuda fa milers d'anys que ha absorbit centenars de civilitzacions. Cada món conquerit "
     "li afegia milions de veus. La Terra havia de ser la següent. Ara només en queda el silenci."),
]

# ---------------------------------------------------------------------------
# Millores de la botiga (cada nivell té un cost i un requisit d'història)
# ---------------------------------------------------------------------------
MILLORES = [
    {"id": "blindatge", "nom": "Blindatge", "desc": "+20 de vida màxima per nivell",
     "costos": [300, 700, 1400], "req": [0, 4, 9]},
    {"id": "potencia", "nom": "Potència", "desc": "+15% de dany amb totes les armes",
     "costos": [400, 900, 1600], "req": [1, 5, 10]},
    {"id": "carregadors", "nom": "Carregadors", "desc": "+30% de munició màxima",
     "costos": [250, 600, 1200], "req": [0, 3, 8]},
    {"id": "iman", "nom": "Imant", "desc": "Atrau els ítems des de més lluny",
     "costos": [200, 500, 1000], "req": [2, 5, 8]},
    {"id": "reflexos", "nom": "Reflexos", "desc": "Més velocitat i invulnerabilitat",
     "costos": [300, 700, 1300], "req": [2, 6, 11]},
    {"id": "doble_salt", "nom": "Propulsors", "desc": "Permet fer un doble salt a l'aire",
     "costos": [1500], "req": [8]},
]

# ---------------------------------------------------------------------------
# Aparença (cosmètics) i passi de batalla
# ---------------------------------------------------------------------------
# Uniformes: colors que substitueixen els tres verds oliva de l'uniforme original
UNIFORMES = {
    "classic": {"nom": "Clàssic", "colors": None},
    "desert": {"nom": "Desert", "colors": ((170, 140, 90), (210, 184, 124), (150, 120, 80))},
    "artic": {"nom": "Àrtic", "colors": ((196, 202, 214), (236, 240, 248), (160, 172, 190))},
    "nocturn": {"nom": "Operacions nocturnes", "colors": ((46, 52, 64), (74, 80, 98), (36, 40, 52))},
    "elit": {"nom": "Elit vermell", "colors": ((150, 30, 34), (204, 52, 44), (110, 22, 28))},
    "ciber": {"nom": "Cibernètic", "colors": ((28, 118, 150), (64, 220, 255), (20, 80, 110))},
    "daurat": {"nom": "Daurat", "colors": ((190, 148, 30), (255, 214, 64), (160, 118, 20))},
}
# Aparences d'arma: tint del metall i color de les bales ("arc" = arc de Sant Martí)
APARENCES_ARMA = {
    "estandard": {"nom": "Estàndard", "tint": None, "bala": None},
    "toxic": {"nom": "Tòxic", "tint": (90, 220, 90), "bala": (130, 255, 90)},
    "plasma": {"nom": "Plasma blau", "tint": (90, 170, 255), "bala": (110, 200, 255)},
    "infern": {"nom": "Infern", "tint": (230, 90, 40), "bala": (255, 110, 40)},
    "arc": {"nom": "Arc de Sant Martí", "tint": (200, 120, 255), "bala": "arc"},
    "daurat": {"nom": "Daurat", "tint": (255, 200, 60), "bala": (255, 220, 80)},
}
TITOLS = {
    "recluta": "Recluta",
    "vetera": "Veterà",
    "cacador": "Caçador d'aliens",
    "heroi": "Heroi de la Terra",
    "llegenda": "Llegenda de Xylos",
}

XP_PER_NIVELL = 200
XP_ESCENARI = 40
XP_PRIMERA_VEGADA = 60
# Cada nivell del passi: llista de recompenses (tipus, valor)
PASSI = [
    [("monedes", 100)],
    [("uniforme", "desert")],
    [("arma", "toxic")],
    [("titol", "vetera")],
    [("monedes", 200)],
    [("uniforme", "artic")],
    [("arma", "plasma")],
    [("monedes", 300)],
    [("uniforme", "nocturn")],
    [("titol", "cacador")],
    [("arma", "infern")],
    [("monedes", 400)],
    [("uniforme", "elit")],
    [("monedes", 500)],
    [("arma", "arc")],
    [("uniforme", "ciber")],
    [("monedes", 600)],
    [("titol", "heroi")],
    [("arma", "daurat")],
    [("uniforme", "daurat"), ("titol", "llegenda")],
]


def nom_recompensa(tipus, valor):
    if tipus == "monedes":
        return f"{valor} monedes"
    if tipus == "uniforme":
        return f"Uniforme {UNIFORMES[valor]['nom']}"
    if tipus == "arma":
        return f"Aparença d'arma {APARENCES_ARMA[valor]['nom']}"
    return f"Títol: {TITOLS[valor]}"
