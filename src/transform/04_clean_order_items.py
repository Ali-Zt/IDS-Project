import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw")
PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

order_items = pd.read_csv(RAW_PATH / "olist_order_items_dataset.csv")

# remove duplicate composite key ( two unique keys together)
order_items = order_items.drop_duplicates(
    subset=["order_id", "order_item_id"]
)

# ensure money values are positive
order_items = order_items[
    (order_items["price"] >= 0) &
    (order_items["freight_value"] >= 0)
]

# convert shipping date
order_items["shipping_limit_date"] = pd.to_datetime(
    order_items["shipping_limit_date"],
    errors="coerce"
)

# create revenue column
order_items["revenue"] = (
    order_items["price"] + order_items["freight_value"]
)

order_items.to_csv(PROCESSED_PATH / "order_items_clean.csv", index=False)

print("Order Items cleaning completed.")
