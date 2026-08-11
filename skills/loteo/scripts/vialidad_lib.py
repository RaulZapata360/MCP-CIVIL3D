# -*- coding: utf-8 -*-
"""Geometria de la vialidad de un loteo: calzada limpia, ejes y mallado.

DE DONDE SALE LA CALZADA. Un DXF de loteo dibuja los lotes, no las calles: la
calzada es el espacio que queda ENTRE las manzanas. Se obtiene por cierre
morfologico de la union de lotes (dilatar y contraer cierra los pasillos entre
manzanas pero no la periferia abierta) y restando despues los propios lotes.

EL BORDE TIENE QUE SALIR DE AHI, NO DE UN REPARTO POR CELDAS. Si el flujo
reparte la vialidad entre calles con nombre muestreando una rejilla y uniendo un
circulo alrededor de cada celda, el poligono resultante tiene un vertice por
metro y giros medianos de 50 grados: es un borde dentado. La vialidad cruda, en
cambio, tiene por borde el propio deslinde de los lotes -- rectas de decenas de
metros. Medido sobre un caso real: 2.293 vertices y giro mediano 52,5 grados
contra 140 vertices y giro mediano 0,0 grados.

El reparto en calles sigue haciendo falta, pero SOLO para saber que rasante
aplica en cada punto, y de eso se encarga `z_red` por eje mas cercano.
"""
import math

import numpy as np
import shapely.geometry as sg
from shapely.ops import unary_union

from terrazas_lib import solo_poligonos, densificar_anillo

ANCHO_ASTILLA = 1.5     # m — mas angosto que esto no es calzada, es ruido
TOL_SIMPLIFICA = 0.05   # m — quita microvertices sin mover las rectas
PASO_BORDE = 2.0        # m
PASO_INTERIOR = 3.0     # m


def limpiar_calzada(cal):
    """Quita las astillas que se cuelan entre lotes vecinos y simplifica.

    Donde dos lotes contiguos no se tocan exactamente, la calzada se cuela entre
    ellos como una lengua de 1 a 2 m de largo y pocos centimetros de ancho. En un
    caso real habia 615 de esas astillas, 51,5 m2 en total: son las "muecas" del
    contorno.

    Se quitan por apertura morfologica y DESPUES se simplifica con 5 cm. No al
    reves, y no solo con apertura: la apertura sola dispara los vertices de 2.308
    a 18.764 porque el buffer sustituye rectas por arcos."""
    d = ANCHO_ASTILLA / 2
    ast = cal.difference(cal.buffer(-d).buffer(d))
    piezas = [p for p in (ast.geoms if ast.geom_type.startswith("Multi") else [ast])
              if p.area > 0.02]
    if piezas:
        cal = cal.difference(unary_union(piezas))
    cal = solo_poligonos(cal.simplify(TOL_SIMPLIFICA))
    piezas = [p for p in (cal.geoms if cal.geom_type.startswith("Multi") else [cal])
              if p.area > 5.0]
    return unary_union(piezas) if piezas else cal


def z_red(calles, x, y, sigma=5.0):
    """Cota de la calzada usando el eje MAS CERCANO de toda la red.

    DOS TRAMPAS QUE ESTA FUNCION EVITA.

    1. Proyectar sobre el eje de "su" calle. El reparto por visibilidad le
       adjudica a una calle trozos que pertenecen a otra; proyectando ahi salen
       estaciones absurdas. En un caso real un punto quedaba a 59,7 m del eje de
       su propia calle -- una calzada mide unos 10 m -- y su cota saltaba 5,65 m
       respecto del punto vecino.

    2. Mezclar solo los ejes de una ventana (el mas cercano mas N metros). Al
       recorrer el borde, ese conjunto entra y sale de golpe y la cota da un
       salto en cada cambio: diente de sierra en la solera. Aqui participan TODOS
       los ejes siempre, con peso que decae exponencialmente; ninguno entra ni
       sale, asi que la cota varia de forma continua."""
    p = sg.Point(x, y)
    ds = [(c["eje"].distance(p), c) for c in calles]
    dmin = min(d for d, _ in ds)
    num = den = 0.0
    for d, c in ds:
        w = math.exp(-(d - dmin) / sigma) / (d + 0.5) ** 2
        if w < 1e-9:
            continue
        num += w * float(np.interp(c["eje"].project(p), c["est"], c["z"]))
        den += w
    return num / den if den else 0.0


