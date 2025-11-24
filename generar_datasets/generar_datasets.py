import pandas as pd
import numpy as np

PRODUCTS = ["P001M", "P002B", "P003N", "P004T", "P005L", "P006Z"]

PRODUCT_NAMES = {
    "P001M": "Manzana Roja",
    "P002B": "Banano",
    "P003N": "Naranja",
    "P004T": "Tomate Riñón",
    "P005L": "Lechuga",
    "P006Z": "Zanahoria"
}

COLUMNS = [
    "product_id", "date", "product_name",
    "quantity_sold", "stock_available", "replenishment",
    "price_per_unit", "total_sales_value",
    "season", "holiday", "demand_status"
]

PRICE_MAP = {
    "P001M": (0.80, 1.20),
    "P002B": (1.50, 2.50),
    "P003N": (0.50, 1.00),
    "P004T": (2.00, 3.20),
    "P005L": (1.00, 2.00),
    "P006Z": (0.40, 0.90),
}

STOCK_MIN = {
    "P001M": 180, "P002B": 200, "P003N": 160,
    "P004T": 220, "P005L": 150, "P006Z": 140
}

STOCK_TARGET = {
    "P001M": 500, "P002B": 550, "P003N": 480,
    "P004T": 580, "P005L": 450, "P006Z": 430
}

def season_from_month(m):
    if m in [12, 1, 2]:
        return "lluvioso"
    elif m in [6, 7, 8]:
        return "seca"
    else:
        return "templado"   # <-- corrección importante

def demand_factor(date):
    factor = 1.0
    if date.month == 12:
        factor *= 1.15
    if date.weekday() >= 5:
        factor *= 1.10
    return factor

def generate_dataset(start_date, end_date, filename):
    print(f"Generando dataset: {filename}")
    dates = pd.date_range(start_date, end_date, freq="D")
    rows = []

    for pid in PRODUCTS:
        stock = np.random.randint(STOCK_TARGET[pid] - 80, STOCK_TARGET[pid] + 40)
        price_low, price_high = PRICE_MAP[pid]
        price = np.random.uniform(price_low, price_high)
        product_name = PRODUCT_NAMES[pid]

        for d in dates:
            base_sales = np.random.randint(50, 110)
            noise = np.random.randint(-20, 20)
            demand = max(0, base_sales + noise)
            demand = int(demand * demand_factor(d))

            qty = min(stock, demand)
            stock_after_sale = stock - qty

            replen = 0
            if stock_after_sale < STOCK_MIN[pid]:
                target = STOCK_TARGET[pid]
                faltante = max(0, target - stock_after_sale)
                replen = np.random.randint(int(faltante * 0.7), int(faltante * 1.1) + 1)
            else:
                if np.random.rand() < 0.20:
                    replen = np.random.randint(40, 130)

            stock = stock_after_sale + replen
            total_value = qty * price
            holiday = True if d.month == 12 and d.day in (24, 25, 31) else False

            if qty > 100:
                status = "alto"
            elif qty >= 60:
                status = "normal"
            else:
                status = "bajo"

            rows.append([
                pid,
                d.strftime("%Y-%m-%d"),
                product_name,
                qty,
                stock,
                replen,
                round(price, 2),
                round(total_value, 2),
                season_from_month(d.month),
                holiday,
                status
            ])

    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(filename, index=False)
    print(f"✔ Dataset creado: {filename}\n")

# ===============================
# GENERACIÓN CORRECTA
# ===============================

generate_dataset("2021-01-01", "2021-12-31", "dataset_2021.csv")
generate_dataset("2022-01-01", "2022-12-31", "dataset_2022.csv")
generate_dataset("2023-01-01", "2023-12-31", "dataset_2023.csv")
generate_dataset("2024-01-01", "2024-12-31", "dataset_2024.csv")
