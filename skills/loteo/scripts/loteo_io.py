# -*- coding: utf-8 -*-
"""Lectura del loteo desde un DXF: lotes, NPT, vialidad y medianeros.

Es la entrada del metodo. Un DXF de loteo trae los deslindes dibujados y los
rotulos con el numero de lote y su cota de piso; NO trae las calles como
poligonos ni los medianeros como entidades. Todo eso se deduce aqui.

Los nombres de capa y el formato del rotulo cambian de un proyecto a otro, asi
que son parametros. El resto del metodo (terrazas_lib, vialidad_lib) no depende
de esto: si el loteo llega por otra via, basta con producir la misma estructura
`[{nombre, poligono, area}]` y el diccionario de NPT.
"""
import collections
import math
import re

import shapely.geometry as sg
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree

CAPA_LOTES = "LOTE TERRENO"
PATRON_NPT = r"NPT\s*([\d]+(?:[.,]\d+)?)"
TOL_VECINO = 0.30       # m — holgura para considerar dos lotes vecinos
LARGO_MIN_MED = 1.0     # m — deslinde mas corto: toque de esquina, no medianero


# ------------------------------------------------------------------- lotes
def _limpiar_anillo(poly, tol=0.05):
    """Elimina vertices duplicados consecutivos.

    Los DXF de loteo traen lados de largo practicamente nulo (vertices dobles
    del dibujo). Sin limpiarlos, esos lotes figuran con deslindes de 0,00 m y el
    conteo de lados sale inflado. Ningun deslinde real mide menos de 5 cm."""
    cs = list(poly.exterior.coords)[:-1]
    out = []
    for p in cs:
        if not out or math.dist(out[-1], p) >= tol:
            out.append(p)
    while len(out) > 3 and math.dist(out[0], out[-1]) < tol:
        out.pop()
    if len(out) < 3:
        return poly
    q = sg.Polygon(out)
    if not q.is_valid:
        q = q.buffer(0)
    return q if q.geom_type == "Polygon" and not q.is_empty else poly


def leer_lotes(dxf, capa=CAPA_LOTES, patron_nombre=r"\d+|AV\s*\d+"):
    """Devuelve (lotes, etiquetas). Cada lote: {nombre, poligono, area, origen}.

    Se usan los anillos CERRADOS de la capa de lotes -- geometria de autor,
    exacta. Los lotes cuyo contorno no se dibujo cerrado se recuperan
    poligonizando el entramado completo (anillos + polilineas abiertas).

    Se consideran cerrados los que traen el flag o cuyo primer y ultimo vertice
    distan menos de 0,5 m: muchos dibujos los cierran 'a ojo', sin el flag.

    OJO CON LOS NUMEROS REPETIDOS. Es habitual que dos lotes fisicos distintos
    compartan numero. Se desambiguan con sufijo -A/-B en orden sur->norte, para
    que el nombre sea estable entre corridas."""
    import ezdxf
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()

    etiquetas = []
    for e in msp:
        if e.dxftype() != "MTEXT":
            continue
        t = re.sub(r"\s+", " ", e.plain_text()).strip()
        if re.fullmatch(patron_nombre, t):
            ins = e.dxf.insert
            etiquetas.append((t, sg.Point(ins.x, ins.y)))

    anillos, abiertas = [], []
    for e in msp:
        if e.dxftype() != "LWPOLYLINE" or e.dxf.layer != capa:
            continue
        pts = [(p[0], p[1]) for p in e.get_points()]
        if len(pts) < 3:
            continue
        d = math.dist(pts[0], pts[-1])
        if e.closed or d < 0.5:
            if d > 1e-9:
                pts.append(pts[0])
            if len(pts) >= 4:
                p = sg.Polygon(pts)
                anillos.append(p if p.is_valid else p.buffer(0))
        else:
            abiertas.append(sg.LineString(pts))

    hallados = []
    for p in anillos:
        dentro = [t for t, pt in etiquetas if p.contains(pt)]
        if len(dentro) == 1:
            hallados.append({"etiqueta": dentro[0], "poligono": p,
                             "origen": "anillo cerrado"})

    cubiertas = collections.Counter(x["etiqueta"] for x in hallados)
    pend = [(t, pt) for t, pt in etiquetas
            if cubiertas[t] < sum(1 for tt, _ in etiquetas if tt == t)]
    if pend:
        lineas = [sg.LineString(p.exterior.coords) for p in anillos] + abiertas
        ya = unary_union([x["poligono"] for x in hallados]) if hallados else None
        for f in polygonize(unary_union(lineas)):
            dentro = [t for t, pt in pend if f.contains(pt)]
            if len(dentro) == 1 and (ya is None
                                     or not f.representative_point().within(ya)):
                hallados.append({"etiqueta": dentro[0], "poligono": f,
                                 "origen": "poligonizacion"})

    porlbl = collections.defaultdict(list)
    for x in hallados:
        porlbl[x["etiqueta"]].append(x)
    lotes = []
    for etiqueta, grupo in porlbl.items():
        grupo.sort(key=lambda x: (x["poligono"].centroid.y, x["poligono"].centroid.x))
        for i, x in enumerate(grupo):
            x["nombre"] = etiqueta if len(grupo) == 1 else f"{etiqueta}-{chr(65 + i)}"
            x["poligono"] = _limpiar_anillo(x["poligono"])
            x["area"] = x["poligono"].area
            lotes.append(x)

    def clave(x):
        m = re.match(r"(\d+)", x["nombre"])
        return (0, int(m.group(1)), x["nombre"]) if m else (1, 0, x["nombre"])

    lotes.sort(key=clave)
    return lotes, etiquetas


