# -*- coding: utf-8 -*-
# ============================================================================
#  SOUTH ISLAND -- TERRENO EXISTENTE (Surface_Exis_SI)
#  Crea las Toposolid en Revit 2026 desde los CSV generados a partir de
#  Volume_Surface_SI.xml, respetando los 10 huecos interiores y las 2 piezas
#  fisicamente separadas.
#
#  Es el MISMO script que el de las 22 superficies de carpeta
#  (..\..\05_Dynamo_Revit), con tres cambios marcados con  # [EXIS]:
#  el nombre y espesor del tipo, el comentario del offset y poco mas. Se ha
#  mantenido deliberadamente igual porque ese ya esta probado contra Revit 2026.
#
#  ENTRADAS (nodos File Path del grafo):
#    IN[0]: All_Points_ByPiece.csv        (SurfaceName,PieceId,X,Y,Z)
#    IN[1]: All_Boundaries_Complete.csv   (SurfaceName,PieceId,RingType,RingId,Seq,X,Y)
#
#  Recordatorios de la API que costaron encontrar:
#    - Toposolid.Create tiene 5 argumentos; el ultimo es levelId.
#    - TODOS los CurveLoop (exterior y huecos) deben ser PLANOS, Z=0. La
#      elevacion real la aporta unicamente la lista de points.
#    - Hay que filtrar puntos consecutivos casi duplicados o Revit lanza
#      "Curve length is too small for endpoints".
#    - CompoundStructure.CreateSingleLayerCompoundStructure devuelve una
#      EndCapCondition que Toposolid rechaza; hay que partir de la estructura
#      de un tipo existente y reducirla a una capa.
# ============================================================================

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
clr.AddReference('System')
import System
import Autodesk.Revit.DB as DB
from Autodesk.Revit.DB import XYZ, Line, CurveLoop
from RevitServices.Persistence import DocumentManager

import csv, os
from collections import OrderedDict
from System.Collections.Generic import List

doc = DocumentManager.Instance.CurrentDBDocument

points_path = IN[0]
boundary_path = IN[1]

MIN_SEG_LEN = 0.1  # ft -- aqui solo afecta a 1 de los 1.988 vertices de contorno

# [EXIS] Espesor del solido. Una superficie TIN de Civil 3D NO tiene espesor, y el
# espesor tampoco viaja en los CSV ni en el LandXML. Un Toposolid de Revit SIEMPRE
# es un solido, asi que si no se fija un tipo propio Revit aplica el primero que
# encuentra en el proyecto -- en la plantilla Imperial ese es "Grassland - 16""
# (1.333 ft), un valor de plantilla sin relacion con el proyecto.
# Tipo propio para no mezclarlo con el de las superficies de carpeta.
ESPESOR_FT = 1.00
NOMBRE_TIPO = 'Terreno Existente - 1.00ft'

# [EXIS] DESFASE AL MODELO DE REVIT -- ver GEORREFERENCIA_Y_COORDENADAS.txt
# Son LOS MISMOS valores que el paquete de las 22 superficies de carpeta. No son
# una propiedad del sistema de coordenadas: se midieron a mano contra el modelo
# de Revit de destino. Se repiten aqui EXACTAMENTE para que el terreno existente
# caiga bajo las carpetas y no desplazado respecto a ellas.
#
# SI IMPORTAS ESTO EN UN MODELO DISTINTO, pon los dos a 0.0 y georreferencia con
# "Specify Coordinates at Point" segun el .txt. Lo que NUNCA hay que hacer es
# dejar un offset aqui y otro distinto en el paquete de carpetas.
OFFSET_X = 1702.20  # ft (Easting)
OFFSET_Y = -3792.42  # ft (Northing)

SAVE_FILE_PATH = r""
GUARDAR_INCREMENTAL = True   # guarda tras cada pieza: permite reanudar si Revit cae


