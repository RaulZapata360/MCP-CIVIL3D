# -*- coding: utf-8 -*-
# ============================================================================
#  clasificar_marcas_pavimento.py
#  Mide (no adivina) si cada categoria de un DXF de marcas viales debe ir a
#  Revit como FAMILIA o como DIRECTSHAPE, y si es candidata a "un solo simbolo
#  con muchas instancias" o a "familia parametrica de N tamanos".
#
#  Aprendido migrando South Island (HRCP): forzar una sola tecnica para todas
#  las categorias da mal resultado. El reparto correcto sale de medir, por
#  capa: planitud contra su plano de ajuste, numero de piezas/huecos, y si el
#  contorno es un rectangulo real (area = largo x ancho) o una forma organica.
#
#  Uso:
#    python clasificar_marcas_pavimento.py <marcas.dxf> [--capas CAPA1,CAPA2,...]
#
#  Salida: una tabla en pantalla con la recomendacion por capa. No escribe
#  nada -- es el paso 1 (diagnostico) antes de exportar con
#  exportar_marcas_pavimento.py.
# ============================================================================
import argparse
import collections
import math
import sys

import ezdxf
import numpy as np
import shapely.geometry as sg
from shapely.ops import unary_union
from scipy.spatial import ConvexHull

# Umbrales aprendidos en South Island (36 flechas + 14 stop bars a familia;
# 26 doble amarilla + 246 lineas a DirectShape). No son un limite fisico, son
# el punto donde la migracion original decidio bien -- reajustar si un
# proyecto nuevo cae justo en la frontera.
UMBRAL_PLANO_FT = 0.15      # error max contra el plano de ajuste
UMBRAL_DISPERSION = 0.05    # coef. de variacion de area para "mismo simbolo"
UMBRAL_RECTANGULARIDAD = 0.98  # area / (largo x ancho) para "es un rectangulo"


def leer_capa_mallas(doc, capa):
    """Lee las entidades AcDbPolyFaceMesh de una capa.

    OJO DE FORMATO: en un LandXML/IFC->DXF de marcas viales, cada marca suele
    ser una malla poliedrica (AcDbPolyFaceMesh), NO una polilinea. En ezdxf,
    los vertices con `flags & 64` son vertices REALES; el resto son registros
    de cara (location en 0,0,0, indices en vtx0..vtx3). Leerlos todos sin
    filtrar da cajas de millones de pies -- confundio un analisis entero antes
    de detectarlo."""
    out = []
    for k, e in enumerate(doc.modelspace().query('POLYLINE[layer=="%s"]' % capa)):
        if e.get_mode() != 'AcDbPolyFaceMesh':
            continue
        V = np.array([[v.dxf.location.x, v.dxf.location.y, v.dxf.location.z]
                      for v in e.vertices if v.dxf.flags & 64])
        T = []
        for v in e.vertices:
            if v.dxf.flags & 64:
                continue
            idx = [abs(v.dxf.get(f, 0)) for f in ('vtx0', 'vtx1', 'vtx2', 'vtx3')]
            idx = [i - 1 for i in idx if i]
            if len(idx) < 3 or max(idx) >= len(V):
                continue
            for j in range(1, len(idx) - 1):
                T.append((idx[0], idx[j], idx[j + 1]))
        if len(V) and T:
            out.append(dict(i=k, V=V, T=T))
    return out


def area3d(V, T):
    return sum(0.5 * np.linalg.norm(np.cross(V[b] - V[a], V[c] - V[a])) for a, b, c in T)


def plano_ajuste(V):
    """z = a(x-cx)+b(y-cy)+c por minimos cuadrados. Devuelve (pendiente %,
    error maximo contra el plano)."""
    cx, cy = V[:, 0].mean(), V[:, 1].mean()
    A = np.column_stack([V[:, 0] - cx, V[:, 1] - cy, np.ones(len(V))])
    coef, *_ = np.linalg.lstsq(A, V[:, 2], rcond=None)
    err = float(np.abs(A @ coef - V[:, 2]).max())
    pend = 100 * math.hypot(coef[0], coef[1])
    return pend, err


def piezas_y_huecos(V, T, min_area_hueco=1.0):
    polys = [sg.Polygon(V[list(t), :2]) for t in T]
    polys = [p for p in polys if p.is_valid and p.area > 1e-9]
    if not polys:
        return 0, 0
    u = unary_union(polys).buffer(0.001).buffer(-0.001)
    geoms = list(u.geoms) if u.geom_type == 'MultiPolygon' else [u]
    n_huecos = sum(1 for g in geoms for r in g.interiors if sg.Polygon(r).area > min_area_hueco)
    return len(geoms), n_huecos


