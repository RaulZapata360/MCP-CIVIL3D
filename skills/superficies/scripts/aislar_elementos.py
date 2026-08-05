# -*- coding: utf-8 -*-
# Saca a un DXF aparte los elementos (mallas polyface) que se le indiquen por su
# numero de orden, con el SOLIDO COMPLETO -- cara superior, paredes y fondo --
# porque lo que se suele querer inspeccionar en estos casos es el espesor, y eso
# no se ve si solo se lleva la cara de arriba.
#
# Cada elemento va a su propia capa (ELEM_nn) para poder aislarlos entre si, y
# ademas se marca en capas separadas su cara superior y su cara inferior, que es
# lo que permite ver de un vistazo donde el espesor deja de ser constante.
#
# Uso:  python aislar_elementos.py <entrada.dxf> <salida.dxf> <n1,n2,...> [dec]
import os, sys
from collections import defaultdict
import numpy as np
import ezdxf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh_utils import solid_faces, polyface_to_mesh, MallaSimple as Malla

ENT = sys.argv[1]
SAL = sys.argv[2]
QUIERO = [int(x) for x in sys.argv[3].split(",")]
DEC = int(sys.argv[4]) if len(sys.argv) > 4 else 3

doc = ezdxf.readfile(ENT)
mallas = [e for e in doc.modelspace()
          if e.dxftype() == "POLYLINE" and e.is_poly_face_mesh]
print(f"{len(mallas)} mallas en el origen; se aislan {QUIERO}\n")

out = ezdxf.new("R2010", setup=True)
omsp = out.modelspace()

for n in QUIERO:
    if not (1 <= n <= len(mallas)):
        print(f"AVISO: no existe el elemento {n}")
        continue
    e = mallas[n - 1]
    vs, caras = polyface_to_mesh(e)
    V = np.array(vs)

    # espesor por columna XY
    col = defaultdict(list)
    for x, y, z in vs:
        col[(round(x, DEC), round(y, DEC))].append(z)
    esp = np.array([max(z) - min(z) for z in col.values() if len(z) >= 2])

    mv, top, _ = solid_faces(Malla(vs, caras), DEC, which="top")
    _, bot, _ = solid_faces(Malla(vs, caras), DEC, which="bottom")
    lat = [f for f in caras if f not in set(top) and f not in set(bot)]

    print(f"ELEMENTO {n}")
    print(f"  caras: {len(caras):,} total = {len(top):,} arriba + {len(bot):,} "
          f"abajo + {len(lat):,} laterales")
    print(f"  columnas XY: {len(col):,}   con 2 o mas Z: {len(esp):,}")
    if len(esp):
        print(f"  espesor: min {esp.min():.3f}  max {esp.max():.3f}  "
              f"media {esp.mean():.3f}  desv {esp.std():.4f} ft")
        vals, cuenta = np.unique(np.round(esp, 3), return_counts=True)
        print(f"  valores distintos de espesor: {len(vals)}")
        for v, c in sorted(zip(vals, cuenta), key=lambda t: -t[1])[:8]:
            print(f"     {v:6.3f} ft  en {c:5,d} columnas  ({100*c/len(esp):5.1f}%)")
    print(f"  Z: {V[:,2].min():.3f} a {V[:,2].max():.3f} ft")
    b = (V[:, 0].min(), V[:, 1].min(), V[:, 0].max(), V[:, 1].max())
    print(f"  extension: {b[2]-b[0]:,.1f} x {b[3]-b[1]:,.1f} ft  "
          f"en ({b[0]:,.1f}, {b[1]:,.1f})")

    for etiqueta, sel, color in ((f"ELEM_{n:02d}_COMPLETO", caras, 8),
                                 (f"ELEM_{n:02d}_SUPERIOR", top, 3),
                                 (f"ELEM_{n:02d}_INFERIOR", bot, 1)):
        if not sel:
            continue
        if etiqueta not in out.layers:
            out.layers.add(etiqueta, color=color)
        pf = omsp.add_polyface(dxfattribs={"layer": etiqueta})
        pf.append_faces([[mv[i] for i in f] for f in sel])
        pf.optimize()

    # las columnas cuyo espesor se sale del valor dominante, marcadas con un
    # circulo para poder ir a verlas
    if len(esp) and len(np.unique(np.round(esp, 3))) > 1:
        vals, cuenta = np.unique(np.round(esp, 3), return_counts=True)
        dominante = vals[np.argmax(cuenta)]
        capa = f"ELEM_{n:02d}_ESPESOR_RARO"
        out.layers.add(capa, color=6)
        raros = 0
        for (x, y), zs in col.items():
            if len(zs) >= 2 and abs((max(zs) - min(zs)) - dominante) > 0.005:
                omsp.add_circle((x, y, max(zs)), radius=1.0,
                                dxfattribs={"layer": capa})
                raros += 1
        print(f"  columnas con espesor distinto de {dominante:.3f}: {raros:,} "
              f"-> marcadas con circulos en la capa {capa}")
    print()

out.saveas(SAL)
print(f"DXF -> {SAL}  ({os.path.getsize(SAL)/1e6:.2f} MB)")
print("coordenadas reales VA83-SF; insertar en 0,0,0 escala 1")
