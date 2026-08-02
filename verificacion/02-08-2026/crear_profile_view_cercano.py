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

print("--- Colocando ProfileView al lado del alineamiento ---")
# Coordenadas exactas cerca del inicio de la calzada: X = 12119850, Y = 3531200
res_pv = mcp_request("profileViewCreate", {
    "alignmentName": "EJE_CALZADA_OFICIAL",
    "profileViewName": "VISTA_PERFIL_PRINCIPAL",
    "insertX": 12119850.0,
    "insertY": 3531200.0
})

print("Resultado de la creación de la vista de perfil:", json.dumps(res_pv, indent=2))
