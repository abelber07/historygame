"""Genera version.json (el manifest que llegeix el launcher) per a una versió de Windows.

Ús: python tools/manifest.py VERSIO ZIP_JOC EXE_LAUNCHER REPO TAG SORTIDA

Les novetats es treuen del README (bloc «**Versión X...**» de la versió base).
"""
import hashlib
import json
import os
import re
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def novetats(versio_base):
    """Línies de la secció de novetats del README per a la versió base (p. ex. 3.4)."""
    try:
        txt = open(os.path.join(ARREL, "README.md"), encoding="utf-8").read()
    except OSError:
        return []
    m = re.search(r"^\*\*Versión " + re.escape(versio_base) + r"\b[^\n]*\*\*\n(.*?)(?:\n\s*\n|\Z)", txt, re.M | re.S)
    if not m:
        return []
    linies = []
    for l in m.group(1).splitlines():
        l = l.strip()
        if l.startswith("- "):
            l = re.sub(r"\*\*(.+?)\*\*", r"\1", l[2:])
            l = re.sub(r"`(.+?)`", r"\1", l)
            linies.append(l)
    return linies


def versio_launcher():
    txt = open(os.path.join(ARREL, "launcher", "launcher.py"), encoding="utf-8").read()
    return int(re.search(r"^VERSIO_LAUNCHER = (\d+)", txt, re.M).group(1))


def main():
    versio, zip_joc, exe_launcher, repo, tag, sortida = sys.argv[1:7]
    base = f"https://github.com/{repo}/releases/download/{tag}"
    base_versio = ".".join(versio.split(".")[:2])
    dades = {
        "versio": versio,
        "joc": {"url": f"{base}/{os.path.basename(zip_joc)}", "sha256": sha256(zip_joc),
                "mida": os.path.getsize(zip_joc), "executable": "Juego.exe"},
        "launcher": {"versio": versio_launcher(), "url": f"{base}/{os.path.basename(exe_launcher)}",
                     "sha256": sha256(exe_launcher)},
        "novetats": {"es": novetats(base_versio)},
    }
    with open(sortida, "w", encoding="utf-8") as f:
        json.dump(dades, f, ensure_ascii=False, indent=1)
    print(json.dumps(dades, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
