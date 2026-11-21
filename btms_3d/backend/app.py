"""
BTMS Flask REST API & Web Application Server
Exposes simulation engine endpoints, real-time 50-cell telemetry, 24 equations inspector,
ML surrogate inference, dataset processing, and serves the interactive Three.js 3D WebGL frontend.
"""

import os
import io
import json
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, Response

from btms_3d.backend.numerical_solver.simulation_engine import RealTimeBTMSEngine
from btms_3d.backend.formula_engine.equation_library import GoverningEquationEngine
from btms_3d.backend.properties.material_database import get_component_properties, COMPONENTS_DATABASE
from btms_3d.backend.dataset_processor.dataset_handler import DatasetProcessor
from btms_3d.backend.ml_prediction.ml_surrogate import MLSurrogatePredictor

# Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR)

# Global Simulation & ML Instances
sim_engine = RealTimeBTMSEngine(initial_temp_c=25.0)
ml_predictor = MLSurrogatePredictor()

def format_telemetry_payload(telemetry):
    """Enriches telemetry dictionary with top-level convenience aliases."""
    if not isinstance(telemetry, dict):
        return telemetry
    res = dict(telemetry)
    if "battery_pack" in res and isinstance(res["battery_pack"], dict):
        bp = res["battery_pack"]
        res["num_cells"] = bp.get("num_cells", len(bp.get("cells", [])))
        res["pack_max_temp_c"] = bp.get("max_cell_temp_c", 25.0)
        res["pack_avg_temp_c"] = bp.get("avg_cell_temp_c", 25.0)
        res["pack_min_temp_c"] = bp.get("min_cell_temp_c", 25.0)
        res["pack_total_heat_w"] = bp.get("total_pack_heat_w", 0.0)
        res["delta_t_pack_c"] = bp.get("delta_t_pack_c", 0.0)
        res["active_hotspot_events"] = bp.get("active_hotspot_events", [])
        res["hotspot_event_history"] = bp.get("hotspot_event_history", [])
        res["cell_counts"] = bp.get("cell_counts", {})
        res["uniformity_status"] = bp.get("uniformity_status", "OPTIMAL (< 5.0 K)")
        res["uniformity_compliant"] = bp.get("uniformity_compliant", True)
        res["bms_status"] = bp.get("bms_status", "NORMAL (15-35°C)")
        res["bms_derate_active"] = bp.get("bms_derate_active", False)
        res["bms_derate_factor"] = bp.get("bms_derate_factor", 1.0)
        res["modules"] = bp.get("modules", res.get("modules", {}))
        res["electrical_validation"] = bp.get("electrical_validation", sim_engine.validate_electrical_network())
        cells = []
        for c in bp.get("cells", []):
            c_copy = dict(c)
            c_copy["temp_c"] = c.get("temperature_c", 25.0)
            c_copy["heat_w"] = c.get("heat_generation_w", 0.0)
            cells.append(c_copy)
        res["cells"] = cells
    if "hydraulics" in res and isinstance(res["hydraulics"], dict):
        res["pump_energy_consumed_j"] = res["hydraulics"].get("pump_energy_consumed_j", 0.0)
        res["pump_energy_consumed_kwh"] = res["hydraulics"].get("pump_energy_consumed_kwh", 0.0)
    if "mhd" in res and isinstance(res["mhd"], dict):
        res["b_field_tesla"] = res["mhd"].get("B0_Tesla", getattr(sim_engine, "B0", 0.50))
        res["lorentz_force_n_m3"] = res["mhd"].get("lorentz_force_N_m3", 0.0)
    else:
        res["b_field_tesla"] = getattr(sim_engine, "B0", 0.50)
        res["lorentz_force_n_m3"] = 0.0
    if "simulation_time_s" in res:
        res["sim_time_s"] = res["simulation_time_s"]
    if "controls" in res and isinstance(res["controls"], dict):
        res["flow_velocity_m_s"] = res["controls"].get("U_in", 0.25)
    ctrl = res.get("controller", {}) if isinstance(res.get("controller"), dict) else {}
    thresh = res.get("controls", {}).get("threshold_c", 35.0) if isinstance(res.get("controls"), dict) else 35.0
    if res.get("pack_max_temp_c", 25.0) >= thresh + 8.0:
        res["system_status"] = "CRITICAL THERMAL"
    elif ctrl.get("cooling_active", False) or res.get("pack_max_temp_c", 25.0) >= thresh:
        res["system_status"] = "COOLING ACTIVE"
    else:
        res["system_status"] = "NORMAL"
    if "pipeline_stations" in res:
        stations = []
        for s in res["pipeline_stations"]:
            s_copy = dict(s)
            s_copy["temp_c"] = s.get("temperature_c", 25.0)
            stations.append(s_copy)
        res["pipeline_stations"] = stations
    if "equations_live" in res:
        eqs = []
        for eq in res["equations_live"]:
            eq_copy = dict(eq)
            eq_copy["calculated_value"] = eq.get("result", 0.0)
            eq_copy["si_units"] = eq.get("unit", "")
            eq_copy["latex_display"] = eq.get("latex", "")
            eqs.append(eq_copy)
        res["equations_live"] = eqs
    return res


