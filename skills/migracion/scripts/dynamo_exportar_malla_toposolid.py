# -*- coding: utf-8 -*-
# ============================================================================
#  dynamo_exportar_malla_toposolid.py
#  Extrae la triangulacion REAL de la cara superior de los Toposolid del
#  proyecto y la escribe a un JSON. Solo lectura -- no modifica nada.
#
#  PARA QUE SIRVE
#  Es el paso 1 de 3 para apoyar piezas ya colocadas (marcas viales, mobiliario,
#  lo que sea) sobre el terreno real de Revit:
#     1. este script (en Dynamo)   -> Toposolid_Malla.json
#     2. conformar_piezas_a_terreno.py (Python normal, FUERA de Revit)
#     3. dynamo_directshape_desde_malla.py con ELEVACION = 0.0
#
#  POR QUE NO SE CONSULTA LA ALTURA DIRECTAMENTE EN REVIT
#  Preguntar la cota del terreno con Solid.IntersectWithCurve() por cada
#  vertice parece lo natural, pero cada llamada es una interseccion booleana
#  B-rep completa -- del orden de MILISEGUNDOS. Medido en South Island: 109.730
#  vertices x ~10 ms = mas de 18 minutos, y Dynamo se colgaba. Filtrar
#  candidatos por caja o agrupar vertices reduce el NUMERO de llamadas pero no
#  el costo unitario, que es el problema de fondo.
#
#  La solucion es invertir el planteo: se le hace UNA sola pregunta cara a
#  Revit ("dame la triangulacion") y las N consultas de altura se resuelven
#  despues fuera, con interpolacion baricentrica -- microsegundos cada una.
#  Extraer triangulos es barato: son ACCESOS a geometria ya calculada, no
#  operaciones booleanas. En South Island: 34.039 triangulos en 1,5 s.
#
#  CADA TOPOSOLID SE GUARDA POR SEPARADO a proposito: las piezas se solapan en
#  planta, y fusionar sus triangulos daria solapes con interpolacion sin
#  sentido. La altura del terreno en un punto es el MAXIMO entre las piezas que
#  lo cubren.
#
#  ENTRADA: ninguna (lee el documento activo).
# ============================================================================
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
import Autodesk.Revit.DB as DB
from RevitServices.Persistence import DocumentManager

import json, os, time

doc = DocumentManager.Instance.CurrentDBDocument

# ============================================================================
#  CONFIGURACION -- AJUSTAR PARA CADA PROYECTO
# ============================================================================
RUTA_SALIDA = r""      # .json de salida. Vacio = junto a este archivo.
CATEGORIA = DB.BuiltInCategory.OST_Toposolid
DEC = 4                # decimales al soldar vertices. 4 = 0,0001 ft (0,03 mm).
                       # NO bajar a 3: se comprobo en este proyecto que
                       # redondear a 3 descarta caras reales.
AREA_MIN_XY = 1e-9     # ft2 -- descarta triangulos verticales (caras
                       # laterales), que en planta degeneran a un segmento
# ============================================================================

log = []


def firmas():
    """Vuelca las firmas reales antes de usarlas. Convencion del repo: no
    adivinar overloads, comprobarlos en ESTE Revit."""
    for tipo, nombres in ((DB.Face, ('Triangulate',)), (DB.Mesh, ('get_Triangle',))):
        try:
            ct = clr.GetClrType(tipo)
            for m in ct.GetMethods():
                if m.Name in nombres:
                    log.append('  %s.%s(%s)' % (tipo.__name__, m.Name, ', '.join(
                        p.ParameterType.Name for p in m.GetParameters())))
        except Exception as ex:
            log.append('  AVISO: no pude reflexionar %s (%s)' % (tipo.__name__, ex))


def triangular(face):
    """Triangulacion mas fina que ofrezca esta version."""
    try:
        return face.Triangulate(1.0)
    except Exception:
        try:
            return face.Triangulate()
        except Exception:
            return None


t0 = time.time()
log.append('=== firmas reales en este Revit ===')
firmas()
log.append('')

