---
name: cara_superior_desde_solido
description: "Convierte mallas polyface volumétricas (sólidos con cara superior, paredes y fondo) en superficies TIN que conservan solo la cara transitable, en DXF o en LandXML por elemento."
---

# Cara superior desde malla sólida

Un DXF exportado desde un modelo de pavimentos suele traer cada elemento como un
**sólido**: cara superior, paredes laterales y cara inferior. Civil 3D no puede hacer
una superficie TIN con eso — un TIN no admite dos cotas en el mismo XY. Esta skill se
queda solo con la cara de arriba, la **transitable**.

## Cuándo usar

*   Un DXF de mallas polyface donde cada elemento es un prisma (paquete de pavimento,
    losa, carpeta) y necesitas la rasante.
*   El conteo de caras "mirando arriba" y "mirando abajo" es idéntico, o cada columna XY
    tiene exactamente 2 valores de Z: señal inequívoca de sólido extruido.
*   Civil 3D importa el LandXML y la superficie sale con el doble de triángulos o con
    "paredes" verticales imposibles.

## Cómo decide qué es "superior"

Se agrupan los vértices que comparten X e Y (redondeados a `DEC` decimales) y una cara se
conserva **solo si sus tres vértices son el de mayor Z de su columna**. Así caen a la vez
las paredes y el fondo, sin tocar la cara buena. Es exacto, no una aproximación: si el
elemento es un prisma extruido verticalmente, no se pierde ni un triángulo.

## Uso

```bash
python skills/superficies/scripts/extraer_cara_superior.py entrada.dxf salida.dxf 4
```

```bash
python skills/superficies/scripts/xml_desde_cara_superior.py entrada.dxf carpeta_salida 4
```

| Script | Qué entrega |
|---|---|
| `extraer_cara_superior.py` | DXF con solo la cara superior. Para inspeccionar antes de convertir. |
| `xml_desde_cara_superior.py` | Un LandXML por elemento, listo para importar a Civil 3D. |
| `aislar_elementos.py` | Saca elementos concretos con el **sólido completo** a capas separadas. Para medir espesores, que no se ven si solo llevas la cara de arriba. |

El tercer argumento es `DEC`, los decimales de XY. **Léete el apartado siguiente antes de
omitirlo.**

## ⚠️ El valor por defecto de DEC pierde geometría

`extraer_cara_superior.py` y `xml_desde_cara_superior.py` traen **DEC=3 por defecto, y con
3 se descartan triángulos reales.** Usa siempre `4` de forma explícita.

**Mecanismo:** si dos vértices distintos están a ~0,0002 ft en XY, `dec=3` los funde en una
sola columna. Sus Z difieren en ~1e-5, más que la tolerancia de 1e-6, así que el más bajo
deja de ser "el máximo" y **toda cara que lo use se descarta** — incluidos triángulos
normales de decenas de ft².

**Caso real** (`SI_CV_SURFACE_DXF.dxf`, South Island, 2026-08-04):

| DEC | caras | área |
|---|---|---|
| 3 | 13.830 | 604.772,0 ft² |
| 4 | 13.838 | 604.915,9 ft² |

Los 8 triángulos perdidos sumaban 143,9 ft², uno solo de 24,6 ft². Es un 0,024 % del
total: **invisible en las métricas agregadas.**

**Cómo elegir DEC:** cuenta las columnas XY con más de 2 valores de Z para dec=2,3,4,5,6.
El correcto es el menor donde ese contador llega a 0. Coincide con el dec=4 de
`malla-a-landxml`.

**Verificación que sí lo detecta:** cuenta aparte las caras con normal Z > 0 directamente
sobre la polyface del DXF y exige que cuadre **malla por malla** con las caras escritas en
el XML. Si no cuadra, el DEC está mal. Las métricas agregadas no sirven acá.

## Qué NO hace esta skill

`xml_desde_cara_superior.py` **respeta la triangulación tal cual viene**: no re-triangula,
no suelda vértices por proximidad, no rellena huecos y no recorta nada. Es deliberado —
cada una de esas operaciones ha destruido geometría real en este proyecto.

Si además necesitas soldar, limpiar o rellenar, eso es `malla-a-landxml`, y es una
decisión aparte que hay que tomar mirando el resultado, no por defecto.

## Solapes en planta: no los resuelve, y es a propósito

Un TIN no admite dos Z en el mismo XY, así que si dos elementos se pisan en planta
tendrás que decidir cuál manda. Esta skill **no decide por ti**.

La herramienta que sí lo automatiza (`mesh_grouped_top_only.py`) está en
[`_cuarentena/`](../_cuarentena/README.md): su regla **elimina la superficie de abajo
entera**, no la recorta. Lee esa advertencia antes de usarla.

Para solapes reales, el criterio que ha funcionado es medir la **forma** del solape, no
solo el área: franjas angostas pegadas a un borde compartido son un roce de triangulación
y se recortan; una huella ancha con desnivel variable son dos superficies distintas y hay
que preguntar cuál va arriba.

## Dependencias

`ezdxf`. La lógica común vive en `mesh_utils.py`, en esta misma carpeta — los scripts la
resuelven por ruta relativa, así que muévelos juntos.

## Ver también

*   `malla-a-landxml` — cuando la malla ya es una superficie (no un sólido).
*   `recorte-y-resta` — para separar piezas una vez extraída la cara superior.
