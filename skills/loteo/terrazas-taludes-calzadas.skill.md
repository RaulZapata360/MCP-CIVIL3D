---
name: terrazas_taludes_calzadas
description: "Genera la superficie de proyecto de un loteo en ladera: terrazas horizontales por lote a su NPT, taludes contra la calzada y entre lotes vecinos, y el pavimento de la vialidad con rasante continua. Parte de un DXF de loteo y el TIN del terreno natural, y entrega LandXML importable a Civil 3D más DXF de bordes editable. Usar cuando pidan modelar plataformas/terrazas de un loteo, generar taludes entre lotes o contra calles, cubicar un loteo en cerro, o cuando una superficie de proyecto ya generada salga con triangulación sucia, bordes dentados o taludes discontinuos."
---

# Terrazas, taludes y calzadas de un loteo en ladera

Construye la **superficie de proyecto** de una subdivisión en cerro.

**Entradas:** un DXF de loteo (deslindes + rótulos de número y NPT) y el TIN del
terreno natural en LandXML.
**Salidas:** un LandXML con una superficie por lote —terraza más sus taludes— y
otra para el pavimento, más un DXF de bordes en capas para retocar a mano.

> Destilada de un proyecto real de 89 lotes. Casi todo lo que aquí aparece como
> advertencia es un fallo que se cometió, se vio en pantalla y se corrigió; las
> cifras citadas son medidas de ese caso, no ejemplos inventados. El paquete es
> autocontenido: no depende de ninguna carpeta de proyecto.

## Cuándo usarla

* Modelar plataformas/terrazas de un loteo con desniveles entre lotes.
* Generar taludes: entre terrazas vecinas y entre lote y calzada.
* Cubicar movimiento de tierras de un loteo en ladera.
* **Diagnosticar** una superficie ya hecha que sale con triángulos sucios, bordes
  dentados, taludes que se truncan o picos que atraviesan la calzada.

---

## 1. La regla geométrica

Todo el método sale de una sola fórmula. Para un punto `p` del lote:

```
z(p) = zb + (NPT − zb) · min(1, d / w)        con   w = |NPT − zb| · razón
```

* `d` — distancia de `p` a la línea de arranque de la junta (deslinde o solera).
* `zb` — cota que rige sobre esa línea: la NPT del vecino, o la rasante de la calle.
* `razón` — H:V del talud. Con **1:1** el ancho es exactamente el desnivel.

En el arranque (`d = 0`) vale `zb`; en el pie (`d = w`) vale `NPT`, que es la cota
de la terraza. **Empalma por los dos lados sin escalón, por construcción.**

**Entre dos terrazas el desnivel es constante** —son dos planos horizontales—, así
que el talud es una banda de ancho uniforme igual al desnivel. Contra la calzada
el ancho varía, porque la rasante sube mientras la plataforma no.

---

## 2. Proceso completo

Copiable y ejecutable. `SCRIPTS` es la carpeta `scripts/` de esta skill.

### Paso 1 — Leer el loteo

```python
import sys; sys.path.insert(0, SCRIPTS)
import loteo_io, terrazas_lib, vialidad_lib, rasantes_red, rasantes_lib, mesh_io

lotes, _ = loteo_io.leer_lotes(DXF, capa="LOTE TERRENO")
npt, avisos = loteo_io.leer_npt(DXF, lotes)
for a in avisos:
    print("AVISO:", a)          # rótulos malformados o lotes sin NPT
```

**Mirar los avisos.** Un `NPT 12100m` sin punto decimal pasa desapercibido y mete
un lote a 12 km de altura. Los números de lote repetidos se desambiguan solos con
sufijo `-A`/`-B` en orden sur→norte.

### Paso 2 — Terreno natural

```python
from mesh_io import read_landxml_surface, barycentric_z
verts, faces = read_landxml_surface(XML_TN, NOMBRE_SUPERFICIE)
```

Construir con eso un muestreador `z(x, y)` con índice espacial (`STRtree` sobre
los triángulos). Se usa para clasificar corte/relleno y para la cota natural de
los ejes de calle.

### Paso 3 — Vialidad limpia

```python
vial = loteo_io.vialidad(lotes, cierre=14.0)
CALZADA = vialidad_lib.limpiar_calzada(vial)
```

`cierre` debe superar el ancho de calle más ancho y quedar por debajo de cualquier
vano exterior que no sea calle. **Verificar midiendo el ancho real de los pasillos
obtenidos** — con un valor mal elegido se cierran patios que no son calle.

### Paso 4 — Ejes y rasantes de la red

