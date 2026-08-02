# -*- coding: utf-8 -*-
"""
Corrige un paquete Dynamo -> Revit (Toposolid) para que la importacion salga
limpia: sin "Slab Shape Edit failed" y sin perfiles rechazados.

    python corregir_paquete_revit.py <carpeta_origen> <carpeta_destino>

Dos defectos distintos, con causas distintas (diagnosticados sobre North Island):

1) "Slab Shape Edit failed"
   Los contornos vienen simplificados (0.01 ft) mientras los puntos siguen
   siendo los vertices del TIN original: miles quedan ligeramente FUERA del
   perfil. Revit no acepta un punto de forma fuera del perimetro. Responder
   "Reset Shape" salva la transaccion pero BORRA los puntos de esa pieza, que
   queda plana (pierde el terreno).
   SOLUCION: descartar esos puntos. Son puntos de borde y el perimetro ya
   define el borde. OJO: proyectarlos sobre el contorno en vez de descartarlos
   es peor -- crea cumulos de puntos casi coincidentes, que es otra causa del
   mismo dialogo (probado: los errores subieron de 7 a 23).
   Ademas se eliminan puntos mutuamente muy proximos, que el script de Dynamo
   no filtra (solo filtra los vertices del contorno).

2) "The input curve loops cannot compose a valid boundary"
   El anillo tiene un PINZAMIENTO: dos tramos no consecutivos pasan a menos de
   la tolerancia de Revit (1/32" = 0.0026 ft) sin llegar a cruzarse. Shapely lo
   da por valido (no hay interseccion exacta); Revit lo rechaza. En North Island
   los pinzamientos culpables median 0.00003 a 0.00009 ft.
   SOLUCION: separar esos tramos hasta superar la tolerancia. El movimiento es
   de decimas de milimetro y no se aprecia.

3) La ruta del log del script de Dynamo apuntaba a ~/Desktop, que no existe si
   el escritorio esta redirigido a OneDrive. Se reescribe junto a los CSV.
"""
from __future__ import annotations

import csv
import math
import os
import shutil
import sys
from collections import OrderedDict, defaultdict

from shapely.geometry import Polygon, Point, LineString
from shapely.ops import nearest_points

MIN_SEG_LEN = 0.1              # filtro de vertices que aplica el script de Dynamo
TOL_REVIT = 1.0 / 32 / 12      # 1/32" en pies = 0.002604
# Solo se descarta lo que Revit no puede digerir. Un punto DENTRO pero pegado al
# borde es valido: exigirle margen descarto el 74% de los puntos y dejo piezas
# con 2 puntos, o sea el terreno aplanado -- justo lo que se quiere evitar.
MARGEN_FUERA = TOL_REVIT       # se descarta si cae FUERA mas que esto
MIN_DIST_PUNTOS = 0.01         # solo puntos practicamente coincidentes
SEPARACION_PINZA = 0.02        # a cuanto se abre un pinzamiento (8x la tolerancia)
UMBRAL_PINZA = 0.005           # por debajo de esto se considera pinzamiento


# ----------------------------------------------------------------- lectura ---
def limpiar(pts):
    """Replica build_loop() del script de Dynamo."""
    out = [pts[0]]
    for p in pts[1:]:
        if math.dist(out[-1], p) >= MIN_SEG_LEN:
            out.append(p)
    while len(out) > 1 and math.dist(out[0], out[-1]) < MIN_SEG_LEN:
        out.pop()
    return out


def cargar(carpeta):
    pts = defaultdict(list)
    with open(os.path.join(carpeta, "All_Points_ByPiece.csv"), newline="") as f:
        r = csv.reader(f)
        cab_p = next(r)
        for row in r:
            pts[(row[0], int(row[1]))].append(
                (float(row[2]), float(row[3]), float(row[4])))
    rings = OrderedDict()
    cab_b = None
    with open(os.path.join(carpeta, "All_Boundaries_Complete.csv"), newline="") as f:
        r = csv.reader(f)
        cab_b = next(r)
        for row in r:
            k = (row[0], int(row[1]))
            d = rings.setdefault(k, {"OUTER": {}, "HOLE": {}})
            d[row[2]].setdefault(int(row[3]), []).append(
                (int(row[4]), float(row[5]), float(row[6])))
    return pts, rings, cab_p, cab_b


# --------------------------------------------------------------- pinzamiento -
def peor_pinza(anillo):
    """(distancia, i, j) del par de tramos NO adyacentes mas proximos."""
    n = len(anillo)
    segs = [LineString([anillo[i], anillo[(i + 1) % n]]) for i in range(n)]
    peor, par = float("inf"), None
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue                      # adyacentes por el cierre
            d = segs[i].distance(segs[j])
            if d < peor:
                peor, par = d, (i, j)
    return peor, par


