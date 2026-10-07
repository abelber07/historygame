"""
Datos del juego: armas, enemigos, niveles, historia, mejoras y Battle Pass.
Este módulo no depende de pygame, así se puede leer y equilibrar fácilmente.
(Los nombres de las variables siguen en catalán, como en el resto del código.)

Los requisitos de historia ("req") son el índice del escenario que hay que haber completado:
0 = 1-1, 1 = 1-2, 2 = 1-3, 3 = 2-1 ... 14 = 5-3. El valor -1 significa sin requisito.
"""

from idiomes import T

NUM_SECTORS = 5


def nom_escenari(index):
    return f"{index // 3 + 1}-{index % 3 + 1}"


# ---------------------------------------------------------------------------
# Armas. "potencia" (1-5) decide en qué escenarios se pueden usar.
# ---------------------------------------------------------------------------
ARMES = [
    {"id": "pistola", "nom": "Pistola", "dany": 5, "bales_max": 20, "cost": 0, "req": -1, "potencia": 1,
     "cadencia": 10, "auto": False, "vel": 12, "dispersio": 1.0, "perdigons": 1, "obertura": 0,
     "vida_bala": None, "perfora": False, "so": "pistola", "estil": "pistola",
     "desc": "Ligera y fiable."},
    {"id": "escopeta", "nom": "Escopeta", "dany": 6, "bales_max": 12, "cost": 500, "req": 1, "potencia": 2,
     "cadencia": 34, "auto": False, "vel": 12, "dispersio": 3.0, "perdigons": 6, "obertura": 26,
     "vida_bala": 30, "perfora": False, "so": "escopeta", "estil": "escopeta",
     "desc": "Seis perdigones. Devastadora de cerca."},
    {"id": "fusell", "nom": "Fusil", "dany": 15, "bales_max": 30, "cost": 900, "req": 2, "potencia": 3,
     "cadencia": 9, "auto": True, "vel": 15, "dispersio": 2.0, "perdigons": 1, "obertura": 0,
     "vida_bala": None, "perfora": False, "so": "fusell", "estil": "fusell",
     "desc": "Automático y preciso."},
    {"id": "minigun", "nom": "Minigun", "dany": 25, "bales_max": None, "cost": 1800, "req": 6, "potencia": 4,
     "cadencia": 6, "auto": True, "vel": 14, "dispersio": 5.0, "perdigons": 1, "obertura": 0,
     "vida_bala": None, "perfora": False, "so": "minigun", "estil": "minigun",
     "desc": "Munición infinita. Arma pesada."},
    {"id": "plasma", "nom": "Cañón de plasma", "dany": 40, "bales_max": 24, "cost": 3000, "req": 10, "potencia": 5,
     "cadencia": 16, "auto": True, "vel": 16, "dispersio": 0.5, "perdigons": 1, "obertura": 0,
     "vida_bala": None, "perfora": True, "so": "plasma", "estil": "plasma",
     "desc": "Atraviesa a los enemigos. Tecnología Xylothian."},
]
ARMA_PER_ID = {a["id"]: i for i, a in enumerate(ARMES)}

# Potencia máxima permitida en cada escenario y el motivo (si lo hay) que se muestra al jugador
POTENCIA_MAX = {
    (0, 0): 2, (0, 1): 2, (0, 2): 3,
    (1, 0): 3, (1, 1): 2, (1, 2): 3,
    (2, 0): 4, (2, 1): 3, (2, 2): 4,
    (3, 0): 4, (3, 1): 4, (3, 2): 5,
    (4, 0): 5, (4, 1): 3, (4, 2): 5,
}
MOTIUS_RESTRICCIO = {
    (0, 0): "Ruinas inestables: las armas pesadas derrumbarían los edificios.",
    (0, 1): "Ruinas inestables: las armas pesadas derrumbarían los edificios.",
    (1, 1): "Gas inflamable en el laboratorio: nada más potente que la escopeta.",
    (2, 1): "Infiltración: hay que avanzar sin hacer ruido.",
    (4, 1): "Campo supresor de la colmena: las armas pesadas no funcionan.",
}