# ==============================================================================
# 1. FRONTEND STATIC FILE SERVING
# ==============================================================================

@app.route("/")
def index():
    """Serves the main 3D simulation laboratory interface."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/css/<path:path>")
def serve_css(path):
    """Serves CSS stylesheets."""
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), path)


@app.route("/js/<path:path>")
def serve_js(path):
    """Serves JavaScript application modules."""
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), path)


@app.after_request
def add_no_cache_headers(response):
    """Prevents browser caching of simulation code and telemetry."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    return response


# ==============================================================================
# 2. CORE SIMULATION API ENDPOINTS
# ==============================================================================

@app.route("/api/status", methods=["GET"])
def get_status():
    """Returns complete real-time telemetry of the BTMS simulation."""
    state = sim_engine.last_telemetry if hasattr(sim_engine, "last_telemetry") else sim_engine.step(0.0)
    return jsonify(format_telemetry_payload(state))


@app.route("/api/step", methods=["POST"])
def step_simulation():
    """Advances simulation by dt seconds and returns updated state."""
    data = request.get_json(silent=True) or {}
    dt = float(data.get("dt", 0.5))
    telemetry = sim_engine.step(dt=dt)
    return jsonify(format_telemetry_payload(telemetry))


@app.route("/api/control", methods=["POST"])
def update_controls():
    """Updates simulation parameters (threshold, C-rate, velocity, magnetic field, etc.)."""
    data = request.get_json(silent=True) or {}
    sim_engine.set_control_parameters(data)
    telemetry = sim_engine.step(dt=0.01)
    return jsonify({
        "success": True,
        "message": "Parameters updated successfully.",
        "state": format_telemetry_payload(telemetry)
    })


@app.route("/api/reset", methods=["POST"])
def reset_simulation():
    """Resets all 50 battery cells and simulation clock to initial state."""
    data = request.get_json(silent=True) or {}
    init_t = float(data.get("initial_temp_c", 25.0))
    sim_engine.reset(initial_temp_c=init_t)
    return jsonify({
        "success": True,
        "message": f"Simulation reset to {init_t:.1f}°C reference state.",
        "state": format_telemetry_payload(sim_engine.last_telemetry)
    })


@app.route("/api/electrical/validate", methods=["GET"])
def validate_electrical_network():
    """Returns complete 180S1P series electrical circuit validation and module statistics."""
    val = sim_engine.validate_electrical_network()
    return jsonify(val)


# ==============================================================================
# 3. COMPONENT INSPECTION & 24 GOVERNING EQUATIONS
# ==============================================================================

