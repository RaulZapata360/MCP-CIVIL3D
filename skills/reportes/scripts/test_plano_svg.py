# -*- coding: utf-8 -*-
"""Pruebas de plano_svg.py. Ejecutar: python test_plano_svg.py"""
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plano_svg import PlanoSVG, PALETA, color_rampa, paso_redondo, _esc

D = tempfile.mkdtemp(prefix="plano_svg_")
ok = fail = 0


def check(nombre, cond, detalle=""):
    global ok, fail
    print(("  OK   " if cond else "  FALLA") + f" {nombre}" + (f"  {detalle}" if detalle else ""))
    if cond:
        ok += 1
    else:
        fail += 1


def coords_de(svg, patron):
    """Extrae los pares x,y del primer path que contenga el patron dado."""
    for m in re.finditer(r'<path d="([^"]+)"', svg):
        d = m.group(1)
        if patron in d or patron == "":
            return [(float(a), float(b)) for a, b in
                    re.findall(r'([-\d.]+) ([-\d.]+)', d)]
    return []


# --- 1. transformacion: escala unica y norte arriba ------------------------
print("\n[1] Transformacion geometrica")
cuadrado = [(0, 0), (100, 0), (100, 100), (0, 100)]
p = PlanoSVG(titulo="T", unidad_lin="m", ancho=1000, alto=800)
p.poligonos([cuadrado], rol="serie1", etiqueta="cuadrado")
r1 = p.guardar(os.path.join(D, "cuadrado.svg"))
svg = open(r1, encoding="utf-8").read()
pts = coords_de(svg, "")
xs = [q[0] for q in pts]
ys = [q[1] for q in pts]
ancho_px, alto_px = max(xs) - min(xs), max(ys) - min(ys)
check("escala identica en X e Y (cuadrado sigue cuadrado)",
      abs(ancho_px - alto_px) < 0.5, f"{ancho_px:.2f} x {alto_px:.2f} px")

rect = [(0, 0), (200, 0), (200, 50), (0, 50)]
p2 = PlanoSVG(ancho=1000, alto=800)
p2.poligonos([rect], rol="serie1")
svg2 = open(p2.guardar(os.path.join(D, "rect.svg")), encoding="utf-8").read()
pts2 = coords_de(svg2, "")
w2 = max(q[0] for q in pts2) - min(q[0] for q in pts2)
h2 = max(q[1] for q in pts2) - min(q[1] for q in pts2)
check("relacion de aspecto preservada (4:1)", abs(w2 / h2 - 4.0) < 0.02,
      f"{w2 / h2:.4f}")

# el vertice de mayor norte debe quedar con menor y en pixeles
p3 = PlanoSVG(ancho=800, alto=600)
p3.poligonos([[(0, 0), (100, 0), (50, 100)]], rol="serie1")
svg3 = open(p3.guardar(os.path.join(D, "tri.svg")), encoding="utf-8").read()
t = coords_de(svg3, "")
check("norte arriba (Y invertido)", t[2][1] < t[0][1],
      f"vertice norte y={t[2][1]:.1f} vs sur y={t[0][1]:.1f}")

# --- 2. XML valido y escapado ---------------------------------------------
print("\n[2] SVG bien formado")
p4 = PlanoSVG(titulo="Sup & Cia <test>", subtitulo="a > b & c", unidad_lin="m")
p4.poligonos([cuadrado], rol="serie1", etiqueta="A & B")
p4.nota("nota con < y &")
r4 = p4.guardar(os.path.join(D, "escape.svg"))
txt4 = open(r4, encoding="utf-8").read()
try:
    ET.fromstring(txt4)
    valido = True
except ET.ParseError as e:
    valido = False
    print("      ", e)
check("XML valido con &, < y > en los textos", valido)
check("los textos van escapados", "&amp;" in txt4 and "&lt;test&gt;" in txt4)
check("_esc escapa los tres caracteres", _esc("a&b<c>d") == "a&amp;b&lt;c&gt;d")

# --- 3. leyenda y chrome ---------------------------------------------------
print("\n[3] Leyenda, escala y norte")
p5 = PlanoSVG(titulo="Plano", unidad_lin="ft")
p5.poligonos([cuadrado], rol="contexto", etiqueta="contexto")
p5.poligonos([[(20, 20), (60, 20), (60, 60), (20, 60)]], rol="serie1", etiqueta="area")
p5.lineas([[(0, 0), (100, 100)]], rol="serie2", etiqueta="eje")
txt5 = open(p5.guardar(os.path.join(D, "leyenda.svg")), encoding="utf-8").read()
for etq in ("contexto", "area", "eje"):
    check(f"leyenda incluye '{etq}'", f">{etq}</text>" in txt5)
check("norte dibujado", ">N</text>" in txt5)
check("escala grafica con unidad", re.search(r'>\d+ ft</text>', txt5) is not None)
check("paso_redondo da numeros 1/2/5", [paso_redondo(v) for v in (3, 7, 45, 230)]
      == [2, 5, 50, 200], str([paso_redondo(v) for v in (3, 7, 45, 230)]))

# --- 4. rampa secuencial ---------------------------------------------------
print("\n[4] Rampa secuencial y gradiente")
p6 = PlanoSVG(titulo="Cotas", unidad_lin="m")
p6.poligonos_graduados([([(i, 0), (i + 1, 0), (i + 1, 1)], float(i)) for i in range(10)],
                       titulo_escala="cota (m)")
