# -*- coding: utf-8 -*-
# Agrupa entidades polyface/MESH de una capa por HUELLA XY compartida (mismo
# footprint = capas apiladas de un mismo paquete estructural). De cada grupo se
# queda SOLO con la malla mas alta (descarta las "inferiores") y extrae su cara
# superior expuesta como una superficie TIN aislada. Ademas, resuelve solapes
# ENTRE GRUPOS distintos: si dos superficies de grupos diferentes comparten
# huella y una esta consistentemente encima de la otra, la de abajo se descarta
# por completo (regla confirmada por el usuario 2026-07-06). Pares que se cruzan
# (sin dominancia limpia) se conservan ambos, marcados con advertencia.
# Salida: un LandXML con una <Surface> por grupo sobreviviente.
#
# Uso: mesh_grouped_top_only.py <dxf> <capa> <salida.xml> [prefijo=Superficie] [decimales_XY=4] [tol_footprint_ft=0.5]
import sys, json, ezdxf
from ezdxf.render import MeshBuilder
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from mesh_utils import solid_faces, solid_thickness_stats, weld_and_clean, boundary_holes, crossing_count, cluster_by_footprint, resolve_group_overlaps, write_landxml

dxf_path = sys.argv[1]; layer = sys.argv[2]; out_xml = sys.argv[3]
prefix = sys.argv[4] if len(sys.argv) > 4 else "Superficie"
DEC = int(sys.argv[5]) if len(sys.argv) > 5 else 4
TOL_FP = float(sys.argv[6]) if len(sys.argv) > 6 else 0.5

doc = ezdxf.readfile(dxf_path); msp = doc.modelspace()

raw = []
for e in msp:
    if e.dxf.layer != layer: continue
    t = e.dxftype()
    if t == "POLYLINE" and e.is_poly_face_mesh:
        raw.append(("POLYLINE", MeshBuilder.from_polyface(e)))
    elif t == "MESH":
        raw.append(("MESH", MeshBuilder.from_mesh(e)))

print(f"entidades encontradas en capa '{layer}': {len(raw)}")
if not raw:
    print("ERROR: no hay entidades polyface/MESH en esa capa"); sys.exit(2)

extents = []
for etype, mb in raw:
    xs = [v[0] for v in mb.vertices]; ys = [v[1] for v in mb.vertices]; zs = [v[2] for v in mb.vertices]
    extents.append({"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys),
                     "zmin": min(zs), "zmax": max(zs)})

groups = cluster_by_footprint(extents, tol=TOL_FP)
print(f"grupos por huella compartida (tol={TOL_FP} ft): {len(groups)}")

report_rows = []
surfaces = []
for gi, grp in enumerate(groups, 1):
    # elegir la malla mas alta del grupo (mayor Z maximo)
    top_local = max(grp, key=lambda i: extents[i]["zmax"])
    etype, mb = raw[top_local]
    n_discarded = len(grp) - 1

    # diagnostico de espesor (para detectar anomalias tipo Grupo 20: espesor variable)
    thick_stats, n_multi, n_total = solid_thickness_stats(mb, DEC)
    es_solido_diag = n_multi > 0 and n_multi >= 0.5 * n_total
    warns = []
    if es_solido_diag and thick_stats is not None:
        tmin, tmax, tmean, tstd = thick_stats
        if tstd > 0.05:  # umbral: espesor variable de forma significativa
            warns.append(f"ADV-EspesorVariable(mean{tmean:.2f}std{tstd:.2f})")
    if len(grp) == 2:  # falta la capa superior tipica (Carpeta Asfaltica) del paquete de 3
        warns.append("ADV-SinCapaSuperior")

    # extraer cara superior (si es solido) y limpiar
    mv, top_face_idx, es_solido = solid_faces(mb, DEC, "top")
    verts, faces, degen, dup = weld_and_clean(mv, top_face_idx, DEC)

    if not faces:
        print(f"  [G{gi:02d}] SIN CARAS VALIDAS -- omitida"); continue

    n_holes, nonman = boundary_holes(faces)
    nc = crossing_count(verts, faces)
    if nc:  # cruces internos detectados solo al ejecutar (no se sabe de antemano)
        warns.append(f"ADV-ClashesInternos{nc}")
    elif nc is None:  # malla grande: QA de cruces omitido, no confundir con "verificado limpio"
        warns.append("ADV-QAOmitidaMallaGrande")

    name = f"{prefix}_G{gi:02d}"
    if warns: name += "_" + "_".join(warns)

    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]; zs = [v[2] for v in verts]

    print(f"  [G{gi:02d}] {name}: capas_grupo={len(grp)} (descartadas={n_discarded})  "
          f"solido={es_solido}  vertices={len(verts)} caras={len(faces)} "
          f"(degen={degen} dup={dup})  huecos={n_holes}  no-manifold={nonman}  cruces={nc}")
    if warns:
        print(f"          *** {' | '.join(warns)} ***")
    warn = "_".join(warns) if warns else None

    surfaces.append((name, verts, faces))
    report_rows.append({
        "grupo": gi, "nombre": name, "n_capas_grupo": len(grp), "n_descartadas": n_discarded,
        "es_solido": es_solido, "espesor_top": (thick_stats[2] if thick_stats else None),
        "espesor_std": (thick_stats[3] if thick_stats else None),
        "warn": warn, "vertices": len(verts), "caras": len(faces),
        "degen": degen, "dup": dup, "huecos": n_holes, "nonmanifold": nonman, "cruces": nc,
        "xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys),
        "zmin": min(zs), "zmax": max(zs),
    })

