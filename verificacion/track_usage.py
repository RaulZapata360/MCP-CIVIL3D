import os
import sys
import json
import argparse
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
USAGE_FILE = os.path.join(CURRENT_DIR, "skill_usage.json")
SESSION_FILE = os.path.join(CURRENT_DIR, "session_logs.json")
ROOT_DIR = os.path.dirname(CURRENT_DIR)

def load_usage_data():
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: error loading usage file: {e}")
    return {"skills": {}, "mcp_tools": {}}

def save_usage_data(data):
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving usage file: {e}")

def load_session_logs():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: error loading session logs: {e}")
    return []

def save_session_logs(logs):
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving session logs: {e}")

def log_skill_usage(skill_name, status="OK"):
    data = load_usage_data()
    skills = data.setdefault("skills", {})
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if skill_name not in skills:
        skills[skill_name] = {
            "name": skill_name,
            "uses": 0,
            "success": 0,
            "last_used": now_str
        }
        
    skills[skill_name]["uses"] += 1
    skills[skill_name]["last_used"] = now_str
    if status.upper() == "OK":
        skills[skill_name]["success"] = skills[skill_name].get("success", 0) + 1
        
    save_usage_data(data)
    print(f"[Telemetry] Skill '{skill_name}' usage logged. Total uses: {skills[skill_name]['uses']}")
    return skills[skill_name]

def log_tool_usage(tool_name):
    data = load_usage_data()
    mcp_tools = data.setdefault("mcp_tools", {})
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if tool_name not in mcp_tools:
        mcp_tools[tool_name] = {
            "name": tool_name,
            "uses": 0,
            "last_used": now_str
        }
        
    mcp_tools[tool_name]["uses"] += 1
    mcp_tools[tool_name]["last_used"] = now_str
    
    save_usage_data(data)
    print(f"[Telemetry] Tool '{tool_name}' usage logged. Total uses: {mcp_tools[tool_name]['uses']}")
    return mcp_tools[tool_name]

def log_session_audit(task, corrections="", warnings="", limitations="", status="OK"):
    logs = load_session_logs()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    entry = {
        "timestamp": now_str,
        "task": task or "Sesión de análisis y verificación",
        "corrections": corrections or "Ninguna corrección registrada",
        "warnings": warnings or "Sin advertencias criticas",
        "limitations": limitations or "Sin limitaciones reportadas",
        "status": status.upper()
    }
    
    logs.insert(0, entry) # Insert at beginning (newest first)
    save_session_logs(logs)
    print(f"[Session Audit Log] Registered entry for task: '{task}'")
    return entry

def main():
    parser = argparse.ArgumentParser(description="Medidor de Uso y Bitácora de Sesión para Asistentes IA")
    parser.add_argument("--skill", type=str, help="Nombre de la skill utilizada")
    parser.add_argument("--tool", type=str, help="Nombre de la herramienta MCP utilizada")
    parser.add_argument("--status", type=str, default="OK", help="Resultado de la ejecución (OK, WIP, FALLA)")
    
    # Arguments for session audit log
    parser.add_argument("--log-session", action="store_true", help="Registrar entrada en la bitácora de sesión de IA")
    parser.add_argument("--task", type=str, default="", help="Descripción del trabajo / uso realizado")
    parser.add_argument("--corrections", type=str, default="", help="Correcciones realizadas durante la sesión")
    parser.add_argument("--warnings", type=str, default="", help="Advertencias encontradas (ej: auditoría de unidades)")
    parser.add_argument("--limitations", type=str, default="", help="Limitaciones o fallas de herramientas descubiertas")
    
    parser.add_argument("--sync", action="store_true", help="Sincronizar dashboard inmediatamente")
    
    args = parser.parse_args()
    
    if args.skill:
        log_skill_usage(args.skill, args.status)
    if args.tool:
        log_tool_usage(args.tool)
    if args.log_session:
        log_session_audit(args.task, args.corrections, args.warnings, args.limitations, args.status)
        
    if args.sync or (args.skill or args.tool or args.log_session):
        # Trigger dashboard update
        import subprocess
        update_script = os.path.join(ROOT_DIR, "update_dashboard.py")
        if os.path.exists(update_script):
            subprocess.run([sys.executable, update_script], cwd=ROOT_DIR)

if __name__ == "__main__":
    main()
