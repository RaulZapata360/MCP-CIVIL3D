#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from router import detectar_intenciones, REGISTRO_SKILLS

class TestRouterIntenciones(unittest.TestCase):
    def test_clasificacion_recorte(self):
        skills = detectar_intenciones("Quiero recortar la superficie de pavimento y ver el área interior")
        self.assertIn("recorte_superficie_con_perimetro", skills)

    def test_clasificacion_drapeado(self):
        skills = detectar_intenciones("Necesito drapear el contorno en 3D para exportar la cota Z")
        self.assertIn("drapeado_contorno_3d", skills)

    def test_clasificacion_auditoria(self):
        skills = detectar_intenciones("Revisar la auditoria del LandXML y verificar caras invisibles")
        self.assertIn("auditoria_superficies_landxml", skills)

    def test_pipeline_completo(self):
        skills = detectar_intenciones("Ejecutar el pipeline completo de verificación")
        self.assertEqual(len(skills), len(REGISTRO_SKILLS))

if __name__ == "__main__":
    unittest.main()
