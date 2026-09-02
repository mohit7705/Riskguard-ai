from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


# ============================================================
# Paths
# ============================================================

RETURNS_PATH = Path("data/raw/returns.parquet")
FEATURES_PATH = Path("data/processed/user_features.parquet")

TRAINING_DATASET_PATH = Path(
    "data/processed/training_dataset.parquet"
)

TRAIN_PATH = Path(
    "data/processed/train.parquet"
)

VALIDATION_PATH = Path(
    "data/processed/validation.parquet"
)

TEST_PATH = Path(
    "data/processed/test.parquet"
)


# ============================================================
# Configuration
# ============================================================

RANDOM_STATE = 42
TEST_SIZE = 0.20
VALIDATION_SIZE = 0.20


# ============================================================
# Return-level ML features
# ============================================================

RETURN_FEATURE_COLUMNS = [
    "order_category",
    "order_value",
    "item_value",
    "quantity",
    "time_to_return_request_hours",
    "refund_amount",
    "return_reason",
    "returned_item_match",
    "item_condition_score",
    "package_weight_delta_pct",
    "vision_confidence_score",
]


# ============================================================
# User-level ML features
# ============================================================

USER_FEATURE_COLUMNS = [
    "account_age_days",
    "lifetime_order_count",
    "lifetime_return_count",
    "total_spent",
    "return_rate",
    "return_velocity_30d",
    "return_velocity_48h",
    "shared_device_count",
    "shared_address_count",
    "shared_payment_fingerprint_count",
    "device_return_velocity_7d",
    "address_return_velocity_7d",
    "payment_return_velocity_7d",
    "cluster_return_velocity_7d",
]


TARGET_COLUMN = "abuse_label"


# ============================================================
# Validation helpers
# ============================================================

def require_columns(
    dataframe: pd.DataFrame,
    columns: list[str],
    dataframe_name: str,
) -> None:
    missing = [
        column
        for column in columns
        if column not in dataframe.columns
    ]

    if missing:
        raise RuntimeError(
            f"{dataframe_name} is missing required columns: "
            f"{missing}"
        )


def validate_target(
    dataframe: pd.DataFrame,
) -> None:
    if TARGET_COLUMN not in dataframe.columns:
        raise RuntimeError(
            f"Target column '{TARGET_COLUMN}' is missing."
        )

    if dataframe[TARGET_COLUMN].isna().any():
        raise RuntimeError(
            "Target column contains NULL values."
        )

    unique_labels = sorted(
        dataframe[TARGET_COLUMN].unique().tolist()
    )

    if unique_labels != [0, 1]:
        raise RuntimeError(
            f"Expected binary target [0, 1], "
            f"received {unique_labels}."
        )


def validate_user_join(
    returns: pd.DataFrame,
    features: pd.DataFrame,
    merged: pd.DataFrame,
) -> None:
    expected_rows = len(returns)

    if len(merged) != expected_rows:
        raise RuntimeError(
            "Join changed the number of return records. "
            f"Expected={expected_rows}, "
            f"received={len(merged)}."
        )

    if merged["user_id"].isna().any():
        raise RuntimeError(
            "Some return records could not be matched "
            "to a user feature row."
        )

    duplicate_users = features["user_id"].duplicated().sum()

    if duplicate_users != 0:
        raise RuntimeError(
            "User feature dataset contains duplicate user IDs: "
            f"{duplicate_users}"
        )


def validate_features(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
) -> None:
    null_count = int(
        dataframe[feature_columns]
        .isna()
        .sum()
        .sum()
    )

    if null_count != 0:
        raise RuntimeError(
            f"Training features contain {null_count} NULL values."
        )


def validate_no_leakage(
    dataframe: pd.DataFrame,
) -> None:
    forbidden_columns = {
        "abuse_type",
        "return_id",
        "order_id",
        "user_id",
        "abuse_label",
    }

    feature_set = set(
        RETURN_FEATURE_COLUMNS
        + USER_FEATURE_COLUMNS
    )

    leakage = feature_set.intersection(
        forbidden_columns
    )

    if leakage:
        raise RuntimeError(
            "Potential target/data leakage detected: "
            f"{sorted(leakage)}"
        )


# ============================================================
# Main
# ============================================================

