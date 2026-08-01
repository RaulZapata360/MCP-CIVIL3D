#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Recorta una superficie TIN de LandXML con un perimetro cerrado de un DXF y
entrega el area interior (2D en planta y 3D real), un plano SVG de verificacion
y, opcionalmente, el LandXML de la superficie cortada y el DXF del contorno.

Uso tipico:
    python recortar_superficie.py --xml superficie.xml --dxf perimetro.dxf --todo

Dependencias: ezdxf, shapely. El SVG se escribe a mano (no requiere matplotlib).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

try:
    import ezdxf
    from ezdxf.math import bulge_to_arc
    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union
except ImportError as exc:                                    # pragma: no cover
    sys.exit(f"Falta una dependencia: {exc}. Instala con: pip install ezdxf shapely")

# El plano de verificacion lo dibuja la skill de reportes (skills/reportes).
_REPORTES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "reportes", "scripts")
sys.path.insert(0, os.path.normpath(_REPORTES))
try:
    from plano_svg import PlanoSVG
except ImportError:                                           # pragma: no cover
    sys.exit(f"No se encontro plano_svg.py en {os.path.normpath(_REPORTES)}. "
             f"Esta herramienta usa la skill de reportes para dibujar el SVG.")

NS = {"lx": "http://www.landxml.org/schema/LandXML-1.2"}

# LandXML declara la unidad lineal; de ahi salen las etiquetas y conversiones.
LINEAL_A_METRO = {
    "meter": 1.0,
    "metre": 1.0,
    "centimeter": 0.01,
    "millimeter": 0.001,
    "kilometer": 1000.0,
    "ussurveyfoot": 1200.0 / 3937.0,          # 0.30480060960122
    "foot": 0.3048,
    "internationalfoot": 0.3048,
    "inch": 0.0254,
}


# --------------------------------------------------------------- utilidades ---
def aviso(msg: str) -> None:
    print(f"  [!] {msg}")


def fmt(v: float, dec: int = 3) -> str:
    return f"{v:,.{dec}f}"


# ----------------------------------------------------------------- LandXML ----
def leer_landxml(ruta: str, nombre_superficie: str | None):
    """Devuelve (nombre, triangulos, meta, unidad). Triangulos como ((E,N,Z)x3)."""
    root = ET.parse(ruta).getroot()

    unidades = root.find("lx:Units", NS)
    lineal, sistema = "meter", "Metric"
    if unidades is not None and len(unidades):
        u = unidades[0]
        sistema = u.tag.split("}")[-1]
        lineal = u.get("linearUnit", "meter")
    factor = LINEAL_A_METRO.get(lineal.lower())
    if factor is None:
        aviso(f"unidad lineal '{lineal}' desconocida; se asume metro para las conversiones")
        factor = 1.0
    unidad = {"sistema": sistema, "lineal": lineal, "a_metro": factor,
              "etiqueta": "ft2" if factor < 0.9 else "m2",
              "etiqueta_lin": "ft" if factor < 0.9 else "m"}

    superficies = root.findall(".//lx:Surface", NS)
    if not superficies:
        sys.exit("El LandXML no contiene ninguna <Surface>.")
    if nombre_superficie:
        elegidas = [s for s in superficies if s.get("name") == nombre_superficie]
        if not elegidas:
            disponibles = ", ".join(repr(s.get("name")) for s in superficies)
            sys.exit(f"No existe la superficie {nombre_superficie!r}. Disponibles: {disponibles}")
        surf = elegidas[0]
    elif len(superficies) == 1:
        surf = superficies[0]
    else:
        disponibles = ", ".join(repr(s.get("name")) for s in superficies)
        sys.exit(f"El archivo tiene {len(superficies)} superficies: {disponibles}\n"
                 f"Indica cual con --superficie.")

    defin = surf.find("lx:Definition", NS)
    meta = {k: defin.get(k) for k in ("surfType", "area2DSurf", "area3DSurf",
                                      "elevMax", "elevMin")}

    # LandXML: el texto de <P> es "norte este cota".
    pts = {}
    for p in defin.find("lx:Pnts", NS):
        n, e, z = (float(v) for v in p.text.split())
        pts[p.get("id")] = (e, n, z)

    # i="1" marca la cara como invisible: son las que Civil 3D descarta por
    # contorno. Si no se excluyen, el area no calza con la del dibujo.
    tris, invisibles = [], 0
    for f in defin.find("lx:Faces", NS):
        if f.get("i") == "1":
            invisibles += 1
            continue
        a, b, c = f.text.split()
        tris.append((pts[a], pts[b], pts[c]))

    meta["n_puntos"] = len(pts)
    meta["n_caras_visibles"] = len(tris)
    meta["n_caras_invisibles"] = invisibles
    return surf.get("name"), tris, meta, unidad


