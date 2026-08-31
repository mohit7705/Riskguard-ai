from pathlib import Path

import pandas as pd


RETURNS_PATH = Path("data/raw/returns.parquet")
FEATURES_PATH = Path("data/processed/user_features.parquet")
OUTPUT_PATH = Path("data/processed/training_dataset.parquet")


def main() -> None:
    print("=" * 60)
    print("RiskGuard AI — ML Training Dataset Builder")
    print("=" * 60)

    # ------------------------------------------------------------
    # 1. Load persisted datasets
    # ------------------------------------------------------------

    print("\n[1/6] Loading persisted datasets...")

    returns = pd.read_parquet(RETURNS_PATH)
    features = pd.read_parquet(FEATURES_PATH)

    print(f"       Returns:  {returns.shape}")
    print(f"       Features: {features.shape}")

    # ------------------------------------------------------------
    # 2. Validate join key
    # ------------------------------------------------------------

    print("\n[2/6] Validating user feature keys...")

    if features["user_id"].duplicated().any():
        raise RuntimeError(
            "Feature dataset contains duplicate user_id values."
        )

    if returns["user_id"].isna().any():
        raise RuntimeError(
            "Returns dataset contains NULL user_id values."
        )

    if features["user_id"].isna().any():
        raise RuntimeError(
            "Feature dataset contains NULL user_id values."
        )

    print("       User ID validation: PASSED")

    # ------------------------------------------------------------
    # 3. Select ML features
    # ------------------------------------------------------------

    feature_columns = [
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

    missing_features = [
        column
        for column in feature_columns
        if column not in features.columns
    ]

    if missing_features:
        raise RuntimeError(
            f"Missing required ML features: {missing_features}"
        )

    print("\n[3/6] ML feature selection: PASSED")
    print(f"       Features selected: {len(feature_columns)}")

    # ------------------------------------------------------------
    # 4. Join return events with user features
    # ------------------------------------------------------------

    print("\n[4/6] Joining return events with user features...")

    user_features = features[
        ["user_id"] + feature_columns
    ].copy()

    training = returns.merge(
        user_features,
        on="user_id",
        how="left",
        validate="many_to_one",
    )

    if len(training) != len(returns):
        raise RuntimeError(
            "Training dataset row count changed during join."
        )

    print(f"       Training rows: {len(training):,}")

    # ------------------------------------------------------------
    # 5. Validate ML dataset
    # ------------------------------------------------------------

    print("\n[5/6] Validating training dataset...")

    if training["abuse_label"].isna().any():
        raise RuntimeError(
            "Training dataset contains NULL abuse labels."
        )

    null_feature_count = int(
        training[feature_columns]
        .isna()
        .sum()
        .sum()
    )

    if null_feature_count != 0:
        raise RuntimeError(
            f"Training features contain {null_feature_count} NULL values."
        )

    label_counts = (
        training["abuse_label"]
        .value_counts()
        .sort_index()
    )

    if int(label_counts.get(0, 0)) != 8_000:
        raise RuntimeError(
            "Expected exactly 8,000 legitimate records."
        )

    if int(label_counts.get(1, 0)) != 2_000:
        raise RuntimeError(
            "Expected exactly 2,000 abusive records."
        )

    print("       Row count: PASSED")
    print("       Label integrity: PASSED")
    print("       Feature NULL check: PASSED")

    # ------------------------------------------------------------
    # 6. Save training dataset
    # ------------------------------------------------------------

    print("\n[6/6] Saving training dataset...")

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    training.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print()
    print("=" * 60)
    print("ML TRAINING DATASET BUILD COMPLETE")
    print("=" * 60)

    print(f"Output: {OUTPUT_PATH}")
    print(f"Rows:   {len(training):,}")
    print(f"Columns:{len(training.columns):,}")

    print("\nLabels:")
    print(label_counts.to_string())

    print("\nML features:")
    for column in feature_columns:
        print(f"  - {column}")

    print("\nSTEP 6: COMPLETE")


if __name__ == "__main__":
    main()