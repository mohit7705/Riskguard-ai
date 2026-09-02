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


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "backend" / "ml" / "models"

EVALUATION_REPORT_PATH = (
    MODEL_DIR / "model_evaluation_report.json"
)

TRAIN_PATH = DATA_DIR / "train.parquet"
VALIDATION_PATH = DATA_DIR / "validation.parquet"
TEST_PATH = DATA_DIR / "test.parquet"

MODEL_PATH = MODEL_DIR / "riskguard_random_forest.joblib"

XGB_MODEL_PATH = (
    MODEL_DIR / "riskguard_xgboost.joblib"
)

FEATURE_IMPORTANCE_PATH = (
    MODEL_DIR / "riskguard_feature_importance.parquet"
)

XGB_FEATURE_IMPORTANCE_PATH = (
    MODEL_DIR / "xgboost_feature_importance.parquet"
)

TARGET_COLUMN = "abuse_label"

RANDOM_STATE = 42


# ============================================================
# Dataset loading
# ============================================================

def load_datasets() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load train, validation and untouched test datasets."""

    required_paths = {
        "training": TRAIN_PATH,
        "validation": VALIDATION_PATH,
        "test": TEST_PATH,
    }

    for name, path in required_paths.items():
        if not path.exists():
            raise FileNotFoundError(
                f"{name.capitalize()} dataset not found: {path}"
            )

    train = pd.read_parquet(TRAIN_PATH)
    validation = pd.read_parquet(VALIDATION_PATH)
    test = pd.read_parquet(TEST_PATH)

    print(f"       Train dataset:      {train.shape}")
    print(f"       Validation dataset: {validation.shape}")
    print(f"       Test dataset:       {test.shape}")

    return train, validation, test


# ============================================================
# Dataset validation
# ============================================================

def validate_datasets(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    """Validate all datasets before model fitting."""

    datasets = {
        "train": train,
        "validation": validation,
        "test": test,
    }

    for name, dataframe in datasets.items():

        if TARGET_COLUMN not in dataframe.columns:
            raise RuntimeError(
                f"Missing target column in {name}: "
                f"{TARGET_COLUMN}"
            )

        if dataframe.isna().any().any():
            raise RuntimeError(
                f"{name.capitalize()} dataset contains NULL values."
            )

        labels = set(
            dataframe[TARGET_COLUMN].unique()
        )

        if labels != {0, 1}:
            raise RuntimeError(
                f"Unexpected {name} labels: {labels}"
            )

    train_features = [
        column
        for column in train.columns
        if column != TARGET_COLUMN
    ]

    validation_features = [
        column
        for column in validation.columns
        if column != TARGET_COLUMN
    ]

    test_features = [
        column
        for column in test.columns
        if column != TARGET_COLUMN
    ]

    if train_features != validation_features:
        raise RuntimeError(
            "Train/validation feature columns do not match."
        )

    if train_features != test_features:
        raise RuntimeError(
            "Train/test feature columns do not match."
        )

    print("       Dataset validation: PASSED")


# ============================================================
# Feature preparation
# ============================================================

def prepare_features(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.Series,
    pd.DataFrame,
    pd.Series,
    pd.DataFrame,
    pd.Series,
    list[str],
]:
    """
    Prepare model features.

    Categorical encoding is learned from TRAIN only.

    Validation and test datasets are then aligned to the
    training feature space.
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
    X_validation = validation[feature_columns].copy()
    X_test = test[feature_columns].copy()

    y_train = train[TARGET_COLUMN].astype(int)
    y_validation = validation[TARGET_COLUMN].astype(int)
    y_test = test[TARGET_COLUMN].astype(int)

    # ----------------------------------------------------------
    # Convert datetime columns
    # ----------------------------------------------------------

    for column in feature_columns:

        if pd.api.types.is_datetime64_any_dtype(
            X_train[column]
        ):

            for dataframe in (
                X_train,
                X_validation,
                X_test,
            ):
                dataframe[column] = (
                    pd.to_datetime(dataframe[column])
                    .astype("int64")
                    // 10**9
                )

    # ----------------------------------------------------------
    # Convert boolean columns
    # ----------------------------------------------------------

    for column in feature_columns:

        if pd.api.types.is_bool_dtype(
            X_train[column]
        ):

            X_train[column] = (
                X_train[column].astype(int)
            )

            X_validation[column] = (
                X_validation[column].astype(int)
            )

            X_test[column] = (
                X_test[column].astype(int)
            )

    # ----------------------------------------------------------
    # Identify categorical columns from TRAIN
    # ----------------------------------------------------------

    categorical_columns = [
        column
        for column in feature_columns
        if (
            pd.api.types.is_object_dtype(
                X_train[column]
            )
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

        # IMPORTANT:
        # Each dataset is encoded independently.
        # No test/validation categories are used to construct
        # the training feature vocabulary.

        X_train = pd.get_dummies(
            X_train,
            columns=categorical_columns,
            dtype=int,
        )

        X_validation = pd.get_dummies(
            X_validation,
            columns=categorical_columns,
            dtype=int,
        )

        X_test = pd.get_dummies(
            X_test,
            columns=categorical_columns,
            dtype=int,
        )

    # ----------------------------------------------------------
    # Align validation/test to TRAIN feature space
    # ----------------------------------------------------------

    final_feature_columns = X_train.columns.tolist()

    X_validation = X_validation.reindex(
        columns=final_feature_columns,
        fill_value=0,
    )

    X_test = X_test.reindex(
        columns=final_feature_columns,
        fill_value=0,
    )

    # ----------------------------------------------------------
    # Final numeric validation
    # ----------------------------------------------------------

    for name, dataframe in {
        "training": X_train,
        "validation": X_validation,
        "test": X_test,
    }.items():

        non_numeric = [
            column
            for column in dataframe.columns
            if not pd.api.types.is_numeric_dtype(
                dataframe[column]
            )
        ]

        if non_numeric:
            raise RuntimeError(
                f"Non-numeric {name} features found: "
                f"{non_numeric}"
            )

        if dataframe.isna().any().any():
            raise RuntimeError(
                f"NULL values found in {name} features."
            )

    if X_train.shape[1] != X_validation.shape[1]:
        raise RuntimeError(
            "Train/validation feature dimensions do not match."
        )

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

    print(
        "       Train-only feature encoding: PASSED"
    )

    return (
        X_train,
        y_train,
        X_validation,
        y_validation,
        X_test,
        y_test,
        final_feature_columns,
    )


# ============================================================
# Model training
# ============================================================

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
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
    )

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
        random_state=RANDOM_STATE,
        n_jobs=-1,
        eval_metric="logloss",
    )

    model.fit(
        X_train,
        y_train,
    )

    return model


