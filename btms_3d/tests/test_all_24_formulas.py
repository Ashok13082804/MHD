"""
Unit Tests for All 24 Governing Equations (Formulas 1 through 24)
"""

import unittest
from btms_3d.backend.formula_engine.equation_library import GoverningEquationEngine


class TestAll24Formulas(unittest.TestCase):

    def test_eq1_c_rate(self):
        res = GoverningEquationEngine.eq1_battery_c_rate(c_rate=2.0, q_rated=20.0)
        self.assertEqual(res["id"], 1)
        self.assertAlmostEqual(res["result"], 40.0, places=4)
        self.assertEqual(res["unit"], "A")

    def test_eq2_bernardi_heat(self):
        # 40 A, Voc=3.85, Vop=3.65, T=300K, dU/dT=-0.00045
        # q_irr = 40 * 0.2 = 8.0 W
        # q_rev = -40 * 300 * (-0.00045) = 5.4 W
        # q_tot = 13.4 W
        res = GoverningEquationEngine.eq2_bernardi_heat_generation(40.0, 3.85, 3.65, 300.0, -0.00045)
        self.assertEqual(res["id"], 2)
        self.assertAlmostEqual(res["result"], 13.4, places=2)
        self.assertEqual(res["unit"], "W")

    def test_eq4_volume_fraction(self):
        res = GoverningEquationEngine.eq4_nanoparticle_volume_fraction(0.02, 0.01)
        self.assertEqual(res["id"], 4)
        self.assertAlmostEqual(res["result"], 0.03, places=4)

    def test_eq5_nanofluid_density(self):
        res = GoverningEquationEngine.eq5_nanofluid_density(997.1, 3970.0, 6320.0, 0.02, 0.01)
        self.assertEqual(res["id"], 5)
        self.assertGreater(res["result"], 997.1)
        self.assertAlmostEqual(res["result"], 1109.787, places=2)

    def test_eq7_nanofluid_viscosity(self):
        mu_f = 8.91e-4
        res = GoverningEquationEngine.eq7_nanofluid_viscosity_brinkman(mu_f, 0.03)
        self.assertEqual(res["id"], 7)
        self.assertGreater(res["result"], mu_f)

    def test_eq8_thermal_conductivity(self):
        kf = 0.613
        res = GoverningEquationEngine.eq8_nanofluid_thermal_conductivity_maxwell(kf, 40.0, 76.5, 0.02, 0.01)
        self.assertEqual(res["id"], 8)
        self.assertGreater(res["result"], kf)

    def test_eq19_reynolds_number(self):
        res = GoverningEquationEngine.eq19_reynolds_number(1000.0, 0.1, 0.01, 1.0e-3)
        self.assertEqual(res["id"], 19)
        self.assertAlmostEqual(res["result"], 1000.0, places=3)

    def test_eq20_prandtl_number(self):
        res = GoverningEquationEngine.eq20_prandtl_number(1.0e-3, 4000.0, 0.8)
        self.assertEqual(res["id"], 20)
        self.assertAlmostEqual(res["result"], 5.0, places=3)

    def test_eq22_hartmann_number(self):
        res = GoverningEquationEngine.eq22_hartmann_number(1.0, 0.01, 100.0, 0.01)
        self.assertEqual(res["id"], 22)
        self.assertAlmostEqual(res["result"], 1.0, places=3)

    def test_eq23_darcy_number(self):
        res = GoverningEquationEngine.eq23_darcy_number(1.0e-8, 0.01)
        self.assertEqual(res["id"], 23)
        self.assertAlmostEqual(res["result"], 1.0e-4, places=6)

    def test_eq24_pec_factor(self):
        res = GoverningEquationEngine.eq24_thermal_performance_factor(8.0, 4.0, 0.08, 0.04)
        self.assertEqual(res["id"], 24)
        # nu_ratio = 2.0, f_ratio = 2.0 -> eta = 2.0 / 2^(1/3) ~ 1.587
        self.assertGreater(res["result"], 1.0)

    def test_all_24_live_execution(self):
        mock_state = {
            "c_rate": 2.0,
            "q_rated": 20.0,
            "max_cell_temp_c": 35.0,
            "phi1": 0.02,
            "phi2": 0.01,
            "U_in": 0.05,
            "B0": 0.5,
            "k_perm": 1.0e-7,
            "porosity": 0.85,
        }
        eqs = GoverningEquationEngine.get_all_equations_live(mock_state)
        self.assertEqual(len(eqs), 24)
        for idx, eq in enumerate(eqs, 1):
            self.assertEqual(eq["id"], idx)
            self.assertIn("result", eq)
            self.assertIn("latex", eq)
            self.assertIn("substitution", eq)


if __name__ == "__main__":
    unittest.main()
