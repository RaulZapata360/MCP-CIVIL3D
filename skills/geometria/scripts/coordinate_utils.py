"""
Módulo de Adaptación Dinámica de Coordenadas de Proyecto (Civil 3D MCP)
Asegura que todas las entidades generadas (alineamientos, vistas de perfil, anotaciones)
se posicionen proporcionalmente a las coordenadas y extensión real del proyecto.
"""

import numpy as np

def calculate_surface_bounds(points_array):
    """
    Dadas las coordenadas (X, Y, Z) de una superficie, calcula su caja envolvente (bounding box),
    centro y dimensiones relativas.
    """
    xs = points_array[:, 0]
    ys = points_array[:, 1]
    zs = points_array[:, 2]

    min_x, max_x = np.min(xs), np.max(xs)
    min_y, max_y = np.min(ys), np.max(ys)
    min_z, max_z = np.min(zs), np.max(zs)

    width_x = max_x - min_x
    height_y = max_y - min_y

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0

    return {
        "min_x": min_x, "max_x": max_x,
        "min_y": min_y, "max_y": max_y,
        "min_z": min_z, "max_z": max_z,
        "width_x": width_x,
        "height_y": height_y,
        "center_x": center_x,
        "center_y": center_y
    }

def get_profile_view_insertion_point(bounds, offset_ratio=0.15):
    """
    Calcula el punto de inserción óptimo para una Vista de Perfil (ProfileView)
    basado en las coordenadas reales del proyecto, situándola al lado este de la superficie.
    """
    offset_x = bounds["width_x"] * offset_ratio if bounds["width_x"] > 0 else 50.0
    insert_x = bounds["max_x"] + offset_x
    insert_y = bounds["min_y"]
    return insert_x, insert_y
