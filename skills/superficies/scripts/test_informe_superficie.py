# -*- coding: utf-8 -*-
"""Pruebas de informe_superficie.py. Ejecutar: python test_informe_superficie.py"""
import math
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import informe_superficie as inf  # noqa: E402

D = tempfile.mkdtemp(prefix="informe_superficie_")
ok = fail = 0


def check(nombre, cond, detalle=""):
    global ok, fail
    print(("  OK   " if cond else "  FALLA") + f" {nombre}" + (f"  {detalle}" if detalle else ""))
    if cond:
        ok += 1
    else:
        fail += 1


# ---------------------------------------------------------- geometria util --
def escribir_landxml(ruta, nombre, puntos_en, caras, unidad="meter", extra_defn=""):
    """puntos_en: dict id -> (E, N, Z). Escribe en el orden LandXML (N E Z)."""
    pnts = "\n".join(f'<P id="{i}">{n:.6f} {e:.6f} {z:.6f}</P>' for i, (e, n, z) in puntos_en.items())
    faces = "\n".join(f'<F>{a} {b} {c}</F>' for a, b, c in caras)
    xml = f"""<?xml version="1.0"?>
<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2">
  <Units><Metric linearUnit="{unidad}" areaUnit="squareMeter" volumeUnit="cubicMeter"
          temperatureUnit="celsius" pressureUnit="mmHG"/></Units>
  <Surfaces>
    <Surface name="{nombre}">
      <Definition surfType="TIN" {extra_defn}>
        <Pnts>{pnts}</Pnts>
        <Faces>{faces}</Faces>
      </Definition>
    </Surface>
  </Surfaces>
</LandXML>"""
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(xml)
    return ruta


def plano_inclinado(m_este, m_norte, z0, x0, y0, x1, y1):
    """Genera dos triangulos que representan el plano z = z0 + m_este*(E-x0) + m_norte*(N-y0)."""
    def z(e, n):
        return z0 + m_este * (e - x0) + m_norte * (n - y0)
    p = {1: (x0, y0, z(x0, y0)), 2: (x1, y0, z(x1, y0)),
         3: (x1, y1, z(x1, y1)), 4: (x0, y1, z(x0, y1))}
    caras = [(1, 2, 3), (1, 3, 4)]
    return p, caras


# --- 1. lectura LandXML y area ----------------------------------------------
print("\n[1] Lectura LandXML y area")
pts, caras = plano_inclinado(0.0, 0.0, 5.0, 0, 0, 100, 100)
ruta_plano = escribir_landxml(os.path.join(D, "plano_horizontal.xml"), "Plano_Horizontal", pts, caras)
nombre, tris, meta, unidad = inf.leer_landxml(ruta_plano)
check("nombre de superficie leido", nombre == "Plano_Horizontal")
check("2 triangulos visibles", len(tris) == 2)
a2 = sum(inf.area2d(t) for t in tris)
check("area 2D de un cuadrado de 100x100 = 10000", abs(a2 - 10000.0) < 1e-6, f"{a2}")
check("superficie horizontal: razon 3D/2D = 1", all(abs(inf.razon_3d(t) - 1.0) < 1e-9 for t in tris))

# --- 2. pendiente y orientacion analiticas ----------------------------------
print("\n[2] Pendiente y orientacion (plano inclinado analitico)")
# z = 0.1*E: sube hacia el Este 10%. La ladera desciende hacia el Oeste (270 grados).
pts2, caras2 = plano_inclinado(0.10, 0.0, 0.0, 0, 0, 100, 100)
tris2 = [tuple(pts2[i] for i in c) for c in caras2]
for t in tris2:
    check("pendiente = 10.000%", abs(inf.pendiente_pct(t) - 10.0) < 1e-6, f"{inf.pendiente_pct(t)}")
    check("orientacion = 270 (Oeste, desciende contra el Este)",
          abs(inf.orientacion_deg(t) - 270.0) < 1e-6, f"{inf.orientacion_deg(t)}")

# z sube hacia el Norte: desciende hacia el Sur (180 grados)
pts3, caras3 = plano_inclinado(0.0, 0.20, 0.0, 0, 0, 100, 100)
tris3 = [tuple(pts3[i] for i in c) for c in caras3]
for t in tris3:
    check("pendiente = 20.000% (gradiente solo en N)", abs(inf.pendiente_pct(t) - 20.0) < 1e-6)
    check("orientacion = 180 (Sur, desciende contra el Norte)",
          abs(inf.orientacion_deg(t) - 180.0) < 1e-6, f"{inf.orientacion_deg(t)}")

