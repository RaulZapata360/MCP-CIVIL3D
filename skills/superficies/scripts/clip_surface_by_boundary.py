# -*- coding: utf-8 -*-
# Recorta 1 o mas superficies (ya generadas en un LandXML) contra un contorno cerrado
# (polilinea o spline) leido de un DXF, quedandose SOLO con la parte DENTRO del
# contorno. Cada superficie se recorta de forma independiente contra el MISMO
# contorno. Salida: un LandXML con las superficies recortadas (sufijo _Recortada).
#
# Uso: clip_surface_by_boundary.py <dxf_contorno> <capa_o_ALL> <xml_superficies> <nombres_separados_por_coma> <salida.xml> [dxf_hueco_interior]
#   dxf_hueco_interior (opcional): DXF con un contorno cerrado ADICIONAL, completamente
#   contenido dentro del contorno principal -- se resta del recorte (anillo entre los
#   2 contornos). Util para recortar la calzada alrededor de una estructura.
import sys, ezdxf
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from mesh_utils import read_landxml_surface, clip_surface_by_polygon, boundary_holes, crossing_count, write_landxml

dxf_path = sys.argv[1]; layer = sys.argv[2]; xml_path = sys.argv[3]
names = [n.strip() for n in sys.argv[4].split(",")]
out_xml = sys.argv[5]
dxf_hueco = sys.argv[6] if len(sys.argv) > 6 else None

def flatten_entity(e):
    if e.dxftype() == "SPLINE":
        return [(p.x, p.y) for p in e.flattening(0.05)]
    if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
        return [(p[0], p[1]) for p in e.get_points()] if e.dxftype() == "LWPOLYLINE" else \
               [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
    return None

def read_boundary(path, layer):
    doc = ezdxf.readfile(path); msp = doc.modelspace()
    for e in msp:
        if layer != "ALL" and e.dxf.layer != layer: continue
        pts = flatten_entity(e)
        if pts:
            print(f"contorno leido de {path}: {e.dxftype()} en capa '{e.dxf.layer}', {len(pts)} puntos aplanados")
            if pts[0] != pts[-1]: pts.append(pts[0])
            return pts
    return None

boundary_pts = read_boundary(dxf_path, layer)
if not boundary_pts:
    print("ERROR: no se encontro una entidad de contorno valida (SPLINE/POLYLINE/LWPOLYLINE)")
    sys.exit(2)

hole_pts = None
if dxf_hueco:
    hole_pts = read_boundary(dxf_hueco, layer)
    if not hole_pts:
        print("ERROR: no se encontro una entidad de contorno valida en el DXF de hueco")
        sys.exit(2)

xs = [p[0] for p in boundary_pts]; ys = [p[1] for p in boundary_pts]
print(f"extent contorno: X {min(xs):.1f}..{max(xs):.1f}  Y {min(ys):.1f}..{max(ys):.1f}")

clipped_surfaces = []
for name in names:
    verts, faces = read_landxml_surface(xml_path, name)
    new_verts, new_faces, stats = clip_surface_by_polygon(verts, faces, boundary_pts, [hole_pts] if hole_pts else None)
    pct = stats["area_recortada"] / stats["area_original"] * 100 if stats["area_original"] else 0
    print(f"\n[{name}]")
    print(f"  triangulos: dentro={stats['n_tri_dentro']} cruzados={stats['n_tri_cruzados']} "
          f"fuera(descartados)={stats['n_tri_fuera']}")
    print(f"  area original={stats['area_original']:.1f} ft2  area recortada={stats['area_recortada']:.1f} ft2 "
          f"({pct:.1f}% conservado)")
    if not new_faces:
        print("  SIN INTERSECCION con el contorno -- omitida")
        continue
    n_holes, nonman = boundary_holes(new_faces)
    nc = crossing_count(new_verts, new_faces)
    print(f"  vertices={len(new_verts)} caras={len(new_faces)}  huecos_internos={n_holes}  "
          f"no-manifold={nonman}  cruces_internos={nc}")
    out_name = f"{name}_Recortada"
    clipped_surfaces.append((out_name, new_verts, new_faces))

write_landxml(out_xml, clipped_surfaces)
print(f"\nOK -> {out_xml}  ({len(clipped_surfaces)} superficies recortadas escritas)")
