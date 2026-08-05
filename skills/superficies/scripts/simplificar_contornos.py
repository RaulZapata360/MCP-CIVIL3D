# -*- coding: utf-8 -*-
# Quita los vertices redundantes de All_Boundaries_Complete.csv.
#
# EL PROBLEMA: los contornos se extraen del borde de la triangulacion, asi que
# CADA vertice de triangulo que cae sobre un tramo recto acaba siendo un vertice
# de la polilinea. Resultado: ~0.4 ft por vertice (Pavement Surface 15 llevaba
# 2,228 vertices donde bastan 62). Los contornos dibujados a mano del proyecto
# van de 5 a 125 ft por vertice. Ese exceso es una de las causas de que Revit
# se atragante al importar.
#
# POR QUE NO SE PUEDE SIMPLIFICAR ANILLO POR ANILLO: la particion planar
# garantiza que dos superficies vecinas comparten EXACTAMENTE la misma linea de
# division. Si cada una simplifica por su cuenta, la linea deja de ser la misma y
# reaparecen los huecos y solapes que tanto costo eliminar. Se probaron dos
# variantes mas debiles antes de llegar a esta:
#   1) quitar vertices colineales mirando solo a los vecinos vivos -> el error se
#      acumula a lo largo de la cadena: 0.15 ft de desviacion con TOL=0.01, un
#      anillo autointersecado y 26 solapes nuevos.
#   2) igual pero acotando contra los vertices ORIGINALES del tramo (garantia de
#      Douglas-Peucker) -> desviacion correcta (0.0100 ft) pero AUN 18 solapes,
#      porque un vertice puede estar sobre una linea compartida y existir solo en
#      el anillo de UNA de las dos vecinas.
#
# PASO PREVIO IMPRESCINDIBLE -- UNIFICAR LOS VERTICES COMPARTIDOS: dos superficies
# vecinas comparten la LINEA pero NO los vertices. Cada una subdivide esa linea
# con los vertices de SU triangulacion. Medido sobre el paquete: el 64% de los
# vertices de borde cae a menos de 0.0001 ft del borde de la vecina (o sea,
# exactamente encima) y el 75.6% a menos de 0.01 ft, pero solo 4,588 de 21,410
# aristas coincidian vertice a vertice.
# Esto envenena el grafo: cada vertice de A que cae sobre un segmento de B hace
# que el extremo de ese segmento tenga grado 3, o sea una "T" FALSA, y las T se
# protegen. Resultado de no hacer este paso: 2,447 nodos protegidos, de los cuales
# 3,957 apariciones eran vertices perfectamente colineales que no se podian tocar
# (Roadway N5 conservaba 328 de 391 vertices colineales, el 83.9%).
# La cura es insertar en cada borde los vertices de la vecina que caen sobre el,
# ANTES de montar el grafo. Asi las cadenas compartidas pasan a ser identicas, las
# T falsas desaparecen y solo quedan las confluencias reales de 3+ superficies.
#
# LO QUE SI FUNCIONA: simplificar la RED DE ARISTAS, no los anillos.
#   1) Se montan todos los bordes como un grafo planar.
#   2) Los NODOS (grado != 2, o donde cambia el conjunto de anillos que usan la
#      arista) se conservan siempre: son las esquinas donde confluyen 3 o mas
#      superficies, y moverlas si abriria huecos.
#   3) Cada ARCO entre dos nodos se simplifica UNA SOLA VEZ con Douglas-Peucker.
#   4) Los anillos se reconstruyen a partir de los arcos ya simplificados.
# Como el arco compartido se simplifica una vez y las dos vecinas leen el mismo
# resultado, la linea de division sigue siendo identica POR CONSTRUCCION -- no es
# algo que haya que comprobar despues.
#
# Uso:  python simplificar_contornos.py <dir_paquete> [tolerancia_ft]
import os, sys, csv, math
from collections import OrderedDict, defaultdict
import shapely.geometry as sg
from shapely.ops import unary_union

D = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\Usuario\OneDrive\Escritorio\Raul ZOIN\HRCP\CIVIL 3D\North Island" \
    r"\Caminos\Avances\07_Superficies IN Finales en XML\Revit_Package_06"
TOL = float(sys.argv[2]) if len(sys.argv) > 2 else 0.01
BND = os.path.join(D, "All_Boundaries_Complete.csv")


