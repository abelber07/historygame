"""
Idiomas del juego: español (el original), catalán e inglés.

Todo el texto del juego está escrito en español; `T(texto)` devuelve la traducción al idioma elegido
(o el mismo texto si no hay traducción). Los textos con datos variables usan plantillas con {nombre},
por ejemplo T("Nivel {n}").format(n=3). Las traducciones están en traduccions.py.
"""
try:
    from traduccions import CA, EN
except ImportError:                       # sin traducciones: todo en español
    CA, EN = {}, {}

IDIOMES = {"es": "Español", "ca": "Català", "en": "English"}
_TAULES = {"ca": CA, "en": EN}
_actual = "es"
REGISTRE = None          # les proves hi posen un set() per recollir tots els textos que es tradueixen


def T(text):
    if REGISTRE is not None and isinstance(text, str):
        REGISTRE.add(text)
    if _actual == "es" or not isinstance(text, str):
        return text
    return _TAULES[_actual].get(text, text)


def idioma():
    return _actual


def posar_idioma(codi):
    global _actual
    _actual = codi if codi in IDIOMES else "es"
