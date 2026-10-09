"""Genera l'entrada de contingut.CODIS per a un codi nou.

    python tools/codi.py ELMEUCODI

El joc és públic, així que a contingut.py només hi va l'empremta (SHA-256) del codi, mai el text:
qui llegeixi el codi font no pot saber quins codis hi ha. Majúscules/minúscules i espais no compten.
"""
import hashlib
import sys


def empremta(codi):
    net = "".join(str(codi).split()).upper()
    return hashlib.sha256(("invasio:" + net).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(f'    "{empremta(sys.argv[1])}": {{"nom": "...", "premis": [("monedes", 1000)]}},')