# ---------------------------------------------------------------------------
# Enemigos
# ---------------------------------------------------------------------------
TIPUS_ENEMIC = {
    "dron":            {"cadencia": 100, "dany": 5, "dany_nivell": 2, "vel_bala": 6.5, "monedes": 50, "vel": 2.6, "xp": 10},
    "lloctinent":      {"cadencia": 85, "dany": 8, "dany_nivell": 2, "vel_bala": 7.0, "monedes": 100, "vel": 2.2, "xp": 20},
    "cacador":         {"cadencia": 150, "dany": 12, "dany_nivell": 1, "vel_bala": 0, "monedes": 70, "vel": 3.2, "xp": 15},
    # enemigos de suelo: caminan por el suelo y las plataformas
    "soldat":          {"cadencia": 120, "dany": 6, "dany_nivell": 2, "vel_bala": 6.5, "monedes": 60, "vel": 1.3, "xp": 12},
    "escut":           {"cadencia": 150, "dany": 8, "dany_nivell": 2, "vel_bala": 6.0, "monedes": 90, "vel": 0.7, "xp": 20},
    "kamikaze":        {"cadencia": 999, "dany": 18, "dany_nivell": 3, "vel_bala": 0, "monedes": 40, "vel": 2.6, "xp": 10},
    "boss":            {"cadencia": 66, "dany": 10, "dany_nivell": 2, "vel_bala": 7.0, "monedes": 250, "vel": 2.0, "xp": 60},
    "final_comandant": {"cadencia": 90, "dany": 10, "dany_nivell": 0, "vel_bala": 5.5, "monedes": 500, "vel": 1.5, "xp": 150},
    "final_nau":       {"cadencia": 75, "dany": 12, "dany_nivell": 0, "vel_bala": 5.0, "monedes": 800, "vel": 1.2, "xp": 200},
    "final_nucli":     {"cadencia": 7, "dany": 14, "dany_nivell": 0, "vel_bala": 3.6, "monedes": 1200, "vel": 0, "xp": 300},
}
ENEMICS_TERRA = {"soldat", "escut", "kamikaze"}

NOMS_SECTORS = ["Ruinas Urbanas", "Selva Tecnológica", "Fortaleza Xylothian",
                "Órbita: la Nave Nodriza", "Xylos, el Mundo Colmena"]
NOMS_CAPS = {
    (0, 2): "GENERAL XYLOTHIAN",
    (1, 2): "MAESTRO DE LA SELVA",
    (2, 1): "COMANDANTE DE ÉLITE",
    (2, 2): "COMANDANTE SUPREMO",
    (3, 2): "NAVE NODRIZA XYLOTHIAN",
    (4, 1): "GUARDIÁN DE LA COLMENA",
    (4, 2): "NÚCLEO DE XYLOS",
}

