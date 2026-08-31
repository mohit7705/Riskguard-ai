import numpy as np
import pandas as pd


def generate_order_items(
    rng: np.random.Generator,
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate 1–3 line items for every order.

    The sum of item values for each order equals order_value.
    """

    if orders.empty:
        raise ValueError("orders dataframe cannot be empty")

    records = []

    for order in orders.itertuples(index=False):
        item_count = int(rng.integers(1, 4))

        if item_count == 1:
            values = [float(order.order_value)]
        else:
            weights = rng.dirichlet(
                np.ones(item_count)
            )

            values = [
                round(
                    float(order.order_value) * float(weight),
                    2,
                )
                for weight in weights[:-1]
            ]

            final_value = round(
                float(order.order_value)
                - sum(values),
                2,
            )

            values.append(final_value)

        for item_number, item_value in enumerate(values, start=1):
            records.append(
                {
                    "order_item_id": (
                        f"OI{len(records) + 1:09d}"
                    ),
                    "order_id": order.order_id,
                    "product_id": (
                        f"P{rng.integers(1, 5001):06d}"
                    ),
                    "product_category": order.order_category,
                    "item_value": item_value,
                    "quantity": 1,
                    "item_number": item_number,
                }
            )

    items = pd.DataFrame(records)

    return items