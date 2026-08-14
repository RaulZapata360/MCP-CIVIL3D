# -*- coding: utf-8 -*-
# ============================================================================
#  dynamo_colocar_familias_marcas.py
#  Coloca en Revit las marcas de una capa exportada como FAMILIA por
#  exportar_marcas_pavimento.py. Sirve para los dos casos:
#
#    ES_PARAMETRICA = False  ->  "mismo simbolo, muchas rotaciones" (ej. una
#         flecha). El script CONSTRUYE la familia el mismo desde CONTORNO
#         (pegar el contenido de <capa>_contorno_paste.txt aqui abajo).
#
#    ES_PARAMETRICA = True   ->  "un rectangulo, muchos tamanos" (ej. lineas
#         de detencion). La familia YA debe existir en el proyecto, creada a
#         mano en el Editor de familias: rectangulo centrado en el origen,
#         largo segun +X, con DOS PARAMETROS DE INSTANCIA de tipo Longitud
#         (los nombres exactos van en NOMBRE_PARAM_LARGO/ANCHO mas abajo).
#         El script solo coloca instancias y les fija esos dos valores.
#
#  ENTRADA (nodo File Path del grafo):
#    IN[0]: <capa>_instancias.csv  (columnas: Id,X,Y,Z,AngDeg,PendPct,
#           PendDirDeg,AreaFt2,ErrPlanoFt,LargoFt,AnchoFt,DzFt)
#
#  ANTES DE USAR ESTE SCRIPT: correr dynamo_diagnostico_firmas_revit.py una
#  vez y comparar sus firmas con las que usa este archivo. No adivinar
#  overloads del API de Revit.
# ============================================================================
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
import Autodesk.Revit.DB as DB
from Autodesk.Revit.DB import XYZ, Line, Transaction
from RevitServices.Persistence import DocumentManager
# StructuralType se referencia como DB.Structure.StructuralType. En CPython
# (Python.NET) el "from ...DB.Structure import StructuralType" puede fallar si
# ese subespacio de nombres aun no esta resuelto, y no aporta nada.

import csv, math, os, tempfile

doc = DocumentManager.Instance.CurrentDBDocument
app = doc.Application

csv_path = IN[0]

# ============================================================================
#  CONFIGURACION -- AJUSTAR PARA CADA PROYECTO
# ============================================================================
OFFSET_X = 0.0    # ft -- si esta capa debe acoplarse a un modelo de Revit
OFFSET_Y = 0.0    # ft    existente, medir estos dos valores como en
                  #       civil3d-to-revit-toposolid.skill.md seccion 4
                  #       (3 vertices de control, dX/dY deben salir iguales
                  #       en los 3). Si el modelo se georreferencia con
                  #       "Specify Coordinates at Point" en vez de esto,
                  #       dejar los dos en 0.0.

ELEVACION = 0.02  # ft sobre la superficie de apoyo, para que la pintura no
                  # parpadee (z-fighting) al coincidir con la cara del terreno

ES_PARAMETRICA = False    # ver la cabecera del archivo

NOMBRE_FAMILIA = 'Marca Vial - Nombre De La Capa'   # <-- CAMBIAR
NOMBRE_PARAM_LARGO = 'Largo'     # solo se usan si ES_PARAMETRICA = True
NOMBRE_PARAM_ANCHO = 'Ancho'

ESPESOR = 0.02     # ft, solo aplica si ES_PARAMETRICA=False (se construye la
                  # familia desde cero con esta extrusion)

# Contorno canonico, SOLO si ES_PARAMETRICA=False. Pegar aqui el contenido de
# <capa>_contorno_paste.txt (lo genera exportar_marcas_pavimento.py). Debe
# apuntar a +X y estar centrado en el origen -- eso ya lo deja hecho el
# exportador, no hay que tocarlo a mano.
CONTORNO = [
    # (x, y),
]

