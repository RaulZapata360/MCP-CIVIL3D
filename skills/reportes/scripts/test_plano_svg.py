# -*- coding: utf-8 -*-
"""Pruebas de plano_svg.py. Ejecutar: python test_plano_svg.py"""
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plano_svg import (PlanoSVG, PALETA, color_rampa, paso_redondo, _esc,
                       colores_mosaico, centroide_anillos, leer_landxml_todas,
                       descolapsar)

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


# --- 8. mosaico de N superficies -------------------------------------------
print("\n[8] Mosaico de N regiones")


def cuad(x, y, lado=10):
    return [(x, y), (x + lado, y), (x + lado, y + lado), (x, y + lado)]


cols = colores_mosaico(25, "claro")
check("colores_mosaico devuelve n colores", len(cols) == 25)
check("todos los colores del mosaico son distintos", len(set(cols)) == 25,
      f"{len(set(cols))} distintos")
check("colores consecutivos bien separados en tono (angulo aureo)",
      all(sum(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) for i in (1, 3, 5)) > 40
          for a, b in zip(cols, cols[1:])),
      "vecinos correlativos no se confunden")
lum_m = [sum(int(c[i:i + 2], 16) for i in (1, 3, 5)) / 3 for c in cols]
check("mosaico claro: luminosidad pareja (el rotulo es lo que identifica)",
      max(lum_m) - min(lum_m) < 60, f"rango {max(lum_m) - min(lum_m):.0f}")