```python
calles = []                       # {nombre, poly, eje, est, z_nat, z}
# ... extraer un eje por calle (rasantes_lib tiene el esqueleto de Voronoi) ...

# ramales que ningún eje recorre: se les da su propio eje
for poly, eje in vialidad_lib.ramales_sin_eje(CALZADA, calles):
    est, zn = rasantes_lib.perfil_terreno(eje, terreno_z)
    calles.append({"nombre": f"Ramal {len(calles)}", "poly": poly, "eje": eje,
                   "est": est, "z_nat": zn, "z": zn.copy()})

accesos = {c["nombre"]: rasantes_lib.accesos(c["eje"], lotes, npt, c["poly"])
           for c in calles}
z_red, cruces = rasantes_red.resolver(calles, accesos, pend_max=0.08)
for c in calles:
    c["z"] = z_red[c["nombre"]]
```

### Paso 5 — Armar cada lote

```python
objetos = {l["nombre"]: terrazas_lib.Lote(l["nombre"], l["poligono"], npt[l["nombre"]])
           for l in lotes if l["nombre"] in npt}

# juntas contra la calzada (cota variable: la rasante)
zc = lambda x, y: vialidad_lib.z_red(calles, x, y)
for n, ob in objetos.items():
    for g in loteo_io.frentes({"poligono": ob.poly}, CALZADA):
        ob.agregar_junta(g, zc, etiqueta="calzada")

# juntas entre vecinos (cota fija: la NPT del lote bajo)
meds = loteo_io.medianeros(lotes)
loteo_io.juntas_de_medianero(objetos, npt, meds)
```

### Paso 6 — Mallar y auditar

```python
superficies, audit = [], []
for n, ob in objetos.items():
    v, f = ob.mallar()
    if not f:
        continue
    superficies.append((f"L_{n.replace(' ','-')}_NPT{ob.npt:.2f}", v, f,
                        f"Lote {n}: terraza a NPT {ob.npt:.2f} m y taludes"))
    audit.append(terrazas_lib.auditar(ob, v, f))
```

### Paso 7 — Calzada y escritura

```python
pts = vialidad_lib.nube_calzada(CALZADA)
cv, cf = vialidad_lib.mallar_poligono(CALZADA, pts, zc)
superficies.insert(0, ("CALZADAS", cv, cf, "Pavimento con rasante de red"))

mesh_io.escribir_landxml(SALIDA_XML, superficies)   # o el writer del proyecto
```

---

## 3. Las seis reglas que hay que respetar

### 3.1 Una función de cota por lote, no una por pieza

**Nunca** partir el lote en piezas (una por talud + la terraza) y mallar cada una
con los vértices de su propio contorno. Da tres fallos a la vez:

* la línea de arranque no recorre el lote de lado a lado, porque cada franja se
  recorta contra las anteriores → quedan secciones a la NPT donde debe haber talud;
* triangular una franja usando solo su contorno produce triángulos que la cruzan
  en diagonal → dentro del talud la pendiente deja de ser la del talud;
* al restar unas franjas de otras salen lenguas finas y astillas.

Y además rompe el TIN: en el borde compartido cada pieza calcula una cota distinta
para el mismo punto. Medido: **3.204 posiciones XY con doble cota**. Civil 3D
deduplica por XY, descarta una y la malla queda descosida — de ahí los taludes que
se truncan por tramos y reaparecen. Con una sola función: **0 conflictos**.

### 3.2 La banda del talud se hace con buffer, no desplazando la línea

Desplazar hacia adentro exige decidir el sentido con un punto de prueba, y esa
prueba **falla cuando la línea cae fuera del lote** — cosa que pasa, porque el
tramo del medianero se reconstruye sobre el contorno de *uno* de los dos vecinos.

| | Desplazamiento | Buffer recortado |
|---|---|---|
| Medianeros con <95 % del deslinde cubierto | 69 de 112 | **3 de 82** |
| Ancho efectivo / teórico | 0,29 | **1,00** |

Complemento: **anclar la junta en el contorno del propio lote**
(`lote.exterior ∩ tramo.buffer(0.40)`). Con desniveles de 0,25 m la banda es más
estrecha que la tolerancia de reconstrucción y el recorte se la come.

### 3.3 Sembrar el pie del talud en la nube de puntos

La malla necesita vértices **en el arranque y en el pie**. Sin el pie, un triángulo
salta del arranque a la terraza cruzando la franja y se pierde la pendiente.

### 3.4 El borde de la calzada viene de la vialidad cruda

