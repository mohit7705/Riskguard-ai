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


def build_user_network(
    user_id: str,
    fallback_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the network surrounding a user.

    Users are connected when they share:
      - device_fingerprint
      - address_hash
      - payment_fingerprint

    The response includes both aggregate network signals and
    explicit infrastructure evidence so analysts can see the
    exact identifiers connecting accounts.
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
        if not fallback_data:
            raise ValueError(f"User not found: {user_id}")

        # Generated RiskGuard identity.
        # The uploaded data does not contain raw infrastructure IDs,
        # so do not invent device/address/payment identifiers.
        target = pd.Series(
            {
                "user_id": user_id,
                "device_fingerprint": None,
                "address_hash": None,
                "payment_fingerprint": None,
            }
        )
    else:
        target = target_rows.iloc[0]

    relationship_columns = {
        "device_fingerprint": "DEVICE",
        "address_hash": "ADDRESS",
        "payment_fingerprint": "PAYMENT",
    }

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str]] = set()
    infrastructure_evidence: list[dict[str, Any]] = []

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

        identifier = str(value)

        relationship_node_id = (
            f"{relationship_type.lower()}:{identifier}"
        )

        nodes[relationship_node_id] = {
            "id": relationship_node_id,
            "type": relationship_type,
            "label": identifier,
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

        related_users = users.loc[
            users[column] == value
        ]

        linked_user_ids: list[str] = []

        for _, related in related_users.iterrows():
            related_user_id = str(related["user_id"])

            if related_user_id == user_id:
                continue

            linked_user_ids.append(related_user_id)

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

        infrastructure_evidence.append(
            {
                "type": relationship_type,
                "identifier": identifier,
                "account_count": len(linked_user_ids) + 1,
                "linked_users": sorted(linked_user_ids),
            }
        )

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

    if not target_rows.empty:
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

    if fallback_data:
        cluster_velocity = int(
            fallback_data.get("cluster_return_velocity_7d", 0) or 0
        )
    else:
        cluster_velocity = max(
            velocity.values(),
            default=0,
        )

    if fallback_data:
        shared_counts = {
            "DEVICE": int(
                fallback_data.get("shared_device_count", 0) or 0
            ),
            "ADDRESS": int(
                fallback_data.get("shared_address_count", 0) or 0
            ),
            "PAYMENT": int(
                fallback_data.get(
                    "shared_payment_fingerprint_count", 0
                ) or 0
            ),
        }

        velocity = {
            "DEVICE": int(
                fallback_data.get("device_return_velocity_7d", 0) or 0
            ),
            "ADDRESS": int(
                fallback_data.get("address_return_velocity_7d", 0) or 0
            ),
            "PAYMENT": int(
                fallback_data.get("payment_return_velocity_7d", 0) or 0
            ),
        }

        infrastructure_evidence = []

        evidence_config = [
            ("DEVICE", "Shared device cluster", "shared_device_count"),
            ("ADDRESS", "Shared address cluster", "shared_address_count"),
            (
                "PAYMENT",
                "Shared payment cluster",
                "shared_payment_fingerprint_count",
            ),
        ]

        for relationship_type, label, field in evidence_config:
            count = int(fallback_data.get(field, 0) or 0)

            if count > 0:
                infrastructure_evidence.append(
                    {
                        "type": relationship_type,
                        "identifier": label,
                        "account_count": count,
                        "linked_users": [],
                        "return_velocity_7d": velocity[
                            relationship_type
                        ],
                    }
                )

    for evidence in infrastructure_evidence:
        relationship_type = evidence["type"]

        evidence["return_velocity_7d"] = velocity.get(
            relationship_type,
            0,
        )

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
        "infrastructure_evidence": infrastructure_evidence,
    }