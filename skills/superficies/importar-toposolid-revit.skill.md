---
name: importar_toposolid_revit
description: "Importa superficies TIN de Civil 3D a Revit 2026 como Toposolid vía Dynamo: resuelve errores de Slab Shape Edit failed, elimina desplomes/estalactitas, arregla cortes de huecos de edificación a cota real y optimiza la densidad para ejecuciones en 10-15 segundos. Incluye georreferenciación exacta y configuración de resolución de curvas de nivel."
---

# Importación de Superficies Civil 3D → Revit 2026 como Toposolid

Flujo completo y validado al 100% contra el proyecto **North Island** (40 superficies/piezas, 45.908 puntos optimizados, 17 huecos de edificación).

**Resultado Alcanzado: 40/40 Toposolid Creados · 0 Errores · 0 Piezas Planas · 100% Relieve 3D Conservado · 17 Huecos Cortados a Cota Real.**

---

## 📌 Por qué esto vive en el repositorio de Civil 3D

Este laboratorio es de AutoCAD/Civil 3D, pero la verificación y entregable del terreno se realiza en **Revit 2026**: es donde el cliente, arquitectura y especialidades los consumen. El flujo nace en Civil 3D (superficies TIN), pasa por LandXML/CSV y se procesa directamente mediante la API de `Toposolid` en Revit vía Dynamo.

```
Civil 3D (TIN)  →  LandXML  →  CSV Puntos + Contornos  →  Dynamo/Python (CPython3)  →  Toposolid 3D
```

---

## ⚡ Regla de Oro: Todo lo que se pueda automatizar en archivos, NO se hace en la GUI

Armar el grafo a mano en el lienzo de Dynamo cuesta decenas de interacciones frágiles y propensas a errores. Cruzar `IN[0]` (puntos) con `IN[1]` (contornos) no lanza ningún mensaje de error pero entrega geometría corrupta.

Un archivo `.dyn` es un JSON estructurado. Se rellena por código sobre una plantilla nativa y las conexiones se realizan por GUIDs de puerto, reduciendo el trabajo manual a abrir el grafo y pulsar **Run**.

---

## 🔍 Registro de Errores Conocidos, Causas Raíz y Soluciones de Ingeniería

### 1. Error "Slab Shape Edit Failed" (Reset Shape borra el terreno y deja piezas planas)
- **Síntoma**: Revit muestra la advertencia nativa *Slab Shape Edit failed* al confirmar la transacción. Responder *Reset Shape* crea el sólido pero borra todos los puntos de elevación, dejando la pieza plana (`0.000 ft`).
- **Causa Raíz**: Puntos 3D de terreno situados coincidentemente encima de las aristas del contorno plano ($Z=0$). `SlabShapeEditor` intenta partir la arista en micro-segmentos con pendientes $> 15,000\%$, violando la restricción de frontera plana del Toposolid.
- **Solución**: Algoritmo de **Regeneración por Grilla Regular Interior** (`Shapely` + `LinearNDInterpolator`). Remuestreo de puntos a un margen de seguridad de $\text{dist} \ge 0.20\text{ ft}$ del perímetro exterior, dejando la frontera `CurveLoop` 100% libre de colisiones.

### 2. Cuello de Botella Geométrico (Pavement Surface 14)
- **Síntoma**: Piezas muy estrechas o tipo cinta fallan sistemáticamente.
- **Causa Raíz**: Estrechamiento del polígono de contorno a tan solo **0.02 ft (6 mm)**, inferior a la tolerancia mínima de modelo de Revit ($1/32'' \approx 0.031\text{ ft}$).
- **Solución**: Suavizado de polígonos mediante buffer e interpolación espacial adaptativa.

### 3. "Pámpanos de Hielo" / Estalactitas Colgantes hacia Z=0
- **Síntoma**: Triángulos verticales que cuelgan por debajo del sólido de las superficies hacia $Z=0$.
- **Causa Raíz**: Vértices de esquinas del perímetro exterior sin punto 3D asignado. Al quedar sin punto 3D en su cota exacta, Revit hace caer la arista del perímetro desde $Z=15\text{ ft}$ hasta $Z=0$.
- **Solución**: Inyección de puntos 3D de terreno exactos en **todos los vértices de contorno del perímetro exterior** (4,303 vértices amarrados en 3D en North Island).

