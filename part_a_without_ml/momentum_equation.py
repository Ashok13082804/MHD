"""
Darcy-Brinkman MHD Momentum Equation Module
Implements Formulation 2:
rho_hnf [dV/dt + (V . grad)V] = -grad(p) + mu_eff Laplacian(V) - (mu_eff/k)V + J x B
"""

import numpy as np
from typing import Dict, Union, Tuple, Optional


def calc_momentum_balance_2d(
    rho_hnf: float,
    mu_eff: float,
    k_perm: float,
    sigma_hnf: float,
    B0: float,
    u: float,
    v: float,
    dp_dx: float,
    dp_dy: float,
    d2u_dx2: float,
    d2u_dy2: float,
    d2v_dx2: float,
    d2v_dy2: float,
    du_dx: float,
    du_dy: float,
    dv_dx: float,
    dv_dy: float
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 2: 2D Darcy-Brinkman MHD Momentum Equation Evaluation.
    Calculates component accelerations, viscous forces, porous resistance, and Lorentz forces.
    
    X-Momentum:
    rho_hnf * du/dt = -dp/dx + mu_eff*(d2u/dx2 + d2u/dy2) - (mu_eff/k)*u - sigma_hnf*B0^2*u - rho_hnf*(u*du/dx + v*du/dy)
    
    Y-Momentum:
    rho_hnf * dv/dt = -dp/dy + mu_eff*(d2v/dx2 + d2v/dy2) - (mu_eff/k)*v - rho_hnf*(u*dv/dx + v*dv/dy)
    """
    if k_perm <= 0.0:
        raise ValueError("Permeability k must be strictly positive.")
    if rho_hnf <= 0.0 or mu_eff <= 0.0:
        raise ValueError("Density and viscosity must be strictly positive.")

    # Inertial convection terms [N/m^3]
    inertia_x = rho_hnf * (u * du_dx + v * du_dy)
    inertia_y = rho_hnf * (u * dv_dx + v * dv_dy)

    # Pressure forces [N/m^3]
    pressure_x = -dp_dx
    pressure_y = -dp_dy

    # Brinkman viscous laplacian forces [N/m^3]
    viscous_x = mu_eff * (d2u_dx2 + d2u_dy2)
    viscous_y = mu_eff * (d2v_dx2 + d2v_dy2)

    # Darcy porous medium resistance [N/m^3]
    porous_drag_x = -(mu_eff / k_perm) * u
    porous_drag_y = -(mu_eff / k_perm) * v

    # Lorentz electromagnetic body force [N/m^3] (transverse field B = (0, B0, 0))
    lorentz_x = -sigma_hnf * (B0 ** 2) * u
    lorentz_y = 0.0

    # Net acceleration [m/s^2]
    net_force_x = pressure_x + viscous_x + porous_drag_x + lorentz_x - inertia_x
    net_force_y = pressure_y + viscous_y + porous_drag_y + lorentz_y - inertia_y
    du_dt = net_force_x / rho_hnf
    dv_dt = net_force_y / rho_hnf

    interpretation = (
        f"Momentum balance results: du/dt = {du_dt:.4e} m/s^2, dv/dt = {dv_dt:.4e} m/s^2. "
        f"X-forces per unit volume: Pressure = {pressure_x:.2f} N/m^3, Viscous = {viscous_x:.2f} N/m^3, "
        f"Porous resistance = {porous_drag_x:.2f} N/m^3, Lorentz force = {lorentz_x:.2f} N/m^3."
    )

    return {
        "formula_name": "Darcy-Brinkman MHD Momentum Equation",
        "equation": "rho_hnf [dV/dt + (V.grad)V] = -grad(p) + mu_eff*Laplacian(V) - (mu_eff/k)*V + J x B",
        "inputs": {
            "rho_hnf": (rho_hnf, "kg/m^3"),
            "mu_eff": (mu_eff, "Pa*s"),
            "k_perm": (k_perm, "m^2"),
            "sigma_hnf": (sigma_hnf, "S/m"),
            "B0": (B0, "T"),
            "u": (u, "m/s"),
            "v": (v, "m/s"),
        },
        "intermediates": {
            "pressure_gradient_x": (pressure_x, "N/m^3"),
            "pressure_gradient_y": (pressure_y, "N/m^3"),
            "viscous_resistance_x": (viscous_x, "N/m^3"),
            "viscous_resistance_y": (viscous_y, "N/m^3"),
            "porous_medium_resistance_x": (porous_drag_x, "N/m^3"),
            "porous_medium_resistance_y": (porous_drag_y, "N/m^3"),
            "magnetic_lorentz_force_x": (lorentz_x, "N/m^3"),
            "magnetic_lorentz_force_y": (lorentz_y, "N/m^3"),
            "inertial_convection_x": (inertia_x, "N/m^3"),
            "inertial_convection_y": (inertia_y, "N/m^3"),
        },
        "result_u_acceleration": du_dt,
        "result_v_acceleration": dv_dt,
        "result": net_force_x,
        "unit": "N/m^3",
        "interpretation": interpretation,
    }


def calc_darcy_brinkman_mhd_channel_profile(
    U_in: float,
    H: float,
    L: float,
    mu_eff: float,
    k_perm: float,
    sigma_hnf: float,
    B0: float,
    Ny: int = 100
) -> Tuple[np.ndarray, np.ndarray, float, np.ndarray]:
    """
    Computes exact fully developed velocity profile u(y), pressure gradient G,
    and pressure distribution p(x) for Darcy-Brinkman MHD channel flow.
    
    Governing ODE:
    mu_eff * d2u/dy2 - (mu_eff/k + sigma_hnf*B0^2)*u = dp/dx = -G
    
    Boundary conditions:
    u(0) = 0, u(H) = 0 (No-slip walls)
    """
    y = np.linspace(0, H, Ny)
    # Effective damping parameter lambda^2 = 1/k + (sigma*B0^2)/mu_eff
    lambda_sq = (1.0 / k_perm) + (sigma_hnf * (B0 ** 2)) / mu_eff
    lam = np.sqrt(lambda_sq)

    arg = lam * H / 2.0
    # Avoid numerical overflow for large arg
    if arg > 50.0:
        integral_factor = 1.0 - (1.0 / arg)
    else:
        integral_factor = 1.0 - (np.tanh(arg) / arg)

    # Required pressure gradient G = -dp/dx [Pa/m]
    G = (U_in * mu_eff * lambda_sq) / max(integral_factor, 1.0e-9)

    # Velocity profile across channel height
    if arg > 50.0:
        u_profile = (G / (mu_eff * lambda_sq)) * (1.0 - np.exp(-lam * np.minimum(y, H - y)))
    else:
        u_profile = (G / (mu_eff * lambda_sq)) * (1.0 - np.cosh(lam * (y - H / 2.0)) / np.cosh(arg))

    # Pressure distribution along channel length L (p_out = 0 gauge at exit x = L)
    x = np.linspace(0, L, 50)
    p_profile = G * (L - x)

    return y, u_profile, G, p_profile