@app.route("/api/inspect/<component_id>", methods=["GET"])
def inspect_component(component_id):
    """Returns deep physical, chemical, engineering, and mathematical inspection data for any component."""
    props = get_component_properties(component_id)
    props["success"] = True

    # Attach live operating state if component is a battery cell
    cid_upper = component_id.upper()
    if cid_upper.startswith("BAT-") or cid_upper.startswith("CELL"):
        cell = sim_engine.pack.get_cell_by_name(cid_upper)
        if cell is not None:
            cooling_area = getattr(cell, "cooling_area_m2", getattr(cell, "COOLING_AREA", 0.00308))
            tim_thick = getattr(cell, "TIM_THICKNESS_M", 0.0004)
            tim_cond = getattr(cell, "TIM_CONDUCTIVITY_W_MK", 3.0)
            zinfo = sim_engine.pack.zones.get(getattr(cell, "zone_id", "ZONE-01"), {})
            live_eng = {
                "id": cell.cell_id,
                "cell_id": cell.cell_id,
                "module_id": getattr(cell, "module_id", "MODULE_A"),
                "module_name": getattr(cell, "module_name", "Module A"),
                "local_row": getattr(cell, "local_row", 0),
                "local_col": getattr(cell, "local_col", 0),
                "top_terminal": getattr(cell, "top_terminal", "+"),
                "bottom_terminal": getattr(cell, "bottom_terminal", "-"),
                "cooling_zone": getattr(cell, "zone_id", "ZONE-01"),
                "form_factor": getattr(cell, "spec", {}).get("name", "21700"),
                "radius_mm": round(getattr(cell, "radius_m", 0.0105) * 1000.0, 2),
                "length_mm": round(getattr(cell, "length_m", 0.0700) * 1000.0, 2),
                "volume_cm3": round(getattr(cell, "volume_m3", 2.42e-5) * 1.0e6, 2),
                "surface_area_cm2": round(getattr(cell, "surface_area_m2", 5.31e-3) * 1.0e4, 2),
                "cooling_area_cm2": round(cooling_area * 1.0e4, 2),
                "thermal_energy_kj": round(cell.compute_thermal_energy_joules() / 1000.0, 3),
                "r_th_total_k_w": round(getattr(cell, "r_th_total", 0.45), 4),
                "temperature_c": round(cell.temp_c, 2),
                "current_temperature_c": round(cell.temp_c, 2),
                "initial_temp_c": round(cell.initial_temp_c, 2),
                "initial_temperature_c": round(cell.initial_temp_c, 2),
                "current_temperature_k": round(cell.temp_c + 273.15, 2),
                "delta_t_c": round(cell.temp_c - cell.initial_temp_c, 2),
                "temp_change_c": round(cell.temp_c - cell.initial_temp_c, 2),
                "max_recorded_temp_c": round(getattr(cell, "max_recorded_temp_c", cell.temp_c), 2),
                "min_recorded_temp_c": round(getattr(cell, "min_recorded_temp_c", cell.temp_c), 2),
                "cooling_rate_c_s": round(getattr(cell, "cooling_rate_c_s", 0.0), 4),
                "temp_history": list(getattr(cell, "temp_history", [cell.temp_c])),
                "heat_generation_w": round(cell.heat_gen_w, 2),
                "q_internal_w": round(getattr(cell, "q_internal_w", 2.76), 2),
                "q_hotspot_w": round(cell.q_hotspot_w, 2),
                "additional_heat_w": round(cell.q_hotspot_w, 2),
                "heat_removal_w": round(cell.heat_removed_w, 2),
                "heat_removed_w": round(cell.heat_removed_w, 2),
                "local_heat_transfer_rate_w": round(cell.heat_removed_w, 2),
                "tim_heat_flux_w_m2": round(cell.q_tim_flux_w_m2, 1),
                "tim_thickness_mm": round(tim_thick * 1000.0, 2),
                "tim_conductivity_w_mk": tim_cond,
                "tim_resistance_k_w": round(tim_thick / (tim_cond * max(cooling_area, 1.0e-6)), 4),
                "heat_gen_vol_w_m3": round(cell.heat_gen_vol_w_m3, 1),
                "status": cell.determine_color(sim_engine.threshold_c)["name"],
                "thermal_status": cell.determine_color(sim_engine.threshold_c)["name"],
                "color_hex": cell.determine_color(sim_engine.threshold_c)["hex"],
                "cooling_status": getattr(cell, "cooling_state", "OPTIMAL"),
                "c_rate": sim_engine.c_rate,
                "current_amperes": round(sim_engine.c_rate * getattr(cell, "q_rated", 4.8), 2),
                "terminal_voltage_v": round(getattr(cell, "v_nom", 3.7) - (sim_engine.c_rate * 0.015), 3),
                "internal_resistance_mohm": round(getattr(cell, "r_int_base", 0.018) * cell.core_factor * 1000.0, 2),
                "hotspot_active": cell.hotspot_multiplier > 1.0 or cell.q_hotspot_w > 0.0,
                "hotspot_multiplier": round(cell.hotspot_multiplier, 2),
                "local_coolant_temp_c": getattr(cell, "local_coolant_temp_c", zinfo.get("temp_inlet_c", 22.0)),
                "local_velocity_m_s": getattr(cell, "local_velocity_m_s", zinfo.get("velocity_m_s", 0.25)),
                "local_coolant_velocity_m_s": getattr(cell, "local_velocity_m_s", zinfo.get("velocity_m_s", 0.25)),
                "local_pressure_pa": getattr(cell, "local_pressure_pa", zinfo.get("pressure_kpa", 101.3) * 1000.0),
                "local_coolant_pressure_pa": getattr(cell, "local_pressure_pa", zinfo.get("pressure_kpa", 101.3) * 1000.0),
                "local_coolant_pressure_kpa": zinfo.get("pressure_kpa", 101.3),
                "valve_status": getattr(cell, "valve_status", zinfo.get("status", "IDLE")),
                "local_valve_status": getattr(cell, "valve_status", zinfo.get("status", "IDLE")),
                "local_valve_opening_pct": round(zinfo.get("valve_position", 0.15) * 100.0, 1),
                "b_field_tesla": getattr(cell, "b_field_tesla", sim_engine.B0),
                "lorentz_force_n_m3": getattr(cell, "lorentz_force_n_m3", 0.0),
            }
            props["live_engineering"] = live_eng
            props["data"] = live_eng

    # Attach S-channel or cooling zone data
    if "ZONE" in cid_upper or "CHANNEL" in cid_upper or "RIBBON" in cid_upper:
        matched_zone = None
        for zid, zinfo in sim_engine.pack.zones.items():
            if zid in cid_upper or zinfo.get("channel_id", "") in cid_upper:
                matched_zone = zinfo
                break
        if not matched_zone and sim_engine.pack.zones:
            matched_zone = list(sim_engine.pack.zones.values())[0]

        if matched_zone:
            props["component_id"] = matched_zone.get("channel_id", "CHANNEL-ZONE-01")
            props["name"] = f"Serpentine S-Bend Cooling Channel ({matched_zone['name']})"
            props["physical"] = {
                "channel_id": matched_zone.get("channel_id", "CHANNEL-ZONE-01"),
                "cooling_zone": matched_zone["zone_id"],
                "channel_geometry": "Smooth 3D Extruded S-Bend Tube with Inner Fluid Lumen",
                "material": "Copper C11000 (k = 398 W/m·K)" if "copper" in sim_engine.plate_material else "Aluminum 6061-T6 (k = 167 W/m·K)",
                "channel_length_m": 0.68,
                "outer_diameter_mm": 5.2,
                "inner_lumen_diameter_mm": 2.86,
                "hydraulic_diameter_mm": 2.86,
                "cross_sectional_area_mm2": 6.42,
                "wall_thickness_mm": 0.5,
                "thermal_conductivity_w_mk": 398.0 if "copper" in sim_engine.plate_material else 167.0,
            }
            props["chemical"] = {
                "nanofluid_base": "Water / Ethylene Glycol (60:40 by vol)",
                "nanoparticles": "Al2O3 (2.0 vol%) + Cu (1.0 vol%) Hybrid Nanofluid",
                "density_kg_m3": sim_engine.last_telemetry.get("nanofluid", {}).get("rho_hnf", 1080.0),
                "dynamic_viscosity_pa_s": sim_engine.last_telemetry.get("nanofluid", {}).get("mu_hnf", 0.001),
                "specific_heat_j_kgk": sim_engine.last_telemetry.get("nanofluid", {}).get("cp_hnf", 3750.0),
                "thermal_conductivity_w_mk": sim_engine.last_telemetry.get("nanofluid", {}).get("k_hnf", 0.68),
            }
            props["live_engineering"] = {
                "cooling_zone": matched_zone["zone_id"],
                "zone_name": matched_zone["name"],
                "valve_status": matched_zone["status"],
                "valve_opening_pct": round(matched_zone["valve_position"] * 100.0, 1),
                "flow_rate_l_min": matched_zone["flow_rate_l_min"],
                "velocity_m_s": matched_zone["velocity_m_s"],
                "local_reynolds": matched_zone["reynolds"],
                "local_nusselt": matched_zone["nusselt"],
                "local_htc_w_m2k": matched_zone["htc_w_m2k"],
                "pressure_kpa": matched_zone["pressure_kpa"],
                "pressure_drop_kpa": matched_zone["pressure_drop_kpa"],
                "temp_inlet_c": matched_zone["temp_inlet_c"],
                "temp_outlet_c": matched_zone["temp_outlet_c"],
                "temp_max_c": matched_zone["temp_max_c"],
                "temp_avg_c": matched_zone["temp_avg_c"],
                "heat_absorbed_w": matched_zone["heat_absorbed_w"],
                "heat_generated_w": matched_zone["heat_gen_w"],
            }

    # Attach Module & Serpentine Cooling Plate Inspection Data
    if cid_upper.startswith("MODULE") or cid_upper.startswith("MOD-") or cid_upper.startswith("PLATE-MODULE") or cid_upper.startswith("SERPENTINE-PLATE-"):
        mod_key = None
        for m_id, m_dict in sim_engine.pack.modules.items():
            if m_id in cid_upper or m_dict.get("plate_id", "") in cid_upper or m_dict.get("name", "").upper() in cid_upper:
                mod_key = m_id
                break
        if not mod_key and sim_engine.pack.modules:
            mod_key = "MODULE_A"

        m_info = sim_engine.pack.modules.get(mod_key, {})
        props["component_id"] = cid_upper
        props["name"] = f"Battery {m_info.get('name', 'Module')} (5x6 Cell Array & Serpentine Cooling)"
        props["physical"] = {
            "module_id": mod_key,
            "module_name": m_info.get("name", "Module"),
            "configuration": "30 Cylindrical Cells (5 Rows x 6 Cols) in Pure Series (30S1P)",
            "cooling_plate": m_info.get("plate_id", "PLATE-MODULE-A"),
            "nominal_voltage_v": round(m_info.get("num_cells", 30) * 3.70, 1),
            "max_voltage_v": round(m_info.get("num_cells", 30) * 4.20, 1),
            "capacity_ah": 4.8,
            "plate_material": "Aluminum 6061-T6 (k = 167 W/m·K)" if "aluminum" in sim_engine.plate_material else "Copper C11000 (k = 398 W/m·K)",
            "plate_height_mm": 70.0,
            "passes_count": 5,
        }
        props["chemical"] = {
            "nanofluid": "Al2O3 (1.5 vol%) + CuO (1.0 vol%) Hybrid Nanofluid in 60:40 Water/EG",
            "cell_chemistry": "Li-ion NMC-811 / Graphite",
        }
        props["live_engineering"] = {
            "module_id": mod_key,
            "valve_status": m_info.get("status", "IDLE"),
            "valve_opening_pct": round(m_info.get("valve_position", 0.15) * 100.0, 1),
            "flow_rate_l_min": m_info.get("flow_rate_l_min", 0.0),
            "flow_fraction_pct": round(m_info.get("flow_fraction", 0.1667) * 100.0, 2),
            "temp_max_c": m_info.get("temp_max_c", 25.0),
            "temp_avg_c": m_info.get("temp_avg_c", 25.0),
            "temp_min_c": m_info.get("temp_min_c", 25.0),
            "heat_absorbed_w": m_info.get("heat_absorbed_w", 0.0),
            "heat_generated_w": m_info.get("heat_gen_w", 0.0),
            "reynolds": m_info.get("reynolds", 0.0),
            "htc_w_m2k": m_info.get("htc_w_m2k", 12.0),
        }

    # Attach Inter-Module Series Jumpers
    if "JUMPER" in cid_upper:
        props["component_id"] = cid_upper
        props["name"] = f"Heavy-Duty Inter-Module Series Jumper Link ({cid_upper})"
        props["physical"] = {
            "component_type": "Inter-Module Heavy-Duty Series Busbar Jumper",
            "material": "C11000 Electrolytic Tough Pitch Copper (99.9% Cu)",
            "conductor_cross_section_mm2": 32.0,
            "current_rating_a": 250.0,
            "insulation": "Flame-Retardant Polyolefin Heat-Shrink Sleeve",
        }
        props["live_engineering"] = {
            "operating_current_a": round(sim_engine.c_rate * 4.8, 1),
            "ir_voltage_drop_mv": round(sim_engine.c_rate * 0.45, 2),
            "temperature_c": round(sim_engine.pack.cells[0].temp_c + 0.5, 2),
            "status": "NORMAL CONTINUITY VERIFIED",
        }

    # Attach electrical busbar & BMS sense wiring data
    if "BUSBAR" in cid_upper or "ELECTRICAL" in cid_upper or "WIRING" in cid_upper or "BMS" in cid_upper:
        props["component_id"] = cid_upper
        props["name"] = "Traction Battery Electrical Busbar & BMS Sensor Harness"
        props["physical"] = {
            "component_type": "Nickel-Plated Copper Busbar Link & Insulated BMS Sense Wire",
            "material": "C11000 High-Conductivity Copper (99.9% Cu, 398 W/m·K, 5.96e7 S/m)",
            "conductor_cross_section_mm2": 24.0,
            "current_carrying_capacity_a": 180.0,
            "series_parallel_config": "180S1P Pure Series Battery Pack Architecture",
        }
        props["chemical"] = {
            "conductor_composition": "Electrolytic Tough Pitch Copper (ETP Cu, UNS C11000)",
            "plating": "Electroplated Pure Nickel (5-8 µm) for oxidation protection",
            "insulation": "High-dielectric Polyimide / ETFE flame-retardant wiring jacket",
            "operating_voltage_dc": round(180 * 3.7, 1),
            "max_system_voltage_dc": round(180 * 4.2, 1),
        }
        props["live_engineering"] = {
            "operating_current_a": round(sim_engine.c_rate * 4.8, 1),
            "system_voltage_v": round(180 * 3.68, 2),
            "total_pack_power_kw": round((sim_engine.c_rate * 4.8 * 180 * 3.68) / 1000.0, 2),
            "bms_sensing_channels": sim_engine.num_cells,
            "bms_status": "NORMAL - ALL 180 VOLTAGE SENSE LINES ACTIVE",
            "busbar_ir_drop_mv": round(sim_engine.c_rate * 1.25, 2),
        }

    # Attach pipeline station live telemetry if applicable
    if cid_upper.startswith("STATION-") or cid_upper.startswith("PIPE"):
        st_num = None
        for part in cid_upper.replace("STATION-", "").replace("PIPE-", "").split("-"):
            if part.isdigit():
                st_num = int(part)
                break
        stations = sim_engine.last_telemetry.get("pipeline_stations", [])
        matched_st = None
        if st_num and 1 <= st_num <= len(stations):
            matched_st = stations[st_num - 1]
        elif stations:
            matched_st = stations[0]
        if matched_st:
            props["live_engineering"] = dict(matched_st)
            props["live_engineering"]["hydraulics"] = sim_engine.last_telemetry.get("hydraulics", {})

    # Attach pump live hydraulics
    if "PUMP" in cid_upper:
        hyd = sim_engine.last_telemetry.get("hydraulics", {})
        ctrl = sim_engine.last_telemetry.get("controller", {})
        props["live_engineering"] = {
            "pump_status": "ACTIVE" if ctrl.get("pump_active") else "OFF",
            "pump_speed_pct": ctrl.get("pump_speed_pct", 0.0),
            "pump_rpm": round(ctrl.get("pump_speed_pct", 0.0) * 36.0, 0),
            "vol_flow_rate_l_min": hyd.get("vol_flow_rate_l_min", 0.0),
            "mass_flow_rate_kg_s": hyd.get("mass_flow_rate_kg_s", 0.0),
            "pressure_rise_kpa": hyd.get("total_delta_p_kPa", 0.0),
            "hydraulic_power_w": hyd.get("p_hydraulic_w", 0.0),
            "electrical_power_w": hyd.get("p_electrical_w", 0.0),
            "pump_efficiency_pct": round(hyd.get("pump_efficiency", 0.75) * 100.0, 1),
        }

    # Attach radiator live thermal performance
    if "RADIATOR" in cid_upper:
        cp = sim_engine.last_telemetry.get("cooling_performance", {})
        ctrl = sim_engine.last_telemetry.get("controller", {})
        props["live_engineering"] = {
            "fan_status": "ACTIVE" if ctrl.get("fan_active") else "OFF",
            "fan_speed_pct": ctrl.get("fan_speed_pct", 0.0),
            "fan_rpm": round(ctrl.get("fan_speed_pct", 0.0) * 28.0, 0),
            "coolant_inlet_t_c": cp.get("T_outlet_c", 25.0),
            "coolant_outlet_t_c": cp.get("T_radiator_return_c", 22.0),
            "heat_rejected_w": cp.get("heat_rejected_radiator_W", 0.0),
            "airflow_velocity_m_s": round(ctrl.get("fan_speed_pct", 0.0) * 0.08, 2),
        }

    # Attach chiller & heat exchanger live data
    if "CHILLER" in cid_upper or "HEX" in cid_upper:
        cp = sim_engine.last_telemetry.get("cooling_performance", {})
        ctrl = sim_engine.last_telemetry.get("controller", {})
        props["live_engineering"] = {
            "chiller_active": ctrl.get("chiller_active", False),
            "heat_removed_total_w": cp.get("heat_removed_W", 0.0),
            "u_value_w_m2k": 2450.0,
            "t_inlet_c": cp.get("T_inlet_c", 22.0),
            "coolant_delta_t_k": cp.get("coolant_delta_T_K", 0.0),
        }

    # Fetch relevant governing equations
    eq_ids = props.get("governing_equations", [1, 2, 3])
    all_eqs = sim_engine.last_telemetry.get("equations_live", [])
    relevant_eq_details = []
    for eq in all_eqs:
        if eq.get("id") in eq_ids:
            eq_copy = dict(eq)
            eq_copy["calculated_value"] = eq.get("result", 0.0)
            eq_copy["si_units"] = eq.get("unit", "")
            eq_copy["latex_display"] = eq.get("latex", "")
            relevant_eq_details.append(eq_copy)
    props["live_equations"] = relevant_eq_details

    return jsonify(props)


