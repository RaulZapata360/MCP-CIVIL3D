# -*- coding: utf-8 -*-
# ============================================================================
#  exportar_marcas_pavimento.py
#  Exporta un DXF de marcas de pavimentacion (mallas AcDbPolyFaceMesh, una
#  capa por tipo de marca) a los archivos que consume Dynamo para crear el
#  hibrido Familia + DirectShape en Revit.
#
#  Generalizado desde la migracion de South Island (HRCP). Sin nada especifico
#  de ese proyecto: origen local, capas y umbrales se pasan por argumento o se
#  calculan del propio archivo.
#
#  PASO PREVIO OBLIGATORIO: correr clasificar_marcas_pavimento.py sobre el
#  mismo DXF y mirar la tabla. No asumir que el reparto de otro proyecto vaya
#  a ser igual al de South Island (alli: flechas y stop bars a familia, doble
#  amarilla y demarcacion a DirectShape) -- depende de la geometria real.
#
#  Uso:
#    python exportar_marcas_pavimento.py <marcas.dxf> <carpeta_salida> \
#        --familia CAPA_FLECHA,CAPA_STOPBAR --directshape CAPA_LINEA,... \
#        [--origen-x 12124000 --origen-y 3524500] [--espesor 0.02]
#
#  Si se omite --origen-x/--origen-y, se calcula igual que en los paquetes de
#  superficie de este mismo repo (minimo de X/Y redondeado a la centena) --
#  ver skills/migracion/scripts/exportar_paquete_revit.py.
#
#  SALIDAS (en <carpeta_salida>):
#    Para cada capa de FAMILIA:
#      <capa>_instancias.csv      -- una fila por marca. Columnas segun si la
#                                     capa resulto "mismo simbolo" (RumboDeg)
#                                     o "parametrica" (AngDeg,LargoFt,AnchoFt)
#      <capa>_contorno.dxf/.svg   -- SOLO si es "mismo simbolo": el contorno
#                                     canonico para construir la familia
#    Para cada capa de DIRECTSHAPE:
#      <capa>_mesh.json           -- solidos cerrados (cascara con espesor)
# ============================================================================
import argparse
import collections
import io
import json
import math
import os
import sys

import ezdxf
import numpy as np
import shapely.geometry as sg
from shapely.ops import unary_union
from scipy.spatial import ConvexHull

DEC = 4


def log(m=''):
    print(m); sys.stdout.flush()


# ------------------------------------------------------------------ lectura
def leer_capa(doc, capa, ox, oy):
    """AcDbPolyFaceMesh -> lista de dict(V, T) en coordenadas LOCALES.

    OJO DE FORMATO: los vertices con `flags & 64` son reales; el resto son
    registros de cara con location en (0,0,0). Leerlos todos sin filtrar da
    cajas de millones de pies -- confundio un analisis entero en South Island
    antes de detectarlo."""
    out = []
    for k, e in enumerate(doc.modelspace().query('POLYLINE[layer=="%s"]' % capa)):
        if e.get_mode() != 'AcDbPolyFaceMesh':
            continue
        V = np.array([[v.dxf.location.x - ox, v.dxf.location.y - oy, v.dxf.location.z]
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
            out.append(dict(i=k, capa=capa, V=V, T=T))
    return out


def area3d(V, T):
    return sum(0.5 * np.linalg.norm(np.cross(V[b] - V[a], V[c] - V[a])) for a, b, c in T)


def plano_ajuste(V):
    cx, cy = V[:, 0].mean(), V[:, 1].mean()
    A = np.column_stack([V[:, 0] - cx, V[:, 1] - cy, np.ones(len(V))])
    coef, *_ = np.linalg.lstsq(A, V[:, 2], rcond=None)
    pend = 100 * math.hypot(coef[0], coef[1])
    dir_asc = math.degrees(math.atan2(coef[1], coef[0])) % 360
    err = float(np.abs(A @ coef - V[:, 2]).max())
    return pend, dir_asc, coef, (cx, cy), err


def z_en(coef, centro, x, y):
    return coef[0] * (x - centro[0]) + coef[1] * (y - centro[1]) + coef[2]


def contorno_2d(V, T, tol=0.005):
    ps = [sg.Polygon(V[list(t), :2]) for t in T]
    u = unary_union([p for p in ps if p.is_valid and p.area > 1e-9]).buffer(0.001).buffer(-0.001)
    return np.array(u.exterior.simplify(tol).coords)[:-1]


def _rot(a):
    return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])


