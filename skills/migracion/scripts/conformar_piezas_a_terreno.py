# -*- coding: utf-8 -*-
# ============================================================================
#  conformar_piezas_a_terreno.py
#  Apoya las piezas de un <capa>_mesh.json sobre el terreno REAL de Revit,
#  vertice a vertice, calculandolo FUERA de Revit con numpy.
#
#  Es el paso 2 de 3:
#     1. dynamo_exportar_malla_toposolid.py (en Dynamo) -> Toposolid_Malla.json
#     2. este script (Python normal, fuera de Revit)
#     3. dynamo_directshape_desde_malla.py con ELEVACION = 0.0
#        (el JSON de salida ya trae la Z FINAL: volver a sumar elevacion la
#         levantaria de mas)
#
#  POR QUE FUERA DE REVIT: ver el encabezado de
#  dynamo_exportar_malla_toposolid.py. Resumen: Solid.IntersectWithCurve() es
#  una interseccion booleana B-rep (milisegundos por llamada) y con ~100.000
#  vertices cuelga Dynamo. Aqui la misma pregunta se responde con una
#  interpolacion baricentrica sobre el triangulo que cubre el punto:
#  microsegundos, vectorizado en C. Es la MISMA superficie, no una aproximacion.
#  Medido en South Island: 109.730 vertices en 0,25 s.
#
#  MODOS
#    'conformar'       cada vertice se apoya en el terreno real. Corrige
#                      enterramiento Y flotacion de una vez.
#    'solo_enterradas' solo sube lo que quedo por debajo del terreno.
#
#  EL ESPESOR SE PRESERVA: una pieza laminar es un solido con DOS vertices por
#  cada XY (cara de arriba y de abajo). Se identifica cual es la de abajo por
#  su separacion (el espesor) y se le resta esa misma cantidad, asi la pieza se
#  apoya sin aplastarse.
#
#  USO:  python conformar_piezas_a_terreno.py
# ============================================================================
import json
import os
import sys
import time

import numpy as np

CARPETA = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
#  CONFIGURACION -- AJUSTAR PARA CADA PROYECTO
# ============================================================================
RUTA_TOPO = os.path.join(CARPETA, 'Toposolid_Malla.json')
RUTA_MARCAS = os.path.join(CARPETA, 'piezas_mesh.json')
RUTA_SALIDA = os.path.join(CARPETA, 'piezas_mesh_corregido.json')
RUTA_LOG = os.path.join(CARPETA, 'log_conformar.txt')

OFFSET_X = 0.0        # el MISMO offset con el que se colocaron las piezas
OFFSET_Y = 0.0
ELEVACION = 0.02      # ft que la cara superior vuela sobre el terreno

MODO = 'conformar'    # 'conformar' | 'solo_enterradas'
TOLERANCIA = 0.02     # ft -- en 'solo_enterradas', por debajo de esto no se toca

CAPAS = ()            # capas a procesar; () = todas las del JSON
# ============================================================================

CELDA = 10.0     # ft -- lado de la celda del indice espacial de triangulos


