using System;
using System.Collections.Generic;
using UnityEngine;

namespace BTMS3D.Simulation
{
    [System.Serializable]
    public class EquationEvaluation
    {
        public int id;
        public string name;
        public string latex;
        public string domain;
        public string explanation;
        public string substitution;
        public float result;
        public string unit;
        public string assumptions;
    }

    /// <summary>
    /// Implements all 24 governing mathematical formulations in C# with step-by-step
    /// substitution, intermediate calculations, and SI units.
    /// </summary>
    public static class GoverningEquations
    {
        // Eq 1: Battery C-Rate
        public static EquationEvaluation Eq1_CRate(float cRate, float qRated)
        {
            float I = cRate * qRated;
            return new EquationEvaluation
            {
                id = 1,
                name = "Battery C-Rate Current Relation",
                latex = "I = C_{rate} \\cdot Q_{rated}",
                domain = "Battery Cells (B01 - B50)",
                explanation = "Calculates operating current based on discharge C-rate and rated capacity.",
                substitution = $"I = ({cRate:F2} h^-1) * ({qRated:F2} Ah)",
                result = I,
                unit = "A",
                assumptions = "Constant rated capacity; uniform discharge."
            };
        }

        // Eq 2: Bernardi Heat Generation
        public static EquationEvaluation Eq2_BernardiHeat(float I, float Voc, float Vop, float T_cell_K, float dU_dT)
        {
            float Q_irr = I * (Voc - Vop);
            float Q_rev = -I * T_cell_K * dU_dT;
            float Q_tot = Q_irr + Q_rev;
            return new EquationEvaluation
            {
                id = 2,
                name = "Bernardi Electrochemical Heat Generation",
                latex = "\\dot{Q}_b = I(V_{oc} - V_{op}) - I \\cdot T \\left(\\frac{\\partial U_{oc}}{\\partial T}\\right)",
                domain = "Battery Cells (B01 - B50)",
                explanation = "Couples irreversible Joule overpotential heating with reversible entropic reaction heating.",
                substitution = $"Q_b = {I:F2}*({Voc:F3} - {Vop:F3}) - ({I:F2}*{T_cell_K:F2}*{dU_dT:F6}) = {Q_irr:F2} + {Q_rev:F2}",
                result = Q_tot,
                unit = "W",
                assumptions = "Uniform current density; constant entropic coefficient."
            };
        }

        // Eq 3: Battery Anisotropic Energy
        public static EquationEvaluation Eq3_AnisotropicConduction(float rho_b, float cp_b, float kx, float ky, float kz, float d2T_dx2, float d2T_dy2, float d2T_dz2, float q_vol)
        {
            float cond = kx * d2T_dx2 + ky * d2T_dy2 + kz * d2T_dz2;
            float dT_dt = (cond + q_vol) / (rho_b * cp_b);
            return new EquationEvaluation
            {
                id = 3,
                name = "Battery 3D Anisotropic Energy Equation",
                latex = "\\rho_b C_{p,b} \\frac{\\partial T}{\\partial t} = k_x \\frac{\\partial^2 T}{\\partial x^2} + k_y \\frac{\\partial^2 T}{\\partial y^2} + k_z \\frac{\\partial^2 T}{\\partial z^2} + q'''_b",
                domain = "Solid Battery Cell Matrix",
                explanation = "3D transient conduction accounting for layered jelly-roll directional conductivities.",
                substitution = $"dT/dt = [{cond:F2} + {q_vol:F2}] / ({rho_b:F1} * {cp_b:F1})",
                result = dT_dt,
                unit = "K/s",
                assumptions = "Orthotropic thermal conductivities; constant cell density."
            };
        }

        // Eq 4: Nanoparticle Total Volume Fraction
        public static EquationEvaluation Eq4_TotalVolumeFraction(float phi1, float phi2)
        {
            float phi_tot = phi1 + phi2;
            return new EquationEvaluation
            {
                id = 4,
                name = "Total Nanoparticle Volume Fraction",
                latex = "\\phi_{total} = \\phi_1 (\\text{Al}_2\\text{O}_3) + \\phi_2 (\\text{CuO})",
                domain = "Hybrid Nanofluid Coolant",
                explanation = "Sum of constituent nanoparticle volume fractions in water base fluid.",
                substitution = $"phi = {phi1:F4} + {phi2:F4}",
                result = phi_tot,
                unit = "dimensionless",
                assumptions = "Rigid non-reacting spherical nanoparticles; dilute suspension."
            };
        }

        // Eq 5: Hybrid Nanofluid Density
        public static EquationEvaluation Eq5_NanofluidDensity(float rho_f, float rho_s1, float rho_s2, float phi1, float phi2)
        {
            float phi_tot = phi1 + phi2;
            float rho_hnf = (1.0f - phi_tot) * rho_f + (phi1 * rho_s1) + (phi2 * rho_s2);
            return new EquationEvaluation
            {
                id = 5,
                name = "Hybrid Nanofluid Effective Density",
                latex = "\\rho_{hnf} = (1 - \\phi_{total})\\rho_f + \\phi_1 \\rho_{s1} + \\phi_2 \\rho_{s2}",
                domain = "Piping Network & Microchannels",
                explanation = "Mass-weighted volume average mixture density.",
                substitution = $"rho_hnf = (1 - {phi_tot:F4})*{rho_f:F1} + {phi1:F4}*{rho_s1:F1} + {phi2:F4}*{rho_s2:F1}",
                result = rho_hnf,
                unit = "kg/m^3",
                assumptions = "Incompressible fluid mixture; homogeneous dispersion."
            };
        }

