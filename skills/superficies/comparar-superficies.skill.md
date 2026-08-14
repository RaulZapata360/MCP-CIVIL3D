---
name: comparar_superficies
description: "Marca en un DXF las zonas donde dos superficies TIN difieren en cota más de un umbral, rasterizando ambas sobre la misma malla regular e interpolando por baricéntricas."
---

# Comparar dos superficies TIN

Responde a "¿en qué se diferencian estas dos versiones del terreno, y dónde?" con un
resultado dibujable, no con un número suelto.

## Cuándo usar

*   Comparar "Vieja" contra "Nueva" del mismo terreno tras una revisión.
*   Verificar que una edición solo tocó donde debía.
*   Localizar dónde se movió una superficie tras un recorte o un pegado.

## Uso

```bash
python skills/superficies/scripts/zonas_desnivel.py vieja.xml nueva.xml salida.dxf [umbral] [paso]
```

## Cómo lo hace

Rasteriza las dos superficies sobre la **misma malla regular** (1 ft por defecto),
interpolando por coordenadas baricéntricas dentro de cada triángulo. Resta celda a celda y
agrupa en polígonos las celdas que superan el umbral.

Rasterizar evita el problema de comparar triangulaciones distintas: dos superficies del
mismo terreno casi nunca comparten vértices, así que no se pueden restar punto a punto.

## Detalles a tener en cuenta

*   **El paso manda en el coste y en el detalle.** 1 ft es fino para una calzada; en un
    terreno de kilómetros súbelo o tardará. Un paso grueso puede saltarse un escalón
    estrecho.
*   **Solo compara donde ambas existen.** Si una superficie no cubre una zona, esa zona no
    sale como diferencia: sale como "sin dato". No confundas una con otra al leer el plano.
*   **El umbral define qué es "diferencia".** Por debajo del ruido de interpolación todo
    parecerá igual; muy bajo y saldrá marcada la superficie entera.

## Peritar una entrega que "quedó mal": 4 medidas que sí distinguen

Caso real (South Island, 2026-08): un entregable de 22 superficies se generó
**uniendo** las secciones originales del IFC en una sola y recortándola de
nuevo. El usuario reportó "el relieve se perdió". Estas cuatro medidas
separaron lo que de verdad pasó de lo que solo lo parecía.

**1. Primero comprobar que se compara lo mismo.** El archivo nuevo traía capas
que el original no tenía (`Pavement`, `Gravel` además de `Roadway`). Comparar
el máximo Z de un archivo contra el del otro medía **la separación entre capas
estructurales**, no un error de relieve — daba una mediana de exactamente
0,5000 ft (6", un espesor de pavimento típico). Comparar Roadway contra Roadway
antes de sacar conclusiones.

**2. Diferencias en mesetas discretas = no es re-triangulación.** Al histograma
de diferencias hay que mirarle la *forma*, no solo la mediana. Una
re-triangulación produce dispersión **continua**; escalones limpios en 0,00 /
+0,18 / +0,50 ft son capas distintas o un desfase sistemático. Son problemas
distintos con causas distintas.

**3. Supervivencia de los puntos: XY vs XYZ.** La prueba más directa de "se
perdió el relieve":

| | mal generada | reconstruida recortando |
|---|---|---|
| puntos originales con **XY** conservada | 97,8 % | — |
| puntos originales con **XYZ** conservada | **17,6 %** | **92,8 %** |
| triángulos originales idénticos | 10,4 % | 60,9 % |

80,3 % conservó su posición en planta pero **ninguna capa nueva tenía su cota**.

**4. Relleno de casco convexo: la firma del `Paste Surface`.** Si el área
sobrante cae **dentro del casco convexo** de la huella original pero **fuera de
la huella real**, y además está concentrada en **un solo trozo** por sección
(no dispersa), es superficie inventada donde el terreno era cóncavo. Medido:
8.689 ft² en una sección y 470 ft² en otra, el 100 % dentro del casco. Es
exactamente lo que hace un Delaunay sobre el conjunto de puntos combinado.

```python
sobra = huella_nueva.difference(huella_original)
dentro_casco = sobra.intersection(huella_original.convex_hull)
# dentro_casco.area / sobra.area ~ 1.0  y pocos trozos grandes -> relleno de casco
```

**Métrica de calidad de la triangulación** (útil como respaldo, no como prueba):
esbeltez = lado mayor ÷ altura sobre ese lado. Equilátero ≈ 1,15; por encima de
20 es una astilla. En el caso real: 25,6 % de astillas en la original → 43,8 %
en la mal generada. Ojo: recortar en secciones **también** sube este número
(37,0 % en la reconstrucción correcta), porque cortar un triángulo crea
astillas en la línea de corte — no confundir eso con relieve dañado. Por eso
esta métrica sola no basta: hay que cruzarla con las medidas 3 y 4.

## Dependencias

`ezdxf`, `shapely`, `numpy`.

## Ver también

*   `recorte-y-resta` — para verificar que un recorte hizo lo que debía.
*   `contornos-y-boundaries` — si la diferencia es de **forma** y no de cota, el problema
    puede ser un boundary que no recorta la triangulación.
*   `recorte-superficie` — el arreglo cuando el diagnóstico da "re-triangulada":
    recortar la triangulación **original** con los contornos de las secciones
    nuevas, que conserva la cota (`|dZ|` máx 0,007 ft en el caso real) en vez
    de recalcularla.