# ============================================================
# Evaluation
# ============================================================

def evaluate_model(
    model,
    X_data: pd.DataFrame,
    y_data: pd.Series,
    model_name: str,
    threshold: float = 0.5,
) -> dict:
    """Evaluate a model at a locked probability threshold."""

    probabilities = (
        model.predict_proba(X_data)[:, 1]
    )

    predictions = (
        probabilities >= threshold
    ).astype(int)

    metrics = {
        "model": model_name,

        "threshold": round(
            threshold,
            4,
        ),

        "accuracy": round(
            accuracy_score(
                y_data,
                predictions,
            ),
            4,
        ),

        "precision": round(
            precision_score(
                y_data,
                predictions,
                zero_division=0,
            ),
            4,
        ),

        "recall": round(
            recall_score(
                y_data,
                predictions,
                zero_division=0,
            ),
            4,
        ),

        "f1_score": round(
            f1_score(
                y_data,
                predictions,
                zero_division=0,
            ),
            4,
        ),

        "roc_auc": round(
            roc_auc_score(
                y_data,
                probabilities,
            ),
            4,
        ),

        "pr_auc": round(
            average_precision_score(
                y_data,
                probabilities,
            ),
            4,
        ),

        "confusion_matrix": (
            confusion_matrix(
                y_data,
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
            y_data,
            predictions,
            target_names=[
                "LEGITIMATE",
                "ABUSIVE",
            ],
            digits=4,
            zero_division=0,
        )
    )

    return metrics


# ============================================================
# Model saving
# ============================================================

def save_model(
    model: RandomForestClassifier,
    feature_columns: list[str],
) -> None:
    """Save Random Forest model and metadata."""

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
            "random_state": RANDOM_STATE,
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
    """Save XGBoost model and metadata."""

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
            "random_state": RANDOM_STATE,
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
        XGB_FEATURE_IMPORTANCE_PATH,
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


# ============================================================
# Evaluation report
# ============================================================

def save_evaluation_report(
    rf_metrics: dict,
    xgb_metrics: dict,
) -> None:
    """Save final model comparison metrics."""

    report = {
        "evaluation_protocol": {
            "train_rows": 6400,
            "validation_rows": 1600,
            "test_rows": 2000,
            "test_usage": (
                "Final evaluation only. "
                "Not used for threshold selection."
            ),
        },
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


# ============================================================
# Main
# ============================================================

def main() -> None:

    print("=" * 60)
    print("RiskGuard AI — ML Training")
    print("=" * 60)

    print()
    print("[1/6] Loading datasets...")

    train, validation, test = load_datasets()

    print()
    print("[2/6] Validating datasets...")

    validate_datasets(
        train,
        validation,
        test,
    )

    print()
    print("[3/6] Preparing model features...")

    (
        X_train,
        y_train,
        X_validation,
        y_validation,
        X_test,
        y_test,
        feature_columns,
    ) = prepare_features(
        train,
        validation,
        test,
    )

    # --------------------------------------------------------
    # Random Forest
    # --------------------------------------------------------

    print()
    print("[4/6] Training Random Forest...")

    rf_model = train_model(
        X_train,
        y_train,
    )

    print(
        "       Random Forest Training: PASSED"
    )

    print()
    print("Random Forest Validation Evaluation")
    print("-" * 60)

    rf_validation_metrics = evaluate_model(
        rf_model,
        X_validation,
        y_validation,
        "Random Forest Validation",
        threshold=0.5,
    )

    save_model(
        rf_model,
        feature_columns,
    )

    # --------------------------------------------------------
    # XGBoost
    # --------------------------------------------------------

    print()
    print("[5/6] Training XGBoost...")

    xgb_model = train_xgboost(
        X_train,
        y_train,
    )

    print(
        "       XGBoost Training: PASSED"
    )

    print()
    print("XGBoost Validation Evaluation")
    print("-" * 60)

    xgb_validation_metrics = evaluate_model(
        xgb_model,
        X_validation,
        y_validation,
        "XGBoost Validation",
        threshold=0.5,
    )

    save_xgboost_model(
        xgb_model,
        feature_columns,
    )

    # --------------------------------------------------------
    # Test evaluation
    # --------------------------------------------------------

    print()
    print("[6/6] Final test evaluation...")

    print(
        "\nRandom Forest FINAL TEST Evaluation"
    )
    print("-" * 60)

    rf_test_metrics = evaluate_model(
        rf_model,
        X_test,
        y_test,
        "Random Forest",
        threshold=0.5,
    )

    print(
        "\nXGBoost FINAL TEST Evaluation"
    )
    print("-" * 60)

    xgb_test_metrics = evaluate_model(
        xgb_model,
        X_test,
        y_test,
        "XGBoost",
        threshold=0.5,
    )

    save_evaluation_report(
        rf_test_metrics,
        xgb_test_metrics,
    )

    print()
    print("=" * 60)
    print("ML TRAINING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
