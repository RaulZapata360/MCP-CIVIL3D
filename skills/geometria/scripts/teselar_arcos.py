#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Muestrea arcos (bulges) en polilíneas DXF según una sagitta dada.
"""
from __future__ import annotations

import argparse
import math
import sys
import os

try:
    import ezdxf
    from ezdxf.math import bulge_to_arc
except ImportError as exc:
    sys.exit(f"Falta dependencia ezdxf: {exc}")


def teselar_bulge(start_pt, end_pt, bulge: float, max_sagitta: float = 0.001) -> list[tuple[float, float]]:
    """Devuelve los puntos muestreados a lo largo del arco real representado por un bulge."""
    if abs(bulge) < 1e-9:
        return [end_pt]

    center, start_angle, end_angle, radius = bulge_to_arc(start_pt, end_pt, bulge)
    if radius <= 1e-9:
        return [end_pt]

    # Angulo barrido por el arco
    sweep = abs(end_angle - start_angle)
    if sweep > 2 * math.pi:
        sweep %= (2 * math.pi)

    # Calculo del paso angular maximo segun sagitta: sagitta = R * (1 - cos(dTheta / 2))
    val = max(-1.0, min(1.0, 1.0 - (max_sagitta / radius)))
    max_dtheta = 2.0 * math.acos(val)
    if max_dtheta <= 1e-6:
        max_dtheta = 0.01

    n_pasos = max(1, math.ceil(sweep / max_dtheta))
    
    puntos = []
    # Determinar direccion del arco segun signo de bulge
    if bulge < 0:
        if end_angle > start_angle:
            start_angle += 2 * math.pi
        delta = (end_angle - start_angle) / n_pasos
    else:
        if end_angle < start_angle:
            end_angle += 2 * math.pi
        delta = (end_angle - start_angle) / n_pasos

    for step in range(1, n_pasos + 1):
        ang = start_angle + step * delta
        x = center.x + radius * math.cos(ang)
        y = center.y + radius * math.sin(ang)
        puntos.append((x, y))

    return puntos


def teselar_polilinea_dxf(ruta_dxf: str, max_sagitta: float = 0.001) -> list[list[tuple[float, float]]]:
    """Lee un DXF y devuelve listas de vertices (X, Y) con arcos teselados."""
    doc = ezdxf.readfile(ruta_dxf)
    msp = doc.modelspace()
    polilineas = []

    for entity in msp:
        if entity.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            pts_teselados = []
            vertices = list(entity.get_points(format="xyb"))
            if not vertices:
                continue

            # Agregar primer punto
            pts_teselados.append((vertices[0][0], vertices[0][1]))

            for i in range(len(vertices) - 1):
                x1, y1, b = vertices[i][0], vertices[i][1], vertices[i][2]
                x2, y2 = vertices[i + 1][0], vertices[i + 1][1]
                
                if abs(b) > 1e-9:
                    sub_pts = teselar_bulge((x1, y1), (x2, y2), b, max_sagitta)
                    pts_teselados.extend(sub_pts)
                else:
                    pts_teselados.append((x2, y2))

            # Si es cerrada y el ultimo bulge no es cero
            if entity.is_closed and len(vertices) > 1:
                x1, y1, b = vertices[-1][0], vertices[-1][1], vertices[-1][2]
                x2, y2 = vertices[0][0], vertices[0][1]
                if abs(b) > 1e-9:
                    sub_pts = teselar_bulge((x1, y1), (x2, y2), b, max_sagitta)
                    pts_teselados.extend(sub_pts)

            polilineas.append(pts_teselados)

    return polilineas


def main():
    parser = argparse.ArgumentParser(description="Teselado de polilíneas DXF con arcos por sagitta.")
    parser.add_argument("--dxf", required=True, help="DXF de entrada")
    parser.add_argument("--sagitta", type=float, default=0.001, help="Sagitta máxima")
    parser.add_argument("--salida", help="DXF de salida")
    args = parser.parse_args()

    resultados = teselar_polilinea_dxf(args.dxf, args.sagitta)
    print(f"OK: Se teselaron {len(resultados)} polílineas. Puntos totales: {sum(len(p) for p in resultados)}")


if __name__ == "__main__":
    main()
