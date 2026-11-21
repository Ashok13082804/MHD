"""
Dynamic Thermal Management Controller with Hysteresis & 8-State Control Logic
Implements States 1-8, Configurable Activation/Deactivation Thresholds,
Actuator Modulation (Pump, Fan, Chiller, Heater, Valve), and Safety Limits.
"""

from typing import Dict, Any


class ThermalCoolingController:
    """
    Manages closed-loop thermal management for EV traction battery pack.
    Implements 8 operating states:
      1. OFF
      2. PASSIVE COOLING
      3. ACTIVE COOLING
      4. NANOFLUID COOLING
      5. MHD NANOFLUID COOLING
      6. HEATING / PRECONDITIONING
      7. TEMPERATURE STABILISING
      8. FAULT / SENSOR ERROR
    """

    DEFAULT_HYSTERESIS = 2.5  # deg C band to prevent rapid chattering

    def __init__(self, threshold_c: float = 35.0, mode: str = "auto", deactivation_threshold_c: float = None):
        self.threshold_c = float(threshold_c)
        self.deactivation_threshold_c = float(deactivation_threshold_c) if deactivation_threshold_c is not None else (self.threshold_c - self.DEFAULT_HYSTERESIS)
        self.mode = mode.lower()  # auto, passive, active, nanofluid, mhd_nanofluid, heating, off

        self.cooling_active = False
        self.chiller_active = False
        self.fan_active = False
        self.heater_active = False
        self.valve_position_pct = 0.0   # 0% = bypass, 100% = full heat rejection loop
        self.pump_speed_pct = 0.0
        self.fan_speed_pct = 0.0
        self.heater_power_w = 0.0
        self.state_id = 1
        self.state_name = "OFF"
        self.status = "Cooling OFF"

    def set_thresholds(self, threshold_c: float, deactivation_threshold_c: float = None):
        """Sets activation threshold and configurable deactivation threshold."""
        self.threshold_c = float(threshold_c)
        if deactivation_threshold_c is not None:
            self.deactivation_threshold_c = float(deactivation_threshold_c)
        else:
            self.deactivation_threshold_c = self.threshold_c - self.DEFAULT_HYSTERESIS
        # Ensure deactivation is strictly lower than activation
        if self.deactivation_threshold_c >= self.threshold_c:
            self.deactivation_threshold_c = self.threshold_c - 1.0

    def set_threshold(self, threshold_c: float):
        """Backwards compatibility for set_threshold."""
        self.set_thresholds(threshold_c)

    def set_mode(self, mode: str):
        """Sets operating mode."""
        self.mode = mode.lower()

    def update(self, max_cell_temp_c: float, ambient_temp_c: float = 25.0, dt: float = 1.0) -> Dict[str, Any]:
        """
        Evaluates 50-cell maximum temperature and transitions between the 8 controller states.
        Applies hysteresis switching and calculates PWM pump, fan, heater, and valve commands.
        """
        # State 8: Fault / Sensor Error Check
        if max_cell_temp_c > 85.0 or max_cell_temp_c < -40.0:
            self.state_id = 8
            self.state_name = "FAULT / SENSOR ERROR"
            self.cooling_active = True
            self.chiller_active = True
            self.fan_active = True
            self.heater_active = False
            self.pump_speed_pct = 100.0
            self.fan_speed_pct = 100.0
            self.valve_position_pct = 100.0
            self.status = "CRITICAL THERMAL RUNAWAY WARNING"
            return self._build_state_dict()

        # State 6: Heating / Preconditioning
        if self.mode == "heating" or (self.mode == "auto" and max_cell_temp_c < 15.0):
            self.state_id = 6
            self.state_name = "HEATING / PRECONDITIONING"
            self.heater_active = True
            self.cooling_active = False
            self.chiller_active = False
            self.fan_active = False
            self.pump_speed_pct = 35.0  # gentle circulation for uniform heating
            self.fan_speed_pct = 0.0
            self.valve_position_pct = 0.0  # bypass radiator
            self.heater_power_w = 1500.0
            self.status = "PTC Preconditioning Active"
            return self._build_state_dict()

        self.heater_active = False
        self.heater_power_w = 0.0

        # State 2: Forced Passive Mode
        if self.mode == "passive":
            self.state_id = 2
            self.state_name = "PASSIVE COOLING"
            self.cooling_active = False
            self.chiller_active = False
            self.fan_active = False
            self.pump_speed_pct = 0.0
            self.fan_speed_pct = 0.0
            self.valve_position_pct = 0.0
            self.status = "Passive Natural Cooling"
            return self._build_state_dict()

        # State 1: Forced OFF Mode
        if self.mode == "off":
            self.state_id = 1
            self.state_name = "OFF"
            self.cooling_active = False
            self.chiller_active = False
            self.fan_active = False
            self.pump_speed_pct = 0.0
            self.fan_speed_pct = 0.0
            self.valve_position_pct = 0.0
            self.status = "Cooling System OFF"
            return self._build_state_dict()

        # Hysteresis Switch:
        # IF T_max >= T_target -> Cooling ON
        # IF T_max <= T_off -> Cooling OFF
        # IF T_off < T_max < T_target -> Maintain previous state
        if not self.cooling_active:
            if max_cell_temp_c >= self.threshold_c:
                self.cooling_active = True
        else:
            if max_cell_temp_c <= self.deactivation_threshold_c:
                self.cooling_active = False

        if self.cooling_active:
            overtemp = max(max_cell_temp_c - self.threshold_c, 0.0)

            # Determine State 3, 4, or 5
            if self.mode == "mhd_nanofluid" or "mhd" in self.mode:
                self.state_id = 5
                self.state_name = "MHD NANOFLUID COOLING"
                self.status = "Coupled MHD Hybrid Nanofluid Cooling Active"
            elif self.mode == "hybrid_nanofluid" or self.mode == "nanofluid":
                self.state_id = 4
                self.state_name = "NANOFLUID COOLING"
                self.status = "Closed-Loop Hybrid Nanofluid Cooling Active"
            else:
                self.state_id = 3
                self.state_name = "ACTIVE COOLING"
                self.status = "Active Fluid Circulation Active"

            # Modulate Actuators proportionally
            self.pump_speed_pct = min(50.0 + overtemp * 12.0, 100.0)
            self.fan_active = True
            self.fan_speed_pct = min(40.0 + overtemp * 14.0, 100.0)
            self.valve_position_pct = min(60.0 + overtemp * 10.0, 100.0)

            # Chiller activation under heavy thermal load (> threshold + 3.5°C)
            if max_cell_temp_c >= self.threshold_c + 3.5:
                self.chiller_active = True
                self.status += " (Chiller Boost Engaged)"
            else:
                self.chiller_active = False
        else:
            self.chiller_active = False
            self.fan_active = False
            self.pump_speed_pct = 0.0
            self.fan_speed_pct = 0.0
            self.valve_position_pct = 0.0

            # State 7 vs State 1
            if max_cell_temp_c > self.deactivation_threshold_c - 4.0:
                self.state_id = 7
                self.state_name = "TEMPERATURE STABILISING"
                self.status = "Temperature Stabilised (Normal Range)"
            else:
                self.state_id = 1
                self.state_name = "OFF"
                self.status = "Cooling System Standby / OFF"

        return self._build_state_dict()

    def _build_state_dict(self) -> Dict[str, Any]:
        """Serializes controller telemetry for API and 3D visualizer."""
        return {
            "cooling_active": self.cooling_active,
            "cooling_mode": self.mode,
            "state_id": self.state_id,
            "state_name": self.state_name,
            "status": self.status,
            "threshold_c": round(self.threshold_c, 2),
            "deactivation_threshold_c": round(self.deactivation_threshold_c, 2),
            "pump_active": self.pump_speed_pct > 0.0,
            "pump_speed_pct": round(self.pump_speed_pct, 1),
            "pump_duty_cycle_pct": round(self.pump_speed_pct, 1),
            "fan_active": self.fan_active,
            "fan_speed_pct": round(self.fan_speed_pct, 1),
            "fan_duty_cycle_pct": round(self.fan_speed_pct, 1),
            "chiller_active": self.chiller_active,
            "heater_active": self.heater_active,
            "heater_power_w": round(self.heater_power_w, 1),
            "valve_position_pct": round(self.valve_position_pct, 1),
        }
