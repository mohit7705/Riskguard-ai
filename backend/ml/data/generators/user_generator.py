from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generate_users(
    rng: np.random.Generator,
    num_users: int,
    start_date: datetime = datetime(2023, 1, 1),
) -> pd.DataFrame:
    """
    Generate synthetic user/account records.

    The function only creates account-level attributes.
    Behavioral and abuse features are calculated later.
    """

    if num_users <= 0:
        raise ValueError("num_users must be greater than 0")

    user_ids = [f"U{i:06d}" for i in range(1, num_users + 1)]

    # Create a controlled population of fresh accounts. These accounts are
    # required for the SUSPICIOUS_ACCOUNT_BEHAVIOR ground-truth class.
    fresh_account_count = max(
        500,
        int(num_users * 0.10),
    )
    fresh_account_count = min(
        fresh_account_count,
        num_users,
    )

    fresh_indices = set(
        rng.choice(
            num_users,
            size=fresh_account_count,
            replace=False,
        )
    )

    account_age_days = np.empty(num_users, dtype=int)
    for index in range(num_users):
        if index in fresh_indices:
            account_age_days[index] = int(rng.integers(0, 8))
        else:
            account_age_days[index] = int(rng.integers(30, 1500))

    account_created_at = [
        start_date - timedelta(days=int(age))
        for age in account_age_days
    ]

    device_ids = [
        f"DEV-{rng.integers(1, num_users + 1):06d}"
        for _ in range(num_users)
    ]

    address_ids = [
        f"ADDR-{rng.integers(1, max(2, num_users // 2) + 1):06d}"
        for _ in range(num_users)
    ]

    payment_ids = [
        f"PAY-{rng.integers(1, num_users + 1):06d}"
        for _ in range(num_users)
    ]

    lifetime_order_count = rng.integers(
        low=1,
        high=101,
        size=num_users,
    )

    total_spent = np.round(
        rng.lognormal(
            mean=np.log(350),
            sigma=0.8,
            size=num_users,
        ),
        2,
    )

    total_spent = np.maximum(total_spent, 20.0)

    users = pd.DataFrame(
        {
            "user_id": user_ids,
            "account_created_at": account_created_at,
            "account_age_days": account_age_days,
            "device_fingerprint": device_ids,
            "address_hash": address_ids,
            "payment_fingerprint": payment_ids,
            "lifetime_order_count": lifetime_order_count,
            "lifetime_return_count": np.zeros(num_users, dtype=int),
            "total_spent": total_spent,
        }
    )

    return users
