---
name: plano_svg_verificacion
description: "Sistema de planos SVG de verificación para Civil 3D y topografía: escribe el SVG como texto plano, sin matplotlib ni librerías gráficas, con escala única, norte, escala gráfica, leyenda y rampa de color validada."
---

# Sistema de Reportes Gráficos SVG

Genera planos en planta de verificación a partir de geometría de Civil 3D
(LandXML, DXF, o listas de coordenadas). El SVG se arma concatenando texto: **no
requiere matplotlib, cairo ni ninguna librería gráfica instalada**.

> **Sobre matplotlib (corregido 2026-08-05).** La versión original de esta skill
> decía que existía porque *"en la máquina de trabajo matplotlib no está"*. Eso ya
> no es cierto: hay matplotlib 3.11.0 instalado. Y esa frase tuvo consecuencias —
> en la sesión del 05/08 se dio por buena y se dibujó el plano de verificación de
> South Island a mano con matplotlib, saltándose esta skill y produciendo un plano
> **sin escala gráfica, sin norte y con rampa arcoíris**, o sea violando las reglas
> 3 y 6 de más abajo. La razón para usar esta skill no es la falta de dependencias:
> son las reglas de lectura, la paleta validada y los tests. Si alguna vez conviene
> un PNG (una malla de cientos de miles de triángulos pesa menos rasterizada), se
> añade un backend acá, no se dibuja por fuera.

## Cuándo usar

*   Verificar visualmente cualquier cálculo geométrico antes de entregarlo: recortes,
    cubicaciones, comparación de superficies, revisión de perímetros.
*   Anexar un plano de control a un informe o a un correo, sin abrir Civil 3D.
*   Cuando el control visual debe poder repetirse solo (en un script, un agente o un
    proceso por lotes) sin intervención en la GUI.

Es el complemento gráfico de las skills de cálculo: ellas dan el número, esta muestra
de dónde salió. En el caso que la originó, el plano fue lo que hizo evidente que la
polilínea de corte se salía de la superficie por ambos extremos.

## Uso como librería

```python
from plano_svg import PlanoSVG

p = PlanoSVG(titulo="Superficie X", subtitulo="área 831,5 m²", unidad_lin="m")
p.nota("línea de contexto en tinta atenuada")
p.poligonos(triangulos,  rol="contexto", etiqueta="TIN original")   # fondo
p.poligonos(recorte,     rol="serie1",   etiqueta="Área interior")  # resultado
p.lineas([perimetro],    rol="serie2",   etiqueta="Perímetro", cerrar=True)
p.puntos(vertices,       rol="serie2",   rotulos=["V1", "V2", "V3", "V4"])
p.guardar("plano.svg")
```

| Método | Para qué |
|---|---|
| `poligonos(anillos, rol, etiqueta)` | Relleno: triángulos, áreas, recintos |
| `poligonos_graduados(anillos_valores, vmin, vmax, titulo_escala, borde_malla)` | Relleno por valor con rampa secuencial + barra de gradiente |
| `mosaico(grupos, etiqueta, borde_malla, rotular)` | N regiones, un color y un rótulo cada una |
| `lineas(polilineas, rol, cerrar, guion)` | Ejes, perímetros, quiebres |
| `puntos(coords, rol, rotulos)` | Vértices, estacas, puntos COGO |
| `nota(texto)` | Línea de contexto bajo el subtítulo |
| `render()` | Calcula el encuadre y devuelve el SVG como texto, sin escribir archivo |
| `guardar(ruta)` | Envoltorio de `render()` que además escribe el archivo |

Roles: `contexto` (tinta de chrome, recesivo) y `serie1`..`serie3` (paleta categórica,
en orden fijo). Temas `claro` y `oscuro`.

### Varias superficies en un plano

```python
from plano_svg import PlanoSVG, leer_landxml_todas

todas, unidad = leer_landxml_todas("entrega.xml")     # todas las <Surface>
p = PlanoSVG(titulo="Entrega", unidad_lin=unidad)
p.mosaico([(n, [[(q[0], q[1]) for q in t] for t in tris]) for n, tris in todas],
          etiqueta=f"{len(todas)} superficies (rótulo = nombre)", borde_malla=True)
p.guardar("identificacion.svg")
```

