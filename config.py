"""
Configuration and Physical Property Constants
BTMS MHD Hybrid Nanofluid Simulation Project
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any

# Ensure matplotlib writable cache directory to prevent warnings in sandboxed environments
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

# Base project paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Sub-output directories
PART_A_RESULTS = os.path.join(OUTPUTS_DIR, "part_a", "numerical_results")
PART_A_GRAPHS = os.path.join(OUTPUTS_DIR, "part_a", "graphs")
PART_A_REPORTS = os.path.join(OUTPUTS_DIR, "part_a", "reports")

PART_B_PREDICTIONS = os.path.join(OUTPUTS_DIR, "part_b", "predictions")
PART_B_GRAPHS = os.path.join(OUTPUTS_DIR, "part_b", "graphs")
PART_B_METRICS = os.path.join(OUTPUTS_DIR, "part_b", "model_metrics")
PART_B_REPORTS = os.path.join(OUTPUTS_DIR, "part_b", "reports")

# Make sure all directories exist
for d in [
    DATA_DIR, OUTPUTS_DIR, MODELS_DIR,
    PART_A_RESULTS, PART_A_GRAPHS, PART_A_REPORTS,
    PART_B_PREDICTIONS, PART_B_GRAPHS, PART_B_METRICS, PART_B_REPORTS,
    os.path.join(MODELS_DIR, "random_forest"),
    os.path.join(MODELS_DIR, "gradient_boosting"),
    os.path.join(MODELS_DIR, "svr"),
    os.path.join(MODELS_DIR, "xgboost"),
    os.path.join(MODELS_DIR, "neural_network")
]:
    os.makedirs(d, exist_ok=True)


# ==============================================================================
# 1. BASE FLUID THERMOPHYSICAL PROPERTIES (Water at T ~ 300 K)
# ==============================================================================
DEFAULT_BASE_FLUID = {
    "name": "Pure Water (H2O)",
    "rho": 997.1,          # Density [kg/m^3]
    "cp": 4179.0,          # Specific heat capacity [J/(kg*K)]
    "k": 0.613,            # Thermal conductivity [W/(m*K)]
    "mu": 8.91e-4,         # Dynamic viscosity [Pa*s or kg/(m*s)]
    "sigma": 0.055,        # Electrical conductivity [S/m]
}

# ==============================================================================
# 2. NANOPARTICLE THERMOPHYSICAL PROPERTIES
# ==============================================================================
NANOPARTICLES = {
    "Al2O3": {
        "name": "Aluminium Oxide (Al2O3)",
        "rho": 3970.0,     # Density [kg/m^3]
        "cp": 765.0,       # Specific heat capacity [J/(kg*K)]
        "k": 40.0,         # Thermal conductivity [W/(m*K)]
        "sigma": 1.0e-10,  # Electrical conductivity [S/m] (dielectric insulator)
    },
    "CuO": {
        "name": "Copper(II) Oxide (CuO)",
        "rho": 6320.0,     # Density [kg/m^3]
        "cp": 531.8,       # Specific heat capacity [J/(kg*K)]
        "k": 76.5,         # Thermal conductivity [W/(m*K)]
        "sigma": 2.7e-6,   # Electrical conductivity [S/m] (semiconductor)
    },
    "Fe3O4": {
        "name": "Magnetite (Fe3O4)",
        "rho": 5180.0,
        "cp": 670.0,
        "k": 8.0,
        "sigma": 2.5e4,
    }
}

# ==============================================================================
# 3. BATTERY THERMOPHYSICAL & ELECTROCHEMICAL PROPERTIES (Li-ion Pouch Cell)
# ==============================================================================
DEFAULT_BATTERY = {
    "name": "Lithium-Ion NMC Pouch Cell (20 Ah)",
    "length": 0.150,       # Length L_b [m] (150 mm)
    "height": 0.065,       # Height H_b [m] (65 mm)
    "thickness": 0.010,    # Thickness W_b [m] (10 mm)
    "rho_b": 2092.0,       # Battery bulk density [kg/m^3]
    "cp_b": 1100.0,        # Battery bulk specific heat [J/(kg*K)]
    "k_b": 3.0,            # In-plane / effective thermal conductivity [W/(m*K)]
    "k_b_transverse": 1.0, # Cross-plane thermal conductivity [W/(m*K)]
    "Q_rated": 20.0,       # Rated battery capacity [Ah]
    "V_oc": 3.85,          # Open-circuit voltage [V]
    "V_op": 3.65,          # Operating voltage under load [V]
    "dU_oc_dT": -0.00045,  # Temperature coefficient of OCV [V/K]
    "R_internal": 0.010,   # Internal resistance [Ohm]
    "T_init": 300.0,       # Initial battery temperature [K]
    "T_max_safe": 328.15,  # Maximum safe operating temperature (55 deg C) [K]
}

# ==============================================================================
# 4. COOLING CHANNEL & POROUS MEDIUM SPECIFICATIONS
# ==============================================================================
DEFAULT_CHANNEL = {
    "L": 0.150,            # Channel length [m] (matches battery length)
    "H": 0.010,            # Channel height [m] (10 mm)
    "W": 0.010,            # Channel width [m]
    "permeability": 1.0e-7,# Porous medium permeability k [m^2]
    "porosity": 0.85,      # Porosity epsilon [-]
    "U_in": 0.05,          # Coolant inlet velocity [m/s]
    "T_in": 298.15,        # Coolant inlet temperature [K] (25 deg C)
    "T_amb": 298.15,       # Ambient temperature [K]
    "B0": 0.5,             # Applied transverse magnetic field [T] (Tesla)
    "h_amb": 5.0,          # Natural convective coefficient to ambient [W/(m^2*K)]
    "R_tc": 0.0,           # Thermal contact resistance at interface [m^2*K/W]
}

# ==============================================================================
# 5. DEFAULT NANOPARTICLE CONCENTRATIONS
# ==============================================================================
DEFAULT_CONCENTRATIONS = {
    "phi1": 0.02,          # Volume fraction Al2O3 (2.0%)
    "phi2": 0.01,          # Volume fraction CuO (1.0%)
}

# ==============================================================================
# 6. MESH & NUMERICAL SOLVER SETTINGS
# ==============================================================================
NUMERICAL_CONFIG = {
    "Nx": 60,              # Number of grid cells in X-direction
    "Ny_fluid": 25,        # Number of grid cells in fluid channel
    "Ny_battery": 25,      # Number of grid cells in battery cell
    "max_iter": 4000,      # Maximum iterations for solver
    "tolerance": 1.0e-6,   # Convergence tolerance for relative temperature residuals
    "omega": 0.8,          # Under-relaxation factor for energy equation
    "dt": 0.05,            # Time step for transient solver [s]
    "t_final": 600.0,      # Final simulation time for transient BTMS [s] (10 min)
}