def main() -> None:

    print("=" * 60)
    print("RiskGuard AI — ML Training Dataset Builder")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Load datasets
    # --------------------------------------------------------

    print("\n[1/7] Loading datasets...")

    if not RETURNS_PATH.exists():
        raise FileNotFoundError(
            f"Missing file: {RETURNS_PATH}"
        )

    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"Missing file: {FEATURES_PATH}"
        )

    returns = pd.read_parquet(
        RETURNS_PATH
    )

    features = pd.read_parquet(
        FEATURES_PATH
    )

    print(
        f"       Returns: {returns.shape}"
    )

    print(
        f"       User features: {features.shape}"
    )

    # --------------------------------------------------------
    # 2. Validate source columns
    # --------------------------------------------------------

    print("\n[2/7] Validating source columns...")

    require_columns(
        returns,
        [
            "return_id",
            "order_id",
            "user_id",
            *RETURN_FEATURE_COLUMNS,
            TARGET_COLUMN,
            "abuse_type",
        ],
        "returns",
    )

    require_columns(
        features,
        [
            "user_id",
            *USER_FEATURE_COLUMNS,
        ],
        "features",
    )

    print("       Source columns: PASSED")

    # --------------------------------------------------------
    # 3. Join return records with user features
    # --------------------------------------------------------

    print(
        "\n[3/7] Joining return-level and user-level features..."
    )

    merged = returns.merge(
        features[
            [
                "user_id",
                *USER_FEATURE_COLUMNS,
            ]
        ],
        on="user_id",
        how="left",
        validate="many_to_one",
    )

    validate_user_join(
        returns,
        features,
        merged,
    )

    print(
        f"       Joined rows: {len(merged):,}"
    )

    print("       User feature join: PASSED")

    # --------------------------------------------------------
    # 4. Build model-ready dataset
    # --------------------------------------------------------

    print(
        "\n[4/7] Building model-ready dataset..."
    )

    model_columns = [
        *RETURN_FEATURE_COLUMNS,
        *USER_FEATURE_COLUMNS,
        TARGET_COLUMN,
    ]

    training_dataset = merged[
        model_columns
    ].copy()

    validate_target(
        training_dataset
    )

    validate_features(
        training_dataset,
        RETURN_FEATURE_COLUMNS
        + USER_FEATURE_COLUMNS,
    )

    validate_no_leakage(
        training_dataset
    )

    print(
        f"       Training rows: "
        f"{len(training_dataset):,}"
    )

    print(
        f"       Feature columns: "
        f"{len(model_columns) - 1}"
    )

    print("       Feature validation: PASSED")

    # --------------------------------------------------------
    # 5. Verify class distribution
    # --------------------------------------------------------

    print(
        "\n[5/7] Checking target distribution..."
    )

    label_counts = (
        training_dataset[TARGET_COLUMN]
        .value_counts()
        .sort_index()
    )

    print(
        label_counts.to_string()
    )

    if set(label_counts.index) != {0, 1}:
        raise RuntimeError(
            "Training dataset must contain both classes."
        )

    print("       Binary target check: PASSED")

    # --------------------------------------------------------
    # 6. Train/test split
    # --------------------------------------------------------

    print(
        "\n[6/7] Creating train/validation/test split..."
    )

    development, test = train_test_split(
        training_dataset,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=training_dataset[TARGET_COLUMN],
    )

    train, validation = train_test_split(
        development,
        test_size=VALIDATION_SIZE,
        random_state=RANDOM_STATE,
        stratify=development[TARGET_COLUMN],
    )

    train = train.reset_index(drop=True)
    validation = validation.reset_index(drop=True)
    test = test.reset_index(drop=True)

    expected_train = 6_400
    expected_validation = 1_600
    expected_test = 2_000

    if len(train) != expected_train:
        raise RuntimeError(
            f"Unexpected train size: {len(train)}"
        )

    if len(validation) != expected_validation:
        raise RuntimeError(
            f"Unexpected validation size: {len(validation)}"
        )

    if len(test) != expected_test:
        raise RuntimeError(
            f"Unexpected test size: {len(test)}"
        )

    train_distribution = (
        train[TARGET_COLUMN]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    validation_distribution = (
        validation[TARGET_COLUMN]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    test_distribution = (
        test[TARGET_COLUMN]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    print(
        f"       Train rows:      {len(train):,}"
    )

    print(
        f"       Validation rows: {len(validation):,}"
    )

    print(
        f"       Test rows:       {len(test):,}"
    )

    print(
        f"       Train labels:      {train_distribution}"
    )

    print(
        f"       Validation labels: {validation_distribution}"
    )

    print(
        f"       Test labels:       {test_distribution}"
    )

    # --------------------------------------------------------
    # 7. Save
    # --------------------------------------------------------

    print(
        "\n[7/7] Saving training datasets..."
    )

    TRAINING_DATASET_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    training_dataset.to_parquet(
        TRAINING_DATASET_PATH,
        index=False,
    )

    train.to_parquet(
        TRAIN_PATH,
        index=False,
    )

    validation.to_parquet(
        VALIDATION_PATH,
        index=False,
    )

    test.to_parquet(
        TEST_PATH,
        index=False,
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "STEP 6: COMPLETE"
    )

    print(
        "=" * 60
    )

    print(
        f"Training dataset: "
        f"{TRAINING_DATASET_PATH}"
    )

    print(
        f"Train dataset:    "
        f"{TRAIN_PATH}"
    )

    print(
        f"Validation dataset: "
        f"{VALIDATION_PATH}"
    )

    print(
        f"Test dataset:     "
        f"{TEST_PATH}"
    )

    print(
        f"Total records:    "
        f"{len(training_dataset):,}"
    )

    print(
        f"Features:         "
        f"{len(model_columns) - 1}"
    )


if __name__ == "__main__":
    main()
