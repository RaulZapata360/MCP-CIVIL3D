# -*- coding: utf-8 -*-
# Funciones compartidas para extraer superficies TIN exactas desde mallas polyface,
# incluyendo deteccion y tratamiento de SOLIDOS (top/bottom face), resolucion de
# solapes entre grupos, y recorte de una superficie ya generada contra un poligono
# de corte (para separar p.ej. "calzada" de "estacionamiento"). Usado por
# mesh_multi_to_landxml.py, mesh_grouped_top_only.py y clip_surface_by_boundary.py.
# Ver memoria 'surface-from-mesh-workflow' para el contexto completo del metodo.
import numpy as np
from collections import defaultdict
import xml.etree.ElementTree as ET


def solid_faces(mb, dec, which="top", tol=1e-6):
    """Si la malla es un SOLIDO (>=1 XY con mas de 1 valor de Z -> tiene cara
    superior + inferior + paredes), se queda SOLO con las caras cuyos 3 vertices
    son el punto de MAYOR Z (which='top') o MENOR Z (which='bottom') en su columna
    XY. Si no es solido (ya es una superficie 2.5D), devuelve las caras tal cual.
    Devuelve (mv, faces_idx, era_solido)."""
    mv = list(mb.vertices)
    xy_extz = {}
    for v in mv:
        k = (round(v[0], dec), round(v[1], dec))
        if k not in xy_extz: xy_extz[k] = [v[2], v[2]]
        else:
            xy_extz[k][0] = min(xy_extz[k][0], v[2])
            xy_extz[k][1] = max(xy_extz[k][1], v[2])
    xy_zset = defaultdict(set)
    for v in mv:
        xy_zset[(round(v[0], dec), round(v[1], dec))].add(round(v[2], 3))
    n_multi = sum(1 for zs in xy_zset.values() if len(zs) > 1)
    es_solido = n_multi > 0 and n_multi >= 0.5 * len(xy_zset)

    target_idx = 1 if which == "top" else 0
    def is_target(vi):
        v = mv[vi]
        k = (round(v[0], dec), round(v[1], dec))
        return abs(v[2] - xy_extz[k][target_idx]) < tol

    if es_solido:
        faces = [fc for fc in mb.faces if all(is_target(vi) for vi in fc)]
    else:
        faces = list(mb.faces)
    return mv, faces, es_solido


def solid_thickness_stats(mb, dec):
    """Devuelve (min,max,mean,std) del espesor (Z_top - Z_bottom) por columna XY,
    y (n_columnas_con_2_Z, n_columnas_total). Para diagnosticar si un 'solido' es
    de espesor constante (paquete de pavimento tipico) o variable (otro tipo de
    elemento)."""
    xy_z = defaultdict(list)
    for v in mb.vertices:
        k = (round(v[0], dec), round(v[1], dec))
        xy_z[k].append(v[2])
    thick = [max(zs) - min(zs) for zs in xy_z.values() if len(zs) >= 2]
    n_multi = len(thick); n_total = len(xy_z)
    if not thick:
        return None, n_multi, n_total
    t = np.array(thick)
    return (t.min(), t.max(), t.mean(), t.std()), n_multi, n_total


def weld_and_clean(mv, raw_face_idx, dec):
    """Suelda vertices por XY y limpia caras degeneradas/duplicadas DENTRO de una
    sola entidad. Devuelve (verts, faces, n_degeneradas, n_duplicadas)."""
    vkey = {}; verts = []
    def vid(x, y, z):
        k = (round(x, dec), round(y, dec)); i = vkey.get(k)
        if i is None: i = len(verts); vkey[k] = i; verts.append((x, y, z))
        return i
    raw = []
    for fc in raw_face_idx:
        idx = [vid(*mv[k]) for k in fc]
        if len(idx) >= 4: raw.append((idx[0], idx[1], idx[2])); raw.append((idx[0], idx[2], idx[3]))
        elif len(idx) == 3: raw.append(tuple(idx))
    faces = []; seen = set(); degen = 0; dup = 0
    for t in raw:
        if len(set(t)) < 3: degen += 1; continue
        key = frozenset(t)
        if key in seen: dup += 1; continue
        seen.add(key); faces.append(t)
    return verts, faces, degen, dup


def face_connected_components(faces):
    """Agrupa caras en componentes CONEXAS por adyacencia de arista (dos caras que
    comparten una arista estan en la misma componente). Devuelve una lista de listas
    de INDICES de cara (sobre la misma lista `faces` de entrada). Necesario para no
    confundir piezas geometricamente DESCONECTADAS (islas separadas de un recorte muy
    marginal) con huecos internos de una sola pieza -- ver comentario en
    clip_surface_by_polygon."""
    edge_to_faces = defaultdict(list)
    for fi, (a, b, c) in enumerate(faces):
        for u, v in [(a, b), (b, c), (c, a)]:
            edge_to_faces[(min(u, v), max(u, v))].append(fi)
    adj = defaultdict(set)
    for fis in edge_to_faces.values():
        for i in fis:
            for j in fis:
                if i != j: adj[i].add(j)
    seen = set(); comps = []
    for fi in range(len(faces)):
        if fi in seen: continue
        comp = []; st = [fi]
        while st:
            x = st.pop()
            if x in seen: continue
            seen.add(x); comp.append(x)
            for y in adj[x]:
                if y not in seen: st.append(y)
        comps.append(comp)
    return comps