# BASCULAR = False por una razon medida, no por comodidad: Revit ancla las
# instancias de familia al plano de su nivel y rechaza sacarlas de la
# horizontal ("Can't rotate element into this position"), y lo hace como
# AVISO propio, no como excepcion -- un try/except no se entera. En vez de
# inclinar cada pieza, se sube la mitad de su propio desnivel (columna DzFt
# del CSV, MEDIDO sobre la malla real, no estimado) para que ningun punto
# quede bajo la superficie de apoyo. Para desniveles grandes (curvas muy
# pronunciadas) esto puede no bastar -- revisar visualmente el resultado.
BASCULAR = False
SIGNO_BASCULADO = -1.0   # si se activa BASCULAR, verificar el signo
                         # reconstruyendo un par de instancias fuera de Revit
                         # antes de fiarse (ver la skill, seccion de verificacion)

# ============================================================================

log = []
errores = []
correcciones = []


def nombre_de(t):
    p = t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
    return p.AsString() if p else ''


def buscar_simbolo(nombre):
    for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol):
        if nombre_de(s) == nombre:
            return s
    return None


def buscar_plantilla():
    """Plantilla de Modelo generico PLANA, en cualquier idioma, comparando el
    nombre COMPLETO contra una lista blanca.

    NO buscar por "contiene generic model": eso coge tambien
    'Generic Model Adaptive.rft', 'Generic Model face based.rft', etc, que NO
    admiten extrusiones simples ("The attempted operation is not permitted in
    this type of family")."""
    raiz = app.FamilyTemplatePath
    BLANCA = ('generic model', 'metric generic model', 'modelo generico metrico',
             'modelo generico', 'modele generique metrique', 'generisches modell')

    def limpia(s):
        for a, b in zip(u'áéíóúñüàèìòùâêîôûç', u'aeiounuaeiouaeiouc'):
            s = s.replace(a, b)
        return s.strip().lower()

    cand = []
    for r, _d, arch in os.walk(raiz):
        for a in arch:
            if a.lower().endswith('.rft') and limpia(os.path.splitext(a)[0]) in BLANCA:
                cand.append(os.path.join(r, a))
    cand.sort(key=lambda p: (0 if 'english-imperial' in p.lower()
                             else 1 if 'english' in p.lower() else 2, p))
    return cand[0] if cand else None