def rect_min(P):
    H = P[ConvexHull(P).vertices]
    mejor = None
    for k in range(len(H)):
        d = H[(k + 1) % len(H)] - H[k]
        ang = math.atan2(d[1], d[0])
        R = _rot(-ang)
        Q = P @ R.T
        w, h = np.ptp(Q[:, 0]), np.ptp(Q[:, 1])
        if mejor is None or w * h < mejor[0] * mejor[1]:
            mejor = (w, h, math.degrees(ang))
    w, h, ang = mejor
    return (max(w, h), min(w, h), ang % 180 if w >= h else (ang + 90) % 180)


def eje_area(V, T):
    """Eje principal por inercia de AREA. SOLO fiable con bastantes triangulos
    (una flecha con ~75 va bien). Con muy pocos (una barra rectangular con 2)
    la covarianza es casi degenerada y el eje sale torcido -- para rectangulos
    usar rect_min(), que es exacto."""
    c, w = [], []
    for a, b, d in T:
        p, q, r = V[a, :2], V[b, :2], V[d, :2]
        u, v = q - p, r - p
        ar = 0.5 * abs(u[0] * v[1] - u[1] * v[0])
        if ar > 1e-12:
            c.append((p + q + r) / 3.0); w.append(ar)
    c, w = np.array(c), np.array(w)
    m = (c * w[:, None]).sum(0) / w.sum()
    d = c - m
    C = (w[:, None, None] * np.einsum('ni,nj->nij', d, d)).sum(0) / w.sum()
    val, vec = np.linalg.eigh(C)
    e = vec[:, np.argmax(val)]
    return math.degrees(math.atan2(e[1], e[0])) % 180, m


def canonizar(V, T, metodo, orientar_punta=False):
    """Lleva la marca a su orientacion canonica y devuelve (P, ang, ancla).

      P      contorno canonico, centrado en su caja envolvente.
      ang    angulo real de la pieza en grados.
      ancla  punto del MUNDO que corresponde al origen de P (para insertar la
             familia por su centro real, no por la media de los vertices --
             confundirlos desplazo instancias hasta 2,5 ft en South Island).

    metodo: 'inercia' (formas organicas con muchos triangulos, ej. flechas) o
    'rect_min' (rectangulos reales: area/(largo*ancho) ~ 1.0).

    Si orientar_punta, el sentido de +X se decide por el CENTROIDE DE AREA
    (cae hacia la parte mas ancha, ej. la cabeza de una flecha) -- NO por
    anchos de banda en los extremos: con contornos simplificados de pocos
    vertices esas bandas se quedan sin puntos y el simbolo sale al reves."""
    W = contorno_2d(V, T)
    if metodo == 'inercia':
        ang, m = eje_area(V, T)
    else:
        _l, _a, ang = rect_min(W)
        m = W.mean(axis=0)
    centrar = lambda Q: Q - [(Q[:, 0].min() + Q[:, 0].max()) / 2,
                             (Q[:, 1].min() + Q[:, 1].max()) / 2]
    P = centrar((W - m) @ _rot(-math.radians(ang)).T)
    if orientar_punta and sg.Polygon(P).centroid.x < 0:
        P = centrar(P @ _rot(math.pi).T)
        ang = (ang + 180) % 360
    d = W - P @ _rot(math.radians(ang)).T
    ancla = d.mean(axis=0)
    assert np.abs(d - ancla).max() < 1e-3, (
        'la transformacion canonica no es un movimiento rigido -- revisar la '
        'malla de esta marca antes de seguir, algo no cuadra geometricamente')
    return P, ang % 360, ancla