swallower = None
try:
    class WarningSwallower(DB.IFailuresPreprocessor):
        """Silencia los avisos de forma de Toposolid.

        El dialogo "Slab Shape Edit failed" es modal y detiene la importacion; si se
        contesta a mano con Reset Shape, esa pieza queda PLANA (pierde el relieve).
        Aqui se absorbe el aviso para que la pieza conserve sus puntos de forma.
        """
        def __init__(self):
            pass

        def PreprocessFailures(self, failuresAccessor):
            for f in failuresAccessor.GetFailureMessages():
                try:
                    sev = f.GetSeverity()
                    if sev == DB.FailureSeverity.Warning:
                        failuresAccessor.DeleteWarning(f)
                    elif sev == DB.FailureSeverity.Error:
                        failuresAccessor.ResolveFailure(f)
                except Exception:
                    pass
            return DB.FailureProcessingResult.Continue
    swallower = WarningSwallower()
except Exception:
    swallower = None


# ---------------- 1. puntos, agrupados por (superficie, pieza) ----------------
points_groups = OrderedDict()
with open(points_path, 'r') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if not row or len(row) < 5:
            continue
        key = (row[0], int(row[1]))
        x = float(row[2]) + OFFSET_X
        y = float(row[3]) + OFFSET_Y
        z = float(row[4])
        points_groups.setdefault(key, []).append(XYZ(x, y, z))

# ------------- 2. contornos, por (superficie, pieza, anillo) -------------
ring_groups = OrderedDict()
with open(boundary_path, 'r') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if not row or len(row) < 7:
            continue
        key = (row[0], int(row[1]))
        rtype, rid, seq = row[2], int(row[3]), int(row[4])
        x = float(row[5]) + OFFSET_X
        y = float(row[6]) + OFFSET_Y
        d = ring_groups.setdefault(key, {'OUTER': {}, 'HOLE': {}})
        d[rtype].setdefault(rid, []).append((seq, XYZ(x, y, 0.0)))


def point_to_segment_dist(p, s1, s2):
    x, y = p.X, p.Y
    x1, y1 = s1.X, s1.Y
    x2, y2 = s2.X, s2.Y
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(x - proj_x, y - proj_y)


def min_dist_loop_to_loop(l1, l2):
    min_d = float('inf')
    n1, n2 = len(l1), len(l2)
    for p in l1:
        for j in range(n2):
            d = point_to_segment_dist(p, l2[j], l2[(j + 1) % n2])
            if d < min_d:
                min_d = d
    for p in l2:
        for i in range(n1):
            d = point_to_segment_dist(p, l1[i], l1[(i + 1) % n1])
            if d < min_d:
                min_d = d
    return min_d


def clean_loop_pts(seq_pts):
    import math
    pts = [p for _, p in sorted(seq_pts, key=lambda t: t[0])]
    if len(pts) < 3:
        return None

    # 1. Distancia inicial
    cleaned = [pts[0]]
    for p in pts[1:]:
        if cleaned[-1].DistanceTo(p) >= MIN_SEG_LEN:
            cleaned.append(p)
    while len(cleaned) > 1 and cleaned[0].DistanceTo(cleaned[-1]) < MIN_SEG_LEN:
        cleaned.pop()
    if len(cleaned) < 3:
        return None

    # 2. Pliegues (foldbacks >= 170 deg)
    changed = True
    while changed and len(cleaned) >= 3:
        changed = False
        n = len(cleaned)
        to_remove = set()
        for i in range(n):
            p1 = cleaned[i]
            p2 = cleaned[(i + 1) % n]
            p3 = cleaned[(i + 2) % n]
            v1_x, v1_y = p2.X - p1.X, p2.Y - p1.Y
            v2_x, v2_y = p3.X - p2.X, p3.Y - p2.Y
            len1 = math.hypot(v1_x, v1_y)
            len2 = math.hypot(v2_x, v2_y)
            if len1 < 0.01 or len2 < 0.01:
                to_remove.add((i + 1) % n)
                changed = True
                break
            dot = (v1_x * v2_x + v1_y * v2_y) / (len1 * len2)
            dot = max(-1.0, min(1.0, dot))
            angle = math.degrees(math.acos(dot))
            if angle >= 170.0:
                to_remove.add((i + 1) % n)
                changed = True
                break
        if changed:
            cleaned = [p for idx, p in enumerate(cleaned) if idx not in to_remove]

    # 3. Micro-segmentos residuales (< 0.01 ft)
    changed = True
    while changed and len(cleaned) >= 3:
        changed = False
        n = len(cleaned)
        for i in range(n):
            p1 = cleaned[i]
            p2 = cleaned[(i + 1) % n]
            if p1.DistanceTo(p2) < 0.01:
                cleaned.pop((i + 1) % n)
                changed = True
                break

    if len(cleaned) < 3:
        return None
    return cleaned


