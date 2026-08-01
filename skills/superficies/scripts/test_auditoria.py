#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import os
from auditar_superficie import auditar_landxml

class TestAuditoria(unittest.TestCase):
    def test_auditoria_prueba_ia(self):
        xml_path = r"C:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\PRUEBAS\Civil3D\SUR\prueba ia\superficie que quiero cortar.xml"
        if os.path.exists(xml_path):
            res = auditar_landxml(xml_path)
            self.assertTrue(res["valido"])
            self.assertGreater(res["caras_visibles"], 0)
            self.assertGreater(res["area_2d_calculada"], 0)

if __name__ == "__main__":
    unittest.main()