def ramales_sin_eje(calzada, calles, radio=15.0, area_min=60.0, largo_min=8.0):
    """Tramos de calzada que ningun eje recorre.

    El eje de una calle no siempre cubre toda su calzada: en un caso real el de
    la principal dejaba fuera 1.562 m2 de su propio pavimento, a 46,8 m de si
    mismo. Eso hace dos danos a la vez -- la cota proyectada sale disparatada, y
    si ademas se recorta la calzada por cercania al eje, ese tramo desaparece.
    La solucion es darles SU PROPIO EJE y resolverlos como una calle mas.

    Devuelve [(poligono, eje)]. La rasante hay que resolverla despues, junto con
    el resto de la red, para que los encuentros queden a cota unica."""
    import rasantes_lib as R
    corr = unary_union([c["eje"].buffer(radio) for c in calles])
    falta = solo_poligonos(calzada.difference(corr))
    out = []
    piezas = falta.geoms if falta.geom_type.startswith("Multi") else [falta]
    for p in sorted(piezas, key=lambda g: -g.area):
        if p.is_empty or p.area < area_min:
            continue
        eje = R._eje_pca(p).intersection(p)
        if eje.geom_type == "MultiLineString":
            eje = max(eje.geoms, key=lambda g: g.length)
        if eje.geom_type == "LineString" and eje.length >= largo_min:
            out.append((p, eje))
    return out


def nube_calzada(poly):
    """Contorno densificado mas siembra interior.

    La siembra interior NO es opcional: triangular un corredor largo usando solo
    los vertices del contorno produce triangulos que lo cruzan de lado a lado, y
    en 3D se ven como pliegues."""
    pts = []
    for p in (poly.geoms if poly.geom_type.startswith("Multi") else [poly]):
        for anillo in [p.exterior] + list(p.interiors):
            pts.extend(densificar_anillo(list(anillo.coords), PASO_BORDE))
    minx, miny, maxx, maxy = poly.bounds
    dentro = poly.buffer(-PASO_INTERIOR * 0.4)
    if not dentro.is_empty:
        for x in np.arange(minx, maxx, PASO_INTERIOR):
            for y in np.arange(miny, maxy, PASO_INTERIOR):
                if dentro.contains(sg.Point(x, y)):
                    pts.append((float(x), float(y)))
    vistos, out = set(), []
    for x, y in pts:
        k = (round(x, 3), round(y, 3))
        if k not in vistos:
            vistos.add(k)
            out.append((x, y))
    return out


def mallar_poligono(poly, pts, zfun, area_min=0.05):
    """Delaunay sobre la nube, quedandose con lo que cae dentro del poligono."""
    from shapely import delaunay_triangles
    tri = delaunay_triangles(sg.MultiPoint([sg.Point(p) for p in pts]))
    idx = {(round(x, 3), round(y, 3)): i for i, (x, y) in enumerate(pts)}
    verts = [(x, y, zfun(x, y)) for x, y in pts]
    faces = []
    for t in tri.geoms:
        if t.area < area_min or not poly.contains(t.representative_point()):
            continue
        try:
            a, b, c = (idx[(round(x, 3), round(y, 3))]
                       for x, y in list(t.exterior.coords)[:-1])
        except (KeyError, ValueError):
            continue
        if a != b and b != c and a != c:
            faces.append((a, b, c))
    usados = sorted({i for f in faces for i in f})
    remap = {v: k for k, v in enumerate(usados)}
    return ([verts[i] for i in usados],
            [(remap[a], remap[b], remap[c]) for a, b, c in faces])