@app.route("/api/hotspot", methods=["POST"])
def set_hotspot():
    """Sets localized thermal hotspots (Configurations A-H, patterns, custom cells, auto mode, or clear)."""
    data = request.get_json(silent=True) or {}
    config_type = data.get("config_type") or data.get("configuration") or data.get("scenario") or data.get("type")
    cell_ids = data.get("cell_ids", [])
    if "cell_id" in data and not cell_ids:
        cell_ids = [data["cell_id"]]
    additional_heat_w = data.get("additional_heat_w") or data.get("heat_w") or data.get("intensity_w")
    multiplier = float(data.get("multiplier", 3.0))
    initial_temp_c = data.get("initial_temp_c")
    duration_s = float(data.get("duration_s", 30.0))
    clear = bool(data.get("clear", False))
    clear_previous = bool(data.get("clear_previous", False))
    auto_config = data.get("auto")

    if clear:
        sim_engine.clear_hotspots()
        telemetry = sim_engine.step(dt=0.01)
        return jsonify({"success": True, "message": "All hotspots cleared.", "state": format_telemetry_payload(telemetry)})

    if auto_config is not None:
        enabled = bool(auto_config.get("enabled", True))
        interval_s = float(auto_config.get("interval_s", 10.0))
        seed = int(auto_config.get("seed", 42))
        sim_engine.set_auto_hotspot_mode(enabled, interval_s, seed)
        telemetry = sim_engine.step(dt=0.01)
        return jsonify({
            "success": True,
            "message": f"Auto hotspot mode {'ENABLED' if enabled else 'DISABLED'} (interval: {interval_s}s, seed: {seed}).",
            "auto_hotspot": {"enabled": enabled, "interval_s": interval_s, "seed": seed},
            "state": format_telemetry_payload(telemetry)
        })

    if config_type and "RANDOM" in config_type.upper():
        heat_val = float(additional_heat_w) if additional_heat_w is not None else 20.0
        event = sim_engine.pack.trigger_random_hotspots(count=10, additional_heat_w=heat_val, duration_s=duration_s)
        telemetry = sim_engine.step(dt=0.01)
        return jsonify({
            "success": True,
            "event_id": event.event_id,
            "event": event.to_dict(),
            "affected_cells": list(event.cell_ids),
            "state": format_telemetry_payload(telemetry)
        })

    if config_type:
        res = sim_engine.apply_hotspot_configuration(
            config_type=config_type,
            custom_cells=cell_ids if cell_ids else None,
            additional_heat_w=additional_heat_w,
            duration_s=duration_s,
            clear_previous=clear_previous
        )
        if hasattr(res, "to_dict"):
            res = res.to_dict()
        telemetry = sim_engine.step(dt=0.01)
        res["state"] = format_telemetry_payload(telemetry)
        res["success"] = True
        if "affected_cells" not in res and "cell_ids" in res:
            res["affected_cells"] = list(res["cell_ids"])
        res["event"] = dict(res)
        return jsonify(res)
        res["state"] = format_telemetry_payload(telemetry)
        return jsonify(res)

    if cell_ids:
        res = sim_engine.apply_hotspot_configuration(
            config_type="CUSTOM",
            custom_cells=cell_ids,
            additional_heat_w=additional_heat_w or 16.0,
            duration_s=duration_s,
            clear_previous=clear_previous
        )
        if initial_temp_c is not None:
            for cid in cell_ids:
                c = sim_engine.pack.get_cell_by_name(cid)
                if c:
                    c.temp_c = float(initial_temp_c)
        telemetry = sim_engine.step(dt=0.01)
        res["state"] = format_telemetry_payload(telemetry)
        return jsonify(res)

    # Default fallback: CELL-125
    res = sim_engine.apply_hotspot_configuration(
        config_type="A",
        additional_heat_w=additional_heat_w or 18.0,
        duration_s=duration_s,
        clear_previous=clear_previous
    )
    telemetry = sim_engine.step(dt=0.01)
    res["state"] = format_telemetry_payload(telemetry)
    return jsonify(res)


