# -*- coding: utf-8 -*-
# polyface/3DFACE/MESH (capa) -> DXF con BREAKLINES (todas las aristas de la malla)
# + CONTORNO exterior, para construir una superficie Civil 3D que:
#   - respeta cada arista de la malla (triangulacion identica donde hay malla),
#   - rellena huecos internos (gore) por Delaunay,
#   - se recorta al contorno exterior.
# Salida: DXF con capas CALZADA_BRK (lineas 3D = breaklines) y CALZADA_BND (polilineas
# cerradas de borde). Vertices soldados por XY. Uso:
#   mesh_to_breaklines_dxf.py <dxf_in> <capa> <dxf_out> [dec=4]
import sys, ezdxf
from ezdxf.render import MeshBuilder
from collections import defaultdict

din=sys.argv[1]; layer=sys.argv[2]; dout=sys.argv[3]
DEC=int(sys.argv[4]) if len(sys.argv)>4 else 4
EMIT_BND=int(sys.argv[5]) if len(sys.argv)>5 else 0  # 0=solo breaklines (usar tu contorno); 1=tambien bucles de borde

src=ezdxf.readfile(din); msp=src.modelspace()
vkey={}; verts=[]
def vid(x,y,z):
    k=(round(x,DEC),round(y,DEC)); i=vkey.get(k)
    if i is None: i=len(verts); vkey[k]=i; verts.append((x,y,z))
    return i
faces=[]
for e in msp:
    if e.dxftype()=="POLYLINE" and e.is_poly_face_mesh:
        mb=MeshBuilder.from_polyface(e); mv=mb.vertices
        for fc in mb.faces:
            gi=[vid(*mv[k]) for k in fc[:3]]
            if len(set(gi))==3: faces.append(tuple(gi))
    elif e.dxftype()=="MESH":
        mb=MeshBuilder.from_mesh(e); mv=mb.vertices
        for fc in mb.faces:
            gi=[vid(*mv[k]) for k in fc[:3]]
            if len(set(gi))==3: faces.append(tuple(gi))

# aristas unicas y de borde
cnt=defaultdict(int)
for a,b,c in faces:
    for u,v in [(a,b),(b,c),(c,a)]: cnt[(min(u,v),max(u,v))]+=1
edges=list(cnt.keys())
bnd=[e for e,n in cnt.items() if n==1]

# Circuito euleriano (Hierholzer) por componente de aristas de borde -> bucles cerrados
adj=defaultdict(list)
for (u,v) in bnd: adj[u].append(v); adj[v].append(u)
used=set(); loops=[]
def edge_key(u,v): return (min(u,v),max(u,v))
for seed in list(adj):
    if all(edge_key(seed,w) in used for w in adj[seed]): continue
    stack=[seed]; path=[]
    while stack:
        u=stack[-1]
        nxt=None
        for w in adj[u]:
            if edge_key(u,w) not in used: nxt=w; break
        if nxt is None: path.append(stack.pop())
        else: used.add(edge_key(u,nxt)); stack.append(nxt)
    if len(path)>=4: loops.append(path)
# ordenar por area (shoelace) para identificar el exterior
def area(loop):
    s=0.0
    for i in range(len(loop)-1):
        x1,y1=verts[loop[i]][0],verts[loop[i]][1]; x2,y2=verts[loop[i+1]][0],verts[loop[i+1]][1]
        s+=x1*y2-x2*y1
    return abs(s)/2
loops.sort(key=area,reverse=True)

doc=ezdxf.new("R2018"); doc.header["$INSUNITS"]=0; m=doc.modelspace()
doc.layers.add("CALZADA_BRK", color=3)
# breaklines: cada arista como linea 3D
for (u,v) in edges:
    m.add_line(verts[u], verts[v], dxfattribs={"layer":"CALZADA_BRK"})
# contornos (opcional, poco fiable con bordes pellizcados): bucles de borde
if EMIT_BND:
    doc.layers.add("CALZADA_BND", color=1)
    for loop in loops:
        pl=m.add_polyline3d([verts[i] for i in loop], dxfattribs={"layer":"CALZADA_BND"}); pl.close(True)
doc.saveas(dout)
print(f"vertices={len(verts)} caras={len(faces)} aristas(breaklines)={len(edges)} bordes={len(bnd)}")
print(f"bucles de contorno={len(loops)} (areas ft2): " + ", ".join(f"{area(l):.0f}" for l in loops[:6]))
print(f"-> EXTERIOR = el de mayor area ({area(loops[0]):.0f} ft2) | el resto son huecos internos")
print(f"OK -> {dout}")
