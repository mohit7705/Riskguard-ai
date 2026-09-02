from __future__ import annotations

from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "backend" / "ml" / "models"

TEST_PATH = DATA_DIR / "test.parquet"
MODEL_PATH = MODEL_DIR / "riskguard_xgboost.joblib"
THRESHOLD_REPORT_PATH = MODEL_DIR / "risk_threshold_report.json"
OUTPUT_PATH = MODEL_DIR / "final_test_evaluation.json"

TARGET_COLUMN = "abuse_label"

FP_COST = 1.0
FN_COST = 5.0


def prepare_test_features(
    test: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare test data using the feature space stored in the model."""

    excluded_columns = {
        TARGET_COLUMN,
        "user_id",
        "return_id",
        "order_id",
    }

    raw_features = [
        column
        for column in test.columns
        if column not in excluded_columns
    ]

    X_test = test[raw_features].copy()
    y_test = test[TARGET_COLUMN].astype(int)

    # ----------------------------------------------------------
    # Datetime conversion
    # ----------------------------------------------------------

    for column in raw_features:
        if pd.api.types.is_datetime64_any_dtype(
            X_test[column]
        ):
            X_test[column] = (
                pd.to_datetime(X_test[column])
                .astype("int64")
                // 10**9
            )

    # ----------------------------------------------------------
    # Boolean conversion
    # ----------------------------------------------------------

    for column in raw_features:
        if pd.api.types.is_bool_dtype(
            X_test[column]
        ):
            X_test[column] = X_test[column].astype(int)

    # ----------------------------------------------------------
    # Categorical encoding
    #
    # The model's feature_columns define the final vocabulary.
    # No training/test vocabulary is constructed here.
    # ----------------------------------------------------------

    categorical_columns = [
        column
        for column in raw_features
        if (
            pd.api.types.is_object_dtype(X_test[column])
            or isinstance(
                X_test[column].dtype,
                pd.CategoricalDtype,
            )
        )
    ]

    if categorical_columns:
        X_test = pd.get_dummies(
            X_test,
            columns=categorical_columns,
            dtype=int,
        )

    # ----------------------------------------------------------
    # Align exactly to trained model feature space
    # ----------------------------------------------------------

    X_test = X_test.reindex(
        columns=feature_columns,
        fill_value=0,
    )

    # ----------------------------------------------------------
    # Numeric validation
    # ----------------------------------------------------------

    non_numeric = [
        column
        for column in X_test.columns
        if not pd.api.types.is_numeric_dtype(
            X_test[column]
        )
    ]

    if non_numeric:
        raise RuntimeError(
            f"Non-numeric test features found: {non_numeric}"
        )

    if X_test.isna().any().any():
        raise RuntimeError(
            "NULL values found in test features."
        )

    return X_test, y_test


def main() -> None:

    print("=" * 60)
    print("RiskGuard AI — Final Test Evaluation")
    print("=" * 60)

    # ----------------------------------------------------------
    # Load threshold selected ONLY from validation
    # ----------------------------------------------------------

    if not THRESHOLD_REPORT_PATH.exists():
        raise FileNotFoundError(
            f"Threshold report not found: "
            f"{THRESHOLD_REPORT_PATH}"
        )

    threshold_report = json.loads(
        THRESHOLD_REPORT_PATH.read_text()
    )

    threshold = float(
        threshold_report["selected_threshold"]
    )

    print()
    print(f"Locked threshold from validation: {threshold:.2f}")
    print(
        "Threshold selection source: VALIDATION SET ONLY"
    )

    # ----------------------------------------------------------
    # Load model
    # ----------------------------------------------------------

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"XGBoost model not found: {MODEL_PATH}"
        )

    bundle = joblib.load(MODEL_PATH)

    if not isinstance(bundle, dict):
        raise RuntimeError(
            "Invalid XGBoost model bundle."
        )

    required_keys = {
        "model",
        "feature_columns",
        "target_column",
        "model_type",
    }

    missing = required_keys.difference(bundle.keys())

    if missing:
        raise RuntimeError(
            f"Model bundle missing keys: {sorted(missing)}"
        )

    model = bundle["model"]
    feature_columns = bundle["feature_columns"]

    if bundle["target_column"] != TARGET_COLUMN:
        raise RuntimeError(
            "Model target column does not match expected target."
        )

    print(f"Model type: {bundle['model_type']}")
    print(f"Model features: {len(feature_columns)}")

    # ----------------------------------------------------------
    # Load untouched test set
    # ----------------------------------------------------------

    if not TEST_PATH.exists():
        raise FileNotFoundError(
            f"Test dataset not found: {TEST_PATH}"
        )

    test = pd.read_parquet(TEST_PATH)

    print(f"Test rows: {len(test):,}")

    X_test, y_test = prepare_test_features(
        test,
        feature_columns,
    )

    # ----------------------------------------------------------
    # Probability prediction
    # ----------------------------------------------------------

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    predictions = (
        probabilities >= threshold
    ).astype(int)

    # ----------------------------------------------------------
    # Metrics
    # ----------------------------------------------------------

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0,
    )

    roc_auc = roc_auc_score(
        y_test,
        probabilities,
    )

    pr_auc = average_precision_score(
        y_test,
        probabilities,
    )

    tn, fp, fn, tp = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1],
    ).ravel()

    business_cost = (
        fp * FP_COST
        + fn * FN_COST
    )

    print()
    print("FINAL TEST PERFORMANCE")
    print("-" * 60)
    print(f"Threshold:          {threshold:.2f}")
    print(f"Accuracy:           {accuracy:.4f}")
    print(f"Precision:          {precision:.4f}")
    print(f"Recall:             {recall:.4f}")
    print(f"F1:                 {f1:.4f}")
    print(f"ROC-AUC:            {roc_auc:.4f}")
    print(f"PR-AUC:             {pr_auc:.4f}")
    print(f"True negatives:     {tn}")
    print(f"False positives:    {fp}")
    print(f"False negatives:    {fn}")
    print(f"True positives:     {tp}")
    print(f"Business cost:      {business_cost:.2f}")

    print()
    print("CLASSIFICATION REPORT")
    print("-" * 60)
    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "LEGITIMATE",
                "ABUSIVE",
            ],
            digits=4,
            zero_division=0,
        )
    )

    # ----------------------------------------------------------
    # Save final evaluation artifact
    # ----------------------------------------------------------

    report = {
        "model": "XGBoost",
        "threshold": threshold,
        "threshold_source": "validation",
        "test_rows": int(len(test)),
        "metrics": {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc),
            "pr_auc": float(pr_auc),
        },
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "business_cost": {
            "false_positive_cost": FP_COST,
            "false_negative_cost": FN_COST,
            "total_cost": float(business_cost),
        },
        "evaluation_protocol": (
            "Threshold selected on validation set and "
            "then evaluated once on untouched test set."
        ),
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
        )
    )

    print()
    print("FINAL TEST REPORT SAVED")
    print("-" * 60)
    print(OUTPUT_PATH)

    print()
    print("=" * 60)
    print("FINAL TEST EVALUATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()