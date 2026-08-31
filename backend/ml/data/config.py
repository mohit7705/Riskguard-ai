from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetConfig:
    # Reproducibility
    seed: int = 42

    # Dataset size
    total_records: int = 10_000

    # Class distribution
    legitimate_records: int = 8_000
    abusive_records: int = 2_000

    # Abuse distribution
    wardrobing_records: int = 400
    serial_returner_records: int = 400
    item_swap_records: int = 400
    abuse_ring_records: int = 400
    suspicious_account_records: int = 400

    # Output
    csv_filename: str = "synthetic_returns.csv"
    parquet_filename: str = "synthetic_returns.parquet"

    # Abuse-ring cluster size
    abuse_ring_min_cluster_size: int = 3
    abuse_ring_max_cluster_size: int = 5

    # Controlled overlap
    legitimate_high_value_probability: float = 0.05
    abusive_low_value_probability: float = 0.05


CONFIG = DatasetConfig()


ABUSE_TYPES = (
    "WARDROBING",
    "SERIAL_RETURNER",
    "ITEM_SWAP_OR_EMPTY_BOX",
    "ABUSE_RING",
    "SUSPICIOUS_ACCOUNT_BEHAVIOR",
)


ORDER_CATEGORIES = (
    "Apparel",
    "Electronics",
    "Luxury",
    "Home",
    "Beauty",
    "Sports",
    "Books",
    "Other",
)


RETURN_REASONS = (
    "Changed mind",
    "Wrong size",
    "Wrong item",
    "Damaged",
    "Not as expected",
    "Defective",
    "Other",
)