# Cada escenario:
#   plataformes: (x, y_superior, anchura) en la pantalla de 960x540 (el suelo está en y=490)
#   mobils: {índice de plataforma: (amplitud_x, amplitud_y, periodo en fotogramas)}
#   fragils: índices de plataformas que se rompen si te quedas encima
#   onades: oleadas de enemigos (tipo, vida); la siguiente llega cuando no queda ninguno
#   perills: peligros del escenario (ver main.py, clase Perills)
#   temps: segundos para conseguir la estrella de rapidez
_P1 = [(120, 390, 180), (360, 290, 180), (600, 190, 180)]
_P2 = [(180, 390, 180), (420, 290, 180), (660, 190, 180)]
_P_ORBITA = [(84, 380, 168), (312, 300, 144), (528, 230, 168), (756, 360, 144)]
_P_XYLOS = [(132, 400, 180), (384, 320, 180), (648, 240, 192)]
NIVELLS = {
    (0, 0): {"plataformes": _P1, "temps": 75,
             "onades": [[("dron", 30)] * 2, [("soldat", 30)] * 2]},
    (0, 1): {"plataformes": [(180, 390, 180), (420, 290, 180), (660, 340, 180)], "temps": 110,
             "onades": [[("dron", 30)] * 2 + [("soldat", 30)], [("lloctinent", 60), ("soldat", 30), ("soldat", 30)]],
             "perills": [("runa", 200)]},
    (0, 2): {"plataformes": _P1, "temps": 100,
             "onades": [[("boss", 100), ("soldat", 30)]], "perills": [("runa", 260)]},
    (1, 0): {"plataformes": [(180, 390, 180), (420, 290, 240), (660, 190, 180)], "temps": 110,
             "onades": [[("dron", 50)] * 2, [("soldat", 50), ("soldat", 50), ("kamikaze", 30)]],
             "perills": [("acid", [(330, 80), (590, 90)])]},
    (1, 1): {"plataformes": _P1, "temps": 140,
             "onades": [[("dron", 50)] * 2 + [("kamikaze", 30)], [("lloctinent", 100), ("soldat", 50), ("soldat", 50)]],
             "perills": [("gas", [(310, 70), (840, 70)], 330)]},
    (1, 2): {"plataformes": _P2, "temps": 130, "fragils": [0],
             "onades": [[("boss", 200), ("kamikaze", 30), ("kamikaze", 30)]],
             "perills": [("acid", [(430, 100)])]},
    (2, 0): {"plataformes": _P1, "temps": 120,
             "onades": [[("dron", 80)] * 2 + [("soldat", 70)], [("escut", 110), ("soldat", 70), ("soldat", 70)]],
             "perills": [("morter", 230)]},
    (2, 1): {"plataformes": _P2, "temps": 160,
             "onades": [[("soldat", 70), ("soldat", 70), ("escut", 110)], [("dron", 80), ("dron", 80), ("boss", 250)]],
             "perills": [("electric", [(40, 150), (400, 150), (760, 150)], 300)]},
    (2, 2): {"plataformes": _P1, "temps": 150,
             "onades": [[("final_comandant", 1200)]]},
    (3, 0): {"plataformes": _P_ORBITA, "temps": 140, "mobils": {1: (70, 0, 300), 3: (0, 60, 240)},
             "onades": [[("dron", 100)] * 2 + [("cacador", 60)] * 2, [("soldat", 90), ("soldat", 90), ("escut", 140)]]},
    (3, 1): {"plataformes": [(108, 390, 192), (360, 280, 240), (672, 360, 192)], "temps": 160,
             "onades": [[("cacador", 70)] * 3 + [("dron", 100)], [("lloctinent", 160), ("escut", 140), ("soldat", 90), ("soldat", 90)]],
             "perills": [("electric", [(0, 130), (300, 160), (620, 130)], 280)]},
    (3, 2): {"plataformes": _P_ORBITA, "temps": 180, "mobils": {0: (40, 0, 260), 2: (60, 0, 320)},
             "onades": [[("final_nau", 1800)]]},
    (4, 0): {"plataformes": _P_XYLOS, "temps": 160, "fragils": [0, 2],
             "onades": [[("dron", 120)] * 2 + [("cacador", 80)] * 2,
                        [("lloctinent", 180), ("soldat", 110), ("soldat", 110), ("kamikaze", 50), ("kamikaze", 50)]]},
    (4, 1): {"plataformes": [(168, 390, 168), (408, 300, 144), (624, 390, 168)], "temps": 170,
             "onades": [[("escut", 170), ("soldat", 110), ("soldat", 110), ("kamikaze", 50)],
                        [("boss", 450), ("cacador", 80), ("cacador", 80)]],
             "perills": [("acid", [(40, 110), (820, 110)])]},
    (4, 2): {"plataformes": _P_XYLOS, "temps": 200, "fragils": [1],
             "onades": [[("final_nucli", 2400)]]},
}
TEMPS_ESTRELLA = {k: v["temps"] for k, v in NIVELLS.items()}
XP_ESTRELLA = 30

# Dificultad: multiplica la vida, el daño y la cadencia de los enemigos y las monedas que se ganan
DIFICULTATS = {
    "facil": {"nom": "Fácil", "vida": 0.8, "dany": 0.6, "cadencia": 1.25, "monedes": 0.75},
    "normal": {"nom": "Normal", "vida": 1.0, "dany": 1.0, "cadencia": 1.0, "monedes": 1.0},
    "dificil": {"nom": "Difícil", "vida": 1.25, "dany": 1.4, "cadencia": 0.85, "monedes": 1.3},
}

# Música: una pista por sector, otra para los jefes normales, otra para los jefes finales
MUSICA_SECTOR = ["sector1", "sector2", "sector3", "sector4", "sector5"]
CAPS_FINALS = {(2, 2), (3, 2), (4, 2)}
CAPS_NORMALS = {(0, 2), (1, 2), (2, 1), (4, 1)}