@app.route("/api/hotspot/events", methods=["GET"])
def get_hotspot_events():
    """Returns active hotspot events, full recorded history, and statistics."""
    bp = sim_engine.last_telemetry.get("battery_pack", {})
    active = bp.get("active_hotspot_events", [e.to_dict() for e in sim_engine.pack.active_hotspot_events])
    history = bp.get("hotspot_event_history", [e.to_dict() for e in sim_engine.pack.hotspot_event_history])
    return jsonify({
        "success": True,
        "active_events_count": len(active),
        "history_events_count": len(history),
        "total_events_count": len(active) + len(history),
        "active_events": active,
        "history": history,
        "scheduled_events": sim_engine.pack.event_schedule
    })


@app.route("/api/hotspot/schedule", methods=["POST"])
def schedule_hotspot_event():
    """Schedules an overheating event to trigger at future simulation time."""
    data = request.get_json(silent=True) or {}
    time_s = float(data.get("time_s", sim_engine.sim_time_s + 10.0))
    config_type = data.get("config_type") or data.get("configuration") or "A"
    cell_ids = data.get("cell_ids")
    heat_w = float(data.get("heat_w") or data.get("additional_heat_w") or 15.0)
    dur_s = float(data.get("duration_s", 25.0))
    res = sim_engine.schedule_hotspot_event(time_s=time_s, config_type=config_type,
                                            cell_ids=cell_ids, heat_w=heat_w, duration_s=dur_s)
    return jsonify(res)


