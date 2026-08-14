# -*- coding: utf-8 -*-
# ============================================================================
#  Volume_Surface_SI.xml  ->  paquete de CSV para crear Toposolid en Revit 2026
#  via Dynamo.  Superficie: Surface_Exis_SI (terreno existente de South Island).
#
#  Sigue el mismo formato de salida que el paquete de las 22 superficies de
#  carpeta (..\..\05_Dynamo_Revit) para que ambos entren en el MISMO modelo de
#  Revit y queden superpuestos: mismo origen local y mismo OFFSET medido.
#
#  Tres cosas de este XML que condicionan todo el script:
#
#  1. 11.676 de las 220.482 caras llevan i="1" (invisibles, fuera del boundary
#     de Civil 3D). Si no se filtran, la huella pasa de 490.244 ft2 a 1.127.492
#     ft2 -- mas del doble. Es el mismo problema documentado en
#     civil3d-boundary-vs-triangulation.
#
#  2. 105.419 puntos utiles con el vecino mas cercano a 1,04 ft de media: es una
#     malla de escaneo de 1 pie. Meter eso en UN solo Toposolid deja Revit
#     inservible, asi que se diezma con control de error vertical conservando
#     SIEMPRE los vertices de contorno.
#
#  3. La superficie tiene 163 caras de mas de 70 grados de pendiente (hasta
#     88,5). Un Toposolid es un campo de alturas 2,5D: NO puede tener dos cotas
#     en el mismo XY. Esos muros se convierten en rampas muy inclinadas pase lo
#     que pase -- con 12.000 puntos y con los 105.419. El script lo mide y lo
#     informa aparte para no confundir ese error con error de diezmado.
#
#  Uso:  python exportar_paquete_revit.py
# ============================================================================
import os, csv, sys, time
import xml.etree.ElementTree as ET
import numpy as np
import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.prepared import prep
from scipy.spatial import Delaunay, cKDTree
import ezdxf

NS = {'l': 'http://www.landxml.org/schema/LandXML-1.2'}

AQUI = os.path.dirname(os.path.abspath(__file__))
XML = os.path.join(os.path.dirname(AQUI), 'Volume_Surface_SI.xml')
OUT_DIR = AQUI

# Origen local: EL MISMO que el paquete de las 22 superficies de carpeta.
# No es cosmetico: a 12 millones de pies el salto entre dos floats de precision
# simple ya supera la tolerancia con la que Revit cierra los contornos.
OX, OY = 12124000.0, 3524500.0

TOL_DECIMADO = 0.25    # ft -- error vertical objetivo del diezmado
TOL_CONTORNO = 0.001   # ft -- Douglas-Peucker sobre los anillos
MIN_HOLE_AREA = 5.0    # ft2 -- por debajo es astilla numerica, no un hueco real
MIN_PIECE_AREA = 1.0   # ft2
MIN_SEG_DYNAMO = 0.1   # ft -- lo que descarta build_loop() en el script de Dynamo


def log(m=''):
    print(m)
    sys.stdout.flush()


# ---------------------------------------------------------------- 1. leer XML
t0 = time.time()
root = ET.parse(XML).getroot()
surf = root.find('.//l:Surface', NS)
NOMBRE = surf.get('name')
defn = surf.find('.//l:Definition', NS)
area2d_xml = float(defn.get('area2DSurf'))

verts = []
id2i = {}
for p in surf.findall('.//l:P', NS):
    n, e, z = (float(x) for x in p.text.split())
    id2i[p.get('id')] = len(verts)
    verts.append((e, n, z))
V = np.array(verts)

faces_vis, n_invis = [], 0
for f in surf.findall('.//l:F', NS):
    if f.get('i') == '1':
        n_invis += 1
        continue
    try:
        a, b, c = (id2i[x] for x in f.text.split())
    except KeyError:
        continue
    faces_vis.append((a, b, c))
F = np.array(faces_vis)

