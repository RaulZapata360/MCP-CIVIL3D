# -*- coding: utf-8 -*-
# Conversor IFC -> DXF con capas NCS (mallas + linework), escala US survey foot, Unitless.
import sys, re, multiprocessing
import numpy as np
import ifcopenshell, ifcopenshell.geom
import ifcopenshell.util.placement as P
import ezdxf
from ezdxf.render import MeshBuilder

ifc_path=sys.argv[1]; dxf_path=sys.argv[2]
_scale_arg = sys.argv[3] if len(sys.argv)>3 else "3.2808333333"

# Mapeo Bentley -> NCS (limpio)
MAP={
 "Geom_Baseline":"C-ROAD-ASSM-BLIN","EXISTING_ELEVATION_ALLIGNMENT":"C-ROAD-FEAT",
 "DES-Surface":"C-ROAD-FEAT","DES_BARRIER_TBS_CONC_DOUBLE_FACE_PAR-M":"C-ROAD-LW-BARRIER",
 "E_Terrain_Bank":"C-ROAD-FEAT","MODELING_AGGREGATE_BASE":"C-ROAD-SHAP",
 "MODELING_ASPHALT_CONCRETE_BASE_COURSE":"C-ROAD-SHAP","MODELING_CONCRETE_BARRIER":"C-ROAD-LW-BARRIER",
 "Pavement Marking White":"C-ROAD-PMRK-N","Road_EdgeOfPavement":"C-ROAD-LW-EP",
 "Road_Pavement":"C-ROAD-SHAP","Road_Shoulder":"C-ROAD-LW-UNPAVE","TC_Aggregate":"C-ROAD-SHAP",
 "TC_Asphalt":"C-ROAD-SHAP","Terrain_Contour_Major":"C-SURF-CONTOUR_Major",
 "Terrain_Contour_Minor":"C-SURF-CONTOUR_Minor","Terrain_Exterior":"C-SURF-BNDY",
 "Terrain_Triangle":"C-SURF-TINN","TL_Pavement Centerline":"C-ROAD-CNTR",
 "TL_Pavement Centerline Sub":"C-ROAD-CNTR","TL_Pavement Edge Sub":"C-ROAD-LW-EP",
 "TRAF_PR_DES_LT_LUM":"C-ROAD-LITE-LUMI-N","TRAF_PR_DES_LT_MP":"C-ROAD-LITE-POLE-N",
 "TRAF_PR_DES_PM_ARR":"C-ROAD-PMRK-ARRW-N","TRAF_PR_DES_PM_LINE":"C-ROAD-PMRK-LINE-N",
 "TRAF_PR_DES_PM_MARK":"C-ROAD-PMRK-MARK-N","TRAF_PR_DES_PM_MSG":"C-ROAD-PMRK-WORD-N",
 "TRAF_PR_DES_PM_SYM":"C-ROAD-PMRK-SYMB-N","TRAF_PR_DES_TS_SIGN":"C-ROAD-SIGN-N",
 "WORKING_3D_Lines":"C-ROAD-LW-LINE","WORKING_Revised_Building_Footprint":"A-BLDG-FPRT",
 # --- South Island: capas de camino adicionales (convencion NCS de NI) ---
 "MODELING_ASPHALT_CONCRETE_SURFACE_COURSE":"C-ROAD-SHAP",
 "MODELING_GUARDRAIL":"C-ROAD-LW-BARRIER","DES_GUARDRAIL_GR-FOA-2_TYPE_I_50":"C-ROAD-LW-BARRIER",
 "TRAF_PR_DES_PM_DBLYELLOW":"C-ROAD-PMRK-LINE-N","TRAF_PR_DES_PM_STOPBAR":"C-ROAD-PMRK-MARK-N",
 "TRAF_PR_DES_SI_OHSTR":"C-ROAD-SIGN-N",
 "Bridge_Diaphragms":"S-BRDG-DIAF","DES_GUARDRAIL_HE_TRAN_GR-MGS4_R_50":"C-ROAD-LW-BARRIER",
 "DES_NOISE_WALL":"C-ROAD-WALL-NOISE-N","DES_TEXT_MISC":"G-ANNO-TEXT-N",
 "MODELING-CORRIDOR_PRELIMINARY":"C-ROAD-CORRIDOR-PRELIM-N",
 "MODELING_CONTINUOUSLY_REINFORCED_CONCRETE_PAVEMENT":"C-ROAD-SHAP",
 "SURVEY_DTM_DISPLAY_TRIANGLES":"C-SURF-TINN",
 # --- North Island: Utilidades y Drenaje civil -> NCS (C-WATR/SSWR/STRM/COMM/PWR) ---
 "Util_Water_Conduits_3D":"C-WATR","Util_Water_Nodes_3D":"C-WATR","Utility-Water":"C-WATR",
 "Util_Sanitary_Conduits":"C-SSWR","Util_Sanitary_Conduits_3D":"C-SSWR","Util_Sanitary_Nodes_3D":"C-SSWR","Utility-SanitarySewer":"C-SSWR",
 "Util_Storm_Conduits_3D":"C-STRM","Util_Storm_Nodes_3D":"C-STRM",
 "Util_Communications_Conduits":"C-COMM","Util_Communications_Conduits_3D":"C-COMM","Util_Communications_Nodes_3D":"C-COMM","Utility-Telephone":"C-COMM","RW_PR_UTIL_LVL_AB_COMM_FO":"C-COMM",
 "Util_Electric_Conduits":"C-PWR","Util_Electric_Conduits_3D":"C-PWR","Utility-Power":"C-PWR","RW_PR_UTIL_LVL_AB_POWER_LINE_UG_MV":"C-PWR",
 "Default":"Default",
}
SPLIT={"Terrain_Design"}  # malla->TINN, linea->FEAT
def ncs(base,is_mesh):
    if base in SPLIT: return "C-SURF-TINN" if is_mesh else "C-ROAD-FEAT"
    return MAP.get(base, base)

