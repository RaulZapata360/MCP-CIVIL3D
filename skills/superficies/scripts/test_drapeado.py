#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import os
import tempfile
from drapear_contorno import drapear_polilineas

class TestDrapeado(unittest.TestCase):
    def test_drapeado_prueba_ia(self):
        xml_path = r"C:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\PRUEBAS\Civil3D\SUR\prueba ia\superficie que quiero cortar.xml"
        dxf_path = r"C:\Users\raulz\OneDrive\Escritorio\Trabajo\IA\PRUEBAS\Civil3D\SUR\prueba ia\polilinea de corte.dxf"
        if os.path.exists(xml_path) and os.path.exists(dxf_path):
            with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                res = drapear_polilineas(xml_path, dxf_path, tmp_path)
                self.assertTrue(os.path.exists(res))
                self.assertGreater(os.path.getsize(res), 0)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
