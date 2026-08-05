# -*- coding: utf-8 -*-
# Recorta una superficie LandXML en piezas usando los contornos de un DXF con
# capas SURF_OUTER_<nombre> y SURF_HOLE_<nombre>.
#
# Es la version general de cortar_editable07.py: alli el origen y los contornos
# estaban fijos, aqui se pasan por linea de comandos.
#
# NO BORRAR CARAS PARA QUITAR CRUCES
# El recorte deja unos pocos triangulos que se pisan en planta, de la
# re-triangulacion del borde. La tentacion es pasarles limpiar(), que elimina de
# cada par la cara menor. MEDIDO en el corte anterior de este proyecto:
#     solape real de TODOS los cruces           : 1.91 ft2 (peor par 0.398)
#     area que limpiar() destruia en una sola sup: 565 ft2
#     ademas partia Roadway N2 en 3 trozos y P11 en 20
# El remedio cuesta unas 2,000 veces mas que la enfermedad, y para el flujo a
# Revit da igual porque la Toposolid se arma con el CONTORNO y los PUNTOS, no con
# la triangulacion. Asi que los cruces se REPORTAN y se dejan.
#
# EL LIMITE DE LA MALLA (parametro opcional <limite.dxf>)
# Los contornos de corte pueden sobresalir del terreno que realmente existe. Si el
# XML de origen es mas grande que la malla de la que salieron los contornos, el
# recorte rellena ese hueco y se acaba entregando superficie donde nunca la hubo.
# Paso en la entrega anterior: 828.6 ft2 repartidos en 14 superficies, con
# Pavement Surface 13 inventando 515 ft2 (el 8.4% de si misma).
# Pasando un DXF con las mallas polyface originales, cada contorno se intersecta
# antes con la huella de su CARA SUPERIOR, y asi el corte no puede salirse de lo
# que existe de verdad.
#
# Uso:
#   python cortar_por_bordes_dxf.py <origen.xml> <bordes.dxf> <dir_salida> [nombre_combinado] [limite.dxf ...]
import os, sys, time, shutil
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict
import ezdxf
import shapely.geometry as sg
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_utils import (write_landxml, clip_surface_by_polygon, crossing_count,
                        face_connected_components, reparar_cruces)
from make_reimport_landxml import crossing_pairs

NS = {'l': 'http://www.landxml.org/schema/LandXML-1.2'}
SRC = sys.argv[1]
DXF = sys.argv[2]
OUT_DIR = sys.argv[3]
COMB = sys.argv[4] if len(sys.argv) > 4 else "_TODAS.xml"
LIMITES = sys.argv[5:]
MIN_PIEZA = 1.0
# al intersectar con la huella de la malla aparecen microastillas en el borde;
# por debajo de esto no se conservan
MIN_TROZO = 0.5

# crossing_count devuelve None -- no 0 -- cuando la malla pasa de max_edges, y una
# comprobacion que devuelve None es una comprobacion que NO se hizo.
MAX_EDGES = 200000


def cruces(v, f):
    n = crossing_count(v, f, max_edges=MAX_EDGES)
    if n is None:
        raise RuntimeError("crossing_count no reviso la malla: sube MAX_EDGES")
    return n


def solape(v, f):
    tot = 0.0
    for a, b in crossing_pairs(v, f):
        ga = sg.Polygon([v[i][:2] for i in f[a]]).buffer(0)
        gb = sg.Polygon([v[i][:2] for i in f[b]]).buffer(0)
        tot += ga.intersection(gb).area
    return tot


def area_tri(a, b, c):
    return 0.5 * abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1]))


def huella(v, f):
    t = [sg.Polygon([v[a][:2], v[b][:2], v[c][:2]]) for a, b, c in f]
    t = [x if x.is_valid else x.buffer(0) for x in t]
    u = unary_union([x for x in t if x.area > 1e-9]).buffer(0)
    g = list(u.geoms) if u.geom_type in ("MultiPolygon", "GeometryCollection") else [u]
    return unary_union([x for x in g if x.geom_type == "Polygon"])


