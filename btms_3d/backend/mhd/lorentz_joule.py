"""
Magnetohydrodynamic (MHD) Lorentz Force and Joule Heating Solver
Implements Formulas 13, 14, and 22 for transverse magnetic field flow control.
"""

import numpy as np
from typing import Dict, Any


class MHDSolver:
    """Calculates electromagnetic body forces, Joule dissipation, and Hartmann flow damping."""

    MU_0 = 1.25663706e-6  # Permeability of free space [H/m or N/A^2]

    @staticmethod
    def calculate_mhd_effects(sigma_hnf: float, B0: float, u_velocity: float,
                              Dh: float = 0.010, mu_hnf: float = 8.91e-4) -> Dict[str, Any]:
        """Calculates Hartmann number, Lorentz body force, Joule heating, and magnetic field H."""
        B0 = max(float(B0), 0.0)
        u_velocity = max(float(u_velocity), 0.0)
        sigma_hnf = max(float(sigma_hnf), 0.0)
        mu_hnf = max(float(mu_hnf), 1.0e-9)
        Dh = max(float(Dh), 1.0e-4)

        # Eq 22: Hartmann Number
        sqrt_term = np.sqrt(sigma_hnf / mu_hnf)
        Ha = float(B0 * Dh * sqrt_term)

        # Eq 13: Lorentz Electromagnetic Body Force [N/m^3]
        f_lorentz = float(-sigma_hnf * (B0 ** 2) * u_velocity)

        # Eq 15: Volumetric Motional Joule Heating [W/m^3]
        q_joule = float(sigma_hnf * (B0 ** 2) * (u_velocity ** 2))

        # Eq 14: Magnetic Field Intensity H [A/m]
        H_field = float(B0 / MHDSolver.MU_0)

        # Hartmann velocity flattening factor
        if Ha > 0.05:
            damping_factor = float(1.0 / (1.0 + 0.12 * (Ha ** 1.2)))
        else:
            damping_factor = 1.0

        return {
            "B0_Tesla": B0,
            "H_field_A_m": H_field,
            "hartmann_number": Ha,
            "Hartmann_number_Ha": Ha,
            "Ha": Ha,
            "lorentz_force_N_m3": f_lorentz,
            "joule_heating_W_m3": q_joule,
            "mhd_active": bool(B0 > 0.01),
            "velocity_damping_factor": damping_factor,
            "flow_suppression_pct": float((1.0 - damping_factor) * 100.0),
        }
