---
name: drapeado_contorno_3d
description: "Drapea polilíneas 2D sobre mallas TIN LandXML interpolando cotas Z para exportar polilíneas 3D en DXF aptas como Breaklines o Boundaries en Civil 3D."
---

# Drapeado e Interpolación 3D de Contornos sobre TIN

Proyecta vértices y segmentos de una polilínea 2D sobre una superficie TIN de LandXML, calculando la elevación Z de cada punto por interpolación plana en los triángulos de la malla y exportando una polilínea 3D nativa en DXF.

## Cuándo usar

*   Para obtener el contorno 3D drapeado de una zona o área de pavimento cortada.
*   Para generar breaklines 3D exactas que se adapten al terreno.

## Entradas requeridas

*   `--xml` (ruta): LandXML de la superficie TIN.
*   `--dxf` (ruta): DXF con la polilínea 2D a drapear.

## Uso

```bash
python skills/superficies/scripts/drapear_contorno.py --xml superficie.xml --dxf contorno2d.dxf --salida contorno3d.dxf
```

## Salida

*   DXF con entidades `POLYLINE` o `LINE` 3D drapeadas sobre las elevaciones reales de la superficie.
