# -*- coding: utf-8 -*-
# SISTEMA polyface/MESH (capa) -> LandXML con MULTIPLES <Surface>, una por CADA
# ENTIDAD DXF separada (no por capa ni por conectividad). Uso: cuando varias
# superficies comparten la misma capa mas no pueden fusionarse (se tocan o se
# traslapan entre si en planta, p.ej. capas de un paquete estructural de
# pavimento), pero cada una es un objeto polyface/MESH propio.
#
# Cada entidad se trata de forma AISLADA: soldadura de vertices por XY, limpieza
# de caras degeneradas/duplicadas y QA de cruces (solapes internos) se hacen
# SOLO dentro de esa entidad -- el traslape EN PLANTA entre dos superficies
# distintas es valido (son objetos TIN independientes); el problema real solo
# existe si el solape ocurre DENTRO de una misma malla.
#
# Salida: un solo LandXML con <Surface name="...">, una por entidad. Civil 3D
# (Insert -> LandXML) lista todas y permite elegir cuales importar.
#
# Uso: mesh_multi_to_landxml.py <dxf> <capa> <salida.xml> <nombres_o_prefijo> [orden=elev] [decimales_XY=4] [nombre_subrasante]
#   nombres_o_prefijo: si contiene comas, lista explicita de nombres (debe calzar
#     con el N de entidades), asignados segun <orden>. Si no tiene comas, se usa
#     como PREFIJO y se numera en el orden de aparicion en el DXF (prefijo_1, _2...).
#   orden: "elev" (default) = ordena entidades de MAYOR a MENOR Z (arriba->abajo,
#     util para capas de pavimento apiladas) antes de asignar nombres explicitos.
#     "dxf" = usa el orden de aparicion en el archivo, sin reordenar.
#   nombre_subrasante: si se da, ADEMAS de las caras superiores de cada entidad,
#     extrae la cara INFERIOR de la entidad mas profunda (menor Z) como una
#     superficie adicional con ese nombre -- el "corte de terreno" que cierra
#     por abajo un paquete de capas apiladas (top de una = bottom de la siguiente).
import sys, ezdxf
from ezdxf.render import MeshBuilder
from collections import defaultdict

dxf_path=sys.argv[1]; layer=sys.argv[2]; out_xml=sys.argv[3]
names_arg=sys.argv[4] if len(sys.argv)>4 else "SUPERFICIE"
order=sys.argv[5] if len(sys.argv)>5 else "elev"
DEC=int(sys.argv[6]) if len(sys.argv)>6 else 4
subrasante_name=sys.argv[7] if len(sys.argv)>7 else None

explicit_names = [n.strip() for n in names_arg.split(",")] if "," in names_arg else None
prefix = names_arg if explicit_names is None else None

doc=ezdxf.readfile(dxf_path); msp=doc.modelspace()

def solid_faces(mb, which="top", tol=1e-6):
    """Si la malla es un SOLIDO (>=1 XY con mas de 1 valor de Z -> tiene cara
    superior + inferior + paredes), se queda SOLO con las caras cuyos 3 vertices
    son el punto de MAYOR Z (which='top') o MENOR Z (which='bottom') en su columna
    XY. Si no es solido (ya es una superficie 2.5D), devuelve las caras tal cual.
    Devuelve (mv, faces_idx, era_solido)."""
    mv = list(mb.vertices)
    xy_extz = {}
    for v in mv:
        k = (round(v[0], DEC), round(v[1], DEC))
        if k not in xy_extz: xy_extz[k] = [v[2], v[2]]
        else:
            xy_extz[k][0] = min(xy_extz[k][0], v[2])
            xy_extz[k][1] = max(xy_extz[k][1], v[2])
    xy_zset = defaultdict(set)
    for v in mv:
        xy_zset[(round(v[0], DEC), round(v[1], DEC))].add(round(v[2], 3))
    n_multi = sum(1 for zs in xy_zset.values() if len(zs) > 1)
    es_solido = n_multi > 0 and n_multi >= 0.5 * len(xy_zset)  # mayoria de XY con 2 Z -> solido

    target_idx = 1 if which == "top" else 0
    def is_target(vi):
        v = mv[vi]
        k = (round(v[0], DEC), round(v[1], DEC))
        return abs(v[2] - xy_extz[k][target_idx]) < tol

    if es_solido:
        faces = [fc for fc in mb.faces if all(is_target(vi) for vi in fc)]
    else:
        faces = list(mb.faces)
    return mv, faces, es_solido

