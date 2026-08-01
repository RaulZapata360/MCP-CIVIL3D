---
name: plano_svg_verificacion
description: "Sistema de planos SVG de verificación para Civil 3D y topografía: escribe el SVG como texto plano, sin matplotlib ni librerías gráficas, con escala única, norte, escala gráfica, leyenda y rampa de color validada."
---

# Sistema de Reportes Gráficos SVG

Genera planos en planta de verificación a partir de geometría de Civil 3D
(LandXML, DXF, o listas de coordenadas). El SVG se arma concatenando texto: **no
requiere matplotlib, cairo ni ninguna librería gráfica instalada**, que es
justamente la razón por la que existe — en la máquina de trabajo matplotlib no
está y no vale la pena instalar dependencias para un dibujo de control.

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
| `poligonos_graduados(anillos_valores, titulo_escala)` | Relleno por valor con rampa secuencial + barra de gradiente |
| `lineas(polilineas, rol, cerrar, guion)` | Ejes, perímetros, quiebres |
| `puntos(coords, rol, rotulos)` | Vértices, estacas, puntos COGO |
| `nota(texto)` | Línea de contexto bajo el subtítulo |
| `guardar(ruta)` | Calcula el encuadre y escribe el archivo |

Roles: `contexto` (tinta de chrome, recesivo) y `serie1`..`serie3` (paleta categórica,
en orden fijo). Temas `claro` y `oscuro`.

## Uso como herramienta

```bash
python skills/reportes/scripts/plano_svg.py --xml superficie.xml --dxf ejes.dxf --color-cota --salida plano.svg
```

Dibuja un LandXML y/o un DXF sin escribir código. `--color-cota` colorea los triángulos
por cota con la rampa secuencial. `--tema oscuro` para pantalla.

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

### 4. Mirar el resultado, no solo los números
La validación de color y el chequeo de desborde son automáticos, pero la composición
hay que verla: abrir el SVG y revisar colisiones de rótulos y encuadre. El bug del
norte fuera del lienzo apareció mirando, no calculando.

## Verificación

```bash
python skills/reportes/scripts/test_plano_svg.py
```

26 comprobaciones: escala idéntica en ambos ejes, relación de aspecto preservada, norte
arriba, XML válido con caracteres especiales, leyenda y escala presentes, rampa de un
solo tono con luminosidad monótona en ambos temas, errores claros ante geometría vacía
o rol inválido, y nada fuera del lienzo en terreno angosto y ancho.

## Quién la usa

*   `skills/superficies/recortar_superficie.py` la importa para su plano de recorte.
    Ese es el patrón: las skills de cálculo no dibujan, delegan acá.