def crear_familia_simbolo():
    """Construye el .rfa desde CONTORNO y lo carga. Devuelve el FamilySymbol."""
    plantilla = buscar_plantilla()
    if plantilla is None:
        raise Exception('no encuentro una plantilla de Modelo generico plana en %s'
                        % app.FamilyTemplatePath)
    log.append('plantilla usada: %s' % plantilla)

    # Un intento fallido anterior pudo dejar el documento de familia ABIERTO
    # (la excepcion salta antes del Close), bloqueando el .rfa: "Saving is not
    # allowed. File has been opened by another Revit instance". Se cierra
    # cualquier resto antes de empezar.
    for d in list(app.Documents):
        try:
            if d.IsFamilyDocument and d.Title.startswith(NOMBRE_FAMILIA):
                d.Close(False)
        except Exception:
            pass

    carpeta = os.path.join(tempfile.gettempdir(), 'marcas_%d' % os.getpid())
    if not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    destino = os.path.join(carpeta, NOMBRE_FAMILIA + '.rfa')

    fdoc = app.NewFamilyDocument(plantilla)
    try:
        t = Transaction(fdoc, 'Contorno de la marca')
        t.Start()
        lazo = DB.CurveArray()
        n = len(CONTORNO)
        for i in range(n):
            x0, y0 = CONTORNO[i]
            x1, y1 = CONTORNO[(i + 1) % n]
            lazo.Append(Line.CreateBound(XYZ(x0, y0, 0.0), XYZ(x1, y1, 0.0)))
        lazos = DB.CurveArrArray()
        lazos.Append(lazo)
        sk = DB.SketchPlane.Create(fdoc, DB.Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero))
        fdoc.FamilyCreate.NewExtrusion(True, lazos, sk, ESPESOR)
        if BASCULAR:
            # Sin esto la familia queda anclada a su nivel y Revit rechaza el
            # basculado. Marcarla como basada en plano de trabajo NO basta si
            # ademas la instancia se crea sobre el nivel del proyecto -- ver
            # el comentario largo junto a BASCULAR mas arriba.
            par = fdoc.OwnerFamily.get_Parameter(DB.BuiltInParameter.FAMILY_WORK_PLANE_BASED)
            if par is not None and not par.IsReadOnly:
                par.Set(1)
        t.Commit()

        opts = DB.SaveAsOptions()
        opts.OverwriteExistingFile = True
        fdoc.SaveAs(destino, opts)
        log.append('familia guardada en %s' % destino)

        # En CPython (Python.NET) NO existe clr.Reference, asi que NO se
        # puede usar LoadFamily(str, Family&) -- devuelve por parametro de
        # salida. Este overload lo devuelve como VALOR de retorno:
        #    Family LoadFamily(Document targetDocument)
        # Y va SIN transaccion abierta: LoadFamily gestiona la suya propia y
        # exige que el documento no sea modificable al llamarla ("The
        # document must not be modifiable before calling LoadFamily").
        fam = fdoc.LoadFamily(doc)
    finally:
        # SIEMPRE cerrar, tambien si algo falla: si no, la siguiente pasada
        # no puede guardar y el error ("opened by another Revit instance")
        # despista sobre la causa real.
        try:
            fdoc.Close(False)
        except Exception:
            pass

    sim = buscar_simbolo(NOMBRE_FAMILIA)
    if sim is None and fam is not None:
        for sid in fam.GetFamilySymbolIds():
            sim = doc.GetElement(sid)
            break
    if sim is None:
        raise Exception('la familia se cargo pero no encuentro su FamilySymbol')
    return sim


def centrar_geometria(inst, objetivo):
    """Mide el centro REAL de la geometria ya colocada (tras fijar los
    parametros y regenerar) y traslada la instancia en XY para que coincida
    con 'objetivo'.

    Por que hace falta: una familia parametrica construida a mano puede no
    crecer simetrica desde su origen de insercion al cambiar sus parametros
    por codigo (en South Island, 14 de 14 necesitaron ajuste, de 3 a 10 ft).
    Se corrige SIN tocar la familia: se mide el centro de las aristas del
    solido ya colocado -- para un prisma rectangular esto es el centro
    geometrico EXACTO, sin importar como este construida la familia por
    dentro -- y se traslada la instancia. Se llama ANTES de girar, para que
    el giro pivote sobre el centro real."""
    opts = DB.Options()
    opts.DetailLevel = DB.ViewDetailLevel.Fine
    geo = inst.get_Geometry(opts)
    solidos = []
    for g in geo:
        if isinstance(g, DB.GeometryInstance):
            for g2 in g.GetInstanceGeometry():
                if isinstance(g2, DB.Solid) and g2.Volume > 1e-9:
                    solidos.append(g2)
        elif isinstance(g, DB.Solid) and g.Volume > 1e-9:
            solidos.append(g)
    if not solidos:
        errores.append(('centrar geometria %s' % inst.Id, 'sin solidos en la geometria'))
        return
    pts = []
    for s in solidos:
        for e in s.Edges:
            c = e.AsCurve()
            pts.append(c.GetEndPoint(0))
            pts.append(c.GetEndPoint(1))
    n = len(pts)
    cx = sum(v.X for v in pts) / n
    cy = sum(v.Y for v in pts) / n
    dx, dy = objetivo.X - cx, objetivo.Y - cy
    if abs(dx) > 0.001 or abs(dy) > 0.001:
        DB.ElementTransformUtils.MoveElement(doc, inst.Id, XYZ(dx, dy, 0.0))
        correcciones.append((inst.Id, dx, dy))


