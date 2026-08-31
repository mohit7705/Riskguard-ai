from __future__ import annotations

import numpy as np
import pandas as pd


ABUSE_TYPES = (
    "WARDROBING",
    "SERIAL_RETURNER",
    "ITEM_SWAP_OR_EMPTY_BOX",
    "ABUSE_RING",
    "SUSPICIOUS_ACCOUNT_BEHAVIOR",
)

# Minimum NEW returns a SERIAL_RETURNER user must receive so that
# return_velocity_30d >= 4 even if none of their older baseline
# returns happen to fall inside the last 30 days.
MIN_SERIAL_VELOCITY = 4


def _require_columns(
    df: pd.DataFrame,
    required: list[str],
    name: str,
) -> None:
    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{name} missing columns: {missing}"
        )


def _build_capacity(
    selected: pd.DataFrame,
    users: pd.DataFrame,
) -> pd.DataFrame:
    """
    Track how many additional return events each user can receive,
    based on the CURRENT state of `selected` (call this fresh
    whenever ownership of rows may have changed).

    Invariant:
        final lifetime_return_count <= lifetime_order_count
    """

    counts = (
        selected.groupby("user_id")
        .size()
        .rename("current_return_count")
    )

    capacity = users[
        [
            "user_id",
            "lifetime_order_count",
            "account_age_days",
        ]
    ].copy()

    capacity["current_return_count"] = (
        capacity["user_id"]
        .map(counts)
        .fillna(0)
        .astype(int)
    )

    capacity["remaining_capacity"] = (
        capacity["lifetime_order_count"]
        - capacity["current_return_count"]
    )

    invalid = capacity["remaining_capacity"] < 0

    if invalid.any():
        bad = capacity.loc[
            invalid,
            [
                "user_id",
                "lifetime_order_count",
                "current_return_count",
            ],
        ]

        raise RuntimeError(
            "Initial return capacity invariant failed:\n"
            f"{bad.to_string(index=False)}"
        )

    return capacity


def _allocate_users(
    rng: np.random.Generator,
    capacity: pd.DataFrame,
    count: int,
    eligible_mask: pd.Series | None = None,
) -> np.ndarray:
    """
    Allocate exactly `count` return events, weighted by remaining
    capacity. Mutates `capacity["remaining_capacity"]` IN PLACE on
    the object the caller passed in, so consecutive calls that share
    the same `capacity` frame (e.g. ABUSE_RING then
    SUSPICIOUS_ACCOUNT_BEHAVIOR) never double-spend a user's
    capacity.
    """

    working = capacity

    mask = working["remaining_capacity"] > 0
    if eligible_mask is not None:
        mask = mask & eligible_mask

    available_idx = working.index[mask]

    if available_idx.empty:
        raise RuntimeError(
            "No users available for return allocation."
        )

    total_capacity = int(
        working.loc[available_idx, "remaining_capacity"].sum()
    )

    if total_capacity < count:
        raise RuntimeError(
            "Insufficient user return capacity. "
            f"Required={count}, available={total_capacity}."
        )

    allocations: list[str] = []

    for _ in range(count):
        avail_mask = working.index.isin(available_idx) & (
            working["remaining_capacity"] > 0
        )
        available = working.loc[avail_mask]

        if available.empty:
            raise RuntimeError(
                "User return capacity exhausted."
            )

        weights = (
            available["remaining_capacity"]
            .to_numpy(dtype=float)
        )

        weights /= weights.sum()

        position = int(
            rng.choice(
                len(available),
                p=weights,
            )
        )

        row_idx = available.index[position]
        user_id = available.iloc[position]["user_id"]

        allocations.append(user_id)

        working.loc[row_idx, "remaining_capacity"] -= 1

    return np.asarray(allocations)


