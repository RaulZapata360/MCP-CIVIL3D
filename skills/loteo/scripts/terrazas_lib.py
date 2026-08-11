# -*- coding: utf-8 -*-
"""Terrazas, taludes y calzadas de un loteo en ladera.

NUCLEO DEL METODO. Cada lote es un objeto `Lote` con:
  · una NPT (cota de piso terminado), que define una terraza HORIZONTAL;
  · una lista de JUNTAS, cada una con una linea de arranque (el deslinde contra
    la calzada o contra un lote vecino) y la cota que rige sobre esa linea.

De ahi sale UNA sola funcion de cota z(x,y) para todo el lote, y con ella se
malla el lote entero de una vez. Ese "de una vez" es lo importante: mallar por
piezas (una por talud, mas la terraza) produce costuras, secciones planas dentro
de un talud y triangulos astilla. Ver el .skill.md para el detalle de por que.

REGLA GEOMETRICA
    z(p) = zb + (NPT - zb) * min(1, d / w)      con  w = |NPT - zb| * razon

donde d es la distancia de p a la linea de la junta y zb la cota sobre esa linea.
Con razon = 1 (talud 1:1) el ancho del talud es exactamente el desnivel, y en el
pie (d = w) la cota vale NPT, que es la de la terraza: empalma sin escalon.
"""
import math

import numpy as np
import shapely.geometry as sg
from shapely.ops import unary_union

RAZON = 1.0            # H:V del talud. 1.0 = 1:1
DZ_MIN = 0.15          # m — por debajo no se dibuja talud
LARGO_MIN_JUNTA = 1.0  # m — un deslinde mas corto es un toque de esquina
PASO_LINEA = 1.5       # m — muestreo del contorno del lote
PASO_REJILLA = 4.0     # m — rejilla interior de la terraza
PASO_QUIEBRE = 1.0     # m — puntos sobre arranque y pie del talud


def solo_poligonos(g):
    """Recortar geometria devuelve a veces GeometryCollection con lineas y
    puntos sueltos. El mallador solo entiende poligonos."""
    if g.is_empty or g.geom_type == "Polygon":
        return g
    partes = [x for x in getattr(g, "geoms", [])
              if x.geom_type == "Polygon" and not x.is_empty and x.area > 1e-9]
    if not partes:
        return sg.Polygon()
    return partes[0] if len(partes) == 1 else sg.MultiPolygon(partes)


def puntos_linea(linea, paso):
    L = linea.length
    n = max(1, int(math.ceil(L / paso)))
    return [linea.interpolate(L * i / n) for i in range(n + 1)]


