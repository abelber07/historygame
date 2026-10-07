# Juego Militar: Invasión Alienígena

![Invasión Alienígena](logo.png)

**Juega en el navegador:** https://abelber07.github.io/historygame/

Versión mejorada y adaptada a la web del juego original [`Joc_final`](https://github.com/abelber07/Joc_final), hecho por Nacho y Abel con Python y Pygame.

## Historia

Año 2139. Sobre la Tierra se abren decenas de portales y por ellos llegan los Xylothians, una especie que no piensa por sí misma: todos sus soldados obedecen a una sola mente. Tras ocho años de guerra, las capitales han caído.

El ejército crea su última arma, el **Proyecto NEXUS**: un soldado con implantes que lo hacen inmune a la señal mental alienígena. En 2147 Nexus despierta en un búnker bajo la ciudad en ruinas y empieza su misión.

Nexus cruza las ruinas, la selva tecnológica y la fortaleza alienígena hasta derrotar al Comandante Supremo. Pero antes de caer, el Comandante llama a la **Nave Nodriza** que orbita la Tierra, y sus restos revelan la verdad: todos los Xylothians obedecen al **Núcleo de Xylos**, en su mundo de origen. Nexus tendrá que subir a la órbita y cruzar el último portal para acabar la guerra para siempre.

La primera vez que se abre el juego se ve una **animación inicial** que cuenta todo esto (se puede saltar con ESC y volver a ver desde *Historia*).

## Sectores

| Sector | Escenarios | Jefe |
|---|---|---|
| 1. Ruinas Urbanas | 1-1 a 1-3 | General Xylothian |
| 2. Selva Tecnológica | 2-1 a 2-3 | Maestro de la Selva |
| 3. Fortaleza Xylothian | 3-1 a 3-3 | Comandante de Élite y **Comandante Supremo** (jefe final) |
| 4. Órbita: la Nave Nodriza | 4-1 a 4-3 | **Nave Nodriza Xylothian** (jefe final) |
| 5. Xylos, el Mundo Colmena | 5-1 a 5-3 | Guardián de la Colmena y **Núcleo de Xylos** (jefe final) |

Cada jefe final tiene su propio patrón: el Comandante Supremo lanza anillos que giran, la Nave Nodriza deja caer cortinas de balas y llama refuerzos, y el Núcleo de Xylos dispara espirales, anillos con un hueco para esquivar y una mirada que te apunta.

Al completar un sector se desbloquea un expediente en **Historia**, con el trasfondo de los Xylothians.

## Controles

| Tecla | Acción |
|---|---|
| A / D o flechas | Moverse |
| ESPACIO / W / flecha arriba | Saltar (mantén pulsado para saltar más; doble salto con los Propulsores) |
| S / flecha abajo | Bajar de una plataforma |
| Clic izquierdo | Disparar (mantén pulsado con las armas automáticas) |
| 1-5 / Q / rueda del ratón | Cambiar de arma |
| P / ESC | Pausa |
| G | Volver al menú |
| M | Activar / silenciar el sonido |
| F11 | Pantalla completa |

## Armas y potencia

| Arma | Daño | Balas | Disparos/s | Potencia | Coste | Disponible tras |
|---|---|---|---|---|---|---|
| Pistola | 5 | 20 | 6 | 1 | Inicial | — |
| Escopeta | 6 × 6 perdigones | 12 | 1,8 | 2 | 500 | 1-2 |
| Fusil | 15 | 30 | 6,7 | 3 | 900 | 1-3 |
| Minigun | 25 | ∞ | 10 | 4 | 1800 | 3-1 |
| Cañón de plasma | 40 (atraviesa enemigos) | 24 | 3,8 | 5 | 3000 | 4-2 |

Cada escenario tiene una **potencia máxima**: las armas más fuertes se bloquean (por ejemplo, en las ruinas inestables del sector 1, en el laboratorio con gas inflamable de la selva o en el campo supresor de la colmena). Si el arma equipada no está permitida, el juego elige la mejor que sí lo está. El selector de niveles muestra la potencia máxima de cada escenario.

## Opciones

Desde el menú (y desde la pausa) se puede ajustar el **volumen de la música** y el **de los efectos** por separado, elegir **pantalla completa o ventana** y el **escalado** (suave o nítido). Todo se guarda.

El juego se dibuja a **960x540** (panorámico 16:9). En un monitor de **1920x1080** se amplía exactamente **x2**: cada píxel del juego son 2x2 píxeles de la pantalla, sin suavizado y sin bandas negras, así que se ve totalmente nítido (y lo mismo a x3 en 2880x1620 o x4 en 4K). En otras resoluciones se usa el escalado elegido en Opciones. En el navegador el lienzo también es de 960x540 y, si la ventana es justo el doble (1920x1080 a pantalla completa), se muestra píxel a píxel.

## Tienda

- **Armas**: compra y equipa las cinco armas. Algunas no se pueden comprar hasta que avanzas en la historia.
- **Mejoras** (cada nivel también tiene un requisito de historia): Blindaje (+20 de vida), Potencia (+15% de daño), Cargadores (+30% de munición), Imán (atrae los objetos), Reflejos (velocidad e invulnerabilidad) y Propulsores (doble salto).
- **Aspecto**: uniformes, aspectos de arma (cambian el color del metal y de las balas) y títulos.

## Battle Pass

Ganas XP eliminando enemigos y completando escenarios (más XP la primera vez). Cada 200 XP subes un nivel del Battle Pass, hasta 20, y desbloqueas monedas y cosméticos exclusivos: uniformes Desierto, Ártico, Nocturno, Élite roja, Cibernético y Dorado; aspectos de arma Tóxico, Plasma azul, Infierno, Arcoíris y Dorado; y títulos como «Cazador de aliens» o «Leyenda de Xylos».

## Novedades

**Versión 2.3**
- Resolución base nueva de 960x540 (16:9): a 1920x1080 el juego se ve a x2 exacto, perfectamente nítido y sin bandas laterales.
- Los 15 fondos redibujados en panorámico, con el tamaño justo para que se pinten píxel a píxel.
- Menús, tienda, Battle Pass, Historia, opciones, HUD, intro y plataformas recolocados para la pantalla panorámica (el menú ahora tiene el logo a la izquierda y los botones a la derecha).
- El escalado x2 es más rápido que el anterior (unos 6,5 ms por fotograma a 1920x1080 en lugar de 8).

**Versión 2.2**
- Pantalla de Opciones con volumen de música y efectos, pantalla completa o ventana y escalado.
- El juego se adapta a la resolución del monitor (1920x1080 a pantalla completa) y llena la pantalla panorámica.
- Música menos fuerte por defecto (30%), recodificada con más calidad y margen para que no distorsione, y búfer de audio más grande para evitar chasquidos. La versión web ya no recomprime el audio (`--no_opt`).

**Versión 2.1**
- Todo el juego en español.
- Animación inicial que cuenta la historia en cinco escenas (portales, invasión, ocho años de guerra, Proyecto NEXUS y el despertar de Nexus).
- Fondos nuevos para los nueve escenarios de los sectores 1, 2 y 3, redibujados con más detalle a partir de la idea original: la torre de vigilancia alienígena en la ciudad, la lluvia con neones, la base del General con su cúpula, la pagoda devorada por la selva, el laboratorio con tanques de criaturas, el árbol-máquina en llamas, las murallas con el cohete, el patio interior con suelo de baldosas y la cima nevada con el portal tras el trono.
- Historia revisada para que todo encaje: por qué Nexus es inmune, de dónde vienen los portales y por qué el Comandante Supremo llama a la Nave Nodriza.
- «Battle Pass» e «Historia» en el menú.

**Versión 2.0**
- Dos sectores nuevos (6 escenarios), dos jefes finales nuevos (Nave Nodriza y Núcleo de Xylos), un jefe nuevo (Guardián de la Colmena) y un enemigo nuevo: el cazador, que se carga y embiste.
- Dos armas nuevas (escopeta y cañón de plasma), potencia de arma por escenario y cambio de arma durante la partida.
- Tienda con pestañas de armas, mejoras y aspecto, con compras que dependen del avance en la historia.
- Battle Pass de 20 niveles con aspectos exclusivos para el soldado y las armas.
- Animaciones de los enemigos: inclinación al moverse, propulsores, aviso luminoso antes de atacar, restos que caen al morir y secuencias de muerte de los jefes con explosiones encadenadas. El Comandante Supremo mueve los tentáculos y tiene una fase de furia, la Nave Nodriza tiene luces y cañones que se iluminan, y el ojo del Núcleo sigue al jugador y parpadea.

**Versión 1.1**
- Animaciones del soldado: correr, reposo, salto, caída, aterrizaje, retroceso, fogonazo, casquillos, polvo y caída al morir. Las balas salen de la punta del arma y la sombra se proyecta sobre la plataforma de debajo.
- Fondos con paralaje y ambiente animado en cada escenario, logotipo nuevo animado e icono nuevo.

**Versión 1.0 (errores corregidos del juego original)**
- El bucle principal no cedía el control (`await asyncio.sleep(0)`) y bloqueaba la pestaña del navegador.
- Los eventos se leían dos veces por fotograma: se perdían clics y teclas.
- El botón «Continuar» de la victoria reiniciaba el combate contra el jefe final.
- La barra de vida del jefe del sector 2 se rellenaba a mitad de combate.
- Los enemigos podían quedarse fuera de la pantalla, donde las balas no llegaban.
- Se podía saltar en el aire después de caer de una plataforma.
- La música se cargaba entera en memoria; ahora se reproduce en streaming (OGG).
- Recursos optimizados de 46 MB a unos 10 MB y guardado automático del progreso.

## Ejecutarlo en el ordenador

```bash
pip install -r requirements.txt
python main.py
```

Para probar la versión web en local:

```bash
pip install pygbag
pygbag .
# y abre http://localhost:8000
```

## Publicación

GitHub Pages publica la raíz de la rama `main` (**Settings → Pages → Deploy from a branch: main / root**). La versión web compilada son los archivos `index.html`, `historygame.tar.gz` y `historygame.apk` de la raíz.

Cuando se sube un cambio a `main.py`, `dades.py` o `assets/`, el workflow `.github/workflows/pages.yml` recompila el juego con pygbag, actualiza esos archivos y vuelve a publicar la página.

## Herramientas

- Python y Pygame (pygame-ce), con asyncio para el bucle principal.
- pygbag para ejecutarlo en el navegador con WebAssembly.
- Gráficos originales de Nacho y Abel (soldado y enemigos), música y efectos libres de derechos.
- Los fondos de los cinco sectores, los jefes finales nuevos, el cazador y las armas nuevas se generan con `tools/generar_assets.py`.
- Los datos del juego (armas, niveles, historia, mejoras y Battle Pass) están en `dades.py`, para equilibrarlo fácilmente. Los nombres de variables del código siguen en catalán.
