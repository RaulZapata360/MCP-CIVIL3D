# -*- coding: utf-8 -*-
"""
Verifica un paquete Dynamo -> Revit (MAESTRO o GEO_REVIT) SIN abrir Revit.

Reproduce exactamente el filtro que aplica Dynamo_CreateToposolids_ConHuecos.py
(MIN_SEG_LEN = 0.1 ft) y comprueba que lo que llegara a Toposolid.Create es
geometria valida. Todo lo que falle aqui es un dialogo bloqueante en Revit.

    python verificar_paquete.py MAESTRO [GEO_REVIT]
"""
from __future__ import annotations

import csv
import math
import os
import sys
from collections import OrderedDict, defaultdict

from shapely.geometry import Polygon, Point

MIN_SEG_LEN = 0.1        # ft, el mismo del script de Dynamo
TOL_REVIT = 1.0 / 32.0 / 12.0   # 1/32" en pies = 0.002604
AQUI = os.path.dirname(os.path.abspath(__file__))

ok = fail = 0


def check(nombre, cond, detalle=""):
    global ok, fail
    print(("  OK   " if cond else "  FALLA") + f" {nombre}" + (f"   {detalle}" if detalle else ""))
    if cond:
        ok += 1
    else:
        fail += 1


def limpiar(pts):
    """Mismo filtro que build_loop() en el script de Dynamo."""
    if not pts:
        return []
    out = [pts[0]]
    for p in pts[1:]:
        if math.dist(out[-1], p) >= MIN_SEG_LEN:
            out.append(p)
    while len(out) > 1 and math.dist(out[0], out[-1]) < MIN_SEG_LEN:
        out.pop()
    return out


def cargar(carpeta):
    base = os.path.join(AQUI, carpeta)
    pts = defaultdict(list)
    with open(os.path.join(base, "All_Points_ByPiece.csv"), newline="") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            pts[(row[0], int(row[1]))].append((float(row[2]), float(row[3]), float(row[4])))
    rings = OrderedDict()
    with open(os.path.join(base, "All_Boundaries_Complete.csv"), newline="") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            key = (row[0], int(row[1]))
            d = rings.setdefault(key, {"OUTER": {}, "HOLE": {}})
            d[row[2]].setdefault(int(row[3]), []).append(
                (int(row[4]), float(row[5]), float(row[6])))
    return pts, rings


def analizar(carpeta):
    print(f"\n{'=' * 72}\n{carpeta}\n{'=' * 72}")
    pts, rings = cargar(carpeta)

    n_pts = sum(len(v) for v in pts.values())
    n_vert = sum(len(l) for d in rings.values() for g in d.values() for l in g.values())
    n_holes = sum(len(d["HOLE"]) for d in rings.values())
    print(f"  piezas {len(rings)} | puntos {n_pts:,} | vertices contorno {n_vert:,} "
          f"| huecos {n_holes}")

    check("40 Toposolid (pares superficie/pieza)", len(rings) == 40, f"{len(rings)}")
    check("22,791 puntos", n_pts == 22791, f"{n_pts:,}")
    check("4,795 vertices de contorno", n_vert == 4795, f"{n_vert:,}")
    check("17 huecos", n_holes == 17, f"{n_holes}")

    sin_outer, degenerados, invalidos, huecos_fuera = [], [], [], []
    cortos, sin_pts = [], []
    # Los puntos son vertices del TIN original; el contorno viene simplificado a
    # 0.01 ft, asi que los puntos del borde quedan hasta 0.01 ft por fuera. Se
    # mide la distancia, no solo dentro/fuera: lo que importa es cuanto.
    fuera_tol = []          # > 0.1 ft: el paquete los descarta, Revit los rechaza
    fuera_revit = []        # > 1/32": sobre la tolerancia de Revit
    peor_fuera = 0.0
    area_total = 0.0
    zmin, zmax = 1e18, -1e18

    for key, d in rings.items():
        etq = f"{key[0]}#{key[1]}"
        if 0 not in d["OUTER"]:
            sin_outer.append(etq)
            continue
        crudo = [(x, y) for _, x, y in sorted(d["OUTER"][0])]
        anillo = limpiar(crudo)
        if len(anillo) < 3:
            degenerados.append(etq)
            continue

        # segmentos por debajo de la tolerancia de Revit (tras el filtro)
        n = len(anillo)
        for i in range(n):
            if math.dist(anillo[i], anillo[(i + 1) % n]) < TOL_REVIT:
                cortos.append(etq)
                break

        poly = Polygon(anillo)
        if not poly.is_valid:
            invalidos.append(f"{etq}: {poly.is_valid_reason if hasattr(poly, 'is_valid_reason') else 'autointersectado'}")
            poly = poly.buffer(0)

        huecos = []
        for rid in sorted(d["HOLE"]):
            hc = limpiar([(x, y) for _, x, y in sorted(d["HOLE"][rid])])
            if len(hc) < 3:
                degenerados.append(f"{etq} hueco {rid}")
                continue
            hp = Polygon(hc)
            if not hp.is_valid:
                hp = hp.buffer(0)
            if not poly.contains(hp):
                huecos_fuera.append(f"{etq} hueco {rid}")
            huecos.append(hc)

        neto = Polygon(anillo, huecos)
        if not neto.is_valid:
            neto = neto.buffer(0)
        area_total += neto.area

        grupo = pts.get(key, [])
        if not grupo:
            sin_pts.append(etq)
        for x, y, z in grupo:
            zmin, zmax = min(zmin, z), max(zmax, z)
            q = Point(x, y)
            if not poly.covers(q):
                dd = q.distance(poly)
                peor_fuera = max(peor_fuera, dd)
                if dd > MIN_SEG_LEN:
                    fuera_tol.append((dd, etq))
                elif dd > TOL_REVIT:
                    fuera_revit.append((dd, etq))

    check("todas las piezas tienen anillo OUTER", not sin_outer, str(sin_outer[:3]))
    check("ningun anillo degenerado tras el filtro de 0.1 ft", not degenerados,
          str(degenerados[:3]))
    check("ningun anillo autointersecado", not invalidos, str(invalidos[:2]))
    check("todos los huecos dentro de su exterior", not huecos_fuera, str(huecos_fuera[:3]))
    check(f"ningun segmento < 1/32\" ({TOL_REVIT:.6f} ft)", not cortos, str(cortos[:3]))
    check("ninguna pieza sin puntos", not sin_pts, str(sin_pts[:3]))
    check(f"ningun punto fuera por mas de {MIN_SEG_LEN} ft (dispara 'Slab Shape Edit failed')",
          not fuera_tol, f"{len(fuera_tol)} puntos")
    print(f"  desborde maximo de un punto : {peor_fuera:.6f} ft "
          f"(= tolerancia de simplificacion del contorno)")
    if fuera_revit:
        peores = sorted(fuera_revit, reverse=True)[:3]
        print(f"  [i] {len(fuera_revit):,} puntos entre 1/32\" y {MIN_SEG_LEN} ft por fuera; "
              f"peor {peores[0][0]:.4f} ft en {peores[0][1]}")
        print(f"      Residuo de simplificar el contorno a 0.01 ft mientras los puntos "
              f"siguen siendo los del TIN original.")
    print(f"  area neta de perfiles : {area_total:,.1f} ft2")
    print(f"  rango Z               : {zmin:.2f} a {zmax:.2f} ft")
    return pts, area_total


