from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.ml.data.config import ORDER_CATEGORIES


def generate_orders(
    rng: np.random.Generator,
    users: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate synthetic orders from existing users.

    Guarantees:
        account_created_at <= ordered_at
        exactly one chronological first order per user
    """

    if users.empty:
        raise ValueError("users dataframe cannot be empty")

    records = []

    for user in users.itertuples(index=False):
        order_count = int(user.lifetime_order_count)

        if order_count <= 0:
            raise ValueError(
                f"Invalid order count for {user.user_id}"
            )

        for _ in range(order_count):
            order_age_days = int(
                rng.integers(
                    low=0,
                    high=max(1, user.account_age_days + 1),
                )
            )

            ordered_at = user.account_created_at + timedelta(
                days=order_age_days,
                hours=int(rng.integers(0, 24)),
                minutes=int(rng.integers(0, 60)),
            )

            category = str(
                rng.choice(ORDER_CATEGORIES)
            )

            order_value = float(
                np.round(
                    np.maximum(
                        rng.lognormal(
                            mean=np.log(180),
                            sigma=0.75,
                        ),
                        20.0,
                    ),
                    2,
                )
            )

            records.append(
                {
                    "order_id": f"O{len(records) + 1:08d}",
                    "user_id": user.user_id,
                    "ordered_at": ordered_at,
                    "order_category": category,
                    "order_value": order_value,
                }
            )

    orders = pd.DataFrame(records)

    orders["ordered_at"] = pd.to_datetime(
        orders["ordered_at"]
    )

    # Chronological ordering within each user.
    orders = orders.sort_values(
        ["user_id", "ordered_at", "order_id"]
    ).reset_index(drop=True)

    # Assign chronological order number.
    orders["order_number"] = (
        orders.groupby("user_id").cumcount() + 1
    )

    # Exactly one actual first order per user.
    orders["is_first_order"] = (
        orders["order_number"] == 1
    )

    return orders