---
name: generacion_planos_svg
description: "Genera planos vectoriales SVG de verificación topográfica (TIN, perímetros, cotas, leyendas, escala gráfica y norte) sin requerir matplotlib ni librerías gráficas externas."
---

# Generación de Planos Vectoriales SVG de Verificación Topográfica

Sistema independiente para generar gráficos vectoriales SVG de alta precisión para control y verificación de trabajos en Civil 3D / LandXML / DXF. Funciona como librería Python (`PlanoSVG`) y como herramienta CLI sin depender de librerías gráficas pesadas (como `matplotlib` o `cairo`).

## Cuándo usar

*   Para emitir planos de verificación de recortes de superficies, contornos o alineaciones.
*   Para generar controles visuales livianos y vectoriales inspeccionables directamente en el navegador o dashboard HTML.
*   Cuando se requiera renderizar geometrías 2D/3D (polígonos, redes de triángulos TIN, polilíneas, puntos) con escalas gráficas automáticas, leyenda, indicador de Norte y paletas cromáticas accesibles (temas claro y oscuro).

## Entradas requeridas

*   Geometrías de terreno (vértices X, Y, Z, triángulos TIN, polígonos o polilíneas).
*   Archivos LandXML o DXF opcionales para renderizado directo CLI.

## Uso en Python

```python
from skills.reportes.scripts.plano_svg import PlanoSVG

p = PlanoSVG(titulo="Verificación de Recorte de Pavimento", subtitulo="Superficie Pavement 5", unidad_lin="ft")
p.poligonos(triangulos, rol="contexto", etiqueta="TIN Original")
p.poligonos(triangulos_recortados, rol="serie1", etiqueta="Área Cortada")
p.lineas([perimetro_coords], rol="serie2", etiqueta="Perímetro de Corte", cerrar=True)
p.guardar("pavement5_verificacion.svg")
```

## Uso desde Línea de Comandos (CLI)

```bash
python skills/reportes/scripts/plano_svg.py --xml superficie.xml --dxf perimetro.dxf --salida verificacion.svg
```

## Salidas

*   `*.svg`: Archivo SVG standalone en XML limpio con:
    *   Soporte para temas visuales (claro y oscuro).
    *   Escala gráfica ajustada automáticamente a números redondos (1, 2, 5 x 10^n).
    *   Símbolo del Norte y membrete informativo.
    *   Leyenda de capas y series asignadas.
    *   Soporte para rampas de color secuenciales (por ej. mapas de elevación o pendientes).

## Estado

Completamente validado y utilizado en los scripts de recorte de superficie (`recortar_superficie.py`) y en la carpeta de pruebas `SUR/prueba ia`. También es la base del informe HTML completo de la skill `informe-analisis-superficies` (`skills/superficies/`), que lo combina con `graficos_svg.py` (barras, rosa de orientación, perfiles) para armar un documento único en vez de planos sueltos.
