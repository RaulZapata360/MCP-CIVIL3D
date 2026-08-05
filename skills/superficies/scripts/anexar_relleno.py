# -*- coding: utf-8 -*-
# Anexa a una superficie ya entregada el trozo de malla que no cubria NINGUNA
# superficie, tomando la geometria del XML de origen.
#
# El caso: el elemento de "Relleno.dxf" mide 17,343.6 ft2, pero 16,936.5 ya
# estaban repartidos entre Roadway N2 (53.7%), Pavement Surface 6 (30.7%) y
# Pavement Surface 10 (13.3%). Solo 407.1 ft2 (2.3%) no los reclamaba nadie. Lo
# que se anexa es ESE hueco, no el elemento entero: pegar el elemento completo
# duplicaria superficie que ya esta en otras tres.
#
# El hueco se calcula como (huella del relleno) - (union de TODAS las superficies
# entregadas), asi que su borde sigue las aristas de los triangulos vecinos y las
# superficies quedan casadas sin solape.
#
# Uso:
#   python anexar_relleno.py <origen.xml> <relleno.dxf> <dir_entrega> <destino> <combinado.xml>
import os, sys, glob
import xml.etree.ElementTree as ET
import ezdxf
import shapely.geometry as sg
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_utils import (write_landxml, clip_surface_by_polygon, crossing_count,
                        face_connected_components, reparar_cruces,
                        solid_faces, polyface_to_mesh, MallaSimple)

NS = {'l': 'http://www.landxml.org/schema/LandXML-1.2'}
SRC = sys.argv[1]
RELL = sys.argv[2]
ENTREGA = sys.argv[3]
DESTINO = sys.argv[4]
COMB = sys.argv[5]
MIN_TROZO = 1.0


def leer_xml(p):
    out = {}
    for s in ET.parse(p).getroot().findall('.//l:Surface', NS):
        v = []; m = {}
        for q in s.findall('.//l:P', NS):
            n, e, z = (float(x) for x in q.text.split())
            m[q.get('id')] = len(v); v.append((e, n, z))
        f = []
        for x in s.findall('.//l:F', NS):
            try: f.append(tuple(m[y] for y in x.text.split()))
            except KeyError: pass
        out[s.get('name')] = (v, f)
    return out


def huella(v, f):
    t = [sg.Polygon([v[a][:2], v[b][:2], v[c][:2]]) for a, b, c in f]
    t = [x if x.is_valid else x.buffer(0) for x in t]
    u = unary_union([x for x in t if x.area > 1e-9]).buffer(0)
    g = list(u.geoms) if u.geom_type in ("MultiPolygon", "GeometryCollection") else [u]
    return unary_union([x for x in g if x.geom_type == "Polygon"])


# origen
SV = []; SF = []
for s in ET.parse(SRC).getroot().findall('.//l:Surface', NS):
    m = {}
    for q in s.findall('.//l:P', NS):
        n, e, z = (float(x) for x in q.text.split())
        m[q.get('id')] = len(SV); SV.append((e, n, z))
    for x in s.findall('.//l:F', NS):
        try: SF.append(tuple(m[y] for y in x.text.split()))
        except KeyError: pass
print(f"origen: {len(SV):,} pts, {len(SF):,} caras")

# huella del relleno
hs = []
for e in ezdxf.readfile(RELL).modelspace():
    if e.dxftype() != "POLYLINE" or not e.is_poly_face_mesh:
        continue
    vs, cs = polyface_to_mesh(e)
    mv, top, _ = solid_faces(MallaSimple(vs, cs), 3, "top")
    t = [sg.Polygon([mv[i][:2] for i in f]) for f in top]
    t = [x if x.is_valid else x.buffer(0) for x in t]
    if t:
        hs.append(unary_union([x for x in t if x.area > 1e-9]).buffer(0))
HR = unary_union(hs).buffer(0)
print(f"relleno: {HR.area:,.1f} ft2")

comb_path = os.path.join(ENTREGA, COMB)
sup = leer_xml(comb_path)
huellas = {nm: huella(v, f) for nm, (v, f) in sup.items()}
TODO = unary_union(list(huellas.values())).buffer(0)
print(f"entrega: {len(sup)} superficies, {TODO.area:,.1f} ft2")

hueco = HR.difference(TODO)
trozos = [g for g in (hueco.geoms if hueco.geom_type != "Polygon" else [hueco])
          if g.geom_type == "Polygon" and g.area > MIN_TROZO]
print(f"\nsin cubrir dentro del relleno: {sum(g.area for g in trozos):,.1f} ft2 "
      f"en {len(trozos)} trozo(s)")
for g in sorted(trozos, key=lambda x: -x.area):
    b = g.bounds
    print(f"   {g.area:9,.1f} ft2  en ({b[0]:,.1f}, {b[1]:,.1f})   "
          f"distancia a {DESTINO}: {g.distance(huellas[DESTINO]):.3f} ft")

if not trozos:
    print("nada que anexar"); sys.exit(0)

# recortar el origen contra cada trozo
nv = []; nf = []
for g in trozos:
    shell = list(g.exterior.coords)[:-1]
    holes = [list(r.coords)[:-1] for r in g.interiors if len(r.coords) >= 4]
    av, af, st = clip_surface_by_polygon(SV, SF, shell,
                                         hole_polys_xy=holes if holes else None,
                                         patch_holes=False)
    base = len(nv)
    nv.extend(av)
    nf.extend([(a+base, b+base, c+base) for a, b, c in af])
print(f"\nrecorte del origen: {len(nv):,} pts, {len(nf):,} caras, "
      f"{huella(nv, nf).area:,.1f} ft2")

# pegar al destino
V, F = sup[DESTINO]
antes = huella(V, F).area
base = len(V)
NV = list(V) + list(nv)
NF = list(F) + [(a+base, b+base, c+base) for a, b, c in nf]
if crossing_count(NV, NF, max_edges=200000):
    NF, _, _ = reparar_cruces(NV, NF)

h = huella(NV, NF)
gs = [x for x in (list(h.geoms) if h.geom_type == "MultiPolygon" else [h])
      if x.area > 0.5]
print(f"\n{DESTINO}: {antes:,.1f} -> {h.area:,.1f} ft2 "
      f"({h.area-antes:+,.1f})   {len(gs)} trozo(s), "
      f"{sum(len(x.interiors) for x in gs)} huecos")
print(f"   componentes de la malla: {len(face_connected_components(NF))}")

# no puede pisar a las demas
peor = 0.0
for nm, hh in huellas.items():
    if nm == DESTINO:
        continue
    a = h.intersection(hh).area
    if a > 0.01:
        print(f"   SOLAPE con {nm}: {a:.4f} ft2")
        peor = max(peor, a)
if peor == 0.0:
    print("   solape con las demas superficies: 0.00 ft2")

sup[DESTINO] = (NV, NF)
write_landxml(os.path.join(ENTREGA, f"{DESTINO}.xml"), [(DESTINO, NV, NF)])
write_landxml(comb_path, [(nm, v, f) for nm, (v, f) in sorted(sup.items())])
print(f"\nescrito -> {os.path.join(ENTREGA, DESTINO + '.xml')}")
print(f"        -> {comb_path}")
