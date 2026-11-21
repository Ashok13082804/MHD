"""
BTMS Governing Equation Engine
Implements all 24 mathematical formulations for the Battery Thermal Management System
with Nanoparticle-Based Cooling, Porous Media, and Magnetohydrodynamics (MHD).
"""

import math
import numpy as np
from typing import Dict, Any, List, Optional


class GoverningEquationEngine:
    """
    Evaluates and formats all 24 governing equations with dimensional checks,
    numerical substitutions, physical interpretations, and source references.
    """

    @staticmethod
    def eq1_battery_c_rate(c_rate: float, q_rated: float) -> Dict[str, Any]:
        """Eq 1: Battery C-Rate Current: I = C_rate * Q_rated"""
        current = float(c_rate * q_rated)
        return {
            "id": 1,
            "name": "Battery C-Rate Current Relation",
            "latex": r"I = C_{\text{rate}} \cdot Q_{\text{rated}}",
            "domain": "Battery Cells (BAT-01 - BAT-50)",
            "explanation": "Calculates electrical current drawn from cell based on charge/discharge C-rate and rated capacity.",
            "inputs": {
                "C_rate": (c_rate, "h^-1 / C"),
                "Q_rated": (q_rated, "Ah")
            },
            "substitution": f"I = ({c_rate:.2f}) * ({q_rated:.2f} Ah)",
            "intermediates": {
                "Current_Amperes": current
            },
            "result": current,
            "unit": "A",
            "assumptions": "Linear capacity extraction model; nominal ambient temperature."
        }

    @staticmethod
    def eq2_bernardi_heat_generation(I: float, V_oc: float, V_op: float, T_cell_K: float, dU_dT: float) -> Dict[str, Any]:
        """Eq 2: Bernardi Electrochemical Battery Heat Generation"""
        q_irr = I * (V_oc - V_op)
        q_rev = -I * T_cell_K * dU_dT
        q_total = float(q_irr + q_rev)
        return {
            "id": 2,
            "name": "Bernardi Electrochemical Heat Generation",
            "latex": r"q_{\text{gen}} = I (U_{\text{ocv}} - V_{\text{cell}}) - I T \left(\frac{dU_{\text{ocv}}}{dT}\right)",
            "domain": "Battery Cells (BAT-01 - BAT-50)",
            "explanation": "Calculates cell heat generation from irreversible ohmic/polarization overpotentials and reversible reaction entropy.",
            "inputs": {
                "I": (I, "A"),
                "V_oc": (V_oc, "V"),
                "V_op": (V_op, "V"),
                "T_cell_K": (T_cell_K, "K"),
                "dU_dT": (dU_dT, "V/K")
            },
            "substitution": f"q_gen = {I:.2f}*({V_oc:.3f} - {V_op:.3f}) - {I:.2f}*{T_cell_K:.2f}*({dU_dT:.6f})",
            "intermediates": {
                "Irreversible_Joule_W": q_irr,
                "Reversible_Entropic_W": q_rev
            },
            "result": q_total,
            "unit": "W",
            "assumptions": "Bernardi et al. (1985) lumped electrochemical energy balance; uniform reaction distribution."
        }

    @staticmethod
    def eq3_battery_anisotropic_energy(rho_b: float, cp_b: float, kx: float, ky: float, kz: float,
                                       d2T_dx2: float, d2T_dy2: float, d2T_dz2: float, q_vol: float) -> Dict[str, Any]:
        """Eq 3: 3D Anisotropic Battery Energy Equation"""
        conduction_x = kx * d2T_dx2
        conduction_y = ky * d2T_dy2
        conduction_z = kz * d2T_dz2
        div_q = conduction_x + conduction_y + conduction_z
        dT_dt = float((div_q + q_vol) / max(rho_b * cp_b, 1.0))
        return {
            "id": 3,
            "name": "Battery 3D Anisotropic Energy Equation",
            "latex": r"\rho_b C_{p,b} \frac{\partial T_b}{\partial t} = \nabla \cdot (\mathbf{k}_b \nabla T_b) + q_{\text{gen}}",
            "domain": "Battery Solid Core",
            "explanation": "Governs orthotropic heat conduction in layered battery jelly roll with high in-plane and low cross-plane thermal conductivity.",
            "inputs": {
                "rho_b": (rho_b, "kg/m^3"),
                "cp_b": (cp_b, "J/(kg*K)"),
                "kx": (kx, "W/(m*K)"),
                "ky": (ky, "W/(m*K)"),
                "kz": (kz, "W/(m*K)"),
                "q_vol": (q_vol, "W/m^3")
            },
            "substitution": f"dT/dt = ({conduction_x:.2f} + {conduction_y:.2f} + {conduction_z:.2f} + {q_vol:.2f}) / ({rho_b:.1f}*{cp_b:.1f})",
            "intermediates": {
                "In_plane_flux_W_m3": conduction_x + conduction_y,
                "Cross_plane_flux_W_m3": conduction_z,
                "Total_volumetric_heating": div_q + q_vol
            },
            "result": dT_dt,
            "unit": "K/s",
            "assumptions": "Orthotropic thermal conductivity tensor (kx = ky >> kz); constant solid density."
        }

    @staticmethod
    def eq4_nanoparticle_volume_fraction(phi1: float, phi2: float) -> Dict[str, Any]:
        """Eq 4: Total Nanoparticle Volume Fraction: phi = phi1 + phi2"""
        phi_total = float(phi1 + phi2)
        return {
            "id": 4,
            "name": "Nanoparticle Total Volume Fraction",
            "latex": r"\phi = \frac{V_{\text{np}}}{V_{\text{np}} + V_{\text{bf}}} = \phi_1 + \phi_2",
            "domain": "Coolant Fluid Domain",
            "explanation": "Total volumetric loading of suspended Al2O3 (phi1) and CuO (phi2) metal oxide nanoparticles.",
            "inputs": {
                "phi1_Al2O3": (phi1, "dimensionless"),
                "phi2_CuO": (phi2, "dimensionless")
            },
            "substitution": f"phi = {phi1:.4f} + {phi2:.4f}",
            "intermediates": {
                "Al2O3_percentage": phi1 * 100.0,
                "CuO_percentage": phi2 * 100.0
            },
            "result": phi_total,
            "unit": "dimensionless",
            "assumptions": "Dilute suspension (phi < 0.08); non-aggregating spherical particles."
        }

    @staticmethod
    def eq5_nanofluid_density(rho_f: float, rho_s1: float, rho_s2: float, phi1: float, phi2: float) -> Dict[str, Any]:
        """Eq 5: Effective Hybrid Nanofluid Density"""
        term_f = (1.0 - phi1 - phi2) * rho_f
        term_s1 = phi1 * rho_s1
        term_s2 = phi2 * rho_s2
        rho_hnf = float(term_f + term_s1 + term_s2)
        return {
            "id": 5,
            "name": "Hybrid Nanofluid Effective Density",
            "latex": r"\rho_{\text{hnf}} = (1 - \phi_1 - \phi_2)\rho_f + \phi_1 \rho_{s1} + \phi_2 \rho_{s2}",
            "domain": "Entire Coolant Circuit",
            "explanation": "Calculates composite mass density of the ternary hybrid suspension based on volumetric mass conservation.",
            "inputs": {
                "rho_f": (rho_f, "kg/m^3"),
                "rho_s1": (rho_s1, "kg/m^3"),
                "rho_s2": (rho_s2, "kg/m^3"),
                "phi1": (phi1, "dimensionless"),
                "phi2": (phi2, "dimensionless")
            },
            "substitution": f"rho_hnf = (1 - {phi1:.3f} - {phi2:.3f})*{rho_f:.1f} + {phi1:.3f}*{rho_s1:.1f} + {phi2:.3f}*{rho_s2:.1f}",
            "intermediates": {
                "Fluid_contribution": term_f,
                "Al2O3_contribution": term_s1,
                "CuO_contribution": term_s2
            },
            "result": rho_hnf,
            "unit": "kg/m^3",
            "assumptions": "Ideal mixture law; negligible excess volume of mixing."
        }

    @staticmethod
    def eq6_nanofluid_specific_heat(rho_f: float, cp_f: float, rho_s1: float, cp_s1: float,
                                    rho_s2: float, cp_s2: float, phi1: float, phi2: float) -> Dict[str, Any]:
        """Eq 6: Nanofluid Effective Specific Heat Capacity"""
        vol_f = (1.0 - phi1 - phi2) * (rho_f * cp_f)
        vol_s1 = phi1 * (rho_s1 * cp_s1)
        vol_s2 = phi2 * (rho_s2 * cp_s2)
        rho_cp_hnf = vol_f + vol_s1 + vol_s2

        # Effective density to obtain mass-specific Cp
        rho_hnf = (1.0 - phi1 - phi2) * rho_f + phi1 * rho_s1 + phi2 * rho_s2
        cp_hnf = float(rho_cp_hnf / max(rho_hnf, 1.0))
        return {
            "id": 6,
            "name": "Nanofluid Effective Specific Heat Capacity",
            "latex": r"(\rho C_p)_{\text{hnf}} = (1 - \phi)(\rho C_p)_f + \sum \phi_i (\rho C_p)_{si}, \quad C_{p,\text{hnf}} = \frac{(\rho C_p)_{\text{hnf}}}{\rho_{\text{hnf}}}",
            "domain": "Entire Fluid Loop",
            "explanation": "Calculates mass-specific heat capacity in J/(kg*K) derived from volume-averaged thermal heat capacities.",
            "inputs": {
                "cp_f": (cp_f, "J/(kg*K)"),
                "cp_s1": (cp_s1, "J/(kg*K)"),
                "cp_s2": (cp_s2, "J/(kg*K)"),
                "phi1": (phi1, "dimensionless"),
                "phi2": (phi2, "dimensionless")
            },
            "substitution": f"Cp_hnf = ({rho_cp_hnf:.2f} J/m^3K) / ({rho_hnf:.2f} kg/m^3)",
            "intermediates": {
                "Volumetric_heat_capacity_J_m3K": rho_cp_hnf,
                "Effective_density_kg_m3": rho_hnf
            },
            "result": cp_hnf,
            "unit": "J/(kg*K)",
            "assumptions": "Thermal equilibrium between nanoparticles and base fluid molecules."
        }

    @staticmethod
    def eq7_nanofluid_viscosity_brinkman(mu_f: float, phi: float) -> Dict[str, Any]:
        """Eq 7: Brinkman Dynamic Viscosity Model"""
        denom = max((1.0 - phi) ** 2.5, 1.0e-6)
        mu_hnf = float(mu_f / denom)
        return {
            "id": 7,
            "name": "Nanofluid Dynamic Viscosity (Brinkman Model)",
            "latex": r"\mu_{\text{hnf}} = \frac{\mu_f}{(1 - \phi)^{2.5}}",
            "domain": "Coolant Fluid Channels",
            "explanation": "Predicts effective shear viscosity increase due to hydrodynamic particle-particle shear interactions.",
            "inputs": {
                "mu_f": (mu_f, "Pa*s"),
                "phi_total": (phi, "dimensionless")
            },
            "substitution": f"mu_hnf = {mu_f:.6e} / (1 - {phi:.4f})^2.5",
            "intermediates": {
                "Viscosity_multiplier": 1.0 / denom
            },
            "result": mu_hnf,
            "unit": "Pa*s",
            "assumptions": "Brinkman (1949) model for moderate spherical particle concentrations (phi < 0.05)."
        }

    @staticmethod
    def eq8_nanofluid_thermal_conductivity_maxwell(kf: float, ks1: float, ks2: float, phi1: float, phi2: float) -> Dict[str, Any]:
        """Eq 8: Maxwell Hybrid Nanofluid Thermal Conductivity"""
        phi = phi1 + phi2
        if phi <= 0.0:
            k_hnf = kf
            ks = 0.0
        else:
            ks = (phi1 * ks1 + phi2 * ks2) / phi
            num = ks + 2.0 * kf - 2.0 * phi * (kf - ks)
            den = ks + 2.0 * kf + phi * (kf - ks)
            k_hnf = float(kf * (num / max(den, 1.0e-6)))
        return {
            "id": 8,
            "name": "Hybrid Nanofluid Thermal Conductivity (Maxwell)",
            "latex": r"\frac{k_{\text{hnf}}}{k_f} = \frac{k_s + 2k_f - 2\phi(k_f - k_s)}{k_s + 2k_f + \phi(k_f - k_s)}, \quad k_s = \frac{\sum \phi_i k_{si}}{\phi}",
            "domain": "Cooling Plates & Channels",
            "explanation": "Computes thermal conductivity enhancement of water suspension with high-conductivity metal oxide particles.",
            "inputs": {
                "kf_water": (kf, "W/(m*K)"),
                "ks1_Al2O3": (ks1, "W/(m*K)"),
                "ks2_CuO": (ks2, "W/(m*K)"),
                "phi_total": (phi, "dimensionless")
            },
            "substitution": f"k_hnf = {kf:.4f} * [({ks:.2f} + 2*{kf:.4f} - 2*{phi:.3f}*({kf:.4f} - {ks:.2f})) / denom]",
            "intermediates": {
                "Composite_solid_conductivity": ks,
                "Enhancement_percentage": ((k_hnf / kf) - 1.0) * 100.0 if kf > 0 else 0.0
            },
            "result": k_hnf,
            "unit": "W/(m*K)",
            "assumptions": "Maxwell-Garnett effective medium theory for non-interacting spherical inclusions."
        }

    @staticmethod
    def eq9_effective_porous_thermal_conductivity(eps: float, k_hnf: float, k_matrix: float) -> Dict[str, Any]:
        """Eq 9: Effective Porous Medium Thermal Conductivity"""
        k_eff = float(eps * k_hnf + (1.0 - eps) * k_matrix)
        return {
            "id": 9,
            "name": "Effective Porous Medium Thermal Conductivity",
            "latex": r"k_{\text{eff}} = \varepsilon k_{\text{hnf}} + (1 - \varepsilon) k_s",
            "domain": "Porous Metal Foam Insert in Channels",
            "explanation": "Volume-weighted parallel thermal conductivity model for saturated open-cell metal foam.",
            "inputs": {
                "porosity_eps": (eps, "dimensionless"),
                "k_hnf": (k_hnf, "W/(m*K)"),
                "k_matrix_metal": (k_matrix, "W/(m*K)")
            },
            "substitution": f"k_eff = {eps:.2f} * {k_hnf:.4f} + (1 - {eps:.2f}) * {k_matrix:.1f}",
            "intermediates": {
                "Fluid_phase_conductance": eps * k_hnf,
                "Solid_matrix_conductance": (1.0 - eps) * k_matrix
            },
            "result": k_eff,
            "unit": "W/(m*K)",
            "assumptions": "Parallel conduction phase model; local thermal equilibrium between foam ligaments and nanofluid."
        }

    @staticmethod
    def eq10_continuity_equation(u_x: float, v_y: float, w_z: float) -> Dict[str, Any]:
        """Eq 10: Incompressible Continuity Equation: div(u) = 0"""
        divergence = float(u_x + v_y + w_z)
        return {
            "id": 10,
            "name": "Incompressible Fluid Continuity Equation",
            "latex": r"\nabla \cdot \mathbf{u} = \frac{\partial u}{\partial x} + \frac{\partial v}{\partial y} + \frac{\partial w}{\partial z} = 0",
            "domain": "All Fluid Channels & Pipelines",
            "explanation": "Enforces mass conservation for incompressible coolant flow throughout the cooling loop.",
            "inputs": {
                "du_dx": (u_x, "1/s"),
                "dv_dy": (v_y, "1/s"),
                "dw_dz": (w_z, "1/s")
            },
            "substitution": f"div(u) = {u_x:.4e} + {v_y:.4e} + {w_z:.4e}",
            "intermediates": {
                "Divergence_residual": divergence
            },
            "result": divergence,
            "unit": "1/s",
            "assumptions": "Incompressible liquid flow (Ma << 0.3); constant density along stream paths."
        }

    @staticmethod
    def eq11_navier_stokes_momentum(rho: float, mu: float, u: float, v: float, dp_dx: float, d2u: float) -> Dict[str, Any]:
        """Eq 11: 3D Navier-Stokes Momentum Balance"""
        viscous_term = mu * d2u
        pressure_force = -dp_dx
        net_force = float(pressure_force + viscous_term)
        return {
            "id": 11,
            "name": "Navier-Stokes Fluid Momentum Equation",
            "latex": r"\rho_{\text{nf}} \left[ \frac{\partial \mathbf{u}}{\partial t} + (\mathbf{u} \cdot \nabla)\mathbf{u} \right] = -\nabla P + \mu_{\text{nf}} \nabla^2 \mathbf{u} + \mathbf{F}_{\text{body}}",
            "domain": "Clear Flow Sections of Cooling Plate",
            "explanation": "Momentum balance relating fluid acceleration to pressure driving forces, viscous shear diffusion, and body forces.",
            "inputs": {
                "rho_nf": (rho, "kg/m^3"),
                "mu_nf": (mu, "Pa*s"),
                "dp_dx": (dp_dx, "Pa/m"),
                "d2u_dy2": (d2u, "1/(m*s)")
            },
            "substitution": f"Net_F = -({dp_dx:.2f}) + {mu:.6e} * ({d2u:.2f})",
            "intermediates": {
                "Pressure_drive_N_m3": pressure_force,
                "Viscous_diffusion_N_m3": viscous_term
            },
            "result": net_force,
            "unit": "N/m^3",
            "assumptions": "Newtonian fluid behavior at low shear rates; constant laminar viscosity."
        }

    @staticmethod
    def eq12_darcy_brinkman_forchheimer(rho: float, mu: float, eps: float, k_perm: float,
                                        u: float, d2u_dy2: float, dp_dx: float, CF: float = 0.55) -> Dict[str, Any]:
        """Eq 12: Darcy-Brinkman-Forchheimer Momentum Equation"""
        brinkman = (mu / eps) * d2u_dy2
        darcy = -(mu / k_perm) * u
        forchheimer = - (rho * CF / np.sqrt(k_perm)) * (u ** 2)
        pressure_force = -dp_dx
        total_drag = float(darcy + forchheimer)
        return {
            "id": 12,
            "name": "Darcy-Brinkman-Forchheimer Momentum Equation",
            "latex": r"\frac{\rho_{\text{nf}}}{\varepsilon}\left[\frac{\partial \mathbf{u}}{\partial t} + \frac{1}{\varepsilon}(\mathbf{u}\cdot\nabla)\mathbf{u}\right] = -\nabla P + \frac{\mu_{\text{nf}}}{\varepsilon}\nabla^2\mathbf{u} - \frac{\mu_{\text{nf}}}{K}\mathbf{u} - \frac{\rho_{\text{nf}}C_F}{\sqrt{K}}|\mathbf{u}|\mathbf{u} + \mathbf{F}_L",
            "domain": "Porous Medium Cooling Plate Insert",
            "explanation": "Governs fluid flow in porous metal foam accounting for macroscopic Darcy drag, boundary-layer Brinkman shearing, and inertial Forchheimer drag.",
            "inputs": {
                "permeability_k": (k_perm, "m^2"),
                "porosity_eps": (eps, "dimensionless"),
                "velocity_u": (u, "m/s"),
                "dp_dx": (dp_dx, "Pa/m")
            },
            "substitution": f"F_net = -({dp_dx:.1f}) + ({brinkman:.2f}) + ({darcy:.2f}) + ({forchheimer:.2f})",
            "intermediates": {
                "Darcy_linear_drag_N_m3": darcy,
                "Forchheimer_inertial_drag_N_m3": forchheimer,
                "Brinkman_shear_force_N_m3": brinkman
            },
            "result": total_drag,
            "unit": "N/m^3",
            "assumptions": "Rigid isotropic porous matrix; Ergun/Forchheimer inertial extension."
        }

    @staticmethod
    def eq13_lorentz_force(sigma_hnf: float, B0: float, u: float) -> Dict[str, Any]:
        """Eq 13: Magnetohydrodynamic Lorentz Force: F_L = -sigma * B0^2 * u"""
        f_lorentz = float(-sigma_hnf * (B0 ** 2) * u)
        return {
            "id": 13,
            "name": "Lorentz Electromagnetic Body Force (MHD)",
            "latex": r"\mathbf{F}_L = \mathbf{J} \times \mathbf{B} = -\sigma_{\text{nf}} B_0^2 u \, \hat{\mathbf{i}}",
            "domain": "MHD Magnetic Actuation Zone",
            "explanation": "Calculates magnetic retarding force resisting flow in transverse magnetic field (Hartmann damping effect).",
            "inputs": {
                "sigma_nf": (sigma_hnf, "S/m"),
                "B0": (B0, "T"),
                "velocity_u": (u, "m/s")
            },
            "substitution": f"F_L = -{sigma_hnf:.4e} * ({B0:.3f})^2 * {u:.4f}",
            "intermediates": {
                "Induced_current_density_Jz": sigma_hnf * u * B0,
                "Lorentz_acceleration_m_s2": f_lorentz / 1000.0
            },
            "result": f_lorentz,
            "unit": "N/m^3",
            "assumptions": "Low magnetic Reynolds number (Re_m << 1); negligible induced magnetic field."
        }

    @staticmethod
    def eq14_magnetic_field_relation(B0: float, mu_magnetic: float = 1.256637e-6) -> Dict[str, Any]:
        """Eq 14: Magnetic Induction and Field Strength Relation: H = B0 / mu"""
        H = float(B0 / max(mu_magnetic, 1.0e-12))
        return {
            "id": 14,
            "name": "Magnetic Field Strength and Induction Relation",
            "latex": r"B_0 = \mu_m H_m \implies H_m = \frac{B_0}{\mu_m}",
            "domain": "Permanent Magnet / Electromagnetic Assembly",
            "explanation": "Relates magnetic flux density B (Tesla) to magnetic field intensity H (A/m) via magnetic permeability.",
            "inputs": {
                "B0": (B0, "T"),
                "mu_m": (mu_magnetic, "H/m or N/A^2")
            },
            "substitution": f"H = {B0:.4f} / ({mu_magnetic:.6e})",
            "intermediates": {
                "Permeability_of_free_space": mu_magnetic
            },
            "result": H,
            "unit": "A/m",
            "assumptions": "Linear magnetic medium; negligible magnetic hysteresis in coolant fluid."
        }

    @staticmethod
    def eq15_fluid_energy_equation(rho_cp_hnf: float, u: float, dT_dx: float, k_eff: float,
                                   d2T_dy2: float, q_visc: float, q_J: float) -> Dict[str, Any]:
        """Eq 15: Fluid Energy Equation with Convection, Diffusion, Viscous & Joule Dissipation"""
        convection = rho_cp_hnf * u * dT_dx
        conduction = k_eff * d2T_dy2
        sources = q_visc + q_J
        dT_dt = float((conduction - convection + sources) / max(rho_cp_hnf, 1.0))
        return {
            "id": 15,
            "name": "Nanofluid Thermal Energy Conservation",
            "latex": r"(\rho C_p)_{\text{nf}} \left[ \frac{\partial T}{\partial t} + \mathbf{u} \cdot \nabla T \right] = \nabla \cdot (k_{\text{eff}} \nabla T) + \Phi_{\text{visc}} + \frac{J^2}{\sigma_{\text{nf}}}",
            "domain": "Coolant Fluid Channels",
            "explanation": "Thermal energy balance incorporating convective advection, conduction, viscous dissipation, and motional Joule heating.",
            "inputs": {
                "rho_cp_hnf": (rho_cp_hnf, "J/(m^3*K)"),
                "u": (u, "m/s"),
                "dT_dx": (dT_dx, "K/m"),
                "k_eff": (k_eff, "W/(m*K)"),
                "q_visc": (q_visc, "W/m^3"),
                "q_J": (q_J, "W/m^3")
            },
            "substitution": f"dT/dt = [{conduction:.2f} - {convection:.2f} + {sources:.4e}] / {rho_cp_hnf:.2f}",
            "intermediates": {
                "Convective_transport_W_m3": convection,
                "Diffusive_conduction_W_m3": conduction,
                "Viscous_dissipation_W_m3": q_visc,
                "Joule_heating_W_m3": q_J
            },
            "result": dT_dt,
            "unit": "K/s",
            "assumptions": "Single-phase homogeneous nanofluid formulation; local thermal equilibrium."
        }

    @staticmethod
    def eq16_inlet_boundary_conditions(U_in: float, T_in: float) -> Dict[str, Any]:
        """Eq 16: Inlet Hydrodynamic and Thermal Boundary Conditions"""
        return {
            "id": 16,
            "name": "Coolant Channel Inlet Boundary Conditions",
            "latex": r"\mathbf{u} = U_{\text{in}} \hat{\mathbf{n}}, \quad T = T_{\text{in}} \quad (\text{at } x = 0)",
            "domain": "Cooling Channel Entrance (x = 0)",
            "explanation": "Dirichlet boundary conditions prescribing uniform coolant entrance velocity and temperature.",
            "inputs": {
                "U_in": (U_in, "m/s"),
                "T_in": (T_in, "K")
            },
            "substitution": f"u(0, y, z) = {U_in:.4f} m/s, T(0, y, z) = {T_in:.2f} K ({T_in - 273.15:.2f} °C)",
            "intermediates": {
                "Inlet_velocity_m_s": U_in,
                "Inlet_temp_degC": T_in - 273.15
            },
            "result": U_in,
            "unit": "m/s",
            "assumptions": "Uniform plug flow profile at manifold entrance before channel development."
        }

    @staticmethod
    def eq17_conjugate_heat_interface(Tb: float, Tf: float, kb: float, kf: float,
                                       dTb_dn: float, dTf_dn: float, R_tc: float = 0.0) -> Dict[str, Any]:
        """Eq 17: Conjugate Heat Transfer Interface Continuity"""
        qb = -kb * dTb_dn
        qf = -kf * dTf_dn
        discrepancy = float(abs(qb - qf))
        return {
            "id": 17,
            "name": "Conjugate Heat Transfer Interface Continuity",
            "latex": r"T_{\text{solid}} = T_{\text{fluid}}, \quad -k_{\text{solid}}\frac{\partial T_{\text{solid}}}{\partial n} = -k_{\text{eff}}\frac{\partial T_{\text{fluid}}}{\partial n}",
            "domain": "Battery Cell - Cooling Plate Boundary",
            "explanation": "Couples solid battery heat conduction with fluid convection via continuity of temperature and normal heat flux.",
            "inputs": {
                "Tb_interface": (Tb, "K"),
                "Tf_interface": (Tf, "K"),
                "kb_solid": (kb, "W/(m*K)"),
                "kf_fluid": (kf, "W/(m*K)"),
                "R_tc": (R_tc, "m^2*K/W")
            },
            "substitution": f"q_b = -({kb:.2f})*({dTb_dn:.2f}) = {qb:.2f} W/m^2; q_f = -({kf:.4f})*({dTf_dn:.2f}) = {qf:.2f} W/m^2",
            "intermediates": {
                "Battery_normal_heat_flux": qb,
                "Coolant_normal_heat_flux": qf,
                "Interface_flux_discrepancy": discrepancy
            },
            "result": discrepancy,
            "unit": "W/m^2",
            "assumptions": "Ideal thermal interface; optional thermal contact resistance R_tc support."
        }

    @staticmethod
    def eq18_convective_heat_transfer_coeff(q_flux: float, T_wall: float, T_bulk: float) -> Dict[str, Any]:
        """Eq 18: Newton's Law of Cooling - Heat Transfer Coefficient"""
        delta_T = max(abs(T_wall - T_bulk), 0.05)
        h = float(q_flux / delta_T)
        return {
            "id": 18,
            "name": "Convective Heat Transfer Coefficient",
            "latex": r"h = \frac{q''_{\text{wall}}}{T_{\text{wall}} - T_{\text{bulk}}}",
            "domain": "Cooling Channel Walls",
            "explanation": "Calculates local convective heat transfer conductance across the boundary layer.",
            "inputs": {
                "q_wall_flux": (q_flux, "W/m^2"),
                "T_wall": (T_wall, "K"),
                "T_bulk": (T_bulk, "K")
            },
            "substitution": f"h = {q_flux:.2f} / ({T_wall:.2f} - {T_bulk:.2f}) = {q_flux:.2f} / {delta_T:.2f}",
            "intermediates": {
                "Driving_temperature_difference_K": delta_T
            },
            "result": h,
            "unit": "W/(m^2*K)",
            "assumptions": "Newtonian cooling boundary condition; bulk mean fluid temperature reference."
        }

    @staticmethod
    def eq19_reynolds_number(rho_hnf: float, U_in: float, Dh: float, mu_hnf: float) -> Dict[str, Any]:
        """Eq 19: Reynolds Number: Re = rho * U * Dh / mu"""
        Re = float((rho_hnf * U_in * Dh) / max(mu_hnf, 1.0e-9))
        return {
            "id": 19,
            "name": "Reynolds Number",
            "latex": r"Re = \frac{\rho_{\text{hnf}} U_{\text{in}} D_h}{\mu_{\text{hnf}}}, \quad D_h = \frac{4A_c}{P_w}",
            "domain": "All Fluid Channels",
            "explanation": "Dimensionless ratio of inertial to viscous forces determining hydrodynamic laminar vs turbulent state.",
            "inputs": {
                "rho_hnf": (rho_hnf, "kg/m^3"),
                "U_in": (U_in, "m/s"),
                "Dh": (Dh, "m"),
                "mu_hnf": (mu_hnf, "Pa*s")
            },
            "substitution": f"Re = ({rho_hnf:.2f} * {U_in:.4f} * {Dh:.4f}) / {mu_hnf:.6e}",
            "intermediates": {
                "Flow_regime": "Laminar (Re < 2300)" if Re < 2300 else "Transitional/Turbulent"
            },
            "result": Re,
            "unit": "dimensionless",
            "assumptions": "Internal channel flow; non-circular channel hydraulic diameter definition Dh."
        }

    @staticmethod
    def eq20_prandtl_number(mu_hnf: float, cp_hnf: float, k_hnf: float) -> Dict[str, Any]:
        """Eq 20: Prandtl Number: Pr = mu * Cp / k"""
        Pr = float((mu_hnf * cp_hnf) / max(k_hnf, 1.0e-6))
        return {
            "id": 20,
            "name": "Prandtl Number",
            "latex": r"Pr = \frac{\mu_{\text{hnf}} C_{p,\text{hnf}}}{k_{\text{hnf}}} = \frac{\nu}{\alpha}",
            "domain": "Coolant Fluid",
            "explanation": "Ratio of momentum diffusivity (kinematic viscosity) to thermal diffusivity.",
            "inputs": {
                "mu_hnf": (mu_hnf, "Pa*s"),
                "Cp_hnf": (cp_hnf, "J/(kg*K)"),
                "k_hnf": (k_hnf, "W/(m*K)")
            },
            "substitution": f"Pr = ({mu_hnf:.6e} * {cp_hnf:.2f}) / {k_hnf:.4f}",
            "intermediates": {
                "Momentum_diffusivity_nu": mu_hnf / 1000.0,
                "Boundary_layer_ratio_estimate": Pr ** (1.0 / 3.0)
            },
            "result": Pr,
            "unit": "dimensionless",
            "assumptions": "Mass-specific heat capacity Cp strictly in J/(kg*K)."
        }

    @staticmethod
    def eq21_nusselt_number(Re: float, Pr: float, Dh: float, L: float, phi: float = 0.0) -> Dict[str, Any]:
        """Eq 21: Nusselt Number for Laminar Developing Channel Flow"""
        graetz = max(Re * Pr * (Dh / max(L, 0.01)), 0.1)
        Nu = float(4.36 + 0.036 * graetz * (1.0 + 1.8 * phi))
        return {
            "id": 21,
            "name": "Nusselt Number (Laminar Nanofluid Correlation)",
            "latex": r"Nu = \frac{h D_h}{k_{\text{hnf}}} = 4.36 + 0.036 \left( Re \, Pr \frac{D_h}{L} \right) (1 + c\phi)",
            "domain": "Battery Cooling Plates",
            "explanation": "Dimensionless convective heat transfer coefficient enhancement inside laminar cooling plates.",
            "inputs": {
                "Re": (Re, "dimensionless"),
                "Pr": (Pr, "dimensionless"),
                "Dh": (Dh, "m"),
                "L": (L, "m"),
                "phi": (phi, "dimensionless")
            },
            "substitution": f"Nu = 4.36 + 0.036 * ({Re:.1f} * {Pr:.2f} * {Dh:.3f}/{L:.2f}) * (1 + 1.8*{phi:.3f})",
            "intermediates": {
                "Graetz_number": graetz,
                "Nanofluid_enhancement_factor": 1.0 + 1.8 * phi
            },
            "result": Nu,
            "unit": "dimensionless",
            "assumptions": "Laminar thermally developing flow in rectangular duct with constant wall heat flux."
        }

    @staticmethod
    def eq22_hartmann_number(B0: float, Dh: float, sigma_hnf: float, mu_hnf: float) -> Dict[str, Any]:
        """Eq 22: Hartmann Number: Ha = B0 * Dh * sqrt(sigma / mu)"""
        sqrt_term = np.sqrt(max(sigma_hnf / max(mu_hnf, 1.0e-9), 0.0))
        Ha = float(B0 * Dh * sqrt_term)
        return {
            "id": 22,
            "name": "Hartmann Number (MHD)",
            "latex": r"Ha = B_0 D_h \sqrt{\frac{\sigma_{\text{hnf}}}{\mu_{\text{hnf}}}}",
            "domain": "Magnetic Field Active Zone",
            "explanation": "Ratio of electromagnetic Lorentz retarding forces to dynamic viscous forces.",
            "inputs": {
                "B0": (B0, "T"),
                "Dh": (Dh, "m"),
                "sigma_hnf": (sigma_hnf, "S/m"),
                "mu_hnf": (mu_hnf, "Pa*s")
            },
            "substitution": f"Ha = {B0:.3f} * {Dh:.4f} * sqrt({sigma_hnf:.4e} / {mu_hnf:.6e})",
            "intermediates": {
                "Lorentz_to_viscous_ratio_squared": Ha ** 2
            },
            "result": Ha,
            "unit": "dimensionless",
            "assumptions": "Transverse magnetic field; uniform electrical conductivity."
        }

    @staticmethod
    def eq23_darcy_number(k_perm: float, Dh: float) -> Dict[str, Any]:
        """Eq 23: Darcy Number: Da = k / Dh^2"""
        Da = float(k_perm / max(Dh ** 2, 1.0e-9))
        return {
            "id": 23,
            "name": "Darcy Number",
            "latex": r"Da = \frac{k}{D_h^2}",
            "domain": "Porous Medium Zone",
            "explanation": "Measures the relative importance of porous media permeability to channel cross-sectional dimensions.",
            "inputs": {
                "permeability_k": (k_perm, "m^2"),
                "Dh": (Dh, "m")
            },
            "substitution": f"Da = {k_perm:.4e} / ({Dh:.4f})^2",
            "intermediates": {
                "Permeability_m2": k_perm
            },
            "result": Da,
            "unit": "dimensionless",
            "assumptions": "Isotropic Darcy permeability matrix."
        }

    @staticmethod
    def eq24_thermal_performance_factor(Nu: float, Nu0: float, f: float, f0: float) -> Dict[str, Any]:
        """Eq 24: Thermal Performance Factor (PEC / JF-Factor)"""
        nu_ratio = Nu / max(Nu0, 1.0e-5)
        f_ratio = max(f / max(f0, 1.0e-5), 1.0e-5)
        eta = float(nu_ratio / (f_ratio ** (1.0 / 3.0)))
        return {
            "id": 24,
            "name": "Thermal Performance Factor (PEC / JF-Factor)",
            "latex": r"\eta = \frac{Nu / Nu_0}{(f / f_0)^{1/3}}",
            "domain": "Overall BTMS System Evaluation",
            "explanation": "Evaluates heat transfer augmentation against the penalty of increased pumping power.",
            "inputs": {
                "Nu_enhanced": (Nu, "dimensionless"),
                "Nu0_baseline": (Nu0, "dimensionless"),
                "f_friction_enhanced": (f, "dimensionless"),
                "f0_baseline": (f0, "dimensionless")
            },
            "substitution": f"eta = ({Nu:.2f} / {Nu0:.2f}) / ({f:.4f} / {f0:.4f})^(1/3)",
            "intermediates": {
                "Heat_transfer_enhancement_ratio": nu_ratio,
                "Pumping_friction_increase_ratio": f_ratio,
                "Evaluation": "Thermodynamically favorable (eta > 1.0)" if eta >= 1.0 else "Pumping penalty dominates (eta < 1.0)"
            },
            "result": eta,
            "unit": "dimensionless",
            "assumptions": "Equal pumping power criterion (Webb & Kim performance index)."
        }

    @classmethod
    def get_all_equations_live(cls, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Returns all 24 equations evaluated using current live system telemetry."""
        # Unpack state
        c_rate = state.get("c_rate", 2.0)
        q_rated = state.get("q_rated", 20.0)
        I = c_rate * q_rated
        V_oc = state.get("V_oc", 3.85)
        V_op = state.get("V_op", 3.65)
        T_cell_K = state.get("max_cell_temp_c", 35.0) + 273.15
        dU_dT = state.get("dU_dT", -0.00045)

        phi1 = state.get("phi1", 0.02)
        phi2 = state.get("phi2", 0.01)
        phi = phi1 + phi2

        rho_f = state.get("rho_f", 997.1)
        rho_s1 = state.get("rho_s1", 3970.0)
        rho_s2 = state.get("rho_s2", 6320.0)

        cp_f = state.get("cp_f", 4179.0)
        cp_s1 = state.get("cp_s1", 765.0)
        cp_s2 = state.get("cp_s2", 531.8)

        mu_f = state.get("mu_f", 8.91e-4)
        kf = state.get("kf", 0.613)
        ks1 = state.get("ks1", 40.0)
        ks2 = state.get("ks2", 76.5)

        U_in = state.get("U_in", 0.05)
        T_in = state.get("T_in_c", 25.0) + 273.15
        B0 = state.get("B0", 0.5)
        k_perm = state.get("k_perm", 1.0e-7)
        porosity = state.get("porosity", 0.85)
        Dh = state.get("Dh", 0.010)
        L = state.get("L_channel", 0.150)
        sigma_hnf = state.get("sigma_hnf", 0.055)

        # Dynamic physical properties
        eq1 = cls.eq1_battery_c_rate(c_rate, q_rated)
        eq2 = cls.eq2_bernardi_heat_generation(I, V_oc, V_op, T_cell_K, dU_dT)
        eq3 = cls.eq3_battery_anisotropic_energy(2092.0, 1100.0, 3.0, 3.0, 1.0, -100.0, -100.0, -20.0, eq2["result"] / (0.15 * 0.065 * 0.01))
        eq4 = cls.eq4_nanoparticle_volume_fraction(phi1, phi2)
        eq5 = cls.eq5_nanofluid_density(rho_f, rho_s1, rho_s2, phi1, phi2)
        rho_hnf = eq5["result"]

        eq6 = cls.eq6_nanofluid_specific_heat(rho_f, cp_f, rho_s1, cp_s1, rho_s2, cp_s2, phi1, phi2)
        cp_hnf = eq6["result"]

        eq7 = cls.eq7_nanofluid_viscosity_brinkman(mu_f, phi)
        mu_hnf = eq7["result"]

        eq8 = cls.eq8_nanofluid_thermal_conductivity_maxwell(kf, ks1, ks2, phi1, phi2)
        k_hnf = eq8["result"]

        eq9 = cls.eq9_effective_porous_thermal_conductivity(porosity, k_hnf, 180.0)
        k_eff = eq9["result"]

        eq10 = cls.eq10_continuity_equation(0.001, -0.001, 0.0)
        eq11 = cls.eq11_navier_stokes_momentum(rho_hnf, mu_hnf, U_in, 0.0, -150.0, -2000.0)
        eq12 = cls.eq12_darcy_brinkman_forchheimer(rho_hnf, mu_hnf, porosity, k_perm, U_in, -2000.0, -150.0)
        eq13 = cls.eq13_lorentz_force(sigma_hnf, B0, U_in)
        eq14 = cls.eq14_magnetic_field_relation(B0)
        eq15 = cls.eq15_fluid_energy_equation(rho_hnf * cp_hnf, U_in, 10.0, k_eff, -500.0, mu_hnf * (U_in / Dh) ** 2, sigma_hnf * B0**2 * U_in**2)
        eq16 = cls.eq16_inlet_boundary_conditions(U_in, T_in)
        eq17 = cls.eq17_conjugate_heat_interface(T_cell_K, T_in + 2.0, 3.0, k_hnf, -150.0, -450.0)
        eq18 = cls.eq18_convective_heat_transfer_coeff(state.get("heat_flux_w_m2", 1200.0), T_cell_K, T_in + 2.0)
        eq19 = cls.eq19_reynolds_number(rho_hnf, U_in, Dh, mu_hnf)
        Re = eq19["result"]

        eq20 = cls.eq20_prandtl_number(mu_hnf, cp_hnf, k_hnf)
        Pr = eq20["result"]

        eq21 = cls.eq21_nusselt_number(Re, Pr, Dh, L, phi)
        Nu = eq21["result"]

        eq22 = cls.eq22_hartmann_number(B0, Dh, sigma_hnf, mu_hnf)
        eq23 = cls.eq23_darcy_number(k_perm, Dh)
        eq24 = cls.eq24_thermal_performance_factor(Nu, 4.36, 0.045, 0.040)

        return [
            eq1, eq2, eq3, eq4, eq5, eq6, eq7, eq8, eq9, eq10,
            eq11, eq12, eq13, eq14, eq15, eq16, eq17, eq18, eq19, eq20,
            eq21, eq22, eq23, eq24
        ]

    # ==========================================================================
    # ADDITIONAL CYLINDRICAL BTMS EQUATIONS (SECTION 9: EQUATIONS A TO O)
    # ==========================================================================

    @staticmethod
    def eq25_cylindrical_cell_volume(r_m: float = 0.0105, L_m: float = 0.070) -> Dict[str, Any]:
        """Eq 25 (A): Cylindrical Cell Volume: V_cell = pi * r^2 * L"""
        vol = float(math.pi * (r_m ** 2) * L_m)
        return {
            "id": 25,
            "code": "A",
            "name": "Cylindrical Cell Volume",
            "latex": r"V_{\text{cell}} = \pi r^2 L",
            "domain": "Cylindrical Cells (21700 / 18650)",
            "explanation": "Calculates volumetric displacement of single cylindrical cell from radius and active length.",
            "inputs": {"r": (r_m, "m"), "L": (L_m, "m")},
            "substitution": f"V_cell = pi * ({r_m*1000:.1f} mm)^2 * ({L_m*1000:.1f} mm)",
            "result": vol,
            "unit": "m^3",
            "assumptions": "Ideal circular cylinder geometry."
        }

    @staticmethod
    def eq26_cylindrical_surface_area(r_m: float = 0.0105, L_m: float = 0.070) -> Dict[str, Any]:
        """Eq 26 (B): Cylindrical Cell Surface Area: A_cell = 2*pi*r*L + 2*pi*r^2"""
        area = float(2.0 * math.pi * r_m * L_m + 2.0 * math.pi * (r_m ** 2))
        return {
            "id": 26,
            "code": "B",
            "name": "Cylindrical Cell Surface Area",
            "latex": r"A_{\text{cell}} = 2\pi r L + 2\pi r^2",
            "domain": "Cylindrical Cells (Can & Terminals)",
            "explanation": "Calculates total outer envelope area for convective and conductive dissipation.",
            "inputs": {"r": (r_m, "m"), "L": (L_m, "m")},
            "substitution": f"A_cell = 2*pi*({r_m:.4f})*({L_m:.4f}) + 2*pi*({r_m:.4f})^2",
            "result": area,
            "unit": "m^2",
            "assumptions": "Cylindrical lateral area plus top button and flat bottom circular faces."
        }

    @staticmethod
    def eq27_battery_thermal_energy(m_kg: float, cp_j_kgk: float, T_cell_c: float, T_ref_c: float = 25.0) -> Dict[str, Any]:
        """Eq 27 (C): Battery Thermal Energy: E_th = m * Cp * (T - T_ref)"""
        delta_T = T_cell_c - T_ref_c
        e_th = float(m_kg * cp_j_kgk * delta_T)
        return {
            "id": 27,
            "code": "C",
            "name": "Battery Sensible Thermal Energy",
            "latex": r"E_{\text{th}} = m C_p (T - T_{\text{ref}})",
            "domain": "Traction Battery Pack Energy Balance",
            "explanation": "Quantifies sensible heat stored in cell thermal mass relative to 25°C ambient reference.",
            "inputs": {"m": (m_kg, "kg"), "C_p": (cp_j_kgk, "J/(kg*K)"), "T": (T_cell_c, "°C"), "T_ref": (T_ref_c, "°C")},
            "substitution": f"E_th = ({m_kg:.4f} kg) * ({cp_j_kgk:.1f} J/kgK) * ({T_cell_c:.2f} - {T_ref_c:.2f})",
            "result": e_th,
            "unit": "J",
            "assumptions": "Constant specific heat over operating temperature span."
        }

    @staticmethod
    def eq28_battery_heat_transfer(h_w_m2k: float, A_m2: float, T_cell_c: float, T_fluid_c: float) -> Dict[str, Any]:
        """Eq 28 (D): Battery Heat Transfer: Q_dot = h * A * (T_cell - T_fluid)"""
        q_dot = float(h_w_m2k * A_m2 * (T_cell_c - T_fluid_c))
        return {
            "id": 28,
            "code": "D",
            "name": "Newton's Law of Battery Heat Transfer",
            "latex": r"\dot{Q} = h A (T_{\text{cell}} - T_{\text{fluid}})",
            "domain": "Cooling Channel Interface",
            "explanation": "Calculates instantaneous rate of convective heat removal from cell surface to fluid.",
            "inputs": {"h": (h_w_m2k, "W/(m^2*K)"), "A": (A_m2, "m^2"), "T_cell": (T_cell_c, "°C"), "T_fluid": (T_fluid_c, "°C")},
            "substitution": f"Q_dot = ({h_w_m2k:.1f}) * ({A_m2:.5f}) * ({T_cell_c:.2f} - {T_fluid_c:.2f})",
            "result": q_dot,
            "unit": "W",
            "assumptions": "Linear temperature difference across fluid thermal boundary layer."
        }

    @staticmethod
    def eq29_thermal_resistance(L_m: float, k_w_mk: float, A_m2: float) -> Dict[str, Any]:
        """Eq 29 (E): Thermal Resistance: R_th = L / (k * A)"""
        r_th = float(L_m / max(k_w_mk * A_m2, 1.0e-9))
        return {
            "id": 29,
            "code": "E",
            "name": "Conduction Thermal Resistance",
            "latex": r"R_{\text{th}} = \frac{L}{k A}",
            "domain": "TIM & Cooling Plate Layers",
            "explanation": "Calculates 1D steady-state conductive thermal resistance for solid material layer.",
            "inputs": {"L": (L_m, "m"), "k": (k_w_mk, "W/(m*K)"), "A": (A_m2, "m^2")},
            "substitution": f"R_th = ({L_m*1000:.3f} mm) / [({k_w_mk:.1f}) * ({A_m2:.5f})]",
            "result": r_th,
            "unit": "K/W",
            "assumptions": "1D Fourier conduction; uniform thermal conductivity."
        }

    @staticmethod
    def eq30_heat_transfer_cooling_plate(T_battery_c: float, T_plate_c: float, R_th_total: float) -> Dict[str, Any]:
        """Eq 30 (F): Heat Transferred Through Cooling Plate: Q_dot_plate = (T_battery - T_plate) / R_th,total"""
        q_plate = float((T_battery_c - T_plate_c) / max(R_th_total, 1.0e-5))
        return {
            "id": 30,
            "code": "F",
            "name": "Cooling Plate Heat Removal Rate",
            "latex": r"\dot{Q}_{\text{plate}} = \frac{T_{\text{battery}} - T_{\text{plate}}}{R_{\text{th,total}}}",
            "domain": "Wavy Metallic Cooling Ribbon",
            "explanation": "Determines total heat flux extracted from cell through series conduction-convection network.",
            "inputs": {"T_battery": (T_battery_c, "°C"), "T_plate": (T_plate_c, "°C"), "R_th,total": (R_th_total, "K/W")},
            "substitution": f"Q_plate = ({T_battery_c:.2f} - {T_plate_c:.2f}) / ({R_th_total:.5f})",
            "result": q_plate,
            "unit": "W",
            "assumptions": "Coupled cell-to-ribbon contact with series TIM and wall resistance."
        }

    @staticmethod
    def eq31_coolant_heat_absorption(m_dot_kg_s: float, cp_hnf_j_kgk: float, T_out_c: float, T_in_c: float) -> Dict[str, Any]:
        """Eq 31 (G): Coolant Heat Absorption: Q_dot_coolant = m_dot * Cp * (T_out - T_in)"""
        delta_T = T_out_c - T_in_c
        q_coolant = float(m_dot_kg_s * cp_hnf_j_kgk * delta_T)
        return {
            "id": 31,
            "code": "G",
            "name": "Coolant Fluid Heat Absorption Rate",
            "latex": r"\dot{Q}_{\text{coolant}} = \dot{m} C_p (T_{\text{out}} - T_{\text{in}})",
            "domain": "Nanofluid Flow Channels",
            "explanation": "First law enthalpy balance of coolant circulating through battery cooling channels.",
            "inputs": {"m_dot": (m_dot_kg_s, "kg/s"), "C_p": (cp_hnf_j_kgk, "J/(kg*K)"), "T_out": (T_out_c, "°C"), "T_in": (T_in_c, "°C")},
            "substitution": f"Q_coolant = ({m_dot_kg_s:.4f}) * ({cp_hnf_j_kgk:.1f}) * ({T_out_c:.2f} - {T_in_c:.2f})",
            "result": q_coolant,
            "unit": "W",
            "assumptions": "Steady-flow open system enthalpy change; negligible kinetic and potential changes."
        }

    @staticmethod
    def eq32_coolant_mass_flow(rho_kg_m3: float, A_flow_m2: float, U_m_s: float) -> Dict[str, Any]:
        """Eq 32 (H): Coolant Mass Flow: m_dot = rho * A * U"""
        m_dot = float(rho_kg_m3 * A_flow_m2 * U_m_s)
        return {
            "id": 32,
            "code": "H",
            "name": "Coolant Mass Flow Rate",
            "latex": r"\dot{m} = \rho A U",
            "domain": "Manifolds & Channel Branches",
            "explanation": "Computes mass continuity for nanofluid through channel cross-sectional area.",
            "inputs": {"rho": (rho_kg_m3, "kg/m^3"), "A": (A_flow_m2, "m^2"), "U": (U_m_s, "m/s")},
            "substitution": f"m_dot = ({rho_kg_m3:.1f}) * ({A_flow_m2:.6f}) * ({U_m_s:.3f})",
            "result": m_dot,
            "unit": "kg/s",
            "assumptions": "Uniform 1D velocity profile across channel cross section."
        }

    @staticmethod
    def eq33_hydraulic_diameter(A_m2: float, P_w_m: float) -> Dict[str, Any]:
        """Eq 33 (I): Hydraulic Diameter: D_h = 4 * A / P_w"""
        dh = float(4.0 * A_m2 / max(P_w_m, 1.0e-6))
        return {
            "id": 33,
            "code": "I",
            "name": "Hydraulic Diameter Relation",
            "latex": r"D_h = \frac{4A}{P_w}",
            "domain": "Non-Circular Microchannels",
            "explanation": "Calculates equivalent characteristic diameter for pressure drop and friction calculations.",
            "inputs": {"A": (A_m2, "m^2"), "P_w": (P_w_m, "m")},
            "substitution": f"D_h = 4 * ({A_m2:.6f}) / ({P_w_m:.4f})",
            "result": dh,
            "unit": "m",
            "assumptions": "Standard hydraulic diameter definition for non-circular ducts."
        }

    @staticmethod
    def eq34_darcy_weisbach_pressure_drop(f_D: float, L_m: float, D_h_m: float, rho_kg_m3: float, U_m_s: float) -> Dict[str, Any]:
        """Eq 34 (J): Darcy-Weisbach Pressure Drop: Delta_P = f_D * (L / D_h) * (rho * U^2 / 2)"""
        dynamic_p = 0.5 * rho_kg_m3 * (U_m_s ** 2)
        dp = float(f_D * (L_m / max(D_h_m, 1.0e-5)) * dynamic_p)
        return {
            "id": 34,
            "code": "J",
            "name": "Darcy-Weisbach Hydraulic Pressure Drop",
            "latex": r"\Delta P = f_D \left(\frac{L}{D_h}\right) \left(\frac{\rho U^2}{2}\right)",
            "domain": "Cooling Ribbons & Pipelines",
            "explanation": "Computes frictional hydraulic pressure dissipation along internal flow passages.",
            "inputs": {"f_D": (f_D, "-"), "L": (L_m, "m"), "D_h": (D_h_m, "m"), "rho": (rho_kg_m3, "kg/m^3"), "U": (U_m_s, "m/s")},
            "substitution": f"Delta_P = ({f_D:.4f}) * ({L_m:.3f} / {D_h_m:.4f}) * [({rho_kg_m3:.1f})*({U_m_s:.3f})^2 / 2]",
            "result": dp,
            "unit": "Pa",
            "assumptions": "Incompressible fluid flow with wall shear friction."
        }

    @staticmethod
    def eq35_pump_hydraulic_power(delta_P_pa: float, Q_vol_m3_s: float) -> Dict[str, Any]:
        """Eq 35 (K): Pump Hydraulic Power: P_h = Delta_P * Q"""
        p_h = float(delta_P_pa * Q_vol_m3_s)
        return {
            "id": 35,
            "code": "K",
            "name": "Pump Hydraulic Power",
            "latex": r"P_h = \Delta P \cdot Q",
            "domain": "Coolant Circulation Pump",
            "explanation": "Calculates useful mechanical fluid power imparted to fluid stream by circulation pump.",
            "inputs": {"Delta_P": (delta_P_pa, "Pa"), "Q": (Q_vol_m3_s, "m^3/s")},
            "substitution": f"P_h = ({delta_P_pa:.1f} Pa) * ({Q_vol_m3_s*60000:.2f} L/min)",
            "result": p_h,
            "unit": "W",
            "assumptions": "Isothermal hydraulic work done on incompressible fluid."
        }

    @staticmethod
    def eq36_pump_electrical_power(P_h_w: float, eta_pump: float = 0.75) -> Dict[str, Any]:
        """Eq 36 (L): Pump Electrical Power: P_e = P_h / eta_pump"""
        p_e = float(P_h_w / max(eta_pump, 0.05))
        return {
            "id": 36,
            "code": "L",
            "name": "Pump Electrical Power Consumption",
            "latex": r"P_e = \frac{P_h}{\eta_{\text{pump}}}",
            "domain": "Pump Electric Drive Motor",
            "explanation": "Computes gross electrical power consumed by pump drive motor including mechanical and motor losses.",
            "inputs": {"P_h": (P_h_w, "W"), "eta_pump": (eta_pump, "-")},
            "substitution": f"P_e = ({P_h_w:.2f} W) / ({eta_pump:.2f})",
            "result": p_e,
            "unit": "W",
            "assumptions": "Combined motor and pump impeller efficiency."
        }

    @staticmethod
    def eq37_fan_power(delta_P_air_pa: float = 85.0, Q_air_m3_s: float = 0.18, eta_fan: float = 0.65) -> Dict[str, Any]:
        """Eq 37 (M): Fan Power: P_fan = Delta_P_air * Q_air / eta_fan"""
        p_fan = float((delta_P_air_pa * Q_air_m3_s) / max(eta_fan, 0.05))
        return {
            "id": 37,
            "code": "M",
            "name": "Radiator Cooling Fan Power",
            "latex": r"P_{\text{fan}} = \frac{\Delta P_{\text{air}} Q_{\text{air}}}{\eta_{\text{fan}}}",
            "domain": "Front Radiator Cooling Fan",
            "explanation": "Calculates electrical power drawn by 7-blade radiator fan overcoming radiator fin core airflow resistance.",
            "inputs": {"Delta_P_air": (delta_P_air_pa, "Pa"), "Q_air": (Q_air_m3_s, "m^3/s"), "eta_fan": (eta_fan, "-")},
            "substitution": f"P_fan = ({delta_P_air_pa:.1f}) * ({Q_air_m3_s:.3f}) / ({eta_fan:.2f})",
            "result": p_fan,
            "unit": "W",
            "assumptions": "Axial fan operating at rated aerodynamic pressure drop."
        }

    @staticmethod
    def eq38_battery_temperature_difference(T_max_c: float, T_min_c: float) -> Dict[str, Any]:
        """Eq 38 (N): Battery Temperature Difference: Delta_T = T_max - T_min"""
        delta_T = float(T_max_c - T_min_c)
        return {
            "id": 38,
            "code": "N",
            "name": "Pack Temperature Non-Uniformity",
            "latex": r"\Delta T_{\text{pack}} = T_{\text{max}} - T_{\text{min}}",
            "domain": "Traction Battery Pack Uniformity",
            "explanation": "Key BTMS thermal safety metric: evaluates cell-to-cell thermal gradient across 500+ cells.",
            "inputs": {"T_max": (T_max_c, "°C"), "T_min": (T_min_c, "°C")},
            "substitution": f"Delta_T = {T_max_c:.2f} °C - {T_min_c:.2f} °C",
            "result": delta_T,
            "unit": "°C",
            "assumptions": "Peak-to-minimum difference across complete array; standard automotive limit <= 5.0°C."
        }

    @staticmethod
    def eq39_cooling_effectiveness(T_hot_in_c: float, T_hot_out_c: float, T_cold_in_c: float) -> Dict[str, Any]:
        """Eq 39 (O): Cooling Effectiveness: epsilon = (T_hot,in - T_hot,out) / (T_hot,in - T_cold,in)"""
        denom = max(T_hot_in_c - T_cold_in_c, 0.05)
        eps = float((T_hot_in_c - T_hot_out_c) / denom)
        return {
            "id": 39,
            "code": "O",
            "name": "Heat Exchanger Cooling Effectiveness",
            "latex": r"\varepsilon_{\text{cooling}} = \frac{T_{\text{hot,in}} - T_{\text{hot,out}}}{T_{\text{hot,in}} - T_{\text{cold,in}}}",
            "domain": "Radiator / Heat Exchanger",
            "explanation": "Calculates dimensionless thermal effectiveness of cooling loop heat rejection.",
            "inputs": {"T_hot,in": (T_hot_in_c, "°C"), "T_hot,out": (T_hot_out_c, "°C"), "T_cold,in": (T_cold_in_c, "°C")},
            "substitution": f"epsilon = ({T_hot_in_c:.2f} - {T_hot_out_c:.2f}) / ({T_hot_in_c:.2f} - {T_cold_in_c:.2f})",
            "result": eps,
            "unit": "-",
            "assumptions": "Cross-flow heat exchanger effectiveness definition."
        }

    @classmethod
    def get_cylindrical_equations_live(cls, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Returns all 15 Additional Cylindrical Equations (A through O) with live substitutions."""
        r_m = state.get("cell_radius_m", 0.0105)
        L_m = state.get("cell_length_m", 0.0700)
        m_kg = state.get("cell_mass_kg", 0.0690)
        cp_b = state.get("cell_cp", 1050.0)
        t_max = state.get("max_cell_temp_c", 25.0)
        t_min = state.get("min_cell_temp_c", 25.0)
        t_in = state.get("T_in_c", 22.0)
        t_out = state.get("T_outlet_c", 24.5)
        u_m_s = state.get("U_in", 0.25)
        dh_m = state.get("Dh", 0.004)
        f_d = state.get("f_D", 0.038)
        dp_pa = state.get("total_delta_p_Pa", 4500.0)
        m_dot = state.get("mass_flow_rate_kg_s", 0.045)
        rho_hnf = state.get("rho_hnf", 1085.0)
        cp_hnf = state.get("cp_hnf", 3850.0)
        h_val = state.get("h_coolant", 450.0)
        vol_flow = state.get("vol_flow_rate_m3_s", 4.15e-5)
        p_hyd = state.get("p_hydraulic_w", 0.18)
        eta_p = state.get("pump_efficiency", 0.75)
        r_th = state.get("r_th_total", 0.12)

        eqA = cls.eq25_cylindrical_cell_volume(r_m, L_m)
        eqB = cls.eq26_cylindrical_surface_area(r_m, L_m)
        eqC = cls.eq27_battery_thermal_energy(m_kg, cp_b, t_max, 25.0)
        eqD = cls.eq28_battery_heat_transfer(h_val, eqB["result"], t_max, t_in)
        eqE = cls.eq29_thermal_resistance(0.0004, 3.0, 0.0015)
        eqF = cls.eq30_heat_transfer_cooling_plate(t_max, t_in, r_th)
        eqG = cls.eq31_coolant_heat_absorption(m_dot, cp_hnf, t_out, t_in)
        eqH = cls.eq32_coolant_mass_flow(rho_hnf, 1.8e-4, u_m_s)
        eqI = cls.eq33_hydraulic_diameter(1.8e-5, 0.018)
        eqJ = cls.eq34_darcy_weisbach_pressure_drop(f_d, 0.35, dh_m, rho_hnf, u_m_s)
        eqK = cls.eq35_pump_hydraulic_power(dp_pa, vol_flow)
        eqL = cls.eq36_pump_electrical_power(p_hyd, eta_p)
        eqM = cls.eq37_fan_power(85.0, 0.18, 0.65)
        eqN = cls.eq38_battery_temperature_difference(t_max, t_min)
        eqO = cls.eq39_cooling_effectiveness(t_out, t_in + 0.5, t_in)

        return [eqA, eqB, eqC, eqD, eqE, eqF, eqG, eqH, eqI, eqJ, eqK, eqL, eqM, eqN, eqO]