check("mosaico oscuro mas oscuro que el claro",
      sum(sum(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in colores_mosaico(8, "oscuro"))
      < sum(sum(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in colores_mosaico(8, "claro")))
try:
    colores_mosaico(3, "fucsia")
    tm = False
except ValueError:
    tm = True
check("colores_mosaico rechaza tema invalido", tm)

p11 = PlanoSVG(titulo="Mosaico", unidad_lin="ft", ancho=1000, alto=800)
p11.mosaico([(f"{i:02d}", [cuad(i * 12, 0)]) for i in range(1, 6)],
            etiqueta="5 superficies (rotulo = nombre)")
txt11 = open(p11.guardar(os.path.join(D, "mosaico.svg")), encoding="utf-8").read()
check("un rotulo por region", sum(f">{i:02d}</text>" in txt11 for i in range(1, 6)) == 5)
check("leyenda de mosaico con UNA entrada, no N",
      txt11.count("superficies (rotulo = nombre)") == 1)
check("rotulos con halo del fondo (paint-order)", 'paint-order="stroke fill"' in txt11)
try:
    ET.fromstring(txt11)
    v11 = True
except ET.ParseError:
    v11 = False
check("SVG del mosaico bien formado", v11)

# el rotulo debe caer DENTRO de su region, no en el centro del plano
p12 = PlanoSVG(ancho=800, alto=600)
p12.mosaico([("A", [cuad(0, 0)]), ("B", [cuad(200, 200)])])
root12 = ET.parse(p12.guardar(os.path.join(D, "mosaico2.svg"))).getroot()
NS12 = "{http://www.w3.org/2000/svg}"
tex = {t.text: (float(t.get("x")), float(t.get("y")))
       for t in root12.iter(NS12 + "text") if t.text in ("A", "B")}
check("rotulo A al suroeste y B al noreste",
      tex["A"][0] < tex["B"][0] and tex["A"][1] > tex["B"][1],
      f"A={tex['A']} B={tex['B']}")

# centroide ponderado por area: no se va hacia donde hay mas vertices
denso = [(0, 0)] + [(i / 10.0, 0) for i in range(1, 10)] + [(1, 0), (1, 1), (0, 1)]
cx, cy = centroide_anillos([denso])
check("centroide ponderado por area, no media de vertices",
      abs(cx - 0.5) < 0.02 and abs(cy - 0.5) < 0.02, f"({cx:.3f}, {cy:.3f})")

# --- 9. escala de cota compartida y malla visible --------------------------
print("\n[9] Escala compartida y borde de malla")
p13 = PlanoSVG(titulo="Cota compartida", unidad_lin="ft")
p13.poligonos_graduados([(cuad(0, 0), 5.0)], vmin=0.0, vmax=100.0,
                        titulo_escala="cota (ft)")
txt13 = open(p13.guardar(os.path.join(D, "compartida.svg")), encoding="utf-8").read()
check("vmin/vmax explicitos mandan sobre el rango de los datos",
      ">0.00</text>" in txt13 and ">100.00</text>" in txt13)
c_solo = color_rampa(5.0, 5.0, 5.0, PALETA["claro"]["rampa"])
c_comp = color_rampa(5.0, 0.0, 100.0, PALETA["claro"]["rampa"])
check("una pieza sola se colorea distinto con escala compartida", c_solo != c_comp,
      f"{c_solo} vs {c_comp}")

p14 = PlanoSVG(unidad_lin="ft")
p14.poligonos_graduados([(cuad(0, 0), 1.0), (cuad(12, 0), 2.0)], borde_malla=True)
txt14 = open(p14.guardar(os.path.join(D, "malla.svg")), encoding="utf-8").read()
check("borde_malla dibuja las aristas", PALETA["claro"]["hairline"] in txt14
      and 'stroke="none"' not in txt14.split("<g stroke")[1][:40])
p15 = PlanoSVG(unidad_lin="ft")
p15.poligonos_graduados([(cuad(0, 0), 1.0)])
txt15 = open(p15.guardar(os.path.join(D, "sinmalla.svg")), encoding="utf-8").read()
check("sin borde_malla no se dibujan aristas", 'stroke="none"' in txt15)

# --- 10. lectura de LandXML multi-superficie -------------------------------
print("\n[10] LandXML con varias superficies")
XML = os.path.join(D, "multi.xml")
with open(XML, "w", encoding="utf-8") as fh:
    fh.write('<?xml version="1.0"?>\n<LandXML '
             'xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2">\n'
             ' <Units><Imperial linearUnit="USSurveyFoot" areaUnit="squareFoot"/></Units>\n'
             ' <Surfaces>\n')
    for k in (1, 2):
        fh.write(f'  <Surface name="S{k}"><Definition surfType="TIN"><Pnts>\n'
                 f'   <P id="1">0 {k * 100} 10</P><P id="2">0 {k * 100 + 10} 11</P>'
                 f'<P id="3">10 {k * 100} 12</P>\n'
                 f'  </Pnts><Faces>\n   <F>1 2 3</F>\n   <F i="1">1 2 3</F>\n'
                 f'  </Faces></Definition></Surface>\n')
    fh.write(' </Surfaces>\n</LandXML>\n')
todas, uni = leer_landxml_todas(XML)
check("lee las dos superficies", len(todas) == 2 and [n for n, _ in todas] == ["S1", "S2"])
check("unidad en pies detectada", uni == "ft")
check("descarta las caras invisibles i='1'", all(len(t) == 1 for _, t in todas),
      str([len(t) for _, t in todas]))
check("orden de coordenadas norte-este respetado",
      todas[0][1][0][0][0] == 100.0 and todas[0][1][0][0][1] == 0.0,
      f"primer punto E,N = {todas[0][1][0][0][:2]}")
try:
    vacio_xml = os.path.join(D, "vacio.xml")
    open(vacio_xml, "w", encoding="utf-8").write(
        '<?xml version="1.0"?><LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2"/>')
    leer_landxml_todas(vacio_xml)
    sin = False
except ValueError:
    sin = True
check("LandXML sin superficies levanta error claro", sin)

# --- 10b. rotulos que no se pisan ------------------------------------------
# Regresion: con 25 superficies, 'SI CV Top 01' y 'SI CV Top 02' salian
# encimados y no se leia ninguno de los dos.
print("\n[10b] Descolapse de rotulos")
ys_d = descolapsar([(100.0, 50.0, 80.0), (100.0, 52.0, 80.0), (100.0, 54.0, 80.0)],
                   alto=15.0)
check("rotulos apilados quedan separados", all(abs(a - b) >= 14.9 for a, b in
                                               [(ys_d[0], ys_d[1]), (ys_d[1], ys_d[2])]),
      str([round(v, 1) for v in ys_d]))
check("el conjunto se queda centrado donde estaba",
      abs(sum(ys_d) / 3 - 52.0) < 0.5, f"centro {sum(ys_d) / 3:.2f}")
ys_lejos = descolapsar([(0.0, 50.0, 40.0), (500.0, 50.0, 40.0)], alto=15.0)
check("rotulos lejanos en X no se mueven", ys_lejos == [50.0, 50.0], str(ys_lejos))
ys_ok = descolapsar([(0.0, 0.0, 40.0), (0.0, 100.0, 40.0)], alto=15.0)
check("rotulos ya separados no se tocan", ys_ok == [0.0, 100.0], str(ys_ok))

p17 = PlanoSVG(titulo="Rotulos apretados", unidad_lin="ft", ancho=900, alto=700)
# Tres regiones minusculas casi encimadas, con dos regiones lejanas que estiran
# la escala: asi las tres primeras caen a menos de 2 px una de otra, que es el
# caso que rompia. Ojo: si el plano es pequeno en unidades de terreno, 3 ft de
# separacion ya son 25 px y no hay colision que resolver.
p17.mosaico([("Uno", [cuad(50, 200.0, 1)]), ("Dos", [cuad(50, 200.6, 1)]),
             ("Tres", [cuad(50, 201.2, 1)]),
             ("SurLejano", [cuad(0, 0, 20)]), ("NorteLejano", [cuad(0, 400, 20)])])
root17 = ET.parse(p17.guardar(os.path.join(D, "apretados.svg"))).getroot()
tt = [(t.text, float(t.get("y"))) for t in root17.iter(NS12 + "text")
      if t.text in ("Uno", "Dos", "Tres")]
check("ningun par de rotulos se pisa en el SVG final",
      all(abs(a[1] - b[1]) >= 14.9 for i, a in enumerate(tt) for b in tt[i + 1:]),
      str([(n, round(y)) for n, y in tt]))
check("se dibuja linea guia al mover un rotulo",
      root17.find(f".//{NS12}g[@stroke='{PALETA['claro']['muted']}']") is not None)

# --- 11. maquetacion del mosaico -------------------------------------------
print("\n[11] Mosaico dentro del lienzo")
p16 = PlanoSVG(titulo="Franja con muchas regiones", subtitulo="angosta", unidad_lin="ft")
p16.mosaico([(f"{i:02d}", [cuad(0, i * 12, 8)]) for i in range(30)],
            etiqueta="30 superficies (rotulo = nombre)")
W16, H16, mal16 = desborde(p16.guardar(os.path.join(D, "mosaico_angosto.svg")))
check("mosaico en terreno angosto: nada fuera del lienzo", not mal16, str(mal16[:3]))

print(f"\n{ok} OK / {fail} fallas   (salidas en {D})")
sys.exit(1 if fail else 0)