def boundary_holes(faces):
    """Devuelve (n_huecos_internos, n_aristas_no_manifold). Los huecos se cuentan POR
    COMPONENTE CONEXA (ver face_connected_components) -- si el resultado tiene varias
    piezas geometricamente separadas (islas, no huecos), NO se cuentan como huecos
    entre si, solo los anillos internos genuinos DENTRO de cada pieza."""
    e2f = defaultdict(int)
    for a, b, c in faces:
        for u, v in [(b, c), (c, a), (a, b)]: e2f[(min(u, v), max(u, v))] += 1
    nonman = sum(1 for n in e2f.values() if n > 2)
    n_holes = 0
    for comp_idx in face_connected_components(faces):
        comp_faces = [faces[i] for i in comp_idx]
        rings = detect_boundary_rings(comp_faces)
        if len(rings) > 1: n_holes += len(rings) - 1
    return n_holes, nonman


def crossing_count(verts, faces, max_edges=6000):
    """QA: pares de aristas que se cruzan en planta (solape interno). None si la
    malla es demasiado grande para revisar a costo razonable."""
    def o(a, b, c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def seg_cross(p1, p2, p3, p4):
        if len({p1, p2, p3, p4}) < 4: return False
        a, b, c, d = verts[p1], verts[p2], verts[p3], verts[p4]
        return (o(a,b,c)>0)!=(o(a,b,d)>0) and (o(c,d,a)>0)!=(o(c,d,b)>0)
    E = set()
    for t in faces:
        for u, v in [(t[0],t[1]),(t[1],t[2]),(t[2],t[0])]: E.add((min(u,v),max(u,v)))
    E = list(E)
    if len(E) > max_edges: return None
    cell = 50.0; grid = defaultdict(list)
    for ei, e in enumerate(E):
        a, b = verts[e[0]], verts[e[1]]
        for cx in range(int(min(a[0],b[0])//cell), int(max(a[0],b[0])//cell)+1):
            for cy in range(int(min(a[1],b[1])//cell), int(max(a[1],b[1])//cell)+1):
                grid[(cx,cy)].append(ei)
    nc = 0; seen = set()
    for lst in grid.values():
        for i in range(len(lst)):
            for j in range(i+1, len(lst)):
                a, b = lst[i], lst[j]
                if (a,b) in seen: continue
                seen.add((a,b))
                if seg_cross(E[a][0],E[a][1],E[b][0],E[b][1]): nc += 1
    return nc


def resolve_group_overlaps(surfaces, dec=2, min_overlap_pct=20.0, z_tol=0.01):
    """Resuelve solapes EN PLANTA entre superficies YA EXTRAIDAS (top-face de cada
    grupo), aplicando la regla: si dos superficies comparten puntos XY y una esta
    consistentemente por ENCIMA de la otra en esos puntos, la de ABAJO se descarta
    por completo (no se recorta, se elimina la superficie entera).

    surfaces: lista de (name, verts, faces). Devuelve (keep, discarded_info, mixed_info):
      keep = lista de (name, verts, faces) sobrevivientes (mismo orden relativo)
      discarded_info = lista de dicts {name, dominated_by} de las eliminadas
      mixed_info = lista de dicts {name_a, name_b, a_above, b_above, n_shared} para
        pares que se CRUZAN (a veces uno arriba, a veces el otro) -- la regla no
        aplica limpio ahi; se conservan ambas y quedan marcadas para revision manual
        (el llamador decide como marcar el nombre).
    """
    xy_z = []
    for name, verts, faces in surfaces:
        d = {}
        for x, y, z in verts:
            k = (round(x, dec), round(y, dec))
            if k not in d or z > d[k]: d[k] = z
        xy_z.append(d)

    n = len(surfaces)
    dominated_by = {}   # idx -> set(idx que lo dominan)
    mixed_pairs = []     # (i, j, a_above, b_above, n_shared) cruzados
    for i in range(n):
        for j in range(i+1, n):
            A, B = xy_z[i], xy_z[j]
            shared = set(A) & set(B)
            if not shared: continue
            na, nb = len(A), len(B)
            pa = len(shared)/na*100; pb = len(shared)/nb*100
            if pa < min_overlap_pct and pb < min_overlap_pct: continue
            a_above = b_above = 0
            for k in shared:
                d = A[k] - B[k]
                if d > z_tol: a_above += 1
                elif d < -z_tol: b_above += 1
            if a_above > 0 and b_above == 0:
                dominated_by.setdefault(j, set()).add(i)   # j esta debajo de i
            elif b_above > 0 and a_above == 0:
                dominated_by.setdefault(i, set()).add(j)   # i esta debajo de j
            elif a_above > 0 and b_above > 0:
                mixed_pairs.append({"i": i, "j": j, "a_above": a_above, "b_above": b_above,
                                     "n_shared": len(shared)})
            # a_above==0 and b_above==0 -> empate exacto, no se marca (se conservan ambas)

    discard_idx = set(dominated_by.keys())
    keep = [surfaces[i] for i in range(n) if i not in discard_idx]
    discarded_info = [{"name": surfaces[i][0],
                        "dominated_by": sorted(surfaces[k][0] for k in dominated_by[i])}
                       for i in sorted(discard_idx)]
    mixed_info = [{"name_a": surfaces[m["i"]][0], "name_b": surfaces[m["j"]][0],
                    "a_above": m["a_above"], "b_above": m["b_above"], "n_shared": m["n_shared"]}
                   for m in mixed_pairs]
    return keep, discarded_info, mixed_info


def cluster_by_footprint(entities_extent, tol=0.5):
    """entities_extent: lista de dicts con xmin,xmax,ymin,ymax. Devuelve lista de
    grupos (listas de indices) que comparten footprint XY dentro de tol (ft)."""
    n = len(entities_extent)
    groups = []; used = [False]*n
    for i in range(n):
        if used[i]: continue
        grp = [i]; used[i] = True
        a = entities_extent[i]
        for j in range(i+1, n):
            if used[j]: continue
            b = entities_extent[j]
            if (abs(a["xmin"]-b["xmin"])<tol and abs(a["xmax"]-b["xmax"])<tol and
                abs(a["ymin"]-b["ymin"])<tol and abs(a["ymax"]-b["ymax"])<tol):
                grp.append(j); used[j] = True
        groups.append(grp)
    return groups


def write_landxml(out_path, surfaces):
    """surfaces: lista de (name, verts, faces). Escribe un LandXML con multiples
    <Surface>, formato Northing/Easting/Elev, caras 1-based, sin datos de vecindad
    (Civil 3D los rechaza)."""
    with open(out_path, "w", encoding="utf-8") as o:
        o.write('<?xml version="1.0"?>\n<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2" date="2026-07-06" time="12:00:00">\n')
        o.write(' <Units><Imperial areaUnit="squareFoot" linearUnit="USSurveyFoot" volumeUnit="cubicFeet" temperatureUnit="fahrenheit" pressureUnit="inHG" diameterUnit="inch" angularUnit="decimal degrees" directionUnit="decimal degrees"/></Units>\n')
        o.write(' <Surfaces>\n')
        for name, verts, faces in surfaces:
            o.write(f'  <Surface name="{name}">\n   <Definition surfType="TIN">\n    <Pnts>\n')
            for i, v in enumerate(verts, 1):
                o.write(f'     <P id="{i}">{v[1]:.4f} {v[0]:.4f} {v[2]:.4f}</P>\n')
            o.write('    </Pnts>\n    <Faces>\n')
            for a, b, c in faces:
                o.write(f'     <F>{a+1} {b+1} {c+1}</F>\n')
            o.write('    </Faces>\n   </Definition>\n  </Surface>\n')
        o.write(' </Surfaces>\n</LandXML>\n')


def read_landxml_surface(xml_path, surf_name):
    """Lee una <Surface> especifica de un LandXML (propio o exportado por Civil 3D).
    Devuelve (verts, faces) con verts en (X=Easting, Y=Northing, Z=Elev) -- coordenadas
    reales de dibujo. Los <F> referencian <P id="..."> por su ID -- se arma un mapeo
    id->indice explicito (NO se asume id secuencial ni que empiece en 1: los LandXML
    exportados por Civil 3D suelen traer IDs con huecos y que no arrancan en 1, p.ej.
    tras ediciones/Rebuild -- asumir id-1==indice corrompe silenciosamente las caras)."""
    ns = {'l': 'http://www.landxml.org/schema/LandXML-1.2'}
    root = ET.parse(xml_path).getroot()
    for s in root.findall('.//l:Surface', ns):
        if s.get('name') != surf_name: continue
        verts = []; id2idx = {}
        for p in s.findall('.//l:P', ns):
            n, e, z = (float(x) for x in p.text.split())
            id2idx[p.get('id')] = len(verts)
            verts.append((e, n, z))
        faces = [tuple(id2idx[x] for x in f.text.split()) for f in s.findall('.//l:F', ns)]
        return verts, faces
    raise ValueError(f"Surface '{surf_name}' no encontrada en {xml_path}")


def barycentric_z(tri_verts, x, y):
    """tri_verts: 3 tuplas (x,y,z) del triangulo ORIGINAL (plano). Interpola Z en
    (x,y) via coordenadas baricentricas -- exacto para cualquier punto dentro o sobre
    el borde del triangulo (asi es como Civil 3D interpola elevacion en un corte)."""
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = tri_verts
    d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if abs(d) < 1e-12:
        return (z1 + z2 + z3) / 3.0
    l1 = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / d
    l2 = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / d
    l3 = 1 - l1 - l2
    return l1 * z1 + l2 * z2 + l3 * z3


def ear_clip_triangulate(poly_xy, holes_xy=None):
    """Triangula un poligono (con huecos interiores opcionales) via mapbox_earcut
    (C++ earcut, libreria de produccion usada por Mapbox -- robusta ante poligonos
    casi degenerados/aristas muy delgadas, a diferencia de un ear-clipping casero).
    poly_xy: lista de (x,y) del anillo exterior. holes_xy: lista opcional de anillos
    interiores (cada uno lista de (x,y)) -- necesario cuando un poligono a restar
    cae COMPLETO dentro del anillo exterior sin tocar su borde (deja un hueco tipo
    "dona"). Devuelve lista de tuplas de indices (0-based) sobre la lista COMBINADA
    poly_xy + cada hueco concatenado en orden (si no hay huecos, es simplemente
    poly_xy, igual que antes -- backward compatible).

    NOTA HISTORICA: la implementacion anterior era un ear-clipping propio con un
    fallback de "abanico" para poligonos degenerados que podia generar triangulos
    autointersectantes (se detecto en el recorte de Superficie_G37 contra
    Contorno_Calzada_N2 -- un caso de recorte muy marginal, ~4% de area conservada,
    que producia cientos de cruces internos y area duplicada ~2x). mapbox_earcut no
    tiene ese fallback y maneja estos casos correctamente."""
    n = len(poly_xy)
    if n < 3: return []
    if n == 3 and not holes_xy: return [(0, 1, 2)]
    import numpy as np
    import mapbox_earcut as earcut
    all_pts = list(poly_xy)
    ring_ends = [n]
    if holes_xy:
        for h in holes_xy:
            all_pts.extend(h)
            ring_ends.append(len(all_pts))
    verts = np.array(all_pts, dtype=np.float64)
    rings = np.array(ring_ends, dtype=np.uint32)
    idx = earcut.triangulate_float64(verts, rings)
    return [tuple(int(v) for v in idx[i:i + 3]) for i in range(0, len(idx), 3)]


def clip_surface_by_polygon(verts, faces, clip_poly_xy, hole_polys_xy=None,
                            patch_holes=True):
    """Recorta una superficie (verts XYZ, faces) contra un poligono de corte cerrado
    (lista de (x,y)), quedandose SOLO con la parte DENTRO. Cada triangulo que el
    contorno atraviesa se recorta exactamente en la linea (via shapely) y se
    re-triangula (ear-clipping); la elevacion de los vertices nuevos se interpola
    baricentricamente del triangulo original (exacto, sin Delaunay).

    hole_polys_xy: opcional, lista de anillos (cada uno lista de (x,y)) que se
    restan del poligono de corte -- para recortar un "anillo" entre un contorno
    exterior y uno o mas contornos interiores (p.ej. calzada alrededor de una
    estructura). Cada hueco debe estar completamente contenido en clip_poly_xy.

    IMPORTANTE: toda la geometria (shapely + ear-clipping) se procesa en
    coordenadas LOCALES (restando un origen de referencia) -- las coordenadas
    reales del proyecto son grandes (~12,000,000+), y hacer aritmetica de
    precision (productos cruzados, tests de convexidad) directo sobre esos
    valores pierde varios digitos de precision de punto flotante, lo que puede
    hacer que el ear-clipping rechace vertices validos y aborte silenciosamente
    dejando huecos "artefacto" en zonas de triangulos delgados. Localizar el
    origen antes de la geometria resuelve esto de raiz (no es solo aflojar una
    tolerancia). Las coordenadas se devuelven ya en el sistema real (se suma el
    origen de vuelta al escribir new_verts).

    Devuelve (new_verts, new_faces, stats) donde stats tiene area_original,
    area_recortada, n_tri_dentro, n_tri_cruzados, n_tri_fuera."""
    import shapely.geometry as sg

    ox, oy = clip_poly_xy[0][0], clip_poly_xy[0][1]  # origen local arbitrario (cualquier punto cercano sirve)
    shell_local = [(x - ox, y - oy) for x, y in clip_poly_xy]
    holes_local = [[(x - ox, y - oy) for x, y in hole] for hole in hole_polys_xy] if hole_polys_xy else None
    clip_poly = sg.Polygon(shell_local, holes_local)
    if not clip_poly.is_valid:
        clip_poly = clip_poly.buffer(0)

    new_verts = []; vkey = {}
    def vid(xl, yl, z, dec=4):
        """xl,yl en coordenadas LOCALES; se guarda ya en coordenadas reales (xl+ox, yl+oy)."""
        k = (round(xl, dec), round(yl, dec), round(z, dec))
        i = vkey.get(k)
        if i is None:
            i = len(new_verts); vkey[k] = i; new_verts.append((xl + ox, yl + oy, z))
        return i

    new_faces = []
    n_dentro = n_cruzado = n_fuera = 0
    area_orig = 0.0; area_clip = 0.0
    for (i1, i2, i3) in faces:
        v1, v2, v3 = verts[i1], verts[i2], verts[i3]
        # version local de los 3 vertices (x,y locales, z real) para barycentric_z e is_convex
        l1 = (v1[0] - ox, v1[1] - oy, v1[2])
        l2 = (v2[0] - ox, v2[1] - oy, v2[2])
        l3 = (v3[0] - ox, v3[1] - oy, v3[2])
        tri = sg.Polygon([(l1[0], l1[1]), (l2[0], l2[1]), (l3[0], l3[1])])
        if not tri.is_valid or tri.area < 1e-9: continue
        area_orig += tri.area
        if tri.within(clip_poly):
            n_dentro += 1
            ia = vid(*l1); ib = vid(*l2); ic = vid(*l3)
            new_faces.append((ia, ib, ic)); area_clip += tri.area
            continue
        inter = tri.intersection(clip_poly)
        if inter.is_empty:
            n_fuera += 1; continue
        n_cruzado += 1
        # la interseccion puede ser MultiPolygon, o una GeometryCollection que
        # mezcla poligonos con lineas/puntos (cuando el triangulo toca el
        # contorno solo de canto). Hay que quedarse SOLO con los poligonos: una
        # version anterior hacia [inter] para todo lo que no fuera MultiPolygon
        # y luego pedia .exterior, lo que reventaba con GeometryCollection.
        if inter.geom_type in ("MultiPolygon", "GeometryCollection"):
            geoms = [g for g in inter.geoms if g.geom_type == "Polygon"]
        elif inter.geom_type == "Polygon":
            geoms = [inter]
        else:
            geoms = []
        for g in geoms:
            if g.is_empty or g.area < 1e-9: continue
            shell = list(g.exterior.coords)[:-1]  # ya en locales (clip_poly y tri estan en locales)
            if len(shell) < 3: continue
            # GOTCHA (2026-07-30): la interseccion de un triangulo con el poligono
            # de corte puede tener HUECOS propios -- pasa cuando un triangulo
            # grande abarca por completo un vacio interior del contorno (p.ej. la
            # huella de una edificacion). Una version anterior solo triangulaba
            # g.exterior e IGNORABA g.interiors, con lo que esos vacios se
            # RELLENABAN silenciosamente: el area salia correcta como suma, pero
            # los huecos desaparecian del resultado. Hay que pasar los anillos
            # interiores a ear_clip_triangulate, que los soporta.
            holes = [list(r.coords)[:-1] for r in g.interiors if len(r.coords) >= 4]
            coords = shell + [p for h in holes for p in h]
            area_clip += g.area
            for (a, b, c) in ear_clip_triangulate(shell, holes if holes else None):
                pa, pb, pc = coords[a], coords[b], coords[c]
                za = barycentric_z((l1, l2, l3), *pa)
                zb = barycentric_z((l1, l2, l3), *pb)
                zc = barycentric_z((l1, l2, l3), *pc)
                ia = vid(pa[0], pa[1], za); ib = vid(pb[0], pb[1], zb); ic = vid(pc[0], pc[1], zc)
                if len({ia, ib, ic}) == 3: new_faces.append((ia, ib, ic))

    # --- soldadura final por PROXIMIDAD (no igualdad exacta) ---
    # Dos triangulos originales vecinos que comparten una arista cruzada por el
    # contorno calculan el mismo punto de corte de forma INDEPENDIENTE (cada uno via
    # su propia interseccion con shapely) -- el resultado puede diferir en centesimas
    # de pie por redondeo interno de GEOS, aunque geometricamente sea el mismo punto.
    # El redondeo a 4 decimales de vid() no siempre alcanza a unificarlos (se han
    # visto diferencias de hasta ~0.04 ft), dejando "grietas" (huecos delgados) en
    # la costura. Se sueldan aqui todos los vertices a <0.05 ft entre si.
    new_verts, new_faces = weld_by_proximity(new_verts, new_faces, tol=0.05)

    # --- parche final: rellenar huecos "artefacto" (la malla ORIGINAL SI tenia
    # cobertura ahi) que sobrevivan a la soldadura por proximidad -- casos raros de
    # convergencia de varios triangulos originales cerca de un punto/esquina del
    # contorno. Un hueco se rellena SOLO si su centroide cae dentro de algun
    # triangulo original (evita rellenar huecos REALES del proyecto, como gores o
    # estructuras, que deben quedar intactos).
    import shapely.geometry as sg
    from shapely.strtree import STRtree
    orig_tris_local = []
    for (i1, i2, i3) in faces:
        v1, v2, v3 = verts[i1], verts[i2], verts[i3]
        t = sg.Polygon([(v1[0] - ox, v1[1] - oy), (v2[0] - ox, v2[1] - oy), (v3[0] - ox, v3[1] - oy)])
        if t.is_valid and t.area > 1e-9: orig_tris_local.append(t)
    tree = STRtree(orig_tris_local)

    # IMPORTANTE: los anillos de borde se calculan POR COMPONENTE CONEXA, no sobre
    # new_faces global. Si el recorte produce varias piezas geometricamente
    # DESCONECTADAS (islas separadas -- pasa cuando el contorno solo roza una
    # esquina marginal de una superficie grande, ver Superficie_G37 contra
    # Contorno_Calzada_N2), tratar el borde exterior de una isla como si fuera un
    # "hueco" de otra isla mas grande produce triangulos espurios que puentean el
    # hueco (real, entre islas) y terminan SOLAPANDO la geometria real (~2x area
    # duplicada, cientos de cruces internos). Al procesar cada componente conexa
    # por separado, cada una tiene su propio anillo exterior (el mas grande DE ESA
    # componente) y solo sus propios anillos internos genuinos se consideran huecos.
    # GOTCHA (2026-07-30): si se pidieron huecos explicitos (hole_polys_xy), el
    # parcheador NO debe rellenarlos. Su criterio es "la malla original cubre
    # esta zona -> es un artefacto", y eso se cumple justamente en los huecos
    # pedidos: la malla de entrada SI tiene triangulos ahi (por eso hubo que
    # recortarlos). Sin esta salvaguarda el recorte quitaba los huecos y el
    # parche los volvia a rellenar, dando un resultado sin ningun hueco pero con
    # el area "correcta" como suma -- un fallo silencioso.
    huecos_pedidos = [sg.Polygon(h) for h in holes_local] if holes_local else []

    # GOTCHA (2026-07-31): con patch_holes=False se desactiva este parche. Es
    # NECESARIO cuando la malla de entrada trae triangulos ultra-alargados (el
    # relleno de casco convexo que produce Civil 3D al re-triangular tras editar
    # una superficie). Al recortar esos slivers, detect_boundary_rings devuelve
    # anillos degenerados que el parche interpreta como huecos y "rellena",
    # generando caras ENORMES fuera del contorno: en Roadway Surface N5 el
    # area_recortada salia exacta (26,639.0) pero la malla acababa con 9,436 ft2
    # fuera del contorno y 2,451 cruces internos. Sin el parche, el recorte es
    # limpio. Dejarlo activado solo cuando la malla de origen es sana.
    n_parcheados = 0
    for comp_face_idx in (face_connected_components(new_faces) if patch_holes else []):
        comp_faces = [new_faces[i] for i in comp_face_idx]
        rings_raw = detect_boundary_rings(comp_faces)
        holes = rings_raw[1:] if len(rings_raw) > 1 else []
        for h_raw in holes:
            h = h_raw[:-1] if (len(h_raw) > 1 and h_raw[0] == h_raw[-1]) else h_raw  # quitar cierre duplicado
            h = list(dict.fromkeys(h))  # por si acaso, sin perder orden
            if len(h) < 3: continue
            xs = [new_verts[v][0] for v in h]; ys = [new_verts[v][1] for v in h]
            cx = sum(xs) / len(xs) - ox; cy = sum(ys) / len(ys) - oy
            pt = sg.Point(cx, cy)
            # ¿es uno de los huecos pedidos explicitamente? Se compara por SOLAPE
            # DE AREA, no por "el centroide cae dentro": un hueco concavo (forma
            # de L o de C) tiene su centroide FUERA de si mismo, y con el test de
            # centroide se colaba y acababa relleno.
            if huecos_pedidos:
                anillo = sg.Polygon([(new_verts[v][0] - ox, new_verts[v][1] - oy) for v in h])
                if not anillo.is_valid: anillo = anillo.buffer(0)
                if not anillo.is_empty and anillo.area > 0:
                    if any(anillo.intersection(hp).area > 0.5 * min(anillo.area, hp.area)
                           for hp in huecos_pedidos):
                        continue  # hueco pedido explicitamente -- respetarlo
            cand = tree.query(pt)
            covered = any(orig_tris_local[j].contains(pt) or orig_tris_local[j].distance(pt) < 0.05 for j in cand)
            if not covered: continue  # hueco real (p.ej. gore/estructura) -- no tocar
            ring_xy_local = [(new_verts[v][0] - ox, new_verts[v][1] - oy) for v in h]
            for (a, b, c) in ear_clip_triangulate(ring_xy_local):
                ia, ib, ic = h[a], h[b], h[c]
                if len({ia, ib, ic}) == 3: new_faces.append((ia, ib, ic))
            n_parcheados += 1

    # dedup final: el parche de huecos puede, en puntos de "pellizco" de la malla
    # (un anillo detectado que en realidad no correspondia a un hueco real), insertar
    # una cara ya existente -- se descartan duplicados exactos (mismo set de 3
    # vertices, sin importar el orden/rotacion).
    seen_faces = set(); deduped = []
    for f in new_faces:
        key = frozenset(f)
        if key in seen_faces: continue
        seen_faces.add(key); deduped.append(f)
    n_dup = len(new_faces) - len(deduped)
    new_faces = deduped

    stats = {"area_original": area_orig, "area_recortada": area_clip,
              "n_tri_dentro": n_dentro, "n_tri_cruzados": n_cruzado, "n_tri_fuera": n_fuera,
              "huecos_artefacto_parcheados": n_parcheados, "caras_duplicadas_removidas": n_dup}
    return new_verts, new_faces, stats


def detect_boundary_rings(faces):
    """Devuelve la lista de anillos de borde, cada uno como lista de indices de
    vertice EN ORDEN SECUENCIAL alrededor del anillo (caminando arista por arista,
    no solo agrupando el componente conexo -- necesario para poder triangular el
    anillo despues con ear-clipping). El primer elemento de cada ring se repite al
    final (cierre). Ordenados de mayor a menor tamano -- el primero es tipicamente
    el perimetro exterior, el resto son huecos internos."""
    e2f = defaultdict(int)
    for a, b, c in faces:
        for u, v in [(b, c), (c, a), (a, b)]: e2f[(min(u, v), max(u, v))] += 1
    bnd = [e for e, n in e2f.items() if n == 1]
    adj = defaultdict(list)
    for u, v in bnd: adj[u].append(v); adj[v].append(u)
    used = set(); rings = []
    for e0 in bnd:
        k0 = (min(e0), max(e0))
        if k0 in used: continue
        u0, v0 = e0; ring = [u0, v0]; used.add(k0); prev, cur = u0, v0
        while cur != u0:
            nxt = None
            for cand in adj[cur]:
                k = (min(cur, cand), max(cur, cand))
                if cand != prev and k not in used: nxt = cand; break
            if nxt is None:
                for cand in adj[cur]:
                    k = (min(cur, cand), max(cur, cand))
                    if k not in used: nxt = cand; break
            if nxt is None: break
            used.add((min(cur, nxt), max(cur, nxt))); ring.append(nxt); prev, cur = cur, nxt
        rings.append(ring)
    rings.sort(key=len, reverse=True)
    return rings


def weld_by_proximity(verts, faces, tol=0.05):
    """Fusiona vertices que esten a menos de <tol> ft entre si (no solo los
    exactamente iguales), usando un arbol espacial + union-find. Cada grupo fusionado
    se reemplaza por el promedio de sus puntos. Descarta caras que queden degeneradas
    tras la fusion. Usado como paso final de limpieza de costuras en recortes."""
    from scipy.spatial import cKDTree
    import numpy as np
    if len(verts) < 2: return verts, faces
    pts = np.array([(v[0], v[1]) for v in verts])
    tree = cKDTree(pts)
    parent = list(range(len(verts)))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i, j in tree.query_pairs(tol):
        ri, rj = find(i), find(j)
        if ri != rj: parent[max(ri, rj)] = min(ri, rj)
    groups = {}
    for i in range(len(verts)):
        r = find(i); groups.setdefault(r, []).append(i)
    new_idx = {}; new_verts = []
    for r, members in groups.items():
        xs = [verts[m][0] for m in members]; ys = [verts[m][1] for m in members]; zs = [verts[m][2] for m in members]
        avg = (sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs))
        gid = len(new_verts); new_verts.append(avg)
        for m in members: new_idx[m] = gid
    new_faces = []
    for a, b, c in faces:
        na, nb, nc = new_idx[a], new_idx[b], new_idx[c]
        if len({na, nb, nc}) == 3: new_faces.append((na, nb, nc))
    return new_verts, new_faces


def subtract_surface_from_surface(verts, faces, sub_verts, sub_faces):
    """Resta (elimina) la huella (footprint, en planta) de una superficie SUSTRAENDA
    (sub_verts, sub_faces) de una superficie PRINCIPAL (verts, faces), dejando SOLO
    la parte de la principal que queda FUERA de esa huella. La huella se calcula
    como la union de todos los triangulos de la sustraenda (via shapely, soporta
    forma concava, huecos propios, o piezas desconectadas -- no se asume que sea un
    poligono simple). Misma estrategia de precision numerica (coordenadas locales),
    mismo ear-clip via mapbox_earcut (con soporte de huecos, para el caso en que la
    huella a restar caiga completa dentro de un triangulo grande sin tocar sus
    bordes, dejando un hueco tipo "dona" en ese triangulo), y la misma soldadura
    final por proximidad para las costuras de los triangulos recortados.

    Devuelve (new_verts, new_faces, stats) donde stats tiene area_original,
    area_resultado, area_huella_resta, n_tri_intactos, n_tri_cruzados, n_tri_eliminados."""
    import shapely.geometry as sg
    from shapely.ops import unary_union

    ox, oy = verts[0][0], verts[0][1]

    sub_tris = []
    for (i1, i2, i3) in sub_faces:
        v1, v2, v3 = sub_verts[i1], sub_verts[i2], sub_verts[i3]
        t = sg.Polygon([(v1[0] - ox, v1[1] - oy), (v2[0] - ox, v2[1] - oy), (v3[0] - ox, v3[1] - oy)])
        if t.is_valid and t.area > 1e-9: sub_tris.append(t)
    sub_poly = unary_union(sub_tris)
    area_huella = sub_poly.area

    new_verts = []; vkey = {}
    def vid(xl, yl, z, dec=4):
        k = (round(xl, dec), round(yl, dec), round(z, dec))
        i = vkey.get(k)
        if i is None:
            i = len(new_verts); vkey[k] = i; new_verts.append((xl + ox, yl + oy, z))
        return i

    new_faces = []
    n_intacto = n_cruzado = n_eliminado = 0
    area_orig = 0.0; area_result = 0.0
    for (i1, i2, i3) in faces:
        v1, v2, v3 = verts[i1], verts[i2], verts[i3]
        l1 = (v1[0] - ox, v1[1] - oy, v1[2])
        l2 = (v2[0] - ox, v2[1] - oy, v2[2])
        l3 = (v3[0] - ox, v3[1] - oy, v3[2])
        tri = sg.Polygon([(l1[0], l1[1]), (l2[0], l2[1]), (l3[0], l3[1])])
        if not tri.is_valid or tri.area < 1e-9: continue
        area_orig += tri.area
        if not tri.intersects(sub_poly):
            n_intacto += 1
            ia = vid(*l1); ib = vid(*l2); ic = vid(*l3)
            new_faces.append((ia, ib, ic)); area_result += tri.area
            continue
        diff = tri.difference(sub_poly)
        if diff.is_empty:
            n_eliminado += 1
            continue
        n_cruzado += 1
        geoms = list(diff.geoms) if diff.geom_type == "MultiPolygon" else [diff]
        for g in geoms:
            if g.is_empty or g.area < 1e-9: continue
            ext = list(g.exterior.coords)[:-1]
            if len(ext) < 3: continue
            holes = [list(interior.coords)[:-1] for interior in g.interiors]
            holes = [h for h in holes if len(h) >= 3]
            area_result += g.area
            all_pts = ext + [pt for h in holes for pt in h]
            for (a, b, c) in ear_clip_triangulate(ext, holes if holes else None):
                pa, pb, pc = all_pts[a], all_pts[b], all_pts[c]
                za = barycentric_z((l1, l2, l3), *pa)
                zb = barycentric_z((l1, l2, l3), *pb)
                zc = barycentric_z((l1, l2, l3), *pc)
                ia = vid(pa[0], pa[1], za); ib = vid(pb[0], pb[1], zb); ic = vid(pc[0], pc[1], zc)
                if len({ia, ib, ic}) == 3: new_faces.append((ia, ib, ic))

    new_verts, new_faces = weld_by_proximity(new_verts, new_faces, tol=0.05)

    seen_faces = set(); deduped = []
    for f in new_faces:
        key = frozenset(f)
        if key in seen_faces: continue
        seen_faces.add(key); deduped.append(f)
    new_faces = deduped

    stats = {"area_original": area_orig, "area_resultado": area_result,
              "area_huella_resta": area_huella,
              "n_tri_intactos": n_intacto, "n_tri_cruzados": n_cruzado,
              "n_tri_eliminados": n_eliminado}
    return new_verts, new_faces, stats


def subtract_polygon_from_surface(verts, faces, polygon_xy):
    """Resta (elimina) un poligono cerrado en planta (polygon_xy, lista de (x,y) en
    coordenadas REALES) de una superficie -- para el caso "dame lo de DENTRO y lo de
    FUERA de este contorno" cuando lo de DENTRO ya se obtiene con
    clip_surface_by_polygon y se necesita el complemento exacto. Internamente
    triangula el poligono (via ear_clip_triangulate, con Z=0 -- no importa, solo se
    usa la huella en planta) y reusa subtract_surface_from_surface.

    GOTCHA (encontrado 2026-07-09, Contorno_Calzada_N5): NO sumar el origen local dos
    veces -- el poligono ya viene en coordenadas reales; solo hay que localizar
    (restar el origen) para triangular, y usar los puntos YA REALES (no
    relocalizarlos otra vez) al reconstruir los vertices que se pasan a
    subtract_surface_from_surface (que localiza internamente con su propio origen,
    el de la superficie principal). Sumar el origen dos veces duplica las
    coordenadas y hace que el poligono a restar quede muy lejos de la superficie,
    de forma que "nada se cruza" silenciosamente (0 triangulos cruzados/eliminados,
    resultado identico al original) -- un fallo silencioso, no un error visible."""
    ring = list(polygon_xy)
    if ring[0] != ring[-1]:
        ring = ring + [ring[0]]
    ring = ring[:-1]  # sin el cierre duplicado, para ear_clip_triangulate
    ox, oy = ring[0]
    ring_local = [(x - ox, y - oy) for x, y in ring]
    tris_idx = ear_clip_triangulate(ring_local)
    poly_verts = [(x, y, 0.0) for x, y in ring]  # YA en coords reales -- no sumar ox,oy de nuevo
    return subtract_surface_from_surface(verts, faces, poly_verts, tris_idx)


def reparar_cruces(verts, faces, max_iter=8):
    """Quita los cruces en planta RE-TRIANGULANDO la zona afectada, en vez de
    borrar las caras culpables.

    POR QUE: limpiar() (en make_reimport_landxml) elimina de cada par la cara mas
    pequeña. Cuando los cruces salen de la re-triangulacion del borde al recortar,
    esas caras son REALES, no astillas: en el corte de "TODO-editable 07" se
    llevaba 55.2 ft2 de Roadway N2 -- partiendola ademas en 3 trozos -- y 25.0 ft2
    de Pavement Surface 13. Es el mismo fallo que ya costo 1,322 ft2 en su dia.

    Aqui se toma la union de los triangulos implicados, se borran, y ese poligono
    se vuelve a triangular por ear clipping. Como la union se rellena con los
    MISMOS vertices que ya estaban, no se inventan cotas ni se pierde area, y el
    ear clipping no produce triangulos solapados por construccion.

    Devuelve (faces_nuevas, n_retrianguladas, area_perdida).
    """
    import shapely.geometry as _sg
    from shapely.ops import unary_union as _uu
    from make_reimport_landxml import crossing_pairs as _cp

    faces = list(faces)
    idx = {}
    for i, p in enumerate(verts):
        idx.setdefault((round(p[0], 6), round(p[1], 6)), i)

    tocadas = 0
    for _ in range(max_iter):
        pares = _cp(verts, faces)
        if not pares:
            break
        impl = sorted({f for par in pares for f in par})
        tris = []
        for fi in impl:
            t = faces[fi]
            g = _sg.Polygon([verts[t[0]][:2], verts[t[1]][:2], verts[t[2]][:2]])
            if not g.is_valid:
                g = g.buffer(0)
            if g.area > 1e-12:
                tris.append(g)
        if not tris:
            break
        zona = _uu(tris).buffer(0)
        quedan = [f for i, f in enumerate(faces) if i not in set(impl)]
        area_antes = sum(g.area for g in tris)

        nuevas = []
        for g in (zona.geoms if zona.geom_type != "Polygon" else [zona]):
            if g.geom_type != "Polygon" or g.area <= 1e-9:
                continue
            shell = list(g.exterior.coords)[:-1]
            holes = [list(r.coords)[:-1] for r in g.interiors if len(r.coords) >= 4]
            try:
                tri = ear_clip_triangulate(shell, holes if holes else None)
            except Exception:
                tri = []
            coords = shell + [p for h in holes for p in h]
            for (a, b, c) in tri:
                try:
                    ia = idx[(round(coords[a][0], 6), round(coords[a][1], 6))]
                    ib = idx[(round(coords[b][0], 6), round(coords[b][1], 6))]
                    ic = idx[(round(coords[c][0], 6), round(coords[c][1], 6))]
                except KeyError:
                    continue          # vertice que no estaba: se descarta el tri
                if ia != ib and ib != ic and ia != ic:
                    nuevas.append((ia, ib, ic))
        # solo se acepta si la reparacion NO pierde area apreciable
        area_desp = sum(abs((verts[b][0]-verts[a][0])*(verts[c][1]-verts[a][1])
                            - (verts[c][0]-verts[a][0])*(verts[b][1]-verts[a][1]))/2
                        for a, b, c in nuevas)
        if area_desp < area_antes - 0.5:
            break                     # no mejora: se deja como esta
        faces = quedan + nuevas
        tocadas += len(impl)

    return faces, tocadas, 0.0


class MallaSimple:
    """Envoltorio minimo (.vertices / .faces) para poder pasarle a solid_faces
    cualquier malla leida de fuera."""
    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces


def polyface_to_mesh(e):
    """(vertices, caras triangulares) de una POLYLINE polyface de ezdxf.

    OJO CON LOS FLAGS: los VERTICES llevan 192 (64|128) y los registros de CARA
    llevan 128 a secas. Filtrar por "flags & 128" no distingue nada, porque los
    vertices tambien lo cumplen -- hay que mirar el bit 64. Los indices de cara
    son 1-based y con signo (el signo marca si la arista es visible), de ahi el
    abs() y el -1.

    Los cuadrilateros se parten en dos triangulos por la diagonal 0-2, que es lo
    unico que admite LandXML.
    """
    vs = []
    caras = []
    for v in e.vertices:
        f = v.dxf.flags
        if f & 64:
            L = v.dxf.location
            vs.append((L.x, L.y, L.z))
        elif f & 128:
            idx = []
            for a in ("vtx0", "vtx1", "vtx2", "vtx3"):
                if v.dxf.hasattr(a):
                    n = v.dxf.get(a)
                    if n:
                        idx.append(abs(n) - 1)
            idx = [i for k, i in enumerate(idx) if i not in idx[:k]]
            if len(idx) == 3:
                caras.append(tuple(idx))
            elif len(idx) == 4:
                caras.append((idx[0], idx[1], idx[2]))
                caras.append((idx[0], idx[2], idx[3]))
    return vs, caras
