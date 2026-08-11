# -*- coding: utf-8 -*-
"""Rasantes de toda la RED vial resueltas con continuidad en los cruces.

EL DEFECTO QUE CORRIGE. `rasantes_lib.resolver_rasante` resuelve una calle a la
vez: se acerca al terreno, da acceso a los lotes que enfrenta y respeta la
pendiente maxima. Pero nada obliga a que dos calles que se cruzan tengan la misma
cota en el cruce. Medido sobre la propuesta, discrepaban hasta 2,86 m -- Calle 4
contra Calle 3 -- y mas de 1 m en otros tres cruces. Un cruce tiene UNA cota: ese
desacuerdo es geometricamente imposible, y al mallar la calzada se convertia en
un pico que la atraviesa.

METODO. Se detectan los cruces (puntos donde dos ejes se acercan a menos de
TOL_CRUCE) y se itera: cada calle se resuelve con el solucionador ya validado,
pero anadiendo el cruce como un objetivo de cota muy pesado; entre pasadas, el
objetivo de cada cruce se actualiza al promedio de lo que proponen las calles que
concurren. Converge en pocas pasadas y deja los cruces cerrados sin tocar el
resto del criterio.
"""
import itertools
import numpy as np
import shapely.geometry as sg

import rasantes_lib as R

TOL_CRUCE = 6.0        # m — dos ejes mas cerca que esto forman un cruce.
                        # Con 3 m se escapaba el encuentro Calle 4 / Calle 3, cuyos
                        # ejes distan 4,4 m pero cuyas calzadas se tocan.
PESO_CRUCE = 60        # repeticiones del objetivo de cruce: lo vuelve casi rigido
ITERS = 8


def detectar_cruces(calles, muestras=400):
    """[{calles: [(nombre, estacion)], punto}] de cada cruce de la red."""
    cruces = []
    for a, b in itertools.combinations(calles, 2):
        ea, eb = a["eje"], b["eje"]
        if ea.distance(eb) > TOL_CRUCE:
            continue
        mejor = None
        for i in range(muestras + 1):
            p = ea.interpolate(ea.length * i / muestras)
            d = eb.distance(p)
            if mejor is None or d < mejor[0]:
                mejor = (d, p)
        d, p = mejor
        cruces.append({"calles": [(a["nombre"], float(ea.project(p))),
                                   (b["nombre"], float(eb.project(p)))],
                        "punto": (p.x, p.y), "dist": d})
    return cruces


def resolver(calles, accesos_por_calle, pend_max, verbose=True):
    """calles: [{nombre, eje, est, z_nat}].  Devuelve {nombre: z_ras}."""
    cruces = detectar_cruces(calles)
    porcalle = {c["nombre"]: c for c in calles}
    z = {}
    for c in calles:
        zz, _ = R.resolver_rasante(c["est"], c["z_nat"],
                                    accesos_por_calle.get(c["nombre"], []),
                                    pend_max=pend_max)
        z[c["nombre"]] = np.asarray(zz, float)

    if verbose:
        print(f"   cruces detectados: {len(cruces)}")
    for it in range(ITERS):
        # cota objetivo de cada cruce = promedio de lo que propone cada calle
        objetivo = []
        for x in cruces:
            zs = [float(np.interp(s, porcalle[n]["est"], z[n])) for n, s in x["calles"]]
            objetivo.append(sum(zs) / len(zs))

        extra = {c["nombre"]: [] for c in calles}
        for x, zo in zip(cruces, objetivo):
            for n, s in x["calles"]:
                extra[n].extend([{"lote": f"__cruce__", "s": s, "npt": zo}] * PESO_CRUCE)

        nuevo = {}
        for c in calles:
            acc = list(accesos_por_calle.get(c["nombre"], [])) + extra[c["nombre"]]
            zz, _ = R.resolver_rasante(c["est"], c["z_nat"], acc, pend_max=pend_max)
            nuevo[c["nombre"]] = np.asarray(zz, float)
        mov = max(float(np.max(np.abs(nuevo[n] - z[n]))) for n in z)
        z = nuevo

        peor = 0.0
        for x in cruces:
            zs = [float(np.interp(s, porcalle[n]["est"], z[n])) for n, s in x["calles"]]
            peor = max(peor, max(zs) - min(zs))
        if verbose:
            print(f"   pasada {it+1}: desacuerdo maximo en cruces {peor:.3f} m "
                  f"(mayor cambio de rasante {mov:.3f} m)")
        if peor < 0.05 and mov < 0.01:
            break
    return z, cruces


def diagnostico(calles, z, cruces):
    porcalle = {c["nombre"]: c for c in calles}
    filas = []
    for x in cruces:
        zs = [(n, float(np.interp(s, porcalle[n]["est"], z[n]))) for n, s in x["calles"]]
        filas.append({"calles": [n for n, _ in zs], "cotas": [v for _, v in zs],
                       "desacuerdo": max(v for _, v in zs) - min(v for _, v in zs),
                       "punto": x["punto"]})
    return filas
