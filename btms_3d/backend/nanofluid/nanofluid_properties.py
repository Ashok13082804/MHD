"""
Hybrid Nanofluid Thermophysical Property Engine
Implements Formulas 4, 5, 6, 7, and 8 for Water/Al2O3-CuO hybrid suspensions.
"""

from typing import Dict, Any, Tuple


class NanofluidPropertyEngine:
    """Calculates density, heat capacity, viscosity, and thermal conductivity of hybrid nanofluid."""

    # Base Fluid: Pure Water at 25 deg C
    RHO_BF = 997.10       # kg/m^3
    CP_BF = 4179.0        # J/(kg*K)
    K_BF = 0.6130         # W/(m*K)
    MU_BF = 8.91e-4       # Pa*s
    SIGMA_BF = 0.0550     # S/m

    # Nanoparticle 1: Al2O3 (Alumina)
    RHO_NP1 = 3970.0
    CP_NP1 = 765.0
    K_NP1 = 40.0
    SIGMA_NP1 = 1.0e-10

    # Nanoparticle 2: CuO (Copper Oxide)
    RHO_NP2 = 6320.0
    CP_NP2 = 531.8
    K_NP2 = 76.5
    SIGMA_NP2 = 2.7e-6

    @classmethod
    def calculate_properties(cls, phi1: float = 0.02, phi2: float = 0.01) -> Dict[str, Any]:
        """Calculates effective thermophysical properties for given volume fractions."""
        phi1 = max(float(phi1), 0.0)
        phi2 = max(float(phi2), 0.0)
        phi_total = phi1 + phi2

        if phi_total >= 0.08:
            phi_total = 0.079
            phi1 = phi_total * 0.66
            phi2 = phi_total * 0.34

        # 1. Density (Eq 5)
        term_f = (1.0 - phi_total) * cls.RHO_BF
        term_s1 = phi1 * cls.RHO_NP1
        term_s2 = phi2 * cls.RHO_NP2
        rho_hnf = term_f + term_s1 + term_s2

        # 2. Specific Heat Capacity (Eq 6)
        vol_cp_f = (1.0 - phi_total) * (cls.RHO_BF * cls.CP_BF)
        vol_cp_s1 = phi1 * (cls.RHO_NP1 * cls.CP_NP1)
        vol_cp_s2 = phi2 * (cls.RHO_NP2 * cls.CP_NP2)
        rho_cp_hnf = vol_cp_f + vol_cp_s1 + vol_cp_s2
        cp_hnf = rho_cp_hnf / max(rho_hnf, 1.0)

        # 3. Dynamic Viscosity (Eq 7 - Brinkman)
        mu_hnf = cls.MU_BF / max((1.0 - phi_total) ** 2.5, 1.0e-6)

        # 4. Thermal Conductivity (Eq 8 - Maxwell)
        if phi_total <= 0.0:
            k_hnf = cls.K_BF
            ks = 0.0
        else:
            ks = (phi1 * cls.K_NP1 + phi2 * cls.K_NP2) / phi_total
            num = ks + 2.0 * cls.K_BF - 2.0 * phi_total * (cls.K_BF - ks)
            den = ks + 2.0 * cls.K_BF + phi_total * (cls.K_BF - ks)
            k_hnf = cls.K_BF * (num / max(den, 1.0e-6))

        # 5. Electrical Conductivity (Maxwell)
        if phi_total <= 0.0:
            sigma_hnf = cls.SIGMA_BF
        else:
            sigma_s = (phi1 * cls.SIGMA_NP1 + phi2 * cls.SIGMA_NP2) / phi_total
            r = sigma_s / max(cls.SIGMA_BF, 1.0e-9)
            num_sig = 3.0 * (r - 1.0) * phi_total
            den_sig = (r + 2.0) - (r - 1.0) * phi_total
            sigma_hnf = cls.SIGMA_BF * (1.0 + num_sig / max(den_sig, 1.0e-6))

        enhancement_k = ((k_hnf / cls.K_BF) - 1.0) * 100.0
        increase_mu = ((mu_hnf / cls.MU_BF) - 1.0) * 100.0

        return {
            "phi1": phi1,
            "phi2": phi2,
            "phi_total": phi_total,
            "rho_hnf": float(rho_hnf),
            "rho_cp_hnf": float(rho_cp_hnf),
            "cp_hnf": float(cp_hnf),
            "k_hnf": float(k_hnf),
            "mu_hnf": float(mu_hnf),
            "sigma_hnf": float(sigma_hnf),
            "enhancement_k_pct": float(enhancement_k),
            "increase_mu_pct": float(increase_mu),
        }