@app.route("/api/hotspot/demonstration_sequence", methods=["POST"])
def run_demonstration_sequence():
    """Loads and schedules the 10-event demonstration sequence matching Requirement 15."""
    seq = sim_engine.load_demonstration_sequence()
    return jsonify({
        "success": True,
        "message": "10-Event Demonstration Sequence scheduled into timeline.",
        "events_count": len(seq),
        "schedule": seq
    })


@app.route("/api/export_hotspot_events_csv", methods=["GET"])
def export_hotspot_events_csv():
    """Exports all recorded hotspot lifecycle events as downloadable CSV."""
    csv_str = sim_engine.export_hotspot_events_csv()
    return Response(
        csv_str.encode("utf-8"),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=btms_hotspot_event_history.csv"}
    )


@app.route("/api/hotspot/scenario/<scenario_code>", methods=["GET", "POST"])
def trigger_hotspot_scenario(scenario_code):
    """Direct shortcut endpoint to activate hotspot scenario A through H."""
    res = sim_engine.apply_hotspot_configuration(config_type=scenario_code)
    telemetry = sim_engine.step(dt=0.01)
    res["state"] = format_telemetry_payload(telemetry)
    return jsonify(res)


@app.route("/api/zones", methods=["GET"])
def get_cooling_zones():
    """Returns real-time status of all independently valved cooling zones."""
    return jsonify({
        "success": True,
        "count": len(sim_engine.pack.zones),
        "zones": sim_engine.pack.zones,
        "shared_pump_duty_pct": sim_engine.last_telemetry.get("controller", {}).get("pump_speed_pct", 0.0),
        "cooling_active": sim_engine.last_telemetry.get("controller", {}).get("cooling_active", False)
    })


