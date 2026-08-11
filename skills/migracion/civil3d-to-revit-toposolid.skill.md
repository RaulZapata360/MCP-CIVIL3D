---
name: civil3d-to-revit-toposolid
description: Procedimiento completo y guía técnica para migrar superficies TIN de Civil 3D a Toposolids individuales en Revit 2024/2025/2026 mediante Dynamo Python. Incluye extracción de puntos y contornos (con huecos interiores y piezas disjuntas), limpiador geométrico en 3 pasadas para evitar errores de auto-intersección (foldbacks) y tolerancia de líneas (ShortCurveTolerance), silenciador seguro de warnings (WarningSwallower), reanudación automática por comentarios, guardado incremental pieza a pieza, diagnóstico de relieve y traslación por vector de coordenadas de control (OFFSET_X/OFFSET_Y).
---

# Civil 3D → Revit Toposolid Migration (via Dynamo & Python)

## 📌 1. Descripción General y Arquitectura

Esta Skill define el procedimiento completo para migrar superficies TIN complejas (caminos, pavimentos, movimiento de tierras, terrenos) exportadas desde **Civil 3D (LandXML)** hacia objetos **Toposolid reales e independientes en Revit (versiones 2024, 2025, 2026)** mediante **Dynamo Python (CPython3)**.

### ¿Por qué NO usar la triangulación directa o archivos DWG/Puntos de Revit?
- **Triangulación Delaunay en Revit**: Si solo se importan los puntos, Revit aplica una triangulación estándar que llena el *hull convexo*, cortando líneas rectas sobre curvas y destruyendo la forma exacta de pasillos/corredores.
- **Toposolid con Contorno Real (CurveLoop)**: Esta metodología le pasa a Revit **tanto la nube de puntos 3D como el contorno real exterior e interior (con huecos/islas y piezas separadas)**, garantizando que el `Toposolid` resultante respete 100% la geometría civil.

---

## 🛠️ 2. Procedimiento Paso a Paso para el Asistente IA (Crear Dynamo desde una Nueva Superficie)

Cuando se requiera crear o migrar un proyecto con una nueva superficie o conjunto de superficies desde Civil 3D a Revit, el asistente IA debe seguir exactamente este flujo de 5 pasos:

### Paso 1: Exportar LandXML desde Civil 3D
1. En Civil 3D, exportar las superficies seleccionadas a un archivo `.xml` (LandXML).
2. Si se trata de múltiples superficies del mismo proyecto, exportarlas todas en un único archivo LandXML para mantener la consistencia espacial y de origen.

### Paso 2: Extraer Puntos 3D y Contornos Reales en CSV (Python)
Ejecutar el script extractor `extract_for_revit.py` (o módulo equivalente) que procesa la estructura del LandXML y genera dos archivos CSV de intercambio:
- **CSV 1: `All_Points_ByPiece.csv`**:
  `SurfaceName,PieceId,X,Y,Z`
- **CSV 2: `All_Boundaries_Complete.csv`**:
  `SurfaceName,PieceId,RingType,RingId,Seq,X,Y`
  *(Donde `RingType` es `OUTER` para el contorno exterior y `HOLE` para huecos interiores).*

### Paso 3: Configurar el Grafo de Dynamo (.dyn)
1. En Dynamo, crear un nuevo script con la estructura recomendada:
   - **Nodo `File Path` (IN[0])**: Apuntando a `All_Points_ByPiece.csv`.
   - **Nodo `File Path` (IN[1])**: Apuntando a `All_Boundaries_Complete.csv`.
   - **Nodo `Python Script`**: Con el motor configurado en **CPython3**.

### Paso 4: Ajustar Parámetros Principales en el Código Python
Dentro del código Python del nodo de Dynamo, configurar los siguientes parámetros:
- `NOMBRE_TIPO`: Nombre del tipo de Toposolid en Revit (ej: `'Carpeta Asfaltica - 1.00ft'`).
- `ESPESOR_FT`: Espesor del sólido en pies (ej: `1.00` ft).
- `MIN_SEG_LEN`: Longitud mínima inicial de segmento (ej: `0.05` o `0.1` ft).
- `OFFSET_X` y `OFFSET_Y`: Desfase de traslación hacia el modelo de Revit (ver Sección 4).
- `SAVE_FILE_PATH`: Ruta para guardado automático o dejar `""` para guardar sobre el documento activo.

### Paso 5: Ejecución y Verificación del Log
- Presionar **Run / Ejecutar** en Dynamo.
- Al finalizar, leer inmediatamente el archivo de diagnóstico `dynamo_log.txt` generado automáticamente junto a los CSV para verificar:
  - `CREADAS EN ESTA SESION (N)`
  - `YA EXISTIAN, OMITIDAS PARA NO DUPLICAR (M)`
  - `ERRORES (0)`

