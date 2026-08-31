from __future__ import annotations

import pandas as pd


REQUIRED_RETURN_COLUMNS = {
    "return_id",
    "user_id",
    "return_requested_at",
}

REQUIRED_USER_COLUMNS = {
    "user_id",
    "device_fingerprint",
    "address_hash",
    "payment_fingerprint",
    "lifetime_order_count",
    "lifetime_return_count",
}


def _validate_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
    dataframe_name: str,
) -> None:
    """Validate that the input DataFrame contains required columns."""

    missing = required_columns.difference(dataframe.columns)

    if missing:
        raise ValueError(
            f"{dataframe_name} is missing required columns: "
            f"{sorted(missing)}"
        )


def calculate_user_return_metrics(
    returns: pd.DataFrame,
    users: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate user-level historical return metrics.

    Metrics:
        return_rate
        return_velocity_30d
        return_velocity_48h
        lifetime_return_count

    The calculations are derived from actual return records.
    No behavioral metric is randomly generated.
    """

    _validate_columns(
        returns,
        REQUIRED_RETURN_COLUMNS,
        "returns",
    )

    _validate_columns(
        users,
        REQUIRED_USER_COLUMNS,
        "users",
    )

    returns = returns.copy()
    users = users.copy()

    returns["return_requested_at"] = pd.to_datetime(
        returns["return_requested_at"]
    )

    return_counts = (
        returns.groupby("user_id")
        .size()
        .rename("lifetime_return_count")
    )

    users["lifetime_return_count"] = (
        users["user_id"]
        .map(return_counts)
        .fillna(0)
        .astype(int)
    )

    users["return_rate"] = (
        users["lifetime_return_count"]
        / users["lifetime_order_count"].clip(lower=1)
    )

    latest_return = returns["return_requested_at"].max()

    window_30d = latest_return - pd.Timedelta(days=30)
    window_48h = latest_return - pd.Timedelta(hours=48)

    recent_30d = (
        returns.loc[
            returns["return_requested_at"] >= window_30d
        ]
        .groupby("user_id")
        .size()
        .rename("return_velocity_30d")
    )

    recent_48h = (
        returns.loc[
            returns["return_requested_at"] >= window_48h
        ]
        .groupby("user_id")
        .size()
        .rename("return_velocity_48h")
    )

    users["return_velocity_30d"] = (
        users["user_id"]
        .map(recent_30d)
        .fillna(0)
        .astype(int)
    )

    users["return_velocity_48h"] = (
        users["user_id"]
        .map(recent_48h)
        .fillna(0)
        .astype(int)
    )

    return users


def calculate_shared_identity_metrics(
    users: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate account-linkage metrics used for abuse-ring detection.

    Metrics:
        shared_device_count
        shared_address_count
        shared_payment_fingerprint_count

    Counts represent the number of unique users sharing each
    infrastructure identifier.
    """

    _validate_columns(
        users,
        REQUIRED_USER_COLUMNS,
        "users",
    )

    users = users.copy()

    device_counts = (
        users.groupby("device_fingerprint")["user_id"]
        .nunique()
    )

    address_counts = (
        users.groupby("address_hash")["user_id"]
        .nunique()
    )

    payment_counts = (
        users.groupby("payment_fingerprint")["user_id"]
        .nunique()
    )

    users["shared_device_count"] = (
        users["device_fingerprint"]
        .map(device_counts)
        .astype(int)
    )

    users["shared_address_count"] = (
        users["address_hash"]
        .map(address_counts)
        .astype(int)
    )

    users["shared_payment_fingerprint_count"] = (
        users["payment_fingerprint"]
        .map(payment_counts)
        .astype(int)
    )

    return users


def calculate_cluster_return_velocity_7d(
    returns: pd.DataFrame,
    users: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate seven-day return velocity across linked accounts.

    Accounts are linked through:
        device_fingerprint
        address_hash
        payment_fingerprint

    The metric is calculated from actual return records and grouped
    infrastructure relationships.
    """

    _validate_columns(
        returns,
        REQUIRED_RETURN_COLUMNS,
        "returns",
    )

    _validate_columns(
        users,
        REQUIRED_USER_COLUMNS,
        "users",
    )

    returns = returns.copy()
    users = users.copy()

    returns["return_requested_at"] = pd.to_datetime(
        returns["return_requested_at"]
    )

    latest_return = returns["return_requested_at"].max()
    window_start = latest_return - pd.Timedelta(days=7)

    recent_returns = returns.loc[
        returns["return_requested_at"] >= window_start
    ].copy()

    identity_columns = [
        "user_id",
        "device_fingerprint",
        "address_hash",
        "payment_fingerprint",
    ]

    identity_map = users[identity_columns].copy()

    recent_returns = recent_returns.merge(
        identity_map,
        on="user_id",
        how="left",
        validate="many_to_one",
    )

    device_velocity = (
        recent_returns.groupby("device_fingerprint")
        .size()
        .rename("device_return_velocity_7d")
    )

    address_velocity = (
        recent_returns.groupby("address_hash")
        .size()
        .rename("address_return_velocity_7d")
    )

    payment_velocity = (
        recent_returns.groupby("payment_fingerprint")
        .size()
        .rename("payment_return_velocity_7d")
    )

    users["device_return_velocity_7d"] = (
        users["device_fingerprint"]
        .map(device_velocity)
        .fillna(0)
        .astype(int)
    )

    users["address_return_velocity_7d"] = (
        users["address_hash"]
        .map(address_velocity)
        .fillna(0)
        .astype(int)
    )

    users["payment_return_velocity_7d"] = (
        users["payment_fingerprint"]
        .map(payment_velocity)
        .fillna(0)
        .astype(int)
    )

    users["cluster_return_velocity_7d"] = users[
        [
            "device_return_velocity_7d",
            "address_return_velocity_7d",
            "payment_return_velocity_7d",
        ]
    ].max(axis=1)

    return users


def calculate_all_user_features(
    returns: pd.DataFrame,
    users: pd.DataFrame,
) -> pd.DataFrame:
    """
    Execute the complete user-level feature aggregation pipeline.
    """

    users = calculate_user_return_metrics(
        returns,
        users,
    )

    users = calculate_shared_identity_metrics(
        users,
    )

    users = calculate_cluster_return_velocity_7d(
        returns,
        users,
    )

    return users