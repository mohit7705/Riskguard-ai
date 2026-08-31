from datetime import timedelta

import numpy as np
import pandas as pd


def generate_baseline_returns(
    rng: np.random.Generator,
    users: pd.DataFrame,
    orders: pd.DataFrame,
    items: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate baseline consumer return behavior.

    Abuse labels and abuse types are intentionally NOT assigned here.
    """

    if users.empty:
        raise ValueError("users dataframe cannot be empty")

    if orders.empty:
        raise ValueError("orders dataframe cannot be empty")

    if items.empty:
        raise ValueError("items dataframe cannot be empty")

    user_lookup = users.set_index("user_id")

    records = []

    for order in orders.itertuples(index=False):
        user = user_lookup.loc[order.user_id]

        # Baseline return probability.
        return_probability = float(
            rng.uniform(0.05, 0.25)
        )

        if rng.random() > return_probability:
            continue

        order_items = items[
            items["order_id"] == order.order_id
        ]

        selected_item = order_items.sample(
            n=1,
            random_state=int(rng.integers(0, 2**32 - 1)),
        ).iloc[0]

        time_to_return_hours = float(
            rng.uniform(48, 720)
        )

        delivery_at = (
            order.ordered_at
            + timedelta(
                days=int(rng.integers(1, 8))
            )
        )

        return_requested_at = (
            delivery_at
            + timedelta(
                hours=time_to_return_hours
            )
        )

        refund_amount = round(
            float(
                rng.uniform(
                    0.85,
                    1.0,
                )
                * selected_item.item_value
                * selected_item.quantity
            ),
            2,
        )

        records.append(
            {
                "return_id": f"R{len(records) + 1:08d}",
                "order_id": order.order_id,
                "user_id": order.user_id,
                "order_category": order.order_category,
                "order_value": order.order_value,
                "product_id": selected_item.product_id,
                "product_category": selected_item.product_category,
                "item_value": selected_item.item_value,
                "quantity": selected_item.quantity,
                "ordered_at": order.ordered_at,
                "delivery_at": delivery_at,
                "return_requested_at": return_requested_at,
                "time_to_return_request_hours": round(
                    time_to_return_hours,
                    2,
                ),
                "refund_amount": refund_amount,
                "return_reason": str(
                    rng.choice(
                        [
                            "Changed mind",
                            "Wrong size",
                            "Not as expected",
                        ]
                    )
                ),
                "returned_item_match": True,
                # ~12% of legitimate returns are a genuinely worn/used
                # item (tried on, kept a while) that still isn't abuse —
                # this creates real overlap with WARDROBING's validator
                # boundary (<0.60) instead of a clean, unrealistic gap.
                "item_condition_score": (
                    float(rng.uniform(0.45, 0.79))
                    if rng.random() < 0.12
                    else float(rng.uniform(0.78, 1.00))
                ),
                "package_weight_delta_pct": float(
                    rng.uniform(0, 15)
                ),
                # ~6% of legitimate returns get a lower vision-match
                # confidence (poor photo, packaging obstruction) without
                # being an actual swap — overlaps ITEM_SWAP's validator
                # boundary (<0.40) instead of a clean gap.
                "vision_confidence_score": (
                    float(rng.uniform(0.30, 0.60))
                    if rng.random() < 0.06
                    else float(rng.uniform(0.82, 1.00))
                ),
                "abuse_label": 0,
                "abuse_type": None,
            }
        )

    returns = pd.DataFrame(records)

    if returns.empty:
        raise RuntimeError(
            "Baseline return generator produced zero returns."
        )

    return returns