def build_loop_from_pts(cleaned):
    if not cleaned or len(cleaned) < 3:
        return None
    loop = CurveLoop()
    n = len(cleaned)
    for i in range(n):
        loop.Append(Line.CreateBound(cleaned[i], cleaned[(i + 1) % n]))
    return loop


def build_loop(seq_pts):
    pts = clean_loop_pts(seq_pts)
    return build_loop_from_pts(pts)


def nombre_de(t):
    """Nombre de un ElementType sin depender de Element.Name (varia segun motor)."""
    p = t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
    return p.AsString() if p else ''


# ---------------- 3. tipo de Toposolid con el espesor del proyecto ------------
t_type = DB.Transaction(doc, "Preparar Tipo Toposolid")
t_type.Start()
default_type_id = DB.ElementId.InvalidElementId
tipo_usado = ''

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
            cs = nuevo.GetCompoundStructure()
            i = cs.LayerCount - 1
            while cs.LayerCount > 1 and i >= 0:
                try:
                    cs.DeleteLayer(i)
                except Exception:
                    pass
                i -= 1
            cs.SetLayerWidth(0, ESPESOR_FT)
            try:
                cs.SetVariableLayer(-1)   # -1 = espesor constante
            except Exception:
                pass
            nuevo.SetCompoundStructure(cs)
            default_type_id = nuevo.Id
            tipo_usado = '%s (creado, %.4f ft, %d capa/s)' % (
                NOMBRE_TIPO, ESPESOR_FT, cs.LayerCount)
        except Exception as ex:
            try:
                cs2 = DB.CompoundStructure.CreateSingleLayerCompoundStructure(
                    DB.MaterialFunctionAssignment.Structure, ESPESOR_FT,
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
t_type.Commit()

level = DB.FilteredElementCollector(doc).OfClass(DB.Level).FirstElement()
level_id = level.Id if level is not None else DB.ElementId.InvalidElementId

# --------- 4. reanudacion: que Toposolid hay ya en el modelo ---------
existentes_labels = set()
for topo in DB.FilteredElementCollector(doc).OfClass(DB.Toposolid):
    p = topo.LookupParameter("Comments")
    if p and p.HasValue and p.AsString():
        existentes_labels.add(p.AsString())

created = []
omitidas_ya_existian = []
errores = []
huecos_omitidos = []


def guardar_documento():
    """Guarda solo si el documento ya tiene ruta, o si SAVE_FILE_PATH esta puesto.
    Nunca inventa un destino: escribir un .rvt donde el usuario no lo espera es
    peor que no guardar."""
    try:
        if not doc.IsModified:
            return "Sin cambios"
        if doc.PathName and not doc.IsDetached and not doc.IsWorkshared:
            doc.Save()
            return "Guardado (Save)"
        if SAVE_FILE_PATH:
            opts = DB.SaveAsOptions()
            opts.OverwriteExistingFile = True
            doc.SaveAs(SAVE_FILE_PATH, opts)
            return "Guardado (SaveAs)"
        return "No guardado: el documento no tiene ruta y SAVE_FILE_PATH esta vacio"
    except Exception as ex_s:
        return "Info guardado: " + str(ex_s)


# --------- 5. creacion pieza a pieza, cada una en su transaccion ---------
for key in ring_groups:
    surf_name, piece_id = key
    n_piezas = len([k for k in ring_groups if k[0] == surf_name])
    label = surf_name if (piece_id == 0 and n_piezas == 1) else "%s - %d" % (surf_name, piece_id + 1)

    if label in existentes_labels:
        omitidas_ya_existian.append(label)
        continue

    t_piece = DB.Transaction(doc, "Crear Toposolid - " + label)
    t_piece.Start()
    if swallower is not None:
        try:
            opts = t_piece.GetFailureHandlingOptions()
            opts.SetFailuresPreprocessor(swallower)
            t_piece.SetFailureHandlingOptions(opts)
        except Exception:
            pass

    try:
        rings = ring_groups[key]
        if 'OUTER' not in rings or 0 not in rings['OUTER']:
            errores.append((label, "sin anillo OUTER"))
            t_piece.RollBack()
            continue

        outer_pts = clean_loop_pts(rings['OUTER'][0])
        if outer_pts is None:
            errores.append((label, "anillo exterior degenerado tras limpieza"))
            t_piece.RollBack()
            continue

        outer = build_loop_from_pts(outer_pts)
        profiles = List[CurveLoop]()
        profiles.Add(outer)

        n_holes = 0
        for rid in sorted(rings.get('HOLE', {}).keys()):
            h_pts = clean_loop_pts(rings['HOLE'][rid])
            if h_pts is None:
                huecos_omitidos.append((label, "%s (degenerado)" % rid))
                continue
            d_out = min_dist_loop_to_loop(h_pts, outer_pts)
            if d_out < 0.05:
                huecos_omitidos.append((label, "%s (toca borde exterior dist=%.4fft)" % (rid, d_out)))
                continue
            hl = build_loop_from_pts(h_pts)
            if hl is not None:
                profiles.Add(hl)
                n_holes += 1

        interior_pts = List[XYZ](points_groups.get(key, []))
        topo = DB.Toposolid.Create(doc, profiles, interior_pts,
                                   default_type_id, level_id)

        p = topo.LookupParameter("Comments")
        if p and not p.IsReadOnly:
            p.Set(label)

        t_piece.Commit()
        created.append((label, n_holes, len(interior_pts), topo.Id, key))

        if GUARDAR_INCREMENTAL:
            guardar_documento()

    except Exception as ex:
        if t_piece.HasStarted() and not t_piece.HasEnded():
            t_piece.RollBack()
        errores.append((label, str(ex)))

final_save_status = guardar_documento()

# --------- 6. autodiagnostico: que piezas perdieron el relieve ---------
relieve_esperado = {}
for k, lista in points_groups.items():
    if lista:
        zs = [q.Z for q in lista]
        relieve_esperado[k] = max(zs) - min(zs)
    else:
        relieve_esperado[k] = 0.0

planas, revisadas = [], []
for label, nh, npts, eid, key in created:
    try:
        el = doc.GetElement(eid)
        if el is None or not getattr(el, 'IsValidObject', True):
            continue
        bb = el.get_BoundingBox(None)
        if bb is None:
            continue
        real = max(0.0, (bb.Max.Z - bb.Min.Z) - ESPESOR_FT)
        esp = relieve_esperado.get(key, 0.0)
        revisadas.append((label, esp, real))
        if esp > 0.10 and real < esp * 0.25:
            planas.append((label, esp, real))
    except Exception:
        pass

# ~/Desktop no existe si el escritorio esta redirigido a OneDrive:
# el log va junto a los CSV, que siempre existen.
log_path = os.path.join(os.path.dirname(points_path), 'dynamo_log.txt')
with open(log_path, 'w') as logf:
    logf.write('SOUTH ISLAND -- TERRENO EXISTENTE (Surface_Exis_SI)\n')
    logf.write('TIPO: {0}\n'.format(tipo_usado))
    logf.write('NIVEL: {0}\n'.format(level.Name if level is not None else 'ninguno'))
    logf.write('OFFSET: X={0} Y={1}\n'.format(OFFSET_X, OFFSET_Y))
    logf.write('ESTADO GUARDADO FINAL: {0}\n\n'.format(final_save_status))

    logf.write('CREADAS EN ESTA SESION ({0}):\n'.format(len(created)))
    for label, nh, npts, eid, key in created:
        logf.write('  OK: {0}  (huecos={1}, puntos={2})\n'.format(label, nh, npts))

    logf.write('\nYA EXISTIAN, OMITIDAS PARA NO DUPLICAR ({0}):\n'.format(
        len(omitidas_ya_existian)))
    for l in omitidas_ya_existian:
        logf.write('  [REANUDADA] {0}\n'.format(l))

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

OUT = (tipo_usado, len(created), len(omitidas_ya_existian), len(planas),
       errores, huecos_omitidos, final_save_status)