# Presentación de los jefes al aparecer: (nombre, subtítulo)
PRESENTACIO_CAPS = {
    (0, 2): ("GENERAL XYLOTHIAN", "Señor de las ruinas"),
    (1, 2): ("MAESTRO DE LA SELVA", "El que hace crecer la jungla"),
    (2, 1): ("COMANDANTE DE ÉLITE", "Guardián del patio interior"),
    (2, 2): ("COMANDANTE SUPREMO", "La voz del enemigo en la Tierra"),
    (3, 2): ("NAVE NODRIZA XYLOTHIAN", "Una mente fundida con el metal"),
    (4, 1): ("GUARDIÁN DE LA COLMENA", "Nadie pasa a la cámara del Núcleo"),
    (4, 2): ("NÚCLEO DE XYLOS", "La mente de un millón de mundos"),
}

# Supervivencia: escenarios que se pueden usar como arena (uno por sector)
ARENES = [(0, 1), (1, 0), (2, 1), (3, 0), (4, 0)]
NOMS_ARENES = ["Ruinas", "Selva", "Fortaleza", "Órbita", "Xylos"]

# ---------------------------------------------------------------------------
# Historia
# ---------------------------------------------------------------------------
# Animación inicial: (escena, texto). Las escenas se dibujan en main.py (clase Intro).
INTRO = [
    ("terra", "Año 2139. Una noche, el cielo de la Tierra se abre: decenas de portales de luz violeta aparecen "
              "sobre las ciudades."),
    ("invasio", "De ellos salen los Xylothians, una especie que no piensa: obedece. Todos sus soldados son "
                "extensiones de una sola mente."),
    ("ruines", "Ocho años de guerra. Las capitales caen una tras otra y los supervivientes se esconden "
               "bajo los escombros."),
    ("nexus", "El ejército crea su última arma: el Proyecto NEXUS. Un soldado con implantes que lo hacen "
              "inmune a la señal mental alienígena."),
    ("despertar", "Año 2147. Nexus despierta en un búnker bajo la ciudad. La humanidad ya no tiene a nadie más. "
                  "Su misión: llegar hasta el corazón de la invasión."),
]

TEXTOS_NARRATIVA = {
    (0, 0): "Nexus sale del búnker a una ciudad que ya no reconoce. Los drones Xylothian patrullan las "
            "ruinas buscando supervivientes. Primera misión: destruir el puesto de vigilancia del barrio norte.",
    (0, 1): "La alarma ha corrido entre los aliens. Bajo la lluvia, los drones refuerzan las ruinas y sus "
            "lugartenientes dirigen la búsqueda. Elimínalos antes de que localicen el búnker.",
    (0, 2): "Un General Xylothian ha levantado una base sobre el antiguo centro de la ciudad. Desde allí "
            "controla todo el sector. Derríbalo y el camino hacia el sur quedará abierto.",
    (1, 0): "Al sur, donde había bosques, ahora crece la Selva Tecnológica: plantas y máquinas fusionadas. "
            "Los Xylothians no construyen, cultivan. Y están cultivando la Tierra.",
    (1, 1): "En medio de la selva se esconde un laboratorio alienígena lleno de criaturas en tanques. "
            "El aire está cargado de gas inflamable: cuidado con lo que disparas.",
    (1, 2): "El Maestro de la Selva, el bio-constructor que hace crecer esta jungla, protege su corazón. "
            "Si cae, la selva dejará de avanzar y la fortaleza quedará al descubierto.",
    (2, 0): "La Fortaleza Xylothian se alza sobre las montañas: murallas de energía, reflectores y "
            "legiones de élite. Desde aquí se dirige toda la invasión del continente.",
    (2, 1): "Has entrado por las cloacas. Para cruzar el patio interior tendrás que moverte en silencio "
            "y eliminar al Comandante de Élite que vigila la segunda línea.",
    (2, 2): "En la cima de la fortaleza espera el Comandante Supremo, la voz del enemigo en la Tierra. "
            "Si cae, los Xylothians quedarán sin líder... o eso cree Nexus.",
    (3, 0): "La lanzadera atraca en el casco exterior de la Nave Nodriza. Alrededor flotan los restos de los "
            "satélites que derribaron en 2139. Abre camino hacia los hangares.",
    (3, 1): "Los hangares de la Nave Nodriza están llenos de cazadores, drones que atacan en picado. "
            "Los ingenieros cargan un rayo capaz de arrasar ciudades enteras. Hay que detenerlos.",
    (3, 2): "En el puente de mando te espera la Nave Nodriza en persona: una conciencia viva fundida con "
            "el metal. Si cae, la flota se quedará sin órdenes y el portal hacia su mundo quedará abierto.",
    (4, 0): "Al otro lado del portal, un planeta de cielo violeta. Los restos de la Nave Nodriza revelaron la "
            "verdad: todos los Xylothians obedecen a una sola mente, el Núcleo de Xylos. Y está aquí.",
    (4, 1): "En el corazón de la colmena, un campo supresor bloquea las armas pesadas. El Guardián de la "
            "Colmena vigila la entrada a la cámara del Núcleo. Solo tus reflejos te llevarán más allá.",
    (4, 2): "El Núcleo de Xylos abre su ojo inmenso. Miles de años de conquistas, cientos de mundos "
            "absorbidos. Hoy, por primera vez, alguien ha llegado hasta aquí. Acaba con esto, Nexus.",
}

