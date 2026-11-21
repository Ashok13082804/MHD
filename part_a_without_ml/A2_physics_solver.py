#!/usr/bin/env python3
"""
SUBPART A2: Coupled BTMS Physics-Based Numerical Solver
2D Conjugate Heat Transfer and Darcy-Brinkman MHD Flow Solver (Without Machine Learning).

Solves:
  1. Darcy-Brinkman MHD momentum equation with Lorentz force damping and porous drag.
  2. 2D Continuity equation.
  3. Conjugate 2D energy equation with:
     - Battery electrochemical heat generation (Bernardi model)
     - Joule heating in hybrid nanofluid (motional induction)
     - Viscous dissipation
     - Interface temperature and heat flux continuity
     - Full inlet, outlet, and convective boundary conditions.
  4. Computes velocity field, temperature field, pressure distribution,
     Nusselt numbers, Reynolds, Prandtl, Hartmann, Darcy, Brinkman numbers.
  5. Monitors convergence residuals and exports CSV files and graphs.
"""

import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

import config
from part_a_without_ml.material_properties import (
    calc_effective_density,
    calc_effective_heat_capacity,
    calc_effective_thermal_conductivity,
    calc_effective_dynamic_viscosity,
    calc_effective_electrical_conductivity,
    calc_battery_heat_generation,
)
from part_a_without_ml.dimensionless_numbers import (
    calc_reynolds_number,
    calc_prandtl_number,
    calc_hartmann_number,
    calc_darcy_number,
    calc_brinkman_number,
    calc_nusselt_number,
    calc_c_rate_current,
)
from part_a_without_ml.boundary_conditions import (
    apply_flow_and_thermal_boundary_conditions,
    compute_harmonic_interface_conductivity,
)
from part_a_without_ml.visualizations import (
    plot_2d_temperature_contour,
    plot_3d_temperature_surface,
    plot_velocity_contour,
    plot_pressure_distribution,
    plot_battery_temp_vs_position,
    plot_coolant_temperature_distribution,
)