def colocar(sim, x, y, z, ang_deg, pend_pct, pend_dir_deg, dz, largo=None, ancho=None):
    subida = ELEVACION if BASCULAR else (dz / 2.0 + ELEVACION)
    p = XYZ(x + OFFSET_X, y + OFFSET_Y, z + subida)
    inst = doc.Create.NewFamilyInstance(p, sim, DB.Structure.StructuralType.NonStructural)

    if ES_PARAMETRICA:
        for nombre, valor in ((NOMBRE_PARAM_LARGO, largo), (NOMBRE_PARAM_ANCHO, ancho)):
            par = inst.LookupParameter(nombre)
            if par is None:
                # LookupParameter busca por NOMBRE EXACTO. Si la familia lo
                # tiene con otro nombre (tilde, mayuscula, espacio de mas),
                # esto NO FALLA -- simplemente no hace nada, y todas las
                # instancias salen con el tamano por defecto de la familia,
                # sin ningun error en el log si no se comprueba esto.
                disponibles = sorted({q.Definition.Name for q in inst.Parameters})
                errores.append(('parametro "%s" no encontrado en %s' % (nombre, inst.Id),
                                'disponibles: %s' % ', '.join(disponibles)))
                continue
            if par.IsReadOnly:
                errores.append(('parametro "%s" de solo lectura en %s' % (nombre, inst.Id), ''))
                continue
            par.Set(valor)
            doc.Regenerate()   # ANTES de leer: sin esto, AsDouble() puede
                               # devolver el valor previo a Set(), no el que
                               # se acaba de poner -- falso positivo de fallo.
            leido = par.AsDouble()
            if abs(leido - valor) > 1e-4:
                # Diagnostico definitivo: comparar tambien contra el TIPO. Si
                # coinciden entre si, el parametro sigue siendo de Tipo pese
                # al cambio hecho en el Editor de familias (no se guardo, o
                # se recargo el .rfa equivocado). En Revit 2024/2025 el
                # dialogo "Family Types" ya no tiene una casilla "Instance"
                # visible en la tabla: hay que seleccionar el parametro y
                # usar el icono de lapiz "Edit Parameter" para reabrirlo.
                try:
                    par_tipo = sim.LookupParameter(nombre)
                    valor_tipo = par_tipo.AsDouble() if par_tipo else None
                except Exception:
                    valor_tipo = None
                errores.append(('parametro "%s" no cuadra tras Set() en %s' % (nombre, inst.Id),
                                'puesto %.4f, leido en la instancia %.4f, leido en el TIPO %s'
                                % (valor, leido,
                                   ('%.4f' % valor_tipo) if valor_tipo is not None else 'N/D')))
        centrar_geometria(inst, p)

    ang = math.radians(ang_deg)
    if abs(ang) > 1e-9:
        eje = Line.CreateBound(p, XYZ(p.X, p.Y, p.Z + 1.0))
        DB.ElementTransformUtils.RotateElement(doc, inst.Id, eje, ang)

    if BASCULAR:
        th = math.atan(pend_pct / 100.0)
        if abs(th) > 1e-9:
            d = math.radians(pend_dir_deg)
            u = XYZ(-math.sin(d), math.cos(d), 0.0)
            eje2 = Line.CreateBound(p, XYZ(p.X + u.X, p.Y + u.Y, p.Z))
            DB.ElementTransformUtils.RotateElement(doc, inst.Id, eje2, SIGNO_BASCULADO * th)
    return inst


def limpiar_anterior():
    ids = []
    for e in DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance):
        p = e.LookupParameter('Comments')
        try:
            v = p.AsString() if (p and p.HasValue) else None
        except Exception:
            v = None
        if v and v.startswith('PM_%s ' % NOMBRE_FAMILIA):
            ids.append(e.Id)
    fams = []
    if not ES_PARAMETRICA:
        for f in DB.FilteredElementCollector(doc).OfClass(DB.Family):
            try:
                if f.Name == NOMBRE_FAMILIA:
                    fams.append(f.Id)
            except Exception:
                pass
    if not ids and not fams:
        return
    t = Transaction(doc, 'Limpiar marcas de la pasada anterior')
    t.Start()
    for i in ids + fams:
        try:
            doc.Delete(i)
        except Exception:
            pass
    t.Commit()
    log.append('limpieza previa: %d instancias, %d familia(s)' % (len(ids), len(fams)))


