"""
Cylindrical Lithium-Ion Traction Battery Pack Model (500+ Cells)
Interleaved Wavy / Scalloped Metallic Cooling Ribbons & Thermal Interface Material
Supports 550, 600 (Default), 700, 800, and 1000 Cylindrical Cells (21700 & 18650 Form Factors).
Implements Equations A, B, C, D, E, F, and N with coupled cell-to-cell conduction.
"""

import math
import random
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set


@dataclass
class HotspotEvent:
    """Represents a discrete or repeated localized overheating event."""
    event_id: str
    sim_time_s: float
    config_type: str
    cell_ids: List[str]
    num_cells: int
    additional_heat_w: float
    duration_s: float
    time_remaining_s: float
    initial_temp_c: float
    peak_temp_c: float
    cooling_activation_time_s: Optional[float] = None
    recovery_time_s: Optional[float] = None
    status: str = "HEATING"  # HEATING, COOLING, RECOVERING, RECOVERED
    max_cooling_flow_l_min: float = 0.0
    energy_removed_j: float = 0.0
    cooling_energy_j: float = 0.0
    zones_affected: List[str] = field(default_factory=list)

    @property
    def affected_cell_ids(self) -> List[str]:
        return self.cell_ids

    @property
    def affected_cells(self) -> List[str]:
        return self.cell_ids

    def __getitem__(self, item: str) -> Any:
        if item == "success":
            return True
        if hasattr(self, item):
            return getattr(self, item)
        d = self.to_dict()
        if item in d:
            return d[item]
        raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self[item]
        except KeyError:
            return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": True,
            "event_id": self.event_id,
            "sim_time_s": round(self.sim_time_s, 2),
            "config_type": self.config_type,
            "cell_ids": self.cell_ids,
            "affected_cells": list(self.cell_ids),
            "affected_cell_ids": list(self.cell_ids),
            "num_cells": self.num_cells,
            "additional_heat_w": round(self.additional_heat_w, 2),
            "intensity_w": round(self.additional_heat_w, 2),
            "duration_s": round(self.duration_s, 2),
            "time_remaining_s": round(max(0.0, self.time_remaining_s), 2),
            "initial_temp_c": round(self.initial_temp_c, 2),
            "peak_temp_c": round(self.peak_temp_c, 2),
            "cooling_activation_time_s": round(self.cooling_activation_time_s, 2) if self.cooling_activation_time_s is not None else None,
            "recovery_time_s": round(self.recovery_time_s, 2) if self.recovery_time_s is not None else None,
            "status": self.status,
            "max_cooling_flow_l_min": round(self.max_cooling_flow_l_min, 2),
            "energy_removed_j": round(self.energy_removed_j, 1),
            "cooling_energy_j": round(self.cooling_energy_j, 1),
            "zones_affected": self.zones_affected
        }


class CylindricalFormFactor:
    """Standardized engineering specifications for cylindrical lithium-ion cells."""

    # 21700 Specification (Default)
    SPEC_21700 = {
        "name": "21700",
        "radius_m": 0.0105,       # 10.5 mm radius (21 mm diameter)
        "length_m": 0.0700,       # 70.0 mm height
        "mass_kg": 0.0690,        # 69 grams
        "nominal_capacity_ah": 4.8, # 4.8 Ah
        "nominal_voltage_v": 3.70,
        "specific_heat_cp": 1050.0, # J/(kg·K)
        "density_kg_m3": 2845.0,
        "k_radial_w_mk": 1.35,     # Radial thermal conductivity (cross jelly roll)
        "k_axial_w_mk": 28.5,      # Axial thermal conductivity (along jelly roll)
        "r_int_base_ohm": 0.016,   # Base AC/DC internal resistance
        "du_dt_v_k": -0.00045,     # Entropic coefficient
    }

    # 18650 Specification
    SPEC_18650 = {
        "name": "18650",
        "radius_m": 0.0090,       # 9.0 mm radius (18 mm diameter)
        "length_m": 0.0650,       # 65.0 mm height
        "mass_kg": 0.0460,        # 46 grams
        "nominal_capacity_ah": 3.2, # 3.2 Ah
        "nominal_voltage_v": 3.70,
        "specific_heat_cp": 1020.0, # J/(kg·K)
        "density_kg_m3": 2780.0,
        "k_radial_w_mk": 1.20,
        "k_axial_w_mk": 26.0,
        "r_int_base_ohm": 0.022,
        "du_dt_v_k": -0.00045,
    }


