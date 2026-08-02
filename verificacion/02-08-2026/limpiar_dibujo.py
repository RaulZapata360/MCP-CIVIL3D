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

# Guardar cambios y verificar
save_res = mcp_request("saveDrawing", {})
print("Estado del archivo DWG:", save_res)
