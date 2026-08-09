---
name: ifc_a_civil3d
description: "Convierte modelos IFC (Bentley OpenRoads/GeoPak) a DXF con capas NCS o a LandXML TIN georreferenciado en VA83-SF, conservando la triangulación, con diagnóstico previo del esquema y control explícito del factor de escala."
---

# IFC → Civil 3D (DXF con capas NCS / LandXML)

Trae modelos IFC de Bentley al entorno Autodesk, georreferenciados en **VA83-SF** (NAD83
Virginia State Plane South, US survey foot), conservando la geometría tal cual viene.

## Cuándo usar

*   Un IFC de OpenRoads/GeoPak que hay que ver o editar en Civil 3D.
*   Necesitas la malla de terreno de un IFC como superficie TIN sin retriangular.
*   Quieres el *linework* (baseline, bordes, breaklines) y no las mallas.

## Uso

```bash
python skills/migracion/scripts/ifc_diagnose.py modelo.ifc
```

```bash
python skills/migracion/scripts/ifc_to_ncs_dxf.py modelo.ifc salida.dxf 3.280839895
```

| Script | Qué entrega |
|---|---|
| `ifc_diagnose.py` | Esquema, entidades y conteos. **Ejecútalo primero, siempre.** |
| `ifc_to_ncs_dxf.py` | DXF con capas **NCS** (mallas + linework), escala US survey foot, *Unitless*. El camino normal. |
| `ifc_to_dxf.py` | DXF genérico. Acepta `auto` para detectar la unidad declarada. |
| `ifc_terrain_to_landxml.py` | La capa de triangulación (p. ej. `Terrain_Triangle`) como LandXML TIN, **conservando exactamente las caras**. |
| `ifc_curves_to_dxf.py` | Solo curvas de `IfcGeometricSet` en representaciones mapeadas. |

## ⚠️ El factor de escala: dos pies distintos, 24 ft de desfase

Es el error que más caro ha salido en esta migración. Hay **dos** conversiones y no son
intercambiables:

| Origen del IFC | Factor correcto | Por qué |
|---|---|---|
| Metros SI | `3.2808333333` | metro → **US survey foot** |
| Pie internacional (0,3048) | `3.280839895` | = 1/0,3048 |

Los IFC de **estructuras** de este proyecto vienen en **pie internacional y ya en
coordenadas State Plane**. Aplicarles `3.2808333333` (el valor por defecto de varios
scripts, pensado para metros) produjo un **desfase de 24 ft** — suficiente para parecer
plausible en pantalla y estar mal.

**Regla:** no aceptes el factor por defecto. Ejecuta `ifc_diagnose.py`, mira la unidad
declarada, y pasa el factor explícito. Si el modelo ya está en pies State Plane, el número
es `3.280839895`.

Los IFC de **edificios** ya vienen en NCS y no necesitan remapeo de capas.

## Cómo verificar que quedó bien georreferenciado

Un desfase de unidades no se ve en el archivo, se ve al superponer. Contrasta contra algo
ya validado:

*   Superpón el resultado con un DWG del proyecto que ya esté en su sitio.
*   Comprueba que las coordenadas caigan en el rango de VA83-SF del proyecto
    (X ≈ 12,1 M / Y ≈ 3,5 M en pies).
*   Un desplazamiento **constante** en todo el modelo es la firma de un factor de escala
    mal elegido, no de un modelo mal hecho.

## Formato del LandXML que sí importa Civil 3D

`ifc_terrain_to_landxml.py` escribe `<P id>Y X Z</P>` y `<F>i j k</F>` con índices
**1-based**. Ojo con el orden: el LandXML va *norte este cota*, al revés del `X Y` del DXF.
Invertirlos no da error — da una superficie silenciosamente girada.

## Dependencias

`ifcopenshell`, `ezdxf`.

## Ver también

*   `malla-a-landxml` — si ya tienes la malla en DXF.
*   El handoff completo de la migración está en
    `Raul ZOIN\Avances\HANDOFF_Migracion_IFC.md`.
