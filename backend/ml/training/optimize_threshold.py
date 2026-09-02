from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "backend" / "ml" / "models"

VALIDATION_PATH = DATA_DIR / "validation.parquet"
MODEL_PATH = MODEL_DIR / "riskguard_xgboost.joblib"

REPORT_PATH = MODEL_DIR / "risk_threshold_report.json"


TARGET_COLUMN = "abuse_label"


# ============================================================
# Business costs
# ============================================================

FALSE_POSITIVE_COST = 1.0
FALSE_NEGATIVE_COST = 5.0


THRESHOLDS = [
    round(value, 2)
    for value in [
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
        0.35,
        0.40,
        0.45,
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
        0.85,
        0.90,
    ]
]


# ============================================================
# Feature preparation
# ============================================================

def prepare_features(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    """
    Prepare validation data using the feature space stored
    in the trained model bundle.

    No feature vocabulary is learned from the test dataset.
    """

    features = dataframe[
        [
            column
            for column in feature_columns
            if column in dataframe.columns
        ]
    ].copy()

    # --------------------------------------------------------
    # Convert datetime columns
    # --------------------------------------------------------

    for column in features.columns:

        if pd.api.types.is_datetime64_any_dtype(
            features[column]
        ):
            features[column] = (
                pd.to_datetime(features[column])
                .astype("int64")
                // 10**9
            )

    # --------------------------------------------------------
    # Convert boolean columns
    # --------------------------------------------------------

    for column in features.columns:

        if pd.api.types.is_bool_dtype(
            features[column]
        ):
            features[column] = (
                features[column].astype(int)
            )

    # --------------------------------------------------------
    # Encode categorical columns
    # --------------------------------------------------------

    categorical_columns = [
        column
        for column in features.columns
        if (
            pd.api.types.is_object_dtype(
                features[column]
            )
            or isinstance(
                features[column].dtype,
                pd.CategoricalDtype,
            )
        )
    ]

    if categorical_columns:

        features = pd.get_dummies(
            features,
            columns=categorical_columns,
            dtype=int,
        )

    # --------------------------------------------------------
    # Align with training feature space
    # --------------------------------------------------------

    features = features.reindex(
        columns=feature_columns,
        fill_value=0,
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if features.isna().any().any():
        raise RuntimeError(
            "NULL values found in validation features."
        )

    non_numeric = [
        column
        for column in features.columns
        if not pd.api.types.is_numeric_dtype(
            features[column]
        )
    ]

    if non_numeric:
        raise RuntimeError(
            "Non-numeric validation features found: "
            f"{non_numeric}"
        )

    return features


# ============================================================
# Business cost
# ============================================================

def calculate_cost(
    false_positives: int,
    false_negatives: int,
) -> float:
    return (
        false_positives * FALSE_POSITIVE_COST
        + false_negatives * FALSE_NEGATIVE_COST
    )


# ============================================================
# Main
# ============================================================

def main() -> None:

    print("=" * 60)
    print("RiskGuard AI — XGBoost Threshold Optimization")
    print("=" * 60)

    # --------------------------------------------------------
    # Validate required artifacts
    # --------------------------------------------------------

    if not VALIDATION_PATH.exists():
        raise FileNotFoundError(
            f"Validation dataset not found: "
            f"{VALIDATION_PATH}"
        )

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"XGBoost model not found: "
            f"{MODEL_PATH}"
        )

    # --------------------------------------------------------
    # Load validation data
    # --------------------------------------------------------

    validation = pd.read_parquet(
        VALIDATION_PATH
    )

    bundle = joblib.load(
        MODEL_PATH
    )

    if not isinstance(bundle, dict):
        raise RuntimeError(
            "Invalid XGBoost model bundle."
        )

    model = bundle["model"]
    feature_columns = bundle["feature_columns"]

    if TARGET_COLUMN not in validation.columns:
        raise RuntimeError(
            f"Missing target column: "
            f"{TARGET_COLUMN}"
        )

    print()
    print(
        f"Validation rows: "
        f"{len(validation):,}"
    )

    # --------------------------------------------------------
    # Prepare validation features
    # --------------------------------------------------------

    X_validation = prepare_features(
        validation,
        feature_columns,
    )

    y_validation = (
        validation[TARGET_COLUMN]
        .astype(int)
    )

    probabilities = model.predict_proba(
        X_validation
    )[:, 1]

    # --------------------------------------------------------
    # Evaluate every threshold
    # --------------------------------------------------------

    results = []

    for threshold in THRESHOLDS:

        predictions = (
            probabilities >= threshold
        ).astype(int)

        tn, fp, fn, tp = confusion_matrix(
            y_validation,
            predictions,
            labels=[0, 1],
        ).ravel()

        precision = precision_score(
            y_validation,
            predictions,
            zero_division=0,
        )

        recall = recall_score(
            y_validation,
            predictions,
            zero_division=0,
        )

        f1 = f1_score(
            y_validation,
            predictions,
            zero_division=0,
        )

        cost = calculate_cost(
            fp,
            fn,
        )

        results.append(
            {
                "threshold": threshold,
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp),
                "true_negatives": int(tn),
                "precision": round(
                    precision,
                    4,
                ),
                "recall": round(
                    recall,
                    4,
                ),
                "f1_score": round(
                    f1,
                    4,
                ),
                "business_cost": round(
                    cost,
                    2,
                ),
            }
        )

    # --------------------------------------------------------
    # Select threshold
    # --------------------------------------------------------

    best = min(
        results,
        key=lambda item: (
            item["business_cost"],
            -item["f1_score"],
            -item["precision"],
        ),
    )

    # --------------------------------------------------------
    # Save validation threshold report
    # --------------------------------------------------------

    report = {
        "model": "XGBoost",

        "validation_rows": len(validation),

        "positive_class": "abusive",
        "negative_class": "legitimate",

        "false_positive_cost": (
            FALSE_POSITIVE_COST
        ),

        "false_negative_cost": (
            FALSE_NEGATIVE_COST
        ),

        "cost_formula": (
            "(false_positives × false_positive_cost) "
            "+ "
            "(false_negatives × false_negative_cost)"
        ),

        "selected_threshold": (
            best["threshold"]
        ),

        "selection_reason": (
            "Threshold selected on the validation set "
            "using minimum expected business cost. "
            "The test set is reserved for final evaluation."
        ),

        "selected_validation_metrics": best,

        "threshold_results": results,

        "validation_average_precision": round(
            average_precision_score(
                y_validation,
                probabilities,
            ),
            4,
        ),
    }

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
        )

    # --------------------------------------------------------
    # Console output
    # --------------------------------------------------------

    print()
    print("THRESHOLD ANALYSIS — VALIDATION SET")
    print("-" * 60)

    print(
        f"False positive cost: "
        f"{FALSE_POSITIVE_COST}"
    )

    print(
        f"False negative cost: "
        f"{FALSE_NEGATIVE_COST}"
    )

    print()

    print(
        f"Selected threshold: "
        f"{best['threshold']:.2f}"
    )

    print(
        f"Validation business cost: "
        f"{best['business_cost']:.2f}"
    )

    print(
        f"Validation precision: "
        f"{best['precision']:.4f}"
    )

    print(
        f"Validation recall: "
        f"{best['recall']:.4f}"
    )

    print(
        f"Validation F1: "
        f"{best['f1_score']:.4f}"
    )

    print()
    print("THRESHOLD COMPARISON")
    print("-" * 60)

    table = pd.DataFrame(
        results
    )

    print(
        table[
            [
                "threshold",
                "precision",
                "recall",
                "f1_score",
                "false_positives",
                "false_negatives",
                "business_cost",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print("REPORT SAVED")
    print("-" * 60)
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
