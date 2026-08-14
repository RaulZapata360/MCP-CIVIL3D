# -*- coding: utf-8 -*-
# ============================================================================
#  dynamo_corregir_enterrado_toposolid.py
#  Sube en Z, sobre el propio elemento ya colocado (sin borrar ni recrear
#  nada), las piezas que dynamo_diagnostico_vs_toposolid.py encontro con su
#  cara superior por debajo de la superficie real del Toposolid.
#
#  Corre SIEMPRE dynamo_diagnostico_vs_toposolid.py primero -- no por
#  cortesia, sino porque este script recalcula la misma prueba en vivo (no
#  reusa ningun log) y el diagnostico es lo que te dice si hace falta
#  correr esto para empezar.
#
#  Por pieza: mide -> si esta enterrada, sube la distancia exacta que hace
#  falta + un margen -> vuelve a medir con la geometria YA trasladada
#  (doc.Regenerate() DENTRO de la transaccion abierta, valido aqui) -> repite
#  hasta MAX_INTENTOS o hasta que quede limpia. Termina con una verificacion
#  en frio (transaccion ya cerrada) para confirmar de verdad, no solo porque
#  MoveElement no lanzo excepcion.
#
#  Idempotente: correrlo dos veces no mueve nada la segunda vez.
#
#  ENTRADA: ninguna (lee y modifica el documento activo).
#
#  HISTORIA -- nueve iteraciones en la migracion original (South Island,
#  HRCP) antes de que esto funcionara de verdad en las 322 piezas del
#  paquete. En orden:
#  1) Un solo muestreo de 8 puntos por pieza -- corrigio 30 de 31 pero dejo
#     una con 0.05 ft de residuo: el peor de 8 puntos no siempre es el peor
#     punto real en una pieza con relieve no uniforme.
#  2) 40 puntos -- encontro 9 enterramientos NUEVOS que ni el primer
#     diagnostico habia visto. Cualquier numero fijo de muestras puede
#     seguir dejando un bulto sin tocar entre dos puntos consecutivos.
#  3) TODOS los vertices de la geometria, sin recortar -- correcto pero tan
#     lento que Dynamo tardaba mas de 15 minutos sin terminar.
#  4) Prefiltro de caja XY por Toposolid (cada punto solo se prueba contra
#     1-2 de los N Toposolid, no contra todos) + deduplicar vertices casi
#     pegados por celda de 0.1 ft, quedandose con el mas bajo de cada celda
#     -- rapido otra vez, sin perder cobertura real.
#  5) Se amplio el alcance a piezas de tipo FamilyInstance (ancladas a su
#     nivel), no solo DirectShape -- moverlas puede disparar avisos de Revit
#     que un dialogo modal (Dynamo se queda "no responde" esperando un OK
#     que nunca llega porque no puede verlo). Se probo envolver la
#     transaccion en un IFailuresPreprocessor (WarningSwallower) para
#     autorresolverlos -- en Python.NET/CPython esa interfaz NO se pudo
#     implementar ("interface takes exactly one argument"), mismo limite
#     que con IFamilyLoadOptions en otras skills. El codigo lo intenta
#     igual (no hace dano si falla) pero NO ASUMIR que protege de verdad.
#  6) Con piezas B-rep simples (una flecha, una barra) el z-fighting seguia
#     visible en Revit pese a "0 enterradas": Solid.Edges solo da los
#     vertices del CONTORNO, y una cara ancha (el asta de una flecha) no
#     tiene ningun vertice propio en el interior. Se probo
#     Face.Triangulate() para cubrir el interior -- SIGUE SIN SERVIR en
#     caras PLANAS: matematicamente 2 triangulos ya representan un
#     rectangulo exacto, asi que Revit no agrega puntos interiores sin
#     importar el nivel de detalle pedido. El fix real: evaluar la cara en
#     su propia cuadricula UV (GetBoundingBox / IsInside / Evaluate), que
#     fuerza densidad real sin depender de que la triangulacion "decida"
#     que no hace falta mas.
#  7) Con eso, dos piezas SEGUIAN sin detectarse -- se veian "desde abajo"
#     del Toposolid. La condicion vieja exigia z_bajo <= p.Z <= z_top (el
#     punto DENTRO del espesor del solido) -- estas dos piezas estaban por
#     debajo de TODO el espesor de la losa (mas abajo que z_bajo), tapadas
#     igual pero tecnicamente "fuera" del rango exigido. Se corrigio: solo
#     importa la cara superior, sin limite inferior.
#  8) Recorrer las 322 piezas de una con la condicion ya corregida hizo que
#     Revit se CERRARA (no solo "no responde") dos veces seguidas -- mas
#     serio que un cuelgue, probablemente una excepcion nativa del motor de
#     geometria. La salida que funciono: acotar el alcance a las piezas
#     puntuales que hacen falta (ver ELEMENTOS_A_CORREGIR mas abajo) en vez
#     de reprocesar TODO el paquete de una sola pasada larga cada vez que
#     algo cambia. Si algo asi vuelve a pasar, es la primera sospecha.
# ============================================================================
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
import Autodesk.Revit.DB as DB
from Autodesk.Revit.DB import XYZ, Line, Transaction, ElementTransformUtils
from RevitServices.Persistence import DocumentManager

