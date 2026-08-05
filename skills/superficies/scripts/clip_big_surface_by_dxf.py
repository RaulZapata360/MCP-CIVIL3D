# -*- coding: utf-8 -*-
# Recorta una superficie TIN grande (cientos de miles / millones de caras)
# contra un contorno cerrado de un DXF, conservando el INTERIOR o el EXTERIOR.
#
# Generalizacion del script clip_exterior_contorno_proyecto.py, que se escribio
# para un caso puntual y termino necesitandose una segunda vez. Pensado para
# mallas donde un recorrido ingenuo cara-por-cara con shapely tardaria horas.
#
# USO:
#   python clip_big_surface_by_dxf.py <in.xml> <nombre_superficie> <contorno.dxf> \
#          <inside|outside> <out.xml> <nombre_salida>
#
# RENDIMIENTO:
#   1) iterparse + numpy, liberando nodos (los XML pasan de 100 MB).
#   2) Pre-filtro VECTORIZADO por bounding box: las caras cuyo bbox no toca el
#      bbox del contorno se resuelven con pura aritmetica numpy, sin una sola
#      llamada a shapely (en la practica es la gran mayoria).
#   3) Solo las caras dudosas pasan por shapely, con geometria PREPARADA
#      (shapely.prepared.prep), que indexa el poligono una vez.
#
# PRECISION: toda la geometria se procesa en coordenadas LOCALES (restando un
# origen). Las coordenadas reales del proyecto son ~12,000,000 y los productos
# cruzados directos sobre esos valores pierden digitos de punto flotante
# suficientes como para dejar huecos artefacto. Ver GOTCHA 1 de la skill
# civil3d-surface-clip-merge.
import os, sys, time
import numpy as np
import xml.etree.ElementTree as ET
import ezdxf
import shapely.geometry as sg
from shapely.prepared import prep

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_utils import write_landxml, ear_clip_triangulate, barycentric_z, boundary_holes

NS = "{http://www.landxml.org/schema/LandXML-1.2}"


def read_dxf_ring(path, tol=0.05):
    """Devuelve un anillo cerrado de (x,y). Soporta tanto un DXF con UNA entidad
    cerrada como uno donde el perimetro esta repartido en VARIAS entidades
    abiertas (p.ej. un ARC + una polilinea, como 'Contorno Pavimento 18.dxf'):
    en ese caso se encadenan por coincidencia de extremos, invirtiendo tramos
    cuando haga falta."""
    segs = []
    for e in ezdxf.readfile(path).modelspace():
        t = e.dxftype()
        if t == "LWPOLYLINE":
            r = [(p[0], p[1]) for p in e.get_points()]; closed = e.closed
        elif t == "POLYLINE":
            r = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]; closed = e.is_closed
        elif t == "SPLINE":
            r = [(p.x, p.y) for p in e.flattening(0.05)]; closed = e.closed
        elif t == "ARC":
            r = [(p.x, p.y) for p in e.flattening(0.05)]; closed = False
        elif t == "LINE":
            r = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]; closed = False
        else:
            continue
        if closed:
            if r[0] != r[-1]: r.append(r[0])
            return r
        segs.append(r)

    if not segs:
        raise SystemExit("No se encontro geometria utilizable en el DXF")
    if len(segs) == 1:
        r = segs[0]
        if r[0] != r[-1]: r.append(r[0])
        return r

    def near(a, b): return abs(a[0]-b[0]) < tol and abs(a[1]-b[1]) < tol
    chain = list(segs.pop(0))
    while segs:
        for i, s in enumerate(segs):
            if   near(chain[-1], s[0]):  chain += s[1:]
            elif near(chain[-1], s[-1]): chain += list(reversed(s))[1:]
            elif near(chain[0],  s[-1]): chain = s[:-1] + chain
            elif near(chain[0],  s[0]):  chain = list(reversed(s))[:-1] + chain
            else: continue
            segs.pop(i); break
        else:
            raise SystemExit(f"No se pudieron encadenar los {len(segs)+1} tramos "
                             f"del DXF (extremos no coinciden dentro de {tol} ft)")
    if not near(chain[0], chain[-1]):
        print(f"  AVISO: el anillo no cierra exacto ("
              f"{((chain[0][0]-chain[-1][0])**2+(chain[0][1]-chain[-1][1])**2)**0.5:.3f} ft), se cierra")
    chain.append(chain[0])
    return chain


