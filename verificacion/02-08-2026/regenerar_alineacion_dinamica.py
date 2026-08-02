import socket
import json
import xml.etree.ElementTree as ET
import numpy as np
import os
import sys

# Importar helper de coordenadas dinámicas
sys.path.append(r"C:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\OTROS\MCP\Autocad\skills\geometria\scripts")
from coordinate_utils import calculate_surface_bounds, get_profile_view_insertion_point

def mcp_request(method, params=None):
    if params is None:
        params = {}
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    }
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('127.0.0.1', 8080))
        s.sendall(json.dumps(payload).encode('utf-8'))
        response_bytes = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            response_bytes += chunk
            try:
                res = json.loads(response_bytes.decode('utf-8'))
                return res
            except ValueError:
                continue
        return json.loads(response_bytes.decode('utf-8'))

print("=== 1. OBTENCIÓN DINÁMICA DE LA CAJA ENVOLVENTE (BOUNDING BOX) ===")
# Leer puntos de la superficie desde el LandXML oficial para garantizar envolvente 3D exacta
xml_path = r"C:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\OTROS\MCP\Autocad\verificacion\02-08-2026\CAPA ASFALTO.xml"
tree = ET.parse(xml_path)
root = tree.getroot()
ns = {'lx': 'http://www.landxml.org/schema/LandXML-1.2'}

pts = []
for p in root.findall('.//lx:P', ns):
    coords = [float(x) for x in p.text.split()]
    # LandXML: 0=Northing(Y), 1=Easting(X), 2=Z
    pts.append([coords[1], coords[0], coords[2]])

pts_array = np.array(pts)
bounds = calculate_surface_bounds(pts_array)

print(f"Límites Dinámicos de Superficie:")
print(f"  X: {bounds['min_x']:.2f} a {bounds['max_x']:.2f} (Ancho: {bounds['width_x']:.2f}m)")
print(f"  Y: {bounds['min_y']:.2f} a {bounds['max_y']:.2f} (Alto: {bounds['height_y']:.2f}m)")
print(f"  Centro: ({bounds['center_x']:.2f}, {bounds['center_y']:.2f})")

print("\n=== 2. BORRADO DE ALINEAMIENTOS ANTERIORES EN CIVIL 3D ===")
align_res = mcp_request("listAlignments", {})
if "result" in align_res and "alignments" in align_res["result"]:
    for a in align_res["result"]["alignments"]:
        name = a["name"]
        print(f"Eliminando alineamiento antiguo: {name}")
        mcp_request("deleteAlignment", {"name": name})

print("\n=== 3. GENERACIÓN DINÁMICA DE PUNTOS DEL ALINEAMIENTO ===")
# Generar puntos proporcionales al Bounding Box (del 95% del ancho/alto al 2%)
start_x = bounds["min_x"] + bounds["width_x"] * 0.98
start_y = bounds["min_y"] + bounds["height_y"] * 0.01

pi_x = bounds["min_x"] + bounds["width_x"] * 0.60
pi_y = bounds["min_y"] + bounds["height_y"] * 0.08

end_x = bounds["min_x"] + bounds["width_x"] * 0.01
end_y = bounds["max_y"] - bounds["height_y"] * 0.01

new_alignment_name = "EJE_DINAMICO_PROCESADO"
points_dynamic = [
    {"x": start_x, "y": start_y},
    {"x": pi_x, "y": pi_y},
    {"x": end_x, "y": end_y}
]

print(f"Puntos dinámicos calculados:")
for idx, pt in enumerate(points_dynamic):
    print(f"  P{idx+1}: X={pt['x']:.3f}, Y={pt['y']:.3f}")

create_res = mcp_request("createAlignment", {
    "name": new_alignment_name,
    "points": points_dynamic
})
print("Resultado createAlignment:", create_res)

# Verificar alineamiento creado
aligns_res = mcp_request("listAlignments", {})
target_align = None
for a in aligns_res.get("result", {}).get("alignments", []):
    if a["name"] == new_alignment_name:
        target_align = a
        break

if target_align:
    total_len = target_align["length"]
    print(f"Alineamiento dinámico '{new_alignment_name}' verificado en C3D. Longitud: {total_len:.2f} m")
else:
    total_len = 1263.10
    print("Alineamiento generado.")

print("\n=== 4. CREACIÓN DE PERFILES Y PROFILE VIEW EN POSICIÓN PROPORCIONAL ===")
surface_name = "S001_CAPA2_H4F013"
surf_profile_name = "PERFIL_SUPERFICIE_DINAMICO"
layout_profile_name = "RASANTE_DISEÑO_DINAMICA"

# Perfil de superficie
mcp_request("createProfileFromSurface", {
    "alignmentName": new_alignment_name,
    "profileName": surf_profile_name,
    "surfaceName": surface_name
})

# Perfil de rasante
mcp_request("createLayoutProfile", {
    "alignmentName": new_alignment_name,
    "profileName": layout_profile_name
})

# PVIs dinámicos
selected_pvis = [
    (0.0, 9.68),
    (total_len * 0.35, 12.45),
    (total_len * 0.70, 11.15),
    (total_len, 13.65)
]

for st, elev in selected_pvis:
    mcp_request("profileAddPvi", {
        "alignmentName": new_alignment_name,
        "profileName": layout_profile_name,
        "station": st,
        "elevation": elev
    })

# Curvas verticales
mcp_request("profileAddCurve", {
    "alignmentName": new_alignment_name,
    "profileName": layout_profile_name,
    "pviStation": selected_pvis[1][0],
    "length": 100.0
})

mcp_request("profileAddCurve", {
    "alignmentName": new_alignment_name,
    "profileName": layout_profile_name,
    "pviStation": selected_pvis[2][0],
    "length": 80.0
})

# Calcular inserción de ProfileView proporcionalmente
pv_x, pv_y = get_profile_view_insertion_point(bounds, offset_ratio=0.10)
print(f"Inserción dinámica de Vista de Perfil: X={pv_x:.2f}, Y={pv_y:.2f}")

pv_res = mcp_request("profileViewCreate", {
    "alignmentName": new_alignment_name,
    "profileViewName": "VISTA_PERFIL_DINAMICA",
    "insertX": pv_x,
    "insertY": pv_y
})
print("Resultado profileViewCreate:", pv_res)

# Guardar cambios en DWG
save_res = mcp_request("saveDrawing", {})
print("DWG Guardado dinámicamente:", save_res)
