#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sistema de Integración de Skills y Enrutador de Intenciones para Civil 3D / Topografía.

Permite detectar la intención de solicitudes en lenguaje natural, mapear habilidades
complementarias y ejecutar pipelines automatizados de procesamiento de superficies,
geometría, reportes y actualización de tablero.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(BASE_DIR, ".."))

# Registro central de intenciones y habilidades
REGISTRO_SKILLS = {
    "auditoria_superficies_landxml": {
        "nombre": "Auditoría de Integridad LandXML",
        "categoria": "Superficies",
        "palabras_clave": ["auditar", "auditoria", "integridad", "caras invisibles", "landxml", "revisar xml"],
        "script": os.path.join(BASE_DIR, "superficies", "scripts", "auditar_superficie.py"),
        "doc": os.path.join(BASE_DIR, "superficies", "auditoria-superficies-landxml.skill.md"),
    },
    "recorte_superficie_con_perimetro": {
        "nombre": "Recorte de Superficie TIN con Perímetro",
        "categoria": "Superficies",
        "palabras_clave": ["cortar", "recortar", "recorte", "perimetro", "area interior", "cubicacion"],
        "script": os.path.join(BASE_DIR, "superficies", "scripts", "recortar_superficie.py"),
        "doc": os.path.join(BASE_DIR, "superficies", "recorte-superficie.skill.md"),
    },
    "drapeado_contorno_3d": {
        "nombre": "Drapeado y Extracción de Contornos 3D",
        "categoria": "Superficies",
        "palabras_clave": ["drapear", "drapeado", "borde 3d", "contorno 3d", "breakline", "cota z"],
        "script": os.path.join(BASE_DIR, "superficies", "scripts", "drapear_contorno.py"),
        "doc": os.path.join(BASE_DIR, "superficies", "drapeado-contorno-3d.skill.md"),
    },
    "teselado_arcos_polilinea": {
        "nombre": "Teselado de Arcos por Sagitta",
        "categoria": "Geometría",
        "palabras_clave": ["teselar", "arcos", "bulge", "sagitta", "curvas", "densificar"],
        "script": os.path.join(BASE_DIR, "geometria", "scripts", "teselar_arcos.py"),
        "doc": os.path.join(BASE_DIR, "geometria", "teselado-arcos-polilinea.skill.md"),
    },
    "generacion_planos_svg": {
        "nombre": "Generación de Planos Vectoriales SVG",
        "categoria": "Reportes",
        "palabras_clave": ["plano", "svg", "vectorial", "reporte visual", "grafico", "leyenda", "escala"],
        "script": os.path.join(BASE_DIR, "reportes", "scripts", "plano_svg.py"),
        "doc": os.path.join(BASE_DIR, "reportes", "generacion-planos-svg.skill.md"),
    },
    "importar_toposolid_revit": {
        "nombre": "Importación de Superficies a Revit como Toposolid",
        "categoria": "Interoperabilidad",
        "palabras_clave": ["revit", "toposolid", "dynamo", "importar a revit", "exportar a revit",
                           "visualizar en revit", "bim", "topografia revit"],
        # corregir_paquete_revit.py prepara el paquete; generar_dyn_toposolid.py arma el grafo.
        "script": os.path.join(BASE_DIR, "superficies", "scripts", "corregir_paquete_revit.py"),
        "doc": os.path.join(BASE_DIR, "superficies", "importar-toposolid-revit.skill.md"),
    },
    "terrazas_taludes_calzadas": {
        "nombre": "Terrazas, Taludes y Calzadas de un Loteo en Ladera",
        "categoria": "Loteo",
        "palabras_clave": ["terraza", "terrazas", "talud", "taludes", "plataforma", "npt",
                            "loteo", "calzada", "calzadas", "rasante", "solera",
                            "cota de piso", "subdivision", "urbanizacion", "cerro",
                            "movimiento de tierras", "cubicar loteo", "escalonamiento"],
        # Biblioteca, no un CLI: se importa `terrazas_lib` y `vialidad_lib` desde el
        # flujo del proyecto, porque cada loteo trae su propia forma de leer lotes y NPT.
        "script": os.path.join(BASE_DIR, "loteo", "scripts", "terrazas_lib.py"),
        "doc": os.path.join(BASE_DIR, "loteo", "terrazas-taludes-calzadas.skill.md"),
    },
}


