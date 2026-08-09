# -*- coding: utf-8 -*-
# Genera un LandXML por cada elemento del DXF de mallas polyface, quedandose con
# la CARA SUPERIOR (misma regla que extraer_cara_superior.py) y RESPETANDO la
# triangulacion tal cual viene.
#
# QUE SIGNIFICA "RESPETAR LA TRIANGULACION": no se re-triangula, no se sueldan
# vertices por proximidad, no se rellenan huecos ni se recorta nada. Cada cara que
# sobrevive al filtro top se escribe con los mismos tres vertices que tenia en el
# DXF. Lo unico que se hace es renumerar los vertices para quedarse solo con los
# que alguna cara usa (los del fondo y las paredes ya no hacen falta) -- eso
# cambia los indices, no la geometria.
#
# Los cuadrilateros del DXF si se parten en dos triangulos, porque LandXML solo
# admite caras de 3 vertices. Es una conversion obligada por el formato, y el
# reparto se hace siempre por la misma diagonal (0-1-2 y 0-2-3).
#
# Uso:  python xml_desde_cara_superior.py <entrada.dxf> <dir_salida> [decimales] [prefijo]
import os, sys, time
from collections import defaultdict
import numpy as np
import ezdxf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_utils import solid_faces, write_landxml

ENT = sys.argv[1]
DIR = sys.argv[2]
DEC = int(sys.argv[3]) if len(sys.argv) > 3 else 3
PREFIJO = sys.argv[4] if len(sys.argv) > 4 else "Top Mesh"


class Malla:
    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces


def leer_polyface(e):
    """(vertices, caras) de una POLYLINE polyface.
    OJO CON LOS FLAGS: los VERTICES llevan 192 (64|128) y los registros de CARA
    llevan 128 a secas. Filtrar por "flags & 128" no distingue nada, porque los
    vertices tambien lo cumplen: hay que mirar el bit 64."""
    vs = []
    caras = []
    for v in e.vertices:
        f = v.dxf.flags
        if f & 64:
            L = v.dxf.location
            vs.append((L.x, L.y, L.z))
        elif f & 128:
            idx = []
            for a in ("vtx0", "vtx1", "vtx2", "vtx3"):
                if v.dxf.hasattr(a):
                    n = v.dxf.get(a)
                    if n:
                        idx.append(abs(n) - 1)     # 1-based y con signo por la
            idx = [i for k, i in enumerate(idx)    # visibilidad de la arista
                   if i not in idx[:k]]
            if len(idx) == 3:
                caras.append(tuple(idx))
            elif len(idx) == 4:
                caras.append((idx[0], idx[1], idx[2]))
                caras.append((idx[0], idx[2], idx[3]))
    return vs, caras


def area_xy(V, faces):
    if not faces:
        return 0.0
    T = np.asarray(V)[np.array(faces, dtype=np.int64)]
    return float(np.abs((T[:, 1, 0]-T[:, 0, 0])*(T[:, 2, 1]-T[:, 0, 1])
                        - (T[:, 2, 0]-T[:, 0, 0])*(T[:, 1, 1]-T[:, 0, 1])).sum()/2)


t0 = time.time()
os.makedirs(DIR, exist_ok=True)
doc = ezdxf.readfile(ENT)
mallas = [e for e in doc.modelspace()
          if e.dxftype() == "POLYLINE" and e.is_poly_face_mesh]
print(f"{len(mallas)} mallas polyface en {os.path.basename(ENT)}\n")

print(f"{'#':>3s} {'nombre':16s} {'caras':>8s} {'puntos':>8s} {'area ft2':>13s} "
      f"{'Z min':>8s} {'Z max':>8s} {'degen':>6s}")
print("-" * 78)
todas = []
tot_f = tot_p = tot_d = 0
tot_a = 0.0
for i, e in enumerate(mallas, 1):
    vs, caras = leer_polyface(e)
    mv, top, es_solido = solid_faces(Malla(vs, caras), DEC, which="top")

    # descartar SOLO los triangulos de area nula: no aportan superficie y hacen
    # fallar la importacion en Civil 3D. Cualquier otro se conserva intacto.
    V = np.asarray(mv)
    buenas = []
    degen = 0
    for f in top:
        a, b, c = V[list(f)]
        if abs((b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])) / 2 < 1e-9:
            degen += 1
            continue
        buenas.append(f)

    # quedarse solo con los vertices que alguna cara usa (fuera fondo y paredes)
    usados = sorted({v for f in buenas for v in f})
    remap = {v: k for k, v in enumerate(usados)}
    verts = [tuple(mv[v]) for v in usados]
    faces = [(remap[a], remap[b], remap[c]) for a, b, c in buenas]

    nombre = f"{PREFIJO} {i:02d}"
    a = area_xy(verts, faces)
    zs = [p[2] for p in verts]
    tot_f += len(faces); tot_p += len(verts); tot_a += a; tot_d += degen
    print(f"{i:3d} {nombre:16s} {len(faces):8,d} {len(verts):8,d} {a:13,.1f} "
          f"{min(zs):8.3f} {max(zs):8.3f} {degen:6d}")
    write_landxml(os.path.join(DIR, f"{nombre}.xml"), [(nombre, verts, faces)])
    todas.append((nombre, verts, faces))

print("-" * 78)
print(f"{'TOTAL':>20s} {tot_f:8,d} {tot_p:8,d} {tot_a:13,.1f} "
      f"{'':8s} {'':8s} {tot_d:6d}")

comb = os.path.join(DIR, f"_TODAS_{PREFIJO.replace(' ', '_')}.xml")
write_landxml(comb, todas)
print(f"\nindividuales -> {DIR}  ({len(todas)} archivos)")
print(f"combinado    -> {comb}")
print(f"tiempo: {time.time()-t0:.0f}s")
