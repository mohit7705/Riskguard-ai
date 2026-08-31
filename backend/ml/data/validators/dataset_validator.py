from __future__ import annotations

import pandas as pd


TOTAL_RECORDS = 10_000
LEGITIMATE_RECORDS = 8_000
ABUSIVE_RECORDS = 2_000
RECORDS_PER_ABUSE_TYPE = 400

ABUSE_TYPES = (
    "WARDROBING",
    "SERIAL_RETURNER",
    "ITEM_SWAP_OR_EMPTY_BOX",
    "ABUSE_RING",
    "SUSPICIOUS_ACCOUNT_BEHAVIOR",
)


def _require_columns(
    dataframe: pd.DataFrame,
    required: set[str],
    name: str,
) -> None:
    missing = sorted(required.difference(dataframe.columns))

    if missing:
        raise RuntimeError(
            f"{name} is missing required columns: {missing}"
        )


def _check_unique_ids(
    dataframe: pd.DataFrame,
    column: str,
) -> None:
    if dataframe[column].duplicated().any():
        duplicates = int(dataframe[column].duplicated().sum())

        raise RuntimeError(
            f"Duplicate {column} values detected: {duplicates}"
        )


def _check_distribution(
    returns: pd.DataFrame,
) -> None:
    if len(returns) != TOTAL_RECORDS:
        raise RuntimeError(
            f"Expected exactly {TOTAL_RECORDS} records; "
            f"received {len(returns)}."
        )

    label_counts = (
        returns["abuse_label"]
        .value_counts()
        .to_dict()
    )

    if label_counts.get(0, 0) != LEGITIMATE_RECORDS:
        raise RuntimeError(
            "Legitimate distribution failed: "
            f"{label_counts.get(0, 0)} != {LEGITIMATE_RECORDS}"
        )

    if label_counts.get(1, 0) != ABUSIVE_RECORDS:
        raise RuntimeError(
            "Abusive distribution failed: "
            f"{label_counts.get(1, 0)} != {ABUSIVE_RECORDS}"
        )

    abuse_counts = (
        returns.loc[
            returns["abuse_label"] == 1,
            "abuse_type",
        ]
        .value_counts()
        .to_dict()
    )

    for abuse_type in ABUSE_TYPES:
        count = abuse_counts.get(abuse_type, 0)

        if count != RECORDS_PER_ABUSE_TYPE:
            raise RuntimeError(
                f"{abuse_type} distribution failed: "
                f"{count} != {RECORDS_PER_ABUSE_TYPE}"
            )

    legitimate_types = returns.loc[
        returns["abuse_label"] == 0,
        "abuse_type",
    ]

    if not legitimate_types.isna().all():
        raise RuntimeError(
            "Legitimate records must have abuse_type = NULL."
        )


def _check_temporal_invariants(
    returns: pd.DataFrame,
) -> None:
    timestamp_columns = [
        "ordered_at",
        "delivery_at",
        "return_requested_at",
    ]

    for column in timestamp_columns:
        returns[column] = pd.to_datetime(
            returns[column],
            errors="raise",
        )

    invalid = (
        (returns["ordered_at"] > returns["delivery_at"])
        | (
            returns["delivery_at"]
            > returns["return_requested_at"]
        )
    )

    if invalid.any():
        raise RuntimeError(
            "Temporal invariant failed: "
            "ordered_at <= delivery_at <= "
            "return_requested_at"
        )


def _check_refund_invariant(
    returns: pd.DataFrame,
) -> None:
    maximum_refund = (
        returns["item_value"]
        * returns["quantity"]
    )

    invalid = (
        returns["refund_amount"]
        > maximum_refund + 0.01
    )

    if invalid.any():
        raise RuntimeError(
            "Refund invariant failed: "
            "refund_amount > item_value * quantity"
        )


def _check_required_values(
    returns: pd.DataFrame,
) -> None:
    required = [
        "return_id",
        "order_id",
        "user_id",
        "order_category",
        "order_value",
        "item_value",
        "quantity",
        "ordered_at",
        "delivery_at",
        "return_requested_at",
        "time_to_return_request_hours",
        "refund_amount",
        "returned_item_match",
        "item_condition_score",
        "package_weight_delta_pct",
        "vision_confidence_score",
        "abuse_label",
        "abuse_type",
    ]

    null_count = int(
        returns[required]
        .isna()
        .sum()
        .sum()
    )

    # abuse_type is intentionally NULL for legitimate records.
    allowed_nulls = int(
        (returns["abuse_label"] == 0).sum()
    )

    actual_nulls = int(
        returns[required]
        .isna()
        .sum()
        .sum()
    )

    if actual_nulls != allowed_nulls:
        raise RuntimeError(
            "Unexpected NULL values detected in dataset."
        )


def _check_return_rate(
    features: pd.DataFrame,
) -> None:
    if "return_rate" not in features.columns:
        raise RuntimeError(
            "Feature dataset missing return_rate."
        )

    invalid = (
        (features["return_rate"] < 0)
        | (features["return_rate"] > 1)
    )

    if invalid.any():
        raise RuntimeError(
            "Return-rate invariant failed: "
            "return_rate must be between 0 and 1."
        )


def _check_feature_nulls(
    features: pd.DataFrame,
) -> None:
    feature_columns = [
        "return_rate",
        "return_velocity_30d",
        "return_velocity_48h",
        "shared_device_count",
        "shared_address_count",
        "shared_payment_fingerprint_count",
        "cluster_return_velocity_7d",
    ]

    missing = [
        column
        for column in feature_columns
        if column not in features.columns
    ]

    if missing:
        raise RuntimeError(
            f"Missing calculated feature columns: {missing}"
        )

    null_count = int(
        features[feature_columns]
        .isna()
        .sum()
        .sum()
    )

    if null_count != 0:
        raise RuntimeError(
            f"Calculated features contain {null_count} NULL values."
        )


