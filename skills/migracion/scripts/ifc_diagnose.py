import sys
from collections import Counter
import ifcopenshell

def hr(t): print("\n" + "="*70 + f"\n{t}\n" + "="*70)

path = sys.argv[1]
print(f"Archivo: {path}")
f = ifcopenshell.open(path)
print(f"Schema: {f.schema}  |  Schema id: {f.schema_identifier}")

def sby(t):
    """by_type seguro: devuelve [] si el tipo no existe en el esquema."""
    try:
        return f.by_type(t)
    except RuntimeError:
        return []

# --- Unidades ---
hr("UNIDADES")
for u in f.by_type("IfcUnitAssignment"):
    for unit in u.Units:
        if unit.is_a("IfcSIUnit"):
            print(f"  SI: {unit.UnitType} = {unit.Prefix or ''}{unit.Name}")
        elif unit.is_a("IfcConversionBasedUnit"):
            print(f"  Conv: {unit.UnitType} = {unit.Name}")
        else:
            print(f"  {unit.is_a()}: {getattr(unit,'UnitType','?')}")

# --- Georreferenciacion ---
hr("GEORREFERENCIACION")
crs = sby("IfcProjectedCRS")
if crs:
    for c in crs:
        print(f"  IfcProjectedCRS: Name={c.Name}  GeodeticDatum={c.GeodeticDatum}  VerticalDatum={c.VerticalDatum}  MapProjection={c.MapProjection}  MapZone={c.MapZone}")
else:
    print("  (sin IfcProjectedCRS)")
mc = sby("IfcMapConversion")
if mc:
    for m in mc:
        print(f"  IfcMapConversion: E={m.Eastings} N={m.Northings} H={m.OrthogonalHeight} XAxisAbs={m.XAxisAbscissa} XAxisOrd={m.XAxisOrdinate} Scale={m.Scale}")
else:
    print("  (sin IfcMapConversion -> modelo puede estar cerca del origen 0,0)")

# --- Sitio / elevacion ---
for s in f.by_type("IfcSite"):
    print(f"  IfcSite: Name={s.Name}  RefElevation={getattr(s,'RefElevation',None)}  RefLatLong={getattr(s,'RefLatitude',None)}/{getattr(s,'RefLongitude',None)}")

# --- Conteo de entidades ---
hr("CONTEO DE ENTIDADES (top 40)")
c = Counter(e.is_a() for e in f)
for name, n in c.most_common(40):
    print(f"  {n:8d}  {name}")
print(f"  TOTAL tipos: {len(c)}  |  TOTAL entidades: {sum(c.values())}")

# --- Alineamientos ---
hr("ALINEAMIENTOS")
aligns = sby("IfcAlignment")
print(f"  IfcAlignment: {len(aligns)}")
for a in aligns:
    print(f"    - #{a.id()} Name={a.Name}")
for t in ("IfcAlignmentHorizontal","IfcAlignmentVertical","IfcAlignmentCant",
          "IfcAlignmentSegment","IfcAlignmentHorizontalSegment","IfcAlignmentVerticalSegment"):
    print(f"  {t}: {len(sby(t))}")

# --- Superficies / mallas ---
hr("SUPERFICIES / MALLAS")
for t in ("IfcTriangulatedFaceSet","IfcTriangulatedIrregularNetwork","IfcPolygonalFaceSet",
          "IfcGeographicElement","IfcFacetedBrep","IfcShellBasedSurfaceModel","IfcSurface"):
    n = len(sby(t))
    if n: print(f"  {t}: {n}")
for tfs in sby("IfcTriangulatedFaceSet")[:5]:
    npts = len(tfs.Coordinates.CoordList) if tfs.Coordinates else 0
    ntri = len(tfs.CoordIndex) if tfs.CoordIndex else 0
    print(f"    TFS #{tfs.id()}: {npts} vertices, {ntri} triangulos")

# --- Productos de infraestructura ---
hr("PRODUCTOS DE INFRAESTRUCTURA")
for t in ("IfcRoad","IfcRoadPart","IfcCourse","IfcPavement","IfcKerb","IfcEarthworksFill",
          "IfcEarthworksCut","IfcPipeSegment","IfcDuctSegment","IfcDistributionElement",
          "IfcBuildingElementProxy","IfcCivilElement"):
    n = len(sby(t))
    if n: print(f"  {t}: {n}")
print("\nDIAGNOSTICO COMPLETO.")

