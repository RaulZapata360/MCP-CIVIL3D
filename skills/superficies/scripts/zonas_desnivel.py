# -*- coding: utf-8 -*-
# Marca en un DXF las zonas donde dos superficies TIN difieren en cota mas de un
# umbral. Pensado para comparar "Vieja" contra "Nueva" del mismo terreno.
#
# COMO: se rasterizan las dos superficies sobre la misma malla regular (por
# defecto 1 ft) interpolando por baricentricas dentro de cada triangulo, se resta
# celda a celda, y las celdas que superan el umbral se agrupan en poligonos.
#
# Se separa por BANDAS de magnitud y por SIGNO, cada una en su capa, porque no es
# lo mismo un desnivel de 0.12 ft que uno de 3 ft, y saber si la nueva sube o baja
# respecto a la vieja suele ser lo que decide si hay que revisar la zona.
#
# Los poligonos salen con el escalon de la malla (bordes en angulo recto): es
# deliberado, marca hasta donde llega el muestreo y no sugiere una precision que
# no hay. Subir la resolucion con --paso si hace falta mas detalle.
#
# Uso:
#   python zonas_desnivel.py <vieja.xml> <nueva.xml> <salida.dxf> [umbral] [paso] [area_min]
#
# area_min descarta las manchas sueltas de pocas celdas: sin ella salen ~3,900
# zonas y el plano deja de leerse. Lo descartado se contabiliza en el informe, no
# se esconde.
import os, sys, time
import xml.etree.ElementTree as ET
import numpy as np
import ezdxf
import shapely.geometry as sg
from shapely.ops import unary_union

NS = {'l': 'http://www.landxml.org/schema/LandXML-1.2'}
VIEJA = sys.argv[1]
NUEVA = sys.argv[2]
SALIDA = sys.argv[3]
UMBRAL = float(sys.argv[4]) if len(sys.argv) > 4 else 0.1
PASO = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
AREA_MIN = float(sys.argv[6]) if len(sys.argv) > 6 else 4.0

# (limite inferior, etiqueta, color ACI)
BANDAS = [(0.1, "0.1-0.25", 3), (0.25, "0.25-0.5", 2), (0.5, "0.5-1", 30),
          (1.0, "1-2", 1), (2.0, "mas de 2", 6)]


def leer(p):
    s = ET.parse(p).getroot().findall('.//l:Surface', NS)[0]
    v = []; m = {}
    for q in s.findall('.//l:P', NS):
        n, e, z = (float(x) for x in q.text.split())
        m[q.get('id')] = len(v); v.append((e, n, z))
    f = []
    for x in s.findall('.//l:F', NS):
        try: f.append(tuple(m[y] for y in x.text.split()))
        except KeyError: pass
    return s.get('name'), np.array(v), np.array(f, dtype=np.int64)


def rasterizar(V, F, x0, y0, nx, ny, paso):
    """Z de la superficie en cada nodo de la malla; NaN donde no hay triangulo."""
    Z = np.full((ny, nx), np.nan)
    T = V[F]
    for t in T:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
        i0 = max(0, int(np.floor((min(ax, bx, cx) - x0) / paso)))
        i1 = min(nx - 1, int(np.ceil((max(ax, bx, cx) - x0) / paso)))
        j0 = max(0, int(np.floor((min(ay, by, cy) - y0) / paso)))
        j1 = min(ny - 1, int(np.ceil((max(ay, by, cy) - y0) / paso)))
        if i1 < i0 or j1 < j0:
            continue
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if den == 0:
            continue
        gx = x0 + np.arange(i0, i1 + 1) * paso
        gy = y0 + np.arange(j0, j1 + 1) * paso
        X, Y = np.meshgrid(gx, gy)
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        l3 = 1.0 - l1 - l2
        dentro = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        if not dentro.any():
            continue
        sub = Z[j0:j1 + 1, i0:i1 + 1]
        sub[dentro] = (l1 * az + l2 * bz + l3 * cz)[dentro]
    return Z