# --------------------------------------------------- solido cerrado (skirt)
def solidificar(V, T, espesor):
    """Lamina -> cascara CERRADA para DirectShape: cara superior, cara
    inferior desplazada -espesor, y faldon en las aristas de borde.

    BUG QUE NO HAY QUE REPETIR: la cara inferior debe construirse en una lista
    APARTE. Hacer "for f in caras: caras.append(...)" itera una lista mientras
    crece al mismo ritmo -- bucle infinito que agota la RAM de la maquina."""
    n = len(V)
    Vs = np.vstack([V, V - np.array([0, 0, espesor])])

    arriba = []
    for (a, b, c) in T:
        p, q, r = V[a], V[b], V[c]
        u, v = q - p, r - p
        if (u[0] * v[1] - u[1] * v[0]) < 0:      # normal hacia +Z
            b, c = c, b
        arriba.append((a, b, c))

    abajo = [(c + n, b + n, a + n) for (a, b, c) in arriba]

    cuenta = collections.Counter()
    for (a, b, c) in arriba:
        for u, v in ((a, b), (b, c), (c, a)):
            cuenta[(min(u, v), max(u, v))] += 1

    faldon = []
    for (a, b, c) in arriba:
        for u, v in ((a, b), (b, c), (c, a)):
            if cuenta[(min(u, v), max(u, v))] == 1:     # solo aristas de borde
                faldon.append((u, v, v + n))
                faldon.append((u, v + n, u + n))

    caras = arriba + abajo + faldon
    assert len(caras) <= 6 * len(T) + 12, 'solidificar() genero mas caras de las posibles'
    return Vs, caras


def es_estanco(T):
    """True si la malla YA es un solido cerrado (toda arista compartida por
    exactamente 2 caras) -- caso de objetos 3D reales (barreras, mobiliario,
    señales) modelados con volumen, a diferencia de una lamina de pintura
    drapeada (2,5D, un solo valor de Z por XY).

    Por que importa: aplicar solidificar() (duplicar + faldon) a un solido
    YA cerrado no encuentra aristas de borde (no las hay) y produce DOS
    cascaras estancas anidadas por el offset -- geometria incorrecta, no solo
    ineficiente. Los solidos ya cerrados se exportan TAL CUAL, sin duplicar."""
    cuenta = collections.Counter()
    for a, b, c in T:
        for u, v in ((a, b), (b, c), (c, a)):
            cuenta[(min(u, v), max(u, v))] += 1
    return bool(cuenta) and set(cuenta.values()) == {2}


def rectangularidad(V, T):
    W = contorno_2d(V, T)
    largo, ancho, _ = rect_min(W)
    a = area3d(V, T)
    return (a / (largo * ancho)) if largo * ancho > 1e-9 else 0.0


