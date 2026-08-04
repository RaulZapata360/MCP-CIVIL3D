# 🏗️ Módulo de Inspección y Servidor MCP para Autodesk Revit

Este módulo proporciona la estructura, guía de instalación y scripts de auditoría para conectar asistentes de IA (mediante **Model Context Protocol - MCP**) con modelos activos de **Autodesk Revit** (versiones 2023, 2024, 2025 y 2026).

---

## 🎯 Propósito del Módulo

1. **Inspección de Salud del Modelo Revit:** Detectar advertencias (*warnings*), elementos duplicados, familias pesadas y errores de geometría.
2. **Auditoría de Superficies (Toposolid):** Verificar cotas, áreas, volúmenes, contornos y huecos de edificación en el modelo `.rvt` activo.
3. **Conexión MCP en Tiempo Real:** Permitir a la IA ejecutar consultas estructuradas directamente sobre el documento abierto en Revit.

---

## ⚙️ Arquitectura del Servidor MCP para Revit

```
+------------------+         MCP (stdio/WebSocket)        +------------------------+
|  IA / Assistant  | <=================================> | Servidor MCP (Node/Py) |
+------------------+                                      +------------------------+
                                                                      ||
                                                            Named Pipe / Local Socket
                                                                      ||
                                                          +------------------------+
                                                          | Plugin C# Revit Add-in |
                                                          +------------------------+
                                                                      ||
                                                           Revit ExternalEvent API
                                                                      ||
                                                          +------------------------+
                                                          | Modelo Activo (.rvt)   |
                                                          +------------------------+
```

---

## 🚀 Repositorios MCP Recomendados e Instalación

### Opción A: Servidor MCP Completo de Auditoría (`revit-mcp-server`)
- **Repositorio:** [LuDattilo/revit-mcp-server](https://github.com/LuDattilo/revit-mcp-server) o [omarabdelazizeng-sketch/oa-aec-mcp](https://github.com/omarabdelazizeng-sketch/oa-aec-mcp)
- **Herramientas que aporta:**
  - `get_warnings`: Obtiene la lista completa de advertencias del modelo con IDs de elementos.
  - `get_element_info`: Consulta parámetros, tipo, nivel y categoría de cualquier elemento.
  - `audit_toposolids`: Analiza el relieve, elevación mínima/máxima y huecos en elementos Toposolid.
  - `get_model_stats`: Resumen general de conteo de familias, vistas y masa del proyecto.

### Opción B: Integración Ligera vía pyRevit (`RevitMCP`)
- **Repositorio:** [oakplank/RevitMCP](https://github.com/oakplank/RevitMCP)
- **Requisito:** Tener instalado `pyRevit`.
- **Instalación:** Clonar la extensión dentro de la carpeta de extensiones de `pyRevit` (`%appdata%\pyRevit\Extensions`).

---

## 📁 Archivos de este Módulo

- `README.md`: Esta guía de arquitectura e instalación.
- `setup_revit_mcp.py`: Script asistido para descargar e integrar el servidor MCP de Revit con `.mcp.json`.
- `toposolid_auditor.py`: Script local para validar reportes de exportación y geometría de superficies antes de la importación.

---

## 📌 Configuración en `.mcp.json` (Ejemplo)

> [!IMPORTANT]
> Usa **siempre rutas relativas a la raíz del repositorio**. Claude Code resuelve las rutas
> del `.mcp.json` desde la carpeta del proyecto, así que evitamos rutas absolutas para que
> el repo funcione igual al clonarlo en otro PC.

```json
{
  "mcpServers": {
    "revit-mcp": {
      "command": "node",
      "args": ["./revit_mcp/server/dist/index.js"],
      "env": {
        "REVIT_VERSION": "2026"
      }
    }
  }
}
```