t0 = time.time()
# ------------------------------------------------------------- origen
SV = []; SF = []
for s in ET.parse(SRC).getroot().findall('.//l:Surface', NS):
    base = len(SV); m = {}
    for q in s.findall('.//l:P', NS):
        n, e, z = (float(x) for x in q.text.split())
        m[q.get('id')] = len(SV); SV.append((e, n, z))
    for x in s.findall('.//l:F', NS):
        try: SF.append(tuple(m[y] for y in x.text.split()))
        except KeyError: pass
print(f"origen {os.path.basename(SRC)}: {len(SV):,} pts, {len(SF):,} caras")

# ------------------------------------------------------------ bordes
outs = defaultdict(list); hols = defaultdict(list)
desc = 0
for e in ezdxf.readfile(DXF).modelspace():
    if e.dxftype() != "LWPOLYLINE":
        continue
    lay = e.dxf.layer
    pts = [(q[0], q[1]) for q in e.get_points()]
    if len(pts) < 4:
        desc += 1; continue
    g = sg.Polygon(pts)
    if not g.is_valid: g = g.buffer(0)
    if g.geom_type != "Polygon" or g.area < 1.0:
        desc += 1; continue
    if lay.startswith("SURF_OUTER_"): outs[lay[len("SURF_OUTER_"):]].append(g)
    elif lay.startswith("SURF_HOLE_"): hols[lay[len("SURF_HOLE_"):]].append(g)
print(f"bordes {os.path.basename(DXF)}: {len(outs)} superficies, "
      f"{sum(len(v) for v in outs.values())} piezas, "
      f"{sum(len(v) for v in hols.values())} huecos"
      + (f" ({desc} degeneradas descartadas)" if desc else ""))

# ------------------------------------------------------- limite de malla
LIMITE = None
if LIMITES:
    from mesh_utils import solid_faces, polyface_to_mesh, MallaSimple
    hs = []
    for ruta in LIMITES:
        n = 0
        for e in ezdxf.readfile(ruta).modelspace():
            if e.dxftype() != "POLYLINE" or not e.is_poly_face_mesh:
                continue
            n += 1
            vs, caras = polyface_to_mesh(e)
            mv, top, _ = solid_faces(MallaSimple(vs, caras), 3, which="top")
            t = [sg.Polygon([mv[i][:2] for i in f]) for f in top]
            t = [x if x.is_valid else x.buffer(0) for x in t]
            t = [x for x in t if x.area > 1e-9]
            if t:
                hs.append(unary_union(t).buffer(0))
        print(f"limite {os.path.basename(ruta)}: {n} mallas polyface")
    LIMITE = unary_union(hs).buffer(0)
    bruto = LIMITE.area

    # La huella es la union de decenas de miles de triangulos y entre elementos
    # vecinos quedan FISURAS CAPILARES. Si se usa tal cual como limite, esas
    # fisuras se convierten en agujeros y en cortes: en la primera prueba dejaron
    # Pavement Surface 12 en 3 piezas con 8 huecos y Roadway N2 con 25.
    # Se cierran con un buffer de ida y vuelta (mitre para no redondear esquinas) y
    # se descartan los huecos residuales pequeños. Los huecos de edificacion, que
    # son los que hay que respetar, rondan los 3,000 ft2 de media, asi que el
    # umbral no los toca ni de lejos.
    CIERRE = 0.10       # ft; cierra fisuras de hasta 0.20 ft de ancho
    HUECO_MIN = 20.0    # ft2
    LIMITE = LIMITE.buffer(CIERRE, join_style=2).buffer(-CIERRE, join_style=2)
    gs = [g for g in (LIMITE.geoms if LIMITE.geom_type != "Polygon" else [LIMITE])
          if g.geom_type == "Polygon"]
    limpios = []
    n_huecos = quitados = 0
    for g in gs:
        buenos = []
        for r in g.interiors:
            if sg.Polygon(r).area >= HUECO_MIN:
                buenos.append(r); n_huecos += 1
            else:
                quitados += 1
        limpios.append(sg.Polygon(g.exterior, buenos))
    LIMITE = unary_union(limpios).buffer(0)
    print(f"limite valido (cara superior de las mallas): {LIMITE.area:,.1f} ft2")
    print(f"   fisuras cerradas: {LIMITE.area-bruto:+,.1f} ft2, "
          f"{quitados} huecos capilares descartados, {n_huecos} huecos reales")