def abrir_pinza(anillo, intentos=8):
    """Separa los tramos pinzados hasta superar la tolerancia de Revit."""
    anillo = [list(p) for p in anillo]
    movimientos = 0
    for _ in range(intentos):
        d, par = peor_pinza([tuple(p) for p in anillo])
        if d >= UMBRAL_PINZA or par is None:
            break
        n = len(anillo)
        i, j = par
        a = LineString([anillo[i], anillo[(i + 1) % n]])
        b = LineString([anillo[j], anillo[(j + 1) % n]])
        pa, pb = nearest_points(a, b)
        vx, vy = pb.x - pa.x, pb.y - pa.y
        norma = math.hypot(vx, vy)
        if norma < 1e-12:                     # se tocan exactamente: usar normal
            dx = anillo[(i + 1) % n][0] - anillo[i][0]
            dy = anillo[(i + 1) % n][1] - anillo[i][1]
            L = math.hypot(dx, dy) or 1.0
            vx, vy, norma = -dy / L, dx / L, 1.0
        ux, uy = vx / norma, vy / norma
        paso = (SEPARACION_PINZA - d) / 2.0
        for idx in (i, (i + 1) % n):          # tramo A se aleja de B
            anillo[idx][0] -= ux * paso
            anillo[idx][1] -= uy * paso
        for idx in (j, (j + 1) % n):          # tramo B se aleja de A
            anillo[idx][0] += ux * paso
            anillo[idx][1] += uy * paso
        movimientos += 1
    return [tuple(p) for p in anillo], movimientos


