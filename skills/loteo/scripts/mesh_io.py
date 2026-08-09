# -*- coding: utf-8 -*-
"""Utilidades de malla TIN: lectura de LandXML, interpolacion baricentrica y
triangulacion de poligonos con huecos.

POR QUE VIVE AQUI. La cadena de calculo original importaba estas tres funciones
desde la skill `civil3d-surface-clip-merge`, que solo existia en la maquina donde
se armo el proyecto. Sin ellas `superficie_proyecto.py` no corre y no se puede
regenerar `datos_proyecto.json` -- que es la fuente del area aprovechable por
lote. Se reimplementan aqui, dentro del proyecto, para que la verificacion sea
reproducible por si sola.

CONVENCION DE COORDENADAS. LandXML escribe cada punto como "norte este cota"
(primero Y, luego X). Los vertices que devuelve este modulo estan en el orden
(x, y, z) que usa el resto del proyecto, asi que la lectura invierte los dos
primeros campos.
"""
import re
import numpy as np
import shapely.geometry as sg
from shapely import constrained_delaunay_triangles


def read_landxml_surface(path, nombre=None):
    """Devuelve (verts, faces) de una <Surface> del LandXML.

    verts: lista de (x, y, z).  faces: lista de (i1, i2, i3) como INDICES
    dentro de `verts`.

    Los <P id> del archivo de Civil 3D no arrancan en 1 ni son correlativos, de
    modo que las caras se remapean por id explicito. Asumir id-1 == indice
    corrompe la malla en silencio (es una de las observaciones ya registradas
    del Informe 1).

    Las caras marcadas con i="1" son las que Civil 3D no dibuja; se conservan
    para que la numeracion de caras siga calzando con `mask_viva.npy`, que se
    genero contra la lista completa.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        s = f.read()

    if nombre:
        # acotar al bloque de la superficie pedida antes de parsear
        m = re.search(r'<Surface\s+name="' + re.escape(nombre) + r'"', s)
        if m:
            ini = m.start()
            sig = s.find("<Surface ", ini + 1)
            s = s[ini:sig] if sig > 0 else s[ini:]

    # el TIN vive en <Definition surfType="TIN">, no en <SourceData><Contours>
    d = s.find('<Definition surfType="TIN"')
    if d >= 0:
        s = s[d:]

    porid = {}
    verts = []
    for mid, cuerpo in re.findall(r'<P\s+id="(\d+)"\s*>([^<]+)</P>', s):
        p = cuerpo.split()
        if len(p) < 3:
            continue
        # LandXML: norte este cota  ->  se entrega (x, y, z)
        porid[int(mid)] = len(verts)
        verts.append((float(p[1]), float(p[0]), float(p[2])))

    faces = []
    for cuerpo in re.findall(r"<F[^>]*>([^<]+)</F>", s):
        p = cuerpo.split()
        if len(p) < 3:
            continue
        try:
            a, b, c = porid[int(p[0])], porid[int(p[1])], porid[int(p[2])]
        except KeyError:
            continue          # cara que referencia un punto ausente
        if a != b and b != c and a != c:
            faces.append((a, b, c))
    return verts, faces


def barycentric_z(tri, x, y):
    """Cota interpolada dentro del triangulo `tri` = (a, b, c), cada uno (x,y,z)."""
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = tri
    den = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if abs(den) < 1e-14:
        return (z1 + z2 + z3) / 3.0
    l1 = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / den
    l2 = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / den
    l3 = 1.0 - l1 - l2
    return l1 * z1 + l2 * z2 + l3 * z3


def ear_clip_triangulate(shell, holes=None):
    """Triangula un poligono 2D con huecos.

    `shell` y cada hueco son listas de (x, y) SIN repetir el punto de cierre.
    Devuelve [(a, b, c)] con indices dentro de la lista concatenada
    shell + hueco1 + hueco2 + ...  (el mismo contrato que espera
    `superficie_proyecto.malla_plana`).

    Se apoya en la triangulacion de Delaunay restringida de shapely, que respeta
    los bordes y los huecos y no agrega vertices nuevos; los vertices de cada
    triangulo se mapean de vuelta a su indice por coordenada.
    """
    holes = holes or []
    pts = list(shell) + [p for h in holes for p in h]
    if len(shell) < 3:
        return []

    idx = {}
    for i, (x, y) in enumerate(pts):
        idx.setdefault((round(x, 7), round(y, 7)), i)

    poly = sg.Polygon(shell, holes if holes else None)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return []

    tris = []
    for t in constrained_delaunay_triangles(poly).geoms:
        cs = list(t.exterior.coords)[:-1]
        if len(cs) != 3:
            continue
        try:
            a, b, c = (idx[(round(x, 7), round(y, 7))] for x, y in cs)
        except KeyError:
            continue      # vertice que no proviene del contorno original
        if a != b and b != c and a != c:
            tris.append((a, b, c))
    return tris