def read_surface(xml_path, surf_name, ox, oy):
    """iterparse con liberacion de nodos: los <P> y <F> del LandXML se leen y se
    descartan sobre la marcha para no mantener el arbol completo en RAM."""
    xs = []; ys = []; zs = []; id2i = {}; faces = []
    want = None
    for ev, el in ET.iterparse(xml_path, events=("start", "end")):
        if ev == "start" and el.tag == NS + "Surface":
            want = (surf_name is None) or (el.get("name") == surf_name)
        elif ev == "end":
            if el.tag == NS + "P" and want:
                n, e, z = (float(v) for v in el.text.split())
                id2i[el.get("id")] = len(xs)
                xs.append(e - ox); ys.append(n - oy); zs.append(z)
                el.clear()
            elif el.tag == NS + "F" and want:
                try: faces.append(tuple(id2i[v] for v in el.text.split()))
                except KeyError: pass
                el.clear()
            elif el.tag == NS + "Surface":
                el.clear()
    if not xs:
        raise SystemExit(f"Superficie '{surf_name}' no encontrada o vacia en {xml_path}")
    return (np.array(xs), np.array(ys), np.array(zs),
            np.array(faces, dtype=np.int64))


def main():
    if len(sys.argv) < 7:
        print(__doc__ or "faltan argumentos"); raise SystemExit(1)
    xml_in, surf_in, dxf_in, mode, xml_out, name_out = sys.argv[1:7]
    if mode not in ("inside", "outside"):
        raise SystemExit("modo debe ser 'inside' o 'outside'")
    keep_inside = (mode == "inside")
    t0 = time.time()

    ring = read_dxf_ring(dxf_in)
    ox, oy = ring[0]
    poly = sg.Polygon([(x - ox, y - oy) for x, y in ring])
    if not poly.is_valid:
        poly = poly.buffer(0)
        print("  contorno auto-reparado con buffer(0)")
    pminx, pminy, pmaxx, pmaxy = poly.bounds
    pp = prep(poly)
    print(f"Contorno: {len(ring)} vertices, area {poly.area:,.1f} ft2")

    print("Leyendo LandXML...")
    X, Y, Z, F = read_surface(xml_in, surf_in, ox, oy)
    print(f"  {len(X):,} puntos / {len(F):,} caras   ({time.time()-t0:.1f}s)")

    fx = X[F]; fy = Y[F]
    disjoint_bbox = ((fx.max(axis=1) < pminx) | (fx.min(axis=1) > pmaxx) |
                     (fy.max(axis=1) < pminy) | (fy.min(axis=1) > pmaxy))
    # bbox disjunto => la cara esta con certeza FUERA del contorno
    if keep_inside:
        idx_fast = np.array([], dtype=np.int64)          # nada se salva de una
        idx_test = np.nonzero(~disjoint_bbox)[0]         # el resto hay que mirarlo
        n_bbox_drop = int(disjoint_bbox.sum())
    else:
        idx_fast = np.nonzero(disjoint_bbox)[0]          # fuera => se conserva
        idx_test = np.nonzero(~disjoint_bbox)[0]
        n_bbox_drop = 0
    print(f"Pre-filtro bbox: {len(idx_fast):,} conservadas directo, "
          f"{n_bbox_drop:,} descartadas directo, {len(idx_test):,} a evaluar "
          f"({100*len(idx_test)/max(len(F),1):.1f}%)")

    new_verts = []; vkey = {}
    def vid(x, y, z, dec=4):
        k = (round(x, dec), round(y, dec), round(z, dec))
        i = vkey.get(k)
        if i is None:
            i = len(new_verts); vkey[k] = i; new_verts.append((x + ox, y + oy, z))
        return i

    out_faces = []
    n_keep = n_drop = n_clip = 0
    area_keep = 0.0; area_drop = 0.0

    def emit(a, b, c):
        out_faces.append((vid(X[a], Y[a], Z[a]), vid(X[b], Y[b], Z[b]), vid(X[c], Y[c], Z[c])))

    for fi in idx_fast:
        a, b, c = F[fi]
        emit(a, b, c)
        area_keep += 0.5*abs((X[b]-X[a])*(Y[c]-Y[a]) - (X[c]-X[a])*(Y[b]-Y[a]))
        n_keep += 1
    area_drop += 0.0

    step = max(1, len(idx_test)//10)
    for k, fi in enumerate(idx_test):
        if k and k % step == 0:
            print(f"    {100*k/len(idx_test):.0f}%  ({time.time()-t0:.1f}s)")
        a, b, c = F[fi]
        pa = (X[a], Y[a]); pb = (X[b], Y[b]); pc = (X[c], Y[c])
        tri = sg.Polygon([pa, pb, pc])
        if not tri.is_valid or tri.area <= 1e-12:
            continue
        inside_all = pp.contains(tri)
        outside_all = pp.disjoint(tri)
        if inside_all or outside_all:
            keep = inside_all if keep_inside else outside_all
            if keep:
                emit(a, b, c); area_keep += tri.area; n_keep += 1
            else:
                area_drop += tri.area; n_drop += 1
            continue
        piece = tri.intersection(poly) if keep_inside else tri.difference(poly)
        if piece.is_empty:
            area_drop += tri.area; n_drop += 1; continue
        area_drop += tri.area - piece.area
        tri3d = ((pa[0], pa[1], Z[a]), (pb[0], pb[1], Z[b]), (pc[0], pc[1], Z[c]))
        parts = list(piece.geoms) if piece.geom_type == "MultiPolygon" else [piece]
        for g in parts:
            if g.geom_type != "Polygon" or g.area <= 1e-9: continue
            shell = list(g.exterior.coords)[:-1]
            holes = [list(r.coords)[:-1] for r in g.interiors]
            allpts = shell + [p for h in holes for p in h]
            try:
                tris = ear_clip_triangulate(shell, holes if holes else None)
            except Exception:
                continue
            ids = [vid(px, py, barycentric_z(tri3d, px, py)) for px, py in allpts]
            for (i1, i2, i3) in tris:
                out_faces.append((ids[i1], ids[i2], ids[i3]))
            area_keep += g.area
        n_clip += 1

    print(f"\nConservadas: {n_keep:,}  eliminadas: {n_drop:,}  recortadas: {n_clip:,}")
    print(f"Vertices resultado: {len(new_verts):,}  caras resultado: {len(out_faces):,}")
    print(f"Area conservada: {area_keep:,.1f} ft2")

    print("\n--- VERIFICACION INDEPENDIENTE ---")
    bad = 0; bad_area = 0.0
    for (i1, i2, i3) in out_faces:
        v1, v2, v3 = new_verts[i1], new_verts[i2], new_verts[i3]
        cx = (v1[0]+v2[0]+v3[0])/3.0 - ox; cy = (v1[1]+v2[1]+v3[1])/3.0 - oy
        c_in = pp.contains(sg.Point(cx, cy))
        if c_in != keep_inside:
            bad += 1
            bad_area += 0.5*abs((v2[0]-v1[0])*(v3[1]-v1[1]) - (v3[0]-v1[0])*(v2[1]-v1[1]))
    lado = "dentro" if keep_inside else "fuera"
    print(f"  caras del resultado con centroide del lado equivocado: {bad}  "
          f"(area total {bad_area:.6f} ft2)")
    print(f"  se esperaba conservar solo lo de {lado} del contorno")
    h, nm = boundary_holes(out_faces)
    print(f"  huecos internos={h}  aristas no-manifold={nm}")

    write_landxml(xml_out, [(name_out, new_verts, out_faces)])
    print(f"\nEscrito: {xml_out}   ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