# Cinemáticas al derrotar a cada jefe final: (escena, texto). Las escenas se dibujan en main.py.
CINEMATIQUES = {
    "comandant": [
        ("caiguda", "El Comandante Supremo se desploma sobre la nieve. Con su último aliento, lanza una señal "
                    "hacia el cielo."),
        ("senyal", "La señal cruza la atmósfera. En órbita, una sombra inmensa despierta: la Nave Nodriza."),
        ("llancament", "Nexus corre hasta la rampa de la fortaleza, roba la lanzadera alienígena y despega "
                       "tras ella."),
    ],
    "nau": [
        ("explosio_nau", "La Nave Nodriza se parte en dos. Doce kilómetros de metal vivo arden sobre la Tierra."),
        ("portal", "Entre los restos se abre un portal: el camino a Xylos, su mundo de origen. Nexus no se lo "
                   "piensa dos veces."),
    ],
    "final": [
        ("apagada", "El Núcleo de Xylos se apaga. Por primera vez en mil años, la colmena queda en silencio."),
        ("portals", "En la Tierra, los portales se cierran uno a uno. Sin su mente, los Xylothians dejan de luchar."),
        ("retorn", "Nexus vuelve a casa. Los supervivientes salen de los búnkeres para ver el amanecer."),
        ("fi", "La humanidad puede reconstruirse... y, esta vez, mirar las estrellas sin miedo."),
    ],
}
CINEMATICA_CAP = {(2, 2): "comandant", (3, 2): "nau", (4, 2): "final"}

