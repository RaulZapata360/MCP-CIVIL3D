---
name: particion_de_superficies
description: "Parte una superficie de la entrega en piezas usando líneas de un DXF como cuchilla, renumerando de norte a sur, y explica por qué los bordes compartidos se reconstruyen por topología y no promediando pares."
---

# Partición de superficies y bordes compartidos

Divide una superficie ya montada en piezas, y deja que dos piezas vecinas compartan
**exactamente** la misma línea divisoria.

## Cuándo usar

*   Una superficie de la entrega tiene que separarse en dos o más sin rehacer el resto.
*   Dos superficies colindantes tienen bordes "casi pegados" pero distintos, y hay líneas
    dobles o cruces en XY entre ellas.

## Uso

```bash
python skills/superficies/scripts/partir_una.py entrega.xml combinado.xml "Nombre Superficie" lineas.dxf
```

`partir_una.py` parte **una** superficie sin tocar las demás. La pieza más al norte
conserva el nombre; las otras toman los primeros números libres de su familia.

## Las líneas de corte se prolongan 5 ft, y hace falta

Las cuchillas suelen venir dibujadas justo de borde a borde. Con el redondeo a 4 decimales
del LandXML, un extremo puede quedarse micrómetros **dentro** de la superficie — y
entonces shapely no parte nada, sin error ni aviso. El script prolonga cada línea 5 ft por
cada extremo antes de usarla. Si partes por tu cuenta, replica esa holgura.

## ⚠️ Bordes compartidos: reconstruir topología, NO promediar pares

Para que dos superficies vecinas compartan la misma divisoria hay dos enfoques, y **solo
uno funciona**:

*   ❌ **Promediar pares de bordes** (`unify_shared_borders.py`, en `_cuarentena/`): para
    cada pareja de bordes "casi pegados" se reemplazan ambos por su línea media. Suena
    razonable y **falla en 53 de 67 casos por autointersección** — al mover un borde para
    casarlo con un vecino se rompe el acuerdo con el vecino del otro lado. El problema es
    que cada pareja se arregla ignorando al resto.
*   ✅ **Reconstruir la topología** (partición planar con `polygonize`): se meten todos los
    bordes en un único grafo planar y se reconstruyen las caras. Por construcción no puede
    haber líneas dobles ni cruces, porque cada arista existe **una sola vez** y las piezas
    la comparten.

La implementación de referencia del método bueno es `planar_partition.py`, que sigue en
`HRCP\CIVIL 3D\Scripts_Migracion\`: está atada a las piezas de North Island y no admite
argumentos, así que no se promovió a skill. Cuando haga falta generalizarla, ese es el
punto de partida — no el promediado por pares.

## Falso positivo conocido: el detector de líneas dobles

El detector de bordes duplicados/paralelos marca como "línea doble" tramos que en realidad
son **una divisoria legítima entre dos piezas distintas**. Antes de unificar un par
señalado, comprueba que sean de verdad dos representaciones del mismo límite físico y no
dos límites reales que casualmente corren en paralelo.

## Dependencias

`ezdxf`, `shapely`. Lógica común en `mesh_utils.py` (misma carpeta).

## Ver también

*   `contornos-y-boundaries` — extraer y simplificar los perímetros que se usan de cuchilla.
*   `rellenar-huecos` — para las costuras que quedan tras partir.
