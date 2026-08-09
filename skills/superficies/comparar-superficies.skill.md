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

## Dependencias

`ezdxf`, `shapely`, `numpy`.

## Ver también

*   `recorte-y-resta` — para verificar que un recorte hizo lo que debía.
*   `contornos-y-boundaries` — si la diferencia es de **forma** y no de cota, el problema
    puede ser un boundary que no recorta la triangulación.
