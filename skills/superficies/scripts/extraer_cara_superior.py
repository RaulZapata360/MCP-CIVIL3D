# -*- coding: utf-8 -*-
# De un DXF con mallas polyface que representan SOLIDOS (cada elemento trae cara
# superior, paredes laterales y cara inferior), se queda solo con la CARA
# SUPERIOR de cada elemento y la escribe en otro DXF.
#
# COMO SE DECIDE QUE ES "SUPERIOR": por columna XY. Se agrupan los vertices que
# comparten X e Y (redondeados a DEC decimales) y una cara se conserva solo si sus
# TRES vertices son el de mayor Z de su columna. Asi caen a la vez las paredes
# (que unen un Z alto con uno bajo) y el fondo. Es la misma regla que ya usa
# mesh_utils.solid_faces, aqui solo se le da de comer las polyface de ezdxf.
#
# Uso:  python extraer_cara_superior.py <entrada.dxf> <salida.dxf> [decimales]
import os, sys, time
from collections import defaultdict
import numpy as np
import ezdxf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_utils import solid_faces, solid_thickness_stats

ENT = sys.argv[1]
SAL = sys.argv[2]
DEC = int(sys.argv[3]) if len(sys.argv) > 3 else 3


class Malla:
    """Adaptador minimo para poder pasarle una polyface de ezdxf a solid_faces."""
    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces


def leer_polyface(e):
    """(vertices, caras) de una POLYLINE polyface. Los cuadrilateros se parten en
    dos triangulos; los indices de cara en DXF son 1-based y el signo marca si la
    arista es visible, asi que hay que tomar el valor absoluto."""
    # OJO CON LOS FLAGS: en una polyface los VERTICES llevan 192 (64|128) y los
    # registros de CARA llevan 128 a secas. Comprobar "f & 128" para distinguirlos
    # no sirve, porque los vertices tambien lo cumplen: hay que mirar el bit 64.
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
                        idx.append(abs(n) - 1)
            idx = [i for k, i in enumerate(idx) if i not in idx[:k]]
            if len(idx) == 3:
                caras.append(tuple(idx))
            elif len(idx) == 4:
                caras.append((idx[0], idx[1], idx[2]))
                caras.append((idx[0], idx[2], idx[3]))
    return vs, caras


def area_xy(vs, faces):
    if not faces:
        return 0.0
    V = np.array(vs)
    T = V[np.array(faces, dtype=np.int64)]
    return float(np.abs((T[:, 1, 0]-T[:, 0, 0])*(T[:, 2, 1]-T[:, 0, 1])
                        - (T[:, 2, 0]-T[:, 0, 0])*(T[:, 1, 1]-T[:, 0, 1])).sum()/2)


t0 = time.time()
doc = ezdxf.readfile(ENT)
msp = doc.modelspace()
mallas = [e for e in msp if e.dxftype() == "POLYLINE" and e.is_poly_face_mesh]
print(f"{len(mallas)} mallas polyface en {os.path.basename(ENT)}\n")

out = ezdxf.new("R2010", setup=True)
omsp = out.modelspace()

print(f"{'#':>3s} {'capa':16s} {'solido':7s} {'caras':>8s} {'top':>8s} "
      f"{'%':>6s} {'area top ft2':>13s} {'espesor':>16s}")
print("-" * 88)
tot_f = tot_t = 0
tot_area = 0.0
no_solidos = []
for i, e in enumerate(mallas, 1):
    vs, caras = leer_polyface(e)
    mb = Malla(vs, caras)
    mv, top, es_solido = solid_faces(mb, DEC, which="top")
    esp, n_multi, n_tot = solid_thickness_stats(mb, DEC)
    tot_f += len(caras); tot_t += len(top)
    a = area_xy(mv, top)
    tot_area += a
    if not es_solido:
        no_solidos.append(i)
    et = (f"{esp[0]:.2f}-{esp[1]:.2f} m{esp[2]:.2f}" if esp else "-")
    print(f"{i:3d} {e.dxf.layer[:16]:16s} {'si' if es_solido else 'NO':7s} "
          f"{len(caras):8,d} {len(top):8,d} {100*len(top)/max(1,len(caras)):5.1f}% "
          f"{a:13,.1f} {et:>16s}")

    if not top:
        continue
    usados = sorted({v for f in top for v in f})
    remap = {v: k for k, v in enumerate(usados)}
    pf = omsp.add_polyface(dxfattribs={"layer": e.dxf.layer})
    pf.append_faces([[mv[a_] for a_ in (f[0], f[1], f[2])] for f in top])
    pf.optimize()

print("-" * 88)
print(f"{'TOTAL':>20s} {'':7s} {tot_f:8,d} {tot_t:8,d} "
      f"{100*tot_t/max(1,tot_f):5.1f}% {tot_area:13,.1f}")
if no_solidos:
    print(f"\nAVISO: las mallas {no_solidos} no se detectaron como solidos, "
          f"se conservan enteras. Revisar si de verdad ya eran superficies.")

out.saveas(SAL)
print(f"\nDXF -> {SAL}  ({os.path.getsize(SAL)/1e6:.1f} MB)")
print(f"tiempo: {time.time()-t0:.0f}s")
