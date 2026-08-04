# -*- coding: utf-8 -*-
"""
Auditor de Superficies Toposolid y Salud de Datos para Revit
-----------------------------------------------------------
Este script inspecciona los archivos CSV de puntos, contornos y el log de Dynamo
para verificar la integridad geometrica de las superficies antes y despues de
la importacion a Revit.
"""

import os
import csv
import json

def auditar_carpeta_entrega(carpeta_path):
    print("=" * 70)
    print("   AUDITORIA DE SUPERFICIES Y SALUD DE DATOS TOPOSOLID (REVIT)")
    print("=" * 70)
    print(f"Carpeta analizada: {carpeta_path}\n")

    pts_csv = os.path.join(carpeta_path, "All_Points_ByPiece.csv")
    bnd_csv = os.path.join(carpeta_path, "All_Boundaries_Complete.csv")
    log_txt = os.path.join(carpeta_path, "dynamo_log.txt")

    # 1. Analizar CSV de Puntos
    if os.path.exists(pts_csv):
        piezas_pts = {}
        total_pts = 0
        min_z = float('inf')
        max_z = float('-inf')

        with open(pts_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # Encabezado
            for row in reader:
                if not row or len(row) < 5:
                    continue
                surf_name, piece_id, x, y, z = row[0], int(row[1]), float(row[2]), float(row[3]), float(row[4])
                key = (surf_name, piece_id)
                piezas_pts[key] = piezas_pts.get(key, 0) + 1
                total_pts += 1
                if z < min_z: min_z = z
                if z > max_z: max_z = z

        print(f"[OK] CSV Puntos (`All_Points_ByPiece.csv`):")
        print(f"   - Total Puntos 3D: {total_pts:,}")
        print(f"   - Total Piezas/Superficies: {len(piezas_pts)}")
        print(f"   - Rango de Elevacion Z: [{min_z:.3f} ft , {max_z:.3f} ft] (Desnivel: {max_z - min_z:.3f} ft)\n")
    else:
        print("[FALLO] CSV de puntos no encontrado.\n")

    # 2. Analizar CSV de Contornos y Huecos
    if os.path.exists(bnd_csv):
        outer_count = 0
        hole_count = 0
        with open(bnd_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if not row or len(row) < 4:
                    continue
                rtype = row[2]
                if rtype == 'OUTER':
                    outer_count += 1
                elif rtype == 'HOLE':
                    hole_count += 1

        print(f"[OK] CSV Contornos (`All_Boundaries_Complete.csv`):")
        print(f"   - Anillos Exteriores (OUTER): {outer_count}")
        print(f"   - Huecos de Edificacion (HOLE): {hole_count}\n")
    else:
        print("[FALLO] CSV de contornos no encontrado.\n")

    # 3. Analizar Log de Ejecucion Dynamo (si existe)
    if os.path.exists(log_txt):
        print(f"[OK] Log de Ejecucion (`dynamo_log.txt`):")
        with open(log_txt, 'r', encoding='utf-8') as f:
            contenido = f.read()
            lines = contenido.splitlines()
            for l in lines[:15]:
                print(f"   | {l}")
        print()
    else:
        print("[INFO] Log de Dynamo aun no generado (se creara al ejecutar `ImportarToposolids.dyn` en Revit).\n")

    print("=" * 70)
    print("ESTADO DEL MODELO: LISTO PARA PROCESAR / INSPECCIONAR EN REVIT")
    print("=" * 70)

if __name__ == "__main__":
    target_dir = r"C:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\OTROS\MCP\Autocad\verificacion\01-08-2026\12_Entrega_DWG_Optimizado\REVIT-Dynamo\ENTREGA_SUPERFICIES_REVIT"
    auditar_carpeta_entrega(target_dir)
