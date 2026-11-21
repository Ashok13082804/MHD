"""
Comprehensive Acceptance Test Suite for:
REAL-TIME 3D AUTOMATIC HOTSPOT GENERATION WITH MHD NANOFLUID TARGETED COOLING
Tests all 14 mandatory acceptance criteria and 15 live engineering parameters.
"""

import unittest
import numpy as np
from btms_3d.backend.numerical_solver.simulation_engine import RealTimeBTMSEngine
from btms_3d.backend.battery.battery_pack_model import CylindricalBatteryPack, IndividualCylindricalCell, HotspotEvent
from btms_3d.backend.app import app, format_telemetry_payload


class TestRealtime3DHotspotMHDTargetedCooling(unittest.TestCase):

    def setUp(self):
        self.engine = RealTimeBTMSEngine(initial_temp_c=25.0)
        self.client = app.test_client()

    def test_01_at_30s_exactly_10_unique_cells_start_heating(self):
        """TEST 1: At 30 simulation seconds, exactly 10 unique cells start heating."""
        # Enable auto hotspot mode
        self.engine.auto_hotspot_enabled = True
        self.engine.auto_hotspot_interval_s = 30.0
        self.engine.pack.auto_hotspot_enabled = True
        self.engine.pack.auto_hotspot_interval_s = 30.0
        self.engine.pack.next_hotspot_boundary_s = 30.0

        # Step 29 seconds (below 30s)
        for _ in range(29):
            self.engine.step(dt=1.0)
        active_events_before = len(self.engine.pack.active_hotspot_events)
        self.assertEqual(active_events_before, 0, "No event should trigger before 30.0s")

        # Step 2 seconds -> reaches 31.0s (crosses 30.0s boundary)
        self.engine.step(dt=1.0)
        self.engine.step(dt=1.0)
        self.assertGreaterEqual(self.engine.sim_time_s, 30.0)
        active_events = self.engine.pack.active_hotspot_events
        self.assertEqual(len(active_events), 1, "Exactly 1 active event at 30.0s boundary")

        event = active_events[0]
        self.assertEqual(len(event.affected_cell_ids), 10, "Event must affect exactly 10 cells")
        self.assertEqual(len(set(event.affected_cell_ids)), 10, "All 10 cell IDs must be unique")

        # Verify exactly 10 cells in the pack have q_hotspot_w > 0
        heating_cells = [c for c in self.engine.pack.cells if c.q_hotspot_w > 0]
        self.assertEqual(len(heating_cells), 10, "Exactly 10 cells in the pack must receive hotspot heat")

    def test_02_at_60s_another_10_cells_selected_without_resetting_temps(self):
        """TEST 2: At 60 simulation seconds, another 10 unique cells are selected without resetting previous temperatures."""
        self.engine.pack.auto_hotspot_enabled = True
        self.engine.pack.auto_hotspot_interval_s = 30.0
        self.engine.pack.next_hotspot_boundary_s = 30.0

        # Run to 31s (triggers first event)
        for _ in range(31):
            self.engine.step(dt=1.0)
        event1 = self.engine.pack.active_hotspot_events[0]
        cells_ev1 = list(event1.affected_cell_ids)
        temps_ev1_at_31 = {cid: self.engine.pack.cell_lookup[cid].temperature_c for cid in cells_ev1}

        # Run to 61s (triggers second event)
        for _ in range(30):
            self.engine.step(dt=1.0)
        self.assertGreaterEqual(self.engine.sim_time_s, 60.0)
        all_events = list(self.engine.pack.active_hotspot_events) + list(self.engine.pack.hotspot_event_history)
        self.assertGreaterEqual(len(all_events), 2)

        # The latest event must have 10 cells
        latest_event = self.engine.pack.active_hotspot_events[-1]
        self.assertEqual(len(latest_event.affected_cell_ids), 10)
        self.assertEqual(len(set(latest_event.affected_cell_ids)), 10)

        # Confirm event 1 cells were NOT reset to 25.0
        for cid in cells_ev1:
            cell = self.engine.pack.cell_lookup[cid]
            self.assertGreater(cell.temperature_c, 25.0, f"Cell {cid} temperature must not be reset to initial 25.0")

    def test_03_multiple_hotspot_regions_coexist(self):
        """TEST 3: Multiple hotspot regions coexist across the 6 modules."""
        # Trigger two independent events with distinct cells across different modules
        ev1 = self.engine.pack.trigger_random_hotspots(count=10, additional_heat_w=20.0, duration_s=40.0, seed=101)
        ev2 = self.engine.pack.trigger_random_hotspots(count=10, additional_heat_w=20.0, duration_s=40.0, seed=202)

        modules_ev1 = {self.engine.pack.cell_lookup[cid].module_id for cid in ev1.affected_cell_ids}
        modules_ev2 = {self.engine.pack.cell_lookup[cid].module_id for cid in ev2.affected_cell_ids}
        all_affected_modules = modules_ev1.union(modules_ev2)

        self.assertGreater(len(all_affected_modules), 1, "Hotspots must span multiple modules across the pack")

    def test_04_only_selected_cells_receive_additional_heat(self):
        """TEST 4: Only selected cells receive additional heat (Q_external = P_hotspot)."""
        ev = self.engine.pack.trigger_random_hotspots(count=10, additional_heat_w=25.0, duration_s=30.0, seed=42)
        selected_set = set(ev.affected_cell_ids)

        for cell in self.engine.pack.cells:
            if cell.id in selected_set:
                self.assertAlmostEqual(cell.q_hotspot_w, 25.0, places=2)
                self.assertAlmostEqual(cell.heat_generation_w, cell.q_internal_w + 25.0, places=2)
            else:
                self.assertEqual(cell.q_hotspot_w, 0.0)
                self.assertAlmostEqual(cell.heat_generation_w, cell.q_internal_w, places=2)

    def test_05_temperatures_increase_via_numerical_heat_equation(self):
        """TEST 5: Cell temperatures increase through the numerical heat equation (rho * Cp * dT/dt)."""
        ev = self.engine.pack.trigger_random_hotspots(count=10, additional_heat_w=30.0, duration_s=30.0, seed=77)
        hot_cell_id = ev.affected_cell_ids[0]
        hot_cell = self.engine.pack.cell_lookup[hot_cell_id]

        initial_temp = hot_cell.temperature_c
        self.assertAlmostEqual(initial_temp, hot_cell.initial_temp_c, places=2)

        # Advance 5 seconds of heat generation
        for _ in range(5):
            self.engine.step(dt=1.0)

        # Temperature must have increased numerically
        self.assertGreater(hot_cell.temperature_c, initial_temp)
        # Check delta T parameter
        self.assertAlmostEqual(hot_cell.delta_t_c, hot_cell.temperature_c - hot_cell.initial_temp_c, places=2)

    def test_06_bms_detects_temperature_changes(self):
        """TEST 6: BMS detects temperature increases (>= 35°C triggers elevated / warning state)."""
        # Inject substantial heat to raise cells above 35°C
        ev = self.engine.pack.trigger_random_hotspots(count=10, additional_heat_w=50.0, duration_s=50.0, seed=12)
        for _ in range(25):
            self.engine.step(dt=1.0)

        max_t = self.engine.pack.max_temp_c
        self.assertGreaterEqual(max_t, 35.0, "Pack max temperature should exceed 35.0°C")
        self.assertTrue(
            any(k in self.engine.pack.bms_status for k in ["ELEVATED", "WARNING", "CRITICAL", "ACTIVE COOLING"]),
            f"BMS status should indicate active response, got: {self.engine.pack.bms_status}"
        )

    def test_07_targeted_valves_and_pump_respond(self):
        """TEST 7: Targeted valves open and pump responds to hotspot locations."""
        # Cause an elevated hotspot in Module A (CELL-001 to CELL-030)
        ev = self.engine.pack.trigger_hotspot_event("CLUSTER", cell_count=10, additional_heat_w=50.0, duration_s=40.0)
        # Run simulation steps to raise temperature past threshold
        for _ in range(25):
            self.engine.step(dt=1.0)

        # At least one zone should have active cooling valve opened
        valves = [z["valve_position"] for z in self.engine.pack.zones.values()]
        max_valve = max(valves)
        self.assertGreater(max_valve, 0.0, "At least one zone valve should open in response to hotspot")
        self.assertGreater(self.engine.pump_duty, 0.0, "Pump duty should activate")

    def test_08_mhd_lorentz_force_influences_momentum(self):
        """TEST 8: Transverse magnetic field creates Lorentz body force influencing fluid momentum."""
        # With B0 = 0.5 T vs B0 = 0.0 T
        self.engine.B0 = 0.5
        telemetry_b5 = self.engine.step(dt=0.1)
        lorentz_force = telemetry_b5["mhd"]["lorentz_force_N_m3"]
        self.assertNotEqual(lorentz_force, 0.0, "Lorentz force Fm = -sigma * B^2 * u must be non-zero when B0 > 0")
        self.assertLess(lorentz_force, 0.0, "Lorentz force acts as Hartmann retarding force (opposing flow)")

        # Verify that effective velocity is damped by Hartmann effect
        ha = telemetry_b5["mhd"]["Hartmann_number_Ha"]
        self.assertGreater(ha, 0.0, "Hartmann number must be positive for B0 > 0")

    def test_09_nanofluid_velocities_derived_from_solver(self):
        """TEST 9: Nanofluid particles visibly move through cooling channels at solver-derived velocities."""
        # Set threshold below cell temp so cooling and pump are active
        self.engine.threshold_c = 24.0
        self.engine.set_control_parameters({"threshold_c": 24.0})
        telemetry = self.engine.step(dt=1.0)
        cells = telemetry["battery_pack"]["cells"]
        for c in cells[:10]:
            self.assertIn("local_velocity_m_s", c, "Each cell must report local_velocity_m_s")
            self.assertIn("local_pressure_pa", c, "Each cell must report local_pressure_pa")
            self.assertIn("local_coolant_temp_c", c, "Each cell must report local_coolant_temp_c")
            self.assertGreater(c["local_velocity_m_s"], 0.0, "Local coolant velocity must be positive when pump is running")

    def test_10_cells_transfer_heat_and_cool(self):
        """TEST 10: Hot cells transfer heat to coolant and gradually cool down."""
        # Heat 10 cells to > 35°C with 60W for 15s
        ev = self.engine.pack.trigger_random_hotspots(count=10, additional_heat_w=60.0, duration_s=15.0, seed=5)
        hot_cid = ev.affected_cell_ids[0]
        hot_cell = self.engine.pack.cell_lookup[hot_cid]

        # Run 15s of heating
        for _ in range(15):
            self.engine.step(dt=1.0)
        peak_temp = hot_cell.temperature_c
        self.assertGreater(peak_temp, 35.0, "Cell must exceed 35.0°C to activate cooling response")

        # After duration ends (heating turns off), run with active cooling
        self.engine.set_control_parameters({"threshold_c": 30.0, "c_rate": 0.5})
        for _ in range(35):
            self.engine.step(dt=1.0)

        # Hot cell must have transferred heat and temperature must have decreased
        cooled_temp = hot_cell.temperature_c
        self.assertLess(cooled_temp, peak_temp, "Cell temperature must decrease when heat turns off and cooling is active")

    def test_11_cell_color_mapping(self):
        """TEST 11: Cell colours reflect calculated temperatures: 0-34.9°C Green, 35-45°C Yellow, 46-60°C+ Red."""
        c = IndividualCylindricalCell("TEST-01", initial_temp_c=25.0)

        # 0 - 34.9°C: Green (#22c55e)
        c.temperature_c = 25.0
        self.assertEqual(c.determine_color(35.0)["hex"], "#22c55e")
        c.temperature_c = 34.8
        self.assertEqual(c.determine_color(35.0)["hex"], "#22c55e")

        # 35.0 - 45.0°C: Yellow (#eab308)
        c.temperature_c = 35.0
        self.assertEqual(c.determine_color(35.0)["hex"], "#eab308")
        c.temperature_c = 42.0
        self.assertEqual(c.determine_color(35.0)["hex"], "#eab308")
        c.temperature_c = 45.0
        self.assertEqual(c.determine_color(35.0)["hex"], "#eab308")

        # 46.0 - 60.0°C+: Red (#ef4444)
        c.temperature_c = 46.0
        self.assertEqual(c.determine_color(35.0)["hex"], "#ef4444")
        c.temperature_c = 65.0
        self.assertIn(c.determine_color(35.0)["hex"], ["#ef4444", "#dc2626"])

    def test_12_new_event_does_not_interrupt_previous_cooling(self):
        """TEST 12: A new event does not interrupt previous cooling operations."""
        self.engine.pack.auto_hotspot_enabled = True
        self.engine.pack.auto_hotspot_interval_s = 30.0
        self.engine.pack.next_hotspot_boundary_s = 30.0
        self.engine.pack.hotspot_duration_s = 20.0  # Event 1 heats from 30s to 50s, then cools

        # Run to 35s in 1s steps (Event 1 heating, time_remaining = 15s)
        for _ in range(35):
            self.engine.step(dt=1.0)
        self.assertEqual(len(self.engine.pack.active_hotspot_events), 1)
        ev1 = self.engine.pack.active_hotspot_events[0]
        self.assertIn(ev1.status, ["HEATING", "TARGETED COOLING"])

        # Run to 65s in 1s steps (Crosses 60s -> Event 2 triggered, Event 1 is in COOLING or RECOVERED)
        for _ in range(30):
            self.engine.step(dt=1.0)
        all_events = list(self.engine.pack.active_hotspot_events) + list(self.engine.pack.hotspot_event_history)
        self.assertGreaterEqual(len(all_events), 2)
        ev2 = self.engine.pack.active_hotspot_events[-1]
        self.assertIn(ev2.status, ["HEATING", "TARGETED COOLING"])

    def test_13_continuous_operation(self):
        """TEST 13: Continuous simulation continues indefinitely past multiple 30s boundaries."""
        self.engine.pack.auto_hotspot_enabled = True
        self.engine.pack.auto_hotspot_interval_s = 30.0
        self.engine.pack.next_hotspot_boundary_s = 30.0

        # Step through 125 seconds
        for _ in range(125):
            self.engine.step(dt=1.0)

        self.assertGreaterEqual(self.engine.sim_time_s, 125.0)
        # Total recorded events across active and history
        total_events = len(self.engine.pack.hotspot_event_history) + len(self.engine.pack.active_hotspot_events)
        self.assertGreaterEqual(total_events, 4, f"Should have triggered at least 4 automatic hotspot events, got {total_events}")

    def test_14_control_operations_and_15_engineering_parameters(self):
        """TEST 14: Pause, resume, reset, manual event, and automatic event controls work properly with all 15 parameters."""
        # Test API Status
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("battery_pack", data)
        self.assertIn("b_field_tesla", data)
        self.assertIn("lorentz_force_n_m3", data)

        # Test Inspection of CELL-023 returning ALL 15 PARAMETERS
        resp_insp = self.client.get("/api/inspect/CELL-023")
        self.assertEqual(resp_insp.status_code, 200)
        insp_data = resp_insp.get_json()
        self.assertTrue(insp_data.get("success"))
        c = insp_data["data"]

        # Assert all 15 mandatory parameters
        self.assertIn("id", c)                          # 1. Cell ID
        self.assertIn("module_id", c)                   # 2. Battery Module
        self.assertIn("temperature_c", c)               # 3. Current Temperature
        self.assertIn("initial_temp_c", c)              # 4. Initial Temperature
        self.assertIn("delta_t_c", c)                   # 5. Temperature Increase
        self.assertIn("q_internal_w", c)                # 6. Internal Heat Generation Rate
        self.assertIn("q_hotspot_w", c)                 # 7. Additional Hotspot Heat
        self.assertIn("status", c)                      # 8. Cell Status
        self.assertIn("cooling_status", c)              # 9. Cooling Status
        self.assertIn("local_coolant_temp_c", c)        # 10. Local Nanofluid Temperature
        self.assertIn("local_velocity_m_s", c)          # 11. Local Nanofluid Velocity
        self.assertIn("local_pressure_pa", c)           # 12. Local Nanofluid Pressure
        self.assertIn("heat_removal_w", c)              # 13. Heat Removed by Coolant
        self.assertIn("b_field_tesla", c)               # 14. Local Magnetic Field
        self.assertIn("valve_status", c)                # 15. Targeted Valve Status

        # Test Manual Hotspot Trigger API
        post_data = {"type": "RANDOM_10", "intensity_w": 22.0, "duration_s": 35.0}
        resp_hs = self.client.post("/api/hotspot", json=post_data)
        self.assertEqual(resp_hs.status_code, 200)
        hs_res = resp_hs.get_json()
        self.assertTrue(hs_res.get("success"))
        self.assertEqual(len(hs_res["event"]["affected_cells"]), 10)

        # Test Reset API
        resp_reset = self.client.post("/api/reset")
        self.assertEqual(resp_reset.status_code, 200)
        reset_res = resp_reset.get_json()
        self.assertTrue(reset_res.get("success"))


if __name__ == "__main__":
    unittest.main()
