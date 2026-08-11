window.DASHBOARD_DATA = {
  "last_update": "2026-08-11 14:00:35",
  "stats": {
    "total_skills": 21,
    "total_tests": 21,
    "tests_ok": 15,
    "tests_falla": 2,
    "tests_wip": 4,
    "total_server_tools": 216,
    "total_server_modules": 30,
    "total_sessions": 6
  },
  "skills": [
    {
      "name": "generacion_planos_svg",
      "description": "Genera planos vectoriales SVG de verificación topográfica (TIN, perímetros, cotas, leyendas, escala gráfica y norte) sin requerir matplotlib ni librerías gráficas externas.",
      "category": "Reportes",
      "file_path": "skills/reportes/generacion-planos-svg.skill.md",
      "uses": 24,
      "success": 24,
      "last_used": "2026-08-02 18:40:00",
      "reliability": "Alta (Probada)",
      "rel_code": "HIGH"
    },
    {
      "name": "auditoria_superficies_landxml",
      "description": "Audita la integridad geométrica y estructural de archivos LandXML TIN: caras invisibles (i='1'), orden de coordenadas Norte/Este vs X/Y, unidades del dibujo y conservación de áreas 2D/3D.",
      "category": "Superficies",
      "file_path": "skills/superficies/auditoria-superficies-landxml.skill.md",
      "uses": 19,
      "success": 19,
      "last_used": "2026-08-11 10:31:00",
      "reliability": "Alta (Probada)",
      "rel_code": "HIGH"
    },
    {
      "name": "plano_svg_verificacion",
      "description": "Sistema de planos SVG de verificación para Civil 3D y topografía: escribe el SVG como texto plano, sin matplotlib ni librerías gráficas, con escala única, norte, escala gráfica, leyenda y rampa de color validada.",
      "category": "Reportes",
      "file_path": "skills/reportes/plano-svg.skill.md",
      "uses": 15,
      "success": 15,
      "last_used": "2026-08-02 17:30:00",
      "reliability": "Alta (Probada)",
      "rel_code": "HIGH"
    },
    {
      "name": "importar_toposolid_revit",
      "description": "Importa superficies TIN de Civil 3D a Revit 2026 como Toposolid vía Dynamo: resuelve errores de Slab Shape Edit failed, elimina desplomes/estalactitas, arregla cortes de huecos de edificación a cota real y optimiza la densidad para ejecuciones en 10-15 segundos. Incluye georreferenciación exacta y configuración de resolución de curvas de nivel.",
      "category": "Superficies",
      "file_path": "skills/superficies/importar-toposolid-revit.skill.md",
      "uses": 15,
      "success": 14,
      "last_used": "2026-08-11 12:45:00",
      "reliability": "Alta (Probada)",
      "rel_code": "HIGH"
    },
    {
      "name": "revision_curvas_verticales",
      "description": "Revisión de curvas verticales y valores K en perfiles longitudinales de Civil 3D según criterios de diseño vial y normativas configurables.",
      "category": "Vialidad",
      "file_path": "skills/vialidad/revision-curvas-verticales.skill.md",
      "uses": 9,
      "success": 8,
      "last_used": "2026-08-02 14:00:00",
      "reliability": "Media (Frecuente)",
      "rel_code": "MEDIUM"
    },
    {
      "name": "recorte_superficie_con_perimetro",
      "description": "Recorta una superficie TIN de LandXML con un perímetro cerrado de un DXF y entrega el área interior 2D y 3D, un plano SVG de verificación, el LandXML de la superficie cortada y el contorno en DXF.",
      "category": "Superficies",
      "file_path": "skills/superficies/recorte-superficie.skill.md",
      "uses": 8,
      "success": 8,
      "last_used": "2026-07-31 12:00:00",
      "reliability": "Media (Frecuente)",
      "rel_code": "MEDIUM"
    },
    {
      "name": "drapeado_contorno_3d",
      "description": "Drapea polilíneas 2D sobre mallas TIN LandXML interpolando cotas Z para exportar polilíneas 3D en DXF aptas como Breaklines o Boundaries en Civil 3D.",
      "category": "Superficies",
      "file_path": "skills/superficies/drapeado-contorno-3d.skill.md",
      "uses": 6,
      "success": 6,
      "last_used": "2026-07-30 15:00:00",
      "reliability": "Media (Frecuente)",
      "rel_code": "MEDIUM"
    },
    {
      "name": "teselado_arcos_polilinea",
      "description": "Tesela polilíneas DXF que contienen arcos (bulges) muestreando directamente la circunferencia real con una tolerancia de sagitta máxima.",
      "category": "Geometria",
      "file_path": "skills/geometria/teselado-arcos-polilinea.skill.md",
      "uses": 5,
      "success": 5,
      "last_used": "2026-07-30 14:00:00",
      "reliability": "Media (Frecuente)",
      "rel_code": "MEDIUM"
    },
    {
      "name": "civil3d-to-revit-toposolid",
      "description": "Procedimiento completo y guía técnica para migrar superficies TIN de Civil 3D a Toposolids individuales en Revit 2024/2025/2026 mediante Dynamo Python. Incluye extracción de puntos y contornos (con huecos interiores y piezas disjuntas), limpiador geométrico en 3 pasadas para evitar errores de auto-intersección (foldbacks) y tolerancia de líneas (ShortCurveTolerance), silenciador seguro de warnings (WarningSwallower), reanudación automática por comentarios, guardado incremental pieza a pieza, diagnóstico de relieve y traslación por vector de coordenadas de control (OFFSET_X/OFFSET_Y).",
      "category": "Migracion",
      "file_path": "skills/migracion/civil3d-to-revit-toposolid.skill.md",
      "uses": 2,
      "success": 1,
      "last_used": "2026-08-11 12:45:00",
      "reliability": "Inicial (Por validar)",
      "rel_code": "LOW"
    },
    {
      "name": "civil3d-to-revit-toposolid",
      "description": "Procedimiento completo y guía técnica para migrar superficies TIN de Civil 3D a Toposolids individuales en Revit 2024/2025/2026 mediante Dynamo Python. Incluye extracción de puntos y contornos (con huecos interiores y piezas disjuntas), limpiador geométrico en 3 pasadas para evitar errores de auto-intersección (foldbacks) y tolerancia de líneas (ShortCurveTolerance), silenciador seguro de warnings (WarningSwallower), reanudación automática por comentarios, guardado incremental pieza a pieza, diagnóstico de relieve y traslación por vector de coordenadas de control (OFFSET_X/OFFSET_Y).",
      "category": "Civil3d-to-revit-toposolid",
      "file_path": "skills/migracion/civil3d-to-revit-toposolid/SKILL.md",
      "uses": 2,
      "success": 1,
      "last_used": "2026-08-11 12:45:00",
      "reliability": "Inicial (Por validar)",
      "rel_code": "LOW"
    },
    {
      "name": "inspeccion_dwg_por_xref",
      "description": "Unifica por XREF todos los DWG de una carpeta en un solo dibujo de comparación visual, con rutas relativas para que la carpeta de salida sea copiable o comprimible sin romper enlaces.",
      "category": "Dibujo",
      "file_path": "skills/dibujo/inspeccion-dwg.skill.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    },
    {
      "name": "terrazas_taludes_calzadas",
      "description": "Genera la superficie de proyecto de un loteo en ladera: terrazas horizontales por lote a su NPT, taludes contra la calzada y entre lotes vecinos, y el pavimento de la vialidad con rasante continua. Parte de un DXF de loteo y el TIN del terreno natural, y entrega LandXML importable a Civil 3D más DXF de bordes editable. Usar cuando pidan modelar plataformas/terrazas de un loteo, generar taludes entre lotes o contra calles, cubicar un loteo en cerro, o cuando una superficie de proyecto ya generada salga con triangulación sucia, bordes dentados o taludes discontinuos.",
      "category": "Loteo",
      "file_path": "skills/loteo/terrazas-taludes-calzadas.skill.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    },
    {
      "name": "ifc_a_civil3d",
      "description": "Convierte modelos IFC (Bentley OpenRoads/GeoPak) a DXF con capas NCS o a LandXML TIN georreferenciado en VA83-SF, conservando la triangulación, con diagnóstico previo del esquema y control explícito del factor de escala.",
      "category": "Migracion",
      "file_path": "skills/migracion/ifc-a-civil3d.skill.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    },
    {
      "name": "cara_superior_desde_solido",
      "description": "Convierte mallas polyface volumétricas (sólidos con cara superior, paredes y fondo) en superficies TIN que conservan solo la cara transitable, en DXF o en LandXML por elemento.",
      "category": "Superficies",
      "file_path": "skills/superficies/cara-superior-desde-solido.skill.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    },
    {
      "name": "comparar_superficies",
      "description": "Marca en un DXF las zonas donde dos superficies TIN difieren en cota más de un umbral, rasterizando ambas sobre la misma malla regular e interpolando por baricéntricas.",
      "category": "Superficies",
      "file_path": "skills/superficies/comparar-superficies.skill.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    },
    {
      "name": "contornos_y_boundaries",
      "description": "Extrae el paquete completo de contornos (anillo exterior y huecos) de cada superficie de un LandXML y simplifica los vértices redundantes; explica por qué un boundary de Civil 3D no recorta la triangulación.",
      "category": "Superficies",
      "file_path": "skills/superficies/contornos-y-boundaries.skill.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    },
    {
      "name": "malla_a_landxml",
      "description": "Convierte mallas polyface/3DFACE/MESH de un DXF en superficies TIN LandXML conservando la triangulación exacta, con soldadura por XY, limpieza de caras degeneradas y relleno de huecos internos.",
      "category": "Superficies",
      "file_path": "skills/superficies/malla-a-landxml.skill.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    },
    {
      "name": "particion_de_superficies",
      "description": "Parte una superficie de la entrega en piezas usando líneas de un DXF como cuchilla, renumerando de norte a sur, y explica por qué los bordes compartidos se reconstruyen por topología y no promediando pares.",
      "category": "Superficies",
      "file_path": "skills/superficies/particion-de-superficies.skill.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    },
    {
      "name": "recorte_y_resta_de_superficies",
      "description": "Recorta superficies TIN de un LandXML contra contornos cerrados de un DXF, resta la huella de una superficie de otra, y parte una superficie en piezas por capas SURF_OUTER/SURF_HOLE.",
      "category": "Superficies",
      "file_path": "skills/superficies/recorte-y-resta.skill.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    },
    {
      "name": "rellenar_huecos_y_costuras",
      "description": "Cierra los huecos entre superficies entregadas y el límite real de la malla tomando la geometría del XML de origen, y anexa a una superficie el trozo que no cubría ninguna otra.",
      "category": "Superficies",
      "file_path": "skills/superficies/rellenar-huecos.skill.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    },
    {
      "name": "⚠️ Cuarentena — herramientas que NO se deben usar sin leer esto",
      "description": "Sin descripción",
      "category": "_cuarentena",
      "file_path": "skills/_cuarentena/README.md",
      "uses": 0,
      "success": 0,
      "last_used": "Sin registrar",
      "reliability": "Sin uso",
      "rel_code": "NONE"
    }
  ],
  "matrix": [
    {
      "servidor": "civil3d-mcp",
      "tool": "get_drawing_info",
      "version_c3d": "2026",
      "dwg_prueba": "tests/dwg/01_vacio.dwg",
      "resultado": "OK",
      "evidencia": "consola",
      "fecha": "2026-07-30",
      "notas": "Devuelve correctamente metadatos del dibujo, unidades y extención"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "list_civil_object_types",
      "version_c3d": "2026",
      "dwg_prueba": "tests/dwg/02_superficies_par.dwg",
      "resultado": "OK",
      "evidencia": "consola",
      "fecha": "2026-07-30",
      "notas": "Inventario y conteo exacto de superficies, alineaciones y redes"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "create_cogo_point",
      "version_c3d": "2026",
      "dwg_prueba": "tests/dwg/01_vacio.dwg",
      "resultado": "WIP",
      "evidencia": "tests/dwg/cogo_vacio.dwg",
      "fecha": "2026-07-30",
      "notas": "El punto se crea pero la descripción avanzada se omite en la transacción"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "sample_surface_elevation",
      "version_c3d": "2026",
      "dwg_prueba": "tests/dwg/02_superficies_par.dwg",
      "resultado": "OK",
      "evidencia": "consola",
      "fecha": "2026-07-30",
      "notas": "Interpola cotas sobre mallas TIN de superficie con alta precisión"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "delete_cogo_point",
      "version_c3d": "2026",
      "dwg_prueba": "tests/dwg/01_vacio.dwg",
      "resultado": "FALLA",
      "evidencia": "consola",
      "fecha": "2026-07-30",
      "notas": "Excepción COM al intentar eliminar puntos por ID de entidad"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "create_alignment",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/02-08-2026/Superficie_cargas_xml.dwg",
      "resultado": "WIP",
      "evidencia": "verificacion/02-08-2026/Informe_Final_Diseno_y_Perfil.html",
      "fecha": "2026-08-02",
      "notas": "Crea alineamientos pero requiere depurar polilíneas huérfanas al revertir"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "create_profile_view",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/02-08-2026/Superficie_cargas_xml.dwg",
      "resultado": "FALLA",
      "evidencia": "consola",
      "fecha": "2026-08-02",
      "notas": "Incompatibilidad de firma en ProfileView.Create para Civil 3D 2026"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "sample_profile_elevations",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/02-08-2026/Superficie_cargas_xml.dwg",
      "resultado": "WIP",
      "evidencia": "verificacion/02-08-2026/Perfil_Longitudinal_Comparativo.html",
      "fecha": "2026-08-02",
      "notas": "Cálculo alfanumérico correcto; en proceso de optimización del refresco en viewport"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "import_revit_toposolid",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/01-08-2026/12_Entrega_DWG_Optimizado/Proyecto_Definitivo.dwg",
      "resultado": "OK",
      "evidencia": "verificacion/01-08-2026/informe-importacion-toposolid.html",
      "fecha": "2026-08-01",
      "notas": "Extracción e importación exitosa de mallas TIN Toposolid desde LandXML a Civil 3D"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "extract_surfaces_landxml",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/01-08-2026/11_Extraer superficies nuevas/TODAS_Superficies_Proyecto.xml",
      "resultado": "OK",
      "evidencia": "verificacion/01-08-2026/HANDOFF-continuar-importacion-revit.md",
      "fecha": "2026-08-01",
      "notas": "Separación y extracción de 32 superficies individuales desde LandXML unificado"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "export_civil3d_to_revit_dynamo",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/01-08-2026/12_Entrega_DWG_Optimizado/Proyecto_Definitivo.dwg",
      "resultado": "OK",
      "evidencia": "verificacion/01-08-2026/informe-importacion-toposolid.html",
      "fecha": "2026-08-01",
      "notas": "Exportación exitosa de topografía desde Civil 3D a Revit mediante scripts Dynamo"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "anonymize_local_landxml",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/02-08-2026 v2/Superficie_tipo_neutral.xml",
      "resultado": "OK",
      "evidencia": "verificacion/02-08-2026 v2/Superficie_tipo_neutral.xml",
      "fecha": "2026-08-02",
      "notas": "Remoción de metadatos confidenciales, eliminación de CRS global y traslación a origen local (0,0) ft (Regla 6)"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "civil3d_surface_volume_calculate",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/02-08-2026 v2/Superficie tipo.dwg",
      "resultado": "OK",
      "evidencia": "verificacion/02-08-2026 v2/informe_estudio_terrazas.html",
      "fecha": "2026-08-02",
      "notas": "Cálculo volumétrico global exacto: Corte 345.68 cu yd, Relleno 644.26 cu yd, Balance neto +298.58 cu yd"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "civil3d_surface_volume_by_region",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/02-08-2026 v2/Superficie tipo.dwg",
      "resultado": "WIP",
      "evidencia": "verificacion/02-08-2026 v2/informe_estudio_terrazas.html",
      "fecha": "2026-08-02",
      "notas": "Herramienta muy práctica y de alto potencial para comparativa y zonificación en 4 terrazas; en proceso de perfeccionamiento"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "civil3d_surface_volume_report",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/02-08-2026 v2/Superficie tipo.dwg",
      "resultado": "OK",
      "evidencia": "verificacion/02-08-2026 v2/informe_estudio_terrazas.html",
      "fecha": "2026-08-02",
      "notas": "Generación automatizada de informe técnico impresurable con gráficos SVG 2D en planta, perfiles de corte/relleno y matriz de unidades imperiales"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "export_civil3d_to_revit_dynamo",
      "version_c3d": "2026",
      "dwg_prueba": "HRCP/CIVIL 3D/South Island/Superficie/04_ZONIFICACION/XML_repaso a mano/SI_SURFACE_XML.xml",
      "resultado": "OK",
      "evidencia": "HRCP/CIVIL 3D/South Island/Superficie/05_Dynamo_Revit/dynamo_log.txt",
      "fecha": "2026-08-07",
      "notas": "Entrega de las 22 superficies de carpeta de South Island: 589,384 ft2 (13.53 ac), 27,821 puntos, 5,886 vertices de contorno, 11 huecos. 22 Toposolid creadas, 0 errores"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "skill_terrazas_taludes_calzadas",
      "version_c3d": "2026",
      "dwg_prueba": "verificacion/07-08-2026/Chaimavida/02_DXF Loteo/Loteo.dxf",
      "resultado": "OK",
      "evidencia": "skills/loteo/terrazas-taludes-calzadas.skill.md",
      "fecha": "2026-08-08",
      "notas": "Superficie de proyecto de loteo en ladera: 89 terrazas a NPT con taludes 1:1 contra calzada y vecinos, y pavimento con rasante de red. Auditoria: cobertura 100%, 0 huecos, 0 piezas sueltas, 0 vertices flotantes, llano en talud 0,01%. Metodo empaquetado como skill reutilizable"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "georreferenciacion_offset_revit",
      "version_c3d": "2026",
      "dwg_prueba": "HRCP/CIVIL 3D/South Island/Superficie/05_Dynamo_Revit/ImportarToposolids.dyn",
      "resultado": "OK",
      "evidencia": "HRCP/CIVIL 3D/South Island/Superficie/05_Dynamo_Revit/GEORREFERENCIA_Y_COORDENADAS.txt",
      "fecha": "2026-08-10",
      "notas": "OFFSET_X=+1,702.20 / OFFSET_Y=-3,792.42 medido contra 3 vertices de control del modelo de Revit; el vector de traslacion sale identico en los 3. No es geodesico: es un ajuste medido"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "extract_surfaces_landxml",
      "version_c3d": "2026",
      "dwg_prueba": "HRCP/CIVIL 3D/South Island/Superficie/08_XML SURFACE EXT/Volume_Surface_SI.xml",
      "resultado": "OK",
      "evidencia": "HRCP/CIVIL 3D/South Island/Superficie/08_XML SURFACE EXT/Dynamo_Revit_IS_EXT/verificacion_superficie.png",
      "fecha": "2026-08-11",
      "notas": "Terreno existente Surface_Exis_SI. Descartadas 11,676 de 220,482 caras con i=\"1\" (invisibles): sin ese filtro la huella sale 1,127,492 ft2 en vez de 490,244.56. Huella reconstruida cuadra al 0.0000 % con area2DSurf. 2 piezas y 10 huecos >5 ft2"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "decimado_tin_control_error",
      "version_c3d": "2026",
      "dwg_prueba": "HRCP/CIVIL 3D/South Island/Superficie/08_XML SURFACE EXT/Volume_Surface_SI.xml",
      "resultado": "OK",
      "evidencia": "HRCP/CIVIL 3D/South Island/Superficie/08_XML SURFACE EXT/Dynamo_Revit_IS_EXT/GEORREFERENCIA_Y_COORDENADAS.txt",
      "fecha": "2026-08-11",
      "notas": "105,419 puntos (malla de escaneo de 1.04 ft) reducidos a 7,711 (7.3 %) por insercion voraz conservando el contorno. Contrastado en malla de 2 ft (121,780 nodos): el juego COMPLETO no mejora, empeora la cola (233 nodos >1 ft frente a 173). Revit re-triangula por Delaunay"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "import_revit_toposolid",
      "version_c3d": "2026",
      "dwg_prueba": "HRCP/CIVIL 3D/South Island/Superficie/08_XML SURFACE EXT/CJV-SI-EXT-RVT25.rvt",
      "resultado": "OK",
      "evidencia": "HRCP/CIVIL 3D/South Island/Superficie/08_XML SURFACE EXT/Dynamo_Revit_IS_EXT/dynamo_log.txt",
      "fecha": "2026-08-11",
      "notas": "2 Toposolid del terreno existente, relieve conservado (18.387 esperado vs 18.388 real). El primer intento FALLO en la pieza grande con 'input curve loops cannot compose a valid boundary': 3 de los 10 huecos tocaban el borde exterior a 0.0000 ft. Resuelto anadiendo min_dist_loop_to_loop() y descartando huecos a menos de 0.05 ft del contorno"
    }
  ],
  "server_tools": [
    {
      "module": "Alignment",
      "file": "alignmentDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_alignment",
          "description": "Reads Civil 3D alignments, reports geometry, and manages editing actions through a single domain tool."
        },
        {
          "name": "civil3d_alignment_report",
          "description": "Builds a structured alignment report by fetching alignment geometry and sampling station locations."
        },
        {
          "name": "civil3d_alignment_add_tangent",
          "description": "Appends a fixed tangent (straight line) entity to a Civil 3D alignment using two end points."
        },
        {
          "name": "civil3d_alignment_add_curve",
          "description": "Appends a fixed horizontal curve entity to a Civil 3D alignment using a pass-through point and radius."
        },
        {
          "name": "civil3d_alignment_add_spiral",
          "description": "Appends a spiral (transition curve) entity to a Civil 3D alignment. Clothoid, cubic, and biquadratic spiral types are supported."
        },
        {
          "name": "civil3d_alignment_delete_entity",
          "description": "Deletes a single entity (tangent, curve, or spiral) from a Civil 3D alignment by its zero-based index."
        },
        {
          "name": "civil3d_alignment_set_station_equation",
          "description": "Adds a station equation to a Civil 3D alignment, allowing the nominal station to differ from the raw measured station."
        },
        {
          "name": "civil3d_alignment_get_station_offset",
          "description": "Returns the station, offset, and perpendicular distance of an XY point relative to a Civil 3D alignment."
        },
        {
          "name": "civil3d_alignment_offset_create",
          "description": "Creates a new offset alignment at a constant distance from an existing base alignment."
        },
        {
          "name": "civil3d_alignment_widen_transition",
          "description": "Creates a variable-offset widening or narrowing transition region on a Civil 3D alignment."
        }
      ],
      "count": 10
    },
    {
      "module": "Assembly",
      "file": "assemblyDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_assembly",
          "description": "Lists, inspects, creates, and edits Civil 3D assemblies and subassemblies through a single domain tool."
        },
        {
          "name": "civil3d_assembly_create",
          "description": "Creates a new Civil 3D assembly at a specified model-space location."
        },
        {
          "name": "civil3d_subassembly_create",
          "description": "Adds a subassembly from the Civil 3D catalog to an existing assembly."
        },
        {
          "name": "civil3d_assembly_edit",
          "description": "Inspects or modifies an existing Civil 3D assembly, including subassembly parameter edits and deletion."
        }
      ],
      "count": 4
    },
    {
      "module": "Coordinatesystem",
      "file": "coordinateSystemDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_coordinate_system",
          "description": "Provides coordinate system information and coordinate transformations."
        }
      ],
      "count": 1
    },
    {
      "module": "Corridor",
      "file": "corridorDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_corridor",
          "description": "Reads Civil 3D corridor data, controls rebuild, computes volumes, and manages regions and target mappings through a single domain tool."
        },
        {
          "name": "civil3d_corridor_summary",
          "description": "Builds a corridor summary by fetching corridor details, corridor surfaces, and optional volume analysis against a reference surface."
        },
        {
          "name": "civil3d_corridor_target_mapping_get",
          "description": "Retrieve the current subassembly target mappings for a Civil 3D corridor. Returns all target parameters for each baseline region."
        },
        {
          "name": "civil3d_corridor_target_mapping_set",
          "description": "Set or update subassembly target mappings on a Civil 3D corridor region. Assigns surfaces, alignments, profiles, or polylines as targets for subassembly parameters."
        },
        {
          "name": "civil3d_corridor_region_add",
          "description": "Add a new region to a Civil 3D corridor baseline, defining which assembly applies over a station range and at what sampling frequency."
        },
        {
          "name": "civil3d_corridor_region_delete",
          "description": "Delete a region from a Civil 3D corridor baseline by its zero-based index. Rebuilds the corridor after deletion."
        }
      ],
      "count": 6
    },
    {
      "module": "Costestimation",
      "file": "costEstimationDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_cost_estimation",
          "description": "Exports pay items and calculates material cost estimates through a single domain tool."
        },
        {
          "name": "civil3d_pay_items_export",
          "description": "Exports pay-item schedules and quantities."
        },
        {
          "name": "civil3d_material_cost_estimate",
          "description": "Calculates a construction cost estimate from Civil 3D quantities and pay items."
        }
      ],
      "count": 3
    },
    {
      "module": "Detention",
      "file": "detentionDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_detention",
          "description": "Calculates detention basin sizing and stage-storage workflows through a single domain tool."
        },
        {
          "name": "civil3d_detention_basin_size_calculate",
          "description": "Calculates detention basin size requirements."
        },
        {
          "name": "civil3d_detention_stage_storage",
          "description": "Generates stage-storage-discharge output for a detention basin surface."
        }
      ],
      "count": 3
    },
    {
      "module": "Docs",
      "file": "docsDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_docs",
          "description": "Lists tool capabilities and routes natural-language orchestration requests through a single docs/orchestration tool."
        },
        {
          "name": "list_tool_capabilities",
          "description": "Lists domain and capability metadata for the Civil 3D MCP tool catalog, including implemented and planned tools."
        },
        {
          "name": "civil3d_orchestrate",
          "description": "Routes a natural-language Civil 3D request to the best starting tool or action and executes routed work through the registered MCP tool surface."
        }
      ],
      "count": 3
    },
    {
      "module": "Drawingruntime",
      "file": "drawingRuntimeDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_drawing",
          "description": "Reads drawing state, settings, selection context, and document operations through a single domain tool."
        },
        {
          "name": "get_drawing_info",
          "description": "Retrieves basic information about the active Civil 3D drawing."
        },
        {
          "name": "get_selected_civil_objects_info",
          "description": "Gets basic properties of currently selected Civil 3D objects."
        },
        {
          "name": "list_civil_object_types",
          "description": "Lists major Civil 3D object types available in the current context."
        }
      ],
      "count": 4
    },
    {
      "module": "Geometry",
      "file": "geometryDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_geometry",
          "description": "Runs COGO calculations and basic drafting geometry creation through a single domain tool."
        },
        {
          "name": "civil3d_cogo_inverse",
          "description": "Calculates bearing and distance between two coordinates."
        },
        {
          "name": "civil3d_cogo_direction_distance",
          "description": "Projects a point from bearing and distance."
        },
        {
          "name": "civil3d_cogo_traverse",
          "description": "Solves a traverse from courses."
        },
        {
          "name": "civil3d_cogo_curve_solve",
          "description": "Solves a horizontal curve from known elements."
        },
        {
          "name": "create_line_segment",
          "description": "Creates a line segment in the drawing."
        },
        {
          "name": "acad_create_polyline",
          "description": "Creates a 2D polyline in model space."
        },
        {
          "name": "acad_create_3dpolyline",
          "description": "Creates a 3D polyline in model space."
        },
        {
          "name": "acad_create_text",
          "description": "Creates DBText in model space."
        },
        {
          "name": "acad_create_mtext",
          "description": "Creates MText in model space."
        }
      ],
      "count": 10
    },
    {
      "module": "Grading",
      "file": "gradingDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_grading",
          "description": "Lists, inspects, creates, deletes, and analyzes Civil 3D grading groups, gradings, and feature lines through a single domain tool."
        },
        {
          "name": "civil3d_feature_line",
          "description": "Reads Civil 3D feature lines and supports exporting them as 3D polylines."
        },
        {
          "name": "civil3d_grading_group_list",
          "description": "Lists all Civil 3D grading groups in the drawing."
        },
        {
          "name": "civil3d_grading_group_get",
          "description": "Gets detailed information about a Civil 3D grading group."
        },
        {
          "name": "civil3d_grading_group_create",
          "description": "Creates a new Civil 3D grading group."
        },
        {
          "name": "civil3d_grading_group_delete",
          "description": "Deletes a Civil 3D grading group and its gradings."
        },
        {
          "name": "civil3d_grading_group_volume",
          "description": "Gets the cut/fill volume report for a Civil 3D grading group."
        },
        {
          "name": "civil3d_grading_group_surface_create",
          "description": "Creates a Civil 3D surface from a grading group."
        },
        {
          "name": "civil3d_grading_list",
          "description": "Lists all grading objects within a specific Civil 3D grading group."
        },
        {
          "name": "civil3d_grading_get",
          "description": "Gets detailed properties of a specific grading object."
        },
        {
          "name": "civil3d_grading_create",
          "description": "Creates a new Civil 3D grading from a feature line using the specified criteria."
        },
        {
          "name": "civil3d_grading_delete",
          "description": "Deletes a grading object from a Civil 3D grading group by handle."
        },
        {
          "name": "civil3d_grading_criteria_list",
          "description": "Lists the available Civil 3D grading criteria sets and criteria names."
        },
        {
          "name": "civil3d_feature_line_create",
          "description": "Creates a new Civil 3D feature line from an ordered list of 3D points."
        }
      ],
      "count": 14
    },
    {
      "module": "Hydrology",
      "file": "hydrologyDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_hydrology",
          "description": "Provides hydrology, catchment, time-of-concentration, SSA, and drainage workflow operations through a single domain tool."
        },
        {
          "name": "civil3d_catchment",
          "description": "Manages Civil 3D catchments and catchment groups including properties, flow paths, and boundaries."
        },
        {
          "name": "civil3d_time_of_concentration",
          "description": "Calculates time of concentration using standard methods and generates hydrographs."
        },
        {
          "name": "civil3d_stm",
          "description": "Manages STM export/import and Storm and Sanitary Analysis launch workflows."
        },
        {
          "name": "civil3d_hydrology_watershed_runoff_workflow",
          "description": "Builds a complete watershed-to-runoff analysis by locating or using an outlet, delineating the watershed, calculating catchment area, converting area units, and estimating Rational Method runoff."
        },
        {
          "name": "civil3d_hydrology_runoff_detention_workflow",
          "description": "Builds a runoff-to-detention workflow by estimating Rational Method runoff, sizing a detention basin, and optionally generating a stage-storage-discharge table."
        },
        {
          "name": "civil3d_hydrology_runoff_pipe_workflow",
          "description": "Builds a runoff-to-pipe-network workflow by estimating Rational Method runoff, then performing HGL and hydraulic capacity analysis on a gravity pipe network."
        }
      ],
      "count": 7
    },
    {
      "module": "Intersection",
      "file": "intersectionDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_intersection",
          "description": "Lists, creates, and inspects Civil 3D intersections through a single domain tool."
        },
        {
          "name": "civil3d_intersection_list",
          "description": "Lists intersections in the active drawing."
        },
        {
          "name": "civil3d_intersection_create",
          "description": "Creates an intersection between two alignments."
        },
        {
          "name": "civil3d_intersection_get",
          "description": "Gets detailed intersection properties."
        }
      ],
      "count": 4
    },
    {
      "module": "Job",
      "file": "jobDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_job",
          "description": "Checks job status or requests cancellation for long-running Civil 3D operations."
        }
      ],
      "count": 1
    },
    {
      "module": "Parcel",
      "file": "parcelDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_parcel",
          "description": "Reads, creates, edits, adjusts, and reports Civil 3D parcel and site data through a single domain tool."
        },
        {
          "name": "civil3d_parcel_create",
          "description": "Creates a new Civil 3D parcel from a closed source object or a vertex list."
        },
        {
          "name": "civil3d_parcel_edit",
          "description": "Edits Civil 3D parcel metadata and styles without changing geometry."
        },
        {
          "name": "civil3d_parcel_lot_line_adjust",
          "description": "Adjusts a parcel lot line until a target area is reached within tolerance."
        },
        {
          "name": "civil3d_parcel_report",
          "description": "Generates a parcel area and dimension report for one or more parcels in a site."
        }
      ],
      "count": 5
    },
    {
      "module": "Pipe",
      "file": "pipeDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_pipe",
          "description": "Reads, analyzes, designs, and manages Civil 3D gravity and pressure pipe systems through a single domain tool."
        },
        {
          "name": "civil3d_pipe_network",
          "description": "Reads Civil 3D pipe network data including networks, pipes, structures, and interference checks."
        },
        {
          "name": "civil3d_pipe_network_edit",
          "description": "Creates and modifies Civil 3D pipe networks, pipes, and structures."
        },
        {
          "name": "civil3d_pipe_catalog",
          "description": "Lists available Civil 3D pipe parts lists and part names to help choose valid inputs for pipe network creation and editing tools."
        },
        {
          "name": "civil3d_pipe_network_hgl_calculate",
          "description": "Calculates hydraulic grade line and energy grade line values for a gravity pipe network."
        },
        {
          "name": "civil3d_pipe_hydraulic_analysis",
          "description": "Runs hydraulic capacity analysis on a gravity pipe network using Manning-based checks."
        },
        {
          "name": "civil3d_pipe_structure_properties",
          "description": "Retrieves detailed properties for a structure in a gravity pipe network."
        },
        {
          "name": "civil3d_pipe_network_size",
          "description": "Sizes gravity-network pipes from Manning full-flow capacity, chooses matching catalog parts, and optionally applies the selected sizes back to the drawing."
        },
        {
          "name": "civil3d_pipe_profile_view_automation",
          "description": "Automates a gravity-pipe profile-view setup by resolving the network alignment/surface, creating an EG profile if needed, and creating the profile view with optional style and band set."
        },
        {
          "name": "civil3d_pressure_network_list",
          "description": "Lists all pressure networks in the active Civil 3D drawing with summary counts for pipes, fittings, and appurtenances."
        },
        {
          "name": "civil3d_pressure_network_get_info",
          "description": "Gets detailed information about a pressure network including its pipes, fittings, and appurtenances."
        },
        {
          "name": "civil3d_pressure_network_create",
          "description": "Creates a new pressure network in the active Civil 3D drawing."
        },
        {
          "name": "civil3d_pressure_network_delete",
          "description": "Deletes a pressure network and all its components from the drawing."
        },
        {
          "name": "civil3d_pressure_network_assign_parts_list",
          "description": "Assigns a pressure parts list to an existing pressure network."
        },
        {
          "name": "civil3d_pressure_network_set_cover",
          "description": "Sets minimum and optional maximum cover requirements for a pressure network."
        },
        {
          "name": "civil3d_pressure_network_validate",
          "description": "Validates a pressure network for cover violations, disconnected components, and parts mismatches."
        },
        {
          "name": "civil3d_pressure_network_export",
          "description": "Exports a pressure network as structured data including pipes, fittings, and appurtenances."
        },
        {
          "name": "civil3d_pressure_network_connect",
          "description": "Connects two pressure networks by merging the source network into the target network."
        },
        {
          "name": "civil3d_pressure_pipe_add",
          "description": "Adds a pressure pipe segment to an existing pressure network."
        },
        {
          "name": "civil3d_pressure_pipe_get_properties",
          "description": "Gets detailed properties of a specific pressure pipe including diameter, length, material, and cover depth."
        },
        {
          "name": "civil3d_pressure_pipe_resize",
          "description": "Changes the part and optional diameter of an existing pressure pipe."
        },
        {
          "name": "civil3d_pressure_fitting_add",
          "description": "Adds a pressure fitting such as an elbow, tee, reducer, or cap to a pressure network."
        },
        {
          "name": "civil3d_pressure_fitting_get_properties",
          "description": "Gets detailed properties of a pressure fitting including type, location, and part size."
        },
        {
          "name": "civil3d_pressure_appurtenance_add",
          "description": "Adds a pressure appurtenance such as a valve, hydrant, or meter to a pressure network."
        }
      ],
      "count": 24
    },
    {
      "module": "Planproduction",
      "file": "planProductionDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_plan_production",
          "description": "Lists, creates, updates, and publishes Civil 3D sheet sets, sheets, plan/profile sheets, and sheet views through a single domain tool."
        },
        {
          "name": "civil3d_sheet_set_list",
          "description": "Lists all Plan Production sheet sets in the active drawing."
        },
        {
          "name": "civil3d_sheet_set_get_info",
          "description": "Gets detailed information about a Plan Production sheet set including all sheets."
        },
        {
          "name": "civil3d_sheet_set_create",
          "description": "Creates a new Plan Production sheet set in the active drawing."
        },
        {
          "name": "civil3d_sheet_add",
          "description": "Adds a new sheet to an existing Plan Production sheet set."
        },
        {
          "name": "civil3d_sheet_get_properties",
          "description": "Gets full properties of a specific sheet within a Plan Production sheet set."
        },
        {
          "name": "civil3d_sheet_set_title_block",
          "description": "Sets or updates the title block template on a sheet within a Plan Production sheet set."
        },
        {
          "name": "civil3d_plan_profile_sheet_create",
          "description": "Creates a plan/profile sheet for a given alignment and optional profile."
        },
        {
          "name": "civil3d_plan_profile_sheet_update_alignment",
          "description": "Updates the alignment and optionally the profile on an existing Plan/Profile sheet."
        },
        {
          "name": "civil3d_sheet_view_create",
          "description": "Creates a viewport or view on a sheet layout."
        },
        {
          "name": "civil3d_sheet_view_set_scale",
          "description": "Updates the scale of a viewport on a sheet layout."
        },
        {
          "name": "civil3d_sheet_publish_pdf",
          "description": "Publishes one or more sheet layouts to a PDF file."
        },
        {
          "name": "civil3d_sheet_set_export",
          "description": "Exports all sheets in a Plan Production sheet set to a single multi-page PDF."
        }
      ],
      "count": 13
    },
    {
      "module": "Plugin",
      "file": "pluginDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_health",
          "description": "Reports the status of the Civil 3D connection and plugin."
        }
      ],
      "count": 1
    },
    {
      "module": "Point",
      "file": "pointDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_point",
          "description": "Reads, creates, imports, transforms, exports, and deletes Civil 3D COGO points and point groups through a single domain tool."
        },
        {
          "name": "create_cogo_point",
          "description": "Creates a single new COGO point in the Civil 3D drawing."
        },
        {
          "name": "civil3d_point_group_create",
          "description": "Creates a new Civil 3D point group with optional filter criteria."
        },
        {
          "name": "civil3d_point_group_update",
          "description": "Updates filter criteria and description of an existing Civil 3D point group."
        },
        {
          "name": "civil3d_point_group_delete",
          "description": "Deletes a Civil 3D point group without deleting the underlying COGO points."
        },
        {
          "name": "civil3d_point_export",
          "description": "Exports Civil 3D COGO points to text or CSV using optional group or point-number filters."
        },
        {
          "name": "civil3d_point_transform",
          "description": "Transforms Civil 3D COGO points by translation, rotation, and/or scaling."
        }
      ],
      "count": 7
    },
    {
      "module": "Profile",
      "file": "profileDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_profile",
          "description": "Reads Civil 3D vertical profiles, reports geometry, and manages creation, editing, and deletion through a single domain tool."
        },
        {
          "name": "civil3d_profile_report",
          "description": "Builds a structured profile report by fetching profile detail and sampling elevations along the profile range."
        },
        {
          "name": "civil3d_profile_add_pvi",
          "description": "Adds a PVI (Point of Vertical Intersection) to a Civil 3D layout profile at the specified station and elevation."
        },
        {
          "name": "civil3d_profile_delete_pvi",
          "description": "Deletes the PVI nearest to the specified station from a Civil 3D layout profile."
        },
        {
          "name": "civil3d_profile_add_curve",
          "description": "Adds a symmetric or asymmetric parabolic vertical curve at an existing PVI in a Civil 3D layout profile."
        },
        {
          "name": "civil3d_profile_set_grade",
          "description": "Sets the grade (slope) of a tangent entity in a Civil 3D layout profile. Grade is expressed as a decimal fraction (0.02 = 2%)."
        },
        {
          "name": "civil3d_profile_get_elevation",
          "description": "Samples the elevation and instantaneous grade of a Civil 3D profile at a given station."
        },
        {
          "name": "civil3d_profile_check_k_values",
          "description": "Validates the K value of every vertical curve in a Civil 3D layout profile against AASHTO minimum K values for the specified design speed. Returns a pass/fail report per curve."
        },
        {
          "name": "civil3d_profile_view_create",
          "description": "Creates a Civil 3D profile view at the specified insertion point in model space. Optionally applies a style and band set."
        },
        {
          "name": "civil3d_profile_view_band_set",
          "description": "Applies a band set style to an existing Civil 3D profile view, updating the data bands displayed above and below the grid."
        }
      ],
      "count": 10
    },
    {
      "module": "Project",
      "file": "projectDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_project",
          "description": "Manages Civil 3D project collaboration workflows including data-shortcut listing, publishing, referencing, promotion, and synchronization through a single domain tool."
        },
        {
          "name": "civil3d_data_shortcut",
          "description": "Lists, synchronizes, and creates data-shortcut references."
        },
        {
          "name": "civil3d_data_shortcut_create",
          "description": "Publishes a Civil 3D object as a project data shortcut."
        },
        {
          "name": "civil3d_data_shortcut_promote",
          "description": "Promotes a read-only data shortcut reference to a local editable object."
        },
        {
          "name": "civil3d_data_shortcut_reference",
          "description": "References an existing project data shortcut into the current drawing."
        },
        {
          "name": "civil3d_data_shortcut_sync",
          "description": "Synchronizes outdated Civil 3D data shortcut references."
        }
      ],
      "count": 6
    },
    {
      "module": "Qc",
      "file": "qcDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_qc",
          "description": "Runs Civil 3D quality-control checks for alignments, profiles, corridors, pipe networks, surfaces, and consolidated QC reporting through a single domain tool."
        },
        {
          "name": "civil3d_qc_check_alignment",
          "description": "Runs QC checks on a Civil 3D alignment."
        },
        {
          "name": "civil3d_qc_check_profile",
          "description": "Runs QC checks on a Civil 3D profile."
        },
        {
          "name": "civil3d_qc_check_corridor",
          "description": "Runs QC checks on a Civil 3D corridor."
        },
        {
          "name": "civil3d_qc_check_pipe_network",
          "description": "Runs QC checks on a Civil 3D pipe network."
        },
        {
          "name": "civil3d_qc_check_surface",
          "description": "Runs QC checks on a Civil 3D TIN surface."
        },
        {
          "name": "civil3d_qc_report_generate",
          "description": "Runs a full QC pass over the active drawing and writes a consolidated report to disk."
        }
      ],
      "count": 7
    },
    {
      "module": "Quantitytakeoff",
      "file": "quantityTakeoffDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_quantity_takeoff",
          "description": "Calculates corridor, surface, network, parcel, alignment, point-group, material-list, earthwork, and export quantity-takeoff operations through a single domain tool."
        },
        {
          "name": "civil3d_qty_corridor_volumes",
          "description": "Calculates corridor material volumes."
        },
        {
          "name": "civil3d_qty_surface_volume",
          "description": "Calculates cut/fill volume between two surfaces."
        },
        {
          "name": "civil3d_qty_pipe_network_lengths",
          "description": "Summarizes gravity pipe-network lengths."
        },
        {
          "name": "civil3d_qty_pressure_network_lengths",
          "description": "Summarizes pressure-network lengths."
        },
        {
          "name": "civil3d_qty_parcel_areas",
          "description": "Lists parcel areas and perimeter data."
        },
        {
          "name": "civil3d_qty_alignment_lengths",
          "description": "Calculates alignment lengths."
        },
        {
          "name": "civil3d_qty_point_count_by_group",
          "description": "Counts points by point group."
        },
        {
          "name": "civil3d_qty_export_to_csv",
          "description": "Exports a consolidated quantity report to CSV."
        },
        {
          "name": "civil3d_qty_material_list_get",
          "description": "Gets a corridor material list and optional quantities."
        },
        {
          "name": "civil3d_qty_earthwork_summary",
          "description": "Generates an earthwork summary between surfaces."
        }
      ],
      "count": 11
    },
    {
      "module": "Section",
      "file": "sectionDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_section",
          "description": "Reads Civil 3D section data, manages sample lines, and controls section view creation and export through a single domain tool."
        },
        {
          "name": "civil3d_section_view_create",
          "description": "Create Civil 3D section views for a sample line group at the specified insertion point. Optionally applies a style, band set, and constrains to a station range."
        },
        {
          "name": "civil3d_section_view_list",
          "description": "List Civil 3D section views in the active drawing, optionally filtered by alignment and sample line group."
        },
        {
          "name": "civil3d_section_view_update_style",
          "description": "Update the display style and/or band set style on existing Civil 3D section views for a sample line group."
        },
        {
          "name": "civil3d_section_view_group_create",
          "description": "Create a Civil 3D section view group — a multi-row grid layout of section views for all stations in a sample line group."
        },
        {
          "name": "civil3d_section_view_export",
          "description": "Export Civil 3D section data to a CSV or text file, including station, offset, and surface elevation data per section."
        }
      ],
      "count": 6
    },
    {
      "module": "Sightdistance",
      "file": "sightDistanceDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_sight_distance",
          "description": "Calculates and checks sight distance compliance through a single domain tool."
        },
        {
          "name": "civil3d_sight_distance_calculate",
          "description": "Calculates required sight distance."
        },
        {
          "name": "civil3d_stopping_distance_check",
          "description": "Checks stopping sight distance along an alignment/profile."
        }
      ],
      "count": 3
    },
    {
      "module": "Slopeanalysis",
      "file": "slopeAnalysisDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_slope_analysis",
          "description": "Calculates slope geometry and checks slope stability through a single domain tool."
        },
        {
          "name": "civil3d_slope_geometry_calculate",
          "description": "Calculates daylight and slope geometry along an alignment."
        },
        {
          "name": "civil3d_slope_stability_check",
          "description": "Checks cut/fill slope stability limits."
        }
      ],
      "count": 3
    },
    {
      "module": "Standards",
      "file": "standardsDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_standards",
          "description": "Inspects and manages Civil 3D styles, labels, standards guidance, and drawing-standard compliance through a single domain tool."
        },
        {
          "name": "civil3d_label",
          "description": "Manages labels on Civil 3D objects."
        },
        {
          "name": "civil3d_style",
          "description": "Lists and inspects Civil 3D styles for supported object types."
        },
        {
          "name": "civil3d_standards_lookup",
          "description": "Looks up Civil 3D standards, template governance, layer/style guidance, and labeling conventions."
        },
        {
          "name": "civil3d_qc_check_labels",
          "description": "Checks Civil 3D labels for missing labels and style-standard violations."
        },
        {
          "name": "civil3d_qc_check_drawing_standards",
          "description": "Audits the active drawing against CAD standards for layer naming, lineweights, and colors."
        },
        {
          "name": "civil3d_qc_fix_drawing_standards",
          "description": "Automatically remediates drawing-standard layer issues."
        }
      ],
      "count": 7
    },
    {
      "module": "Superelevation",
      "file": "superelevationDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_superelevation",
          "description": "Gets, sets, checks, and reports alignment superelevation through a single domain tool."
        },
        {
          "name": "civil3d_superelevation_get",
          "description": "Gets alignment superelevation data."
        },
        {
          "name": "civil3d_superelevation_set",
          "description": "Applies superelevation design to an alignment."
        },
        {
          "name": "civil3d_superelevation_design_check",
          "description": "Checks superelevation design compliance."
        },
        {
          "name": "civil3d_superelevation_report",
          "description": "Generates a superelevation report."
        }
      ],
      "count": 5
    },
    {
      "module": "Surface",
      "file": "surfaceDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_surface",
          "description": "Reads, analyzes, edits, and automates Civil 3D surface workflows through a single domain tool."
        },
        {
          "name": "civil3d_surface_edit",
          "description": "Modifies Civil 3D surface data by adding points, breaklines, boundaries, extracting contours, and computing volumes."
        },
        {
          "name": "civil3d_surface_volume_calculate",
          "description": "Calculate cut/fill volumes between two Civil 3D surfaces."
        },
        {
          "name": "civil3d_surface_volume_report",
          "description": "Generate a formatted volume report comparing two Civil 3D surfaces."
        },
        {
          "name": "civil3d_surface_volume_by_region",
          "description": "Calculate cut/fill volumes between two surfaces within a specific polygon region boundary."
        },
        {
          "name": "civil3d_surface_analyze_slope",
          "description": "Analyze slope distribution across a Civil 3D surface."
        },
        {
          "name": "civil3d_surface_analyze_elevation",
          "description": "Analyze elevation band distribution across a Civil 3D surface."
        },
        {
          "name": "civil3d_surface_analyze_directions",
          "description": "Analyze aspect and facing-direction distribution across a Civil 3D surface."
        },
        {
          "name": "civil3d_surface_watershed_add",
          "description": "Adds watershed analysis results to a Civil 3D surface."
        },
        {
          "name": "civil3d_surface_contour_interval_set",
          "description": "Set minor and major contour display intervals for a Civil 3D surface."
        },
        {
          "name": "civil3d_surface_statistics_get",
          "description": "Retrieve detailed statistics for a single Civil 3D surface."
        },
        {
          "name": "civil3d_surface_sample_elevations",
          "description": "Sample elevations on a Civil 3D surface using grid, point, or transect methods."
        },
        {
          "name": "civil3d_surface_create_from_dem",
          "description": "Create a Civil 3D TIN surface by importing a DEM or raster terrain file."
        },
        {
          "name": "civil3d_surface_comparison_workflow",
          "description": "Builds a structured surface comparison by fetching two surfaces and computing cut/fill differences."
        },
        {
          "name": "civil3d_surface_drainage_workflow",
          "description": "Runs a surface drainage workflow by tracing a flow path, sampling elevations, and estimating runoff."
        }
      ],
      "count": 15
    },
    {
      "module": "Survey",
      "file": "surveyDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_survey",
          "description": "Lists, creates, imports, and manages Civil 3D survey databases, figures, observations, and network adjustments through a single domain tool."
        },
        {
          "name": "civil3d_survey_database_list",
          "description": "Lists Civil 3D survey databases associated with the current drawing."
        },
        {
          "name": "civil3d_survey_database_create",
          "description": "Creates a new Civil 3D survey database."
        },
        {
          "name": "civil3d_survey_figure_list",
          "description": "Lists survey figures in one or more Civil 3D survey databases."
        },
        {
          "name": "civil3d_survey_figure_get",
          "description": "Gets detailed vertex data for a specific Civil 3D survey figure."
        },
        {
          "name": "civil3d_survey_observation_list",
          "description": "Lists raw field-book observations stored in a Civil 3D survey database."
        },
        {
          "name": "civil3d_survey_network_adjust",
          "description": "Performs a traverse or least-squares adjustment on a Civil 3D survey network."
        },
        {
          "name": "civil3d_survey_figure_create",
          "description": "Creates a new survey figure by connecting existing survey points in order."
        },
        {
          "name": "civil3d_survey_landxml_import",
          "description": "Imports survey data from a LandXML file into a Civil 3D survey database and/or drawing."
        }
      ],
      "count": 9
    },
    {
      "module": "Workflow",
      "file": "workflowDomain.ts",
      "tools_list": [
        {
          "name": "civil3d_workflow",
          "description": "Runs multi-step Civil 3D workflows that compose existing QC, grading, surface, project, survey, pipe-design, standards, and plan-production operations through a single domain tool."
        },
        {
          "name": "civil3d_workflow_corridor_qc_report",
          "description": "Runs corridor QC and optionally generates a consolidated QC report file."
        },
        {
          "name": "civil3d_workflow_grading_surface_volume",
          "description": "Calculates grading surface cut/fill volume between an existing and proposed surface."
        },
        {
          "name": "civil3d_workflow_surface_comparison_report",
          "description": "Runs a structured surface comparison and follows it with a volume report."
        },
        {
          "name": "civil3d_workflow_data_shortcut_publish_sync",
          "description": "Publishes a data shortcut for a Civil 3D object and immediately synchronizes it."
        },
        {
          "name": "civil3d_workflow_data_shortcut_reference_sync",
          "description": "References a project data shortcut into the current drawing and immediately synchronizes it."
        },
        {
          "name": "civil3d_workflow_project_startup",
          "description": "Checks plugin health, optionally creates a startup drawing, inspects drawing readiness, lists data shortcuts, and can save the startup drawing."
        },
        {
          "name": "civil3d_workflow_project_reference_setup",
          "description": "References one or more project data shortcuts, synchronizes them, reviews the resulting shortcut state, and can save the drawing."
        },
        {
          "name": "civil3d_workflow_drawing_readiness_audit",
          "description": "Checks plugin health, drawing metadata, settings, object types, current selection, and drawing standards in one readiness audit."
        },
        {
          "name": "civil3d_workflow_feature_line_to_grading",
          "description": "Inspects a feature line, optionally creates a grading group, builds grading from it, and can generate a grading surface."
        },
        {
          "name": "civil3d_workflow_pipe_network_design",
          "description": "Sizes a gravity pipe network and optionally follows it with a hydraulic analysis pass."
        },
        {
          "name": "civil3d_workflow_plan_production_publish",
          "description": "Publishes either a named sheet set or an explicit list of layouts to a PDF output."
        },
        {
          "name": "civil3d_workflow_qc_fix_and_verify",
          "description": "Audits drawing standards, applies fixes, and re-runs the audit to verify compliance."
        },
        {
          "name": "civil3d_workflow_survey_import_adjust_figures",
          "description": "Imports survey LandXML, optionally adjusts a network, optionally creates a figure, and lists resulting survey figures."
        }
      ],
      "count": 14
    }
  ],
  "graph_stats": {
    "nodes": 195,
    "edges": 0,
    "communities": 20,
    "active": true
  },
  "timeline": [
    {
      "file": "matriz.csv",
      "path": "verificacion/matriz.csv",
      "source": "Workspace",
      "mtime": 1786471207.9627907,
      "date": "2026-08-11 14:00",
      "date_raw": "2026-08-11T14:00:07.962791"
    },
    {
      "file": "router.py",
      "path": "skills/router.py",
      "source": "Workspace",
      "mtime": 1786471186.4226403,
      "date": "2026-08-11 13:59",
      "date_raw": "2026-08-11T13:59:46.422640"
    },
    {
      "file": "terrazas-taludes-calzadas.skill.md",
      "path": "skills/loteo/terrazas-taludes-calzadas.skill.md",
      "source": "Workspace",
      "mtime": 1786471186.4226403,
      "date": "2026-08-11 13:59",
      "date_raw": "2026-08-11T13:59:46.422640"
    },
    {
      "file": "terrazas_lib.py",
      "path": "skills/loteo/scripts/terrazas_lib.py",
      "source": "Workspace",
      "mtime": 1786471186.421801,
      "date": "2026-08-11 13:59",
      "date_raw": "2026-08-11T13:59:46.421801"
    },
    {
      "file": "vialidad_lib.py",
      "path": "skills/loteo/scripts/vialidad_lib.py",
      "source": "Workspace",
      "mtime": 1786471186.421801,
      "date": "2026-08-11 13:59",
      "date_raw": "2026-08-11T13:59:46.421801"
    },
    {
      "file": "rasantes_lib.py",
      "path": "skills/loteo/scripts/rasantes_lib.py",
      "source": "Workspace",
      "mtime": 1786471186.4207964,
      "date": "2026-08-11 13:59",
      "date_raw": "2026-08-11T13:59:46.420796"
    },
    {
      "file": "rasantes_red.py",
      "path": "skills/loteo/scripts/rasantes_red.py",
      "source": "Workspace",
      "mtime": 1786471186.4207964,
      "date": "2026-08-11 13:59",
      "date_raw": "2026-08-11T13:59:46.420796"
    },
    {
      "file": "loteo_io.py",
      "path": "skills/loteo/scripts/loteo_io.py",
      "source": "Workspace",
      "mtime": 1786471186.4192922,
      "date": "2026-08-11 13:59",
      "date_raw": "2026-08-11T13:59:46.419292"
    },
    {
      "file": "mesh_io.py",
      "path": "skills/loteo/scripts/mesh_io.py",
      "source": "Workspace",
      "mtime": 1786471186.4192922,
      "date": "2026-08-11 13:59",
      "date_raw": "2026-08-11T13:59:46.419292"
    },
    {
      "file": "dashboard_data.json",
      "path": "dashboard_data.json",
      "source": "Workspace",
      "mtime": 1786471186.4182923,
      "date": "2026-08-11 13:59",
      "date_raw": "2026-08-11T13:59:46.418292"
    },
    {
      "file": "dashboard_data.js",
      "path": "dashboard_data.js",
      "source": "Workspace",
      "mtime": 1786471186.4172926,
      "date": "2026-08-11 13:59",
      "date_raw": "2026-08-11T13:59:46.417293"
    },
    {
      "file": "session_logs.json",
      "path": "verificacion/session_logs.json",
      "source": "Workspace",
      "mtime": 1786469608.112259,
      "date": "2026-08-11 13:33",
      "date_raw": "2026-08-11T13:33:28.112259"
    }
  ],
  "session_logs": [
    {
      "timestamp": "2026-08-11 12:45:00",
      "task": "Terreno existente de South Island (Surface_Exis_SI): LandXML a Toposolid de Revit con diezmado controlado, 2 piezas y 10 huecos",
      "corrections": "Los huecos que TOCAN el contorno exterior invalidan el argumento 'profiles' de Toposolid.Create. 3 de los 10 huecos estaban a 0.0000 ft del borde y tumbaban la pieza grande entera; se anadio min_dist_loop_to_loop() al script de Dynamo para descartar los que queden a menos de 0.05 ft. Tras el arreglo, 2 de 2 piezas OK.",
      "warnings": "Filtrar SIEMPRE las caras con i=\"1\" del LandXML antes de reconstruir la huella: aqui eran 11,676 de 220,482 y sin filtrarlas el area sale mas del doble (1,127,492 ft2 contra 490,244.56 reales).",
      "limitations": "Un Toposolid es un campo de alturas 2,5D: las 163 caras de mas de 70 grados (hasta 88.5) salen como rampas y no se arreglan con mas puntos. Mandar los 105,419 puntos en vez de 7,711 no mejora la fidelidad: la empeora en la cola, porque Revit re-triangula por Delaunay y pierde las lineas de rotura del TIN.",
      "status": "OK"
    },
    {
      "timestamp": "2026-08-10 10:27:00",
      "task": "Ajuste de georreferenciacion del paquete de las 22 superficies de South Island contra el modelo de Revit de destino",
      "corrections": "OFFSET_X/OFFSET_Y pasan de 0.0 a +1,702.20 / -3,792.42, medidos comparando 3 vertices de control entre la importacion de Dynamo y el modelo de Revit. El vector sale identico en los 3 puntos.",
      "warnings": "Ese offset NO es una propiedad del sistema de coordenadas y no se puede copiar entre islas ni entre modelos: es un ajuste medido. North Island usa otro (-3,298.08 / +2,207.36) y otro origen local.",
      "limitations": "LEEME_INSTRUCCIONES_USO.md del paquete de las 22 carpetas quedo desactualizado: sigue diciendo que los offsets valen 0.0 mientras el .py y el .txt ya llevan los valores medidos.",
      "status": "OK"
    },
    {
      "timestamp": "2026-08-07 16:15:00",
      "task": "Entrega de las 22 superficies de carpeta de South Island como Toposolid de Revit 2026",
      "corrections": "El .dyn y el .py sueltos se unificaron con el MISMO codigo (en North Island habian divergido: el .dyn tenia reanudacion y el .py no).",
      "warnings": "Origen local propio de South Island (E 12,124,000 / N 3,524,500), distinto del de North Island (E 12,119,000 / N 3,530,500) y no intercambiable.",
      "limitations": "Contornos simplificados con Douglas-Peucker a 0.001 ft: de 21,073 a 5,886 vertices, con hueco maximo de 0.00008 ft entre superficies adyacentes.",
      "status": "OK"
    },
    {
      "timestamp": "2026-08-02 18:59:00",
      "task": "Estudio de terrazación en 4 lotes, traslación neutral LandXML y cubicación por regiones",
      "corrections": "Corrección de error de unidades en informe y esquemas (asumición de metros corregida a Sistema Imperial nativo ft, sq ft, cu yd). Rediseño proporcionado de la tabla de cubicación en informe HTML y ajuste de proporciones en el Dashboard QA.",
      "warnings": "Regla Mandatoria 7: Inspección indispensable de la etiqueta <Units> en archivos LandXML antes de procesar superficies. Asumir metros en terrenos medidos en pies altera los volúmenes en 35.31x.",
      "limitations": "civil3d_surface_volume_by_region catalogada como WIP (práctica y con alto potencial, en proceso de perfeccionamiento en Civil 3D 2026). ProfileView.Create desactualizado para firmas .NET de C3D 2026.",
      "status": "WIP"
    },
    {
      "timestamp": "2026-08-01 17:30:00",
      "task": "Extracción de superficies TIN desde LandXML e importación de Toposolid en Revit 2026",
      "corrections": "Eliminación de estalactitas y desplomes en mallas TIN, corrección de Slab Shape Edit failed mediante Dynamo y georreferenciación de mallas.",
      "warnings": "Archivos LandXML con superficies unificadas requieren extracción individual previa para evitar sobrecarga en Revit.",
      "limitations": "Dynamo requiere ejecutar en modo autónomo de 10-15s para mallas densas de más de 10,000 caras.",
      "status": "OK"
    },
    {
      "timestamp": "2026-07-30 16:00:00",
      "task": "Muestreo de cotas TIN y auditoría básica de dibujo DWG en Civil 3D 2026",
      "corrections": "Sanitización de rutas locales en matriz.csv y corrección de codificación UTF-8.",
      "warnings": "Puntos COGO sin grupo predeterminado pueden perder descripciones avanzadas.",
      "limitations": "delete_cogo_point genera excepción COM al eliminar entidades por ID directo.",
      "status": "OK"
    }
  ]
};
