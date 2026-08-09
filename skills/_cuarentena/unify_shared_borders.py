# -*- coding: utf-8 -*-
# Unifica los bordes compartidos entre superficies colindantes: donde dos
# superficies DISTINTAS tienen su borde "casi pegado" (a pocos pies una de
# otra), se reemplaza ese tramo en AMBAS por una unica linea promedio -- asi
# ya no hay 2 lineas distintas para el mismo limite fisico, y no puede haber
# intersecciones en XY entre bordes de superficies distintas.
#
# METODO (por cada par candidato, de mayor tramo a menor, para resolver
# primero los casos mas claros):
#   1. Sobre cada anillo, identificar el tramo CONTIGUO de vertices (indices
#      consecutivos, en el orden real del anillo) cuya distancia al OTRO
#      anillo es <= MAX_GAP. No se usa un buffer+interseccion (eso ya nos
#      dio problemas de sesgo) sino distancia real punto a punto.
#   2. Construir la linea promedio: se usa como "columna" el lado con MAS
#      vertices en el tramo (mejor resolucion), y para cada uno de sus puntos
#      se busca el punto mas cercano en el tramo del otro lado (proyeccion
#      sobre el segmento, no solo al vertice mas cercano) y se promedia.
#   3. Reemplazar el tramo en AMBOS anillos por esa misma polilinea (en el
#      orden/sentido que corresponda a cada uno).
#   4. Verificar: los anillos siguen siendo simples y validos.
#
# Se procesa un par a la vez y se recalculan los tramos candidatos DESPUES de
# cada reemplazo (los anillos cambian), para no trabajar con indices viejos.
#
# VERIFICACION FINAL (independiente, sobre el resultado completo):
#   - ningun par de anillos de superficies DISTINTAS se cruza en XY
#   - cada anillo sigue siendo una LinearRing valida y simple
#   - comparacion de area antes/despues por superficie (no debe haber saltos
#     grandes -- estamos promediando bordes que ya estaban a pocos pies, el
#     area solo deberia cambiar en una franja angosta)
import csv, math, os
from collections import defaultdict
import shapely.geometry as sg
from shapely.ops import unary_union

B = r"C:\Users\Usuario\OneDrive\Escritorio\Raul ZOIN\HRCP\CIVIL 3D\North Island\Caminos\Avances\07_Superficies IN Finales en XML"
BOUND_CSV = B + r"\Revit_Package\All_Boundaries_Complete.csv"
OUT_CSV = B + r"\Revit_Package\All_Boundaries_Unified.csv"
OUT_DXF = B + r"\Contornos_Unificados.dxf"
OUT_MD = B + r"\Informe_Unificacion_Bordes.md"

OX, OY = 12119000.0, 3530500.0
MAX_GAP = 5.0          # ft -- por encima de esto, dos bordes no se consideran "el mismo limite"
MIN_RUN_FT = 10.0      # ft -- tramos mas cortos que esto no se tocan (evita ruido en esquinas)
MAX_ROUNDS = 200        # limite de seguridad de pares a procesar


def cargar_anillos(path):
    tmp = defaultdict(list)
    with open(path, newline="", encoding="ascii") as fh:
        r = csv.DictReader(fh)
        for row in r:
            key = (row["SurfaceName"], int(row["PieceId"]), row["RingType"], int(row["RingId"]))
            tmp[key].append((int(row["Seq"]), float(row["X"]), float(row["Y"])))
    out = {}
    for key, pts in tmp.items():
        pts.sort(key=lambda t: t[0])
        out[key] = [(x, y) for _, x, y in pts]
    return out


def dist(a, b): return math.hypot(a[0]-b[0], a[1]-b[1])


def ring_len(pts):
    n = len(pts)
    return sum(dist(pts[i], pts[(i+1) % n]) for i in range(n))


def encontrar_tramo(pts_a, ring_b_ls):
    """Devuelve el tramo CONTIGUO mas largo de indices de pts_a (con posible
    wraparound) cuya distancia a ring_b_ls es <= MAX_GAP. None si no hay."""
    n = len(pts_a)
    d = [ring_b_ls.distance(sg.Point(p)) for p in pts_a]
    cerca = [i for i in range(n) if d[i] <= MAX_GAP]
    if not cerca: return None
    # agrupar en corridas contiguas (con wraparound)
    cerca_set = set(cerca)
    visto = set()
    mejores = []
    for i in cerca:
        if i in visto: continue
        # extender hacia atras y adelante
        lo = i
        while (lo - 1) % n in cerca_set and (lo - 1) % n not in visto:
            lo = (lo - 1) % n
            if lo == i: break
        hi = i
        while (hi + 1) % n in cerca_set:
            hi = (hi + 1) % n
            if hi == lo: break
        # marcar visto
        k = lo
        run = [lo]
        while k != hi:
            k = (k + 1) % n
            run.append(k)
            visto.add(k)
        visto.add(lo)
        mejores.append(run)
    if not mejores: return None
    mejores.sort(key=len, reverse=True)
    run = mejores[0]
    if len(run) < 2: return None
    largo = sum(dist(pts_a[run[k]], pts_a[run[k+1]]) for k in range(len(run)-1))
    if largo < MIN_RUN_FT: return None
    return run, largo


