"""
Boundary Conditions and Interface Conjugate Heat Transfer
Implements Formulations 10, 11, and 12 for BTMS Simulation.
"""

import numpy as np
from typing import Dict, Union, Tuple, Optional


# ==============================================================================
# FORMULA 10: Boundary Conditions Formulation
# ==============================================================================
def apply_flow_and_thermal_boundary_conditions(
    u: np.ndarray,
    v: np.ndarray,
    T: np.ndarray,
    U_in: float,
    T_in: float,
    Nx: int,
    Ny_fluid: int,
    Ny_total: int,
    dx: float,
    dy: float,
    h_amb: float = 5.0,
    T_amb: float = 298.15,
    k_battery: float = 3.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    FORMULA 10: Applies boundary conditions directly to the 2D field arrays.
    
    1. INLET (x = 0, fluid zone j in [0, Ny_fluid-1]):
       u[0, j] = U_in
       v[0, j] = 0.0
       T[0, j] = T_in
       
    2. OUTLET (x = L, i = Nx-1, fluid zone):
       du/dx = 0 -> u[Nx-1, j] = u[Nx-2, j]
       dv/dx = 0 -> v[Nx-1, j] = v[Nx-2, j]
       dT/dx = 0 -> T[Nx-1, j] = T[Nx-2, j]
       
    3. CHANNEL BOTTOM WALL (y = 0, j = 0):
       No-slip: u[i, 0] = 0.0, v[i, 0] = 0.0
       Adiabatic impermeable wall: dT/dy = 0 -> T[i, 0] = T[i, 1]
       
    4. INTERFACE WALL (y = H_f, j = Ny_fluid):
       No-slip fluid wall: u[i, Ny_fluid-1] = 0.0, v[i, Ny_fluid-1] = 0.0
       
    5. BATTERY TOP OUTER BOUNDARY (y = H_f + H_b, j = Ny_total-1):
       Convective heat dissipation to ambient air:
       -k_b * dT/dy = h_amb * (T - T_amb)
       => T[i, Ny_total-1] = (k_b * T[i, Ny_total-2] + h_amb * dy * T_amb) / (k_b + h_amb * dy)
    """
    # 1. INLET
    u[0, :Ny_fluid] = U_in
    v[0, :Ny_fluid] = 0.0
    T[0, :Ny_fluid] = T_in

    # 2. OUTLET (Neumann zero-gradient)
    u[-1, :Ny_fluid] = u[-2, :Ny_fluid]
    v[-1, :Ny_fluid] = v[-2, :Ny_fluid]
    T[-1, :] = T[-2, :]

    # 3. BOTTOM POROUS WALL (y = 0)
    u[:, 0] = 0.0
    v[:, 0] = 0.0
    T[:, 0] = T[:, 1]  # adiabatic

    # 4. INTERFACE NO-SLIP FOR FLUID
    u[:, Ny_fluid - 1] = 0.0
    v[:, Ny_fluid - 1] = 0.0

    # In battery solid domain, fluid velocities are zero
    u[:, Ny_fluid:] = 0.0
    v[:, Ny_fluid:] = 0.0

    # 5. BATTERY TOP OUTER WALL (Robin boundary condition)
    alpha = (h_amb * dy) / k_battery
    T[:, -1] = (T[:, -2] + alpha * T_amb) / (1.0 + alpha)

    # Battery lateral walls (x = 0 and x = L in battery zone): insulated
    T[0, Ny_fluid:] = T[1, Ny_fluid:]
    T[-1, Ny_fluid:] = T[-2, Ny_fluid:]

    return u, v, T


def evaluate_boundary_conditions_record(
    U_in: float,
    T_in: float,
    T_wall: float,
    q_wall: float
) -> Dict[str, Union[float, str]]:
    """
    Returns structured explanation of Formula 10 for reporting and calculators.
    """
    return {
        "formula_name": "Boundary Conditions Formulation",
        "equation": "Inlet: (u=U_in, v=0, T=T_in); Outlet: (du/dn=0, dv/dn=0, dT/dn=0); Wall: (u=0, v=0, q_wall=-k*dT/dn)",
        "inputs": {
            "U_in": (U_in, "m/s"),
            "T_in": (T_in, "K"),
            "T_wall": (T_wall, "K"),
            "q_wall": (q_wall, "W/m^2"),
        },
        "intermediates": {
            "inlet_velocity_vector": (f"({U_in:.3f}, 0.000)", "m/s"),
            "outlet_derivative_condition": ("du/dx = 0, dv/dx = 0, dT/dx = 0", "Neumann"),
            "no_slip_condition": ("u = 0, v = 0 at y = 0 and y = H_f", "Dirichlet"),
        },
        "result": U_in,
        "unit": "Applied directly in finite-difference solver",
        "interpretation": "Full hydrodynamic and thermal boundary conditions enforce mass, momentum, and heat conservation at all domain boundaries.",
    }


# ==============================================================================
# FORMULA 11: Temperature Continuity at Interface
# ==============================================================================
def calc_temperature_continuity(
    T_b: float,
    T_f: float,
    tolerance: float = 1.0e-4
) -> Dict[str, Union[float, str, bool]]:
    """
    FORMULA 11: Temperature Continuity at Battery-Coolant Interface.
    At the ideal contact interface (no thermal contact resistance):
    T_b(x, y_int) = T_f(x, y_int)
    
    Parameters:
        T_b (float): Battery surface temperature at interface [K]
        T_f (float): Coolant fluid temperature at interface [K]
        tolerance (float): Numerical tolerance [K]
    """
    delta_T_interface = abs(T_b - T_f)
    is_continuous = bool(delta_T_interface <= tolerance)

    interpretation = (
        f"Interface temperature difference is |T_b - T_f| = {delta_T_interface:.6f} K. "
        f"Temperature continuity ({'SATISFIED' if is_continuous else 'RESIDUAL RESENT'}) "
        f"ensures unbroken temperature profile across solid-fluid interface."
    )

    return {
        "formula_name": "Temperature Continuity at Battery-Coolant Interface",
        "equation": "T_b = T_f (at y = y_interface)",
        "inputs": {
            "T_b": (T_b, "K"),
            "T_f": (T_f, "K"),
        },
        "intermediates": {
            "temperature_jump_Delta_T": (delta_T_interface, "K"),
            "numerical_tolerance": (tolerance, "K"),
        },
        "result": delta_T_interface,
        "is_continuous": is_continuous,
        "unit": "K",
        "interpretation": interpretation,
    }


# ==============================================================================
# FORMULA 12: Heat Flux Continuity at Interface
# ==============================================================================
def calc_heat_flux_continuity(
    k_b: float,
    dT_b_dn: float,
    k_f: float,
    dT_f_dn: float,
    R_tc: float = 0.0,
    T_b: Optional[float] = None,
    T_f: Optional[float] = None
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 12: Heat Flux Continuity at Battery-Coolant Interface.
    Ideal Interface (R_tc = 0):
        q''_b = -k_b * (dT_b/dn) = -k_f * (dT_f/dn) = q''_f
        
    Modified Interface with Thermal Contact Resistance (R_tc > 0):
        -k_b * (dT_b/dn) = (T_b - T_f) / R_tc = -k_f * (dT_f/dn)
        
    Parameters:
        k_b (float): Battery thermal conductivity [W/(m*K)]
        dT_b_dn (float): Battery normal temperature gradient [K/m]
        k_f (float): Coolant effective thermal conductivity [W/(m*K)]
        dT_f_dn (float): Fluid normal temperature gradient [K/m]
        R_tc (float): Thermal contact resistance [m^2*K/W] (default: 0.0)
        T_b (float, optional): Battery surface temperature [K]
        T_f (float, optional): Fluid surface temperature [K]
    """
    if k_b <= 0 or k_f <= 0:
        raise ValueError("Conductivity values must be strictly positive.")

    # Battery heat flux entering interface [W/m^2]
    q_b = -k_b * dT_b_dn
    # Fluid heat flux leaving interface [W/m^2]
    q_f = -k_f * dT_f_dn

    if R_tc > 0.0:
        if T_b is None or T_f is None:
            raise ValueError("T_b and T_f are required when thermal contact resistance R_tc > 0.")
        q_contact = (T_b - T_f) / R_tc
        flux_discrepancy = abs(q_b - q_contact) + abs(q_f - q_contact)
        model_desc = f"Interface includes thermal contact resistance R_tc = {R_tc:.4e} m^2*K/W."
    else:
        q_contact = q_b
        flux_discrepancy = abs(q_b - q_f)
        model_desc = "Ideal thermal contact interface (R_tc = 0 m^2*K/W)."

    interpretation = (
        f"Battery interface heat flux: q''_b = {q_b:.2f} W/m^2, Coolant flux: q''_f = {q_f:.2f} W/m^2. "
        f"Discrepancy = {flux_discrepancy:.4e} W/m^2. {model_desc}"
    )

    return {
        "formula_name": "Heat Flux Continuity at Interface",
        "equation": "-k_b * (dT_b/dn) = -k_f * (dT_f/dn) [Ideal] or (T_b - T_f)/R_tc [With Contact Resistance]",
        "inputs": {
            "k_b": (k_b, "W/(m*K)"),
            "dT_b_dn": (dT_b_dn, "K/m"),
            "k_f": (k_f, "W/(m*K)"),
            "dT_f_dn": (dT_f_dn, "K/m"),
            "R_tc": (R_tc, "m^2*K/W"),
        },
        "intermediates": {
            "battery_heat_flux": (q_b, "W/m^2"),
            "fluid_heat_flux": (q_f, "W/m^2"),
            "contact_layer_heat_flux": (q_contact, "W/m^2"),
        },
        "result_flux": q_b,
        "result": flux_discrepancy,
        "unit": "W/m^2",
        "interpretation": interpretation,
    }


def compute_harmonic_interface_conductivity(
    k_battery: float,
    k_fluid: float,
    dy_b: float,
    dy_f: float,
    R_tc: float = 0.0
) -> float:
    """
    Computes effective harmonic mean interface thermal conductance for finite difference:
    k_interface = (dy_b + dy_f) / (dy_b / k_b + dy_f / k_f + R_tc)  [W/(m*K)]
    """
    thermal_resistance = (dy_b / (2.0 * k_battery)) + (dy_f / (2.0 * k_fluid)) + R_tc
    dy_total = 0.5 * (dy_b + dy_f)
    return float(dy_total / thermal_resistance)