La calzada se obtiene restando las manzanas a su envolvente. **Ese** polígono tiene
por borde el deslinde de los lotes: rectas de decenas de metros.

Si en cambio se usa el polígono de un reparto por celdas —muestrear una rejilla y
unir un círculo por celda— el borde sale dentado:

| | Reparto por celdas | Vialidad cruda |
|---|---|---|
| Vértices | 2.293 | **140** |
| Lado mediano | 0,69 m | **14,57 m** |
| Giro mediano | 52,5° | **0,0°** |

Efecto en cadena: contra un borde dentado los frentes de lote salen partidos en
491 trocitos de 4 m; contra el limpio, **100 rectas de 21,6 m**.

### 3.5 Las rasantes se resuelven como RED, no calle por calle

Resolver cada calle por separado no obliga a que dos que se cruzan compartan cota
en el cruce. Medido: **hasta 2,86 m** de discrepancia. Un cruce tiene una sola
cota; ese desacuerdo se convierte en un pico que atraviesa la calzada.

`rasantes_red.resolver` itera añadiendo el cruce como objetivo de cota muy pesado y
actualizando el objetivo al promedio de lo que proponen las calles concurrentes.
Baja el desacuerdo a **0,23 m** (el residuo lo impone el tope de pendiente).

Dos complementos:

* **Ejes para los ramales sin eje.** El eje de una calle no siempre cubre toda su
  calzada — en el caso real dejaba fuera 1.562 m² a 46,8 m de sí mismo. Darles su
  propio eje, no descartarlos: descartarlos borra pavimento del modelo.
* **Mezcla suave entre ejes** (`vialidad_lib.z_red`). Promediar solo los de una
  ventana hace que el conjunto entre y salga de golpe al recorrer el borde: diente
  de sierra en la solera. Que participen todos con peso exponencial decreciente.

### 3.6 El acceso a lote es restricción dura, no un costo a ponderar

Ponderarlo contra el movimiento de tierras lo deja comprar: mover la plataforma de
un lote de 550 m² un metro cuesta del orden de 550 m³, así que cualquier peso
razonable pierde. Medido: una optimización mejoraba tierra y talud y **empeoraba el
acceso del 27 % al 63 %** fuera de tolerancia.

Con banda dura (±1,50 m contra su calzada) y resolviendo NPT y rasantes
**acopladas** —iterar hasta que ambas dejan de moverse, 3-4 pasadas— el resultado
baja a 17 %, mejor que el proyecto de partida.

---

## 4. Corte o relleno lo decide el terreno, no las cotas

La razón del talud **no** la decide cuál de las dos cotas es más alta, sino **dónde
está el terreno natural**:

* terreno por encima de ambas → **corte** (típico 1:1)
* terreno por debajo de ambas → **relleno** (típico 1,5:1)
* terreno entre medias → mixto, razón ponderada

Se cometió el error de clasificar el talud de frente solo por el signo del
desnivel. Si el lote queda bajo la calle pero el terreno está aún más abajo, hay
que **rellenar**, y el talud ocupa 1,5 veces más ancho.

Si el proyecto adopta 1:1 para todo, declararlo explícitamente — no heredarlo por
descuido.

---

## 5. Auditoría: qué medir siempre

Un corte en ladera **no admite** superficie flotante, huecos, ni zonas planas
dentro de un talud. `terrazas_lib.auditar` devuelve por lote:

| Métrica | Valor sano |
|---|---|
| `cobertura` | 100,000 % del lote |
| `hueco` | 0 m² |
| `piezas` | 1 |
| `flotantes` | 0 vértices sin cara |
| `llano_en_talud` | ~0 — fue el fallo principal |
| `pendiente_fuera_regla` | bajo; sube en esquinas donde dos taludes concurren |

Sobre el XML terminado, comprobar además **posiciones XY con más de una cota**: si
hay alguna, el TIN es inválido y Civil 3D lo destrozará al importar.

```python
import collections
xy = collections.defaultdict(set)
for x, y, z in verts:
    xy[(round(x, 2), round(y, 2))].add(round(z, 2))
conflictos = sum(1 for zs in xy.values() if len(zs) > 1)
```

Y contra el medianero: **área de banda / (desnivel × largo)** debe dar ≈ 1,00, y la
proyección de la banda sobre el eje del deslinde debe cubrirlo entero.

> Cuidado al medir la cobertura por distancia al tramo: el tramo puede estar hasta
> 0,30 m **fuera** del lote alto, y entonces la banda legítima cuenta como no
> cubierta. Medir por proyección sobre el eje del deslinde.

---

## 6. Lo que NO se puede hacer

