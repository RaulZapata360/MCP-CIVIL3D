# -*- coding: utf-8 -*-
# ============================================================================
#  dynamo_diagnostico_vs_toposolid.py
#  Comprueba, contra la geometria SOLIDA REAL del Toposolid ya en Revit (no
#  una aproximacion externa), si alguna pieza colocada por esta skill queda
#  con su cara superior por debajo de la superficie del terreno -- lo que la
#  hace invisible o parcialmente tapada (z-fighting) sin importar el
#  material o el estilo de vista.
#
#  Solo lectura -- no modifica nada. Correr esto SIEMPRE antes de
#  dynamo_corregir_enterrado_toposolid.py, para tener un numero real de
#  cuantas piezas hacen falta corregir en vez de adivinar.
#
#  ENTRADA: ninguna (lee el documento activo).
#
#  HISTORIA -- por que la prueba es la que es (South Island, HRCP):
#  1) La primera version uso ReferenceIntersector (el mismo mecanismo que
#     usa Revit para "que hay debajo del cursor"), disparando un rayo desde
#     una View3D elegida al azar. Fallo el 100% de las piezas -- la vista
#     resulto ser el problema (visibilidad/crop box/categoria), no un
#     hallazgo real. Se abandono: depender de UNA vista es fragil.
#  2) Se cambio a Solid.IntersectWithCurve() sobre la geometria REAL de cada
#     Toposolid -- geometria pura, no depende de ninguna vista.
#  3) La condicion de "enterrado" NO debe exigir que el punto este DENTRO
#     del espesor del solido (z_bajo <= p.Z <= z_alto). Una pieza puede
#     estar por debajo de TODO el espesor de la losa (mas abajo que
#     z_bajo) -- se ve "desde abajo" del terreno, tapada igual, pero
#     tecnicamente no esta "adentro" del rango. Lo unico que importa es la
#     cara SUPERIOR: cualquier punto por debajo de z_top necesita subir.
# ============================================================================
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
import Autodesk.Revit.DB as DB
from Autodesk.Revit.DB import XYZ, Line
from RevitServices.Persistence import DocumentManager

import os

doc = DocumentManager.Instance.CurrentDBDocument

# ============================================================================
#  CONFIGURACION -- AJUSTAR PARA CADA PROYECTO
# ============================================================================
PREFIJOS_COMMENTS = ['PM_']   # prefijos del parametro Comments que identifican
                               # las piezas a comprobar (ver PREFIJO_COMMENTS en
                               # dynamo_colocar_familias_marcas.py /
                               # dynamo_directshape_desde_malla.py). Puede
                               # llevar varios, p.ej. ['PM_ARR ', 'PM_LINE ']
CLASES_A_BUSCAR = ['DirectShape', 'FamilyInstance']   # 'DirectShape', 'FamilyInstance', o ambos
CATEGORIA_TOPOSOLID = DB.BuiltInCategory.OST_Toposolid
RUTA_LOG = None   # None = junto a este script; o una ruta absoluta a .txt
# ============================================================================

MEDIA_ALTURA = 5.0       # ft -- medio largo del segmento vertical de prueba,
                          # centrado en cada punto. Debe ser mayor que el
                          # peor desnivel esperado entre pieza y Toposolid.
TOLERANCIA = 0.02        # ft -- margen de elevacion que ya llevan las piezas
MARGEN_BBOX = 0.5        # ft -- holgura de la caja XY de cada Toposolid antes
                          # de probar la interseccion cara (descarta rapido
                          # los Toposolid que ni de lejos corresponden)
RESOLUCION_GRILLA = 0.1  # ft -- deduplica vertices casi pegados de la malla
PASOS_GRILLA_UV = 10     # subdivisiones por cara al evaluarla en su propia UV
AREA_MIN_GRILLA = 0.5    # ft2 -- por debajo de esto no vale la pena la grilla
                          # UV (una malla ya fina, como una cinta triangulada,
                          # no la necesita: sus propios vertices de borde ya
                          # cubren de sobra un triangulo asi de chico)

log = []
errores = []


def leer_comments(e):
    try:
        p = e.LookupParameter('Comments')
        return p.AsString() if (p and p.HasValue) else None
    except Exception:
        return None


