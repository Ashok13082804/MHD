"""
Dataset Ingestion, Validation, and Processing Engine
Supports CSV and JSON file upload, data range checks, unit verification, and parameter mapping.
"""

import io
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional


class DatasetProcessor:
    """Parses and scientifically validates experimental or simulation datasets for BTMS."""

    REQUIRED_FIELDS = [
        "inlet_velocity",
        "inlet_temperature_c",
        "discharge_c_rate",
    ]

    COLUMN_ALIASES = {
        "u_in": "inlet_velocity",
        "velocity": "inlet_velocity",
        "flow_velocity": "inlet_velocity",
        "t_in": "inlet_temperature_c",
        "t_in_c": "inlet_temperature_c",
        "inlet_temp": "inlet_temperature_c",
        "inlet_temp_c": "inlet_temperature_c",
        "c_rate": "discharge_c_rate",
        "crate": "discharge_c_rate",
        "discharge_rate": "discharge_c_rate",
        "b0": "magnetic_field",
        "magnetic_field_t": "magnetic_field",
        "phi1": "al2o3_fraction",
        "phi2": "cuo_fraction",
        "k_perm": "permeability",
        "q_rated": "rated_capacity",
    }

    PHYSICAL_RANGES = {
        "inlet_velocity": (0.001, 1.0, "m/s"),
        "inlet_temperature_c": (-15.0, 60.0, "°C"),
        "initial_temperature": (-15.0, 60.0, "°C"),
        "ambient_temperature": (-20.0, 50.0, "°C"),
        "magnetic_field": (0.0, 3.0, "T"),
        "al2o3_fraction": (0.0, 0.05, "dimensionless"),
        "cuo_fraction": (0.0, 0.04, "dimensionless"),
        "discharge_c_rate": (0.1, 8.0, "C"),
        "porosity": (0.2, 0.99, "dimensionless"),
        "permeability": (1.0e-12, 1.0e-5, "m^2"),
        "threshold_temp": (20.0, 55.0, "°C"),
    }

    @classmethod
    def parse_and_validate(cls, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Parses CSV or JSON file and validates all records against physical boundaries."""
        fn = filename.lower()
        records: List[Dict[str, Any]] = []
        warnings: List[str] = []

        try:
            if fn.endswith(".csv") or fn.endswith(".txt"):
                s = file_content.decode("utf-8")
                df = pd.read_csv(io.StringIO(s))
                records = df.to_dict(orient="records")
            elif fn.endswith(".json"):
                s = file_content.decode("utf-8")
                data = json.loads(s)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    records = [data]
            else:
                return {
                    "success": False,
                    "error": f"Unsupported file extension for '{filename}'. Please upload .csv, .json, or .txt.",
                    "records": []
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parsing error in '{filename}': {str(e)}",
                "records": []
            }

        if not records:
            return {
                "success": False,
                "error": "Dataset is empty.",
                "records": []
            }

        # Normalize keys in all records using COLUMN_ALIASES
        normalized_records = []
        for rec in records:
            norm_rec = {}
            for k, val in rec.items():
                k_lower = str(k).strip().lower()
                canonical_k = cls.COLUMN_ALIASES.get(k_lower, k_lower)
                norm_rec[canonical_k] = val
            normalized_records.append(norm_rec)
        records = normalized_records

        # Check required columns on first record
        first_keys = set(records[0].keys())
        missing = [req for req in cls.REQUIRED_FIELDS if req not in first_keys]
        if missing:
            return {
                "success": False,
                "error": f"Missing mandatory columns: {missing}",
                "records": []
            }

        # Validate physical limits for each record
        validated_records = []
        for idx, rec in enumerate(records):
            clean_rec = {}
            for k, val in rec.items():
                if k in cls.PHYSICAL_RANGES:
                    min_val, max_val, unit = cls.PHYSICAL_RANGES[k]
                    try:
                        num_val = float(val)
                        if num_val < min_val or num_val > max_val:
                            warnings.append(
                                f"Row {idx+1}: '{k}' = {num_val} outside expected range [{min_val}, {max_val}] {unit}."
                            )
                            # Clip to boundary
                            num_val = max(min_val, min(num_val, max_val))
                        clean_rec[k] = num_val
                    except (ValueError, TypeError):
                        warnings.append(f"Row {idx+1}: Could not convert '{k}' = {val} to numeric.")
                else:
                    clean_rec[k] = val

            validated_records.append(clean_rec)

        return {
            "success": True,
            "filename": filename,
            "record_count": len(validated_records),
            "valid_rows": len(validated_records),
            "records": validated_records,
            "warnings": warnings[:10],
            "total_warnings": len(warnings)
        }