# --- resolver solapes ENTRE GRUPOS: descartar la que esta debajo (regla confirmada) ---
print(f"\n=== Resolviendo solapes entre {len(surfaces)} superficies ===")
kept, discarded_info, mixed_info = resolve_group_overlaps(surfaces)

for d in discarded_info:
    print(f"  DESCARTADA: {d['name']}  (dominada por: {', '.join(d['dominated_by'])})")

# pares mixtos (cruzados, sin dominancia limpia): conservar ambas, marcar con advertencia
mixed_names = set()
for m in mixed_info:
    print(f"  MIXTO (conservar ambas, marcar): {m['name_a']} <-> {m['name_b']}  "
          f"(A arriba en {m['a_above']}, B arriba en {m['b_above']} de {m['n_shared']} pts)")
    mixed_names.add(m["name_a"]); mixed_names.add(m["name_b"])

final_surfaces = []
name_map = {}  # nombre original -> nombre final (con posible sufijo de advertencia)
for name, verts, faces in kept:
    final_name = name
    if name in mixed_names:
        partner = next(m["name_b"] if m["name_a"] == name else m["name_a"]
                        for m in mixed_info if name in (m["name_a"], m["name_b"]))
        final_name = f"{name}_ADV-CrucePlantaCon-{partner}"
    name_map[name] = final_name
    final_surfaces.append((final_name, verts, faces))

discarded_names = {d["name"] for d in discarded_info}
print(f"\nresultado: {len(final_surfaces)} superficies finales "
      f"({len(discarded_info)} descartadas, {len(mixed_info)} pares marcados con advertencia)")

write_landxml(out_xml, final_surfaces)
print(f"\nOK -> {out_xml}  ({len(final_surfaces)} superficies escritas)")

# actualizar el reporte: marcar descartadas y renombrar las de advertencia de cruce
for row in report_rows:
    if row["nombre"] in discarded_names:
        row["descartada_por_solape"] = True
        row["dominada_por"] = next(d["dominated_by"] for d in discarded_info if d["name"] == row["nombre"])
    else:
        row["descartada_por_solape"] = False
        if row["nombre"] in name_map and name_map[row["nombre"]] != row["nombre"]:
            new_name = name_map[row["nombre"]]
            added_tag = new_name[len(row["nombre"]):].lstrip("_")  # ej. ADV-CrucePlantaCon-Superficie_G34
            row["nombre"] = new_name
            row["warn"] = f"{row['warn']}_{added_tag}" if row["warn"] else added_tag

rep_path = out_xml.rsplit(".", 1)[0] + "_report.json"
with open(rep_path, "w", encoding="utf-8") as f:
    json.dump(report_rows, f, ensure_ascii=False, indent=1)
print(f"reporte de datos -> {rep_path}")
