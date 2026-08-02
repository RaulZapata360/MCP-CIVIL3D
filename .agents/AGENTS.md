# Guía de Inicialización para Asistentes IA (Onboarding)

¡Hola, Asistente IA! Si es la primera vez que abres este repositorio en una nueva máquina o sesión, sigue estas reglas de inicialización ESTRICTAMENTE antes de interactuar con el usuario o realizar tareas complejas:

## 1. Setup del Entorno
Si notas que el proyecto no ha sido inicializado en la máquina del usuario (por ejemplo, faltan dependencias de Python o Node.js):
- Recomienda o ejecuta el script `setup_workspace.bat` que se encuentra en la raíz del repositorio. 
- Este script configurará de forma portátil las rutas en `.mcp.json` usando un wrapper, e instalará los paquetes necesarios.

## 2. Comprensión del Contexto (Graphify)
El contexto y la arquitectura completa de este repositorio ya ha sido procesada previamente mediante Graphify y los resultados están en la carpeta `graphify-out/`.
- **NO adivines la arquitectura.** Utiliza inmediatamente tu herramienta/skill `graphify-windows` para consultar el estado del proyecto, los nodos y cómo se relacionan las skills entre sí.
- Esto te dará el contexto operativo instantáneo para saber qué hace cada script dentro de la carpeta `skills/`.

## 3. Oferta de Herramientas
Una vez que hayas leído el contexto y el entorno esté configurado:
- Infórmale al usuario que estás listo.
- Ofrécele usar cualquiera de las herramientas/skills disponibles en la carpeta `skills/`, o recomiéndale abrir el dashboard interactivo ejecutando `iniciar_laboratorio.bat`.

## 4. Referenciación y Coordenadas Dinámicas del Proyecto (REGLA MANDATORIA)
- **Cero Coordenadas 'Hardcoded':** Queda estrictamente prohibido usar valores numéricos fijos o adivinados para coordenadas (X, Y) al crear o posicionar entidades en Civil 3D.
- **Obtención Dinámica del Envolvente (Bounding Box):** Antes de crear cualquier alineamiento, perfil, vista de perfil o etiqueta, la IA debe consultar el *Bounding Box* (`minX`, `minY`, `maxX`, `maxY`) de la superficie activa o dibujo en tiempo real.
- **Ubicación Proporcional:** Todas las entidades (como Vistas de Perfil o Anotaciones) deben posicionarse con offsets relativos respecto al ancho/alto real de la superficie del proyecto activo (usando `skills/geometria/scripts/coordinate_utils.py`).

## 5. Protocolo Obligatorio de Registro y Auditoría QA (`verificacion/matriz.csv`) (REGLA MANDATORIA)
Cualquier Asistente de IA que realice pruebas, modificaciones, compilaciones o validaciones sobre herramientas MCP o planos de Civil 3D DEBE seguir esta secuencia de registro sin excepción:
1. **Registro Inmediato en Matriz:** Al finalizar o auditar cada prueba (tanto si resulta en `OK`, `WIP` o `FALLA`), agregar una fila descriptiva en `verificacion/matriz.csv` indicando: `servidor,tool,version_c3d,dwg_prueba,resultado,evidencia,fecha,notas`.
2. **Sincronización del Dashboard:** Ejecutar inmediatamente `python update_dashboard.py` para actualizar los gráficos y tablas en `dashboard.html`.
3. **Creación de Informe de Evidencia:** Toda prueba o hallazgo relevante debe documentarse con su archivo de evidencia (.md o .html) en la carpeta con la fecha del día `verificacion/DD-MM-YYYY/`.

## 6. Protección de Datos, Confidencialidad y Anonimización (REGLA MANDATORIA)
- **Anonimización de Ubicaciones y Clientes:** Queda estrictamente prohibido guardar en informes HTML, archivos Markdown, la matriz CSV o logs del sistema nombres reales de ubicaciones geográficas, sitios específicos, países o clientes.
- **Nombres Genéricos:** Usar siempre nombres genéricos y neutrales (ej. `Proyecto_Definitivo.dwg`, `TODAS_Superficies_Proyecto.xml`, `Sitio_Estudio`, `Superficie_Base`).
- **Resguardo de Coordenadas Absolutas:** No publicar ni exponer coordenadas geográficas reales del cliente en reportes públicos o documentación compartida; utilizar coordenadas relativas o descriptivas.

