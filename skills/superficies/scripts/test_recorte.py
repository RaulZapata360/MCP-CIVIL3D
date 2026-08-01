# -*- coding: utf-8 -*-
"""Pruebas de recortar_superficie.py contra casos con resultado analitico conocido.

Ejecutar: python test_recorte.py
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import ezdxf
from shapely.geometry import Polygon
from shapely.ops import unary_union

AQUI = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(AQUI, "recortar_superficie.py")
D = tempfile.mkdtemp(prefix="recorte_")
NS = {"lx": "http://www.landxml.org/schema/LandXML-1.2"}
PEND = 0.10                                    # plano z = 0.10 * x
RAZON = math.sqrt(1 + PEND ** 2)               # razon 3D/2D exacta de ese plano
ok = fail = 0


def check(nombre, cond, detalle=""):
    global ok, fail
    print(("  OK   " if cond else "  FALLA") + f" {nombre}" + (f"  {detalle}" if detalle else ""))
    if cond:
        ok += 1
    else:
        fail += 1


def tin_metrico(ruta, lado=200.0, n=20):
    """Malla regular sobre un plano inclinado, en metros."""
    paso, pid, ids, P, F = lado / n, 1, {}, [], []
    for i in range(n + 1):
        for j in range(n + 1):
            x, y = i * paso, j * paso
            ids[(i, j)] = pid
            P.append(f'\t\t\t\t\t<P id="{pid}">{y:.6f} {x:.6f} {PEND * x:.6f}</P>')
            pid += 1
    for i in range(n):
        for j in range(n):
            a, b, c, d = ids[(i, j)], ids[(i + 1, j)], ids[(i + 1, j + 1)], ids[(i, j + 1)]
            F.append(f'\t\t\t\t\t<F>{a} {b} {c}</F>')
            F.append(f'\t\t\t\t\t<F>{a} {c} {d}</F>')
    a2 = lado * lado
    xml = ['<?xml version="1.0"?>',
           '<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2">',
           '\t<Units>',
           '\t\t<Metric areaUnit="squareMeter" linearUnit="meter" volumeUnit="cubicMeter" '
           'temperatureUnit="celsius" pressureUnit="milliBars" diameterUnit="millimeter" '
           'angularUnit="decimal degrees" directionUnit="decimal degrees"></Metric>',
           '\t</Units>', '\t<Surfaces>', '\t\t<Surface name="Plano Test">',
           f'\t\t\t<Definition surfType="TIN" area2DSurf="{a2:.9f}" '
           f'area3DSurf="{a2 * RAZON:.9f}" elevMax="{PEND * lado:.4f}" elevMin="0.">',
           '\t\t\t\t<Pnts>'] + P + ['\t\t\t\t</Pnts>', '\t\t\t\t<Faces>'] + F + \
          ['\t\t\t\t</Faces>', '\t\t\t</Definition>', '\t\t</Surface>',
           '\t</Surfaces>', '</LandXML>']
    open(ruta, "w", encoding="utf-8").write("\n".join(xml))


def dxf_circulo(ruta, cx, cy, r):
    """Circulo exacto: LWPOLYLINE de 2 vertices con bulge=1 (dos semicircunferencias)."""
    doc = ezdxf.new("R2018")
    doc.modelspace().add_lwpolyline([(cx - r, cy, 0, 0, 1.0), (cx + r, cy, 0, 0, 1.0)],
                                    format="xyseb", close=True,
                                    dxfattribs={"layer": "CORTE"})
    doc.saveas(ruta)


def dxf_poly(ruta, pts, capa="CORTE"):
    doc = ezdxf.new("R2018")
    doc.modelspace().add_lwpolyline(pts, close=True, dxfattribs={"layer": capa})
    doc.saveas(ruta)


def correr(xml, dxf, extra=()):
    js = os.path.join(D, "res.json")
    r = subprocess.run([sys.executable, TOOL, "--xml", xml, "--dxf", dxf,
                        "--salida", D, "--json", js, *extra],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stdout + r.stderr
    return json.load(open(js, encoding="utf-8")), r.stdout


def area_landxml(ruta):
    d = ET.parse(ruta).getroot().find(".//lx:Surface/lx:Definition", NS)
    pts = {p.get("id"): tuple(float(v) for v in p.text.split())
           for p in d.find("lx:Pnts", NS)}
    tot, polis = 0.0, []
    for f in d.find("lx:Faces", NS):
        a, b, c = (pts[i] for i in f.text.split())
        p = Polygon([(a[1], a[0]), (b[1], b[0]), (c[1], c[0])])
        tot += p.area
        polis.append(p)
    return tot, unary_union(polis).area


# --- 1. arcos (bulges) + unidades metricas ---------------------------------
print("\n[1] Circulo con bulges sobre TIN metrico inclinado")
xml = os.path.join(D, "plano.xml")
dxf = os.path.join(D, "circulo.dxf")
tin_metrico(xml)
R = 50.0
dxf_circulo(dxf, 100.0, 100.0, R)
res, log = correr(xml, dxf, ["--sagitta", "0.001", "--prefijo", "t1", "--landxml-salida"])
if res is None:
    print(log); sys.exit(1)
teorica = math.pi * R ** 2
check("area 2D = pi*r^2", abs(res["area_interior_2d"] - teorica) / teorica < 1e-4,
      f'{res["area_interior_2d"]:.4f} vs {teorica:.4f}')
check("area 3D = 2D * sqrt(1+m^2)",
      abs(res["area_interior_3d"] - res["area_interior_2d"] * RAZON) < 1e-6,
      f'razon {res["area_interior_3d"] / res["area_interior_2d"]:.9f}')
check("unidad metrica detectada", res["unidad"]["etiqueta"] == "m2")
check("area total del TIN correcta", abs(res["area_total_2d"] - 40000.0) < 1e-6)
t, u = area_landxml(os.path.join(D, "t1_superficie_cortada.xml"))
check("LandXML exportado sin solapes", abs(t - u) < 1e-6, f"suma {t:.4f} union {u:.4f}")
check("LandXML exportado conserva el area", abs(t - res["area_interior_2d"]) < 1e-6)

# el error de teselado debe BAJAR al afinar la sagitta (no tener piso fijo)
errores = []
for sg in ("0.01", "0.001", "0.0001"):
    r_, _ = correr(xml, dxf, ["--sagitta", sg, "--prefijo", "tconv", "--sin-svg"])
    errores.append(abs(r_["area_interior_2d"] - teorica) / teorica)
check("el error de arcos converge al afinar --sagitta",
      errores[0] > errores[1] * 5 and errores[1] > errores[2] * 5,
      " -> ".join(f"{e:.2e}" for e in errores))

# --- 2. poligono no convexo (ear clipping) ---------------------------------
print("\n[2] Poligono en L (no convexo) -> ear clipping")
dxf2 = os.path.join(D, "ele.dxf")
L = [(20, 20), (150, 20), (150, 70), (70, 70), (70, 160), (20, 160)]
dxf_poly(dxf2, L)
res2, log2 = correr(xml, dxf2, ["--prefijo", "t2", "--landxml-salida"])
teor2 = Polygon(L).area
check("area 2D = area del poligono en L", abs(res2["area_interior_2d"] - teor2) < 1e-6,
      f'{res2["area_interior_2d"]:.4f} vs {teor2:.4f}')
t2, u2 = area_landxml(os.path.join(D, "t2_superficie_cortada.xml"))
check("LandXML no convexo sin solapes", abs(t2 - u2) < 1e-6)
check("LandXML no convexo conserva el area", abs(t2 - teor2) < 1e-6)

# --- 3. avisos y errores ---------------------------------------------------
print("\n[3] Avisos y manejo de errores")
res3, log3 = correr(xml, dxf2, ["--prefijo", "t3", "--sin-svg"])
check("cobertura 100% no gatilla aviso", "se sale de la superficie" not in log3)

dxf4 = os.path.join(D, "fuera.dxf")
dxf_poly(dxf4, [(500, 500), (600, 500), (600, 600), (500, 600)])
res4, log4 = correr(xml, dxf4, ["--prefijo", "t4", "--sin-svg"])
check("perimetro sin contacto -> avisa y no inventa area",
      res4 is None and "no se superponen" in log4 and "area interior = 0" in log4)

dxf5 = os.path.join(D, "parcial.dxf")
dxf_poly(dxf5, [(150, 150), (300, 150), (300, 300), (150, 300)])
res5, log5 = correr(xml, dxf5, ["--prefijo", "t5", "--sin-svg"])
check("perimetro que se sale -> avisa cobertura parcial",
      res5 is not None and "se sale de la superficie" in log5
      and abs(res5["area_interior_2d"] - 2500.0) < 1e-6,
      f'{res5["area_interior_2d"] if res5 else "-"} y cobertura {res5["cobertura_pct"]:.1f}%')

doc = ezdxf.new("R2018")
doc.modelspace().add_lwpolyline([(20, 20), (60, 20), (60, 60)], close=True,
                                dxfattribs={"layer": "A"})
doc.modelspace().add_lwpolyline([(80, 80), (120, 80), (120, 120)], close=True,
                                dxfattribs={"layer": "B"})
dxf6 = os.path.join(D, "dos.dxf")
doc.saveas(dxf6)
res6, log6 = correr(xml, dxf6, ["--prefijo", "t6", "--sin-svg"])
check("2 polilineas -> pide elegir en vez de adivinar",
      res6 is None and "polilineas candidatas" in log6)
res7, _ = correr(xml, dxf6, ["--prefijo", "t7", "--sin-svg", "--capa", "B"])
check("--capa selecciona la correcta", res7 and abs(res7["area_interior_2d"] - 800.0) < 1e-6)
res8, _ = correr(xml, dxf6, ["--prefijo", "t8", "--sin-svg", "--unir-todas"])
check("--unir-todas suma ambas", res8 and abs(res8["area_interior_2d"] - 1600.0) < 1e-6)

# --- 4. plano SVG (usa la skill de reportes) -------------------------------
print("\n[4] Plano de verificacion")
svg = os.path.join(D, "t1_verificacion.svg")
txt = open(svg, encoding="utf-8").read()
ET.fromstring(txt)
check("SVG valido y no vacio", len(txt) > 5000 and txt.rstrip().endswith("</svg>"),
      f"{len(txt) / 1024:.1f} KB")
check("leyenda con las tres capas", "TIN original" in txt and "Area interior" in txt
      and "Perimetro de corte" in txt)
check("norte y escala grafica", ">N</text>" in txt and " m</text>" in txt)
res9, _ = correr(xml, dxf2, ["--prefijo", "t9", "--tema", "oscuro"])
txt9 = open(os.path.join(D, "t9_verificacion.svg"), encoding="utf-8").read()
check("--tema oscuro cambia el fondo", '#1a1a19' in txt9)

print(f"\n{ok} OK / {fail} fallas   (salidas en {D})")
sys.exit(1 if fail else 0)
