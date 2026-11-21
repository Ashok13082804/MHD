#!/usr/bin/env python3
"""
SUBPART B2: Machine Learning Prediction and BTMS Visualization Module
Interactive and automated prediction program that:
  1. Accepts manual or programmatic physical parameters.
  2. Prints every input parameter with its name and SI units.
  3. Computes dependent thermophysical and dimensionless numbers.
  4. Loads trained ML models and predicts numerical BTMS outputs.
  5. Computes reference physics-based solver outputs for direct comparison.
  6. Calculates and displays prediction errors (absolute & percentage).
  7. Generates visual comparisons and high-resolution plots.
  8. Saves predictions to CSV and exports a comprehensive technical report.
"""

import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import sys
import argparse
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from part_a_without_ml.material_properties import (
    calc_effective_density,
    calc_effective_heat_capacity,
    calc_effective_thermal_conductivity,
    calc_effective_dynamic_viscosity,
    calc_effective_electrical_conductivity,
    calc_joule_heating,
    calc_lorentz_force,
    calc_battery_heat_generation,
    validate_nanoparticle_volume_fractions,
)
from part_a_without_ml.dimensionless_numbers import (
    calc_reynolds_number,
    calc_prandtl_number,
    calc_hartmann_number,
    calc_darcy_number,
    calc_brinkman_number,
    calc_c_rate_current,
)
from part_b_with_ml.feature_preprocessing import INPUT_FEATURES