def dist_pt_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 == 0.0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def douglas_peucker(pts, tol):
    """Simplifica una polilinea ABIERTA conservando los dos extremos. Garantiza
    que ningun punto original queda a mas de tol de la linea resultante."""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    pila = [(0, len(pts) - 1)]
    while pila:
        i, j = pila.pop()
        if j - i < 2:
            continue
        a, b = pts[i], pts[j]
        peor, pk = tol, -1
        for k in range(i + 1, j):
            d = dist_pt_seg(pts[k], a, b)
            if d > peor:
                peor, pk = d, k
        if pk >= 0:
            keep[pk] = True
            pila.append((i, pk))
            pila.append((pk, j))

    # Douglas-Peucker es voraz de arriba abajo y conserva vertices que ya no hacen
    # falta una vez fijados los demas. Una pasada de pulido quita los que sobran:
    # se prueba a eliminar cada superviviente y se acepta si TODOS los puntos
    # originales del tramo que abarca siguen a menos de tol de la recta. Medido:
    # recupera unos 600 vertices sobre 4,500 sin tocar la garantia de desviacion.
    vivos = [i for i, k in enumerate(keep) if k]
    cambio = True
    while cambio and len(vivos) > 2:
        cambio = False
        for a in range(1, len(vivos) - 1):
            i, j = vivos[a - 1], vivos[a + 1]
            if max((dist_pt_seg(pts[t], pts[i], pts[j])
                    for t in range(i + 1, j)), default=0.0) <= tol:
                del vivos[a]
                cambio = True
                break
    return [pts[i] for i in vivos]


def key(p):
    return (round(p[0], 4), round(p[1], 4))


# ---------------------------------------------------------------- lectura
tmp = OrderedDict()
with open(BND) as f:
    r = csv.reader(f)
    hdr = next(r)
    for row in r:
        k = (row[0], int(row[1]), row[2], int(row[3]))
        tmp.setdefault(k, []).append((int(row[4]), (float(row[5]), float(row[6]))))
rings = OrderedDict((k, [q for _, q in sorted(v, key=lambda t: t[0])])
                    for k, v in tmp.items())
orig = {k: list(v) for k, v in rings.items()}
n_orig = sum(len(v) for v in rings.values())

# --------------------------------- unificar los vertices compartidos
# Inserta en cada anillo los vertices de OTRAS superficies que caen sobre sus
# segmentos. Sin esto las cadenas compartidas no coinciden vertice a vertice y el
# grafo se llena de "T" falsas que bloquean la simplificacion (ver cabecera).
from shapely.strtree import STRtree

EPS = 0.01     # a que distancia se considera que un vertice esta SOBRE el borde

todos = []
dueno = []
for rk, pts in rings.items():
    for p in pts:
        todos.append(sg.Point(p))
        dueno.append(rk[0])          # nombre de la superficie
arbol = STRtree(todos)

def candidatos(pts, surf, eps):
    """Por cada segmento del anillo, que vertices de OTRAS superficies caen sobre
    el. Devuelve {indice de segmento: [puntos en orden a lo largo del segmento]}."""
    n = len(pts)
    res = {}
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        seg = sg.LineString([a, b])
        if seg.length < 1e-9:
            continue
        cand = []
        for j in arbol.query(seg.buffer(eps)):
            if dueno[j] == surf:
                continue                       # de la misma superficie, no aporta
            q = (todos[j].x, todos[j].y)
            if key(q) == key(a) or key(q) == key(b):
                continue
            if dist_pt_seg(q, a, b) > eps:
                continue
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / (dx * dx + dy * dy)
            if 1e-9 < t < 1 - 1e-9:
                cand.append((t, q))
        vistos = set()
        orden = []
        for t, q in sorted(cand):
            if key(q) in vistos:
                continue
            vistos.add(key(q))
            orden.append(q)
        if orden:
            res[i] = orden
    return res


def armar(pts, cand, activos):
    out = []
    for i, p in enumerate(pts):
        out.append(p)
        if i in activos:
            out.extend(cand[i])
    return out


def simple(anillo):
    return sg.LinearRing(anillo + [anillo[0]]).is_simple


# La insercion NO puede romper el anillo: un vertice ajeno que este hasta eps
# fuera del segmento mete un pequeño desvio, y donde el borde vuelve sobre si
# mismo (un cuello estrecho) ese desvio llega a cruzarse. Con eps=0.01 al bruto
# quedaban 11 anillos autointersecados incluso con la simplificacion apagada.
#
# Descartar la insercion del anillo ENTERO es peor el remedio: los que fallan son
# los grandes, se quedan llenos de "T" falsas y el paquete entero empeora (medido:
# 69.6% de reduccion, frente al 82.4% del caso sin romper). Bajarles el eps a todos
# tampoco: deja a Roadway N9 sin ninguna insercion.
#
# Asi que el descarte es POR SEGMENTO. Se prueban por bloques y, si un bloque
# rompe el anillo, se prueba segmento a segmento dentro de el. Solo se cae la
# insercion concreta que cruza, no las otras miles del mismo anillo.
insertados = 0
parciales = []
for rk in list(rings):
    base = rings[rk]
    cand = candidatos(base, rk[0], EPS)
    if not cand:
        continue
    segs = sorted(cand)
    if simple(armar(base, cand, set(segs))):
        rings[rk] = armar(base, cand, set(segs))
        insertados += sum(len(v) for v in cand.values())
        continue
    activos = set()
    BLOQUE = 64
    for k0 in range(0, len(segs), BLOQUE):
        bloque = segs[k0:k0 + BLOQUE]
        if simple(armar(base, cand, activos | set(bloque))):
            activos |= set(bloque)
        else:
            for s in bloque:
                if simple(armar(base, cand, activos | {s})):
                    activos.add(s)
    rings[rk] = armar(base, cand, activos)
    puestos = sum(len(cand[s]) for s in activos)
    insertados += puestos
    parciales.append((rk[0], len(segs) - len(activos),
                      sum(len(v) for v in cand.values()) - puestos))
