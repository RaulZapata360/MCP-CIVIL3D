import sys, csv, re, multiprocessing
import ifcopenshell
import ifcopenshell.geom
import ezdxf
from ezdxf.render import MeshBuilder
from collections import Counter

ifc_path = sys.argv[1]
dxf_path = sys.argv[2]
scale_arg = sys.argv[3] if len(sys.argv) > 3 else "auto"   # "auto" = detectar unidad
csv_path = sys.argv[4] if len(sys.argv) > 4 else dxf_path.rsplit(".",1)[0] + "_manifest.csv"

print(f"IFC : {ifc_path}")
print(f"DXF : {dxf_path}")

f = ifcopenshell.open(ifc_path)
print(f"Schema: {f.schema}")

# --- Escala: auto-detecta unidad (foot -> 1.0 ; metre -> US survey foot) ---
if scale_arg == "auto":
    lu = "?"
    for ua in f.by_type("IfcUnitAssignment"):
        for u in ua.Units:
            if getattr(u, "UnitType", None) == "LENGTHUNIT":
                lu = ((u.Prefix or "") + u.Name) if u.is_a("IfcSIUnit") else (u.Name if u.is_a("IfcConversionBasedUnit") else lu)
    scale = 1.0 if ("foot" in lu.lower() or "feet" in lu.lower()) else 3.2808333333
    print(f"Unidad detectada: {lu}  ->  escala x{scale}")
elif scale_arg == "georef":
    # Modo correcto VA83-SF (US survey ft, ~12.1M): destino siempre US survey foot.
    # ifcopenshell (use-world-coords) entrega METROS (= valor_archivo * unit_scale).
    #  - Archivo en PIE (estructuras, unit_scale=0.3048): sus coords YA son State Plane ft.
    #    Para preservarlas verbatim hay que invertir el ×unit_scale -> scale = 1/unit_scale.
    #  - Archivo en METROS SI (caminos, unit_scale=1.0): convertir m->US survey ft -> 3.2808333333.
    import ifcopenshell.util.unit as _U
    us = _U.calculate_unit_scale(f)  # metros por unidad-de-archivo
    scale = (1.0/us) if abs(us-1.0) > 1e-9 else 3.2808333333
    print(f"georef: unit_scale={us}  ->  escala x{scale}")
else:
    scale = float(scale_arg)
    print(f"Escala aplicada: x{scale}")

# --- Mapa: id de item asignado -> capa CAD (Bentley). Items pueden ser
#     IfcShapeRepresentation, IfcRepresentationItem o IfcGeometricSet (IFC4x3 mapeado). ---
layer_by_item = {}
for pla in f.by_type("IfcPresentationLayerAssignment"):
    for item in (pla.AssignedItems or []):
        try: layer_by_item[item.id()] = pla.Name or "Default"
        except Exception: pass
print(f"Capas de presentacion: {len(set(layer_by_item.values()))}")

def resolve_layer(elem):
    rep = getattr(elem, "Representation", None)
    if rep:
        for sr in (rep.Representations or []):
            if sr.id() in layer_by_item: return layer_by_item[sr.id()]
            for it in (getattr(sr, "Items", None) or []):
                if it.id() in layer_by_item: return layer_by_item[it.id()]
                # representacion mapeada (IFC4x3): seguir al MappedRepresentation
                if it.is_a("IfcMappedItem"):
                    try:
                        mr = it.MappingSource.MappedRepresentation
                        if mr.id() in layer_by_item: return layer_by_item[mr.id()]
                        for mit in (mr.Items or []):
                            if mit.id() in layer_by_item: return layer_by_item[mit.id()]
                    except Exception: pass
    return "IFC_" + elem.is_a()

settings = ifcopenshell.geom.settings()
for k in ("use-world-coords",):
    try: settings.set(k, True)
    except Exception:
        try: settings.set(settings.USE_WORLD_COORDS, True)
        except Exception: pass
# incluir curvas/linework (baseline, bordes, breaklines)
for k in ("include-curves",):
    try: settings.set(k, True)
    except Exception:
        try: settings.set(settings.INCLUDE_CURVES, True)
        except Exception: pass

