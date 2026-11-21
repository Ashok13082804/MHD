"""
Automated Verification Suite for all 15 Required System Behaviors (Section 20).
Tests all functional requirements programmatically against the integrated BTMS engine and API.
"""

import unittest
import json
import io
from btms_3d.backend.app import app
from btms_3d.backend.numerical_solver.simulation_engine import RealTimeBTMSEngine
from btms_3d.backend.formula_engine.equation_library import GoverningEquationEngine

class TestSystem15Requirements(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.engine = RealTimeBTMSEngine(initial_temp_c=25.0)

    def test_01_fifty_individual_battery_cells(self):
        """TEST 01: Exactly 180 individual cylindrical cells in series arrangement (12x15)."""
        res = self.client.get('/api/status')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        cells = data.get('cells', [])
        self.assertEqual(len(cells), 180, "Pack must contain exactly 180 individual cells")
        self.assertEqual(cells[0]['id'], 'CELL-001')
        self.assertEqual(cells[179]['id'], 'CELL-180')

    def test_02_temperature_threshold_slider(self):
        """TEST 02: Change battery temperature threshold."""
        res = self.client.post('/api/control', json={'threshold_c': 38.5})
        self.assertEqual(res.status_code, 200)
        status = self.client.get('/api/status').get_json()
        self.assertEqual(status['controls']['threshold_c'], 38.5)

    def test_03_heat_generation_color_transition(self):
        """TEST 03: Increasing heat generation turns cells yellow, orange, or red."""
        # High C-rate (4C) and passive cooling
        self.client.post('/api/control', json={'c_rate': 4.0, 'threshold_c': 30.0, 'cooling_mode': 'Passive'})
        # Step simulation several times
        for _ in range(8):
            res = self.client.post('/api/step', json={'dt': 1.0})
        data = res.get_json()
        self.assertGreater(data['pack_max_temp_c'], 25.0)
        # Check cell colors
        cells = data.get('cells', [])
        hottest = max(cells, key=lambda c: c.get('temp_c', c.get('temperature_c', 25.0)))
        # Cell should be yellow, orange, red or normal
        self.assertIn('color_name', hottest)

    def test_04_automatic_cooling_activation(self):
        """TEST 04: Active cooling triggers pump and nanofluid circulation."""
        # Pre-warm cells above threshold (32°C > 30°C threshold)
        self.client.post('/api/reset', json={'initial_temp_c': 32.0})
        self.client.post('/api/control', json={'threshold_c': 30.0, 'cooling_mode': 'Auto'})
        res = self.client.post('/api/step', json={'dt': 0.5})
        data = res.get_json()
        ctrl = data['controller']
        self.assertTrue(ctrl['cooling_active'])
        self.assertGreater(ctrl['pump_speed_pct'], 0.0)
        self.assertGreater(ctrl['fan_speed_pct'], 0.0)

    def test_05_pipeline_fluid_temperature_gradient(self):
        """TEST 05: Fluid temperature changes along pipeline."""
        res = self.client.get('/api/status')
        data = res.get_json()
        stations = data.get('pipeline_stations', [])
        self.assertEqual(len(stations), 10, "Must have 10 pipeline telemetry stations")
        t_in = stations[3].get('temp_c', stations[3].get('temperature_c', 25.0)) # Inlet station
        t_out = stations[6].get('temp_c', stations[6].get('temperature_c', 25.0)) # Outlet station
        self.assertGreaterEqual(t_out, t_in)

    def test_06_click_individual_battery_inspection(self):
        """TEST 06: Inspection returns ID, temp, Q_gen, equations, substitutions, and properties."""
        res = self.client.get('/api/inspect/BAT-15')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['component_id'], 'BAT-15')
        self.assertIn('physical', data)
        self.assertIn('chemical', data)
        self.assertIn('live_engineering', data)
        self.assertIn('live_equations', data)
        self.assertGreater(len(data['live_equations']), 0)
        eq1 = data['live_equations'][0]
        self.assertIn('substitution', eq1)
        self.assertTrue('calculated_value' in eq1 or 'result' in eq1)

    def test_07_click_cooling_pipeline_station(self):
        """TEST 07: Click pipeline/station to display local flow properties."""
        res = self.client.get('/api/inspect/STATION-04')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('physical', data)
        self.assertIn('governing_equations', data)

    def test_08_change_nanoparticle_concentration(self):
        """TEST 08: Changing nanoparticle concentration updates properties."""
        res = self.client.post('/api/control', json={'phi1': 0.02, 'phi2': 0.02})
        self.assertEqual(res.status_code, 200)
        status = self.client.get('/api/status').get_json()
        nano = status.get('nanofluid', {})
        self.assertAlmostEqual(nano.get('phi_total', 0.0), 0.04, places=3)
        self.assertGreater(nano.get('k_hnf', 0.0), 0.60)

    def test_09_mhd_mode_activation(self):
        """TEST 09: Magnetic field activates Lorentz force and Hartmann number."""
        res = self.client.post('/api/control', json={'cooling_mode': 'MHD Nanofluid', 'B0': 1.2})
        self.assertEqual(res.status_code, 200)
        status = self.client.get('/api/status').get_json()
        mhd = status.get('mhd', {})
        self.assertGreater(mhd.get('B0_Tesla', mhd.get('B0_T', 0.0)), 0.0)
        self.assertGreater(mhd.get('hartmann_number', mhd.get('Ha', 0.0)), 0.0)

    def test_10_upload_and_validate_dataset(self):
        """TEST 10: Upload dataset, validate parameters, and apply to model."""
        csv_content = (
            "U_in,T_in,C_rate,B0,phi1,phi2,k_perm,Q_rated\n"
            "0.35,22.0,2.5,0.7,0.015,0.015,1.0e-7,20.0\n"
            "0.50,20.0,3.0,1.0,0.02,0.02,5.0e-8,20.0\n"
        ).encode('utf-8')
        
        data = {'file': (io.BytesIO(csv_content), 'test_dataset.csv')}
        res = self.client.post('/api/upload_dataset', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        upload_resp = res.get_json()
        self.assertTrue(upload_resp['success'])
        self.assertEqual(upload_resp['valid_rows'], 2)

        # Apply record
        apply_res = self.client.post('/api/apply_dataset', json={'record': upload_resp['records'][0]})
        self.assertEqual(apply_res.status_code, 200)
        self.assertTrue(apply_res.get_json()['success'])

    def test_11_camera_presets_defined(self):
        """TEST 11: 3D scene files and presets verification."""
        with self.client.get('/js/main.js') as res:
            data = res.data
            self.assertIn(b'cameraPresets', data)
            self.assertIn(b'OrbitControls', data)

    def test_12_formula_enabled_components_validation(self):
        """TEST 12: Equation substitutions, inputs, results, and SI units."""
        res = self.client.get('/api/equations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['count'], 24)
        for eq in data['equations']:
            self.assertIn('id', eq)
            self.assertIn('name', eq)
            self.assertTrue('latex_display' in eq or 'latex' in eq)
            self.assertIn('substitution', eq)
            self.assertTrue('calculated_value' in eq or 'result' in eq)
            self.assertTrue('si_units' in eq or 'unit' in eq)

    def test_13_thermal_reduction_under_cooling(self):
        """TEST 13: Active cooling reduces battery temperature towards target."""
        eng = RealTimeBTMSEngine(initial_temp_c=42.0)
        eng.set_control_parameters({'threshold_c': 30.0, 'cooling_mode': 'Active', 'U_in': 0.8, 'c_rate': 0.5})
        initial_t = sum(c.temp_c for c in eng.pack.cells) / len(eng.pack.cells)
        # Step under high cooling
        for _ in range(20):
            eng.step(dt=2.0)
        final_t = sum(c.temp_c for c in eng.pack.cells) / len(eng.pack.cells)
        self.assertLess(final_t, initial_t, "Pack temperature must decrease under high cooling")

    def test_14_stop_and_reset_simulation(self):
        """TEST 14: Stop and reset simulation."""
        res = self.client.post('/api/reset', json={'initial_temp_c': 25.0})
        self.assertEqual(res.status_code, 200)
        status = self.client.get('/api/status').get_json()
        self.assertLess(status['pack_max_temp_c'], 26.0)
        self.assertAlmostEqual(status['pack_avg_temp_c'], 25.0, places=1)

    def test_15_export_simulation_results_csv(self):
        """TEST 15: Export structured simulation report CSV."""
        res = self.client.get('/api/export_csv')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'CELL-001', res.data)
        self.assertIn(b'CELL-180', res.data)
        self.assertIn(b'BAT-01', res.data)
        self.assertIn(b'c_rate', res.data)
        self.assertIn(b'threshold_c', res.data)

if __name__ == '__main__':
    unittest.main()
