import socket
import json
import xml.etree.ElementTree as ET
import numpy as np

def mcp_request(method, params=None, timeout=10.0):
    if params is None:
        params = {}
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    }
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect(('127.0.0.1', 8080))
        s.sendall(json.dumps(payload).encode('utf-8'))
        response_bytes = b""
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response_bytes += chunk
            except socket.timeout:
                break
        if response_bytes:
            return json.loads(response_bytes.decode('utf-8'))
        return {}

def main():
    print("=== INICIANDO GENERACIÓN DE ALINEACIÓN Y PERFIL EN SUPERFICIE ===")
    
    # 1. Verificar Superficies Activas
    surfaces_res = mcp_request("listSurfaces")
    print("Superficies detectadas:", surfaces_res)
    
    surface_name = "S001_CAPA2_H4F013"
    alignment_name = "EJE_ALINEACION_SUPERFICIE"
    
    # 2. Verificar Alineamientos Activos
    align_res = mcp_request("listAlignments")
    print("Alineamientos previos:", align_res)
    
    # 3. Definir Puntos sobre la Superficie (Bounding Box: X=12119087 a 12119712, Y=3531168 a 3532198)
    points_over_surface = [
        {"x": 12119712.779, "y": 3531177.244},
        {"x": 12119468.078, "y": 3531250.845},
        {"x": 12119089.189, "y": 3532198.631}
    ]
    
    # Crear Alineación Horizontal sobre la superficie
    create_align_res = mcp_request("createAlignment", {
        "name": alignment_name,
        "points": points_over_surface
    })
    print("Resultado creación alineación:", create_align_res)
    
    # 4. Crear Perfil de Terreno desde la Superficie
    create_prof_res = mcp_request("createProfileFromSurface", {
        "alignmentName": alignment_name,
        "profileName": "PERFIL_TERRENO_SUPERFICIE",
        "surfaceName": surface_name
    })
    print("Resultado creación perfil superficie:", create_prof_res)
    
    # 5. Muestrear elevaciones a lo largo del perfil
    sample_res = mcp_request("sampleProfileElevations", {
        "alignmentName": alignment_name,
        "profileName": "PERFIL_TERRENO_SUPERFICIE",
        "interval": 50.0
    })
    samples = sample_res.get("result", {}).get("samples", [])
    print(f"Muestras de cota obtenidas: {len(samples)} puntos")
    
    # 6. Crear Rasante de Diseño (Layout Profile)
    # Definir PVIs adaptados a la geometría del terreno
    pvis = [
        {"station": 0.0, "elevation": 9.80},
        {"station": 442.08, "elevation": 12.50},
        {"station": 884.17, "elevation": 11.20},
        {"station": 1263.10, "elevation": 13.70}
    ]
    
    create_layout_res = mcp_request("createLayoutProfile", {
        "alignmentName": alignment_name,
        "profileName": "RASANTE_DISENO_PROPUESTA",
        "pvis": pvis
    })
    print("Resultado creación rasante:", create_layout_res)
    
    # Agregar curvas verticales normadas en los PVIs
    # PVI 2: Cresta (L=100m)
    mcp_request("profileAddCurve", {
        "alignmentName": alignment_name,
        "profileName": "RASANTE_DISENO_PROPUESTA",
        "pviIndex": 1,
        "curveLength": 100.0
    })
    
    # PVI 3: Sagrario (L=80m)
    mcp_request("profileAddCurve", {
        "alignmentName": alignment_name,
        "profileName": "RASANTE_DISENO_PROPUESTA",
        "pviIndex": 2,
        "curveLength": 80.0
    })
    
    # 7. Crear Vista de Perfil (ProfileView) ubicada al lado de la superficie (~X=12119850, Y=3531200)
    profile_view_res = mcp_request("profileViewCreate", {
        "alignmentName": alignment_name,
        "profileViewName": "VISTA_PERFIL_SUPERFICIE",
        "insertX": 12119850.0,
        "insertY": 3531200.0,
        "styleName": "Standard"
    })
    print("Resultado creación vista de perfil:", profile_view_res)
    
    # 8. Guardar Cambios en el DWG
    save_res = mcp_request("saveDrawing")
    print("Resultado guardado DWG:", save_res)
    
    print("\n=== PROCESO COMPLETADO SATISFACTORIAMENTE ===")

if __name__ == "__main__":
    main()