def _allocate_serial_returners(
    rng: np.random.Generator,
    capacity: pd.DataFrame,
    count: int,
) -> np.ndarray:
    """
    Allocate SERIAL_RETURNER events.

    Every affected user must satisfy, in the FINAL dataset:

        account_age_days      >= 30
        lifetime_order_count  >= 5
        return_rate           >= 0.65
        return_velocity_30d   >= 4

    Unlike a proportional/weighted draw (which spreads `count`
    thinly across every eligible user and leaves almost none of
    them actually over the threshold), this concentrates each
    selected user's FULL requirement onto them, and only spends the
    leftover budget as bonus returns on users already past
    threshold - so every SERIAL_RETURNER user genuinely qualifies.
    """

    eligible = capacity.loc[
        (capacity["account_age_days"] >= 30)
        & (capacity["lifetime_order_count"] >= 5)
        & (capacity["remaining_capacity"] > 0)
    ].copy()

    if eligible.empty:
        raise RuntimeError(
            "No eligible users for SERIAL_RETURNER."
        )

    eligible["required_returns"] = np.ceil(
        eligible["lifetime_order_count"] * 0.65
    ).astype(int)

    rate_min = (
        eligible["required_returns"] - eligible["current_return_count"]
    ).clip(lower=0)

    # All injected serial-returner returns are dated inside the most
    # recent ~30-day window (see the date logic below), but a user's
    # pre-existing baseline returns almost never are - so don't let
    # required_min be reduced by current_return_count for velocity.
    eligible["required_min"] = np.maximum(rate_min, MIN_SERIAL_VELOCITY)

    feasible = eligible.loc[
        eligible["required_min"] <= eligible["remaining_capacity"]
    ].copy()

    if feasible.empty:
        raise RuntimeError(
            "No users have enough return capacity to fully clear "
            "both the SERIAL_RETURNER rate and velocity thresholds."
        )

    feasible = feasible.sample(
        frac=1,
        random_state=int(rng.integers(0, 2**32 - 1)),
    ).reset_index(drop=True)

    picked: dict[str, int] = {}
    cumulative = 0

    for _, row in feasible.iterrows():
        need = int(row["required_min"])
        if need == 0:
            continue
        if cumulative + need <= count:
            picked[row["user_id"]] = need
            cumulative += need
        if cumulative == count:
            break

    if cumulative < count:
        leftover = count - cumulative

        spare = {
            uid: int(
                feasible.loc[feasible["user_id"] == uid, "remaining_capacity"].iloc[0]
            ) - n
            for uid, n in picked.items()
        }
        spendable = [uid for uid in picked if spare[uid] > 0]

        i = 0
        while leftover > 0:
            if not spendable:
                raise RuntimeError(
                    f"Insufficient capacity to place {count} SERIAL_RETURNER "
                    f"records while keeping every serial user above threshold "
                    f"(short by {leftover})."
                )

            uid = spendable[i % len(spendable)]
            picked[uid] += 1
            spare[uid] -= 1
            leftover -= 1

            if spare[uid] == 0:
                spendable.remove(uid)
            else:
                i += 1

    allocations: list[str] = []
    for uid, n in picked.items():
        allocations.extend([uid] * n)

    allocations_arr = np.asarray(allocations, dtype=object)
    rng.shuffle(allocations_arr)

    for uid, n in picked.items():
        capacity.loc[
            capacity["user_id"] == uid, "remaining_capacity"
        ] -= n

    return allocations_arr


def _create_ring_clusters(
    rng: np.random.Generator,
    users: pd.DataFrame,
) -> list[list[str]]:
    """
    Create 3-5 user abuse-ring clusters.
    """

    pool = users["user_id"].to_numpy().copy()

    rng.shuffle(pool)

    clusters: list[list[str]] = []

    cursor = 0

    while cursor + 3 <= len(pool):
        max_size = min(
            5,
            len(pool) - cursor,
        )

        size = int(
            rng.integers(
                3,
                max_size + 1,
            )
        )

        cluster = pool[
            cursor:cursor + size
        ].tolist()

        clusters.append(cluster)

        cursor += size

        if len(clusters) >= 20:
            break

    return clusters


