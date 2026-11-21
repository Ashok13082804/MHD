"""
Material Properties and Thermophysical Formulations for BTMS Hybrid Nanofluid
Implements Formulations 13, 14, 15, 16, 17, 18, Effective Heat Capacity, and Battery Heat Generation.
"""

import numpy as np
from typing import Dict, Tuple, Optional, Union


# ==============================================================================
# FORMULA 14: Fluid and Nanoparticle Density Definitions & Validation
# ==============================================================================
def validate_nanoparticle_volume_fractions(phi1: float, phi2: float) -> Tuple[bool, str]:
    """
    Validates nanoparticle volume fractions according to physical constraints:
    phi1 >= 0, phi2 >= 0, phi1 + phi2 < 1.0.
    
    Parameters:
        phi1 (float): Volume fraction of nanoparticle 1 (e.g. Al2O3).
        phi2 (float): Volume fraction of nanoparticle 2 (e.g. CuO).
        
    Returns:
        Tuple[bool, str]: (is_valid, message).
    """
    if phi1 < 0.0:
        return False, f"Invalid phi1 = {phi1}: Volume fraction of nanoparticle 1 must be non-negative."
    if phi2 < 0.0:
        return False, f"Invalid phi2 = {phi2}: Volume fraction of nanoparticle 2 must be non-negative."
    if (phi1 + phi2) >= 1.0:
        return False, f"Invalid total concentration phi1 + phi2 = {phi1 + phi2:.4f}: Total volume fraction must be strictly less than 1.0."
    return True, "Volume fractions are physically valid."


