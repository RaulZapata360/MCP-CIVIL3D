---
name: inspeccion_dwg_por_xref
description: "Unifica por XREF todos los DWG de una carpeta en un solo dibujo de comparación visual, con rutas relativas para que la carpeta de salida sea copiable o comprimible sin romper enlaces."
---

# Unificar DWG por XREF para inspección visual

Junta muchos DWG en un solo dibujo para verlos superpuestos en Civil 3D, sin fusionar
geometría ni tocar los originales.

## Cuándo usar

*   Comprobar que un lote de conversiones cayó en su sitio (típico tras una migración IFC).
*   Comparar entregas de la misma zona que llegan en archivos separados.
*   Preparar un paquete de revisión para enviar a alguien.

## Uso

```bash
python skills/dibujo/scripts/unify_xref.py carpeta_dwg carpeta_salida nombre_unificado
```

## Por qué XREF y no un merge

Un `INSERT` copia la geometría: el dibujo se hincha y deja de reflejar los originales
cuando estos cambian. Un **XREF** enlaza. Los originales siguen mandando y el unificado
pesa casi nada.

## Lo que lo hace compartible

El DWG resultante queda en `<carpeta_salida>\<nombre>.dwg` con sus xrefs apuntando por
**ruta relativa** a `<carpeta_salida>\_xref_src\sNNN.dwg`. Basta copiar o comprimir esa
carpeta completa —incluida `_xref_src`— para que abra en otro equipo.

Si mueves el DWG **fuera** de su carpeta de salida, se rompen los enlaces: la ruta relativa
deja de resolver. Mueve la carpeta entera, no el archivo suelto.

## Dependencias

`ezdxf`.

## Ver también

*   `ifc-a-civil3d` — la conversión cuyo resultado se suele inspeccionar así.