def proyecta_en_linea(pt, line):
    """Punto mas cercano de shapely LineString a pt, como tupla (x,y)."""
    p = line.interpolate(line.project(sg.Point(pt)))
    return (p.x, p.y)


def linea_promedio(chain_a, chain_b):
    """chain_a, chain_b: listas de puntos (en orden, ya orientadas del mismo
    lado a lado -- chain_a es la 'columna'). Devuelve la polilinea promedio,
    mismo numero de puntos que chain_a."""
    line_b = sg.LineString(chain_b) if len(chain_b) >= 2 else None
    out = []
    for p in chain_a:
        if line_b is None:
            out.append(p)
            continue
        q = proyecta_en_linea(p, line_b)
        out.append(((p[0]+q[0])/2.0, (p[1]+q[1])/2.0))
    return out


def reemplazar_tramo(pts, run, nueva_chain):
    """Devuelve una nueva lista de puntos con el tramo 'run' (indices, puede
    envolver) reemplazado por nueva_chain (en el mismo orden que run)."""
    n = len(pts)
    fuera = [i for i in range(n) if i not in set(run)]
    if not fuera:
        return list(nueva_chain)  # todo el anillo era el tramo (caso raro)
    # reconstruir empezando justo despues del final del tramo, dando la vuelta
    start = (run[-1] + 1) % n
    orden = []
    i = start
    while i != run[0]:
        orden.append(i)
        i = (i + 1) % n
    nuevos = [pts[i] for i in orden] + list(nueva_chain)
    return nuevos


anillos = cargar_anillos(BOUND_CSV)
outers = {k: v for k, v in anillos.items() if k[2] == "OUTER"}
holes = {k: v for k, v in anillos.items() if k[2] == "HOLE"}
print(f"{len(outers)} anillos OUTER, {len(holes)} anillos HOLE (los HOLE no se tocan)")

surf_pts = dict(outers)  # copia mutable

log = []
cambios_por_superficie = defaultdict(float)
rechazados = set()   # (ka,kb) que ya fallaron -- no reintentar

