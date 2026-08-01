---
name: recorte_superficie_con_perimetro
description: "Recorta una superficie TIN de LandXML con un perímetro cerrado de un DXF y entrega el área interior 2D y 3D, un plano SVG de verificación, el LandXML de la superficie cortada y el contorno en DXF."
---

# Recorte de Superficie TIN con Perímetro y Cálculo de Área Interior

Calcula el área de superficie que queda dentro de un perímetro cerrado, sin
depender de que Civil 3D esté abierto. El corte es geométrico exacto: interseca
cada triángulo del TIN contra el polígono y suma las piezas resultantes.

## Cuándo usar

*   Cuando piden "el área dentro de este polígono" sobre una superficie exportada a LandXML.
*   Cubicaciones y estados de pago por superficie (pavimentos, carpetas, sellos, áreas verdes).
*   Verificar un recorte que ya se hizo en Civil 3D, antes de emitir el plano o el informe.
*   El MCP de Civil 3D **no tiene** herramienta de recorte de superficie: solo lectura,
    puntos, líneas y polilíneas. Esta skill cubre ese vacío.

## Entradas requeridas

*   `--xml` (ruta): LandXML con la superficie. Se exporta desde Civil 3D con `_ExportToLandXML`.
*   `--dxf` (ruta): DXF con la polilínea cerrada del perímetro de corte.

## Uso

```bash
python skills/superficies/scripts/recortar_superficie.py --xml superficie.xml --dxf perimetro.dxf --todo
```

| Opción | Para qué |
|---|---|
| `--superficie NOMBRE` | Elegir la superficie si el LandXML trae varias |
| `--capa CAPA` / `--handle H` | Elegir la polilínea si el DXF trae varias |
| `--unir-todas` | Sumar todas las polilíneas del DXF como un solo perímetro |
| `--sagitta N` | Flecha máxima al teselar arcos (por defecto 0.001, en unidades del dibujo) |
| `--landxml-salida` | Exportar el LandXML de la superficie cortada |
| `--dxf-borde` | Exportar el contorno del área interior (2D y 3D drapeado) |
| `--json ARCHIVO` | Volcar los resultados para consumirlos desde otro script o agente |
| `--todo` | Todas las salidas |

## Salidas

*   **Área interior 2D** (proyectada en planta) y **3D** (superficie real), en la unidad
    del LandXML más su equivalente en m², ha y acres.
*   `*_verificacion.svg` — plano de control: TIN de fondo en tinta atenuada, área
    interior en el color de serie 1, perímetro y vértices numerados en el de serie 2,
    con escala gráfica, norte y leyenda. Lo dibuja la skill
    `skills/reportes` (`plano_svg.py`), que se importa desde acá: esta herramienta
    calcula, no dibuja. Acepta `--tema claro|oscuro`.
*   `*_superficie_cortada.xml` — LandXML del TIN recortado, listo para importar a Civil 3D.
*   `*_borde_interior.dxf` — contorno del área interior en capas separadas, para pegarlo
    en el dibujo y aplicarlo como *Outer boundary* y reproducir el corte de forma nativa.

## Detalles críticos (aprendidos a la mala)

### 1. Las caras `i="1"` del LandXML hay que descartarlas
En `<Faces>`, el atributo `i="1"` marca la cara como invisible: son las que Civil 3D
excluye por contorno. **Si no se descartan, el área no calza con la del dibujo.** En el
caso de prueba eran 145 de 870 caras. La herramienta las excluye y luego contrasta el
área recalculada del TIN completo contra la declarada en el `<Definition>`; si no
calzan al decimal, avisa.

### 2. El orden de coordenadas del LandXML es *norte este cota*
El texto de cada `<P>` es `northing easting elevation`, al revés del `X Y` del DXF.
Invertirlos no produce error, produce un área silenciosamente equivocada. La herramienta
compara los *bounding box* del TIN y del perímetro: si no se tocan pero sí lo harían al
invertir norte/este, lo dice explícitamente.

### 3. El área 3D se calcula por triángulo, no al final
Para cada triángulo, la razón `área3D/área2D` es constante en todo su plano, así que la
pieza recortada hereda esa misma razón. Es exacto, no una aproximación. Comparar la
razón global 3D/2D contra el terreno da un buen chequeo de sanidad: cerca de 1,000 en
terreno plano, más alta en pendiente.

### 4. Los arcos (bulges) de la polilínea hay que teselarlos sobre el arco real
Una polilínea con arcos leída solo por sus vértices da un área muy equivocada (un
círculo de 2 vértices con bulge degenera a área 0). Ojo: **no usar
`ezdxf.path.make_path().flattening()`** — convierte el arco a curvas Bézier que quedan
~0,03 % por fuera, y afinar la sagitta converge a la Bézier, no al arco. La herramienta
muestrea sobre la circunferencia real con `bulge_to_arc`, así el error sí baja
proporcionalmente al bajar `--sagitta`.

### 5. El perímetro puede ser más grande que la superficie
El resultado es *la superficie que existe dentro del perímetro*, que no es lo mismo que
*el área del perímetro*. La herramienta informa el porcentaje del polígono que cae sobre
el TIN y avisa si es menor a 100 %. En el caso de prueba la cobertura fue 51,6 %: el
polígono se salía del pavimento por ambos extremos, y sin ese aviso el número se habría
reportado como si fuera el área del polígono.

## Verificación contra Civil 3D (si está abierto, vía el MCP)

Vale la pena cruzar el resultado antes de emitirlo:

*   `get_surface_info(nombre)` → `area_2d` y `area_3d` deben calzar con el área
    recalculada del TIN completo que imprime la herramienta.
*   `sample_surface_elevation(nombre, este, norte)` → debe calzar con las cotas
    interpoladas dentro del recorte.

En el caso de prueba ambos calzaron: área 37.165,53067 / 37.178,39523 ft² idénticas, y
las cotas coincidieron hasta el sexto decimal.

## Falsos positivos conocidos

*   **Superficies con huecos internos:** si el TIN tiene un vacío y el perímetro lo
    cruza, el área interior sale correcta pero el contorno exportado trae varios anillos.
    Revisar el conteo de "regiones resultantes" que informa la herramienta.
*   **Perímetro auto-intersectado:** se corrige con `buffer(0)` y se avisa, pero conviene
    arreglar la polilínea en el dibujo: el área "corregida" puede no ser la que se quería.
*   **Unidades:** el LandXML declara la unidad y de ahí salen las etiquetas. Un LandXML
    métrico exportado desde un dibujo en pies (o al revés) da números coherentes pero mal
    rotulados. Confirmar contra `get_drawing_info` del MCP.

## Dependencias

*   `ezdxf` y `shapely` (`pip install ezdxf shapely`).
*   `skills/reportes/scripts/plano_svg.py` para el plano de verificación. Se resuelve
    por ruta relativa; si mueves una de las dos skills, ajusta `_REPORTES` en el script.

## Verificación

```bash
python skills/superficies/scripts/test_recorte.py
```

20 comprobaciones contra casos con resultado analítico conocido: círculo con arcos
sobre plano inclinado (área = πr², razón 3D/2D = √(1+m²)), convergencia del error de
teselado al afinar `--sagitta`, polígono no convexo, unidades métricas, perímetro sin
contacto, perímetro que se sale parcialmente, DXF con varias polilíneas, y el plano SVG
con su leyenda. Además reproduce el caso real (`SUR/prueba ia`, Pavement Surface 5:
8.950,443 ft² en planta) cruzado contra Civil 3D.