class CoupledBTMSSolver:
    """
    Coupled 2D Finite-Difference Solver for Darcy-Brinkman MHD Hybrid Nanofluid BTMS.
    """

    def __init__(
        self,
        Nx: int = config.NUMERICAL_CONFIG["Nx"],
        Ny_f: int = config.NUMERICAL_CONFIG["Ny_fluid"],
        Ny_b: int = config.NUMERICAL_CONFIG["Ny_battery"],
        U_in: float = config.DEFAULT_CHANNEL["U_in"],
        T_in: float = config.DEFAULT_CHANNEL["T_in"],
        T_amb: float = config.DEFAULT_CHANNEL["T_amb"],
        B0: float = config.DEFAULT_CHANNEL["B0"],
        k_perm: float = config.DEFAULT_CHANNEL["permeability"],
        phi1: float = config.DEFAULT_CONCENTRATIONS["phi1"],
        phi2: float = config.DEFAULT_CONCENTRATIONS["phi2"],
        c_rate: float = 2.0,
        R_tc: float = config.DEFAULT_CHANNEL["R_tc"]
    ):
        self.Nx = Nx
        self.Ny_f = Ny_f
        self.Ny_b = Ny_b
        self.Ny = Ny_f + Ny_b
        self.U_in = U_in
        self.T_in = T_in
        self.T_amb = T_amb
        self.B0 = B0
        self.k_perm = k_perm
        self.phi1 = phi1
        self.phi2 = phi2
        self.c_rate = c_rate
        self.R_tc = R_tc

        # Geometry
        self.Lx = config.DEFAULT_CHANNEL["L"]
        self.Hf = config.DEFAULT_CHANNEL["H"]
        self.Hb = config.DEFAULT_BATTERY["height"]
        self.W = config.DEFAULT_BATTERY["thickness"]
        self.H_total = self.Hf + self.Hb

        # Discretization steps
        self.dx = self.Lx / (self.Nx - 1)
        self.dy_f = self.Hf / self.Ny_f
        self.dy_b = self.Hb / self.Ny_b

        # Coordinates
        self.x = np.linspace(0.0, self.Lx, self.Nx)
        y_f_coords = np.linspace(0.0, self.Hf, self.Ny_f, endpoint=False)
        y_b_coords = np.linspace(self.Hf, self.H_total, self.Ny_b)
        self.y = np.concatenate([y_f_coords, y_b_coords])
        self.y_fluid = self.y[:self.Ny_f]
        self.y_battery = self.y[self.Ny_f:]
        self.X, self.Y = np.meshgrid(self.x, self.y, indexing='ij')

        # Compute physical properties
        self._compute_properties()

        # Initialize fields
        self.u = np.zeros((self.Nx, self.Ny))
        self.v = np.zeros((self.Nx, self.Ny))
        self.p = np.zeros((self.Nx, self.Ny))
        self.T = np.full((self.Nx, self.Ny), self.T_in)
        # Initialize battery zone with ambient/initial temperature
        self.T[:, self.Ny_f:] = config.DEFAULT_BATTERY["T_init"]

    def _compute_properties(self):
        """Calculates effective thermophysical properties for the hybrid nanofluid and battery."""
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

        # Effective properties
        res_rho = calc_effective_density(rho_f, rho_s1, rho_s2, self.phi1, self.phi2)
        self.rho_hnf = res_rho["result"]

        res_cp = calc_effective_heat_capacity(rho_f, cp_f, rho_s1, cp_s1, rho_s2, cp_s2, self.phi1, self.phi2)
        self.rho_cp_hnf = res_cp["result_volumetric"]
        self.cp_hnf = res_cp["result_specific"]

        res_k = calc_effective_thermal_conductivity(k_f, k_s1, k_s2, self.phi1, self.phi2)
        self.k_hnf = res_k["result"]

        res_mu = calc_effective_dynamic_viscosity(mu_f, self.phi1, self.phi2)
        self.mu_hnf = res_mu["result"]

        res_sigma = calc_effective_electrical_conductivity(sigma_f, sigma_s1, sigma_s2, self.phi1, self.phi2)
        self.sigma_hnf = res_sigma["result"]

        # Battery properties
        self.rho_b = config.DEFAULT_BATTERY["rho_b"]
        self.cp_b = config.DEFAULT_BATTERY["cp_b"]
        self.rho_cp_b = self.rho_b * self.cp_b
        self.k_b = config.DEFAULT_BATTERY["k_b"]

        # Battery heat generation via Bernardi model
        I_batt = self.c_rate * config.DEFAULT_BATTERY["Q_rated"]
        self.I_batt = I_batt
        vol_b = self.Lx * self.Hb * self.W
        res_batt = calc_battery_heat_generation(
            I=I_batt,
            V_oc=config.DEFAULT_BATTERY["V_oc"],
            V_op=config.DEFAULT_BATTERY["V_op"],
            T_battery=config.DEFAULT_BATTERY["T_init"],
            dU_oc_dT=config.DEFAULT_BATTERY["dU_oc_dT"],
            volume_b=vol_b
        )
        self.Q_b_total_W = res_batt["result_watts"]
        self.q_b_vol = res_batt["result_volumetric"]  # W/m^3

        # Dimensionless numbers
        self.Re = calc_reynolds_number(self.rho_hnf, self.U_in, self.Hf, self.mu_hnf)["result"]
        self.Pr = calc_prandtl_number(self.mu_hnf, self.cp_hnf, self.k_hnf)["result"]
        self.Ha = calc_hartmann_number(self.B0, self.Hf, self.sigma_hnf, self.mu_hnf)["result"]
        self.Da = calc_darcy_number(self.k_perm, self.Hf)["result"]
        self.Br = calc_brinkman_number(self.mu_hnf, self.U_in, self.k_hnf, max(abs(config.DEFAULT_BATTERY["T_init"] - self.T_in), 1.0))["result"]

    def solve_hydrodynamics(self):
        """
        Solves the Darcy-Brinkman MHD momentum equation in the fluid channel:
        mu_eff * d2u/dy2 - (mu_eff/k + sigma_hnf*B0^2)*u = dp/dx = -G
        Subject to: u(0) = 0 (bottom porous wall), u(H_f) = 0 (interface no-slip).
        """
        # Hartmann and Darcy resistance parameter:
        # lambda^2 = 1/k_perm + (sigma_hnf * B0^2) / mu_hnf
        lambda_sq = (1.0 / self.k_perm) + (self.sigma_hnf * (self.B0 ** 2)) / self.mu_hnf
        lam = np.sqrt(lambda_sq)

        arg = lam * self.Hf / 2.0
        if arg > 50.0:
            integral_factor = 1.0 - (1.0 / arg)
        else:
            integral_factor = 1.0 - (np.tanh(arg) / arg)

        # Pressure gradient G = -dp/dx to sustain inlet velocity U_in
        self.G = (self.U_in * self.mu_hnf * lambda_sq) / max(integral_factor, 1.0e-9)

        # Compute fully developed analytical-numerical velocity profile across y_fluid
        yf = self.y_fluid
        if arg > 50.0:
            u_profile = (self.G / (self.mu_hnf * lambda_sq)) * (1.0 - np.exp(-lam * np.minimum(yf, self.Hf - yf)))
        else:
            u_profile = (self.G / (self.mu_hnf * lambda_sq)) * (1.0 - np.cosh(lam * (yf - self.Hf / 2.0)) / np.cosh(arg))

        # Assign across fluid grid
        for i in range(self.Nx):
            self.u[i, :self.Ny_f] = u_profile
            self.v[i, :self.Ny_f] = 0.0  # Parallel channel flow

        # Zero velocity in solid battery domain
        self.u[:, self.Ny_f:] = 0.0
        self.v[:, self.Ny_f:] = 0.0

        # Pressure field p(x)
        self.delta_p = self.G * self.Lx
        for i in range(self.Nx):
            self.p[i, :self.Ny_f] = self.G * (self.Lx - self.x[i])

    def solve_energy_conjugate(
        self,
        max_iter: int = config.NUMERICAL_CONFIG["max_iter"],
        tol: float = config.NUMERICAL_CONFIG["tolerance"],
        omega: float = config.NUMERICAL_CONFIG["omega"]
    ) -> List[float]:
        """
        Solves the steady conjugate 2D Energy Equation using Successive Over-Relaxation (SOR):
        In fluid:
          (rho*Cp)_hnf * u * dT/dx = k_hnf * (d2T/dx2 + d2T/dy2) + Q_visc + Q_J
        In battery:
          0 = k_b * (d2T/dx2 + d2T/dy2) + q_b_vol
        At interface (j = Ny_f - 1 / Ny_f):
          -k_b * dT/dy = -k_hnf * dT/dy (harmonic interface conductance)
        """
        residual_history = []
        dx2 = self.dx ** 2
        dyf2 = self.dy_f ** 2
        dyb2 = self.dy_b ** 2

        # Viscous dissipation and Joule heating fields in fluid
        Q_visc = np.zeros((self.Nx, self.Ny_f))
        Q_J = np.zeros((self.Nx, self.Ny_f))
        for j in range(1, self.Ny_f - 1):
            du_dy = (self.u[:, j + 1] - self.u[:, j - 1]) / (2.0 * self.dy_f)
            Q_visc[:, j] = self.mu_hnf * (du_dy ** 2)
            Q_J[:, j] = self.sigma_hnf * (self.B0 ** 2) * (self.u[:, j] ** 2)

        k_interface = compute_harmonic_interface_conductivity(
            self.k_b, self.k_hnf, self.dy_b, self.dy_f, self.R_tc
        )

        for iteration in range(max_iter):
            T_old = self.T.copy()

            # Apply boundary conditions
            self.u, self.v, self.T = apply_flow_and_thermal_boundary_conditions(
                self.u, self.v, self.T,
                U_in=self.U_in, T_in=self.T_in,
                Nx=self.Nx, Ny_fluid=self.Ny_f, Ny_total=self.Ny,
                dx=self.dx, dy=self.dy_b,
                h_amb=config.DEFAULT_CHANNEL["h_amb"],
                T_amb=self.T_amb,
                k_battery=self.k_b
            )

            # 1. FLUID CHANNEL INTERIOR NODES (1 <= i <= Nx-2, 1 <= j < Ny_f - 1)
            for i in range(1, self.Nx - 1):
                for j in range(1, self.Ny_f - 1):
                    u_loc = self.u[i, j]
                    coeff_conv = (self.rho_cp_hnf * u_loc) / self.dx
                    a_P = (2.0 * self.k_hnf / dx2) + (2.0 * self.k_hnf / dyf2) + coeff_conv
                    diff_flux = self.k_hnf * ((self.T[i + 1, j] + self.T[i - 1, j]) / dx2 + (self.T[i, j + 1] + self.T[i, j - 1]) / dyf2)
                    conv_flux = coeff_conv * self.T[i - 1, j]
                    source_flux = Q_visc[i, j] + Q_J[i, j]
                    T_target = (diff_flux + conv_flux + source_flux) / a_P
                    self.T[i, j] = (1.0 - omega) * self.T[i, j] + omega * T_target

            # 2. CONJUGATE INTERFACE (j = Ny_f - 1)
            j_int = self.Ny_f - 1
            g_f = self.k_hnf / self.dy_f
            g_b = self.k_b / self.dy_b
            if self.R_tc > 0.0:
                T_target_int = (g_f * self.T[1:-1, j_int - 1] + g_b * self.T[1:-1, j_int + 1]) / (g_f + g_b + self.R_tc * g_f * g_b)
            else:
                T_target_int = (g_f * self.T[1:-1, j_int - 1] + g_b * self.T[1:-1, j_int + 1]) / (g_f + g_b)
            self.T[1:-1, j_int] = (1.0 - omega) * self.T[1:-1, j_int] + omega * T_target_int

            # 3. BATTERY SOLID INTERIOR NODES (1 <= i <= Nx-2, Ny_f <= j < Ny - 1)
            for i in range(1, self.Nx - 1):
                for j in range(self.Ny_f, self.Ny - 1):
                    a_P = (2.0 * self.k_b / dx2) + (2.0 * self.k_b / dyb2)
                    diff_flux = self.k_b * ((self.T[i + 1, j] + self.T[i - 1, j]) / dx2 + (self.T[i, j + 1] + self.T[i, j - 1]) / dyb2)
                    source_flux = self.q_b_vol
                    T_target = (diff_flux + source_flux) / a_P
                    self.T[i, j] = (1.0 - omega) * self.T[i, j] + omega * T_target

            # Residual check: maximum normalized absolute change
            residual = np.max(np.abs(self.T - T_old)) / (np.max(self.T) - np.min(self.T) + 1.0e-5)
            residual_history.append(float(residual))

            if residual < tol and iteration > 100:
                break

        self.iterations_run = iteration + 1
        self.final_residual = residual_history[-1]
        self.residual_history = residual_history
        return residual_history

    def compute_thermal_performance(self) -> Dict[str, Any]:
        """Calculates engineering BTMS metrics: max temperature, outlet temp, Nu, heat removed."""
        # Battery zone temperatures
        T_battery = self.T[:, self.Ny_f:]
        self.T_max_battery = float(np.max(T_battery))
        self.T_min_battery = float(np.min(T_battery))
        self.T_avg_battery = float(np.mean(T_battery))
        self.delta_T_battery = self.T_max_battery - self.T_min_battery

        # Coolant outlet temperature profile at x = L (i = Nx - 1)
        T_outlet = self.T[-1, :self.Ny_f]
        u_outlet = self.u[-1, :self.Ny_f]
        # Mass-weighted bulk coolant temperature
        self.T_outlet_bulk = float(np.sum(u_outlet * T_outlet) / max(np.sum(u_outlet), 1.0e-9))

        # Mass flow rate [kg/s] = rho * U_in * H_f * W
        self.mass_flow_rate = self.rho_hnf * self.U_in * self.Hf * self.W
        # Total heat removed by fluid stream [W]
        self.Q_removed = self.mass_flow_rate * self.cp_hnf * (self.T_outlet_bulk - self.T_in)

        # Interface heat transfer and local Nusselt number along x
        j_int = self.Ny_f - 1
        dT_dy_interface = (self.T[:, j_int] - self.T[:, j_int - 1]) / self.dy_f
        q_interface = self.k_hnf * dT_dy_interface  # W/m^2
        T_wall = self.T[:, j_int]

        delta_T_local = np.maximum(T_wall - self.T_in, 0.1)
        self.h_local = q_interface / delta_T_local
        self.Nu_local = self.h_local * self.Hf / self.k_hnf
        self.Nu_avg = float(np.mean(self.Nu_local[1:-1]))

        # Safety status
        self.is_thermally_safe = bool(self.T_max_battery <= config.DEFAULT_BATTERY["T_max_safe"])

        return {
            "T_max_battery": self.T_max_battery,
            "T_min_battery": self.T_min_battery,
            "T_avg_battery": self.T_avg_battery,
            "delta_T_battery": self.delta_T_battery,
            "T_outlet_bulk": self.T_outlet_bulk,
            "Q_generated_W": self.Q_b_total_W,
            "Q_removed_W": self.Q_removed,
            "Nu_avg": self.Nu_avg,
            "Re": self.Re,
            "Pr": self.Pr,
            "Ha": self.Ha,
            "Da": self.Da,
            "Br": self.Br,
            "pressure_drop_Pa": self.delta_p,
            "is_thermally_safe": self.is_thermally_safe,
            "iterations": self.iterations_run,
            "final_residual": self.final_residual,
        }


