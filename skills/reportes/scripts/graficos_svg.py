#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Graficos SVG de apoyo para informes tecnicos: barras, rosa de orientacion y
perfiles (longitudinales o transversales) con sombreado de corte/relleno.

Mismo principio que `plano_svg.py`: el SVG se arma concatenando texto, sin
matplotlib ni ninguna libreria grafica. Comparte paleta y helpers de escape
con `plano_svg` para que un informe que combine plano + graficos se vea como
un solo sistema, no como piezas sueltas.

    from graficos_svg import grafico_barras, grafico_rosa, grafico_perfil

Cada funcion devuelve el SVG como texto (para incrustar inline en HTML) y
no escribe archivo: quien llama decide si lo guarda suelto o lo incrusta.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plano_svg import PALETA, FUENTE, _esc, paso_redondo  # noqa: E402

SERIES_ORDEN = ("serie1", "serie2", "serie3")


def _cabecera(ancho: int, alto: int, C: dict) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
        f'viewBox="0 0 {ancho} {alto}" font-family=\'{FUENTE}\'>',
        f'<rect width="{ancho}" height="{alto}" fill="{C["fondo"]}"/>',
    ]


def _titulos(O: list[str], titulo: str, subtitulo: str, margen: int, C: dict) -> int:
    y = margen
    if titulo:
        O.append(f'<text x="{margen}" y="{y}" font-size="15" font-weight="600" '
                 f'fill="{C["tinta"]}">{_esc(titulo)}</text>')
        y += 18
    if subtitulo:
        O.append(f'<text x="{margen}" y="{y}" font-size="12" '
                 f'fill="{C["tinta2"]}">{_esc(subtitulo)}</text>')
        y += 16
    return y + 6


# --------------------------------------------------------------- barras -----
def grafico_barras(categorias, valores, titulo: str = "", subtitulo: str = "",
                    unidad_val: str = "", colores=None, ancho: int = 760,
                    alto: int = 360, margen: int = 52, tema: str = "claro",
                    valor_fmt=None) -> str:
    """Barras verticales con eje, grilla y valor sobre cada barra.

    `categorias`: etiquetas (una por barra). `valores`: numeros, mismo largo.
    `colores`: lista opcional de roles ('serie1'..) o colores hex, uno por
    barra; por defecto todas usan `serie1`.
    """
    if len(categorias) != len(valores):
        raise ValueError("categorias y valores deben tener el mismo largo")
    if not categorias:
        raise ValueError("grafico_barras necesita al menos una categoria")
    C = PALETA[tema]
    valor_fmt = valor_fmt or (lambda v: f"{v:,.1f}")
    O = _cabecera(ancho, alto, C)
    y0 = _titulos(O, titulo, subtitulo, margen, C)

    pie = alto - 46
    area_h = pie - y0
    area_w = ancho - 2 * margen
    vmax = max(max(valores), 0.0)
    vmax = vmax if vmax > 0 else 1.0
    paso = paso_redondo(vmax / 4.0)
    tope = paso * math.ceil(vmax / paso) if vmax > 0 else paso

    # grilla horizontal con rotulos del eje de valor
    n_lineas = max(1, round(tope / paso))
    for i in range(n_lineas + 1):
        v = i * paso
        y = y0 + area_h - (v / tope) * area_h
        O.append(f'<line x1="{margen}" y1="{y:.1f}" x2="{margen + area_w}" y2="{y:.1f}" '
                 f'stroke="{C["hairline"]}" stroke-width="1"/>')
        O.append(f'<text x="{margen - 8}" y="{y + 4:.1f}" font-size="10.5" '
                 f'fill="{C["muted"]}" text-anchor="end">{v:,.0f}</text>')

    n = len(categorias)
    ancho_slot = area_w / n
    ancho_barra = min(ancho_slot * 0.62, 64)
    for i, (cat, val) in enumerate(zip(categorias, valores)):
        rol = (colores[i] if colores else "serie1")
        color = C.get(rol, rol if str(rol).startswith("#") else C["serie1"])
        h = (max(val, 0.0) / tope) * area_h
        x = margen + i * ancho_slot + (ancho_slot - ancho_barra) / 2
        y = y0 + area_h - h
        O.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{ancho_barra:.1f}" '
                 f'height="{max(h, 0):.1f}" rx="2" fill="{color}"/>')
        if val:
            O.append(f'<text x="{x + ancho_barra / 2:.1f}" y="{y - 6:.1f}" font-size="11" '
                     f'fill="{C["tinta2"]}" text-anchor="middle">{valor_fmt(val)}</text>')
        etiqueta = str(cat)
        O.append(f'<text x="{x + ancho_barra / 2:.1f}" y="{y0 + area_h + 16:.1f}" '
                 f'font-size="11" fill="{C["tinta2"]}" text-anchor="middle">'
                 f'{_esc(etiqueta)}</text>')

    O.append(f'<line x1="{margen}" y1="{y0 + area_h:.1f}" x2="{margen + area_w}" '
             f'y2="{y0 + area_h:.1f}" stroke="{C["borde"]}" stroke-width="1"/>')
    if unidad_val:
        O.append(f'<text x="{margen}" y="{alto - 6}" font-size="10.5" '
                 f'fill="{C["muted"]}">{_esc(unidad_val)}</text>')
    O.append("</svg>")
    return "\n".join(O)


