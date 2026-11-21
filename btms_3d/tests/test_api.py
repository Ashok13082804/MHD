"""
Unit Tests for Flask REST API Endpoints
"""

import unittest
import json
from btms_3d.backend.app import app


class TestBTMSAPI(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_status_endpoint(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("simulation_time_s", data)
        self.assertIn("battery_pack", data)
        self.assertEqual(len(data["battery_pack"]["cells"]), 180)
        self.assertEqual(data["battery_pack"]["num_cells"], 180)
        self.assertIn("dimensionless", data)

    def test_step_endpoint(self):
        resp = self.client.post("/api/step", json={"dt": 1.0})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data["step_count"], 0)

    def test_control_endpoint(self):
        payload = {"c_rate": 3.0, "threshold_c": 38.0, "B0": 0.8}
        resp = self.client.post("/api/control", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["state"]["controls"]["c_rate"], 3.0)
        self.assertEqual(data["state"]["controls"]["threshold_c"], 38.0)

    def test_inspect_cell_b01(self):
        resp = self.client.get("/api/inspect/BAT-01")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["component_id"], "BAT-01")
        self.assertIn("physical", data)
        self.assertIn("chemical", data)
        self.assertIn("live_engineering", data)
        self.assertIn("live_equations", data)

    def test_inspect_component_radiator(self):
        resp = self.client.get("/api/inspect/radiator")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["component_type"], "radiator")
        self.assertIn("physical", data)
        self.assertIn("chemical", data)

    def test_equations_catalog(self):
        resp = self.client.get("/api/equations")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 24)
        self.assertEqual(len(data["equations"]), 24)

    def test_equations_single(self):
        resp = self.client.get("/api/equations/1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["id"], 1)
        self.assertIn("latex", data)
        self.assertIn("substitution", data)

    def test_ml_prediction_endpoint(self):
        payload = {
            "U_in": 0.05,
            "T_in_c": 25.0,
            "c_rate": 2.0,
            "B0": 0.5
        }
        resp = self.client.post("/api/predict_ml", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("predicted_peak_temp_c", data)
        self.assertIn("physics_solver_temp_c", data)

    def test_hotspot_configuration_endpoints(self):
        """Tests triggering Configuration A through H via /api/hotspot."""
        for cfg in ["A", "B", "C", "D", "E", "F", "G", "H"]:
            resp = self.client.post("/api/hotspot", json={"config_type": cfg, "additional_heat_w": 18.0, "duration_s": 20.0})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data.get("success"))
            self.assertIn("affected_cells", data)

    def test_hotspot_events_and_schedule_endpoints(self):
        """Tests /api/hotspot/events and /api/hotspot/schedule."""
        # Schedule an event
        sched_resp = self.client.post("/api/hotspot/schedule", json={
            "time_s": 15.0,
            "config_type": "B",
            "heat_w": 16.0,
            "duration_s": 20.0
        })
        self.assertEqual(sched_resp.status_code, 200)
        sched_data = sched_resp.get_json()
        self.assertTrue(sched_data.get("success"))

        # Query events
        events_resp = self.client.get("/api/hotspot/events")
        self.assertEqual(events_resp.status_code, 200)
        events_data = events_resp.get_json()
        self.assertTrue(events_data.get("success"))
        self.assertIn("active_events", events_data)
        self.assertIn("history", events_data)

    def test_demonstration_sequence_and_csv_export_endpoints(self):
        """Tests /api/hotspot/demonstration_sequence and /api/export_hotspot_events_csv."""
        demo_resp = self.client.post("/api/hotspot/demonstration_sequence")
        self.assertEqual(demo_resp.status_code, 200)
        demo_data = demo_resp.get_json()
        self.assertTrue(demo_data.get("success"))
        self.assertEqual(demo_data["events_count"], 10)

        csv_resp = self.client.get("/api/export_hotspot_events_csv")
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp.mimetype, "text/csv")
        self.assertIn(b"Event_ID", csv_resp.data)


if __name__ == "__main__":
    unittest.main()