`mosaico` reparte tonos con el **ángulo áureo** (137,508°), no en orden correlativo:
las regiones vecinas suelen tener índices consecutivos, y con reparto lineal saldrían
de tonos casi iguales. Deja **una sola entrada de leyenda**, no N.

## Uso como herramienta

```bash
python skills/reportes/scripts/plano_svg.py --xml superficie.xml --dxf ejes.dxf --color-cota --salida plano.svg
```

Dibuja un LandXML y/o un DXF sin escribir código. `--color-cota` colorea los triángulos
por cota con la rampa secuencial. `--tema oscuro` para pantalla.

Para una entrega de varias superficies, los dos planos que hacen falta:

```bash
python skills/reportes/scripts/plano_svg.py --xml entrega.xml --todas --borde-malla --titulo "Identificacion" --salida ident.svg
```

```bash
python skills/reportes/scripts/plano_svg.py --xml entrega.xml --todas --color-cota --borde-malla --titulo "Cota" --salida cota.svg
```

| Opción | Para qué |
|---|---|
| `--todas` | Todas las `<Surface>` del XML, no solo la primera |
| `--borde-malla` | Dibuja las aristas de los triángulos |
| `--cota-min` / `--cota-max` | Recorta la rampa cuando el terreno es plano con outliers |

## Reglas de diseño (no son estéticas, son de lectura)

1.  **Una sola escala para X e Y.** Ajustar cada eje por separado llena mejor la hoja
    pero deforma la geometría, y un plano deformado no sirve para verificar nada.
2.  **Eje Y invertido.** En SVG el Y crece hacia abajo y el norte hacia arriba. Sin
    invertir, el plano sale espejado y el error es difícil de ver.
3.  **Rampa secuencial de un solo tono**, claro→oscuro, con luminosidad monótona.
    Nunca arcoíris: el arcoíris inventa fronteras donde el terreno no las tiene.
4.  **Colores de serie en orden fijo**, nunca ciclados. El contexto (el TIN de fondo)
    usa tinta de chrome, no un color de serie: no es un dato, es el telón.
5.  **Leyenda siempre presente** con dos o más capas, y los textos en tinta, nunca en
    el color de la serie.
6.  **Escala gráfica con número redondo** (1/2/5 × 10ⁿ) y norte. Un plano sin escala no
    es un plano.

## Paleta

Instancia de referencia validada con el validador de la skill `dataviz`
(`node scripts/validate_palette.js`), **PASS en los 5 chequeos en ambos modos**:
banda de luminosidad, piso de croma, separación para daltonismo, piso de visión normal
y contraste contra el fondo.

| Rol | Claro | Oscuro |
|---|---|---|
| serie1 | `#2a78d6` | `#3987e5` |
| serie2 | `#eb6834` | `#d95926` |
| serie3 | `#1baf7a` | `#199e70` |

Peor par en claro: ΔE 24,7 (protanopía) y 33,6 (visión normal), muy sobre los pisos de
8 y 15. Si cambias un color, **corre el validador de nuevo** — no lo estimes a ojo.

## Detalles críticos (aprendidos a la mala)

### 1. El origen del contenido no es el origen del marco
El contenido se centra dentro del área de dibujo, así que su origen `(ox, oy)` está
corrido respecto del marco `(mx, my)`. Usar uno por el otro dibuja el norte y el
recuadro **fuera del lienzo** cuando el terreno es angosto: en el caso real la "N"
quedó en x=1420 sobre un lienzo de 1200 y simplemente no se veía. Hay test de regresión
con un terreno angosto y otro ancho.

### 2. Hay que escapar `&`, `<` y `>` en todos los textos
Una superficie llamada "Pavimento & Berma" rompe el SVG entero y el visor no muestra
nada. Todo texto pasa por `_esc()`.