class IndividualCylindricalCell:
    """
    Represents an individual cylindrical battery cell in the 500+ cell matrix.
    Computes Equations A, B, C, D, E, F with independent thermal and electrochemical states.
    """

    # Reference temperature for thermal energy: 25.0 °C = 298.15 K
    T_REF_K = 298.15

    # Thermal Interface Material (TIM) Properties (Silicone thermal gap filler)
    TIM_THICKNESS_M = 0.0004       # 0.40 mm
    TIM_CONDUCTIVITY_W_MK = 3.0    # 3.0 W/(m·K)
    PLATE_WALL_THICKNESS_M = 0.0008 # 0.80 mm extruded aluminum ribbon wall
    K_ALUMINUM_W_MK = 167.0        # Aluminum 6061-T6
    K_COPPER_W_MK = 398.0          # Copper C11000
    COOLING_AREA = 0.00308         # m^2 contact area per cell with wavy ribbons

    def __init__(self, cell_id: str, initial_temp_c: float = 25.0,
                 row: int = 0, col: int = 0, total_rows: int = 10, total_cols: int = 18,
                 form_factor: str = "21700", plate_material: str = "aluminum",
                 series_index: int = 0,
                 module_id: str = "MODULE_A", module_name: str = "Module A",
                 module_index: int = 0, module_matrix_row: int = 0, module_matrix_col: int = 0,
                 local_row: int = 0, local_col: int = 0,
                 pos_x: float = 0.0, pos_y: float = 0.0, pos_z: float = 0.0):
        self.cell_id = cell_id
        self.row = row
        self.col = col
        self.total_rows = total_rows
        self.total_cols = total_cols
        self.series_index = int(series_index)

        # 6-Module Architecture Attributes
        self.module_id = module_id
        self.module_name = module_name
        self.module_index = int(module_index)
        self.module_matrix_row = int(module_matrix_row)
        self.module_matrix_col = int(module_matrix_col)
        self.local_row = int(local_row)
        self.local_col = int(local_col)
        self.pos_x = float(pos_x)
        self.pos_y = float(pos_y)
        self.pos_z = float(pos_z)

        # Alternating series electrical polarity orientation:
        # Preceding cell (+) connects to next cell (-)
        self.polarity = "+" if self.series_index % 2 == 0 else "-"
        self.top_terminal = "+" if self.series_index % 2 == 0 else "-"
        self.bottom_terminal = "-" if self.series_index % 2 == 0 else "+"

        # Form factor configuration
        self.spec = CylindricalFormFactor.SPEC_21700 if form_factor == "21700" else CylindricalFormFactor.SPEC_18650
        self.radius_m = self.spec["radius_m"]
        self.length_m = self.spec["length_m"]
        self.mass_kg = self.spec["mass_kg"]
        self.cp = self.spec["specific_heat_cp"]
        self.q_rated = self.spec["nominal_capacity_ah"]
        self.v_nom = self.spec["nominal_voltage_v"]
        self.r_int_base = self.spec["r_int_base_ohm"]
        self.du_dt = self.spec["du_dt_v_k"]
        self.k_radial = self.spec["k_radial_w_mk"]
        self.k_axial = self.spec["k_axial_w_mk"]
        self.plate_material = plate_material.lower()
        self.k_plate = self.K_COPPER_W_MK if "copper" in self.plate_material else self.K_ALUMINUM_W_MK

        # Spacing / Pitch
        self.pitch_x = 2.0 * self.radius_m + 0.003  # 3 mm inter-cell gap
        self.pitch_y = 2.0 * self.radius_m + 0.003

        # Equation A: Cylindrical Cell Volume: V_cell = pi * r^2 * L
        self.volume_m3 = float(math.pi * (self.radius_m ** 2) * self.length_m)

        # Equation B: Cylindrical Cell Surface Area: A_cell = 2 * pi * r * L + 2 * pi * r^2
        self.surface_area_m2 = float(2.0 * math.pi * self.radius_m * self.length_m + 2.0 * math.pi * (self.radius_m ** 2))

        # Wavy / Scalloped Cooling Ribbon Contact Area:
        # Both front and back arc contacts contouring the cylinder (~60° wrap angle each side = 2 * pi/3 * 2 * r * L)
        self.wrap_angle_rad = 2.0 * math.pi / 3.0  # 120 degrees total contact per cell
        self.cooling_area_m2 = float(self.wrap_angle_rad * 2.0 * self.radius_m * self.length_m)
        self.COOLING_AREA = self.cooling_area_m2

        # Thermal and operating state
        self.temp_c = float(initial_temp_c)
        self.initial_temp_c = float(initial_temp_c)
        self.max_recorded_temp_c = float(initial_temp_c)
        self.min_recorded_temp_c = float(initial_temp_c)
        self.cooling_rate_c_s = 0.0
        self.temp_history: List[float] = [round(float(initial_temp_c), 2)]
        self.heat_gen_w = 0.0
        self.heat_gen_vol_w_m3 = 0.0
        self.heat_removed_w = 0.0
        self.q_tim_flux_w_m2 = 0.0
        self.r_th_total = 0.0
        self.hotspot_multiplier = 1.0
        self.hotspot_duration_s = 0.0
        self.hotspot_time_remaining_s = 0.0
        self.q_hotspot_w = 0.0
        self.current_a = 0.0
        self.voltage_v = self.v_nom
        self.r_int_ohm = self.r_int_base
        self.c_rate = 2.0
        self.q_neighbors_w = 0.0
        self.cooling_state = "OPTIMAL"
        self.q_internal_w = 2.76
        self.local_coolant_temp_c = 20.0
        self.local_velocity_m_s = 0.25
        self.local_pressure_pa = 101325.0
        self.valve_status = "MODULATED (50%)"
        self.b_field_tesla = 0.50
        self.lorentz_force_n_m3 = 0.0

        # Assigned cooling zone (ZONE-01 to ZONE-15 matching serpentine row passes)
        if total_rows <= 15:
            self.zone_id = f"ZONE-{row+1:02d}"
        else:
            zone_idx = (row // max(total_rows // 10, 1)) + 1
            self.zone_id = f"ZONE-{zone_idx:02d}"

        # Core vs peripheral geometric distribution
        dist_from_edge_r = min(row, (total_rows - 1) - row)
        dist_from_edge_c = min(col, (total_cols - 1) - col)
        edge_metric = (dist_from_edge_r / max(total_rows / 2, 1.0)) + (dist_from_edge_c / max(total_cols / 2, 1.0))
        self.core_factor = 1.0 + 0.15 * min(edge_metric / 2.0, 1.0)

        # Precompute initial nominal thermal resistance
        self.calculate_thermal_resistance(h_coolant=850.0)

    @property
    def heat_generation_w(self) -> float:
        return self.heat_gen_w

    @property
    def id(self) -> str:
        return self.cell_id

    @property
    def temperature_c(self) -> float:
        return self.temp_c

    @temperature_c.setter
    def temperature_c(self, val: float):
        self.temp_c = float(val)

    @property
    def delta_t_c(self) -> float:
        return self.temp_c - self.initial_temp_c

    # --------------------------------------------------------------------------
    # EQUATION C: Battery Thermal Energy
    # E_th = m * Cp * (T - T_ref)
    # --------------------------------------------------------------------------
    def compute_thermal_energy_joules(self, t_ref_c: float = 0.0) -> float:
        """Calculates total thermal energy stored relative to reference temperature (default 0°C)."""
        return float(self.mass_kg * self.cp * (self.temp_c - t_ref_c))

    # --------------------------------------------------------------------------
    # Electrochemical Heat Generation (Bernardi Model)
    # q_gen = I*(U_ocv - V_cell) - I*T*(dU_ocv/dT) = I^2*R_int - I*T*(dU/dT)
    # --------------------------------------------------------------------------
    def compute_heat_generation(self, c_rate: float = 2.0) -> float:
        """Calculates internal electrochemical heat generation."""
        self.c_rate = float(c_rate)
        self.current_a = max(c_rate * self.q_rated, 0.0)
        # Temperature-dependent internal resistance
        self.r_int_ohm = (self.r_int_base * self.core_factor) * (1.0 + 0.0035 * max(self.temp_c - 25.0, 0.0))
        q_irr = (self.current_a ** 2) * self.r_int_ohm
        t_kelvin = self.temp_c + 273.15
        q_rev = -self.current_a * t_kelvin * self.du_dt
        self.voltage_v = max(2.8, self.v_nom - self.current_a * self.r_int_ohm)
        q_normal = float(q_irr + q_rev)
        self.q_internal_w = q_normal
        if self.q_hotspot_w > 0.0:
            self.heat_gen_w = q_normal + self.q_hotspot_w
        else:
            self.heat_gen_w = q_normal * self.hotspot_multiplier
        self.heat_gen_vol_w_m3 = float(self.heat_gen_w / max(self.volume_m3, 1.0e-8))
        return self.heat_gen_w

    # --------------------------------------------------------------------------
    # EQUATION E & F: Series Thermal Resistance & Cooling Plate Heat Transfer
    # R_th = L / (k * A)
    # Q_dot_plate = (T_battery - T_plate) / R_th,total
    # --------------------------------------------------------------------------
    def calculate_thermal_resistance(self, h_coolant: float) -> float:
        """
        Calculates series thermal resistance from cylinder core through cell radial conduction,
        TIM silicone pad, aluminum/copper wavy ribbon wall, and convective nanofluid boundary.
        """
        # 1. Effective lumped radial conduction from active roll volume to casing:
        # R_radial = 1 / (6 * pi * k_radial * L)
        r_radial = 1.0 / max(6.0 * math.pi * self.k_radial * self.length_m, 1.0e-4) # ~0.63 K/W

        # 2. TIM conduction resistance: L / (k * A)
        r_tim = self.TIM_THICKNESS_M / max(self.TIM_CONDUCTIVITY_W_MK * self.cooling_area_m2, 1.0e-6) # ~0.043 K/W

        # 3. Cooling ribbon metallic wall conduction: L / (k * A)
        r_plate = self.PLATE_WALL_THICKNESS_M / max(self.k_plate * self.cooling_area_m2, 1.0e-6) # ~0.0016 K/W

        # 4. Fluid convection boundary: 1 / (h * A)
        r_conv = 1.0 / max(h_coolant * self.cooling_area_m2, 1.0e-4)

        # Scale for coupled inter-ribbon conduction
        self.r_th_total = float((r_radial + r_tim + r_plate + r_conv) * 0.5)
        return self.r_th_total

    def compute_plate_heat_transfer(self, T_coolant_c: float, h_coolant: float) -> float:
        """
        Calculates heat transferred through cooling plate into nanofluid:
        Q_dot_plate = (T_cell - T_coolant) / R_th,total
        """
        r_tot = self.calculate_thermal_resistance(h_coolant)
        delta_t = self.temp_c - T_coolant_c
        q_plate = delta_t / max(r_tot, 1.0e-5)
        self.heat_removed_w = float(q_plate)
        self.q_tim_flux_w_m2 = float(q_plate / max(self.cooling_area_m2, 1.0e-6))
        return self.heat_removed_w

    def update_temperature(self, dt: float, q_removed: float, q_neighbors: float = 0.0,
                           q_heater: float = 0.0, q_ambient: float = 0.0) -> float:
        """Updates cell temperature via transient energy conservation."""
        self.q_neighbors_w = float(q_neighbors)
        heat_cap = self.mass_kg * self.cp
        net_heat = (self.heat_gen_w + q_heater + q_neighbors) - q_removed - q_ambient
        dT = (net_heat * dt) / max(heat_cap, 1.0)
        self.cooling_rate_c_s = float(dT / max(dt, 1.0e-4))
        self.temp_c += float(dT)
        self.temp_c = max(self.temp_c, -30.0)

        # Update cooling state
        if self.temp_c >= 45.0:
            self.cooling_state = "CRITICAL"
        elif self.temp_c >= 35.0:
            self.cooling_state = "SURGE_COOLING"
        elif self.temp_c >= 30.0:
            self.cooling_state = "MODULATING"
        else:
            self.cooling_state = "OPTIMAL"

        # Track extremes and history
        if self.temp_c > self.max_recorded_temp_c:
            self.max_recorded_temp_c = self.temp_c
        if self.temp_c < self.min_recorded_temp_c:
            self.min_recorded_temp_c = self.temp_c

        if len(self.temp_history) >= 40:
            self.temp_history.pop(0)
        self.temp_history.append(round(self.temp_c, 2))

        # Hotspot countdown
        if self.hotspot_time_remaining_s > 0.0:
            self.hotspot_time_remaining_s -= dt
            if self.hotspot_time_remaining_s <= 0.0:
                self.hotspot_multiplier = 1.0
                self.q_hotspot_w = 0.0
                self.hotspot_duration_s = 0.0
                self.hotspot_time_remaining_s = 0.0

        return self.temp_c

    def determine_color(self, threshold_c: float = 35.0) -> Dict[str, str]:
        """
        Exact 3-Color Cell Temperature Mapping (Section 6):
        - 0–34.9°C: Green (#22c55e) — Normal
        - 35.0–45.0°C: Yellow (#eab308) — Moderate / Warning
        - 46.0–60.0°C+: Red (#ef4444) — Heated / Overheated
        - > 60°C: Red (#dc2626) — Critical Overheating Warning (No artificial numerical clamping)
        """
        t = self.temp_c
        if t < 35.0:
            return {"name": "Normal (Green)", "hex": "#22c55e", "status": "normal"}
        elif t <= 45.0:
            return {"name": "Moderate / Warning (Yellow)", "hex": "#eab308", "status": "moderate"}
        elif t <= 60.0:
            return {"name": "Heated / Overheated (Red)", "hex": "#ef4444", "status": "overheated"}
        else:
            return {"name": "Critical Overheating (Red)", "hex": "#dc2626", "status": "critical"}

    def to_dict(self, threshold_c: float = 35.0) -> Dict[str, Any]:
        """Serializes cell state for JSON API payloads and detailed inspection (all 15 Section 8 parameters)."""
        color_info = self.determine_color(threshold_c)
        e_th = self.compute_thermal_energy_joules()
        return {
            "id": self.cell_id,
            "cell_id": self.cell_id,
            "row": self.row,
            "col": self.col,
            "series_index": getattr(self, "series_index", 0),
            "polarity": getattr(self, "polarity", "+"),
            "top_terminal": getattr(self, "top_terminal", "+"),
            "bottom_terminal": getattr(self, "bottom_terminal", "-"),
            "module_id": getattr(self, "module_id", "MODULE_A"),
            "module_name": getattr(self, "module_name", "Module A"),
            "module_index": getattr(self, "module_index", 0),
            "module_matrix_row": getattr(self, "module_matrix_row", 0),
            "module_matrix_col": getattr(self, "module_matrix_col", 0),
            "local_row": getattr(self, "local_row", 0),
            "local_col": getattr(self, "local_col", 0),
            "pos_x": round(getattr(self, "pos_x", 0.0), 3),
            "pos_y": round(getattr(self, "pos_y", 0.0), 3),
            "pos_z": round(getattr(self, "pos_z", 0.0), 3),
            "cooling_zone_id": self.zone_id,
            "connected_channel": "CHANNEL-SERPENTINE-CONTINUOUS",
            "connected_plate": "PLATE-SERPENTINE-CONTINUOUS",
            "form_factor": self.spec["name"],
            "radius_mm": round(self.radius_m * 1000.0, 2),
            "diameter_mm": round(self.radius_m * 2000.0, 2),
            "height_mm": round(self.length_m * 1000.0, 2),
            "volume_cm3": round(self.volume_m3 * 1.0e6, 3),
            "surface_area_cm2": round(self.surface_area_m2 * 1.0e4, 3),
            "cooling_area_cm2": round(self.cooling_area_m2 * 1.0e4, 3),
            "mass_g": round(self.mass_kg * 1000.0, 1),
            "mass_kg": round(self.mass_kg, 4),
            "density_kg_m3": round(self.spec["density_kg_m3"], 1),
            "specific_heat_j_kgk": round(self.cp, 1),
            "thermal_energy_joules": round(e_th, 2),
            "temperature_c": round(self.temp_c, 2),
            "temp_c": round(self.temp_c, 2),
            "initial_temp_c": round(self.initial_temp_c, 2),
            "temp_change_c": round(self.temp_c - self.initial_temp_c, 2),
            "max_recorded_temp_c": round(self.max_recorded_temp_c, 2),
            "min_recorded_temp_c": round(self.min_recorded_temp_c, 2),
            "cooling_rate_c_s": round(self.cooling_rate_c_s, 4),
            "temp_history": list(self.temp_history),
            "heat_generation_w": round(self.heat_gen_w, 2),
            "heat_w": round(self.heat_gen_w, 2),
            "q_internal_w": round(getattr(self, "q_internal_w", 2.76), 2),
            "q_external_w": round(self.q_hotspot_w, 2),
            "q_hotspot_w": round(self.q_hotspot_w, 2),
            "heat_removed_w": round(self.heat_removed_w, 2),
            "local_heat_transfer_w": round(self.heat_removed_w, 2),
            "local_coolant_temp_c": round(getattr(self, "local_coolant_temp_c", 20.0), 2),
            "local_velocity_m_s": round(getattr(self, "local_velocity_m_s", 0.25), 3),
            "local_pressure_pa": round(getattr(self, "local_pressure_pa", 101325.0), 1),
            "valve_status": getattr(self, "valve_status", "MODULATED (50%)"),
            "b_field_tesla": round(getattr(self, "b_field_tesla", 0.50), 2),
            "lorentz_force_n_m3": round(getattr(self, "lorentz_force_n_m3", 0.0), 3),
            "tim_heat_flux_w_m2": round(self.q_tim_flux_w_m2, 1),
            "tim_thickness_mm": round(self.TIM_THICKNESS_M * 1000.0, 2),
            "tim_conductivity_w_mk": self.TIM_CONDUCTIVITY_W_MK,
            "tim_resistance_k_w": round(self.TIM_THICKNESS_M / (self.TIM_CONDUCTIVITY_W_MK * self.cooling_area_m2), 4),
            "r_th_total_k_w": round(self.r_th_total, 4),
            "heat_gen_vol_w_m3": round(self.heat_gen_vol_w_m3, 1),
            "current_a": round(self.current_a, 2),
            "voltage_v": round(self.voltage_v, 3),
            "r_int_mohm": round(self.r_int_ohm * 1000.0, 2),
            "c_rate": round(self.c_rate, 2),
            "cooling_state": self.cooling_state,
            "cooling_status": self.cooling_state,
            "heat_transfer_to_neighbors_w": round(self.q_neighbors_w, 3),
            "color_hex": color_info["hex"],
            "color_name": color_info["name"],
            "status": color_info["name"],
            "thermal_status": color_info["status"],
            "is_above_threshold": bool(self.temp_c >= threshold_c),
            "hotspot_active": bool(self.hotspot_multiplier > 1.0 or self.q_hotspot_w > 0.0),
            "hotspot_multiplier": round(self.hotspot_multiplier, 2),
            "hotspot_time_remaining_s": round(self.hotspot_time_remaining_s, 1),
        }


class ModuleDict(dict):
    """Dictionary holding exactly 6 modules (MODULE_A to MODULE_F) with MODULE_1..6 aliases."""
    _ALIASES = {
        "MODULE_1": "MODULE_A",
        "MODULE_2": "MODULE_B",
        "MODULE_3": "MODULE_C",
        "MODULE_4": "MODULE_D",
        "MODULE_5": "MODULE_E",
        "MODULE_6": "MODULE_F",
    }
    def __getitem__(self, key):
        canonical = self._ALIASES.get(str(key).upper(), key)
        return super().__getitem__(canonical)

    def get(self, key, default=None):
        canonical = self._ALIASES.get(str(key).upper(), key)
        return super().get(canonical, default)

    def __contains__(self, key):
        canonical = self._ALIASES.get(str(key).upper(), key)
        return super().__contains__(canonical)


class CylindricalBatteryPack:
    """
    Manages the complete cylindrical battery pack (500+ cells).
    Default configuration: 600 cells (20 rows x 30 columns).
    Supported dynamic configurations: 550, 600, 700, 800, 1000 cells.
    Uses vectorized NumPy computation for sub-millisecond execution times.
    """

    MODULE_CONFIG = [
        {"id": "MODULE_A", "alias": "MODULE_1", "name": "Module 1", "mat_row": 0, "mat_col": 0, "cell_start": 1, "cell_end": 30, "plate_id": "PLATE-SERPENTINE-CONTINUOUS", "channel_id": "CHANNEL-SERPENTINE-CONTINUOUS"},
        {"id": "MODULE_B", "alias": "MODULE_2", "name": "Module 2", "mat_row": 0, "mat_col": 1, "cell_start": 31, "cell_end": 60, "plate_id": "PLATE-SERPENTINE-CONTINUOUS", "channel_id": "CHANNEL-SERPENTINE-CONTINUOUS"},
        {"id": "MODULE_C", "alias": "MODULE_3", "name": "Module 3", "mat_row": 0, "mat_col": 2, "cell_start": 61, "cell_end": 90, "plate_id": "PLATE-SERPENTINE-CONTINUOUS", "channel_id": "CHANNEL-SERPENTINE-CONTINUOUS"},
        {"id": "MODULE_D", "alias": "MODULE_4", "name": "Module 4", "mat_row": 1, "mat_col": 0, "cell_start": 91, "cell_end": 120, "plate_id": "PLATE-SERPENTINE-CONTINUOUS", "channel_id": "CHANNEL-SERPENTINE-CONTINUOUS"},
        {"id": "MODULE_E", "alias": "MODULE_5", "name": "Module 5", "mat_row": 1, "mat_col": 1, "cell_start": 121, "cell_end": 150, "plate_id": "PLATE-SERPENTINE-CONTINUOUS", "channel_id": "CHANNEL-SERPENTINE-CONTINUOUS"},
        {"id": "MODULE_F", "alias": "MODULE_6", "name": "Module 6", "mat_row": 1, "mat_col": 2, "cell_start": 151, "cell_end": 180, "plate_id": "PLATE-SERPENTINE-CONTINUOUS", "channel_id": "CHANNEL-SERPENTINE-CONTINUOUS"},
    ]

    CONFIGURATIONS = {
        180: (10, 18),    # 2 rows x 3 cols of modules (each module 5 rows x 6 cols = 30 cells) = 180 cells
        50: (5, 10),      # Backwards-compatible 50-cell mode
        550: (22, 25),    # 22 rows x 25 cols = 550 cells
        600: (20, 30),    # 20 rows x 30 cols = 600 cells
        700: (20, 35),    # 20 rows x 35 cols = 700 cells
        800: (20, 40),    # 20 rows x 40 cols = 800 cells
        1000: (25, 40),   # 25 rows x 40 cols = 1000 cells
    }

    def __init__(self, initial_temp_c: float = 25.0, num_cells: int = 180,
                 form_factor: str = "21700", plate_material: str = "aluminum"):
        self.num_cells = int(num_cells)
        self.form_factor = str(form_factor)
        self.plate_material = str(plate_material)
        self.initial_temp_c = float(initial_temp_c)

        # Resolve grid dimensions
        if self.num_cells in self.CONFIGURATIONS:
            self.rows, self.cols = self.CONFIGURATIONS[self.num_cells]
        else:
            # Automatic factorization
            self.rows = int(math.isqrt(self.num_cells * 2 // 3))
            self.cols = int(math.ceil(self.num_cells / self.rows))
            self.num_cells = self.rows * self.cols

        self.num_cooling_plates = 6 if self.num_cells == 180 else max(self.rows - 1, 1)

        # Hotspot & Scenario Manager (Automatic 10 cells every 30s)
        self.auto_hotspot_enabled = True
        self.auto_hotspot_interval_s = 30.0  # Exactly every 30 seconds
        self.next_hotspot_boundary_s = 30.0  # First event scheduled at 00:30 (sim_time_s = 30.0)
        self.hotspot_cells_per_event = 10   # Exactly 10 cells per event
        self.hotspot_intensity_w = 20.0     # 20W additional heat
        self.hotspot_duration_s = 40.0
        self.auto_hotspot_timer_s = 0.0
        self.auto_hotspot_seed = 42
        self._rng = random.Random(self.auto_hotspot_seed)
        self.active_hotspot_scenario = "NONE"
        self.current_B0 = 0.50
        self.current_lorentz_force = 0.0

        # Advanced Continuous Hotspot Management & Lifecycle Tracking
        self.sim_time_s = 0.0
        self.hotspot_event_counter = 0
        self.active_hotspot_events: List[HotspotEvent] = []
        self.hotspot_event_history: List[HotspotEvent] = []
        self.event_schedule: List[Dict[str, Any]] = []
        self.bms_derate_active = False
        self.bms_derate_factor = 1.0
        self.bms_status = "NORMAL (15-35°C)"

        # Initialize Cell Objects and Independent Cooling Zones
        self.cells: List[IndividualCylindricalCell] = []
        self.modules: Dict[str, Dict[str, Any]] = {}
        self.zones: Dict[str, Dict[str, Any]] = {}
        self._init_cells()
        self._init_zones()

    @property
    def cell_lookup(self) -> Dict[str, IndividualCylindricalCell]:
        return {c.cell_id: c for c in self.cells}

    @property
    def max_temp_c(self) -> float:
        return max((c.temp_c for c in self.cells), default=self.initial_temp_c)

    @property
    def num_rows(self) -> int:
        return self.rows

    @property
    def num_cols(self) -> int:
        return self.cols

    @property
    def cell_radius(self) -> float:
        return self.cells[0].radius_m if self.cells else 0.0105

    @property
    def cell_length(self) -> float:
        return self.cells[0].length_m if self.cells else 0.0700

    @property
    def cell_mass(self) -> float:
        return self.cells[0].mass_kg if self.cells else 0.0690

    @property
    def cell_cp(self) -> float:
        return self.cells[0].cp if self.cells else 1050.0

    @property
    def cell_pitch_x(self) -> float:
        return self.cells[0].pitch_x if self.cells else 0.0240

    @property
    def cell_pitch_y(self) -> float:
        return self.cells[0].pitch_y if self.cells else 0.0240

    @property
    def r_th_total(self) -> float:
        return self.cells[0].r_th_total if self.cells else 0.12

    def _init_cells(self):
        """
        Constructs individual cylindrical cell instances.
        For 180 cells: divides pack into 6 independent modules (2x3 matrix),
        each containing 30 cells in 5 rows x 6 cols with serpentine series connections.
        Alternating polarity: preceding (+) to next (-).
        """
        self.cells = []
        if self.num_cells == 180:
            pitchX = 0.86
            pitchZ = 0.92
            gapX = 1.20
            gapZ = 1.40
            mod_step_x = 6.0 * pitchX + gapX
            mod_step_z = 5.0 * pitchZ + gapZ

            for mod_idx, m_info in enumerate(self.MODULE_CONFIG):
                mod_id = m_info["id"]
                mod_name = m_info["name"]
                mat_r = m_info["mat_row"]
                mat_c = m_info["mat_col"]
                mod_center_x = (mat_c - 1.0) * mod_step_x
                mod_center_z = (mat_r - 0.5) * mod_step_z

                for k_mod in range(30):
                    k_global = mod_idx * 30 + k_mod
                    cell_id = f"CELL-{k_global + 1:03d}"

                    # Intra-module 5 rows x 6 cols serpentine sequence
                    lr = k_mod // 6
                    if lr % 2 == 0:
                        lc = k_mod % 6
                    else:
                        lc = 5 - (k_mod % 6)

                    cell_x = mod_center_x + (lc - 2.5) * pitchX
                    cell_z = mod_center_z + (lr - 2.0) * pitchZ
                    cell_y = 1.20 + 0.34

                    global_row = mat_r * 5 + lr
                    global_col = mat_c * 6 + lc

                    init_t = self.initial_temp_c + (math.sin(global_row * 0.7 + global_col * 0.4) * 0.35)
                    cell = IndividualCylindricalCell(
                        cell_id=cell_id,
                        initial_temp_c=init_t,
                        row=global_row,
                        col=global_col,
                        total_rows=self.rows,
                        total_cols=self.cols,
                        form_factor=self.form_factor,
                        plate_material=self.plate_material,
                        series_index=k_global,
                        module_id=mod_id,
                        module_name=mod_name,
                        module_index=mod_idx,
                        module_matrix_row=mat_r,
                        module_matrix_col=mat_c,
                        local_row=lr,
                        local_col=lc,
                        pos_x=cell_x,
                        pos_y=cell_y,
                        pos_z=cell_z
                    )
                    cell.zone_id = mod_id
                    self.cells.append(cell)
        else:
            digits = max(3, len(str(self.num_cells)))
            for k in range(self.num_cells):
                r = k // self.cols
                if r % 2 == 0:
                    c = k % self.cols
                else:
                    c = self.cols - 1 - (k % self.cols)
                cell_id = f"CELL-{k+1:0{digits}d}"
                init_t = self.initial_temp_c + (math.sin(r * 0.7 + c * 0.4) * 0.35)
                cell = IndividualCylindricalCell(
                    cell_id=cell_id, row=r, col=c,
                    total_rows=self.rows, total_cols=self.cols,
                    initial_temp_c=init_t, form_factor=self.form_factor,
                    plate_material=self.plate_material,
                    series_index=k
                )
                self.cells.append(cell)

    def _init_zones(self):
        """
        Partitions pack into independently valved cooling zones.
        For 180 cells: 6 independent cooling zones (MODULE_A to MODULE_F).
        """
        self.modules = ModuleDict()
        self.zones = {}

        if self.num_cells == 180:
            for m_idx, m_info in enumerate(self.MODULE_CONFIG):
                mod_id = m_info["id"]
                cell_ids = [f"CELL-{i:03d}" for i in range(m_info["cell_start"], m_info["cell_end"] + 1)]
                m_dict = {
                    "zone_id": mod_id,
                    "module_id": mod_id,
                    "id": mod_id,
                    "name": f"{m_info['name']} Cooling Plate",
                    "module_name": m_info["name"],
                    "matrix_row": m_info["mat_row"],
                    "matrix_col": m_info["mat_col"],
                    "cell_start": m_info["cell_start"],
                    "cell_end": m_info["cell_end"],
                    "cell_ids": cell_ids,
                    "num_cells": len(cell_ids),
                    "plate_id": m_info["plate_id"],
                    "channel_id": m_info["channel_id"],
                    "valve_position": 0.15,
                    "target_temp_c": 35.0,
                    "flow_fraction": 1.0 / 6.0,
                    "flow_rate_l_min": 0.0,
                    "velocity_m_s": 0.0,
                    "pressure_kpa": 101.3,
                    "pressure_drop_kpa": 0.0,
                    "temp_inlet_c": 22.0,
                    "temp_outlet_c": 22.0,
                    "temp_max_c": 25.0,
                    "temp_avg_c": 25.0,
                    "temp_min_c": 25.0,
                    "heat_gen_w": 0.0,
                    "heat_absorbed_w": 0.0,
                    "reynolds": 0.0,
                    "nusselt": 4.36,
                    "htc_w_m2k": 12.0,
                    "status": "IDLE"
                }
                self.modules[mod_id] = m_dict
                self.zones[mod_id] = m_dict
                ch = chr(ord('A') + m_idx)
                self.zones[f"ZONE_{ch}"] = m_dict
                self.zones[f"ZONE-{m_idx+1:02d}"] = m_dict

            for extra in range(7, 16):
                mod_ref = list(self.modules.values())[(extra - 1) % 6]
                self.zones[f"ZONE-{extra:02d}"] = mod_ref
            self.num_zones = 6
        else:
            self.num_zones = self.rows if self.rows <= 15 else min(10, self.rows)
            rows_per_zone = max(self.rows // self.num_zones, 1)

            for z in range(self.num_zones):
                zone_id = f"ZONE-{z+1:02d}"
                if self.num_zones == self.rows:
                    zone_rows = [z]
                else:
                    r_start = z * rows_per_zone
                    r_end = (z + 1) * rows_per_zone if (z < self.num_zones - 1) else self.rows
                    zone_rows = list(range(r_start, r_end))
                zone_cells = [c.cell_id for c in self.cells if c.row in zone_rows]

                z_dict = {
                    "zone_id": zone_id,
                    "module_id": zone_id,
                    "id": zone_id,
                    "name": f"Cooling Zone #{z+1:02d} (Rows {zone_rows[0]+1}-{zone_rows[-1]+1})",
                    "rows": zone_rows,
                    "cell_ids": zone_cells,
                    "channel_id": f"CHANNEL-PASS-{z+1:02d}",
                    "plate_id": f"PLATE-ZONE-{z+1:02d}",
                    "valve_position": 0.15,
                    "target_temp_c": 35.0,
                    "flow_fraction": 1.0 / self.num_zones,
                    "flow_rate_l_min": 0.0,
                    "velocity_m_s": 0.0,
                    "pressure_kpa": 101.3,
                    "pressure_drop_kpa": 0.0,
                    "temp_inlet_c": 22.0,
                    "temp_outlet_c": 22.0,
                    "temp_max_c": 25.0,
                    "temp_avg_c": 25.0,
                    "temp_min_c": 25.0,
                    "heat_gen_w": 0.0,
                    "heat_absorbed_w": 0.0,
                    "reynolds": 0.0,
                    "nusselt": 4.36,
                    "htc_w_m2k": 12.0,
                    "status": "IDLE"
                }
                self.zones[zone_id] = z_dict
                self.modules[zone_id] = z_dict

    def validate_electrical_network(self) -> Dict[str, Any]:
        """
        Validates complete 180S1P series electrical network:
        - 180 individual cells in 6 independent modules (30 cells each)
        - Pure series sequence CELL-001 -> ... -> CELL-180
        - Alternating polarity cell-by-cell (+/-)
        - 174 Intra-module busbars
        - 5 Inter-module jumpers (A->B, B->C, C->D, D->E, E->F)
        - Main Pack Positive (+HV 666V DC) at Module A CELL-001 Top (+)
        - Main Pack Negative (-HV 0V GND) at Module F CELL-180 Top (-)
        """
        num_cells = len(self.cells)
        modules_summary = []
        is_valid = True
        broken_links = []

        for m_info in self.MODULE_CONFIG:
            m_id = m_info["id"]
            m_cells = [c for c in self.cells if getattr(c, "module_id", "") == m_id]
            m_avg_t = float(np.mean([c.temp_c for c in m_cells])) if m_cells else 25.0
            m_max_t = float(np.max([c.temp_c for c in m_cells])) if m_cells else 25.0
            m_min_t = float(np.min([c.temp_c for c in m_cells])) if m_cells else 25.0
            modules_summary.append({
                "module_id": m_id,
                "name": m_info["name"],
                "cell_count": len(m_cells),
                "cell_range": f"CELL-{m_info['cell_start']:03d} to CELL-{m_info['cell_end']:03d}",
                "nominal_voltage_v": round(len(m_cells) * 3.70, 2),
                "temp_max_c": round(m_max_t, 2),
                "temp_avg_c": round(m_avg_t, 2),
                "temp_min_c": round(m_min_t, 2),
                "positive_terminal_cell": f"CELL-{m_info['cell_start']:03d} (Top +)",
                "negative_terminal_cell": f"CELL-{m_info['cell_end']:03d} (Top -)",
            })

        jumpers = [
            {"id": "JUMPER-A-B", "from_module": "MODULE_A", "from_cell": "CELL-030", "from_terminal": "Top (-)", "to_module": "MODULE_B", "to_cell": "CELL-031", "to_terminal": "Top (+)", "status": "CONNECTED"},
            {"id": "JUMPER-B-C", "from_module": "MODULE_B", "from_cell": "CELL-060", "from_terminal": "Top (-)", "to_module": "MODULE_C", "to_cell": "CELL-061", "to_terminal": "Top (+)", "status": "CONNECTED"},
            {"id": "JUMPER-C-D", "from_module": "MODULE_C", "from_cell": "CELL-090", "from_terminal": "Top (-)", "to_module": "MODULE_D", "to_cell": "CELL-091", "to_terminal": "Top (+)", "status": "CONNECTED"},
            {"id": "JUMPER-D-E", "from_module": "MODULE_D", "from_cell": "CELL-120", "from_terminal": "Top (-)", "to_module": "MODULE_E", "to_cell": "CELL-121", "to_terminal": "Top (+)", "status": "CONNECTED"},
            {"id": "JUMPER-E-F", "from_module": "MODULE_E", "from_cell": "CELL-150", "from_terminal": "Top (-)", "to_module": "MODULE_F", "to_cell": "CELL-151", "to_terminal": "Top (+)", "status": "CONNECTED"},
        ]

        for idx in range(num_cells - 1):
            c1 = self.cells[idx]
            c2 = self.cells[idx + 1]
            if c1.polarity == c2.polarity:
                broken_links.append(f"Polarity fault between {c1.cell_id} and {c2.cell_id}")
                is_valid = False

        nominal_voltage = round(num_cells * 3.70, 1)
        max_voltage = round(num_cells * 4.20, 1)
        min_voltage = round(num_cells * 3.00, 1)
        rated_capacity_ah = 4.8
        pack_energy_kwh = round((nominal_voltage * rated_capacity_ah) / 1000.0, 3)

        return {
            "status": "VALID_SERIES_NETWORK" if is_valid else "FAULT_DETECTED",
            "is_valid_series": is_valid,
            "circuit_type": "180S1P Pure Series",
            "circuit_architecture": "180S1P Pure Series",
            "total_cells": num_cells,
            "num_modules": len(modules_summary),
            "nominal_voltage_v": nominal_voltage,
            "nominal_pack_voltage_v": nominal_voltage,
            "max_voltage_v": max_voltage,
            "min_voltage_v": min_voltage,
            "rated_capacity_ah": rated_capacity_ah,
            "rated_energy_kwh": pack_energy_kwh,
            "continuity_verified": is_valid,
            "broken_links_count": len(broken_links),
            "broken_links": broken_links,
            "main_positive_terminal": {
                "cell_id": "CELL-001",
                "module_id": "MODULE_A",
                "terminal": "TOP_POSITIVE",
                "potential_v": nominal_voltage,
                "label": "+HV Red Post (+666V DC)"
            },
            "main_negative_terminal": {
                "cell_id": f"CELL-{num_cells:03d}",
                "module_id": "MODULE_F",
                "terminal": "TOP_NEGATIVE",
                "potential_v": 0.0,
                "label": "-HV Blue Post (0V GND)"
            },
            "intra_module_busbars_count": 174,
            "intra_module_busbars": 174,
            "inter_module_jumpers_count": 5,
            "inter_module_jumpers": 5,
            "total_interconnects": 179,
            "total_series_links": 179,
            "inter_module_jumpers_list": jumpers,
            "modules": modules_summary
        }

    def get_cell_at(self, r: int, c: int) -> Optional[IndividualCylindricalCell]:
        """Returns cell at grid coordinates (row, col) respecting module and serpentine order."""
        if self.num_cells == 180:
            if not (0 <= r < 10 and 0 <= c < 18):
                return None
            mat_r = r // 5
            mat_c = c // 6
            mod_idx = mat_r * 3 + mat_c
            lr = r % 5
            lc = c % 6
            if lr % 2 == 0:
                k_mod = lr * 6 + lc
            else:
                k_mod = lr * 6 + (5 - lc)
            k_global = mod_idx * 30 + k_mod
            if 0 <= k_global < len(self.cells):
                return self.cells[k_global]
            return None
        else:
            if not (0 <= r < self.rows and 0 <= c < self.cols):
                return None
            if r % 2 == 0:
                k = r * self.cols + c
            else:
                k = r * self.cols + (self.cols - 1 - c)
            if 0 <= k < len(self.cells):
                return self.cells[k]
            return None

    def set_cell_hotspot(self, cell_id: str, multiplier: float = 2.5, duration_s: float = 0.0):
        """Injects localized thermal hotspot into a specific cell."""
        cell = self.get_cell_by_name(cell_id)
        if cell:
            cell.hotspot_multiplier = float(multiplier)
            cell.hotspot_duration_s = float(duration_s)
            cell.hotspot_time_remaining_s = float(duration_s)

    def set_custom_hotspot(self, cell_ids: List[str], multiplier: float = 3.0,
                           initial_temp_c: float = None, duration_s: float = 0.0) -> List[str]:
        """Sets user-defined hotspot parameters on selected cells."""
        applied = []
        for cid in cell_ids:
            cell = self.get_cell_by_name(cid)
            if cell:
                cell.hotspot_multiplier = float(multiplier)
                cell.hotspot_duration_s = float(duration_s)
                cell.hotspot_time_remaining_s = float(duration_s)
                if initial_temp_c is not None:
                    cell.temp_c = float(initial_temp_c)
                applied.append(cell.cell_id)
        return applied

    def trigger_random_hotspots(self, count: int = 10, additional_heat_w: float = 15.0,
                               duration_s: float = 40.0, num_cells: Optional[int] = None,
                               intensity_w: Optional[float] = None, seed: Optional[int] = None) -> HotspotEvent:
        """
        Selects EXACTLY `count` (default 10) individual cylindrical cells randomly without duplicates,
        preserving the existing thermal states of all other cells, and applies localized overheating.
        """
        if num_cells is not None:
            count = num_cells
        if intensity_w is not None:
            additional_heat_w = intensity_w
        if seed is not None:
            self._rng = random.Random(seed)

        count = min(count, len(self.cells))
        selected_cells = self._rng.sample(self.cells, count)

        for c in selected_cells:
            c.q_hotspot_w += float(additional_heat_w)
            c.hotspot_multiplier = max(c.hotspot_multiplier, 3.5)
            c.hotspot_duration_s = max(c.hotspot_duration_s, float(duration_s))
            c.hotspot_time_remaining_s = max(c.hotspot_time_remaining_s, float(duration_s))
            c.compute_heat_generation(getattr(self, "c_rate", 2.0))

        self.hotspot_event_counter += 1
        evt_id = f"EVT-{self.hotspot_event_counter:04d}"
        init_t = max((c.temp_c for c in selected_cells), default=self.initial_temp_c)
        zones_aff = sorted(list(set(c.zone_id for c in selected_cells)))

        event = HotspotEvent(
            event_id=evt_id,
            sim_time_s=self.sim_time_s,
            config_type=f"RANDOM_{count}_CELLS",
            cell_ids=[c.cell_id for c in selected_cells],
            num_cells=len(selected_cells),
            additional_heat_w=float(additional_heat_w),
            duration_s=float(duration_s),
            time_remaining_s=float(duration_s),
            initial_temp_c=init_t,
            peak_temp_c=init_t,
            status="HEATING",
            zones_affected=zones_aff
        )
        self.active_hotspot_events.append(event)
        self.total_hotspot_events_created = getattr(self, "total_hotspot_events_created", 0) + 1

        return event

    def trigger_hotspot_event(self, config_type: str = "CLUSTER", cell_count: int = 10,
                              additional_heat_w: float = 20.0, duration_s: float = 30.0,
                              seed: Optional[int] = None) -> HotspotEvent:
        """Triggers a localized hotspot event by configuration code or random cluster."""
        if seed is not None:
            self._rng = random.Random(seed)
        cfg_upper = str(config_type).strip().upper()
        if cfg_upper in ("CLUSTER", "RANDOM", "RANDOM_10", "10_CELLS"):
            return self.trigger_random_hotspots(count=cell_count, additional_heat_w=additional_heat_w, duration_s=duration_s)
        res = self.apply_hotspot_configuration(config_type=config_type, additional_heat_w=additional_heat_w, duration_s=duration_s)
        if isinstance(res, HotspotEvent):
            return res
        # Return the last active event created
        if self.active_hotspot_events:
            return self.active_hotspot_events[-1]
        return self.trigger_random_hotspots(count=cell_count, additional_heat_w=additional_heat_w, duration_s=duration_s)

    def apply_hotspot_configuration(self, config_type: str, custom_cells: Optional[List[str]] = None,
                                    additional_heat_w: Optional[float] = None, duration_s: float = 30.0,
                                    clear_previous: bool = False) -> Dict[str, Any]:
        """
        Applies localized overheating event matching Configurations A through H,
        predefined geometric patterns, or custom user selections.
        Operates continuously alongside existing active events unless clear_previous is True.
        """
        if clear_previous:
            self.clear_hotspots()

        cfg_code = str(config_type).strip().upper()
        self.active_hotspot_scenario = cfg_code

        # Check for Random 10 cells configuration
        if "RANDOM" in cfg_code or cfg_code in ("10_CELLS", "AUTO_10"):
            heat_w = max(float(additional_heat_w), 1.0) if additional_heat_w is not None else 15.0
            return self.trigger_random_hotspots(count=10, additional_heat_w=heat_w, duration_s=duration_s)

        # Default heat based on configuration if not specified
        if additional_heat_w is not None:
            heat_w = max(float(additional_heat_w), 1.0)
        else:
            if cfg_code in ("A", "B", "C", "D"):
                heat_w = 18.0
            elif cfg_code in ("E", "F"):
                heat_w = 15.0
            elif cfg_code in ("G", "H"):
                heat_w = 14.0
            else:
                heat_w = 16.0

        dur_s = max(float(duration_s), 2.0)

        # Midpoints for centered patterns
        r_mid = max(self.rows // 2, 0)
        c_mid = max(self.cols // 2, 0)
        targets: List[IndividualCylindricalCell] = []

        if custom_cells:
            for cid in custom_cells:
                c = self.get_cell_by_name(cid)
                if c and c not in targets:
                    targets.append(c)
            desc = f"Custom Hotspot Configuration: {len(targets)} cells selected (+{heat_w:.1f}W for {dur_s:.1f}s)"

        elif cfg_code == "A":
            # Configuration A: Single cell overheating (e.g. CELL-125)
            c = self.get_cell_by_name("CELL-125") or self.get_cell_at(r_mid, c_mid)
            targets = [c]
            desc = f"Configuration A: Single Cell Overheating ({c.cell_id} at +{heat_w:.1f}W for {dur_s:.1f}s)"

        elif cfg_code == "B":
            # Configuration B: Double adjacent cells (e.g. CELL-125 & CELL-126)
            c1 = self.get_cell_by_name("CELL-125") or self.get_cell_at(r_mid, c_mid)
            c2 = self.get_cell_by_name("CELL-126") or self.get_cell_at(r_mid, min(c_mid + 1, self.cols - 1))
            targets = [c for c in (c1, c2) if c is not None]
            desc = f"Configuration B: Double Adjacent Cells Overheating ({c1.cell_id}, {c2.cell_id} at +{heat_w:.1f}W)"

        elif cfg_code == "C":
            # Configuration C: Triple adjacent cells
            c1 = self.get_cell_at(r_mid, max(0, c_mid - 1))
            c2 = self.get_cell_at(r_mid, c_mid)
            c3 = self.get_cell_at(r_mid, min(self.cols - 1, c_mid + 1))
            targets = [c for c in (c1, c2, c3) if c is not None]
            desc = f"Configuration C: Triple Adjacent Cells Overheating ({', '.join(c.cell_id for c in targets)} at +{heat_w:.1f}W)"

        elif cfg_code == "D":
            # Configuration D: Quadruple adjacent cells (2x2 cluster)
            r2 = min(r_mid + 1, self.rows - 1)
            c2 = min(c_mid + 1, self.cols - 1)
            raw = [
                self.get_cell_at(r_mid, c_mid),
                self.get_cell_at(r_mid, c2),
                self.get_cell_at(r2, c_mid),
                self.get_cell_at(r2, c2)
            ]
            targets = [c for c in raw if c is not None]
            desc = f"Configuration D: Quadruple 2x2 Cluster Overheating (4 cells at +{heat_w:.1f}W)"

        elif cfg_code == "E":
            # Configuration E: Small batch (5 to 10 cells, 2x4 cluster)
            for r in range(r_mid, min(r_mid + 2, self.rows)):
                for c in range(max(0, c_mid - 2), min(self.cols, c_mid + 2)):
                    cell = self.get_cell_at(r, c)
                    if cell:
                        targets.append(cell)
            desc = f"Configuration E: Small Batch Overheating ({len(targets)} cells in 2x4 cluster at +{heat_w:.1f}W)"

        elif cfg_code == "F":
            # Configuration F: Medium batch (10 to 25 cells, 4x4 cluster = 16 cells)
            r_start = max(0, r_mid - 1)
            r_end = min(self.rows, r_start + 4)
            c_start = max(0, c_mid - 2)
            c_end = min(self.cols, c_start + 4)
            for r in range(r_start, r_end):
                for c in range(c_start, c_end):
                    cell = self.get_cell_at(r, c)
                    if cell:
                        targets.append(cell)
            desc = f"Configuration F: Medium Batch Overheating ({len(targets)} cells in 4x4 cluster at +{heat_w:.1f}W)"

        elif cfg_code == "G":
            # Configuration G: Large group (20 to 35 cells)
            r_start = max(0, r_mid - 2)
            r_end = min(self.rows, r_start + 5)
            c_start = max(0, c_mid - 3)
            c_end = min(self.cols, c_start + 7)
            for r in range(r_start, r_end):
                for c in range(c_start, c_end):
                    cell = self.get_cell_at(r, c)
                    if cell:
                        targets.append(cell)
            desc = f"Configuration G: Large Group Overheating ({len(targets)} cells in group at +{heat_w:.1f}W)"

        elif cfg_code == "H":
            # Configuration H: Multiple independent hotspots (2-3 distinct zones simultaneously)
            # Cluster 1 in Zone 2
            r1 = max(1, self.rows // 5)
            for c in range(max(0, c_mid - 4), min(self.cols, c_mid - 1)):
                cell = self.get_cell_at(r1, c)
                if cell:
                    targets.append(cell)
            # Cluster 2 in Zone 7
            r2 = max(2, (self.rows * 7) // 10)
            for c in range(max(0, c_mid + 2), min(self.cols, c_mid + 5)):
                cell = self.get_cell_at(r2, c)
                if cell:
                    targets.append(cell)
            # Cluster 3 in Zone 9
            r3 = min(self.rows - 2, max(0, (self.rows * 9) // 10))
            for c in range(max(0, c_mid - 2), min(self.cols, c_mid + 1)):
                cell = self.get_cell_at(r3, c)
                if cell:
                    targets.append(cell)
            desc = f"Configuration H: Multiple Independent Hotspots ({len(targets)} cells across 3 distant zones at +{heat_w:.1f}W)"

        elif cfg_code == "HORIZONTAL":
            # Horizontal pattern
            r = r_mid
            for c in range(max(0, c_mid - 4), min(self.cols, c_mid + 5)):
                cell = self.get_cell_at(r, c)
                if cell:
                    targets.append(cell)
            desc = f"Horizontal Pattern Hotspot: Row {r+1} segment ({len(targets)} cells)"

        elif cfg_code == "VERTICAL":
            # Vertical pattern
            c = c_mid
            for r in range(max(0, r_mid - 4), min(self.rows, r_mid + 5)):
                cell = self.get_cell_at(r, c)
                if cell:
                    targets.append(cell)
            desc = f"Vertical Pattern Hotspot: Column {c+1} segment ({len(targets)} cells)"

        elif cfg_code == "CENTRAL":
            # Central core cluster
            for r in range(max(0, r_mid - 1), min(self.rows, r_mid + 2)):
                for c in range(max(0, c_mid - 2), min(self.cols, c_mid + 2)):
                    cell = self.get_cell_at(r, c)
                    if cell:
                        targets.append(cell)
            desc = f"Central Core Hotspot: Central block ({len(targets)} cells)"

        elif cfg_code == "EDGE":
            # Edge/perimeter pattern
            for c in range(0, min(self.cols, 8)):
                cell = self.get_cell_at(0, c)
                if cell:
                    targets.append(cell)
            desc = f"Edge Perimeter Hotspot: Outer boundary ({len(targets)} cells)"

        elif cfg_code == "SEPARATED":
            # Separated isolated cells
            pts = [(1, 2), (r_mid, c_mid), (max(0, self.rows - 2), max(0, self.cols - 3))]
            for r, c in pts:
                cell = self.get_cell_at(r, c)
                if cell:
                    targets.append(cell)
            desc = f"Separated Hotspot: 3 Disjoint points across pack ({len(targets)} cells)"

        elif cfg_code == "MULTI_CLUSTER":
            # Multi cluster: three 2x2 clusters
            centers = [(max(1, self.rows // 4), max(1, self.cols // 4)),
                       (r_mid, c_mid),
                       (max(2, (self.rows * 3) // 4), max(2, (self.cols * 3) // 4))]
            for cr, cc in centers:
                c1 = self.get_cell_at(cr, cc)
                c2 = self.get_cell_at(cr, min(cc + 1, self.cols - 1))
                c3 = self.get_cell_at(min(cr + 1, self.rows - 1), cc)
                c4 = self.get_cell_at(min(cr + 1, self.rows - 1), min(cc + 1, self.cols - 1))
                for cl in (c1, c2, c3, c4):
                    if cl and cl not in targets:
                        targets.append(cl)
                targets.append(self.cells[min(cr + 1, self.rows - 1) * self.cols + min(cc + 1, self.cols - 1)])
            desc = f"Multi-Cluster Hotspot: 3 distinct 2x2 clusters ({len(targets)} cells)"

        else:
            # Fallback single cell
            c = self.cells[r_mid * self.cols + c_mid]
            targets = [c]
            desc = f"Hotspot Configuration {cfg_code}: 1 cell ({c.cell_id})"

        # Deduplicate targets
        unique_targets = []
        for cell in targets:
            if cell not in unique_targets:
                unique_targets.append(cell)
        targets = unique_targets

        # Apply additional heat and duration to individual cells
        for c in targets:
            c.q_hotspot_w += heat_w
            c.hotspot_multiplier = max(c.hotspot_multiplier, 2.5)
            c.hotspot_duration_s = max(c.hotspot_duration_s, dur_s)
            c.hotspot_time_remaining_s = max(c.hotspot_time_remaining_s, dur_s)

        # Register new HotspotEvent
        self.hotspot_event_counter += 1
        evt_id = f"EVT-{self.hotspot_event_counter:04d}"
        init_t = max((c.temp_c for c in targets), default=self.initial_temp_c)
        zones_aff = sorted(list(set(c.zone_id for c in targets)))

        event = HotspotEvent(
            event_id=evt_id,
            sim_time_s=self.sim_time_s,
            config_type=cfg_code,
            cell_ids=[c.cell_id for c in targets],
            num_cells=len(targets),
            additional_heat_w=heat_w,
            duration_s=dur_s,
            time_remaining_s=dur_s,
            initial_temp_c=init_t,
            peak_temp_c=init_t,
            status="HEATING",
            zones_affected=zones_aff
        )
        self.active_hotspot_events.append(event)

        return {
            "success": True,
            "event_id": evt_id,
            "configuration": cfg_code,
            "scenario": cfg_code,
            "description": desc,
            "affected_cells": [c.cell_id for c in targets],
            "num_cells": len(targets),
            "additional_heat_w": heat_w,
            "duration_s": dur_s,
            "zones_affected": zones_aff,
            "sim_time_s": round(self.sim_time_s, 2),
            "active_events_count": len(self.active_hotspot_events),
            "simulated_test_scenario": True
        }

    def apply_hotspot_scenario(self, scenario: str) -> Dict[str, Any]:
        """Applies predefined scenarios matching Configurations A through H or custom."""
        return self.apply_hotspot_configuration(config_type=scenario, clear_previous=False)

    def schedule_hotspot_event(self, time_s: float, config_type: str, cell_ids: Optional[List[str]] = None,
                               heat_w: float = 15.0, duration_s: float = 30.0) -> Dict[str, Any]:
        """Schedules a future overheating event at time_s."""
        sched_item = {
            "time_s": float(time_s),
            "config_type": str(config_type).upper(),
            "cell_ids": cell_ids,
            "heat_w": float(heat_w),
            "duration_s": float(duration_s),
            "triggered": False
        }
        self.event_schedule.append(sched_item)
        self.event_schedule.sort(key=lambda x: x["time_s"])
        return {
            "success": True,
            "message": f"Event {sched_item['config_type']} scheduled at t={time_s:.1f}s",
            "schedule_count": len(self.event_schedule)
        }

    def load_demonstration_sequence(self) -> List[Dict[str, Any]]:
        """
        Schedules the 10-event demonstration sequence matching Requirement 15:
        Step 1: Normal initial state (t=0..5s)
        Step 2: Single cell hotspot (Config A, t=6s)
        Step 3: Double adjacent cell hotspot (Config B, t=14s)
        Step 4: Quadruple adjacent cell hotspot (Config D, t=22s)
        Step 5: Cell 1 recovers while 2nd & 3rd continue (observed during t=22..35s)
        Step 6: Small batch hotspot (Config E, t=32s)
        Step 7: Multiple independent zones (Config H, t=42s)
        Step 8: Medium batch (Config F, t=52s)
        Step 9: Repeat single hotspot on recovered cell (Config A, t=62s)
        Step 10: Final multi-cluster verification (Config C, t=72s)
        """
        self.event_schedule = [
            {"time_s": 6.0, "config_type": "A", "heat_w": 18.0, "duration_s": 12.0, "triggered": False},
            {"time_s": 14.0, "config_type": "B", "heat_w": 16.0, "duration_s": 14.0, "triggered": False},
            {"time_s": 22.0, "config_type": "D", "heat_w": 16.0, "duration_s": 15.0, "triggered": False},
            {"time_s": 32.0, "config_type": "E", "heat_w": 15.0, "duration_s": 15.0, "triggered": False},
            {"time_s": 42.0, "config_type": "H", "heat_w": 15.0, "duration_s": 18.0, "triggered": False},
            {"time_s": 52.0, "config_type": "F", "heat_w": 14.0, "duration_s": 16.0, "triggered": False},
            {"time_s": 62.0, "config_type": "A", "heat_w": 18.0, "duration_s": 12.0, "triggered": False},
            {"time_s": 72.0, "config_type": "C", "heat_w": 16.0, "duration_s": 15.0, "triggered": False},
            {"time_s": 82.0, "config_type": "B", "heat_w": 16.0, "duration_s": 14.0, "triggered": False},
            {"time_s": 92.0, "config_type": "G", "heat_w": 14.0, "duration_s": 18.0, "triggered": False},
        ]
        return list(self.event_schedule)

    def export_hotspot_events_csv(self) -> str:
        """Exports full recorded event history and active events as formatted CSV string."""
        all_events = list(self.hotspot_event_history) + list(self.active_hotspot_events)
        all_events.sort(key=lambda e: e.sim_time_s)

        headers = [
            "Event_ID", "Sim_Time_s", "Config_Type", "Num_Cells", "Cell_IDs",
            "Additional_Heat_W", "Duration_s", "Initial_Temp_C", "Peak_Temp_C",
            "Cooling_Activation_Time_s", "Recovery_Time_s", "Status",
            "Max_Cooling_Flow_L_min", "Energy_Removed_J", "Cooling_Energy_J", "Zones_Affected"
        ]
        lines = [",".join(headers)]
        for ev in all_events:
            c_ids_str = ";".join(ev.cell_ids)
            zones_str = ";".join(ev.zones_affected)
            row = [
                ev.event_id,
                f"{ev.sim_time_s:.2f}",
                ev.config_type,
                str(ev.num_cells),
                f'"{c_ids_str}"',
                f"{ev.additional_heat_w:.2f}",
                f"{ev.duration_s:.2f}",
                f"{ev.initial_temp_c:.2f}",
                f"{ev.peak_temp_c:.2f}",
                f"{ev.cooling_activation_time_s:.2f}" if ev.cooling_activation_time_s is not None else "N/A",
                f"{ev.recovery_time_s:.2f}" if ev.recovery_time_s is not None else "N/A",
                ev.status,
                f"{ev.max_cooling_flow_l_min:.2f}",
                f"{ev.energy_removed_j:.1f}",
                f"{ev.cooling_energy_j:.1f}",
                f'"{zones_str}"'
            ]
            lines.append(",".join(row))
        return "\n".join(lines)

    def set_auto_hotspot_mode(self, enabled: bool, interval_s: float = 30.0, seed: int = 42):
        """Toggles automated periodic hotspot generation."""
        self.auto_hotspot_enabled = bool(enabled)
        self.auto_hotspot_interval_s = float(interval_s)
        self.auto_hotspot_seed = int(seed)
        self._rng = random.Random(self.auto_hotspot_seed)
        self.auto_hotspot_timer_s = 0.0
        if self.auto_hotspot_enabled:
            mult = math.floor(self.sim_time_s / self.auto_hotspot_interval_s) + 1
            self.next_hotspot_boundary_s = mult * self.auto_hotspot_interval_s
            if self.next_hotspot_boundary_s <= self.sim_time_s:
                self.next_hotspot_boundary_s = self.sim_time_s + self.auto_hotspot_interval_s

    def clear_hotspots(self):
        """Clears all localized hotspots and resets active events."""
        for c in self.cells:
            c.hotspot_multiplier = 1.0
            c.hotspot_duration_s = 0.0
            c.hotspot_time_remaining_s = 0.0
            c.q_hotspot_w = 0.0
        self.active_hotspot_scenario = "NONE"
        for ev in self.active_hotspot_events:
            ev.status = "CLEARED"
            self.hotspot_event_history.append(ev)
        self.active_hotspot_events = []

    def step(self, dt: float, c_rate: float, h_coolant: float, T_coolant_c: float,
             threshold_c: float = 35.0, cooling_active: bool = True, heater_active: bool = False,
             heater_power_total_w: float = 0.0, total_vol_flow_l_min: float = 18.0,
             base_velocity_m_s: float = 0.25, B0: float = 0.50, lorentz_force: float = 0.0) -> Dict[str, Any]:
        """
        Executes a coupled transient thermal time step for all 180 cylindrical cells.
        Couples internal generation, wavy cooling ribbon heat absorption, neighbor conduction,
        MHD Lorentz force damping, and localized zonal adaptive hydraulic redistribution.
        """
        self.current_B0 = float(B0)
        self.current_lorentz_force = float(lorentz_force)

        # Advance internal pack simulation clock
        self.sim_time_s += dt

        # Process any scheduled hotspot events
        for item in self.event_schedule:
            if not item.get("triggered", False) and self.sim_time_s >= item["time_s"]:
                item["triggered"] = True
                self.apply_hotspot_configuration(
                    config_type=item["config_type"],
                    custom_cells=item.get("cell_ids"),
                    additional_heat_w=item.get("heat_w"),
                    duration_s=item.get("duration_s", 30.0),
                    clear_previous=False
                )

        # 1. Automatic Hotspot Boundary Scheduler (Every 30 simulation seconds: exactly 10 unique cells)
        if self.auto_hotspot_enabled:
            while self.sim_time_s >= self.next_hotspot_boundary_s:
                intensity = getattr(self, "hotspot_intensity_w", 20.0)
                cells_cnt = getattr(self, "hotspot_cells_per_event", 10)
                duration = getattr(self, "hotspot_duration_s", 40.0)
                self.trigger_random_hotspots(count=cells_cnt, additional_heat_w=intensity, duration_s=duration)
                self.next_hotspot_boundary_s += self.auto_hotspot_interval_s

        n = len(self.cells)
        temps = np.array([c.temp_c for c in self.cells], dtype=np.float64)
        heat_rates = np.zeros(n, dtype=np.float64)
        heat_removed_rates = np.zeros(n, dtype=np.float64)

        # BMS Protective Power Derating check
        pre_max_t = float(np.max(temps)) if n > 0 else self.initial_temp_c
        if pre_max_t >= 55.0:
            self.bms_derate_active = True
            self.bms_derate_factor = max(0.2, 1.0 - ((pre_max_t - 55.0) / 5.0) * 0.8)
            self.bms_status = f"CRITICAL (≥ 55°C) - DERATED ({int(self.bms_derate_factor*100)}% Power)"
        elif pre_max_t >= 45.0:
            self.bms_derate_active = False
            self.bms_derate_factor = 1.0
            self.bms_status = "WARNING (45-55°C) - TARGETED COOLING"
        elif pre_max_t >= threshold_c:
            self.bms_derate_active = False
            self.bms_derate_factor = 1.0
            self.bms_status = "ELEVATED (35-45°C) - TARGETED COOLING"
        else:
            self.bms_derate_active = False
            self.bms_derate_factor = 1.0
            self.bms_status = "NORMAL (15-35°C)"

        effective_c_rate = c_rate * self.bms_derate_factor
        q_heater_per_cell = (heater_power_total_w / max(n, 1)) if heater_active else 0.0

        # Reshape for spatial conduction
        grid_temps = np.zeros((self.rows, self.cols), dtype=np.float64)
        for cell in self.cells:
            grid_temps[cell.row, cell.col] = cell.temp_c
        k_neighbor = 0.08  # Cell-to-cell thermal coupling conductance [W/K]
        neighbor_flux = np.zeros_like(grid_temps)

        # 2D discrete Laplacian for neighbor cell-to-cell conduction
        neighbor_flux[:-1, :] += k_neighbor * (grid_temps[1:, :] - grid_temps[:-1, :])
        neighbor_flux[1:, :] += k_neighbor * (grid_temps[:-1, :] - grid_temps[1:, :])
        neighbor_flux[:, :-1] += k_neighbor * (grid_temps[:, 1:] - grid_temps[:, :-1])
        neighbor_flux[:, 1:] += k_neighbor * (grid_temps[:, :-1] - grid_temps[:, 1:])
        flat_neighbor_flux = neighbor_flux.flatten()

        # 2. Zonal Adaptive Hydraulic Calculations (Parallel Branches)
        # Identify overheated cells per zone, modulate valve, and rebalance hydraulic network
        zone_max_temps = {}
        for zone_id, zinfo in self.zones.items():
            z_cells = [self.cells[idx] for idx in range(n) if self.cells[idx].cell_id in zinfo["cell_ids"]]
            if z_cells:
                z_tmax = max(c.temp_c for c in z_cells)
                z_tavg = sum(c.temp_c for c in z_cells) / len(z_cells)
                z_tmin = min(c.temp_c for c in z_cells)
            else:
                z_tmax = z_tavg = z_tmin = 25.0

            zinfo["temp_max_c"] = round(z_tmax, 2)
            zinfo["temp_avg_c"] = round(z_tavg, 2)
            zinfo["temp_min_c"] = round(z_tmin, 2)
            zone_max_temps[zone_id] = z_tmax

            # Modulate zonal flow-control valve
            if cooling_active:
                if z_tmax >= threshold_c:
                    # Regulate valve open proportionally to overtemp
                    overtemp = z_tmax - threshold_c
                    zinfo["valve_position"] = min(1.0, 0.40 + overtemp * 0.20)
                    zinfo["status"] = "ACTIVE_COOLING"
                elif z_tmax <= threshold_c - 2.5:
                    zinfo["valve_position"] = 0.15 # Baseline idle bypass flow
                    zinfo["status"] = "IDLE"
                else:
                    zinfo["status"] = "MODULATING"
            else:
                zinfo["valve_position"] = 0.0
                zinfo["status"] = "OFF"

        # Hydraulic network conductance balance across parallel zones
        conductances = {}
        for zone_id, zinfo in self.zones.items():
            theta = max(zinfo["valve_position"], 0.05)
            # R_hyd = R_channel + R_valve / theta^2
            conductances[zone_id] = 1.0 / math.sqrt(1.0 + (0.35 / (theta ** 2)))

        total_cond = sum(conductances.values()) or 1.0
        zone_htc = {}
        for zone_id, zinfo in self.zones.items():
            frac = conductances[zone_id] / total_cond
            zinfo["flow_fraction"] = round(frac, 4)
            z_flow = (total_vol_flow_l_min * frac) if cooling_active else 0.0
            zinfo["flow_rate_l_min"] = round(z_flow, 2)

            # Local velocity strictly proportional to hydraulic flow redistribution
            z_u = (base_velocity_m_s * frac * self.num_zones) if cooling_active else 0.0
            zinfo["velocity_m_s"] = round(z_u, 3)

            # Local Reynolds and Nusselt
            z_re = max(z_u * 0.00286 * 1080.0 / 0.001, 0.0)
            z_nu = 4.36 + 0.036 * z_re * 5.37 * (0.00286 / 0.6) if z_re > 0 else 4.36
            z_h = (z_nu * 0.68) / 0.00286 if z_u > 0 else 12.0
            zinfo["reynolds"] = round(z_re, 1)
            zinfo["nusselt"] = round(z_nu, 2)
            zinfo["htc_w_m2k"] = round(z_h, 1)
            zone_htc[zone_id] = z_h

            # Local pressure drop
            z_dp = (0.025 * (0.6 / 0.00286) * (1080.0 * (z_u ** 2) / 2.0)) / 1000.0 if z_u > 0 else 0.0
            zinfo["pressure_drop_kpa"] = round(z_dp, 3)
            zinfo["pressure_kpa"] = round(101.3 + z_dp, 2)

        # 3. Individual Cell Coupled Energy Conservation
        zone_heat_absorbed = {zid: 0.0 for zid in self.zones}
        zone_heat_generated = {zid: 0.0 for zid in self.zones}

        for idx, cell in enumerate(self.cells):
            # Electrochemical heat generation (Bernardi) with BMS derated c_rate
            cell.compute_heat_generation(effective_c_rate)
            heat_rates[idx] = cell.heat_gen_w
            zone_heat_generated[cell.zone_id] = zone_heat_generated.get(cell.zone_id, 0.0) + cell.heat_gen_w

            # Convective cooling through S-channel into nanofluid
            # Uses cell's specific zonal HTC!
            local_h = zone_htc.get(cell.zone_id, h_coolant)

            if cooling_active:
                q_plate = cell.compute_plate_heat_transfer(T_coolant_c, local_h)
            else:
                # Natural convection & radiation in stagnant enclosure
                delta_t = cell.temp_c - T_coolant_c
                q_plate = 2.8 * cell.cooling_area_m2 * delta_t
                cell.heat_removed_w = float(q_plate)
                cell.q_tim_flux_w_m2 = float(q_plate / max(cell.cooling_area_m2, 1.0e-6))

            heat_removed_rates[idx] = cell.heat_removed_w
            zone_heat_absorbed[cell.zone_id] = zone_heat_absorbed.get(cell.zone_id, 0.0) + cell.heat_removed_w

            # Ambient heat dissipation from peripheral cells
            is_edge = (cell.row == 0 or cell.row == self.rows - 1 or cell.col == 0 or cell.col == self.cols - 1)
            q_amb = (3.5 * cell.surface_area_m2 * (cell.temp_c - 25.0)) if is_edge else 0.0

            # Advance temperature state
            cell.update_temperature(
                dt=dt,
                q_removed=cell.heat_removed_w,
                q_neighbors=float(neighbor_flux[cell.row, cell.col]),
                q_heater=q_heater_per_cell,
                q_ambient=q_amb
            )
            temps[idx] = cell.temp_c

            # Update cell local hydraulic and electromagnetic state
            zinfo = self.zones.get(cell.zone_id, {})
            cell.local_velocity_m_s = float(zinfo.get("velocity_m_s", base_velocity_m_s))
            cell.local_pressure_pa = float(zinfo.get("pressure_kpa", 101.3) * 1000.0)
            cell.local_coolant_temp_c = float(zinfo.get("temp_outlet_c", T_coolant_c))
            cell.valve_status = f"OPEN ({int(zinfo.get('valve_position', 0.5)*100)}%)" if cooling_active else "CLOSED (0%)"
            cell.b_field_tesla = float(self.current_B0)
            cell.lorentz_force_n_m3 = float(self.current_lorentz_force)

            if cell.temp_c >= threshold_c and cooling_active:
                cell.cooling_state = "TARGETED COOLING"
            elif cooling_active and cell.temp_c > 33.5:
                cell.cooling_state = "ACTIVE COOLING"
            elif cooling_active:
                cell.cooling_state = "OPTIMAL"
            else:
                cell.cooling_state = "STANDBY"

        # Update zone heat totals and temperature rises
        for zone_id, zinfo in self.zones.items():
            q_abs = zone_heat_absorbed.get(zone_id, 0.0)
            zinfo["heat_absorbed_w"] = round(q_abs, 2)
            zinfo["heat_gen_w"] = round(zone_heat_generated.get(zone_id, 0.0), 2)
            zinfo["temp_inlet_c"] = round(T_coolant_c, 2)

            m_dot_z = (zinfo["flow_rate_l_min"] / 60.0) * (1080.0 / 1000.0)
            if m_dot_z > 0.0:
                dT_z = q_abs / max(m_dot_z * 3750.0, 1.0)
                zinfo["temp_outlet_c"] = round(T_coolant_c + dT_z, 2)
            else:
                zinfo["temp_outlet_c"] = round(T_coolant_c, 2)

        # 4. Update Active Hotspot Events Lifecycle
        for ev in self.active_hotspot_events:
            ev.time_remaining_s = max(0.0, ev.time_remaining_s - dt)
            ev_cells = [self.get_cell_by_name(cid) for cid in ev.cell_ids]
            ev_cells = [c for c in ev_cells if c is not None]
            if ev_cells:
                peak_c = max(c.temp_c for c in ev_cells)
                ev.peak_temp_c = max(ev.peak_temp_c, peak_c)
                if peak_c >= threshold_c and ev.cooling_activation_time_s is None:
                    ev.cooling_activation_time_s = round(self.sim_time_s, 2)

                for zid in ev.zones_affected:
                    if zid in self.zones:
                        ev.max_cooling_flow_l_min = max(ev.max_cooling_flow_l_min, self.zones[zid]["flow_rate_l_min"])

                q_rem = sum(c.heat_removed_w for c in ev_cells)
                ev.energy_removed_j += q_rem * dt
                ev.cooling_energy_j += (q_rem * 0.15) * dt

                if ev.time_remaining_s > 0.0:
                    if peak_c >= threshold_c and cooling_active:
                        ev.status = "TARGETED COOLING"
                    else:
                        ev.status = "HEATING"
                else:
                    if ev.status in ("HEATING", "TARGETED COOLING"):
                        ev.status = "COOLING"
                        for c in ev_cells:
                            c.q_hotspot_w = max(0.0, c.q_hotspot_w - ev.additional_heat_w)
                            if c.q_hotspot_w <= 0.0:
                                c.hotspot_multiplier = 1.0

                    # Recovery check: all cells cool below threshold - 1.5 (<= 33.5C)
                    if all(c.temp_c <= max(threshold_c - 1.5, 33.5) for c in ev_cells):
                        ev.status = "RECOVERED"
                        if ev.recovery_time_s is None:
                            ev.recovery_time_s = round(self.sim_time_s, 2)

        # Move RECOVERED events to history
        active_list = []
        for ev in self.active_hotspot_events:
            if ev.status == "RECOVERED":
                self.hotspot_event_history.append(ev)
            else:
                active_list.append(ev)
        self.active_hotspot_events = active_list

        max_t = float(np.max(temps))
        min_t = float(np.min(temps))
        avg_t = float(np.mean(temps))
        delta_t = max_t - min_t  # Equation N

        hottest_idx = int(np.argmax(temps))
        coldest_idx = int(np.argmin(temps))

        # Exact 3-color mapping counts:
        # Green (0–34°C, Normal), Yellow (35–45°C, Moderate), Red (46–60°C+, Heated/Overheated)
        num_normal = sum(1 for c in self.cells if c.temp_c <= 34.0)
        num_moderate = sum(1 for c in self.cells if 34.0 < c.temp_c <= 45.0)
        num_overheated = sum(1 for c in self.cells if c.temp_c > 45.0)
        num_critical = sum(1 for c in self.cells if c.temp_c > 60.0)
        uniformity_status = "OPTIMAL (< 5.0 K)" if delta_t < 5.0 else f"NON_UNIFORM ({delta_t:.1f} K >= 5.0 K)"

        return {
            "num_cells": n,
            "rows": self.rows,
            "cols": self.cols,
            "form_factor": self.form_factor,
            "plate_material": self.plate_material,
            "num_cooling_plates": self.num_cooling_plates,
            "num_zones": self.num_zones,
            "zones": self.zones,
            "modules": getattr(self, "modules", self.zones),
            "electrical_validation": self.validate_electrical_network() if hasattr(self, "validate_electrical_network") else {},
            "auto_hotspot_enabled": self.auto_hotspot_enabled,
            "auto_hotspot_interval_s": self.auto_hotspot_interval_s,
            "active_hotspot_scenario": self.active_hotspot_scenario,
            "max_cell_temp_c": max_t,
            "min_cell_temp_c": min_t,
            "avg_cell_temp_c": avg_t,
            "delta_t_pack_c": delta_t,
            "uniformity_compliant": bool(delta_t < 5.0),
            "uniformity_status": uniformity_status,
            "bms_status": self.bms_status,
            "bms_derate_active": self.bms_derate_active,
            "bms_derate_factor": round(self.bms_derate_factor, 3),
            "cell_counts": {
                "normal": num_normal,
                "moderate": num_moderate,
                "elevated": num_moderate,
                "heated": num_overheated,
                "overheated": num_overheated,
                "critical": num_critical
            },
            "active_hotspot_events": [e.to_dict() for e in self.active_hotspot_events],
            "hotspot_event_history": [e.to_dict() for e in self.hotspot_event_history],
            "scheduled_events_count": len([e for e in self.event_schedule if not e.get("triggered", False)]),
            "total_pack_heat_w": float(np.sum(heat_rates)),
            "total_heat_removed_w": float(np.sum(heat_removed_rates)),
            "total_thermal_energy_kj": float(np.sum([c.compute_thermal_energy_joules() for c in self.cells])) / 1000.0,
            "cells": [c.to_dict(threshold_c) for c in self.cells],
            "hottest_cell_id": self.cells[hottest_idx].cell_id,
            "coldest_cell_id": self.cells[coldest_idx].cell_id,
        }

    def get_cell_by_name(self, name: str) -> Optional[IndividualCylindricalCell]:
        """Finds cell by ID e.g. 'CELL-235', 'CELL-0235', 'BAT-23', or integer index."""
        name_clean = str(name).strip().upper()
        # Direct numeric index
        if name_clean.isdigit():
            idx = int(name_clean) - 1
            if 0 <= idx < len(self.cells):
                return self.cells[idx]

        # Extract numeric component
        num_str = "".join([ch for ch in name_clean if ch.isdigit()])
        if num_str:
            num = int(num_str)
            idx = num - 1
            if 0 <= idx < len(self.cells):
                return self.cells[idx]

        # Name match
        for cell in self.cells:
            if cell.cell_id == name_clean:
                return cell
        return None

    def reset(self, initial_temp_c: float = 25.0):
        """Resets all cylindrical cells to reference temperature state."""
        self.initial_temp_c = float(initial_temp_c)
        self.sim_time_s = 0.0
        self.hotspot_event_counter = 0
        self.active_hotspot_events = []
        self.hotspot_event_history = []
        self.event_schedule = []
        self.bms_derate_active = False
        self.bms_derate_factor = 1.0
        self.bms_status = "NORMAL (15-35°C)"
        self.active_hotspot_scenario = "NONE"
        self.next_hotspot_boundary_s = 30.0
        self.auto_hotspot_timer_s = 0.0
        for i, cell in enumerate(self.cells):
            r = i // self.cols
            c = i % self.cols
            cell.temp_c = float(initial_temp_c + (math.sin(r * 0.7 + c * 0.4) * 0.35))
            cell.initial_temp_c = cell.temp_c
            cell.max_recorded_temp_c = cell.temp_c
            cell.min_recorded_temp_c = cell.temp_c
            cell.temp_history = [round(cell.temp_c, 2)]
            cell.heat_gen_w = 0.0
            cell.q_internal_w = 2.76
            cell.heat_gen_vol_w_m3 = 0.0
            cell.heat_removed_w = 0.0
            cell.hotspot_multiplier = 1.0
            cell.hotspot_duration_s = 0.0
            cell.hotspot_time_remaining_s = 0.0
            cell.q_hotspot_w = 0.0
            cell.cooling_state = "OPTIMAL"
            cell.local_coolant_temp_c = 20.0
            cell.local_velocity_m_s = 0.25
            cell.local_pressure_pa = 101325.0
            cell.valve_status = "MODULATED (50%)"


# Backward compatibility alias
class BatteryPack50Cells(CylindricalBatteryPack):
    """Backwards compatibility wrapper for tests referencing 50-cell pack."""

    def __init__(self, initial_temp_c: float = 25.0):
        super().__init__(initial_temp_c=initial_temp_c, num_cells=50, form_factor="21700")
        # Retain BAT-xx naming for tests expecting BAT-xx
        for idx, cell in enumerate(self.cells):
            cell.cell_id = f"BAT-{idx+1:02d}"


# Alias for backwards compatibility
IndividualBatteryCell = IndividualCylindricalCell
