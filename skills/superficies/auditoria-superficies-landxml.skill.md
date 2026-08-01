---
name: auditoria_superficies_landxml
description: "Audita la integridad geométrica y estructural de archivos LandXML TIN: caras invisibles (i='1'), orden de coordenadas Norte/Este vs X/Y, unidades del dibujo y conservación de áreas 2D/3D."
---

# Auditoría e Integridad de Superficies LandXML TIN

Verifica la coherencia estructural y de datos de archivos LandXML exportados desde Civil 3D u otras plataformas topográficas.

## Cuándo usar

*   Antes de usar una superficie LandXML en cálculos volumétricos o recortes.
*   Cuando las áreas calculadas no coincidan con las declaradas en el dibujo.
*   Para verificar la correcta asignación de unidades (pies vs metros) y la orientación de coordenadas (Northing Easting vs X Y).

## Entradas requeridas

*   `--xml` (ruta): Archivo LandXML a auditar.
*   `--superficie` (opcional): Nombre de la superficie específica si existen varias.

## Uso

```bash
python skills/superficies/scripts/auditar_superficie.py --xml superficie.xml
```

## Reporte de Auditoría

*   Conteo de caras totales e invisibles (`i="1"`).
*   Área recalculada del TIN vs. área declarada en `<Definition>`.
*   Chequeo de Bounding Box y coherencia de inversión Norte/Este.
*   Unidad lineal declarada y factor de conversión.
