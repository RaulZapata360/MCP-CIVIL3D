#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Informe HTML autocontenido de analisis de una o dos superficies TIN (LandXML).

Genera un unico archivo .html (sin dependencias externas en el navegador:
SVG incrustado inline, CSS embebido) con:

    * Ficha de identificacion y resumen numerico (area, cotas, pendiente media).
    * Zonificacion de cotas (banda hipsometrica): tabla + plano en planta con
      rampa de color + grafico de barras de area por banda.
    * Zonificacion de pendientes: tabla + plano coloreado + barras.
    * Analisis de orientacion (aspecto): rosa de orientacion + tabla.
    * Perfil longitudinal y secciones transversales a lo largo de un eje
      (opcional, requiere un DXF con la polilinea del eje).
    * Computo volumetrico corte/relleno entre dos superficies (opcional,
      requiere una segunda superficie de diseño), por muestreo en grilla.
    * Hallazgos y recomendaciones automaticas.

No requiere Civil 3D abierto. Solo necesita `ezdxf` si se usa `--eje-dxf`
(perfiles / secciones); el resto funciona con la libreria estandar.

Uso tipico:
    python informe_superficie.py --xml existente.xml --salida informe.html

    python informe_superficie.py --xml existente.xml --xml-disenio disenio.xml \\
        --eje-dxf eje.dxf --transectos --salida informe.html --json informe.json
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime

_REPORTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reportes", "scripts")
_GEOMETRIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "geometria", "scripts")
sys.path.insert(0, os.path.normpath(_REPORTES))
sys.path.insert(0, os.path.normpath(_GEOMETRIA))
from plano_svg import PlanoSVG, paso_redondo  # noqa: E402
from graficos_svg import grafico_barras, grafico_rosa, grafico_perfil  # noqa: E402

NS = {"lx": "http://www.landxml.org/schema/LandXML-1.2"}

# LandXML declara la unidad lineal; de ahi salen las etiquetas y conversiones
# (misma tabla que `recortar_superficie.py`, duplicada a proposito para que
# este script funcione sin depender de shapely/ezdxf salvo que se pidan
# perfiles/transectos).
LINEAL_A_METRO = {
    "meter": 1.0,
    "metre": 1.0,
    "centimeter": 0.01,
    "millimeter": 0.001,
    "kilometer": 1000.0,
    "ussurveyfoot": 1200.0 / 3937.0,
    "foot": 0.3048,
    "internationalfoot": 0.3048,
    "inch": 0.0254,
}

UMBRAL_PENDIENTE_PLANA = 0.5  # % -- por debajo de esto la orientacion no es fiable


def aviso(msg: str) -> None:
    print(f"  [!] {msg}")


def fmt(v: float, dec: int = 2) -> str:
    return f"{v:,.{dec}f}"


# ------------------------------------------------------------------ LandXML --
def leer_landxml(ruta: str, nombre: str | None = None):
    """Devuelve (nombre, triangulos [(E,N,Z)x3], meta, unidad)."""
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No existe el archivo {ruta}")
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
        raise ValueError("El LandXML no contiene ninguna <Surface>.")
    if nombre:
        elegidas = [s for s in superficies if s.get("name") == nombre]
        if not elegidas:
            disponibles = ", ".join(repr(s.get("name")) for s in superficies)
            raise ValueError(f"No existe la superficie {nombre!r}. Disponibles: {disponibles}")
        surf = elegidas[0]
    elif len(superficies) == 1:
        surf = superficies[0]
    else:
        disponibles = ", ".join(repr(s.get("name")) for s in superficies)
        raise ValueError(f"El archivo tiene {len(superficies)} superficies: {disponibles}. "
                          f"Indica cual con --superficie / --superficie-disenio.")

    defin = surf.find("lx:Definition", NS)
    meta = {k: defin.get(k) for k in ("surfType", "area2DSurf", "area3DSurf", "elevMax", "elevMin")}

    pts = {}
    for p in defin.find("lx:Pnts", NS):
        n, e, z = (float(v) for v in p.text.split())
        pts[p.get("id")] = (e, n, z)          # LandXML: texto es "norte este cota"

    tris, invisibles = [], 0
    for f in defin.find("lx:Faces", NS):
        if f.get("i") == "1":                  # cara invisible: descartada por contorno
            invisibles += 1
            continue
        a, b, c = f.text.split()
        tris.append((pts[a], pts[b], pts[c]))

    if not tris:
        raise ValueError(f"La superficie {surf.get('name')!r} no tiene caras visibles.")

    meta["n_puntos"] = len(pts)
    meta["n_caras_visibles"] = len(tris)
    meta["n_caras_invisibles"] = invisibles
    return surf.get("name", "Sin nombre"), tris, meta, unidad


# --------------------------------------------------------------- geometria --
def area2d(t) -> float:
    (x1, y1, _), (x2, y2, _), (x3, y3, _) = t
    return abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2.0


def _normal(t):
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = t
    ux, uy, uz = x2 - x1, y2 - y1, z2 - z1
    vx, vy, vz = x3 - x1, y3 - y1, z3 - z1
    return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)


def razon_3d(t) -> float:
    """area3D/area2D del triangulo (constante en todo su plano)."""
    a, b, c = _normal(t)
    return math.sqrt(a * a + b * b + c * c) / abs(c) if c else float("inf")


def pendiente_pct(t) -> float:
    a, b, c = _normal(t)
    if c == 0:
        return float("inf")
    return 100.0 * math.sqrt(a * a + b * b) / abs(c)