def puntos_de(e):
    """TODOS los vertices reales de la geometria ya colocada -- bordes Y
    CARAS grandes evaluadas en su propia cuadricula UV.

    Face.Triangulate() NO sirve para cubrir el interior de una cara PLANA:
    matematicamente le alcanza con 2 triangulos usando solo las 4 esquinas,
    asi que Revit no agrega ningun punto interior sin importar el nivel de
    detalle pedido. Esto es invisible mientras se prueba con mallas ya finas
    (una cinta triangulada), pero revienta con extrusiones B-rep simples de
    pocas caras grandes (una flecha, una barra rectangular): su unico
    vertice esta en el contorno, y un bulto del Toposolid justo debajo del
    interior de la cara queda invisible para la prueba aunque la pieza
    entera este casi tocando el terreno ahi. Por eso se evalua la cara
    directamente en su dominio UV (GetBoundingBox / IsInside / Evaluate),
    que fuerza densidad real sin importar si la cara es plana o curva."""
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
    # deduplicar por celda XY, quedandose con el punto MAS BAJO de cada
    # celda -- el caso mas desfavorable para enterramiento, y sin esto una
    # malla fina mete cientos de vertices casi pegados sin aportar nada
    # nuevo entre si (costoso: cada punto paga una interseccion de solido).
    mas_bajo_por_celda = {}
    for p in pts:
        clave = (round(p.X / RESOLUCION_GRILLA), round(p.Y / RESOLUCION_GRILLA))
        actual = mas_bajo_por_celda.get(clave)
        if actual is None or p.Z < actual.Z:
            mas_bajo_por_celda[clave] = p
    return list(mas_bajo_por_celda.values())


def bbox_xy_de(solido):
    """Caja XY del solido, calculada a mano con Edge.Tessellate() (sirve
    igual para bordes rectos que curvos) -- no asumir un metodo de bounding
    box directo sobre Solid sin comprobarlo antes."""
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
    """Devuelve cuanto Toposolid queda por ENCIMA de la cara superior del
    peor punto (None si ninguno esta por debajo). Solo importa z_top -- NO
    exigir que el punto este entre z_bajo y z_top: una pieza puede estar por
    debajo de TODO el espesor de la losa (mas abajo que z_bajo) y seguir
    tapada igual, aunque tecnicamente no este "adentro" del rango."""
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
    raise Exception('no encontre ningun solido de Toposolid en el documento -- '
                    'revisar categoria/fase/nivel antes de continuar')

opts_curva = DB.SolidCurveIntersectionOptions()
opts_curva.ResultType = DB.SolidCurveIntersectionMode.CurveSegmentsInside

piezas = []
for nombre_clase in CLASES_A_BUSCAR:
    clase = CLASE_POR_NOMBRE.get(nombre_clase)
    if clase is None:
        continue
    for e in DB.FilteredElementCollector(doc).OfClass(clase):
        v = leer_comments(e)
        if v and any(v.startswith(p) for p in PREFIJOS_COMMENTS):
            piezas.append(e)
log.append('piezas candidatas: %d' % len(piezas))

resultados = []
for e in piezas:
    v = leer_comments(e)
    try:
        pts = puntos_de(e)
        if not pts:
            errores.append((v, 'sin puntos de geometria para muestrear'))
            continue
        dz = peor_enterramiento(pts, topo_solidos, opts_curva)
        resultados.append((v, dz if dz is not None else 0.0))
    except Exception as ex:
        errores.append((v, str(ex)))

enterradas = [r for r in resultados if r[1] > TOLERANCIA]
enterradas.sort(key=lambda r: -r[1])

ruta_log = RUTA_LOG or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'dynamo_log_diagnostico_toposolid.txt')
with open(ruta_log, 'w') as fh:
    fh.write('DIAGNOSTICO vs TOPOSOLID (geometria solida real, sin depender de ninguna vista)\n')
    fh.write('=' * 74 + '\n\n')
    for l in log:
        fh.write(l + '\n')
    fh.write('\npiezas comprobadas: %d   con error: %d\n\n' % (len(resultados), len(errores)))
    fh.write('ENTERRADAS (cara superior del Toposolid por encima de la pieza), '
             'tolerancia %.2f ft:\n' % TOLERANCIA)
    fh.write('%d de %d\n\n' % (len(enterradas), len(resultados)))
    for v, dz in enterradas[:60]:
        fh.write('  %-20s dz=%+.3f ft\n' % (v, dz))
    if len(enterradas) > 60:
        fh.write('  ... y %d mas\n' % (len(enterradas) - 60))
    fh.write('\nERRORES (%d):\n' % len(errores))
    for v, m in errores[:30]:
        fh.write('  %s\n    %s\n' % (v, m))

OUT = (len(resultados), len(enterradas), len(errores), enterradas[:15], ruta_log)
