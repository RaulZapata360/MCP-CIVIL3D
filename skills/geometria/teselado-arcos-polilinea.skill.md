---
name: teselado_arcos_polilinea
description: "Tesela polilíneas DXF que contienen arcos (bulges) muestreando directamente la circunferencia real con una tolerancia de sagitta máxima."
---

# Teselado de Arcos y Bulges en Polilíneas por Sagitta

Muestrea polilíneas 2D/3D con arcos (*bulges*) convirtiendo arcos curvos en polígonos discretizados de alta precisión geométrica. Mantiene el error de área estrictamente controlado por el parámetro `--sagitta`.

## Cuándo usar

*   Antes de recortar mallas TIN LandXML o calcular áreas sobre polígonos con curvas.
*   Para convertir arcos DXF en vértices ordenados sin usar aproximaciones Bézier externas (que introducen errores de contorno).

## Entradas requeridas

*   `--dxf` (ruta): Archivo DXF con polilíneas.
*   `--sagitta` (float): Tolerancia máxima de sagitta (flecha) en unidades del dibujo (por defecto: 0.001).

## Uso

```bash
python skills/geometria/scripts/teselar_arcos.py --dxf perimetro.dxf --sagitta 0.001 --salida perimetro_teselado.dxf
```

## Salida

*   DXF con polilíneas compuestas por segmentos rectos densificados sobre la geometría circular exacta.
