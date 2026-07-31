---
name: revision_curvas_verticales
description: "Revisión de curvas verticales y valores K en perfiles longitudinales de Civil 3D según criterios de diseño vial y normativas configurables."
---

# Revisión de Curvas Verticales contra Criterio de Diseño Vial

Este skill permite realizar una revisión automatizada de la geometría de curvas verticales en alineaciones y perfiles longitudinales de Civil 3D, contrastando los parámetros obtenidos contra los límites mínimos de diseño vial o la normativa aplicable que se defina.

## Cuándo usar
Revisión de rasantes viales nuevas o de terceros antes de emitir planos definitivos o informes de aprobación de trazado longitudinal.

## Entradas requeridas
*   `nombre_alineamiento` (string): Nombre del eje en el dibujo.
*   `velocidad_diseno` (number): Velocidad de diseño del tramo en km/h (ej: 50, 80, 100).
*   `tipo_via` (string): Tipo de vía (`Urbana`, `Rural`, `Local`) para determinar pendientes máximas.
*   `normativa` (string, opcional): Normativa o tabla de criterios a aplicar.

## Criterios aplicados (Parámetros de Diseño Vial)

### 1. Parámetros K Mínimos (Distancia de Visibilidad de Parada)
El parámetro K ($K = L/A$, donde $L$ es la longitud de la curva en metros y $A$ es la diferencia algebraica de pendientes en %) debe cumplir con los siguientes pisos prácticos:

| Velocidad de Diseño (km/h) | K Mínimo Convexa (Cresta) | K Mínimo Cóncava (Sagrario) |
|:--------------------------:|:-------------------------:|:--------------------------:|
|             30             |             2             |             4              |
|             40             |             4             |             6              |
|             50             |             7             |             9              |
|             60             |            11             |            13              |
|             80             |            26             |            22              |
|            100             |            52             |            32              |
|            120             |            95             |            43              |

### 2. Longitud Mínima de Curva
Para evitar quiebres bruscos en la rasante, la longitud mínima de la curva vertical ($L_{min}$) se calcula como:
$$L_{min} = 0.6 \times V_d$$
Donde $V_d$ es la velocidad de diseño en km/h.

---

## Código de Referencia / Flujo en C# (in-process)

Para acceder a los PVI (Puntos de Intersección Vertical) y extraer los datos de curvatura en Civil 3D, el modelo adaptará el siguiente flujo utilizando la API .NET:

```csharp
// Obtener el documento activo y la base de datos
CivilDocument doc = CivilApplication.ActiveDocument;
using (Transaction trans = HostApplicationServices.WorkingDatabase.TransactionManager.StartTransaction())
{
    // Buscar la alineación por nombre
    ObjectId alignId = doc.GetAlignmentIds()[0]; // Reemplazar por búsqueda por nombre
    Alignment align = trans.GetObject(alignId, OpenMode.ForRead) as Alignment;
    
    // Obtener perfiles de la alineación
    foreach (ObjectId profileId in align.GetProfileIds())
    {
        Profile profile = trans.GetObject(profileId, OpenMode.ForRead) as Profile;
        if (profile.ProfileType == ProfileType.Design)
        {
            // Recorrer los PVI
            ProfilePVICollection pvis = profile.PVIs;
            for (int i = 0; i < pvis.Count; i++)
            {
                ProfilePVI pvi = pvis.GetPVIAt(i);
                // Extraer geometría de curva si el PVI es curvo
                if (pvi.EntityId != null) {
                    // Calcular diferencias algebraicas y valores K
                }
            }
        }
    }
}
```

## Falsos positivos conocidos
*   **Zonas de Intersección / Rotondas:** En empalmes y zonas de velocidad controlada a paso de peatón se permiten valores K inferiores por condiciones de borde urbano. Estos casos deben marcarse en el reporte pero se revisan a criterio del proyectista.
*   **Tangentes verticales muy cortas:** Tramas de pendiente constante de menos de 10 metros entre curvas consecutivas pueden levantar falsas alarmas de longitud mínima.
