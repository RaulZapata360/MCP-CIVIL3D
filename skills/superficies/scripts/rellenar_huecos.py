# -*- coding: utf-8 -*-
# Cierra los huecos que quedan entre las superficies entregadas y el limite real
# de la malla, tomando la geometria del XML de origen.
#
# A QUIEN SE ASIGNA CADA HUECO: si se pasa un XML de referencia (por ejemplo el
# que el usuario reparo a mano en Civil 3D), se mira que superficie lo cubria alli
# y se respeta esa decision. El nombre se traduce por geometria -- la superficie
# mia que mas se solapa con esa -- para que funcione aunque se hayan renumerado.
# Si la referencia no cubre el hueco, se lo lleva la vecina con mas contacto.
#
# POR QUE NO SE USA EL XML REPARADO DIRECTAMENTE: al añadir puntos, Civil 3D
# re-triangula por Delaunay y rellena el casco convexo. El archivo reparado media
# 780,187 ft2 cuando el terreno real son 633,394: 180,302 ft2 de relleno inventado,
# con 8 superficies convertidas literalmente en su casco convexo. Y aun asi dejaba
# 33,509 ft2 del terreno SIN cubrir. De ese archivo solo se aprovecha la decision
# de a quien pertenece cada hueco; la geometria sale del origen limpio.
#
# Uso:
#   python rellenar_huecos.py <origen.xml> <limite.dxf> <dir_entrega> <combinado.xml> [referencia.xml]
import os, sys
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
LIM = sys.argv[2]
ENT = sys.argv[3]
COMB = sys.argv[4]
REF = sys.argv[5] if len(sys.argv) > 5 else None
# Umbral de hueco. Por debajo de ~2 ft2 lo que hay entre superficies vecinas no son
# agujeros sino fisuras capilares del casado de bordes, y perseguirlas sale caro:
# con 0.5 ft2 el recorte se fragmentaba y dejaba 50 astillas sueltas (5.4 ft2),
# 30 de ellas en Pavement Surface 1 por un hueco de 0.7 ft2.
MIN_HUECO = float(sys.argv[6]) if len(sys.argv) > 6 else 2.0
# Trozos sueltos que genera el propio recorte y que no aportan nada.
MIN_ASTILLA = 0.05


def leer(p):
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


SV = []; SF = []
for s in ET.parse(SRC).getroot().findall('.//l:Surface', NS):
    m = {}
    for q in s.findall('.//l:P', NS):
        n, e, z = (float(x) for x in q.text.split())
        m[q.get('id')] = len(SV); SV.append((e, n, z))
    for x in s.findall('.//l:F', NS):
        try: SF.append(tuple(m[y] for y in x.text.split()))
        except KeyError: pass

hs = []
for e in ezdxf.readfile(LIM).modelspace():
    if e.dxftype() != "POLYLINE" or not e.is_poly_face_mesh:
        continue
    vs, cs = polyface_to_mesh(e)
    mv, top, _ = solid_faces(MallaSimple(vs, cs), 3, "top")
    t = [sg.Polygon([mv[i][:2] for i in f]) for f in top]
    t = [x if x.is_valid else x.buffer(0) for x in t]
    if t:
        hs.append(unary_union([x for x in t if x.area > 1e-9]).buffer(0))
HM = unary_union(hs).buffer(0)

sup = leer(os.path.join(ENT, COMB))
hsup = {nm: huella(v, f) for nm, (v, f) in sup.items()}
HAC = unary_union(list(hsup.values())).buffer(0)
print(f"limite de la malla : {HM.area:,.1f} ft2")
print(f"entrega actual     : {HAC.area:,.1f} ft2 en {len(sup)} superficies")

ref = href = None
if REF:
    ref = leer(REF)
    href = {nm: huella(v, f) for nm, (v, f) in ref.items()}
    print(f"referencia         : {len(ref)} superficies "
          f"({os.path.basename(REF)})")

hueco = HM.difference(HAC)
trozos = sorted([g for g in (hueco.geoms if hueco.geom_type != "Polygon" else [hueco])
                 if g.geom_type == "Polygon" and g.area > MIN_HUECO],
                key=lambda g: -g.area)
print(f"\nhuecos a cerrar: {sum(g.area for g in trozos):,.1f} ft2 en "
      f"{len(trozos)} trozo(s)")