def orientacion_deg(t) -> float:
    """Direccion de maxima pendiente descendente, grados desde el norte, horario.

    Del plano a*E + b*N + c*Z + d = 0 (Z=-(aE+bN+d)/c), el gradiente en (E,N)
    es (-a/c, -b/c); la direccion de descenso es su opuesto: (a/c, b/c). Esta
    formula es invariante ante un giro de 180 grados del vector normal (a,b,c
    y -a,-b,-c dan el mismo plano), asi que no importa el orden de los
    vertices del triangulo. Verificado con un plano inclinado analitico en
    `test_informe_superficie.py`.
    """
    a, b, c = _normal(t)
    if c == 0:
        return 0.0
    dE, dN = a / c, b / c
    return math.degrees(math.atan2(dE, dN)) % 360.0


def cota_media(t) -> float:
    return sum(p[2] for p in t) / 3.0


# ------------------------------------------------------------- zonificacion --
def bandas_desde_cortes(cortes: list[float]) -> list[tuple[float, float]]:
    cortes = sorted(cortes)
    bandas = [(cortes[i], cortes[i + 1]) for i in range(len(cortes) - 1)]
    bandas.append((cortes[-1], math.inf))
    return bandas


def resolver_bandas(spec: str | None, vmin: float, vmax: float) -> list[tuple[float, float]]:
    """spec = entero (N bandas de ancho igual) o lista separada por comas (cortes)."""
    if spec is None:
        spec = "6"
    spec = str(spec).strip()
    if "," in spec:
        return bandas_desde_cortes([float(x) for x in spec.split(",")])
    n = max(1, int(spec))
    paso = (vmax - vmin) / n if vmax > vmin else 1.0
    return [(vmin + i * paso, vmin + (i + 1) * paso) for i in range(n)]


def etiqueta_banda(lo: float, hi: float, unidad_txt: str = "", dec: int = 1) -> str:
    if math.isinf(hi):
        return f"> {lo:,.{dec}f}{unidad_txt}"
    if math.isinf(lo):
        return f"< {hi:,.{dec}f}{unidad_txt}"
    return f"{lo:,.{dec}f} - {hi:,.{dec}f}{unidad_txt}"


def zonificar(tris, valor_fn, bandas: list[tuple[float, float]]):
    """Asigna cada triangulo a la primera banda [lo, hi) que lo contiene.

    Las bandas deben venir ordenadas y contiguas; la ultima captura todo lo
    que quede (tipicamente hi=inf). Invariante verificado en tests: la suma
    de area2d de todas las bandas es igual al area2d total.
    """
    zonas = [{"min": lo, "max": hi, "area2d": 0.0, "area3d": 0.0, "n_triangulos": 0}
             for lo, hi in bandas]
    ultimo = len(bandas) - 1
    for t in tris:
        v = valor_fn(t)
        idx = ultimo
        for i, (_, hi) in enumerate(bandas):
            if v < hi:
                idx = i
                break
        a = area2d(t)
        zonas[idx]["area2d"] += a
        zonas[idx]["area3d"] += a * razon_3d(t)
        zonas[idx]["n_triangulos"] += 1
    return zonas


_CARDINALES = {
    4: ["N", "E", "S", "O"],
    8: ["N", "NE", "E", "SE", "S", "SO", "O", "NO"],
    16: ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
         "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"],
}


def nombres_sectores(n_sectores: int) -> list[str] | None:
    """Nombres cardinales para conteos de sector habituales (4/8/16); None si
    no hay una convencion estandar para ese numero (se usan rangos en grados)."""
    return _CARDINALES.get(n_sectores)


