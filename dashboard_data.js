window.DASHBOARD_DATA = {
  "last_update": "2026-08-01 13:32:57",
  "stats": {
    "total_skills": 7,
    "total_tests": 5,
    "tests_ok": 3,
    "tests_falla": 1,
    "tests_wip": 1,
    "total_server_tools": 216,
    "total_server_modules": 30
  },
  "skills": [
    {
      "name": "teselado_arcos_polilinea",
      "description": "Tesela polilíneas DXF que contienen arcos (bulges) muestreando directamente la circunferencia real con una tolerancia de sagitta máxima.",
      "category": "Geometria",
      "file_path": "skills/geometria/teselado-arcos-polilinea.skill.md"
    },
    {
      "name": "generacion_planos_svg",
      "description": "Genera planos vectoriales SVG de verificación topográfica (TIN, perímetros, cotas, leyendas, escala gráfica y norte) sin requerir matplotlib ni librerías gráficas externas.",
      "category": "Reportes",
      "file_path": "skills/reportes/generacion-planos-svg.skill.md"
    },
    {
      "name": "plano_svg_verificacion",
      "description": "Sistema de planos SVG de verificación para Civil 3D y topografía: escribe el SVG como texto plano, sin matplotlib ni librerías gráficas, con escala única, norte, escala gráfica, leyenda y rampa de color validada.",
      "category": "Reportes",
      "file_path": "skills/reportes/plano-svg.skill.md"
    },
    {
      "name": "auditoria_superficies_landxml",
      "description": "Audita la integridad geométrica y estructural de archivos LandXML TIN: caras invisibles (i='1'), orden de coordenadas Norte/Este vs X/Y, unidades del dibujo y conservación de áreas 2D/3D.",
      "category": "Superficies",
      "file_path": "skills/superficies/auditoria-superficies-landxml.skill.md"
    },
    {
      "name": "drapeado_contorno_3d",
      "description": "Drapea polilíneas 2D sobre mallas TIN LandXML interpolando cotas Z para exportar polilíneas 3D en DXF aptas como Breaklines o Boundaries en Civil 3D.",
      "category": "Superficies",
      "file_path": "skills/superficies/drapeado-contorno-3d.skill.md"
    },
    {
      "name": "recorte_superficie_con_perimetro",
      "description": "Recorta una superficie TIN de LandXML con un perímetro cerrado de un DXF y entrega el área interior 2D y 3D, un plano SVG de verificación, el LandXML de la superficie cortada y el contorno en DXF.",
      "category": "Superficies",
      "file_path": "skills/superficies/recorte-superficie.skill.md"
    },
    {
      "name": "revision_curvas_verticales",
      "description": "Revisión de curvas verticales y valores K en perfiles longitudinales de Civil 3D según criterios de diseño vial y normativas configurables.",
      "category": "Vialidad",
      "file_path": "skills/vialidad/revision-curvas-verticales.skill.md"
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
      "notas": "Devuelve correctamente metadatos del dibujo"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "list_civil_object_types",
      "version_c3d": "2026",
      "dwg_prueba": "tests/dwg/02_superficies_par.dwg",
      "resultado": "OK",
      "evidencia": "consola",
      "fecha": "2026-07-30",
      "notas": "Cuenta superficies y alineaciones"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "create_cogo_point",
      "version_c3d": "2026",
      "dwg_prueba": "tests/dwg/01_vacio.dwg",
      "resultado": "WIP",
      "evidencia": "tests/dwg/cogo_vacio.dwg",
      "fecha": "2026-07-30",
      "notas": "El punto se crea pero la descripción se omite"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "sample_surface_elevation",
      "version_c3d": "2026",
      "dwg_prueba": "tests/dwg/02_superficies_par.dwg",
      "resultado": "OK",
      "evidencia": "consola",
      "fecha": "2026-07-30",
      "notas": "Interpola cotas correctamente"
    },
    {
      "servidor": "civil3d-mcp",
      "tool": "delete_cogo_point",
      "version_c3d": "2026",
      "dwg_prueba": "tests/dwg/01_vacio.dwg",
      "resultado": "FALLA",
      "evidencia": "consola",
      "fecha": "2026-07-30",
      "notas": "Excepción COM al intentar eliminar"
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
      "file": "package.json",
      "path": "package.json",
      "source": "Workspace",
      "mtime": 1785605112.2566922,
      "date": "2026-08-01 13:25",
      "date_raw": "2026-08-01T13:25:12.256692"
    },
    {
      "file": "dashboard_data.js",
      "path": "dashboard_data.js",
      "source": "Workspace",
      "mtime": 1785604608.7540739,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:48.754074"
    },
    {
      "file": "dashboard_data.json",
      "path": "dashboard_data.json",
      "source": "Workspace",
      "mtime": 1785604608.7540739,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:48.754074"
    },
    {
      "file": "test_router.py",
      "path": "skills/tests/test_router.py",
      "source": "Workspace",
      "mtime": 1785604602.4043071,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:42.404307"
    },
    {
      "file": "test_recorte.py",
      "path": "skills/superficies/scripts/test_recorte.py",
      "source": "Workspace",
      "mtime": 1785604602.4033105,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:42.403311"
    },
    {
      "file": "test_auditoria.py",
      "path": "skills/superficies/scripts/test_auditoria.py",
      "source": "Workspace",
      "mtime": 1785604602.4023118,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:42.402312"
    },
    {
      "file": "test_drapeado.py",
      "path": "skills/superficies/scripts/test_drapeado.py",
      "source": "Workspace",
      "mtime": 1785604602.4023118,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:42.402312"
    },
    {
      "file": "drapear_contorno.py",
      "path": "skills/superficies/scripts/drapear_contorno.py",
      "source": "Workspace",
      "mtime": 1785604602.4013114,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:42.401311"
    },
    {
      "file": "recortar_superficie.py",
      "path": "skills/superficies/scripts/recortar_superficie.py",
      "source": "Workspace",
      "mtime": 1785604602.4013114,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:42.401311"
    },
    {
      "file": "auditar_superficie.py",
      "path": "skills/superficies/scripts/auditar_superficie.py",
      "source": "Workspace",
      "mtime": 1785604602.4003112,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:42.400311"
    },
    {
      "file": "drapeado-contorno-3d.skill.md",
      "path": "skills/superficies/drapeado-contorno-3d.skill.md",
      "source": "Workspace",
      "mtime": 1785604602.3993099,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:42.399310"
    },
    {
      "file": "recorte-superficie.skill.md",
      "path": "skills/superficies/recorte-superficie.skill.md",
      "source": "Workspace",
      "mtime": 1785604602.3993099,
      "date": "2026-08-01 13:16",
      "date_raw": "2026-08-01T13:16:42.399310"
    }
  ]
};
