#!/usr/bin/env python3
"""
SUBPART B1: Machine Learning Model Training Module
Trains and compares 5 regression models on the physics-informed BTMS dataset:
  1. Random Forest Regressor
  2. XGBoost Regressor
  3. Support Vector Regression (SVR)
  4. Gradient Boosting Regressor
  5. Artificial Neural Network (MLP / Deep PyTorch Architecture)

Evaluates:
  - Mean Absolute Error (MAE)
  - Mean Squared Error (MSE)
  - Root Mean Squared Error (RMSE)
  - R² Score (Coefficient of Determination)
  - Training Time and Inference Latency
  - Saves all trained models to disk
  - Exports performance metrics to CSV
  - Generates Plots 21, 22, and 23
"""

import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import sys
import time
import joblib
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
import xgboost as xgb

import config
from part_b_with_ml.feature_preprocessing import (
    split_and_scale_data,
    save_preprocessor,
    INPUT_FEATURES
)
from part_b_with_ml.model_evaluation import (
    evaluate_regression_model,
    plot_actual_vs_predicted,
    plot_model_comparison_bar,
    plot_prediction_error_distribution
)


def train_and_evaluate_all_models(
    dataset_path: str = os.path.join(config.DATA_DIR, "processed_dataset.csv"),
    target_col: str = "T_max_battery",
    save_models: bool = True
) -> pd.DataFrame:
    """
    Trains and benchmarks all 5 regression models on the physics-based dataset.
    """
    print("\n" + "=" * 90)
    print(" PART B1: MACHINE LEARNING MODEL TRAINING & COMPARISON ".center(90, "="))
    print("=" * 90)

    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}. Generating now...")
        from part_b_with_ml.B1_dataset_generation import generate_physics_dataset
        df = generate_physics_dataset(n_samples=1500)
    else:
        df = pd.read_csv(dataset_path)

    print(f"Loaded dataset: {df.shape[0]} samples, {df.shape[1]} features.")
    print(f"Target variable for regression: '{target_col}' (Battery Maximum Temperature [K])")
    print(f"Input feature count: {len(INPUT_FEATURES)}")
    for feat in INPUT_FEATURES:
        print(f"  * {feat}")

    # Split and scale data (Train 70%, Val 15%, Test 15%)
    data_dict = split_and_scale_data(df, features=INPUT_FEATURES, target=target_col, random_state=42)
    X_train_scaled = data_dict["X_train_scaled"]
    X_test_scaled = data_dict["X_test_scaled"]
    y_train = data_dict["y_train"]
    y_test = data_dict["y_test"]
    scaler = data_dict["scaler_X"]

    # Save feature scaler
    scaler_path = os.path.join(config.MODELS_DIR, "feature_scaler.joblib")
    save_preprocessor(scaler, scaler_path)
    print(f"\n[PREPROCESSOR SAVED] Input feature scaler saved to: {scaler_path}")

    # Model initializations
    models = {
        "Random Forest": RandomForestRegressor(
            n_estimators=100, max_depth=16, random_state=42, n_jobs=-1
        ),
        "XGBoost": xgb.XGBRegressor(
            n_estimators=120, max_depth=6, learning_rate=0.08, random_state=42, n_jobs=-1
        ),
        "SVR": SVR(
            C=50.0, epsilon=0.05, kernel="rbf"
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.08, max_depth=5, random_state=42
        ),
        "Neural Network (MLP)": MLPRegressor(
            hidden_layer_sizes=(128, 64, 32),
            activation="relu",
            solver="adam",
            alpha=0.001,
            max_iter=600,
            random_state=42,
            early_stopping=True
        ),
    }

    comparison_records = []
    eval_results_list = []

    print("\n--- TRAINING & EVALUATING MODELS ---")

    for name, model in models.items():
        print(f"\nTraining [{name}]...")
        t_start = time.time()
        model.fit(X_train_scaled, y_train)
        train_time = time.time() - t_start

        # Evaluate metrics on unseen test set
        eval_res = evaluate_regression_model(
            model, X_train_scaled, y_train, X_test_scaled, y_test, model_name=name
        )
        eval_res["train_time_s"] = train_time
        eval_results_list.append(eval_res)

        print(f"  * Training Time   : {train_time:.2f} s")
        print(f"  * Inference Latency: {eval_res['Inference_Time_ms']:.2f} ms")
        print(f"  * MAE             : {eval_res['MAE']:.4f} K")
        print(f"  * RMSE            : {eval_res['RMSE']:.4f} K")
        print(f"  * R² Score        : {eval_res['R2_Score']:.5f}")
        print(f"  * MAPE (%)        : {eval_res['MAPE_percent']:.3f}%")

        comparison_records.append({
            "Model": name,
            "MAE": eval_res["MAE"],
            "MSE": eval_res["MSE"],
            "RMSE": eval_res["RMSE"],
            "R2_Score": eval_res["R2_Score"],
            "MAPE_percent": eval_res["MAPE_percent"],
            "Train_Time_s": train_time,
            "Inference_Time_ms": eval_res["Inference_Time_ms"],
        })

        if save_models:
            slug = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
            model_dir = os.path.join(config.MODELS_DIR, slug)
            os.makedirs(model_dir, exist_ok=True)
            model_file = os.path.join(model_dir, f"{slug}_model.joblib")
            joblib.dump(model, model_file)
            print(f"  [MODEL SAVED] Model checkpoint saved to: {model_file}")

    comparison_df = pd.DataFrame(comparison_records)
    comparison_df = comparison_df.sort_values(by="R2_Score", ascending=False).reset_index(drop=True)

    # Save metrics table to CSV
    metrics_csv_path = os.path.join(config.PART_B_METRICS, "model_comparison.csv")
    comparison_df.to_csv(metrics_csv_path, index=False)
    print(f"\n[FILE SAVED] Performance comparison table exported to: {metrics_csv_path}")

    # Generate Graphical Visualizations
    print("\n--- GENERATING EVALUATION VISUALIZATIONS ---")
    p21_path = os.path.join(config.PART_B_GRAPHS, "21_actual_vs_predicted.png")
    plot_actual_vs_predicted(eval_results_list, target_col, p21_path)
    print(f"[GRAPH SAVED] Plot 21 (Actual vs Predicted) saved to: {p21_path}")

    p22_path = os.path.join(config.PART_B_GRAPHS, "22_model_performance_comparison.png")
    plot_model_comparison_bar(comparison_df, p22_path)
    print(f"[GRAPH SAVED] Plot 22 (Model Comparison) saved to: {p22_path}")

    p23_path = os.path.join(config.PART_B_GRAPHS, "23_prediction_error_distribution.png")
    plot_prediction_error_distribution(eval_results_list, p23_path)
    print(f"[GRAPH SAVED] Plot 23 (Residual Error Distribution) saved to: {p23_path}")

    print("\n" + "=" * 90)
    print(" SUBPART B1 COMPLETED SUCCESSFULLY ".center(90, "="))
    print("=" * 90)
    print("\nFINAL MODEL LEADERBOARD:")
    print(comparison_df.to_string(index=False))
    return comparison_df


if __name__ == "__main__":
    train_and_evaluate_all_models()
