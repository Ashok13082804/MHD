"""
Unit Tests for Thermal Cooling Controller and Hysteresis Logic
"""

import unittest
from btms_3d.backend.thermal_controller.cooling_controller import ThermalCoolingController


class TestCoolingController(unittest.TestCase):

    def setUp(self):
        self.controller = ThermalCoolingController(threshold_c=35.0, mode="hybrid_nanofluid")

    def test_default_state(self):
        self.assertEqual(self.controller.threshold_c, 35.0)
        self.assertEqual(self.controller.deactivation_threshold_c, 32.5)
        self.assertFalse(self.controller.cooling_active)

    def test_threshold_activation(self):
        # Temp below threshold -> cooling inactive
        state = self.controller.update(max_cell_temp_c=30.0)
        self.assertFalse(state["cooling_active"])

        # Temp at or above threshold -> cooling active
        state = self.controller.update(max_cell_temp_c=35.2)
        self.assertTrue(state["cooling_active"])
        self.assertGreater(state["pump_speed_pct"], 0.0)

    def test_hysteresis_band(self):
        # Activate cooling at 36.0°C
        self.controller.update(max_cell_temp_c=36.0)
        self.assertTrue(self.controller.cooling_active)

        # Cool down to 34.0°C (between 32.5 and 35.0) -> cooling must REMAIN ACTIVE due to hysteresis
        state = self.controller.update(max_cell_temp_c=34.0)
        self.assertTrue(state["cooling_active"], "Cooling should stay active within hysteresis band.")

        # Cool down to 32.0°C (below deactivation threshold 32.5°C) -> cooling DEACTIVATES
        state = self.controller.update(max_cell_temp_c=32.0)
        self.assertFalse(state["cooling_active"], "Cooling should deactivate below deactivation threshold.")

    def test_mode_passive(self):
        self.controller.set_mode("passive")
        state = self.controller.update(max_cell_temp_c=40.0)
        self.assertFalse(state["cooling_active"])
        self.assertEqual(state["pump_speed_pct"], 0.0)

    def test_mode_chiller(self):
        # Severe overtemperature triggers chiller boost
        state = self.controller.update(max_cell_temp_c=42.0)
        self.assertTrue(state["chiller_active"])
        self.assertEqual(state["pump_speed_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
