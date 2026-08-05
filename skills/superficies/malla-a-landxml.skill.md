---
name: malla_a_landxml
description: "Convierte mallas polyface/3DFACE/MESH de un DXF en superficies TIN LandXML conservando la triangulación exacta, con soldadura por XY, limpieza de caras degeneradas y relleno de huecos internos."
---

# Malla polyface → superficie TIN (LandXML)

Lleva una malla de un DXF a una superficie de Civil 3D **conservando exactamente su
triangulación**, sin pasar por Delaunay. Es el camino que funciona cuando "importar el
DXF" deja huecos, retriangula de más o rellena el casco convexo.

## Cuándo usar

*   Tienes una malla (polyface, 3DFACE o MESH) y necesitas una superficie Civil 3D idéntica.
*   Importar puntos produce una superficie que "corta recto" por donde debería curvar.
*   La superficie importada tiene huecos con el mensaje `Point ... ignored - duplicate`.

## Uso

```bash
python skills/superficies/scripts/mesh_to_landxml.py dibujo.dxf CAPA salida.xml
```

| Script | Cuándo |
|---|---|
| `mesh_to_landxml.py` | Una superficie por capa. El caso normal. |
| `mesh_multi_to_landxml.py` | Una superficie **por cada entidad DXF**. Cuando varias superficies comparten capa pero no pueden fusionarse porque se tocan o se traslapan en planta. |
| `mesh_to_breaklines_dxf.py` | Salida como *breaklines* + contorno, para construir la superficie de forma nativa en Civil 3D. Respeta cada arista, rellena huecos internos por Delaunay y recorta al contorno. |

## ⚠️ Exporta DXF, no DWG

`DXFOUT` desde Civil 3D **se cuelga** con mallas grandes. Exporta el DXF desde Civil 3D
directamente, no conviertas un DWG después.

## Los tres pasos que hacen que funcione

1.  **Soldadura de vértices por XY.** Un TIN no admite dos puntos en el mismo XY. Sin
    soldar, Civil 3D descarta el duplicado y **abre un hueco** justo ahí. Se redondea XY a
    4 decimales (mismo criterio que `cara-superior-desde-solido`).
2.  **Descarte de caras degeneradas y duplicadas**, que aparecen al colapsar vértices
    durante la soldadura.
3.  **Relleno de huecos internos**, para que no queden espacios donde la malla sí tenía
    material.

Lo que **no** funciona, ya probado: SNAP, unión por vecindad y FILL de Civil 3D.

## Triángulos solapados en las costuras

Cuando dos secciones de la malla se montan una sobre otra, hay que quitar el solape antes
de escribir el LandXML. Pero **no borres caras a lo bruto**: en este proyecto una limpieza
por cruces destruyó 565 ft² para arreglar 0,27 ft² de solape real. Mide primero cuánto
solape hay de verdad.

Ojo con el chequeo automático: `crossing_count()` de `mesh_utils.py` **devuelve `None`**
si la malla supera 6.000 aristas, y un `None` impreso sin cuidado se lee igual que "0
cruces". Una superficie de ~14.000 triángulos ronda las 21.000 aristas, así que en la
práctica el contador no responde justo cuando más falta hace.

## Dependencias

`ezdxf`, `shapely`. Lógica común en `mesh_utils.py` (misma carpeta).

## Ver también

*   `cara-superior-desde-solido` — si la malla es un sólido, primero quita paredes y fondo.
*   `contornos-y-boundaries` — si la forma la define un boundary y no la triangulación.
