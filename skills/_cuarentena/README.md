# ⚠️ Cuarentena — herramientas que NO se deben usar sin leer esto

Estos scripts **funcionan** en el sentido de que se ejecutan sin error. El problema es lo
que hacen. Están aquí, y no en `skills/`, porque cada uno destruyó geometría real en este
proyecto o quedó superado por un método mejor.

No se borraron porque su código sigue siendo útil como punto de partida, y porque saber
*por qué* fallaron es tan valioso como el código que los reemplaza.

---

## `merge_clipped_surfaces.py` — MUTILA la superficie

**Qué pretende:** combinar N superficies ya recortadas en una sola *watertight*, soldando
por proximidad donde se tocan y rellenando las costuras angostas.

**Qué pasa en realidad:** el resultado sale **peor que el problema original**. La
soldadura por proximidad y el relleno de costuras se comen geometría legítima.

**No lo uses para volver a unir lo recortado.** Si necesitas una entrega unida, revisa
primero si de verdad hace falta una sola superficie: en este proyecto casi siempre era
mejor entregar las piezas por separado.

---

## `mesh_grouped_top_only.py` — elimina superficies enteras

**Qué pretende:** agrupar mallas por huella XY, quedarse con la más alta de cada grupo y
resolver los solapes entre grupos.

**Qué pasa en realidad:** su docstring lo dice sin rodeos —

> si dos superficies comparten puntos XY y una está consistentemente por ENCIMA de la
> otra, la de ABAJO **se descarta por completo (no se recorta, se elimina la superficie
> entera)**

Con `min_overlap_pct=20.0`, basta que se solapen un 20 % para que la de abajo desaparezca
**íntegra**, incluido el 80 % que no solapaba con nada.

Caso medido en South Island (`SI_CV_SURFACE_DXF.dxf`): dos mallas con 15.424 ft² de
solape — el 71 % de la de abajo, que rondaba los 21.700 ft². Aplicar la regla habría
borrado también ~6.300 ft² de superficie limpia. Y el desnivel entre ambas no era
constante (0,01–2,46 ft), lo que indica que **no** eran dos capas del mismo paquete sino
dos superficies distintas: exactamente el caso que hay que consultar, no automatizar.

Además construye sus avisos sobre `crossing_count()`, que devuelve `None` por encima de
6.000 aristas y se lee igual que "0 cruces".

**Si aun así lo necesitas:** ejecútalo, lee la lista `DESCARTADA:` que imprime, y verifica
una por una que cada superficie eliminada sobraba de verdad.

---

## `unify_shared_borders.py` — superado, falla 53 de 67

**Qué pretende:** que dos superficies vecinas compartan el mismo límite, reemplazando cada
pareja de bordes "casi pegados" por su línea media.

**Por qué no funciona:** arregla cada pareja ignorando al resto. Al mover un borde para
casarlo con un vecino se rompe el acuerdo con el vecino del otro lado. Resultado: **53 de
67 casos terminan en autointersección**.

**Qué usar en su lugar:** partición planar — meter todos los bordes en un grafo planar y
reconstruir las caras con `polygonize`. Por construcción cada arista existe una sola vez.
Ver `skills/superficies/particion-de-superficies.skill.md`; la implementación de
referencia es `planar_partition.py` en `HRCP\CIVIL 3D\Scripts_Migracion\`.

---

## Regla general que sale de los tres

Los tres comparten el mismo patrón: **resolver un conflicto geométrico borrando uno de los
lados.** Es rápido, deja métricas agregadas impecables y destruye trabajo real.

Antes de aceptar cualquier limpieza automática:

1. Mide el área **real** del conflicto, no el número de incidencias.
2. Mira la **forma**: un roce de triangulación no se parece a un solape de verdad.
3. **Míralo en pantalla.** Un "0 huecos" ya convivió aquí con una superficie destrozada.