import os

doc = DocumentManager.Instance.CurrentDBDocument

# ============================================================================
#  CONFIGURACION -- AJUSTAR PARA CADA PROYECTO
# ============================================================================
PREFIJOS_COMMENTS = ['PM_']   # igual que en dynamo_diagnostico_vs_toposolid.py
CLASES_A_BUSCAR = ['DirectShape', 'FamilyInstance']
CATEGORIA_TOPOSOLID = DB.BuiltInCategory.OST_Toposolid

# Si el paquete es grande (cientos de piezas) y una pasada completa llega a
# cerrar Revit (ver punto 8 del historial arriba), poner aqui SOLO los IDs
# de Comments que hace falta corregir (los que salieron en el diagnostico) y
# dejar la lista vacia para procesar todo de una. Reprocesar de a pocos es
# mas lento pero mucho mas seguro que arriesgar el paquete completo de nuevo.
ELEMENTOS_A_CORREGIR = []   # ej. ['PM_ARR 197', 'PM_ARR 194'] -- vacio = todas

RUTA_LOG = None   # None = junto a este script; o una ruta absoluta a .txt
# ============================================================================

MEDIA_ALTURA = 5.0
TOLERANCIA = 0.02
MARGEN_SUBIDA = 0.05    # ft de aire extra sobre el Toposolid al subir una pieza
MAX_INTENTOS = 4        # por pieza -- red de seguridad si una subida no alcanza
MARGEN_BBOX = 0.5
RESOLUCION_GRILLA = 0.1
PASOS_GRILLA_UV = 10
AREA_MIN_GRILLA = 0.5

log = []
errores = []

# Se intenta, pero NO se puede asumir que funciona -- ver punto 5 del
# historial. Envuelto en try/except: si esta interfaz no se puede
# implementar en este entorno, el script sigue sin ella en vez de tumbarse
# en la propia definicion de la clase.
swallower = None
try:
    class WarningSwallower(DB.IFailuresPreprocessor):
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
except Exception as ex_sw:
    log.append('AVISO: no se pudo crear WarningSwallower, la transaccion queda sin el (%s)' % ex_sw)


def leer_comments(e):
    try:
        p = e.LookupParameter('Comments')
        return p.AsString() if (p and p.HasValue) else None
    except Exception:
        return None


def puntos_de(e):
    opts = DB.Options()
    opts.DetailLevel = DB.ViewDetailLevel.Fine
    geo = e.get_Geometry(opts)
    pts = []
    for g in geo:
        objetos = list(g.GetInstanceGeometry()) if isinstance(g, DB.GeometryInstance) else [g]
        for g2 in objetos:
            if isinstance(g2, DB.Mesh):
                pts.extend(list(g2.Vertices))
            elif isinstance(g2, DB.Solid) and g2.Volume >= 0:
                for edge in g2.Edges:
                    c = edge.AsCurve()
                    pts.append(c.GetEndPoint(0))
                    pts.append(c.GetEndPoint(1))
                for face in g2.Faces:
                    try:
                        if face.Area < AREA_MIN_GRILLA:
                            continue
                        bbox = face.GetBoundingBox()
                        for iu in range(PASOS_GRILLA_UV + 1):
                            u = bbox.Min.U + (bbox.Max.U - bbox.Min.U) * iu / PASOS_GRILLA_UV
                            for iv in range(PASOS_GRILLA_UV + 1):
                                v = bbox.Min.V + (bbox.Max.V - bbox.Min.V) * iv / PASOS_GRILLA_UV
                                uv = DB.UV(u, v)
                                if face.IsInside(uv):
                                    pts.append(face.Evaluate(uv))
                    except Exception:
                        pass
    mas_bajo_por_celda = {}
    for p in pts:
        clave = (round(p.X / RESOLUCION_GRILLA), round(p.Y / RESOLUCION_GRILLA))
        actual = mas_bajo_por_celda.get(clave)
        if actual is None or p.Z < actual.Z:
            mas_bajo_por_celda[clave] = p
    return list(mas_bajo_por_celda.values())