---

## 🛑 3. Catálogo de Errores Resueltos y Advertencias Evitadas (Gotchas & Fixes)

Este catálogo documenta los errores de Revit API, CPython3 y Dynamo que fueron identificados y resueltos, con sus soluciones obligatorias que todo asistente IA debe aplicar:

### ❌ Error 1: Auto-intersecciones de Contorno y Pliegues de $180^\circ$ (Foldbacks)
- **Mensaje de Revit**: `The input curve loops cannot compose a valid boundary... some curve loops intersect with each other.`
- **Causa**: Las fronteras exportadas desde Civil 3D suelen contener vértices donde la línea avanza y regresa inmediatamente sobre sí misma (pliegues de $180^\circ$ o picos auto-solapados).
- **Solución Obligatoria (Pasada 2 del limpiador `build_loop`)**:
  Calcular el ángulo vectorial entre vértices consecutivos $p_1, p_2, p_3$. Si el ángulo entre $\vec{v}_1$ y $\vec{v}_2$ es $\ge 170^\circ$, eliminar el vértice $p_2$. Repetir iterativamente hasta que el contorno no tenga ningún pliegue.

### ❌ Error 2: Tolerancia de Longitud de Línea Corta (`ShortCurveTolerance`)
- **Mensaje de Revit**: `Curve length is too small for Revit's tolerance (as identified by Application.ShortCurveTolerance).`
- **Causa**: Vértices en el contorno separados por menos de $0.0052\text{ ft}$ (1.5 mm). Suele ocurrir tras remover pliegues en la Pasada 2 si los puntos extremos quedaron muy próximos.
- **Solución Obligatoria (Pasada 3 del limpiador `build_loop`)**:
  Re-evaluar el contorno tras la eliminación de pliegues y eliminar cualquier micro-segmento residual menor a $0.01\text{ ft}$.
  *(Garantiza que la longitud mínima de todas las líneas sea $> 0.03\text{ ft}$, muy superior a la tolerancia de Revit).*

### ❌ Error 3: Incompatibilidad de Herencia .NET en CPython3 (`WarningSwallower`)
- **Mensaje de Dynamo/Python**: `TypeError: cannot create instances of WarningSwallower` o fallos en el binding de `IFailuresPreprocessor`.
- **Causa**: En Dynamo Revit 2025/2026 con CPython3, heredar directamente de la interfaz .NET `DB.IFailuresPreprocessor` puede fallar durante la instanciación en tiempo de ejecución.
- **Solución Obligatoria (Wrapper Seguro `try...except`)**:
  ```python
  swallower = None
  try:
      class WarningSwallower(DB.IFailuresPreprocessor):
          def PreprocessFailures(self, failuresAccessor):
              for f in failuresAccessor.GetFailureMessages():
                  try:
                      sev = f.GetSeverity()
                      if sev == DB.FailureSeverity.Warning:
                          failuresAccessor.DeleteWarning(f)
                      elif sev == DB.FailureSeverity.Error:
                          failuresAccessor.ResolveFailure(f)
                  except Exception:
                      pass
              return DB.FailureProcessingResult.Continue
      swallower = WarningSwallower()
  except Exception:
      swallower = None
  ```
  Y al iniciar transacciones:
  ```python
  if swallower is not None:
      try:
          opts = t_piece.GetFailureHandlingOptions()
          opts.SetFailuresPreprocessor(swallower)
          t_piece.SetFailureHandlingOptions(opts)
      except Exception:
          pass
  ```

### ❌ Error 4: Referencias Inválidas en Diagnóstico (`The referenced object is not valid`)
- **Mensaje de Revit/Python**: `The referenced object is not valid, possibly because it has been deleted from the database, or its creation was undone.`
- **Causa**: Intentar inspeccionar las propiedades de un `Element` en Python después de un rollback o cuando la referencia del objeto transitorio se invalidó.
- **Solución Obligatoria**:
  ```python
  el = doc.GetElement(eid)
  if el is None or not getattr(el, 'IsValidObject', True):
      continue
  ```

### ❌ Error 5: Huecos Interiores que Tocan o Solapan el Contorno Exterior
- **Mensaje de Revit**: `The input curve loops cannot compose a valid boundary... some curve loops intersect with each other.`
- **Causa**: En superficies de terreno de Civil 3D, algunos bucles de huecos (`HOLE`) comparten vértices o bordes directamente sobre el perímetro exterior (`OUTER`) (distancia $= 0.0000\text{ ft}$). La API de Revit exige que todos los huecos interiores sean **estrictamente disjuntos** de la frontera exterior.
- **Solución Obligatoria**:
  Medir la distancia espacial mínima entre el bucle del hueco y el perímetro exterior (`min_dist_loop_to_loop`). Si la distancia es $< 0.05\text{ ft}$, omitir ese hueco de la colección `profiles` para permitir que el `Toposolid` se cree sin errores.