def leer_npt(dxf, lotes, patron=PATRON_NPT):
    """nombre de lote -> NPT, leyendo el rotulo que cae dentro de cada lote.

    Devuelve tambien la lista de avisos: rotulos malformados o lotes sin NPT.
    Conviene mirarlos: un 'NPT 12100m' sin punto decimal pasa desapercibido y
    mete un lote a 12 km de altura."""
    import ezdxf
    doc = ezdxf.readfile(dxf)
    marcas = []
    for e in doc.modelspace():
        if e.dxftype() != "MTEXT":
            continue
        t = re.sub(r"\s+", " ", e.plain_text()).strip()
        m = re.search(patron, t, re.I)
        if m:
            ins = e.dxf.insert
            marcas.append((float(m.group(1).replace(",", ".")),
                            sg.Point(ins.x, ins.y), t))

    npt, avisos = {}, []
    for l in lotes:
        dentro = [(v, t) for v, p, t in marcas if l["poligono"].contains(p)]
        if not dentro:
            avisos.append(f"lote {l['nombre']}: sin rotulo NPT")
        elif len(dentro) > 1:
            avisos.append(f"lote {l['nombre']}: {len(dentro)} rotulos NPT, se toma el primero")
            npt[l["nombre"]] = dentro[0][0]
        else:
            npt[l["nombre"]] = dentro[0][0]
    for n, v in npt.items():
        if not (0 < v < 9000):
            avisos.append(f"lote {n}: NPT {v} fuera de rango, revisar el rotulo")
    return npt, avisos


# ---------------------------------------------------------------- vialidad
def vialidad(lotes, cierre=14.0, area_min=5.0):
    """Poligono de la vialidad interior: cierre morfologico de la union de lotes
    menos los propios lotes.

    `cierre` debe superar el ancho de calle mas ancho y quedar por debajo de
    cualquier vano exterior que no sea calle. Verificar midiendo el ancho real
    de los pasillos obtenidos."""
    U = unary_union([l["poligono"] for l in lotes])
    env = U.buffer(cierre, join_style=2).buffer(-cierre, join_style=2)
    vial = env.difference(U)
    partes = [p for p in (vial.geoms if vial.geom_type.startswith("Multi") else [vial])
              if p.area > area_min]
    return unary_union(partes) if partes else vial


def rotulos_calle(dxf, prefijo="CALLE"):
    """[(nombre, Point)] de los rotulos de calle del dibujo."""
    import ezdxf
    out = []
    for e in ezdxf.readfile(dxf).modelspace():
        if e.dxftype() != "MTEXT":
            continue
        t = re.sub(r"\s+", " ", e.plain_text()).strip()
        if t.upper().startswith(prefijo):
            out.append((t.title(), sg.Point(e.dxf.insert.x, e.dxf.insert.y)))
    return out


