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

Sigue estas directivas para asegurar que el repositorio funcione de forma fluida y sin configuración manual.
