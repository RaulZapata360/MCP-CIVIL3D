---
name: informe_analisis_superficies
description: "Genera un informe HTML autocontenido de analisis de superficie(s) TIN LandXML: zonificacion de cotas y pendientes, rosa de orientacion, perfil longitudinal y secciones transversales con corte/relleno sombreado, computo volumetrico por grilla, tablas y hallazgos automaticos."
---

# Informe de Analisis de Superficies

Arma el informe completo que normalmente se arma a mano después de correr media
docena de herramientas sueltas: zonifica cotas y pendientes, dibuja la rosa de
orientación, muestrea el perfil y las secciones transversales de un eje, calcula
corte/relleno entre dos superficies, y lo entrega todo en **un solo archivo HTML**
con el look de documento técnico del repositorio (papel claro, serif editorial,
acento petróleo), listo para imprimir a PDF.

No requiere Civil 3D abierto — trabaja sobre LandXML exportado. Si `--eje-dxf` no
se usa, tampoco requiere `ezdxf`: perfiles y transectos son la única parte que
depende de un DXF.

## Cuándo usar

*   Cuando piden "un informe de la superficie" o "el análisis de la superficie X"
    y hay que entregar algo presentable, no solo números sueltos en la consola.
*   Auditorías de terreno: distribución de cotas y pendientes, zonas de ladera con
    orientación desfavorable, verificación rápida de un levantamiento.
*   Estudios de corte y relleno entre una superficie existente y una de diseño,
    con perfil y secciones transversales a lo largo de un eje.
*   Como paso final de las skills `auditoria-superficies-landxml` y
    `recorte-superficie`: aquéllas calculan y verifican una pieza; ésta arma el
    documento que junta todo para el cliente o el archivo del proyecto.

## Entradas requeridas

*   `--xml` (ruta): LandXML con la superficie existente/base. Único requisito
    obligatorio.
*   `--superficie` (opcional): nombre de la superficie si el XML trae varias.
*   `--xml-disenio` / `--superficie-disenio` (opcional): segunda superficie
    (diseño) para habilitar el cómputo volumétrico corte/relleno.
*   `--eje-dxf` / `--capa-eje` (opcional): DXF con la polilínea de eje, para
    perfil longitudinal y, con `--transectos`, secciones transversales. Arcos se
    teselan sobre el arco real (reutiliza `teselar_bulge` de la skill
    `geometria`), no sobre una aproximación Bézier.

## Uso

```bash
# Informe minimo: solo zonificacion, orientacion y hallazgos
python skills/superficies/scripts/informe_superficie.py \
    --xml existente.xml --salida informe.html

# Con corte/relleno entre existente y diseño
python skills/superficies/scripts/informe_superficie.py \
    --xml existente.xml --xml-disenio disenio.xml \
    --salida informe.html --json informe.json

# Completo: perfil longitudinal + secciones transversales cada 50 m
python skills/superficies/scripts/informe_superficie.py \
    --xml existente.xml --xml-disenio disenio.xml \
    --eje-dxf eje.dxf --capa-eje EJE --transectos \
    --intervalo-transectos 50 --ancho-izq 15 --ancho-der 15 \
    --proyecto "Sitio_Estudio" --salida informe.html --json informe.json
```

| Opción | Para qué | Default |
|---|---|---|
| `--bandas-cota` | N de bandas iguales o cortes `"0,10,20,30"` | `6` bandas iguales |
| `--bandas-pendiente` | cortes de pendiente en % | `0,5,10,15,25` (última banda abierta) |
| `--sectores-orientacion` | sectores de la rosa (4/8/16 usan nombres cardinales) | `8` |
| `--espaciamiento-volumen` | paso de la grilla de volumen | automático (≈ ancho del solape / 80) |
| `--intervalo-perfil` | muestreo del perfil longitudinal | `25` (unidad del dibujo) |
| `--intervalo-transectos` | separación entre secciones | `50` |
| `--tema` | `claro` u `oscuro` | `claro` |
| `--proyecto` | nombre genérico para el membrete | `Sitio_Estudio` |

## Salidas

*   Un `.html` autocontenido (SVG incrustado inline, CSS embebido, sin CDN ni
    fuentes externas): abre en cualquier navegador y se imprime a PDF con
    `@media print` ya resuelto (saltos de página evitando cortar tablas o
    hallazgos a la mitad).
*   Secciones del informe: ficha de identificación + resumen numérico → zonificación
    de cotas (plano con rampa + barras + tabla) → zonificación de pendientes (idem)
    → rosa de orientación + tabla → perfil longitudinal (si hay eje) → secciones
    transversales con corte/relleno sombreado (si `--transectos`) → cómputo
    volumétrico (si hay superficie de diseño) → hallazgos y recomendaciones.
*   `--json`: todos los valores numéricos (estadísticas, bandas, orientación,
    volumen) para que otro script o agente los consuma sin parsear HTML.

## Qué gráficas muestra y por qué

*   **Plano en planta con rampa continua** (`PlanoSVG.poligonos_graduados`, de la
    skill `reportes`) para cota y para pendiente: un mapa de calor da la forma del
    terreno de un vistazo; la tabla de bandas da el número exacto.
*   **Barras de área por banda**: cuánto terreno cae en cada rango de cota o
    pendiente, no solo el promedio.