def densificar_anillo(coords, paso):
    """Anade puntos intermedios CONSERVANDO los vertices originales.

    Interpolar a intervalos regulares sobre todo el anillo los borra, y con ellos
    las esquinas: en una prueba real eso perdio 593 m2 de calzada solo por
    redondeo. Hay que recorrer lado a lado."""
    out = []
    for a, b in zip(coords[:-1], coords[1:]):
        out.append(a)
        d = math.dist(a, b)
        if d < 1e-9:
            continue
        for i in range(1, int(d // paso) + 1):
            t = i * paso / d
            if t < 1 - 1e-9:
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


class Lote:
    """Un lote con su terraza y sus taludes."""

    def __init__(self, nombre, poly, npt, razon=RAZON):
        self.nombre = nombre
        self.poly = poly
        self.npt = float(npt)
        self.razon = razon
        self.juntas = []

    # ------------------------------------------------------------- juntas
    def agregar_junta(self, linea, zb, etiqueta=""):
        """`zb` puede ser un numero (cota fija, caso medianero entre terrazas) o
        una funcion (x, y) -> cota (caso calzada, cuya rasante varia)."""
        f = zb if callable(zb) else (lambda x, y, z=float(zb): z)
        self.juntas.append({"linea": linea, "zb": f, "etiqueta": etiqueta})

    def ancho_max(self, j, paso=2.0):
        ws = [abs(self.npt - j["zb"](p.x, p.y)) * self.razon
              for p in puntos_linea(j["linea"], paso)]
        return max(ws) if ws else 0.0

    # --------------------------------------------------------------- cota
    def z(self, x, y):
        """Manda la junta con menor distancia NORMALIZADA al ancho de su propio
        talud. Fuera de toda junta es terraza, a NPT exacta."""
        p = sg.Point(x, y)
        mejor_t, mejor_z = 1.0, self.npt
        for j in self.juntas:
            zb = j["zb"](x, y)
            w = abs(self.npt - zb) * self.razon
            if w < 1e-6:
                continue
            t = j["linea"].distance(p) / w
            if t < mejor_t:
                mejor_t = t
                mejor_z = zb + (self.npt - zb) * t
        return mejor_z

    # -------------------------------------------------------------- banda
    def banda(self, j):
        """Huella en planta del talud: buffer de la linea por su ancho,
        recortado al lote.

        SE USA BUFFER, NO DESPLAZAMIENTO. Desplazar la linea hacia adentro exige
        decidir el sentido con un punto de prueba, y esa prueba falla cuando la
        linea del medianero cae fuera del lote -- cosa que pasa, porque el tramo
        se reconstruye sobre el contorno de UNO de los dos vecinos y los DXF de
        loteo dibujan lotes contiguos separados hasta 15 cm. En una medicion
        real, con desplazamiento 69 de 112 medianeros cubrian menos del 95 % de
        su deslinde y el ancho efectivo era el 29 % del teorico; con buffer, la
        mediana de area/teorica pasa a 1,00."""
        w = self.ancho_max(j)
        if w < 1e-6:
            return None
        g = solo_poligonos(
            j["linea"].buffer(w, cap_style=2, join_style=2).intersection(self.poly))
        return None if g.is_empty or g.area < 0.05 else g

    def bandas(self):
        bs = [b for b in (self.banda(j) for j in self.juntas) if b is not None]
        return unary_union(bs) if bs else None

    # --------------------------------------------------------------- malla
    def nube(self):
        """Puntos donde se evalua la cota: contorno, rejilla interior y --clave--
        los quiebres de cada talud (arranque y pie). Sembrar el pie es lo que
        impide que un triangulo salte del arranque a la terraza cruzando el
        talud, que es como se pierde la pendiente dentro de la franja."""
        pts = []
        for anillo in [self.poly.exterior] + list(self.poly.interiors):
            pts.extend(densificar_anillo(list(anillo.coords), PASO_LINEA))
        for j in self.juntas:
            g = self.banda(j)
            if g is None:
                continue
            for q in (g.geoms if g.geom_type.startswith("Multi") else [g]):
                for anillo in [q.exterior] + list(q.interiors):
                    for p in puntos_linea(sg.LineString(anillo.coords), PASO_QUIEBRE):
                        if (self.poly.contains(p)
                                or self.poly.exterior.distance(p) < 0.05):
                            pts.append((p.x, p.y))
        minx, miny, maxx, maxy = self.poly.bounds
        interior = self.poly.buffer(-0.5)
        if not interior.is_empty:
            for x in np.arange(minx, maxx, PASO_REJILLA):
                for y in np.arange(miny, maxy, PASO_REJILLA):
                    if interior.contains(sg.Point(x, y)):
                        pts.append((float(x), float(y)))
        vistos, out = set(), []
        for x, y in pts:
            k = (round(x, 3), round(y, 3))
            if k not in vistos:
                vistos.add(k)
                out.append((x, y))
        return out

    def mallar(self):
        from shapely import delaunay_triangles
        pts = self.nube()
        if len(pts) < 3:
            return [], []
        tri = delaunay_triangles(sg.MultiPoint([sg.Point(p) for p in pts]))
        idx = {(round(x, 3), round(y, 3)): i for i, (x, y) in enumerate(pts)}
        verts = [(x, y, self.z(x, y)) for x, y in pts]
        faces = []
        for t in tri.geoms:
            if t.area < 1e-4 or not self.poly.contains(t.representative_point()):
                continue
            try:
                a, b, c = (idx[(round(x, 3), round(y, 3))]
                           for x, y in list(t.exterior.coords)[:-1])
            except (KeyError, ValueError):
                continue
            if a != b and b != c and a != c:
                faces.append((a, b, c))
        usados = sorted({i for f in faces for i in f})
        remap = {v: k for k, v in enumerate(usados)}
        return ([verts[i] for i in usados],
                [(remap[a], remap[b], remap[c]) for a, b, c in faces])


# ------------------------------------------------------------------ auditoria
def auditar(lote, verts, faces, tol_pendiente=15.0):
    """Irregularidades que un corte en cerro no puede tener.

    Un corte en ladera no admite superficie flotante, huecos, ni zonas planas
    dentro de un talud. Se mide todo eso, mas la desviacion de la pendiente
    respecto de la razon adoptada."""
    v = np.asarray(verts, float)
    tris = [sg.Polygon([(v[i][0], v[i][1]) for i in t]) for t in faces]
    u = unary_union(tris) if tris else sg.Polygon()
    banda = lote.bandas()
    obj = math.degrees(math.atan(1.0 / lote.razon))   # 1:1 -> 45 grados

    r = {"lote": lote.nombre,
         "cobertura": (u.area / lote.poly.area * 100) if lote.poly.area else 0.0,
         "hueco": lote.poly.difference(u).area,
         "piezas": len(list(u.geoms)) if u.geom_type.startswith("Multi") else 1,
         "flotantes": len(verts) - len({i for t in faces for i in t}),
         "area_talud": banda.area if banda is not None else 0.0,
         "llano_en_talud": 0.0, "pendiente_fuera_regla": 0.0}

    if banda is None:
        return r
    for t, tt in zip(tris, faces):
        if not banda.contains(t.representative_point()):
            continue
        zs = [v[i][2] for i in tt]
        if max(zs) - min(zs) < 0.01:
            r["llano_en_talud"] += t.area
            continue
        a, b, c = v[tt[0]], v[tt[1]], v[tt[2]]
        n = np.cross(b - a, c - a)
        if abs(n[2]) < 1e-12:
            continue
        pend = math.degrees(math.atan2(math.hypot(n[0], n[1]), abs(n[2])))
        if abs(pend - obj) > tol_pendiente:
            r["pendiente_fuera_regla"] += t.area
    return r