def cargar_sopa(ruta, log):
    """Todos los triangulos de las 22 piezas en una sola 'sopa', con una
    marca de cuales son SOSPECHOSOS de ser cara inferior colada.

    POR QUE NO SE USA UNA TRIANGULACION FORMAL (matplotlib/scipy): esas
    exigen una triangulacion valida -- sin puntos XY repetidos y sin
    triangulos solapados -- y esta malla no lo es, por dos motivos
    independientes:

      1) 14A se queda con los triangulos cuya normal mira hacia arriba,
         calculada desde el bobinado de sus propios vertices. Pero
         Face.Triangulate() los devuelve segun la parametrizacion de la
         SUPERFICIE, y en Revit el sentido de esa parametrizacion no siempre
         coincide con la orientacion real de la cara dentro del solido (para
         eso existe Face.OrientationMatchesSurfaceOrientation). Unas pocas
         caras inferiores salen con el bobinado invertido y pasan el filtro.
         Se detectan solas: dejan vertices que comparten XY exacto con otro,
         separados justo por el espesor de la losa (1,0000 ft medido en las
         22 piezas) -- y una superficie de terreno real es univaluada.
      2) Aun quitando esos, la malla siguio siendo rechazada, asi que hay
         ademas solapes en planta dentro de alguna pieza.

    Un localizador propio por rejilla no necesita que la malla sea valida:
    se queda con el MAXIMO Z entre los triangulos que cubren el punto, que
    es exactamente la semantica que se quiere (la cara de arriba del
    terreno) y tolera solapes en vez de fallar con ellos."""
    with open(ruta, 'r') as fh:
        datos = json.load(fh)
    A, B, C, S = [], [], [], []
    n_bajos = 0
    for pieza in datos['piezas']:
        v = np.asarray(pieza['v'], dtype=float)
        t = np.asarray(pieza['t'], dtype=np.int64)
        if len(t) == 0:
            continue
        # vertices que comparten XY con otro mas alto -> cara inferior colada
        _, inversa, cuenta = np.unique(v[:, :2], axis=0,
                                       return_inverse=True, return_counts=True)
        bajo = np.zeros(len(v), dtype=bool)
        if cuenta.max() > 1:
            orden = np.lexsort((-v[:, 2], inversa))
            g = inversa[orden]
            es_primero = np.ones(len(orden), dtype=bool)
            es_primero[1:] = g[1:] != g[:-1]
            alto = np.zeros(len(v), dtype=bool)
            alto[orden[es_primero]] = True
            bajo = (~alto) & (cuenta[inversa] > 1)
            n_bajos += int(bajo.sum())
        A.append(v[t[:, 0]])
        B.append(v[t[:, 1]])
        C.append(v[t[:, 2]])
        S.append(bajo[t].any(axis=1))
    A = np.vstack(A); B = np.vstack(B); C = np.vstack(C)
    S = np.concatenate(S)
    log.append('  triangulos en la sopa: %d   sospechosos de cara inferior: %d '
               '(de %d vertices duplicados en XY)' % (len(A), int(S.sum()), n_bajos))
    return datos, A, B, C, S


def indice_rejilla(A, B, C):
    """cell_id -> triangulos que la tocan, en formato ordenado para buscar
    con searchsorted (sin diccionarios ni listas por celda)."""
    minx = np.minimum(np.minimum(A[:, 0], B[:, 0]), C[:, 0])
    maxx = np.maximum(np.maximum(A[:, 0], B[:, 0]), C[:, 0])
    miny = np.minimum(np.minimum(A[:, 1], B[:, 1]), C[:, 1])
    maxy = np.maximum(np.maximum(A[:, 1], B[:, 1]), C[:, 1])
    org_x, org_y = minx.min(), miny.min()
    ix0 = np.floor((minx - org_x) / CELDA).astype(np.int64)
    ix1 = np.floor((maxx - org_x) / CELDA).astype(np.int64)
    iy0 = np.floor((miny - org_y) / CELDA).astype(np.int64)
    iy1 = np.floor((maxy - org_y) / CELDA).astype(np.int64)
    ny = int(iy1.max()) + 1

    celdas, tris = [], []
    for i in range(len(A)):
        for ix in range(ix0[i], ix1[i] + 1):
            base = ix * ny
            for iy in range(iy0[i], iy1[i] + 1):
                celdas.append(base + iy)
                tris.append(i)
    celdas = np.asarray(celdas, dtype=np.int64)
    tris = np.asarray(tris, dtype=np.int64)
    orden = np.argsort(celdas, kind='stable')
    return {'celdas': celdas[orden], 'tris': tris[orden],
            'org': (org_x, org_y), 'ny': ny}


