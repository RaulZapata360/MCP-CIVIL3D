# -*- coding: utf-8 -*-
"""
Asistente de Configuración del Servidor MCP para Revit
------------------------------------------------------
Este script facilita la clonación, compilación e integración del servidor MCP
de Revit en el laboratorio de IA.
"""

import os
import sys

def mostrar_guia_instalacion():
    print("=" * 75)
    print("   ASISTENTE DE CONFIGURACION: RECURSOS Y SERVIDOR MCP PARA REVIT")
    print("=" * 75)
    print("""
Este modulo 'revit_mcp' esta listo para conectar asistentes de IA con Revit.

PASOS RECOMENDADOS PARA ACTIVAR LA INSPECCION EN TIEMPO REAL:

1. RECOMENDACION PRINCIPAL (Sin instalacion de complementos pesados):
   - Abre Revit 2025/2026 con tu modelo (.rvt).
   - Abre Dynamo y ejecuta `ImportarToposolids.dyn` que ya dejamos precableado.
   - Ejecuta `python revit_mcp/toposolid_auditor.py` para validar los resultados.

2. PARA HABILITAR CONEXION MCP DIRECTA (IA -> Revit):
   - Repositorio recomendado: https://github.com/LuDattilo/revit-mcp-server
   - Clonar el repositorio en `revit_mcp/server/`:
     git clone https://github.com/LuDattilo/revit-mcp-server.git revit_mcp/server
   - Copiar el complemento C# (.dll) a la carpeta de add-ins de Revit:
     %APPDATA%\\Autodesk\\Revit\\Addins\\2026\\
   - Registrar la entrada en .mcp.json.

===========================================================================
""")

if __name__ == "__main__":
    mostrar_guia_instalacion()