def bbox_xy_de(solido):
    minx = miny = maxx = maxy = None
    for edge in solido.Edges:
        for p in edge.Tessellate():
            if minx is None or p.X < minx:
                minx = p.X
            if maxx is None or p.X > maxx:
                maxx = p.X
            if miny is None or p.Y < miny:
                miny = p.Y
            if maxy is None or p.Y > maxy:
                maxy = p.Y
    return (minx, maxx, miny, maxy)


def cargar_topo_solidos():
    opts_topo = DB.Options()
    opts_topo.DetailLevel = DB.ViewDetailLevel.Fine
    solidos = []
    for e in DB.FilteredElementCollector(doc).OfCategory(CATEGORIA_TOPOSOLID) \
                                              .WhereElementIsNotElementType():
        geo = e.get_Geometry(opts_topo)
        if geo is None:
            continue
        for g in geo:
            objetos = list(g.GetInstanceGeometry()) if isinstance(g, DB.GeometryInstance) else [g]
            for g2 in objetos:
                if isinstance(g2, DB.Solid) and g2.Volume > 0:
                    solidos.append((g2, bbox_xy_de(g2)))
    return solidos


def peor_enterramiento(pts, topo_solidos, opts_curva):
    peor_dz = None
    for p in pts:
        arriba = XYZ(p.X, p.Y, p.Z + MEDIA_ALTURA)
        abajo = XYZ(p.X, p.Y, p.Z - MEDIA_ALTURA)
        if arriba.DistanceTo(abajo) < 0.001:
            continue
        segmento = Line.CreateBound(arriba, abajo)
        for solido, (minx, maxx, miny, maxy) in topo_solidos:
            if minx is None:
                continue
            if not (minx - MARGEN_BBOX <= p.X <= maxx + MARGEN_BBOX and
                    miny - MARGEN_BBOX <= p.Y <= maxy + MARGEN_BBOX):
                continue
            try:
                interseccion = solido.IntersectWithCurve(segmento, opts_curva)
            except Exception:
                continue
            if interseccion is None or interseccion.SegmentCount == 0:
                continue
            for i in range(interseccion.SegmentCount):
                seg = interseccion.GetCurveSegment(i)
                z0 = seg.GetEndPoint(0).Z
                z1 = seg.GetEndPoint(1).Z
                z_top = max(z0, z1)
                if p.Z < z_top - TOLERANCIA:
                    dz = z_top - p.Z
                    if peor_dz is None or dz > peor_dz:
                        peor_dz = dz
    return peor_dz


CLASE_POR_NOMBRE = {'DirectShape': DB.DirectShape, 'FamilyInstance': DB.FamilyInstance}

topo_solidos = cargar_topo_solidos()
log.append('solidos de Toposolid cargados: %d' % len(topo_solidos))
if not topo_solidos:
    raise Exception('no encontre ningun solido de Toposolid -- nada que corregir')

opts_curva = DB.SolidCurveIntersectionOptions()
opts_curva.ResultType = DB.SolidCurveIntersectionMode.CurveSegmentsInside

piezas = []
for nombre_clase in CLASES_A_BUSCAR:
    clase = CLASE_POR_NOMBRE.get(nombre_clase)
    if clase is None:
        continue
    for e in DB.FilteredElementCollector(doc).OfClass(clase):
        v = leer_comments(e)
        if not v:
            continue
        if ELEMENTOS_A_CORREGIR:
            if v in ELEMENTOS_A_CORREGIR:
                piezas.append(e)
        elif any(v.startswith(p) for p in PREFIJOS_COMMENTS):
            piezas.append(e)