# --------------------------------------------------------------------- DXF ----
def teselar(vertices, cerrada: bool, sagitta: float):
    """Convierte [(x, y, bulge)] en lista de puntos (x, y) muestreando los arcos.

    Los puntos se toman sobre la circunferencia real. No se usa
    ezdxf.path.make_path().flattening(): ese camino aproxima el arco con curvas
    Bezier que quedan ~0.03% por fuera, y afinar la sagitta converge a la Bezier,
    no al arco (en un circulo de radio 50 son ~2 m2 de error que no bajan nunca).
    """
    pts = []
    n = len(vertices)
    tramos = range(n) if cerrada else range(n - 1)
    for i in tramos:
        x0, y0, b = vertices[i]
        x1, y1, _ = vertices[(i + 1) % n]
        pts.append((x0, y0))
        if abs(b) <= 1e-12 or math.dist((x0, y0), (x1, y1)) < 1e-12:
            continue
        centro, _, _, radio = bulge_to_arc((x0, y0), (x1, y1), b)
        if radio <= 0:
            continue
        barrido = 4.0 * math.atan(b)                  # signo: + antihorario
        # paso angular tal que la flecha del tramo no supere la sagitta pedida
        paso = 2.0 * math.acos(max(-1.0, min(1.0, 1.0 - min(sagitta / radio, 1.0))))
        nseg = min(4096, max(2, int(math.ceil(abs(barrido) / max(paso, 1e-9)))))
        a0 = math.atan2(y0 - centro.y, x0 - centro.x)
        for k in range(1, nseg):
            a = a0 + barrido * k / nseg
            pts.append((centro.x + radio * math.cos(a), centro.y + radio * math.sin(a)))
    if not cerrada:
        pts.append((vertices[-1][0], vertices[-1][1]))
    return pts


def leer_perimetro(ruta: str, capa: str | None, handle: str | None,
                   unir_todas: bool, sagitta: float):
    """Devuelve (poligono shapely, descripcion). Tesela los arcos (bulges)."""
    doc = ezdxf.readfile(ruta)
    msp = doc.modelspace()

    cands = []
    for e in msp:
        t = e.dxftype()
        if t == "LWPOLYLINE":
            cerrada = bool(e.closed)
            verts = [(p[0], p[1], p[4]) for p in e.get_points("xyseb")]
        elif t == "POLYLINE" and not e.is_poly_face_mesh and not e.is_polygon_mesh:
            cerrada = bool(e.is_closed)
            verts = [(v.dxf.location.x, v.dxf.location.y,
                      v.dxf.bulge if v.dxf.hasattr("bulge") else 0.0)
                     for v in e.vertices]
        else:
            continue
        if capa and e.dxf.layer != capa:
            continue
        if handle and e.dxf.handle.upper() != handle.upper():
            continue
        if len(verts) < 2:
            continue
        arcos = any(abs(v[2]) > 1e-12 for v in verts)
        pts = teselar(verts, cerrada, sagitta)
        if len(pts) >= 3:
            cands.append((e, pts, cerrada, arcos))

    if not cands:
        filtro = f" (capa={capa!r}, handle={handle!r})" if capa or handle else ""
        sys.exit(f"No se encontro ninguna polilinea utilizable en el DXF{filtro}.")

    if len(cands) > 1 and not unir_todas:
        detalle = "\n".join(
            f"    handle {e.dxf.handle}  capa {e.dxf.layer}  "
            f"{len(p)} vertices  cerrada={'si' if c else 'no'}"
            for e, p, c, _ in cands)
        sys.exit(f"El DXF tiene {len(cands)} polilineas candidatas:\n{detalle}\n"
                 f"Elige una con --capa o --handle, o unelas todas con --unir-todas.")

    polis, desc = [], []
    for e, pts, cerrada, arcos in cands:
        if math.dist(pts[0], pts[-1]) < 1e-9:
            pts = pts[:-1]
        elif not cerrada:
            hueco = math.dist(pts[0], pts[-1])
            aviso(f"polilinea {e.dxf.handle} abierta (separacion {hueco:.4f}); se cierra sola")
        poly = Polygon(pts)
        if not poly.is_valid:
            aviso(f"polilinea {e.dxf.handle} auto-intersectada; se corrige con buffer(0)")
            poly = poly.buffer(0)
            if poly.is_empty:
                sys.exit(f"La polilinea {e.dxf.handle} no define un area valida.")
        polis.append(poly)
        desc.append({"handle": e.dxf.handle, "capa": e.dxf.layer,
                     "vertices": len(pts), "cerrada_en_dxf": cerrada, "arcos": arcos})

    return unary_union(polis), desc