def weld_and_clean(mv, raw_face_idx):
    """Suelda vertices por XY y limpia caras degeneradas/duplicadas DENTRO de una sola entidad."""
    vkey={}; verts=[]
    def vid(x,y,z):
        k=(round(x,DEC),round(y,DEC)); i=vkey.get(k)
        if i is None: i=len(verts); vkey[k]=i; verts.append((x,y,z))
        return i
    raw=[]
    for fc in raw_face_idx:
        idx=[vid(*mv[k]) for k in fc]
        if len(idx)>=4: raw.append((idx[0],idx[1],idx[2])); raw.append((idx[0],idx[2],idx[3]))
        elif len(idx)==3: raw.append(tuple(idx))
    faces=[]; seen=set(); degen=0; dup=0
    for t in raw:
        if len(set(t))<3: degen+=1; continue
        key=frozenset(t)
        if key in seen: dup+=1; continue
        seen.add(key); faces.append(t)
    return verts, faces, degen, dup

def boundary_holes(faces):
    e2f=defaultdict(int)
    for a,b,c in faces:
        for u,v in [(b,c),(c,a),(a,b)]: e2f[(min(u,v),max(u,v))]+=1
    nonman=sum(1 for n in e2f.values() if n>2)
    bnd=[e for e,n in e2f.items() if n==1]
    adj=defaultdict(list)
    for u,v in bnd: adj[u].append(v); adj[v].append(u)
    seen=set(); rings=[]
    for s in list(adj):
        if s in seen: continue
        comp=[]; st=[s]
        while st:
            x=st.pop()
            if x in seen: continue
            seen.add(x); comp.append(x)
            for y in adj[x]:
                if y not in seen: st.append(y)
        rings.append(comp)
    rings.sort(key=len, reverse=True)
    return (len(rings)-1 if rings else 0), nonman