@app.route("/api/equations", methods=["GET"])
def get_all_equations():
    """Returns all 24 core governing equations plus 15 cylindrical equations (A through O) with live numerical substitutions."""
    all_eqs = sim_engine.last_telemetry.get("equations_live", [])
    cyl_eqs = sim_engine.last_telemetry.get("cylindrical_equations", [])
    eqs = []
    for eq in all_eqs:
        eq_copy = dict(eq)
        eq_copy["calculated_value"] = eq.get("result", 0.0)
        eq_copy["si_units"] = eq.get("unit", "")
        eq_copy["latex_display"] = eq.get("latex", "")
        eqs.append(eq_copy)
    cyl_formatted = []
    for eq in cyl_eqs:
        eq_copy = dict(eq)
        eq_copy["calculated_value"] = eq.get("result", 0.0)
        eq_copy["si_units"] = eq.get("unit", "")
        eq_copy["latex_display"] = eq.get("latex", "")
        cyl_formatted.append(eq_copy)
    return jsonify({
        "count": len(eqs),
        "equations": eqs,
        "cylindrical_count": len(cyl_formatted),
        "cylindrical_equations": cyl_formatted,
        "total_count": len(eqs) + len(cyl_formatted)
    })


@app.route("/api/equations/<int:eq_id>", methods=["GET"])
def get_single_equation(eq_id):
    """Returns detailed mathematical and numerical breakdown for a specific formula (1-24)."""
    eqs = sim_engine.last_telemetry.get("equations_live", [])
    match = next((eq for eq in eqs if eq.get("id") == eq_id), None)
    if match:
        return jsonify(match)
    return jsonify({"error": f"Equation with ID {eq_id} not found."}), 404


