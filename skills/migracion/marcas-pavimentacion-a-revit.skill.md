---
name: marcas-pavimentacion-a-revit
description: Migra elementos discretos de un DXF de IFC (marcas de pavimentación, barreras New Jersey, mobiliario, señales — cualquier malla AcDbPolyFaceMesh) a Revit 2024/2025/2026 como Familias o DirectShape, decidiendo la técnica por medición geométrica en vez de a ojo. Incluye clasificador automático (planitud, piezas, huecos, rectangularidad), exportador que detecta si cada malla ya es un sólido cerrado o una lámina 2,5D que hay que solidificar, matemática de colocación verificable fuera de Revit (eje de inercia vs rectángulo mínimo, ancla por transformación rígida), diagnóstico y corrección de piezas enterradas en el Toposolid tras colocarlas, y las plantillas de Dynamo con cada gotcha de la API de Revit ya resuelto (plantillas de familia por idioma, ciclo de vida de LoadFamily, parámetros Tipo vs Instancia, TessellatedShapeBuilder con caras que se tocan, Solid.IntersectWithCurve, grilla UV de caras).
---

# Marcas de pavimentación (y otros objetos discretos) → Revit

## Por qué existe esta skill

Un IFC→DXF de elementos viales trae docenas o cientos de piezas: flechas,
líneas, barreras, señales, mobiliario. Ninguna técnica única sirve para
todas — forzar un solo Toposolid las aplana, forzar una familia por pieza es
inviable con formas orgánicas, y forzar DirectShape para todo desperdicia la
reutilización cuando sí hay piezas repetidas. La decisión correcta sale de
**medir la geometría real de cada categoría**, no de mirarla.

Validado en dos migraciones reales:

- **South Island (HRCP), marcas de pavimento**: 322 piezas en 4 categorías —
  36 flechas (mismo símbolo, 22 rotaciones) y 14 líneas de detención
  (rectángulos, 13 tamaños) a Familia; 26 dobles amarillas y 246 líneas de
  demarcación (curvas orgánicas, hasta 9 piezas y 5 huecos por marca) a
  DirectShape. 322/322 creadas, 0 errores.
- **Barreras New Jersey**: 12 piezas, todas geometría 3D real (no láminas de
  pintura) — el clasificador las mandó a DirectShape correctamente, y sirvió
  para encontrar que el exportador necesitaba detectar mallas **ya
  cerradas** y no intentar darles espesor otra vez (ver más abajo).

Después de colocar las 322 piezas de South Island, varias quedaron
invisibles o parcialmente tapadas por el relieve real del Toposolid (no
detectable por métricas agregadas ni por una nube de puntos externa
decimada) — de ahí salió el Paso 5 y sus dos scripts de diagnóstico/
corrección, con nueve iteraciones documentadas en el catálogo de errores.

---

## Flujo de trabajo

```
DXF del IFC (mallas AcDbPolyFaceMesh, una capa por categoria)
   -> clasificar_marcas_pavimento.py     mide y recomienda tecnica por capa
   -> exportar_marcas_pavimento.py       exporta segun la recomendacion
   -> dynamo_diagnostico_firmas_revit.py corre SIEMPRE antes de tocar Revit
   -> dynamo_colocar_familias_marcas.py  para las capas de Familia
   -> dynamo_directshape_desde_malla.py  para las capas de DirectShape
   -> dynamo_diagnostico_vs_toposolid.py       verificar contra el terreno YA en Revit
   -> dynamo_corregir_enterrado_toposolid.py   subir lo que haga falta
```

### Paso 0 — el DXF puede no ser el bueno, aunque parezca serlo

En South Island había dos DXF de las mismas marcas: uno pasado por la
plantilla del proyecto y otro exportado en crudo del IFC. El de plantilla
**perdía 2 categorías enteras** (36 flechas + 14 stop bars, 15,7 % de la
pintura) — no un recorte parcial, categorías completas ausentes. El de crudo
sí las tenía, pese a llamarse "No Georeferenciado" — estaba en las mismas
coordenadas exactas (comprobado por Hausdorff 0,000000 ft contra las 272
marcas comunes a ambos archivos).

**Antes de exportar nada**, si hay más de un DXF candidato: contar entidades
por capa en cada uno y comparar contra lo que se espera ver en el plano. Una
diferencia de conteo entre archivos de la "misma" entrega es una señal real,
no ruido.

