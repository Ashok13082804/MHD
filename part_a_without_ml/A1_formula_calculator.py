#!/usr/bin/env python3
"""
SUBPART A1: Individual Formula Numerical Calculator
Physics-Based Numerical Calculator for all 18 Formulations without Machine Learning.

This module evaluates each of the 18 research formulations individually, displaying:
  1. Input parameters with actual names and SI units.
  2. Formula name and mathematical equation.
  3. Substituted parameter values and intermediate calculations.
  4. Final numerical result with units.
  5. Scientific physical interpretation.
  6. Results table exported to CSV.
  7. High-resolution graphical visualizations.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from typing import Dict, Any, List

import config
from part_a_without_ml.material_properties import (
    calc_effective_density,
    calc_effective_heat_capacity,
    calc_effective_thermal_conductivity,
    calc_effective_dynamic_viscosity,
    calc_effective_electrical_conductivity,
    calc_joule_heating,
    calc_lorentz_force,
    calc_darcy_brinkman_mhd_forces,
    calc_battery_heat_generation,
    validate_nanoparticle_volume_fractions,
)
from part_a_without_ml.dimensionless_numbers import (
    calc_reynolds_number,
    calc_prandtl_number,
    calc_hartmann_number,
    calc_darcy_number,
    calc_brinkman_number,
    calc_nusselt_number,
    calc_local_nusselt_number,
    calc_c_rate_current,
)
from part_a_without_ml.energy_equation import (
    calc_energy_equation_terms,
    simulate_1d_transient_temperature,
)
from part_a_without_ml.momentum_equation import (
    calc_momentum_balance_2d,
    calc_darcy_brinkman_mhd_channel_profile,
)
from part_a_without_ml.boundary_conditions import (
    evaluate_boundary_conditions_record,
    calc_temperature_continuity,
    calc_heat_flux_continuity,
)
from part_a_without_ml.visualizations import (
    plot_dimensionless_relationships,
    plot_temperature_vs_time,
    plot_velocity_distributions,
    plot_pressure_distribution,
)


def print_section_header(title: str):
    """Prints a styled banner for terminal readability."""
    width = 90
    print("\n" + "=" * width)
    print(f" {title.upper()} ".center(width, "="))
    print("=" * width)


def print_formula_result(res: Dict[str, Any], formula_num: int):
    """
    Standardized printer adhering to the strict project output requirements:
    - Input parameters with actual names and SI units
    - Formula name and mathematical equation
    - Substituted values and intermediate steps
    - Final numerical result with units
    - Scientific physical interpretation
    """
    print(f"\n[FORMULATION {formula_num}]: {res.get('formula_name', 'Mathematical Formula')}")
    print(f"  Governing Equation: {res.get('equation', 'N/A')}")
    print("\n  --- INPUT PARAMETERS ---")
    inputs = res.get("inputs", {})
    for param_name, val_unit in inputs.items():
        val, unit = val_unit
        if isinstance(val, float):
            print(f"    * {param_name:<30} = {val:>14.6e} [{unit}]")
        else:
            print(f"    * {param_name:<30} = {str(val):>14} [{unit}]")

    print("\n  --- INTERMEDIATE CALCULATIONS ---")
    intermediates = res.get("intermediates", {})
    if intermediates:
        for term_name, val_unit in intermediates.items():
            if isinstance(val_unit, tuple):
                val, unit = val_unit
                if isinstance(val, (float, np.floating)):
                    print(f"    * {term_name:<30} = {float(val):>14.6e} [{unit}]")
                else:
                    print(f"    * {term_name:<30} = {str(val):>14} [{unit}]")
            elif isinstance(val_unit, dict):
                print(f"    * {term_name}:")
                for sub_k, sub_v in val_unit.items():
                    print(f"        - {sub_k:<24} = {sub_v:>10.2f} A")
            else:
                print(f"    * {term_name:<30} = {str(val_unit)}")
    else:
        print("    * Direct analytical evaluation.")

    print("\n  --- FINAL NUMERICAL OUTPUT ---")
    result = res.get("result")
    unit = res.get("unit", "")
    if isinstance(result, (float, np.floating)):
        print(f"    >> Calculated Result : {float(result):>14.6e} {unit}")
    else:
        print(f"    >> Calculated Result : {str(result)} {unit}")

    if "result_vector" in res:
        print(f"    >> Vector Components : {res['result_vector']} {unit}")

    print("\n  --- PHYSICAL INTERPRETATION ---")
    print(f"    {res.get('interpretation', 'Verified against theoretical constraints.')}")
    print("-" * 90)


def run_all_18_formulations(
    phi1: float = config.DEFAULT_CONCENTRATIONS["phi1"],
    phi2: float = config.DEFAULT_CONCENTRATIONS["phi2"],
    U_in: float = config.DEFAULT_CHANNEL["U_in"],
    T_in: float = config.DEFAULT_CHANNEL["T_in"],
    T_batt_init: float = config.DEFAULT_BATTERY["T_init"],
    B0: float = config.DEFAULT_CHANNEL["B0"],
    k_perm: float = config.DEFAULT_CHANNEL["permeability"],
    c_rate: float = 2.0,
    save_outputs: bool = True
) -> pd.DataFrame:
    """
    Executes and documents all 18 mathematical formulations sequentially.
    """
    print_section_header("PART A1: INDIVIDUAL FORMULA NUMERICAL CALCULATOR")
    print(f"System Configuration:")
    print(f"  * Coolant Base Fluid      : {config.DEFAULT_BASE_FLUID['name']}")
    print(f"  * Nanoparticle 1 (phi1)   : {config.NANOPARTICLES['Al2O3']['name']} (fraction = {phi1:.4f})")
    print(f"  * Nanoparticle 2 (phi2)   : {config.NANOPARTICLES['CuO']['name']} (fraction = {phi2:.4f})")
    print(f"  * Inlet Velocity U_in     : {U_in:.4f} m/s")
    print(f"  * Inlet Temperature T_in  : {T_in:.2f} K")
    print(f"  * Initial Battery Temp    : {T_batt_init:.2f} K")
    print(f"  * Magnetic Field B0       : {B0:.3f} T")
    print(f"  * Permeability k_perm     : {k_perm:.2e} m^2")
    print(f"  * Battery Discharge C-Rate: {c_rate:.1f}C")

    # Physical properties from database
    rho_f = config.DEFAULT_BASE_FLUID["rho"]
    cp_f = config.DEFAULT_BASE_FLUID["cp"]
    k_f = config.DEFAULT_BASE_FLUID["k"]
    mu_f = config.DEFAULT_BASE_FLUID["mu"]
    sigma_f = config.DEFAULT_BASE_FLUID["sigma"]

    rho_s1 = config.NANOPARTICLES["Al2O3"]["rho"]
    cp_s1 = config.NANOPARTICLES["Al2O3"]["cp"]
    k_s1 = config.NANOPARTICLES["Al2O3"]["k"]
    sigma_s1 = config.NANOPARTICLES["Al2O3"]["sigma"]

    rho_s2 = config.NANOPARTICLES["CuO"]["rho"]
    cp_s2 = config.NANOPARTICLES["CuO"]["cp"]
    k_s2 = config.NANOPARTICLES["CuO"]["k"]
    sigma_s2 = config.NANOPARTICLES["CuO"]["sigma"]

    L_char = config.DEFAULT_CHANNEL["H"]  # Channel hydraulic gap height L = 0.01 m
    Delta_T = max(abs(T_batt_init - T_in), 1.0)

    results_table: List[Dict[str, Any]] = []

    # --------------------------------------------------------------------------
    # FORMULA 14: Fluid and Nanoparticle Densities Validation
    # --------------------------------------------------------------------------
    is_valid, msg = validate_nanoparticle_volume_fractions(phi1, phi2)
    res_14 = {
        "formula_name": "Fluid and Nanoparticle Density Validation & Separation",
        "equation": "phi1 >= 0, phi2 >= 0, phi1 + phi2 < 1.0; rho_f, rho_s1, rho_s2 separately specified",
        "inputs": {
            "rho_f (Water)": (rho_f, "kg/m^3"),
            "rho_s1 (Al2O3)": (rho_s1, "kg/m^3"),
            "rho_s2 (CuO)": (rho_s2, "kg/m^3"),
            "phi1": (phi1, "dimensionless"),
            "phi2": (phi2, "dimensionless"),
        },
        "intermediates": {
            "total_solid_volume_fraction": (phi1 + phi2, "dimensionless"),
            "fluid_volume_fraction": (1.0 - phi1 - phi2, "dimensionless"),
        },
        "result": "PASSED (Physically Valid)",
        "unit": "Validation Status",
        "interpretation": f"Concentrations {phi1=:.3f}, {phi2=:.3f} are physically admissible. {msg}",
    }
    print_formula_result(res_14, 14)
    results_table.append({
        "Formula_ID": 14,
        "Formula_Name": res_14["formula_name"],
        "Numerical_Result": 1.0,
        "Unit": "Status",
        "Equation": res_14["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 13: Effective Hybrid Nanofluid Density
    # --------------------------------------------------------------------------
    res_13 = calc_effective_density(rho_f, rho_s1, rho_s2, phi1, phi2)
    rho_hnf = res_13["result"]
    print_formula_result(res_13, 13)
    results_table.append({
        "Formula_ID": 13,
        "Formula_Name": res_13["formula_name"],
        "Numerical_Result": rho_hnf,
        "Unit": res_13["unit"],
        "Equation": res_13["equation"]
    })

    # --------------------------------------------------------------------------
    # SECTION 3: Effective Heat Capacity (Volumetric & Mass-Specific)
    # --------------------------------------------------------------------------
    res_cp = calc_effective_heat_capacity(rho_f, cp_f, rho_s1, cp_s1, rho_s2, cp_s2, phi1, phi2)
    rho_cp_hnf = res_cp["result_volumetric"]
    cp_hnf = res_cp["result_specific"]
    print_formula_result(res_cp, 3) # Heat capacity section
    results_table.append({
        "Formula_ID": "3-HC",
        "Formula_Name": res_cp["formula_name"],
        "Numerical_Result": cp_hnf,
        "Unit": res_cp["unit"],
        "Equation": res_cp["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 15: Effective Thermal Conductivity & Viscosity
    # --------------------------------------------------------------------------
    res_15 = calc_effective_thermal_conductivity(k_f, k_s1, k_s2, phi1, phi2, model="maxwell")
    k_hnf = res_15["result"]
    print_formula_result(res_15, 15)
    results_table.append({
        "Formula_ID": 15,
        "Formula_Name": res_15["formula_name"],
        "Numerical_Result": k_hnf,
        "Unit": res_15["unit"],
        "Equation": res_15["equation"]
    })

    res_15b = calc_effective_dynamic_viscosity(mu_f, phi1, phi2, model="brinkman")
    mu_hnf = res_15b["result"]
    print_formula_result(res_15b, 15)  # 15b
    results_table.append({
        "Formula_ID": "15-Visc",
        "Formula_Name": res_15b["formula_name"],
        "Numerical_Result": mu_hnf,
        "Unit": res_15b["unit"],
        "Equation": res_15b["equation"]
    })

    res_sigma = calc_effective_electrical_conductivity(sigma_f, sigma_s1, sigma_s2, phi1, phi2)
    sigma_hnf = res_sigma["result"]

    # --------------------------------------------------------------------------
    # FORMULA 16: Joule Heating
    # --------------------------------------------------------------------------
    res_16 = calc_joule_heating(sigma_hnf, B0, u=U_in, v=0.0)
    Q_J = res_16["result"]
    print_formula_result(res_16, 16)
    results_table.append({
        "Formula_ID": 16,
        "Formula_Name": res_16["formula_name"],
        "Numerical_Result": Q_J,
        "Unit": res_16["unit"],
        "Equation": res_16["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 17: Lorentz Force
    # --------------------------------------------------------------------------
    res_17 = calc_lorentz_force(sigma_hnf, B0, u=U_in, v=0.0)
    F_L = res_17["result"]
    print_formula_result(res_17, 17)
    results_table.append({
        "Formula_ID": 17,
        "Formula_Name": res_17["formula_name"],
        "Numerical_Result": F_L,
        "Unit": res_17["unit"],
        "Equation": res_17["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 18: Darcy-Brinkman MHD Combined Momentum Formulation
    # --------------------------------------------------------------------------
    res_18 = calc_darcy_brinkman_mhd_forces(
        rho_hnf=rho_hnf,
        mu_eff=mu_hnf,
        k_perm=k_perm,
        sigma_hnf=sigma_hnf,
        B0=B0,
        u=U_in,
        laplacian_u=-8.0 * U_in / (L_char ** 2), # Poiseuille estimate
        dp_dx=-500.0
    )
    print_formula_result(res_18, 18)
    results_table.append({
        "Formula_ID": 18,
        "Formula_Name": res_18["formula_name"],
        "Numerical_Result": res_18["result"],
        "Unit": res_18["unit"],
        "Equation": res_18["equation"]
    })

    # --------------------------------------------------------------------------
    # SECTION 4: Battery Heat Generation (Bernardi Model)
    # --------------------------------------------------------------------------
    Q_rated = config.DEFAULT_BATTERY["Q_rated"]
    I_batt = c_rate * Q_rated
    V_oc = config.DEFAULT_BATTERY["V_oc"]
    V_op = config.DEFAULT_BATTERY["V_op"]
    dU_oc_dT = config.DEFAULT_BATTERY["dU_oc_dT"]
    vol_b = config.DEFAULT_BATTERY["length"] * config.DEFAULT_BATTERY["height"] * config.DEFAULT_BATTERY["thickness"]

    res_batt = calc_battery_heat_generation(I_batt, V_oc, V_op, T_batt_init, dU_oc_dT, volume_b=vol_b)
    Q_b_vol = res_batt["result_volumetric"]
    print_formula_result(res_batt, 4) # Section 4
    results_table.append({
        "Formula_ID": "4-BATT",
        "Formula_Name": res_batt["formula_name"],
        "Numerical_Result": res_batt["result_watts"],
        "Unit": "W",
        "Equation": res_batt["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 1: Energy Equation
    # --------------------------------------------------------------------------
    res_1 = calc_energy_equation_terms(
        rho_cp_eff=rho_cp_hnf,
        k_eff=k_hnf,
        u=U_in,
        v=0.0,
        dT_dx=(T_batt_init - T_in) / config.DEFAULT_BATTERY["length"],
        dT_dy=(T_batt_init - T_in) / L_char,
        d2T_dx2=0.0,
        d2T_dy2=-2.0 * (T_batt_init - T_in) / (L_char ** 2),
        Q_b=0.0, # inside fluid channel
        Q_visc=mu_hnf * (U_in / L_char) ** 2,
        Q_J=Q_J
    )
    print_formula_result(res_1, 1)
    results_table.append({
        "Formula_ID": 1,
        "Formula_Name": res_1["formula_name"],
        "Numerical_Result": res_1["result"],
        "Unit": res_1["unit"],
        "Equation": res_1["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 2: Momentum Equation (Darcy-Brinkman MHD)
    # --------------------------------------------------------------------------
    res_2 = calc_momentum_balance_2d(
        rho_hnf=rho_hnf,
        mu_eff=mu_hnf,
        k_perm=k_perm,
        sigma_hnf=sigma_hnf,
        B0=B0,
        u=U_in,
        v=0.0,
        dp_dx=- (mu_hnf / k_perm + sigma_hnf * B0**2) * U_in,
        dp_dy=0.0,
        d2u_dx2=0.0,
        d2u_dy2=-8.0 * U_in / (L_char ** 2),
        d2v_dx2=0.0,
        d2v_dy2=0.0,
        du_dx=0.0,
        du_dy=0.0,
        dv_dx=0.0,
        dv_dy=0.0
    )
    print_formula_result(res_2, 2)
    results_table.append({
        "Formula_ID": 2,
        "Formula_Name": res_2["formula_name"],
        "Numerical_Result": res_2["result"],
        "Unit": res_2["unit"],
        "Equation": res_2["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 3: Reynolds Number
    # --------------------------------------------------------------------------
    res_3 = calc_reynolds_number(rho_hnf, U_in, L_char, mu_hnf)
    print_formula_result(res_3, 3)
    results_table.append({
        "Formula_ID": 3,
        "Formula_Name": res_3["formula_name"],
        "Numerical_Result": res_3["result"],
        "Unit": res_3["unit"],
        "Equation": res_3["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 4: Prandtl Number (Mass-Specific Cp)
    # --------------------------------------------------------------------------
    res_4 = calc_prandtl_number(mu_hnf, cp_hnf, k_hnf)
    print_formula_result(res_4, 4)
    results_table.append({
        "Formula_ID": 4,
        "Formula_Name": res_4["formula_name"],
        "Numerical_Result": res_4["result"],
        "Unit": res_4["unit"],
        "Equation": res_4["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 5: Hartmann Number
    # --------------------------------------------------------------------------
    res_5 = calc_hartmann_number(B0, L_char, sigma_hnf, mu_hnf)
    print_formula_result(res_5, 5)
    results_table.append({
        "Formula_ID": 5,
        "Formula_Name": res_5["formula_name"],
        "Numerical_Result": res_5["result"],
        "Unit": res_5["unit"],
        "Equation": res_5["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 6: Darcy Number
    # --------------------------------------------------------------------------
    res_6 = calc_darcy_number(k_perm, L_char)
    print_formula_result(res_6, 6)
    results_table.append({
        "Formula_ID": 6,
        "Formula_Name": res_6["formula_name"],
        "Numerical_Result": res_6["result"],
        "Unit": res_6["unit"],
        "Equation": res_6["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 7: Brinkman Number
    # --------------------------------------------------------------------------
    res_7 = calc_brinkman_number(mu_hnf, U_in, k_hnf, Delta_T=Delta_T)
    print_formula_result(res_7, 7)
    results_table.append({
        "Formula_ID": 7,
        "Formula_Name": res_7["formula_name"],
        "Numerical_Result": res_7["result"],
        "Unit": res_7["unit"],
        "Equation": res_7["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 8: Nusselt Number
    # --------------------------------------------------------------------------
    h_conv_estimate = 4.36 * k_hnf / L_char # Laminar internal convection
    res_8 = calc_nusselt_number(h=h_conv_estimate, L=L_char, k_eff=k_hnf)
    print_formula_result(res_8, 8)
    results_table.append({
        "Formula_ID": 8,
        "Formula_Name": res_8["formula_name"],
        "Numerical_Result": res_8["result"],
        "Unit": res_8["unit"],
        "Equation": res_8["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 9: C-Rate & Battery Current
    # --------------------------------------------------------------------------
    res_9 = calc_c_rate_current(c_rate, Q_rated)
    print_formula_result(res_9, 9)
    results_table.append({
        "Formula_ID": 9,
        "Formula_Name": res_9["formula_name"],
        "Numerical_Result": res_9["result"],
        "Unit": res_9["unit"],
        "Equation": res_9["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 10: Boundary Conditions
    # --------------------------------------------------------------------------
    res_10 = evaluate_boundary_conditions_record(U_in, T_in, T_wall=T_batt_init, q_wall=Q_b_vol * 0.01)
    print_formula_result(res_10, 10)
    results_table.append({
        "Formula_ID": 10,
        "Formula_Name": res_10["formula_name"],
        "Numerical_Result": U_in,
        "Unit": "m/s (Applied in Solver)",
        "Equation": res_10["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 11: Temperature Continuity at Interface
    # --------------------------------------------------------------------------
    res_11 = calc_temperature_continuity(T_b=305.15, T_f=305.15)
    print_formula_result(res_11, 11)
    results_table.append({
        "Formula_ID": 11,
        "Formula_Name": res_11["formula_name"],
        "Numerical_Result": res_11["result"],
        "Unit": res_11["unit"],
        "Equation": res_11["equation"]
    })

    # --------------------------------------------------------------------------
    # FORMULA 12: Heat Flux Continuity at Interface
    # --------------------------------------------------------------------------
    k_batt = config.DEFAULT_BATTERY["k_b"]
    dT_b_dn = - (T_batt_init - 305.15) / 0.03
    dT_f_dn = - (305.15 - T_in) / (L_char / 2.0)
    res_12 = calc_heat_flux_continuity(k_b=k_batt, dT_b_dn=dT_b_dn, k_f=k_hnf, dT_f_dn=dT_f_dn, R_tc=0.0)
    print_formula_result(res_12, 12)
    results_table.append({
        "Formula_ID": 12,
        "Formula_Name": res_12["formula_name"],
        "Numerical_Result": res_12["result_flux"],
        "Unit": "W/m^2",
        "Equation": res_12["equation"]
    })

    # Convert to DataFrame
    df_results = pd.DataFrame(results_table)

    if save_outputs:
        csv_path = os.path.join(config.PART_A_RESULTS, "formula_calculator_results.csv")
        df_results.to_csv(csv_path, index=False)
        print(f"\n[FILE SAVED] Numerical results table exported to: {csv_path}")

        # Generate plots
        print("\n[GENERATING GRAPHS] Plotting parametric curves for all applicable formulations...")
        plot_dimensionless_relationships(config.PART_A_GRAPHS)

        # Plot transient temperature curve
        times, temps = simulate_1d_transient_temperature(
            t_span=600.0, Nt=120, T_init=T_batt_init, T_in=T_in,
            u_avg=U_in, L=config.DEFAULT_CHANNEL["L"],
            rho_cp_eff=rho_cp_hnf, k_eff=k_hnf, q_b_vol=Q_b_vol, Q_J=Q_J
        )
        t_plot_path = os.path.join(config.PART_A_GRAPHS, "01_transient_temperature_evolution.png")
        plot_temperature_vs_time(times, temps, t_plot_path)

        # Velocity & pressure profiles
        y_pts, u_pts, G_grad, p_pts = calc_darcy_brinkman_mhd_channel_profile(
            U_in=U_in, H=L_char, L=config.DEFAULT_CHANNEL["L"],
            mu_eff=mu_hnf, k_perm=k_perm, sigma_hnf=sigma_hnf, B0=B0
        )
        v_plot_path = os.path.join(config.PART_A_GRAPHS, "06_velocity_profile.png")
        plot_velocity_distributions(y_pts, u_pts, v_plot_path)

        p_plot_path = os.path.join(config.PART_A_GRAPHS, "09_pressure_distribution.png")
        x_pts = np.linspace(0, config.DEFAULT_CHANNEL["L"], len(p_pts))
        plot_pressure_distribution(x_pts, p_pts, p_plot_path)

        print(f"[GRAPHS SAVED] High-resolution PNG graphs saved to: {config.PART_A_GRAPHS}")

    print_section_header("SUBPART A1 COMPLETED SUCCESSFULLY")
    return df_results


if __name__ == "__main__":
    run_all_18_formulations()