f=ifcopenshell.open(ifc_path)
# Escala: "georef" = modo correcto VA83-SF. Archivo en PIE (estructuras) -> 1/unit_scale
# (preserva coords State Plane ft verbatim, invirtiendo el x0.3048 de ifcopenshell).
# Archivo en METROS SI (caminos) -> 3.2808333333 (m -> US survey ft). Si se pasa un
# numero, se usa tal cual (compatibilidad con lotes antiguos).
if _scale_arg == "georef":
    import ifcopenshell.util.unit as _U
    _us=_U.calculate_unit_scale(f)
    scale=(1.0/_us) if abs(_us-1.0)>1e-9 else 3.2808333333
    print(f"georef: unit_scale={_us} -> escala x{scale}")
else:
    scale=float(_scale_arg)
lbi={}
for pla in f.by_type("IfcPresentationLayerAssignment"):
    for it in (pla.AssignedItems or []): lbi[it.id()]=(pla.Name or "Default").split("::")[0]
def resolve(e):
    rep=e.Representation
    if rep:
        for sr in rep.Representations:
            if sr.id() in lbi: return lbi[sr.id()]
            for it in (sr.Items or []):
                if it.id() in lbi: return lbi[it.id()]
                if it.is_a("IfcMappedItem"):
                    mr=it.MappingSource.MappedRepresentation
                    if mr.id() in lbi: return lbi[mr.id()]
                    for m in (mr.Items or []):
                        if m.id() in lbi: return lbi[m.id()]
    return "Default"

doc=ezdxf.new("R2018"); doc.header["$INSUNITS"]=0; msp=doc.modelspace()
def L(name):
    n=(re.sub(r'[<>/\\":;?*|,=`]',"_",name) or "0")[:200]
    if n not in doc.layers: doc.layers.add(n)
    return n

