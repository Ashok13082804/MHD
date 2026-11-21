"""
Model Evaluation and Metrics Module for Part B
Computes MAE, MSE, RMSE, R2 score, training and inference times, and generates comparison reports.
"""

import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Tuple
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    import seaborn as sns
except ImportError:
    sns = None


def evaluate_regression_model(
    model: Any,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    model_name: str = "RegressionModel",
    is_torch: bool = False
) -> Dict[str, Any]:
    """
    Evaluates regression model performance on test dataset and measures timing.
    """
    # Prediction on test set and inference time measurement
    t_start_infer = time.time()
    if is_torch:
        import torch
        model.eval()
        with torch.no_grad():
            preds_tensor = model(torch.tensor(X_test, dtype=torch.float32))
            y_pred = preds_tensor.squeeze().cpu().numpy()
    else:
        y_pred = model.predict(X_test)
    inference_time = (time.time() - t_start_infer) * 1000.0  # in milliseconds

    # Metric computations
    mae = float(mean_absolute_error(y_test, y_pred))
    mse = float(mean_squared_error(y_test, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_test, y_pred))

    # Percentage error (MAPE)
    denom = np.maximum(np.abs(y_test), 1.0e-5)
    mape = float(np.mean(np.abs((y_test - y_pred) / denom)) * 100.0)

    return {
        "model_name": model_name,
        "MAE": mae,
        "MSE": mse,
        "RMSE": rmse,
        "R2_Score": r2,
        "MAPE_percent": mape,
        "Inference_Time_ms": inference_time,
        "y_true": y_test,
        "y_pred": y_pred,
    }


def plot_actual_vs_predicted(
    evaluation_results: List[Dict[str, Any]],
    target_name: str,
    save_path: str
):
    """
    Plot 21: Actual versus predicted ML results scatter plot with 45-degree parity line.
    """
    n_models = len(evaluation_results)
    fig, axes = plt.subplots(1, n_models, figsize=(5 * n_models, 4.5), dpi=300, sharey=True)
    if n_models == 1:
        axes = [axes]

    colors = ['#1f77b4', '#2ca02c', '#ff7f0e', '#d62728', '#9467bd']

    for idx, (res, ax) in enumerate(zip(evaluation_results, axes)):
        y_true = res["y_true"]
        y_pred = res["y_pred"]
        name = res["model_name"]
        r2 = res["R2_Score"]
        rmse = res["RMSE"]

        ax.scatter(y_true, y_pred, color=colors[idx % len(colors)], alpha=0.55, edgecolors='none', s=25)
        min_val = min(np.min(y_true), np.min(y_pred))
        max_val = max(np.max(y_true), np.max(y_pred))
        ax.plot([min_val, max_val], [min_val, max_val], 'k--', lw=1.8, label="Parity (y = x)")

        ax.set_xlabel(f"Actual {target_name}", fontsize=11, fontweight='bold')
        if idx == 0:
            ax.set_ylabel(f"Predicted {target_name}", fontsize=11, fontweight='bold')
        ax.set_title(f"{name}\n$R^2 = {r2:.4f}$ | RMSE = {rmse:.3f}", fontsize=11, fontweight='bold')
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(loc="upper left")

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_model_comparison_bar(
    comparison_df: pd.DataFrame,
    save_path: str
):
    """
    Plot 22: ML model performance comparison bar chart (R2 and RMSE).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), dpi=300)
    models = comparison_df["Model"]
    x_pos = np.arange(len(models))

    # R2 Score Bar Chart
    bars1 = ax1.bar(x_pos, comparison_df["R2_Score"], color="#2b5c8f", width=0.5, edgecolor='black')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(models, rotation=25, ha='right', fontweight='bold')
    ax1.set_ylabel("R² Score (Higher is Better)", fontsize=11, fontweight='bold')
    ax1.set_title("Regression Accuracy ($R^2$ Score)", fontsize=12, fontweight='bold')
    ax1.set_ylim([max(0.0, comparison_df["R2_Score"].min() - 0.05), 1.02])
    ax1.grid(axis='y', linestyle=':', alpha=0.6)
    for bar in bars1:
        h = bar.get_height()
        ax1.annotate(f"{h:.4f}", xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

    # RMSE Bar Chart
    bars2 = ax2.bar(x_pos, comparison_df["RMSE"], color="#e06666", width=0.5, edgecolor='black')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(models, rotation=25, ha='right', fontweight='bold')
    ax2.set_ylabel("RMSE (Lower is Better)", fontsize=11, fontweight='bold')
    ax2.set_title("Root Mean Squared Error (RMSE)", fontsize=12, fontweight='bold')
    ax2.grid(axis='y', linestyle=':', alpha=0.6)
    for bar in bars2:
        h = bar.get_height()
        ax2.annotate(f"{h:.3f}", xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_prediction_error_distribution(
    evaluation_results: List[Dict[str, Any]],
    save_path: str
):
    """
    Plot 23: ML prediction error distribution (Residual Histogram / KDE).
    """
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    colors = ['#1f77b4', '#2ca02c', '#ff7f0e', '#d62728', '#9467bd']

    for idx, res in enumerate(evaluation_results):
        error = res["y_pred"] - res["y_true"]
        name = res["model_name"]
        ax.hist(error, bins=30, alpha=0.45, label=f"{name} (Mean: {np.mean(error):.2e})", color=colors[idx % len(colors)])

    ax.axvline(0.0, color='black', linestyle='--', lw=1.5, label="Zero Error")
    ax.set_xlabel("Prediction Residual Error ($y_{pred} - y_{true}$)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Frequency Count", fontsize=11, fontweight='bold')
    ax.set_title("Prediction Error Distributions Across Machine Learning Models", fontsize=12, fontweight='bold')
    ax.legend(frameon=True)
    ax.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300)
    plt.close()