### Paso 1 — clasificar, no adivinar

```bash
python clasificar_marcas_pavimento.py <marcas.dxf>
```

Para cada capa mide: área total, error máximo contra su plano de mejor
ajuste, número de piezas y huecos (unión de triángulos con shapely), y
`area / (largo × ancho)` del rectángulo mínimo (dice si la forma es un
rectángulo real). Con esos cuatro números decide:

| Condición | Técnica |
|---|---|
| Plana (≤0,15 ft) + 1 pieza + 0 huecos + área casi idéntica entre piezas | **Familia**, 1 símbolo + instancias rotadas |
| Plana + 1 pieza + 0 huecos + `area/(largo·ancho)` ≥ 0,98 pero tamaños distintos | **Familia paramétrica** (largo/ancho variables) |
| Cualquier otra cosa: varias piezas, huecos, mala planitud | **DirectShape** desde la malla |

Los umbrales son los que acertaron en South Island (0,079 ft y 0,050 ft de
planitud real para las categorías que fueron a familia; 0,777 y 0,818 ft para
las que fueron a DirectShape) — hay margen de sobra entre ambos grupos, pero
si un proyecto nuevo cae justo en la frontera, reajustar `UMBRAL_PLANO_FT` /
`UMBRAL_DISPERSION` / `UMBRAL_RECTANGULARIDAD` al principio del script.

**Ojo con `AcDbPolyFaceMesh`**: no es una polilínea. En ezdxf, los vértices
con `flags & 64` son vértices reales; el resto son registros de cara con
`location` en (0,0,0) y los índices en `vtx0..vtx3`. Leerlos todos sin
filtrar da cajas de millones de pies — confundió un análisis entero antes de
detectarlo.

### Paso 2 — exportar según lo que midió el paso 1

```bash
python exportar_marcas_pavimento.py <marcas.dxf> <carpeta_salida> \
    --familia CAPA1,CAPA2 --directshape CAPA3,CAPA4 \
    [--origen-x N --origen-y N] [--espesor 0.02]
```

Si se omite el origen local, se calcula igual que en los paquetes de
superficie de este mismo repo (mínimo de X/Y redondeado a la centena).
**Restar coordenadas de 12 millones de pies a coordenadas de miles no es
cosmético**: a esa magnitud el salto entre dos flotantes de precisión simple
ya supera la tolerancia con la que Revit cierra geometría.

**Para capas de Familia**, decide entre dos sub-casos por la misma dispersión
de área del paso 1:

- **Mismo símbolo** (ej. una flecha): el eje real se calcula por **inercia de
  área** (`eje_area`), NO por el rectángulo de área mínima. En una forma con
  una parte más ancha que otra (como la cabeza de una flecha), el rectángulo
  mínimo sale girado respecto al eje verdadero — en South Island daba
  14,659×5,302 ft en vez de los 15,000×5,500 reales, y usarlo como eje dejaba
  el contorno torcido y el símbolo apuntando al revés. El sentido (`+X`) se
  decide por el **centroide de área**, que cae hacia la parte ancha; medirlo
  por anchos de banda en los extremos falla con contornos de pocos vértices.
  Se exporta el contorno canónico en `.dxf` y en un `.txt` con la lista de
  Python ya lista para pegar en `CONTORNO` del script de Dynamo.
- **Paramétrica** (ej. barras rectas de tamaños distintos): el eje se calcula
  con `rect_min`, que para un rectángulo real es exacto. `eje_area` NO sirve
  aquí — con muy pocos triángulos (una barra puede tener solo 2) la
  covarianza es casi degenerada y el eje sale torcido ~1°.

En ambos casos, el punto de inserción (`ancla`) se recupera resolviendo la
transformación rígida completa (`W = R(ang)·P + ancla` para TODOS los
vértices, con un `assert` que lo comprueba) — no la media de los vértices de
la malla. Confundir ambos desplazó instancias hasta 2,5 ft en South Island,
porque la malla tiene más vértices donde el drapeado original era más fino.