### 3. Las pruebas van junto a la skill, no en una carpeta temporal
La suite de este sistema vivía en el scratchpad de la sesión y se borró sola en medio
del trabajo. Los tests están en `scripts/test_plano_svg.py` y se corren solos.

### 4. Dibujar la triangulación es lo único que verifica una malla
Un relleno liso oculta exactamente el defecto que se busca: caras perdidas, huecos,
triángulos cruzados. `borde_malla=True` deja ver la malla. La arista va en **tinta al
15 % de opacidad**, no en gris claro: sobre un relleno saturado un hairline claro se
lee como línea blanca y tapa el dato — el primer plano de cota de South Island salió
así, con la malla comiéndose el relieve.

### 5. Una sola escala de color para todas las superficies
Si cada superficie escala su propio rango de cota, **cada junta inventa un salto de
color que no existe** y ya no se distingue el artefacto del defecto. Por eso
`poligonos_graduados` acepta `vmin`/`vmax` explícitos y el CLI los comparte entre todas
las superficies. Y si se recorta la rampa (`--cota-min`/`--cota-max`), el plano lo dice
en la nota: un recorte callado aparenta un rango de cotas que no es el del dato.

### 6. Los rótulos se descolapsan solos, pero hay que mirarlos igual
`descolapsar()` separa en vertical los rótulos que se pisan (nunca en horizontal: mover
en X sugiere que el rótulo es de la región de al lado) y dibuja línea guía si el rótulo
tuvo que alejarse más de 6 px. Con 25 superficies, `SI CV Top 01` y `SI CV Top 02` salían
encimados y no se leía ninguno.

### 7. El color de `mosaico` no codifica nada
`serie1..serie3` son categorías **que se leen** — por eso son tres y van en orden fijo.
El mosaico resuelve otra cosa: que dos regiones pegadas no se confundan, como en el
coloreado de mapas. El identificador real es el rótulo, y por eso los rellenos son
pálidos: tienen que perder contra el texto. **No hagas una leyenda de N entradas con
ellos**: si el lector necesita mirar un color y saber qué significa, son categorías, y
entonces son como mucho tres.

### 8. Mirar el resultado, no solo los números
La validación de color y el chequeo de desborde son automáticos, pero la composición
hay que verla: abrir el SVG y revisar colisiones de rótulos y encuadre. El bug del
norte fuera del lienzo apareció mirando, no calculando.

## Verificación

```bash
python skills/reportes/scripts/test_plano_svg.py
```

54 comprobaciones: escala idéntica en ambos ejes, relación de aspecto preservada, norte
arriba, XML válido con caracteres especiales, leyenda y escala presentes, rampa de un
solo tono con luminosidad monótona en ambos temas, errores claros ante geometría vacía
o rol inválido, y nada fuera del lienzo en terreno angosto y ancho. Más: colores de
mosaico distintos y separados en tono, centroide ponderado por área, rótulos que no se
pisan con línea guía, escala de cota compartida, borde de malla, y lectura de LandXML
multi-superficie con caras `i="1"` descartadas.

Ojo con un falso positivo al escribir tests de rótulos: si el plano es pequeño en
unidades de terreno, tres regiones separadas 3 ft ya quedan a 25 px y **no hay colisión
que resolver** — el test pasa sin ejercitar nada. Hay que estirar la escala con regiones
lejanas para que las de prueba se junten de verdad.

## Quién la usa

*   `skills/superficies/recortar_superficie.py` la importa para su plano de recorte.
    Ese es el patrón: las skills de cálculo no dibujan, delegan acá.
*   `skills/superficies/informe_superficie.py` (skill `informe-analisis-superficies`)
    usa `render()` para incrustar el plano en planta directamente dentro del HTML
    del informe, sin pasar por un archivo `.svg` intermedio.
*   `skills/reportes/scripts/graficos_svg.py` es el compañero de este módulo:
    mismas paleta y helpers de escape, para barras, rosa de orientación y
    perfiles (con sombreado de corte/relleno) que no son planos en planta.