def rosa_orientacion(tris, n_sectores: int = 8):
    """Area por sector de orientacion (aspecto). Triangulos casi planos se
    excluyen: su direccion de descenso no es representativa (ruido de
    redondeo, no terreno real)."""
    ancho = 360.0 / n_sectores
    valores = [0.0] * n_sectores
    excluidos = 0
    for t in tris:
        if pendiente_pct(t) < UMBRAL_PENDIENTE_PLANA:
            excluidos += 1
            continue
        deg = orientacion_deg(t)
        idx = int(((deg + ancho / 2) % 360) // ancho)
        valores[idx] += area2d(t)
    centros = [i * ancho for i in range(n_sectores)]
    return centros, valores, excluidos


# ------------------------------------------------------------- estadisticas --
def calcular_estadisticas(tris, meta) -> dict:
    a2 = sum(area2d(t) for t in tris)
    a3 = sum(area2d(t) * razon_3d(t) for t in tris)
    zs = [p[2] for t in tris for p in t]
    pends = [pendiente_pct(t) for t in tris]
    zmed = sum(area2d(t) * cota_media(t) for t in tris) / a2 if a2 else 0.0
    pmed = sum(a * p for a, p in zip((area2d(t) for t in tris), pends)) / a2 if a2 else 0.0
    return {
        "area2d": a2, "area3d": a3,
        "cota_min": min(zs), "cota_max": max(zs), "cota_media_ponderada": zmed,
        "pendiente_media_ponderada": pmed, "pendiente_max": max(pends) if pends else 0.0,
        "n_puntos": meta.get("n_puntos", 0), "n_triangulos": len(tris),
        "n_caras_invisibles": meta.get("n_caras_invisibles", 0),
        "area2d_declarada": float(meta["area2DSurf"]) if meta.get("area2DSurf") else None,
        "area3d_declarada": float(meta["area3DSurf"]) if meta.get("area3DSurf") else None,
    }


# --------------------------------------------------------- indice espacial --
def indice_espacial(tris, celda: float):
    """Bucket grid de bounding-boxes de triangulos, sin dependencias externas.

    Sustituye a un R-tree para el volumen de datos tipico de un TIN de obra:
    la busqueda de un punto solo revisa la celda y sus 8 vecinas.
    """
    idx = defaultdict(list)
    celda = max(celda, 1e-6)
    for t in tris:
        xs = [p[0] for p in t]
        ys = [p[1] for p in t]
        i0, i1 = int(math.floor(min(xs) / celda)), int(math.floor(max(xs) / celda))
        j0, j1 = int(math.floor(min(ys) / celda)), int(math.floor(max(ys) / celda))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                idx[(i, j)].append(t)
    return idx


def _en_triangulo(t, x: float, y: float):
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = t
    den = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if abs(den) < 1e-12:
        return None
    l1 = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / den
    l2 = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / den
    l3 = 1.0 - l1 - l2
    if l1 < -1e-9 or l2 < -1e-9 or l3 < -1e-9:
        return None
    return l1 * z1 + l2 * z2 + l3 * z3


def cota_en(idx, celda: float, x: float, y: float):
    i, j = int(math.floor(x / celda)), int(math.floor(y / celda))
    for di in (0, -1, 1):
        for dj in (0, -1, 1):
            for t in idx.get((i + di, j + dj), ()):
                z = _en_triangulo(t, x, y)
                if z is not None:
                    return z
    return None


def bbox_tris(tris):
    xs = [p[0] for t in tris for p in t]
    ys = [p[1] for t in tris for p in t]
    return min(xs), min(ys), max(xs), max(ys)


# --------------------------------------------------------------- volumenes --
def volumen_grid(tris_base, tris_disenio, espaciamiento: float) -> dict:
    """Corte/relleno por muestreo en grilla regular sobre el solape de ambas
    superficies. No es el metodo TIN exacto de Civil 3D (que interseca la
    malla completa); es una estimacion por grilla, adecuada para un informe
    de verificacion. Cruzar contra `civil3d_surface_volume_calculate` /
    `civil3d_qty_earthwork_summary` cuando Civil 3D este abierto.
    """
    x0b, y0b, x1b, y1b = bbox_tris(tris_base)
    x0d, y0d, x1d, y1d = bbox_tris(tris_disenio)
    x0, y0 = max(x0b, x0d), max(y0b, y0d)
    x1, y1 = min(x1b, x1d), min(y1b, y1d)
    if x0 >= x1 or y0 >= y1:
        raise ValueError("las superficies no se superponen: no se puede calcular el volumen")

    celda_idx = espaciamiento * 2
    idx_base = indice_espacial(tris_base, celda_idx)
    idx_dis = indice_espacial(tris_disenio, celda_idx)

    nx = max(1, int((x1 - x0) / espaciamiento))
    ny = max(1, int((y1 - y0) / espaciamiento))
    area_celda = espaciamiento * espaciamiento

    corte = relleno = 0.0
    muestras = sin_dato = 0
    for i in range(nx):
        x = x0 + (i + 0.5) * espaciamiento
        for j in range(ny):
            y = y0 + (j + 0.5) * espaciamiento
            zb = cota_en(idx_base, celda_idx, x, y)
            zd = cota_en(idx_dis, celda_idx, x, y)
            if zb is None or zd is None:
                sin_dato += 1
                continue
            muestras += 1
            dz = zd - zb
            if dz < 0:
                corte += -dz * area_celda
            elif dz > 0:
                relleno += dz * area_celda

    total = muestras + sin_dato
    return {
        "corte_volumen": corte, "relleno_volumen": relleno, "neto_volumen": relleno - corte,
        "muestras": muestras, "sin_dato": sin_dato,
        "cobertura_pct": 100.0 * muestras / total if total else 0.0,
        "espaciamiento": espaciamiento, "area_muestreada": muestras * area_celda,
        "bbox_solape": (x0, y0, x1, y1),
    }


# --------------------------------------------------------------------- eje --
def leer_eje_dxf(ruta: str, capa: str | None = None, sagitta: float = 0.001):
    """Lee la primera polilinea del DXF (o de la capa indicada), teselando
    arcos sobre el arco real (no sobre su aproximacion Bezier)."""
    try:
        import ezdxf
    except ImportError as exc:                                     # pragma: no cover
        raise ImportError(f"--eje-dxf requiere ezdxf: {exc}. Instala con: pip install ezdxf") from exc
    from teselar_arcos import teselar_bulge

    doc = ezdxf.readfile(ruta)
    msp = doc.modelspace()
    candidatas = [e for e in msp if e.dxftype() in ("LWPOLYLINE", "POLYLINE")
                  and (capa is None or e.dxf.layer == capa)]
    if not candidatas:
        disponibles = sorted({e.dxf.layer for e in msp if e.dxftype() in ("LWPOLYLINE", "POLYLINE")})
        raise ValueError(f"no se encontro una polilinea de eje en el DXF"
                          f"{' en la capa ' + capa if capa else ''}. Capas disponibles: {disponibles}")
    entity = candidatas[0]
    vertices = list(entity.get_points(format="xyb"))
    pts = [(vertices[0][0], vertices[0][1])]
    for i in range(len(vertices) - 1):
        x1, y1, b = vertices[i]
        x2, y2 = vertices[i + 1][0], vertices[i + 1][1]
        if abs(b) > 1e-9:
            pts.extend(teselar_bulge((x1, y1), (x2, y2), b, sagitta))
        else:
            pts.append((x2, y2))
    return pts, entity.dxf.layer


def _longitud(eje) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(eje, eje[1:]))