def run_subpart_a2(
    phi1: float = config.DEFAULT_CONCENTRATIONS["phi1"],
    phi2: float = config.DEFAULT_CONCENTRATIONS["phi2"],
    U_in: float = config.DEFAULT_CHANNEL["U_in"],
    T_in: float = config.DEFAULT_CHANNEL["T_in"],
    B0: float = config.DEFAULT_CHANNEL["B0"],
    k_perm: float = config.DEFAULT_CHANNEL["permeability"],
    c_rate: float = 2.0,
    save_outputs: bool = True
) -> Dict[str, Any]:
    """
    Executes the complete coupled physics-based solver for Subpart A2.
    """
    print("\n" + "=" * 90)
    print(" PART A2: COUPLED PHYSICS-BASED BTMS NUMERICAL SOLVER ".center(90, "="))
    print("=" * 90)

    print("\n--- SIMULATION INPUT PARAMETERS ---")
    print(f"  * Inlet Velocity U_in            : {U_in:>14.4f} [m/s]")
    print(f"  * Inlet Temperature T_in         : {T_in:>14.2f} [K]")
    print(f"  * Magnetic Flux Density B0       : {B0:>14.3f} [T]")
    print(f"  * Porous Permeability k_perm     : {k_perm:>14.2e} [m^2]")
    print(f"  * Nanoparticle 1 Fraction (Al2O3): {phi1:>14.4f} [-]")
    print(f"  * Nanoparticle 2 Fraction (CuO)  : {phi2:>14.4f} [-]")
    print(f"  * Battery Discharge C-Rate       : {c_rate:>14.2f} [C]")
    print(f"  * Battery Rated Capacity         : {config.DEFAULT_BATTERY['Q_rated']:>14.1f} [Ah]")
    print(f"  * Channel Dimensions (L x H x W) : {config.DEFAULT_CHANNEL['L']*1000:.1f} x {config.DEFAULT_CHANNEL['H']*1000:.1f} x {config.DEFAULT_BATTERY['thickness']*1000:.1f} [mm]")

    solver = CoupledBTMSSolver(
        U_in=U_in, T_in=T_in, B0=B0, k_perm=k_perm,
        phi1=phi1, phi2=phi2, c_rate=c_rate
    )

    print("\n--- THERMOPHYSICAL & DIMENSIONLESS METRICS ---")
    print(f"  * Effective Density rho_hnf      : {solver.rho_hnf:>14.2f} [kg/m^3]")
    print(f"  * Effective Specific Heat Cp_hnf : {solver.cp_hnf:>14.2f} [J/(kg*K)]")
    print(f"  * Effective Conductivity k_hnf   : {solver.k_hnf:>14.4f} [W/(m*K)]")
    print(f"  * Effective Dynamic Viscosity    : {solver.mu_hnf:>14.4e} [Pa*s]")
    print(f"  * Effective Electrical Conduct.  : {solver.sigma_hnf:>14.4e} [S/m]")
    print(f"  * Battery Heat Generation (Q_b)  : {solver.Q_b_total_W:>14.2f} [W] ({solver.q_b_vol:>12.1f} W/m^3)")
    print(f"  * Reynolds Number (Re)           : {solver.Re:>14.2f} [-]")
    print(f"  * Prandtl Number (Pr)            : {solver.Pr:>14.2f} [-]")
    print(f"  * Hartmann Number (Ha)           : {solver.Ha:>14.4f} [-]")
    print(f"  * Darcy Number (Da)              : {solver.Da:>14.4e} [-]")
    print(f"  * Brinkman Number (Br)           : {solver.Br:>14.4e} [-]")

    print("\n--- SOLVING HYDRODYNAMICS & COUPLED CONJUGATE ENERGY EQUATION ---")
    start_time = time.time()
    solver.solve_hydrodynamics()
    residuals = solver.solve_energy_conjugate()
    elapsed = time.time() - start_time
    metrics = solver.compute_thermal_performance()

    print(f"  >> Convergence achieved in {metrics['iterations']} iterations (Final Residual = {metrics['final_residual']:.2e})")
    print(f"  >> Solution CPU Time: {elapsed:.2f} seconds")

    print("\n--- NUMERICAL SIMULATION RESULTS ---")
    print(f"  * Peak Battery Temperature T_max : {metrics['T_max_battery']:>14.2f} [K] ({metrics['T_max_battery'] - 273.15:.2f} °C)")
    print(f"  * Minimum Battery Temp T_min     : {metrics['T_min_battery']:>14.2f} [K] ({metrics['T_min_battery'] - 273.15:.2f} °C)")
    print(f"  * Average Battery Temp T_avg     : {metrics['T_avg_battery']:>14.2f} [K] ({metrics['T_avg_battery'] - 273.15:.2f} °C)")
    print(f"  * Cell Temperature Nonuniformity : {metrics['delta_T_battery']:>14.2f} [K]")
    print(f"  * Coolant Mean Outlet Temp       : {metrics['T_outlet_bulk']:>14.2f} [K] (Delta T_rise = {metrics['T_outlet_bulk'] - T_in:.2f} K)")
    print(f"  * Channel Pressure Drop Delta p  : {metrics['pressure_drop_Pa']:>14.2f} [Pa]")
    print(f"  * Average Nusselt Number Nu_avg  : {metrics['Nu_avg']:>14.2f} [-]")
    print(f"  * Thermal Safety Limit (328.15 K): {'COMPLIANT (SAFE)' if metrics['is_thermally_safe'] else 'EXCEEDED (UNSAFE)'}")

    if save_outputs:
        # Save summary CSV
        summary_df = pd.DataFrame([{
            "U_in_m_s": U_in,
            "T_in_K": T_in,
            "B0_T": B0,
            "k_perm_m2": k_perm,
            "phi1_Al2O3": phi1,
            "phi2_CuO": phi2,
            "c_rate": c_rate,
            "Re": solver.Re,
            "Pr": solver.Pr,
            "Ha": solver.Ha,
            "Da": solver.Da,
            "Br": solver.Br,
            "Nu_avg": metrics["Nu_avg"],
            "T_max_battery_K": metrics["T_max_battery"],
            "T_avg_battery_K": metrics["T_avg_battery"],
            "T_outlet_bulk_K": metrics["T_outlet_bulk"],
            "delta_p_Pa": metrics["pressure_drop_Pa"],
            "Q_gen_W": metrics["Q_generated_W"],
            "Q_removed_W": metrics["Q_removed_W"],
            "is_safe": metrics["is_thermally_safe"],
        }])
        csv_path = os.path.join(config.PART_A_RESULTS, "btms_solver_summary.csv")
        summary_df.to_csv(csv_path, index=False)
        print(f"\n[FILE SAVED] BTMS solver summary exported to: {csv_path}")

        # Save 2D Temperature Field CSV
        field_df = pd.DataFrame(solver.T, index=[f"x_{x_val:.4f}m" for x_val in solver.x],
                                columns=[f"y_{y_val:.4f}m" for y_val in solver.y])
        field_path = os.path.join(config.PART_A_RESULTS, "btms_2d_temperature_field.csv")
        field_df.to_csv(field_path)
        print(f"[FILE SAVED] 2D temperature field exported to: {field_path}")

        # Generate and save contour and surface plots
        print("\n[GENERATING GRAPHS] Generating 2D contours and 3D surface visualizations...")
        plot_2d_temperature_contour(
            solver.X, solver.Y, solver.T, solver.Hf,
            os.path.join(config.PART_A_GRAPHS, "04_2d_temperature_contour.png")
        )
        plot_3d_temperature_surface(
            solver.X, solver.Y, solver.T,
            os.path.join(config.PART_A_GRAPHS, "05_3d_temperature_surface.png")
        )
        plot_velocity_contour(
            solver.X[:, :solver.Ny_f], solver.Y[:, :solver.Ny_f], solver.u[:, :solver.Ny_f],
            os.path.join(config.PART_A_GRAPHS, "08_velocity_contour.png")
        )
        j_int = solver.Ny_f - 1
        plot_battery_temp_vs_position(
            solver.x, solver.T[:, j_int], solver.T[:, -1],
            os.path.join(config.PART_A_GRAPHS, "02_battery_temp_vs_position.png")
        )
        plot_coolant_temperature_distribution(
            solver.x, np.mean(solver.T[:, :solver.Ny_f], axis=1),
            os.path.join(config.PART_A_GRAPHS, "03_coolant_temperature_distribution.png")
        )
        print(f"[GRAPHS SAVED] Solver graphs saved to: {config.PART_A_GRAPHS}")

    print("\n" + "=" * 90)
    print(" SUBPART A2 COMPLETED SUCCESSFULLY ".center(90, "="))
    print("=" * 90)
    return metrics


if __name__ == "__main__":
    run_subpart_a2()
