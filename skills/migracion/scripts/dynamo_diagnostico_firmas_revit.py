# -*- coding: utf-8 -*-
# ============================================================================
#  dynamo_diagnostico_firmas_revit.py
#  CORRER SIEMPRE PRIMERO, antes de tocar cualquier otro script de esta skill.
#  No modifica el documento. Vuelca en un .txt las firmas REALES del API de
#  Revit de la version instalada, para no adivinar overloads.
#
#  Por que hace falta: "No method matches given arguments" no dice que
#  argumento falta. Adivinar cuesta iteraciones enteras (paso en
#  Toposolid.Create -- 3 argumentos supuestos, tiene 5) y algunas llamadas
#  fallan por motivos que ni siquiera son de firma (ver mas abajo).
#
#  Nodo Python Script en Dynamo, motor CPython3, SIN entradas.
# ============================================================================
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
import Autodesk.Revit.DB as DB
from RevitServices.Persistence import DocumentManager

import os

doc = DocumentManager.Instance.CurrentDBDocument
app = doc.Application

# Amplia esta lista con cualquier llamada que vayas a usar y no este aqui.
QUE_MIRAR = [
    (DB.Document, 'LoadFamily'),
    (DB.SketchPlane, 'Create'),
    (DB.Plane, 'CreateByNormalAndOrigin'),
    (DB.ElementTransformUtils, 'RotateElement'),
    (DB.ElementTransformUtils, 'MoveElement'),
    (DB.DirectShape, 'CreateElement'),
    (DB.DirectShape, 'SetShape'),
    (DB.TessellatedShapeBuilder, 'AddFace'),
    (DB.TessellatedShapeBuilder, 'Build'),
    (DB.TessellatedShapeBuilder, 'GetBuildResult'),
    (DB.TessellatedFace, '.ctor'),
    (DB.Line, 'CreateBound'),
]

lineas = []


def firmar(tipo, nombre):
    try:
        ct = clr.GetClrType(tipo)   # CPython3 lo necesita: tipo.GetMethods()
    except Exception:               # directo da AttributeError
        ct = tipo
    out = []
    try:
        if nombre == '.ctor':
            for m in ct.GetConstructors():
                out.append('  new %s(%s)' % (
                    ct.Name, ', '.join(p.ParameterType.Name + ' ' + p.Name
                                       for p in m.GetParameters())))
        else:
            for m in ct.GetMethods():
                if m.Name != nombre:
                    continue
                out.append('  %s %s(%s)' % (
                    m.ReturnType.Name, m.Name,
                    ', '.join(p.ParameterType.Name + ' ' + p.Name
                              for p in m.GetParameters())))
    except Exception as ex:
        out.append('  ERROR: %s' % ex)
    return out or ['  (no encontrado)']


lineas.append('Revit %s   doc: %s' % (app.VersionNumber, doc.Title))
lineas.append('')

for tipo, nombre in QUE_MIRAR:
    lineas.append('=== %s.%s ===' % (getattr(tipo, '__name__', str(tipo)), nombre))
    lineas.extend(firmar(tipo, nombre))
    lineas.append('')

# Las fabricas de creacion de familias/instancias NO viven en el tipo Document
# directamente. OJO: NUNCA usar getattr(doc, 'FamilyCreate', None) para
# comprobar si existe -- eso INVOCA el getter de la propiedad, y en un
# documento de PROYECTO lanza InvalidOperationException ("can only be used in
# the Revit Family Editor"); getattr con default solo protege de
# AttributeError, no de esa excepcion, y tumba el script entero.
# Reflexionar sobre las CLASES no necesita ninguna instancia.
lineas.append('=== fabricas de creacion (por tipo, sin instanciar) ===')
try:
    import Autodesk.Revit.Creation as CR
    for tipo, etiqueta in ((CR.FamilyItemFactory, 'doc.FamilyCreate (solo en Editor de familias)'),
                           (CR.Document, 'doc.Create (documentos de proyecto)')):
        lineas.append('  -- %s --' % etiqueta)
        try:
            ct = clr.GetClrType(tipo)
        except Exception:
            ct = tipo
        for m in ct.GetMethods():
            if m.Name in ('NewExtrusion', 'NewFamilyInstance', 'NewDimension'):
                lineas.append('    %s %s(%s)' % (
                    m.ReturnType.Name, m.Name,
                    ', '.join(p.ParameterType.Name + ' ' + p.Name for p in m.GetParameters())))
except Exception as ex:
    lineas.append('  ERROR: %s' % ex)
lineas.append('')

# Motor de Python: decide como se recogen los parametros "out" del API
# (p.ej. LoadFamily(filename, Family&) necesita clr.Reference, que NO existe
# en CPython -- hay que usar el overload que devuelve la Family como retorno).
lineas.append('=== motor de Python del nodo ===')
try:
    import sys
    lineas.append('  version    : %s' % sys.version.replace('\n', ' '))
    lineas.append('  motor      : %s' % ('IronPython' if 'IronPython' in sys.version
                                         else 'CPython (Python.NET)'))
    lineas.append('  clr.Reference disponible: %s' % hasattr(clr, 'Reference'))
except Exception as ex:
    lineas.append('  ERROR: %s' % ex)
lineas.append('')

# Plantillas de familia disponibles -- el idioma del Revit instalado decide
# el nombre ("Generic Model.rft" en ingles, "Modelo generico metrico.rft" en
# espanol...). No asumir ingles.
lineas.append('=== plantillas de familia "generic model" encontradas ===')
try:
    raiz = app.FamilyTemplatePath
    lineas.append('  FamilyTemplatePath = %s' % raiz)
    BLANCA = ('generic model', 'metric generic model', 'modelo generico metrico',
             'modelo generico', 'modele generique metrique', 'generisches modell')

    def limpia(s):
        for a, b in zip(u'áéíóúñüàèìòùâêîôûç', u'aeiounuaeiouaeiouc'):
            s = s.replace(a, b)
        return s.strip().lower()

    for r, _d, arch in os.walk(raiz):
        for a in arch:
            if a.lower().endswith('.rft') and limpia(os.path.splitext(a)[0]) in BLANCA:
                lineas.append('    %s' % os.path.join(r, a))
except Exception as ex:
    lineas.append('  ERROR: %s' % ex)

texto = '\n'.join(lineas)
try:
    p = os.path.join(os.path.dirname(__file__), 'firmas_revit.txt')
except Exception:
    p = os.path.join(os.path.expanduser('~'), 'firmas_revit.txt')
try:
    with open(p, 'w') as fh:
        fh.write(texto)
    texto += '\n\n(guardado en %s)' % p
except Exception as ex:
    texto += '\n\n(no se pudo guardar: %s)' % ex

OUT = texto
