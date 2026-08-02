import socket
import json

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

print("--- Paso 1: Creando ProfileView (Vista de Perfil Longitudinal) en Civil 3D ---")
alignment_name = "EJE_CALZADA_OFICIAL"
profile_view_name = "PERFIL_LONGITUDINAL_CALZADA"

# Puntos de inserción cerca de la alineación
res_pv = mcp_request("profileViewCreate", {
    "alignmentName": alignment_name,
    "profileViewName": profile_view_name,
    "insertX": 12120000.0,
    "insertY": 3531000.0
})

print("Respuesta profileViewCreate:", json.dumps(res_pv, indent=2))

# Muestrear elevaciones del terreno y la rasante a lo largo del eje
print("\n--- Paso 2: Muestreando elevaciones del Perfil de Terreno ---")
res_sample_surf = mcp_request("sampleProfileElevations", {
    "alignmentName": alignment_name,
    "profileName": "PERFIL_TERRENO_OFICIAL",
    "interval": 50.0
})
print("Muestreo Terreno:", json.dumps(res_sample_surf, indent=2))

print("\n--- Paso 3: Muestreando elevaciones del Perfil de Rasante ---")
res_sample_rasante = mcp_request("sampleProfileElevations", {
    "alignmentName": alignment_name,
    "profileName": "RASANTE_DISENO_OFICIAL",
    "interval": 50.0
})
print("Muestreo Rasante:", json.dumps(res_sample_rasante, indent=2))
