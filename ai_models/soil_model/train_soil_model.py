"""
CropPulse – Tabular Soil Moisture ML Training & Benchmarking Pipeline
Benchmarks Linear Regression, Random Forest, and XGBoost Regressor.
Selects the best model based on validation metrics (MAE, RMSE, R²) and exports to .pkl.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

DATASET_PATH = "datasets/soil/soil_moisture_data.csv"
OUTPUT_DIR = "ai_models/saved_models"
MODEL_SAVE_PATH = os.path.join(OUTPUT_DIR, "soil_model.pkl")
RANDOM_SEED = 42

SOIL_TYPE_MAP = {"sandy": 0, "loamy": 1, "clay": 2, "silt": 3, "peaty": 4}


def load_dataset(csv_path: str):
    """Load, encode, and split dataset."""
    df = pd.read_csv(csv_path)

    # Encode soil type into categorical index
    df["soil_type_idx"] = df["soil_type"].str.lower().str.strip().map(SOIL_TYPE_MAP).fillna(1)

    # Features: [temperature, humidity, rainfall, wind_speed, soil_type_idx, previous_moisture]
    feature_cols = ["temperature", "humidity", "rainfall", "wind_speed", "soil_type_idx", "previous_moisture"]
    target_col = "soil_moisture"

    X = df[feature_cols].copy()
    # Normalize features according to preprocessing pipeline
    X["temperature"] = X["temperature"] / 50.0
    X["humidity"] = X["humidity"] / 100.0
    X["rainfall"] = X["rainfall"].clip(upper=200.0) / 200.0
    X["wind_speed"] = X["wind_speed"].clip(upper=100.0) / 100.0
    X["soil_type_idx"] = X["soil_type_idx"] / 4.0
    X["previous_moisture"] = X["previous_moisture"] / 100.0

    X_vals = X.values.astype(np.float32)
    y_vals = df[target_col].values.astype(np.float32)

    X_train, X_temp, y_train, y_temp = train_test_split(
        X_vals, y_vals, test_size=0.2, random_state=RANDOM_SEED
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=RANDOM_SEED
    )

    print(f"[Dataset] Train={len(X_train)} | Val={len(X_val)} | Test={len(X_test)}")
    return X_train, X_val, X_test, y_train, y_val, y_test


def benchmark_models(X_train, X_val, y_train, y_val):
    """Train and evaluate candidate regression models."""
    candidates = {
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(alpha=1.0),
        "Random Forest": RandomForestRegressor(n_estimators=150, max_depth=8, random_state=RANDOM_SEED),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=150, learning_rate=0.08, max_depth=4, random_state=RANDOM_SEED),
    }

    if XGB_AVAILABLE:
        candidates["XGBoost"] = xgb.XGBRegressor(
            n_estimators=150, learning_rate=0.08, max_depth=4, random_state=RANDOM_SEED
        )

    results = {}
    best_name = None
    best_score = float("inf")  # Lower MAE is better
    best_model = None

    print("\n[Benchmarking Machine Learning Models]")
    print("=" * 65)
    print(f"{'Model':<22} | {'MAE':<10} | {'RMSE':<10} | {'R2':<10}")
    print("-" * 65)

    for name, model in candidates.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_val)

        mae = mean_absolute_error(y_val, preds)
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        r2 = r2_score(y_val, preds)

        results[name] = {"mae": mae, "rmse": rmse, "r2": r2, "model": model}
        print(f"{name:<22} | {mae:<10.3f} | {rmse:<10.3f} | {r2:<10.3f}")

        if mae < best_score:
            best_score = mae
            best_name = name
            best_model = model

    print("=" * 65)
    print(f"[Best Model] Selected: {best_name} (MAE: {best_score:.3f})\n")
    return best_name, best_model, results


def evaluate_and_save(best_name, best_model, X_test, y_test):
    """Evaluate winning model on holdout test set and export checkpoint."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    test_preds = best_model.predict(X_test)

    mae = mean_absolute_error(y_test, test_preds)
    rmse = np.sqrt(mean_squared_error(y_test, test_preds))
    r2 = r2_score(y_test, test_preds)

    print(f"[Test Evaluation] {best_name}:")
    print(f"   MAE:  {mae:.3f}%")
    print(f"   RMSE: {rmse:.3f}%")
    print(f"   R2:   {r2:.3f}")

    joblib.dump(best_model, MODEL_SAVE_PATH)
    print(f"[Saved] Model serialized to: {MODEL_SAVE_PATH}")

    # Plot Scatter Plot
    plt.figure(figsize=(6, 6))
    plt.scatter(y_test, test_preds, alpha=0.5, s=20, color="#198754", label="Predictions")
    min_val, max_val = min(y_test.min(), test_preds.min()), max(y_test.max(), test_preds.max())
    plt.plot([min_val, max_val], [min_val, max_val], "r--", label="Ideal")
    plt.xlabel("Actual Moisture (%)")
    plt.ylabel("Predicted Moisture (%)")
    plt.title(f"Soil Moisture: {best_name} Test Results")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plot_path = os.path.join(OUTPUT_DIR, "soil_predictions_scatter.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"[Plot] Evaluation scatter plot saved to: {plot_path}")


def main():
    if not os.path.exists(DATASET_PATH):
        print(f"[Error] Dataset not found at: {DATASET_PATH}")
        return

    X_train, X_val, X_test, y_train, y_val, y_test = load_dataset(DATASET_PATH)
    best_name, best_model, _ = benchmark_models(X_train, X_val, y_train, y_val)
    evaluate_and_save(best_name, best_model, X_test, y_test)


if __name__ == "__main__":
    main()
