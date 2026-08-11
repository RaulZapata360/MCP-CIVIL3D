# -*- coding: utf-8 -*-
"""Rasantes de calzada: eje, perfil longitudinal y cubicación de la vialidad.

CRITERIO ACORDADO (2026-08-07): pendiente longitudinal máxima 12 %, mínima 0,5 %
para escurrimiento. La rasante debe además dar acceso a todos los lotes que
enfrenta.

MÉTODO
  1. EJE. El DXF no trae eje de calle, así que se extrae el eje medio del
     polígono de calzada por diagrama de Voronoi de su contorno densificado: las
     aristas de Voronoi interiores forman el esqueleto, y el camino más largo
     entre sus extremos es el eje. Es el mismo eje que trazaría un proyectista.
  2. RASANTE. Se resuelve un problema de mínimos cuadrados con restricciones:
       · acercarse al terreno natural (minimiza movimiento de tierras),
       · pasar cerca de la NPT de cada lote que enfrenta (garantiza el acceso),
       · pendiente entre nodos acotada a ±12 %.
     La pendiente mínima de 0,5 % no se impone como restricción —haría el
     problema no convexo, porque excluye una banda alrededor de cero— sino que
     se verifica al final y se marcan los tramos planos.
  3. CUBICACIÓN. Volumen entre la rasante y el terreno natural sobre el polígono
     de calzada, con el mismo método exacto de partición de triángulos que se usó
     en los lotes.
"""
import math
import numpy as np
import shapely.geometry as sg
from shapely.ops import unary_union
from scipy.spatial import Voronoi
from scipy.optimize import minimize
import networkx as nx

PEND_MAX = 0.12       # 12 %
PEND_MIN = 0.005      # 0,5 % — se verifica, no se impone
PASO_NODO = 20.0      # m entre nodos de la rasante
PESO_ACCESO = 3.0     # cuánto pesa servir la NPT del lote frente al terreno
TOL_ACCESO = 1.50     # m — desnivel aceptable entre calzada y NPT del lote


