# -*- coding: utf-8 -*-
# Combina N superficies YA RECORTADAS (mismo LandXML, un mismo contorno) en una sola
# superficie watertight: suelda por proximidad los puntos donde superficies VECINAS
# se tocan, y rellena los huecos angostos que quedan en las costuras entre superficies
# distintas (donde no llegaban a tocarse) SOLO si esa zona esta cubierta por alguna de
# las superficies ORIGINALES sin recortar (evita rellenar huecos reales del proyecto).
#
# Uso: merge_clipped_surfaces.py <xml_recortadas> <nombres_separados_por_coma> <xml_original_38> <nombre_salida> <salida.xml> [weld_tol]
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from mesh_utils import (read_landxml_surface, weld_by_proximity, face_connected_components,
                         detect_boundary_rings, ear_clip_triangulate, write_landxml)
import xml.etree.ElementTree as ET
import shapely.geometry as sg
from shapely.strtree import STRtree

xml_path = sys.argv[1]
names = [n.strip() for n in sys.argv[2].split(",")]
xml_original = sys.argv[3]
out_name = sys.argv[4]
out_xml = sys.argv[5]
weld_tol = float(sys.argv[6]) if len(sys.argv) > 6 else 0.15

# --- combinar todas las superficies recortadas en una sola malla ---
all_verts = []; all_faces = []
for name in names:
    verts, faces = read_landxml_surface(xml_path, name)
    offset = len(all_verts)
    all_verts.extend(verts)
    for (a, b, c) in faces:
        all_faces.append((a + offset, b + offset, c + offset))
print(f"combinadas {len(names)} superficies: {len(all_verts)} vertices, {len(all_faces)} caras (antes de soldar)")

all_verts, all_faces = weld_by_proximity(all_verts, all_faces, tol=weld_tol)
print(f"tras soldar (tol={weld_tol} ft): {len(all_verts)} vertices, {len(all_faces)} caras")

# --- cargar TODAS las superficies originales (sin recortar) como referencia para
#     decidir si un hueco de costura esta cubierto por datos reales ---
ns = {'l': 'http://www.landxml.org/schema/LandXML-1.2'}
root_orig = ET.parse(xml_original).getroot()
ref_tris = []  # lista de poligonos shapely (coords REALES, sin localizar)
for s in root_orig.findall('.//l:Surface', ns):
    sverts = []
    for p in s.findall('.//l:P', ns):
        n, e, z = (float(x) for x in p.text.split())
        sverts.append((e, n, z))
    sfaces = [tuple(int(x) - 1 for x in f.text.split()) for f in s.findall('.//l:F', ns)]
    for (i1, i2, i3) in sfaces:
        v1, v2, v3 = sverts[i1], sverts[i2], sverts[i3]
        t = sg.Polygon([(v1[0], v1[1]), (v2[0], v2[1]), (v3[0], v3[1])])
        if t.is_valid and t.area > 1e-9: ref_tris.append(t)
ref_tree = STRtree(ref_tris)
print(f"referencia: {len(ref_tris)} triangulos de las 38 superficies originales")

# --- localizar coordenadas (gotcha 1: precision numerica con coords ~12,000,000) ---
ox, oy = all_verts[0][0], all_verts[0][1]

n_parcheados = 0; n_reales_sin_tocar = 0
comps = face_connected_components(all_faces)
print(f"{len(comps)} componentes conexas tras soldar")
for comp_face_idx in comps:
    comp_faces = [all_faces[i] for i in comp_face_idx]
    rings_raw = detect_boundary_rings(comp_faces)
    holes = rings_raw[1:] if len(rings_raw) > 1 else []
    for h_raw in holes:
        h = h_raw[:-1] if (len(h_raw) > 1 and h_raw[0] == h_raw[-1]) else h_raw
        h = list(dict.fromkeys(h))
        if len(h) < 3: continue
        xs = [all_verts[v][0] for v in h]; ys = [all_verts[v][1] for v in h]
        cx = sum(xs) / len(xs); cy = sum(ys) / len(ys)
        pt = sg.Point(cx, cy)
        cand = ref_tree.query(pt)
        covered = any(ref_tris[j].contains(pt) or ref_tris[j].distance(pt) < 0.1 for j in cand)
        if not covered:
            n_reales_sin_tocar += 1
            print(f"  hueco NO cubierto por datos originales -- se deja intacto: centroide=({cx:.2f},{cy:.2f}) n_verts_anillo={len(h)}")
            continue
        ring_xy_local = [(all_verts[v][0] - ox, all_verts[v][1] - oy) for v in h]
        for (a, b, c) in ear_clip_triangulate(ring_xy_local):
            ia, ib, ic = h[a], h[b], h[c]
            if len({ia, ib, ic}) == 3: all_faces.append((ia, ib, ic))
        n_parcheados += 1
        print(f"  hueco parchado: centroide=({cx:.2f},{cy:.2f}) area_aprox_verts={len(h)}")

# dedup final
seen = set(); deduped = []
for f in all_faces:
    key = frozenset(f)
    if key in seen: continue
    seen.add(key); deduped.append(f)
n_dup = len(all_faces) - len(deduped)
all_faces = deduped

print(f"\nhuecos parchados: {n_parcheados}  huecos reales dejados intactos: {n_reales_sin_tocar}  caras_duplicadas_removidas: {n_dup}")
print(f"resultado final: {len(all_verts)} vertices, {len(all_faces)} caras")

write_landxml(out_xml, [(out_name, all_verts, all_faces)])
print(f"\nOK -> {out_xml}")