# ----------------------------------------------------------------- rosa -----
def grafico_rosa(sectores_grados, valores, titulo: str = "", unidad_val: str = "",
                  ancho: int = 480, alto: int = 480, tema: str = "claro") -> str:
    """Diagrama de rosa (orientacion / aspecto), norte arriba, sentido horario.

    `sectores_grados`: centro de cada sector en grados (0=N, 90=E, ...).
    `valores`: magnitud (area, %, conteo) por sector, mismo largo.
    """
    if len(sectores_grados) != len(valores):
        raise ValueError("sectores_grados y valores deben tener el mismo largo")
    if not sectores_grados:
        raise ValueError("grafico_rosa necesita al menos un sector")
    C = PALETA[tema]
    O = _cabecera(ancho, alto, C)
    y0 = _titulos(O, titulo, "", 20, C)

    cx, cy = ancho / 2, y0 + (alto - y0 - 30) / 2 + 6
    radio = min(cx, cy - y0) - 34
    vmax = max(valores) or 1.0
    n = len(sectores_grados)
    ancho_sector = 360.0 / n if n > 1 else 40.0

    # anillos de referencia
    for frac in (0.25, 0.5, 0.75, 1.0):
        O.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radio * frac:.1f}" '
                 f'fill="none" stroke="{C["hairline"]}" stroke-width="1"/>')
    O.append(f'<text x="{cx + 3:.1f}" y="{cy - radio - 4:.1f}" font-size="10" '
             f'fill="{C["muted"]}">{vmax:,.1f} {_esc(unidad_val)}</text>')

    def punto(deg, r):
        rad = math.radians(deg)
        return cx + r * math.sin(rad), cy - r * math.cos(rad)

    for centro, val in zip(sectores_grados, valores):
        r = (val / vmax) * radio if vmax else 0.0
        a0, a1 = centro - ancho_sector / 2, centro + ancho_sector / 2
        p0 = punto(a0, r)
        p1 = punto(a1, r)
        large_arc = 1 if (a1 - a0) > 180 else 0
        d = (f"M {cx:.2f} {cy:.2f} L {p0[0]:.2f} {p0[1]:.2f} "
             f"A {r:.2f} {r:.2f} 0 {large_arc} 1 {p1[0]:.2f} {p1[1]:.2f} Z")
        O.append(f'<path d="{d}" fill="{C["serie1"]}" fill-opacity="0.82" '
                 f'stroke="{C["fondo"]}" stroke-width="1"/>')

    # rotulos cardinales
    for lbl, deg in (("N", 0), ("E", 90), ("S", 180), ("O", 270)):
        px, py = punto(deg, radio + 16)
        O.append(f'<text x="{px:.1f}" y="{py + 4:.1f}" font-size="12" font-weight="700" '
                 f'fill="{C["tinta"]}" text-anchor="middle">{lbl}</text>')

    O.append("</svg>")
    return "\n".join(O)