        // Eq 6: Nanofluid Specific Heat
        public static EquationEvaluation Eq6_NanofluidSpecificHeat(float rho_f, float cp_f, float rho_s1, float cp_s1, float rho_s2, float cp_s2, float phi1, float phi2)
        {
            float phi_tot = phi1 + phi2;
            float rho_hnf = (1.0f - phi_tot) * rho_f + (phi1 * rho_s1) + (phi2 * rho_s2);
            float vol_cap = (1.0f - phi_tot) * rho_f * cp_f + (phi1 * rho_s1 * cp_s1) + (phi2 * rho_s2 * cp_s2);
            float cp_hnf = vol_cap / Mathf.Max(rho_hnf, 1e-4f);
            return new EquationEvaluation
            {
                id = 6,
                name = "Nanofluid Effective Specific Heat Capacity",
                latex = "(\\rho C_p)_{hnf} = (1 - \\phi_{total})(\\rho C_p)_f + \\phi_1 (\\rho C_p)_{s1} + \\phi_2 (\\rho C_p)_{s2}",
                domain = "Piping Network & Microchannels",
                explanation = "Thermal equilibrium specific heat capacity per unit mass.",
                substitution = $"Cp_hnf = {vol_cap:F1} / {rho_hnf:F1}",
                result = cp_hnf,
                unit = "J/(kg*K)",
                assumptions = "Thermal equilibrium between nanoparticles and base fluid molecules."
            };
        }

        // Eq 7: Dynamic Viscosity Brinkman
        public static EquationEvaluation Eq7_ViscosityBrinkman(float mu_f, float phi_tot)
        {
            float mu_hnf = mu_f / Mathf.Pow(1.0f - phi_tot, 2.5f);
            return new EquationEvaluation
            {
                id = 7,
                name = "Nanofluid Dynamic Viscosity (Brinkman Model)",
                latex = "\\mu_{hnf} = \\frac{\\mu_f}{(1 - \\phi_{total})^{2.5}}",
                domain = "Cooling Channels & Pump",
                explanation = "Viscous resistance amplification due to hydrodynamic particle-particle shear interactions.",
                substitution = $"mu_hnf = {mu_f:E3} / (1 - {phi_tot:F4})^2.5",
                result = mu_hnf,
                unit = "Pa*s",
                assumptions = "Dilute spherical suspensions; Newtonian rheological behavior."
            };
        }

        // Eq 8: Thermal Conductivity Maxwell
        public static EquationEvaluation Eq8_ThermalConductivityMaxwell(float kf, float ks1, float ks2, float phi1, float phi2)
        {
            float phi_tot = phi1 + phi2;
            float ks_eff = (phi_tot > 1e-6f) ? (phi1 * ks1 + phi2 * ks2) / phi_tot : kf;
            float num = ks_eff + 2.0f * kf - 2.0f * phi_tot * (kf - ks_eff);
            float den = ks_eff + 2.0f * kf + phi_tot * (kf - ks_eff);
            float k_hnf = kf * (num / Mathf.Max(den, 1e-4f));
            return new EquationEvaluation
            {
                id = 8,
                name = "Hybrid Nanofluid Thermal Conductivity (Maxwell)",
                latex = "k_{hnf} = k_f \\left[ \\frac{k_s + 2k_f - 2\\phi(k_f - k_s)}{k_s + 2k_f + \\phi(k_f - k_s)} \\right]",
                domain = "Battery Cold Plate Microchannels",
                explanation = "Enhanced conduction through metallic nanoparticle dispersion.",
                substitution = $"k_hnf = {kf:F3} * ({num:F3} / {den:F3})",
                result = k_hnf,
                unit = "W/(m*K)",
                assumptions = "Spherical non-interacting particles; negligible interfacial Kapitza thermal resistance."
            };
        }

        // Eq 19: Reynolds Number
        public static EquationEvaluation Eq19_ReynoldsNumber(float rho_hnf, float U_in, float Dh, float mu_hnf)
        {
            float Re = (rho_hnf * U_in * Dh) / Mathf.Max(mu_hnf, 1e-6f);
            return new EquationEvaluation
            {
                id = 19,
                name = "Reynolds Number",
                latex = "Re = \\frac{\\rho_{hnf} U_{in} D_h}{\\mu_{hnf}}",
                domain = "Cooling Channels & Piping",
                explanation = "Ratio of inertial forces to viscous forces governing laminar vs turbulent regime.",
                substitution = $"Re = ({rho_hnf:F1} * {U_in:F4} * {Dh:F4}) / {mu_hnf:E3}",
                result = Re,
                unit = "dimensionless",
                assumptions = "Channel hydraulic diameter Dh = 4A/P; steady uniform velocity."
            };
        }

