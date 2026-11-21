"""
Unit Tests for Machine Learning Pipeline and Predictions (Part B)
"""

import unittest
import os
import joblib
import numpy as np
import pandas as pd
import config
from part_b_with_ml.feature_preprocessing import split_and_scale_data, INPUT_FEATURES
from part_b_with_ml.B2_prediction import predict_btms_performance


class TestMLPredictions(unittest.TestCase):

    def test_feature_scaling_and_split(self):
        # Create synthetic test dataframe
        n = 50
        data = {feat: np.random.uniform(1.0, 10.0, n) for feat in INPUT_FEATURES}
        data["T_max_battery"] = np.random.uniform(300.0, 350.0, n)
        df = pd.DataFrame(data)

        split_dict = split_and_scale_data(df, features=INPUT_FEATURES, target="T_max_battery")
        self.assertIn("X_train_scaled", split_dict)
        self.assertIn("scaler_X", split_dict)
        # Check standard scaling mean near 0 and std near 1
        means = np.mean(split_dict["X_train_scaled"], axis=0)
        np.testing.assert_allclose(means, 0.0, atol=1e-5)

    def test_prediction_execution(self):
        # Predict using gradient boosting
        res = predict_btms_performance(
            U_in=0.06, T_in=298.15, B0=0.4, phi1=0.02, phi2=0.01,
            c_rate=1.5, model_name="gradient_boosting", save_outputs=False
        )
        self.assertIn("T_max_ml", res)
        self.assertIn("T_max_phys", res)
        self.assertIn("abs_error", res)
        self.assertLess(res["rel_error_pct"], 5.0)  # error must be within 5%


if __name__ == "__main__":
    unittest.main()