def detectar_intenciones(texto: str) -> list[str]:
    """Identifica las skills asociadas a un texto o consulta en lenguaje natural."""
    texto_lower = texto.lower()
    skills_detectadas = []

    # Si solicita pipeline completo
    if any(k in texto_lower for k in ["completo", "todo", "pipeline", "verificacion completa"]):
        return list(REGISTRO_SKILLS.keys())

    for key, info in REGISTRO_SKILLS.items():
        if any(kw in texto_lower for kw in info["palabras_clave"]):
            skills_detectadas.append(key)

    return skills_detectadas


def ejecutar_pipeline(xml_path: str, dxf_path: str, salida_dir: str | None = None) -> dict:
    """Ejecuta el pipeline completo unificado de recortes y verificación."""
    if not salida_dir:
        salida_dir = os.path.dirname(os.path.abspath(xml_path))

    resultados = {}

    # 1. Auditoría
    print("\n[1/4] Ejecutando Auditoría de LandXML...")
    cmd_aud = [sys.executable, REGISTRO_SKILLS["auditoria_superficies_landxml"]["script"], "--xml", xml_path]
    p_aud = subprocess.run(cmd_aud, capture_output=True, text=True)
    resultados["auditoria"] = p_aud.stdout

    # 2. Recorte + SVG + DXF
    print("[2/4] Ejecutando Recorte TIN con Perímetro DXF...")
    cmd_rec = [sys.executable, REGISTRO_SKILLS["recorte_superficie_con_perimetro"]["script"], "--xml", xml_path, "--dxf", dxf_path, "--todo"]
    p_rec = subprocess.run(cmd_rec, capture_output=True, text=True)
    resultados["recorte"] = p_rec.stdout

    # 3. Drapeado 3D
    print("[3/4] Ejecutando Drapeado 3D de Contornos...")
    drape_out = os.path.join(salida_dir, "borde_drapeado_3d.dxf")
    cmd_drp = [sys.executable, REGISTRO_SKILLS["drapeado_contorno_3d"]["script"], "--xml", xml_path, "--dxf", dxf_path, "--salida", drape_out]
    p_drp = subprocess.run(cmd_drp, capture_output=True, text=True)
    resultados["drapeado"] = p_drp.stdout

    # 4. Actualizar Dashboard
    print("[4/4] Sincronizando Tablero del Laboratorio...")
    cmd_dash = [sys.executable, os.path.join(ROOT_DIR, "update_dashboard.py")]
    p_dash = subprocess.run(cmd_dash, capture_output=True, text=True)
    resultados["dashboard"] = p_dash.stdout

    print("\nPipeline completado exitosamente.")
    return resultados


def main():
    parser = argparse.ArgumentParser(description="Router e Integrador de Skills por Intención.")
    parser.add_argument("--intencion", help="Frase de intención en lenguaje natural para clasificar")
    parser.add_argument("--pipeline", action="store_true", help="Ejecutar el pipeline unificado sobre XML y DXF")
    parser.add_argument("--xml", help="Ruta al LandXML")
    parser.add_argument("--dxf", help="Ruta al DXF")
    args = parser.parse_args()

    if args.intencion:
        skills = detectar_intenciones(args.intencion)
        print(f"Intención recibida: {args.intencion!r}")
        print(f"Skills complementarias identificadas ({len(skills)}):")
        for s in skills:
            info = REGISTRO_SKILLS[s]
            print(f"  - [{s}] {info['nombre']} (Categoría: {info['categoria']})")
        return

    if args.pipeline:
        if not args.xml or not args.dxf:
            sys.exit("Error: --pipeline requiere especificación de --xml y --dxf")
        ejecutar_pipeline(args.xml, args.dxf)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
