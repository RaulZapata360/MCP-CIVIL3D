---
name: terrazas_taludes_calzadas
description: "Genera la superficie de proyecto de un loteo en ladera: terrazas horizontales por lote a su NPT, taludes contra la calzada y entre lotes vecinos, y el pavimento de la vialidad con rasante continua. Entrega LandXML importable a Civil 3D y DXF de bordes editable. Usar cuando pidan modelar plataformas/terrazas de un loteo, generar taludes entre lotes o contra calles, cubicar un loteo en cerro, o cuando una superficie de proyecto ya generada salga con triangulación sucia, bordes dentados o taludes discontinuos."
---

# Terrazas, taludes y calzadas de un loteo en ladera

Construye la **superficie de proyecto** de una subdivisión en cerro a partir de
tres insumos: el DXF del loteo, el TIN del terreno natural y una NPT por lote.

El resultado es un LandXML con una superficie por lote —terraza más sus taludes—
y otra para el pavimento, más un DXF de bordes para retocar a mano.

> Esta skill nació de un proyecto real de 89 lotes. Casi todo lo que aparece aquí
> como advertencia es un fallo que se cometió, se vio en pantalla y se corrigió.
> Las cifras citadas son medidas de ese caso, no ejemplos inventados.

## Cuándo usarla

* Modelar plataformas/terrazas de un loteo con desniveles entre lotes.
* Generar taludes: entre terrazas vecinas y entre lote y calzada.
* Cubicar movimiento de tierras de un loteo en ladera.
* **Diagnosticar** una superficie de proyecto ya hecha que sale con triángulos
  sucios, bordes dentados, taludes que se truncan o picos que atraviesan la calzada.

## La regla geométrica

Todo el método sale de una sola fórmula. Para un punto `p` del lote:

```
z(p) = zb + (NPT − zb) · min(1, d / w)        con   w = |NPT − zb| · razón
```

* `d` — distancia de `p` a la línea de arranque de la junta (deslinde o solera).
* `zb` — cota que rige sobre esa línea: la NPT del vecino, o la rasante de la calle.
* `razón` — H:V del talud. Con **1:1** el ancho es exactamente el desnivel.

En el arranque (`d=0`) vale `zb`; en el pie (`d=w`) vale `NPT`, que es la cota de
la terraza. Empalma por los dos lados sin escalón, por construcción.

**Entre dos terrazas el desnivel es constante** —son dos planos horizontales—, así
que ahí el talud es una banda de ancho uniforme igual al desnivel. Contra la
calzada el ancho varía, porque la rasante sube mientras la plataforma no.

## Las seis reglas que hay que respetar

### 1. Una función de cota por lote, no una por pieza

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
se truncan por tramos y reaparecen.

Con una sola función evaluada igual desde cualquier parte: **0 conflictos**.

### 2. La banda del talud se hace con buffer, no desplazando la línea

Desplazar hacia adentro exige decidir el sentido con un punto de prueba, y esa
prueba **falla cuando la línea cae fuera del lote** — cosa que pasa, porque el
tramo del medianero se reconstruye sobre el contorno de *uno* de los dos vecinos y
los DXF de loteo dibujan lotes contiguos separados hasta 15 cm.

Con desplazamiento: 69 de 112 medianeros cubrían menos del 95% de su deslinde y el
ancho efectivo era el **29%** del teórico. Con `linea.buffer(w) ∩ lote`:
área/teórica **mediana 1,00**, y el 99% del área teórica total.

Complemento: **anclar la junta en el contorno del propio lote** (`lote.exterior ∩
tramo.buffer(0.40)`), no en el tramo reconstruido. Con desniveles de 0,25 m la
banda es más estrecha que la tolerancia de reconstrucción y el recorte se la come.

### 3. Sembrar el pie del talud en la nube de puntos

La malla necesita vértices **en el arranque y en el pie** de cada talud. Sin el
pie, un triángulo salta del arranque a la terraza cruzando la franja y se pierde
la pendiente dentro de ella.

### 4. El borde de la calzada viene de la vialidad cruda

