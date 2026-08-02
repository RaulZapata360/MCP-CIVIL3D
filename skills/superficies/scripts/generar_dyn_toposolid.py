# -*- coding: utf-8 -*-
"""
Genera el grafo .dyn de importacion de Toposolid ya cableado.

    python generar_dyn_toposolid.py <carpeta_paquete> [<plantilla.dyn>]

Por que existe
--------------
Armar el grafo a mano en Dynamo es la parte lenta y fragil del flujo: hay que
colocar 3 nodos, pulsar el "+" para anadir IN[1], pegar 160 lineas en el editor
de Python y arrastrar 3 cables entre puertos de pocos pixeles. Cruzar IN[0] con
IN[1] no da ningun error: entrega geometria mal.

Un .dyn es JSON. Aqui se rellenan los valores sobre una PLANTILLA generada por
el propio Dynamo, asi el esquema y la version son correctos por construccion.
Las conexiones se hacen por GUID de puerto, no por pixeles: no pueden quedar
"casi bien".

Si no hay plantilla, se crea una vez a mano en Dynamo (2 nodos File Path + 1
Python Script con IN[0] e IN[1]) y se guarda; sirve para siempre.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import uuid

NOMBRE = "ImportarToposolids.dyn"
PUNTOS = "All_Points_ByPiece.csv"
CONTORNOS = "All_Boundaries_Complete.csv"
SCRIPT = "Dynamo_CreateToposolids_ConHuecos.py"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    paquete = os.path.abspath(sys.argv[1])
    plantilla = sys.argv[2] if len(sys.argv) > 2 else None

    for n in (PUNTOS, CONTORNOS, SCRIPT):
        if not os.path.exists(os.path.join(paquete, n)):
            sys.exit("Falta %s en %s" % (n, paquete))

    destino = os.path.join(paquete, NOMBRE)
    if plantilla is None:
        # buscar una plantilla en carpetas hermanas
        padre = os.path.dirname(paquete)
        for d in sorted(os.listdir(padre)):
            cand = os.path.join(padre, d, NOMBRE)
            if os.path.exists(cand) and os.path.abspath(cand) != destino:
                plantilla = cand
                break
    if plantilla is None or not os.path.exists(plantilla):
        sys.exit("No hay plantilla .dyn. Crea una en Dynamo (2 File Path + 1 Python\n"
                 "Script con IN[0] e IN[1]), guardala y pasala como 2o argumento.")

    shutil.copy2(plantilla, destino)
    with open(destino, encoding="utf-8") as f:
        g = json.load(f)

    vistas = {v["Id"]: v for v in g["View"]["NodeViews"]}
    fn = [n for n in g["Nodes"]
          if n["ConcreteType"].startswith("CoreNodeModels.Input.Filename")]
    py = [n for n in g["Nodes"]
          if n["ConcreteType"].startswith("PythonNodeModels.PythonNode")]
    if len(fn) != 2 or len(py) != 1:
        sys.exit("La plantilla debe tener exactamente 2 File Path y 1 Python Script "
                 "(hay %d y %d)." % (len(fn), len(py)))
    py = py[0]
    if len(py["Inputs"]) < 2:
        sys.exit("El nodo Python de la plantilla necesita IN[0] e IN[1] "
                 "(pulsa el '+' del nodo una vez y vuelve a guardar).")

    fn.sort(key=lambda n: vistas[n["Id"]]["Y"])      # menor Y = arriba = puntos
    for nodo, archivo in ((fn[0], PUNTOS), (fn[1], CONTORNOS)):
        ruta = os.path.join(paquete, archivo)
        nodo["HintPath"] = ruta
        nodo["InputValue"] = ruta

    with open(os.path.join(paquete, SCRIPT), encoding="utf-8") as f:
        py["Code"] = f.read()
    py["Engine"] = "CPython3"

    def entrada(nombre):
        return next(p["Id"] for p in py["Inputs"] if p["Name"] == nombre)

    g["Connectors"] = [
        {"Start": fn[0]["Outputs"][0]["Id"], "End": entrada("IN[0]"),
         "Id": uuid.uuid4().hex, "IsHidden": "False"},
        {"Start": fn[1]["Outputs"][0]["Id"], "End": entrada("IN[1]"),
         "Id": uuid.uuid4().hex, "IsHidden": "False"},
    ]
    g["View"]["Dynamo"]["RunType"] = "Manual"     # nada se ejecuta al abrir
    g["Uuid"] = str(uuid.uuid4())
    g["Name"] = os.path.splitext(NOMBRE)[0]

    with open(destino, "w", encoding="utf-8") as f:
        json.dump(g, f, indent=2, ensure_ascii=False)

    # --- verificacion por GUID, no por pixeles ----------------------------
    with open(destino, encoding="utf-8") as f:
        v = json.load(f)
    sal = {p["Id"]: n for n in v["Nodes"] for p in n.get("Outputs", [])}
    pin = {p["Id"]: p["Name"] for n in v["Nodes"] for p in n.get("Inputs", [])}
    print("Grafo: %s" % destino)
    print("  Dynamo %s | modo %s" % (v["View"]["Dynamo"]["Version"],
                                     v["View"]["Dynamo"]["RunType"]))
    esperado = {PUNTOS: "IN[0]", CONTORNOS: "IN[1]"}
    ok = True
    for c in v["Connectors"]:
        arch = os.path.basename(sal[c["Start"]].get("HintPath", "?"))
        destino_puerto = pin[c["End"]]
        bien = esperado.get(arch) == destino_puerto
        ok &= bien
        print("  %-30s --> %-6s %s" % (arch, destino_puerto, "OK" if bien else "MAL"))
    pyv = [n for n in v["Nodes"]
           if n["ConcreteType"].startswith("PythonNodeModels")][0]
    print("  script %d caracteres, motor %s" % (len(pyv["Code"]), pyv["Engine"]))
    if "dirname(points_path)" not in pyv["Code"]:
        print("  [!] el log del script no apunta junto a los CSV")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
