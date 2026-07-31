---
trigger: always_on
description: Regla de enrutamiento y uso de mecanismos del ecosistema Civil3D-MCP.
---

## Clasificación de Mecanismos de Herramientas

Cuando interactúes con el repositorio `civil3d-mcp-lab`, debes clasificar las herramientas disponibles en 3 categorías bien diferenciadas:

1. **Herramientas de Ejecución en Civil 3D (MCP Server en `server/`):**
   - Invocadas mediante protocolo MCP (`civil3d_...`).
   - Se ejecutan en tiempo real contra el proceso de Autodesk Civil 3D abierto.
   - Usar para consultar o modificar el plano `.dwg`.

2. **Skills y Conocimiento de Dominio (`skills/` y `.agents/`):**
   - Documentos Markdown con heurísticas de ingeniería y diseño.
   - Se leen antes de ejecutar acciones paramétricas para saber qué criterios y fórmulas aplicar.

3. **Herramientas de Auditoría y QA (`verificacion/` y `dashboard.html`):**
   - Matriz `matriz.csv` y script `update_dashboard.py`.
   - Se usan para evaluar y reportar el estado de salud de las herramientas MCP.