La calzada se obtiene restando las manzanas a su envolvente. **Ese** polígono
tiene por borde el deslinde de los lotes: rectas de decenas de metros.

Si en cambio se usa el polígono del reparto por calles —que se arma muestreando
una rejilla y uniendo un círculo por celda— el borde sale dentado:

| | Reparto por celdas | Vialidad cruda |
|---|---|---|
| Vértices | 2.293 | **140** |
| Lado mediano | 0,69 m | **14,57 m** |
| Giro mediano | 52,5° | **0,0°** |

El reparto en calles sigue haciendo falta, pero solo para saber qué rasante aplica.

### 5. Las rasantes se resuelven como RED, no calle por calle

Resolver cada calle por separado no obliga a que dos que se cruzan compartan cota
en el cruce. Medido: discrepaban hasta **2,86 m**. Un cruce tiene una sola cota;
ese desacuerdo se convierte en un pico que atraviesa la calzada.

`rasantes_red.resolver` itera añadiendo el cruce como objetivo de cota muy pesado y
actualizando el objetivo al promedio de lo que proponen las calles concurrentes.
Baja el desacuerdo a **0,23 m** (el residuo lo impone el tope de pendiente).

Dos complementos:
* **Ejes para los ramales sin eje.** El eje de una calle no siempre cubre toda su
  calzada — en el caso real dejaba fuera 1.562 m² a 46,8 m de sí mismo. Darles su
  propio eje, no descartarlos.
* **Mezcla suave entre ejes** (`z_red`). Promediar solo los de una ventana hace que
  el conjunto entre y salga de golpe al recorrer el borde: diente de sierra en la
  solera. Que participen todos con peso exponencial decreciente.

### 6. El acceso es restricción dura, no un costo a ponderar

Si se optimizan las NPT ponderando acceso contra movimiento de tierras, el acceso
se deja comprar: mover la plataforma de un lote de 550 m² un metro cuesta del orden
de 550 m³, así que cualquier peso razonable pierde. Resultado medido: la propuesta
mejoraba tierra y talud y **empeoraba el acceso del 27% al 63%** fuera de tolerancia.

Con el acceso como banda dura (±1,50 m contra su calzada) y resolviendo NPT y
rasantes **acopladas** (iterar hasta que ambas dejan de moverse, 3-4 pasadas):
17% fuera de tolerancia, mejor que el proyecto de partida.

## Cómo clasificar corte y relleno

La razón del talud **no** la decide cuál de las dos cotas es más alta, sino **dónde
está el terreno natural**:

* terreno por encima de ambas → **corte**
* terreno por debajo de ambas → **relleno**
* terreno entre medias → mixto, razón ponderada

Se cometió el error de clasificar el talud de frente solo por el signo del
desnivel. Si el lote queda bajo la calle pero el terreno está aún más abajo, hay
que **rellenar**, y el talud ocupa 1,5 veces más ancho.

(Si el proyecto adopta 1:1 para todo, como en el caso real, esta distinción solo
afecta al ancho — pero hay que declararlo explícitamente, no heredarlo por descuido.)

## Auditoría: qué medir siempre

Un corte en ladera **no admite** superficie flotante, huecos, ni zonas planas
dentro de un talud. `terrazas_lib.auditar` devuelve por lote:

| Métrica | Valor sano |
|---|---|
| `cobertura` | 100,000% del lote |
| `hueco` | 0 m² |
| `piezas` | 1 |
| `flotantes` | 0 vértices sin cara |
| `llano_en_talud` | ~0 (fue el fallo principal) |
| `pendiente_fuera_regla` | bajo; sube en esquinas donde dos taludes concurren |

Y sobre el XML terminado, comprobar **posiciones XY con más de una cota**: si hay
alguna, el TIN es inválido y Civil 3D lo destrozará al importar.

## Lo que NO se puede hacer

**Una superficie escalonada no puede ser un TIN único.** Un TIN es una función
z(x,y): no admite dos cotas en el mismo punto. En el caso real había **86 esquinas**
compartidas por lotes con distinta NPT y 22 pares de lotes solapados. Emitir una
superficie combinada de todos los lotes produce exactamente el desastre que se ve
al importarla.