def _punto_en_estacion(eje, estacion: float):
    acum = 0.0
    for a, b in zip(eje, eje[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg < 1e-12:
            continue
        if acum + seg >= estacion - 1e-9:
            t = max(0.0, min(1.0, (estacion - acum) / seg))
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        acum += seg
    return eje[-1]


def _direccion_en_estacion(eje, estacion: float):
    acum = 0.0
    for a, b in zip(eje, eje[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg < 1e-12:
            continue
        if acum + seg >= estacion - 1e-9:
            return (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
        acum += seg
    a, b = eje[-2], eje[-1]
    seg = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    return (b[0] - a[0]) / seg, (b[1] - a[1]) / seg


def muestrear_perfil(tris, eje, intervalo: float):
    longitud = _longitud(eje)
    if longitud <= 0:
        raise ValueError("el eje no tiene longitud (revisa la polilinea del DXF)")
    celda = max(intervalo, 1.0) * 2
    idx = indice_espacial(tris, celda)
    n = max(1, int(longitud // intervalo))
    estaciones = [min(i * intervalo, longitud) for i in range(n + 1)]
    if estaciones[-1] < longitud - 1e-6:
        estaciones.append(longitud)
    muestras = []
    for est in estaciones:
        x, y = _punto_en_estacion(eje, est)
        z = cota_en(idx, celda, x, y)
        muestras.append({"estacion": est, "x": x, "y": y, "cota": z})
    return muestras, longitud


def muestrear_transecto(superficies_idx, eje, estacion: float, izq: float, der: float, paso: float):
    """superficies_idx: dict nombre -> (indice, celda). Devuelve lista de filas
    {"offset": ..., <nombre>: cota|None, ...} a lo largo de la normal al eje."""
    x0, y0 = _punto_en_estacion(eje, estacion)
    ux, uy = _direccion_en_estacion(eje, estacion)
    nx, ny = -uy, ux
    offsets = []
    o = -izq
    while o <= der + 1e-9:
        offsets.append(round(o, 6))
        o += paso
    filas = []
    for off in offsets:
        x, y = x0 + nx * off, y0 + ny * off
        fila = {"offset": off}
        for nombre, (idx, celda) in superficies_idx.items():
            fila[nombre] = cota_en(idx, celda, x, y)
        filas.append(fila)
    return filas


# ------------------------------------------------------------------ contornos --
def extraer_contornos(tris, intervalo: float):
    """Segmentos de contorno por interseccion triangulo-a-triangulo (marching
    triangles simple, sin fusionar en polilineas continuas). Aproximado: para
    contornos definitivos de plano usar `civil3d_surface_extract_contours`
    con Civil 3D abierto; esto es solo para el plano de verificacion."""
    if intervalo <= 0:
        raise ValueError("el intervalo de contornos debe ser mayor que 0")
    segmentos = defaultdict(list)
    for t in tris:
        zs = [p[2] for p in t]
        zmin, zmax = min(zs), max(zs)
        nivel = math.ceil(zmin / intervalo) * intervalo
        while nivel <= zmax:
            pts = []
            for i in range(3):
                a, b = t[i], t[(i + 1) % 3]
                za, zb = a[2], b[2]
                if za == zb:
                    continue
                if (za - nivel) * (zb - nivel) <= 0:
                    f = (nivel - za) / (zb - za)
                    if -1e-9 <= f <= 1 + 1e-9:
                        f = min(1.0, max(0.0, f))
                        pts.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            if len(pts) >= 2:
                segmentos[nivel].append((pts[0], pts[1]))
            nivel += intervalo
    return segmentos


# --------------------------------------------------------------- HTML ------
CSS = """
:root { --accent:#0e5563; --tinta:#1c1c1a; --tinta2:#5a5952; --fondo:#fbfaf7;
        --papel:#ffffff; --borde:#ddd9cf; --alerta:#a13d2b; --ok:#1c6e4a; }
* { box-sizing:border-box; }
body { margin:0; padding:2.5rem 3rem 4rem; background:var(--fondo); color:var(--tinta);
       font-family:Georgia,'Times New Roman',serif; line-height:1.5; }
h1,h2,h3 { font-family:Georgia,serif; font-weight:normal; color:var(--tinta); }
h1 { font-size:1.7rem; margin:0 0 .2rem; }
h2 { font-size:1.2rem; color:var(--accent); border-bottom:1px solid var(--borde);
     padding-bottom:.3rem; margin-top:2.4rem; }
h3 { font-size:1rem; margin-bottom:.5rem; }
.titleblock { border:1px solid var(--borde); background:var(--papel); padding:1.1rem 1.4rem;
              display:flex; flex-wrap:wrap; gap:.3rem 2.2rem; margin-bottom:1.4rem; }
.titleblock .campo { font-size:.86rem; color:var(--tinta2); }
.titleblock .campo b { color:var(--tinta); font-weight:normal; font-family:inherit; }
.subtitulo { color:var(--tinta2); font-size:.95rem; margin-bottom:1.2rem; }
.stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:.9rem;
         margin:1rem 0 1.6rem; }
.stat { background:var(--papel); border:1px solid var(--borde); border-left:3px solid var(--accent);
        padding:.6rem .8rem; }
.stat .val { font-size:1.25rem; }
.stat .lbl { font-size:.74rem; color:var(--tinta2); text-transform:uppercase; letter-spacing:.03em; }
.section { background:var(--papel); border:1px solid var(--borde); padding:1.2rem 1.4rem;
           margin-bottom:1rem; break-inside:avoid; }
table { border-collapse:collapse; width:100%; font-size:.88rem; margin:.6rem 0 1rem; }
th,td { border:1px solid var(--borde); padding:.35rem .6rem; text-align:left; }
th { background:#f1efe8; font-weight:normal; color:var(--tinta2); }
td.num,th.num { text-align:right; font-variant-numeric:tabular-nums; }
figure { margin:.6rem 0; }
figure svg { max-width:100%; height:auto; display:block; }
figcaption { font-size:.8rem; color:var(--tinta2); margin-top:.3rem; }
.grid-secciones { display:grid; grid-template-columns:repeat(auto-fit,minmax(400px,1fr)); gap:.8rem; }
.finding { border-left:3px solid var(--tinta2); background:var(--papel); padding:.55rem .9rem;
           margin:.5rem 0; font-size:.9rem; break-inside:avoid; }
.finding-alerta { border-color:var(--alerta); }
.finding-ok { border-color:var(--ok); }
.finding-info { border-color:var(--accent); }
footer { margin-top:2.4rem; font-size:.78rem; color:var(--tinta2); }
.page-break { break-after:page; }
@media print {
  body { background:#fff; padding:0 1.2cm; }
  .titleblock, .section, .finding { break-inside:avoid; }
  h2 { break-after:avoid; }
}
"""


def _fila(cols, num_desde=1):
    return "<tr>" + "".join(
        f'<td class="num">{c}</td>' if i >= num_desde else f"<td>{c}</td>"
        for i, c in enumerate(cols)
    ) + "</tr>"


def render_stat(valor: str, etiqueta: str) -> str:
    return f'<div class="stat"><div class="val">{valor}</div><div class="lbl">{etiqueta}</div></div>'


def render_finding(tipo: str, texto: str) -> str:
    return f'<div class="finding finding-{tipo}">{texto}</div>'


def escala_aproximada(bbox, ancho_hoja_m: float = 0.42) -> int:
    """Escala numerica aproximada 1:N para una hoja de ~A3 apaisada, redondeada
    a un valor de uso habitual (500/1000/2000/...)."""
    x0, y0, x1, y1 = bbox
    dim = max(x1 - x0, y1 - y0, 1e-6)
    n = dim / ancho_hoja_m
    pasos = (100, 200, 250, 500, 1000, 1250, 2000, 2500, 5000, 10000, 20000, 50000)
    return min(pasos, key=lambda p: abs(p - n)) if n <= pasos[-1] else int(round(n / 5000.0) * 5000)


def _sanear_json(obj):
    """Reemplaza inf/-inf/nan (bandas abiertas) por None: JSON estandar no los
    admite y algunos lectores externos no toleran el 'Infinity' de Python."""
    if isinstance(obj, float):
        return None if math.isinf(obj) or math.isnan(obj) else obj
    if isinstance(obj, dict):
        return {k: _sanear_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanear_json(v) for v in obj]
    return obj


def generar_informe(args) -> dict:
    tema = args.tema
    nombre, tris, meta, unidad = leer_landxml(args.xml, args.superficie)
    ul = unidad["etiqueta_lin"]
    stats = calcular_estadisticas(tris, meta)

    hallazgos = []
    if stats["area2d_declarada"] and abs(stats["area2d_declarada"] - stats["area2d"]) > max(1e-3, stats["area2d_declarada"] * 1e-6):
        hallazgos.append(("alerta", f"El area 2D recalculada ({fmt(stats['area2d'])} {unidad['etiqueta']}) "
                                     f"difiere de la declarada en el LandXML ({fmt(stats['area2d_declarada'])} {unidad['etiqueta']})."))
    if stats["n_caras_invisibles"]:
        hallazgos.append(("info", f"Se descartaron {stats['n_caras_invisibles']} caras marcadas como invisibles "
                                   f"(i=\"1\"), tal como lo hace Civil 3D por contorno."))

    # --- zonificacion de cotas -------------------------------------------
    bandas_cota = resolver_bandas(args.bandas_cota, stats["cota_min"], stats["cota_max"])
    zonas_cota = zonificar(tris, cota_media, bandas_cota)
    etq_cota = [etiqueta_banda(z["min"], z["max"], f" {ul}") for z in zonas_cota]

    plano_cota = PlanoSVG(titulo=f"Zonificacion de cotas — {nombre}",
                          subtitulo=f"{stats['n_triangulos']:,} triangulos | {unidad['sistema']}/{unidad['lineal']}",
                          unidad_lin=ul, tema=tema)
    plano_cota.poligonos_graduados(
        [([(p[0], p[1]) for p in t], cota_media(t)) for t in tris], titulo_escala=f"cota ({ul})")
    svg_plano_cota = plano_cota.render()
    svg_barras_cota = grafico_barras(
        etq_cota, [z["area2d"] for z in zonas_cota], titulo="Area por banda de cota",
        unidad_val=f"area ({unidad['etiqueta']})", valor_fmt=lambda v: f"{v:,.0f}", tema=tema)

    # --- zonificacion de pendientes ---------------------------------------
    cortes_pend = args.bandas_pendiente or "0,5,10,15,25"
    bandas_pend = bandas_desde_cortes([float(x) for x in cortes_pend.split(",")])
    zonas_pend = zonificar(tris, pendiente_pct, bandas_pend)
    etq_pend = [etiqueta_banda(z["min"], z["max"], "%") for z in zonas_pend]

    plano_pend = PlanoSVG(titulo=f"Zonificacion de pendientes — {nombre}",
                          subtitulo="rampa continua; las bandas de la tabla usan los mismos cortes",
                          unidad_lin=ul, tema=tema)
    plano_pend.poligonos_graduados(
        [([(p[0], p[1]) for p in t], pendiente_pct(t)) for t in tris], titulo_escala="pendiente (%)")
    svg_plano_pend = plano_pend.render()
    svg_barras_pend = grafico_barras(
        etq_pend, [z["area2d"] for z in zonas_pend], titulo="Area por banda de pendiente",
        unidad_val=f"area ({unidad['etiqueta']})", valor_fmt=lambda v: f"{v:,.0f}", tema=tema)

    # bandas_desde_cortes siempre agrega al final la banda abierta (ultimo_corte, inf):
    # es la banda de mayor pendiente, sin importar cuantos cortes haya.
    umbral_alto = bandas_pend[-1][0]
    pct_pend_alta = 100.0 * zonas_pend[-1]["area2d"] / stats["area2d"] if stats["area2d"] else 0.0
    if pct_pend_alta > 5.0:
        hallazgos.append(("alerta", f"{pct_pend_alta:.1f}% del area tiene pendiente mayor a "
                                     f"{umbral_alto:.0f}%: revisar estabilidad de taludes "
                                     f"(ver skill `slope_analysis`)."))
    elif pct_pend_alta > 0:
        hallazgos.append(("info", f"{pct_pend_alta:.1f}% del area supera {umbral_alto:.0f}% de pendiente."))

    # --- orientacion --------------------------------------------------------
    centros, valores_rosa, excluidos = rosa_orientacion(tris, args.sectores_orientacion)
    svg_rosa = grafico_rosa(centros, valores_rosa, titulo="Orientacion de laderas (aspecto)",
                            unidad_val=unidad["etiqueta"], tema=tema)
    nombres_cardinales = nombres_sectores(args.sectores_orientacion)
    etq_rosa = nombres_cardinales or [
        etiqueta_banda(c - 180.0 / args.sectores_orientacion, c + 180.0 / args.sectores_orientacion, "")
        for c in centros]

    # --- eje: perfil longitudinal y transectos -------------------------------
    eje = None
    perfil_svg = None
    perfil_muestras = None
    transectos = []
    tris_disenio = None
    nombre_dis = None
    stats_dis = None
    volumen = None

    if args.xml_disenio:
        nombre_dis, tris_disenio, meta_dis, _ = leer_landxml(args.xml_disenio, args.superficie_disenio)
        stats_dis = calcular_estadisticas(tris_disenio, meta_dis)

    if args.eje_dxf:
        eje, capa_eje = leer_eje_dxf(args.eje_dxf, args.capa_eje)
        muestras, longitud = muestrear_perfil(tris, eje, args.intervalo_perfil)
        series = [{"nombre": nombre, "valores": [m["cota"] for m in muestras], "rol": "serie1"}]
        if tris_disenio is not None:
            muestras_dis, _ = muestrear_perfil(tris_disenio, eje, args.intervalo_perfil)
            series.append({"nombre": nombre_dis, "valores": [m["cota"] for m in muestras_dis], "rol": "serie2"})
        perfil_svg = grafico_perfil(
            [m["estacion"] for m in muestras], series, titulo="Perfil longitudinal",
            subtitulo=f"eje capa '{capa_eje}' | longitud {fmt(longitud)} {ul} | intervalo {args.intervalo_perfil} {ul}",
            unidad_est=ul, unidad_elev=ul, ancho=900, alto=340, tema=tema,
            sombrear_entre=(nombre_dis, nombre) if tris_disenio is not None else None)
        perfil_muestras = muestras

        if args.transectos:
            superficies_idx = {nombre: (indice_espacial(tris, max(args.paso_transecto, 1.0) * 2),
                                        max(args.paso_transecto, 1.0) * 2)}
            if tris_disenio is not None:
                superficies_idx[nombre_dis] = (indice_espacial(tris_disenio, max(args.paso_transecto, 1.0) * 2),
                                               max(args.paso_transecto, 1.0) * 2)
            n_est = max(1, int(longitud // args.intervalo_transectos))
            estaciones_corte = [min(i * args.intervalo_transectos, longitud) for i in range(n_est + 1)]
            for est in estaciones_corte:
                filas = muestrear_transecto(superficies_idx, eje, est, args.ancho_izq, args.ancho_der,
                                            args.paso_transecto)
                offs = [f["offset"] for f in filas]
                series_t = [{"nombre": nombre, "valores": [f[nombre] for f in filas], "rol": "serie1"}]
                if tris_disenio is not None:
                    series_t.append({"nombre": nombre_dis, "valores": [f[nombre_dis] for f in filas], "rol": "serie2"})
                svg_t = grafico_perfil(
                    offs, series_t, titulo=f"Seccion en {fmt(est)} {ul}",
                    unidad_est=ul, unidad_elev=ul, ancho=440, alto=260, tema=tema,
                    sombrear_entre=(nombre_dis, nombre) if tris_disenio is not None else None)
                transectos.append({"estacion": est, "svg": svg_t, "filas": filas})

    if tris_disenio is not None:
        espaciamiento = args.espaciamiento_volumen
        if espaciamiento is None:
            x0, y0, x1, y1 = bbox_tris(tris)
            espaciamiento = paso_redondo(min(x1 - x0, y1 - y0) / 80.0) or 1.0
        volumen = volumen_grid(tris, tris_disenio, espaciamiento)
        direccion = "relleno" if volumen["neto_volumen"] > 0 else ("corte" if volumen["neto_volumen"] < 0 else "equilibrado")
        hallazgos.append(("info" if direccion != "equilibrado" else "ok",
                          f"Balance neto: {direccion} de {fmt(abs(volumen['neto_volumen']))} "
                          f"{unidad['etiqueta']}·{ul} (metodo de grilla, paso {fmt(volumen['espaciamiento'])} {ul})."))
        if volumen["cobertura_pct"] < 90.0:
            hallazgos.append(("alerta", f"La grilla de volumen solo tuvo dato en ambas superficies en "
                                        f"{volumen['cobertura_pct']:.1f}% del area de solape: el resultado "
                                        f"puede no representar toda la zona de interes."))

    if not hallazgos:
        hallazgos.append(("ok", "No se detectaron inconsistencias automaticas en esta corrida."))

    # --- ensamblar resultado -------------------------------------------------
    x0, y0, x1, y1 = bbox_tris(tris)
    resultado = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "proyecto": args.proyecto,
        "superficie": nombre, "unidad": unidad, "estadisticas": stats,
        "bandas_cota": [{"etiqueta": e, **z} for e, z in zip(etq_cota, zonas_cota)],
        "bandas_pendiente": [{"etiqueta": e, **z} for e, z in zip(etq_pend, zonas_pend)],
        "orientacion": [{"centro_deg": c, "area2d": v} for c, v in zip(centros, valores_rosa)],
        "orientacion_excluidos_planos": excluidos,
        "superficie_disenio": nombre_dis, "estadisticas_disenio": stats_dis,
        "volumen": volumen,
        "eje": ({"longitud": _longitud(eje), "perfil": perfil_muestras} if eje else None),
        "escala_aprox": escala_aproximada((x0, y0, x1, y1)),
        "hallazgos": [{"tipo": t, "texto": x} for t, x in hallazgos],
    }

    pagina_html = render_html(
        args=args, nombre=nombre, unidad=unidad, stats=stats, hallazgos=hallazgos,
        svg_plano_cota=svg_plano_cota, svg_barras_cota=svg_barras_cota,
        zonas_cota=zonas_cota, etq_cota=etq_cota,
        svg_plano_pend=svg_plano_pend, svg_barras_pend=svg_barras_pend,
        zonas_pend=zonas_pend, etq_pend=etq_pend,
        svg_rosa=svg_rosa, centros=centros, valores_rosa=valores_rosa, etq_rosa=etq_rosa,
        perfil_svg=perfil_svg, transectos=transectos,
        nombre_dis=nombre_dis, stats_dis=stats_dis, volumen=volumen,
        escala_aprox=resultado["escala_aprox"],
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.salida)) or ".", exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as fh:
        fh.write(pagina_html)
    resultado["archivo_html"] = args.salida

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(_sanear_json(resultado), fh, indent=2, ensure_ascii=False)
        resultado["archivo_json"] = args.json

    return resultado


def render_html(*, args, nombre, unidad, stats, hallazgos,
                 svg_plano_cota, svg_barras_cota, zonas_cota, etq_cota,
                 svg_plano_pend, svg_barras_pend, zonas_pend, etq_pend,
                 svg_rosa, centros, valores_rosa, etq_rosa,
                 perfil_svg, transectos, nombre_dis, stats_dis, volumen, escala_aprox) -> str:
    # Texto libre (nombres de superficie/proyecto vienen del LandXML o de la
    # linea de comandos): se escapa antes de incrustarlo en el HTML.
    nombre = html.escape(str(nombre))
    nombre_dis = html.escape(str(nombre_dis)) if nombre_dis else nombre_dis
    ue, ul = html.escape(unidad["etiqueta"]), html.escape(unidad["etiqueta_lin"])
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    filas_cota = "".join(
        _fila([etq_cota[i], f"{z['area2d']:,.1f}", f"{z['area3d']:,.1f}",
              f"{100.0 * z['area2d'] / stats['area2d']:,.1f}%" if stats['area2d'] else "0%", z["n_triangulos"]])
        for i, z in enumerate(zonas_cota))
    filas_pend = "".join(
        _fila([etq_pend[i], f"{z['area2d']:,.1f}",
              f"{100.0 * z['area2d'] / stats['area2d']:,.1f}%" if stats['area2d'] else "0%", z["n_triangulos"]])
        for i, z in enumerate(zonas_pend))
    filas_rosa = "".join(
        _fila([etq_rosa[i], f"{v:,.1f}",
              f"{100.0 * v / sum(valores_rosa):,.1f}%" if sum(valores_rosa) else "0%"])
        for i, v in enumerate(valores_rosa))

    seccion_volumen = ""
    if volumen:
        seccion_volumen = f"""
<div class="section">
<h2>Computo volumetrico (corte / relleno)</h2>
<p class="subtitulo">{nombre} (existente) vs {nombre_dis} (diseño) — metodo de grilla,
paso {fmt(volumen['espaciamiento'])} {ul}, cobertura {volumen['cobertura_pct']:.1f}% del area de solape.</p>
<table>
<tr><th></th><th class="num">Volumen ({ue}·{ul})</th></tr>
{_fila(["Corte", f"{volumen['corte_volumen']:,.1f}"])}
{_fila(["Relleno", f"{volumen['relleno_volumen']:,.1f}"])}
{_fila(["Neto (relleno - corte)", f"{volumen['neto_volumen']:,.1f}"])}
</table>
</div>"""

    seccion_perfil = ""
    if perfil_svg:
        seccion_perfil = f"""
<div class="section">
<h2>Perfil longitudinal</h2>
<figure>{perfil_svg}</figure>
</div>"""

    seccion_transectos = ""
    if transectos:
        tarjetas = "".join(f'<figure>{t["svg"]}</figure>' for t in transectos)
        seccion_transectos = f"""
<div class="section">
<h2>Secciones transversales</h2>
<p class="subtitulo">{len(transectos)} secciones cada {fmt(args.intervalo_transectos)} {ul},
ancho izq/der {args.ancho_izq}/{args.ancho_der} {ul}.</p>
<div class="grid-secciones">{tarjetas}</div>
</div>"""

    hallazgos_html = "".join(render_finding(t, x) for t, x in hallazgos)

    proyecto = html.escape(args.proyecto or "Sitio_Estudio")
    titulo_informe = html.escape(args.titulo) if args.titulo else f"Informe de analisis de superficie — {nombre}"

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>{titulo_informe}</title>
<style>{CSS}</style>
</head><body>

<header class="titleblock">
  <div class="campo">Proyecto: <b>{proyecto}</b></div>
  <div class="campo">Superficie: <b>{nombre}</b>{' vs ' + nombre_dis if nombre_dis else ''}</div>
  <div class="campo">Sistema: <b>{html.escape(unidad['sistema'])} / {html.escape(unidad['lineal'])}</b></div>
  <div class="campo">Escala aprox. plano: <b>1:{escala_aprox:,}</b></div>
  <div class="campo">Generado: <b>{fecha}</b></div>
</header>

<h1>{titulo_informe}</h1>
<p class="subtitulo">Informe generado automaticamente a partir de LandXML, sin requerir Civil 3D
abierto. Cruzar los resultados marcados como estimacion con las herramientas MCP
(<code>civil3d_surface_statistics_get</code>, <code>civil3d_surface_volume_calculate</code>) cuando
el dibujo este disponible.</p>

<div class="stats">
  {render_stat(f"{stats['area2d']:,.1f} {ue}", "Area 2D (planta)")}
  {render_stat(f"{stats['area3d']:,.1f} {ue}", "Area 3D (real)")}
  {render_stat(f"{stats['cota_min']:,.2f} {ul}", "Cota minima")}
  {render_stat(f"{stats['cota_media_ponderada']:,.2f} {ul}", "Cota media (pond.)")}
  {render_stat(f"{stats['cota_max']:,.2f} {ul}", "Cota maxima")}
  {render_stat(f"{stats['pendiente_media_ponderada']:,.1f} %", "Pendiente media")}
  {render_stat(f"{stats['pendiente_max']:,.1f} %", "Pendiente maxima")}
  {render_stat(f"{stats['n_triangulos']:,}", "Triangulos")}
</div>

<div class="section">
<h2>Zonificacion de cotas</h2>
<figure>{svg_plano_cota}<figcaption>Plano en planta coloreado por cota media de triangulo (rampa continua).</figcaption></figure>
<figure>{svg_barras_cota}</figure>
<table>
<tr><th>Banda</th><th class="num">Area 2D ({ue})</th><th class="num">Area 3D ({ue})</th><th class="num">% del total</th><th class="num">Triangulos</th></tr>
{filas_cota}
</table>
</div>

<div class="section">
<h2>Zonificacion de pendientes</h2>
<figure>{svg_plano_pend}<figcaption>Plano en planta coloreado por pendiente de triangulo (rampa continua).</figcaption></figure>
<figure>{svg_barras_pend}</figure>
<table>
<tr><th>Banda</th><th class="num">Area 2D ({ue})</th><th class="num">% del total</th><th class="num">Triangulos</th></tr>
{filas_pend}
</table>
</div>

<div class="section">
<h2>Orientacion de laderas (aspecto)</h2>
<figure>{svg_rosa}<figcaption>Area ponderada por sector de orientacion (N arriba, sentido horario). Triangulos
con pendiente menor a {UMBRAL_PENDIENTE_PLANA}% se excluyen por no tener orientacion representativa.</figcaption></figure>
<table>
<tr><th>Sector</th><th class="num">Area ({ue})</th><th class="num">% del total orientado</th></tr>
{filas_rosa}
</table>
</div>

{seccion_perfil}
{seccion_transectos}
{seccion_volumen}

<div class="section">
<h2>Hallazgos y recomendaciones</h2>
{hallazgos_html}
</div>

<footer>Generado por la skill <code>informe-analisis-superficies</code> ·
{fecha} · sin datos de cliente ni coordenadas absolutas segun la politica del repositorio.</footer>

</body></html>"""


# ---------------------------------------------------------------------- CLI --
def main() -> int:
    ap = argparse.ArgumentParser(description="Informe HTML de analisis de superficie(s) TIN LandXML.")
    ap.add_argument("--xml", required=True, help="LandXML de la superficie existente/base")
    ap.add_argument("--superficie", help="nombre de la superficie si el XML trae varias")
    ap.add_argument("--xml-disenio", help="LandXML de una segunda superficie (diseño) para corte/relleno")
    ap.add_argument("--superficie-disenio", help="nombre de la superficie de diseño si el XML trae varias")
    ap.add_argument("--eje-dxf", help="DXF con la polilinea de eje para perfil/transectos")
    ap.add_argument("--capa-eje", help="capa de la polilinea de eje dentro del DXF")
    ap.add_argument("--intervalo-perfil", type=float, default=25.0, help="intervalo de muestreo del perfil longitudinal")
    ap.add_argument("--transectos", action="store_true", help="generar secciones transversales a lo largo del eje")
    ap.add_argument("--intervalo-transectos", type=float, default=50.0, help="separacion entre estaciones de corte")
    ap.add_argument("--ancho-izq", type=float, default=15.0, help="ancho de transecto a la izquierda del eje")
    ap.add_argument("--ancho-der", type=float, default=15.0, help="ancho de transecto a la derecha del eje")
    ap.add_argument("--paso-transecto", type=float, default=1.0, help="paso de muestreo dentro de cada transecto")
    ap.add_argument("--bandas-cota", help="N de bandas iguales, o cortes separados por coma (ej. '0,10,20,30')")
    ap.add_argument("--bandas-pendiente", help="cortes de pendiente en %% separados por coma (default 0,5,10,15,25)")
    ap.add_argument("--sectores-orientacion", type=int, default=8, help="numero de sectores de la rosa de orientacion")
    ap.add_argument("--espaciamiento-volumen", type=float, help="paso de la grilla de volumen (auto si se omite)")
    ap.add_argument("--proyecto", default="Sitio_Estudio", help="nombre generico del proyecto para el membrete")
    ap.add_argument("--titulo", help="titulo del informe")
    ap.add_argument("--tema", default="claro", choices=("claro", "oscuro"))
    ap.add_argument("--salida", default="informe_superficie.html", help="archivo HTML de salida")
    ap.add_argument("--json", help="volcar los resultados numericos a un archivo JSON")
    args = ap.parse_args()

    try:
        res = generar_informe(args)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        sys.exit(f"ERROR: {exc}")

    print(f"Informe generado: {res['archivo_html']}")
    if res.get("archivo_json"):
        print(f"JSON: {res['archivo_json']}")
    print(f"  superficie: {res['superficie']} | area2D {res['estadisticas']['area2d']:,.1f} "
          f"{res['unidad']['etiqueta']} | cota {res['estadisticas']['cota_min']:,.2f} a "
          f"{res['estadisticas']['cota_max']:,.2f} {res['unidad']['etiqueta_lin']}")
    if res.get("volumen"):
        print(f"  volumen neto: {res['volumen']['neto_volumen']:,.1f} "
              f"{res['unidad']['etiqueta']}·{res['unidad']['etiqueta_lin']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
