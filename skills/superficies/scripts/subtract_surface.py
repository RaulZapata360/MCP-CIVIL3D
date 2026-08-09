# -*- coding: utf-8 -*-
# Resta la huella (en planta) de una superficie SUSTRAENDA de una superficie
# PRINCIPAL, dejando solo la parte de la principal que queda fuera de esa huella.
# Uso: subtract_surface.py <xml_principal> <nombre_principal> <xml_sustraendo> <nombre_sustraendo> <nombre_salida> <salida.xml>
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from mesh_utils import (read_landxml_surface, subtract_surface_from_surface, boundary_holes,
                         crossing_count, face_connected_components, write_landxml)
import shapely.geometry as sg
from shapely.ops import unary_union

xml_main = sys.argv[1]; name_main = sys.argv[2]
xml_sub = sys.argv[3]; name_sub = sys.argv[4]
out_name = sys.argv[5]; out_xml = sys.argv[6]

verts, faces = read_landxml_surface(xml_main, name_main)
sub_verts, sub_faces = read_landxml_surface(xml_sub, name_sub)
print(f"principal '{name_main}': {len(verts)} vertices, {len(faces)} caras")
print(f"sustraendo '{name_sub}': {len(sub_verts)} vertices, {len(sub_faces)} caras")

new_verts, new_faces, stats = subtract_surface_from_surface(verts, faces, sub_verts, sub_faces)
print(f"\narea_original={stats['area_original']:.1f} ft2  area_huella_resta={stats['area_huella_resta']:.1f} ft2  "
      f"area_resultado={stats['area_resultado']:.1f} ft2")
print(f"triangulos: intactos={stats['n_tri_intactos']} cruzados={stats['n_tri_cruzados']} eliminados={stats['n_tri_eliminados']}")

n_holes, nonman = boundary_holes(new_faces)
nc = crossing_count(new_verts, new_faces)
comps = face_connected_components(new_faces)
print(f"vertices={len(new_verts)} caras={len(new_faces)}  huecos_internos={n_holes}  no-manifold={nonman}  "
      f"cruces_internos={nc}  componentes_conexas={len(comps)}")

# QA: la union real de triangulos no deberia tener area duplicada (ratio ~1.0)
tris = []; sum_area = 0.0
for (i1, i2, i3) in new_faces:
    v1, v2, v3 = new_verts[i1], new_verts[i2], new_verts[i3]
    t = sg.Polygon([(v1[0], v1[1]), (v2[0], v2[1]), (v3[0], v3[1])])
    if t.is_valid and t.area > 1e-9:
        tris.append(t); sum_area += t.area
union_area = unary_union(tris).area if tris else 0.0
ratio = sum_area / union_area if union_area else None
print(f"QA solape: suma_areas_triangulos={sum_area:.1f}  area_union_real={union_area:.1f}  ratio={ratio}")

write_landxml(out_xml, [(out_name, new_verts, new_faces)])
print(f"\nOK -> {out_xml}")
