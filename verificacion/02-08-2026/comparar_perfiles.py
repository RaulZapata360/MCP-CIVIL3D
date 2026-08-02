import socket
import json
import math
import os

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

alignment_name = "EJE_CALZADA_OFICIAL"
surf_profile = "PERFIL_TERRENO_OFICIAL"
rasante_profile = "RASANTE_DISENO_OFICIAL"

# Muestreo
sample_surf = mcp_request("sampleProfileElevations", {"alignmentName": alignment_name, "profileName": surf_profile, "interval": 50.0})["result"]["samples"]
sample_ras = mcp_request("sampleProfileElevations", {"alignmentName": alignment_name, "profileName": rasante_profile, "interval": 50.0})["result"]["samples"]

# Generar SVG para la gráfica de perfil
width, height = 900, 300
pad_l, pad_r, pad_t, pad_b = 60, 20, 30, 40

stations = [s['station'] for s in sample_surf]
elev_surf = [s['elevation'] for s in sample_surf]
elev_ras = [s['elevation'] for s in sample_ras]

min_st, max_st = min(stations), max(stations)
min_el = min(min(elev_surf), min(elev_ras)) - 0.5
max_el = max(max(elev_surf), max(elev_ras)) + 0.5

def map_x(st):
    return pad_l + (st - min_st) / (max_st - min_st) * (width - pad_l - pad_r)

def map_y(el):
    return height - pad_b - (el - min_el) / (max_el - min_el) * (height - pad_t - pad_b)

pts_surf_svg = " ".join([f"{map_x(st):.1f},{map_y(el):.1f}" for st, el in zip(stations, elev_surf)])
pts_ras_svg = " ".join([f"{map_x(st):.1f},{map_y(el):.1f}" for st, el in zip(stations, elev_ras)])

# Marcar Grid de Elevaciones y Estaciones
grid_lines = ""
for el_val in range(math.floor(min_el), math.ceil(max_el) + 1):
    y_pos = map_y(el_val)
    grid_lines += f'<line x1="{pad_l}" y1="{y_pos:.1f}" x2="{width - pad_r}" y2="{y_pos:.1f}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3 3"/>'
    grid_lines += f'<text x="{pad_l - 8}" y="{y_pos + 4:.1f}" fill="#94a3b8" font-size="10" text-anchor="end">{el_val}m</text>'

for st_val in range(0, int(max_st) + 1, 100):
    x_pos = map_x(st_val)
    grid_lines += f'<line x1="{x_pos:.1f}" y1="{pad_t}" x2="{x_pos:.1f}" y2="{height - pad_b}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3 3"/>'
    grid_lines += f'<text x="{x_pos:.1f}" y="{height - 15}" fill="#94a3b8" font-size="10" text-anchor="middle">0+{st_val:03d}</text>'

svg_chart = f"""
<svg viewBox="0 0 {width} {height}" style="width: 100%; height: auto; background: rgba(15, 23, 42, 0.6); border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.2);">
    {grid_lines}
    <!-- Terreno (Verde/Azul) -->
    <polyline fill="none" stroke="#10b981" stroke-width="2.5" points="{pts_surf_svg}" />
    <!-- Rasante (Violeta/Magenta) -->
    <polyline fill="none" stroke="#6366f1" stroke-width="2.5" stroke-dasharray="5 3" points="{pts_ras_svg}" />
    
    <!-- Leyenda -->
    <rect x="{width - 240}" y="10" width="12" height="12" fill="#10b981" rx="2" />
    <text x="{width - 220}" y="20" fill="#f8fafc" font-size="12">Superficie Terreno (TIN)</text>

    <rect x="{width - 240}" y="28" width="12" height="12" fill="#6366f1" rx="2" />
    <text x="{width - 220}" y="38" fill="#f8fafc" font-size="12">Rasante de Diseño</text>
</svg>
"""

# HTML
html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comparativa de Perfiles: Terreno vs Rasante</title>
    <style>
        :root {{
            --primary: #6366f1;
            --bg-dark: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.7);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
            --border: rgba(99, 102, 241, 0.2);
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            margin: 0;
            padding: 30px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 2px solid var(--primary);
            padding-bottom: 15px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        h1 {{
            margin: 0;
            font-size: 1.8rem;
            color: #ffffff;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 0.9rem;
        }}
        th {{
            background: rgba(255,255,255,0.05);
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 0.75rem;
        }}
        .diff-pos {{ color: #ef4444; font-weight: 600; }} /* Corte */
        .diff-neg {{ color: #3b82f6; font-weight: 600; }} /* Relleno */
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Comparativa de Perfiles: Terreno vs Rasante</h1>
                <p style="color: var(--text-muted); margin: 5px 0 0 0;">Alineamiento: <code>{alignment_name}</code> | Vista de Perfil creada en Civil 3D</p>
            </div>
        </div>

        <div class="card">
            <h3>Perfil Longitudinal Interactivo</h3>
            {svg_chart}
        </div>

        <div class="card">
            <h3>Tabla Comparativa de Cotas y Desmontes/Terraplenes</h3>
            <table>
                <thead>
                    <tr>
                        <th>Progresiva (m)</th>
                        <th>Cota Terreno (m)</th>
                        <th>Cota Rasante (m)</th>
                        <th>Diferencia / Corte-Relleno (m)</th>
                    </tr>
                </thead>
                <tbody>
"""

for s_surf, s_ras in zip(sample_surf, sample_ras):
    st = s_surf['station']
    z_s = s_surf['elevation']
    z_r = s_ras['elevation']
    diff = z_r - z_s
    diff_str = f"+{diff:.3f} m (Relleno)" if diff >= 0 else f"{diff:.3f} m (Corte)"
    diff_class = "diff-neg" if diff >= 0 else "diff-pos"
    
    html_content += f"""
                    <tr>
                        <td>0+{st:06.2f}</td>
                        <td>{z_s:.3f}</td>
                        <td>{z_r:.3f}</td>
                        <td class="{diff_class}">{diff_str}</td>
                    </tr>
"""

html_content += f"""
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

report_path = r"C:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\OTROS\MCP\Autocad\verificacion\02-08-2026\Informe_Comparativa_Perfiles.html"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print("Reporte de perfiles generado con éxito:", report_path)