# ==============================================================================
# FORMULA 13: Effective Hybrid Nanofluid Density
# ==============================================================================
def calc_effective_density(
    rho_f: float,
    rho_s1: float,
    rho_s2: float,
    phi1: float,
    phi2: float
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 13: Hybrid Nanofluid Effective Density.
    rho_hnf = (1 - phi1 - phi2) * rho_f + phi1 * rho_s1 + phi2 * rho_s2
    
    Parameters:
        rho_f (float): Base fluid density [kg/m^3]
        rho_s1 (float): Nanoparticle 1 (Al2O3) density [kg/m^3]
        rho_s2 (float): Nanoparticle 2 (CuO) density [kg/m^3]
        phi1 (float): Nanoparticle 1 volume fraction [-]
        phi2 (float): Nanoparticle 2 volume fraction [-]
        
    Returns:
        Dict: Complete calculation details, intermediate terms, result, and interpretation.
    """
    is_valid, msg = validate_nanoparticle_volume_fractions(phi1, phi2)
    if not is_valid:
        raise ValueError(msg)
    if rho_f <= 0 or rho_s1 <= 0 or rho_s2 <= 0:
        raise ValueError("Density values must be strictly positive.")

    # Intermediate terms
    term_fluid = (1.0 - phi1 - phi2) * rho_f
    term_s1 = phi1 * rho_s1
    term_s2 = phi2 * rho_s2
    rho_hnf = term_fluid + term_s1 + term_s2

    interpretation = (
        f"Hybrid nanofluid density is {rho_hnf:.2f} kg/m^3 (increase of "
        f"{((rho_hnf / rho_f) - 1.0) * 100:.2f}% over base fluid {rho_f:.2f} kg/m^3) "
        f"due to dispersed high-density nanoparticles."
    )

    return {
        "formula_name": "Effective Hybrid Nanofluid Density",
        "equation": "rho_hnf = (1 - phi1 - phi2)*rho_f + phi1*rho_s1 + phi2*rho_s2",
        "inputs": {
            "rho_f": (rho_f, "kg/m^3"),
            "rho_s1": (rho_s1, "kg/m^3"),
            "rho_s2": (rho_s2, "kg/m^3"),
            "phi1": (phi1, "dimensionless"),
            "phi2": (phi2, "dimensionless"),
        },
        "intermediates": {
            "fluid_mass_fraction_term": (term_fluid, "kg/m^3"),
            "nanoparticle_1_term": (term_s1, "kg/m^3"),
            "nanoparticle_2_term": (term_s2, "kg/m^3"),
            "total_particle_volume_fraction": (phi1 + phi2, "dimensionless"),
        },
        "result": rho_hnf,
        "unit": "kg/m^3",
        "interpretation": interpretation,
    }


# ==============================================================================
# SECTION 3: Effective Volumetric and Mass-Specific Heat Capacity
# ==============================================================================
def calc_effective_heat_capacity(
    rho_f: float,
    cp_f: float,
    rho_s1: float,
    cp_s1: float,
    rho_s2: float,
    cp_s2: float,
    phi1: float,
    phi2: float
) -> Dict[str, Union[float, str]]:
    """
    SECTION 3: Effective Heat Capacity of Hybrid Nanofluid.
    Volumetric: (rho*Cp)_hnf = (1 - phi1 - phi2)*(rho*Cp)_f + phi1*(rho*Cp)_s1 + phi2*(rho*Cp)_s2 [J/(m^3*K)]
    Mass-specific: Cp_hnf = (rho*Cp)_hnf / rho_hnf [J/(kg*K)]
    """
    is_valid, msg = validate_nanoparticle_volume_fractions(phi1, phi2)
    if not is_valid:
        raise ValueError(msg)

    # Volumetric heat capacities
    vol_cap_f = rho_f * cp_f
    vol_cap_s1 = rho_s1 * cp_s1
    vol_cap_s2 = rho_s2 * cp_s2

    term_f = (1.0 - phi1 - phi2) * vol_cap_f
    term_s1 = phi1 * vol_cap_s1
    term_s2 = phi2 * vol_cap_s2
    rho_cp_hnf = term_f + term_s1 + term_s2

    # Density to get mass-specific Cp
    rho_hnf_data = calc_effective_density(rho_f, rho_s1, rho_s2, phi1, phi2)
    rho_hnf = rho_hnf_data["result"]
    cp_hnf = rho_cp_hnf / rho_hnf

    interpretation = (
        f"Volumetric heat capacity is {rho_cp_hnf:.2f} J/(m^3*K). "
        f"Mass-specific heat capacity is {cp_hnf:.2f} J/(kg*K), which is slightly lower than "
        f"pure water ({cp_f:.2f} J/(kg*K)) because solid metal oxides possess lower specific heat."
    )

    return {
        "formula_name": "Effective Heat Capacity (Volumetric and Mass-Specific)",
        "equation": "(rho*Cp)_hnf = (1 - phi1 - phi2)*(rho*Cp)_f + phi1*(rho*Cp)_s1 + phi2*(rho*Cp)_s2; Cp_hnf = (rho*Cp)_hnf / rho_hnf",
        "inputs": {
            "rho_f": (rho_f, "kg/m^3"),
            "cp_f": (cp_f, "J/(kg*K)"),
            "rho_s1": (rho_s1, "kg/m^3"),
            "cp_s1": (cp_s1, "J/(kg*K)"),
            "rho_s2": (rho_s2, "kg/m^3"),
            "cp_s2": (cp_s2, "J/(kg*K)"),
            "phi1": (phi1, "dimensionless"),
            "phi2": (phi2, "dimensionless"),
        },
        "intermediates": {
            "base_fluid_vol_capacity": (vol_cap_f, "J/(m^3*K)"),
            "nanoparticle_1_vol_capacity": (vol_cap_s1, "J/(m^3*K)"),
            "nanoparticle_2_vol_capacity": (vol_cap_s2, "J/(m^3*K)"),
            "effective_density": (rho_hnf, "kg/m^3"),
        },
        "result_volumetric": rho_cp_hnf,
        "result_specific": cp_hnf,
        "result": cp_hnf,
        "unit": "J/(kg*K)",
        "unit_volumetric": "J/(m^3*K)",
        "interpretation": interpretation,
    }


# ==============================================================================
# FORMULA 15: Effective Thermal Conductivity and Effective Dynamic Viscosity
# ==============================================================================
def calc_effective_thermal_conductivity(
    k_f: float,
    k_s1: float,
    k_s2: float,
    phi1: float,
    phi2: float,
    model: str = "maxwell"
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 15: Effective Thermal Conductivity of Hybrid Nanofluid.
    Implements the hybrid Maxwell formulation (Takabi & Salehi, Chamkha et al.):
    Let phi = phi1 + phi2.
    Composite solid conductivity: k_s = (phi1 * k_s1 + phi2 * k_s2) / phi (for phi > 0)
    k_hnf / k_f = [k_s + 2*k_f - 2*phi*(k_f - k_s)] / [k_s + 2*k_f + phi*(k_f - k_s)]
    
    Assumptions:
    - Dilute suspension of spherical nanoparticles.
    - Negligible interfacial thermal resistance (Kapitza resistance) at macro-continuum scale.
    - Maxwell's self-consistent field approximation for two dispersed solid phases.
    """
    is_valid, msg = validate_nanoparticle_volume_fractions(phi1, phi2)
    if not is_valid:
        raise ValueError(msg)
    if k_f <= 0 or k_s1 <= 0 or k_s2 <= 0:
        raise ValueError("Thermal conductivity values must be strictly positive.")

    phi = phi1 + phi2
    if phi == 0.0:
        k_hnf = k_f
        k_s = 0.0
    else:
        # Weighted solid conductivity
        k_s = (phi1 * k_s1 + phi2 * k_s2) / phi
        numerator = k_s + 2.0 * k_f - 2.0 * phi * (k_f - k_s)
        denominator = k_s + 2.0 * k_f + phi * (k_f - k_s)
        k_hnf = k_f * (numerator / denominator)

    enhancement = ((k_hnf / k_f) - 1.0) * 100.0
    interpretation = (
        f"Hybrid nanofluid thermal conductivity is {k_hnf:.4f} W/(m*K), an enhancement of "
        f"{enhancement:.2f}% relative to base fluid ({k_f:.4f} W/(m*K)). "
        f"Model used: Extended Maxwell model for hybrid suspensions."
    )

    return {
        "formula_name": "Effective Thermal Conductivity (Hybrid Maxwell Model)",
        "equation": "k_hnf = k_f * [k_s + 2*k_f - 2*phi*(k_f - k_s)] / [k_s + 2*k_f + phi*(k_f - k_s)]",
        "inputs": {
            "k_f": (k_f, "W/(m*K)"),
            "k_s1": (k_s1, "W/(m*K)"),
            "k_s2": (k_s2, "W/(m*K)"),
            "phi1": (phi1, "dimensionless"),
            "phi2": (phi2, "dimensionless"),
        },
        "intermediates": {
            "total_solid_volume_fraction": (phi, "dimensionless"),
            "equivalent_solid_conductivity": (k_s, "W/(m*K)"),
            "thermal_conductivity_ratio": (k_hnf / k_f, "dimensionless"),
        },
        "result": k_hnf,
        "unit": "W/(m*K)",
        "interpretation": interpretation,
    }


def calc_effective_dynamic_viscosity(
    mu_f: float,
    phi1: float,
    phi2: float,
    model: str = "brinkman"
) -> Dict[str, Union[float, str]]:
    """
    Effective Dynamic Viscosity of Hybrid Nanofluid.
    Brinkman Model: mu_hnf = mu_f / (1 - phi1 - phi2)^2.5
    Batchelor Model: mu_hnf = mu_f * (1 + 2.5*phi + 6.2*phi^2)
    
    Assumptions:
    - Spherical, non-aggregating nanoparticles in low-shear Newtonian flow.
    - Valid for moderate concentrations (phi < 0.10).
    """
    is_valid, msg = validate_nanoparticle_volume_fractions(phi1, phi2)
    if not is_valid:
        raise ValueError(msg)
    if mu_f <= 0:
        raise ValueError("Base fluid viscosity must be strictly positive.")

    phi = phi1 + phi2
    if phi == 0.0:
        mu_hnf = mu_f
    elif model.lower() == "brinkman":
        mu_hnf = mu_f / ((1.0 - phi) ** 2.5)
    elif model.lower() == "batchelor":
        mu_hnf = mu_f * (1.0 + 2.5 * phi + 6.2 * (phi ** 2))
    else:
        raise ValueError(f"Unknown viscosity model: {model}. Choose 'brinkman' or 'batchelor'.")

    increase = ((mu_hnf / mu_f) - 1.0) * 100.0
    interpretation = (
        f"Effective dynamic viscosity is {mu_hnf:.6e} Pa*s (increase of {increase:.2f}% "
        f"over base fluid {mu_f:.6e} Pa*s). "
        f"Model: {model.capitalize()} correlation."
    )

    return {
        "formula_name": f"Effective Dynamic Viscosity ({model.capitalize()} Model)",
        "equation": "mu_hnf = mu_f / (1 - phi)^2.5" if model.lower() == "brinkman" else "mu_hnf = mu_f*(1 + 2.5*phi + 6.2*phi^2)",
        "inputs": {
            "mu_f": (mu_f, "Pa*s"),
            "phi1": (phi1, "dimensionless"),
            "phi2": (phi2, "dimensionless"),
        },
        "intermediates": {
            "total_volume_fraction": (phi, "dimensionless"),
            "viscosity_enhancement_factor": (mu_hnf / mu_f, "dimensionless"),
        },
        "result": mu_hnf,
        "unit": "Pa*s",
        "interpretation": interpretation,
    }


def calc_effective_electrical_conductivity(
    sigma_f: float,
    sigma_s1: float,
    sigma_s2: float,
    phi1: float,
    phi2: float
) -> Dict[str, Union[float, str]]:
    """
    Effective Electrical Conductivity of Hybrid Nanofluid using Maxwell's formulation.
    sigma_s = (phi1*sigma_s1 + phi2*sigma_s2) / phi
    sigma_hnf / sigma_f = 1 + [3*(sigma_s/sigma_f - 1)*phi] / [(sigma_s/sigma_f + 2) - (sigma_s/sigma_f - 1)*phi]
    """
    is_valid, msg = validate_nanoparticle_volume_fractions(phi1, phi2)
    if not is_valid:
        raise ValueError(msg)
    if sigma_f <= 0:
        raise ValueError("Base fluid electrical conductivity must be strictly positive.")

    phi = phi1 + phi2
    if phi == 0.0:
        sigma_hnf = sigma_f
        sigma_s = 0.0
    else:
        sigma_s = (phi1 * sigma_s1 + phi2 * sigma_s2) / phi
        r = sigma_s / sigma_f
        num = 3.0 * (r - 1.0) * phi
        den = (r + 2.0) - (r - 1.0) * phi
        sigma_hnf = sigma_f * (1.0 + num / den)

    return {
        "formula_name": "Effective Electrical Conductivity (Maxwell Model)",
        "equation": "sigma_hnf = sigma_f * [1 + 3*(r - 1)*phi / ((r + 2) - (r - 1)*phi)] where r = sigma_s/sigma_f",
        "inputs": {
            "sigma_f": (sigma_f, "S/m"),
            "sigma_s1": (sigma_s1, "S/m"),
            "sigma_s2": (sigma_s2, "S/m"),
            "phi1": (phi1, "dimensionless"),
            "phi2": (phi2, "dimensionless"),
        },
        "intermediates": {
            "composite_solid_conductivity": (sigma_s, "S/m"),
            "conductivity_ratio_r": (sigma_s / sigma_f if phi > 0 else 1.0, "dimensionless"),
        },
        "result": sigma_hnf,
        "unit": "S/m",
        "interpretation": f"Effective electrical conductivity is {sigma_hnf:.6e} S/m for the hybrid suspension.",
    }


# ==============================================================================
# FORMULA 16: Joule Heating
# ==============================================================================
def calc_joule_heating(
    sigma_hnf: float,
    B0: float,
    u: float,
    v: float = 0.0,
    E_field: Tuple[float, float, float] = (0.0, 0.0, 0.0)
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 16: Joule Heating.
    Under low-magnetic Reynolds number (Re_m << 1) and transverse magnetic field B = (0, B0, 0):
    J = sigma_hnf * (E + V x B)
    With zero external electric field (E = 0), V = (u, v, 0):
    V x B = (u*i + v*j) x (B0*j) = u*B0*k
    |J|^2 = sigma_hnf^2 * B0^2 * u^2
    Q_J = |J|^2 / sigma_hnf = sigma_hnf * |V x B|^2 = sigma_hnf * B0^2 * u^2  [W/m^3]
    
    Parameters:
        sigma_hnf (float): Effective electrical conductivity [S/m]
        B0 (float): Applied magnetic flux density [T]
        u (float): X-direction velocity [m/s]
        v (float): Y-direction velocity [m/s]
        E_field (Tuple): External electric field vector [V/m]
    """
    if sigma_hnf < 0:
        raise ValueError("Electrical conductivity cannot be negative.")
    if B0 < 0:
        raise ValueError("Magnetic field magnitude B0 must be non-negative.")

    # In transverse field B = (0, B0, 0), cross product V x B produces J_z = sigma * (u*B0 + Ez)
    v_cross_b_z = u * B0
    J_z = sigma_hnf * (E_field[2] + v_cross_b_z)
    
    # Volumetric Joule heating [W/m^3]
    if sigma_hnf > 0:
        Q_J = (J_z ** 2) / sigma_hnf
    else:
        Q_J = 0.0

    interpretation = (
        f"Joule heating rate is {Q_J:.6e} W/m^3 generated internally via eddy current dissipation "
        f"(J_z = {J_z:.6e} A/m^2) under transverse magnetic field B0 = {B0:.3f} T."
    )

    return {
        "formula_name": "Joule Heating (Motional Current Model)",
        "equation": "Q_J = sigma_hnf * |V x B|^2 = sigma_hnf * B0^2 * u^2",
        "inputs": {
            "sigma_hnf": (sigma_hnf, "S/m"),
            "B0": (B0, "T"),
            "u": (u, "m/s"),
            "v": (v, "m/s"),
        },
        "intermediates": {
            "induced_current_density_Jz": (J_z, "A/m^2"),
            "motional_electric_field": (v_cross_b_z, "V/m"),
        },
        "result": Q_J,
        "unit": "W/m^3",
        "interpretation": interpretation,
    }


# ==============================================================================
# FORMULA 17: Lorentz Force
# ==============================================================================
def calc_lorentz_force(
    sigma_hnf: float,
    B0: float,
    u: float,
    v: float = 0.0,
    w: float = 0.0
) -> Dict[str, Union[float, str, Tuple[float, float, float]]]:
    """
    FORMULA 17: Lorentz Force Vector.
    F_L = J x B
    With B = (0, B0, 0) and low-Rm induction J = sigma_hnf * (V x B):
    V x B = (u*i + v*j + w*k) x (B0*j) = -w*B0*i + 0*j + u*B0*k
    J = sigma_hnf * (-w*B0*i + u*B0*k)
    F_L = J x B = [sigma*(-w*B0*i + u*B0*k)] x (B0*j)
        = -sigma*w*B0^2*(i x j) + sigma*u*B0^2*(k x j)
        = -sigma*w*B0^2*k - sigma*u*B0^2*i
    In 2D (w = 0):
        F_L,x = -sigma_hnf * B0^2 * u
        F_L,y = 0.0
        F_L,z = 0.0
    """
    if sigma_hnf < 0:
        raise ValueError("Electrical conductivity cannot be negative.")

    F_Lx = -sigma_hnf * (B0 ** 2) * u
    F_Ly = 0.0
    F_Lz = -sigma_hnf * (B0 ** 2) * w
    F_L_mag = float(np.sqrt(F_Lx**2 + F_Ly**2 + F_Lz**2))

    interpretation = (
        f"Lorentz body force acts in -X direction with magnitude {abs(F_Lx):.6e} N/m^3, "
        f"acting as an electromagnetic Hartmann brake opposing fluid flow."
    )

    return {
        "formula_name": "Lorentz Force (Electromagnetic Body Force)",
        "equation": "F_L = J x B = -sigma_hnf * B0^2 * u * i_hat",
        "inputs": {
            "sigma_hnf": (sigma_hnf, "S/m"),
            "B0": (B0, "T"),
            "u": (u, "m/s"),
            "v": (v, "m/s"),
        },
        "intermediates": {
            "F_Lx": (F_Lx, "N/m^3"),
            "F_Ly": (F_Ly, "N/m^3"),
            "F_Lz": (F_Lz, "N/m^3"),
        },
        "result_vector": (F_Lx, F_Ly, F_Lz),
        "result": F_Lx,
        "result_magnitude": F_L_mag,
        "unit": "N/m^3",
        "interpretation": interpretation,
    }


# ==============================================================================
# FORMULA 18: Darcy-Brinkman MHD Combined Momentum Formulation
# ==============================================================================
def calc_darcy_brinkman_mhd_forces(
    rho_hnf: float,
    mu_eff: float,
    k_perm: float,
    sigma_hnf: float,
    B0: float,
    u: float,
    laplacian_u: float,
    dp_dx: float,
    inertia_x: float = 0.0
) -> Dict[str, Union[float, str]]:
    """
    FORMULA 18: Darcy-Brinkman MHD Momentum Equation Balance.
    rho_hnf * [dV/dt + (V . grad)V] = -grad(p) + mu_eff * laplacian(V) - (mu_eff/k)*V + J x B
    
    Components in X-direction:
    1. Inertial Force: rho_hnf * [u du/dx + v du/dy]
    2. Pressure Gradient Force: -dp/dx
    3. Brinkman Viscous Diffusion Force: mu_eff * laplacian(u)
    4. Darcy Porous Resistance: -(mu_eff / k_perm) * u
    5. Lorentz Force: -sigma_hnf * B0^2 * u
    """
    if k_perm <= 0:
        raise ValueError("Permeability k must be strictly positive.")

    viscous_force = mu_eff * laplacian_u
    darcy_drag = -(mu_eff / k_perm) * u
    lorentz_force = -sigma_hnf * (B0 ** 2) * u
    pressure_force = -dp_dx

    # Net force per unit volume [N/m^3]
    net_force = pressure_force + viscous_force + darcy_drag + lorentz_force

    interpretation = (
        f"Darcy-Brinkman-MHD balance: Viscous force = {viscous_force:.4e} N/m^3, "
        f"Darcy resistance = {darcy_drag:.4e} N/m^3, Lorentz damping = {lorentz_force:.4e} N/m^3, "
        f"Pressure drive = {pressure_force:.4e} N/m^3."
    )

    return {
        "formula_name": "Darcy-Brinkman MHD Momentum Equation Formulation",
        "equation": "rho_hnf*[dV/dt + (V.grad)V] = -grad(p) + mu_eff*Laplacian(V) - (mu_eff/k)*V + JxB",
        "inputs": {
            "rho_hnf": (rho_hnf, "kg/m^3"),
            "mu_eff": (mu_eff, "Pa*s"),
            "k_perm": (k_perm, "m^2"),
            "sigma_hnf": (sigma_hnf, "S/m"),
            "B0": (B0, "T"),
            "u": (u, "m/s"),
            "dp_dx": (dp_dx, "Pa/m"),
            "laplacian_u": (laplacian_u, "1/(m*s)"),
        },
        "intermediates": {
            "pressure_gradient_force": (pressure_force, "N/m^3"),
            "brinkman_viscous_force": (viscous_force, "N/m^3"),
            "darcy_porous_drag": (darcy_drag, "N/m^3"),
            "lorentz_magnetic_force": (lorentz_force, "N/m^3"),
        },
        "result": net_force,
        "unit": "N/m^3",
        "interpretation": interpretation,
    }


# ==============================================================================
# SECTION 4: Battery Heat Generation Model (Bernardi et al.)
# ==============================================================================
def calc_battery_heat_generation(
    I: float,
    V_oc: float,
    V_op: float,
    T_battery: float,
    dU_oc_dT: float,
    volume_b: Optional[float] = None
) -> Dict[str, Union[float, str]]:
    """
    SECTION 4: Electrochemical Battery Heat Generation Model (Bernardi et al., 1985).
    Q_dot_b = I * (V_oc - V_op) - I * T_battery * (dU_oc / dT)  [Watts]
    Volumetric: q_dot_b = Q_dot_b / volume_b  [W/m^3]
    
    Terms:
    1. Irreversible Joule / polarization heating: Q_irr = I * (V_oc - V_op) = I^2 * R_int
    2. Reversible entropic heat of electrochemical reaction: Q_rev = -I * T_battery * (dU_oc / dT)
    """
    # Irreversible Joule/overpotential heating
    Q_irr = I * (V_oc - V_op)
    # Reversible reaction entropic heat
    Q_rev = -I * T_battery * dU_oc_dT
    # Total heat generation in Watts
    Q_total = Q_irr + Q_rev

    if volume_b and volume_b > 0:
        q_volumetric = Q_total / volume_b
    else:
        q_volumetric = Q_total

    interpretation = (
        f"Battery heat generation is {Q_total:.3f} W (Irreversible Joule: {Q_irr:.3f} W, "
        f"Reversible entropic: {Q_rev:.3f} W at current I = {I:.2f} A, T = {T_battery:.2f} K)."
    )

    return {
        "formula_name": "Battery Electrochemical Heat Generation (Bernardi Model)",
        "equation": "Q_dot_b = I*(V_oc - V) - I*T*(dU_oc/dT)",
        "inputs": {
            "I": (I, "A"),
            "V_oc": (V_oc, "V"),
            "V_op": (V_op, "V"),
            "T_battery": (T_battery, "K"),
            "dU_oc_dT": (dU_oc_dT, "V/K"),
            "volume_b": (volume_b if volume_b else 1.0, "m^3"),
        },
        "intermediates": {
            "irreversible_joule_heat": (Q_irr, "W"),
            "reversible_entropic_heat": (Q_rev, "W"),
            "cell_overpotential": (V_oc - V_op, "V"),
        },
        "result_watts": Q_total,
        "result_volumetric": q_volumetric,
        "result": q_volumetric if volume_b else Q_total,
        "unit": "W/m^3" if volume_b else "W",
        "interpretation": interpretation,
    }
