"""
Dimensionless Numbers and Electrochemical Formulations
Implements Formulations 3, 4, 5, 6, 7, 8, and 9 for BTMS Hybrid Nanofluid Simulation.
"""

import numpy as np
from typing import Dict, Union, List, Optional


# ==============================================================================
# FORMULA 3: Reynolds Number
# ==============================================================================
def calc_reynolds_number(
    rho_hnf: float,
    U_in: float,
    L: float,
    mu_eff: float
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 3: Reynolds Number.
    Re = (rho_hnf * U_in * L) / mu_eff
    
    Parameters:
        rho_hnf (float): Effective hybrid nanofluid density [kg/m^3]
        U_in (float): Coolant inlet velocity [m/s]
        L (float): Characteristic length (e.g. channel hydraulic diameter) [m]
        mu_eff (float): Effective dynamic viscosity [Pa*s]
        
    Returns:
        Dict: Calculation record including interpretation of inertial vs viscous forces.
    """
    if mu_eff <= 0.0:
        raise ValueError("Effective viscosity mu_eff must be strictly positive to avoid division by zero.")
    if L <= 0.0:
        raise ValueError("Characteristic length L must be strictly positive.")
    if rho_hnf <= 0.0:
        raise ValueError("Fluid density must be strictly positive.")

    Re = (rho_hnf * U_in * L) / mu_eff

    if Re < 2300.0:
        regime = "Laminar flow (viscous forces dominate, stable boundary layers, no turbulent mixing)"
    elif Re <= 4000.0:
        regime = "Transitional flow regime (intermittent turbulent bursts)"
    else:
        regime = "Turbulent flow (inertial forces dominate, chaotic eddy diffusivity)"

    interpretation = (
        f"Reynolds number is {Re:.2f}. Flow is in the {regime}. "
        f"The ratio of inertial to viscous forces indicates the stability of the hydrodynamic boundary layer."
    )

    return {
        "formula_name": "Reynolds Number",
        "equation": "Re = (rho_hnf * U_in * L) / mu_eff",
        "inputs": {
            "rho_hnf": (rho_hnf, "kg/m^3"),
            "U_in": (U_in, "m/s"),
            "L": (L, "m"),
            "mu_eff": (mu_eff, "Pa*s"),
        },
        "intermediates": {
            "momentum_flux_scale": (rho_hnf * (U_in ** 2), "N/m^2"),
            "viscous_shear_scale": (mu_eff * U_in / L, "N/m^2"),
        },
        "result": Re,
        "unit": "dimensionless",
        "interpretation": interpretation,
    }


# ==============================================================================
# FORMULA 4: Prandtl Number
# ==============================================================================
def calc_prandtl_number(
    mu_eff: float,
    Cp_hnf: float,
    k_eff: float
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 4: Prandtl Number.
    Pr = (mu_eff * Cp_hnf) / k_eff
    
    IMPORTANT:
    Uses mass-specific heat capacity Cp_hnf in [J/(kg*K)], NOT volumetric heat capacity.
    
    Parameters:
        mu_eff (float): Effective dynamic viscosity [Pa*s or kg/(m*s)]
        Cp_hnf (float): Mass-specific heat capacity [J/(kg*K)]
        k_eff (float): Effective thermal conductivity [W/(m*K)]
    """
    if k_eff <= 0.0:
        raise ValueError("Thermal conductivity k_eff must be strictly positive to avoid division by zero.")
    if mu_eff <= 0.0 or Cp_hnf <= 0.0:
        raise ValueError("Viscosity and specific heat must be strictly positive.")

    Pr = (mu_eff * Cp_hnf) / k_eff

    # Physical interpretation: ratio of momentum diffusivity (nu = mu/rho) to thermal diffusivity (alpha = k/(rho*Cp))
    interpretation = (
        f"Prandtl number is {Pr:.2f}. Since Pr > 1, momentum diffusivity (kinematic viscosity) "
        f"diffuses faster than thermal diffusivity. Consequently, the hydrodynamic boundary layer "
        f"is thicker than the thermal boundary layer (delta_h / delta_t ~ Pr^(1/3) = {Pr**(1/3):.2f})."
    )

    return {
        "formula_name": "Prandtl Number",
        "equation": "Pr = (mu_eff * Cp_hnf) / k_eff",
        "inputs": {
            "mu_eff": (mu_eff, "Pa*s"),
            "Cp_hnf": (Cp_hnf, "J/(kg*K)"),
            "k_eff": (k_eff, "W/(m*K)"),
        },
        "intermediates": {
            "viscous_heat_capacity_product": (mu_eff * Cp_hnf, "W/(m*K)"),
            "boundary_layer_thickness_ratio_estimate": (Pr ** (1.0 / 3.0), "dimensionless"),
        },
        "result": Pr,
        "unit": "dimensionless",
        "interpretation": interpretation,
    }


# ==============================================================================
# FORMULA 5: Hartmann Number
# ==============================================================================
def calc_hartmann_number(
    B0: float,
    L: float,
    sigma_hnf: float,
    mu_eff: float
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 5: Hartmann Number.
    Ha = B0 * L * sqrt(sigma_hnf / mu_eff)
    
    Parameters:
        B0 (float): Magnetic flux density [T]
        L (float): Characteristic length [m]
        sigma_hnf (float): Effective electrical conductivity [S/m]
        mu_eff (float): Effective dynamic viscosity [Pa*s]
    """
    if mu_eff <= 0.0:
        raise ValueError("Effective viscosity mu_eff must be strictly positive.")
    if sigma_hnf < 0.0:
        raise ValueError("Electrical conductivity must be non-negative.")
    if B0 < 0.0:
        raise ValueError("Magnetic field B0 must be non-negative.")

    sqrt_ratio = float(np.sqrt(sigma_hnf / mu_eff))
    Ha = B0 * L * sqrt_ratio

    if Ha == 0.0:
        influence = "No magnetic field applied (Ha = 0). Flow is pure hydrodynamic Darcy-Brinkman flow."
    elif Ha < 1.0:
        influence = "Weak magnetic damping (Ha < 1). Viscous forces dominate over magnetic Lorentz retarding forces."
    elif Ha <= 10.0:
        influence = "Moderate MHD effect (1 <= Ha <= 10). Lorentz force flattens the channel core velocity profile (Hartmann flow)."
    else:
        influence = "Strong MHD damping (Ha > 10). Intense Lorentz retarding force creates thin Hartmann boundary layers (delta_Ha ~ L/Ha) and increases pressure drop."

    interpretation = f"Hartmann number is {Ha:.4f}. {influence}"

    return {
        "formula_name": "Hartmann Number",
        "equation": "Ha = B0 * L * sqrt(sigma_hnf / mu_eff)",
        "inputs": {
            "B0": (B0, "T"),
            "L": (L, "m"),
            "sigma_hnf": (sigma_hnf, "S/m"),
            "mu_eff": (mu_eff, "Pa*s"),
        },
        "intermediates": {
            "sqrt_sigma_over_mu": (sqrt_ratio, "m^(-1)*T^(-1)"),
            "lorentz_to_viscous_force_ratio_Ha2": (Ha ** 2, "dimensionless"),
        },
        "result": Ha,
        "unit": "dimensionless",
        "interpretation": interpretation,
    }


# ==============================================================================
# FORMULA 6: Darcy Number
# ==============================================================================
def calc_darcy_number(
    k_perm: float,
    L: float
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 6: Darcy Number.
    Da = k / L^2
    
    Parameters:
        k_perm (float): Porous medium permeability k [m^2]
        L (float): Characteristic length [m]
    """
    if L <= 0.0:
        raise ValueError("Characteristic length L must be strictly positive.")
    if k_perm <= 0.0:
        raise ValueError("Permeability k must be strictly positive.")

    Da = k_perm / (L ** 2)

    if Da < 1.0e-5:
        influence = "Extremely low permeability (Da << 10^-5). Darcy drag completely dominates momentum diffusion."
    elif Da < 1.0e-3:
        influence = "Moderate permeability porous medium (10^-5 <= Da <= 10^-3). Significant porous flow resistance."
    else:
        influence = "High permeability (Da > 10^-3). Brinkman viscous shearing and open-channel fluid effects are prominent."

    interpretation = (
        f"Darcy number is {Da:.4e}. {influence} "
        f"Da represents the ratio of porous medium permeability to cross-sectional area."
    )

    return {
        "formula_name": "Darcy Number",
        "equation": "Da = k / L^2",
        "inputs": {
            "k_perm": (k_perm, "m^2"),
            "L": (L, "m"),
        },
        "intermediates": {
            "L_squared": (L ** 2, "m^2"),
        },
        "result": Da,
        "unit": "dimensionless",
        "interpretation": interpretation,
    }


# ==============================================================================
# FORMULA 7: Brinkman Number
# ==============================================================================
def calc_brinkman_number(
    mu_eff: float,
    U_in: float,
    k_eff: float,
    Delta_T: float
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 7: Brinkman Number.
    Br = (mu_eff * U_in^2) / (k_eff * Delta_T)
    
    Parameters:
        mu_eff (float): Effective dynamic viscosity [Pa*s]
        U_in (float): Coolant inlet velocity [m/s]
        k_eff (float): Effective thermal conductivity [W/(m*K)]
        Delta_T (float): Characteristic temperature difference (e.g., T_wall - T_in) [K]
        
    Note:
        Delta_T must be strictly positive (nonzero) to avoid division by zero.
    """
    if abs(Delta_T) < 1.0e-6:
        raise ValueError(f"Delta_T must be nonzero (got {Delta_T:.6f} K) to avoid division by zero in Brinkman number.")
    if k_eff <= 0.0:
        raise ValueError("Thermal conductivity k_eff must be strictly positive.")

    Delta_T_abs = abs(Delta_T)
    Br = (mu_eff * (U_in ** 2)) / (k_eff * Delta_T_abs)

    if Br < 1.0e-3:
        influence = "Negligible viscous heating (Br << 1). Heat transfer is overwhelmingly governed by battery heat conduction and convection."
    elif Br < 0.1:
        influence = "Minor viscous dissipation. Viscous shear produces small local heating in boundary layers."
    else:
        influence = "Noticeable viscous heating (Br >= 0.1). Viscous dissipation significantly alters temperature profile."

    interpretation = (
        f"Brinkman number is {Br:.6e} with characteristic Delta_T = {Delta_T_abs:.2f} K. "
        f"{influence} Br gauges the ratio of viscous heat dissipation to molecular heat conduction."
    )

    return {
        "formula_name": "Brinkman Number",
        "equation": "Br = (mu_eff * U_in^2) / (k_eff * Delta_T)",
        "inputs": {
            "mu_eff": (mu_eff, "Pa*s"),
            "U_in": (U_in, "m/s"),
            "k_eff": (k_eff, "W/(m*K)"),
            "Delta_T": (Delta_T_abs, "K"),
        },
        "intermediates": {
            "viscous_dissipation_scale": (mu_eff * (U_in ** 2), "W/m"),
            "conduction_scale": (k_eff * Delta_T_abs, "W/m"),
        },
        "result": Br,
        "unit": "dimensionless",
        "interpretation": interpretation,
    }


# ==============================================================================
# FORMULA 8: Nusselt Number
# ==============================================================================
def calc_nusselt_number(
    h: float,
    L: float,
    k_eff: float
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 8a: Average / Global Nusselt Number from heat transfer coefficient.
    Nu = (h * L) / k_eff
    
    Parameters:
        h (float): Convective heat transfer coefficient [W/(m^2*K)]
        L (float): Characteristic length [m]
        k_eff (float): Effective thermal conductivity [W/(m*K)]
    """
    if k_eff <= 0.0:
        raise ValueError("Thermal conductivity k_eff must be strictly positive.")
    if L <= 0.0:
        raise ValueError("Characteristic length L must be strictly positive.")

    Nu = (h * L) / k_eff

    interpretation = (
        f"Nusselt number is {Nu:.2f}. Convective heat transfer is {Nu:.2f} times "
        f"more effective than pure stagnant molecular conduction across length L = {L:.3f} m."
    )

    return {
        "formula_name": "Nusselt Number (Convective)",
        "equation": "Nu = (h * L) / k_eff",
        "inputs": {
            "h": (h, "W/(m^2*K)"),
            "L": (L, "m"),
            "k_eff": (k_eff, "W/(m*K)"),
        },
        "intermediates": {
            "convective_conductance_scale": (h * L, "W/(m*K)"),
        },
        "result": Nu,
        "unit": "dimensionless",
        "interpretation": interpretation,
    }


def calc_local_nusselt_number(
    dT_dn_wall: Union[float, np.ndarray],
    L: float,
    T_w: Union[float, np.ndarray],
    T_in: float
) -> Dict[str, Union[float, np.ndarray, str]]:
    """
    FORMULA 8b: Local Nusselt number from spatial wall temperature gradient.
    Nu_local = -L / (T_w - T_in) * (dT/dn)_wall
    
    Parameters:
        dT_dn_wall (float or np.ndarray): Temperature gradient normal to the wall [K/m].
        L (float): Characteristic length [m].
        T_w (float or np.ndarray): Wall surface temperature [K].
        T_in (float): Coolant inlet temperature [K].
    """
    delta_T = np.maximum(np.abs(np.array(T_w) - T_in), 1.0e-5)
    Nu_local = - (L / delta_T) * np.array(dT_dn_wall)

    # Average if array provided
    if isinstance(Nu_local, np.ndarray):
        Nu_avg = float(np.mean(Nu_local))
    else:
        Nu_avg = float(Nu_local)

    interpretation = (
        f"Average Nusselt number from wall thermal gradient is {Nu_avg:.2f}. "
        f"Wall normal gradient dT/dn directly dictates the interface cooling flux."
    )

    return {
        "formula_name": "Local and Average Nusselt Number (Gradient Formulation)",
        "equation": "Nu_local = -L / (T_w - T_in) * (dT/dn)_wall",
        "inputs": {
            "L": (L, "m"),
            "T_in": (T_in, "K"),
        },
        "result_local": Nu_local,
        "result": Nu_avg,
        "unit": "dimensionless",
        "interpretation": interpretation,
    }


# ==============================================================================
# FORMULA 9: C-Rate and Battery Current
# ==============================================================================
def calc_c_rate_current(
    c_rate: float,
    Q_rated: float
) -> Dict[str, Union[float, str, Dict[str, float]]]:
    """
    FORMULA 9: Battery Current from C-Rate.
    I = C_rate * Q_rated
    
    Parameters:
        c_rate (float): Charging or discharging C-rate [1/h or dimensionless C]
        Q_rated (float): Rated battery capacity [Ah]
        
    Calculates current for the specified C-rate, as well as benchmark values:
    0.5C, 1.0C, 2.0C, 3.0C.
    """
    if Q_rated <= 0.0:
        raise ValueError("Rated battery capacity Q_rated must be strictly positive.")
    if c_rate < 0.0:
        raise ValueError("C-rate must be non-negative.")

    I = c_rate * Q_rated

    # Benchmark standard C-rates
    benchmarks = {
        "0.5C": 0.5 * Q_rated,
        "1.0C": 1.0 * Q_rated,
        "2.0C": 2.0 * Q_rated,
        "3.0C": 3.0 * Q_rated,
    }

    interpretation = (
        f"For a battery capacity of {Q_rated:.1f} Ah at {c_rate:.2f}C, the operating current is {I:.2f} A. "
        f"Benchmark discharge currents: 0.5C = {benchmarks['0.5C']:.1f} A, 1.0C = {benchmarks['1.0C']:.1f} A, "
        f"2.0C = {benchmarks['2.0C']:.1f} A, 3.0C = {benchmarks['3.0C']:.1f} A."
    )

    return {
        "formula_name": "C-Rate Battery Current",
        "equation": "I = C_rate * Q_rated",
        "inputs": {
            "c_rate": (c_rate, "dimensionless C (1/h)"),
            "Q_rated": (Q_rated, "Ah"),
        },
        "intermediates": {
            "standard_benchmark_currents_amperes": benchmarks,
        },
        "result": I,
        "unit": "A",
        "interpretation": interpretation,
    }
