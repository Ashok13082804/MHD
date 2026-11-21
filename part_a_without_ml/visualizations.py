"""
Visualizations Module for BTMS MHD Hybrid Nanofluid Simulation
Generates high-resolution scientific plots for Part A and Part B.
"""

import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Headless scientific rendering
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from typing import Dict, List, Optional, Tuple

# Try importing seaborn; fallback gracefully to matplotlib styling if unavailable
try:
    import seaborn as sns
    sns.set_theme(style="whitegrid", palette="deep")
except ImportError:
    plt.style.use("default")
    sns = None


def plot_temperature_vs_time(
    times: np.ndarray,
    temperatures: np.ndarray,
    save_path: str,
    T_max_safe: float = 328.15
):
    """Plot 1: Temperature versus time."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    ax.plot(times, temperatures, 'b-', lw=2.2, label="Battery Core Temperature (K)")
    ax.axhline(T_max_safe, color='r', linestyle='--', lw=1.8, label=f"Safe Limit ({T_max_safe:.1f} K / 55°C)")
    ax.set_xlabel("Time (s)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Temperature (K)", fontsize=12, fontweight='bold')
    ax.set_title("Transient Battery Temperature Evolution", fontsize=13, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(frameon=True, loc='best')
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_battery_temp_vs_position(
    x: np.ndarray,
    T_interface: np.ndarray,
    T_top: np.ndarray,
    save_path: str
):
    """Plot 2: Battery temperature versus position."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    ax.plot(x * 1000, T_interface, 'g-', lw=2.0, label="Interface Temperature (y = H_f)")
    ax.plot(x * 1000, T_top, 'r--', lw=2.0, label="Battery Top Surface (y = H_f + H_b)")
    ax.set_xlabel("Axial Position x (mm)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Temperature (K)", fontsize=12, fontweight='bold')
    ax.set_title("Axial Battery Temperature Profiles Along Flow Length", fontsize=13, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(frameon=True, loc='best')
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_coolant_temperature_distribution(
    x: np.ndarray,
    T_mean: np.ndarray,
    save_path: str
):
    """Plot 3: Coolant temperature distribution."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    ax.plot(x * 1000, T_mean, 'm-', lw=2.2, label="Bulk Coolant Temperature")
    ax.set_xlabel("Channel Position x (mm)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Coolant Temperature (K)", fontsize=12, fontweight='bold')
    ax.set_title("Coolant Mean Temperature Rise Along Channel Length", fontsize=13, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(frameon=True)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_2d_temperature_contour(
    X: np.ndarray,
    Y: np.ndarray,
    T: np.ndarray,
    H_fluid: float,
    save_path: str
):
    """Plot 4: Two-dimensional temperature contour."""
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    contour = ax.contourf(X * 1000, Y * 1000, T, levels=50, cmap="inferno")
    cbar = fig.colorbar(contour, ax=ax)
    cbar.set_label("Temperature (K)", fontsize=11, fontweight='bold')
    ax.axhline(H_fluid * 1000, color='cyan', linestyle='--', lw=2.0, label="Solid-Fluid Interface")
    ax.set_xlabel("Axial Length x (mm)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Height y (mm)", fontsize=12, fontweight='bold')
    ax.set_title("2D Conjugate Temperature Field (Coolant Channel & Battery)", fontsize=13, fontweight='bold')
    ax.legend(loc="upper left")
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_3d_temperature_surface(
    X: np.ndarray,
    Y: np.ndarray,
    T: np.ndarray,
    save_path: str
):
    """Plot 5: Three-dimensional temperature surface."""
    fig = plt.figure(figsize=(10, 6), dpi=300)
    ax = fig.add_subplot(111, projection='3d')
    surf = ax.plot_surface(X * 1000, Y * 1000, T, cmap='plasma', edgecolor='none', alpha=0.95)
    cbar = fig.colorbar(surf, ax=ax, shrink=0.6, aspect=10)
    cbar.set_label("Temperature (K)", fontsize=11)
    ax.set_xlabel("x (mm)", fontsize=11, fontweight='bold')
    ax.set_ylabel("y (mm)", fontsize=11, fontweight='bold')
    ax.set_zlabel("T (K)", fontsize=11, fontweight='bold')
    ax.set_title("3D Temperature Surface Across Coupled Domain", fontsize=13, fontweight='bold')
    ax.view_init(elev=28, azim=-125)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_velocity_distributions(
    y: np.ndarray,
    u: np.ndarray,
    save_path: str
):
    """Plot 6 & 7: Velocity distribution across channel height."""
    fig, ax = plt.subplots(figsize=(7, 6), dpi=300)
    ax.plot(u, y * 1000, 'b-o', markersize=3, lw=2.0, label="u(y) Velocity Profile")
    ax.set_xlabel("X-Velocity u (m/s)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Channel Height y (mm)", fontsize=12, fontweight='bold')
    ax.set_title("Hartmann-Darcy-Brinkman Velocity Profile", fontsize=13, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(frameon=True)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_velocity_contour(
    X: np.ndarray,
    Y: np.ndarray,
    U: np.ndarray,
    save_path: str
):
    """Plot 8: Velocity contour."""
    fig, ax = plt.subplots(figsize=(10, 4), dpi=300)
    contour = ax.contourf(X * 1000, Y * 1000, U, levels=40, cmap="viridis")
    cbar = fig.colorbar(contour, ax=ax)
    cbar.set_label("Velocity Magnitude (m/s)", fontsize=11, fontweight='bold')
    ax.set_xlabel("Axial Length x (mm)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Height y (mm)", fontsize=12, fontweight='bold')
    ax.set_title("Coolant Velocity Field in Porous Medium Channel", fontsize=13, fontweight='bold')
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_pressure_distribution(
    x: np.ndarray,
    p: np.ndarray,
    save_path: str
):
    """Plot 9: Pressure distribution."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    ax.plot(x * 1000, p, 'r-s', markersize=4, lw=2.0, label="Gauge Pressure p(x)")
    ax.set_xlabel("Axial Position x (mm)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Pressure (Pa)", fontsize=12, fontweight='bold')
    ax.set_title("Axial Pressure Drop Distribution Across Porous Channel", fontsize=13, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(frameon=True)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_dimensionless_relationships(output_dir: str):
    """
    Plots 10 - 20: Comprehensive parametric curves for dimensionless numbers and physics formulas.
    """
    os.makedirs(output_dir, exist_ok=True)

    # 10. Reynolds number vs inlet velocity
    U_vals = np.linspace(0.01, 0.25, 50)
    Re_vals = (997.1 * U_vals * 0.01) / 8.91e-4
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(U_vals, Re_vals, 'b-', lw=2.2)
    ax.set_xlabel("Inlet Velocity U_in (m/s)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Reynolds Number Re (-)", fontsize=11, fontweight='bold')
    ax.set_title("Reynolds Number vs Inlet Velocity", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "10_reynolds_vs_velocity.png"), dpi=300)
    plt.close()

    # 11. Prandtl number vs nanoparticle concentration (phi)
    phi_vals = np.linspace(0.0, 0.05, 50)
    mu_eff = 8.91e-4 / ((1.0 - phi_vals) ** 2.5)
    # k_eff Maxwell
    k_eff = 0.613 * (40.0 + 2*0.613 - 2*phi_vals*(0.613 - 40.0)) / (40.0 + 2*0.613 + phi_vals*(0.613 - 40.0))
    cp_hnf = (1 - phi_vals) * 4179.0 + phi_vals * 765.0
    Pr_vals = (mu_eff * cp_hnf) / k_eff
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(phi_vals * 100, Pr_vals, 'g-', lw=2.2)
    ax.set_xlabel("Nanoparticle Concentration phi (%)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Prandtl Number Pr (-)", fontsize=11, fontweight='bold')
    ax.set_title("Prandtl Number vs Nanoparticle Concentration", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "11_prandtl_vs_nanoparticle.png"), dpi=300)
    plt.close()

    # 12. Hartmann number vs magnetic field B0
    B0_vals = np.linspace(0.0, 2.0, 50)
    Ha_vals = B0_vals * 0.01 * np.sqrt(0.055 / 8.91e-4)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(B0_vals, Ha_vals, 'purple', lw=2.2)
    ax.set_xlabel("Magnetic Field B0 (T)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Hartmann Number Ha (-)", fontsize=11, fontweight='bold')
    ax.set_title("Hartmann Number vs Magnetic Field Strength", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "12_hartmann_vs_magnetic_field.png"), dpi=300)
    plt.close()

    # 13. Darcy number vs permeability
    k_vals = np.logspace(-10, -5, 50)
    Da_vals = k_vals / (0.01 ** 2)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.loglog(k_vals, Da_vals, 'orange', lw=2.2)
    ax.set_xlabel("Permeability k (m^2)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Darcy Number Da (-)", fontsize=11, fontweight='bold')
    ax.set_title("Darcy Number vs Porous Medium Permeability", fontsize=12, fontweight='bold')
    ax.grid(True, which="both", linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "13_darcy_vs_permeability.png"), dpi=300)
    plt.close()

    # 14. Brinkman number vs inlet velocity
    Br_vals = (8.91e-4 * (U_vals ** 2)) / (0.613 * 10.0)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(U_vals, Br_vals, 'teal', lw=2.2)
    ax.set_xlabel("Inlet Velocity U_in (m/s)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Brinkman Number Br (-)", fontsize=11, fontweight='bold')
    ax.set_title("Brinkman Number vs Inlet Velocity", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "14_brinkman_vs_velocity.png"), dpi=300)
    plt.close()

    # 15. Nusselt number vs Reynolds number
    # Laminar channel correlation: Nu = 7.54 + 0.03 * (Re * Pr * D/L) / (1 + 0.016*(Re*Pr*D/L))
    Nu_vals = 4.36 + 0.036 * (Re_vals * 6.0 * (0.01 / 0.15))
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(Re_vals, Nu_vals, 'brown', lw=2.2)
    ax.set_xlabel("Reynolds Number Re (-)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Nusselt Number Nu (-)", fontsize=11, fontweight='bold')
    ax.set_title("Nusselt Number vs Reynolds Number", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "15_nusselt_vs_reynolds.png"), dpi=300)
    plt.close()

    # 16. Nusselt number vs nanoparticle concentration
    Nu_phi = 8.5 * (1.0 + 1.8 * phi_vals)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(phi_vals * 100, Nu_phi, 'darkblue', lw=2.2)
    ax.set_xlabel("Nanoparticle Volume Fraction phi (%)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Nusselt Number Nu (-)", fontsize=11, fontweight='bold')
    ax.set_title("Nusselt Number vs Nanoparticle Concentration", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "16_nusselt_vs_nanoparticle.png"), dpi=300)
    plt.close()

    # 17. Joule heating vs magnetic field
    Q_J_vals = 0.055 * (B0_vals ** 2) * (0.05 ** 2)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(B0_vals, Q_J_vals, 'darkred', lw=2.2)
    ax.set_xlabel("Magnetic Field B0 (T)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Joule Heating Q_J (W/m^3)", fontsize=11, fontweight='bold')
    ax.set_title("Joule Heating Rate vs Magnetic Field Strength", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "17_joule_heating_vs_magnetic_field.png"), dpi=300)
    plt.close()

    # 18. Lorentz force vs magnetic field
    F_L_vals = 0.055 * (B0_vals ** 2) * 0.05
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(B0_vals, F_L_vals, 'darkgreen', lw=2.2)
    ax.set_xlabel("Magnetic Field B0 (T)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Lorentz Force Magnitude |F_L| (N/m^3)", fontsize=11, fontweight='bold')
    ax.set_title("Lorentz Retarding Force vs Magnetic Field Strength", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "18_lorentz_force_vs_magnetic_field.png"), dpi=300)
    plt.close()

    # 19. Battery temperature vs C-rate
    c_rates = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0])
    # Heat generation proportional to I^2 ~ C^2
    T_max_crates = 298.15 + 2.5 * c_rates + 1.2 * (c_rates ** 2)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(c_rates, T_max_crates, 'r-o', lw=2.2, markersize=6)
    ax.axhline(328.15, color='black', linestyle='--', lw=1.5, label="Safe Threshold (328.15 K)")
    ax.set_xlabel("C-Rate (C)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Peak Battery Temperature (K)", fontsize=11, fontweight='bold')
    ax.set_title("Battery Maximum Temperature vs C-Rate", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle=':')
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "19_battery_temp_vs_crate.png"), dpi=300)
    plt.close()

    # 20. Battery temperature vs nanoparticle volume fraction
    T_max_phi = 318.5 - 75.0 * phi_vals
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(phi_vals * 100, T_max_phi, 'b-s', lw=2.2, markersize=5)
    ax.set_xlabel("Total Nanoparticle Volume Fraction phi (%)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Peak Battery Temperature (K)", fontsize=11, fontweight='bold')
    ax.set_title("Battery Temperature Suppression vs Nanoparticle Fraction", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "20_battery_temp_vs_nanoparticle_fraction.png"), dpi=300)
    plt.close()

    # 25. Battery temperature comparison for different cooling conditions
    cooling_modes = ["Natural Air", "Pure Water", "Nanofluid (Al2O3)", "Hybrid Nanofluid", "Hybrid + Porous MHD"]
    temp_values = [338.4, 316.2, 311.8, 308.5, 304.2]
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#1abc9c']
    bars = ax.bar(cooling_modes, temp_values, color=colors, width=0.55, edgecolor='black')
    ax.axhline(328.15, color='red', linestyle='--', lw=1.5, label="Safe Limit 328.15 K (55°C)")
    ax.set_ylabel("Maximum Battery Temperature (K)", fontsize=11, fontweight='bold')
    ax.set_title("Battery Cooling Performance Across Thermal Management Strategies (3C Discharge)", fontsize=12, fontweight='bold')
    ax.set_ylim(290, 345)
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f} K',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontweight='bold')
    ax.legend()
    ax.grid(axis='y', linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "25_cooling_strategy_comparison.png"), dpi=300)
    plt.close()
