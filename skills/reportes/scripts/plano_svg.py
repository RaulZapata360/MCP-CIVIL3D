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
        # mosaico: saturacion y luminosidad fijas para los rellenos de N regiones.
        # Claras a proposito: encima van los rotulos en tinta, que son el
        # identificador real (ver colores_mosaico).
        "mosaico_s": 0.42,
        "mosaico_l": 0.76,
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
        "mosaico_s": 0.38,
        "mosaico_l": 0.34,
    },
}

# Angulo aureo en grados. Al repartir tonos con este paso, dos indices
# consecutivos quedan lo mas lejos posible en el circulo cromatico, que es
# justo lo que hace falta cuando las regiones vecinas suelen ser correlativas.
ANGULO_AUREO = 137.508

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


def _hsl_a_hex(h: float, s: float, l: float) -> str:
    """HSL -> #rrggbb. h en grados, s y l en 0..1."""
    c = (1 - abs(2 * l - 1)) * s
    hp = (h % 360) / 60.0
    x = c * (1 - abs(hp % 2 - 1))
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x),
               (0, x, c), (x, 0, c), (c, 0, x)][int(hp) % 6]
    m = l - c / 2
    return "#%02x%02x%02x" % tuple(round(255 * (v + m)) for v in (r, g, b))


def colores_mosaico(n: int, tema: str = "claro"):
    """n rellenos para distinguir regiones vecinas (no para codificar un dato).

    OJO CON LA DIFERENCIA, que no es cosmetica: la paleta categorica validada
    (serie1..serie3) codifica *categorias que se leen*, y por eso son solo tres
    y van en orden fijo. Aqui el color no codifica nada: resuelve el problema de
    coloreado de mapas -- que dos parcelas pegadas no se confundan. El
    identificador real es el rotulo en tinta que va encima, y por eso los
    rellenos son deliberadamente palidos (claro) u oscuros (oscuro): tienen que
    perder contra el texto.

    Consecuencia practica: NO uses esto para una leyenda de N entradas. Si el
    lector necesita mirar un color y saber que significa, son categorias y
    entonces son como mucho tres.
    """
    if tema not in PALETA:
        raise ValueError(f"tema desconocido: {tema!r} (usa 'claro' u 'oscuro')")
    C = PALETA[tema]
    return [_hsl_a_hex(i * ANGULO_AUREO, C["mosaico_s"], C["mosaico_l"])
            for i in range(max(0, int(n)))]