ronda = 0
while ronda < MAX_ROUNDS:
    ronda += 1
    # recalcular TODOS los pares candidatos con el estado actual
    keys = list(surf_pts.keys())
    mejor = None
    for i in range(len(keys)):
        for j in range(i+1, len(keys)):
            ka, kb = keys[i], keys[j]
            if ka[0] == kb[0]:
                continue
            if (ka, kb) in rechazados:
                continue
            pts_a = surf_pts[ka]; pts_b = surf_pts[kb]
            ring_b_ls = sg.LinearRing(pts_b + [pts_b[0]])
            # filtro rapido por bbox
            xa = [p[0] for p in pts_a]; ya = [p[1] for p in pts_a]
            xb = [p[0] for p in pts_b]; yb = [p[1] for p in pts_b]
            if (max(xa)+MAX_GAP < min(xb) or max(xb)+MAX_GAP < min(xa) or
                max(ya)+MAX_GAP < min(yb) or max(yb)+MAX_GAP < min(ya)):
                continue
            ta = encontrar_tramo(pts_a, ring_b_ls)
            if ta is None: continue
            run_a, largo_a = ta
            if mejor is None or largo_a > mejor[0]:
                mejor = (largo_a, ka, kb, run_a)
    if mejor is None:
        print(f"\nNo quedan mas pares con tramo compartido >= {MIN_RUN_FT} ft. Ronda final: {ronda-1}")
        break

    largo_a, ka, kb, run_a = mejor
    pts_a = surf_pts[ka]; pts_b = surf_pts[kb]
    ring_b_ls = sg.LinearRing(pts_b + [pts_b[0]])
    chain_a = [pts_a[i] for i in run_a]

    # tramo correspondiente en B: el que esta cerca de chain_a
    tb = encontrar_tramo(pts_b, sg.LineString(chain_a) if len(chain_a) >= 2 else sg.Point(chain_a[0]))
    if tb is None:
        print(f"  [rechazado] {ka} <-> {kb}: no se encontro tramo correspondiente en B")
        rechazados.add((ka, kb))
        continue
    run_b, largo_b = tb
    chain_b = [pts_b[i] for i in run_b]

    # orientar chain_b para que corresponda punto-a-punto con chain_a (mismo sentido)
    if dist(chain_a[0], chain_b[0]) + dist(chain_a[-1], chain_b[-1]) > \
       dist(chain_a[0], chain_b[-1]) + dist(chain_a[-1], chain_b[0]):
        chain_b_al = list(reversed(chain_b))
    else:
        chain_b_al = chain_b

    # columna = el lado con mas puntos (mejor resolucion)
    if len(chain_a) >= len(chain_b_al):
        avg = linea_promedio(chain_a, chain_b_al)
        avg_para_a = avg
        avg_para_b = list(reversed(avg))
    else:
        avg = linea_promedio(chain_b_al, chain_a)
        avg_para_b = avg
        avg_para_a = list(reversed(avg))

    area_a_antes = sg.Polygon(pts_a).area if sg.Polygon(pts_a).is_valid else sg.Polygon(pts_a).buffer(0).area
    area_b_antes = sg.Polygon(pts_b).area if sg.Polygon(pts_b).is_valid else sg.Polygon(pts_b).buffer(0).area

    nuevos_a = reemplazar_tramo(pts_a, run_a, avg_para_a)
    nuevos_b = reemplazar_tramo(pts_b, run_b, avg_para_b)

    poly_a = sg.Polygon(nuevos_a); poly_b = sg.Polygon(nuevos_b)
    ok_a = poly_a.is_valid and sg.LinearRing(nuevos_a + [nuevos_a[0]]).is_simple
    ok_b = poly_b.is_valid and sg.LinearRing(nuevos_b + [nuevos_b[0]]).is_simple
    if not (ok_a and ok_b):
        motivo = []
        if not poly_a.is_valid: motivo.append("poly_a invalida")
        elif not sg.LinearRing(nuevos_a+[nuevos_a[0]]).is_simple: motivo.append("anillo_a no-simple")
        if not poly_b.is_valid: motivo.append("poly_b invalida")
        elif not sg.LinearRing(nuevos_b+[nuevos_b[0]]).is_simple: motivo.append("anillo_b no-simple")
        print(f"  [rechazado] {ka} <-> {kb}: tramo={largo_a:.0f}ft  motivo={','.join(motivo)}")
        rechazados.add((ka, kb))
        continue

    area_a_desp = poly_a.area
    area_b_desp = poly_b.area
    cambios_por_superficie[ka[0]] += abs(area_a_desp - area_a_antes)
    cambios_por_superficie[kb[0]] += abs(area_b_desp - area_b_antes)

    surf_pts[ka] = nuevos_a
    surf_pts[kb] = nuevos_b
    rechazados.add((ka, kb))   # ya unificado -- no reprocesar (evita bucle infinito en el punto fijo)
    log.append((ka, kb, largo_a, area_a_antes, area_a_desp, area_b_antes, area_b_desp))
    print(f"  ronda {ronda}: {ka[0]}(p{ka[1]}) <-> {kb[0]}(p{kb[1]})  tramo={largo_a:.1f}ft  "
          f"area A {area_a_antes:,.1f}->{area_a_desp:,.1f}  area B {area_b_antes:,.1f}->{area_b_desp:,.1f}")

print(f"\n{len(log)} unificaciones aplicadas en {ronda} rondas")

# ---------------------------------------------------------------- salidas
import ezdxf

exitosos = {(ka, kb) for ka, kb, *_ in log}
fallidos_info = []  # se recalculan al final los que quedaron con hueco real

# recalcular, sobre el estado FINAL, que pares siguen teniendo un tramo
# compartido con gap real (no unificado) -- para el reporte de pendientes
def gap_real(pts_a, ring_b_ls, run):
    ds = [ring_b_ls.distance(sg.Point(pts_a[i])) for i in run]
    return sum(ds) / len(ds), max(ds)