print(f"vertices insertados para unificar bordes compartidos: {insertados:,}"
      f"   ({n_orig:,} -> {sum(len(v) for v in rings.values()):,})")
if parciales:
    print("  inserciones descartadas por cruzar el anillo: "
          + ", ".join(f"{s}: {v} vertices en {n} segmentos" for s, n, v in sorted(parciales)))

# ------------------------------------------------------------- el grafo
coord = {}                       # key -> (x,y) representativo
arista = defaultdict(set)        # frozenset({ka,kb}) -> {ring_id}
adj = defaultdict(set)           # key -> {key vecino}
for rk, pts in rings.items():
    n = len(pts)
    for i, p in enumerate(pts):
        coord.setdefault(key(p), p)
    for i in range(n):
        a, b = key(pts[i]), key(pts[(i + 1) % n])
        if a == b:
            continue
        arista[frozenset((a, b))].add(rk)
        adj[a].add(b)
        adj[b].add(a)

# un punto es NODO si no es un simple paso entre dos aristas equivalentes
inc = defaultdict(list)
for e, rs in arista.items():
    for k in e:
        inc[k].append((e, rs))
nodos = set()
for k, lst in inc.items():
    if len(lst) != 2 or len(adj[k]) != 2:
        nodos.add(k)
    elif lst[0][1] != lst[1][1]:
        nodos.add(k)          # aqui cambia que superficies comparten la linea
compartidas = sum(1 for rs in arista.values() if len(rs) > 1)
print(f"anillos: {len(rings)}   vertices: {n_orig:,}")
print(f"aristas: {len(arista):,}  (compartidas por 2+ anillos: {compartidas:,})")
print(f"nodos del grafo (intocables): {len(nodos):,}")
print(f"tolerancia: {TOL} ft\n")

# ------------------------------------------------- descomposicion en arcos
# Cada arco se guarda UNA vez con una clave canonica (la cadena de vertices, o su
# inversa si es menor). Asi las dos superficies que comparten un arco apuntan al
# mismo objeto: lo que se decida sobre el vale igual para las dos.
arcos = {}                       # clave canonica -> lista de puntos
arcos_de = defaultdict(list)     # ring_id -> [clave canonica]
anclas_extra = set()