# ------------------------------------------------------------- corte
por_superficie = OrderedDict()
print(f"\n{'PIEZA':26s} {'objetivo':>10s} {'obtenido':>10s} {'dif':>8s} "
      f"{'fuera':>8s} {'pz':>3s} {'hu':>3s}")
print("-" * 76)
avisos = []
recortado_por_limite = []
for nm in sorted(outs):
    for pz, pieza in enumerate(outs[nm]):
        hs = [h for h in hols.get(nm, []) if pieza.contains(h.representative_point())]

        # el contorno no puede reclamar terreno que la malla no tiene
        trozos = [pieza]
        if LIMITE is not None:
            recorte = pieza.intersection(LIMITE)
            # Lo que se pierde hay que medirlo DESCONTANDO ANTES los huecos de
            # edificacion pedidos: la huella de la malla ya no los tiene, asi que
            # si no se descuentan el informe los cuenta como recorte y da cifras
            # absurdas (50,965 ft2 en vez de 785, porque los 17 huecos suman
            # 50,180).
            util = pieza.difference(unary_union(hs)) if hs else pieza
            perdido = util.difference(LIMITE).area
            if perdido > 0.01:
                recortado_por_limite.append((nm, pz, perdido))
            trozos = [g for g in (recorte.geoms
                                  if recorte.geom_type != "Polygon" else [recorte])
                      if g.geom_type == "Polygon" and g.area > MIN_TROZO]

        obj = unary_union(trozos)
        if hs:
            obj = obj.difference(unary_union(hs))

        nv = []; nf = []
        for tg in trozos:
            th = [h for h in hs if tg.contains(h.representative_point())]
            shell = list(tg.exterior.coords)[:-1]
            holes = [list(h.exterior.coords)[:-1] for h in th]
            for r in tg.interiors:
                holes.append(list(r.coords)[:-1])
            av, af, st = clip_surface_by_polygon(SV, SF, shell,
                                                 hole_polys_xy=holes if holes else None,
                                                 patch_holes=False)
            base = len(nv)
            nv.extend(av)
            nf.extend([(a+base, b+base, c+base) for a, b, c in af])
        if not nf:
            avisos.append(f"{nm} p{pz+1}: sin geometria tras aplicar el limite")
            print(f"{nm+' p'+str(pz+1):26s} {obj.area:10,.1f} {'VACIO':>10s}")
            continue
        if cruces(nv, nf):
            nf, _, _ = reparar_cruces(nv, nf)

        comps = face_connected_components(nf)
        info = sorted(((sum(area_tri(nv[nf[i][0]], nv[nf[i][1]], nv[nf[i][2]])
                            for i in c), c) for c in comps), key=lambda t: -t[0])
        kept = [nf[i] for a, c in info if a > MIN_PIEZA for i in c]
        idx = {}; fv = []; ff = []
        for (a, b, c) in kept:
            tri = []
            for oi in (a, b, c):
                if oi not in idx:
                    idx[oi] = len(fv); fv.append(nv[oi])
                tri.append(idx[oi])
            ff.append(tuple(tri))
        if not ff:
            avisos.append(f"{nm} p{pz+1}: el origen no cubre nada de este contorno")
            print(f"{nm+' p'+str(pz+1):26s} {obj.area:10,.1f} {'VACIO':>10s}")
            continue
        got = huella(fv, ff)
        gs = [x for x in (list(got.geoms) if got.geom_type == "MultiPolygon" else [got])
              if x.area > 1]
        dif = 100*(got.area-obj.area)/obj.area
        print(f"{nm+' p'+str(pz+1):26s} {obj.area:10,.1f} {got.area:10,.1f} "
              f"{dif:+7.3f}% {got.difference(obj).area:8.4f} {len(gs):3d} "
              f"{sum(len(x.interiors) for x in gs):3d}")
        if dif < -0.5:
            avisos.append(f"{nm} p{pz+1}: falta {obj.area-got.area:,.1f} ft2 "
                          f"({-dif:.2f}%) -- el origen no llega a cubrir el contorno")
        por_superficie.setdefault(nm, []).append((fv, ff))