asigna = {}
print(f"\n{'area ft2':>10s} {'destino':24s} {'criterio'}")
print("-" * 62)
for g in trozos:
    destino = None
    criterio = ""
    if href:
        # que superficie de la referencia lo cubre
        cand = sorted(((g.intersection(h).area, nm) for nm, h in href.items()
                       if g.intersects(h)), reverse=True)
        if cand and cand[0][0] > 0.5 * g.area:
            nm_ref = cand[0][1]
            # traducir el nombre por geometria
            trad = sorted(((href[nm_ref].intersection(h).area, nm)
                           for nm, h in hsup.items()
                           if href[nm_ref].intersects(h)), reverse=True)
            if trad:
                destino = trad[0][1]
                criterio = f"la referencia lo daba a {nm_ref}"
    if destino is None:
        cand = sorted(((g.buffer(0.1).intersection(h.buffer(0.1)).area, nm)
                       for nm, h in hsup.items() if g.buffer(0.1).intersects(h)),
                      reverse=True)
        if not cand:
            print(f"{g.area:10,.1f} {'(aislado, se descarta)':24s}")
            continue
        destino = cand[0][1]
        criterio = "vecina con mas contacto"
    asigna.setdefault(destino, []).append(g)
    print(f"{g.area:10,.1f} {destino:24s} {criterio}")

print(f"\nAPLICANDO")
for destino, gs in sorted(asigna.items()):
    V, F = sup[destino]
    antes = huella(V, F).area
    nv = []; nf = []
    for g in gs:
        shell = list(g.exterior.coords)[:-1]
        holes = [list(r.coords)[:-1] for r in g.interiors if len(r.coords) >= 4]
        av, af, st = clip_surface_by_polygon(SV, SF, shell,
                                             hole_polys_xy=holes if holes else None,
                                             patch_holes=False)
        base = len(nv)
        nv.extend(av)
        nf.extend([(a+base, b+base, c+base) for a, b, c in af])
    if not nf:
        print(f"   {destino}: el origen no cubre el hueco, se omite")
        continue
    # el recorte contra un poligono pequeño se astilla; se descartan los trozos
    # sueltos por debajo de MIN_ASTILLA antes de pegar nada
    comps = face_connected_components(nf)
    def _a(i):
        a, b, c = (nv[nf[i][0]], nv[nf[i][1]], nv[nf[i][2]])
        return 0.5*abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))
    buenos = [i for c in comps if sum(_a(i) for i in c) >= MIN_ASTILLA for i in c]
    quitadas = len(nf) - len(buenos)
    if quitadas:
        print(f"   {destino}: {quitadas} caras sueltas descartadas del parche")
    nf = [nf[i] for i in buenos]
    if not nf:
        continue
    base = len(V)
    NV = list(V) + list(nv)
    NF = list(F) + [(a+base, b+base, c+base) for a, b, c in nf]
    if crossing_count(NV, NF, max_edges=200000):
        NF, _, _ = reparar_cruces(NV, NF)
    sup[destino] = (NV, NF)
    h = huella(NV, NF)
    print(f"   {destino:24s} {antes:10,.1f} -> {h.area:10,.1f} ft2 "
          f"({h.area-antes:+7,.1f})  {len(face_connected_components(NF))} componente(s)")

hsup = {nm: huella(v, f) for nm, (v, f) in sup.items()}
HAC = unary_union(list(hsup.values())).buffer(0)
print(f"\nVERIFICACION")
print(f"   entrega: {HAC.area:,.1f} ft2, {sum(len(f) for _, f in sup.values()):,} caras")
print(f"   del limite queda sin cubrir: {HM.difference(HAC).area:,.1f} ft2")
print(f"   fuera del limite           : {HAC.difference(HM).area:,.1f} ft2")
ks = list(hsup)
sol = [(hsup[ks[i]].intersection(hsup[ks[j]]).area, ks[i], ks[j])
       for i in range(len(ks)) for j in range(i+1, len(ks))
       if hsup[ks[i]].intersects(hsup[ks[j]])]
sol = [x for x in sol if x[0] > 0.01]
print(f"   pares con solape > 0.01 ft2: {len(sol)}"
      + (f"   mayor {max(sol)[0]:.4f} ft2" if sol else ""))

for nm, (v, f) in sup.items():
    write_landxml(os.path.join(ENT, f"{nm}.xml"), [(nm, v, f)])
write_landxml(os.path.join(ENT, COMB),
              [(nm, v, f) for nm, (v, f) in sorted(sup.items())])
print(f"\nescrito -> {ENT}")
