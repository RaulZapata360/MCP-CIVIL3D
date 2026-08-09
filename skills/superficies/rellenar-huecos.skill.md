---
name: rellenar_huecos_y_costuras
description: "Cierra los huecos entre superficies entregadas y el límite real de la malla tomando la geometría del XML de origen, y anexa a una superficie el trozo que no cubría ninguna otra."
---

# Rellenar huecos y costuras

Cierra los vacíos que quedan **entre** superficies entregadas y el borde real de la malla,
sin inventar geometría: todo lo que se añade sale del XML de origen.

## Cuándo usar

*   Tras recortar o partir, quedan franjas sin cubrir en las costuras.
*   Un elemento de la malla original no lo reclama ninguna superficie de la entrega.

## Uso

```bash
python skills/superficies/scripts/rellenar_huecos.py origen.xml limite.xml entrega.xml combinado.xml [referencia.xml] [min_hueco]
```

```bash
python skills/superficies/scripts/anexar_relleno.py origen.xml relleno.dxf entrega.xml "Superficie Destino" combinado.xml
```

| Script | Qué hace |
|---|---|
| `rellenar_huecos.py` | Cierra los huecos entre las superficies entregadas y el límite real de la malla. |
| `anexar_relleno.py` | Anexa a una superficie **solo el trozo** que no cubría ninguna otra. |

## A quién se asigna cada hueco

Si le pasas un XML de referencia (por ejemplo el que reparaste a mano en Civil 3D), el
script mira qué superficie lo cubría allí y **respeta esa decisión**. El nombre se traduce
por geometría, no por cadena de texto, así que sirve aunque hayas renombrado.

Sin referencia, decide por adyacencia. Revisa el resultado: la adyacencia acierta casi
siempre, pero "casi" no es suficiente en una entrega.

## Anexa el hueco, no el elemento entero

Es el error que motivó `anexar_relleno.py`. Un elemento de relleno medía 17.343,6 ft², pero
16.936,5 ya estaban repartidos entre tres superficies vecinas. **Solo 407,1 ft² (2,3 %) no
los reclamaba nadie.** Pegar el elemento completo habría creado un solape del 97,7 % con
sus vecinas.

Antes de anexar, mide siempre cuánto del elemento está ya cubierto.

## ⚠️ Un filtro por tamaño NO distingue cicatriz de vacío real

Tentador y equivocado. En North Island los **vacíos reales de edificación** iban de 262 a
12.637 ft², y las **cicatrices** del saneado llegaban a 447 ft². Los rangos se solapan: dos
vacíos reales caían por debajo de la cicatriz más grande.

Cualquier umbral por área o borra vacíos legítimos o deja cicatrices. Hay que distinguirlos
por **procedencia** (¿estaba ese vacío en el origen, o lo abrió el recorte?), no por tamaño.

## Dependencias

`ezdxf`, `shapely`. Lógica común en `mesh_utils.py` (misma carpeta).

## Ver también

*   `recorte-y-resta` — la operación que suele abrir estas costuras.
*   `contornos-y-boundaries` — los vacíos de edificación son reales y deben viajar.
