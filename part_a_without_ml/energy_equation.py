"""
Energy Equation Module for Hybrid Nanofluid BTMS
Implements Formulation 1:
(rho Cp)_eff [dT/dt + u(dT/dx) + v(dT/dy)] = k_eff (d^2T/dx^2 + d^2T/dy^2) + Q_b + Q_visc + Q_J
"""

import numpy as np
from typing import Dict, Union, Tuple, Optional


def calc_energy_equation_terms(
    rho_cp_eff: float,
    k_eff: float,
    u: float,
    v: float,
    dT_dx: float,
    dT_dy: float,
    d2T_dx2: float,
    d2T_dy2: float,
    Q_b: float = 0.0,
    Q_visc: float = 0.0,
    Q_J: float = 0.0
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 1: Local Energy Equation Term Breakdown and dT/dt Calculation.
    
    (rho Cp)_eff * dT/dt = k_eff * (d^2T/dx^2 + d^2T/dy^2) 
                           - (rho Cp)_eff * (u*dT/dx + v*dT/dy) 
                           + Q_b + Q_visc + Q_J
                           
    Parameters:
        rho_cp_eff (float): Effective volumetric heat capacity [J/(m^3*K)]
        k_eff (float): Effective thermal conductivity [W/(m*K)]
        u (float): X-velocity [m/s]
        v (float): Y-velocity [m/s]
        dT_dx (float): Temperature gradient in X [K/m]
        dT_dy (float): Temperature gradient in Y [K/m]
        d2T_dx2 (float): Second derivative in X [K/m^2]
        d2T_dy2 (float): Second derivative in Y [K/m^2]
        Q_b (float): Battery heat generation term [W/m^3]
        Q_visc (float): Viscous dissipation [W/m^3]
        Q_J (float): Joule heating [W/m^3]
    """
    if rho_cp_eff <= 0.0:
        raise ValueError("Effective volumetric heat capacity must be strictly positive.")

    # Convective transport term [W/m^3]
    convection = rho_cp_eff * (u * dT_dx + v * dT_dy)

    # Thermal conduction diffusion term [W/m^3]
    laplacian_T = d2T_dx2 + d2T_dy2
    conduction = k_eff * laplacian_T

    # Total volumetric source term [W/m^3]
    source_total = Q_b + Q_visc + Q_J

    # Rate of change of temperature dT/dt [K/s]
    # (rho Cp)_eff * dT/dt = conduction - convection + source_total
    net_heat_rate = conduction - convection + source_total
    dT_dt = net_heat_rate / rho_cp_eff

    interpretation = (
        f"Local energy rate dT/dt is {dT_dt:.4e} K/s. "
        f"Conduction: {conduction:.2f} W/m^3, Convection: -{convection:.2f} W/m^3, "
        f"Sources: Q_b = {Q_b:.2f} W/m^3, Q_visc = {Q_visc:.4e} W/m^3, Q_J = {Q_J:.4e} W/m^3."
    )

    return {
        "formula_name": "Hybrid Nanofluid Energy Equation",
        "equation": "(rho Cp)_eff [dT/dt + u(dT/dx) + v(dT/dy)] = k_eff (d^2T/dx^2 + d^2T/dy^2) + Q_b + Q_visc + Q_J",
        "inputs": {
            "rho_cp_eff": (rho_cp_eff, "J/(m^3*K)"),
            "k_eff": (k_eff, "W/(m*K)"),
            "u": (u, "m/s"),
            "v": (v, "m/s"),
            "dT_dx": (dT_dx, "K/m"),
            "dT_dy": (dT_dy, "K/m"),
            "d2T_dx2": (d2T_dx2, "K/m^2"),
            "d2T_dy2": (d2T_dy2, "K/m^2"),
            "Q_b": (Q_b, "W/m^3"),
            "Q_visc": (Q_visc, "W/m^3"),
            "Q_J": (Q_J, "W/m^3"),
        },
        "intermediates": {
            "convective_heat_flux": (convection, "W/m^3"),
            "conductive_heat_flux": (conduction, "W/m^3"),
            "total_heat_source": (source_total, "W/m^3"),
            "net_volumetric_heating": (net_heat_rate, "W/m^3"),
        },
        "result": dT_dt,
        "unit": "K/s",
        "interpretation": interpretation,
    }


def calc_viscous_dissipation_2d(
    mu_eff: float,
    du_dx: float,
    du_dy: float,
    dv_dx: float,
    dv_dy: float
) -> float:
    """
    Computes viscous dissipation in 2D incompressible fluid flow:
    Q_visc = mu_eff * [2*(du/dx)^2 + 2*(dv/dy)^2 + (du/dy + dv/dx)^2]  [W/m^3]
    """
    term_normal = 2.0 * (du_dx ** 2) + 2.0 * (dv_dy ** 2)
    term_shear = (du_dy + dv_dx) ** 2
    return float(mu_eff * (term_normal + term_shear))


def simulate_1d_transient_temperature(
    t_span: float = 600.0,
    Nt: int = 100,
    T_init: float = 300.0,
    T_in: float = 298.15,
    u_avg: float = 0.05,
    L: float = 0.15,
    rho_cp_eff: float = 4.0e6,
    k_eff: float = 0.65,
    q_b_vol: float = 50000.0,
    Q_J: float = 0.0,
    Q_visc: float = 0.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simulates transient battery and coolant temperature variation over time t in [0, t_span].
    Returns (times, temperatures).
    """
    times = np.linspace(0.0, t_span, Nt)
    # Lumped-transient coupled thermal balance
    # rho_cp * dT/dt = q_b_vol - (h_eff * A / V)*(T - T_in) + Q_J + Q_visc
    # Effective convection coefficient h_eff from Graetz / channel flow
    h_eff = 2.0 * k_eff / 0.01  # approx 130 W/(m^2*K)
    tau = rho_cp_eff * 0.01 / h_eff # thermal time constant [s]
    
    T_steady = T_in + (q_b_vol + Q_J + Q_visc) * 0.01 / h_eff
    temperatures = T_steady + (T_init - T_steady) * np.exp(-times / tau)
    return times, temperatures