for rk, pts in rings.items():
    n = len(pts)
    idx_nodos = [i for i, p in enumerate(pts) if key(p) in nodos]
    if len(idx_nodos) < 2:
        # Anillo aislado sin nodos, o con uno solo: es el caso de los huecos de
        # edificacion, que no tocan a ninguna otra superficie. Hacen falta DOS
        # anclas para poder abrirlo en arcos; con una sola el unico "arco" va del
        # vertice a si mismo, Douglas-Peucker no llega a correr y el anillo se
        # queda en 1 vertice.
        idx_nodos = sorted(set(idx_nodos) | {0, n // 2})
        for i in idx_nodos:
            anclas_extra.add(key(pts[i]))
    for a in range(len(idx_nodos)):
        i, j = idx_nodos[a], idx_nodos[(a + 1) % len(idx_nodos)]
        tramo = [pts[(i + t) % n] for t in range(((j - i) % n) + 1)]
        if len(tramo) <= 2:
            continue
        ks = tuple(key(p) for p in tramo)
        ck = min(ks, ks[::-1])
        arcos.setdefault(ck, tramo if ks == ck else tramo[::-1])
        arcos_de[rk].append(ck)
print(f"arcos distintos: {len(arcos):,}   "
      f"(longitud media {sum(len(v) for v in arcos.values())/max(1,len(arcos)):.0f} vertices)")


def construir(tol_arco):
    """Aplica Douglas-Peucker a cada arco con SU tolerancia y rearma los anillos."""
    vivos = set(nodos) | anclas_extra
    for ck, tramo in arcos.items():
        for p in douglas_peucker(tramo, tol_arco[ck]):
            vivos.add(key(p))
    out = OrderedDict()
    for rk, pts in rings.items():
        v = [p for p in pts if key(p) in vivos]
        v = [p for i, p in enumerate(v) if i == 0 or key(p) != key(v[i - 1])]
        while len(v) > 1 and key(v[0]) == key(v[-1]):
            v.pop()
        out[rk] = v
    return out


def roto(pts):
    return len(pts) < 3 or not sg.LinearRing(pts + [pts[0]]).is_simple


# Un arco largo simplificado de golpe puede cortar por encima de un
# estrechamiento y hacer que el anillo se cruce consigo mismo. En vez de bajar la
# tolerancia de todo el paquete, se baja SOLO en los arcos de los anillos que
# fallan, y se repite. Como el arco es compartido, la vecina hereda la misma
# version mas fina y la linea comun sigue siendo identica.
tol_arco = dict.fromkeys(arcos, TOL)
nuevo = construir(tol_arco)
for intento in range(1, 15):
    malos_ahora = [rk for rk, pts in nuevo.items() if roto(pts)]
    if not malos_ahora:
        break
    afectados = set()
    for rk in malos_ahora:
        afectados.update(arcos_de[rk])
    tocados = 0
    for ck in afectados:
        if tol_arco[ck] > 0.0:
            tol_arco[ck] = 0.0 if tol_arco[ck] <= 1e-4 else tol_arco[ck] / 4.0
            tocados += 1
    print(f"  reparacion {intento}: {len(malos_ahora)} anillos cruzados -> "
          f"se afina la tolerancia de {tocados:,} arcos")
    if tocados == 0:
        break
    nuevo = construir(tol_arco)

afinados = sum(1 for v in tol_arco.values() if v < TOL)
n_new = sum(len(v) for v in nuevo.values())
print(f"arcos que necesitaron tolerancia mas fina: {afinados:,} de {len(arcos):,}")
print(f"vertices: {n_orig:,} -> {n_new:,}   ({100*(1-n_new/n_orig):.1f}% menos)")

# ------------------------------------------------------- verificaciones
print("\nVERIFICACION")
malos = []
desv_max = 0.0
for rk, pts in nuevo.items():
    if len(pts) < 3:
        malos.append((rk, "quedan menos de 3 vertices"))
        continue
    if not sg.LinearRing(pts + [pts[0]]).is_simple:
        malos.append((rk, "el anillo simplificado se autointerseca"))
        continue
    ls = sg.LineString(pts + [pts[0]])
    desv_max = max(desv_max, max(ls.distance(sg.Point(p)) for p in orig[rk]))
print(f"  anillos rotos                    : {len(malos)}")
for rk, m in malos:
    print(f"      {rk}: {m}")
print(f"  desviacion maxima vs el original : {desv_max:.4f} ft")


def perfiles(dic):
    out = {}
    for (s, pz, tipo, rid), pts in dic.items():
        if tipo != "OUTER":
            continue
        hs = [v for (s2, p2, t2, _), v in dic.items()
              if t2 == "HOLE" and s2 == s and p2 == pz and len(v) >= 3]
        g = sg.Polygon(pts, hs)
        out[(s, pz)] = g if g.is_valid else g.buffer(0)
    return out


pa, pb = perfiles(orig), perfiles(nuevo)
aa, ab = sum(g.area for g in pa.values()), sum(g.area for g in pb.values())
print(f"  area total  {aa:,.1f} -> {ab:,.1f} ft2   ({ab-aa:+.1f})")
peor = max((abs(pb[k].area - pa[k].area), k) for k in pa)
print(f"  mayor cambio de area en un perfil: {peor[0]:.2f} ft2 en {peor[1][0]}")

ks = list(pb)
sol = []
for i in range(len(ks)):
    for j in range(i + 1, len(ks)):
        if not pb[ks[i]].intersects(pb[ks[j]]):
            continue
        a = pb[ks[i]].intersection(pb[ks[j]]).area
        if a > 0.01:
            sol.append((a, ks[i][0], ks[j][0]))
print(f"  solapes > 0.01 ft2               : {len(sol)}")
for a, x, y in sorted(sol, reverse=True)[:6]:
    print(f"      {x} / {y}: {a:.3f} ft2")
print(f"  cobertura perdida                : "
      f"{unary_union(list(pa.values())).difference(unary_union(list(pb.values()))).area:.2f} ft2")

if malos:
    print("\nABORTADO: hay anillos rotos, no se escribe nada.")
    sys.exit(1)

# ------------------------------------------------------------- escritura
rows = []
for (s, pz, tipo, rid), pts in nuevo.items():
    for i, (x, y) in enumerate(pts):
        rows.append([s, pz, tipo, rid, i, f"{x:.4f}", f"{y:.4f}"])
with open(BND, "w", newline="", encoding="ascii") as f:
    w = csv.writer(f)
    w.writerow(hdr)
    w.writerows(rows)
print(f"\nescrito -> {BND}   ({len(rows):,} vertices)")