def predict_btms_performance(
    U_in: float = 0.05,
    T_in: float = 298.15,
    T_batt_init: float = 300.0,
    T_amb: float = 298.15,
    B0: float = 0.5,
    phi1: float = 0.02,
    phi2: float = 0.01,
    k_perm: float = 1.0e-7,
    c_rate: float = 2.0,
    Q_rated: float = 20.0,
    L_char: float = 0.010,
    model_name: str = "gradient_boosting",
    save_outputs: bool = True
) -> Dict[str, Any]:
    """
    Executes the full physics vs ML prediction and comparison pipeline.
    """
    print("\n" + "=" * 90)
    print(" PART B2: MACHINE LEARNING-BASED PREDICTION & COMPARISON ".center(90, "="))
    print("=" * 90)

    # 1. Print all input parameters
    print("\n--- 1. INPUT PARAMETERS ---")
    inputs = [
        ("Coolant Inlet Velocity (U_in)", U_in, "m/s"),
        ("Coolant Inlet Temperature (T_in)", T_in, "K"),
        ("Initial Battery Temperature (T_batt_init)", T_batt_init, "K"),
        ("Ambient Temperature (T_amb)", T_amb, "K"),
        ("Magnetic Field Strength (B0)", B0, "T"),
        ("Al2O3 Volume Fraction (phi1)", phi1, "dimensionless"),
        ("CuO Volume Fraction (phi2)", phi2, "dimensionless"),
        ("Porous Permeability (k_perm)", k_perm, "m^2"),
        ("Battery Discharge C-Rate", c_rate, "C (1/h)"),
        ("Rated Battery Capacity (Q_rated)", Q_rated, "Ah"),
        ("Characteristic Channel Height (L_char)", L_char, "m"),
    ]
    for name, val, unit in inputs:
        if isinstance(val, float) and (val < 1.0e-3 or val > 1.0e4):
            print(f"  * {name:<42} : {val:>14.4e} [{unit}]")
        else:
            print(f"  * {name:<42} : {val:>14.4f} [{unit}]")

    # Physical validation
    is_valid, msg = validate_nanoparticle_volume_fractions(phi1, phi2)
    if not is_valid:
        raise ValueError(f"Physics validation failed: {msg}")

    # 2. Calculate dependent physical properties
    print("\n--- 2. CALCULATED DEPENDENT PHYSICAL PROPERTIES ---")
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

    rho_hnf = calc_effective_density(rho_f, rho_s1, rho_s2, phi1, phi2)["result"]
    res_cp = calc_effective_heat_capacity(rho_f, cp_f, rho_s1, cp_s1, rho_s2, cp_s2, phi1, phi2)
    rho_cp_hnf = res_cp["result_volumetric"]
    cp_hnf = res_cp["result"]
    k_hnf = calc_effective_thermal_conductivity(k_f, k_s1, k_s2, phi1, phi2)["result"]
    mu_hnf = calc_effective_dynamic_viscosity(mu_f, phi1, phi2)["result"]
    sigma_hnf = calc_effective_electrical_conductivity(sigma_f, sigma_s1, sigma_s2, phi1, phi2)["result"]

    # Dimensionless numbers
    Re = calc_reynolds_number(rho_hnf, U_in, L_char, mu_hnf)["result"]
    Pr = calc_prandtl_number(mu_hnf, cp_hnf, k_hnf)["result"]
    Ha = calc_hartmann_number(B0, L_char, sigma_hnf, mu_hnf)["result"]
    Da = calc_darcy_number(k_perm, L_char)["result"]
    Br = calc_brinkman_number(mu_hnf, U_in, k_hnf, max(abs(T_batt_init - T_in), 1.0))["result"]

    # Electrochemical heat generation
    I_batt = c_rate * Q_rated
    vol_b = config.DEFAULT_BATTERY["length"] * config.DEFAULT_BATTERY["height"] * config.DEFAULT_BATTERY["thickness"]
    res_batt = calc_battery_heat_generation(
        I_batt, config.DEFAULT_BATTERY["V_oc"], config.DEFAULT_BATTERY["V_op"],
        T_batt_init, config.DEFAULT_BATTERY["dU_oc_dT"], volume_b=vol_b
    )
    Q_b_W = res_batt["result_watts"]
    q_b_vol = res_batt["result_volumetric"]

    # Lorentz & Joule dissipation
    Q_J_W_m3 = calc_joule_heating(sigma_hnf, B0, u=U_in)["result"]
    F_L_x = calc_lorentz_force(sigma_hnf, B0, u=U_in)["result"]

    print(f"  * Effective Density (rho_hnf)             : {rho_hnf:>14.2f} [kg/m^3]")
    print(f"  * Effective Specific Heat (Cp_hnf)        : {cp_hnf:>14.2f} [J/(kg*K)]")
    print(f"  * Effective Conductivity (k_hnf)          : {k_hnf:>14.4f} [W/(m*K)]")
    print(f"  * Effective Dynamic Viscosity (mu_hnf)    : {mu_hnf:>14.4e} [Pa*s]")
    print(f"  * Effective Electrical Conduct. (sigma)   : {sigma_hnf:>14.4e} [S/m]")
    print(f"  * Reynolds Number (Re)                    : {Re:>14.2f} [-]")
    print(f"  * Prandtl Number (Pr)                     : {Pr:>14.2f} [-]")
    print(f"  * Hartmann Number (Ha)                    : {Ha:>14.4f} [-]")
    print(f"  * Darcy Number (Da)                       : {Da:>14.4e} [-]")
    print(f"  * Brinkman Number (Br)                    : {Br:>14.4e} [-]")
    print(f"  * Operating Current (I)                   : {I_batt:>14.2f} [A]")
    print(f"  * Battery Heat Generation (Q_b)           : {Q_b_W:>14.2f} [W]")
    print(f"  * Volumetric Joule Heating (Q_J)          : {Q_J_W_m3:>14.4e} [W/m^3]")
    print(f"  * Lorentz Retarding Force (F_Lx)          : {F_L_x:>14.4e} [N/m^3]")

    # 3. Load Trained Machine Learning Model
    print(f"\n--- 3. LOAD TRAINED ML MODEL: [{model_name.upper()}] ---")
    scaler_path = os.path.join(config.MODELS_DIR, "feature_scaler.joblib")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Scaler not found at {scaler_path}. Please execute Subpart B1 first.")

    scaler = joblib.load(scaler_path)

    # Normalize model name for directory path
    model_slug = model_name.lower().replace(" ", "_")
    model_file = os.path.join(config.MODELS_DIR, model_slug, f"{model_slug}_model.joblib")
    if not os.path.exists(model_file):
        # Fallback to gradient_boosting or random_forest
        print(f"Model file {model_file} not found. Checking fallback models...")
        fallback_models = ["gradient_boosting", "xgboost", "random_forest", "svr"]
        found = False
        for fb in fallback_models:
            fb_file = os.path.join(config.MODELS_DIR, fb, f"{fb}_model.joblib")
            if os.path.exists(fb_file):
                model_slug = fb
                model_file = fb_file
                found = True
                break
        if not found:
            raise FileNotFoundError("No trained ML model found. Run 'python part_b_with_ml/B1_model_training.py' first.")

    ml_model = joblib.load(model_file)
    print(f"  >> Successfully loaded ML model from: {model_file}")

    # 4. Predict Output Using ML Model
    input_vector = np.array([[
        U_in, T_in, T_batt_init, T_amb, B0, phi1, phi2, k_perm, c_rate, Q_rated, L_char
    ]])
    input_scaled = scaler.transform(input_vector)
    T_max_ml_pred = float(ml_model.predict(input_scaled)[0])

    # 5. Reference Physics-Based Calculation (Ground Truth)
    # Graetz-Leveque + thermal resistance network ground truth
    L_batt = config.DEFAULT_BATTERY["length"]
    H_batt = config.DEFAULT_BATTERY["height"]
    W_batt = config.DEFAULT_BATTERY["thickness"]
    k_b = config.DEFAULT_BATTERY["k_b"]
    Graetz = (Re * Pr * L_char / L_batt)
    Nu_avg_phys = 4.36 + 0.036 * Graetz * (1.0 + 1.5 * (phi1 + phi2))
    h_eff = Nu_avg_phys * k_hnf / L_char
    R_cond_b = (H_batt / 2.0) / (k_b * (L_batt * W_batt))
    R_conv_f = 1.0 / (h_eff * (L_batt * W_batt))
    R_tot = R_cond_b + R_conv_f
    T_avg_phys = T_in + Q_b_W * R_tot
    T_max_phys = T_avg_phys + (Q_b_W * R_cond_b * 0.6)

    # Calculate errors
    abs_error = abs(T_max_ml_pred - T_max_phys)
    rel_error_pct = (abs_error / T_max_phys) * 100.0

    # 6. Display Comparison Table
    print("\n--- 4. ACTUAL PHYSICS vs ML PREDICTED COMPARISON ---")
    print(f"{'Metric':<38} | {'Physics Numerical':<18} | {'ML Predicted':<18} | {'Abs Error':<12} | {'Rel Error (%)':<14} | {'Unit'}")
    print("-" * 115)
    print(f"{'Peak Battery Temp (T_max_battery)':<38} | {T_max_phys:>18.2f} | {T_max_ml_pred:>18.2f} | {abs_error:>12.4f} | {rel_error_pct:>13.3f}% | K")
    print(f"{'Peak Temp in Celsius':<38} | {T_max_phys - 273.15:>18.2f} | {T_max_ml_pred - 273.15:>18.2f} | {abs_error:>12.4f} | {rel_error_pct:>13.3f}% | °C")
    print("-" * 115)

    is_safe_phys = bool(T_max_phys <= config.DEFAULT_BATTERY["T_max_safe"])
    is_safe_ml = bool(T_max_ml_pred <= config.DEFAULT_BATTERY["T_max_safe"])
    print(f"\nThermal Safety Assessment (Safe Limit <= 328.15 K / 55°C):")
    print(f"  * Physics Assessment : {'SAFE (PASS)' if is_safe_phys else 'UNSAFE (EXCEEDED LIMIT)'}")
    print(f"  * ML Prediction      : {'SAFE (PASS)' if is_safe_ml else 'UNSAFE (EXCEEDED LIMIT)'}")
    print(f"  * Discrepancy Note   : Synthetic physics-informed ML model prediction. Not claimed as experimental proof.")

    # 7. Generate Visualization
    pred_plot_path = os.path.join(config.PART_B_GRAPHS, "prediction_comparison_bar.png")
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    cats = ["Physics Simulation", f"ML Prediction ({model_slug.upper()})"]
    vals = [T_max_phys, T_max_ml_pred]
    colors = ["#2b5c8f", "#27ae60"]
    bars = ax.bar(cats, vals, color=colors, width=0.45, edgecolor='black')
    ax.axhline(config.DEFAULT_BATTERY["T_max_safe"], color='r', linestyle='--', lw=1.8, label=f"Max Safe Limit ({config.DEFAULT_BATTERY['T_max_safe']:.1f} K)")
    ax.set_ylabel("Peak Temperature (K)", fontsize=11, fontweight='bold')
    ax.set_title("BTMS Peak Temperature: Physics Solver vs Machine Learning", fontsize=12, fontweight='bold')
    ax.set_ylim([280, max(T_max_phys, T_max_ml_pred) + 15])
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{h:.2f} K\n({h - 273.15:.1f} °C)", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points", ha='center', va='bottom', fontweight='bold', fontsize=10)
    ax.legend(loc="upper left")
    ax.grid(axis='y', linestyle=':', alpha=0.6)
    plt.tight_layout()
    os.makedirs(os.path.dirname(pred_plot_path), exist_ok=True)
    plt.savefig(pred_plot_path, dpi=300)
    plt.close()
    print(f"\n[GRAPH SAVED] Prediction comparison bar plot saved to: {pred_plot_path}")

    # 8. Save CSV Results
    pred_df = pd.DataFrame([{
        "U_in_m_s": U_in,
        "T_in_K": T_in,
        "T_batt_init_K": T_batt_init,
        "T_amb_K": T_amb,
        "B0_T": B0,
        "phi1_Al2O3": phi1,
        "phi2_CuO": phi2,
        "k_perm_m2": k_perm,
        "c_rate": c_rate,
        "Q_rated_Ah": Q_rated,
        "L_char_m": L_char,
        "ML_Model_Used": model_name,
        "Physics_T_max_K": T_max_phys,
        "ML_Predicted_T_max_K": T_max_ml_pred,
        "Absolute_Error_K": abs_error,
        "Relative_Error_Percent": rel_error_pct,
        "Thermal_Safety_Phys": is_safe_phys,
        "Thermal_Safety_ML": is_safe_ml,
    }])
    pred_csv_path = os.path.join(config.PART_B_PREDICTIONS, "prediction_results.csv")
    pred_df.to_csv(pred_csv_path, index=False)
    print(f"[FILE SAVED] Prediction CSV exported to: {pred_csv_path}")

    # 9. Save Detailed Prediction Report
    report_path = os.path.join(config.PART_B_REPORTS, "prediction_report.txt")
    with open(report_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("BTMS MHD HYBRID NANOFLUID PREDICTION REPORT (SUBPART B2)\n")
        f.write("=" * 80 + "\n\n")
        f.write("1. INPUT SPECIFICATIONS:\n")
        for name, val, unit in inputs:
            f.write(f"   * {name:<40} : {val} [{unit}]\n")
        f.write("\n2. THERMOPHYSICAL PROPERTIES:\n")
        f.write(f"   * Effective Density (rho_hnf)             : {rho_hnf:.2f} kg/m^3\n")
        f.write(f"   * Effective Specific Heat (Cp_hnf)        : {cp_hnf:.2f} J/(kg*K)\n")
        f.write(f"   * Effective Thermal Conductivity (k_hnf)  : {k_hnf:.4f} W/(m*K)\n")
        f.write(f"   * Effective Dynamic Viscosity (mu_hnf)    : {mu_hnf:.4e} Pa*s\n")
        f.write(f"   * Reynolds Number (Re)                    : {Re:.2f}\n")
        f.write(f"   * Hartmann Number (Ha)                    : {Ha:.4f}\n")
        f.write(f"   * Darcy Number (Da)                       : {Da:.4e}\n")
        f.write(f"   * Battery Current (I)                     : {I_batt:.2f} A\n")
        f.write(f"   * Battery Heat Generation (Q_b)           : {Q_b_W:.2f} W\n")
        f.write("\n3. PREDICTION & ERROR ANALYSIS:\n")
        f.write(f"   * Machine Learning Algorithm              : {model_name}\n")
        f.write(f"   * Physics Reference Peak Temperature      : {T_max_phys:.2f} K ({T_max_phys - 273.15:.2f} °C)\n")
        f.write(f"   * ML Predicted Peak Temperature           : {T_max_ml_pred:.2f} K ({T_max_ml_pred - 273.15:.2f} °C)\n")
        f.write(f"   * Absolute Prediction Discrepancy         : {abs_error:.4f} K\n")
        f.write(f"   * Relative Error Percentage               : {rel_error_pct:.3f}%\n")
        f.write(f"   * Safe Thermal Threshold Compliant        : {'YES' if is_safe_ml else 'NO'}\n")
        f.write("\n4. SCIENTIFIC DISCLAIMER:\n")
        f.write("   Predictions are derived from a physics-informed surrogate model trained on governing\n")
        f.write("   hydrodynamic and conjugate thermal transport equations. Model results should be\n")
        f.write("   benchmarked against calibrated laboratory experimental tests prior to cell packaging.\n")
    print(f"[REPORT SAVED] Detailed prediction report exported to: {report_path}")

    print("\n" + "=" * 90)
    print(" SUBPART B2 COMPLETED SUCCESSFULLY ".center(90, "="))
    print("=" * 90)
    return {
        "T_max_phys": T_max_phys,
        "T_max_ml": T_max_ml_pred,
        "abs_error": abs_error,
        "rel_error_pct": rel_error_pct,
        "model_used": model_name
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Subpart B2: ML Prediction and Visualization")
    parser.add_argument("--U_in", type=float, default=0.05, help="Inlet velocity [m/s]")
    parser.add_argument("--T_in", type=float, default=298.15, help="Inlet coolant temperature [K]")
    parser.add_argument("--T_batt_init", type=float, default=300.0, help="Initial battery temperature [K]")
    parser.add_argument("--T_amb", type=float, default=298.15, help="Ambient temperature [K]")
    parser.add_argument("--B0", type=float, default=0.5, help="Magnetic field strength [T]")
    parser.add_argument("--phi1", type=float, default=0.02, help="Al2O3 volume fraction")
    parser.add_argument("--phi2", type=float, default=0.01, help="CuO volume fraction")
    parser.add_argument("--k_perm", type=float, default=1.0e-7, help="Porous permeability [m^2]")
    parser.add_argument("--c_rate", type=float, default=2.0, help="Battery C-rate [C]")
    parser.add_argument("--Q_rated", type=float, default=20.0, help="Rated battery capacity [Ah]")
    parser.add_argument("--L_char", type=float, default=0.010, help="Channel characteristic height [m]")
    parser.add_argument("--model", type=str, default="gradient_boosting", help="ML model name")
    args = parser.parse_args()

    predict_btms_performance(
        U_in=args.U_in,
        T_in=args.T_in,
        T_batt_init=args.T_batt_init,
        T_amb=args.T_amb,
        B0=args.B0,
        phi1=args.phi1,
        phi2=args.phi2,
        k_perm=args.k_perm,
        c_rate=args.c_rate,
        Q_rated=args.Q_rated,
        L_char=args.L_char,
        model_name=args.model
    )
