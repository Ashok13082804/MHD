"""
Porous Media Hydrodynamic & Thermal Solver
Implements Formulas 9, 12, and 23 for Darcy-Brinkman-Forchheimer porous inserts.
"""

import numpy as np
from typing import Dict, Any


class PorousMediaSolver:
    """Calculates flow resistance and effective thermal properties for metal-foam porous channels."""

    @staticmethod
    def calculate_porous_properties(k_perm: float, porosity: float, k_hnf: float,
                                    k_matrix: float = 167.0, Dh: float = 0.010) -> Dict[str, Any]:
        """Calculates Darcy number and effective porous medium thermal conductivity."""
        porosity = min(max(float(porosity), 0.1), 0.99)
        k_perm = max(float(k_perm), 1.0e-12)
        Dh = max(float(Dh), 1.0e-4)

        # Eq 9: Effective Porous Thermal Conductivity
        k_eff = float(porosity * k_hnf + (1.0 - porosity) * k_matrix)

        # Eq 23: Darcy Number
        Da = float(k_perm / (Dh ** 2))

        return {
            "porosity": porosity,
            "permeability_k": k_perm,
            "k_matrix_solid": k_matrix,
            "k_eff_porous": k_eff,
            "darcy_number": Da,
            "conduction_solid_fraction": (1.0 - porosity) * k_matrix,
            "conduction_fluid_fraction": porosity * k_hnf,
        }

    @staticmethod
    def calculate_pressure_drop(rho: float, mu: float, u: float, length: float,
                                k_perm: float, porosity: float = 0.85, CF: float = 0.55) -> Dict[str, Any]:
        """
        Calculates pressure drop across porous channel:
        dp/dx = (mu / k_perm)*u + (rho * CF / sqrt(k_perm))*u^2
        """
        u = max(float(u), 1.0e-5)
        length = max(float(length), 1.0e-3)
        k_perm = max(float(k_perm), 1.0e-12)

        dp_dx_darcy = (mu / k_perm) * u
        dp_dx_forchheimer = (rho * CF / np.sqrt(k_perm)) * (u ** 2)
        dp_dx_total = dp_dx_darcy + dp_dx_forchheimer
        delta_p = float(dp_dx_total * length)

        Dh = 0.010  # standard channel hydraulic diameter
        f_darcy = float(2.0 * delta_p * Dh / max(rho * (u ** 2) * length, 1.0e-6))

        return {
            "delta_p_Pa": delta_p,
            "dp_dx_Pa_m": float(dp_dx_total),
            "darcy_drag_pct": float((dp_dx_darcy / dp_dx_total) * 100.0),
            "forchheimer_drag_pct": float((dp_dx_forchheimer / dp_dx_total) * 100.0),
            "apparent_friction_factor": f_darcy,
        }