opts = DB.Options()
opts.DetailLevel = DB.ViewDetailLevel.Fine

piezas = []
tot_caras = tot_crudos = tot_guardados = 0
desc_vertical = desc_abajo = 0

for e in DB.FilteredElementCollector(doc).OfCategory(CATEGORIA) \
                                          .WhereElementIsNotElementType():
    geo = e.get_Geometry(opts)
    if geo is None:
        continue
    verts, lista_v, tris = {}, [], []
    for g in geo:
        objetos = list(g.GetInstanceGeometry()) if isinstance(g, DB.GeometryInstance) else [g]
        for g2 in objetos:
            if not (isinstance(g2, DB.Solid) and g2.Volume > 0):
                continue
            for face in g2.Faces:
                tot_caras += 1
                malla = triangular(face)
                if malla is None:
                    continue
                n = malla.NumTriangles
                tot_crudos += n
                for i in range(n):
                    tri = malla.get_Triangle(i)
                    p0, p1, p2 = tri.get_Vertex(0), tri.get_Vertex(1), tri.get_Vertex(2)
                    # Normal del PROPIO triangulo, calculada aqui (sin interop):
                    # descarta caras inferiores y laterales sin depender de
                    # ComputeNormal ni de que la UV del centro caiga dentro de
                    # la region recortada de la cara.
                    cruz_z = ((p1.X - p0.X) * (p2.Y - p0.Y) -
                              (p1.Y - p0.Y) * (p2.X - p0.X))
                    if abs(cruz_z) < AREA_MIN_XY:
                        desc_vertical += 1
                        continue
                    if cruz_z < 0:
                        desc_abajo += 1
                        continue
                    idx = []
                    for p in (p0, p1, p2):
                        clave = (round(p.X, DEC), round(p.Y, DEC), round(p.Z, DEC))
                        j = verts.get(clave)
                        if j is None:
                            j = len(lista_v)
                            verts[clave] = j
                            lista_v.append([clave[0], clave[1], clave[2]])
                        idx.append(j)
                    if len(set(idx)) < 3:
                        continue
                    tris.append(idx)
                    tot_guardados += 1
    if tris:
        piezas.append({'id': e.Id.IntegerValue, 'v': lista_v, 't': tris})
        log.append('Toposolid %-10s %6d vertices %7d triangulos' % (e.Id, len(lista_v), len(tris)))

if not piezas:
    raise Exception('no se extrajo ningun triangulo -- revisar la categoria y que el '
                    'documento correcto este abierto')

base = RUTA_SALIDA or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'Toposolid_Malla.json')
with open(base, 'w') as fh:
    json.dump({'n': len(piezas),
               'unidades': 'ft, coordenadas de PROYECTO',
               'piezas': piezas}, fh)

ruta_log = os.path.splitext(base)[0] + '_log.txt'
with open(ruta_log, 'w') as fh:
    fh.write('EXPORTAR MALLA DEL TOPOSOLID (para calcular fuera de Revit)\n')
    fh.write('=' * 62 + '\n\n')
    for l in log:
        fh.write(l + '\n')
    fh.write('\nRESUMEN\n')
    fh.write('  piezas ..................... %d\n' % len(piezas))
    fh.write('  caras recorridas ........... %d\n' % tot_caras)
    fh.write('  triangulos crudos .......... %d\n' % tot_crudos)
    fh.write('  descartados por verticales . %d\n' % desc_vertical)
    fh.write('  descartados por mirar abajo  %d\n' % desc_abajo)
    fh.write('  triangulos guardados ....... %d\n' % tot_guardados)
    fh.write('\n  COMPROBACION: en una losa, "guardados" y "descartados por mirar\n')
    fh.write('  abajo" deben ser CASI IGUALES (la cara inferior refleja a la\n')
    fh.write('  superior). Si difieren mucho, el filtro de normal esta fallando.\n')
    fh.write('\n  archivo: %s (%.1f MB)\n' % (base, os.path.getsize(base) / 1e6))
    fh.write('\ntiempo: %.1f s\n' % (time.time() - t0))

OUT = (len(piezas), tot_guardados, base, ruta_log)