**Para capas de DirectShape**, cada malla se solidifica dándole espesor hacia
abajo y cosiendo un faldón en el contorno — **excepto que ya venga cerrada**.
Esto es lo que enseñaron las barreras New Jersey: sus 12 mallas ya eran
sólidos completos (cada arista compartida por exactamente 2 caras, alturas
reales de 2,9–5,2 ft), no láminas de pintura. Aplicarles el mismo
"duplicar+coser" que a la pintura no falla con un error — produce dos
cáscaras estancas anidadas, geometría incorrecta sin ningún aviso. El
exportador comprueba `es_estanco()` por cada malla y las deja pasar tal cual
si ya son sólidas.

```python
def es_estanco(T):
    cuenta = collections.Counter()
    for a, b, c in T:
        for u, v in ((a, b), (b, c), (c, a)):
            cuenta[(min(u, v), max(u, v))] += 1
    return bool(cuenta) and set(cuenta.values()) == {2}
```

### Paso 3 — antes de tocar Revit, verificar fuera de Revit

Para las capas de Familia, antes de escribir una línea de Dynamo: reconstruir
cada instancia desde el contorno canónico + su fila del CSV (girar, trasladar
al ancla) y compararla con la malla original del DXF.

```python
# error en planta: distancia de cada vertice reconstruido al contorno real
# error en cota:   contra el plano de ajuste de la malla original
```

En South Island esto dio 0,032 ft de mediana / 0,137 ft máximo en planta, y
0,0001 ft en cota — y sirvió para atrapar el error del punto de inserción
(2,5 ft) antes de que llegara a Revit, en vez de después de una pasada fallida.

### Paso 4 — Dynamo, con las firmas del API confirmadas primero

```
dynamo_diagnostico_firmas_revit.py   -- SIEMPRE primero, no modifica nada
dynamo_colocar_familias_marcas.py    -- una vez por cada capa de Familia
dynamo_directshape_desde_malla.py    -- una vez por cada capa de DirectShape
```

Cada uno lleva un bloque `CONFIGURACION -- AJUSTAR PARA CADA PROYECTO` al
principio (offset, nombre de familia, si es paramétrica, elevación). Nada de
South Island ni de ningún otro proyecto concreto queda hardcodeado.

### Paso 5 — verificar contra el Toposolid real, no dar la colocación por buena

Las piezas quedan colocadas con la cota que trae el CSV/JSON exportado, más
una elevación fija pequeña (0,02 ft típico). Eso alcanza casi siempre, pero
**"casi siempre" no es lo mismo que "siempre"**: si el Toposolid tiene un
relieve real que la fuente de datos de la colocación no capturó exactamente
en ese punto, la pieza puede terminar total o parcialmente enterrada dentro
del terreno — invisible, o con z-fighting (franjas visibles/invisibles
alternadas) según lo cerca que quede. Esto **no se ve** en las métricas
agregadas del Paso 1 ni en el log de creación del Paso 4: la pieza se creó
bien, con la geometría correcta, en las coordenadas correctas — el problema
aparece recién al mirarla en Revit, y solo en algunas piezas puntuales.

```
dynamo_diagnostico_vs_toposolid.py       -- SIEMPRE primero, solo lectura
dynamo_corregir_enterrado_toposolid.py   -- sube lo que el diagnostico marco
```

El diagnóstico prueba, para cada pieza, si su geometría real queda por
debajo de la cara superior del **sólido real** de cada Toposolid del
proyecto — no una aproximación externa (una nube de puntos decimada de la
superficie puede tener 20 ft de salto entre vecinos y no sirve para esto).
La corrección repite la misma prueba, sube lo que haga falta más un margen,
y vuelve a medir con la geometría ya trasladada antes de darla por resuelta.

Nueve iteraciones (documentadas dentro de
`dynamo_corregir_enterrado_toposolid.py`) hicieron falta para que esto
cubriera los casos reales — resumen en el catálogo de abajo; el más caro:
**una condición de "enterrado" que exigía que el punto estuviera dentro del
espesor del sólido dejaba pasar como "libre" una pieza que estaba por
debajo de TODA la losa**, tapada igual pero técnicamente "fuera" del rango
exigido.

---

## Catálogo de errores resueltos (API de Revit vía Dynamo/CPython3)

Nueve pasadas en total en la migración original. Ninguna por la geometría
exportada — todas por el entorno de Revit. En orden de cuándo aparecen:

