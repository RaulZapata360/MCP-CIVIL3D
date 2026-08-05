#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sistema de planos SVG de verificacion para Civil 3D / topografia.

Escribe SVG como texto plano: no necesita matplotlib, cairo ni ninguna libreria
grafica. Sirve como libreria (importar PlanoSVG) y como herramienta de linea de
comandos para dibujar un LandXML y/o un DXF sin escribir codigo.

    from plano_svg import PlanoSVG
    p = PlanoSVG(titulo="Superficie X", unidad_lin="m")
    p.poligonos(triangulos, rol="contexto", etiqueta="TIN original")
    p.poligonos(recorte, rol="serie1", etiqueta="Area interior")
    p.lineas([perimetro], rol="serie2", etiqueta="Perimetro", cerrar=True)
    p.guardar("plano.svg")

Reglas de color: paleta categorica validada (ver bloque PALETA). Los roles de
serie se asignan en orden fijo, nunca ciclado; el contexto usa tinta de chrome,
no un color de serie; los textos van en tinta, nunca en el color de la serie.
"""
from __future__ import annotations

import math
import os
import sys

# --------------------------------------------------------------------- PALETA --
# Paleta de referencia validada con el validador de la skill dataviz:
# categorica (slots 1-2) PASS en los 5 chequeos, claro (#ffffff) y oscuro
# (#1a1a19). Los slots se usan en orden fijo: serie1, serie2, serie3.
PALETA = {
    "claro": {
        "fondo": "#ffffff",
        "tinta": "#0b0b0b",
        "tinta2": "#52514e",
        "muted": "#898781",
        "hairline": "#e1e0d9",
        "borde": "#c3c2b7",
        "contexto_relleno": "#ededea",
        "contexto_borde": "#c3c2b7",
        "serie1": "#2a78d6",
        "serie2": "#eb6834",
        "serie3": "#1baf7a",
        # rampa secuencial de un solo tono (azul), claro -> oscuro
        "rampa": ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
    },
    "oscuro": {
        "fondo": "#1a1a19",
        "tinta": "#ffffff",
        "tinta2": "#c3c2b7",
        "muted": "#898781",
        "hairline": "#2c2c2a",
        "borde": "#383835",
        "contexto_relleno": "#2c2c2a",
        "contexto_borde": "#4a4a46",
        "serie1": "#3987e5",
        "serie2": "#d95926",
        "serie3": "#199e70",
        # sobre fondo oscuro la rampa se invierte para que el maximo siga siendo
        # el extremo de mayor contraste; la luminosidad se mantiene monotona.
        "rampa": ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"],
    },
}

FUENTE = 'system-ui, -apple-system, "Segoe UI", Arial, sans-serif'


def _esc(t) -> str:
    """Escapa texto para XML. Sin esto un nombre con & rompe el SVG."""
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _mezclar(c1: str, c2: str, t: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def color_rampa(v: float, vmin: float, vmax: float, rampa) -> str:
    """Interpola un valor dentro de la rampa secuencial."""
    if vmax <= vmin:
        return rampa[len(rampa) // 2]
    f = min(1.0, max(0.0, (v - vmin) / (vmax - vmin))) * (len(rampa) - 1)
    i = min(len(rampa) - 2, int(f))
    return _mezclar(rampa[i], rampa[i + 1], f - i)


def paso_redondo(objetivo: float) -> float:
    """Numero redondo 1/2/5 x 10^n mas cercano, para la escala grafica."""
    if objetivo <= 0:
        return 1.0
    exp = math.floor(math.log10(objetivo))
    return min((1, 2, 5, 10), key=lambda m: abs(m * 10 ** exp - objetivo)) * 10 ** exp


# ------------------------------------------------------------------ PLANO SVG --
class PlanoSVG:
    """Plano en planta con escala unica, norte, escala grafica y leyenda.

    Todo se guarda en coordenadas de terreno y se transforma recien al guardar,
    asi el encuadre sale del contenido y no hay que conocerlo de antemano.
    """

    ALTO_TITULO = 64
    ALTO_PIE = 58

    def __init__(self, titulo: str = "", subtitulo: str = "", unidad_lin: str = "m",
                 ancho: int = 1200, alto: int = 900, margen: int = 44,
                 tema: str = "claro"):
        if tema not in PALETA:
            raise ValueError(f"tema desconocido: {tema!r} (usa 'claro' u 'oscuro')")
        self.titulo, self.subtitulo, self.unidad = titulo, subtitulo, unidad_lin
        self.ancho, self.alto, self.margen = ancho, alto, margen
        self.tema, self.C = tema, PALETA[tema]
        self._capas = []          # dicts con geometria en coordenadas mundo
        self._leyenda = []        # (tipo, color, etiqueta)
        self._gradiente = None    # (vmin, vmax, titulo)
        self._notas = []

    # ---------------------------------------------------------------- entradas
    def _rol_color(self, rol: str) -> str:
        if rol == "contexto":
            return self.C["contexto_relleno"]
        if rol not in self.C:
            raise ValueError(f"rol desconocido: {rol!r}")
        return self.C[rol]

    def poligonos(self, anillos, rol: str = "serie1", etiqueta: str | None = None,
                  opacidad: float = 1.0):
        """anillos: iterable de listas [(x, y), ...] en coordenadas de terreno."""
        anillos = [list(a) for a in anillos if len(a) >= 3]
        if not anillos:
            return self
        color = self._rol_color(rol)
        borde = self.C["contexto_borde"] if rol == "contexto" else color
        self._capas.append(dict(tipo="poly", anillos=anillos, relleno=color,
                                borde=borde, grosor=0.5 if rol == "contexto" else 0.6,
                                opacidad=opacidad))
        if etiqueta:
            self._leyenda.append(("relleno", color, etiqueta))
        return self

    def poligonos_graduados(self, anillos_valores, vmin=None, vmax=None,
                            titulo_escala: str = "", etiqueta: str | None = None):
        """anillos_valores: iterable de (anillo, valor). Rampa secuencial de un tono."""
        items = [(list(a), float(v)) for a, v in anillos_valores if len(a) >= 3]
        if not items:
            return self
        vs = [v for _, v in items]
        vmin = min(vs) if vmin is None else vmin
        vmax = max(vs) if vmax is None else vmax
        anillos, colores = [], []
        for a, v in items:
            anillos.append(a)
            colores.append(color_rampa(v, vmin, vmax, self.C["rampa"]))
        self._capas.append(dict(tipo="poly_multi", anillos=anillos, colores=colores,
                                grosor=0.0, opacidad=1.0))
        self._gradiente = (vmin, vmax, titulo_escala or etiqueta or "")
        return self

    def lineas(self, polilineas, rol: str = "serie2", etiqueta: str | None = None,
               grosor: float = 2.0, cerrar: bool = False, guion: str | None = None):
        polilineas = [list(p) for p in polilineas if len(p) >= 2]
        if not polilineas:
            return self
        color = self._rol_color(rol)
        self._capas.append(dict(tipo="linea", polilineas=polilineas, borde=color,
                                grosor=grosor, cerrar=cerrar, guion=guion))
        if etiqueta:
            self._leyenda.append(("linea", color, etiqueta))
        return self

    def puntos(self, coords, rol: str = "serie2", etiqueta: str | None = None,
               radio: float = 4.0, rotulos=None):
        coords = list(coords)
        if not coords:
            return self
        color = self._rol_color(rol)
        self._capas.append(dict(tipo="punto", coords=coords, relleno=color,
                                radio=radio, rotulos=list(rotulos) if rotulos else None))
        if etiqueta:
            self._leyenda.append(("punto", color, etiqueta))
        return self

    def nota(self, texto: str):
        self._notas.append(texto)
        return self

    # ------------------------------------------------------------- transformar
    def _bbox(self):
        xs, ys = [], []
        for c in self._capas:
            if c["tipo"] in ("poly", "poly_multi"):
                for a in c["anillos"]:
                    xs += [p[0] for p in a]
                    ys += [p[1] for p in a]
            elif c["tipo"] == "linea":
                for p in c["polilineas"]:
                    xs += [q[0] for q in p]
                    ys += [q[1] for q in p]
            else:
                xs += [p[0] for p in c["coords"]]
                ys += [p[1] for p in c["coords"]]
        if not xs:
            raise ValueError("El plano no tiene geometria que dibujar.")
        return min(xs), min(ys), max(xs), max(ys)

    def _transformar(self):
        """Devuelve (tx, escala, marco). El marco es el area de dibujo en pixeles.

        Ojo: el origen del contenido (ox, oy) esta centrado dentro del marco y no
        coincide con el origen del marco. Usar uno por el otro deja el norte y el
        recuadro fuera del lienzo cuando el terreno es angosto.
        """
        x0, y0, x1, y1 = self._bbox()
        mx = self.margen
        my = self.margen + (self.ALTO_TITULO if (self.titulo or self.subtitulo) else 0)
        mw = self.ancho - 2 * self.margen
        mh = self.alto - my - self.margen - self.ALTO_PIE
        # Una sola escala para X e Y: deformar el plano lo haria inutil para verificar.
        s = min(mw / max(x1 - x0, 1e-9), mh / max(y1 - y0, 1e-9))
        ox = mx + (mw - (x1 - x0) * s) / 2
        oy = my + (mh - (y1 - y0) * s) / 2

        def tx(x, y):
            # El eje Y del SVG crece hacia abajo y el norte hacia arriba: se invierte.
            return ox + (x - x0) * s, oy + (y1 - y) * s

        return tx, s, (mx, my, mw, mh)

    # ------------------------------------------------------------------ render
    def render(self) -> str:
        """Devuelve el SVG como texto, sin escribir archivo.

        Para incrustarlo en un informe HTML autocontenido (ver skill
        `informe-analisis-superficies`): el mismo motor de dibujo sirve para
        archivo suelto (`guardar`) o para incrustacion inline (`render`).
        """
        tx, s, (mx, my, mw, mh) = self._transformar()
        C = self.C
        O = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.ancho}" '
             f'height="{self.alto}" viewBox="0 0 {self.ancho} {self.alto}" '
             f'font-family=\'{FUENTE}\'>',
             f'<rect width="{self.ancho}" height="{self.alto}" fill="{C["fondo"]}"/>']

        def d(coords, cerrar=True):
            return " ".join(("M " if i == 0 else "L ") + "%.2f %.2f" % tx(*c)
                            for i, c in enumerate(coords)) + (" Z" if cerrar else "")

        for c in self._capas:
            if c["tipo"] == "poly":
                O.append(f'<g fill="{c["relleno"]}" stroke="{c["borde"]}" '
                         f'stroke-width="{c["grosor"]}" fill-opacity="{c["opacidad"]}">')
                O += [f'<path d="{d(a)}"/>' for a in c["anillos"]]
                O.append("</g>")
            elif c["tipo"] == "poly_multi":
                O.append('<g stroke="none">')
                O += [f'<path d="{d(a)}" fill="{col}"/>'
                      for a, col in zip(c["anillos"], c["colores"])]
                O.append("</g>")
            elif c["tipo"] == "linea":
                guion = f' stroke-dasharray="{c["guion"]}"' if c.get("guion") else ""
                O.append(f'<g fill="none" stroke="{c["borde"]}" stroke-width="{c["grosor"]}" '
                         f'stroke-linejoin="round"{guion}>')
                O += [f'<path d="{d(p, c["cerrar"])}"/>' for p in c["polilineas"]]
                O.append("</g>")
            else:
                O.append(f'<g fill="{c["relleno"]}">')
                for i, p in enumerate(c["coords"]):
                    px, py = tx(*p)
                    O.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{c["radio"]}"/>')
                O.append("</g>")
                if c["rotulos"]:
                    O.append(f'<g fill="{C["tinta2"]}" font-size="12">')
                    for p, r in zip(c["coords"], c["rotulos"]):
                        px, py = tx(*p)
                        O.append(f'<text x="{px + 7:.2f}" y="{py - 6:.2f}">{_esc(r)}</text>')
                    O.append("</g>")

        # marco del area de dibujo
        O.append(f'<rect x="{mx:.1f}" y="{my:.1f}" width="{mw:.1f}" height="{mh:.1f}" '
                 f'fill="none" stroke="{C["hairline"]}" stroke-width="1"/>')

        # titulo y subtitulo
        y = self.margen + 6
        if self.titulo:
            O.append(f'<text x="{self.margen}" y="{y}" font-size="20" font-weight="600" '
                     f'fill="{C["tinta"]}">{_esc(self.titulo)}</text>')
            y += 22
        if self.subtitulo:
            O.append(f'<text x="{self.margen}" y="{y}" font-size="13" '
                     f'fill="{C["tinta2"]}">{_esc(self.subtitulo)}</text>')
            y += 18
        for n in self._notas[:2]:
            O.append(f'<text x="{self.margen}" y="{y}" font-size="12" '
                     f'fill="{C["muted"]}">{_esc(n)}</text>')
            y += 15

        # norte, arriba a la derecha del area de dibujo
        nx, ny = mx + mw - 20, my + 24
        O += [f'<path d="M {nx} {ny - 18} l -6 16 l 6 -4 l 6 4 Z" fill="{C["tinta"]}"/>',
              f'<text x="{nx}" y="{ny + 14}" font-size="12" font-weight="700" '
              f'fill="{C["tinta"]}" text-anchor="middle">N</text>']

        # escala grafica, abajo a la izquierda
        py = self.alto - self.margen - 22
        paso = paso_redondo((self._bbox()[2] - self._bbox()[0]) / 5.0)
        largo = paso * s
        O += [f'<line x1="{self.margen}" y1="{py}" x2="{self.margen + largo:.1f}" y2="{py}" '
              f'stroke="{C["tinta2"]}" stroke-width="2"/>',
              f'<line x1="{self.margen}" y1="{py - 5}" x2="{self.margen}" y2="{py + 5}" '
              f'stroke="{C["tinta2"]}" stroke-width="2"/>',
              f'<line x1="{self.margen + largo:.1f}" y1="{py - 5}" '
              f'x2="{self.margen + largo:.1f}" y2="{py + 5}" '
              f'stroke="{C["tinta2"]}" stroke-width="2"/>',
              f'<text x="{self.margen}" y="{py + 20}" font-size="12" fill="{C["muted"]}">'
              f'{paso:,.0f} {_esc(self.unidad)}</text>']

        # leyenda, abajo, a la derecha de la escala grafica
        lx = self.margen + largo + 46
        ly = py + 4
        for tipo, color, etq in self._leyenda:
            if tipo == "linea":
                O.append(f'<line x1="{lx}" y1="{ly - 4}" x2="{lx + 20}" y2="{ly - 4}" '
                         f'stroke="{color}" stroke-width="2.5"/>')
            elif tipo == "punto":
                O.append(f'<circle cx="{lx + 10}" cy="{ly - 4}" r="4.5" fill="{color}"/>')
            else:
                O.append(f'<rect x="{lx}" y="{ly - 11}" width="20" height="13" rx="2" '
                         f'fill="{color}"/>')
            O.append(f'<text x="{lx + 27}" y="{ly}" font-size="12.5" fill="{C["tinta2"]}">'
                     f'{_esc(etq)}</text>')
            lx += 27 + len(str(etq)) * 6.6 + 24

        # barra de gradiente si hubo capa graduada
        if self._gradiente:
            vmin, vmax, tit = self._gradiente
            gx, gw = lx, 150
            if gx + gw > self.ancho - self.margen:
                gx, gw = self.ancho - self.margen - 150, 150
            stops = "".join(
                f'<stop offset="{i / (len(C["rampa"]) - 1):.4f}" stop-color="{c}"/>'
                for i, c in enumerate(C["rampa"]))
            O += [f'<defs><linearGradient id="g1" x1="0" x2="1">{stops}</linearGradient></defs>',
                  f'<rect x="{gx}" y="{ly - 12}" width="{gw}" height="13" rx="2" '
                  f'fill="url(#g1)" stroke="{C["hairline"]}" stroke-width="0.5"/>',
                  f'<text x="{gx}" y="{ly + 14}" font-size="11" fill="{C["muted"]}">'
                  f'{vmin:,.2f}</text>',
                  f'<text x="{gx + gw}" y="{ly + 14}" font-size="11" fill="{C["muted"]}" '
                  f'text-anchor="end">{vmax:,.2f}</text>']
            if tit:
                O.append(f'<text x="{gx + gw / 2}" y="{ly - 17}" font-size="11" '
                         f'fill="{C["muted"]}" text-anchor="middle">{_esc(tit)}</text>')

        O.append("</svg>")
        return "\n".join(O)

    # ----------------------------------------------------------------- guardar
    def guardar(self, ruta: str) -> str:
        texto = self.render()
        os.makedirs(os.path.dirname(os.path.abspath(ruta)) or ".", exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as fh:
            fh.write(texto)
        return ruta


# ------------------------------------------------------------ lectores comunes --
def leer_landxml(ruta: str, nombre: str | None = None):
    """Devuelve (nombre, triangulos [(E,N,Z)x3], unidad_lineal)."""
    import xml.etree.ElementTree as ET
    ns = {"lx": "http://www.landxml.org/schema/LandXML-1.2"}
    root = ET.parse(ruta).getroot()
    u = root.find("lx:Units", ns)
    lineal = "m"
    if u is not None and len(u):
        lineal = u[0].get("linearUnit", "meter")
        lineal = "ft" if "oot" in lineal else "m"
    sup = root.findall(".//lx:Surface", ns)
    if not sup:
        raise ValueError("El LandXML no tiene <Surface>.")
    s = next((x for x in sup if x.get("name") == nombre), None) if nombre else sup[0]
    if s is None:
        raise ValueError(f"No existe la superficie {nombre!r}.")
    d = s.find("lx:Definition", ns)
    pts = {}
    for p in d.find("lx:Pnts", ns):
        n, e, z = (float(v) for v in p.text.split())
        pts[p.get("id")] = (e, n, z)
    tris = []
    for f in d.find("lx:Faces", ns):
        if f.get("i") == "1":            # cara invisible: excluida por contorno
            continue
        a, b, c = f.text.split()
        tris.append((pts[a], pts[b], pts[c]))
    return s.get("name"), tris, lineal


def leer_dxf(ruta: str, capa: str | None = None):
    """Devuelve (polilineas [(x,y)...], descripcion). Requiere ezdxf."""
    import ezdxf
    msp = ezdxf.readfile(ruta).modelspace()
    out = []
    for e in msp:
        if capa and e.dxf.layer != capa:
            continue
        t = e.dxftype()
        if t == "LWPOLYLINE":
            out.append(([(p[0], p[1]) for p in e.get_points("xy")], bool(e.closed)))
        elif t == "POLYLINE" and not e.is_poly_face_mesh and not e.is_polygon_mesh:
            out.append(([(v.dxf.location.x, v.dxf.location.y) for v in e.vertices],
                        bool(e.is_closed)))
        elif t == "LINE":
            out.append(([(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)], False))
    return out


# ---------------------------------------------------------------------- CLI ----
def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(
        description="Plano SVG de verificacion a partir de un LandXML y/o un DXF.")
    ap.add_argument("--xml", help="LandXML con la superficie")
    ap.add_argument("--dxf", help="DXF con lineas/polilineas a superponer")
    ap.add_argument("--superficie", help="nombre de la superficie si el XML trae varias")
    ap.add_argument("--capa", help="filtrar entidades del DXF por capa")
    ap.add_argument("--salida", default="plano.svg", help="archivo SVG de salida")
    ap.add_argument("--titulo", default="", help="titulo del plano")
    ap.add_argument("--color-cota", action="store_true",
                    help="colorear los triangulos por cota (rampa secuencial)")
    ap.add_argument("--tema", default="claro", choices=("claro", "oscuro"))
    ap.add_argument("--ancho", type=int, default=1200)
    ap.add_argument("--alto", type=int, default=900)
    a = ap.parse_args()

    if not a.xml and not a.dxf:
        ap.error("indica al menos --xml o --dxf")

    nombre, tris, unidad = (None, [], "m")
    if a.xml:
        nombre, tris, unidad = leer_landxml(a.xml, a.superficie)

    p = PlanoSVG(titulo=a.titulo or (nombre or os.path.basename(a.dxf or "")),
                 unidad_lin=unidad, ancho=a.ancho, alto=a.alto, tema=a.tema)
    if tris:
        if a.color_cota:
            p.poligonos_graduados(
                [([(q[0], q[1]) for q in t], sum(q[2] for q in t) / 3.0) for t in tris],
                titulo_escala=f"cota ({unidad})")
            p.nota(f"{len(tris)} triangulos coloreados por cota media")
        else:
            p.poligonos([[(q[0], q[1]) for q in t] for t in tris], rol="contexto",
                        etiqueta=f"TIN ({len(tris)} triangulos)")
    if a.dxf:
        ent = leer_dxf(a.dxf, a.capa)
        abiertas = [g for g, cer in ent if not cer]
        cerradas = [g for g, cer in ent if cer]
        if cerradas:
            p.lineas(cerradas, rol="serie2", etiqueta="polilineas cerradas", cerrar=True)
        if abiertas:
            p.lineas(abiertas, rol="serie1", etiqueta="lineas / polilineas abiertas")
    ruta = p.guardar(a.salida)
    print(f"Plano generado: {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