def altura_terreno(px, py, A, B, C, idx, mascara=None):
    """Z de la cara superior del terreno en cada (px, py): maximo Z entre los
    triangulos que cubren el punto. NaN donde no lo cubre ninguno.
    'mascara' permite excluir triangulos (p.ej. los sospechosos)."""
    org_x, org_y = idx['org']
    ny = idx['ny']
    z = np.full(px.shape, np.nan, dtype=float)

    qx = np.floor((px - org_x) / CELDA).astype(np.int64)
    qy = np.floor((py - org_y) / CELDA).astype(np.int64)
    q_celda = qx * ny + qy

    for celda in np.unique(q_celda):
        pts = np.flatnonzero(q_celda == celda)
        lo = np.searchsorted(idx['celdas'], celda, 'left')
        hi = np.searchsorted(idx['celdas'], celda, 'right')
        if lo == hi:
            continue
        cand = idx['tris'][lo:hi]
        if mascara is not None:
            cand = cand[mascara[cand]]
            if cand.size == 0:
                continue

        a = A[cand]; b = B[cand]; c = C[cand]          # (T,3)
        x = px[pts][:, None]; y = py[pts][:, None]      # (P,1)

        # coordenadas baricentricas sin normalizar (productos cruzados en XY)
        w0 = (b[:, 0] - x) * (c[:, 1] - y) - (c[:, 0] - x) * (b[:, 1] - y)
        w1 = (c[:, 0] - x) * (a[:, 1] - y) - (a[:, 0] - x) * (c[:, 1] - y)
        w2 = (a[:, 0] - x) * (b[:, 1] - y) - (b[:, 0] - x) * (a[:, 1] - y)
        det = w0 + w1 + w2
        signo = np.where(det >= 0.0, 1.0, -1.0)
        tol = 1e-9 * np.abs(det)
        dentro = ((w0 * signo >= -tol) & (w1 * signo >= -tol) &
                  (w2 * signo >= -tol) & (np.abs(det) > 0.0))
        if not dentro.any():
            continue

        zz = (w0 * a[:, 2] + w1 * b[:, 2] + w2 * c[:, 2]) / np.where(det == 0.0, 1.0, det)
        zz = np.where(dentro, zz, -np.inf)
        mejor = zz.max(axis=1)
        hay = np.isfinite(mejor)
        if hay.any():
            z[pts[hay]] = mejor[hay]
    return z