### ⚠️ Advertencia Informada: "Thickness of this Toposolid may be slightly inaccurate due to extreme Shape Editing"
- **Significado**: Es un aviso puramente informativo de Revit cuando un Toposolid plano se deforma con alta pendiente en 3D.
- **Acción**: Absolutamente inocuo. El elemento se crea correctamente con su relieve intacto. El `WarningSwallower` lo absorbe automáticamente.

---

## 🔄 4. Traslación Espacial y Acoplamiento a Modelos de Revit (`OFFSET_X` / `OFFSET_Y`)

Cuando las superficies se deben acoplar a un archivo `.rvt` ya existente con un sistema de coordenadas específico:

1. Pedir al usuario 3 vértices de control medidos en la importación inicial de Dynamo ($E_{\text{origen}}, N_{\text{origen}}$) y sus 3 vértices correspondientes en el modelo objetivo de Revit ($E_{\text{destino}}, N_{\text{destino}}$).
2. Calcular el vector de traslación constante para cada par:
   $$\text{OFFSET\_X} = E_{\text{destino}} - E_{\text{origen}}$$
   $$\text{OFFSET\_Y} = N_{\text{destino}} - N_{\text{origen}}$$
3. Verificar que $\Delta E$ y $\Delta N$ sean idénticos en los 3 puntos controlados.
4. Escribir `OFFSET_X` y `OFFSET_Y` en las constantes globales del script Python de Dynamo.

---

## ⚡ 5. Código Python Completo de Referencia para Dynamo (`build_loop` en 3 Pasadas)

A continuación se muestra el algoritmo de construcción de contornos sin errores:

```python
def build_loop(seq_pts):
    """Construye un CurveLoop cerrado y plano en Z=0.
    Aplica limpiador en 3 pasadas:
    1. Distancia consecutiva inicial (>= MIN_SEG_LEN)
    2. Eliminación de pliegues/picos auto-solapados (>= 170 deg)
    3. Eliminación final de micro-segmentos (< 0.01 ft)
    """
    import math
    pts = [p for _, p in sorted(seq_pts, key=lambda t: t[0])]
    if len(pts) < 3:
        return None

    # 1. Pasada 1: Filtrado inicial por distancia minima
    cleaned = [pts[0]]
    for p in pts[1:]:
        if cleaned[-1].DistanceTo(p) >= MIN_SEG_LEN:
            cleaned.append(p)
    while len(cleaned) > 1 and cleaned[0].DistanceTo(cleaned[-1]) < MIN_SEG_LEN:
        cleaned.pop()
    if len(cleaned) < 3:
        return None

    # 2. Pasada 2: Eliminar pliegues / picos auto-solapados (foldbacks >= 170 deg)
    changed = True
    while changed and len(cleaned) >= 3:
        changed = False
        n = len(cleaned)
        to_remove = set()
        for i in range(n):
            p1 = cleaned[i]
            p2 = cleaned[(i + 1) % n]
            p3 = cleaned[(i + 2) % n]
            v1_x, v1_y = p2.X - p1.X, p2.Y - p1.Y
            v2_x, v2_y = p3.X - p2.X, p3.Y - p2.Y
            len1 = math.hypot(v1_x, v1_y)
            len2 = math.hypot(v2_x, v2_y)
            if len1 < 0.01 or len2 < 0.01:
                to_remove.add((i + 1) % n)
                changed = True
                break
            dot = (v1_x * v2_x + v1_y * v2_y) / (len1 * len2)
            dot = max(-1.0, min(1.0, dot))
            angle = math.degrees(math.acos(dot))
            if angle >= 170.0:
                to_remove.add((i + 1) % n)
                changed = True
                break
        if changed:
            cleaned = [p for idx, p in enumerate(cleaned) if idx not in to_remove]

    # 3. Pasada 3: Limpieza final de micro-segmentos residuales (< 0.01 ft)
    changed = True
    while changed and len(cleaned) >= 3:
        changed = False
        n = len(cleaned)
        for i in range(n):
            p1 = cleaned[i]
            p2 = cleaned[(i + 1) % n]
            if p1.DistanceTo(p2) < 0.01:
                cleaned.pop((i + 1) % n)
                changed = True
                break

    if len(cleaned) < 3:
        return None

    loop = CurveLoop()
    n = len(cleaned)
    for i in range(n):
        loop.Append(Line.CreateBound(cleaned[i], cleaned[(i + 1) % n]))
    return loop
```
