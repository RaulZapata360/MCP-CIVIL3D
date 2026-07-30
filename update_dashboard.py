import os
import csv
import json
import re
from datetime import datetime

# Rutas de origen
WORKSPACE_PATH = r"c:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\OTROS\MCP\Autocad"
SERVER_PATH = r"C:\Users\raulz\mcp-servers\civil3d-mcp"

def clean_path(path, base_path):
    rel = os.path.relpath(path, base_path)
    return rel.replace("\\", "/")

def get_skills():
    skills = []
    skills_dir = os.path.join(WORKSPACE_PATH, "skills")
    if not os.path.exists(skills_dir):
        return skills
    
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
                
                skills.append({
                    "name": title,
                    "description": desc,
                    "category": category.capitalize(),
                    "file_path": relative_path
                })
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
    tools_dir = os.path.join(SERVER_PATH, "src", "civil3d_mcp")
    if not os.path.exists(tools_dir):
        return tools
        
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
                            
                            # Dec can be Call like @mcp.tool(...)
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
                                            elif isinstance(kw.value, ast.JoinedStr):
                                                dec_args["description"] = "".join(
                                                    part.value for part in kw.value.values if isinstance(part, ast.Constant)
                                                )
                                            else:
                                                try:
                                                    # Eval string concatenations safely
                                                    dec_args["description"] = eval(compile(ast.Expression(kw.value), '<string>', 'eval'))
                                                except:
                                                    dec_args["description"] = "Herramienta Civil 3D"
                            
                            if is_tool:
                                name = dec_args.get("name", node.name)
                                desc = dec_args.get("description")
                                if not desc:
                                    doc = ast.get_docstring(node)
                                    if doc:
                                        desc = doc.strip().split("\n")[0]
                                    else:
                                        desc = "Herramienta de Civil 3D"
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

def main():
    print("Iniciando escaneo del espacio de trabajo...")
    skills = get_skills()
    matrix, matrix_stats = get_verification_matrix()
    server_tools = get_server_tools()
    graph_stats = get_graphify_stats()
    timeline = get_timeline()
    
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
            "total_server_modules": len(server_tools)
        },
        "skills": skills,
        "matrix": matrix,
        "server_tools": server_tools,
        "graph_stats": graph_stats,
        "timeline": timeline
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