def esqueleto_red(vial, paso=1.5):
    """Esqueleto de TODA la red vial de una vez, por Voronoi de su contorno.

    IMPORTANTE: no debe extraerse el eje calle por calle. Cada calle es un trozo
    del mismo corredor y varias vienen partidas en varias piezas; sacar el
    esqueleto de una pieza aislada devuelve una rama corta en vez del eje real
    (a Calle Principal 1 le daba 171 m de eje cuando mide 588). Se esqueletiza la
    red completa y después se reparte por calle."""
    polys = list(vial.geoms) if vial.geom_type == "MultiPolygon" else [vial]
    pts = []
    for p in polys:
        for anillo in [p.exterior] + list(p.interiors):
            n = max(20, int(anillo.length / paso))
            pts.extend(anillo.interpolate(i / n, normalized=True).coords[0]
                       for i in range(n))
    vor = Voronoi(np.array(pts))
    G = nx.Graph()
    for (i, j) in vor.ridge_vertices:
        if i < 0 or j < 0:
            continue
        a, b = vor.vertices[i], vor.vertices[j]
        seg = sg.LineString([a, b])
        if not vial.contains(seg):
            continue
        G.add_edge(i, j, weight=seg.length,
                   mid=((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    return G, vor


def podar(G, min_pua=6.0):
    """Elimina las púas del esqueleto de Voronoi.

    El diagrama de Voronoi de un contorno poligonal genera una espina central
    útil MÁS una púa hacia cada vértice del contorno. Sin podarlas el grafo queda
    tan ramificado que el camino más largo salta de púa en púa y devuelve un eje
    mucho más corto que la calle. Se recortan iterativamente las ramas terminales
    cuya longitud acumulada no llega a `min_pua`."""
    H = G.copy()
    cambio = True
    while cambio:
        cambio = False
        for n in [x for x in H.nodes if H.degree(x) == 1]:
            vecino = next(iter(H[n]))
            if H[n][vecino]["weight"] < min_pua:
                H.remove_node(n)
                cambio = True
    return H


def repartir_esqueleto(G, rotulos, U):
    """Asigna cada arista del esqueleto a una calle.

    Se reparte el ESQUELETO, no el área. Repartir el área y luego cortar el
    esqueleto con cada trozo lo fragmenta: el polígono de Calle Principal 1 viene
    en 5 piezas y su eje salía de 168 m en vez de los ~420 m reales. Sobre el
    esqueleto la conectividad se conserva.

    Criterio: el rótulo CALLE más cercano cuya visual no atraviese un lote — el
    mismo que se usó para nombrar las áreas."""
    asign = {}
    for u, v, d in G.edges(data=True):
        pt = sg.Point(d["mid"])
        elegido = None
        for nom, rp in sorted(rotulos, key=lambda c: c[1].distance(pt)):
            if not sg.LineString([pt, rp]).intersects(U):
                elegido = nom
                break
        if elegido is None:
            elegido = min(rotulos, key=lambda c: c[1].distance(pt))[0]
        asign.setdefault(elegido, []).append((u, v, d["weight"]))
    return asign


def eje_conectado(G, vor, aristas, poly=None, min_len=5.0):
    """Eje de una calle como camino CONECTADO del esqueleto completo.

    El reparto por rótulo cede las intersecciones a la calle transversal, lo que
    parte el corredor de la calle principal en trozos sueltos; buscar el camino
    más largo dentro de esos trozos devolvía 167 m para una calle de ~500 m. Aquí
    se toman los dos nodos ASIGNADOS más distantes entre sí y se traza el camino
    entre ellos sobre el esqueleto COMPLETO, de modo que el eje puede atravesar
    las intersecciones y sale continuo."""
    nodos = {u for u, v, w in aristas} | {v for u, v, w in aristas}
    nodos = [n for n in nodos if n in G]
    if len(nodos) < 2:
        return _eje_pca(poly) if poly is not None else None
    comp = max(nx.connected_components(G), key=len)
    nodos = [n for n in nodos if n in comp]
    if len(nodos) < 2:
        return _eje_pca(poly) if poly is not None else None
    K = G.subgraph(comp)
    d1 = nx.single_source_dijkstra_path_length(K, nodos[0], weight="weight")
    a = max((n for n in nodos if n in d1), key=lambda n: d1[n])
    d2 = nx.single_source_dijkstra_path_length(K, a, weight="weight")
    b = max((n for n in nodos if n in d2), key=lambda n: d2[n])
    camino = nx.dijkstra_path(K, a, b, weight="weight")
    linea = sg.LineString([vor.vertices[i] for i in camino]).simplify(0.5)
    if linea.length >= min_len:
        return linea
    return _eje_pca(poly) if poly is not None else linea


def eje_desde_asignacion(vor, aristas, poly=None, min_len=5.0):
    """Camino más largo dentro de las aristas asignadas a una calle."""
    H = nx.Graph()
    for u, v, w in aristas:
        H.add_edge(u, v, weight=w)
    if H.number_of_nodes() < 2:
        return _eje_pca(poly) if poly is not None else None
    comp = max(nx.connected_components(H), key=lambda c: sum(
        H[u][v]["weight"] for u in c for v in H[u] if v in c) / 2)
    K = H.subgraph(comp)
    a = next(iter(K.nodes))
    d1 = nx.single_source_dijkstra_path_length(K, a, weight="weight")
    b = max(d1, key=d1.get)
    d2 = nx.single_source_dijkstra_path_length(K, b, weight="weight")
    c2 = max(d2, key=d2.get)
    camino = nx.dijkstra_path(K, b, c2, weight="weight")
    linea = sg.LineString([vor.vertices[i] for i in camino]).simplify(0.5)
    if linea.length >= min_len:
        return linea
    return _eje_pca(poly) if poly is not None else linea


def _eje_pca(poly):
    if poly.geom_type == "MultiPolygon":
        poly = max(poly.geoms, key=lambda p: p.area)
    c = np.array(poly.exterior.coords)
    m = c.mean(axis=0)
    _, _, vt = np.linalg.svd(c - m, full_matrices=False)
    d = vt[0]
    t = (c - m) @ d
    return sg.LineString([m + d * t.min(), m + d * t.max()])


def perfil_terreno(linea, muestreador, paso=PASO_NODO):
    """Estaciones y cota natural del eje."""
    L = linea.length
    n = max(2, int(round(L / paso)))
    est, z = [], []
    for i in range(n + 1):
        s = L * i / n
        p = linea.interpolate(s)
        zz = muestreador(p.x, p.y)
        if zz is None and z:
            zz = z[-1]
        if zz is None:
            continue
        est.append(s); z.append(zz)
    return np.array(est), np.array(z)


def accesos(linea, lotes, npt, poly_calle, dmax=1.0):
    """Para cada lote que enfrenta la calzada: estación del eje más cercana y NPT."""
    out = []
    for l in lotes:
        if l["poligono"].distance(poly_calle) > dmax:
            continue
        nom = l["nombre"]
        if nom not in npt:
            continue
        p = l["poligono"].centroid
        s = linea.project(p)
        out.append({"lote": nom, "s": float(s), "npt": float(npt[nom])})
    return out


def resolver_rasante(est, z_nat, acc, pend_max=PEND_MAX, peso_acceso=PESO_ACCESO):
    """Mínimos cuadrados con restricción de pendiente. Devuelve z de cada nodo."""
    n = len(est)
    ds = np.diff(est)
    ds[ds <= 0] = 1e-6

    # matriz de interpolación de los accesos sobre los nodos
    filas, objetivo = [], []
    for a in acc:
        s = min(max(a["s"], est[0]), est[-1])
        k = int(np.searchsorted(est, s) - 1)
        k = min(max(k, 0), n - 2)
        t = (s - est[k]) / (est[k + 1] - est[k])
        fila = np.zeros(n); fila[k] = 1 - t; fila[k + 1] = t
        filas.append(fila); objetivo.append(a["npt"])
    Aacc = np.array(filas) if filas else np.zeros((0, n))
    bacc = np.array(objetivo) if objetivo else np.zeros(0)

    def fobj(zz):
        r1 = zz - z_nat
        r2 = (Aacc @ zz - bacc) if len(bacc) else np.zeros(0)
        return float(r1 @ r1 + peso_acceso * (r2 @ r2))

    def grad(zz):
        g = 2 * (zz - z_nat)
        if len(bacc):
            g = g + 2 * peso_acceso * (Aacc.T @ (Aacc @ zz - bacc))
        return g

    cons = [{"type": "ineq",
             "fun": (lambda zz, i=i: pend_max * ds[i] - abs(zz[i + 1] - zz[i]))}
            for i in range(n - 1)]
    r = minimize(fobj, z_nat.copy(), jac=grad, constraints=cons,
                 method="SLSQP", options={"maxiter": 600, "ftol": 1e-8})
    return r.x, r


def diagnosticar(est, z_ras, z_nat, acc):
    ds = np.diff(est)
    g = np.diff(z_ras) / np.where(ds > 0, ds, 1e-9)
    planos = [(float(est[i]), float(est[i + 1]), float(g[i] * 100))
              for i in range(len(g)) if abs(g[i]) < PEND_MIN]
    excedidos = [(float(est[i]), float(est[i + 1]), float(g[i] * 100))
                 for i in range(len(g)) if abs(g[i]) > PEND_MAX + 1e-6]
    fuera = []
    for a in acc:
        s = min(max(a["s"], est[0]), est[-1])
        zc = float(np.interp(s, est, z_ras))
        d = zc - a["npt"]
        if abs(d) > TOL_ACCESO:
            fuera.append({"lote": a["lote"], "npt": a["npt"], "calzada": zc, "dif": d})
    return {
        "pend_media_pct": float(np.average(np.abs(g), weights=ds) * 100),
        "pend_max_pct": float(np.abs(g).max() * 100),
        "tramos_planos": planos,
        "tramos_excedidos": excedidos,
        "accesos_fuera_tolerancia": fuera,
        "n_accesos": len(acc),
        "desnivel_medio_vs_tn": float(np.mean(z_ras - z_nat)),
        "desnivel_max_vs_tn": float(np.max(np.abs(z_ras - z_nat))),
    }


def cubicar_calzada(verts, faces, poly, linea, est, z_ras):
    """Volumen entre la rasante (interpolada a lo largo del eje) y el terreno."""
    from perfil_lib import _area2d
    v = np.asarray(verts, float); f = np.asarray(faces, int)
    vc = vr = 0.0
    ac_ = ar_ = 0.0
    for i1, i2, i3 in f:
        p = [v[i1], v[i2], v[i3]]
        cx = (p[0][0] + p[1][0] + p[2][0]) / 3
        cy = (p[0][1] + p[1][1] + p[2][1]) / 3
        s = linea.project(sg.Point(cx, cy))
        zr = float(np.interp(s, est, z_ras))
        d = [q[2] - zr for q in p]
        ar = _area2d(p[0], p[1], p[2])
        if ar <= 0:
            continue
        med = sum(d) / 3.0
        if med >= 0:
            vc += ar * med; ac_ += ar
        else:
            vr += ar * (-med); ar_ += ar
    return {"vol_corte": vc, "vol_relleno": vr, "vol_neto": vc - vr,
            "area_corte": ac_, "area_relleno": ar_}
