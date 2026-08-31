from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[3]

USERS_PATH = BASE_DIR / "data/raw/users.parquet"
RETURNS_PATH = BASE_DIR / "data/raw/returns.parquet"


def _load_users() -> pd.DataFrame:
    return pd.read_parquet(USERS_PATH)


def _load_returns() -> pd.DataFrame:
    return pd.read_parquet(RETURNS_PATH)


def build_user_network(user_id: str) -> dict[str, Any]:
    """
    Build the network surrounding a user.

    Users are connected when they share:
      - device_fingerprint
      - address_hash
      - payment_fingerprint

    Return velocity is calculated from the same seven-day
    relationship logic used by the feature pipeline.
    """

    users = _load_users()
    returns = _load_returns()

    required_user_columns = {
        "user_id",
        "device_fingerprint",
        "address_hash",
        "payment_fingerprint",
    }

    missing = required_user_columns - set(users.columns)

    if missing:
        raise ValueError(
            f"Users dataset missing columns: {sorted(missing)}"
        )

    target_rows = users.loc[
        users["user_id"] == user_id
    ]

    if target_rows.empty:
        raise ValueError(f"User not found: {user_id}")

    target = target_rows.iloc[0]

    relationship_columns = {
        "device_fingerprint": "DEVICE",
        "address_hash": "ADDRESS",
        "payment_fingerprint": "PAYMENT",
    }

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str]] = set()

    # Target user node.
    target_node_id = f"user:{user_id}"

    nodes[target_node_id] = {
        "id": target_node_id,
        "type": "USER",
        "label": user_id,
        "is_target": True,
    }

    for column, relationship_type in relationship_columns.items():
        value = target[column]

        if pd.isna(value):
            continue

        relationship_node_id = (
            f"{relationship_type.lower()}:{value}"
        )

        nodes[relationship_node_id] = {
            "id": relationship_node_id,
            "type": relationship_type,
            "label": str(value),
            "is_target": False,
        }

        edge_key = (
            target_node_id,
            relationship_node_id,
            relationship_type,
        )

        if edge_key not in edge_keys:
            edges.append(
                {
                    "source": target_node_id,
                    "target": relationship_node_id,
                    "type": relationship_type,
                }
            )
            edge_keys.add(edge_key)

        # Find all users sharing this infrastructure.
        related_users = users.loc[
            users[column] == value
        ]

        for _, related in related_users.iterrows():
            related_user_id = str(related["user_id"])

            if related_user_id == user_id:
                continue

            related_node_id = f"user:{related_user_id}"

            nodes[related_node_id] = {
                "id": related_node_id,
                "type": "USER",
                "label": related_user_id,
                "is_target": False,
            }

            related_edge_key = (
                related_node_id,
                relationship_node_id,
                relationship_type,
            )

            if related_edge_key not in edge_keys:
                edges.append(
                    {
                        "source": related_node_id,
                        "target": relationship_node_id,
                        "type": relationship_type,
                    }
                )
                edge_keys.add(related_edge_key)

    # Calculate seven-day return velocity for the target's
    # shared infrastructure.
    returns = returns.copy()

    if "return_requested_at" in returns.columns:
        returns["return_requested_at"] = pd.to_datetime(
            returns["return_requested_at"]
        )

        latest_return = returns["return_requested_at"].max()
        window_start = latest_return - pd.Timedelta(days=7)

        recent_returns = returns.loc[
            returns["return_requested_at"] >= window_start
        ].copy()

        identity_map = users[
            [
                "user_id",
                "device_fingerprint",
                "address_hash",
                "payment_fingerprint",
            ]
        ]

        recent_returns = recent_returns.merge(
            identity_map,
            on="user_id",
            how="left",
            validate="many_to_one",
        )
    else:
        recent_returns = pd.DataFrame()

    velocity: dict[str, int] = {}

    for column, relationship_type in relationship_columns.items():
        value = target[column]

        if pd.isna(value) or recent_returns.empty:
            velocity[relationship_type] = 0
            continue

        velocity[relationship_type] = int(
            (
                recent_returns[column] == value
            ).sum()
        )

    cluster_velocity = max(velocity.values(), default=0)

    # Network counts.
    shared_counts = {
        "DEVICE": int(
            users.loc[
                users["device_fingerprint"]
                == target["device_fingerprint"],
                "user_id",
            ].nunique()
        ),
        "ADDRESS": int(
            users.loc[
                users["address_hash"]
                == target["address_hash"],
                "user_id",
            ].nunique()
        ),
        "PAYMENT": int(
            users.loc[
                users["payment_fingerprint"]
                == target["payment_fingerprint"],
                "user_id",
            ].nunique()
        ),
    }

    return {
        "user_id": user_id,
        "nodes": list(nodes.values()),
        "edges": edges,
        "network_summary": {
            "shared_device_count": shared_counts["DEVICE"],
            "shared_address_count": shared_counts["ADDRESS"],
            "shared_payment_fingerprint_count": shared_counts["PAYMENT"],
            "device_return_velocity_7d": velocity["DEVICE"],
            "address_return_velocity_7d": velocity["ADDRESS"],
            "payment_return_velocity_7d": velocity["PAYMENT"],
            "cluster_return_velocity_7d": cluster_velocity,
        },
    }