log.append('piezas candidatas: %d%s' % (len(piezas),
           ' (alcance acotado por ELEMENTOS_A_CORREGIR)' if ELEMENTOS_A_CORREGIR else ''))

subidas = []   # (id, dz_inicial, subida_total, intentos)
t = Transaction(doc, 'Subir piezas enterradas en el Toposolid')
t.Start()
if swallower is not None:
    fho = t.GetFailureHandlingOptions()
    fho.SetFailuresPreprocessor(swallower)
    t.SetFailureHandlingOptions(fho)
try:
    for e in piezas:
        v = leer_comments(e)
        try:
            dz_inicial = None
            subida_total = 0.0
            intentos = 0
            while intentos < MAX_INTENTOS:
                pts = puntos_de(e)
                if not pts:
                    errores.append((v, 'sin puntos de geometria para muestrear'))
                    break
                dz = peor_enterramiento(pts, topo_solidos, opts_curva)
                if dz is None or dz <= TOLERANCIA:
                    break
                if dz_inicial is None:
                    dz_inicial = dz
                subida = dz + MARGEN_SUBIDA
                ElementTransformUtils.MoveElement(doc, e.Id, XYZ(0, 0, subida))
                # Transaccion SIGUE ABIERTA aqui -- a diferencia de un
                # Regenerate() fuera de toda transaccion (eso SI tumba el
                # script: "Modification of the document is forbidden...
                # there is no open transaction"). Dentro de una transaccion
                # abierta es valido y hace falta para que la siguiente
                # vuelta del while lea la geometria YA trasladada.
                doc.Regenerate()
                subida_total += subida
                intentos += 1
            if dz_inicial is not None:
                subidas.append((v, dz_inicial, subida_total, intentos))
        except Exception as ex:
            errores.append((v, str(ex)))
    t.Commit()
except Exception as ex_t:
    t.RollBack()
    raise Exception('fallo la transaccion de subida, no se movio nada: %s' % ex_t)

# --- verificacion en frio: transaccion ya cerrada, Commit() ya regenero ----
topo_solidos_2 = cargar_topo_solidos()
siguen_enterradas = []
for e in piezas:
    v = leer_comments(e)
    if v not in [s[0] for s in subidas]:
        continue
    try:
        pts = puntos_de(e)
        dz = peor_enterramiento(pts, topo_solidos_2, opts_curva)
        if dz is not None and dz > TOLERANCIA:
            siguen_enterradas.append((v, dz))
    except Exception as ex:
        errores.append((v + ' (verificacion)', str(ex)))

ruta_log = RUTA_LOG or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'dynamo_log_corregir_enterradas.txt')
with open(ruta_log, 'w') as fh:
    fh.write('CORREGIR PIEZAS ENTERRADAS EN EL TOPOSOLID\n')
    fh.write('=' * 60 + '\n\n')
    for l in log:
        fh.write(l + '\n')
    fh.write('\nSUBIDAS (%d), margen extra %.2f ft por intento (max %d intentos):\n'
             % (len(subidas), MARGEN_SUBIDA, MAX_INTENTOS))
    for v, dz, subida_total, intentos in sorted(subidas, key=lambda r: -r[1]):
        fh.write('  %-20s enterrada %.3f ft -> subida total %.3f ft (%d intento%s)\n'
                 % (v, dz, subida_total, intentos, '' if intentos == 1 else 's'))
    fh.write('\nVERIFICACION EN FRIO: siguen enterradas (%d de %d subidas):\n'
             % (len(siguen_enterradas), len(subidas)))
    if siguen_enterradas:
        for v, dz in siguen_enterradas:
            fh.write('  %-20s todavia dz=%+.3f ft -- REVISAR A MANO\n' % (v, dz))
    else:
        fh.write('  ninguna -- las %d piezas subidas quedaron limpias\n' % len(subidas))
    fh.write('\nERRORES (%d):\n' % len(errores))
    for v, m in errores[:30]:
        fh.write('  %s\n    %s\n' % (v, m))

OUT = (len(subidas), len(siguen_enterradas), len(errores), subidas[:15], ruta_log)
