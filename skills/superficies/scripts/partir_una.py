# -*- coding: utf-8 -*-
# Parte UNA superficie de la entrega ya montada usando las lineas de un DXF, sin
# rehacer el resto. La pieza mas al norte conserva el nombre y las demas se llevan
# los primeros numeros libres de su familia.
#
# LAS LINEAS SE PROLONGAN 5 ft por cada extremo antes de usarlas como cuchilla:
# vienen dibujadas justo de borde a borde y, con el redondeo a 4 decimales del
# LandXML, un extremo puede quedarse micrometros dentro y shapely no parte nada.
# Lo que sobra fuera de la superficie no corta, asi que no cambia el resultado.
#
# Uso:
#   python partir_una.py <dir_entrega> <combinado.xml> <nombre> <lineas.dxf>
import os, sys, re
import xml.etree.ElementTree as ET
import ezdxf
import shapely.geometry as sg
from shapely.ops import unary_union, split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_utils import (write_landxml, clip_surface_by_polygon, crossing_count,
                        face_connected_components, reparar_cruces)

NS = {'l': 'http://www.landxml.org/schema/LandXML-1.2'}
ENT = sys.argv[1]
COMB = sys.argv[2]
NOMBRE = sys.argv[3]
DXF = sys.argv[4]
MIN_PIEZA = 1.0
MIN_ASTILLA = 0.05


def huella(v, f):
    t = [sg.Polygon([v[a][:2], v[b][:2], v[c][:2]]) for a, b, c in f]
    t = [x if x.is_valid else x.buffer(0) for x in t]
    u = unary_union([x for x in t if x.area > 1e-9]).buffer(0)
    g = list(u.geoms) if u.geom_type in ("MultiPolygon", "GeometryCollection") else [u]
    return unary_union([x for x in g if x.geom_type == "Polygon"])


def alargar(L, extra=5.0):
    (x0, y0), (x1, y1) = L.coords[0], L.coords[-1]
    dx, dy = x1 - x0, y1 - y0
    n = (dx*dx + dy*dy) ** 0.5
    return sg.LineString([(x0-dx/n*extra, y0-dy/n*extra),
                          (x1+dx/n*extra, y1+dy/n*extra)])


sup = {}
for s in ET.parse(os.path.join(ENT, COMB)).getroot().findall('.//l:Surface', NS):
    v = []; m = {}
    for q in s.findall('.//l:P', NS):
        n, e, z = (float(x) for x in q.text.split())
        m[q.get('id')] = len(v); v.append((e, n, z))
    f = []
    for x in s.findall('.//l:F', NS):
        try: f.append(tuple(m[y] for y in x.text.split()))
        except KeyError: pass
    sup[s.get('name')] = (v, f)
if NOMBRE not in sup:
    print(f"no existe {NOMBRE!r} en la entrega"); sys.exit(1)
print(f"entrada: {len(sup)} superficies, {sum(len(f) for _, f in sup.values()):,} caras")

V, F = sup.pop(NOMBRE)
H = huella(V, F)
Ls = [sg.LineString([(q[0], q[1]) for q in e.get_points()])
      for e in ezdxf.readfile(DXF).modelspace() if e.dxftype() == "LWPOLYLINE"]
piezas = sorted([g for g in split(H, unary_union([alargar(L) for L in Ls])).geoms
                 if g.area > MIN_PIEZA], key=lambda g: -g.centroid.y)
print(f"\n{NOMBRE}: {H.area:,.1f} ft2 con {len(Ls)} linea(s) -> {len(piezas)} piezas")

# nombres: la mas al norte conserva el suyo, las demas cogen numeros libres
fam = NOMBRE.rsplit(" ", 1)[0]
usados = set()
for nm in list(sup) + [NOMBRE]:
    m = re.match(rf"^{re.escape(fam)} N?(\d+)$", nm)
    if m:
        usados.add(int(m.group(1)))
pref = "N" if fam.startswith("Roadway") else ""
libres = (n for n in range(1, 999) if n not in usados)

for i, g in enumerate(piezas, 1):
    shell = list(g.exterior.coords)[:-1]
    holes = [list(r.coords)[:-1] for r in g.interiors if len(r.coords) >= 4]
    nv, nf, st = clip_surface_by_polygon(V, F, shell,
                                         hole_polys_xy=holes if holes else None,
                                         patch_holes=False)
    if crossing_count(nv, nf, max_edges=200000):
        nf, _, _ = reparar_cruces(nv, nf)
    # el recorte se astilla en los bordes; fuera los trozos sueltos sin entidad
    comps = face_connected_components(nf)

    def _a(k):
        a, b, c = nv[nf[k][0]], nv[nf[k][1]], nv[nf[k][2]]
        return 0.5*abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
    buenos = [k for c in comps if sum(_a(k) for k in c) >= MIN_ASTILLA for k in c]
    quitadas = len(nf) - len(buenos)
    nf = [nf[k] for k in buenos]
    idx = {}; fv = []; ff = []
    for (a, b, c) in nf:
        tri = []
        for oi in (a, b, c):
            if oi not in idx:
                idx[oi] = len(fv); fv.append(nv[oi])
            tri.append(idx[oi])
        ff.append(tuple(tri))

    nombre = NOMBRE if i == 1 else f"{fam} {pref}{next(libres)}"
    h = huella(fv, ff)
    print(f"   pieza {i}: {nombre:24s} {h.area:10,.1f} ft2 "
          f"(objetivo {g.area:,.1f}, {100*(h.area-g.area)/g.area:+.3f}%)  "
          f"{len(ff):,} caras  {len(face_connected_components(ff))} comp"
          + (f"  [{quitadas} caras sueltas fuera]" if quitadas else ""))
    sup[nombre] = (fv, ff)

hs = {nm: huella(v, f) for nm, (v, f) in sup.items()}
print(f"\nVERIFICACION")
print(f"   superficies: {len(sup)}   caras: {sum(len(f) for _, f in sup.values()):,}")
print(f"   area total : {unary_union(list(hs.values())).area:,.1f} ft2")
ks = list(hs)
sol = [(hs[ks[i]].intersection(hs[ks[j]]).area, ks[i], ks[j])
       for i in range(len(ks)) for j in range(i+1, len(ks))
       if hs[ks[i]].intersects(hs[ks[j]])]
sol = [x for x in sol if x[0] > 0.01]
print(f"   pares con solape > 0.01 ft2: {len(sol)}"
      + (f"   mayor {max(sol)[0]:.4f} ft2" if sol else ""))

for nm, (v, f) in sup.items():
    write_landxml(os.path.join(ENT, f"{nm}.xml"), [(nm, v, f)])
write_landxml(os.path.join(ENT, COMB),
              [(nm, v, f) for nm, (v, f) in sorted(sup.items())])
print(f"\nescrito -> {ENT}")
