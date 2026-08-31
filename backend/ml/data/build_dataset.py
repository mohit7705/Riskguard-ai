from pathlib import Path

import numpy as np

from backend.ml.data.generators.user_generator import generate_users
from backend.ml.data.generators.order_generator import generate_orders
from backend.ml.data.generators.item_generator import generate_order_items
from backend.ml.data.generators.return_generator import generate_baseline_returns
from backend.ml.data.generators.abuse_injector import inject_abuse
from backend.ml.data.features.aggregations import calculate_all_user_features
from backend.ml.data.validators.dataset_validator import validate_dataset


SEED = 42
USER_COUNT = 2_000
TARGET_RETURN_RECORDS = 10_000

DATA_ROOT = Path("data")

RAW_DIR = DATA_ROOT / "raw"
PROCESSED_DIR = DATA_ROOT / "processed"


def main() -> None:
    print("=" * 60)
    print("RiskGuard AI — Dataset Builder")
    print("=" * 60)

    # ------------------------------------------------------------
    # 1. Create output directories
    # ------------------------------------------------------------

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/7] Output directories ready.")

    # ------------------------------------------------------------
    # 2. Deterministic random generator
    # ------------------------------------------------------------

    rng = np.random.default_rng(SEED)

    print(f"[2/7] Random seed: {SEED}")

    # ------------------------------------------------------------
    # 3. Generate base data
    # ------------------------------------------------------------

    print("[3/7] Generating users...")

    users = generate_users(
        rng,
        USER_COUNT,
    )

    print(f"       Users: {len(users):,}")

    print("[3/7] Generating orders...")

    orders = generate_orders(
        rng,
        users,
    )

    print(f"       Orders: {len(orders):,}")

    print("[3/7] Generating order items...")

    items = generate_order_items(
        rng,
        orders,
    )

    print(f"       Order items: {len(items):,}")

    print("[3/7] Generating baseline returns...")

    returns = generate_baseline_returns(
        rng,
        users,
        orders,
        items,
    )

    print(f"       Baseline returns: {len(returns):,}")

    # ------------------------------------------------------------
    # 4. Inject controlled abuse ground truth
    # ------------------------------------------------------------

    print("[4/7] Injecting abuse ground truth...")

    final_returns, updated_users = inject_abuse(
        rng,
        returns,
        users,
        TARGET_RETURN_RECORDS,
    )

    print(f"       Final return records: {len(final_returns):,}")

    # ------------------------------------------------------------
    # 5. Calculate ML features
    # ------------------------------------------------------------

    print("[5/7] Calculating user features...")

    features = calculate_all_user_features(
        final_returns,
        updated_users,
    )

    print(f"       Feature rows: {len(features):,}")
    print(f"       Feature columns: {len(features.columns):,}")

    # ------------------------------------------------------------
    # 6. Validate the complete dataset
    # ------------------------------------------------------------

    print("[6/7] Validating dataset...")

    validate_dataset(
        final_returns,
        features,
    )

    print("       Dataset validation: PASSED")

    # ------------------------------------------------------------
    # 7. Persist datasets
    # ------------------------------------------------------------

    print("[7/7] Saving datasets...")

    users_path = RAW_DIR / "users.parquet"
    orders_path = RAW_DIR / "orders.parquet"
    items_path = RAW_DIR / "order_items.parquet"
    returns_path = RAW_DIR / "returns.parquet"
    features_path = PROCESSED_DIR / "user_features.parquet"

    updated_users.to_parquet(
        users_path,
        index=False,
    )

    orders.to_parquet(
        orders_path,
        index=False,
    )

    items.to_parquet(
        items_path,
        index=False,
    )

    final_returns.to_parquet(
        returns_path,
        index=False,
    )

    features.to_parquet(
        features_path,
        index=False,
    )

    print()
    print("=" * 60)
    print("DATASET BUILD COMPLETE")
    print("=" * 60)

    print(f"Users:         {users_path}")
    print(f"Orders:        {orders_path}")
    print(f"Order items:   {items_path}")
    print(f"Returns:       {returns_path}")
    print(f"Features:      {features_path}")

    print()
    print("Final dataset:")
    print(f"  Records:     {len(final_returns):,}")
    print(
        f"  Legitimate:  "
        f"{int((final_returns['abuse_label'] == 0).sum()):,}"
    )
    print(
        f"  Abusive:     "
        f"{int((final_returns['abuse_label'] == 1).sum()):,}"
    )

    print()
    print("Abuse distribution:")

    distribution = (
        final_returns["abuse_type"]
        .value_counts(dropna=False)
    )

    print(distribution.to_string())

    print()
    print("Feature dataset:")
    print(f"  Rows:         {len(features):,}")
    print(f"  Columns:      {len(features.columns):,}")
    print(
        f"  NULL values:  "
        f"{int(features.isna().sum().sum()):,}"
    )

    print()
    print("STEP 4: COMPLETE")


if __name__ == "__main__":
    main()