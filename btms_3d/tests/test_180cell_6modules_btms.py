"""
Unit and Integration Tests for 180-Cell BTMS with Six Battery Modules,
Series Connections, and Functional Serpentine Nanofluid Cooling.
"""

import unittest
from btms_3d.backend.app import app
from btms_3d.backend.battery.battery_pack_model import CylindricalBatteryPack, IndividualCylindricalCell
from btms_3d.backend.numerical_solver.simulation_engine import RealTimeBTMSEngine


class Test180Cell6ModulesBTMS(unittest.TestCase):
    """Verifies all components of the 180-cell, 6-module BTMS specification."""

    def setUp(self):
        self.pack = CylindricalBatteryPack(initial_temp_c=25.0, num_cells=180)
        self.engine = RealTimeBTMSEngine(initial_temp_c=25.0)
        self.client = app.test_client()

    def test_01_exact_180_cells_and_module_partitioning(self):
        """Checks exactly 180 cells divided into 6 modules of 30 cells (5x6)."""
        self.assertEqual(len(self.pack.cells), 180)
        modules = {}
        for c in self.pack.cells:
            mod_id = c.module_id
            modules.setdefault(mod_id, []).append(c)

        expected_mods = ["MODULE_A", "MODULE_B", "MODULE_C", "MODULE_D", "MODULE_E", "MODULE_F"]
        self.assertEqual(sorted(list(modules.keys())), sorted(expected_mods))

        # Each module must contain exactly 30 cells in 5 rows x 6 cols
        for mod_id in expected_mods:
            cells = modules[mod_id]
            self.assertEqual(len(cells), 30)
            local_rows = {c.local_row for c in cells}
            local_cols = {c.local_col for c in cells}
            self.assertEqual(local_rows, {0, 1, 2, 3, 4})
            self.assertEqual(local_cols, {0, 1, 2, 3, 4, 5})

        # Cell ID ranges
        self.assertEqual(modules["MODULE_A"][0].cell_id, "CELL-001")
        self.assertEqual(modules["MODULE_A"][-1].cell_id, "CELL-030")
        self.assertEqual(modules["MODULE_B"][0].cell_id, "CELL-031")
        self.assertEqual(modules["MODULE_B"][-1].cell_id, "CELL-060")
        self.assertEqual(modules["MODULE_C"][0].cell_id, "CELL-061")
        self.assertEqual(modules["MODULE_C"][-1].cell_id, "CELL-090")
        self.assertEqual(modules["MODULE_D"][0].cell_id, "CELL-091")
        self.assertEqual(modules["MODULE_D"][-1].cell_id, "CELL-120")
        self.assertEqual(modules["MODULE_E"][0].cell_id, "CELL-121")
        self.assertEqual(modules["MODULE_E"][-1].cell_id, "CELL-150")
        self.assertEqual(modules["MODULE_F"][0].cell_id, "CELL-151")
        self.assertEqual(modules["MODULE_F"][-1].cell_id, "CELL-180")

    def test_02_pure_series_polarity_and_electrical_validation(self):
        """Checks alternating polarity and 180S1P series electrical validation."""
        val = self.pack.validate_electrical_network()
        self.assertEqual(val["status"], "VALID_SERIES_NETWORK")
        self.assertTrue(val["continuity_verified"])
        self.assertEqual(val["total_cells"], 180)
        self.assertEqual(val["num_modules"], 6)
        self.assertEqual(val["nominal_voltage_v"], 666.0)
        self.assertEqual(val["intra_module_busbars_count"], 174)
        self.assertEqual(val["inter_module_jumpers_count"], 5)
        self.assertEqual(val["total_interconnects"], 179)
        self.assertEqual(val["main_positive_terminal"]["cell_id"], "CELL-001")
        self.assertEqual(val["main_negative_terminal"]["cell_id"], "CELL-180")

        # Verify API endpoint
        res = self.client.get('/api/electrical/validate')
        self.assertEqual(res.status_code, 200)
        api_val = res.get_json()
        self.assertEqual(api_val["status"], "VALID_SERIES_NETWORK")
        self.assertEqual(api_val["nominal_voltage_v"], 666.0)

    def test_03_six_module_cooling_zones_and_adaptive_valving(self):
        """Checks 6 independent module cooling zones and adaptive flow control."""
        self.assertEqual(len(self.pack.modules), 6)
        for mod_id in ["MODULE_A", "MODULE_B", "MODULE_C", "MODULE_D", "MODULE_E", "MODULE_F"]:
            self.assertIn(mod_id, self.pack.modules)
            minfo = self.pack.modules[mod_id]
            self.assertEqual(len(minfo["cell_ids"]), 30)

        # Inject heat in Module B (CELL-031 to CELL-040)
        for i in range(31, 41):
            cell = self.pack.get_cell_by_name(f"CELL-{i:03d}")
            cell.temp_c = 44.0

        self.pack.step(dt=1.0, c_rate=1.0, h_coolant=500.0, T_coolant_c=22.0, threshold_c=35.0,
                       cooling_active=True, total_vol_flow_l_min=18.0)

        mod_b = self.pack.modules["MODULE_B"]
        mod_a = self.pack.modules["MODULE_A"]
        # Module B valve must open higher than Module A
        self.assertGreater(mod_b["valve_position"], mod_a["valve_position"])
        self.assertGreater(mod_b["flow_rate_l_min"], mod_a["flow_rate_l_min"])

    def test_04_exact_10_cells_hotspot_trigger(self):
        """Checks that trigger_random_hotspots selects exactly 10 unique cells without duplicates."""
        res = self.pack.trigger_random_hotspots(count=10, additional_heat_w=15.0, duration_s=40.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["num_cells"], 10)
        self.assertEqual(len(set(res["affected_cells"])), 10)
        self.assertEqual(res["additional_heat_w"], 15.0)

        # Verify cells have additional heat
        for cid in res["affected_cells"]:
            c = self.pack.get_cell_by_name(cid)
            self.assertGreater(c.q_hotspot_w, 0.0)

    def test_05_continuous_operation_at_30s_intervals(self):
        """Checks continuous operation with repeated 30-second interval hotspot generation."""
        self.pack.auto_hotspot_enabled = True
        self.pack.auto_hotspot_interval_s = 30.0
        self.pack.hotspot_intensity_w = 15.0

        # Initial state: 0 events
        self.assertEqual(len(self.pack.active_hotspot_events), 0)

        # Advance 29s: No event yet
        self.pack.step(dt=29.0, c_rate=1.0, h_coolant=400.0, T_coolant_c=22.0)
        self.assertEqual(len(self.pack.active_hotspot_events), 0)

        # Advance 2s (t=31s): Event 1 triggered (10 cells)
        self.pack.step(dt=2.0, c_rate=1.0, h_coolant=400.0, T_coolant_c=22.0)
        self.assertEqual(len(self.pack.active_hotspot_events), 1)
        self.assertEqual(self.pack.active_hotspot_events[0].num_cells, 10)

        # Advance to t=62s: Event 2 triggered (another 10 cells)
        self.pack.step(dt=31.0, c_rate=1.0, h_coolant=400.0, T_coolant_c=22.0)
        self.assertGreaterEqual(len(self.pack.active_hotspot_events), 2)

    def test_06_exact_three_color_mapping(self):
        """Checks exact 3-color bands: Green (0-34), Yellow (35-45), Red (46-60), Red Warning (>60)."""
        c = self.pack.cells[0]

        # 0-34°C: Green (#22c55e)
        c.temp_c = 25.0
        self.assertEqual(c.determine_color()["hex"], "#22c55e")
        c.temp_c = 34.0
        self.assertEqual(c.determine_color()["hex"], "#22c55e")

        # 35-45°C: Yellow (#eab308)
        c.temp_c = 35.0
        self.assertEqual(c.determine_color()["hex"], "#eab308")
        c.temp_c = 42.0
        self.assertEqual(c.determine_color()["hex"], "#eab308")
        c.temp_c = 45.0
        self.assertEqual(c.determine_color()["hex"], "#eab308")

        # 46-60°C: Red (#ef4444)
        c.temp_c = 46.0
        self.assertEqual(c.determine_color()["hex"], "#ef4444")
        c.temp_c = 55.0
        self.assertEqual(c.determine_color()["hex"], "#ef4444")
        c.temp_c = 60.0
        self.assertEqual(c.determine_color()["hex"], "#ef4444")

        # > 60°C: Red Critical Warning (#dc2626)
        c.temp_c = 65.0
        self.assertEqual(c.determine_color()["hex"], "#dc2626")


if __name__ == "__main__":
    unittest.main()
