from __future__ import annotations

from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "backend" / "ml" / "models"
EVALUATION_REPORT_PATH = (
    MODEL_DIR / "model_evaluation_report.json"
)

TRAIN_PATH = DATA_DIR / "train.parquet"
TEST_PATH = DATA_DIR / "test.parquet"

MODEL_PATH = MODEL_DIR / "riskguard_random_forest.joblib"
XGB_MODEL_PATH = (
    MODEL_DIR / "riskguard_xgboost.joblib"
)
FEATURE_IMPORTANCE_PATH = (
    MODEL_DIR / "riskguard_feature_importance.parquet"
)


TARGET_COLUMN = "abuse_label"


def load_datasets() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the prepared train and test datasets."""

    if not TRAIN_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {TRAIN_PATH}"
        )

    if not TEST_PATH.exists():
        raise FileNotFoundError(
            f"Test dataset not found: {TEST_PATH}"
        )

    train = pd.read_parquet(TRAIN_PATH)
    test = pd.read_parquet(TEST_PATH)

    print(f"       Train dataset: {train.shape}")
    print(f"       Test dataset:  {test.shape}")

    return train, test


def validate_datasets(
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    """Validate the training inputs before model fitting."""

    if TARGET_COLUMN not in train.columns:
        raise RuntimeError(
            f"Missing target column in train dataset: "
            f"{TARGET_COLUMN}"
        )

    if TARGET_COLUMN not in test.columns:
        raise RuntimeError(
            f"Missing target column in test dataset: "
            f"{TARGET_COLUMN}"
        )

    if train.isna().any().any():
        raise RuntimeError(
            "Training dataset contains NULL values."
        )

    if test.isna().any().any():
        raise RuntimeError(
            "Test dataset contains NULL values."
        )

    train_features = [
        column
        for column in train.columns
        if column != TARGET_COLUMN
    ]

    test_features = [
        column
        for column in test.columns
        if column != TARGET_COLUMN
    ]

    if train_features != test_features:
        raise RuntimeError(
            "Train/test feature columns do not match."
        )

    train_labels = set(train[TARGET_COLUMN].unique())
    test_labels = set(test[TARGET_COLUMN].unique())

    if train_labels != {0, 1}:
        raise RuntimeError(
            f"Unexpected train labels: {train_labels}"
        )

    if test_labels != {0, 1}:
        raise RuntimeError(
            f"Unexpected test labels: {test_labels}"
        )

    print("       Dataset validation: PASSED")


def prepare_features(
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.Series,
    pd.DataFrame,
    pd.Series,
    list[str],
]:
    """
    Prepare model-ready features.

    Numeric features are kept as-is.
    Boolean features are converted to integers.
    Categorical features are one-hot encoded using the
    combined train/test feature space.
    Identifier columns are excluded.
    """

    excluded_columns = {
        TARGET_COLUMN,
        "user_id",
        "return_id",
        "order_id",
    }

    feature_columns = [
        column
        for column in train.columns
        if column not in excluded_columns
    ]

    X_train = train[feature_columns].copy()
    X_test = test[feature_columns].copy()

    y_train = train[TARGET_COLUMN].astype(int)
    y_test = test[TARGET_COLUMN].astype(int)

    # ----------------------------------------------------------
    # Convert datetime columns
    # ----------------------------------------------------------

    for column in feature_columns:
        if pd.api.types.is_datetime64_any_dtype(
            X_train[column]
        ):
            X_train[column] = (
                pd.to_datetime(X_train[column])
                .astype("int64")
                // 10**9
            )

            X_test[column] = (
                pd.to_datetime(X_test[column])
                .astype("int64")
                // 10**9
            )

    # ----------------------------------------------------------
    # Convert boolean columns
    # ----------------------------------------------------------

    for column in feature_columns:
        if pd.api.types.is_bool_dtype(X_train[column]):
            X_train[column] = X_train[column].astype(int)
            X_test[column] = X_test[column].astype(int)

    # ----------------------------------------------------------
    # Identify categorical columns
    # ----------------------------------------------------------

    categorical_columns = [
        column
        for column in feature_columns
        if (
            pd.api.types.is_object_dtype(X_train[column])
            or pd.api.types.is_categorical_dtype(
                X_train[column]
            )
        )
    ]

    if categorical_columns:
        print(
            "       Categorical features:",
            categorical_columns,
        )

        # Combine train and test ONLY for consistent
        # one-hot column creation.
        combined = pd.concat(
            [
                X_train,
                X_test,
            ],
            axis=0,
            ignore_index=True,
        )

        train_length = len(X_train)

        combined = pd.get_dummies(
            combined,
            columns=categorical_columns,
            dtype=int,
        )

        X_train = combined.iloc[
            :train_length
        ].copy()

        X_test = combined.iloc[
            train_length:
        ].copy()

    # ----------------------------------------------------------
    # Final numeric validation
    # ----------------------------------------------------------

    non_numeric = [
        column
        for column in X_train.columns
        if not pd.api.types.is_numeric_dtype(
            X_train[column]
        )
    ]

    if non_numeric:
        raise RuntimeError(
            "Non-numeric model features found: "
            f"{non_numeric}"
        )

    if X_train.isna().any().any():
        raise RuntimeError(
            "NULL values found in training features."
        )

    if X_test.isna().any().any():
        raise RuntimeError(
            "NULL values found in test features."
        )

    final_feature_columns = X_train.columns.tolist()

    if X_train.shape[1] != X_test.shape[1]:
        raise RuntimeError(
            "Train/test feature dimensions do not match."
        )

    print(
        f"       Original features: "
        f"{len(feature_columns)}"
    )

    print(
        f"       Encoded model features: "
        f"{len(final_feature_columns)}"
    )

    print("       Feature preparation: PASSED")

    return (
        X_train,
        y_train,
        X_test,
        y_test,
        final_feature_columns,
    )


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> RandomForestClassifier:
    """Train the baseline RiskGuard Random Forest."""

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    return model


def train_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> XGBClassifier:
    """Train the XGBoost RiskGuard model."""

    model = XGBClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=4,
        random_state=42,
        n_jobs=-1,
        eval_metric="logloss",
    )

    model.fit(
        X_train,
        y_train,
    )

    return model


def evaluate_model(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model_name: str,
) -> dict:
    """Evaluate model performance."""

    predictions = model.predict(X_test)
    probabilities = (
        model.predict_proba(X_test)[:, 1]
    )

    metrics = {
        "model": model_name,

        "accuracy": round(
            accuracy_score(
                y_test,
                predictions,
            ),
            4,
        ),

        "precision": round(
            precision_score(
                y_test,
                predictions,
            ),
            4,
        ),

        "recall": round(
            recall_score(
                y_test,
                predictions,
            ),
            4,
        ),

        "f1_score": round(
            f1_score(
                y_test,
                predictions,
            ),
            4,
        ),

        "roc_auc": round(
            roc_auc_score(
                y_test,
                probabilities,
            ),
            4,
        ),

        "pr_auc": round(
            average_precision_score(
                y_test,
                probabilities,
            ),
            4,
        ),

        "confusion_matrix": (
            confusion_matrix(
                y_test,
                predictions,
            )
            .tolist()
        ),
    }

    print()
    print(f"{model_name} PERFORMANCE")
    print("-" * 60)

    for key, value in metrics.items():
        print(
            f"{key}: {value}"
        )

    print()

    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "LEGITIMATE",
                "ABUSIVE",
            ],
            digits=4,
        )
    )

    return metrics


def save_model(
    model: RandomForestClassifier,
    feature_columns: list[str],
) -> None:
    """Save model and feature metadata."""

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        {
            "model": model,
            "feature_columns": feature_columns,
            "target_column": TARGET_COLUMN,
            "model_type": "RandomForestClassifier",
            "random_state": 42,
        },
        MODEL_PATH,
    )

    importance = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance": model.feature_importances_,
        }
    ).sort_values(
        "importance",
        ascending=False,
    )

    importance.to_parquet(
        FEATURE_IMPORTANCE_PATH,
        index=False,
    )

    print()
    print("MODEL SAVED")
    print("-" * 60)
    print(f"Model: {MODEL_PATH}")
    print(
        f"Feature importance: "
        f"{FEATURE_IMPORTANCE_PATH}"
    )

    print()
    print("TOP 10 FEATURES:")
    print(
        importance.head(10).to_string(
            index=False
        )
    )


def save_xgboost_model(
    model: XGBClassifier,
    feature_columns: list[str],
) -> None:
    """Save XGBoost model and feature metadata."""

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        {
            "model": model,
            "feature_columns": feature_columns,
            "target_column": TARGET_COLUMN,
            "model_type": "XGBClassifier",
            "random_state": 42,
        },
        XGB_MODEL_PATH,
    )

    importance = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance": model.feature_importances_,
        }
    ).sort_values(
        "importance",
        ascending=False,
    )

    importance.to_parquet(
        MODEL_DIR / "xgboost_feature_importance.parquet",
        index=False,
    )

    print()
    print("XGBOOST MODEL SAVED")
    print("-" * 60)
    print(f"Model: {XGB_MODEL_PATH}")

    print()
    print("TOP 10 XGBOOST FEATURES:")

    print(
        importance.head(10).to_string(
            index=False
        )
    )


def save_evaluation_report(
    rf_metrics: dict,
    xgb_metrics: dict,
) -> None:
    """Save model comparison metrics."""

    report = {
        "random_forest": rf_metrics,
        "xgboost": xgb_metrics,
    }

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        EVALUATION_REPORT_PATH,
        "w",
    ) as file:
        json.dump(
            report,
            file,
            indent=4,
        )

    print()
    print("EVALUATION REPORT SAVED")
    print("-" * 60)
    print(EVALUATION_REPORT_PATH)


def main() -> None:
    print("=" * 60)
    print("RiskGuard AI — Baseline Model Training")
    print("=" * 60)

    print()
    print("[1/5] Loading training datasets...")

    train, test = load_datasets()

    print()
    print("[2/5] Validating datasets...")

    validate_datasets(
        train,
        test,
    )

    print()
    print("[3/5] Preparing model features...")

    (
        X_train,
        y_train,
        X_test,
        y_test,
        feature_columns,
    ) = prepare_features(
        train,
        test,
    )

    print()
    print("[4/6] Training Random Forest...")

    rf_model = train_model(
        X_train,
        y_train,
    )

    print("       Random Forest Training: PASSED")

    print()
    print("Random Forest Evaluation")
    print("-" * 60)

    rf_metrics = evaluate_model(
        rf_model,
        X_test,
        y_test,
        "Random Forest",
    )

    save_model(
        rf_model,
        feature_columns,
    )

    print()
    print("[5/6] Training XGBoost...")

    xgb_model = train_xgboost(
        X_train,
        y_train,
    )

    print("       XGBoost Training: PASSED")

    print()
    print("XGBoost Evaluation")
    print("-" * 60)

    xgb_metrics = evaluate_model(
        xgb_model,
        X_test,
        y_test,
        "XGBoost",
    )

    save_xgboost_model(
        xgb_model,
        feature_columns,
    )

    save_evaluation_report(
        rf_metrics,
        xgb_metrics,
    )

    print()
    print("[6/6] MODEL TRAINING COMPLETE")


if __name__ == "__main__":
    main()
