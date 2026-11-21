"""
Real-Time Coupled Numerical BTMS Simulation Engine
Integrates 500+ cylindrical cell battery pack, interleaved wavy metal cooling channels, TIM interface,
nanofluid thermophysical models, Darcy-Brinkman porous flow, transverse MHD Lorentz/Joule solver,
8-state thermal hysteresis controller, hydraulic pressure-drop network, and pipeline sampling stations.
"""

import time
import math
import numpy as np
from typing import Dict, Any, List, Optional

from btms_3d.backend.battery.battery_pack_model import CylindricalBatteryPack, BatteryPack50Cells
from btms_3d.backend.nanofluid.nanofluid_properties import NanofluidPropertyEngine
from btms_3d.backend.porous_media.darcy_brinkman import PorousMediaSolver
from btms_3d.backend.mhd.lorentz_joule import MHDSolver
from btms_3d.backend.thermal_controller.cooling_controller import ThermalCoolingController
from btms_3d.backend.formula_engine.equation_library import GoverningEquationEngine


class RealTimeBTMSEngine:
    """Master simulation engine running continuous time-stepping numerical BTMS calculations."""

    def __init__(self, initial_temp_c: float = 25.0):
        # Simulation Clock
        self.sim_time_s = 0.0
        self.start_wall_time = time.time()
        self.step_count = 0
        self.is_running = True
        self.speed_multiplier = 1.0

        # Pack Configuration (Default 180 Cylindrical Cells: 15 rows x 12 cols Series Pack)
        self.num_cells = 180
        self.form_factor = "21700"
        self.plate_material = "aluminum"

        # Primary Simulation Parameters
        self.c_rate = 2.0               # Discharge C-rate
        self.q_rated = 20.0             # Rated capacity [Ah]
        self.threshold_c = 35.0         # Activation threshold [°C] (T_target)
        self.deactivation_threshold_c = 32.5 # Deactivation threshold [°C] (T_off)
        self.cooling_mode = "auto"      # auto, passive, active, nanofluid, mhd_nanofluid, heating, off
        self.U_in = 0.25                # Nominal inlet velocity [m/s]
        self.T_in_c = 22.0              # Inlet coolant temp [°C]
        self.T_amb_c = 25.0             # Ambient air temp [°C]
        self.B0 = 0.50                  # Magnetic field [Tesla]
        self.phi1 = 0.015               # Al2O3 volume fraction
        self.phi2 = 0.010               # CuO volume fraction
        self.k_perm = 1.0e-7            # Porous permeability [m^2]
        self.porosity = 0.85            # Metal foam porosity
        self.pipe_roughness = 1.5e-5    # Drawn aluminum tubing roughness [m]
        self.pump_efficiency = 0.75     # Electric pump combined efficiency

        # Instantiate Battery Pack
        self.pack = CylindricalBatteryPack(
            initial_temp_c=initial_temp_c,
            num_cells=self.num_cells,
            form_factor=self.form_factor,
            plate_material=self.plate_material
        )

        # Update wavy channel geometry
        self._update_channel_geometry()

        # Controller
        self.controller = ThermalCoolingController(
            threshold_c=self.threshold_c,
            mode=self.cooling_mode,
            deactivation_threshold_c=self.deactivation_threshold_c
        )

        # Baseline Nusselt and friction factor for PEC evaluation
        self.Nu_0 = 4.36
        self.f_0 = 0.040
        self.cumulative_cooling_energy_j = 0.0

        # Initial Step to populate fields
        self.step(dt=0.01)

    def _update_channel_geometry(self):
        """Calculates hydraulic channel geometry based on pack row/col layout."""
        rows = self.pack.num_rows
        cols = self.pack.num_cols
        num_ribbons = max(rows - 1, 1)
        microchannels_per_ribbon = 4
        self.num_channels = num_ribbons * microchannels_per_ribbon
        self.channel_w = 0.005          # 5 mm width
        self.channel_h = 0.002          # 2 mm height
        self.channel_area = self.channel_w * self.channel_h # 1.0e-5 m^2 per channel
        self.total_flow_area = self.num_channels * self.channel_area # total cross-section m^2
        self.wetted_perimeter = 2.0 * (self.channel_w + self.channel_h) # 0.014 m
        # Hydraulic diameter: Dh = 4 * A / Pw
        self.Dh = 4.0 * self.channel_area / max(self.wetted_perimeter, 1.0e-6) # 0.002857 m (2.86 mm)
        self.L_channel = cols * self.pack.cell_pitch_x          # Channel length across pack [m]

    def reconfigure(self, num_cells: int = 180, form_factor: str = "21700", plate_material: str = "aluminum"):
        """Reconfigures battery pack cell count, cell form factor, and plate material."""
        self.num_cells = int(num_cells)
        self.form_factor = str(form_factor)
        self.plate_material = str(plate_material)
        self.pack.reconfigure(num_cells=self.num_cells, form_factor=self.form_factor, plate_material=self.plate_material)
        self._update_channel_geometry()

    def set_control_parameters(self, params: Dict[str, Any]):
        """Updates runtime controls from frontend, user inputs, or dataset."""
        if "num_cells" in params or "form_factor" in params or "plate_material" in params:
            new_cells = int(params.get("num_cells", self.num_cells))
            new_ff = str(params.get("form_factor", self.form_factor))
            new_mat = str(params.get("plate_material", self.plate_material))
            if new_cells != self.num_cells or new_ff != self.form_factor or new_mat != self.plate_material:
                self.reconfigure(new_cells, new_ff, new_mat)

        if "c_rate" in params:
            self.c_rate = max(float(params["c_rate"]), 0.0)
        if "threshold_c" in params:
            self.threshold_c = float(params["threshold_c"])
        if "deactivation_threshold_c" in params:
            self.deactivation_threshold_c = float(params["deactivation_threshold_c"])
        self.controller.set_thresholds(self.threshold_c, self.deactivation_threshold_c)

        if "cooling_mode" in params:
            self.cooling_mode = str(params["cooling_mode"]).lower()
            self.controller.set_mode(self.cooling_mode)
        if "U_in" in params or "inlet_velocity" in params:
            self.U_in = max(float(params.get("U_in", params.get("inlet_velocity", self.U_in))), 0.001)
        if "T_in_c" in params or "inlet_temperature_c" in params:
            self.T_in_c = float(params.get("T_in_c", params.get("inlet_temperature_c", self.T_in_c)))
        if "T_amb_c" in params or "ambient_temperature" in params:
            self.T_amb_c = float(params.get("T_amb_c", params.get("ambient_temperature", self.T_amb_c)))
        if "B0" in params or "magnetic_field" in params:
            self.B0 = max(float(params.get("B0", params.get("magnetic_field", self.B0))), 0.0)
        if "phi1" in params or "al2o3_fraction" in params:
            self.phi1 = max(float(params.get("phi1", params.get("al2o3_fraction", self.phi1))), 0.0)
        if "phi2" in params or "cuo_fraction" in params:
            self.phi2 = max(float(params.get("phi2", params.get("cuo_fraction", self.phi2))), 0.0)
        if "k_perm" in params or "permeability" in params:
            self.k_perm = max(float(params.get("k_perm", params.get("permeability", self.k_perm))), 1.0e-11)
        if "porosity" in params:
            self.porosity = min(max(float(params["porosity"]), 0.1), 0.99)
        if "speed_multiplier" in params:
            self.speed_multiplier = max(float(params["speed_multiplier"]), 0.1)
        if "hotspot_intensity_w" in params or "additional_heat_w" in params:
            self.pack.hotspot_intensity_w = max(float(params.get("hotspot_intensity_w", params.get("additional_heat_w", 15.0))), 1.0)
        if "auto_hotspot_enabled" in params:
            self.pack.auto_hotspot_enabled = bool(params["auto_hotspot_enabled"])
        if "auto_hotspot_interval_s" in params:
            self.pack.auto_hotspot_interval_s = max(float(params["auto_hotspot_interval_s"]), 1.0)
        if "hotspot_seed" in params or "seed" in params:
            seed_val = int(params.get("hotspot_seed", params.get("seed", 42)))
            self.pack._rng = random.Random(seed_val)
        # Hotspot injection for individual cell testing
        if "hotspot_cell" in params:
            self.pack.set_cell_hotspot(params["hotspot_cell"], params.get("multiplier", 2.5))
        if "clear_hotspots" in params:
            self.pack.clear_hotspots()

    @property
    def pump_duty(self) -> float:
        if hasattr(self, "last_telemetry") and self.last_telemetry:
            return float(self.last_telemetry.get("controller", {}).get("pump_duty_cycle_pct", 0.0))
        if hasattr(self, "controller") and hasattr(self.controller, "last_pump_duty"):
            return float(self.controller.last_pump_duty)
        return 0.0

    @pump_duty.setter
    def pump_duty(self, val: float):
        if hasattr(self, "controller") and hasattr(self.controller, "last_pump_duty"):
            self.controller.last_pump_duty = float(val)

    def validate_electrical_network(self) -> Dict[str, Any]:
        """Exposes electrical network validation from the underlying battery pack model."""
        return self.pack.validate_electrical_network()

    def set_cell_hotspot(self, cell_id: str, multiplier: float = 2.5):
        """Injects localized heat generation hotspot into a specific cell."""
        self.pack.set_cell_hotspot(cell_id, multiplier)

    def calculate_darcy_friction_factor(self, Re: float) -> float:
        """
        Calculates Darcy friction factor:
        Laminar (Re <= 2300): f = 64 / Re (with rectangular duct aspect ratio adjustment)
        Turbulent (Re > 2300): Haaland formula for commercial pipes.
        """
        if Re <= 0.1:
            return 640.0
        if Re <= 2300.0:
            # Rectangular duct aspect ratio alpha = 2/5 = 0.4 -> f*Re approx 65.0
            return 65.0 / Re
        else:
            rel_roughness = self.pipe_roughness / self.Dh
            term = (rel_roughness / 3.7) ** 1.11 + 6.9 / Re
            return float((-1.8 * math.log10(max(term, 1.0e-10))) ** (-2))

    def step(self, dt: float = 0.5) -> Dict[str, Any]:
        """Advances simulation by dt seconds with full coupled physics calculations."""
        effective_dt = dt * self.speed_multiplier
        self.sim_time_s += effective_dt
        self.step_count += 1

        # 1. Nanofluid Thermophysical Properties
        nf = NanofluidPropertyEngine.calculate_properties(self.phi1, self.phi2)

        # 2. Controller State Evaluation (Hysteresis & Actuator PWM commands)
        current_max_t = max(c.temp_c for c in self.pack.cells)
        ctrl_state = self.controller.update(current_max_t, self.T_amb_c, effective_dt)

        # 3. Dynamic Velocity Field & Flow Coupling
        # If cooling is OFF, pump duty is 0 -> fluid velocity drops to 0!
        pump_factor = (ctrl_state["pump_duty_cycle_pct"] / 100.0) if ctrl_state["cooling_active"] else 0.0
        if ctrl_state["heater_active"]:
            pump_factor = 0.35  # Low circulation for heating

        u_commanded = self.U_in * pump_factor

        # 4. MHD Lorentz Damping (if magnetic field is present)
        effective_B0 = self.B0 if (self.cooling_mode == "mhd_nanofluid" or self.B0 > 0.0) else 0.0
        mhd = MHDSolver.calculate_mhd_effects(nf["sigma_hnf"], effective_B0, max(u_commanded, 0.001), self.Dh, nf["mu_hnf"])
        u_actual = u_commanded * (mhd["velocity_damping_factor"] if u_commanded > 0.0 else 0.0)

        # 5. Hydraulic Calculations (Flow Rate, Reynolds, Friction Factor, Pressure Drop)
        vol_flow_rate_m3_s = u_actual * self.total_flow_area # m^3/s
        vol_flow_rate_l_min = vol_flow_rate_m3_s * 60000.0  # L/min
        mass_flow_rate_kg_s = nf["rho_hnf"] * vol_flow_rate_m3_s # kg/s

        Re = (nf["rho_hnf"] * u_actual * self.Dh) / max(nf["mu_hnf"], 1.0e-9) if u_actual > 0.0 else 0.0
        Pr = (nf["mu_hnf"] * nf["cp_hnf"]) / max(nf["k_hnf"], 1.0e-6)

        # Darcy-Weisbach pressure drop across channels
        f_D = self.calculate_darcy_friction_factor(Re) if Re > 0.0 else 0.0
        if u_actual > 0.0:
            delta_p_channel_pa = f_D * (self.L_channel / self.Dh) * (nf["rho_hnf"] * (u_actual ** 2) / 2.0)
            # Add minor losses (manifolds, elbows, fittings: sum(K) approx 4.5)
            delta_p_minor_pa = 4.5 * (nf["rho_hnf"] * (u_actual ** 2) / 2.0)
            total_delta_p_pa = delta_p_channel_pa + delta_p_minor_pa
        else:
            delta_p_channel_pa = 0.0
            total_delta_p_pa = 0.0

        # Pump power calculations
        p_hydraulic_w = total_delta_p_pa * vol_flow_rate_m3_s # W
        p_electrical_w = p_hydraulic_w / max(self.pump_efficiency, 0.1) if p_hydraulic_w > 0 else 0.0
        self.cumulative_cooling_energy_j += p_electrical_w * effective_dt

        # 6. Convective Heat Transfer in Inter-Cell Channels
        if u_actual > 0.0:
            graetz = max(Re * Pr * (self.Dh / max(self.L_channel, 0.01)), 0.1)
            Nu = 4.36 + 0.036 * graetz * (1.0 + 2.2 * nf["phi_total"])
            # Enhanced with porous matrix if enabled
            porous = PorousMediaSolver.calculate_porous_properties(
                self.k_perm, self.porosity, nf["k_hnf"], k_matrix=167.0, Dh=self.Dh
            )
            h_coolant = (Nu * porous["k_eff_porous"]) / max(self.Dh, 1.0e-4)  # W/(m^2*K)
        else:
            Nu = 4.36
            porous = {"k_eff_porous": nf["k_hnf"], "darcy_number": 1.0e-4}
            h_coolant = 12.0  # Natural convection stagnant limit

        eta_pec = (Nu / self.Nu_0) / max((f_D / self.f_0) ** (1.0 / 3.0), 0.1) if f_D > 0 else 1.0

        # 7. Battery Pack Coupled Energy Step
        pack_state = self.pack.step(
            dt=effective_dt,
            c_rate=self.c_rate,
            h_coolant=h_coolant,
            T_coolant_c=self.T_in_c,
            threshold_c=self.threshold_c,
            cooling_active=ctrl_state["cooling_active"],
            heater_active=ctrl_state["heater_active"],
            heater_power_total_w=ctrl_state.get("heater_power_w", 0.0),
            total_vol_flow_l_min=vol_flow_rate_l_min,
            base_velocity_m_s=u_actual,
            B0=effective_B0,
            lorentz_force=mhd["lorentz_force_N_m3"]
        )

        # 8. Nanofluid Thermal Energy Absorption & Radiator Heat Rejection
        total_heat_absorbed_w = pack_state["total_heat_removed_w"] if ctrl_state["cooling_active"] else 0.0
        if mass_flow_rate_kg_s > 0.0:
            cp_flow = mass_flow_rate_kg_s * nf["cp_hnf"]
            delta_T_coolant = total_heat_absorbed_w / max(cp_flow, 1.0e-3)
            T_outlet_c = self.T_in_c + delta_T_coolant
        else:
            delta_T_coolant = 0.0
            T_outlet_c = self.T_in_c

        # Radiator Heat Rejection Calculation:
        # Fan airflow rejects heat from radiator to ambient
        fan_speed_fraction = (ctrl_state["fan_speed_pct"] / 100.0) if ctrl_state["fan_active"] else 0.0
        air_flow_rate_kg_s = 0.25 * fan_speed_fraction
        cp_air = 1005.0 # J/kg*K
        radiator_effectiveness = 0.72
        if fan_speed_fraction > 0.0 and T_outlet_c > self.T_amb_c:
            q_max_possible = min(mass_flow_rate_kg_s * nf["cp_hnf"], air_flow_rate_kg_s * cp_air) * (T_outlet_c - self.T_amb_c)
            q_radiator_w = radiator_effectiveness * q_max_possible
            T_radiator_return_c = T_outlet_c - (q_radiator_w / max(mass_flow_rate_kg_s * nf["cp_hnf"], 1.0e-3))
        else:
            q_radiator_w = 0.0
            T_radiator_return_c = T_outlet_c

        # 9. Pipeline Sampling Locations (10 continuous loop stations)
        pipeline_stations = self._compute_pipeline_stations(
            self.T_in_c, T_outlet_c, T_radiator_return_c, u_actual, total_delta_p_pa,
            nf, Re, Pr, Nu, total_heat_absorbed_w, mass_flow_rate_kg_s, vol_flow_rate_m3_s
        )

        # Build Full Telemetry State
        telemetry = {
            "simulation_time_s": round(self.sim_time_s, 2),
            "wall_clock_time_s": round(time.time() - self.start_wall_time, 2),
            "step_count": self.step_count,
            "speed_multiplier": self.speed_multiplier,
            "controls": {
                "num_cells": self.num_cells,
                "form_factor": self.form_factor,
                "plate_material": self.plate_material,
                "c_rate": self.c_rate,
                "q_rated": self.q_rated,
                "threshold_c": self.threshold_c,
                "deactivation_threshold_c": self.deactivation_threshold_c,
                "cooling_mode": self.cooling_mode,
                "U_in": self.U_in,
                "T_in_c": self.T_in_c,
                "T_amb_c": self.T_amb_c,
                "B0": self.B0,
                "phi1": self.phi1,
                "phi2": self.phi2,
                "k_perm": self.k_perm,
                "porosity": self.porosity,
            },
            "controller": ctrl_state,
            "battery_pack": pack_state,
            "nanofluid": nf,
            "mhd": mhd,
            "porous": {
                "k_eff_porous": porous["k_eff_porous"],
                "darcy_number": porous["darcy_number"],
                "delta_p_Pa": total_delta_p_pa,
                "friction_factor": f_D,
            },
            "hydraulics": {
                "D_h_m": round(self.Dh, 5),
                "friction_factor_fD": round(f_D, 4),
                "total_delta_p_kPa": round(total_delta_p_pa / 1000.0, 3),
                "vol_flow_rate_l_min": round(vol_flow_rate_l_min, 2),
                "mass_flow_rate_kg_s": round(mass_flow_rate_kg_s, 4),
                "p_hydraulic_w": round(p_hydraulic_w, 2),
                "p_electrical_w": round(p_electrical_w, 2),
                "pump_efficiency": self.pump_efficiency,
                "pump_energy_consumed_j": round(self.cumulative_cooling_energy_j, 1),
                "pump_energy_consumed_kwh": round(self.cumulative_cooling_energy_j / 3.6e6, 4),
            },
            "dimensionless": {
                "Re": round(Re, 2),
                "Pr": round(Pr, 2),
                "Nu": round(Nu, 2),
                "Ha": round(mhd["hartmann_number"], 4),
                "Da": round(porous["darcy_number"], 6),
                "eta_pec": round(eta_pec, 3),
            },
            "cooling_performance": {
                "h_coolant_W_m2K": round(h_coolant, 1),
                "heat_removed_W": round(total_heat_absorbed_w, 2),
                "heat_rejected_radiator_W": round(q_radiator_w, 2),
                "T_inlet_c": round(self.T_in_c, 2),
                "T_outlet_c": round(T_outlet_c, 2),
                "T_radiator_return_c": round(T_radiator_return_c, 2),
                "coolant_delta_T_K": round(delta_T_coolant, 2),
                "flow_rate_L_min": round(vol_flow_rate_l_min, 2),
                "pressure_drop_kPa": round(total_delta_p_pa / 1000.0, 3),
                "cooling_energy_consumed_j": round(self.cumulative_cooling_energy_j, 1),
            },
            "pipeline_stations": pipeline_stations,
            "zones": pack_state.get("zones", {}),
            "modules": pack_state.get("modules", pack_state.get("zones", {})),
            "electrical_validation": pack_state.get("electrical_validation", {}),
            "hotspot_status": {
                "active_scenario": getattr(self.pack, "active_hotspot_scenario", "NONE"),
                "auto_enabled": getattr(self.pack, "auto_hotspot_enabled", False),
                "auto_interval_s": getattr(self.pack, "auto_hotspot_interval_s", 10.0),
                "active_events": pack_state.get("active_hotspot_events", []),
                "active_events_count": len(pack_state.get("active_hotspot_events", [])),
                "event_history_count": len(pack_state.get("hotspot_event_history", [])),
                "scheduled_events_count": pack_state.get("scheduled_events_count", 0),
            },
            "bms": {
                "status": pack_state.get("bms_status", "NORMAL (15-35°C)"),
                "derate_active": pack_state.get("bms_derate_active", False),
                "derate_factor": pack_state.get("bms_derate_factor", 1.0),
                "uniformity_compliant": pack_state.get("uniformity_compliant", True),
                "uniformity_status": pack_state.get("uniformity_status", "OPTIMAL (< 5.0 K)"),
                "cell_counts": pack_state.get("cell_counts", {}),
            },
        }

        # Attach live equations evaluation (24 core + 15 cylindrical A-O)
        flat_state = self._flatten_state_for_eqs(telemetry)
        telemetry["equations_live"] = GoverningEquationEngine.get_all_equations_live(flat_state)
        telemetry["cylindrical_equations"] = GoverningEquationEngine.get_cylindrical_equations_live(flat_state)
        self.last_telemetry = telemetry
        return telemetry

    def _compute_pipeline_stations(
        self, T_in_c: float, T_out_c: float, T_rad_ret: float, u: float, delta_p: float,
        nf: Dict[str, Any], Re: float, Pr: float, Nu: float, q_removed: float,
        m_dot: float, q_vol: float
    ) -> List[Dict[str, Any]]:
        """Generates 10 computational sampling locations along the continuous cooling pipeline loop."""
        n_c = self.num_cells
        half_c = n_c // 2
        stations = [
            ("Station 1: Coolant Reservoir Outlet", 0.0, 0.05, T_rad_ret, 0.05),
            ("Station 2: Circulation Pump Suction Port", 0.1, 0.06, T_rad_ret, 0.06),
            ("Station 3: Pump Impeller Discharge Nozzle", 0.2, 0.95, T_in_c, 0.95),
            ("Station 4: Plate Chiller / Heat Exchanger Bypass", 0.35, 0.90, T_in_c - 0.2, 0.90),
            ("Station 5: Battery Pack Cold Inlet Manifold", 0.50, 0.85, T_in_c, 0.85),
            (f"Station 6: Micro-channel Entrance (Cells 001-{min(50, n_c):03d})", 0.60, 0.78, T_in_c + (T_out_c - T_in_c) * 0.25, 0.78),
            (f"Station 7: Micro-channel Midpoint (Cells {half_c-25:03d}-{half_c+25:03d})", 0.70, 0.70, T_in_c + (T_out_c - T_in_c) * 0.60, 0.70),
            (f"Station 8: Micro-channel Exit (Cells {n_c-50:03d}-{n_c:03d})", 0.80, 0.62, T_in_c + (T_out_c - T_in_c) * 0.90, 0.62),
            ("Station 9: Battery Pack Hot Outlet Manifold", 0.90, 0.55, T_out_c, 0.55),
            ("Station 10: Front Radiator Return Line", 1.0, 0.30, T_rad_ret, 0.30),
        ]

        results = []
        for idx, (name, frac_len, frac_p, temp_val, p_scale) in enumerate(stations, 1):
            local_p = (delta_p * p_scale) / 1000.0  # in kPa
            results.append({
                "station_id": idx,
                "name": name,
                "loop_fraction": frac_len,
                "temperature_c": round(temp_val, 2),
                "temperature_k": round(temp_val + 273.15, 2),
                "velocity_m_s": round(u * (0.85 + 0.3 * (1.0 - frac_len)), 4),
                "pressure_kpa": round(local_p, 3),
                "mass_flow_kg_s": round(m_dot, 4),
                "flow_rate_l_min": round(q_vol * 60000.0, 2),
                "heat_transfer_rate_w": round(q_removed * (1.0 - frac_len), 2),
                "nanoparticle_fraction_pct": round(nf["phi_total"] * 100.0, 2),
                "density_kg_m3": round(nf["rho_hnf"], 1),
                "viscosity_pa_s": round(nf["mu_hnf"], 6),
                "conductivity_w_mk": round(nf["k_hnf"], 4),
                "specific_heat_j_kgk": round(nf["cp_hnf"], 1),
                "local_reynolds": round(Re, 1),
                "local_prandtl": round(Pr, 2),
                "local_nusselt": round(Nu, 2),
                "color_indicator": self._get_pipeline_color(temp_val),
            })
        return results

    def _get_pipeline_color(self, temp_c: float) -> str:
        """Determines pipeline hex color gradient based on local coolant temperature."""
        if temp_c <= 22.0:
            return "#0d47a1"  # Dark blue
        elif temp_c <= 26.0:
            return "#00b0ff"  # Light blue / Cyan
        elif temp_c <= 30.0:
            return "#00e676"  # Green
        elif temp_c <= 34.0:
            return "#ffd600"  # Yellow
        elif temp_c <= 38.0:
            return "#ff6d00"  # Orange
        else:
            return "#d50000"  # Red

    def _flatten_state_for_eqs(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Flattens nested simulation state for the governing equation library."""
        flat = {}
        flat.update(telemetry["controls"])
        flat["max_cell_temp_c"] = telemetry["battery_pack"]["max_cell_temp_c"]
        flat["min_cell_temp_c"] = telemetry["battery_pack"]["min_cell_temp_c"]
        flat["V_oc"] = 3.85
        flat["V_op"] = 3.65
        flat["dU_dT"] = -0.00045
        flat["rho_f"] = 997.10
        flat["rho_s1"] = 3970.0
        flat["rho_s2"] = 6320.0
        flat["cp_f"] = 4179.0
        flat["cp_s1"] = 765.0
        flat["cp_s2"] = 531.8
        flat["mu_f"] = 8.91e-4
        flat["kf"] = 0.6130
        flat["ks1"] = 40.0
        flat["ks2"] = 76.5
        flat["Dh"] = self.Dh
        flat["L_channel"] = self.L_channel
        flat["sigma_hnf"] = telemetry["nanofluid"]["sigma_hnf"]
        flat["heat_flux_w_m2"] = 1250.0

        # Hydraulic equations inputs
        flat["total_delta_p_kPa"] = telemetry["hydraulics"]["total_delta_p_kPa"]
        flat["total_delta_p_Pa"] = telemetry["hydraulics"]["total_delta_p_kPa"] * 1000.0
        flat["vol_flow_rate_l_min"] = telemetry["hydraulics"]["vol_flow_rate_l_min"]
        flat["vol_flow_rate_m3_s"] = telemetry["hydraulics"]["vol_flow_rate_l_min"] / 60000.0
        flat["mass_flow_rate_kg_s"] = telemetry["hydraulics"]["mass_flow_rate_kg_s"]
        flat["p_hydraulic_w"] = telemetry["hydraulics"]["p_hydraulic_w"]
        flat["p_electrical_w"] = telemetry["hydraulics"]["p_electrical_w"]
        flat["f_D"] = telemetry["hydraulics"]["friction_factor_fD"]

        # Cylindrical cell inputs
        flat["cell_radius_m"] = self.pack.cell_radius
        flat["cell_length_m"] = self.pack.cell_length
        flat["cell_mass_kg"] = self.pack.cell_mass
        flat["cell_cp"] = self.pack.cell_cp
        flat["T_outlet_c"] = telemetry["cooling_performance"]["T_outlet_c"]
        flat["rho_hnf"] = telemetry["nanofluid"]["rho_hnf"]
        flat["cp_hnf"] = telemetry["nanofluid"]["cp_hnf"]
        flat["h_coolant"] = telemetry["cooling_performance"]["h_coolant_W_m2K"]
        flat["pump_efficiency"] = self.pump_efficiency
        flat["r_th_total"] = self.pack.r_th_total
        return flat

    def reset(self, initial_temp_c: float = 25.0):
        """Resets battery cells and simulation clock to initial reference conditions."""
        self.sim_time_s = 0.0
        self.start_wall_time = time.time()
        self.step_count = 0
        self.cumulative_cooling_energy_j = 0.0
        self.pack.reset(initial_temp_c)
        self.step(dt=0.0)

    def apply_hotspot_configuration(self, config_type: str, custom_cells: Optional[List[str]] = None,
                                    additional_heat_w: Optional[float] = None, duration_s: float = 30.0,
                                    clear_previous: bool = False) -> Dict[str, Any]:
        """Applies localized overheating event matching Configurations A-H or patterns."""
        res = self.pack.apply_hotspot_configuration(config_type, custom_cells, additional_heat_w, duration_s, clear_previous)
        self.step(dt=0.01)
        return res

    def schedule_hotspot_event(self, time_s: float, config_type: str, cell_ids: Optional[List[str]] = None,
                               heat_w: float = 15.0, duration_s: float = 30.0) -> Dict[str, Any]:
        """Schedules a future overheating event at time_s."""
        return self.pack.schedule_hotspot_event(time_s, config_type, cell_ids, heat_w, duration_s)

    def load_demonstration_sequence(self) -> List[Dict[str, Any]]:
        """Loads and schedules the 10-event demonstration sequence matching Requirement 15."""
        return self.pack.load_demonstration_sequence()

    def export_hotspot_events_csv(self) -> str:
        """Exports recorded event history as CSV string."""
        return self.pack.export_hotspot_events_csv()

    def apply_hotspot_scenario(self, scenario_code: str) -> Dict[str, Any]:
        """Applies predefined hotspot scenario (A to F)."""
        return self.pack.apply_hotspot_scenario(scenario_code)

    def set_custom_hotspot(self, cell_ids: List[str], multiplier: float = 3.0,
                           initial_temp_c: float = None, duration_s: float = 0.0) -> List[str]:
        """Sets custom hotspot parameters on selected cells."""
        return self.pack.set_custom_hotspot(cell_ids, multiplier, initial_temp_c, duration_s)

    def set_auto_hotspot_mode(self, enabled: bool, interval_s: float = 10.0, seed: int = 42):
        """Enables/disables automated periodic hotspot testing."""
        self.pack.set_auto_hotspot_mode(enabled, interval_s, seed)

    def clear_hotspots(self):
        """Clears all active hotspots."""
        self.pack.clear_hotspots()
        self.step(dt=0.01)

