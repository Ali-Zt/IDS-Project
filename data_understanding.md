
## 1. Overview

This document presents the structural analysis and profiling results of the Olist e-commerce dataset. The analysis focuses on the following tables:

* Customers
* Orders
* Order Items
* Products

The objective of this phase is to identify:

* Primary keys
* Table relationships
* Missing values
* Data quality issues
* Structural consistency


# 2. Customers Table

## Structure

The Customers table contains 99,441 rows and 5 columns.
The primary key is `customer_id`.

No duplicate primary keys were detected.
No fully duplicated rows were identified.

The table includes the following columns:

* customer_id (string)
* customer_unique_id (string)
* customer_zip_code_prefix (int64)
* customer_city (string)
* customer_state (string)

## Missing Values

No missing values were detected in any column.

## Data Issues Identified

Zip Code Formatting:
The `customer_zip_code_prefix` column is stored as an integer. Analysis shows that 75,446 records contain 5-digit zip codes, while 23,995 records contain 4-digit zip codes. Since Brazilian ZIP codes should contain 5 digits, the 4-digit values likely lost a leading zero due to numeric formatting.

Customer Uniqueness:
There are 96,096 unique values in `customer_unique_id`, while the table contains 99,441 rows. This indicates that some customers placed multiple orders, which is expected behavior.

## Relationships

The `customer_id` column links to the Orders table.
The relationship between Customers and Orders is one-to-many, meaning one customer can place multiple orders.

Cardinality validation confirms that each customer appears only once in the Customers table.

---

# 3. Orders Table

## Structure

The Orders table contains 99,441 rows and 8 columns.
The primary key is `order_id`.

No duplicate primary keys were detected.
No fully duplicated rows were identified.

The table includes the following columns:

* order_id (string)
* customer_id (string)
* order_status (string)
* order_purchase_timestamp (datetime)
* order_approved_at (datetime)
* order_delivered_carrier_date (datetime)
* order_delivered_customer_date (datetime)
* order_estimated_delivery_date (datetime)

## Missing Values

Missing values were identified in delivery-related columns:

* order_approved_at: 160 missing values (0.16%)
* order_delivered_carrier_date: 1,783 missing values (1.79%)
* order_delivered_customer_date: 2,965 missing values (2.98%)

These missing values are logically associated with orders that were canceled, unavailable, or not yet delivered.

## Data Issues Identified

Timeline Validation:
No cases were found where an order was delivered before it was purchased. This confirms temporal consistency.

Order Status Distribution:
The majority of orders (96,478) are marked as delivered. A smaller proportion of orders are shipped, canceled, unavailable, invoiced, processing, created, or approved. These categories explain the presence of missing delivery timestamps.

## Relationships

The `customer_id` column links to the Customers table (many-to-one relationship).
The `order_id` column links to the Order Items table (one-to-many relationship).

Cardinality validation shows that 9,803 orders contain more than one item. The maximum number of items in a single order is 21, and the average number of items per order is 1.14.

---

# 4. Order Items Table

## Structure

The Order Items table contains 112,650 rows and 7 columns.
It uses a composite primary key consisting of `order_id` and `order_item_id`.

No duplicate composite keys were detected.
No fully duplicated rows were identified.

The table includes the following columns:

* order_id (string)
* order_item_id (integer)
* product_id (string)
* seller_id (string)
* shipping_limit_date (string)
* price (float)
* freight_value (float)

## Missing Values

No missing values were detected in this table.

## Data Issues Identified

Outliers:
Although no negative price or freight values were found, statistical analysis identified 8,427 price outliers and 12,134 freight outliers. These extreme values may affect revenue analysis and require treatment during data transformation.

Data Type Issue:
The `shipping_limit_date` column is stored as a string instead of a datetime type. This requires conversion to enable proper time-based analysis.

## Relationships

The `order_id` column links to the Orders table (many-to-one).
The `product_id` column links to the Products table (many-to-one).
The `seller_id` column links to the Sellers table.

Cardinality validation shows that 14,834 products appear in more than one order. The maximum number of times a single product appears is 527, with an average repetition of 3.42.

---

# 5. Products Table

## Structure

The Products table contains 32,951 rows and 9 columns.
The primary key is `product_id`.

No duplicate primary keys were detected.
No fully duplicated rows were identified.

The table includes the following columns:

* product_id (string)
* product_category_name (string)
* product_name_lenght (float)
* product_description_lenght (float)
* product_photos_qty (float)
* product_weight_g (float)
* product_length_cm (float)
* product_height_cm (float)
* product_width_cm (float)

## Missing Values

Missing values were identified in the following columns:

* product_category_name: 610 missing values (1.85%)
* product_name_lenght: 610 missing values (1.85%)
* product_description_lenght: 610 missing values (1.85%)
* product_photos_qty: 610 missing values (1.85%)
* product_weight_g: 2 missing values (0.01%)
* product_length_cm: 2 missing values (0.01%)
* product_height_cm: 2 missing values (0.01%)
* product_width_cm: 2 missing values (0.01%)

## Data Issues Identified

Missing Product Categories:
Approximately 1.85% of products do not have a category assigned. These records require imputation or classification as "unknown" during cleaning.

Zero or Negative Product Weight:
Four records contain zero or negative weight values, which are physically invalid and must be corrected or removed.

Numeric Columns Stored as Float:
Several numeric columns are stored as float due to the presence of missing values. After cleaning, appropriate numeric types can be enforced.

## Relationships

The `product_id` column links to the Order Items table.
The relationship between Products and Order Items is one-to-many.


# 6. Overall Data Model

The dataset follows a transactional e-commerce relational structure centered around the Orders table.

The core relationships are:

Customers → Orders → Order Items → Products

Additional supporting tables in the full schema include:

* Payments (linked by order_id)
* Reviews (linked by order_id)
* Sellers (linked by seller_id)
* Geolocation (linked by zip_code_prefix)

The Orders table functions as the central fact table, connecting customers, products, sellers, and transactional information.


# 7. Summary of Data Quality Findings

The dataset demonstrates strong structural integrity:

* No duplicate primary keys
* No fully duplicated rows
* Valid relational cardinality
* No temporal inconsistencies

The primary issues identified include:

* Inconsistent zip code formatting
* Missing delivery timestamps
* Statistical outliers in price and freight
* Missing product category information
* A small number of invalid product weights