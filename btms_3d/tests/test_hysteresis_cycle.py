"""
Test End-to-End Automatic Hysteresis Cooling Cycle
Tests that:
1. Below threshold (T < 35°C): Cooling is OFF (pump=0, fan=0, valve=0).
2. When cell temperatures exceed T_target (>= 35°C): Cooling automatically turns ON (pump>0, fan>0, valve>0).
3. Under active cooling, cells lose heat to the interleaved cooling plates and cell temperature actually decreases.
4. When cell temperatures drop below T_off (<= 32.5°C): Cooling automatically turns OFF.
"""

import unittest
from btms_3d.backend.numerical_solver.simulation_engine import RealTimeBTMSEngine


class TestHysteresisCoolingCycle(unittest.TestCase):

    def setUp(self):
        self.engine = RealTimeBTMSEngine(initial_temp_c=34.0)
        self.engine.set_control_parameters({
            "threshold_c": 35.0,
            "deactivation_threshold_c": 32.5,
            "cooling_mode": "auto",
            "c_rate": 3.0,
            "U_in": 0.35,
        })

    def test_end_to_end_hysteresis_cycle(self):
        # 1. Standby Verification (T < 35°C)
        t0 = self.engine.step(dt=0.1)
        self.assertLess(t0["battery_pack"]["max_cell_temp_c"], 35.0)
        self.assertFalse(t0["controller"]["cooling_active"])
        self.assertEqual(t0["controller"]["pump_speed_pct"], 0.0)
        self.assertEqual(t0["controller"]["fan_speed_pct"], 0.0)

        # 2. Inject Hotspot on BAT-23 and BAT-24 to trigger thermal threshold
        self.engine.set_cell_hotspot("BAT-23", multiplier=4.0)
        self.engine.set_cell_hotspot("BAT-24", multiplier=4.0)

        # Step until threshold crossed
        peak_t = None
        for _ in range(80):
            t = self.engine.step(dt=0.5)
            if t["battery_pack"]["max_cell_temp_c"] >= 35.0:
                peak_t = t
                break

        self.assertIsNotNone(peak_t, "Cells should cross the 35°C threshold under hotspot loading.")
        self.assertGreaterEqual(peak_t["battery_pack"]["max_cell_temp_c"], 35.0)

        # Step into active cooling
        t_active = self.engine.step(dt=0.5)
        self.assertTrue(t_active["controller"]["cooling_active"], "Cooling must automatically turn ON.")
        self.assertGreater(t_active["controller"]["pump_speed_pct"], 0.0, "Pump duty must be > 0.")
        self.assertGreater(t_active["controller"]["fan_speed_pct"], 0.0, "Fan duty must be > 0.")
        self.assertIn(t_active["controller"]["state_id"], [3, 4, 5], "State must be Active/Nanofluid cooling.")

        # Prove cell temperature actually reduced under cooling
        self.assertLess(
            t_active["battery_pack"]["max_cell_temp_c"],
            peak_t["battery_pack"]["max_cell_temp_c"],
            "Cell temperature must actively drop under active cooling."
        )

        # 3. Allow cooling loop to bring temperature down below T_off (32.5°C)
        self.engine.pack.clear_hotspots()
        self.engine.set_control_parameters({"c_rate": 0.5})

        cooled_down = False
        t_final = None
        for _ in range(120):
            t = self.engine.step(dt=0.5)
            if not t["controller"]["cooling_active"]:
                cooled_down = True
                t_final = t
                break

        self.assertTrue(cooled_down, "Cooling system must bring cells below T_off and automatically turn OFF.")
        self.assertLessEqual(t_final["battery_pack"]["max_cell_temp_c"], 32.5)
        self.assertEqual(t_final["controller"]["pump_speed_pct"], 0.0, "Pump must stop when cooling turns off.")
        self.assertEqual(t_final["controller"]["fan_speed_pct"], 0.0, "Fan must stop when cooling turns off.")
        self.assertIn(t_final["controller"]["state_id"], [1, 7], "Controller must return to OFF or Stabilising.")


if __name__ == "__main__":
    unittest.main()
