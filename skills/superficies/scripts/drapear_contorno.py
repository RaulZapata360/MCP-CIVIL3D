#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Drapea una polilínea 2D sobre una superficie TIN LandXML interpolando cotas Z.
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    import ezdxf
    from shapely.geometry import Point, Polygon
except ImportError as exc:
    sys.exit(f"Falta dependencia: {exc}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "geometria", "scripts")))
from recortar_superficie import leer_landxml
from teselar_arcos import teselar_polilinea_dxf


def interpolar_z_triangulo(p1, p2, p3, x: float, y: float) -> float:
    """Interpola cota Z sobre el plano formado por p1, p2, p3."""
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    x3, y3, z3 = p3

    # Vector normal N = (A, B, C) via producto cruz (p2-p1) x (p3-p1)
    v1 = (x2 - x1, y2 - y1, z2 - z1)
    v2 = (x3 - x1, y3 - y1, z3 - z1)
    a = v1[1] * v2[2] - v1[2] * v2[1]
    b = v1[2] * v2[0] - v1[0] * v2[2]
    c = v1[0] * v2[1] - v1[1] * v2[0]

    if abs(c) < 1e-9:
        return z1
    d = -(a * x1 + b * y1 + c * z1)
    return -(a * x + b * y + d) / c


def drapear_polilineas(ruta_xml: str, ruta_dxf: str, ruta_salida: str) -> str:
    # 1. Leer superficie TIN
    _, triangulos, _, unidad = leer_landxml(ruta_xml, None)

    # Pre-preparar polígonos de triángulos para búsqueda rápida
    tri_polys = []
    for tri in triangulos:
        p1, p2, p3 = tri
        poly = Polygon([(p1[0], p1[1]), (p2[0], p2[1]), (p3[0], p3[1])])
        tri_polys.append((poly, tri))

    # 2. Leer polilíneas 2D teselando arcos
    polilineas_2d = teselar_polilinea_dxf(ruta_dxf, 0.001)

    # 3. Drapear vértices
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    capa_3d = "DRAPE_3D_CONTOUR"
    doc.layers.new(capa_3d, dxfattribs={"color": 3})  # Verde

    for pol in polilineas_2d:
        pts_3d = []
        for x, y in pol:
            pt_shapely = Point(x, y)
            z_found = 0.0
            encontrado = False
            for poly, tri in tri_polys:
                if poly.contains(pt_shapely) or poly.touches(pt_shapely):
                    z_found = interpolar_z_triangulo(tri[0], tri[1], tri[2], x, y)
                    encontrado = True
                    break
            if not encontrado:
                dist_min = float("inf")
                for poly, tri in tri_polys:
                    d = poly.distance(pt_shapely)
                    if d < dist_min:
                        dist_min = d
                        z_found = (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0
            pts_3d.append((x, y, z_found))

        if pts_3d:
            msp.add_polyline3d(pts_3d, dxfattribs={"layer": capa_3d})

    doc.saveas(ruta_salida)
    return ruta_salida


def main():
    parser = argparse.ArgumentParser(description="Drapeado 3D de polilíneas sobre LandXML TIN.")
    parser.add_argument("--xml", required=True, help="LandXML TIN")
    parser.add_argument("--dxf", required=True, help="DXF 2D")
    parser.add_argument("--salida", required=True, help="DXF 3D de salida")
    args = parser.parse_args()

    out = drapear_polilineas(args.xml, args.dxf, args.salida)
    print(f"OK: Polilínea drapeada 3D guardada en {out}")


if __name__ == "__main__":
    main()