# ==============================================================================
# 4. DATASET PROCESSING & ML SURROGATE
# ==============================================================================

@app.route("/api/upload_dataset", methods=["POST"])
def upload_dataset():
    """Accepts uploaded CSV or JSON file, validates bounds, and returns dataset summary."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded in form field 'file'."}), 400

    file = request.files["file"]
    content = file.read()
    filename = file.filename or "uploaded_dataset.csv"

    res = DatasetProcessor.parse_and_validate(content, filename)
    return jsonify(res)


@app.route("/api/apply_dataset", methods=["POST"])
def apply_dataset_record():
    """Applies a selected record from an ingested dataset to the simulation engine."""
    data = request.get_json(silent=True) or {}
    record = data.get("record", {})
    if not record:
        return jsonify({"success": False, "error": "No record payload provided."}), 400

    sim_engine.set_control_parameters(record)
    telemetry = sim_engine.step(0.01)
    return jsonify({
        "success": True,
        "message": "Dataset configuration applied to simulation engine.",
        "state": telemetry
    })


@app.route("/api/predict_ml", methods=["POST"])
def predict_ml():
    """Runs fast ML surrogate model prediction for peak battery temperature."""
    data = request.get_json(silent=True) or {}
    u_in = float(data.get("U_in", sim_engine.U_in))
    t_in = float(data.get("T_in_c", sim_engine.T_in_c))
    t_init = float(data.get("T_batt_init_c", 25.0))
    t_amb = float(data.get("T_amb_c", sim_engine.T_amb_c))
    b0 = float(data.get("B0", sim_engine.B0))
    phi1 = float(data.get("phi1", sim_engine.phi1))
    phi2 = float(data.get("phi2", sim_engine.phi2))
    k_perm = float(data.get("k_perm", sim_engine.k_perm))
    c_rate = float(data.get("c_rate", sim_engine.c_rate))
    q_rated = float(data.get("Q_rated", 20.0))
    l_char = float(data.get("L_char", sim_engine.Dh))

    res = ml_predictor.predict(
        U_in=u_in, T_in_c=t_in, T_batt_init_c=t_init, T_amb_c=t_amb,
        B0=b0, phi1=phi1, phi2=phi2, k_perm=k_perm, c_rate=c_rate,
        Q_rated=q_rated, L_char=l_char
    )

    # Attach current physics-based solver peak temperature for side-by-side comparison
    physics_max_t = sim_engine.pack.step(0.0, c_rate, 450.0, t_in)["max_cell_temp_c"]
    res["physics_solver_temp_c"] = round(physics_max_t, 2)
    res["absolute_error_c"] = round(abs(res["predicted_peak_temp_c"] - physics_max_t), 3)

    return jsonify(res)


@app.route("/api/reconfigure_pack", methods=["POST"])
def reconfigure_pack():
    """Dynamically reconfigures cell count (550, 600, 700, 800, 1000), form factor, and plate material."""
    data = request.get_json(silent=True) or {}
    num_cells = int(data.get("num_cells", sim_engine.num_cells))
    form_factor = str(data.get("form_factor", sim_engine.form_factor))
    plate_material = str(data.get("plate_material", sim_engine.plate_material))
    sim_engine.reconfigure(num_cells=num_cells, form_factor=form_factor, plate_material=plate_material)
    telemetry = sim_engine.step(0.01)
    return jsonify({
        "success": True,
        "message": f"Pack reconfigured to {num_cells} cells ({form_factor}, {plate_material} wavy plates).",
        "state": format_telemetry_payload(telemetry)
    })


@app.route("/api/export_csv", methods=["GET"])
def export_csv():
    """Exports all cylindrical battery cells and current system metrics as downloadable CSV."""
    cells = [c.to_dict(sim_engine.threshold_c) for c in sim_engine.pack.cells]
    df = pd.DataFrame(cells)

    # Legacy cell ID alias for compatibility
    df["legacy_id"] = [f"BAT-{(i % 50) + 1:02d}" for i in range(len(cells))]

    # Add system-level columns
    df["sim_time_s"] = sim_engine.sim_time_s
    df["c_rate"] = sim_engine.c_rate
    df["threshold_c"] = sim_engine.threshold_c
    df["cooling_mode"] = sim_engine.cooling_mode
    df["U_in_m_s"] = sim_engine.U_in
    df["T_in_c"] = sim_engine.T_in_c
    df["B0_T"] = sim_engine.B0
    df["phi1_Al2O3"] = sim_engine.phi1
    df["phi2_CuO"] = sim_engine.phi2
    df["Re"] = sim_engine.last_telemetry["dimensionless"]["Re"]
    df["Nu"] = sim_engine.last_telemetry["dimensionless"]["Nu"]

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode("utf-8")

    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=btms_simulation_results.csv"}
    )


if __name__ == "__main__":
    print("\n=======================================================")
    print("  3D BTMS FLASK API SERVER STARTING ON PORT 5001")
    print("  Open browser at: http://localhost:5001")
    print("=======================================================\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
