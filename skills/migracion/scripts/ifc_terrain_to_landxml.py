# -*- coding: utf-8 -*-
# Extrae la malla de terreno (capa de triangulacion, p.ej. "Terrain_Triangle") de un IFC
# y la escribe como LandXML TIN conservando EXACTAMENTE las caras (sin retriangular).
# Escala "georef": metros SI -> 3.2808333333 ; pie 0.3048 -> 1/0.3048. Formato igual al
# Superficie_Proyecto_NI.xml que ya funciona: <P id>Y X Z</P>, <F>i j k</F> 1-based.
import sys, multiprocessing
import ifcopenshell, ifcopenshell.geom
import ifcopenshell.util.unit as U

ifc_path = sys.argv[1]
out_xml  = sys.argv[2]
layer_match = sys.argv[3] if len(sys.argv) > 3 else "Terrain_Triangle"
surf_name   = sys.argv[4] if len(sys.argv) > 4 else "Superficie_Proyecto_SI"

f = ifcopenshell.open(ifc_path)
us = U.calculate_unit_scale(f)
scale = (1.0/us) if abs(us-1.0) > 1e-9 else 3.2808333333
print(f"schema={f.schema} unit_scale={us} -> escala x{scale}  capa~='{layer_match}'")

# capa por id de item (presentation layers)
lbi = {}
for pla in f.by_type("IfcPresentationLayerAssignment"):
    for it in (pla.AssignedItems or []):
        try: lbi[it.id()] = (pla.Name or "").split("::")[0]
        except Exception: pass
def resolve(e):
    rep = getattr(e, "Representation", None)
    if rep:
        for sr in (rep.Representations or []):
            if sr.id() in lbi: return lbi[sr.id()]
            for it in (sr.Items or []):
                if it.id() in lbi: return lbi[it.id()]
                if it.is_a("IfcMappedItem"):
                    try:
                        mr = it.MappingSource.MappedRepresentation
                        if mr.id() in lbi: return lbi[mr.id()]
                        for m in (mr.Items or []):
                            if m.id() in lbi: return lbi[m.id()]
                    except Exception: pass
    return ""

st = ifcopenshell.geom.settings()
try: st.set("use-world-coords", True)
except Exception:
    try: st.set(st.USE_WORLD_COORDS, True)
    except Exception: pass

vkey={}; verts=[]; faces=[]
def vid(x,y,z):
    k=(round(x,5),round(y,5),round(z,5)); i=vkey.get(k)
    if i is None: i=len(verts); vkey[k]=i; verts.append((x,y,z))
    return i

it = ifcopenshell.geom.iterator(st, f, multiprocessing.cpu_count())
n_el=0
if it.initialize():
    while True:
        sh=it.get()
        try:
            e=f.by_id(sh.id); lay=resolve(e)
            if layer_match.lower() in (lay or "").lower():
                vf=sh.geometry.verts; ff=sh.geometry.faces
                gi=[vid(vf[i]*scale, vf[i+1]*scale, vf[i+2]*scale) for i in range(0,len(vf),3)]
                for i in range(0,len(ff),3):
                    a,b,c=gi[ff[i]],gi[ff[i+1]],gi[ff[i+2]]
                    if len({a,b,c})==3: faces.append((a,b,c))
                n_el+=1
        except Exception: pass
        if not it.next(): break

print(f"elementos en capa={n_el}  vertices unicos={len(verts)}  caras={len(faces)}")
if not faces:
    print("ERROR: sin caras en esa capa"); sys.exit(2)
xs=[v[0] for v in verts]; ys=[v[1] for v in verts]; zs=[v[2] for v in verts]
print(f"extent X {min(xs):.1f}..{max(xs):.1f}  Y {min(ys):.1f}..{max(ys):.1f}  Z {min(zs):.2f}..{max(zs):.2f}")

with open(out_xml,"w",encoding="utf-8") as o:
    o.write('<?xml version="1.0"?>\n')
    o.write('<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2" date="2026-06-30" time="12:00:00">\n')
    o.write(' <Units><Imperial areaUnit="squareFoot" linearUnit="USSurveyFoot" volumeUnit="cubicFeet" temperatureUnit="fahrenheit" pressureUnit="inHG" diameterUnit="inch" angularUnit="decimal degrees" directionUnit="decimal degrees"/></Units>\n')
    o.write(' <Surfaces>\n')
    o.write(f'  <Surface name="{surf_name}">\n   <Definition surfType="TIN">\n    <Pnts>\n')
    for i,v in enumerate(verts,1):
        o.write(f'     <P id="{i}">{v[1]:.4f} {v[0]:.4f} {v[2]:.4f}</P>\n')  # Northing Easting Z
    o.write('    </Pnts>\n    <Faces>\n')
    for t in faces:
        o.write(f'     <F>{t[0]+1} {t[1]+1} {t[2]+1}</F>\n')
    o.write('    </Faces>\n   </Definition>\n  </Surface>\n </Surfaces>\n</LandXML>\n')
print(f"OK -> {out_xml}")