### ❌ `doc.FamilyCreate` lanza excepción en un documento de proyecto
`InvalidOperationException: can only be used in the Revit Family Editor`.
`getattr(doc, 'FamilyCreate', None)` **no protege** — el `default` de
`getattr` solo cubre `AttributeError`, y esta excepción sale igual y tumba el
script. Para consultar firmas sin abrir ningún documento, reflexionar sobre
las **clases** `Autodesk.Revit.Creation.FamilyItemFactory` /
`Autodesk.Revit.Creation.Document`, no sobre instancias.

### ❌ `"The attempted operation is not permitted in this type of family"`
Al crear la extrusión. Causa: se cogió `Generic Model Adaptive.rft` (o
`face based`, `wall based`...) porque el nombre "contiene" *generic model*.
Comparar el nombre **completo** contra una lista blanca, y contemplar el
idioma de la instalación de Revit (`Modelo genérico métrico` en español,
`Modèle générique métrique` en francés...).

### ❌ `"The document must not be modifiable before calling LoadFamily"`
`LoadFamily` gestiona su propia transacción; llamarla dentro de una abierta
falla con este mensaje. Debe ir **sin transacción abierta**.

### ❌ `"Saving is not allowed. File has been opened by another Revit instance"`
Un intento anterior dejó el documento de familia abierto (la excepción saltó
antes del `Close()`), bloqueando el `.rfa`. `Close()` siempre en un
`finally`, y además cerrar cualquier resto de una pasada anterior al empezar.

### ❌ En CPython (Python.NET) no existe `clr.Reference`
`LoadFamily(str, Family&)` devuelve por parámetro de salida — no sirve.
Usar `fdoc.LoadFamily(doc)`, el overload que devuelve la `Family` como
retorno.

### ❌ `"Can't rotate element into this position"` (aviso, no excepción)
Revit ancla las instancias de familia al plano de su nivel y rechaza sacarlas
de la horizontal. **Lo notifica como aviso propio de Revit, no como
excepción de Python** — un `try/except` no se entera, y el log dice "0
errores" con las 36 instancias rechazadas igualmente (solo aparece en el
`*_Error Report.html` del proyecto). Marcar la familia como "basada en plano
de trabajo" (`FAMILY_WORK_PLANE_BASED`) no basta si la instancia se crea
sobre el nivel del proyecto. Alternativa usada: no inclinar, subir cada pieza
la mitad de su propio desnivel real (medido sobre la malla, columna `DzFt`
del CSV — estimarlo como `largo × pendiente` lo TRIPLICA, porque supone la
pieza alineada con la línea de máxima pendiente) para que ningún punto quede
bajo la superficie de apoyo.

### ❌ Parámetro con el tamaño de una sola instancia repetido en todas
Causa: `Largo`/`Ancho` creados como parámetro de **Tipo**, no de Instancia.
En Revit 2024/2025 el diálogo *Family Types* ya no tiene una casilla
"Instance" visible en la tabla (UI de versiones antiguas) — hay que
seleccionar la fila del parámetro y usar el icono de **lápiz "Edit
Parameter"** para reabrir el diálogo con las opciones Type/Instance.

### ❌ El tamaño sigue sin cuadrar tras marcar Instancia
`par.AsDouble()` leído **antes** de `doc.Regenerate()` puede devolver el
valor previo a `Set()` — falso positivo de fallo. Orden correcto siempre:
`Set() → Regenerate() → leer`. Si sigue sin cuadrar después de corregir el
orden, comparar también contra el valor leído desde el **Tipo**
(`simbolo.LookupParameter(nombre)`): si Instancia y Tipo coinciden, el
parámetro sigue siendo de Tipo pese al cambio hecho en el Editor de
familias — no se guardó, o se recargó el `.rfa` equivocado.

### ❌ Tamaño correcto pero instancias desplazadas, cada una distinto
Una familia dibujada a mano por alguien nuevo en Revit puede no crecer
simétrica desde su origen al cambiar sus parámetros por código (en South
Island, 14 de 14 necesitaron ajuste, de 3 a 10 ft, cada una un valor
distinto porque cada una tiene un tamaño distinto). **No se corrige
reconstruyendo la familia** con restricciones de simetría (frágil de guiar a
alguien sin experiencia en Revit) — se corrige leyendo el centro real del
sólido ya colocado (promedio de los extremos de sus aristas: exacto para un
prisma rectangular, sea cual sea su construcción interna) y trasladando la
instancia ANTES de girarla. Ver `centrar_geometria()`.

