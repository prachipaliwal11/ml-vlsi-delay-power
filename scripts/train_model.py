import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import joblib
import os

from feature_utils import build_training_matrix, FEATURE_COLUMNS

df = pd.read_csv("data/dataset.csv")

os.makedirs("models", exist_ok=True)

X = build_training_matrix(df)
FEATURES = FEATURE_COLUMNS

param_dist = {
    "n_estimators": [100, 200, 300, 500],
    "max_depth": [None, 5, 10, 15, 20],
    "min_samples_leaf": [1, 2, 4, 8],
    "max_features": ["sqrt", "log2", None],
}


def train_and_evaluate(target_col, model_name):
    y = df[target_col]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    base_model = RandomForestRegressor(random_state=42)
    search = RandomizedSearchCV(
        base_model, param_dist, n_iter=20, cv=5,
        scoring="r2", random_state=42, n_jobs=-1
    )
    search.fit(X_train, y_train)
    best_model = search.best_estimator_

    y_pred = best_model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"\n=== {target_col} ===")
    print(f"Best params: {search.best_params_}")
    print(f"R²:   {r2:.4f}")
    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")

    joblib.dump(best_model, f"models/{model_name}.pkl")
    print(f"Saved models/{model_name}.pkl")

    importances = pd.Series(best_model.feature_importances_, index=FEATURES).sort_values(ascending=False)
    print("Feature importances:")
    print(importances)

    return best_model, importances


if __name__ == "__main__":
    # delay_ps / power_mW kept for backward compatibility with predict.py
    # / the Streamlit demo. tpHL_ps / tpLH_ps are the more physically
    # direct new targets -- delay_ps is just their max.
    train_and_evaluate("delay_ps", "delay_model")
    train_and_evaluate("tpHL_ps", "tpHL_model")
    train_and_evaluate("tpLH_ps", "tpLH_model")
    train_and_evaluate("power_mW", "power_model")