def poligonos(mask, x0, y0, paso):
    """Agrupa las celdas marcadas en poligonos. Se comprimen primero en tiras
    horizontales para no unir millones de cuadraditos de uno en uno."""
    cajas = []
    ny, nx = mask.shape
    for j in range(ny):
        fila = mask[j]
        if not fila.any():
            continue
        d = np.diff(np.concatenate(([0], fila.view(np.int8), [0])))
        ini = np.flatnonzero(d == 1)
        fin = np.flatnonzero(d == -1)
        for a, b in zip(ini, fin):
            cajas.append(sg.box(x0 + (a - 0.5) * paso, y0 + (j - 0.5) * paso,
                                x0 + (b - 0.5) * paso, y0 + (j + 0.5) * paso))
    if not cajas:
        return []
    # union por trozos: unir 200,000 cajas de golpe se atraganta
    u = None
    for k in range(0, len(cajas), 20000):
        parte = unary_union(cajas[k:k + 20000])
        u = parte if u is None else unary_union([u, parte])
    gs = list(u.geoms) if u.geom_type != "Polygon" else [u]
    return [g for g in gs if g.geom_type == "Polygon"]


t0 = time.time()
nv, VV, VF = leer(VIEJA)
nn, NV_, NF = leer(NUEVA)
print(f"vieja {nv!r}: {len(VV):,} pts, {len(VF):,} caras")
print(f"nueva {nn!r}: {len(NV_):,} pts, {len(NF):,} caras")

x0 = min(VV[:, 0].min(), NV_[:, 0].min()); x1 = max(VV[:, 0].max(), NV_[:, 0].max())
y0 = min(VV[:, 1].min(), NV_[:, 1].min()); y1 = max(VV[:, 1].max(), NV_[:, 1].max())
nx = int(np.ceil((x1 - x0) / PASO)) + 1
ny = int(np.ceil((y1 - y0) / PASO)) + 1
print(f"malla: {nx:,} x {ny:,} nodos de {PASO} ft  "
      f"({(x1-x0):,.0f} x {(y1-y0):,.0f} ft)")

ZV = rasterizar(VV, VF, x0, y0, nx, ny, PASO)
print(f"  vieja rasterizada ({time.time()-t0:.0f}s)")
ZN = rasterizar(NV_, NF, x0, y0, nx, ny, PASO)
print(f"  nueva rasterizada ({time.time()-t0:.0f}s)")

valido = ~np.isnan(ZV) & ~np.isnan(ZN)
dz = np.where(valido, ZN - ZV, np.nan)
area_celda = PASO * PASO
n_val = int(valido.sum())
print(f"\nnodos con las dos superficies: {n_val:,}  ({n_val*area_celda:,.0f} ft2)")
print(f"solo en la vieja: {int((~np.isnan(ZV) & np.isnan(ZN)).sum())*area_celda:,.0f} ft2")
print(f"solo en la nueva: {int((np.isnan(ZV) & ~np.isnan(ZN)).sum())*area_celda:,.0f} ft2")
ad = np.abs(dz[valido])
print(f"\n|dz|: mediana {np.median(ad):.4f}  p95 {np.percentile(ad,95):.3f}  "
      f"p99 {np.percentile(ad,99):.3f}  max {ad.max():.3f} ft")
print(f"media con signo: {dz[valido].mean():+.4f} ft")

doc = ezdxf.new("R2010", setup=True)
msp = doc.modelspace()
doc.layers.add("DZ_LEYENDA", color=7)

# zonas que solo existen en una de las dos superficies: no son un desnivel, son
# falta de dato, y conviene verlas para no confundirlas con una diferencia de cota
for m, capa, col in ((~np.isnan(ZV) & np.isnan(ZN), "DZ_SOLO_VIEJA", 5),
                     (np.isnan(ZV) & ~np.isnan(ZN), "DZ_SOLO_NUEVA", 4)):
    if not m.any():
        continue
    doc.layers.add(capa, color=col)
    for g in poligonos(m, x0, y0, PASO):
        if g.area < AREA_MIN:
            continue
        msp.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={"layer": capa})
        for r in g.interiors:
            msp.add_lwpolyline(list(r.coords), close=True, dxfattribs={"layer": capa})

print(f"\nZONAS CON |dz| > {UMBRAL} ft   (manchas de menos de {AREA_MIN:g} ft2 aparte)")
print(f"{'banda (ft)':14s} {'signo':6s} {'zonas':>7s} {'area ft2':>12s} "
      f"{'% del total':>12s}  {'descartadas':>18s}")