def centroide_anillos(anillos):
    """Centroide ponderado por area de un conjunto de anillos.

    La media simple de los vertices se va hacia donde la malla esta mas densa,
    que en una superficie triangulada no es el centro sino el borde curvo. Con
    ponderacion por area el rotulo cae donde uno lo espera. Si el area total es
    nula (geometria degenerada) cae de vuelta a la media simple, que al menos
    existe.
    """
    sx = sy = sa = 0.0
    for a in anillos:
        for i in range(1, len(a) - 1):
            (x0, y0), (x1, y1), (x2, y2) = a[0], a[i], a[i + 1]
            cr = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
            sa += cr
            sx += cr * (x0 + x1 + x2)
            sy += cr * (y0 + y1 + y2)
    if abs(sa) > 1e-12:
        return sx / (3 * sa), sy / (3 * sa)
    pts = [p for a in anillos for p in a]
    if not pts:
        raise ValueError("no hay geometria para calcular el centroide")
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def descolapsar(cajas, alto: float = 15.0, iteraciones: int = 60):
    """Separa rotulos que se pisan, moviendolos solo en vertical.

    cajas: lista de (x, y, ancho). Devuelve la lista de y corregidas, en el
    mismo orden. Empuja el par que colisiona en sentidos opuestos, asi ninguno
    se lleva todo el desplazamiento y el conjunto se queda centrado donde
    estaba. Solo se considera colision si ademas se solapan en horizontal:
    dos rotulos a la misma altura en extremos opuestos del plano no molestan.

    Movimiento vertical y no horizontal a proposito: en un plano en planta
    desplazar en X sugiere que el rotulo pertenece a la region de al lado.
    """
    ys = [float(y) for _, y, _ in cajas]
    for _ in range(iteraciones):
        movido = False
        for i in range(len(cajas)):
            for j in range(i + 1, len(cajas)):
                xi, _, wi = cajas[i]
                xj, _, wj = cajas[j]
                if abs(xi - xj) > (wi + wj) / 2:
                    continue
                dv = ys[i] - ys[j]
                falta = alto - abs(dv)
                if falta <= 0:
                    continue
                paso = falta / 2 + 0.1
                if dv >= 0:
                    ys[i] += paso
                    ys[j] -= paso
                else:
                    ys[i] -= paso
                    ys[j] += paso
                movido = True
        if not movido:
            break
    return ys


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
                            titulo_escala: str = "", etiqueta: str | None = None,
                            borde_malla: bool = False):
        """anillos_valores: iterable de (anillo, valor). Rampa secuencial de un tono.

        vmin/vmax explicitos sirven para COMPARTIR la escala entre varias
        llamadas: si cada superficie escala su propio rango, aparecen saltos de
        color falsos en cada junta y ya no se distingue el artefacto del
        defecto real.

        borde_malla dibuja el contorno de cada pieza en hairline. Con un TIN eso
        deja ver la triangulacion, que es lo unico que demuestra que no se
        perdieron caras -- un relleno liso oculta justo el defecto que se busca.
        """
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
                                borde=self.C["tinta"] if borde_malla else None,
                                grosor=0.25 if borde_malla else 0.0, opacidad=1.0))
        self._gradiente = (vmin, vmax, titulo_escala or etiqueta or "")
        return self

    def mosaico(self, grupos, etiqueta: str | None = None,
                borde_malla: bool = True, rotular: bool = True):
        """Un color por region para N regiones, con su rotulo encima.

        grupos: iterable de (nombre, anillos), donde anillos es la lista de
        poligonos de esa region (p.ej. los triangulos de una superficie TIN).

        Pensado para "cual es cual" cuando hay mas regiones que colores de serie
        (ver colores_mosaico). Deja UNA sola entrada de leyenda, no N: una
        leyenda de 25 filas no se lee, y el color aqui no significa nada por si
        mismo -- lo que identifica es el rotulo.
        """
        grupos = [(n, [list(a) for a in anillos if len(a) >= 3])
                  for n, anillos in grupos]
        grupos = [(n, a) for n, a in grupos if a]
        if not grupos:
            return self
        colores = colores_mosaico(len(grupos), self.tema)
        anillos, cols, rotulos = [], [], []
        for (nombre, ans), col in zip(grupos, colores):
            anillos += ans
            cols += [col] * len(ans)
            if rotular:
                rotulos.append((centroide_anillos(ans), nombre))
        self._capas.append(dict(tipo="poly_multi", anillos=anillos, colores=cols,
                                borde=self.C["tinta"] if borde_malla else None,
                                grosor=0.25 if borde_malla else 0.0, opacidad=1.0))
        if rotulos:
            self._capas.append(dict(tipo="rotulo", items=rotulos))
        if etiqueta:
            self._leyenda.append(("mosaico", colores[:3], etiqueta))
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
            elif c["tipo"] == "rotulo":
                xs += [p[0][0] for p in c["items"]]
                ys += [p[0][1] for p in c["items"]]
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

    # ----------------------------------------------------------------- guardar
    def guardar(self, ruta: str) -> str:
        tx, s, (mx, my, mw, mh) = self._transformar()
        C = self.C
        O = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.ancho}" '
             f'height="{self.alto}" viewBox="0 0 {self.ancho} {self.alto}" '
             f'font-family=\'{FUENTE}\'>',
             f'<rect width="{self.ancho}" height="{self.alto}" fill="{C["fondo"]}"/>']

        def d(coords, cerrar=True):
            return " ".join(("M " if i == 0 else "L ") + "%.2f %.2f" % tx(*c)
                            for i, c in enumerate(coords)) + (" Z" if cerrar else "")

        # Los rotulos van al final pase lo que pase: si se dibujan en el orden
        # en que se agregaron, cualquier capa posterior los tapa.
        for c in sorted(self._capas, key=lambda c: c["tipo"] == "rotulo"):
            if c["tipo"] == "poly":
                O.append(f'<g fill="{c["relleno"]}" stroke="{c["borde"]}" '
                         f'stroke-width="{c["grosor"]}" fill-opacity="{c["opacidad"]}">')
                O += [f'<path d="{d(a)}"/>' for a in c["anillos"]]
                O.append("</g>")
            elif c["tipo"] == "poly_multi":
                # La malla va en tinta MUY transparente, no en gris claro: sobre un
                # relleno saturado un hairline claro se lee como linea blanca y
                # tapa el dato. En tinta al 15 % se lee como textura sobre
                # cualquier color, claro u oscuro.
                borde = c.get("borde")
                O.append(f'<g stroke="{borde}" stroke-width="{c["grosor"]}" '
                         f'stroke-opacity="0.15">' if borde else '<g stroke="none">')
                O += [f'<path d="{d(a)}" fill="{col}"/>'
                      for a, col in zip(c["anillos"], c["colores"])]
                O.append("</g>")
            elif c["tipo"] == "rotulo":
                FS = 12.5
                anclas = [tx(x, y) for (x, y), _ in c["items"]]
                cajas = [(px, py, len(t) * FS * 0.58)
                         for (px, py), (_, t) in zip(anclas, c["items"])]
                ys = descolapsar(cajas, alto=FS + 2.5)
                # linea guia si el rotulo tuvo que alejarse de su region
                guias = [(a, y) for a, y in zip(anclas, ys) if abs(a[1] - y) > 6]
                if guias:
                    O.append(f'<g stroke="{C["muted"]}" stroke-width="0.8" fill="none">')
                    O += [f'<path d="M {a[0]:.2f} {a[1]:.2f} L {a[0]:.2f} {y:.2f}"/>'
                          for a, y in guias]
                    O.append("</g>")
                # halo del color del fondo con paint-order, para que el rotulo se
                # lea sobre cualquier relleno sin taparlo con una caja opaca
                O.append(f'<g font-size="{FS}" font-weight="700" fill="{C["tinta"]}" '
                         f'stroke="{C["fondo"]}" stroke-width="3.2" '
                         f'paint-order="stroke fill" text-anchor="middle">')
                for (px, _), y, (_, texto) in zip(anclas, ys, c["items"]):
                    O.append(f'<text x="{px:.2f}" y="{y:.2f}">{_esc(texto)}</text>')
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
            elif tipo == "mosaico":
                # varios recuadros: el color no identifica una categoria, solo
                # avisa de que hay varias regiones. Un swatch unico mentiria.
                for k, col in enumerate(color):
                    O.append(f'<rect x="{lx + k * 7}" y="{ly - 11}" width="6" height="13" '
                             f'rx="1" fill="{col}"/>')
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
        os.makedirs(os.path.dirname(os.path.abspath(ruta)) or ".", exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as fh:
            fh.write("\n".join(O))
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


def leer_landxml_todas(ruta: str):
    """Devuelve ([(nombre, triangulos), ...], unidad_lineal) con TODAS las <Surface>.

    Un LandXML de entrega suele traer una superficie por elemento; dibujarlas de
    a una pierde justo lo que hay que verificar, que es como encajan entre si.
    """
    import xml.etree.ElementTree as ET
    ns = {"lx": "http://www.landxml.org/schema/LandXML-1.2"}
    root = ET.parse(ruta).getroot()
    u = root.find("lx:Units", ns)
    lineal = "m"
    if u is not None and len(u):
        lineal = "ft" if "oot" in u[0].get("linearUnit", "meter") else "m"
    out = []
    for s in root.findall(".//lx:Surface", ns):
        d = s.find("lx:Definition", ns)
        if d is None:
            continue
        pts = {}
        for p in d.find("lx:Pnts", ns):
            n, e, z = (float(v) for v in p.text.split())
            pts[p.get("id")] = (e, n, z)
        tris = []
        for f in d.find("lx:Faces", ns):
            if f.get("i") == "1":        # cara invisible: excluida por contorno
                continue
            a, b, c = f.text.split()
            tris.append((pts[a], pts[b], pts[c]))
        if tris:
            out.append((s.get("name") or f"Superficie {len(out) + 1}", tris))
    if not out:
        raise ValueError("El LandXML no tiene ninguna <Surface> con caras.")
    return out, lineal


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
    ap.add_argument("--todas", action="store_true",
                    help="dibujar TODAS las superficies del XML: un color y un "
                         "rotulo por superficie (o rampa de cota compartida si "
                         "se combina con --color-cota)")
    ap.add_argument("--color-cota", action="store_true",
                    help="colorear los triangulos por cota (rampa secuencial)")
    ap.add_argument("--cota-min", type=float,
                    help="recortar el minimo de la rampa de cota. Util cuando unos "
                         "pocos triangulos bajos comprimen todo el resto; el plano "
                         "avisa del recorte en la nota")
    ap.add_argument("--cota-max", type=float, help="recortar el maximo de la rampa")
    ap.add_argument("--borde-malla", action="store_true",
                    help="dibujar las aristas de los triangulos (deja ver la "
                         "triangulacion; imprescindible para verificar que no "
                         "se perdieron caras)")
    ap.add_argument("--tema", default="claro", choices=("claro", "oscuro"))
    ap.add_argument("--ancho", type=int, default=1200)
    ap.add_argument("--alto", type=int, default=900)
    a = ap.parse_args()

    if not a.xml and not a.dxf:
        ap.error("indica al menos --xml o --dxf")

    nombre, tris, unidad, todas = (None, [], "m", None)
    if a.xml:
        if a.todas:
            todas, unidad = leer_landxml_todas(a.xml)
        else:
            nombre, tris, unidad = leer_landxml(a.xml, a.superficie)

    p = PlanoSVG(titulo=a.titulo or (nombre or os.path.basename(a.xml or a.dxf or "")),
                 unidad_lin=unidad, ancho=a.ancho, alto=a.alto, tema=a.tema)
    if todas:
        n_tris = sum(len(t) for _, t in todas)
        if a.color_cota:
            # Una sola escala para todas: si cada superficie escala su propio
            # rango, cada junta inventa un salto de color que no existe.
            zs = [q[2] for _, ts in todas for t in ts for q in t]
            vmin = a.cota_min if a.cota_min is not None else min(zs)
            vmax = a.cota_max if a.cota_max is not None else max(zs)
            p.poligonos_graduados(
                [([(q[0], q[1]) for q in t], sum(q[2] for q in t) / 3.0)
                 for _, ts in todas for t in ts],
                vmin=vmin, vmax=vmax, titulo_escala=f"cota ({unidad})",
                borde_malla=a.borde_malla)
            nota = (f"{len(todas)} superficies, {n_tris:,} triangulos, "
                    f"escala de cota compartida")
            # Un recorte de rampa NO se calla nunca: si no se dice, el plano
            # aparenta un rango de cotas que no es el del dato.
            if a.cota_min is not None or a.cota_max is not None:
                nota += (f" -- RAMPA RECORTADA a {vmin:,.2f}-{vmax:,.2f} {unidad} "
                         f"(dato real {min(zs):,.2f}-{max(zs):,.2f})")
            p.nota(nota)
        else:
            p.mosaico([(n, [[(q[0], q[1]) for q in t] for t in ts])
                       for n, ts in todas],
                      etiqueta=f"{len(todas)} superficies (rotulo = nombre)",
                      borde_malla=a.borde_malla)
            p.nota(f"{n_tris:,} triangulos en total")
    elif tris:
        if a.color_cota:
            p.poligonos_graduados(
                [([(q[0], q[1]) for q in t], sum(q[2] for q in t) / 3.0) for t in tris],
                titulo_escala=f"cota ({unidad})", borde_malla=a.borde_malla)
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