# --- pase 1: mallas (iterador) ---
st=ifcopenshell.geom.settings()
for k in ("use-world-coords",):
    try: st.set(k,True)
    except:
        try: st.set(st.USE_WORLD_COORDS,True)
        except: pass
it=ifcopenshell.geom.iterator(st,f,multiprocessing.cpu_count())
nm=nl=0
if it.initialize():
    while True:
        sh=it.get()
        try:
            e=f.by_id(sh.id); base=resolve(e)
            vf=sh.geometry.verts; ff=sh.geometry.faces
            verts=[(vf[i]*scale,vf[i+1]*scale,vf[i+2]*scale) for i in range(0,len(vf),3)]
            if ff:
                faces=[(ff[i],ff[i+1],ff[i+2]) for i in range(0,len(ff),3)]
                mb=MeshBuilder(); mb.add_mesh(vertices=verts,faces=faces)
                mb.render_polyface(msp,dxfattribs={"layer":L(ncs(base,True))}); nm+=1
        except Exception: pass
        if not it.next(): break

# --- pase 2: curvas (mapped IfcGeometricSet) ---
def mcto(op):
    m=np.eye(4)
    try:
        o=np.array(op.LocalOrigin.Coordinates,float) if op.LocalOrigin else np.zeros(3)
        x=np.array(op.Axis1.DirectionRatios,float) if op.Axis1 else np.array([1.,0,0])
        y=np.array(op.Axis2.DirectionRatios,float) if op.Axis2 else np.array([0.,1,0])
        z=np.array(op.Axis3.DirectionRatios,float) if getattr(op,'Axis3',None) else np.cross(x,y)
        x/=np.linalg.norm(x); y/=np.linalg.norm(y); z/=np.linalg.norm(z)
        s=op.Scale or 1.0
        m[:3,0]=x*s; m[:3,1]=y*s; m[:3,2]=z*s; m[:3,3]=o
    except: pass
    return m
def a2(pl):
    try: return P.get_axis2placement(pl)
    except: return np.eye(4)
for e in f.by_type("IfcBuildingElementProxy"):
    rep=e.Representation
    if not rep: continue
    try: Mo=P.get_local_placement(e.ObjectPlacement)
    except: Mo=np.eye(4)
    base=resolve(e); layer=L(ncs(base,False))
    for sr in rep.Representations:
        for itm in (sr.Items or []):
            if not itm.is_a("IfcMappedItem"): continue
            Mt=mcto(itm.MappingTarget) if itm.MappingTarget else np.eye(4)
            Mg=a2(itm.MappingSource.MappingOrigin) if itm.MappingSource.MappingOrigin else np.eye(4)
            M=Mo@Mt@Mg
            for git in (itm.MappingSource.MappedRepresentation.Items or []):
                if not git.is_a("IfcGeometricSet"): continue
                for el in (git.Elements or []):
                    pts=None
                    if el.is_a("IfcPolyline"): pts=[tuple(list(p.Coordinates)+[0,0])[:3] for p in el.Points]
                    elif el.is_a("IfcCompositeCurve"):
                        for seg in (el.Segments or []):
                            pc=getattr(seg,"ParentCurve",None)
                            if pc and pc.is_a("IfcPolyline"):
                                sp=[tuple(list(p.Coordinates)+[0,0])[:3] for p in pc.Points]
                                w=[(M@np.array([q[0],q[1],q[2],1.0]))[:3]*scale for q in sp]
                                if len(w)>=2: msp.add_polyline3d([tuple(v) for v in w],dxfattribs={"layer":layer}); nl+=1
                        continue
                    if pts:
                        w=[(M@np.array([q[0],q[1],q[2],1.0]))[:3]*scale for q in pts]
                        if len(w)>=2: msp.add_polyline3d([tuple(v) for v in w],dxfattribs={"layer":layer}); nl+=1

doc.saveas(dxf_path)
print(f"mallas={nm} lineas={nl} capas={len(doc.layers)-1} -> {dxf_path}")
print("OK")
