# -*- coding: utf-8 -*-
# SISTEMA polyface/3DFACE/MESH (capa) -> LandXML TIN, robusto y reusable.
# Conserva EXACTAMENTE la triangulacion de la malla (sin Delaunay) y rellena los
# huecos internos para que Civil 3D no deje espacios:
#   - Soldadura de vertices por XY (TIN no admite 2 puntos en el mismo XY -> evita
#     el "Point ... ignored - duplicate" que abre huecos).
#   - Descarta caras degeneradas (colapsadas tras soldar) y caras duplicadas.
#   - RELLENA huecos internos reales: triangula cada bucle de borde interno usando
#     SOLO sus vertices (Z interpolada, sin vertices nuevos -> costura perfecta).
#     El resto de la superficie queda identico a la malla.
#   - Reporta aristas no-manifold y huecos antes/despues.
#   (No se escriben vecinos: Civil los rechazaba; el algoritmo estandar conserva
#    todas las caras dadas, asi que con la malla + relleno la superficie es completa.)
# Uso: mesh_to_landxml.py <dxf> <capa> <salida.xml> [nombre_sup] [decimales_XY=4] [fill=1]
import sys, ezdxf
import numpy as np
from scipy.spatial import Delaunay
from ezdxf.render import MeshBuilder
from collections import defaultdict

dxf_path=sys.argv[1]; layer=sys.argv[2]; out_xml=sys.argv[3]
surf_name=sys.argv[4] if len(sys.argv)>4 else "SUPERFICIE"
DEC=int(sys.argv[5]) if len(sys.argv)>5 else 4   # tolerancia soldadura XY = 10^-DEC ft
FILL=int(sys.argv[6]) if len(sys.argv)>6 else 0  # 0=exacto (seguro); 1=rellenar huecos (EXPERIMENTAL: la deteccion de anillos falla con bordes pellizcados/multi-pieza)
SNAP=float(sys.argv[7]) if len(sys.argv)>7 else 0.0  # ft: fusiona vertices casi-coincidentes. OJO: en mallas densas pliega triangulos y crea cruces -> dejar 0. Para solapes usar remocion quirurgica de triangulos (ver mesh_overlap_clean).

doc=ezdxf.readfile(dxf_path); msp=doc.modelspace()

# --- soldadura por XY (un solo Z por XY: el primero visto) ---
vkey={}; verts=[]
def vid(x,y,z):
    k=(round(x,DEC),round(y,DEC)); i=vkey.get(k)
    if i is None: i=len(verts); vkey[k]=i; verts.append((x,y,z))
    return i

raw_faces=[]; n_pf=n_mesh=n_3df=0
def consume(mb):
    mv=list(mb.vertices)
    for fc in mb.faces:
        idx=[vid(*mv[k]) for k in fc]
        if len(idx)>=4: raw_faces.append((idx[0],idx[1],idx[2])); raw_faces.append((idx[0],idx[2],idx[3]))
        elif len(idx)==3: raw_faces.append((idx[0],idx[1],idx[2]))

for e in msp:
    if e.dxf.layer!=layer: continue
    t=e.dxftype()
    if t=="POLYLINE" and e.is_poly_face_mesh: consume(MeshBuilder.from_polyface(e)); n_pf+=1
    elif t=="MESH": consume(MeshBuilder.from_mesh(e)); n_mesh+=1
    elif t=="3DFACE":
        pts=[e.dxf.vtx0,e.dxf.vtx1,e.dxf.vtx2,e.dxf.vtx3]
        idx=[vid(p.x,p.y,p.z) for p in pts]
        if idx[2]==idx[3]: idx=idx[:3]
        if len(idx)>=4: raw_faces.append((idx[0],idx[1],idx[2])); raw_faces.append((idx[0],idx[2],idx[3]))
        elif len(idx)==3: raw_faces.append(tuple(idx))
        n_3df+=1

# --- snap: fusiona vertices casi-coincidentes (juntas de secciones a <SNAP ft) ---
if SNAP>0 and len(verts)>1:
    from scipy.spatial import cKDTree
    pts=np.array([[v[0],v[1]] for v in verts])
    parent=list(range(len(verts)))
    def _find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    for a,b in cKDTree(pts).query_pairs(SNAP):
        ra,rb=_find(a),_find(b)
        if ra!=rb: parent[max(ra,rb)]=min(ra,rb)
    rep={}; nv=[]; o2n={}
    for i in range(len(verts)):
        r=_find(i)
        if r not in rep: rep[r]=len(nv); nv.append(verts[r])
        o2n[i]=rep[r]
    nsnap=len(verts)-len(nv)
    if nsnap: print(f"snap(tol={SNAP}ft): {nsnap} vertices casi-coincidentes fusionados")
    verts=nv
    raw_faces=[(o2n[a],o2n[b],o2n[c]) for (a,b,c) in raw_faces]

# --- limpiar: degeneradas (vertice repetido) y duplicadas ---
faces=[]; seen=set(); degen=0; dup=0
for t in raw_faces:
    if len(set(t))<3: degen+=1; continue
    key=frozenset(t)
    if key in seen: dup+=1; continue
    seen.add(key); faces.append(t)

if not faces:
    print("ERROR: sin caras en esa capa"); sys.exit(2)

