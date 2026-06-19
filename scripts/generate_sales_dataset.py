"""Generate a full-fledged, realistic restaurant sales dataset for forecasting.

Creates a 180-day historical dataset for 5 distinct menu items with
weekly seasonality, linear trends, and random noise.
Outputs the dataset to tests/data/kaggle_restaurant_sales.csv.
"""

import os
import csv
import random
from datetime import datetime, timedelta

# Settings
DAYS = 180
TENANT_ID = 1
START_DATE = datetime.now() - timedelta(days=DAYS)

MENU_ITEMS = [
    {"item_id": 1, "name": "Butter Chicken", "avg_qty": 15, "unit_price": 380.0},
    {"item_id": 2, "name": "Paneer Tikka", "avg_qty": 20, "unit_price": 290.0},
    {"item_id": 3, "name": "Garlic Naan", "avg_qty": 45, "unit_price": 60.0},
    {"item_id": 4, "name": "Mango Lassi", "avg_qty": 25, "unit_price": 120.0},
    {"item_id": 5, "name": "Gulab Jamun", "avg_qty": 18, "unit_price": 90.0},
]


def generate_dataset():
    # Target path
    output_dir = os.path.join("tests", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "kaggle_restaurant_sales.csv")

    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Header
        writer.writerow(["date", "item_id", "item_name", "quantity", "unit_price", "tenant_id"])

        for day_offset in range(DAYS):
            current_date = START_DATE + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")
            day_of_week = current_date.weekday()  # 0: Monday, 6: Sunday

            # Seasonality: weekends (Fri/Sat/Sun) have higher volume
            if day_of_week in [4, 5]:  # Fri, Sat
                seasonality_multiplier = 1.4
            elif day_of_week == 6:  # Sun
                seasonality_multiplier = 1.2
            else:  # Mon-Thu
                seasonality_multiplier = 0.9

            # Trend: slight positive trend over the 6 months (up to 15% increase)
            trend_multiplier = 1.0 + (day_offset / DAYS) * 0.15

            for item in MENU_ITEMS:
                # Add random fluctuation to quantity
                base_qty = item["avg_qty"] * seasonality_multiplier * trend_multiplier
                quantity = int(max(1, round(random.gauss(base_qty, base_qty * 0.15))))

                writer.writerow([
                    date_str,
                    item["item_id"],
                    item["name"],
                    quantity,
                    item["unit_price"],
                    TENANT_ID
                ])

    print(f"Successfully generated full-fledged sales dataset at: {output_file}")


if __name__ == "__main__":
    generate_dataset()
