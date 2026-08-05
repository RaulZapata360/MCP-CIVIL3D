# -*- coding: utf-8 -*-
# Extrae linework (baseline, bordes, breaklines) de un IFC4x3 con curvas en
# IfcGeometricSet dentro de representaciones mapeadas. Aplica transformaciones a mano.
import sys, csv, re, json, math
import numpy as np
import ifcopenshell
import ifcopenshell.util.placement as P
import ezdxf
from collections import Counter

ifc_path = sys.argv[1]
dxf_path = sys.argv[2]
scale    = float(sys.argv[3]) if len(sys.argv) > 3 else 3.2808333333  # m -> US survey foot
csv_path = dxf_path.rsplit(".",1)[0] + "_manifest.csv"

f = ifcopenshell.open(ifc_path)
print("Schema:", f.schema)

layer_by_item = {}
for pla in f.by_type("IfcPresentationLayerAssignment"):
    for it in (pla.AssignedItems or []):
        layer_by_item[it.id()] = pla.Name or "Default"

def mat_axis2(plac):
    try: return P.get_axis2placement(plac)
    except Exception: return np.eye(4)

def mat_cto(op):
    """IfcCartesianTransformationOperator3D / nonUniform -> 4x4."""
    m = np.eye(4)
    try:
        o = np.array(op.LocalOrigin.Coordinates, dtype=float) if op.LocalOrigin else np.zeros(3)
        x = np.array(op.Axis1.DirectionRatios, float) if op.Axis1 else np.array([1.,0,0])
        y = np.array(op.Axis2.DirectionRatios, float) if op.Axis2 else np.array([0.,1,0])
        z = np.array(op.Axis3.DirectionRatios, float) if getattr(op,'Axis3',None) else np.cross(x,y)
        for v in (x,y,z):
            n=np.linalg.norm(v);
        x=x/np.linalg.norm(x); y=y/np.linalg.norm(y); z=z/np.linalg.norm(z)
        s1 = op.Scale if op.Scale else 1.0
        s2 = getattr(op,'Scale2',None) or s1
        s3 = getattr(op,'Scale3',None) or s1
        m[:3,0]=x*s1; m[:3,1]=y*s2; m[:3,2]=z*s3; m[:3,3]=o
    except Exception: pass
    return m

doc = ezdxf.new("R2018"); doc.header["$INSUNITS"]=0
msp = doc.modelspace()
PALETTE=[1,2,3,4,5,6,30,40,50,140,150,160,170,200,210,9,8,11,12,13,14]
lc={}
def lay(raw):
    n=(re.sub(r'[<>/\\":;?*|,=`]',"_",raw) or "IFC")[:200]
    if n not in doc.layers: doc.layers.add(n,color=lc.setdefault(n,PALETTE[len(lc)%len(PALETTE)]))
    return n

EXT=[None]*6
def upd(p):
    for i in range(3):
        if EXT[i] is None or p[i]<EXT[i]: EXT[i]=p[i]
        if EXT[i+3] is None or p[i]>EXT[i+3]: EXT[i+3]=p[i]

def poly_pts(el):
    if el.is_a("IfcPolyline"):
        return [tuple(list(pt.Coordinates)+[0,0])[:3] for pt in el.Points]
    return None

def add_world(pts3, M, layer):
    out=[]
    for p in pts3:
        w = M @ np.array([p[0],p[1],p[2],1.0])
        q = (w[0]*scale, w[1]*scale, w[2]*scale)
        out.append(q); upd(q)
    if len(out)>=2:
        msp.add_polyline3d(out, dxfattribs={"layer": layer})
        return 1
    return 0

rows=[]; npl=ncc=skip=0
for e in f.by_type("IfcBuildingElementProxy"):
    rep=e.Representation
    if not rep: continue
    try: M_obj = P.get_local_placement(e.ObjectPlacement)
    except Exception: M_obj = np.eye(4)
    for sr in rep.Representations:
        for it in (sr.Items or []):
            if not it.is_a("IfcMappedItem"): continue
            M_t = mat_cto(it.MappingTarget) if it.MappingTarget else np.eye(4)
            M_o = mat_axis2(it.MappingSource.MappingOrigin) if it.MappingSource.MappingOrigin else np.eye(4)
            M = M_obj @ M_t @ M_o
            mr = it.MappingSource.MappedRepresentation
            for git in (mr.Items or []):
                if not git.is_a("IfcGeometricSet"): continue
                layer = lay(layer_by_item.get(git.id(), "IFC_curves"))
                for el in (git.Elements or []):
                    pts = poly_pts(el)
                    if pts:
                        if add_world(pts, M, layer): npl+=1
                        rows.append([e.id(), git.id(), el.is_a(), layer_by_item.get(git.id(),"?"), len(pts)])
                    elif el.is_a("IfcCompositeCurve"):
                        # best-effort: segmentos IfcPolyline
                        got=False
                        for seg in (el.Segments or []):
                            pc=getattr(seg,"ParentCurve",None)
                            sp=poly_pts(pc) if pc else None
                            if sp and add_world(sp, M, layer): got=True
                        if got: ncc+=1
                        else: skip+=1
                    else:
                        skip+=1

doc.saveas(dxf_path)
with open(csv_path,"w",newline="",encoding="utf-8") as cf:
    w=csv.writer(cf); w.writerow(["proxy_id","geomset_id","curve_type","cad_layer","n_points"]); w.writerows(rows)
by_layer=Counter(r[3] for r in rows)
info={"scale":scale,"insunits":0,"schema":f.schema,"type":"linework",
      "extent":{"xmin":EXT[0],"ymin":EXT[1],"zmin":EXT[2],"xmax":EXT[3],"ymax":EXT[4],"zmax":EXT[5]},
      "polylines":npl,"composite":ncc,"skipped":skip,"layers":sorted(by_layer)}
with open(dxf_path.rsplit(".",1)[0]+".info.json","w",encoding="utf-8") as jf: json.dump(info,jf,indent=1)
print("\n--- Polilineas por capa ---")
for t,n in by_layer.most_common(): print(f"  {n:6d}  {t}")
print(f"\nPolilineas: {npl} | compuestas: {ncc} | omitidas: {skip} | capas: {len(by_layer)}")
if EXT[0] is not None:
    print(f"Extent X {EXT[0]*1:.1f}..{EXT[3]:.1f} Y {EXT[1]:.1f}..{EXT[4]:.1f} Z {EXT[2]:.1f}..{EXT[5]:.1f}")
print("OK")