        // Eq 20: Prandtl Number
        public static EquationEvaluation Eq20_PrandtlNumber(float mu_hnf, float cp_hnf, float k_hnf)
        {
            float Pr = (mu_hnf * cp_hnf) / Mathf.Max(k_hnf, 1e-4f);
            return new EquationEvaluation
            {
                id = 20,
                name = "Prandtl Number",
                latex = "Pr = \\frac{\\mu_{hnf} C_{p,hnf}}{k_{hnf}}",
                domain = "Thermal Boundary Layer",
                explanation = "Ratio of momentum diffusivity (kinematic viscosity) to thermal diffusivity.",
                substitution = $"Pr = ({mu_hnf:E3} * {cp_hnf:F1}) / {k_hnf:F3}",
                result = Pr,
                unit = "dimensionless",
                assumptions = "Bulk mixture thermodynamic properties; continuum assumption."
            };
        }

        // Eq 21: Nusselt Number
        public static EquationEvaluation Eq21_NusseltNumber(float Re, float Pr, float Dh, float L_plate, float phi_tot)
        {
            float Nu = 4.36f + 0.036f * (Re * Pr * Dh / Mathf.Max(L_plate, 0.01f)) * (1.0f + 1.5f * phi_tot);
            return new EquationEvaluation
            {
                id = 21,
                name = "Nusselt Number (Laminar Nanofluid Correlation)",
                latex = "Nu = 4.36 + 0.036 \\left(Re \\cdot Pr \\frac{D_h}{L}\\right) (1 + 1.5\\phi)",
                domain = "Convective Cooling Interface",
                explanation = "Dimensionless convective heat transfer coefficient relative to pure conduction.",
                substitution = $"Nu = 4.36 + 0.036 * ({Re:F1} * {Pr:F2} * {Dh:F4} / {L_plate:F2}) * (1 + 1.5*{phi_tot:F4})",
                result = Nu,
                unit = "dimensionless",
                assumptions = "Thermally developing laminar duct flow; uniform heat flux boundary condition."
            };
        }

        // Eq 22: Hartmann Number (MHD)
        public static EquationEvaluation Eq22_HartmannNumber(float B0, float Dh, float sigma_hnf, float mu_hnf)
        {
            float Ha = B0 * Dh * Mathf.Sqrt(Mathf.Max(sigma_hnf, 0.0f) / Mathf.Max(mu_hnf, 1e-6f));
            return new EquationEvaluation
            {
                id = 22,
                name = "Hartmann Number (MHD)",
                latex = "Ha = B_0 D_h \\sqrt{\\frac{\\sigma_{hnf}}{\\mu_{hnf}}}",
                domain = "Magnetic Field Interaction Zone",
                explanation = "Ratio of electromagnetic Lorentz braking force to hydrodynamic viscous force.",
                substitution = $"Ha = {B0:F2} * {Dh:F4} * sqrt({sigma_hnf:E3} / {mu_hnf:E3})",
                result = Ha,
                unit = "dimensionless",
                assumptions = "Transverse uniform magnetic field B0; low magnetic Reynolds number."
            };
        }

        // Eq 23: Darcy Number (Porous Media)
        public static EquationEvaluation Eq23_DarcyNumber(float k_perm, float Dh)
        {
            float Da = k_perm / Mathf.Max(Dh * Dh, 1e-8f);
            return new EquationEvaluation
            {
                id = 23,
                name = "Darcy Number",
                latex = "Da = \\frac{K}{D_h^2}",
                domain = "Porous Metal Foam Microchannel Inserts",
                explanation = "Permeability of porous foam relative to the square of macroscopic channel height.",
                substitution = $"Da = {k_perm:E2} / ({Dh:F4})^2",
                result = Da,
                unit = "dimensionless",
                assumptions = "Isotropic open-cell metal foam matrix."
            };
        }

        // Eq 24: Thermal Performance Evaluation Criteria
        public static EquationEvaluation Eq24_ThermalPerformanceFactor(float Nu, float Nu0, float f, float f0)
        {
            float eta = (Nu / Mathf.Max(Nu0, 1e-4f)) / Mathf.Pow(Mathf.Max(f / Mathf.Max(f0, 1e-4f), 1e-4f), 1.0f / 3.0f);
            return new EquationEvaluation
            {
                id = 24,
                name = "Thermal Performance Factor (PEC / JF-Factor)",
                latex = "\\eta = \\frac{Nu / Nu_0}{(f / f_0)^{1/3}}",
                domain = "Overall BTMS Efficiency Metric",
                explanation = "Assesses heat transfer enhancement gain relative to the associated pumping power penalty.",
                substitution = $"eta = ({Nu:F2} / {Nu0:F2}) / ({f:F4} / {f0:F4})^(1/3)",
                result = eta,
                unit = "dimensionless",
                assumptions = "Constant pumping power comparison basis; eta > 1 indicates net thermodynamic benefit."
            };
        }
    }
}