# ============================================================== exportacion
def exportar_familia(marcas, capa, out_dir, dec=DEC):
    areas = np.array([area3d(m['V'], m['T']) for m in marcas])
    disp = float(areas.std() / areas.mean()) if areas.mean() > 0 else 1.0
    rects = np.array([rectangularidad(m['V'], m['T']) for m in marcas])
    es_rectangulo = float(np.median(rects)) >= 0.98
    mismo_simbolo = disp <= 0.05

    filas = []
    for m in marcas:
        V, T = m['V'], m['T']
        pend, dir_asc, coef, centro, err = plano_ajuste(V)
        metodo = 'inercia' if (mismo_simbolo and len(T) >= 20) else 'rect_min'
        Pc, ang, ancla = canonizar(V, T, metodo, orientar_punta=mismo_simbolo)
        ax_, ay_ = ancla
        az_ = z_en(coef, centro, ax_, ay_)
        largo, ancho = float(np.ptp(Pc[:, 0])), float(np.ptp(Pc[:, 1]))
        dz = float(np.ptp(V[:, 2]))
        filas.append(dict(Id=m['i'], X=round(ax_, dec), Y=round(ay_, dec), Z=round(az_, dec),
                          AngDeg=round(ang, 3), PendPct=round(pend, 3), PendDirDeg=round(dir_asc, 3),
                          AreaFt2=round(area3d(V, T), 3), ErrPlanoFt=round(err, 4),
                          LargoFt=round(largo, dec), AnchoFt=round(ancho, dec),
                          DzFt=round(dz, dec)))

    cols = ['Id', 'X', 'Y', 'Z', 'AngDeg', 'PendPct', 'PendDirDeg', 'AreaFt2',
           'ErrPlanoFt', 'LargoFt', 'AnchoFt', 'DzFt']
    p = os.path.join(out_dir, '%s_instancias.csv' % capa)
    with io.open(p, 'w', newline='', encoding='ascii') as fh:
        fh.write(','.join(cols) + '\n')
        for f in filas:
            fh.write(','.join(str(f[c]) for c in cols) + '\n')

    tipo = 'mismo simbolo (%d rotaciones)' % len({round(f['AngDeg']) for f in filas}) \
        if mismo_simbolo else ('parametrica (largo/ancho variables)' if es_rectangulo
                               else 'SIN PATRON CLARO -- revisar antes de construir la familia')
    log(f'  {capa}: {len(marcas)} marcas -> {os.path.basename(p)}  [{tipo}]')

    if mismo_simbolo:
        patron = max(marcas, key=lambda m: len(m['V']))
        ring, _, _ = canonizar(patron['V'], patron['T'], 'inercia'
                               if len(patron['T']) >= 20 else 'rect_min', orientar_punta=True)
        d = ezdxf.new('R2018'); ms = d.modelspace()
        d.layers.new('CONTORNO', dxfattribs={'color': 2})
        ms.add_lwpolyline([(float(x), float(y)) for x, y in ring],
                          close=True, dxfattribs={'layer': 'CONTORNO'})
        pd = os.path.join(out_dir, '%s_contorno.dxf' % capa)
        d.saveas(pd)
        a_pat = sg.Polygon(ring).area
        a_med = float(areas.mean())
        if abs(a_pat - a_med) > 0.05 * a_med:
            log(f'    AVISO: el contorno patron ({a_pat:.2f} ft2) no representa bien '
                f'la media de la capa ({a_med:.2f} ft2) -- revisar a mano')
        log(f'    contorno canonico -> {os.path.basename(pd)}  '
            f'({np.ptp(ring[:,0]):.3f} x {np.ptp(ring[:,1]):.3f} ft)')

        # Lista de Python lista para pegar en CONTORNO dentro de
        # dynamo_colocar_familias_marcas.py -- asi el script de Dynamo no
        # depende de parsear un DXF desde dentro de Revit.
        pp = os.path.join(out_dir, '%s_contorno_paste.txt' % capa)
        with io.open(pp, 'w', encoding='ascii') as fh:
            fh.write('CONTORNO = [\n')
            for x, y in ring:
                fh.write('    (%.4f, %.4f),\n' % (x, y))
            fh.write(']\n')
        log(f'    para pegar en Dynamo -> {os.path.basename(pp)}')
    return filas


