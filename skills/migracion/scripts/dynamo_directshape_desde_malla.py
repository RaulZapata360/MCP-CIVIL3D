# -*- coding: utf-8 -*-
# ============================================================================
#  dynamo_directshape_desde_malla.py
#  Crea en Revit un DirectShape por cada marca de un <capa>_mesh.json
#  generado por exportar_marcas_pavimento.py. Sirve tanto para laminas
#  drapeadas (pintura, ya solidificadas con espesor) como para objetos 3D
#  que YA venian solidos en el DXF (barreras, mobiliario, senales -- el
#  exportador los detecta y los deja pasar sin duplicar).
#
#  ENTRADA (nodo File Path del grafo):
#    IN[0]: <capa>_mesh.json
#
#  ANTES DE USAR ESTE SCRIPT: correr dynamo_diagnostico_firmas_revit.py una
#  vez y comparar sus firmas con las que usa este archivo.
# ============================================================================
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
clr.AddReference('System')
import Autodesk.Revit.DB as DB
from Autodesk.Revit.DB import XYZ, Transaction, ElementId
from RevitServices.Persistence import DocumentManager
from System.Collections.Generic import List

import json, os, time

doc = DocumentManager.Instance.CurrentDBDocument
mesh_json = IN[0]

# ============================================================================
#  CONFIGURACION -- AJUSTAR PARA CADA PROYECTO
# ============================================================================
OFFSET_X = 0.0    # ft -- ver dynamo_colocar_familias_marcas.py, misma logica.
OFFSET_Y = 0.0    #       Debe ser EL MISMO offset que uses en el resto de
                  #       capas de este mismo proyecto, o las piezas quedan
                  #       desplazadas unas respecto a otras.
ELEVACION = 0.0   # ft -- 0.02 tipico para pintura sobre pavimento (evita
                  #       z-fighting); 0.0 para objetos que ya se apoyan solos
                  #       en su cota real (barreras, mobiliario).

NOMBRE_MATERIAL = None    # p.ej. 'Marca Vial - Blanco'. None = sin material.
COLOR_RGB = (200, 200, 200)   # solo si NOMBRE_MATERIAL y hay que crearlo
PREFIJO_COMMENTS = 'PM'   # etiqueta en el parametro Comments de cada pieza,
                          # para poder identificarlas y para que la limpieza
                          # de una pasada anterior no borre OTRAS capas
# ============================================================================

log = []
errores = []


def material_id(nombre, rgb):
    if not nombre:
        return ElementId.InvalidElementId
    try:
        for m in DB.FilteredElementCollector(doc).OfClass(DB.Material):
            if m.Name == nombre:
                return m.Id
        mid = DB.Material.Create(doc, nombre)
        mat = doc.GetElement(mid)
        mat.Color = DB.Color(*rgb)
        return mid
    except Exception as ex:
        log.append('AVISO: sin material "%s" (%s)' % (nombre, ex))
        return ElementId.InvalidElementId


def construir(marca, mat_id):
    """Malla (V,F) -> GeometryObject para DirectShape."""
    V = marca['v']
    b = DB.TessellatedShapeBuilder()
    b.OpenConnectedFaceSet(False)
    for (i, j, k) in marca['f']:
        lazo = List[XYZ]()
        for idx in (i, j, k):
            x, y, z = V[idx]
            lazo.Add(XYZ(x + OFFSET_X, y + OFFSET_Y, z + ELEVACION))
        b.AddFace(DB.TessellatedFace(lazo, mat_id))
    b.CloseConnectedFaceSet()
    # AnyGeometry + repliegue a Mesh: si la malla tiene alguna arista
    # compartida por mas de 2 caras (una cinta que se toca a si misma, tipico
    # en pintura con trazos que se cruzan) o cualquier otra imperfeccion,
    # Target=Solid puro falla en bloque. Con este ajuste, lo que puede ser
    # solido sale solido y el resto sale como malla, en vez de perder la
    # pieza entera.
    b.Target = DB.TessellatedShapeBuilderTarget.AnyGeometry
    b.Fallback = DB.TessellatedShapeBuilderFallback.Mesh
    b.GraphicsStyleId = ElementId.InvalidElementId
    b.Build()
    return b.GetBuildResult().GetGeometricalObjects()


