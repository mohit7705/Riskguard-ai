from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    roc_auc_score,
    average_precision_score,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "backend" / "ml" / "models"

TRAIN_PATH = DATA_DIR / "train.parquet"
XGB_MODEL_PATH = MODEL_DIR / "riskguard_xgboost.joblib"
CALIBRATED_MODEL_PATH = (
    MODEL_DIR / "riskguard_xgboost_calibrated.joblib"
)

TARGET_COLUMN = "abuse_label"

RANDOM_STATE = 42
CALIBRATION_METHOD = "sigmoid"
CALIBRATION_CV = 5


def prepare_features(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    """Prepare features exactly as the training pipeline does."""

    excluded_columns = {
        TARGET_COLUMN,
        "user_id",
        "return_id",
        "order_id",
    }

    available_features = [
        column
        for column in dataframe.columns
        if column not in excluded_columns
    ]

    frame = dataframe[available_features].copy()

    for column in available_features:

        if pd.api.types.is_datetime64_any_dtype(
            frame[column]
        ):
            frame[column] = (
                pd.to_datetime(frame[column])
                .astype("int64")
                // 10**9
            )

        if pd.api.types.is_bool_dtype(
            frame[column]
        ):
            frame[column] = frame[column].astype(int)

    categorical_columns = [
        column
        for column in available_features
        if (
            pd.api.types.is_object_dtype(frame[column])
            or isinstance(
                frame[column].dtype,
                pd.CategoricalDtype,
            )
        )
    ]

    if categorical_columns:
        frame = pd.get_dummies(
            frame,
            columns=categorical_columns,
            dtype=int,
        )

    frame = frame.reindex(
        columns=feature_columns,
        fill_value=0,
    )

    if frame.isna().any().any():
        raise RuntimeError(
            "Calibration features contain NULL values."
        )

    non_numeric = [
        column
        for column in frame.columns
        if not pd.api.types.is_numeric_dtype(
            frame[column]
        )
    ]

    if non_numeric:
        raise RuntimeError(
            f"Non-numeric calibration features: {non_numeric}"
        )

    return frame


def main() -> None:

    print("=" * 60)
    print("RiskGuard AI — XGBoost Probability Calibration")
    print("=" * 60)

    if not TRAIN_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {TRAIN_PATH}"
        )

    if not XGB_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"XGBoost model not found: {XGB_MODEL_PATH}"
        )

    print("\n[1/5] Loading XGBoost model...")

    bundle = joblib.load(XGB_MODEL_PATH)

    if not isinstance(bundle, dict):
        raise RuntimeError(
            "Invalid XGBoost model bundle."
        )

    required_keys = {
        "model",
        "feature_columns",
        "target_column",
    }

    missing = required_keys.difference(bundle.keys())

    if missing:
        raise RuntimeError(
            f"XGBoost bundle missing keys: {sorted(missing)}"
        )

    base_model = bundle["model"]
    feature_columns = bundle["feature_columns"]

    print(
        f"       Base model: {bundle.get('model_type', 'XGBoost')}"
    )

    print(
        f"       Features: {len(feature_columns)}"
    )

    print("\n[2/5] Loading training data...")

    train = pd.read_parquet(TRAIN_PATH)

    X_train = prepare_features(
        train,
        feature_columns,
    )

    y_train = train[TARGET_COLUMN].astype(int)

    print(
        f"       Training rows: {len(X_train)}"
    )

    print(
        f"       Positive class: {int(y_train.sum())}"
    )

    print(
        f"       Negative class: {int((y_train == 0).sum())}"
    )

    print("\n[3/5] Fitting probability calibrator...")

    calibrated_model = CalibratedClassifierCV(
        estimator=base_model,
        method=CALIBRATION_METHOD,
        cv=CALIBRATION_CV,
        n_jobs=-1,
    )

    calibrated_model.fit(
        X_train,
        y_train,
    )

    print("       Calibration: PASSED")
    print(
        f"       Method: {CALIBRATION_METHOD}"
    )
    print(
        f"       Cross-validation folds: {CALIBRATION_CV}"
    )

    print("\n[4/5] Checking calibrated training probabilities...")

    probabilities = calibrated_model.predict_proba(
        X_train
    )[:, 1]

    print(
        f"       Brier score: "
        f"{brier_score_loss(y_train, probabilities):.6f}"
    )

    print(
        f"       Log loss: "
        f"{log_loss(y_train, probabilities):.6f}"
    )

    print(
        f"       ROC-AUC: "
        f"{roc_auc_score(y_train, probabilities):.6f}"
    )

    print(
        f"       PR-AUC: "
        f"{average_precision_score(y_train, probabilities):.6f}"
    )

    print("\n[5/5] Saving calibrated model...")

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        {
            "model": calibrated_model,
            "feature_columns": feature_columns,
            "target_column": TARGET_COLUMN,
            "model_type": "CalibratedXGBClassifier",
            "base_model_type": "XGBClassifier",
            "calibration_method": CALIBRATION_METHOD,
            "calibration_cv": CALIBRATION_CV,
            "random_state": RANDOM_STATE,
        },
        CALIBRATED_MODEL_PATH,
    )

    print()
    print("CALIBRATED MODEL SAVED")
    print("-" * 60)
    print(CALIBRATED_MODEL_PATH)

    print()
    print("=" * 60)
    print("STEP 6A: CALIBRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