def rect_min(P):
    """(largo, ancho, angulo del lado largo). El area/(largo*ancho) dice si P
    es de verdad un rectangulo (ratio ~1.0) o una forma con mas dispersion."""
    H = P[ConvexHull(P).vertices]
    mejor = None
    for k in range(len(H)):
        d = H[(k + 1) % len(H)] - H[k]
        ang = math.atan2(d[1], d[0])
        R = np.array([[math.cos(-ang), -math.sin(-ang)], [math.sin(-ang), math.cos(-ang)]])
        Q = P @ R.T
        w, h = np.ptp(Q[:, 0]), np.ptp(Q[:, 1])
        if mejor is None or w * h < mejor[0] * mejor[1]:
            mejor = (w, h, ang)
    w, h, ang = mejor
    return max(w, h), min(w, h)


def analizar_capa(nombre, marcas):
    n = len(marcas)
    areas, pends, errs, piezas_l, huecos_l, ratios = [], [], [], [], [], []
    for m in marcas:
        a = area3d(m['V'], m['T'])
        pend, err = plano_ajuste(m['V'])
        np_, nh = piezas_y_huecos(m['V'], m['T'])
        try:
            contorno = m['V'][:, :2]
            largo, ancho = rect_min(contorno)
            ratio = a / (largo * ancho) if largo * ancho > 1e-9 else 0.0
        except Exception:
            ratio = 0.0
        areas.append(a); pends.append(pend); errs.append(err)
        piezas_l.append(np_); huecos_l.append(nh); ratios.append(ratio)

    areas = np.array(areas)
    disp_area = float(areas.std() / areas.mean()) if areas.mean() > 0 else 1.0
    max_err = float(np.max(errs)) if errs else 0.0
    max_piezas = max(piezas_l) if piezas_l else 0
    tot_huecos = sum(huecos_l)
    rectangularidad = float(np.median(ratios)) if ratios else 0.0

    plano = max_err <= UMBRAL_PLANO_FT
    una_pieza = max_piezas <= 1 and tot_huecos == 0
    es_rectangulo = rectangularidad >= UMBRAL_RECTANGULARIDAD
    mismo_simbolo = disp_area <= UMBRAL_DISPERSION

    if plano and una_pieza:
        if mismo_simbolo:
            tecnica = 'FAMILIA (1 simbolo + instancias)'
        elif es_rectangulo:
            tecnica = 'FAMILIA (parametrica: largo/ancho variables)'
        else:
            tecnica = 'FAMILIA (revisar: plana y 1 pieza, pero sin patron claro)'
    else:
        tecnica = 'DIRECTSHAPE (desde la malla)'

    return dict(capa=nombre, n=n, area=areas.sum(), max_err=max_err, max_piezas=max_piezas,
               huecos=tot_huecos, disp_area=disp_area, rectangularidad=rectangularidad,
               tecnica=tecnica)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('dxf')
    ap.add_argument('--capas', help='Coma-separado. Si se omite, se analizan todas las capas '
                                    'con entidades AcDbPolyFaceMesh.')
    args = ap.parse_args()

    doc = ezdxf.readfile(args.dxf)
    todas = {e.dxf.layer for e in doc.modelspace()
            if e.dxftype() == 'POLYLINE' and e.get_mode() == 'AcDbPolyFaceMesh'}
    capas = args.capas.split(',') if args.capas else sorted(todas)
    if not capas:
        print('No se encontraron capas con mallas AcDbPolyFaceMesh en el DXF.')
        sys.exit(1)

    print(f'{"capa":32s} {"n":>5s} {"area":>10s} {"err.plano":>10s} {"piezas":>7s} '
          f'{"huecos":>7s} {"disp.area":>10s} {"rect.":>6s}   tecnica recomendada')
    print('-' * 130)
    resumen = []
    for capa in capas:
        marcas = leer_capa_mallas(doc, capa)
        if not marcas:
            print(f'{capa:32s}  (sin mallas en esta capa, se omite)')
            continue
        r = analizar_capa(capa, marcas)
        resumen.append(r)
        print(f"{r['capa']:32s} {r['n']:5d} {r['area']:10,.1f} {r['max_err']:10.3f} "
              f"{r['max_piezas']:7d} {r['huecos']:7d} {r['disp_area']:10.3f} "
              f"{r['rectangularidad']:6.3f}   {r['tecnica']}")

    n_fam = sum(1 for r in resumen if r['tecnica'].startswith('FAMILIA'))
    n_ds = sum(1 for r in resumen if r['tecnica'].startswith('DIRECTSHAPE'))
    print('-' * 130)
    print(f'{len(resumen)} capas: {n_fam} a familia, {n_ds} a DirectShape. '
          f'{sum(r["n"] for r in resumen)} marcas en total.')
    print('\nSiguiente paso: exportar_marcas_pavimento.py usando estas mismas capas.')


if __name__ == '__main__':
    main()