## 7. Auditoría Rigurosa de Unidades y Metadatos Topográficos ("Razonar Antes de Actuar") (REGLA MANDATORIA)
- **Cero Suposiciones de Unidades:** Queda estrictamente prohibido asumir o adivinar las unidades de medida (metros vs. pies). La IA debe inspeccionar siempre y explícitamente el encabezado del archivo insumo (`<Units>` en LandXML) o las propiedades del dibujo en Civil 3D (`Database.LinearUnits`) ANTES de calcular volúmenes, áreas o cotas.
- **Declaración de Sistema de Medición:** Todo análisis debe declarar el sistema nativo del proyecto (`Imperial`: `foot`, `squareFoot`, `cubicYard` vs. `Metric`: `meter`, `squareMeter`, `cubicMeter`) y presentar los resultados en las unidades nativas principales, incluyendo la conversión secundaria si aplica.

## 8. Patrón Estándar para Informes Técnicos HTML (REGLA MANDATORIA)
- **Estándar Documento Técnico:** Todo informe de análisis, estudio topográfico, cubicación o auditoría DEBE generarse automáticamente como un archivo HTML autocontenido (estilo hoja de papel clara, serif editorial Georgia para títulos, paleta sobria petróleo `--accent: #0e5563`, sin emojis ni glows informales en contextos formales).
- **Estructura Requerida:** Bloque de identificación viñeta (`.titleblock`), resumen numérico (`.stats`), esquema visual en planta 2D (SVG), perfiles transversales con áreas de corte/relleno sombreadas (SVG), tabla de cómputos volumétricos (`td.num`) y bloques de hallazgos/recomendaciones (`.finding`).
- **Soporte de Impresión (PDF):** Conservar el bloque `@media print` con reglas `break-inside: avoid` y saltos de página delibardos (`<div class="page-break"></div>`).

## 9. Registro Automatizado de Telemetría y Uso de Skills (REGLA MANDATORIA)
- **Contador de Uso por Skill:** Cada vez que el asistente utilice o aplique los criterios de una habilidad de la carpeta `skills/`, debe registrar el evento ejecutando `python verificacion/track_usage.py --skill <nombre_skill> [--status OK/WIP/FALLA]`.
- **Métricas de Confiabilidad:** Los conteos de uso se consolidan dinámicamente en `verificacion/skill_usage.json` y se despliegan en el dashboard (`http://localhost:8000/dashboard.html`), ordenando las habilidades por frecuencia de uso y nivel de confiabilidad (`🔥 Alta`, `⚡ Media`, `🔹 Inicial`).

## 10. Registro Obligatorio de Bitácora de Sesión, Correcciones y Limitaciones (REGLA MANDATORIA)
- **Cierre Obligatorio de Sesión:** Cada Asistente de IA que trabaje en este repositorio DEBE registrar una entrada detallada en la bitácora de sesiones ejecutando:
  `python verificacion/track_usage.py --log-session --task "<tarea>" --corrections "<correcciones>" --warnings "<advertencias>" --limitations "<limitaciones>" --status "<OK/WIP/FALLA>"`
- **Campos Requeridos en la Bitácora:**
  1. `tarea`: Uso o análisis realizado en la sesión.
  2. `correcciones`: Ajustes de código, correcciones de unidades o parches aplicados.
  3. `advertencias`: Hallazgos críticos de unidades, datos o riesgos de diseño.
  4. `limitaciones`: Restricciones o bugs descubiertos en herramientas MCP / Civil 3D 2026.
- **Sincronización:** Todas las entradas se archivan en `verificacion/session_logs.json` y alimentan automáticamente la bitácora visual desplegada en `http://localhost:8000/dashboard.html`.

Sigue estas directivas para asegurar que el repositorio funcione de forma fluida y sin configuración manual.
