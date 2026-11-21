"""
Unit and Integration Tests for Advanced Continuous Battery Operation with
Repeated Localized Hotspots, Connected Kirchhoff Cooling, and Event History.
"""

import unittest
import numpy as np
from btms_3d.backend.battery.battery_pack_model import CylindricalBatteryPack
from btms_3d.backend.numerical_solver.simulation_engine import RealTimeBTMSEngine


class TestAdvancedContinuousHotspots(unittest.TestCase):
    """Verifies continuous operation, multi-hotspot coexistence, and lifecycle tracking."""

    def setUp(self):
        self.pack = CylindricalBatteryPack(initial_temp_c=25.0, num_cells=600)
        self.engine = RealTimeBTMSEngine(initial_temp_c=25.0)

    def test_continuous_operation_multi_event_coexistence(self):
        """Verifies multiple hotspot events run concurrently without resetting simulation."""
        # Initial step
        self.engine.step(dt=2.0)
        self.assertAlmostEqual(self.engine.sim_time_s, 2.0, places=1)
        self.assertEqual(len(self.engine.pack.active_hotspot_events), 0)

        # Trigger Event 1: Config A (CELL-125)
        res1 = self.engine.apply_hotspot_configuration("A", additional_heat_w=18.0, duration_s=15.0)
        self.assertTrue(res1["success"])
        self.assertEqual(len(self.engine.pack.active_hotspot_events), 1)
        self.assertIn("CELL-125", res1["affected_cells"])

        # Step forward 5s: CELL-125 heats up
        self.engine.step(dt=5.0)
        c125 = self.engine.pack.get_cell_by_name("CELL-125")
        self.assertGreater(c125.temp_c, 26.0)

        # Trigger Event 2: Config B without clearing previous event!
        res2 = self.engine.apply_hotspot_configuration("B", additional_heat_w=16.0, duration_s=15.0, clear_previous=False)
        self.assertTrue(res2["success"])
        # Both events must coexist!
        self.assertEqual(len(self.engine.pack.active_hotspot_events), 2)

        # Step forward 10s: First event progresses, second event heats up
        for _ in range(5):
            self.engine.step(dt=2.0)

        telemetry = self.engine.last_telemetry
        bp = telemetry["battery_pack"]
        self.assertIn("cell_counts", bp)
        # Normal cells must be the vast majority (not all turned red!)
        self.assertGreater(bp["cell_counts"]["normal"] + bp["cell_counts"]["elevated"], 150)

    def test_all_configurations_a_through_h_and_patterns(self):
        """Verifies Configurations A through H, geometric patterns, and custom cell selections."""
        configs = ["A", "B", "C", "D", "E", "F", "G", "H", "HORIZONTAL", "VERTICAL", "CENTRAL", "EDGE", "SEPARATED", "MULTI_CLUSTER"]
        expected_min_counts = {
            "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 10, "G": 25, "H": 6,
            "HORIZONTAL": 5, "VERTICAL": 5, "CENTRAL": 8, "EDGE": 6, "SEPARATED": 3, "MULTI_CLUSTER": 10
        }
        for cfg in configs:
            self.pack.clear_hotspots()
            res = self.pack.apply_hotspot_configuration(cfg, additional_heat_w=15.0, duration_s=20.0)
            self.assertTrue(res["success"], f"Failed for config {cfg}")
            self.assertGreaterEqual(res["num_cells"], expected_min_counts[cfg], f"Count mismatch for {cfg}")

        # Custom cell selection
        custom_ids = ["CELL-050", "CELL-100", "CELL-150"]
        res_custom = self.pack.apply_hotspot_configuration("CUSTOM", custom_cells=custom_ids)
        self.assertEqual(res_custom["num_cells"], 3)
        self.assertEqual(res_custom["affected_cells"], custom_ids)

    def test_connected_kirchhoff_cooling_hydraulic_balancing(self):
        """Verifies connected parallel network rebalances flow when multiple zones overheat."""
        # Trigger Config H (multi-zone across distant zones) with strong thermal loading
        self.engine.apply_hotspot_configuration("H", additional_heat_w=80.0, duration_s=40.0)

        # Step simulation to allow heat to cross 35°C threshold and valves to react
        for _ in range(25):
            self.engine.step(dt=1.0)

        zones = self.engine.last_telemetry["zones"]
        active_zones = [z for z in zones.values() if z["valve_position"] > 0.2]
        idle_zones = [z for z in zones.values() if z["valve_position"] <= 0.2]

        # Overheated zones must receive higher flow than idle baseline zones
        self.assertGreater(len(active_zones), 0)
        self.assertGreater(len(idle_zones), 0)
        for az in active_zones:
            for iz in idle_zones:
                self.assertGreater(az["flow_rate_l_min"], iz["flow_rate_l_min"])

    def test_temperature_uniformity_tracking(self):
        """Verifies delta T pack calculation and uniformity compliance status."""
        state = self.engine.step(dt=1.0)
        bp = state["battery_pack"]
        self.assertIn("delta_t_pack_c", bp)
        self.assertIn("uniformity_status", bp)
        self.assertIn("uniformity_compliant", bp)

        # Initially pack is uniform (delta T < 5.0 K)
        self.assertTrue(bp["uniformity_compliant"])

        # Inject strong localized hotspot
        self.engine.apply_hotspot_configuration("A", additional_heat_w=35.0, duration_s=40.0)
        for _ in range(15):
            self.engine.step(dt=1.0)

        state2 = self.engine.last_telemetry["battery_pack"]
        self.assertGreater(state2["delta_t_pack_c"], 1.0)

    def test_bms_protective_power_derating(self):
        """Verifies BMS activates proportional power derating when approaching 60°C."""
        c = self.engine.pack.cells[100]
        c.temp_c = 57.5 # Above 55°C critical threshold

        self.engine.step(dt=0.5)
        bp = self.engine.last_telemetry["battery_pack"]
        self.assertTrue(bp["bms_derate_active"])
        self.assertLess(bp["bms_derate_factor"], 1.0)
        self.assertIn("DERATED", bp["bms_status"])

    def test_demonstration_sequence_and_csv_export(self):
        """Verifies Requirement 15: 10-event demonstration sequence and CSV export."""
        self.engine.reset()
        seq = self.engine.load_demonstration_sequence()
        self.assertEqual(len(seq), 10)

        # Step through timeline to trigger events
        # Step through 40 simulated seconds
        for _ in range(20):
            self.engine.step(dt=2.0)

        csv_content = self.engine.export_hotspot_events_csv()
        self.assertIn("Event_ID", csv_content)
        self.assertIn("Config_Type", csv_content)
        self.assertIn("Peak_Temp_C", csv_content)
        lines = csv_content.strip().split("\n")
        # Header + at least several triggered events
        self.assertGreater(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