# ---------------------------------------------------------------------------
if ES_PARAMETRICA:
    if not NOMBRE_FAMILIA or NOMBRE_FAMILIA == 'Marca Vial - Nombre De La Capa':
        raise Exception('pon NOMBRE_FAMILIA con el nombre real de tu familia parametrica')
else:
    if not CONTORNO or len(CONTORNO) < 3:
        raise Exception('pega el contenido de <capa>_contorno_paste.txt en CONTORNO')

limpiar_anterior()

sim = buscar_simbolo(NOMBRE_FAMILIA)
if sim is None:
    if ES_PARAMETRICA:
        raise Exception(
            'familia "%s" no encontrada. Es parametrica: creala a mano en el Editor '
            'de familias (rectangulo centrado en el origen, largo segun +X, extrusion, '
            'parametros DE INSTANCIA "%s"/"%s" tipo Longitud) y cargala en el proyecto '
            '(Insert -> Load Family) antes de correr esto.'
            % (NOMBRE_FAMILIA, NOMBRE_PARAM_LARGO, NOMBRE_PARAM_ANCHO))
    sim = crear_familia_simbolo()
    log.append('familia "%s" creada' % NOMBRE_FAMILIA)
else:
    log.append('familia "%s": ya existia, se reutiliza' % NOMBRE_FAMILIA)

with open(csv_path, 'r') as fh:
    filas = list(csv.DictReader(fh))

creadas = 0
t = Transaction(doc, 'Colocar marcas - %s' % NOMBRE_FAMILIA)
t.Start()
if not sim.IsActive:
    sim.Activate()
    doc.Regenerate()
for f in filas:
    try:
        inst = colocar(sim, float(f['X']), float(f['Y']), float(f['Z']),
                       float(f['AngDeg']), float(f['PendPct']), float(f['PendDirDeg']),
                       float(f['DzFt']),
                       largo=float(f['LargoFt']) if ES_PARAMETRICA else None,
                       ancho=float(f['AnchoFt']) if ES_PARAMETRICA else None)
        p = inst.LookupParameter('Comments')
        if p and not p.IsReadOnly:
            p.Set('PM_%s %s' % (NOMBRE_FAMILIA, f['Id']))
        creadas += 1
    except Exception as ex:
        errores.append(('marca %s' % f['Id'], str(ex)))
t.Commit()

ruta_log = os.path.join(os.path.dirname(csv_path), 'dynamo_log_%s.txt' % NOMBRE_FAMILIA)
with open(ruta_log, 'w') as fh:
    fh.write('MARCAS DE PAVIMENTACION -- %s\n' % NOMBRE_FAMILIA)
    fh.write('ES_PARAMETRICA=%s  OFFSET X=%s Y=%s  elevacion=%s ft\n\n'
             % (ES_PARAMETRICA, OFFSET_X, OFFSET_Y, ELEVACION))
    for l in log:
        fh.write(l + '\n')
    fh.write('\nCREADAS: %d de %d\n' % (creadas, len(filas)))
    if ES_PARAMETRICA:
        fh.write('\nCORRECCION DE CENTRADO: %d de %d necesitaron ajuste\n'
                 % (len(correcciones), creadas))
        if correcciones:
            mags = sorted((dx * dx + dy * dy) ** 0.5 for _i, dx, dy in correcciones)
            fh.write('  magnitud: minimo %.3f | mediana %.3f | maximo %.3f ft\n'
                     % (mags[0], mags[len(mags) // 2], mags[-1]))
    fh.write('\nERRORES (%d):\n' % len(errores))
    for q, m in errores:
        fh.write('  %s\n    %s\n' % (q, m))

OUT = (creadas, len(filas), len(errores), errores[:10], len(correcciones), '\n'.join(log), ruta_log)