txt6 = open(p6.guardar(os.path.join(D, "rampa.svg")), encoding="utf-8").read()
check("gradiente definido", "<linearGradient" in txt6 and 'fill="url(#g1)"' in txt6)
check("extremos de la escala rotulados", ">0.00</text>" in txt6 and ">9.00</text>" in txt6)
ramp = PALETA["claro"]["rampa"]
check("rampa de un solo tono, no arcoiris", color_rampa(0, 0, 1, ramp) == ramp[0]
      and color_rampa(1, 0, 1, ramp) == ramp[-1])
lum = [sum(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in ramp]
check("luminosidad monotona en la rampa", all(a > b for a, b in zip(lum, lum[1:])),
      str(lum))
lum_o = [sum(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in PALETA["oscuro"]["rampa"]]
check("rampa oscura tambien monotona", all(a < b for a, b in zip(lum_o, lum_o[1:])),
      str(lum_o))

# --- 5. temas --------------------------------------------------------------
print("\n[5] Temas")
p7 = PlanoSVG(titulo="Oscuro", tema="oscuro")
p7.poligonos([cuadrado], rol="serie1", etiqueta="a")
txt7 = open(p7.guardar(os.path.join(D, "oscuro.svg")), encoding="utf-8").read()
check("tema oscuro usa fondo y serie oscuros",
      PALETA["oscuro"]["fondo"] in txt7 and PALETA["oscuro"]["serie1"] in txt7)
check("tema oscuro no arrastra colores del claro", PALETA["claro"]["serie1"] not in txt7)
try:
    PlanoSVG(tema="fucsia")
    malo = False
except ValueError:
    malo = True
check("tema invalido levanta error", malo)

# --- 6. errores ------------------------------------------------------------
print("\n[6] Errores")
try:
    PlanoSVG(titulo="vacio").guardar(os.path.join(D, "vacio.svg"))
    vacio = False
except ValueError:
    vacio = True
check("plano sin geometria levanta error claro", vacio)
try:
    PlanoSVG().poligonos([cuadrado], rol="serie99")
    rol = False
except ValueError:
    rol = True
check("rol desconocido levanta error", rol)
p8 = PlanoSVG(titulo="filtra")
p8.poligonos([[(0, 0), (1, 1)]], rol="serie1")       # menos de 3 puntos
check("poligonos degenerados se ignoran sin reventar", len(p8._capas) == 0)


# --- 7. maquetacion: nada se sale del lienzo -------------------------------
# Regresion: el norte se dibujaba en x=1420 sobre un lienzo de 1200 porque se
# usaba el origen del contenido centrado como si fuera el del marco.
print("\n[7] Maquetacion dentro del lienzo")
NS = "{http://www.w3.org/2000/svg}"


def desborde(ruta, margen=44):
    root = ET.parse(ruta).getroot()
    W, H = float(root.get("width")), float(root.get("height"))
    peor = []
    for t in root.iter(NS + "text"):
        x, y = float(t.get("x")), float(t.get("y"))
        fs = float(t.get("font-size", 12))
        anc = len(t.text or "") * fs * 0.58
        anchor = t.get("text-anchor", "start")
        x0 = x if anchor == "start" else (x - anc / 2 if anchor == "middle" else x - anc)
        if x0 < 0 or x0 + anc > W or y < 0 or y > H:
            peor.append((t.text, round(x0), round(x0 + anc), round(y)))
    for r in root.iter(NS + "rect"):
        x, w_ = float(r.get("x", 0)), float(r.get("width", 0))
        if x < -0.5 or x + w_ > W + 0.5:
            peor.append(("rect", round(x), round(x + w_), 0))
    return W, H, peor


# terreno angosto y alto: el caso que destapo el bug
angosto = [(0, 0), (30, 0), (30, 400), (0, 400)]
p9 = PlanoSVG(titulo="Terreno angosto", subtitulo="franja vertical", unidad_lin="m")
p9.poligonos([angosto], rol="contexto", etiqueta="franja")
p9.poligonos([[(5, 100), (25, 100), (25, 300), (5, 300)]], rol="serie1",
             etiqueta="interior")
p9.lineas([[(0, 0), (30, 400)]], rol="serie2", etiqueta="diagonal")
W9, H9, mal9 = desborde(p9.guardar(os.path.join(D, "angosto.svg")))
check("terreno angosto: nada fuera del lienzo", not mal9, str(mal9[:3]))

# terreno ancho y bajo
ancho_bajo = [(0, 0), (500, 0), (500, 40), (0, 40)]
p10 = PlanoSVG(titulo="Terreno ancho", unidad_lin="ft")
p10.poligonos([ancho_bajo], rol="contexto", etiqueta="franja horizontal larga")
p10.poligonos_graduados([([(i * 50, 0), ((i + 1) * 50, 0), ((i + 1) * 50, 40)], i * 1.0)
                         for i in range(10)], titulo_escala="cota (ft)")
W10, H10, mal10 = desborde(p10.guardar(os.path.join(D, "ancho.svg")))
check("terreno ancho + gradiente: nada fuera del lienzo", not mal10, str(mal10[:3]))

# el marco debe coincidir con el area de dibujo, no con el contenido centrado
root9 = ET.parse(os.path.join(D, "angosto.svg")).getroot()
marcos = [r for r in root9.iter(NS + "rect") if r.get("fill") == "none"]
check("marco del area de dibujo bien ubicado",
      len(marcos) == 1 and abs(float(marcos[0].get("x")) - 44) < 0.6
      and abs(float(marcos[0].get("width")) - (1200 - 88)) < 0.6,
      f'x={marcos[0].get("x")} w={marcos[0].get("width")}' if marcos else "sin marco")

print(f"\n{ok} OK / {fail} fallas   (salidas en {D})")
sys.exit(1 if fail else 0)