def _reconcile_user_aggregates(
    selected: pd.DataFrame,
    users: pd.DataFrame,
) -> pd.DataFrame:
    """
    Recalculate lifetime return counters from final events.
    """

    users = users.copy()

    counts = (
        selected.groupby("user_id")
        .size()
        .rename("lifetime_return_count")
    )

    users["lifetime_return_count"] = (
        users["user_id"]
        .map(counts)
        .fillna(0)
        .astype(int)
    )

    invalid = (
        users["lifetime_return_count"]
        > users["lifetime_order_count"]
    )

    if invalid.any():
        bad = users.loc[
            invalid,
            [
                "user_id",
                "lifetime_order_count",
                "lifetime_return_count",
            ],
        ]

        raise RuntimeError(
            "User aggregate invariant failed:\n"
            f"{bad.to_string(index=False)}"
        )

    return users


def inject_abuse(
    rng: np.random.Generator,
    returns: pd.DataFrame,
    users: pd.DataFrame,
    target_records: int = 10_000,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create the locked RiskGuard AI ground-truth dataset.

    Distribution:

        8,000 legitimate
        400 WARDROBING
        400 SERIAL_RETURNER
        400 ITEM_SWAP_OR_EMPTY_BOX
        400 ABUSE_RING
        400 SUSPICIOUS_ACCOUNT_BEHAVIOR

    Execution order matters here: WARDROBING and ITEM_SWAP never
    change `user_id`, so they can run any time. ABUSE_RING and
    SUSPICIOUS_ACCOUNT_BEHAVIOR reassign rows to different owners,
    which changes how many baseline returns each user actually ends
    up with. SERIAL_RETURNER cares about that final per-user return
    count (it has to push each chosen user over rate/velocity
    thresholds), so it must run LAST, against a capacity table
    rebuilt after the reassignments have already happened.
    """

    _require_columns(
        returns,
        [
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
        ],
        "returns",
    )

    _require_columns(
        users,
        [
            "user_id",
            "account_created_at",
            "account_age_days",
            "device_fingerprint",
            "address_hash",
            "payment_fingerprint",
            "lifetime_order_count",
            "lifetime_return_count",
            "total_spent",
        ],
        "users",
    )

    if target_records != 10_000:
        raise ValueError(
            "RiskGuard AI requires exactly 10,000 records."
        )

    if len(returns) < target_records:
        raise ValueError(
            f"Need at least {target_records} baseline returns; "
            f"received {len(returns)}."
        )

    selected = (
        returns.sample(
            frac=1,
            random_state=int(
                rng.integers(
                    0,
                    2**32 - 1,
                )
            ),
        )
        .reset_index(drop=True)
        .iloc[:target_records]
        .copy()
    )

    selected["abuse_label"] = 0
    selected["abuse_type"] = None

    indexes = np.arange(target_records)

    rng.shuffle(indexes)

    wardrobing_idx = indexes[0:400]
    serial_idx = indexes[400:800]
    item_swap_idx = indexes[800:1200]
    ring_idx = indexes[1200:1600]
    suspicious_idx = indexes[1600:2000]

    # ==============================================================
    # WARDROBING (no ownership change - order-independent)
    # ==============================================================

    selected.loc[wardrobing_idx, "abuse_label"] = 1
    selected.loc[wardrobing_idx, "abuse_type"] = "WARDROBING"
    selected.loc[wardrobing_idx, "order_category"] = rng.choice(
        ["Apparel", "Luxury", "Electronics"], size=400,
    )
    selected.loc[wardrobing_idx, "order_value"] = np.round(
        rng.uniform(150, 900, size=400), 2
    )
    selected.loc[wardrobing_idx, "time_to_return_request_hours"] = np.round(
        rng.uniform(6, 72, size=400), 2
    )
    # WARDROBING — stays < 0.60 (validator requirement), narrowed to sit right at
    # the overlap boundary with the new legitimate lower-tail band.
    selected.loc[wardrobing_idx, "item_condition_score"] = np.round(
        rng.uniform(0.45, 0.59, size=400), 3
    )
    selected.loc[wardrobing_idx, "returned_item_match"] = True
    # WARDROBING — no validator constraint on this field, keep as-is
    selected.loc[wardrobing_idx, "vision_confidence_score"] = np.round(
        rng.uniform(0.65, 0.93, size=400), 3
    )

    # ==============================================================
    # ITEM SWAP / EMPTY BOX (no ownership change - order-independent)
    # ==============================================================

    selected.loc[item_swap_idx, "abuse_label"] = 1
    selected.loc[item_swap_idx, "abuse_type"] = "ITEM_SWAP_OR_EMPTY_BOX"
    selected.loc[item_swap_idx, "returned_item_match"] = False
    # ITEM_SWAP_OR_EMPTY_BOX — the validator's rule is an OR (returned_item_match=False already
    # satisfies it), so this field isn't validator-constrained — widen
    # it to overlap the new legitimate 0–15 band.
    selected.loc[item_swap_idx, "package_weight_delta_pct"] = np.round(
        rng.uniform(5.0, 85.0, size=400), 2
    )
    # ITEM_SWAP_OR_EMPTY_BOX — stays < 0.40 (validator requirement), narrowed to the overlap edge.
    selected.loc[item_swap_idx, "vision_confidence_score"] = np.round(
        rng.uniform(0.30, 0.39, size=400), 3
    )
    selected.loc[item_swap_idx, "refund_amount"] = np.round(
        selected.loc[item_swap_idx, "item_value"].to_numpy()
        * selected.loc[item_swap_idx, "quantity"].to_numpy()
        * rng.uniform(0.50, 0.95, size=400),
        2,
    )

    # ==============================================================
    # ABUSE RING (reassigns ownership - must run before SERIAL_RETURNER)
    # ==============================================================

    selected.loc[ring_idx, "abuse_label"] = 1
    selected.loc[ring_idx, "abuse_type"] = "ABUSE_RING"

    ring_clusters = _create_ring_clusters(rng, users)
    if not ring_clusters:
        raise RuntimeError("Unable to create abuse-ring clusters.")

    pre_ring_capacity = _build_capacity(selected, users)

    ring_cluster = ring_clusters[0]

    ring_capacity = pre_ring_capacity[
        pre_ring_capacity["user_id"].isin(ring_cluster)
        & (pre_ring_capacity["remaining_capacity"] > 0)
    ]

    if ring_capacity["remaining_capacity"].sum() < 400:
        ring_users: list[str] = []

        for cluster in ring_clusters:
            for user_id in cluster:
                row = pre_ring_capacity[pre_ring_capacity["user_id"] == user_id]
                if row.empty:
                    continue
                if int(row.iloc[0]["remaining_capacity"]) > 0:
                    ring_users.append(user_id)

            if (
                pre_ring_capacity[pre_ring_capacity["user_id"].isin(ring_users)][
                    "remaining_capacity"
                ].sum()
                >= 400
            ):
                break

        if not ring_users:
            raise RuntimeError(
                "No capacity available for abuse-ring allocation."
            )

        ring_cluster = ring_users

    ring_capacity_mask = pre_ring_capacity["user_id"].isin(ring_cluster)
    ring_users_allocated = _allocate_users(
        rng, pre_ring_capacity, 400, ring_capacity_mask
    )

    selected.loc[ring_idx, "user_id"] = ring_users_allocated

    shared_device = f"RING-DEV-{rng.integers(1, 10000):05d}"
    shared_address = f"RING-ADDR-{rng.integers(1, 10000):05d}"
    shared_payment = f"RING-PAY-{rng.integers(1, 10000):05d}"

    users.loc[users["user_id"].isin(ring_cluster), "device_fingerprint"] = shared_device
    users.loc[users["user_id"].isin(ring_cluster), "address_hash"] = shared_address
    users.loc[users["user_id"].isin(ring_cluster), "payment_fingerprint"] = shared_payment

    # ==============================================================
    # SUSPICIOUS ACCOUNT BEHAVIOR (reassigns ownership too - shares
    # the SAME capacity frame `pre_ring_capacity` as ABUSE_RING so
    # the two steps can't double-spend a user's capacity)
    # ==============================================================

    selected.loc[suspicious_idx, "abuse_label"] = 1
    selected.loc[suspicious_idx, "abuse_type"] = "SUSPICIOUS_ACCOUNT_BEHAVIOR"

    # The validator's ground-truth rule requires account_age_days <= 7
    # for every SUSPICIOUS_ACCOUNT_BEHAVIOR row - do NOT relax this,
    # even if capacity is tight; a relaxed row is a validator failure,
    # not a warning.
    suspicious_mask = (
        (pre_ring_capacity["account_age_days"] <= 7)
        & (pre_ring_capacity["remaining_capacity"] > 0)
    )

    suspicious_capacity_available = int(
        pre_ring_capacity.loc[suspicious_mask, "remaining_capacity"].sum()
    )

    if suspicious_capacity_available < 400:
        raise RuntimeError(
            "Insufficient return capacity among accounts with "
            "account_age_days <= 7 for SUSPICIOUS_ACCOUNT_BEHAVIOR "
            f"injection. available={suspicious_capacity_available}, "
            "required=400."
        )

    suspicious_users = _allocate_users(
        rng, pre_ring_capacity, 400, suspicious_mask
    )

    selected.loc[suspicious_idx, "user_id"] = suspicious_users
    selected.loc[suspicious_idx, "order_value"] = np.round(
        rng.uniform(800, 2000, size=400), 2
    )
    selected.loc[suspicious_idx, "time_to_return_request_hours"] = np.round(
        rng.uniform(1, 12, size=400), 2
    )

    # ==============================================================
    # SERIAL RETURNER (runs LAST, against capacity rebuilt fresh so
    # it reflects the ownership changes ABUSE_RING/SUSPICIOUS just
    # made, and concentrates each user's full requirement instead of
    # spreading 400 records thinly across every eligible user)
    # ==============================================================

    selected.loc[serial_idx, "abuse_label"] = 1
    selected.loc[serial_idx, "abuse_type"] = "SERIAL_RETURNER"

    pre_serial_capacity = _build_capacity(
        selected.drop(index=serial_idx),
        users,
    )

    serial_users = _allocate_serial_returners(
        rng,
        pre_serial_capacity,
        400,
    )

    selected.loc[serial_idx, "user_id"] = serial_users
    selected.loc[serial_idx, "returned_item_match"] = True
    selected.loc[serial_idx, "item_condition_score"] = np.round(
        rng.uniform(0.65, 0.95, size=400), 3
    )
    selected.loc[serial_idx, "vision_confidence_score"] = np.round(
        rng.uniform(0.70, 0.95, size=400), 3
    )

    # Put serial-return events in the latest 30-day window so
    # return_velocity_30d actually reflects them.
    latest_return = pd.to_datetime(selected["return_requested_at"]).max()

    serial_dates = (
        latest_return
        - pd.to_timedelta(rng.uniform(0, 29 * 24, size=400), unit="h")
    )

    delivery_dates = pd.to_datetime(selected.loc[serial_idx, "delivery_at"])

    serial_dates = pd.Series(
        serial_dates,
        index=selected.loc[serial_idx].index,
    )

    serial_dates = serial_dates.where(
        serial_dates >= delivery_dates,
        delivery_dates + pd.Timedelta(hours=1),
    )

    selected.loc[serial_idx, "return_requested_at"] = serial_dates.values

    selected.loc[serial_idx, "time_to_return_request_hours"] = (
        pd.to_datetime(selected.loc[serial_idx, "return_requested_at"])
        - pd.to_datetime(selected.loc[serial_idx, "ordered_at"])
    ).dt.total_seconds() / 3600.0

    # ==============================================================
    # Final invariants
    # ==============================================================

    selected = selected.reset_index(drop=True)

    if len(selected) != 10_000:
        raise RuntimeError("Final record count invariant failed.")

    abusive = selected["abuse_label"] == 1

    if int(abusive.sum()) != 2_000:
        raise RuntimeError("Abusive record count invariant failed.")

    if int((~abusive).sum()) != 8_000:
        raise RuntimeError("Legitimate record count invariant failed.")

    distribution = (
        selected.loc[abusive, "abuse_type"].value_counts().to_dict()
    )

    for abuse_type in ABUSE_TYPES:
        if distribution.get(abuse_type, 0) != 400:
            raise RuntimeError(f"{abuse_type} distribution failed.")

    users = _reconcile_user_aggregates(selected, users)

    return selected, users