def exportar_directshape(marcas, capa, out_dir, espesor, dec=DEC):
    salida = []
    tot_v = tot_f = 0
    n_pasan, n_solidifican = 0, 0
    for m in marcas:
        V, T = m['V'], m['T']
        if es_estanco(T):
            # Ya es un solido cerrado (objeto 3D real: barrera, mobiliario,
            # senal...). Se exporta TAL CUAL -- duplicarlo con solidificar()
            # produciria dos cascaras anidadas, no un solido correcto.
            Vs, caras = V, T
            n_pasan += 1
        else:
            # Lamina 2,5D (ej. pintura drapeada): fabricarle espesor.
            Vs, caras = solidificar(V, T, espesor)
            n_solidifican += 1
        tot_v += len(Vs); tot_f += len(caras)
        salida.append(dict(id=m['i'], capa=capa, area=round(area3d(V, T), 3),
                           estanco_origen=es_estanco(T),
                           v=[[round(float(x), dec) for x in p] for p in Vs],
                           f=[[int(a), int(b), int(c)] for a, b, c in caras]))
    p = os.path.join(out_dir, '%s_mesh.json' % capa)
    with io.open(p, 'w', encoding='ascii') as fh:
        json.dump(dict(espesor_ft=espesor, n=len(salida), marcas=salida), fh)
    log(f'  {capa}: {len(marcas)} marcas ({n_pasan} ya solidas, {n_solidifican} laminadas), '
        f'{tot_v:,} vertices, {tot_f:,} caras -> {os.path.basename(p)}  '
        f'({os.path.getsize(p)/1e6:.1f} MB)')
    if n_pasan:
        log(f'    {n_pasan} pasaron tal cual (mismos vertices/caras del DXF): si alguna sale '
            f'invisible o "al reves" en Revit, es un problema de orientacion de normales del '
            f'origen, no de esta exportacion -- revisar con TessellatedShapeBuilderTarget.AnyGeometry')
    return salida


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('dxf')
    ap.add_argument('out_dir')
    ap.add_argument('--familia', default='', help='Capas a exportar como familia, separadas por coma')
    ap.add_argument('--directshape', default='', help='Capas a exportar como DirectShape, separadas por coma')
    ap.add_argument('--origen-x', type=float, default=None)
    ap.add_argument('--origen-y', type=float, default=None)
    ap.add_argument('--espesor', type=float, default=0.02, help='ft, espesor del solido de pintura')
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    doc = ezdxf.readfile(args.dxf)

    capas_fam = [c for c in args.familia.split(',') if c]
    capas_ds = [c for c in args.directshape.split(',') if c]
    if not capas_fam and not capas_ds:
        log('Nada que exportar: pasa --familia y/o --directshape con las capas '
           '(correr antes clasificar_marcas_pavimento.py para saber cuales).')
        sys.exit(1)

    if args.origen_x is None or args.origen_y is None:
        xs, ys = [], []
        for e in doc.modelspace().query('POLYLINE'):
            if e.get_mode() != 'AcDbPolyFaceMesh':
                continue
            for v in e.vertices:
                if v.dxf.flags & 64:
                    xs.append(v.dxf.location.x); ys.append(v.dxf.location.y)
        ox = args.origen_x if args.origen_x is not None else int(min(xs) // 100) * 100
        oy = args.origen_y if args.origen_y is not None else int(min(ys) // 100) * 100
    else:
        ox, oy = args.origen_x, args.origen_y
    log(f'Origen local: E {ox:,.0f} / N {oy:,.0f}  (restado a todas las coordenadas)')
    log(f'Espesor DirectShape: {args.espesor} ft\n')

    total_marcas = total_area = 0
    if capas_fam:
        log('=== FAMILIA ===')
        for capa in capas_fam:
            marcas = leer_capa(doc, capa, ox, oy)
            if not marcas:
                log(f'  {capa}: AVISO -- 0 marcas encontradas, se omite'); continue
            exportar_familia(marcas, capa, args.out_dir)
            total_marcas += len(marcas)
            total_area += sum(area3d(m['V'], m['T']) for m in marcas)

    if capas_ds:
        log('\n=== DIRECTSHAPE ===')
        for capa in capas_ds:
            marcas = leer_capa(doc, capa, ox, oy)
            if not marcas:
                log(f'  {capa}: AVISO -- 0 marcas encontradas, se omite'); continue
            exportar_directshape(marcas, capa, args.out_dir, args.espesor)
            total_marcas += len(marcas)
            total_area += sum(area3d(m['V'], m['T']) for m in marcas)

    with io.open(os.path.join(args.out_dir, 'ORIGEN_LOCAL.txt'), 'w', encoding='utf-8') as fh:
        fh.write('Origen local restado a todas las coordenadas de este paquete:\n')
        fh.write(f'  E = {ox:.4f}\n  N = {oy:.4f}\n\n')
        fh.write('Para georreferenciar en Revit: Manage -> Coordinates -> Specify\n')
        fh.write('Coordinates at Point, en el origen (0,0,0) del modelo introducir\n')
        fh.write(f'E {ox:.3f} / N {oy:.3f} / Z 0.000 (si no se aplica ningun OFFSET_X/\n')
        fh.write('OFFSET_Y adicional para acoplarse a un modelo de Revit existente).\n')

    log(f'\n{total_marcas} marcas exportadas, {total_area:,.1f} ft2 -> {args.out_dir}')


if __name__ == '__main__':
    main()