log(f"Superficie          : {NOMBRE}")
log(f"Puntos en el XML    : {len(V):,}")
log(f"Caras visibles      : {len(F):,}   (descartadas por i=\"1\": {n_invis:,})")
log(f"area2DSurf del XML  : {area2d_xml:,.2f} ft2")

# ------------------------------------------------- 2. huella 2D: piezas+huecos
tris = [sg.Polygon([V[a, :2], V[b, :2], V[c, :2]]) for a, b, c in F]
tris = [t for t in tris if t.is_valid and t.area > 1e-9]
u = unary_union(tris).buffer(0)
geoms = [g for g in (list(u.geoms) if u.geom_type == 'MultiPolygon' else [u])
         if g.area > MIN_PIECE_AREA]
geoms.sort(key=lambda g: -g.area)
log(f"Huella reconstruida : {u.area:,.2f} ft2  "
    f"(desvio {100*(u.area-area2d_xml)/area2d_xml:+.4f} % respecto al XML)")
log(f"Piezas separadas    : {len(geoms)}")

XY, Z = V[:, :2], V[:, 2]
tree = cKDTree(XY)

# ------------------------------- 3. anillos simplificados + vertices a mantener
anillos = []          # (piece_id, tipo, ring_id, [(x,y), ...])
bnd_idx = set()
peor_desvio = 0.0
n_vert_orig = n_vert_simp = 0

for pi, g in enumerate(geoms):
    lista = [('OUTER', 0, g.exterior)]
    hid = 0
    for r in g.interiors:
        if sg.Polygon(r).area > MIN_HOLE_AREA:
            lista.append(('HOLE', hid, r))
            hid += 1
    for tipo, rid, ring in lista:
        orig = np.array(ring.coords)[:-1]
        simp = np.array(ring.simplify(TOL_CONTORNO, preserve_topology=False).coords)[:-1]
        n_vert_orig += len(orig)
        n_vert_simp += len(simp)
        # desvio real: distancia de cada vertice original al anillo simplificado
        ls = sg.LinearRing(np.vstack([simp, simp[:1]]))
        d = max(ls.distance(sg.Point(p)) for p in orig)
        peor_desvio = max(peor_desvio, d)
        anillos.append((pi, tipo, rid, simp))
        dd, ii = tree.query(simp, k=1)
        bnd_idx.update(ii[dd < 0.05].tolist())

bnd_idx = np.array(sorted(bnd_idx))
n_holes = sum(1 for a in anillos if a[1] == 'HOLE')
log(f"Anillos             : {len(anillos)}  ({len(geoms)} exteriores + {n_holes} huecos >{MIN_HOLE_AREA:g} ft2)")
log(f"Vertices de contorno: {n_vert_orig:,} -> {n_vert_simp:,} tras Douglas-Peucker "
    f"{TOL_CONTORNO} ft (desvio real max {peor_desvio:.5f} ft)")

# aviso: segmentos que el build_loop de Dynamo va a tirar por ser < 0.1 ft
cortos = 0
for _, _, _, pts in anillos:
    dd = np.linalg.norm(np.diff(np.vstack([pts, pts[:1]]), axis=0), axis=1)
    cortos += int((dd < MIN_SEG_DYNAMO).sum())
log(f"Segmentos < {MIN_SEG_DYNAMO} ft     : {cortos}  (los filtrara build_loop() en Dynamo)")

# ------------------------------------------------------ 4. diezmado con error
used_vis = np.unique(F.reshape(-1))


def interp(tri, sel, idx):
    s = tri.find_simplex(XY[idx])
    ok = s >= 0
    z = np.full(len(idx), np.nan)
    if ok.any():
        T = tri.transform[s[ok]]
        d = XY[idx][ok] - T[:, 2]
        b0 = T[:, 0, 0] * d[:, 0] + T[:, 0, 1] * d[:, 1]
        b1 = T[:, 1, 0] * d[:, 0] + T[:, 1, 1] * d[:, 1]
        bary = np.column_stack([b0, b1, 1 - b0 - b1])
        z[ok] = (Z[sel][tri.simplices[s[ok]]] * bary).sum(axis=1)
    return z, ok