**Una superficie escalonada no puede ser un TIN único.** Un TIN es una función
z(x,y): no admite dos cotas en el mismo punto. En el caso real había **86 esquinas**
compartidas por lotes con distinta NPT y 22 pares de lotes solapados. Emitir una
superficie combinada de todos los lotes produce exactamente el desastre que se ve
al importarla.

**Emitir una superficie por lote.** Cada una es un TIN válido. Para volúmenes, usar
superficies separadas (plataformas / taludes / calzadas), no una combinada.

---

## 7. Trampas de datos ya vistas

* **`<P id>` de LandXML no arranca en 1 ni es correlativo.** Remapear por id
  explícito; asumir `id-1 == índice` corrompe la malla en silencio.
* **Nombres de lote vs nombre de archivo.** `Lote_AV-1.xml` ↔ lote `"AV 1"`.
  Comparar literal dejó fuera un área verde de 2.596,8 m² sin avisar. Normalizar
  separadores y **avisar** de los que no calcen.
* **Lotes contiguos separados hasta 0,14 m.** Reconstruir medianeros con tolerancia
  de 10 cm perdía deslindes enteros — uno de 32,4 m con 3,50 m de desnivel, sin
  talud. Usar 0,30 m.
* **Deslindes de menos de 1 m son toques de esquina**, no medianeros. Generarles
  talud produce astillas.
* **Simplify, no apertura, para limpiar contornos.** La apertura morfológica
  sustituye rectas por arcos: multiplicó los vértices de 2.308 a 18.764 y las
  astillas de triángulo de 187 a 12.788.
* **Densificar conservando los vértices originales.** Interpolar a intervalos
  regulares sobre todo el anillo borra las esquinas: 593 m² de calzada perdidos.
* **Sembrar puntos interiores antes de triangular.** Un corredor largo triangulado
  solo desde el contorno da triángulos que lo cruzan de lado a lado.
* **Astillas entre lotes vecinos.** Donde dos lotes no se tocan exactamente, la
  calzada se cuela como una lengua de 1-2 m: 615 de ellas, 51,5 m². Son las
  "muecas" del contorno.

---

## 8. Módulos

| Archivo | Qué hace |
|---|---|
| `scripts/loteo_io.py` | Lee lotes y NPT del DXF, vialidad, medianeros, frentes, juntas |
| `scripts/terrazas_lib.py` | Clase `Lote`: juntas, función de cota, banda, nube, mallado, `auditar` |
| `scripts/vialidad_lib.py` | Calzada limpia, `z_red`, ramales sin eje, mallado de polígono |
| `scripts/rasantes_red.py` | Rasantes de toda la red con cruces a cota única |
| `scripts/rasantes_lib.py` | Eje por esqueleto de Voronoi y rasante de una calle |
| `scripts/mesh_io.py` | LandXML, triangulación con huecos, interpolación baricéntrica |

Solo depende de `numpy`, `shapely`, `scipy`, `networkx` y `ezdxf`.

Prueba mínima de que el paquete funciona, sin necesidad de ningún proyecto:

```python
import shapely.geometry as sg, terrazas_lib
L = terrazas_lib.Lote("P", sg.Polygon([(0,0),(40,0),(40,30),(0,30)]), 110.0)
L.agregar_junta(sg.LineString([(0,0),(40,0)]), 107.0)   # junta 3 m más baja
L.z(20, 1.5)                            # -> 108.500   (1:1 exacto)
L.banda(L.juntas[0]).area               # -> 120.00 m² (40 × 3)
terrazas_lib.auditar(L, *L.mallar())    # cobertura 100 %, todo lo demás en 0
```

---

## 9. Criterios de proyecto a acordar antes de empezar

No son decisiones técnicas sino de diseño. **Preguntar, no asumir:**

* **Razón del talud.** 1:1 para todo es lo más simple y fue lo adoptado.
* **Pendiente máxima de calzada.** En camino rural sin pavimentar, **8 %**: por
  encima falla la tracción con barro, la distancia de frenado en bajada, y el agua
  que escurre por la carpeta la erosiona. Con 12 % el trazado queda pegado al tope.
* **Tolerancia de acceso** y ancho mínimo de frente a nivel (p. ej. 3 m con ≤0,30 m
  de desnivel; el resto se resuelve con rampa dentro del lote al 15 %).
* **Grilla de NPT.** Redondear a metro no es un criterio, es un descuido: deja
  plataformas lejos de su cota de equilibrio y saltos innecesarios entre vecinos.
  Con grilla de 0,25 m hay margen para mejorar tierra **y** superficie a la vez.