### ❌ `TessellatedShapeBuilder` con `Target=Solid` falla en algunas piezas
Una malla con alguna arista compartida por **más de 2 caras** (una cinta de
pintura que se toca a sí misma en un cruce — 38 de 272 líneas en South
Island) no es un sólido válido. `Target=AnyGeometry` + `Fallback=Mesh`: lo
que puede ser sólido sale sólido, el resto sale como malla, en vez de perder
la pieza entera.

### ❌ `ReferenceIntersector` con una `View3D` elegida al azar: 100% de fallo mudo
Primer intento de comprobar enterramiento contra el Toposolid: disparar un
rayo vertical (`ReferenceIntersector.FindNearest`, el mismo mecanismo que
usa Revit para "qué hay debajo del cursor") desde una `View3D` cualquiera.
Falló el 100% de las 272 piezas probadas con "ningún rayo encontró
Toposolid debajo" — no era un hallazgo real, era que la vista elegida al
azar podía tener el Toposolid oculto o fuera de su crop box, y
`ReferenceIntersector` depende enteramente de lo que ESA vista puede ver.
**Abandonado**: cualquier prueba geométrica que dependa de una vista es
frágil. Reemplazado por `Solid.IntersectWithCurve()` sobre la geometría
real de cada Toposolid — geometría pura, no depende de ninguna vista.

### ❌ La condición de "enterrado" no debe exigir estar DENTRO del espesor
`Solid.IntersectWithCurve()` con `SolidCurveIntersectionMode.
CurveSegmentsInside` da, por cada segmento, un `z_bajo` y un `z_alto`. La
tentación es exigir `z_bajo <= punto.Z <= z_alto` para considerar "enterrado"
— pero una pieza puede estar por debajo de **todo el espesor** de la losa
(más abajo que `z_bajo`, no "dentro" del rango) y seguir tapada igual: se ve
"desde abajo" del Toposolid porque la losa entera queda por encima. La
condición correcta solo mira la cara superior: `punto.Z < z_alto - tolerancia`,
sin límite inferior. Costó 9 iteraciones completas encontrar esto porque las
8 anteriores fallaban por razones de MUESTREO (ver las dos entradas
siguientes) y enmascaraban este bug de lógica hasta que dos piezas
concretas, ya con muestreo exhaustivo, seguían dando "0 enterradas" pese a
ser invisibles en Revit.

### ❌ `Face.Triangulate()` no agrega puntos interiores en caras PLANAS
Para cubrir el interior de una pieza (no solo su contorno de vértices) y
detectar un bulto del terreno lejos de cualquier borde, la solución obvia es
triangular cada cara con `Face.Triangulate()`. **No sirve en una cara
plana**: matemáticamente 2 triángulos ya representan un rectángulo exacto,
así que Revit no agrega ningún punto interior sin importar el nivel de
detalle pedido — se comprobó en la práctica corriendo la comprobación
completa y obteniendo "0 piezas enterradas" pese a un z-fighting real y
visible en Revit sobre una extrusión simple (una flecha: su asta rectangular
solo tiene vértices en el contorno). El reemplazo que sí funciona: evaluar
la cara directamente en su propio dominio UV —
`Face.GetBoundingBox()` (rango U/V) → recorrer una cuadrícula propia →
`Face.IsInside(uv)` → `Face.Evaluate(uv)` — que fuerza densidad real
independientemente de si la cara es plana o curva. Para no re-explotar el
costo en piezas ya finamente trianguladas (una malla de cientos de
triángulos pequeños, típica de una cinta de pintura), filtrar por
`Face.Area` antes: las caras chicas ya tienen cobertura de sobra con sus
propios vértices de borde.

### ❌ Un chequeo geométrico exhaustivo puede colgar o cerrar Revit
Probar cada vértice de cada pieza contra cada Toposolid, sin ningún filtro
previo, puede tardar más de 15 minutos sin terminar (CPU activa, no
colgado — motor de Python de Dynamo de un solo hilo). Dos mitigaciones que
sí funcionan: (1) prefiltro barato de caja XY por Toposolid ANTES de la
prueba geométrica cara — cada punto termina probándose contra 1-2 Toposolid,
no contra todos; (2) deduplicar vértices casi pegados por celda XY
(quedándose con el más bajo de cada celda, el caso más desfavorable) antes
de medir — una malla fina mete cientos de puntos redundantes sin aportar
nada entre sí. Aun así, recorrer un paquete grande (300+ piezas) de una sola
pasada larga con la lógica ya corregida hizo que **Revit se cerrara** (no
solo "no responde") dos veces seguidas — más serio que lentitud, sospecha de
excepción nativa del motor de geometría. La salida que funcionó: acotar el
alcance a las piezas puntuales que hacen falta corregir en vez de
reprocesar todo el paquete de una vez cada corrida.