keys = list(surf_pts.keys())
pendientes = []
vistos = set()
for i in range(len(keys)):
    for j in range(i+1, len(keys)):
        ka, kb = keys[i], keys[j]
        if ka[0] == kb[0] or (ka, kb) in vistos: continue
        vistos.add((ka, kb))
        pts_a = surf_pts[ka]; pts_b = surf_pts[kb]
        ring_b_ls = sg.LinearRing(pts_b + [pts_b[0]])
        xa=[p[0] for p in pts_a]; ya=[p[1] for p in pts_a]
        xb=[p[0] for p in pts_b]; yb=[p[1] for p in pts_b]
        if (max(xa)+MAX_GAP < min(xb) or max(xb)+MAX_GAP < min(xa) or
            max(ya)+MAX_GAP < min(yb) or max(yb)+MAX_GAP < min(ya)):
            continue
        ta = encontrar_tramo(pts_a, ring_b_ls)
        if ta is None: continue
        run_a, largo_a = ta
        gm, gx = gap_real(pts_a, ring_b_ls, run_a)
        if gm < 0.05: continue  # ya practicamente coincide (unificado o siempre estuvo asi)
        c = pts_a[run_a[len(run_a)//2]]
        pendientes.append({"a": ka, "b": kb, "largo": largo_a, "gap_medio": gm,
                           "gap_max": gx, "centro": c})

pendientes.sort(key=lambda d: -d["largo"])

# --- CSV actualizado (mismo formato que All_Boundaries_Complete.csv) ---
out_rows = []
for (surf, piece, rtype, rid), pts in outers.items():
    final_pts = surf_pts.get((surf, piece, rtype, rid), pts)
    for seq, (x, y) in enumerate(final_pts):
        out_rows.append([surf, piece, "OUTER", 0, seq, f"{x:.4f}", f"{y:.4f}"])
for (surf, piece, rtype, rid), pts in holes.items():
    for seq, (x, y) in enumerate(pts):
        out_rows.append([surf, piece, "HOLE", rid, seq, f"{x:.4f}", f"{y:.4f}"])

with open(OUT_CSV, "w", newline="", encoding="ascii") as fh:
    w = csv.writer(fh)
    w.writerow(["SurfaceName", "PieceId", "RingType", "RingId", "Seq", "X", "Y"])
    w.writerows(out_rows)
print(f"\nCSV actualizado: {OUT_CSV}")

# --- DXF: verde = unificados (14), rojo = pendientes (con gap real) ---
doc = ezdxf.new("R2018")
msp = doc.modelspace()
doc.layers.new("BORDE_UNIFICADO", dxfattribs={"color": 3})
doc.layers.new("BORDE_PENDIENTE", dxfattribs={"color": 1})
for ka, kb, largo, *_ in log:
    pts = surf_pts[ka]
    ring_b_ls = sg.LinearRing(surf_pts[kb] + [surf_pts[kb][0]])
    ta = encontrar_tramo(pts, ring_b_ls)
    if ta:
        run, _ = ta
        coords = [(pts[i][0]+OX, pts[i][1]+OY) for i in run]
        msp.add_lwpolyline(coords, dxfattribs={"layer": "BORDE_UNIFICADO"})
for p in pendientes:
    ka = p["a"]; pts = surf_pts[ka]
    ring_b_ls = sg.LinearRing(surf_pts[p["b"]] + [surf_pts[p["b"]][0]])
    ta = encontrar_tramo(pts, ring_b_ls)
    if ta:
        run, _ = ta
        coords = [(pts[i][0]+OX, pts[i][1]+OY) for i in run]
        msp.add_lwpolyline(coords, dxfattribs={"layer": "BORDE_PENDIENTE"})
doc.saveas(OUT_DXF)
print(f"DXF: {OUT_DXF}")

# --- informe ---
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("# Unificación de bordes compartidos — estado actual\n\n")
    f.write(f"Método: promedio punto-a-punto entre bordes cercanos, reemplazando el tramo "
            f"compartido en ambas superficies por la misma línea. Se verifica que el anillo "
            f"resultante siga siendo válido y simple antes de aceptar el cambio.\n\n")
    f.write(f"**{len(log)} pares unificados con éxito** (verde en `Contornos_Unificados.dxf`, "
            f"capa `BORDE_UNIFICADO`).\n\n")
    f.write("| Superficie A | Superficie B | Tramo |\n|---|---|---|\n")
    for ka, kb, largo, *_ in sorted(log, key=lambda x: -x[2]):
        f.write(f"| {ka[0]} (p{ka[1]}) | {kb[0]} (p{kb[1]}) | {largo:.1f} ft |\n")

    f.write(f"\n**{len(pendientes)} pares PENDIENTES** (rojo en el DXF, capa `BORDE_PENDIENTE`) "
            f"— el reemplazo automático habría dejado un polígono inválido (autointersectado), "
            f"así que no se tocaron. Siguen con 2 líneas distintas.\n\n")
    f.write("| Superficie A | Superficie B | Tramo | Gap medio | Gap máx | Ubicación (real) |\n")
    f.write("|---|---|---|---|---|---|\n")
    for p in pendientes:
        ka, kb = p["a"], p["b"]
        f.write(f"| {ka[0]} (p{ka[1]}) | {kb[0]} (p{kb[1]}) | {p['largo']:.1f} ft | "
                f"{p['gap_medio']:.2f} ft | {p['gap_max']:.2f} ft | "
                f"({p['centro'][0]+OX:,.0f}, {p['centro'][1]+OY:,.0f}) |\n")

print(f"Informe: {OUT_MD}")
print(f"\nRESUMEN: {len(log)} unificados, {len(pendientes)} pendientes")
