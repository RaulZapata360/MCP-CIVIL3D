---
name: contornos_y_boundaries
description: "Extrae el paquete completo de contornos (anillo exterior y huecos) de cada superficie de un LandXML y simplifica los vértices redundantes; explica por qué un boundary de Civil 3D no recorta la triangulación."
---

# Contornos, huecos y el engaño de los boundaries

Saca los perímetros reales de cada superficie y los deja utilizables aguas abajo (Dynamo,
Revit, dibujo de verificación).

## Cuándo usar

*   Necesitas el contorno de cada pieza para llevarla a Revit o a Dynamo.
*   Los contornos que extraes traen miles de vértices y hay que aligerarlos.
*   Una superficie se ve bien en Civil 3D pero llega **inflada** a Revit o a la nube.

## Uso

```bash
python skills/superficies/scripts/export_surface_boundaries_complete.py superficies.xml carpeta_salida [OX OY]
```

```bash
python skills/superficies/scripts/simplificar_contornos.py All_Boundaries_Complete.csv 0.01
```

| Script | Qué hace |
|---|---|
| `export_surface_boundaries_complete.py` | Anillo exterior de **cada pieza** de cada superficie + **todos** los anillos interiores (huecos de edificaciones y estructuras). |
| `simplificar_contornos.py` | Quita vértices redundantes. Los contornos salen del borde de la triangulación, así que cada vértice de triángulo sobre un tramo recto acaba en la polilínea. |

Ambos traen rutas del proyecto como valor por defecto; pásales los argumentos para usarlos
en otro sitio.

## ⚠️ Un boundary "hide/outer" NO recorta la triangulación

Es el malentendido que más tiempo ha costado en este proyecto.

En Civil 3D, un boundary de tipo *hide* u *outer* es **solo una máscara de
visualización**. Los triángulos sobrantes siguen dentro de la definición de la superficie.
En pantalla la superficie se ve con su forma correcta; pero **el export a LandXML, el
conector de nube y el link a Revit leen la triangulación**, no el boundary, y ven la forma
inflada — hasta **5,4×** el área real en los casos medidos.

**Cómo detectarlo:** compara el área de la triangulación contra el área del contorno. Si
la superficie "llena" un casco convexo que no le corresponde, tienes el problema.

**Cómo arreglarlo:** hay que hacer que la triangulación *sea* la forma real, no que un
boundary la disimule — recortando la superficie de verdad y re-importándola. El recorte
lo cubre `recorte-y-resta`.

Corolario práctico: **nunca valides una superficie solo mirándola en Civil 3D.** Lo que ves
puede no ser lo que se exporta.

## Un aviso sobre los huecos

Un análisis anterior concluyó que "las superficies no tienen huecos reales y los vacíos son
solo máscaras tipo *Hide*". **Eso era falso** y llevó a perder vacíos de edificación
legítimos. Los huecos de edificación son reales y tienen que viajar en el paquete de
contornos: no los des por máscaras sin comprobarlo pieza por pieza.

## Dependencias

`ezdxf`, `shapely`.

## Ver también

*   `recorte-y-resta` — para que la triangulación pase a ser la forma real.
*   `particion-de-superficies` — para bordes compartidos entre piezas vecinas.
