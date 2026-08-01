# Graph Report - Autocad  (2026-08-01)

## Corpus Check
- 24 files · ~27,844 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 195 nodes · 230 edges · 20 communities (17 shown, 3 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9b85b715`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]

## God Nodes (most connected - your core abstractions)
1. `PlanoSVG` - 14 edges
2. `main()` - 10 edges
3. `Recorte de Superficie TIN con Perímetro y Cálculo de Área Interior` - 10 edges
4. `main()` - 9 edges
5. `Sistema de Reportes Gráficos SVG` - 9 edges
6. `stats` - 8 edges
7. `detectar_intenciones()` - 7 edges
8. `Generación de Planos Vectoriales SVG de Verificación Topográfica` - 7 edges
9. `main()` - 6 edges
10. `Detalles críticos (aprendidos a la mala)` - 6 edges

## Surprising Connections (you probably didn't know these)
- `drapear_polilineas()` --calls--> `teselar_polilinea_dxf()`  [INFERRED]
  skills/superficies/scripts/drapear_contorno.py → skills/geometria/scripts/teselar_arcos.py
- `escribir_svg()` --calls--> `PlanoSVG`  [INFERRED]
  skills/superficies/scripts/recortar_superficie.py → skills/reportes/scripts/plano_svg.py

## Import Cycles
- None detected.

## Communities (20 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.22
Nodes (8): 1. Parámetros K Mínimos (Distancia de Visibilidad de Parada), 2. Longitud Mínima de Curva, Criterios aplicados (Manual de Carreteras de Chile, Vol. 3), Cuándo usar, Código de Referencia / Flujo en C# (in-process), Entradas requeridas, Falsos positivos conocidos, Revisión de Curvas Verticales contra Criterio de Diseño (Manual de Carreteras Chile)

### Community 1 - "Community 1"
Cohesion: 0.14
Nodes (13): 1. El origen del contenido no es el origen del marco, 2. Hay que escapar `&`, `<` y `>` en todos los textos, 3. Las pruebas van junto a la skill, no en una carpeta temporal, 4. Mirar el resultado, no solo los números, Cuándo usar, Detalles críticos (aprendidos a la mala), Paleta, Quién la usa (+5 more)

### Community 2 - "Community 2"
Cohesion: 0.50
Nodes (7): clean_path(), get_graphify_stats(), get_server_tools(), get_skills(), get_timeline(), get_verification_matrix(), main()

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (18): graph_stats, active, communities, edges, nodes, last_update, matrix, server_tools (+10 more)

### Community 4 - "Community 4"
Cohesion: 0.12
Nodes (17): color_rampa(), _esc(), leer_dxf(), leer_landxml(), main(), _mezclar(), paso_redondo(), PlanoSVG (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.19
Nodes (19): aviso(), cota_en_plano(), escribir_dxf_borde(), escribir_landxml(), escribir_svg(), fmt(), leer_landxml(), leer_perimetro() (+11 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (15): 1. Las caras `i="1"` del LandXML hay que descartarlas, 2. El orden de coordenadas del LandXML es *norte este cota*, 3. El área 3D se calcula por triángulo, no al final, 4. Los arcos (bulges) de la polilínea hay que teselarlos sobre el arco real, 5. El perímetro puede ser más grande que la superficie, Cuándo usar, Dependencias, Detalles críticos (aprendidos a la mala) (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.22
Nodes (4): dxf_circulo(), Malla regular sobre un plano inclinado, en metros., Circulo exacto: LWPOLYLINE de 2 vertices con bulge=1 (dos semicircunferencias)., tin_metrico()

### Community 11 - "Community 11"
Cohesion: 0.25
Nodes (7): Cuándo usar, Entradas requeridas, Estado, Generación de Planos Vectoriales SVG de Verificación Topográfica, Salidas, Uso desde Línea de Comandos (CLI), Uso en Python

### Community 13 - "Community 13"
Cohesion: 0.24
Nodes (6): detectar_intenciones(), ejecutar_pipeline(), main(), Identifica las skills asociadas a un texto o consulta en lenguaje natural., Ejecuta el pipeline completo unificado de recortes y verificación., TestRouterIntenciones

### Community 14 - "Community 14"
Cohesion: 0.27
Nodes (6): main(), Devuelve los puntos muestreados a lo largo del arco real representado por un bul, Lee un DXF y devuelve listas de vertices (X, Y) con arcos teselados., teselar_bulge(), teselar_polilinea_dxf(), TestTeselado

### Community 15 - "Community 15"
Cohesion: 0.32
Nodes (5): drapear_polilineas(), interpolar_z_triangulo(), main(), Interpola cota Z sobre el plano formado por p1, p2, p3., TestDrapeado

### Community 16 - "Community 16"
Cohesion: 0.33
Nodes (5): Cuándo usar, Entradas requeridas, Salida, Teselado de Arcos y Bulges en Polilíneas por Sagitta, Uso

### Community 17 - "Community 17"
Cohesion: 0.40
Nodes (3): auditar_landxml(), main(), TestAuditoria

### Community 18 - "Community 18"
Cohesion: 0.33
Nodes (5): Auditoría e Integridad de Superficies LandXML TIN, Cuándo usar, Entradas requeridas, Reporte de Auditoría, Uso

### Community 19 - "Community 19"
Cohesion: 0.33
Nodes (5): Cuándo usar, Drapeado e Interpolación 3D de Contornos sobre TIN, Entradas requeridas, Salida, Uso

## Knowledge Gaps
- **66 isolated node(s):** `graphify`, `Workflow: graphify`, `Cuándo usar`, `Entradas requeridas`, `Uso` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PlanoSVG` connect `Community 4` to `Community 8`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `escribir_svg()` connect `Community 8` to `Community 4`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **What connects `Devuelve los puntos muestreados a lo largo del arco real representado por un bul`, `Lee un DXF y devuelve listas de vertices (X, Y) con arcos teselados.`, `Escapa texto para XML. Sin esto un nombre con & rompe el SVG.` to the rest of the system?**
  _89 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.10526315789473684 - nodes in this community are weakly interconnected._
- **Should `Community 4` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._
- **Should `Community 9` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._