# ---------------------------------------------------------------------- main -
def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    origen, destino = sys.argv[1], sys.argv[2]
    if not os.path.isdir(origen):
        sys.exit("No existe: " + origen)
    os.makedirs(destino, exist_ok=True)

    pts, rings, cab_p, cab_b = cargar(origen)
    print("Origen: %s" % origen)
    print("  piezas %d | puntos %d" % (len(rings), sum(len(v) for v in pts.values())))

    # --- 1. abrir pinzamientos del contorno exterior -----------------------
    print("\n[1] Pinzamientos del contorno (tolerancia Revit %.6f ft)" % TOL_REVIT)
    nuevos_anillos = {}
    arreglados = []
    for k, d in rings.items():
        crudo = [(x, y) for _, x, y in sorted(d["OUTER"][0])]
        anillo = limpiar(crudo)
        if len(anillo) < 4:
            nuevos_anillos[k] = anillo
            continue
        antes, _ = peor_pinza(anillo)
        if antes >= UMBRAL_PINZA:
            nuevos_anillos[k] = anillo
            continue
        abierto, movs = abrir_pinza(anillo)
        despues, _ = peor_pinza(abierto)
        ok = Polygon(abierto).is_valid and LineString(abierto + [abierto[0]]).is_simple
        arreglados.append((k, antes, despues, movs, ok))
        nuevos_anillos[k] = abierto
    if arreglados:
        for k, a, b, m, ok in arreglados:
            print("  %-28s %.8f -> %.8f ft  (%d ajustes) %s"
                  % (("%s#%d" % k)[:28], a, b, m, "OK" if ok else "REVISAR"))
    else:
        print("  ninguno")
    if any(not ok for *_, ok in arreglados):
        sys.exit("ABORTADO: algun anillo quedo invalido tras abrir el pinzamiento.")

    # --- 2. puntos: descartar los de fuera y los demasiado juntos ----------
    print("\n[2] Puntos de forma")
    salida, fuera_tot, juntos_tot = [], 0, 0
    for k in rings:
        anillo = nuevos_anillos[k]
        huecos = []
        for rid in sorted(rings[k]["HOLE"]):
            h = limpiar([(x, y) for _, x, y in sorted(rings[k]["HOLE"][rid])])
            if len(h) >= 3:
                huecos.append(h)
        perfil = Polygon(anillo, huecos) if len(anillo) >= 3 else None
        if perfil is not None and not perfil.is_valid:
            perfil = perfil.buffer(0)
        conservados = []
        for x, y, z in pts.get(k, []):
            if perfil is not None:
                q = Point(x, y)
                if not perfil.covers(q) and q.distance(perfil) > MARGEN_FUERA:
                    fuera_tot += 1
                    continue
            if any(math.dist((x, y), (px, py)) < MIN_DIST_PUNTOS
                   for px, py, _ in conservados[-40:]):
                juntos_tot += 1
                continue
            conservados.append((x, y, z))
        for x, y, z in conservados:
            salida.append((k[0], k[1], x, y, z))
    print("  descartados por caer fuera del perfil : %d" % fuera_tot)
    print("  descartados por estar muy juntos      : %d" % juntos_tot)
    print("  puntos conservados                    : %d" % len(salida))
    vacias = [k for k in rings if not any(s[0] == k[0] and s[1] == k[1] for s in salida[:0])]
    por_pieza = defaultdict(int)
    for s in salida:
        por_pieza[(s[0], s[1])] += 1
    sin = [k for k in rings if por_pieza[k] == 0]
    if sin:
        print("  [!] piezas que quedarian SIN puntos: %s" % sin)
    print("  minimo de puntos en una pieza         : %d" % min(por_pieza.values()))

    # --- escribir paquete --------------------------------------------------
    with open(os.path.join(destino, "All_Points_ByPiece.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cab_p)
        for s, pid, x, y, z in salida:
            w.writerow([s, pid, "%.9f" % x, "%.9f" % y, "%.6f" % z])

    with open(os.path.join(destino, "All_Boundaries_Complete.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cab_b)
        for k, d in rings.items():
            for seq, (x, y) in enumerate(nuevos_anillos[k]):
                w.writerow([k[0], k[1], "OUTER", 0, seq, "%.9f" % x, "%.9f" % y])
            for rid in sorted(d["HOLE"]):
                for seq, (_, x, y) in enumerate(sorted(d["HOLE"][rid])):
                    w.writerow([k[0], k[1], "HOLE", rid, seq, "%.9f" % x, "%.9f" % y])

    for nombre in ("Surface_Boundaries_Complete_v2.dxf", "GEORREFERENCIA.txt",
                   "Dynamo_DiagnosticoToposolidCreate.py"):
        o = os.path.join(origen, nombre)
        if os.path.exists(o):
            shutil.copy2(o, os.path.join(destino, nombre))

    # --- script con la ruta del log corregida ------------------------------
    with open(os.path.join(origen, "Dynamo_CreateToposolids_ConHuecos.py"),
              encoding="utf-8") as f:
        codigo = f.read()
    viejo = "log_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'dynamo_log.txt')"
    nuevo = ("# ~/Desktop no existe si el escritorio esta redirigido a OneDrive:\n"
             "# el log va junto a los CSV, que siempre existen.\n"
             "log_path = os.path.join(os.path.dirname(points_path), 'dynamo_log.txt')")
    if viejo in codigo:
        codigo = codigo.replace(viejo, nuevo)
    with open(os.path.join(destino, "Dynamo_CreateToposolids_ConHuecos.py"),
              "w", encoding="utf-8") as f:
        f.write(codigo)

    # --- verificacion final sobre lo escrito -------------------------------
    print("\n[3] Verificacion del paquete escrito")
    pts2, rings2, _, _ = cargar(destino)
    mal_pinza, mal_fuera, mal_juntos = [], 0, 0
    for k, d in rings2.items():
        anillo = limpiar([(x, y) for _, x, y in sorted(d["OUTER"][0])])
        if len(anillo) >= 4:
            p, _ = peor_pinza(anillo)
            if p < TOL_REVIT:
                mal_pinza.append((k, p))
        perfil = Polygon(anillo) if len(anillo) >= 3 else None
        if perfil is not None and not perfil.is_valid:
            perfil = perfil.buffer(0)
        grupo = pts2.get(k, [])
        for i, (x, y, z) in enumerate(grupo):
            q = Point(x, y)
            if perfil is not None and not perfil.covers(q) and q.distance(perfil) > MARGEN_FUERA:
                mal_fuera += 1
            for x2, y2, _ in grupo[max(0, i - 40):i]:
                if math.dist((x, y), (x2, y2)) < MIN_DIST_PUNTOS:
                    mal_juntos += 1
                    break
    print("  piezas con pinzamiento bajo tolerancia : %d" % len(mal_pinza))
    for k, p in mal_pinza:
        print("     %-28s %.8f ft" % (("%s#%d" % k)[:28], p))
    print("  puntos fuera del perfil                : %d" % mal_fuera)
    print("  puntos demasiado juntos                : %d" % mal_juntos)
    ok = not mal_pinza and mal_fuera == 0 and mal_juntos == 0
    print("\n  %s" % ("OK: paquete listo para importar sin dialogos"
                      if ok else "ATENCION: quedan defectos"))
    print("  -> %s" % destino)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