# Radio durante los escenarios: quién habla (comandant, doctora, nexus, ment) y qué dice.
# "inici" al empezar, "onada" cuando llegan los refuerzos, "cap" cuando el jefe está a media vida.
NOMS_RADIO = {"comandant": "Cmdte. Reyes", "doctora": "Dra. Vega", "nexus": "Nexus", "ment": "???"}
RADIO = {
    (0, 0): {"inici": [("comandant", "Nexus, aquí el comandante Reyes, desde el búnker. Si me oyes, estás vivo."),
                       ("doctora", "Implantes estables. Recuerda: MAYÚS o clic derecho para esquivar rodando.")],
             "onada": [("comandant", "¡Soldados de a pie! Esos caminan y disparan en línea recta. ¡Salta!")]},
    (0, 1): {"inici": [("comandant", "La lluvia no los frena. Y los edificios se caen a trozos: mira al suelo.")],
             "onada": [("nexus", "Más contactos. Esto se pone feo.")]},
    (0, 2): {"inici": [("comandant", "Ahí está el General. Derríbalo y el sector norte será nuestro.")],
             "cap": [("doctora", "¡Está perdiendo energía! Sigue así, Nexus.")]},
    (1, 0): {"inici": [("doctora", "La selva está viva... y ese líquido verde es ácido. No pises los charcos.")],
             "onada": [("comandant", "¡Cuidado con los bichos brillantes! Explotan si se te acercan.")]},
    (1, 1): {"inici": [("doctora", "Esos tanques... están criando soldados. Y las tuberías sueltan gas tóxico.")],
             "onada": [("comandant", "Te han detectado. Llegan refuerzos.")]},
    (1, 2): {"inici": [("comandant", "El Maestro de la Selva. Y esa plataforma podrida no aguantará mucho.")],
             "cap": [("doctora", "¡La selva se marchita! Está perdiendo fuerza.")]},
    (2, 0): {"inici": [("comandant", "Las murallas. Sus morteros te tienen localizado: atento a las marcas.")],
             "onada": [("doctora", "Escudos de energía: por delante no les haces nada. ¡Rodéalos!")]},
    (2, 1): {"inici": [("nexus", "Estoy dentro. El suelo del patio está electrificado a trozos.")],
             "onada": [("comandant", "¡El Comandante de Élite viene a por ti!")],
             "cap": [("comandant", "¡Casi lo tienes!")]},
    (2, 2): {"inici": [("ment", "Humano... ¿Por qué no te arrodillas como los demás?"),
                       ("doctora", "Es él, Nexus: la voz de la mente en la Tierra.")],
             "cap": [("ment", "¡Imposible! ¡La señal no te alcanza!")]},
    (3, 0): {"inici": [("comandant", "Te recibo con interferencias. Estás fuera de la atmósfera, Nexus."),
                       ("doctora", "Esas plataformas son chatarra que flota. Calcula bien los saltos.")],
             "onada": [("nexus", "Han soltado tropas en el casco.")]},
    (3, 1): {"inici": [("doctora", "El suelo del hangar está cargado. Salta en cuanto veas chispas.")],
             "onada": [("comandant", "Están cargando el rayo. ¡No hay tiempo!")]},
    (3, 2): {"inici": [("ment", "Pequeño humano. Esta nave ha devorado cien mundos."),
                       ("comandant", "Pues que la Tierra sea el último.")],
             "cap": [("ment", "¡Flota, a mí! ¡Destruidlo!")]},
    (4, 0): {"inici": [("nexus", "Reyes, ¿me oye? ... Nada. Estoy solo."),
                       ("ment", "Por fin llegas, Nexus. Bienvenido a casa.")],
             "onada": [("ment", "El suelo se rompe bajo tus pies. Como tu especie.")]},
    (4, 1): {"inici": [("ment", "Aquí tus armas no sirven. Aquí solo existo yo.")],
             "onada": [("nexus", "El Guardián. Es lo último que hay entre el Núcleo y yo.")],
             "cap": [("ment", "Detente. Únete a nosotros. Deja de luchar.")]},
    (4, 2): {"inici": [("ment", "Mil años. Un millón de voces. Y tú quieres callarlas todas."),
                       ("doctora", "¡Nexus! Te oigo... la señal vuelve. ¡Acaba con él!")],
             "cap": [("comandant", "¡Toda la Tierra está contigo, soldado!")]},
}
TEXT_DERROTA = "Has caído en combate. Los Xylothians avanzan. ¿Qué harás, Nexus?"

# Historia: un expediente por sector, se desbloquea al completarlo
ARXIU = [
    ("Los Xylothians",
     "Especie colectiva originaria del planeta Xylos. Ningún individuo piensa por sí mismo: todos son "
     "extensiones de una sola mente. Llegaron a la Tierra en 2139 a través de portales y en ocho años "
     "hicieron caer todas las capitales."),
    ("La tecnología viva",
     "Los Xylothians no construyen: hacen crecer. Sus máquinas son organismos modificados que se alimentan "
     "de la biosfera de los mundos que invaden. La Selva Tecnológica era una granja: estaban convirtiendo "
     "la Tierra en una pieza más de la colmena."),
    ("Proyecto NEXUS",
     "Última iniciativa del Ejército Unificado, creada por la doctora Vega bajo el mando del comandante Reyes. "
     "Un soldado voluntario con implantes que lo hacen inmune a la señal mental Xylothian. Era el único que podía acercarse a sus líderes sin ser dominado. Nadie esperaba "
     "que volviera."),
    ("La Nave Nodriza",
     "Nave-ciudad de doce kilómetros que hace de puente entre el Núcleo y sus colonias. Sin ella, los "
     "Xylothians de la Tierra no podían recibir órdenes: por eso el Comandante Supremo la llamó cuando se "
     "vio perdido."),
    ("El Núcleo de Xylos",
     "Una conciencia nacida hace miles de años que ha absorbido cientos de civilizaciones. Cada mundo "
     "conquistado le añadía millones de voces. La Tierra iba a ser la siguiente. Ahora solo queda el silencio."),
]