# invertir el orden de los vertices no debe cambiar pendiente ni orientacion
t_inv = (tris2[0][2], tris2[0][1], tris2[0][0])
check("orden de vertices no afecta la pendiente", abs(inf.pendiente_pct(t_inv) - inf.pendiente_pct(tris2[0])) < 1e-9)
check("orden de vertices no afecta la orientacion", abs(inf.orientacion_deg(t_inv) - inf.orientacion_deg(tris2[0])) < 1e-9)

# --- 3. zonificacion: invariante de area total ------------------------------
print("\n[3] Zonificacion")
ptsz, carasz = plano_inclinado(0.0, 0.0, 0.0, 0, 0, 100, 100)
# malla mas fina para tener variedad de cotas: usamos el plano inclinado con pendiente
ptsz2, carasz2 = plano_inclinado(0.30, 0.0, 0.0, 0, 0, 100, 100)  # cotas 0..30
trisz = [tuple(ptsz2[i] for i in c) for c in carasz2]
bandas = inf.resolver_bandas("6", 0.0, 30.0)
zonas = inf.zonificar(trisz, inf.cota_media, bandas)
suma = sum(z["area2d"] for z in zonas)
check("suma de areas por banda == area total (sin perdidas ni duplicados)",
      abs(suma - sum(inf.area2d(t) for t in trisz)) < 1e-6, f"{suma}")
check("6 bandas generadas", len(zonas) == 6)

bandas_pend = inf.bandas_desde_cortes([0, 5, 10, 15, 25])
check("ultima banda de pendiente es abierta (inf)", math.isinf(bandas_pend[-1][1]))
etiqueta_abierta = inf.etiqueta_banda(25, math.inf, "%")
check("etiqueta de banda abierta usa '>'", etiqueta_abierta.startswith(">"), etiqueta_abierta)

# --- 4. rosa de orientacion --------------------------------------------------
print("\n[4] Rosa de orientacion")
centros, valores, excluidos = inf.rosa_orientacion(tris2, n_sectores=8)
idx_270 = centros.index(270.0)
check("toda el area cae en el sector de 270 grados (unica pendiente)",
      valores[idx_270] > 0 and sum(v for i, v in enumerate(valores) if i != idx_270) < 1e-6)

pts_planos, caras_planos = plano_inclinado(0.0, 0.0, 5.0, 0, 0, 100, 100)
tris_planos = [tuple(pts_planos[i] for i in c) for c in caras_planos]
_, _, excluidos_planos = inf.rosa_orientacion(tris_planos, n_sectores=8)
check("triangulos planos se excluyen de la rosa (sin orientacion fiable)", excluidos_planos == 2)

# --- 5. indice espacial y muestreo -------------------------------------------
print("\n[5] Indice espacial")
idx = inf.indice_espacial(tris2, 20.0)
z_centro = inf.cota_en(idx, 20.0, 50.0, 50.0)
check("cota interpolada en el centro (z=0.1*50=5.0)", abs(z_centro - 5.0) < 1e-9, f"{z_centro}")
z_fuera = inf.cota_en(idx, 20.0, 500.0, 500.0)
check("punto fuera de la superficie devuelve None", z_fuera is None)

# --- 6. volumen por grilla: dos planos paralelos ----------------------------
print("\n[6] Volumen por grilla (analitico)")
pts_base, caras_base = plano_inclinado(0.0, 0.0, 0.0, 0, 0, 100, 100)
pts_dis, caras_dis = plano_inclinado(0.0, 0.0, 2.0, 0, 0, 100, 100)   # +2m de relleno uniforme
tris_base = [tuple(pts_base[i] for i in c) for c in caras_base]
tris_dis = [tuple(pts_dis[i] for i in c) for c in caras_dis]
vol = inf.volumen_grid(tris_base, tris_dis, espaciamiento=5.0)
esperado = 100.0 * 100.0 * 2.0  # area x espesor constante
check("relleno uniforme de 2m sobre 100x100 = 20000 (grilla exacta, sin borde)",
      abs(vol["relleno_volumen"] - esperado) < 1e-6, f"{vol['relleno_volumen']}")
check("sin corte cuando el diseño esta uniformemente por encima", vol["corte_volumen"] < 1e-9)
check("cobertura 100% (grilla alineada con ambas superficies)", abs(vol["cobertura_pct"] - 100.0) < 1e-6)

# Caso inverso: diseño por debajo => corte
pts_dis2, caras_dis2 = plano_inclinado(0.0, 0.0, -1.5, 0, 0, 100, 100)
tris_dis2 = [tuple(pts_dis2[i] for i in c) for c in caras_dis2]
vol2 = inf.volumen_grid(tris_base, tris_dis2, espaciamiento=5.0)
check("corte uniforme de 1.5m = 15000", abs(vol2["corte_volumen"] - 15000.0) < 1e-6, f"{vol2['corte_volumen']}")
check("neto negativo cuando predomina el corte", vol2["neto_volumen"] < 0)