### 4. Caída de Terreno hacia Z=0 en los Huecos de Edificación
- **Síntoma**: Las superficies forman curvas de nivel concéntricas descendentes hacia el fondo en el borde de los edificios.
- **Causa Raíz**: Los bucles interiores `HOLE` se crean planos a $Z=0$ pero carecían de puntos 3D de elevación en sus vértices.
- **Solución**: Asignación e inyección de **puntos 3D en todos los vértices de huecos de edificación** (354 puntos en 17 huecos), logrando cortes verticales limpios a cota real.

### 5. Rendimiento y Congelamiento de Interfaz (639,000 Puntos)
- **Síntoma**: Revit y Dynamo se congelan ("No responde") por más de 15 minutos.
- **Causa Raíz**: Remuestreo a 1.0 ft en superficies gigantes (> 100k sq ft) infló la matriz a 639k puntos.
- **Solución**: Densidad adaptativa inteligente (puntos originales limpios en 32 superficies sanas + grilla adaptativa en 8 problemáticas), reduciendo la matriz a **45,908 puntos** y el tiempo de ejecución a **10-15 segundos**.

---

## 📍 Georreferenciación, Coordenadas y Escalado

Para posicionar las superficies con precisión milimétrica en el modelo BIM:

* **Sistema de Coordenadas Original**: `VA83-SF` (Virginia State Plane South Zone, NAD83).
* **Unidades de Dibujo**: `US Survey Foot` (Pies de Agrimensura de EE.UU.).
* **Escala Lineal**: 1.0 (Sin escalado adicional; 1 unidad = 1 US Survey Foot).
* **Rango de Elevación Z**: Cotas topográficas reales entre `Z = 8.600 ft` y `Z = 16.700 ft`.

### Especificación de Coordenadas Compartidas en Revit
Tras ejecutar la importación en Revit:
1. Ir a **Manage** → **Coordinates** → **Specify Coordinates at Point**.
2. Seleccionar el punto de Origen (0,0,0) del modelo de Revit e ingresar:
   - **Easting (E)**: `12,119,000.000 ft`
   - **Northing (N)**: `3,530,500.000 ft`
   - **Elevation (Z)**: `0.000 ft`

> **⚠️ PRECAUCIÓN:** NO utilices las coordenadas de la variante *GEO_REVIT*. Provocaría un desfase de 24 ft en la posición espacial del proyecto.

---

## 👁️ Configuración de Resolución de Curvas de Nivel (0.1 ft y 0.5 ft)

Las curvas de nivel se configuran como un estilo visual del `ToposolidType` en Revit:
1. Seleccionar cualquier superficie `Toposolid` → **Edit Type**.
2. En la fila **Contour Display**, hacer clic en **Edit...**.
3. Ingresar las dimensiones en pulgadas (formato Imperial de Revit):
   - **Primary Contours (Curvas Mayores - 0.5 ft)**: Ingresar `6"` (o `0' 6"`).
   - **Secondary Contours (Curvas Menores - 0.1 ft)**: Ingresar `1.2"` (o `0' 1.2"`).
4. Pulsa **OK** → **Apply**. Revit renderizará las curvas de nivel densas a cada 0.1 ft y 0.5 ft.

---

## 🛑 Verificaciones de 10 Segundos Antes de Ejecutar

```powershell
Get-Process Revit          # Debe haber UNA SOLA instancia activa de Revit
python -c "import shapely, scipy"
```

1. **Una sola instancia de Revit**: Con dos instancias abiertas, Dynamo no arranca y no envía ningún mensaje de aviso.
2. **Dynamo no relanza tras cerrarlo en la misma sesión**: Si se cierra la ventana de Dynamo, reiniciar Revit antes de reabrirlo.
3. **Modo de Ejecución**: Mantener siempre `"RunType": "Manual"` en el `.dyn`.
