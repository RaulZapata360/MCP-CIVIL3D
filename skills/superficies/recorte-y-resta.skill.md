---
name: recorte_y_resta_de_superficies
description: "Recorta superficies TIN de un LandXML contra contornos cerrados de un DXF, resta la huella de una superficie de otra, y parte una superficie en piezas por capas SURF_OUTER/SURF_HOLE."
---

# Recorte y resta de superficies TIN

Operaciones booleanas en planta sobre superficies ya exportadas a LandXML, sin necesidad
de que Civil 3D esté abierto. Cada triángulo que cruza el contorno se recorta **exacto en
la línea**, no se descarta entero.

## Cuándo usar

*   Quedarte solo con la parte de una superficie dentro (o fuera) de un perímetro.
*   Que una superficie deje de invadir el territorio de su vecina.
*   Partir una superficie unificada en las piezas del proyecto.

## Uso

```bash
python skills/superficies/scripts/clip_surface_by_boundary.py contorno.dxf CAPA superficies.xml "Nombre1,Nombre2" salida.xml
```

| Script | Para qué |
|---|---|
| `clip_surface_by_boundary.py` | Recorta N superficies contra un contorno, conservando lo de **dentro**. Acepta un DXF extra de hueco interior. |
| `clip_big_surface_by_dxf.py` | Igual pero para mallas de cientos de miles a millones de caras, conservando interior **o** exterior. Un recorrido cara-por-cara con shapely tardaría horas; este usa índice espacial y numpy. |
| `subtract_surface.py` | Resta la huella en planta de una superficie de otra. Deja solo lo que queda fuera. |
| `cortar_por_bordes_dxf.py` | Parte una superficie en piezas usando capas `SURF_OUTER_<nombre>` y `SURF_HOLE_<nombre>`. |

## ⚠️ Nunca borres caras para quitar cruces

Es la lección más cara de este proyecto. Una limpieza automática por cruces **destruyó
565 ft² de superficie real para arreglar 0,27 ft² de solape**. La proporción no es un
caso raro: los cruces detectados suelen ser artefactos numéricos del borde, no material
sobrante.

Antes de borrar nada:

1.  Mide el área **real** del solape, no el número de pares de aristas que se cruzan.
2.  Mira la **forma**: franjas angostas y alargadas pegadas a un borde compartido
    (compacidad 0,13–0,22) son roce de triangulación y se recortan. Una huella ancha con
    desnivel variable son dos superficies distintas y hay que decidir cuál manda.
3.  Recorta en la línea. No elimines la cara ni, mucho menos, la superficie entera.

## ⚠️ `crossing_count()` puede devolver `None` y leerse como "0 cruces"

En `mesh_utils.py`:

```python
def crossing_count(verts, faces, max_edges=6000):
    ...
    if len(E) > max_edges: return None
```

Por encima de 6.000 aristas devuelve `None`. Una superficie de ~14.000 triángulos ronda
las 21.000 aristas, así que **en las superficies grandes el chequeo no se ejecuta** — y un
`None` impreso sin comprobar se lee igual que "sin cruces". Si vas a usarlo como criterio
de aceptación, verifica explícitamente que no sea `None`.

## Verifica con una fuente independiente

El algoritmo de recorte no puede ser su propio juez. En este proyecto un recorte se dio
por bueno con sus métricas internas y la verificación independiente
(`shapely.symmetric_difference`) reveló un 136 % de diferencia respecto al área esperada.

Contrasta siempre contra algo que no sea el propio script: `symmetric_difference` de
shapely, el área declarada en el `<Definition>` del LandXML, o la superficie en Civil 3D
vía el MCP.

Y por encima de todo: **míralo en pantalla**. Las métricas agregadas han ocultado más de
una superficie mutilada — un "0 huecos" convivió con una superficie destrozada.

## Dependencias

`ezdxf`, `shapely`, `numpy` (para `clip_big_surface_by_dxf.py`). Lógica común en
`mesh_utils.py` (misma carpeta).

## Ver también

*   `_cuarentena/README.md` — `merge_clipped_surfaces.py` **NO se debe usar** para volver
    a unir lo recortado.
*   `rellenar-huecos` — para las costuras que deja el recorte.