# superficies que no se solapan levantan error claro
pts_lejos, caras_lejos = plano_inclinado(0.0, 0.0, 0.0, 1000, 1000, 1100, 1100)
tris_lejos = [tuple(pts_lejos[i] for i in c) for c in caras_lejos]
try:
    inf.volumen_grid(tris_base, tris_lejos, espaciamiento=5.0)
    sin_solape = False
except ValueError:
    sin_solape = True
check("superficies sin solape levantan ValueError", sin_solape)

# --- 7. eje: estaciones y perfil ---------------------------------------------
print("\n[7] Muestreo de perfil a lo largo de un eje")
eje = [(0.0, 50.0), (100.0, 50.0)]  # recta E-W a N=50
muestras, longitud = inf.muestrear_perfil(tris2, eje, intervalo=25.0)
check("longitud del eje = 100", abs(longitud - 100.0) < 1e-9)
check("5 muestras (0,25,50,75,100)", len(muestras) == 5, str(len(muestras)))
check("cota en estacion 50 = 0.1*50 = 5.0",
      abs(next(m["cota"] for m in muestras if abs(m["estacion"] - 50.0) < 1e-6) - 5.0) < 1e-6)

# --- 8. informe HTML completo ------------------------------------------------
print("\n[8] Generacion de informe HTML")


class NS:
    pass


args = NS()
args.xml = ruta_plano
args.superficie = None
args.xml_disenio = None
args.superficie_disenio = None
args.eje_dxf = None
args.capa_eje = None
args.intervalo_perfil = 25.0
args.transectos = False
args.intervalo_transectos = 50.0
args.ancho_izq = 15.0
args.ancho_der = 15.0
args.paso_transecto = 1.0
args.bandas_cota = None
args.bandas_pendiente = None
args.sectores_orientacion = 8
args.espaciamiento_volumen = None
args.proyecto = "Proyecto <Prueba> & Cia"
args.titulo = None
args.tema = "claro"
args.salida = os.path.join(D, "informe.html")
args.json = os.path.join(D, "informe.json")

res = inf.generar_informe(args)
check("informe HTML se genero", os.path.exists(res["archivo_html"]))
check("informe JSON se genero", os.path.exists(res["archivo_json"]))
contenido = open(res["archivo_html"], encoding="utf-8").read()
for etiqueta in ("titleblock", "Zonificacion de cotas", "Zonificacion de pendientes",
                  "Orientacion de laderas", "Hallazgos y recomendaciones", "@media print"):
    check(f"informe contiene bloque '{etiqueta}'", etiqueta in contenido)
check("nombre de proyecto con caracteres especiales queda escapado",
      "&lt;Prueba&gt;" in contenido and "&amp;" in contenido)
check("no quedan '<Prueba>' sin escapar (riesgo de HTML roto)", "<Prueba>" not in contenido)

# el HTML debe contener SVG bien formado dentro (al menos un <svg ...>...</svg> parseable)
import re
m = re.search(r"<svg[^>]*>.*?</svg>", contenido, re.DOTALL)
check("hay al menos un SVG incrustado", m is not None)
if m:
    try:
        ET.fromstring(m.group(0))
        svg_valido = True
    except ET.ParseError as e:
        svg_valido = False
        print("      ", e)
    check("el primer SVG incrustado es XML valido", svg_valido)

# --- 9. informe con dos superficies (corte/relleno) --------------------------
print("\n[9] Informe con superficie de diseño (volumen)")
ruta_dis = escribir_landxml(os.path.join(D, "plano_disenio.xml"), "Plano_Disenio", pts_dis, caras_dis)
args2 = NS()
args2.__dict__.update(args.__dict__)
args2.xml = os.path.join(D, "plano_base.xml")
escribir_landxml(args2.xml, "Plano_Base", pts_base, caras_base)
args2.xml_disenio = ruta_dis
args2.superficie = None
args2.superficie_disenio = None
args2.salida = os.path.join(D, "informe_volumen.html")
args2.json = os.path.join(D, "informe_volumen.json")
res2 = inf.generar_informe(args2)
check("informe con volumen incluye la seccion de computo volumetrico",
      "Computo volumetrico" in open(res2["archivo_html"], encoding="utf-8").read())
check("JSON reporta el volumen neto esperado (~20000, relleno uniforme)",
      res2["volumen"] is not None and abs(res2["volumen"]["neto_volumen"] - 20000.0) < 1e-3,
      str(res2["volumen"]))

print(f"\n{ok} OK / {fail} fallas   (salidas en {D})")
sys.exit(1 if fail else 0)
