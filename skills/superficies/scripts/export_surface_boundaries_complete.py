# -*- coding: utf-8 -*-
# PAQUETE COMPLETO DE CONTORNOS de las superficies de North Island:
# anillo exterior de CADA pieza de CADA superficie + TODOS los anillos
# interiores (huecos de edificaciones/estructuras).
#
# CORRECCION IMPORTANTE (2026-07-28): una version anterior de este analisis
# concluyo que "las superficies no tienen huecos reales y los vacios son solo
# mascaras de visualizacion tipo Hide de Civil 3D". ESO ERA FALSO. El error fue
# no haber inspeccionado nunca los anillos INTERIORES del poligono de cada
# superficie -- solo se habian cruzado footprints externos contra ellas. La
# verificacion correcta (unary_union de los triangulos -> revisar .interiors)
# encuentra 17 huecos interiores reales repartidos en 8 superficies. Esos
# huecos SI viajan dentro del LandXML y se pueden extraer directamente, sin
# necesidad de geometria externa.
#
# Metodo: se reconstruye la huella 2D de cada superficie como union de sus
# triangulos (shapely). El resultado puede ser MultiPolygon (superficies
# partidas en piezas fisicamente separadas) y cada pieza puede tener anillos
# interiores (huecos). Se exportan todos, ordenados.
#
# SALIDAS (en ...\Caminos\Avances\08_Void_Contours\):
#   1) Surface_Boundaries_Complete.dxf -- coords REALES VA83-SF, para verificar
#      superpuesto en Civil 3D. Capas:
#        SURF_OUTER_<superficie>  (verde)  anillo exterior de cada pieza
#        SURF_HOLE_<superficie>   (rojo)   anillos interiores (huecos)
#   2) All_Boundaries_Complete.csv -- ORIGEN LOCAL (X-12119000 / Y-3530500),
#      para consumir desde Dynamo. Columnas:
#        SurfaceName, PieceId, RingType, RingId, Seq, X, Y
#      RingType = OUTER | HOLE. Un Toposolid por cada (SurfaceName, PieceId),
#      usando su OUTER como perfil exterior y sus HOLE como CurveLoop interiores.
import os, csv, sys
import xml.etree.ElementTree as ET
import shapely.geometry as sg
from shapely.ops import unary_union
import ezdxf

NS = {'l': 'http://www.landxml.org/schema/LandXML-1.2'}

# Rutas por defecto (el caso original). Sobreescribibles por linea de comandos:
#   python export_surface_boundaries_complete.py <in.xml> <out_dir> [origen_x] [origen_y]
BASE = r"C:\Users\Usuario\OneDrive\Escritorio\Raul ZOIN\HRCP\CIVIL 3D\North Island\Caminos\Avances"
XML = BASE + r"\07_Superficies IN Finales en XML\NI_ALL SURFACES_AI.xml"
OUT_DIR = BASE + r"\08_Void_Contours"
OX, OY = 12119000.0, 3530500.0     # mismo origen local del paquete de Revit
MIN_HOLE_AREA = 5.0                # ft2 -- descarta slivers numericos
MIN_PIECE_AREA = 1.0

if len(sys.argv) >= 3:
    XML, OUT_DIR = sys.argv[1], sys.argv[2]
if len(sys.argv) >= 5:
    OX, OY = float(sys.argv[3]), float(sys.argv[4])
print(f"Entrada: {XML}")
print(f"Salida : {OUT_DIR}")
print(f"Origen local: X-{OX:,.0f} Y-{OY:,.0f}\n")

os.makedirs(OUT_DIR, exist_ok=True)

root = ET.parse(XML).getroot()
doc = ezdxf.new("R2018")
msp = doc.modelspace()
rows = []
pt_rows = []
summary = []

