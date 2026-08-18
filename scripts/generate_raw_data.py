# Generates the raw shipment data for the Bertus delivery performance exercise.
# All data is synthetic, modeled on Bertus's real business (physical media wholesale:
# vinyl/CD/DVD/merch, NL carriers, independent stores/retail chains/online retailers).
# Deliberately kept "raw": dates are plain strings, delay/on-time/month are NOT
# precomputed, so the notebook has real cleaning and feature engineering to do.
import csv
import random
from datetime import date, timedelta

random.seed(42)

CUSTOMER_TYPES = ['Independent Store', 'Retail Chain', 'Online Retailer']
COUNTRIES = ['Netherlands', 'Germany', 'Belgium', 'France', 'United Kingdom', 'United States']
PRODUCTS = ['Vinyl', 'CD', 'DVD', 'Merchandise']
CARRIERS = ['PostNL', 'DHL', 'DPD', 'GLS', 'UPS']
DELAY_REASONS = ['Carrier delay', 'Customs hold', 'Stock shortage', 'Documentation error', 'Weather']

START_DATE = date(2026, 4, 1)
ROW_COUNT = 140


def add_days(d, days):
    return d + timedelta(days=days)


def main():
    rows = []
    for i in range(1, ROW_COUNT + 1):
        order_date = add_days(START_DATE, random.randint(0, 134))
        lead_time = random.randint(3, 10)
        promised = add_days(order_date, lead_time)
        is_late = random.random() < 0.28
        if is_late:
            actual = add_days(promised, random.randint(1, 9))
            delay_reason = random.choice(DELAY_REASONS)
        else:
            actual = add_days(promised, -random.randint(0, 1))
            delay_reason = ''
        rows.append({
            'shipment_id': f'SH{i:04d}',
            'order_date': order_date.isoformat(),
            'customer_type': random.choice(CUSTOMER_TYPES),
            'destination_country': random.choice(COUNTRIES),
            'product_category': random.choice(PRODUCTS),
            'carrier': random.choice(CARRIERS),
            'promised_delivery_date': promised.isoformat(),
            'actual_delivery_date': actual.isoformat(),
            'delay_reason': delay_reason,
            'order_value_eur': random.randint(45, 1800),
        })

    out_path = 'bertus_shipments_raw.csv'
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f'Written: {out_path} ({len(rows)} rows)')


if __name__ == '__main__':
    main()
