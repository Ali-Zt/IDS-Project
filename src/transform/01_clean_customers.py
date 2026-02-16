import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw")
PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

customers = pd.read_csv(RAW_PATH / "olist_customers_dataset.csv")

# ensure primary key being unique
customers = customers.drop_duplicates(subset="customer_id")

# standardize city names
customers["customer_city"] = customers["customer_city"].str.strip().str.title()

# fix zip code for it to become 5 digits ( which is the strandared zip code length in brazil )
customers["customer_zip_code_prefix"] = (
    customers["customer_zip_code_prefix"]
    .astype(str)
    .str.zfill(5)
)

customers.to_csv(PROCESSED_PATH / "customers_clean.csv", index=False)

print("Customers cleaning completed.")
