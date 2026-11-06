# Sales CSV imports

`POST /api/v1/data/upload-sales` accepts manager/owner uploads up to 5 MiB
and 10,000 data rows. CSV must use UTF-8 (a BOM is accepted), unique headers,
and consistent column counts. Binary, malformed and empty files are rejected.

Required columns: `order_id`, `date`, `item_name`, `quantity`, `unit_price`,
`total_amount`, `payment_method`, `tax_amount`. `customer_id` is optional and
must belong to the authenticated tenant. Legacy CSVs need the new columns.
Use a stable source order identifier; retain it on retries.

```csv
order_id,date,item_name,quantity,unit_price,total_amount,payment_method,tax_amount,customer_id
POS-1042,2026-10-23,Masala dosa,2,100.00,250.00,upi,12.50,
POS-1042,2026-10-23,Filter coffee,1,50.00,250.00,upi,12.50,
```

Names must match existing tenant menu items, case-insensitively. Dates mean
UTC; supported formats include `YYYY-MM-DD` and `YYYY-MM-DD HH:MM:SS`.
Quantities are 1–1,000; orders have at most 100 lines. Amounts are INR with at
most two decimal places, bounded by 99,999,999.99. `total_amount` is the order
subtotal before tax and must equal the sum of line prices times quantities.
Repeat the subtotal and order tax on each row. Tax is between zero and the
subtotal. Payment methods: `cash`, `card`, `digital_wallet`, `upi`, `bank_transfer`.

Rows sharing an order ID must have identical date, customer, subtotal, tax
and payment method. One invalid row rejects its whole order; other valid
orders can still be imported. Errors include data row numbers. The response
reports `rows_inserted` (orders), `items_matched` (lines), `orders_skipped`
and `validation_errors`.

Tenant-scoped receipts store order IDs and SHA-256 hashes of normalized
content. Exact retries, including reordered lines, skip existing orders.
Changed content under an existing ID is rejected. Database uniqueness also
protects concurrent workers. Sales, lines and receipts are written together.
The existing startup schema initialization creates the new `imported_orders`
table; restart the API before using this importer. Older imports have no
receipts, so identify already-imported orders before reuploading legacy exports.

For checkout JSON, `tax_rate` is a fraction in `[0, 1]`: `0.05` means 5%.