def limpiar_anterior(capa):
    viejos = []
    for e in DB.FilteredElementCollector(doc).OfClass(DB.DirectShape):
        p = e.LookupParameter('Comments')
        try:
            v = p.AsString() if (p and p.HasValue) else None
        except Exception:
            v = None
        if v and v.startswith('%s_%s ' % (PREFIJO_COMMENTS, capa)):
            viejos.append(e.Id)
    if not viejos:
        return
    t = Transaction(doc, 'Limpiar marcas de la pasada anterior')
    t.Start()
    for i in viejos:
        try:
            doc.Delete(i)
        except Exception:
            pass
    t.Commit()
    log.append('limpieza previa: %d DirectShape' % len(viejos))


# ---------------------------------------------------------------------------
t0 = time.time()
with open(mesh_json, 'r') as fh:
    datos = json.load(fh)
marcas = datos['marcas']
capa = marcas[0]['capa'] if marcas else 'SinCapa'
log.append('JSON: %d marcas, espesor %s ft, capa "%s"' % (datos['n'], datos.get('espesor_ft'), capa))

limpiar_anterior(capa)

t = Transaction(doc, 'Material')
t.Start()
mat_id = material_id(NOMBRE_MATERIAL, COLOR_RGB)
t.Commit()

cat = ElementId(DB.BuiltInCategory.OST_GenericModel)
creadas, solidos, mallas, vacias = 0, 0, 0, []

for m in marcas:
    t = Transaction(doc, 'Marca %s %s' % (capa, m['id']))
    t.Start()
    try:
        geo = construir(m, mat_id)
        n_geo = geo.Count if hasattr(geo, 'Count') else len(geo)
        if n_geo == 0:
            vacias.append(m['id'])
            t.RollBack()
            continue
        ds = DB.DirectShape.CreateElement(doc, cat)
        ds.SetShape(geo)
        ds.Name = '%s %s' % (capa, m['id'])
        p = ds.LookupParameter('Comments')
        if p and not p.IsReadOnly:
            p.Set('%s_%s %s' % (PREFIJO_COMMENTS, capa, m['id']))
        t.Commit()
        creadas += 1
        try:
            if any(isinstance(g, DB.Solid) for g in geo):
                solidos += 1
            else:
                mallas += 1
        except Exception:
            pass
    except Exception as ex:
        if t.HasStarted() and not t.HasEnded():
            t.RollBack()
        errores.append((m['id'], str(ex)))

# Verificacion leyendo el modelo de vuelta -- no fiarse de que "no salto nada".
con_geo = 0
for e in DB.FilteredElementCollector(doc).OfClass(DB.DirectShape):
    p = e.LookupParameter('Comments')
    try:
        v = p.AsString() if (p and p.HasValue) else None
    except Exception:
        v = None
    if v and v.startswith('%s_%s ' % (PREFIJO_COMMENTS, capa)):
        try:
            g = e.get_Geometry(DB.Options())
            if g is not None and len([x for x in g]) > 0:
                con_geo += 1
        except Exception:
            pass

ruta_log = os.path.join(os.path.dirname(mesh_json), 'dynamo_log_%s.txt' % capa)
with open(ruta_log, 'w') as fh:
    fh.write('MARCAS DE PAVIMENTACION / OBJETOS 3D -- %s (DirectShape)\n' % capa)
    fh.write('OFFSET X=%s Y=%s   elevacion=%s ft\n\n' % (OFFSET_X, OFFSET_Y, ELEVACION))
    for l in log:
        fh.write(l + '\n')
    fh.write('\nCREADAS: %d de %d\n' % (creadas, len(marcas)))
    fh.write('  como solido: %d   como malla: %d\n' % (solidos, mallas))
    fh.write('  con geometria verificada en el modelo: %d\n' % con_geo)
    if vacias:
        fh.write('  sin geometria (el constructor no devolvio nada): %s\n' % vacias[:20])
    fh.write('\nERRORES (%d):\n' % len(errores))
    for i, msg in errores[:30]:
        fh.write('  marca %s\n    %s\n' % (i, msg))
    fh.write('\ntiempo: %.0f s\n' % (time.time() - t0))

OUT = (creadas, solidos, mallas, con_geo, len(errores), errores[:5], ruta_log)