### ❌ `IFailuresPreprocessor` tampoco se puede implementar desde CPython
Mover una `FamilyInstance` anclada a su nivel (a diferencia de un
`DirectShape`, que no lo está) puede disparar un aviso propio de Revit con
un diálogo MODAL — Dynamo se queda "no responde" esperando un OK que nunca
llega porque no puede verlo ni contestarlo. La solución estándar es envolver
la transacción en un `IFailuresPreprocessor` que descarte avisos
automáticamente (`WarningSwallower`, patrón ya usado y documentado en
`civil3d-to-revit-toposolid.skill.md`) — pero en este entorno (Python.NET
CPython3) implementar esa interfaz falla igual que `IFamilyLoadOptions`
(ver la skill hermana): `"interface takes exactly one argument"`. El código
lo intenta de todas formas envuelto en `try/except` (no hace daño si falla),
pero **no asumir que protege de verdad** — si algo vuelve a colgar Dynamo al
mover una pieza anclada, es una causa distinta que investigar de nuevo.

### ❌ Reflexionar `Enum.GetNames` para volcar valores de un enum al log
`PythonEvaluator.Evaluate operation failed ... violates the constraint of
type 'TEnum'`. Python.NET resuelve mal ese genérico y liga `TEnum` al propio
argumento `Type` pasado — el fallo ocurre en la capa de interop, **fuera**
de cualquier `try/except` de Python, y tumba el nodo entero. No hace falta:
los nombres de un enum conocido (`AnyGeometry`, `Solid`... / `Mesh`,
`Salvage`, `Abort`...) no aportan nada por sí solos.

**La lección que más caro salió, repetida tres veces**: dar por bueno el
silencio. El basculado rechazado sin excepción, `get_BoundingBox(None)` (no
resuelve el overload en CPython) dando "0 inclinadas y 0 planas" a la vez, y
`LookupParameter` sin comprobar si de verdad encontró el parámetro. La
defensa en los tres casos es la misma: **verificar leyendo el modelo de
vuelta**, nunca confiar en que no saltó nada.

---

## Archivos de esta skill

- `clasificar_marcas_pavimento.py` — diagnóstico, no modifica nada. Correr
  siempre primero sobre un DXF nuevo.
- `exportar_marcas_pavimento.py` — exporta CSV de colocación (Familia) y
  JSON de mallas (DirectShape), detectando `es_estanco()` por pieza.
- `dynamo_diagnostico_firmas_revit.py` — vuelca las firmas reales del API de
  la versión de Revit instalada. Correr siempre antes de los dos siguientes.
- `dynamo_colocar_familias_marcas.py` — plantilla única para ambos casos de
  Familia (mismo símbolo / paramétrica), con `CONFIGURACION` al principio.
- `dynamo_directshape_desde_malla.py` — plantilla para DirectShape, sirve
  igual para láminas solidificadas que para sólidos ya cerrados.
- `dynamo_diagnostico_vs_toposolid.py` — solo lectura. Comprueba, contra la
  geometría real de cada Toposolid del proyecto, si alguna pieza colocada
  queda con su cara superior por debajo del terreno.
- `dynamo_corregir_enterrado_toposolid.py` — sube las piezas que el
  diagnóstico anterior marcó, con reintento por pieza y verificación en frío
  al final. Tiene un modo acotado (`ELEMENTOS_A_CORREGIR`) para reprocesar
  solo piezas puntuales en vez de todo el paquete, por si un paquete grande
  llega a colgar o cerrar Revit al procesarlo entero de una vez.

Todos los scripts de Dynamo se pegan en un nodo **Python Script** (motor
**CPython3**) de un grafo nuevo, con un nodo **File Path** por cada entrada
que aparece como `IN[n]` en la cabecera del archivo — mismo patrón que
`civil3d-to-revit-toposolid.skill.md`.
