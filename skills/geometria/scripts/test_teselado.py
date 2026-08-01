#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import math
from teselar_arcos import teselar_bulge

class TestTeselado(unittest.TestCase):
    def test_linea_recta(self):
        pts = teselar_bulge((0, 0), (10, 0), 0.0, 0.001)
        self.assertEqual(len(pts), 1)
        self.assertAlmostEqual(pts[0][0], 10.0)
        self.assertAlmostEqual(pts[0][1], 0.0)

    def test_arco_semicirculo(self):
        # Bulge 1.0 representa un semicirculo de r=5 entre (0,0) y (10,0)
        pts = teselar_bulge((0, 0), (10, 0), 1.0, 0.01)
        self.assertGreater(len(pts), 2)
        # El centro esta en (5,0) y r=5. Verificar que los puntos muestreados caen en el arco.
        for x, y in pts:
            dist = math.hypot(x - 5.0, y - 0.0)
            self.assertAlmostEqual(dist, 5.0, places=4)

if __name__ == "__main__":
    unittest.main()
