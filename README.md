# Joc Militar: Invasió Alienígena

![Invasió Alienígena](logo.png)

**Juga-hi al navegador:** https://abelber07.github.io/historygame/

Versió millorada i adaptada a web del joc original [`Joc_final`](https://github.com/abelber07/Joc_final), fet per Nacho i Abel amb Python i Pygame.

## Història

Any 2147. Els Xylothians, una espècie que comparteix una sola ment, han devastat la Terra. Nexus, un soldat cibernètic immune al seu senyal mental, és l'última esperança de la humanitat.

Nexus travessa les ruïnes, la selva tecnològica i la fortalesa alienígena fins a derrotar el Comandant Suprem. Però abans de caure, el Comandant crida la **Nau Mare** que orbita la Terra, i les seves restes revelen la veritat: tots els Xylothians obeeixen el **Nucli de Xylos**, al seu món d'origen. Nexus haurà de pujar a l'òrbita i creuar l'últim portal per acabar la guerra per sempre.

## Sectors

| Sector | Escenaris | Cap |
|---|---|---|
| 1. Ruïnes Urbanes | 1-1 a 1-3 | General Xylothian |
| 2. Selva Tecnològica | 2-1 a 2-3 | Mestre de la Selva |
| 3. Fortalesa Xylothian | 3-1 a 3-3 | Comandant d'Elit i **Comandant Suprem** (cap final) |
| 4. Òrbita: la Nau Mare | 4-1 a 4-3 | **Nau Mare Xylothian** (cap final) |
| 5. Xylos, el Món Rusc | 5-1 a 5-3 | Guardià del Rusc i **Nucli de Xylos** (cap final) |

Cada cap final té el seu patró: el Comandant Suprem llança anells que giren, la Nau Mare deixa caure cortines de bales i crida reforços, i el Nucli de Xylos dispara espirals, anells amb un buit per esquivar i una mirada que t'apunta.

Quan completes un sector desbloqueges una entrada de l'**Arxiu**, amb el lore dels Xylothians.

## Controls

| Tecla | Acció |
|---|---|
| A / D o fletxes | Moure's |
| ESPAI / W / fletxa amunt | Saltar (mantén premut per saltar més alt; doble salt amb els Propulsors) |
| S / fletxa avall | Baixar d'una plataforma |
| Clic esquerre | Disparar (mantén premut amb les armes automàtiques) |
| 1-5 / Q / roda del ratolí | Canviar d'arma |
| P / ESC | Pausa |
| G | Tornar al menú |
| M | Activar / silenciar el so |

## Armes i potència

| Arma | Dany | Bales | Tirs/s | Potència | Cost | Disponible després de |
|---|---|---|---|---|---|---|
| Pistola | 5 | 20 | 6 | 1 | Inicial | — |
| Escopeta | 6 × 6 perdigons | 12 | 1,8 | 2 | 500 | 1-2 |
| Fusell | 15 | 30 | 6,7 | 3 | 900 | 1-3 |
| Minigun | 25 | ∞ | 10 | 4 | 1800 | 3-1 |
| Canó de plasma | 40 (travessa enemics) | 24 | 3,8 | 5 | 3000 | 4-2 |

Cada escenari té una **potència màxima**: les armes més potents s'hi bloquegen (per exemple, a les ruïnes inestables del sector 1, al laboratori amb gas inflamable de la selva o al camp supressor del rusc). Si l'arma equipada no està permesa, el joc tria la millor que sí que ho està. El selector de nivells mostra la potència màxima de cada escenari.

## Botiga

- **Armes**: compra i equipa les cinc armes. Algunes no es poden comprar fins que avances en la història.
- **Millores** (cada nivell també té un requisit d'història): Blindatge (+20 de vida), Potència (+15% de dany), Carregadors (+30% de munició), Imant (atrau els ítems), Reflexos (velocitat i invulnerabilitat) i Propulsors (doble salt).
- **Aparença**: uniformes, aparences d'arma (canvien el color del metall i de les bales) i títols.

## Passi de batalla

Guanyes XP eliminant enemics i completant escenaris (més XP la primera vegada). Cada 200 XP puges un nivell del passi, fins a 20, i desbloqueges monedes i cosmètics exclusius: uniformes Desert, Àrtic, Operacions nocturnes, Elit vermell, Cibernètic i Daurat; aparences d'arma Tòxic, Plasma blau, Infern, Arc de Sant Martí i Daurat; i títols com «Caçador d'aliens» o «Llegenda de Xylos».

## Novetats d'aquesta versió

**Versió 2.0**
- Dos sectors nous (6 escenaris) amb fons nous, dos caps finals nous (Nau Mare i Nucli de Xylos), un cap nou (Guardià del Rusc) i un enemic nou: el caçador, que es carrega i envesteix.
- Història ampliada i coherent amb el final, i Arxiu de lore.
- Dues armes noves (escopeta i canó de plasma), potència d'arma per escenari i canvi d'arma durant la partida.
- Botiga amb pestanyes d'armes, millores i aparença, amb compres que depenen de l'avanç en la història.
- Passi de batalla de 20 nivells amb aparences exclusives per al soldat i les armes.
- Animacions dels enemics: inclinació en moure's, propulsors, avís lluminós abans d'atacar, restes que cauen en morir i seqüències de mort dels caps amb explosions encadenades. El Comandant Suprem mou els tentacles i té una fase de fúria, la Nau Mare té llums i canons que s'il·luminen, i l'ull del Nucli segueix el jugador i parpelleja.
- Els desats de la versió anterior es migren automàticament.


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

**Animacions i gràfics (versió 1.1)**
- El soldat ara té animacions: córrer (6 fotogrames amb les cames en moviment), respiració en repòs, salt, caiguda, aixafament en aterrar, retrocés i flamarada del canó, beines que salten, pols als peus i caiguda en morir.
- Les bales surten de la punta real de cada arma.
- L'ombra del jugador es projecta sobre la plataforma de sota i es fa petita i transparent en saltar (abans es quedava enganxada als peus).
- Fons amb paral·laxi i ambient animat a cada escenari: cendra i platets llunyans a la ciutat, pluja, guspires i resplendor de foc, espores lluminoses i fulles a la selva, reflectors a la fortalesa, interferències d'energia, neu i llamps al combat final.
- Logotip nou animat (platet volant amb raig tractor sobre la Terra) a la pantalla de càrrega i al menú, i icona nova per a la pestanya del navegador.

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

Quan es puja un canvi a `main.py`, `dades.py` o `assets/`, el workflow `.github/workflows/pages.yml` recompila el joc amb pygbag, actualitza aquests fitxers i torna a publicar la pàgina.

## Eines

- Python i Pygame (pygame-ce), amb asyncio per al bucle principal.
- pygbag per executar-lo al navegador amb WebAssembly.
- Assets propis (imatges, fons) i música i efectes lliures de drets.
- L'art dels sectors 4 i 5, els caps finals nous, el caçador i les armes noves es generen amb `tools/generar_assets.py`.
- Les dades del joc (armes, nivells, història, millores i passi) són a `dades.py`, per equilibrar-lo fàcilment.
