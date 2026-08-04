import os
import csv
import json
import re
from datetime import datetime

# Rutas de origen dinámicas para soporte multidispositivo
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_PATH = CURRENT_DIR

# Buscar servidor MCP local. Solo rutas relativas al repositorio: las rutas absolutas
# que habia aqui apuntaban a maquinas concretas (incluida otra distinta a esta) y no
# funcionan al clonar en otro PC.
POSSIBLE_SERVER_PATHS = [
    os.path.join(CURRENT_DIR, "server"),
    os.path.abspath(os.path.join(CURRENT_DIR, "..", "Civil3D-mcp")),
]

SERVER_PATH = next((p for p in POSSIBLE_SERVER_PATHS if os.path.exists(p)), POSSIBLE_SERVER_PATHS[0])

def clean_path(path, base_path):
    rel = os.path.relpath(path, base_path)
    return rel.replace("\\", "/")

def recover_usage_from_dashboard():
    """Rescata los contadores del ultimo dashboard_data.json generado.

    Red de seguridad: si falta skill_usage.json, sin esto el dashboard se
    regeneraria con todo a 0 y SOBRESCRIBIRIA el historial de uso, que es el
    medidor de confianza de cada skill. Perdida silenciosa e irreversible.
    """
    dash = os.path.join(WORKSPACE_PATH, "dashboard_data.json")
    if not os.path.exists(dash):
        return {}
    try:
        with open(dash, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    recovered = {}
    for item in data.get("skills", []):
        if item.get("uses", 0) > 0:
            recovered[item["name"]] = {
                "uses": item["uses"],
                "success": item.get("success", item["uses"]),
                "last_used": item.get("last_used", "Sin registrar"),
            }
    return recovered


def load_usage_telemetry():
    usage_file = os.path.join(WORKSPACE_PATH, "verificacion", "skill_usage.json")
    if os.path.exists(usage_file):
        try:
            with open(usage_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando skill_usage.json: {e}")

    # No hay telemetria: antes de dar todo por 0, intentar rescatar lo ultimo conocido.
    recovered = recover_usage_from_dashboard()
    if recovered:
        total = sum(s["uses"] for s in recovered.values())
        print(f"AVISO: falta verificacion/skill_usage.json.")
        print(f"       Se rescataron {len(recovered)} skills ({total} usos) del dashboard anterior")
        print(f"       y se regenera el archivo para no perder el medidor de confianza.")
        os.makedirs(os.path.join(WORKSPACE_PATH, "verificacion"), exist_ok=True)
        try:
            with open(usage_file, "w", encoding="utf-8") as f:
                json.dump({"skills": recovered, "mcp_tools": {}}, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            print(f"       (no se pudo reescribir skill_usage.json: {e})")
        return {"skills": recovered, "mcp_tools": {}}

    return {"skills": {}, "mcp_tools": {}}

def get_skills():
    skills = []
    skills_dir = os.path.join(WORKSPACE_PATH, "skills")
    if not os.path.exists(skills_dir):
        return skills
        
    telemetry = load_usage_telemetry()
    skills_data = telemetry.get("skills", {})
    
    for root, dirs, files in os.walk(skills_dir):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                relative_path = clean_path(file_path, WORKSPACE_PATH)
                category = os.path.basename(root)
                
                # Leer frontmatter simple
                title = file
                desc = "Sin descripción"
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Intentar leer frontmatter yaml
                    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
                    if fm_match:
                        fm_text = fm_match.group(1)
                        for line in fm_text.split("\n"):
                            if ":" in line:
                                k, v = line.split(":", 1)
                                k = k.strip().lower()
                                v = v.strip().strip('"').strip("'")
                                if k == "name":
                                    title = v
                                elif k == "description":
                                    desc = v
                    else:
                        # Si no hay yaml, tomar el primer H1
                        h1_match = re.search(r"^#\s+(.*)$", content, re.MULTILINE)
                        if h1_match:
                            title = h1_match.group(1).strip()
                except Exception as e:
                    print(f"Error leyendo skill {file}: {e}")
                
                # Extraer telemetría para esta skill (por nombre o identificador)
                key = title.lower().replace(" ", "_")
                t_info = skills_data.get(key, skills_data.get(title, {}))
                uses = t_info.get("uses", 0)
                success = t_info.get("success", uses)
                last_used = t_info.get("last_used", "Sin registrar")
                
                if uses >= 15:
                    reliability = "Alta (Probada)"
                    rel_code = "HIGH"
                elif uses >= 5:
                    reliability = "Media (Frecuente)"
                    rel_code = "MEDIUM"
                elif uses > 0:
                    reliability = "Inicial (Por validar)"
                    rel_code = "LOW"
                else:
                    reliability = "Sin uso"
                    rel_code = "NONE"
                
                skills.append({
                    "name": title,
                    "description": desc,
                    "category": category.capitalize(),
                    "file_path": relative_path,
                    "uses": uses,
                    "success": success,
                    "last_used": last_used,
                    "reliability": reliability,
                    "rel_code": rel_code
                })
                
    # Ordenar por usos descendente
    skills.sort(key=lambda s: s["uses"], reverse=True)
    return skills

def get_verification_matrix():
    matrix = []
    stats = {"OK": 0, "FALLA": 0, "WIP": 0, "total": 0}
    matrix_csv = os.path.join(WORKSPACE_PATH, "verificacion", "matriz.csv")
    if not os.path.exists(matrix_csv):
        return matrix, stats
        
    try:
        with open(matrix_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                res = row.get("resultado", "").upper()
                if res in stats:
                    stats[res] += 1
                else:
                    stats[res] = 1
                stats["total"] += 1
                matrix.append({
                    "servidor": row.get("servidor", ""),
                    "tool": row.get("tool", ""),
                    "version_c3d": row.get("version_c3d", ""),
                    "dwg_prueba": row.get("dwg_prueba", ""),
                    "resultado": res,
                    "evidencia": row.get("evidencia", ""),
                    "fecha": row.get("fecha", ""),
                    "notas": row.get("notas", "")
                })
    except Exception as e:
        print(f"Error leyendo matriz CSV: {e}")
    return matrix, stats

def get_server_tools():
    import ast
    tools = []
    
    # 1. Probar estructura TypeScript (src/tools/domains/*.ts)
    ts_domains_dir = os.path.join(SERVER_PATH, "src", "tools", "domains")
    if os.path.exists(ts_domains_dir):
        for file in sorted(os.listdir(ts_domains_dir)):
            if file.endswith("Domain.ts"):
                file_path = os.path.join(ts_domains_dir, file)
                domain_name = file.replace("Domain.ts", "").capitalize()
                file_tools = []
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Extraer bloques de herramientas toolName / description
                    tool_matches = re.findall(
                        r'toolName:\s*"([^"]+)",?\s*(?:displayName:[^,]+,?\s*)?description:\s*"([^"]+)"',
                        content, re.DOTALL
                    )
                    for t_name, t_desc in tool_matches:
                        file_tools.append({
                            "name": t_name,
                            "description": t_desc.replace("\n", " ").strip()
                        })
                except Exception as e:
                    print(f"Error parseando TS domain {file}: {e}")
                
                tools.append({
                    "module": domain_name,
                    "file": file,
                    "tools_list": file_tools,
                    "count": len(file_tools)
                })
        if tools:
            return tools

    # 2. Probar estructura Python (src/civil3d_mcp/tools_*.py)
    tools_dir = os.path.join(SERVER_PATH, "src", "civil3d_mcp")
    if os.path.exists(tools_dir):
        for file in os.listdir(tools_dir):
            if file.startswith("tools_") and file.endswith(".py"):
                file_path = os.path.join(tools_dir, file)
                tool_name = file.replace("tools_", "").replace(".py", "").capitalize()
                file_tools = []
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=file_path)
                    
                    class ToolVisitor(ast.NodeVisitor):
                        def visit_FunctionDef(self, node):
                            self.check_function(node)
                            self.generic_visit(node)
                        def visit_AsyncFunctionDef(self, node):
                            self.check_function(node)
                            self.generic_visit(node)
                            
                        def check_function(self, node):
                            for dec in node.decorator_list:
                                is_tool = False
                                dec_args = {}
                                if isinstance(dec, ast.Call):
                                    func = dec.func
                                    if isinstance(func, ast.Attribute) and func.attr == "tool":
                                        is_tool = True
                                    elif isinstance(func, ast.Name) and func.id == "tool":
                                        is_tool = True
                                        
                                    if is_tool:
                                        for kw in dec.keywords:
                                            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                                dec_args["name"] = kw.value.value
                                            elif kw.arg == "description":
                                                if isinstance(kw.value, ast.Constant):
                                                    dec_args["description"] = kw.value.value
                                
                                if is_tool:
                                    name = dec_args.get("name", node.name)
                                    desc = dec_args.get("description", "Herramienta Civil 3D")
                                    file_tools.append({
                                        "name": name,
                                        "description": desc
                                    })
                    
                    visitor = ToolVisitor()
                    visitor.visit(tree)
                except Exception as e:
                    print(f"Error parseando AST en {file}: {e}")
                    
                tools.append({
                    "module": tool_name,
                    "file": file,
                    "tools_list": file_tools,
                    "count": len(file_tools)
                })
    return tools

def get_graphify_stats():
    stats = {"nodes": 0, "edges": 0, "communities": 0, "active": False}
    graph_json = os.path.join(WORKSPACE_PATH, "graphify-out", "graph.json")
    if os.path.exists(graph_json):
        try:
            with open(graph_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            stats["active"] = True
            stats["nodes"] = len(data.get("nodes", []))
            stats["edges"] = len(data.get("edges", []))
            # Calcular comunidades distintas
            cids = set()
            for n in data.get("nodes", []):
                cid = n.get("community")
                if cid is not None:
                    cids.add(cid)
            stats["communities"] = len(cids)
        except Exception as e:
            print(f"Error leyendo grafo de Graphify: {e}")
    return stats

def get_timeline():
    timeline = []
    seen_files = set()
    
    # Listas de extensiones y carpetas excluidas
    exclude_dirs = {".git", ".venv", "node_modules", "__pycache__", "graphify-out", ".agents"}
    exclude_exts = {".pyc", ".png", ".jpg", ".zip", ".log", ".scr", ".gitkeep"}
    
    # Recorrer workspace local
    for root, dirs, files in os.walk(WORKSPACE_PATH):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if any(file.endswith(ext) for ext in exclude_exts) or file.startswith("."):
                continue
            file_path = os.path.join(root, file)
            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime)
            rel_path = clean_path(file_path, WORKSPACE_PATH)
            timeline.append({
                "file": file,
                "path": rel_path,
                "source": "Workspace",
                "mtime": mtime,
                "date": dt.strftime("%Y-%m-%d %H:%M"),
                "date_raw": dt.isoformat()
            })
            
    # Recorrer servidor externo
    for root, dirs, files in os.walk(SERVER_PATH):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if any(file.endswith(ext) for ext in exclude_exts) or file.startswith("."):
                continue
            file_path = os.path.join(root, file)
            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime)
            rel_path = clean_path(file_path, SERVER_PATH)
            timeline.append({
                "file": file,
                "path": "civil3d-mcp/" + rel_path,
                "source": "Server Codebase",
                "mtime": mtime,
                "date": dt.strftime("%Y-%m-%d %H:%M"),
                "date_raw": dt.isoformat()
            })
            
    # Ordenar por mtime desc y tomar los primeros 12
    timeline.sort(key=lambda x: x["mtime"], reverse=True)
    return timeline[:12]

def get_session_logs():
    session_file = os.path.join(WORKSPACE_PATH, "verificacion", "session_logs.json")
    if os.path.exists(session_file):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando session_logs.json: {e}")
    return []

def main():
    print("Iniciando escaneo del espacio de trabajo...")
    skills = get_skills()
    matrix, matrix_stats = get_verification_matrix()
    server_tools = get_server_tools()
    graph_stats = get_graphify_stats()
    timeline = get_timeline()
    session_logs = get_session_logs()
    
    # Compilar estadísticas de servidor
    total_server_tools = sum(m["count"] for m in server_tools)
    
    data = {
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {
            "total_skills": len(skills),
            "total_tests": matrix_stats["total"],
            "tests_ok": matrix_stats.get("OK", 0),
            "tests_falla": matrix_stats.get("FALLA", 0),
            "tests_wip": matrix_stats.get("WIP", 0),
            "total_server_tools": total_server_tools,
            "total_server_modules": len(server_tools),
            "total_sessions": len(session_logs)
        },
        "skills": skills,
        "matrix": matrix,
        "server_tools": server_tools,
        "graph_stats": graph_stats,
        "timeline": timeline,
        "session_logs": session_logs
    }
    
    output_file = os.path.join(WORKSPACE_PATH, "dashboard_data.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    js_output_file = os.path.join(WORKSPACE_PATH, "dashboard_data.js")
    with open(js_output_file, "w", encoding="utf-8") as f:
        f.write("window.DASHBOARD_DATA = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n")
        
    print(f"Escaneo completo. Datos guardados en {output_file} y {js_output_file}")

if __name__ == "__main__":
    main()