resultado = OrderedDict()
for nm, trozos in por_superficie.items():
    V = []; F = []
    for fv, ff in trozos:
        base = len(V)
        V.extend(fv)
        F.extend([(a+base, b+base, c+base) for a, b, c in ff])
    resultado[nm] = (V, F)

os.makedirs(OUT_DIR, exist_ok=True)
comb = os.path.join(OUT_DIR, COMB)
write_landxml(comb, [(nm, v, f) for nm, (v, f) in sorted(resultado.items())])

# write_landxml redondea a 4 decimales, asi que hay que releer del DISCO para
# saber que quedo de verdad. Una pasada de re-triangulacion y lo que sobreviva se
# reporta (ver NO BORRAR CARAS en la cabecera).
for ronda in (1, 2):
    r2 = ET.parse(comb).getroot(); rel = OrderedDict(); malas = []
    for su in r2.findall('.//l:Surface', NS):
        nm = su.get('name'); v = []; mm = {}
        for q in su.findall('.//l:P', NS):
            n, e, z = (float(x) for x in q.text.split())
            mm[q.get('id')] = len(v); v.append((e, n, z))
        f = []
        for x in su.findall('.//l:F', NS):
            try: f.append(tuple(mm[y] for y in x.text.split()))
            except KeyError: pass
        c = cruces(v, f)
        if c: malas.append((nm, c, solape(v, f)))
        rel[nm] = (v, f)
    if not malas:
        print(f"\n0 cruces en el archivo guardado")
        break
    if ronda == 1:
        print(f"\n{len(malas)} superficies con cruces, se re-triangulan")
        arr = {nm for nm, _, _ in malas}
        write_landxml(comb, [(nm, v, reparar_cruces(v, f)[0] if nm in arr else f)
                             for nm, (v, f) in rel.items()])
        continue
    print(f"\nCRUCES RESIDUALES (se dejan a proposito, no se borran)")
    print(f"   {'superficie':24s} {'cruces':>7s} {'solape ft2':>12s}")
    for nm, c, so in sorted(malas, key=lambda t: -t[2]):
        print(f"   {nm:24s} {c:7d} {so:12.5f}")
    print(f"   TOTAL {sum(x[2] for x in malas):.3f} ft2 de solape sobre "
          f"{sum(len(f) for _, f in rel.values()):,} caras")

r3 = ET.parse(comb).getroot()
tp = tf = 0
for su in r3.findall('.//l:Surface', NS):
    nm = su.get('name'); v = []; mm = {}
    for q in su.findall('.//l:P', NS):
        n, e, z = (float(x) for x in q.text.split())
        mm[q.get('id')] = len(v); v.append((e, n, z))
    f = []
    for x in su.findall('.//l:F', NS):
        try: f.append(tuple(mm[y] for y in x.text.split()))
        except KeyError: pass
    tp += len(v); tf += len(f)
    write_landxml(os.path.join(OUT_DIR, f"{nm}.xml"), [(nm, v, f)])

if recortado_por_limite:
    tot = sum(x[2] for x in recortado_por_limite)
    print(f"\nRECORTADO POR EL LIMITE DE LA MALLA: {tot:,.1f} ft2 en "
          f"{len(recortado_por_limite)} piezas")
    print("   superficie que el contorno reclamaba y la malla no tiene")
    for nm, pz, a in sorted(recortado_por_limite, key=lambda t: -t[2]):
        if a >= 0.5:
            print(f"   {nm:24s} p{pz+1} {a:10,.1f} ft2")

if avisos:
    print(f"\nAVISOS ({len(avisos)}):")
    for a in avisos:
        print(f"   {a}")

print(f"\n{len(resultado)} superficies, {tp:,} puntos, {tf:,} caras")
print(f"combinado    -> {comb}")
print(f"individuales -> {OUT_DIR}")
print(f"tiempo: {time.time()-t0:.0f}s")