**Emitir una superficie por lote.** Cada una es un TIN válido. Para volúmenes,
usar superficies separadas (plataformas / taludes / calzadas), no una combinada.

## Trampas de datos ya vistas

* **`<P id>` de LandXML no arranca en 1 ni es correlativo.** Hay que remapear por
  id explícito; asumir `id-1 == índice` corrompe la malla en silencio.
* **Nombres de lote vs nombre de archivo.** `Lote_AV-1.xml` ↔ lote `"AV 1"`.
  Comparar literal dejó fuera un área verde de 2.596,8 m² sin avisar. Normalizar
  separadores y avisar de los que no calcen.
* **Lotes contiguos separados hasta 0,14 m.** Reconstruir medianeros con
  tolerancia de 10 cm perdía deslindes enteros (uno de 32,4 m con 3,50 m de
  desnivel, sin talud). Usar 0,30 m.
* **Simplify, no apertura, para limpiar contornos.** La apertura morfológica
  sustituye rectas por arcos: en una prueba multiplicó los vértices de 2.308 a
  18.764 y las astillas de triángulo de 187 a 12.788.
* **Densificar conservando los vértices originales.** Interpolar a intervalos
  regulares sobre todo el anillo borra las esquinas: 593 m² de calzada perdidos.

## Módulos

| Archivo | Qué hace |
|---|---|
| `scripts/mesh_io.py` | Lee/escribe LandXML, triangulación con huecos, interpolación baricéntrica |
| `scripts/terrazas_lib.py` | Clase `Lote`: juntas, función de cota, banda, nube, mallado, `auditar` |
| `scripts/vialidad_lib.py` | Calzada limpia, `z_red`, ramales sin eje, mallado de polígono |
| `scripts/rasantes_red.py` | Rasantes de toda la red con cruces a cota única |
| `scripts/rasantes_lib.py` | Eje por esqueleto de Voronoi y rasante de una calle (mínimos cuadrados con pendiente acotada) |

El paquete es autocontenido: solo depende de `numpy`, `shapely`, `scipy`,
`networkx` y `ezdxf`. Prueba mínima de que funciona:

```python
import shapely.geometry as sg, terrazas_lib
L = terrazas_lib.Lote("P", sg.Polygon([(0,0),(40,0),(40,30),(0,30)]), 110.0)
L.agregar_junta(sg.LineString([(0,0),(40,0)]), 107.0)   # junta 3 m mas baja
L.z(20, 1.5)              # -> 108.500   (1:1 exacto)
L.banda(L.juntas[0]).area # -> 120.00 m2 (40 x 3)
terrazas_lib.auditar(L, *L.mallar())   # cobertura 100 %, todo lo demas en 0
```

## Orden de trabajo

1. Extraer lotes del DXF y NPT de sus rótulos.
2. Vialidad cruda → `limpiar_calzada`.
3. Ejes de calle; `ramales_sin_eje` para lo que quede sin cubrir.
4. `rasantes_red.resolver` con el tope de pendiente del proyecto.
5. Por lote: juntas con calzada (`z_red`) y con vecinos (NPT del más bajo).
6. `Lote.mallar()` y `auditar()`.
7. Escribir LandXML: una superficie por lote más la calzada.
8. DXF de bordes en capas separadas (arranque/pie, calle/medianero) para retoque manual.

## Criterios de proyecto a acordar antes de empezar

No son decisiones técnicas sino de diseño. Preguntar, no asumir:

* **Razón del talud.** 1:1 es lo adoptado en el caso real.
* **Pendiente máxima de calzada.** En camino rural sin pavimentar, **8%**: por
  encima falla la tracción con barro, la distancia de frenado en bajada y la
  carpeta se erosiona. 12% deja el trazado pegado al tope.
* **Tolerancia de acceso** y ancho mínimo de frente a nivel.
* **Grilla de NPT.** Redondear a metro no es un criterio, es un descuido: deja
  plataformas lejos de su cota de equilibrio y saltos innecesarios entre vecinos.
