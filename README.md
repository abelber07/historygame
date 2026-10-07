# Joc Militar: Invasió Alienígena

**Juga-hi al navegador:** https://abelber07.github.io/historygame/

Versió millorada i adaptada a web del joc original [`Joc_final`](https://github.com/abelber07/Joc_final), fet per Nacho i Abel amb Python i Pygame.

## Context

Any 2147. Els Xylothians, una raça alienígena, han devastat la Terra. Nexus, un soldat cibernètic, és l'última esperança de la humanitat per aturar la invasió infiltrant-se a les bases enemigues.

En vèncer el líder alienígena, Nexus destrueix la fortalesa, tanca els portals Xylothians i assegura la supervivència de la humanitat... de moment.

## Controls

| Tecla | Acció |
|---|---|
| A / D o fletxes | Moure's |
| ESPAI / W / fletxa amunt | Saltar (mantén premut per saltar més alt) |
| S / fletxa avall | Baixar d'una plataforma |
| Clic esquerre | Disparar (mantén premut amb les armes automàtiques) |
| P / ESC | Pausa |
| G | Tornar al menú |
| M | Activar / silenciar el so |

## Armes

| Arma | Dany | Bales | Tirs/s | Mode | Cost |
|---|---|---|---|---|---|
| Pistola | 5 | 20 | 6 | Semiautomàtica | Inicial |
| Fusell | 15 | 30 | 6,7 | Automàtica | 700 |
| Minigun | 25 | ∞ | 10 | Automàtica | 1400 |

Les armes es compren a la Botiga amb les monedes que guanyes eliminant enemics (dron 50, lloctinent 100, cap 250, Comandant Suprem 500).

## Nivells

Tres sectors amb tres escenaris cadascun: **Ruïnes Urbanes**, **Selva Tecnològica** i **Fortalesa Xylothian**. Cada sector acaba amb un cap amb el seu propi patró d'atac, i l'escenari final és el combat contra el Comandant Suprem Xylothian (anells de projectils que giren i una fase de fúria a mitja vida).

## Novetats d'aquesta versió

**Errors corregits**
- El bucle principal no cedia el control (`await asyncio.sleep(0)`), cosa que bloquejava la pestanya al navegador.
- Els esdeveniments es llegien dues vegades per fotograma: es perdien clics i tecles, i prémer G durant la partida tornava al menú amb la música del nivell encara sonant.
- El botó «Continuar» de la pantalla de victòria reiniciava el combat contra el cap final.
- La barra de vida del cap del sector 2 tornava a omplir-se a mitja lluita.
- Els enemics podien quedar-se fora de la pantalla, on les bales no hi arribaven.
- Es podia saltar a l'aire després de caure d'una plataforma, i en saltar per sota d'una plataforma el jugador s'hi «enganxava».
- El jugador sempre mirava a la dreta quan estava quiet; els sprites es veien deformats.
- La música es carregava sencera a memòria (`Sound` amb MP3 de 8 MB); ara es reprodueix en streaming.
- El text de la narrativa «saltava» mentre s'escrivia i trigava més de 20 segons a aparèixer.
- La pantalla de càrrega durava 10 segons obligatoris; el botó «Sortir» deixava la pantalla en negre al navegador.
- S'ha eliminat un fitxer que no era del joc (`assets/get_attachment_url`) i la música duplicada.

**Millores**
- Funciona al navegador (pygbag / WebAssembly) i es publica sol a GitHub Pages amb GitHub Actions.
- Assets optimitzats: de 46 MB a uns 10 MB (música en OGG amb volum normalitzat, efectes retallats).
- El progrés (monedes, armes i nivells) es desa automàticament (localStorage al navegador, `partida.json` a l'escriptori).
- Armes automàtiques (fusell i minigun en mantenir el clic), cadència per arma i dispersió.
- Salt més precís: salt variable, marge per saltar just després de sortir d'una plataforma i baixar de plataformes.
- Invulnerabilitat breu després de rebre un impacte, tremolor de pantalla i parpelleig dels enemics ferits.
- Bales del jugador i dels enemics amb colors diferents; punt de mira.
- Nous enemics: lloctinents (sector 1 i 2) i un comandant d'elit al sector 3, tal com explica la narrativa. Cada cap té un color i un patró d'atac propis.
- Els enemics deixen ítems de vegades i els ítems apareixen segons el que necessites (vida o munició).
- HUD nou: cors amb mitges vides, munició, monedes, enemics restants i barra de vida del cap amb el seu nom.
- Pausa (també automàtica en canviar de finestra), so on/off, botiga amb estadístiques de cada arma, selector de nivells amb escenaris completats.
- Tipografies pixel art incloses (Press Start 2P i VT323, llicència SIL OFL).

## Executar-lo a l'ordinador

```bash
pip install -r requirements.txt
python main.py
```

Per provar la versió web en local:

```bash
pip install pygbag
pygbag .
# i obre http://localhost:8000
```

## Publicació

GitHub Pages publica l'arrel de la branca `main` (**Settings → Pages → Deploy from a branch: main / root**). La versió web compilada són els fitxers `index.html`, `historygame.tar.gz` i `historygame.apk` de l'arrel.

Quan es puja un canvi a `main.py` o a `assets/`, el workflow `.github/workflows/pages.yml` recompila el joc amb pygbag, actualitza aquests fitxers i torna a publicar la pàgina.

## Eines

- Python i Pygame (pygame-ce), amb asyncio per al bucle principal.
- pygbag per executar-lo al navegador amb WebAssembly.
- Assets propis (imatges, fons) i música i efectes lliures de drets.
