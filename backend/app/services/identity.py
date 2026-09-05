from __future__ import annotations

import hashlib
from typing import Any


def resolve_user_id(
    data: dict[str, Any],
    assignment_id: str,
) -> str:
    """
    Resolve or generate a stable internal RiskGuard user ID.

    Existing user_id is always preserved.

    If no user_id exists, a deterministic ID is generated from
    the available raw identity/transaction data and scoped to
    the assignment.
    """

    existing_user_id = _clean(data.get("user_id"))

    if existing_user_id:
        return existing_user_id

    identity_keys = (
        "customer_id",
        "account_id",
        "buyer_id",
        "email",
        "phone",
        "mobile",
        "user",
    )

    for key in identity_keys:
        value = _clean(data.get(key))

        if value:
            return _generate_user_id(
                assignment_id=assignment_id,
                identity=f"{key}:{value.lower()}",
            )

    stable_keys = (
        "order_id",
        "return_id",
        "order_value",
        "item_value",
        "quantity",
        "order_category",
        "return_reason",
    )

    parts = []

    for key in stable_keys:
        value = _clean(data.get(key))

        if value:
            parts.append(f"{key}={value}")

    if not parts:
        raise ValueError(
            "Unable to generate user_id: no usable identity data found."
        )

    return _generate_user_id(
        assignment_id=assignment_id,
        identity="|".join(parts),
    )


def _generate_user_id(
    assignment_id: str,
    identity: str,
) -> str:
    raw = f"{assignment_id}:{identity}"

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:12].upper()

    return f"U-{digest}"


def _clean(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    return value or None