def crossing_count(verts, faces):
    """QA: pares de aristas que se cruzan en planta (solape interno de ESTA entidad)."""
    def o(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def seg_cross(p1,p2,p3,p4):
        if len({p1,p2,p3,p4})<4: return False
        a,b,c,d=verts[p1],verts[p2],verts[p3],verts[p4]
        return (o(a,b,c)>0)!=(o(a,b,d)>0) and (o(c,d,a)>0)!=(o(c,d,b)>0)
    E=set()
    for t in faces:
        for u,v in [(t[0],t[1]),(t[1],t[2]),(t[2],t[0])]: E.add((min(u,v),max(u,v)))
    E=list(E)
    if len(E) > 6000:
        return None
    cell=50.0; grid=defaultdict(list)
    for ei,e in enumerate(E):
        a,b=verts[e[0]],verts[e[1]]
        for cx in range(int(min(a[0],b[0])//cell),int(max(a[0],b[0])//cell)+1):
            for cy in range(int(min(a[1],b[1])//cell),int(max(a[1],b[1])//cell)+1):
                grid[(cx,cy)].append(ei)
    nc=0; seen=set()
    for lst in grid.values():
        for i in range(len(lst)):
            for j in range(i+1,len(lst)):
                a,b=lst[i],lst[j]
                if (a,b) in seen: continue
                seen.add((a,b))
                if seg_cross(E[a][0],E[a][1],E[b][0],E[b][1]): nc+=1
    return nc

# --- recolectar entidades EN ORDEN DE APARICION en el DXF ---
raw_entities = []
for e in msp:
    if e.dxf.layer != layer: continue
    t = e.dxftype()
    if t == "POLYLINE" and e.is_poly_face_mesh:
        raw_entities.append(("POLYLINE", MeshBuilder.from_polyface(e)))
    elif t == "MESH":
        raw_entities.append(("MESH", MeshBuilder.from_mesh(e)))

print(f"entidades encontradas en capa '{layer}': {len(raw_entities)}")
if not raw_entities:
    print("ERROR: no hay entidades polyface/MESH en esa capa"); sys.exit(2)

if explicit_names and len(explicit_names) != len(raw_entities):
    print(f"ERROR: se dieron {len(explicit_names)} nombres pero hay {len(raw_entities)} entidades")
    sys.exit(3)

# --- procesar cada entidad (deteccion de solido -> top face, soldadura + limpieza aisladas) ---
processed = []
for etype, mb in raw_entities:
    mv, top_face_idx, es_solido = solid_faces(mb, "top")
    verts, faces, degen, dup = weld_and_clean(mv, top_face_idx)
    max_z = max(v[2] for v in verts) if verts else None
    min_z = min(v[2] for v in verts) if verts else None
    processed.append({"etype": etype, "mb": mb, "verts": verts, "faces": faces, "degen": degen,
                       "dup": dup, "max_z": max_z, "min_z": min_z, "es_solido": es_solido,
                       "caras_originales": len(mb.faces), "caras_top": len(top_face_idx)})

# --- orden para asignar nombres explicitos ---
if order == "elev":
    idx_order = sorted(range(len(processed)), key=lambda i: -processed[i]["max_z"])
else:
    idx_order = list(range(len(processed)))

# asignar nombre a cada entidad (por su indice original)
name_by_idx = {}
if explicit_names:
    for rank, orig_idx in enumerate(idx_order):
        name_by_idx[orig_idx] = explicit_names[rank]
else:
    for rank, orig_idx in enumerate(idx_order):
        name_by_idx[orig_idx] = f"{prefix}_{rank+1}"

surfaces = []
for i, p in enumerate(processed):
    name = name_by_idx[i]
    verts, faces = p["verts"], p["faces"]
    if not faces:
        print(f"  [{i+1}] {name}: SIN CARAS VALIDAS -- omitida"); continue
    n_holes, nonman = boundary_holes(faces)
    nc = crossing_count(verts, faces)
    nc_txt = str(nc) if nc is not None else "omitido (malla grande)"
    xs=[v[0] for v in verts]; ys=[v[1] for v in verts]
    solido_txt = f"SOLIDO detectado -> se uso solo cara superior ({p['caras_top']}/{p['caras_originales']} caras)" if p["es_solido"] else "superficie simple (no era solido)"
    print(f"  [{i+1}] {name}: {p['etype']}  [{solido_txt}]")
    print(f"       vertices={len(verts)} caras={len(faces)} "
          f"(degen={p['degen']} dup={p['dup']})  huecos_internos={n_holes}  no-manifold={nonman}  "
          f"cruces_internos={nc_txt}")
    print(f"       extent X {min(xs):.1f}..{max(xs):.1f}  Y {min(ys):.1f}..{max(ys):.1f}  "
          f"Z {p['min_z']:.3f}..{p['max_z']:.3f}")
    if nc:
        print(f"       *** ATENCION: {nc} cruce(s) interno(s) -- triangulos solapados en planta ***")
    surfaces.append((name, verts, faces))

# --- subrasante: cara INFERIOR de la entidad mas profunda (menor min_z) ---
if subrasante_name:
    deepest_i = min(range(len(processed)), key=lambda i: processed[i]["min_z"])
    p = processed[deepest_i]
    mv, bot_face_idx, es_solido = solid_faces(p["mb"], "bottom")
    verts, faces, degen, dup = weld_and_clean(mv, bot_face_idx)
    if faces:
        n_holes, nonman = boundary_holes(faces)
        nc = crossing_count(verts, faces)
        nc_txt = str(nc) if nc is not None else "omitido (malla grande)"
        xs=[v[0] for v in verts]; ys=[v[1] for v in verts]
        zs=[v[2] for v in verts]
        print(f"  [Subrasante] {subrasante_name}: cara INFERIOR de '{name_by_idx[deepest_i]}' "
              f"({len(bot_face_idx)}/{len(p['mb'].faces)} caras)")
        print(f"       vertices={len(verts)} caras={len(faces)} (degen={degen} dup={dup}) "
              f"huecos_internos={n_holes}  no-manifold={nonman}  cruces_internos={nc_txt}")
        print(f"       extent X {min(xs):.1f}..{max(xs):.1f}  Y {min(ys):.1f}..{max(ys):.1f}  "
              f"Z {min(zs):.3f}..{max(zs):.3f}")
        if nc:
            print(f"       *** ATENCION: {nc} cruce(s) interno(s) ***")
        surfaces.append((subrasante_name, verts, faces))
    else:
        print(f"  [Subrasante] SIN CARAS VALIDAS -- omitida")

# --- escribir UN LandXML con multiples <Surface> ---
with open(out_xml, "w", encoding="utf-8") as o:
    o.write('<?xml version="1.0"?>\n<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2" date="2026-07-06" time="12:00:00">\n')
    o.write(' <Units><Imperial areaUnit="squareFoot" linearUnit="USSurveyFoot" volumeUnit="cubicFeet" temperatureUnit="fahrenheit" pressureUnit="inHG" diameterUnit="inch" angularUnit="decimal degrees" directionUnit="decimal degrees"/></Units>\n')
    o.write(' <Surfaces>\n')
    for name, verts, faces in surfaces:
        o.write(f'  <Surface name="{name}">\n   <Definition surfType="TIN">\n    <Pnts>\n')
        for i, v in enumerate(verts, 1):
            o.write(f'     <P id="{i}">{v[1]:.4f} {v[0]:.4f} {v[2]:.4f}</P>\n')  # Northing Easting Elev
        o.write('    </Pnts>\n    <Faces>\n')
        for a, b, c in faces:
            o.write(f'     <F>{a+1} {b+1} {c+1}</F>\n')
        o.write('    </Faces>\n   </Definition>\n  </Surface>\n')
    o.write(' </Surfaces>\n</LandXML>\n')

print(f"\nOK -> {out_xml}  ({len(surfaces)} superficies escritas)")
