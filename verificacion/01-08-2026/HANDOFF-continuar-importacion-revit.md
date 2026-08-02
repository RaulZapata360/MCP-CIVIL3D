# PROMPT DE CONTINUACIÓN — Importación Civil 3D → Revit (Toposolid)

Copia todo este archivo como primer mensaje al asistente que continúe.

---

## Objetivo

Exportar 40 superficies TIN de Civil 3D (proyecto North Island) a Revit 2026 como
Toposolid, vía Dynamo. **El trabajo está terminado cuando una ejecución produzca
40 Toposolid, 0 errores y 0 piezas planas**, y el modelo se pueda recorrer en 3D
con todas las superficies mostrando su relieve real. Nada menos que eso.

## Lee esto primero

1. `skills/superficies/importar-toposolid-revit.skill.md` — el flujo completo,
   las coordenadas de UI ya programadas y todas las trampas conocidas.
2. `verificacion/01-08-2026/informe-importacion-toposolid.html` — el diagnóstico
   en 10 secciones.

Ambos están en `C:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\OTROS\MCP\Autocad\`.

## Estado actual: 39 de 40 bien, un defecto abierto

**Funciona:** las 40 Toposolid se crean con contorno correcto, sus 17 huecos de
edificación, las piezas separadas, y el tipo `Carpeta Asfaltica - 0.17ft` con el
espesor real de la carpeta asfáltica. Log: `CREADAS (40), ERRORES (0)`.

**El único defecto:** Revit levanta el diálogo bloqueante *Slab Shape Edit failed*
(7 errores) al confirmar la transacción. La única respuesta que no aborta todo es
**Reset Shape**, que crea la pieza con su huella y su espesor pero **le borra todos
los puntos de forma**: queda plana, sin ningún dato de elevación.

### Las 8 piezas afectadas (ya identificadas)

| Pieza | Relieve esperado | Medido |
|---|---|---|
| Pavement Surface 12 | 7,024 ft | 0,000 |
| Pavement Surface 14 | 4,066 ft | 0,000 |
| Roadway Surface N6 | 4,041 ft | 0,000 |
| Roadway Surface N9 | 2,580 ft | 0,000 |
| Pavement Surface 15 | 2,186 ft | 0,000 |
| Pavement Surface 6 · pieza 1 | 2,056 ft | 0,000 |
| Roadway Surface N12 | 1,901 ft | 0,000 |
| Pavement Surface 19 | 0,568 ft | 0,000 |

El script las detecta solo: tras `TransactionTaskDone()` compara el bounding box
menos el espesor contra el relieve del CSV. Una pieza reseteada da exactamente
`0,000`. El log lo imprime bajo `PIEZAS QUE PERDIERON EL RELIEVE`.

## NO repitas estas cuatro hipótesis — ya están descartadas

| Hipótesis | Resultado medido |
|---|---|
| Proyectar hacia adentro los puntos que caen fuera del perfil | **Empeora**: 7 → 23 errores |
| Descartar esos 566 puntos | Sin efecto: siguen 7 |
| Bajar a 0 los puntos sobre la tolerancia de Revit (597 → 0) | Sin efecto: los mismos 7 |
| Que las piezas se distingan por tamaño, densidad o nº de puntos | Todos los rangos se solapan con el grupo sano |

Dato que mata la cuarta: la pieza con más puntos del proyecto (Roadway N6, 3.737)
falla, y la segunda con más (Pavement 11, 2.582) funciona. La más pequeña de las 8
tiene 17 puntos y hay piezas correctas con 10. Solo una de las ocho tiene un defecto
propio (Pavement Surface 6: cúmulo de puntos a 0,00014 ft).

## SIGUIENTE PASO — el ensayo que discrimina

**Importar solo las 8 piezas en un proyecto Revit vacío.**

- Si **fallan igual** → el problema es intrínseco a la pieza. Continuar con
  bisección por puntos (importar con la mitad de los puntos, luego un cuarto)
  hasta aislar el punto que rompe el editor de forma. Alternativa: añadir los
  puntos con `SlabShapeEditor` de a uno capturando la excepción.
- Si **funcionan** → es efecto de escala o interacción. Probar dividir la
  importación en varias transacciones (p. ej. 10 piezas cada una) y alterar el
  orden de creación: si cambian las que fallan, es interacción; si son las mismas,
  es de la pieza.

Para filtrar los CSV a las 8 piezas, ambos archivos tienen la columna
`SurfaceName` y `PieceId` como primeras dos columnas.

## Rutas exactas

```
Paquete (CSV + script + grafo):
C:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\PRUEBAS\Civil3D\NORTE\31-07-2026\12_Entrega_DWG_Optimizado\REVIT-Dynamo\MAESTRO_CORREGIDO\
  All_Points_ByPiece.csv        (SurfaceName,PieceId,X,Y,Z)      22.225 puntos
  All_Boundaries_Complete.csv   (SurfaceName,PieceId,RingType,RingId,Seq,X,Y)
  Dynamo_CreateToposolids_ConHuecos.py   <- el script que va DENTRO del nodo Python
  ImportarToposolids.dyn                 <- el grafo, ya cableado
  dynamo_log.txt                         <- resultado de la última ejecución