def main():
    t0 = time.time()
    log = []

    for ruta in (RUTA_TOPO, RUTA_MARCAS):
        if not os.path.exists(ruta):
            print('FALTA: %s' % ruta)
            if ruta == RUTA_TOPO:
                print('  -> hay que correr 14A_Exportar_Malla_Toposolid.dyn en Revit primero.')
            return 1

    log.append('Toposolid')
    datos_topo, A, B, C, sospechoso = cargar_sopa(RUTA_TOPO, log)
    idx = indice_rejilla(A, B, C)
    log.append('  indice de rejilla: celda %.0f ft, %d entradas'
               % (CELDA, len(idx['celdas'])))

    with open(RUTA_MARCAS, 'r') as fh:
        datos = json.load(fh)
    marcas = [m for m in datos['marcas'] if (not CAPAS or m['capa'] in CAPAS)]
    n_vert_total = sum(len(m['v']) for m in marcas)
    log.append('Marcas: %d piezas (%s), %d vertices en total'
               % (len(marcas), ', '.join(CAPAS) if CAPAS else 'todas', n_vert_total))
    log.append('MODO = %s' % MODO)
    log.append('')

    # --- una sola consulta vectorizada para TODOS los vertices de golpe ------
    todos_x = np.empty(n_vert_total)
    todos_y = np.empty(n_vert_total)
    todos_z = np.empty(n_vert_total)
    rangos = []
    k = 0
    for m in marcas:
        v = np.asarray(m['v'], dtype=float)
        n = len(v)
        todos_x[k:k + n] = v[:, 0] + OFFSET_X
        todos_y[k:k + n] = v[:, 1] + OFFSET_Y
        todos_z[k:k + n] = v[:, 2]
        rangos.append((k, k + n))
        k += n

    t_consulta = time.time()
    limpios = ~sospechoso
    z_terreno = altura_terreno(todos_x, todos_y, A, B, C, idx, mascara=limpios)
    dt_consulta = time.time() - t_consulta
    n_cubiertos = int(np.count_nonzero(~np.isnan(z_terreno)))
    log.append('Consulta de altura: %d vertices en %.2f s (%.1f us por vertice)'
               % (n_vert_total, dt_consulta, 1e6 * dt_consulta / max(1, n_vert_total)))
    log.append('  cubiertos por el terreno: %d de %d (%.1f%%)'
               % (n_cubiertos, n_vert_total, 100.0 * n_cubiertos / n_vert_total))
    if n_cubiertos < n_vert_total:
        log.append('  AVISO: %d vertices caen FUERA de todo Toposolid -- se dejan con su Z '
                   'original (no hay terreno contra el que apoyarlos)'
                   % (n_vert_total - n_cubiertos))

    # Comprobacion cruzada: repetir la consulta SIN excluir los triangulos
    # sospechosos de cara inferior. Si excluirlos hubiera abierto un agujero
    # en el terreno, aqui aparecerian puntos cubiertos que antes no lo
    # estaban -- y esos habrian quedado sin apoyo por culpa de la limpieza.
    if sospechoso.any():
        z_todo = altura_terreno(todos_x, todos_y, A, B, C, idx, mascara=None)
        perdidos = int(np.count_nonzero(np.isnan(z_terreno) & ~np.isnan(z_todo)))
        ambos = ~np.isnan(z_terreno) & ~np.isnan(z_todo)
        difmax = float(np.abs(z_terreno[ambos] - z_todo[ambos]).max()) if ambos.any() else 0.0
        log.append('  control (con y sin los triangulos sospechosos): %d vertices perderian '
                   'apoyo al excluirlos, diferencia maxima de altura %.4f ft'
                   % (perdidos, difmax))
        if perdidos:
            log.append('    OJO: hay zonas cubiertas SOLO por cara inferior -- revisar antes '
                       'de dar por bueno el resultado')
    log.append('')

    # --- correccion POR VERTICE, preservando el espesor ----------------------
    #
    # OJO -- una version anterior agrupaba los vertices en celdas XY de 0,01 ft
    # y usaba UN SOLO valor de terreno (el maximo de la celda) para todo el
    # grupo. Esta mal, y se vio con datos reales: en la marca 193 una celda
    # junto 3 posiciones XY distintas separadas 0,005 ft, y el terreno varia
    # 0,9169 ft en esa distancia (un borde casi vertical del Toposolid). Los
    # vertices del lado bajo recibieron la altura del lado alto y quedaron
    # volando 0,94 ft. Con escalones reales de hasta 0,17 ft entre piezas
    # solapadas, cualquier agrupacion espacial del terreno introduce este error.
    #
    # Ahora cada vertice usa SU PROPIO terreno. El espesor se conserva por
    # construccion: la cara de arriba y la de abajo estan en el MISMO XY
    # exacto (la pieza se extruyo recta hacia abajo), asi que consultan el
    # mismo terreno, y basta con bajar la de abajo el espesor de la marca.
    espesor = float(datos.get('espesor_ft', 0.02))
    marcas_corregidas = []
    deltas_todos = []
    piezas_tocadas = 0
    sin_cobertura_piezas = []
    n_inferiores = 0

    for m, (i0, i1) in zip(marcas, rangos):
        v = np.asarray(m['v'], dtype=float)
        zt = z_terreno[i0:i1]
        px = todos_x[i0:i1]
        py = todos_y[i0:i1]

        # Identificar que vertices son la cara INFERIOR: los que tienen otro
        # vertice en su MISMO XY exacto, justo un espesor mas arriba.
        clave = np.stack([np.round(px * 1e6).astype(np.int64),
                          np.round(py * 1e6).astype(np.int64)], axis=1)
        _, columna = np.unique(clave, axis=0, return_inverse=True)
        columna = np.asarray(columna).ravel()
        orden = np.lexsort((v[:, 2], columna))
        col_ord = columna[orden]
        z_ord = v[orden, 2]
        es_inferior_ord = np.zeros(len(v), dtype=bool)
        if len(v) > 1:
            misma_col = col_ord[1:] == col_ord[:-1]
            salto = z_ord[1:] - z_ord[:-1]
            es_inferior_ord[:-1] = misma_col & (np.abs(salto - espesor) <= 1e-4)
        es_inferior = np.zeros(len(v), dtype=bool)
        es_inferior[orden] = es_inferior_ord
        n_inferiores += int(es_inferior.sum())

        objetivo = zt + ELEVACION - np.where(es_inferior, espesor, 0.0)
        delta = np.where(np.isnan(zt), 0.0, objetivo - v[:, 2])
        if MODO == 'solo_enterradas':
            delta = np.where(delta > TOLERANCIA, delta, 0.0)

        movidos = np.flatnonzero(delta != 0.0)
        if movidos.size:
            piezas_tocadas += 1
            deltas_todos.append(delta[movidos])

        v_corr = v.copy()
        v_corr[:, 2] += delta
        marcas_corregidas.append({'id': m['id'], 'capa': m['capa'], 'area': m.get('area'),
                                  'v': [[round(float(a), 5), round(float(b), 5), round(float(c), 5)]
                                        for a, b, c in v_corr],
                                  'f': m['f']})
        if np.isnan(zt).all():
            sin_cobertura_piezas.append(m['id'])

    if deltas_todos:
        d = np.concatenate(deltas_todos)
        subidos = d[d > 0]
        bajados = d[d < 0]
        log.append('CORRECCION APLICADA')
        log.append('  piezas con algun vertice movido: %d de %d' % (piezas_tocadas, len(marcas)))
        log.append('  vertices movidos: %d de %d' % (d.size, n_vert_total))
        log.append('    subidos (estaban enterrados): %d   max %.3f ft   mediana %.3f ft'
                   % (subidos.size, subidos.max() if subidos.size else 0.0,
                      np.median(subidos) if subidos.size else 0.0))
        log.append('    bajados (estaban flotando):   %d   max %.3f ft   mediana %.3f ft'
                   % (bajados.size, -bajados.min() if bajados.size else 0.0,
                      -np.median(bajados) if bajados.size else 0.0))
    else:
        log.append('CORRECCION APLICADA: ningun vertice necesito moverse')
    log.append('  vertices identificados como cara inferior: %d de %d (%.1f%%, se espera ~50%%)'
               % (n_inferiores, n_vert_total, 100.0 * n_inferiores / max(1, n_vert_total)))
    if sin_cobertura_piezas:
        log.append('  piezas SIN terreno debajo en ningun vertice (%d): %s'
                   % (len(sin_cobertura_piezas), sin_cobertura_piezas[:20]))
    log.append('')

    # --- verificacion: volver a medir el resultado, no darlo por bueno -------
    z_final = np.empty(n_vert_total)
    k = 0
    for mc in marcas_corregidas:
        arr = np.asarray(mc['v'], dtype=float)
        z_final[k:k + len(arr)] = arr[:, 2]
        k += len(arr)

    cubierto = ~np.isnan(z_terreno)
    holgura = z_final[cubierto] - z_terreno[cubierto]     # >0 = por encima del terreno
    # El umbral NO puede ser mas fino que la precision con la que se guarda el
    # JSON (5 decimales = 1e-5 ft): la cara inferior se deja exactamente a la
    # cota del terreno, asi que ese redondeo la puede dejar unas micras por
    # debajo. Con 1e-6 la verificacion daba 18.923 falsos positivos de 1,5 um.
    UMBRAL_ENTERRADO = 1e-4      # ft = 0,03 mm
    enterrados = int(np.count_nonzero(holgura < -UMBRAL_ENTERRADO))
    log.append('VERIFICACION sobre el resultado (solo vertices con terreno debajo)')
    log.append('  holgura sobre el terreno: min %.4f | mediana %.4f | max %.4f ft'
               % (holgura.min(), np.median(holgura), holgura.max()))
    log.append('  vertices por debajo del terreno mas de %.0e ft: %d'
               % (UMBRAL_ENTERRADO, enterrados))
    if MODO == 'conformar':
        fuera = int(np.count_nonzero(np.abs(holgura - ELEVACION) > 1e-4))
        log.append('  vertices cuya cara no quedo exactamente a %.2f ft del terreno: %d'
                   % (ELEVACION, fuera))
        log.append('    (se esperan los de la cara INFERIOR, a %.2f ft por debajo de la '
                   'superior -- el espesor de la marca)' % datos.get('espesor_ft', 0.02))

    salida = {'origen_local': datos['origen_local'],
              'espesor_ft': datos['espesor_ft'],
              'n': len(marcas_corregidas),
              'modo_correccion': MODO,
              'marcas': marcas_corregidas}
    with open(RUTA_SALIDA, 'w') as fh:
        json.dump(salida, fh)
    log.append('')
    log.append('salida: %s  (%.1f MB)' % (RUTA_SALIDA, os.path.getsize(RUTA_SALIDA) / 1e6))
    log.append('tiempo total: %.1f s' % (time.time() - t0))

    texto = '\n'.join(log)
    with open(RUTA_LOG, 'w') as fh:
        fh.write('SOUTH ISLAND -- CORRECCION DE ALTURA CALCULADA FUERA DE REVIT\n')
        fh.write('=' * 70 + '\n\n')
        fh.write(texto + '\n')
    print(texto)
    return 0


if __name__ == '__main__':
    sys.exit(main())
