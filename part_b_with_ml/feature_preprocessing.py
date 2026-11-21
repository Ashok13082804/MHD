"""
Feature Preprocessing and Pipeline Utilities for Part B
Handles dataset splitting, normalization, standardization, and feature schema definitions.
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Any
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler

# Core input features for physical models
INPUT_FEATURES = [
    "U_in",               # Inlet velocity [m/s]
    "T_in",               # Inlet temperature [K]
    "T_batt_init",        # Initial battery temperature [K]
    "T_amb",              # Ambient temperature [K]
    "B0",                 # Magnetic field [T]
    "phi1",               # Al2O3 volume fraction [-]
    "phi2",               # CuO volume fraction [-]
    "k_perm",             # Porous permeability [m^2]
    "c_rate",             # Discharge C-rate [C]
    "Q_rated",            # Rated battery capacity [Ah]
    "L_char",             # Characteristic height [m]
]

# Physical and thermal output targets
PRIMARY_TARGETS = [
    "T_max_battery",      # Maximum battery temperature [K]
    "T_avg_battery",      # Average battery temperature [K]
    "T_outlet_bulk",      # Coolant bulk outlet temperature [K]
    "Nu_avg",             # Average Nusselt number [-]
    "delta_p",            # Pressure drop [Pa]
    "Q_b_W",              # Battery heat generation [W]
    "Q_J_W_m3",           # Volumetric Joule heating [W/m^3]
    "Lorentz_force_x",    # Lorentz retarding force [N/m^3]
    "rho_hnf",            # Effective hybrid nanofluid density [kg/m^3]
    "k_hnf",              # Effective thermal conductivity [W/(m*K)]
    "mu_hnf",             # Effective dynamic viscosity [Pa*s]
    "cp_hnf",             # Mass-specific heat capacity [J/(kg*K)]
    "Re",                 # Reynolds number [-]
    "Pr",                 # Prandtl number [-]
    "Ha",                 # Hartmann number [-]
    "Da",                 # Darcy number [-]
    "Br",                 # Brinkman number [-]
]


def split_and_scale_data(
    df: pd.DataFrame,
    features: List[str] = INPUT_FEATURES,
    target: str = "T_max_battery",
    test_size: float = 0.15,
    val_size: float = 0.15,
    random_state: int = 42,
    scaler_type: str = "standard"
) -> Dict[str, Any]:
    """
    Splits dataset into Train (70%), Validation (15%), and Test (15%) sets,
    and applies standardization to prevent data leakage.
    """
    X = df[features].values
    y = df[target].values

    # Step 1: Split train+val vs test
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, shuffle=True
    )

    # Step 2: Split train vs val
    val_ratio = val_size / (1.0 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_ratio, random_state=random_state, shuffle=True
    )

    # Fit scaler strictly on training data
    if scaler_type == "minmax":
        scaler_X = MinMaxScaler()
    else:
        scaler_X = StandardScaler()

    X_train_scaled = scaler_X.fit_transform(X_train)
    X_val_scaled = scaler_X.transform(X_val)
    X_test_scaled = scaler_X.transform(X_test)

    return {
        "X_train": X_train,
        "X_val": X_val,
        "X_test": X_test,
        "X_train_scaled": X_train_scaled,
        "X_val_scaled": X_val_scaled,
        "X_test_scaled": X_test_scaled,
        "y_train": y_train,
        "y_val": y_val,
        "y_test": y_test,
        "scaler_X": scaler_X,
        "features": features,
        "target": target,
    }


def save_preprocessor(scaler: Any, save_path: str):
    """Saves fitted scaler to disk."""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    joblib.dump(scaler, save_path)


def load_preprocessor(load_path: str) -> Any:
    """Loads fitted scaler from disk."""
    return joblib.load(load_path)