def boundary_rings(faces):
    """Devuelve (rings, nonman). ring = lista ordenada de indices de vertice (cerrado)."""
    e2f=defaultdict(list)
    for a,b,c in faces:
        for u,v in [(b,c),(c,a),(a,b)]: e2f[(min(u,v),max(u,v))].append(1)
    nonman=sum(1 for v in e2f.values() if len(v)>2)
    bnd=[e for e,fs in e2f.items() if len(fs)==1]
    adj=defaultdict(list)
    for u,v in bnd: adj[u].append(v); adj[v].append(u)
    used=set(); rings=[]
    for e0 in bnd:
        k0=(min(e0),max(e0))
        if k0 in used: continue
        u0,v0=e0; ring=[u0,v0]; used.add(k0); prev,cur=u0,v0
        while cur!=u0:
            nxt=None
            for cand in adj[cur]:
                k=(min(cur,cand),max(cur,cand))
                if cand!=prev and k not in used: nxt=cand; break
            if nxt is None:
                for cand in adj[cur]:
                    k=(min(cur,cand),max(cur,cand))
                    if k not in used: nxt=cand; break
            if nxt is None: break
            used.add((min(cur,nxt),max(cur,nxt))); ring.append(nxt); prev,cur=cur,nxt
        rings.append(ring)
    return rings, nonman

def pip(x,y,poly):
    """point-in-polygon (ray casting). poly = lista [(x,y),...]"""
    n=len(poly); inside=False; j=n-1
    for i in range(n):
        xi,yi=poly[i]; xj,yj=poly[j]
        if ((yi>y)!=(yj>y)) and (x < (xj-xi)*(y-yi)/(yj-yi+1e-30)+xi): inside=not inside
        j=i
    return inside

def fill_ring(ring, verts):
    """Triangula el interior del anillo usando SOLO sus vertices (Z real)."""
    r=ring[:-1] if (len(ring)>1 and ring[0]==ring[-1]) else ring[:]
    r=list(dict.fromkeys(r))           # quita repetidos preservando orden
    if len(r)<3: return []
    if len(r)==3: return [(r[0],r[1],r[2])]
    pts=np.array([[verts[i][0],verts[i][1]] for i in r])
    poly=[(verts[i][0],verts[i][1]) for i in r]
    try: d=Delaunay(pts)
    except Exception: return []
    out=[]
    for s in d.simplices:
        cx=pts[s,0].mean(); cy=pts[s,1].mean()
        if pip(cx,cy,poly): out.append((r[s[0]],r[s[1]],r[s[2]]))
    return out

# --- deteccion de huecos ---
rings,nonman=boundary_rings(faces)
rings.sort(key=len,reverse=True)
holes=rings[1:] if rings else []      # el mayor = perimetro exterior
print(f"entidades: polyface={n_pf} mesh={n_mesh} 3dface={n_3df}")
print(f"vertices soldados(XY,dec={DEC})={len(verts)}  caras malla={len(faces)}  (degeneradas={degen} duplicadas={dup})")
print(f"no-manifold(>2)={nonman}  perimetros+huecos={len(rings)}  huecos internos={len(holes)}")
nfill=0
if FILL and holes:
    for h in holes:
        xs=[verts[i][0] for i in h]; ys=[verts[i][1] for i in h]
        new=fill_ring(h,verts)
        faces.extend(new); nfill+=len(new)
        print(f"   HUECO {len(set(h))} nodos  X {min(xs):.1f}..{max(xs):.1f} Y {min(ys):.1f}..{max(ys):.1f}  -> +{len(new)} caras de relleno")
    # verificar que cerraron
    rings2,_=boundary_rings(faces); rings2.sort(key=len,reverse=True)
    print(f"   tras relleno: huecos internos restantes={max(0,len(rings2)-1)}  caras totales={len(faces)} (+{nfill})")
elif holes:
    for h in holes:
        xs=[verts[i][0] for i in h]; ys=[verts[i][1] for i in h]
        print(f"   HUECO {len(set(h))} nodos  X {min(xs):.1f}..{max(xs):.1f} Y {min(ys):.1f}..{max(ys):.1f} (sin rellenar)")

# --- escribir LandXML (caras simples; el algoritmo estandar las conserva todas) ---
with open(out_xml,"w",encoding="utf-8") as o:
    o.write('<?xml version="1.0"?>\n<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2" date="2026-06-30" time="12:00:00">\n')
    o.write(' <Units><Imperial areaUnit="squareFoot" linearUnit="USSurveyFoot" volumeUnit="cubicFeet" temperatureUnit="fahrenheit" pressureUnit="inHG" diameterUnit="inch" angularUnit="decimal degrees" directionUnit="decimal degrees"/></Units>\n')
    o.write(f' <Surfaces>\n  <Surface name="{surf_name}">\n   <Definition surfType="TIN">\n    <Pnts>\n')
    for i,v in enumerate(verts,1):
        o.write(f'     <P id="{i}">{v[1]:.4f} {v[0]:.4f} {v[2]:.4f}</P>\n')  # Northing Easting Elev
    o.write('    </Pnts>\n    <Faces>\n')
    for a,b,c in faces:
        o.write(f'     <F>{a+1} {b+1} {c+1}</F>\n')
    o.write('    </Faces>\n   </Definition>\n  </Surface>\n </Surfaces>\n</LandXML>\n')
print(f"OK -> {out_xml}")
