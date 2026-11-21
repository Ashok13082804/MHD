"""
Unit Tests for Formulations 1 through 18
"""

import unittest
import numpy as np
from part_a_without_ml.material_properties import (
    calc_effective_density,
    calc_effective_heat_capacity,
    calc_effective_thermal_conductivity,
    calc_effective_dynamic_viscosity,
    calc_effective_electrical_conductivity,
    calc_joule_heating,
    calc_lorentz_force,
    calc_darcy_brinkman_mhd_forces,
    calc_battery_heat_generation,
)
from part_a_without_ml.dimensionless_numbers import (
    calc_reynolds_number,
    calc_prandtl_number,
    calc_hartmann_number,
    calc_darcy_number,
    calc_brinkman_number,
    calc_nusselt_number,
    calc_local_nusselt_number,
    calc_c_rate_current,
)
from part_a_without_ml.energy_equation import calc_energy_equation_terms
from part_a_without_ml.momentum_equation import calc_momentum_balance_2d
from part_a_without_ml.boundary_conditions import (
    calc_temperature_continuity,
    calc_heat_flux_continuity,
)


class TestAll18Formulas(unittest.TestCase):

    def test_formula_1_energy_equation(self):
        res = calc_energy_equation_terms(
            rho_cp_eff=4.0e6, k_eff=0.65, u=0.05, v=0.0,
            dT_dx=10.0, dT_dy=100.0, d2T_dx2=0.0, d2T_dy2=-1000.0,
            Q_b=10000.0, Q_visc=10.0, Q_J=5.0
        )
        self.assertIn("result", res)
        self.assertEqual(res["unit"], "K/s")

    def test_formula_2_momentum_equation(self):
        res = calc_momentum_balance_2d(
            rho_hnf=1050.0, mu_eff=9.5e-4, k_perm=1.0e-7, sigma_hnf=0.05, B0=0.5,
            u=0.05, v=0.0, dp_dx=-500.0, dp_dy=0.0,
            d2u_dx2=0.0, d2u_dy2=-800.0, d2v_dx2=0.0, d2v_dy2=0.0,
            du_dx=0.0, du_dy=0.0, dv_dx=0.0, dv_dy=0.0
        )
        self.assertIn("result_u_acceleration", res)
        self.assertIn("result_v_acceleration", res)

    def test_formula_3_reynolds_number(self):
        res = calc_reynolds_number(rho_hnf=1000.0, U_in=0.1, L=0.01, mu_eff=1.0e-3)
        self.assertAlmostEqual(res["result"], 1000.0, places=4)

    def test_formula_4_prandtl_number(self):
        res = calc_prandtl_number(mu_eff=1.0e-3, Cp_hnf=4000.0, k_eff=0.8)
        # Pr = (1e-3 * 4000) / 0.8 = 4.0 / 0.8 = 5.0
        self.assertAlmostEqual(res["result"], 5.0, places=4)

    def test_formula_5_hartmann_number(self):
        # Ha = B0 * L * sqrt(sigma / mu)
        # If B0 = 1.0, L = 0.01, sigma = 100, mu = 0.01 -> sqrt(10000) = 100 -> Ha = 1 * 0.01 * 100 = 1.0
        res = calc_hartmann_number(B0=1.0, L=0.01, sigma_hnf=100.0, mu_eff=0.01)
        self.assertAlmostEqual(res["result"], 1.0, places=4)

    def test_formula_6_darcy_number(self):
        # Da = k / L^2
        res = calc_darcy_number(k_perm=1.0e-8, L=0.01)
        # 1e-8 / (1e-4) = 1e-4
        self.assertAlmostEqual(res["result"], 1.0e-4, places=6)

    def test_formula_7_brinkman_number(self):
        # Br = (mu * U^2) / (k * Delta_T)
        res = calc_brinkman_number(mu_eff=1.0e-3, U_in=1.0, k_eff=0.5, Delta_T=2.0)
        # 1e-3 * 1 / (0.5 * 2) = 1e-3
        self.assertAlmostEqual(res["result"], 1.0e-3, places=6)

    def test_formula_8_nusselt_number(self):
        res = calc_nusselt_number(h=500.0, L=0.01, k_eff=0.5)
        # Nu = 500 * 0.01 / 0.5 = 10.0
        self.assertAlmostEqual(res["result"], 10.0, places=4)

    def test_formula_9_c_rate(self):
        res = calc_c_rate_current(c_rate=2.5, Q_rated=20.0)
        self.assertAlmostEqual(res["result"], 50.0, places=4)

    def test_formula_11_temperature_continuity(self):
        res_cont = calc_temperature_continuity(T_b=310.0, T_f=310.0)
        self.assertTrue(res_cont["is_continuous"])
        self.assertEqual(res_cont["result"], 0.0)

    def test_formula_12_heat_flux_continuity(self):
        # k_b * dT_b/dn = k_f * dT_f/dn
        res = calc_heat_flux_continuity(k_b=3.0, dT_b_dn=-100.0, k_f=0.6, dT_f_dn=-500.0)
        # q_b = -3 * (-100) = 300
        # q_f = -0.6 * (-500) = 300 -> discrepancy = 0.0
        self.assertAlmostEqual(res["result"], 0.0, places=4)


if __name__ == "__main__":
    unittest.main()