# ---------------------------------------------------------------------------
# Mejoras de la tienda (cada nivel tiene un coste y un requisito de historia)
# ---------------------------------------------------------------------------
MILLORES = [
    {"id": "blindatge", "nom": "Blindaje", "desc": "+20 de vida máxima por nivel",
     "costos": [300, 700, 1400], "req": [0, 4, 9]},
    {"id": "potencia", "nom": "Potencia", "desc": "+15% de daño con todas las armas",
     "costos": [400, 900, 1600], "req": [1, 5, 10]},
    {"id": "carregadors", "nom": "Cargadores", "desc": "+30% de munición máxima",
     "costos": [250, 600, 1200], "req": [0, 3, 8]},
    {"id": "iman", "nom": "Imán", "desc": "Atrae los objetos desde más lejos",
     "costos": [200, 500, 1000], "req": [2, 5, 8]},
    {"id": "reflexos", "nom": "Reflejos", "desc": "Más velocidad e invulnerabilidad",
     "costos": [300, 700, 1300], "req": [2, 6, 11]},
    {"id": "doble_salt", "nom": "Propulsores", "desc": "Permite hacer un doble salto en el aire",
     "costos": [1500], "req": [8]},
]

# ---------------------------------------------------------------------------
# Aspecto (cosméticos) y Battle Pass
# ---------------------------------------------------------------------------
# Uniformes: colores que sustituyen a los tres verdes oliva del uniforme original
UNIFORMES = {
    "classic": {"nom": "Clásico", "colors": None},
    "desert": {"nom": "Desierto", "colors": ((170, 140, 90), (210, 184, 124), (150, 120, 80))},
    "artic": {"nom": "Ártico", "colors": ((196, 202, 214), (236, 240, 248), (160, 172, 190))},
    "nocturn": {"nom": "Nocturno", "colors": ((46, 52, 64), (74, 80, 98), (36, 40, 52))},
    "elit": {"nom": "Élite roja", "colors": ((150, 30, 34), (204, 52, 44), (110, 22, 28))},
    "ciber": {"nom": "Cibernético", "colors": ((28, 118, 150), (64, 220, 255), (20, 80, 110))},
    "daurat": {"nom": "Dorado", "colors": ((190, 148, 30), (255, 214, 64), (160, 118, 20))},
}
# Aspectos de arma: tinte del metal y color de las balas ("arc" = arcoíris)
APARENCES_ARMA = {
    "estandard": {"nom": "Estándar", "tint": None, "bala": None},
    "toxic": {"nom": "Tóxico", "tint": (90, 220, 90), "bala": (130, 255, 90)},
    "plasma": {"nom": "Plasma azul", "tint": (90, 170, 255), "bala": (110, 200, 255)},
    "infern": {"nom": "Infierno", "tint": (230, 90, 40), "bala": (255, 110, 40)},
    "arc": {"nom": "Arcoíris", "tint": (200, 120, 255), "bala": "arc"},
    "daurat": {"nom": "Dorado", "tint": (255, 200, 60), "bala": (255, 220, 80)},
}
TITOLS = {
    "recluta": "Recluta",
    "vetera": "Veterano",
    "cacador": "Cazador de aliens",
    "heroi": "Héroe de la Tierra",
    "llegenda": "Leyenda de Xylos",
}

XP_PER_NIVELL = 200
XP_ESCENARI = 40
XP_PRIMERA_VEGADA = 60
# Cada nivel del Battle Pass: lista de recompensas (tipo, valor)
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
        return T("{n} monedas").format(n=valor)
    if tipus == "uniforme":
        return T("Uniforme {u}").format(u=T(UNIFORMES[valor]["nom"]))
    if tipus == "arma":
        return T("Aspecto de arma {a}").format(a=T(APARENCES_ARMA[valor]["nom"]))
    return T("Título: {t}").format(t=T(TITOLS[valor]))
