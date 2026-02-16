## 1. Overview

This report documents the data quality assessment performed on the Olist e-commerce dataset. The objective is to evaluate data reliability, identify inconsistencies, and validate critical business metrics before transformation and analysis.

The following quality dimensions were evaluated:

* Null checks
* Duplicate checks
* Revenue validation
* Delivery validation


# 2. Null Checks

A null value assessment was conducted across all analyzed tables.

## Customers

No missing values were detected in any column.
The table is fully complete.

## Orders

Missing values were detected in delivery-related timestamps:

* order_approved_at: 160 missing values (0.16%)
* order_delivered_carrier_date: 1,783 missing values (1.79%)
* order_delivered_customer_date: 2,965 missing values (2.98%)

These missing values are logically consistent with order statuses such as canceled, unavailable, or processing. Therefore, they are considered conditionally valid rather than data errors.

## Order Items

No missing values were detected.
All transactional records contain complete pricing and shipping information.

## Products

Missing values were identified in product attribute fields:

* 610 missing values (1.85%) in:

  * product_category_name
  * product_name_lenght
  * product_description_lenght
  * product_photos_qty

* 2 missing values (0.01%) in:

  * product_weight_g
  * product_length_cm
  * product_height_cm
  * product_width_cm


# 3. Duplicate Checks

Duplicate validation was performed at both primary key and full-row levels.

## Customers

* Duplicate primary keys: 0
* Fully duplicated rows: 0

## Orders

* Duplicate primary keys: 0
* Fully duplicated rows: 0

## Order Items

* Duplicate composite keys (order_id, order_item_id): 0
* Fully duplicated rows: 0

## Products

* Duplicate primary keys: 0
* Fully duplicated rows: 0


# 4. Revenue Validation

Revenue integrity was evaluated using the monetary columns in the Order Items table.

Monetary columns assessed:

* price
* freight_value

## Negative Value Check

* Negative price values: 0
* Negative freight values: 0

No invalid negative monetary values were found.

## Outlier Detection

Statistical outliers were identified:

* 8,427 price outliers
* 12,134 freight outliers

While these values are not invalid, they may distort revenue aggregation and require controlled treatment (e.g., IQR filtering or capping) during transformation.

## Revenue Consistency

Revenue at the order level is derived as:

price + freight_value per item, aggregated by order_id.

The dataset structure supports accurate revenue aggregation since:

* No duplicate composite keys exist
* No missing monetary values are present
* Referential integrity between Orders and Order Items is preserved

# 5. Delivery Validation

Delivery validation was performed to ensure temporal and logical consistency in the Orders table.

## Timeline Consistency

Orders delivered before purchase date: 0

No temporal inconsistencies were detected between purchase and delivery timestamps.

## Missing Delivery Dates

Missing delivery timestamps are aligned with non-delivered order statuses, such as:

* canceled
* unavailable
* processing

This confirms that null delivery values are logically consistent rather than data errors.

## Order Status Distribution

The majority of orders are marked as delivered (96,478 records). A smaller portion represents non-delivered statuses, which explains the presence of missing delivery timestamps.


# 6. Overall Data Quality Assessment

The dataset demonstrates strong structural and transactional integrity:

* No duplicate primary keys
* No fully duplicated rows
* No negative monetary values
* No invalid delivery timelines
* Valid relational cardinality

Identified issues are primarily:

* Missing product attributes
* Missing delivery timestamps (conditionally valid)
* Statistical outliers in price and freight
* Zip code formatting inconsistencies