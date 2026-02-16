import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw")
PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

products = pd.read_csv(RAW_PATH / "olist_products_dataset.csv")

# remove duplicate Primary key
products = products.drop_duplicates(subset="product_id")

# remove invalid weight (weight less than 0)
products = products[products["product_weight_g"] > 0]

# remove all products that have invalid dimensions
products = products[
    (products["product_length_cm"] > 0) &
    (products["product_height_cm"] > 0) &
    (products["product_width_cm"] > 0)
]

# fill missing category with unknown
products["product_category_name"] = (
    products["product_category_name"]
    .fillna("unknown")
)

products.to_csv(PROCESSED_PATH / "products_clean.csv", index=False)

print("Products cleaning completed.")