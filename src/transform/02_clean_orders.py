import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw")
PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

orders = pd.read_csv(RAW_PATH / "olist_orders_dataset.csv")

# remove duplicate Primary key
orders = orders.drop_duplicates(subset="order_id")

# convert to datetime
date_columns = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

for col in date_columns:
    orders[col] = pd.to_datetime(orders[col], errors="coerce")

# make sure no delivery before purchase
orders = orders[
    (orders["order_delivered_customer_date"].isna()) |
    (orders["order_delivered_customer_date"] >= orders["order_purchase_timestamp"])
]

orders.to_csv(PROCESSED_PATH / "orders_clean.csv", index=False)

print("Orders cleaning completed.")
