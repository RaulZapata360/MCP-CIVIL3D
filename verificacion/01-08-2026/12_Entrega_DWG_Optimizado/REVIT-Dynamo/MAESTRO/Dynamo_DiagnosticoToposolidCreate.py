# -*- coding: utf-8 -*-
# Script de DIAGNOSTICO -- no crea nada, solo lista las firmas reales de
# Toposolid.Create disponibles en tu version de Revit, usando reflection de .NET.
#
# v2: en CPython3 (el motor que usa tu Dynamo) hay que pedir el System.Type real
# via clr.GetClrType(...) antes de poder usar GetMethods() -- por eso v1 daba
# "has no attribute 'GetMethods'".
#
# USO: pegar en un nodo Python Script nuevo (no hace falta ningun IN), correr,
# y pasarme el contenido de OUT (o revisar "toposolid_create_signatures.txt").

import clr
clr.AddReference('RevitAPI')
import Autodesk.Revit.DB as DB
import os

clr_type = clr.GetClrType(DB.Toposolid)
methods = clr_type.GetMethods()

lines = []
for m in methods:
    if m.Name == 'Create':
        params = m.GetParameters()
        param_strs = ['{0} {1}'.format(p.ParameterType.ToString(), p.Name) for p in params]
        lines.append('Create(' + ', '.join(param_strs) + ')')

out_text = '\n'.join(lines) if lines else 'No se encontraron metodos Create en Toposolid'

log_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'toposolid_create_signatures.txt')
with open(log_path, 'w') as f:
    f.write(out_text)

OUT = out_text