*   **Rosa de orientación**: hacia dónde miran las laderas (relevante para
    exposición solar, drenaje superficial, criterios de estabilidad).
*   **Perfil longitudinal** y **secciones transversales sombreadas**: la
    geometría real a lo largo de un eje, con el área de corte (tinta de serie2)
    y relleno (tinta de serie1) pintada entre las dos superficies — el mismo
    patrón que pide el estándar de informes técnicos del repositorio.

Todo se dibuja a mano en SVG (módulo `skills/reportes/scripts/graficos_svg.py`,
nuevo compañero de `plano_svg.py`): mismo principio de "sin matplotlib" y misma
paleta validada, para que un informe que combine plano y gráficos se vea como un
solo sistema.

## Reglas de diseño (heredadas del estándar de informes del repositorio)

1.  **Georgia serif para títulos, acento petróleo `#0e5563`, papel claro.** Sin
    emojis ni glows informales — es un documento técnico, no un dashboard de
    producto.
2.  **Cada superficie/eje se lee una sola vez** y se indexa espacialmente
    (`indice_espacial`, grilla de buckets) antes de muestrear: perfiles,
    transectos y volumen reutilizan el mismo índice en vez de recorrer todos los
    triángulos por cada punto.
3.  **El volumen es por grilla, no TIN exacto.** Se documenta la cobertura (%) y
    el paso usado; si la cobertura baja de 90% se levanta un hallazgo de alerta.
    Para el número definitivo, cruzar con `civil3d_surface_volume_calculate` o
    `civil3d_qty_earthwork_summary` cuando Civil 3D esté abierto.
4.  **Nombres de proyecto y superficie se escapan** antes de incrustarlos en el
    HTML (`html.escape`): un nombre con `&`, `<` o `>` no debe romper el
    documento ni inyectar marcado.
5.  **Sin datos de cliente por defecto.** `--proyecto` usa `Sitio_Estudio` si no
    se indica otro, siguiendo la regla de anonimización del repositorio
    (`.agents/AGENTS.md` #6): no hardcodear nombres reales de sitios o clientes
    en los informes generados.

## Detalles críticos (aprendidos al construirla)

### 1. La orientación (aspecto) es invariante al orden de los vértices
La dirección de descenso se deriva del gradiente `(-a/c, -b/c)` del plano del
triángulo, que no cambia si el vector normal se invierte (mismo plano, normal
opuesta). Verificado con un plano inclinado analítico: `z = 0.1·E` da pendiente
10.000% y orientación 270° (desciende hacia el Oeste) sin importar el orden de
`p1,p2,p3`.

### 2. Los triángulos casi planos no tienen orientación fiable
Por debajo de `0.5%` de pendiente la dirección de descenso es ruido de redondeo,
no terreno real. Se excluyen de la rosa (y se informa cuántos) en vez de
mancharla con valores arbitrarios.

### 3. Cada banda de zonificación se queda con su triángulo exactamente una vez
`zonificar()` asigna cada triángulo a la primera banda `[lo, hi)` que lo
contiene; la banda final (pendiente) queda abierta con `hi = inf`. Invariante
verificado en los tests: la suma de área de todas las bandas es igual al área
total, sin huecos ni doble conteo.

### 4. El volumen por grilla solo mide donde ambas superficies tienen dato
La grilla recorre el rectángulo de **solape** de ambas cajas envolventes; una
celda sin dato en cualquiera de las dos superficies se cuenta como "sin dato" y
resta de la cobertura, no se asume cero. Con dos planos paralelos (caso
analítico) el volumen calza al dato exacto porque la grilla queda alineada con
ambas superficies.

### 5. `render()` separa "dibujar" de "guardar"
Se agregó `PlanoSVG.render()` (devuelve el texto SVG sin escribir archivo) para
poder incrustar el plano inline en el HTML del informe sin pasar por un archivo
intermedio. `guardar()` sigue funcionando igual — es un envoltorio de
`render()` — así que no rompe nada de la skill `reportes`.

## Verificación

```bash
python skills/superficies/scripts/test_informe_superficie.py
```

45 comprobaciones: lectura de LandXML y área, pendiente/orientación contra un
plano inclinado analítico (con y sin invertir el orden de vértices), invariante
de área en la zonificación, exclusión de triángulos planos en la rosa, índice
espacial dentro y fuera de la superficie, volumen de grilla contra dos planos
paralelos conocidos (relleno y corte), muestreo de perfil sobre un eje recto,
generación de informe HTML (bloques presentes, SVG interno bien formado,
escapado de texto con caracteres especiales) y el flujo completo con superficie
de diseño.

## Quién la usa / Dependencias

*   Importa `PlanoSVG` y `paso_redondo` de `skills/reportes/scripts/plano_svg.py`,
    y las funciones de `skills/reportes/scripts/graficos_svg.py` (nuevo).
*   Si se usa `--eje-dxf`, importa `teselar_bulge` de
    `skills/geometria/scripts/teselar_arcos.py` y requiere `ezdxf`. El resto del
    informe (zonificación, orientación, volumen) solo necesita la librería
    estándar de Python.
*   Complementa a `auditoria-superficies-landxml` (integridad del TIN) y
    `recorte-superficie` (recorte + plano de verificación): ninguna de las dos
    arma un documento final: ésta sí.
