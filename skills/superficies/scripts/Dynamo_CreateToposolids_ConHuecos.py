# -*- coding: utf-8 -*-
# Crea las Toposolid en Revit RESPETANDO LOS HUECOS INTERIORES (edificaciones y
# estructuras) y las superficies partidas en varias piezas.
#
# ENTRADAS (nodos File Path):
#   IN[0]: All_Points_ByPiece.csv        (SurfaceName,PieceId,X,Y,Z)
#   IN[1]: All_Boundaries_Complete.csv   (SurfaceName,PieceId,RingType,RingId,Seq,X,Y)
#
# Recordatorios de la API:
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

# Espesor del solido. OJO: una superficie TIN de Civil 3D NO tiene espesor, y el
# espesor tampoco viaja en los CSV ni en el LandXML. Un Toposolid de Revit SIEMPRE
# es un solido, asi que si no se fija un tipo propio Revit aplica el primero que
# encuentra en el proyecto -- en la plantilla Imperial ese es "Grassland - 16""
# (1.333 ft), un valor de plantilla sin relacion con el proyecto.
ESPESOR_FT = 0.17                              # carpeta asfaltica (2.04")
NOMBRE_TIPO = 'Carpeta Asfaltica - 0.17ft'

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
    while len(cleaned) > 1 and cleaned[0].DistanceTo(cleaned[-1]) < MIN_SEG_LEN:
        cleaned.pop()
    if len(cleaned) < 3:
        return None
    loop = CurveLoop()
    n = len(cleaned)
    for i in range(n):
        loop.Append(Line.CreateBound(cleaned[i], cleaned[(i + 1) % n]))
    return loop


def nombre_de(t):
    """Nombre de un ElementType sin depender de Element.Name (varia segun motor)."""
    p = t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
    return p.AsString() if p else ''


level = DB.FilteredElementCollector(doc).OfClass(DB.Level).FirstElement()
level_id = level.Id if level is not None else DB.ElementId.InvalidElementId

TransactionManager.Instance.EnsureInTransaction(doc)

# ---- tipo de Toposolid con el espesor del proyecto -----------------------
tipo_usado = ''
default_type_id = DB.ElementId.InvalidElementId
existente = None
for t in DB.FilteredElementCollector(doc).OfClass(DB.ToposolidType):
    if nombre_de(t) == NOMBRE_TIPO:
        existente = t
        break

if existente is not None:
    default_type_id = existente.Id
    tipo_usado = '%s (ya existia)' % NOMBRE_TIPO
else:
    base = DB.FilteredElementCollector(doc).OfClass(DB.ToposolidType).FirstElement()
    if base is not None:
        nuevo = None
        try:
            nuevo = base.Duplicate(NOMBRE_TIPO)
            # NO usar CompoundStructure.CreateSingleLayerCompoundStructure: la
            # estructura que devuelve trae una EndCapCondition que Toposolid
            # rechaza ("wrong EndCap condition for this element type"). Se parte
            # de la estructura del tipo existente, que ya es valida, y solo se
            # reduce a una capa con el espesor pedido.
            cs = nuevo.GetCompoundStructure()
            i = cs.LayerCount - 1
            while cs.LayerCount > 1 and i >= 0:
                try:
                    cs.DeleteLayer(i)
                except Exception:
                    pass
                i -= 1
            cs.SetLayerWidth(0, ESPESOR_FT)
            nuevo.SetCompoundStructure(cs)
            default_type_id = nuevo.Id
            tipo_usado = '%s (creado, %.4f ft, %d capa/s)' % (
                NOMBRE_TIPO, ESPESOR_FT, cs.LayerCount)
        except Exception as ex:
            # segundo intento: estructura nueva forzando el remate correcto
            try:
                cs2 = DB.CompoundStructure.CreateSingleLayerCompoundStructure(
                    DB.MaterialFunctionAssignment.Structure,
                    ESPESOR_FT,
                    DB.ElementId.InvalidElementId)
                cs2.EndCap = DB.EndCapCondition.NoEndCap
                objetivo = nuevo if nuevo is not None else base
                objetivo.SetCompoundStructure(cs2)
                default_type_id = objetivo.Id
                tipo_usado = '%s (creado via NoEndCap, %.4f ft)' % (NOMBRE_TIPO, ESPESOR_FT)
            except Exception as ex2:
                default_type_id = base.Id
                tipo_usado = '%s (FALLO crear el tipo: %s | %s)' % (
                    nombre_de(base), str(ex), str(ex2))

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
        created.append((label, n_holes, len(interior_pts), topo.Id, key))
    except Exception as ex:
        errores.append((label, str(ex)))

