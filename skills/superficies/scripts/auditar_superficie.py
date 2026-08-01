#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Audita la integridad de superficies TIN en LandXML.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import xml.etree.ElementTree as ET

NS = {"lx": "http://www.landxml.org/schema/LandXML-1.2"}

def auditar_landxml(ruta_xml: str, nombre_surf: str | None = None) -> dict:
    if not os.path.exists(ruta_xml):
        raise FileNotFoundError(f"No existe el archivo {ruta_xml}")

    tree = ET.parse(ruta_xml)
    root = tree.getroot()

    unidades = root.find("lx:Units", NS)
    lineal = "meter"
    if unidades is not None and len(unidades):
        lineal = unidades[0].get("linearUnit", "meter")

    superficies = root.findall(".//lx:Surface", NS)
    if not superficies:
        return {"valido": False, "error": "No se encontraron superficies <Surface>"}

    target_surf = None
    if nombre_surf:
        for s in superficies:
            if s.get("name") == nombre_surf:
                target_surf = s
                break
        if not target_surf:
            return {"valido": False, "error": f"Superficie {nombre_surf!r} no encontrada"}
    else:
        target_surf = superficies[0]

    nombre = target_surf.get("name", "Sin Nombre")
    defin = target_surf.find("lx:Definition", NS)
    
    area_2d_decl = None
    area_3d_decl = None
    if defin is not None:
        area_2d_decl = float(defin.get("area2DSurf", 0.0)) if defin.get("area2DSurf") else None
        area_3d_decl = float(defin.get("area3DSurf", 0.0)) if defin.get("area3DSurf") else None

    # Leer puntos <P id="1">N E Z</P>
    puntos = {}
    pnts_elem = target_surf.find(".//lx:Pnts", NS)
    if pnts_elem is not None:
        for p in pnts_elem.findall("lx:P", NS):
            pid = int(p.get("id"))
            parts = [float(x) for x in p.text.split()]
            # LandXML: Northing Easting Elevation
            puntos[pid] = (parts[1], parts[0], parts[2])  # (East, North, Elev)

    # Leer caras <F i="1">p1 p2 p3</F>
    caras_visibles = []
    caras_invisibles = []
    faces_elem = target_surf.find(".//lx:Faces", NS)
    if faces_elem is not None:
        for f in faces_elem.findall("lx:F", NS):
            pid1, pid2, pid3 = [int(x) for x in f.text.split()[:3]]
            invisible = f.get("i") == "1"
            if invisible:
                caras_invisibles.append((pid1, pid2, pid3))
            else:
                caras_visibles.append((pid1, pid2, pid3))

    # Calcular área 2D real sumando triángulos visibles
    area_2d_calc = 0.0
    for p1, p2, p3 in caras_visibles:
        if p1 in puntos and p2 in puntos and p3 in puntos:
            x1, y1, _ = puntos[p1]
            x2, y2, _ = puntos[p2]
            x3, y3, _ = puntos[p3]
            a = abs(x1*(y2 - y3) + x2*(y3 - y1) + x3*(y1 - y2)) / 2.0
            area_2d_calc += a

    return {
        "valido": True,
        "nombre": nombre,
        "unidad": lineal,
        "puntos_totales": len(puntos),
        "caras_visibles": len(caras_visibles),
        "caras_invisibles": len(caras_invisibles),
        "area_2d_declarada": area_2d_decl,
        "area_2d_calculada": area_2d_calc,
        "diferencia_area_2d": (area_2d_calc - area_2d_decl) if area_2d_decl else 0.0
    }

def main():
    parser = argparse.ArgumentParser(description="Auditoría de integridad LandXML.")
    parser.add_argument("--xml", required=True, help="LandXML a auditar")
    parser.add_argument("--superficie", help="Nombre de superficie")
    args = parser.parse_args()

    res = auditar_landxml(args.xml, args.superficie)
    if not res["valido"]:
        print(f"ERROR: {res['error']}")
        sys.exit(1)

    print(f"--- Auditoría LandXML: {res['nombre']} ---")
    print(f"Unidad lineal: {res['unidad']}")
    print(f"Puntos totales: {res['puntos_totales']}")
    print(f"Caras visibles: {res['caras_visibles']} | Caras invisibles: {res['caras_invisibles']}")
    print(f"Área 2D calculada: {res['area_2d_calculada']:,.2f}")
    if res['area_2d_declarada']:
        print(f"Área 2D declarada: {res['area_2d_declarada']:,.2f}")
        print(f"Diferencia: {res['diferencia_area_2d']:,.4f}")

if __name__ == "__main__":
    main()