Repo del laboratorio:
C:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\OTROS\MCP\Autocad\
  skills/superficies/importar-toposolid-revit.skill.md
  skills/superficies/scripts/Dynamo_CreateToposolids_ConHuecos.py   (copia sincronizada)
  skills/superficies/scripts/corregir_paquete_revit.py
  skills/superficies/scripts/generar_dyn_toposolid.py
  verificacion/01-08-2026/informe-importacion-toposolid.html
  verificacion/01-08-2026/verificar_paquete.py
```

Entorno: Revit 2026.4 · Dynamo 3.6.2.11575 · CPython3 · Python 3.14 con shapely y
ezdxf · unidades US survey foot.

## Reglas que NO puedes saltarte

1. **Una sola instancia de Revit.** Con dos, Dynamo no arranca y **no da ningún
   mensaje**: el botón simplemente no hace nada. Verifica `Get-Process Revit`.
2. **Dynamo no relanza tras cerrarlo** dentro de la misma sesión de Revit. La única
   secuencia válida es: `reiniciar Revit → crear proyecto → abrir Dynamo → grafo → Run`.
3. **Nunca "Cancel"** en *Slab Shape Edit failed*: aborta la transacción entera y se
   pierden las 40. Siempre **Reset Shape**.
4. **No armes el grafo a mano en el lienzo.** El `.dyn` es JSON: se rellena por
   código y las conexiones se hacen por GUID de puerto. Cruzar `IN[0]` con `IN[1]`
   no da error, entrega geometría mal. `IN[0]` = puntos, `IN[1]` = contornos.
5. **Ejecuta siempre en modo Manual** (`"RunType": "Manual"` en el `.dyn`).
6. **RevitCortex (MCP de Revit) no funciona**: el add-in carga pero nunca levanta el
   puerto 8080. No pierdas tiempo ahí; verifica a mano.
7. **El log va junto a los CSV**, no en `~/Desktop` (no existe con OneDrive).

## Para ver las superficies en Revit

No aparecen en la vista en planta: el rango de vista corta muy por debajo de las
cotas 8,6–16,7 ft. Abre **Project Browser → 3D Views → {3D}** y escribe `ZF`.
Para contar: clic en una superficie → botón derecho → *Select All Instances* →
*In Entire Project*.

## Pendientes menores

- Georreferenciar en **E 12.119.000,000 / N 3.530.500,000** (valores de MAESTRO;
  los de GEO_REVIT son otros y mezclarlos es el error de 24 ft que se documenta
  en el LEEME del paquete).
- El XML corregido de Pavement Surface 2 no se pudo aplicar: faltan los scripts de
  migración (`simplificar_contornos.py`, `export_surface_boundaries_complete.py`,
  `puntos_desde_cortadas.py`), que el LEEME ubica en `HRCP\CIVIL 3D\Scripts_Migracion`.
  Como el traslape que motivó la corrección no existe (medido: 0,0000 ft²), puede
  que ya no haga falta.

## Cómo trabaja este usuario

Quiere que actúes, no que le preguntes por cada paso. Valora que le corrijas cuando
los datos contradicen una hipótesis suya —ya pasó dos veces— y que le digas
claramente qué no funcionó. Prefiere los informes en HTML autocontenido
(skill `informe-html`). Todo el trabajo se documenta en el repo del MCP para que
otros agentes lo retomen.
