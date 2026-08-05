#!/usr/bin/env python3
"""
Unifica por XREF (Insert>Attach) todos los DWG de una carpeta en un solo
"dibujo unificado", para comparacion visual en Civil 3D -- y COMPARTIBLE:
el DWG resultante queda en <carpeta_salida>\\<nombre>.dwg con sus xrefs
apuntando, por RUTA RELATIVA, a <carpeta_salida>\\_xref_src\\sNNN.dwg. Basta
copiar/zippear esa carpeta de salida completa (incluida _xref_src) para que
otra persona la abra en cualquier maquina sin depender de nada local.

No modifica ni copia el contenido real de los DWG fuente hasta el momento de
compartir: _xref_src son hardlinks NTFS (mismo volumen, sin admin) con
nombre corto, porque accoreconsole tokeniza los scripts por CUALQUIER
espacio en blanco (no solo por linea) y los nombres de archivo fuente
(carpeta 02_DWG_Template_HRCP) tienen espacios. Al copiar la carpeta de
salida a otra maquina/zip, los hardlinks se vuelven copias reales
independientes (normal, es justamente lo que se quiere para compartir).

Uso:
  python unify_xref.py <carpeta_fuente> <dwg_salida> [--glob "*.dwg"] [--exclude regex]

Requiere: Windows, mismo volumen NTFS para carpeta_fuente y carpeta_salida,
AutoCAD 2026 accoreconsole.exe, plantilla HRCP (.dwt).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ACCORECONSOLE = r"C:\Program Files\Autodesk\AutoCAD 2026\accoreconsole.exe"
TEMPLATE = r"C:\Users\Usuario\OneDrive\Escritorio\Raul ZOIN\HRCP\Template Oficial\HRCP_C3D_CivilTemplate_V09.dwt"
PORTABILITY_CHECK_ROOT = Path(r"C:\Temp\unify_xref_portcheck")

DEFAULT_EXCLUDE = re.compile(r"_recover|_v2\b|^~\$", re.IGNORECASE)
LINKDIR_NAME = "_xref_src"
TMP_NAME = "_tmp_out.dwg"


def collect_sources(folder: Path, glob: str, exclude: str | None):
    excl = re.compile(exclude, re.IGNORECASE) if exclude else DEFAULT_EXCLUDE
    return sorted(p for p in folder.glob(glob) if p.is_file() and not excl.search(p.name))


def make_hardlinks(files, linkdir: Path):
    linkdir.mkdir(parents=True, exist_ok=True)
    for old in linkdir.glob("*.dwg"):
        old.unlink()
    links = []
    for i, f in enumerate(files, start=1):
        link = linkdir / f"s{i:03d}.dwg"
        try:
            os.link(f, link)  # hardlink: same volume, no admin, no extra disk use
        except OSError as e:
            raise RuntimeError(
                f"No se pudo crear hardlink para {f} "
                f"(¿carpeta_fuente en otro volumen que {linkdir}?): {e}"
            )
        links.append((link, f))
    return links


def build_attach_scr(links, tmp_name: str, scr_path: Path):
    # Every token here is deliberately space-free and expressed RELATIVE to
    # the accoreconsole process's working directory, which run_accoreconsole
    # sets to out_dwg.parent. That sidesteps two separate bugs found earlier:
    #  1) accoreconsole tokenizes .scr files by ANY whitespace, so a spaced
    #     absolute path (source filenames have spaces) breaks mid-token.
    #  2) XREFPATHTYPE=Relative (the default) computes its stored delta
    #     against the CURRENT DIRECTORY at ATTACH time when the host is
    #     still unsaved -- and never recomputes it after SAVEAS. Since we
    #     attach args as bare "_xref_src\\sNNN.dwg" while CWD == the file's
    #     actual final folder, the relative delta comes out correct by
    #     construction, no separate SAVEAS-then-reattach dance needed.
    lines = ["FILEDIA", "0"]
    for i, _ in enumerate(links, start=1):
        rel = f"{LINKDIR_NAME}\\s{i:03d}.dwg"
        lines += ["-XREF", "A", rel, "0,0,0", "1", "", ""]
    lines += ["SAVEAS", "2018", tmp_name, "QUIT"]
    scr_path.write_text("\n".join(lines), encoding="ascii")


def run_accoreconsole(base_dwg, scr_path: Path, log_path: Path, cwd: Path):
    with open(log_path, "w", encoding="utf-8", errors="replace") as log:
        subprocess.run(
            [ACCORECONSOLE, "/i", str(base_dwg), "/s", str(scr_path), "/l", "en-US"],
            stdout=log, stderr=subprocess.STDOUT, timeout=600, cwd=str(cwd),
        )


def list_xrefs(dwg_path: Path, workdir: Path):
    """Reopen dwg_path headless (cwd = dwg_path.parent) and return the list
    of (name, stored_path) tuples from `-XREF ?`, plus the reported total."""
    scr_path = workdir / "list.scr"
    log_path = workdir / "list_log.txt"
    scr_path.write_text("\n".join(["-XREF", "?", "*", "QUIT"]), encoding="ascii")
    run_accoreconsole(dwg_path.name, scr_path, log_path, cwd=dwg_path.parent)
    # accoreconsole writes its redirected stdout as UTF-16LE, not UTF-8 --
    # confirmed by trial: reading as UTF-8 silently parses to zero matches.
    text = log_path.read_text(encoding="utf-16-le", errors="replace")
    entries = re.findall(r'"([^"]+)"\s+Attach\s+(\S.*\.dwg)', text)
    total_match = re.search(r"Total Xref\(s\):\s*(\d+)", text)
    total = int(total_match.group(1)) if total_match else 0
    return entries, total


def verify_portable(final_dwg: Path, linkdir: Path, expected_count: int):
    """Copy the whole deliverable (dwg + _xref_src) to an unrelated scratch
    folder and reopen it from there. This is the actual claim being made
    (\"share this folder and it just works\") so it's what gets tested,
    not just \"paths look relative in the original location\"."""
    PORTABILITY_CHECK_ROOT.mkdir(parents=True, exist_ok=True)
    check_dir = PORTABILITY_CHECK_ROOT / f"chk_{os.getpid()}_{final_dwg.stem}"
    if check_dir.exists():
        shutil.rmtree(check_dir)
    check_dir.mkdir(parents=True)
    shutil.copy2(final_dwg, check_dir / final_dwg.name)
    shutil.copytree(linkdir, check_dir / LINKDIR_NAME)

    copied_dwg = check_dir / final_dwg.name
    entries, total = list_xrefs(copied_dwg, check_dir)

    problems = []
    if total != expected_count or len(entries) != expected_count:
        problems.append(f"total esperado {expected_count}, reportado {total}, listado {len(entries)}")
    for name, stored_path in entries:
        if re.match(r"^[A-Za-z]:\\", stored_path):
            problems.append(f'xref "{name}": ruta guardada es ABSOLUTA ({stored_path}), no portable')
        resolved = (copied_dwg.parent / stored_path).resolve()
        if not resolved.exists():
            problems.append(f'xref "{name}": ruta relativa "{stored_path}" no resuelve tras copiar ({resolved})')

    shutil.rmtree(check_dir, ignore_errors=True)
    return (len(problems) == 0), problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_folder")
    ap.add_argument("output_dwg")
    ap.add_argument("--glob", default="*.dwg")
    ap.add_argument("--exclude", default=None, help="regex adicional para excluir archivos")
    args = ap.parse_args()

    folder = Path(args.source_folder)
    out_dwg = Path(args.output_dwg)
    files = collect_sources(folder, args.glob, args.exclude)
    if not files:
        print(f"Sin archivos que coincidan en {folder}")
        sys.exit(1)

    print(f"Fuente: {folder}  ({len(files)} DWG)")
    for f in files:
        print(f"  - {f.name}")

    out_dwg.parent.mkdir(parents=True, exist_ok=True)
    linkdir = out_dwg.parent / LINKDIR_NAME
    links = make_hardlinks(files, linkdir)

    tmp_path = out_dwg.parent / TMP_NAME
    if tmp_path.exists():
        tmp_path.unlink()
    scr_path = out_dwg.parent / "_attach.scr"
    build_attach_scr(links, TMP_NAME, scr_path)

    log_path = out_dwg.with_suffix(".unify_log.txt")
    run_accoreconsole(TEMPLATE, scr_path, log_path, cwd=out_dwg.parent)

    if not tmp_path.exists():
        print(f"FALLO: no se genero el DWG unificado. Ver log: {log_path}")
        sys.exit(2)

    ok, problems = verify_portable(tmp_path, linkdir, len(links))
    if not ok:
        print("FALLO DE VERIFICACION DE PORTABILIDAD:")
        for p in problems:
            print(f"  - {p}")
        print(f"El DWG intermedio (sin renombrar) quedo en: {tmp_path}")
        sys.exit(3)

    try:
        if out_dwg.exists():
            out_dwg.unlink()
        tmp_path.rename(out_dwg)
    except PermissionError:
        print(f"FALLO: {out_dwg} esta abierto/bloqueado (¿Civil 3D con el archivo abierto?).")
        print(f"El resultado verificado quedo esperando en: {tmp_path}")
        sys.exit(4)
    for junk in (scr_path,):
        junk.unlink(missing_ok=True)

    print(f"OK -> {out_dwg}")
    print(f"   {len(links)} xrefs, ruta relativa, verificados portables (copia+reapertura en carpeta ajena).")
    print(f"   Para compartir: copia/zippea la carpeta completa {out_dwg.parent} (incluye {LINKDIR_NAME}\\).")
    print(f"   Log: {log_path}")


if __name__ == "__main__":
    main()