def comparar(a, b):
    print(f"\n{'=' * 72}\nDESFASE MAESTRO - GEO_REVIT\n{'=' * 72}")
    comunes = set(a) & set(b)
    dx, dy, n = [], [], 0
    for k in comunes:
        for p, q in zip(a[k], b[k]):
            dx.append(p[0] - q[0])
            dy.append(p[1] - q[1])
            n += 1
    check("mismo numero de puntos en ambas variantes",
          sum(len(v) for v in a.values()) == sum(len(v) for v in b.values()))
    print(f"  comparados {n:,} puntos")
    print(f"  dX: {min(dx):+.3f} a {max(dx):+.3f} ft   (LEEME, magnitud: 24.238 a 24.241)")
    print(f"  dY: {min(dy):+.3f} a {max(dy):+.3f} ft   (LEEME, magnitud: 7.061 a 7.065)")
    # El LEEME mezcla los signos: la tabla da MAESTRO-GEO_REVIT positivo y la linea
    # de "verificado punto a punto" lo da negativo. Se comparan magnitudes.
    check("|dX| coincide con lo documentado",
          abs(abs(min(dx)) - 24.238) < 0.01 and abs(abs(max(dx)) - 24.241) < 0.01)
    check("|dY| coincide con lo documentado",
          abs(abs(min(dy)) - 7.061) < 0.01 and abs(abs(max(dy)) - 7.065) < 0.01)
    # contraste independiente: la diferencia de los origenes de georreferenciacion
    check("|dX| coincide con la tabla de georreferenciacion (12,119,000 - 12,118,975.762)",
          abs(abs(sum(dx) / len(dx)) - 24.238) < 0.005,
          f"medio {sum(dx) / len(dx):+.4f} ft")
    # el desfase debe ser una traslacion, no una escala: rango acotado
    check("el desfase es traslacion pura (no escala)",
          (max(dx) - min(dx)) < 0.01 and (max(dy) - min(dy)) < 0.01,
          f"dispersion dX {max(dx) - min(dx):.4f} / dY {max(dy) - min(dy):.4f} ft")


if __name__ == "__main__":
    carpetas = sys.argv[1:] or ["MAESTRO", "GEO_REVIT"]
    datos = {}
    for c in carpetas:
        datos[c], _ = analizar(c)
    if "MAESTRO" in datos and "GEO_REVIT" in datos:
        comparar(datos["MAESTRO"], datos["GEO_REVIT"])
    print(f"\n{ok} OK / {fail} fallas")
    sys.exit(1 if fail else 0)