t1 = time.time()
paso = max(1, len(used_vis) // 2000)
sel = np.union1d(bnd_idx, used_vis[::paso])
cand = np.setdiff1d(used_vis, sel)
for it in range(80):
    tri = Delaunay(XY[sel])
    z, ok = interp(tri, sel, cand)
    err = np.abs(z - Z[cand])
    err[~ok] = 0.0
    peores = np.argsort(-err)[:max(500, int((err > TOL_DECIMADO).sum() * 0.30))]
    if err[peores[0]] <= TOL_DECIMADO:
        break
    peores = peores[err[peores] > TOL_DECIMADO]
    sel = np.union1d(sel, cand[peores])
    cand = np.setdiff1d(cand, cand[peores])

tri = Delaunay(XY[sel])
z, ok = interp(tri, sel, used_vis)
err_all = np.abs(z - Z[used_vis])
log(f"\nDiezmado            : {len(used_vis):,} -> {len(sel):,} puntos "
    f"({100.0*len(sel)/len(used_vis):.1f} %)  [{it+1} iteraciones, {time.time()-t1:.0f} s]")

# separar el error de los muros (inherente al 2,5D) del error de terreno normal
p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
nrm = np.cross(p1 - p0, p2 - p0)
ln = np.linalg.norm(nrm, axis=1)
pend = np.degrees(np.arccos(np.clip(np.abs(nrm[:, 2]) / np.maximum(ln, 1e-12), 0, 1)))
emp_v = np.unique(F[pend > 70].reshape(-1)) if (pend > 70).any() else np.array([], int)
cerca_muro = np.zeros(len(used_vis), bool)
if len(emp_v):
    tm = cKDTree(XY[emp_v])
    cerca_muro = tm.query(XY[used_vis], k=1)[0] < 3.0

llano = err_all[~cerca_muro & ok]
muro = err_all[cerca_muro & ok]
log(f"  caras > 70 grados : {(pend>70).sum()}  (max {pend.max():.1f} grados) "
    f"-> {int(cerca_muro.sum()):,} puntos a menos de 3 ft de un muro")
log(f"  error TERRENO ({len(llano):,} pts): medio {llano.mean():.4f}  p95 {np.percentile(llano,95):.4f}  "
    f"p99.9 {np.percentile(llano,99.9):.4f}  max {llano.max():.4f} ft")
log(f"  error MUROS   ({len(muro):,} pts): medio {muro.mean():.4f}  p95 {np.percentile(muro,95):.4f}  "
    f"max {muro.max():.4f} ft  <- limite 2,5D, NO mejora con mas puntos")

# --------------------------------------------- 5. asignar puntos a cada pieza
sel_set = set(sel.tolist())
pt_rows_dec, pt_rows_full = [], []
resumen = []
for pi, g in enumerate(geoms):
    gb = prep(g.buffer(0.5))
    dentro = [i for i in used_vis if gb.contains(sg.Point(XY[i, 0], XY[i, 1]))]
    n_dec = 0
    for i in dentro:
        fila = [NOMBRE, pi, f"{XY[i,0]-OX:.4f}", f"{XY[i,1]-OY:.4f}", f"{Z[i]:.4f}"]
        pt_rows_full.append(fila)
        if i in sel_set:
            pt_rows_dec.append(fila)
            n_dec += 1
    nh = sum(1 for a in anillos if a[0] == pi and a[1] == 'HOLE')
    resumen.append((pi, g.area, len(dentro), n_dec, nh))

# ------------------------------------------------------------- 6. escribir CSV
bnd_rows = []
for pi, tipo, rid, pts in anillos:
    for seq, (x, y) in enumerate(pts):
        bnd_rows.append([NOMBRE, pi, tipo, rid, seq, f"{x-OX:.4f}", f"{y-OY:.4f}"])


def escribir(nombre, cab, filas):
    p = os.path.join(OUT_DIR, nombre)
    with open(p, 'w', newline='', encoding='ascii') as fh:
        w = csv.writer(fh)
        w.writerow(cab)
        w.writerows(filas)
    return p


CAB_P = ["SurfaceName", "PieceId", "X", "Y", "Z"]
p1_ = escribir("All_Points_ByPiece.csv", CAB_P, pt_rows_dec)
p2_ = escribir("All_Points_ByPiece_FULL.csv", CAB_P, pt_rows_full)
p3_ = escribir("All_Boundaries_Complete.csv",
               ["SurfaceName", "PieceId", "RingType", "RingId", "Seq", "X", "Y"], bnd_rows)

# ----------------------------------------- 7. DXF de verificacion (coords VA83-SF)
doc = ezdxf.new("R2018")
msp = doc.modelspace()
doc.layers.new(f"SURF_OUTER_{NOMBRE}", dxfattribs={"color": 3})
doc.layers.new(f"SURF_HOLE_{NOMBRE}", dxfattribs={"color": 1})
for pi, tipo, rid, pts in anillos:
    lay = f"SURF_{tipo}_{NOMBRE}"
    msp.add_polyline3d([(float(x), float(y), 0.0) for x, y in pts],
                       dxfattribs={"layer": lay, "closed": True})
dxf_path = os.path.join(OUT_DIR, "SI_Exis_Bordes.dxf")
try:
    doc.saveas(dxf_path)
    dxf_ok = True
except PermissionError:
    dxf_ok = False

# ------------------------------------------------------------- 8. verificacion
log("\n" + "=" * 74)
log(f"{'pieza':>6} {'area ft2':>13} {'pts totales':>12} {'pts diezmados':>14} {'huecos':>7}")
for pi, a, nt, nd, nh in resumen:
    log(f"{pi:6d} {a:13,.1f} {nt:12,} {nd:14,} {nh:7d}")
log(f"{'TOTAL':>6} {sum(r[1] for r in resumen):13,.1f} {len(pt_rows_full):12,} "
    f"{len(pt_rows_dec):14,} {n_holes:7d}")

# area encerrada por los contornos que realmente se exportan
area_csv = 0.0
for pi, g in enumerate(geoms):
    ext = [a for a in anillos if a[0] == pi and a[1] == 'OUTER'][0][3]
    poly = sg.Polygon(ext)
    for a in anillos:
        if a[0] == pi and a[1] == 'HOLE':
            poly = poly.difference(sg.Polygon(a[3]))
    area_csv += poly.area
log(f"\nArea encerrada por los contornos exportados: {area_csv:,.2f} ft2")
log(f"  vs area2DSurf del XML {area2d_xml:,.2f} ft2  ->  {area_csv-area2d_xml:+,.2f} ft2 "
    f"({100*(area_csv-area2d_xml)/area2d_xml:+.4f} %)")
log(f"  (la diferencia son los {int(sum(1 for g in geoms for r in g.interiors if sg.Polygon(r).area <= MIN_HOLE_AREA))} "
    f"huecos-astilla de menos de {MIN_HOLE_AREA:g} ft2 que no se exportan)")

log(f"\nCSV puntos diezmados -> {p1_}")
log(f"CSV puntos completos -> {p2_}")
log(f"CSV contornos        -> {p3_}   ({len(bnd_rows):,} vertices)")
log(f"DXF verificacion     -> {dxf_path}" if dxf_ok else
    f"DXF NO escrito (bloqueado por otra aplicacion): {dxf_path}")
log(f"\nOrigen local restado : E {OX:,.0f}  N {OY:,.0f}")
log(f"Total {time.time()-t0:.0f} s")