print("-" * 80)
total = 0.0
descartado_total = 0.0
descartado_n = 0
focos = []
for k, (lo, etiq, color) in enumerate(BANDAS):
    if lo < UMBRAL:
        continue
    hi = BANDAS[k + 1][0] if k + 1 < len(BANDAS) else 1e9
    for signo, sufijo in ((+1, "SUBE"), (-1, "BAJA")):
        m = valido & (dz * signo >= lo) & (dz * signo < hi)
        if not m.any():
            continue
        capa = f"DZ_{sufijo}_{etiq.replace(' ', '').replace('.', 'p')}"
        doc.layers.add(capa, color=color if signo > 0 else color)
        todas = poligonos(m, x0, y0, PASO)
        gs = [g for g in todas if g.area >= AREA_MIN]
        a = sum(g.area for g in gs)
        desc = sum(g.area for g in todas if g.area < AREA_MIN)
        n_desc = len(todas) - len(gs)
        total += a
        descartado_total += desc
        descartado_n += n_desc
        print(f"{etiq:14s} {sufijo:6s} {len(gs):7,d} {a:12,.0f} "
              f"{100*a/(n_val*area_celda):11.2f}%  {n_desc:6,d} / {desc:8,.0f}")
        for g in gs:
            # El pico se mide SOLO en las celdas de esta zona y de esta banda. Si
            # se mide sobre el rectangulo envolvente se cuelan celdas vecinas de
            # otras bandas y salen disparates (una zona de 0.1-0.25 llegaba a
            # anunciar +3.68 ft, que era de la mancha de al lado).
            i0 = max(0, int((g.bounds[0]-x0)/PASO)); i1 = int((g.bounds[2]-x0)/PASO)+1
            j0 = max(0, int((g.bounds[1]-y0)/PASO)); j1 = int((g.bounds[3]-y0)/PASO)+1
            sub = dz[j0:j1, i0:i1]
            subm = m[j0:j1, i0:i1]
            vals = sub[subm]
            pico = (vals.max() if signo > 0 else vals.min()) if vals.size else 0.0
            focos.append((g.area, signo, etiq, pico, g.representative_point()))
            msp.add_lwpolyline(list(g.exterior.coords), close=True,
                               dxfattribs={"layer": capa})
            for r in g.interiors:
                msp.add_lwpolyline(list(r.coords), close=True,
                                   dxfattribs={"layer": capa})
            if g.area >= 200:
                p = g.representative_point()
                msp.add_text(f"{pico:+.2f} ft / {g.area:,.0f} ft2",
                             dxfattribs={"layer": "DZ_LEYENDA", "height": 3.0}) \
                   .set_placement((p.x, p.y))
print("-" * 80)
print(f"{'TOTAL':14s} {'':6s} {'':7s} {total:12,.0f} "
      f"{100*total/(n_val*area_celda):11.2f}%  {descartado_n:6,d} / {descartado_total:8,.0f}")
print(f"\n(las descartadas son manchas de pocas celdas: {descartado_n:,} zonas, "
      f"{descartado_total:,.0f} ft2 = {100*descartado_total/(n_val*area_celda):.2f}%)")

print("\nLOS 15 FOCOS MAS GRANDES  (ir a estas coordenadas en Civil 3D)")
print(f"{'#':>3s} {'banda':10s} {'signo':6s} {'area ft2':>10s} {'dz pico':>9s} "
      f"{'X':>14s} {'Y':>13s}")
for i, (a, signo, etiq, pico, p) in enumerate(sorted(focos, key=lambda t: -t[0])[:15], 1):
    print(f"{i:3d} {etiq:10s} {'SUBE' if signo>0 else 'BAJA':6s} {a:10,.0f} "
          f"{pico:+9.2f} {p.x:14,.1f} {p.y:13,.1f}")

print("\nLOS 10 PICOS MAS ALTOS  (por magnitud del desnivel, no por area)")
print(f"{'#':>3s} {'banda':10s} {'signo':6s} {'area ft2':>10s} {'dz pico':>9s} "
      f"{'X':>14s} {'Y':>13s}")
for i, (a, signo, etiq, pico, p) in enumerate(
        sorted(focos, key=lambda t: -abs(t[3]))[:10], 1):
    print(f"{i:3d} {etiq:10s} {'SUBE' if signo>0 else 'BAJA':6s} {a:10,.0f} "
          f"{pico:+9.2f} {p.x:14,.1f} {p.y:13,.1f}")

doc.saveas(SALIDA)
print(f"\nDXF -> {SALIDA}")
print(f"coordenadas reales VA83-SF; insertar en 0,0,0 escala 1")
print(f"tiempo: {time.time()-t0:.0f}s")