def _check_ground_truth_rules(
    returns: pd.DataFrame,
    features: pd.DataFrame,
) -> None:
    data = returns.merge(
        features[
            [
                "user_id",
                "account_age_days",
                "lifetime_order_count",
                "lifetime_return_count",
                "return_rate",
                "return_velocity_30d",
                "shared_device_count",
                "shared_address_count",
                "shared_payment_fingerprint_count",
                "cluster_return_velocity_7d",
            ]
        ],
        on="user_id",
        how="left",
        validate="many_to_one",
    )

    abusive = data["abuse_label"] == 1

    # --------------------------------------------------------------
    # WARDROBING
    # --------------------------------------------------------------

    wardrobing = data["abuse_type"] == "WARDROBING"

    invalid = wardrobing & ~(
        data["order_category"].isin(
            ["Apparel", "Luxury", "Electronics"]
        )
        & (data["time_to_return_request_hours"] <= 72)
        & (data["item_condition_score"] < 0.60)
        & (data["order_value"] >= 150)
    )

    if invalid.any():
        raise RuntimeError(
            "WARDROBING ground-truth rule failed."
        )

    # --------------------------------------------------------------
    # SERIAL RETURNER
    # --------------------------------------------------------------

    serial = (
        data["abuse_type"]
        == "SERIAL_RETURNER"
    )

    invalid = serial & ~(
        (data["lifetime_order_count"] >= 5)
        & (data["return_rate"] >= 0.65)
        & (data["return_velocity_30d"] >= 4)
        & (data["account_age_days"] >= 30)
    )

    if invalid.any():
        raise RuntimeError(
            "SERIAL_RETURNER ground-truth rule failed."
        )

    # --------------------------------------------------------------
    # ITEM SWAP / EMPTY BOX
    # --------------------------------------------------------------

    item_swap = (
        data["abuse_type"]
        == "ITEM_SWAP_OR_EMPTY_BOX"
    )

    invalid = item_swap & ~(
        (
            (~data["returned_item_match"])
            | (data["package_weight_delta_pct"] > 30)
        )
        & (data["vision_confidence_score"] < 0.40)
    )

    if invalid.any():
        raise RuntimeError(
            "ITEM_SWAP_OR_EMPTY_BOX ground-truth rule failed."
        )

    # --------------------------------------------------------------
    # ABUSE RING
    # --------------------------------------------------------------

    ring = data["abuse_type"] == "ABUSE_RING"

    invalid = ring & ~(
        (
            (data["shared_device_count"] >= 3)
            | (data["shared_address_count"] >= 4)
        )
        & (data["shared_payment_fingerprint_count"] >= 2)
        & (data["cluster_return_velocity_7d"] >= 6)
    )

    if invalid.any():
        raise RuntimeError(
            "ABUSE_RING ground-truth rule failed."
        )

    # --------------------------------------------------------------
    # SUSPICIOUS ACCOUNT BEHAVIOR
    # --------------------------------------------------------------

    suspicious = (
        data["abuse_type"]
        == "SUSPICIOUS_ACCOUNT_BEHAVIOR"
    )

    invalid = suspicious & ~(
        (data["account_age_days"] <= 7)
        & (data["order_value"] >= 800)
        & (data["time_to_return_request_hours"] <= 12)
    )

    if invalid.any():
        raise RuntimeError(
            "SUSPICIOUS_ACCOUNT_BEHAVIOR "
            "ground-truth rule failed."
        )

    if not (data.loc[abusive, "abuse_type"].isin(ABUSE_TYPES)).all():
        raise RuntimeError(
            "Abusive records contain an unknown abuse type."
        )


def validate_dataset(
    returns: pd.DataFrame,
    features: pd.DataFrame | None = None,
) -> bool:
    """
    Validate the complete RiskGuard AI synthetic dataset.

    Raises RuntimeError on any contract violation.

    Returns:
        True when every invariant passes.
    """

    required_return_columns = {
        "return_id",
        "order_id",
        "user_id",
        "order_category",
        "order_value",
        "item_value",
        "quantity",
        "ordered_at",
        "delivery_at",
        "return_requested_at",
        "time_to_return_request_hours",
        "refund_amount",
        "returned_item_match",
        "item_condition_score",
        "package_weight_delta_pct",
        "vision_confidence_score",
        "abuse_label",
        "abuse_type",
    }

    _require_columns(
        returns,
        required_return_columns,
        "returns",
    )

    _check_unique_ids(
        returns,
        "return_id",
    )

    _check_unique_ids(
        returns,
        "order_id",
    )

    _check_distribution(
        returns,
    )

    _check_temporal_invariants(
        returns,
    )

    _check_refund_invariant(
        returns,
    )

    _check_required_values(
        returns,
    )

    if features is not None:
        _check_return_rate(
            features,
        )

        _check_feature_nulls(
            features,
        )

        _check_ground_truth_rules(
            returns,
            features,
        )

    print("DATASET VALIDATION: PASSED")
    print(f"TOTAL RECORDS: {len(returns)}")
    print("LEGITIMATE: 8000")
    print("ABUSIVE: 2000")
    print("EACH ABUSE TYPE: 400")
    print("TEMPORAL INVARIANT: PASSED")
    print("REFUND INVARIANT: PASSED")
    print("ID UNIQUENESS: PASSED")

    if features is not None:
        print("RETURN RATE INVARIANT: PASSED")
        print("FEATURE NULL CHECK: PASSED")
        print("GROUND-TRUTH RULES: PASSED")

    return True
