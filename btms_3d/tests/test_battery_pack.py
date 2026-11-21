"""
Unit Tests for 50-Cell EV Traction Battery Pack Model
"""

import unittest
from btms_3d.backend.battery.battery_pack_model import BatteryPack50Cells, IndividualBatteryCell


class TestBatteryPack(unittest.TestCase):

    def setUp(self):
        self.pack = BatteryPack50Cells(initial_temp_c=25.0)

    def test_cell_count_and_naming(self):
        self.assertEqual(len(self.pack.cells), 50)
        expected_ids = [f"BAT-{i+1:02d}" for i in range(50)]
        actual_ids = [c.cell_id for c in self.pack.cells]
        self.assertEqual(actual_ids, expected_ids)

    def test_grid_layout_5x10(self):
        rows = [c.row for c in self.pack.cells]
        cols = [c.col for c in self.pack.cells]
        self.assertEqual(set(rows), {0, 1, 2, 3, 4})
        self.assertEqual(set(cols), {0, 1, 2, 3, 4, 5, 6, 7, 8, 9})
        # Check first and last cell positions
        self.assertEqual((self.pack.cells[0].row, self.pack.cells[0].col), (0, 0))
        self.assertEqual((self.pack.cells[49].row, self.pack.cells[49].col), (4, 9))

    def test_selective_color_mapping(self):
        cell = IndividualBatteryCell("TEST-01", 20.0)
        self.assertIn("Green", cell.determine_color(35.0)["name"])

        cell.temp_c = 28.0
        self.assertIn("Green", cell.determine_color(35.0)["name"])

        cell.temp_c = 34.0
        self.assertIn("Green", cell.determine_color(35.0)["name"])

        cell.temp_c = 38.0
        self.assertIn("Yellow", cell.determine_color(35.0)["name"])

        cell.temp_c = 48.0
        self.assertIn("Red", cell.determine_color(35.0)["name"])

        cell.temp_c = 62.0
        self.assertIn("Red", cell.determine_color(35.0)["name"])

    def test_bernardi_heat_generation(self):
        cell = self.pack.cells[0]
        q = cell.compute_heat_generation(c_rate=2.0)
        self.assertGreater(q, 0.0)
        self.assertGreater(cell.heat_gen_vol_w_m3, 0.0)

    def test_pack_step_execution(self):
        res = self.pack.step(dt=1.0, c_rate=2.0, h_coolant=300.0, T_coolant_c=25.0, threshold_c=35.0)
        self.assertIn("max_cell_temp_c", res)
        self.assertIn("min_cell_temp_c", res)
        self.assertIn("avg_cell_temp_c", res)
        self.assertEqual(len(res["cells"]), 50)
        self.assertIn("hottest_cell_id", res)


if __name__ == "__main__":
    unittest.main()
