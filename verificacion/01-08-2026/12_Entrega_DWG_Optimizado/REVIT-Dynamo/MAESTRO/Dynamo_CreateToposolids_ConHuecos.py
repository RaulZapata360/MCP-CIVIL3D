# -*- coding: utf-8 -*-
# Crea las Toposolid en Revit RESPETANDO LOS HUECOS INTERIORES (edificaciones y
# estructuras) y las superficies partidas en varias piezas.
#
# Diferencias vs Dynamo_CreateToposolids.py (la version anterior, sin huecos):
#   - Lee el CSV nuevo con columnas (SurfaceName, PieceId, RingType, RingId,
#     Seq, X, Y). RingType = OUTER | HOLE.
#   - Crea UN Toposolid por cada par (SurfaceName, PieceId) -- hay superficies
#     partidas en piezas fisicamente separadas (p.ej. Gravel Surface 1 son 3).
#   - Agrega cada anillo HOLE como un CurveLoop ADICIONAL dentro de "profiles".
#     Asi es como Toposolid.Create representa huecos: el primer loop es el
#     perimetro exterior y los siguientes son huecos interiores.
#   - Los puntos vienen ya asignados por pieza desde Python (columna PieceId),
#     porque pasarle a una pieza los puntos de otra deja puntos fuera de su
#     contorno y dispara el dialogo bloqueante "Slab Shape Edit failed".
#
# ENTRADAS (nodos File Path):
#   IN[0]: All_Points_ByPiece.csv        (SurfaceName,PieceId,X,Y,Z)
#   IN[1]: All_Boundaries_Complete.csv   (SurfaceName,PieceId,RingType,RingId,Seq,X,Y)
#
# Recordatorios de la API (ver el tutorial, seccion 3):
#   - Toposolid.Create tiene 5 argumentos, el ultimo es levelId.
#   - TODOS los CurveLoop (exterior y huecos) deben ser PLANOS, Z=0. La
#     elevacion real la aporta unicamente la lista de points.
#   - Hay que filtrar puntos consecutivos casi duplicados o Revit lanza
#     "Curve length is too small for endpoints".

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
import Autodesk.Revit.DB as DB
from Autodesk.Revit.DB import XYZ, Line, CurveLoop
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

import csv, os
from collections import OrderedDict
from System.Collections.Generic import List

doc = DocumentManager.Instance.CurrentDBDocument

points_path = IN[0]
boundary_path = IN[1]

MIN_SEG_LEN = 0.1  # ft

# ---------------- puntos, agrupados por (superficie, pieza) ----------------
points_groups = OrderedDict()
with open(points_path, 'r') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        key = (row[0], int(row[1]))
        x, y, z = float(row[2]), float(row[3]), float(row[4])
        points_groups.setdefault(key, []).append(XYZ(x, y, z))

# ------------- contornos, agrupados por (superficie, pieza, anillo) -------------
# ring_groups[(surf, piece)] = {'OUTER': {0: [(seq, XYZ), ...]},
#                               'HOLE':  {0: [...], 1: [...]}}
ring_groups = OrderedDict()
with open(boundary_path, 'r') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        key = (row[0], int(row[1]))
        rtype, rid, seq = row[2], int(row[3]), int(row[4])
        x, y = float(row[5]), float(row[6])
        d = ring_groups.setdefault(key, {'OUTER': {}, 'HOLE': {}})
        d[rtype].setdefault(rid, []).append((seq, XYZ(x, y, 0.0)))


def build_loop(seq_pts):
    """seq_pts: lista de (seq, XYZ). Devuelve un CurveLoop cerrado y plano, o
    None si tras limpiar quedan menos de 3 puntos utilizables."""
    pts = [p for _, p in sorted(seq_pts, key=lambda t: t[0])]
    cleaned = [pts[0]]
    for p in pts[1:]:
        if cleaned[-1].DistanceTo(p) >= MIN_SEG_LEN:
            cleaned.append(p)
    # el ultimo punto puede coincidir con el primero (cierre duplicado)
    while len(cleaned) > 1 and cleaned[0].DistanceTo(cleaned[-1]) < MIN_SEG_LEN:
        cleaned.pop()
    if len(cleaned) < 3:
        return None
    loop = CurveLoop()
    n = len(cleaned)
    for i in range(n):
        loop.Append(Line.CreateBound(cleaned[i], cleaned[(i + 1) % n]))
    return loop


default_type_id = DB.ElementId.InvalidElementId
first_type = DB.FilteredElementCollector(doc).OfClass(DB.ToposolidType).FirstElement()
if first_type is not None:
    default_type_id = first_type.Id

level = DB.FilteredElementCollector(doc).OfClass(DB.Level).FirstElement()
level_id = level.Id if level is not None else DB.ElementId.InvalidElementId

TransactionManager.Instance.EnsureInTransaction(doc)

created = []
errores = []
huecos_omitidos = []

for key in ring_groups:
    surf_name, piece_id = key
    label = surf_name if piece_id == 0 and len(
        [k for k in ring_groups if k[0] == surf_name]) == 1 else "%s - %d" % (surf_name, piece_id + 1)
    try:
        rings = ring_groups[key]
        if 0 not in rings['OUTER']:
            errores.append((label, "sin anillo OUTER"))
            continue

        outer = build_loop(rings['OUTER'][0])
        if outer is None:
            errores.append((label, "anillo exterior degenerado tras limpieza"))
            continue

        profiles = List[CurveLoop]()
        profiles.Add(outer)

        n_holes = 0
        for rid in sorted(rings['HOLE'].keys()):
            hl = build_loop(rings['HOLE'][rid])
            if hl is None:
                huecos_omitidos.append((label, rid))
                continue
            profiles.Add(hl)
            n_holes += 1

        interior_pts = List[XYZ](points_groups.get(key, []))
        topo = DB.Toposolid.Create(doc, profiles, interior_pts,
                                   default_type_id, level_id)

        p = topo.LookupParameter("Comments")
        if p and not p.IsReadOnly:
            p.Set(label)
        created.append((label, n_holes, len(interior_pts)))
    except Exception as ex:
        errores.append((label, str(ex)))

TransactionManager.Instance.TransactionTaskDone()

log_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'dynamo_log.txt')
with open(log_path, 'w') as logf:
    logf.write('CREADAS ({0}):\n'.format(len(created)))
    for label, nh, npts in created:
        logf.write('  OK: {0}  (huecos={1}, puntos={2})\n'.format(label, nh, npts))
    logf.write('\nERRORES ({0}):\n'.format(len(errores)))
    for label, msg in errores:
        logf.write('  FALLO: {0}\n    {1}\n'.format(label, msg))
    logf.write('\nHUECOS OMITIDOS por degenerados ({0}):\n'.format(len(huecos_omitidos)))
    for label, rid in huecos_omitidos:
        logf.write('  {0} hueco #{1}\n'.format(label, rid))

OUT = (len(created), errores, huecos_omitidos)