# -------------------------------------------------------------- medianeros
def medianeros(lotes, tol=TOL_VECINO, largo_min=LARGO_MIN_MED):
    """[{a, b, tramo}] — el tramo de deslinde que comparte cada par de vecinos.

    SOBRE LA TOLERANCIA. Con 10 cm se pierden medianeros enteros: es habitual que
    dos lotes contiguos esten dibujados a 0,14 m uno de otro, y entonces ese
    deslinde no existe para el calculo -- en un caso real, 32,4 m de medianero
    con 3,50 m de desnivel se quedaban sin talud. Entre lotes que NO son vecinos
    median calles de una decena de metros, asi que 30 cm distingue sin
    ambiguedad.

    La interseccion contra el buffer roza el circulo casi tangencialmente en las
    puntas y deja ahi un vertice espurio. Se limpia con simplify(0.5): esa
    tolerancia separa el ruido del buffer (medido: hasta 0,42 m) de los quiebres
    genuinos del deslinde (medido: 9,28 m en el unico caso real)."""
    porlote = {l["nombre"]: l["poligono"] for l in lotes}
    vistos, out = set(), []
    for l in lotes:
        a = l["nombre"]
        for b, pb in porlote.items():
            if b == a or tuple(sorted((a, b))) in vistos:
                continue
            if l["poligono"].distance(pb) > tol:
                continue
            comun = l["poligono"].exterior.intersection(pb.buffer(tol))
            if comun.is_empty:
                continue
            geoms = [g for g in (comun.geoms if hasattr(comun, "geoms") else [comun])
                     if g.geom_type in ("LineString", "MultiLineString")
                     and g.length > largo_min]
            if not geoms:
                continue
            vistos.add(tuple(sorted((a, b))))
            for g in geoms:
                for ls in (g.geoms if g.geom_type == "MultiLineString" else [g]):
                    if ls.length <= largo_min:
                        continue
                    if len(ls.coords) > 2:
                        ls = ls.simplify(0.5, preserve_topology=False)
                    out.append({"a": a, "b": b, "tramo": ls})
    return out


def frentes(lote, calzada, tol=0.30, largo_min=1.0):
    """Tramos del contorno del lote que dan a la calzada.

    Se miden contra la calzada LIMPIA. Contra un poligono de calzada dentado,
    cada frente sale partido en decenas de trocitos y el talud se genera a
    pedazos: medido, 491 tramos de 4 m de mediana contra 100 tramos de 21,6 m."""
    out = []
    com = lote["poligono"].exterior.intersection(calzada.buffer(tol))
    if com.is_empty:
        return out
    for g in (com.geoms if hasattr(com, "geoms") else [com]):
        if g.geom_type == "LineString" and g.length >= largo_min:
            out.append(g)
        elif g.geom_type == "MultiLineString":
            out.extend(x for x in g.geoms if x.length >= largo_min)
    return out


def juntas_de_medianero(objetos, npt, meds, dz_min=0.15, largo_min=LARGO_MIN_MED):
    """Cuelga en cada lote las juntas contra sus vecinos. Devuelve cuantas puso.

    El talud lo absorbe el lote ALTO: es el que retrocede para dejar que el
    terreno baje hasta la cota del vecino.

    La junta se apoya en el contorno DEL PROPIO lote alto, no en el tramo
    reconstruido. Ese tramo se traza sobre el borde de uno de los dos vecinos y
    puede quedar fuera del otro; si la banda se centra fuera, el recorte al lote
    se come parte del ancho -- y con desniveles de 0,25 m se lo come casi
    entero."""
    n = 0
    for m in meds:
        a, b = m["a"], m["b"]
        if a not in objetos or b not in objetos:
            continue
        if abs(npt[a] - npt[b]) < dz_min or m["tramo"].length < largo_min:
            continue
        alto = a if npt[a] > npt[b] else b
        z_vecino = min(npt[a], npt[b])
        propio = objetos[alto].poly.exterior.intersection(m["tramo"].buffer(0.40))
        piezas = [g for g in (propio.geoms if hasattr(propio, "geoms") else [propio])
                  if g.geom_type == "LineString" and g.length >= largo_min]
        for g in (piezas or [m["tramo"]]):
            objetos[alto].agregar_junta(g, z_vecino, etiqueta=f"medianero {a}-{b}")
            n += 1
    return n