# ------------------------------------------------------------- geometria 3D ---
def razon_3d(t) -> float:
    """area3D/area2D del triangulo. Constante en todo su plano."""
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = t
    ux, uy, uz = x2 - x1, y2 - y1, z2 - z1
    vx, vy, vz = x3 - x1, y3 - y1, z3 - z1
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    return math.sqrt(nx * nx + ny * ny + nz * nz) / abs(nz) if nz else float("inf")


def cota_en_plano(t, x, y) -> float:
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = t
    den = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    l1 = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / den
    l2 = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / den
    return l1 * z1 + l2 * z2 + (1 - l1 - l2) * z3


def triangular(anillo):
    """Triangula un anillo simple (sin huecos). Abanico si es convexo, si no ear clipping."""
    n = len(anillo)
    if n < 3:
        return []
    if n == 3:
        return [(0, 1, 2)]
    if Polygon(anillo).equals(Polygon(anillo).convex_hull):
        return [(0, i, i + 1) for i in range(1, n - 1)]

    def area2(a, b, c):
        return ((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

    idx = list(range(n))
    if sum(anillo[i][0] * anillo[(i + 1) % n][1] - anillo[(i + 1) % n][0] * anillo[i][1]
           for i in range(n)) < 0:
        idx.reverse()                                   # trabajar siempre en CCW
    orejas, guardia = [], 0
    while len(idx) > 3 and guardia < 10 * n:
        guardia += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = anillo[i0], anillo[i1], anillo[i2]
            if area2(a, b, c) <= 1e-12:
                continue
            tri = Polygon([a, b, c])
            if any(tri.contains(Point(anillo[j])) for j in idx if j not in (i0, i1, i2)):
                continue
            orejas.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        orejas.append(tuple(idx))
    return orejas


# ------------------------------------------------------------------- recorte ---
def recortar(tris, corte):
    total2d = total3d = int2d = int3d = 0.0
    piezas, tocados, parciales = [], 0, 0
    for t in tris:
        tp = Polygon([(p[0], p[1]) for p in t])
        if tp.area <= 0:
            continue
        r = razon_3d(t)
        total2d += tp.area
        total3d += tp.area * r
        if not tp.intersects(corte):
            continue
        inter = tp.intersection(corte)
        if inter.is_empty or inter.area <= 0:
            continue
        tocados += 1
        if inter.area < tp.area - 1e-9:
            parciales += 1
        int2d += inter.area
        int3d += inter.area * r
        for g in getattr(inter, "geoms", [inter]):
            if g.geom_type == "Polygon" and g.area > 0:
                piezas.append((g, t))
    return dict(total2d=total2d, total3d=total3d, int2d=int2d, int3d=int3d,
                piezas=piezas, tocados=tocados, parciales=parciales)


# ----------------------------------------------------------------------- SVG ---
def escribir_svg(ruta, nombre, tris, piezas, corte, res, unidad, tema="claro",
                 ancho=1200, alto=900):
    """Arma el plano de verificacion con el sistema de reportes (plano_svg)."""
    a2, a3 = res["int2d"], res["int3d"]
    ue = unidad["etiqueta"]
    cob = 100.0 * a2 / corte.area if corte.area else 0.0
    p = PlanoSVG(titulo=f"{nombre} — recorte con perimetro DXF",
                 subtitulo=f"Area interior 2D {fmt(a2)} {ue} "
                           f"({fmt(a2 * unidad['a_metro'] ** 2)} m2)  ·  "
                           f"3D {fmt(a3)} {ue}  ·  relacion 3D/2D {a3 / a2:.6f}",
                 unidad_lin=unidad["etiqueta_lin"], ancho=ancho, alto=alto, tema=tema)
    p.nota(f"Perimetro de corte {fmt(corte.area)} {ue}; {cob:.1f}% cae sobre la superficie"
           + ("" if cob >= 99.9 else " — el resto queda fuera del TIN"))
    p.poligonos([[(q[0], q[1]) for q in t] for t in tris], rol="contexto",
                etiqueta=f"TIN original ({len(tris)} triangulos)")
    p.poligonos([list(g.exterior.coords)[:-1] for g, _ in piezas], rol="serie1",
                etiqueta=f"Area interior ({fmt(a2)} {ue})")
    p.lineas([list(a.coords)[:-1] for a in [corte.exterior] + list(corte.interiors)],
             rol="serie2", etiqueta="Perimetro de corte", cerrar=True)
    vertices = list(corte.exterior.coords)[:-1]
    p.puntos(vertices, rol="serie2",
             rotulos=[f"V{i}" for i in range(1, len(vertices) + 1)])
    p.guardar(ruta)


# ------------------------------------------------------------ salidas extra ---
def escribir_landxml(ruta, nombre, piezas, res, unidad):
    puntos, indice, caras, con_huecos = [], {}, [], 0
    for g, t in piezas:
        if g.interiors:
            con_huecos += 1
            continue
        anillo = list(g.exterior.coords)[:-1]
        ids = []
        for x, y in anillo:
            clave = (round(x, 6), round(y, 6))
            if clave not in indice:
                indice[clave] = len(puntos) + 1
                puntos.append((x, y, cota_en_plano(t, x, y)))
            ids.append(indice[clave])
        for i0, i1, i2 in triangular(anillo):
            caras.append((ids[i0], ids[i1], ids[i2]))
    if con_huecos:
        aviso(f"{con_huecos} piezas con huecos internos se omitieron del LandXML "
              f"(no afectan el area informada)")

    zs = [p[2] for p in puntos] or [0.0]
    imperial = unidad["a_metro"] < 0.9
    um = ('\t\t<Imperial areaUnit="squareFoot" linearUnit="%s" volumeUnit="cubicYard" '
          'temperatureUnit="fahrenheit" pressureUnit="inchHG" diameterUnit="inch" '
          'angularUnit="decimal degrees" directionUnit="decimal degrees"></Imperial>'
          % unidad["lineal"]) if imperial else (
          '\t\t<Metric areaUnit="squareMeter" linearUnit="meter" volumeUnit="cubicMeter" '
          'temperatureUnit="celsius" pressureUnit="milliBars" diameterUnit="millimeter" '
          'angularUnit="decimal degrees" directionUnit="decimal degrees"></Metric>')

    L = ['<?xml version="1.0"?>',
         '<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" '
         'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xsi:schemaLocation="http://www.landxml.org/schema/LandXML-1.2 '
         'http://www.landxml.org/schema/LandXML-1.2/LandXML-1.2.xsd" '
         'version="1.2" language="English">',
         '\t<Units>', um, '\t</Units>', '\t<Surfaces>',
         f'\t\t<Surface name="{nombre} - Cortada" desc="Recorte con perimetro DXF">',
         f'\t\t\t<Definition surfType="TIN" area2DSurf="{res["int2d"]:.9f}" '
         f'area3DSurf="{res["int3d"]:.9f}" elevMax="{max(zs):.4f}" '
         f'elevMin="{min(zs):.4f}">', '\t\t\t\t<Pnts>']
    L += [f'\t\t\t\t\t<P id="{i}">{y:.9f} {x:.9f} {z:.6f}</P>'
          for i, (x, y, z) in enumerate(puntos, 1)]
    L += ['\t\t\t\t</Pnts>', '\t\t\t\t<Faces>']
    L += [f'\t\t\t\t\t<F>{a} {b} {c}</F>' for a, b, c in caras]
    L += ['\t\t\t\t</Faces>', '\t\t\t</Definition>', '\t\t</Surface>',
          '\t</Surfaces>', '</LandXML>']
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    return len(puntos), len(caras)


def escribir_dxf_borde(ruta, piezas, corte, tris):
    region = unary_union([g for g, _ in piezas]).simplify(0)
    doc = ezdxf.new("R2018", setup=True)
    msp = doc.modelspace()
    for capa, color in (("CORTE-AREA-INTERIOR-2D", 30), ("CORTE-AREA-INTERIOR-3D", 5),
                        ("CORTE-POLIGONO-ORIGINAL", 1)):
        doc.layers.add(capa, color=color)

    def cota(x, y):
        for t in tris:
            if Polygon([(p[0], p[1]) for p in t]).buffer(1e-7).covers(Point(x, y)):
                return cota_en_plano(t, x, y)
        return 0.0

    n_anillos = 0
    for parte in getattr(region, "geoms", [region]):
        for anillo in [parte.exterior] + list(parte.interiors):
            pts = list(anillo.coords)[:-1]
            msp.add_lwpolyline(pts, close=True,
                               dxfattribs={"layer": "CORTE-AREA-INTERIOR-2D"})
            p3 = [(x, y, cota(x, y)) for x, y in pts]
            msp.add_polyline3d(p3 + [p3[0]],
                               dxfattribs={"layer": "CORTE-AREA-INTERIOR-3D"})
            n_anillos += 1
    for anillo in [corte.exterior] + list(corte.interiors):
        msp.add_lwpolyline(list(anillo.coords)[:-1], close=True,
                           dxfattribs={"layer": "CORTE-POLIGONO-ORIGINAL"})
    doc.saveas(ruta)
    return n_anillos, region


# ---------------------------------------------------------------------- main ---
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Recorta una superficie TIN de LandXML con un perimetro DXF.")
    ap.add_argument("--xml", required=True, help="LandXML con la superficie")
    ap.add_argument("--dxf", required=True, help="DXF con la polilinea de corte")
    ap.add_argument("--superficie", help="nombre de la superficie (si el XML trae varias)")
    ap.add_argument("--capa", help="filtrar la polilinea por capa")
    ap.add_argument("--handle", help="filtrar la polilinea por handle")
    ap.add_argument("--unir-todas", action="store_true",
                    help="unir todas las polilineas del DXF en un solo perimetro")
    ap.add_argument("--sagitta", type=float, default=0.001,
                    help="flecha maxima al teselar arcos, en unidades del dibujo "
                         "(el error de area baja proporcionalmente; 0.001 es ~0.003%% "
                         "en un circulo de radio 50)")
    ap.add_argument("--salida", help="carpeta de salida (por defecto, la del DXF)")
    ap.add_argument("--prefijo", default="corte", help="prefijo de los archivos generados")
    ap.add_argument("--landxml-salida", action="store_true",
                    help="exportar el LandXML de la superficie cortada")
    ap.add_argument("--dxf-borde", action="store_true",
                    help="exportar el contorno del area interior a DXF (2D y 3D)")
    ap.add_argument("--sin-svg", action="store_true", help="no generar el SVG")
    ap.add_argument("--tema", default="claro", choices=("claro", "oscuro"),
                    help="tema del plano de verificacion")
    ap.add_argument("--json", help="volcar los resultados a un archivo JSON")
    ap.add_argument("--todo", action="store_true", help="generar todas las salidas")
    args = ap.parse_args()

    if args.todo:
        args.landxml_salida = args.dxf_borde = True

    destino = args.salida or os.path.dirname(os.path.abspath(args.dxf))
    os.makedirs(destino, exist_ok=True)

    nombre, tris, meta, unidad = leer_landxml(args.xml, args.superficie)
    ue, ul = unidad["etiqueta"], unidad["etiqueta_lin"]
    print(f"Superficie: {nombre}  ({meta['surfType']}, {unidad['sistema']}/{unidad['lineal']})")
    print(f"  puntos {meta['n_puntos']} | caras visibles {meta['n_caras_visibles']} "
          f"| descartadas por invisibles {meta['n_caras_invisibles']}")

    corte, desc = leer_perimetro(args.dxf, args.capa, args.handle,
                                 args.unir_todas, args.sagitta)
    for dd in desc:
        print(f"  perimetro: handle {dd['handle']} capa {dd['capa']} "
              f"{dd['vertices']} vertices{' (con arcos teselados)' if dd['arcos'] else ''}")
    print(f"  area del poligono de corte: {fmt(corte.area)} {ue}")

    # Chequeo de orden N/E: si el TIN y el perimetro no se tocan pero si lo harian
    # al invertir norte/este, el problema es el orden de coordenadas, no el corte.
    tin_bbox = unary_union([Polygon([(p[0], p[1]) for p in t]) for t in tris]).bounds
    cb = corte.bounds
    solapa = not (tin_bbox[2] < cb[0] or cb[2] < tin_bbox[0] or
                  tin_bbox[3] < cb[1] or cb[3] < tin_bbox[1])
    if not solapa:
        inv = not (tin_bbox[3] < cb[0] or cb[2] < tin_bbox[1] or
                   tin_bbox[2] < cb[1] or cb[3] < tin_bbox[0])
        aviso("el perimetro y la superficie no se superponen." +
              (" Al invertir norte/este si lo harian: revisa el orden de coordenadas "
               "del LandXML o el sistema del DXF." if inv else
               " Verifica que ambos esten en el mismo sistema de coordenadas."))

    res = recortar(tris, corte)

    dec = float(meta["area2DSurf"] or 0), float(meta["area3DSurf"] or 0)
    print(f"\nControl del TIN completo ({ue}):")
    print(f"  area 2D declarada {fmt(dec[0])} | recalculada {fmt(res['total2d'])} "
          f"| dif {abs(dec[0] - res['total2d']):.6f}")
    print(f"  area 3D declarada {fmt(dec[1])} | recalculada {fmt(res['total3d'])} "
          f"| dif {abs(dec[1] - res['total3d']):.6f}")
    if dec[0] and abs(dec[0] - res["total2d"]) > max(1e-4, dec[0] * 1e-9):
        aviso("el area recalculada no calza con la declarada en el LandXML")

    a2, a3 = res["int2d"], res["int3d"]
    if a2 <= 0:
        aviso("el perimetro no intersecta la superficie: area interior = 0")
        return 1

    f2 = unidad["a_metro"] ** 2
    cob = 100.0 * a2 / corte.area if corte.area else 0.0
    region = unary_union([g for g, _ in res["piezas"]])
    partes = list(getattr(region, "geoms", [region]))
    zs = [cota_en_plano(t, x, y) for g, t in res["piezas"]
          for x, y in list(g.exterior.coords)[:-1]]

    print(f"\nRecorte: {res['tocados']} triangulos intervienen "
          f"({res['parciales']} cortados parcialmente)")
    print(f"  cobertura del poligono sobre el TIN: {cob:.4f}%  "
          f"(fuera: {fmt(corte.area - a2)} {ue})")
    if cob < 99.9:
        aviso("el perimetro se sale de la superficie: el area entregada es la "
              "superficie existente dentro del perimetro, no el area del perimetro")
    print(f"  regiones resultantes: {len(partes)} | huecos: "
          f"{[len(p.interiors) for p in partes]}")
    print(f"  cotas dentro del corte: {min(zs):.4f} a {max(zs):.4f} {ul}")

    print(f"\n=== AREA INTERIOR ===")
    print(f"  2D (planta) : {fmt(a2)} {ue} = {fmt(a2 * f2)} m2 = {a2 * f2 / 1e4:,.5f} ha")
    print(f"  3D (real)   : {fmt(a3)} {ue} = {fmt(a3 * f2)} m2 = {a3 * f2 / 1e4:,.5f} ha")
    if unidad["a_metro"] < 0.9:
        print(f"  en acres    : 2D {a2 / 43560.0:,.5f} ac | 3D {a3 / 43560.0:,.5f} ac")
    print(f"  relacion 3D/2D: {a3 / a2:.6f}")

    generados = {}
    base = os.path.join(destino, args.prefijo)
    if not args.sin_svg:
        ruta = base + "_verificacion.svg"
        escribir_svg(ruta, nombre, tris, res["piezas"], corte, res, unidad, args.tema)
        generados["svg"] = ruta
    if args.landxml_salida:
        ruta = base + "_superficie_cortada.xml"
        np_, nc_ = escribir_landxml(ruta, nombre, res["piezas"], res, unidad)
        generados["landxml"] = ruta
        print(f"\nLandXML cortado: {np_} puntos / {nc_} triangulos")
    if args.dxf_borde:
        ruta = base + "_borde_interior.dxf"
        n_anillos, reg = escribir_dxf_borde(ruta, res["piezas"], corte, tris)
        generados["dxf"] = ruta
        if abs(reg.area - a2) > 1e-6:
            aviso(f"el contorno exportado difiere del area calculada en "
                  f"{abs(reg.area - a2):.6f} {ue}")
        print(f"Contorno DXF: {n_anillos} anillo(s), area {fmt(reg.area)} {ue}")

    if generados:
        print("\nArchivos generados:")
        for k, v in generados.items():
            print(f"  {k:8s} {v}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"superficie": nombre, "unidad": unidad,
                       "area_interior_2d": a2, "area_interior_3d": a3,
                       "area_interior_2d_m2": a2 * f2, "area_interior_3d_m2": a3 * f2,
                       "area_poligono": corte.area, "cobertura_pct": cob,
                       "area_total_2d": res["total2d"], "area_total_3d": res["total3d"],
                       "cota_min": min(zs), "cota_max": max(zs),
                       "triangulos_intervienen": res["tocados"],
                       "triangulos_parciales": res["parciales"],
                       "regiones": len(partes), "archivos": generados},
                      fh, indent=2, ensure_ascii=False)
        print(f"  json     {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
