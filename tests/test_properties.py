"""
Unit Tests for Thermophysical Properties and Physical Validation
"""

import unittest
import numpy as np
import config
from part_a_without_ml.material_properties import (
    validate_nanoparticle_volume_fractions,
    calc_effective_density,
    calc_effective_heat_capacity,
    calc_effective_thermal_conductivity,
    calc_effective_dynamic_viscosity,
    calc_effective_electrical_conductivity,
    calc_joule_heating,
    calc_lorentz_force,
    calc_battery_heat_generation,
)


class TestMaterialProperties(unittest.TestCase):

    def test_volume_fraction_validation(self):
        # Valid cases
        valid, _ = validate_nanoparticle_volume_fractions(0.02, 0.01)
        self.assertTrue(valid)

        # Invalid cases
        invalid_neg, _ = validate_nanoparticle_volume_fractions(-0.01, 0.02)
        self.assertFalse(invalid_neg)

        invalid_sum, _ = validate_nanoparticle_volume_fractions(0.6, 0.5)
        self.assertFalse(invalid_sum)

    def test_density_limiting_case(self):
        # At zero nanoparticle fractions, rho_hnf must exactly equal rho_f
        rho_f = 997.1
        rho_s1 = 3970.0
        rho_s2 = 6320.0
        res = calc_effective_density(rho_f, rho_s1, rho_s2, phi1=0.0, phi2=0.0)
        self.assertAlmostEqual(res["result"], rho_f, places=4)

        # With positive volume fractions, density must strictly increase
        res_mix = calc_effective_density(rho_f, rho_s1, rho_s2, phi1=0.02, phi2=0.01)
        self.assertGreater(res_mix["result"], rho_f)

    def test_thermal_conductivity_limiting_case(self):
        # At zero fractions, k_hnf must equal k_f
        k_f = 0.613
        k_s1 = 40.0
        k_s2 = 76.5
        res = calc_effective_thermal_conductivity(k_f, k_s1, k_s2, phi1=0.0, phi2=0.0)
        self.assertAlmostEqual(res["result"], k_f, places=4)

        # Addition of nanoparticles must enhance thermal conductivity
        res_mix = calc_effective_thermal_conductivity(k_f, k_s1, k_s2, phi1=0.02, phi2=0.01)
        self.assertGreater(res_mix["result"], k_f)

    def test_dynamic_viscosity_limiting_case(self):
        mu_f = 8.91e-4
        res = calc_effective_dynamic_viscosity(mu_f, phi1=0.0, phi2=0.0)
        self.assertAlmostEqual(res["result"], mu_f, places=6)

        res_mix = calc_effective_dynamic_viscosity(mu_f, phi1=0.02, phi2=0.01)
        self.assertGreater(res_mix["result"], mu_f)

    def test_joule_heating_zero_magnetic_field(self):
        # When B0 = 0, Joule heating must be identically zero
        res = calc_joule_heating(sigma_hnf=0.05, B0=0.0, u=0.1)
        self.assertEqual(res["result"], 0.0)

    def test_lorentz_force_zero_magnetic_field(self):
        # When B0 = 0, Lorentz force must be identically zero
        res = calc_lorentz_force(sigma_hnf=0.05, B0=0.0, u=0.1)
        self.assertEqual(res["result"], 0.0)
        self.assertEqual(res["result_magnitude"], 0.0)

    def test_battery_heat_generation(self):
        # Current = 40 A, overpotential = 0.2 V, entropic term
        res = calc_battery_heat_generation(I=40.0, V_oc=3.85, V_op=3.65, T_battery=300.0, dU_oc_dT=-0.00045)
        # Q_irr = 40 * 0.2 = 8.0 W
        # Q_rev = -40 * 300 * (-0.00045) = 5.4 W
        # Q_tot = 13.4 W
        self.assertAlmostEqual(res["result_watts"], 13.4, places=2)


if __name__ == "__main__":
    unittest.main()