# --------------------------------------------------------------- perfil -----
def grafico_perfil(estaciones, series, titulo: str = "", subtitulo: str = "",
                    unidad_est: str = "m", unidad_elev: str = "m",
                    ancho: int = 900, alto: int = 340, margen: int = 56,
                    tema: str = "claro", sombrear_entre: tuple[str, str] | None = None,
                    exagerar_vertical: bool = True) -> str:
    """Linea de estacion (o desplante) vs cota. Sirve para perfil longitudinal
    y para seccion transversal (usar offset como "estacion").

    `series`: lista de dicts {"nombre", "valores" (mismo largo que
    `estaciones`, con None para huecos), "rol"}. Si `sombrear_entre` trae dos
    nombres de serie, el area entre ambas se sombrea: por debajo de la
    primera (corte) en tinta de serie2, por encima (relleno) en tinta de
    serie1 -- convencion de disenio/rasante sobre existente.
    """
    if not estaciones:
        raise ValueError("grafico_perfil necesita al menos una estacion")
    C = PALETA[tema]
    O = _cabecera(ancho, alto, C)
    y0 = _titulos(O, titulo, subtitulo, margen, C)

    pie = alto - 40
    area_h = pie - y0
    area_w = ancho - 2 * margen

    e0, e1 = min(estaciones), max(estaciones)
    todos_val = [v for s in series for v in s["valores"] if v is not None]
    if not todos_val:
        raise ValueError("ninguna serie tiene valores para graficar")
    zmin, zmax = min(todos_val), max(todos_val)
    if zmax - zmin < 1e-9:
        zmin, zmax = zmin - 1, zmax + 1
    margen_z = (zmax - zmin) * 0.1
    zmin, zmax = zmin - margen_z, zmax + margen_z

    def tx(e):
        return margen + (e - e0) / max(e1 - e0, 1e-9) * area_w

    def ty(z):
        return y0 + area_h - (z - zmin) / (zmax - zmin) * area_h

    # grilla horizontal (cotas)
    paso_z = paso_redondo((zmax - zmin) / 5.0)
    z = math.ceil(zmin / paso_z) * paso_z
    while z <= zmax:
        y = ty(z)
        O.append(f'<line x1="{margen}" y1="{y:.1f}" x2="{margen + area_w}" y2="{y:.1f}" '
                 f'stroke="{C["hairline"]}" stroke-width="1"/>')
        O.append(f'<text x="{margen - 8}" y="{y + 3.5:.1f}" font-size="10" '
                 f'fill="{C["muted"]}" text-anchor="end">{z:,.1f}</text>')
        z += paso_z

    # grilla vertical (estaciones)
    paso_e = paso_redondo((e1 - e0) / 6.0) if e1 > e0 else 1.0
    e = math.ceil(e0 / paso_e) * paso_e if paso_e else e0
    while e <= e1:
        x = tx(e)
        O.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{pie}" '
                 f'stroke="{C["hairline"]}" stroke-width="1"/>')
        O.append(f'<text x="{x:.1f}" y="{pie + 16}" font-size="10" fill="{C["muted"]}" '
                 f'text-anchor="middle">{e:,.0f}</text>')
        e += (paso_e or 1.0)

    series_por_nombre = {s["nombre"]: s for s in series}

    def tramos_validos(vals):
        tramo = []
        for e, v in zip(estaciones, vals):
            if v is None:
                if len(tramo) > 1:
                    yield tramo
                tramo = []
            else:
                tramo.append((e, v))
        if len(tramo) > 1:
            yield tramo

    if sombrear_entre and all(n in series_por_nombre for n in sombrear_entre):
        n_sup, n_inf = sombrear_entre
        v_sup = series_por_nombre[n_sup]["valores"]
        v_inf = series_por_nombre[n_inf]["valores"]
        for i in range(len(estaciones) - 1):
            a_sup, b_sup = v_sup[i], v_sup[i + 1]
            a_inf, b_inf = v_inf[i], v_inf[i + 1]
            if None in (a_sup, b_sup, a_inf, b_inf):
                continue
            relleno = (a_sup - a_inf) >= 0 or (b_sup - b_inf) >= 0
            color = C["serie1"] if relleno else C["serie2"]
            e_a, e_b = estaciones[i], estaciones[i + 1]
            d = (f"M {tx(e_a):.2f} {ty(a_sup):.2f} L {tx(e_b):.2f} {ty(b_sup):.2f} "
                 f"L {tx(e_b):.2f} {ty(b_inf):.2f} L {tx(e_a):.2f} {ty(a_inf):.2f} Z")
            O.append(f'<path d="{d}" fill="{color}" fill-opacity="0.35" stroke="none"/>')
        O.append(f'<g font-size="11" fill="{C["tinta2"]}">'
                 f'<rect x="{margen}" y="{y0 - 24}" width="12" height="10" fill="{C["serie1"]}" fill-opacity="0.5"/>'
                 f'<text x="{margen + 16}" y="{y0 - 15}">relleno</text>'
                 f'<rect x="{margen + 74}" y="{y0 - 24}" width="12" height="10" fill="{C["serie2"]}" fill-opacity="0.5"/>'
                 f'<text x="{margen + 90}" y="{y0 - 15}">corte</text></g>')

    for i, s in enumerate(series):
        rol = s.get("rol") or SERIES_ORDEN[i % len(SERIES_ORDEN)]
        color = C.get(rol, rol if str(rol).startswith("#") else C["serie1"])
        for tramo in tramos_validos(s["valores"]):
            d = " ".join(("M " if j == 0 else "L ") + f"{tx(e):.2f} {ty(v):.2f}"
                         for j, (e, v) in enumerate(tramo))
            O.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
        lx = margen + area_w - 150 + (i * 0)
        ly = y0 - 24 + i * 16
        O.append(f'<line x1="{lx:.1f}" y1="{ly - 3:.1f}" x2="{lx + 20:.1f}" y2="{ly - 3:.1f}" '
                 f'stroke="{color}" stroke-width="2.5"/>')
        O.append(f'<text x="{lx + 26:.1f}" y="{ly:.1f}" font-size="11" '
                 f'fill="{C["tinta2"]}">{_esc(s["nombre"])}</text>')

    O.append(f'<rect x="{margen}" y="{y0}" width="{area_w:.1f}" height="{area_h:.1f}" '
             f'fill="none" stroke="{C["borde"]}" stroke-width="1"/>')
    O.append(f'<text x="{margen + area_w}" y="{alto - 6}" font-size="10.5" '
             f'fill="{C["muted"]}" text-anchor="end">estacion/desplante ({_esc(unidad_est)}) '
             f'vs cota ({_esc(unidad_elev)})</text>')
    O.append("</svg>")
    return "\n".join(O)
