# Informe de Auditoría y Estado de Revisión del Plugin MCP Civil 3D

**Fecha de Evaluación:** 02 de Agosto de 2026  
**Entorno:** Autodesk Civil 3D 2026 (.NET 8.0 / C# Plugin `Civil3DMcpPlugin.dll`)  
**Dictamen General:** ⚠️ **EN REVISIÓN / NO RECOMENDADO PARA USO EN PRODUCCIÓN SEVERA (WORK IN PROGRESS)**

---

## 📌 Resumen Ejecutivo

Tras realizar una batería de pruebas de integración directa entre el protocolo MCP, scripts de automatización Python y el dibujo activo en Autodesk Civil 3D (`Superficie_cargas_xml.dwg`), se han identificado inconsistencias técnicas, limitaciones en la API de Autodesk y fallas de renderizado gráfico que impiden declarar esta herramienta lista para proyectos de ingeniería de producción.

---

## 🔍 Hallazgos Técnicos y Deficiencias Identificadas

### 1. Creación e Interacción de Vista de Perfil (`ProfileView.Create`) — **[ESTADO: FALLA]**
* **Incompatibilidad de Overloads en la API de Civil 3D 2026:** El método de reflexión `ProfileView.Create` presenta incompatibilidades de firma de parámetros entre versiones .NET de Autodesk Civil 3D, provocando excepciones nulas en transacciones en segundo plano.
* **Falta de Encuadre/Focus Gráfico:** Los objetos de vistas de perfil insertados mediante el protocolo MCP se crean en la base de datos del archivo `.dwg`, pero AutoCAD no actualiza automáticamente la cámara visual ni ejecuta un `ZOOM EXTENTS`, dejando la grilla fuera del campo de visión del operador humano.

### 2. Creación y Eliminación de Alineamientos (`createAlignment` / `deleteAlignment`) — **[ESTADO: WIP]**
* **Polilíneas Huérfanas de AutoCAD:** Al crear un alineamiento a partir de una polilínea o conjunto de PIs y posteriormente invocar `deleteAlignment`, Civil 3D remueve la entidad de alineamiento del *Prospector*, pero la entidad gráfica base (`Polyline` / `Polyline3d`) permanece dibujada en el modelo de AutoCAD, produciendo desorientación visual y entidades residuales en el espacio de trabajo.
* **Coordenadas Rígidas / Desfasadas:** Los intentos iniciales de generación paramétrica utilizaron puntos no adaptados a la caja envolvente real del proyecto activo, requiriendo módulos adicionales de corrección de coordenadas relativas (`coordinate_utils.py`).

### 3. Sincronización Gráfica y Renderizado en Tiempo Real — **[ESTADO: WIP]**
* **Falta de Rediseño Automático (`Regen`):** La ejecución de comandos mediante el flujo MCP en segundo plano (`CommandContext`) no gatilla el repintado de pantalla del *Viewport* de AutoCAD hasta que el usuario interactúa manualmente con el mouse o la consola (`REGENALL`), dando la falsa impresión de que los elementos no fueron generados.

---

## 📊 Matriz de Evaluación de Herramientas Afectadas

| Herramienta MCP | Versión C3D | Estado Auditado | Observación / Causa Raíz |
| :--- | :---: | :---: | :--- |
| `create_alignment` | 2026 | **WIP** | Requiere eliminación manual de polilíneas residuales en CAD. |
| `create_profile_view` | 2026 | **FALLA** | Incompatibilidad de firmas .NET y falta de foco automático en pantalla. |
| `sample_profile_elevations` | 2026 | **WIP** | Correcto en datos numéricos; falla en la renderización directa de pantalla. |
| `delete_alignment` | 2026 | **WIP** | Deja objetos gráficos nativos de AutoCAD sin depurar en ModelSpace. |

---

## 📋 Conclusión y Recomendación

Se procede a registrar de forma oficial esta evaluación en la matriz de control de calidad del repositorio (`verificacion/matriz.csv`) y en el dashboard de auditoría (`dashboard.html`).

**Recomendación:** Se prohíbe el uso de este conjunto de herramientas MCP para entregables definitivos o modificaciones directas en planos de producción hasta que se resuelva la capa de renderizado nativo y la compatibilidad completa de la API de Civil 3D 2026.