for s in root.findall('.//l:Surface', NS):
    name = s.get('name')
    verts = []; id2i = {}; verts3d = []
    for p in s.findall('.//l:P', NS):
        n, e, z = (float(x) for x in p.text.split())
        id2i[p.get('id')] = len(verts)
        verts.append((e - OX, n - OY)); verts3d.append((e - OX, n - OY, z))
    tris = []
    for f in s.findall('.//l:F', NS):
        try: a, b, c = (id2i[x] for x in f.text.split())
        except KeyError: continue
        t = sg.Polygon([verts[a], verts[b], verts[c]])
        if t.is_valid and t.area > 1e-9: tris.append(t)
    if not tris:
        print(f"  AVISO: {name} sin triangulos validos"); continue

    u = unary_union(tris).buffer(0)
    geoms = list(u.geoms) if u.geom_type == "MultiPolygon" else [u]
    geoms = [g for g in geoms if g.area > MIN_PIECE_AREA]
    geoms.sort(key=lambda g: -g.area)

    lay_o = f"SURF_OUTER_{name}"
    lay_h = f"SURF_HOLE_{name}"
    if lay_o not in doc.layers: doc.layers.new(lay_o, dxfattribs={"color": 3})
    if lay_h not in doc.layers: doc.layers.new(lay_h, dxfattribs={"color": 1})

    n_holes = 0; hole_area = 0.0
    for pi, g in enumerate(geoms):
        coords = list(g.exterior.coords)
        msp.add_polyline3d([(x + OX, y + OY, 0.0) for x, y in coords],
                           dxfattribs={"layer": lay_o, "closed": True})
        for seq, (x, y) in enumerate(coords[:-1]):
            rows.append([name, pi, "OUTER", 0, seq, f"{x:.4f}", f"{y:.4f}"])

        hi = 0
        for r in g.interiors:
            a = sg.Polygon(r).area
            if a <= MIN_HOLE_AREA: continue
            hc = list(r.coords)
            msp.add_polyline3d([(x + OX, y + OY, 0.0) for x, y in hc],
                               dxfattribs={"layer": lay_h, "closed": True})
            for seq, (x, y) in enumerate(hc[:-1]):
                rows.append([name, pi, "HOLE", hi, seq, f"{x:.4f}", f"{y:.4f}"])
            hi += 1; n_holes += 1; hole_area += a

        # Asignar cada punto de la superficie a SU pieza. Imprescindible cuando
        # una superficie esta partida en varias piezas: si a la pieza A se le
        # pasan tambien los puntos de la pieza B, esos puntos caen fuera de su
        # contorno y Revit dispara el dialogo bloqueante "Slab Shape Edit
        # failed". Se usa un buffer chico para no perder los puntos que estan
        # justo sobre el borde por ruido de redondeo.
        gb = g.buffer(0.5)
        for (x, y, z) in verts3d:
            if gb.contains(sg.Point(x, y)):
                pt_rows.append([name, pi, f"{x:.4f}", f"{y:.4f}", f"{z:.4f}"])

    summary.append((name, len(geoms), n_holes, hole_area, u.area))

csv_path = os.path.join(OUT_DIR, "All_Boundaries_Complete.csv")
with open(csv_path, "w", newline="", encoding="ascii") as fh:
    w = csv.writer(fh)
    w.writerow(["SurfaceName", "PieceId", "RingType", "RingId", "Seq", "X", "Y"])
    w.writerows(rows)

pts_path = os.path.join(OUT_DIR, "All_Points_ByPiece.csv")
with open(pts_path, "w", newline="", encoding="ascii") as fh:
    w = csv.writer(fh)
    w.writerow(["SurfaceName", "PieceId", "X", "Y", "Z"])
    w.writerows(pt_rows)

# El DXF va AL FINAL y no es bloqueante: es solo para verificacion visual, y si
# esta abierto como DWG Reference en Civil 3D queda bloqueado por Windows. Los
# CSV, que son lo que consume Dynamo, ya estan escritos a estas alturas.
dxf_path = os.path.join(OUT_DIR, "Surface_Boundaries_Complete_v2.dxf")
try:
    doc.saveas(dxf_path)
    dxf_ok = True
except PermissionError:
    dxf_ok = False

print(f"{'SUPERFICIE':24s} {'piezas':>7s} {'huecos':>7s} {'area huecos':>13s} {'area util':>13s}")
print("-" * 72)
for name, npieces, nh, ha, ua in summary:
    print(f"{name:24s} {npieces:7d} {nh:7d} {ha:13,.0f} {ua:13,.0f}")

tp = sum(x[1] for x in summary); th = sum(x[2] for x in summary)
print(f"\nSuperficies: {len(summary)}   Piezas (=Toposolid a crear): {tp}   Huecos interiores: {th}")
print(f"Area total de huecos: {sum(x[3] for x in summary):,.0f} ft2")
print(f"\nDXF          -> {dxf_path}" if dxf_ok else
      f"\nDXF          -> NO ESCRITO: bloqueado por otra aplicacion (Civil 3D?).\n"
      f"                 Cierra o descarga la referencia y vuelve a correr este script.\n"
      f"                 {dxf_path}")
print(f"CSV contornos-> {csv_path}   ({len(rows)} vertices)")
print(f"CSV puntos   -> {pts_path}   ({len(pt_rows)} puntos asignados por pieza)")
