# Graph Report - Autocad  (2026-07-30)

## Corpus Check
- 6 files · ~14,167 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 41 nodes · 42 edges · 8 communities (6 shown, 2 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]

## God Nodes (most connected - your core abstractions)
1. `stats` - 8 edges
2. `main()` - 6 edges
3. `Revisión de Curvas Verticales contra Criterio de Diseño (Manual de Carreteras Chile)` - 6 edges
4. `graph_stats` - 5 edges
5. `clean_path()` - 3 edges
6. `get_skills()` - 3 edges
7. `get_timeline()` - 3 edges
8. `Criterios aplicados (Manual de Carreteras de Chile, Vol. 3)` - 3 edges
9. `get_verification_matrix()` - 2 edges
10. `get_server_tools()` - 2 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (8 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.22
Nodes (8): 1. Parámetros K Mínimos (Distancia de Visibilidad de Parada), 2. Longitud Mínima de Curva, Criterios aplicados (Manual de Carreteras de Chile, Vol. 3), Cuándo usar, Código de Referencia / Flujo en C# (in-process), Entradas requeridas, Falsos positivos conocidos, Revisión de Curvas Verticales contra Criterio de Diseño (Manual de Carreteras Chile)

### Community 1 - "Community 1"
Cohesion: 0.25
Nodes (8): stats, tests_falla, tests_ok, tests_wip, total_server_modules, total_server_tools, total_skills, total_tests

### Community 2 - "Community 2"
Cohesion: 0.50
Nodes (7): clean_path(), get_graphify_stats(), get_server_tools(), get_skills(), get_timeline(), get_verification_matrix(), main()

### Community 3 - "Community 3"
Cohesion: 0.33
Nodes (5): last_update, matrix, server_tools, skills, timeline

### Community 4 - "Community 4"
Cohesion: 0.40
Nodes (5): graph_stats, active, communities, edges, nodes

## Knowledge Gaps
- **24 isolated node(s):** `last_update`, `total_skills`, `total_tests`, `tests_ok`, `tests_falla` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `stats` connect `Community 1` to `Community 3`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Why does `graph_stats` connect `Community 4` to `Community 3`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **What connects `last_update`, `total_skills`, `total_tests` to the rest of the system?**
  _24 weakly-connected nodes found - possible documentation gaps or missing edges._