TransactionManager.Instance.TransactionTaskDone()

# ---- autodiagnostico: que piezas perdieron el relieve --------------------
# El dialogo "Slab Shape Edit failed" se resuelve con Reset Shape, que borra los
# puntos de forma y deja la pieza PLANA. Revit no informa cuales fueron: el
# dialogo es anonimo y ocurre al confirmar la transaccion, no en cada Create.
# Se detectan comparando el relieve real (bounding box menos el espesor) contra
# el que traen los datos de origen.
relieve_esperado = {}
for k, lista in points_groups.items():
    if lista:
        zs = [q.Z for q in lista]
        relieve_esperado[k] = max(zs) - min(zs)
    else:
        relieve_esperado[k] = 0.0

planas = []
revisadas = []
for item in created:
    label, nh, npts, eid, key = item
    try:
        el = doc.GetElement(eid)
        bb = el.get_BoundingBox(None)
        if bb is None:
            continue
        alto = bb.Max.Z - bb.Min.Z
        real = alto - ESPESOR_FT          # el solido = relieve + espesor
        if real < 0:
            real = 0.0
        esp = relieve_esperado.get(key, 0.0)
        revisadas.append((label, esp, real))
        # perdio el terreno: los datos dicen que sube y el solido esta plano
        if esp > 0.10 and real < esp * 0.25:
            planas.append((label, esp, real))
    except Exception:
        pass

# ~/Desktop no existe si el escritorio esta redirigido a OneDrive:
# el log va junto a los CSV, que siempre existen.
log_path = os.path.join(os.path.dirname(points_path), 'dynamo_log.txt')
with open(log_path, 'w') as logf:
    logf.write('TIPO: {0}\n'.format(tipo_usado))
    logf.write('NIVEL: {0}\n\n'.format(level.Name if level is not None else 'ninguno'))
    logf.write('CREADAS ({0}):\n'.format(len(created)))
    for label, nh, npts, eid, key in created:
        logf.write('  OK: {0}  (huecos={1}, puntos={2})\n'.format(label, nh, npts))
    logf.write('\nERRORES ({0}):\n'.format(len(errores)))
    for label, msg in errores:
        logf.write('  FALLO: {0}\n    {1}\n'.format(label, msg))
    logf.write('\nHUECOS OMITIDOS por degenerados ({0}):\n'.format(len(huecos_omitidos)))
    for label, rid in huecos_omitidos:
        logf.write('  {0} hueco #{1}\n'.format(label, rid))

    logf.write('\n' + '=' * 62 + '\n')
    logf.write('PIEZAS QUE PERDIERON EL RELIEVE ({0}) -- efecto de Reset Shape\n'
               .format(len(planas)))
    logf.write('=' * 62 + '\n')
    if planas:
        logf.write('  %-34s %10s %10s\n' % ('pieza', 'esperado', 'real'))
        for label, esp, real in sorted(planas, key=lambda t: -t[1]):
            logf.write('  %-34s %9.3f %9.3f\n' % (label[:34], esp, real))
    else:
        logf.write('  ninguna: todas conservan su relieve\n')

    logf.write('\nRELIEVE POR PIEZA (esperado vs real, ft)\n')
    logf.write('  %-34s %10s %10s  %s\n' % ('pieza', 'esperado', 'real', 'estado'))
    for label, esp, real in sorted(revisadas, key=lambda t: -t[1]):
        estado = 'PLANA' if (esp > 0.10 and real < esp * 0.25) else 'ok'
        logf.write('  %-34s %9.3f %9.3f  %s\n' % (label[:34], esp, real, estado))

OUT = (tipo_usado, len(created), len(planas), errores, huecos_omitidos)