doc = ezdxf.new("R2018")
doc.header["$INSUNITS"] = 0  # 0 = Unitless (estandar del proyecto para archivos Civil)
msp = doc.modelspace()
EXT = [None]*6  # xmin,ymin,zmin,xmax,ymax,zmax
def upd_ext(v):
    x,y,z = v
    if EXT[0] is None:
        EXT[0],EXT[1],EXT[2],EXT[3],EXT[4],EXT[5] = x,y,z,x,y,z
    else:
        EXT[0]=min(EXT[0],x);EXT[1]=min(EXT[1],y);EXT[2]=min(EXT[2],z)
        EXT[3]=max(EXT[3],x);EXT[4]=max(EXT[4],y);EXT[5]=max(EXT[5],z)

PALETTE = [1,2,3,4,5,6,30,40,50,140,150,160,170,200,210,9,8,11,12,13,14]
layer_color = {}
def sanitize(name): return (re.sub(r'[<>/\\":;?*|,=`]', "_", name) or "IFC")[:200]
def get_layer(raw):
    lname = sanitize(raw)
    if lname not in doc.layers:
        doc.layers.add(lname, color=layer_color.setdefault(lname, PALETTE[len(layer_color)%len(PALETTE)]))
    return lname

it = ifcopenshell.geom.iterator(settings, f, multiprocessing.cpu_count())
rows = []
n_mesh = n_line = n_err = n_tri = n_seg = 0
if it.initialize():
    while True:
        shape = it.get()
        try:
            elem = f.by_id(shape.id)
            etype = elem.is_a()
            layer = get_layer(resolve_layer(elem))
            vf = shape.geometry.verts
            verts = [(vf[i]*scale, vf[i+1]*scale, vf[i+2]*scale) for i in range(0, len(vf), 3)]
            for v in verts: upd_ext(v)
            faces_flat = shape.geometry.faces
            edges_flat = shape.geometry.edges
            ntri = nseg = 0
            if faces_flat:  # superficie/solido -> malla
                faces = [(faces_flat[i], faces_flat[i+1], faces_flat[i+2]) for i in range(0, len(faces_flat), 3)]
                mb = MeshBuilder(); mb.add_mesh(vertices=verts, faces=faces)
                mb.render_polyface(msp, dxfattribs={"layer": layer})
                ntri = len(faces); n_mesh += 1; n_tri += ntri
            elif edges_flat:  # curva/linework -> lineas 3D
                for i in range(0, len(edges_flat), 2):
                    a, b = edges_flat[i], edges_flat[i+1]
                    msp.add_line(verts[a], verts[b], dxfattribs={"layer": layer})
                    nseg += 1
                n_line += 1; n_seg += nseg
            rows.append([shape.id, shape.guid, etype, resolve_layer(elem), len(verts), ntri, nseg])
        except Exception as ex:
            n_err += 1
            rows.append([getattr(shape,'id','?'), getattr(shape,'guid','?'), "ERROR", str(ex), 0,0,0])
        if not it.next(): break

doc.saveas(dxf_path)
with open(csv_path, "w", newline="", encoding="utf-8") as cf:
    w = csv.writer(cf); w.writerow(["ifc_id","guid","type","cad_layer","n_vertices","n_triangles","n_segments"]); w.writerows(rows)

by_layer = Counter(r[3] for r in rows if r[2] != "ERROR")
print("\n--- Elementos por capa CAD ---")
for t,n in by_layer.most_common(): print(f"  {n:6d}  {t}")
import json
info = {"scale": scale, "insunits": 0, "schema": f.schema,
        "extent": {"xmin":EXT[0],"ymin":EXT[1],"zmin":EXT[2],"xmax":EXT[3],"ymax":EXT[4],"zmax":EXT[5]},
        "meshes": n_mesh, "lines": n_line, "triangles": n_tri, "segments": n_seg,
        "layers": sorted(set(r[3] for r in rows if r[2] != "ERROR"))}
with open(dxf_path.rsplit(".",1)[0] + ".info.json", "w", encoding="utf-8") as jf:
    json.dump(info, jf, indent=1)
print(f"\nMallas: {n_mesh} ({n_tri} triang.) | Lineas: {n_line} ({n_seg} segs) | errores: {n_err}")
print(f"Capas creadas en DXF: {len(doc.layers)-1}")
print(f"Extent X {EXT[0]:.1f}..{EXT[3]:.1f} Y {EXT[1]:.1f}..{EXT[4]:.1f} Z {EXT[2]:.1f}..{EXT[5]:.1f}")
print("OK")
