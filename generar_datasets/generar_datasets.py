import pandas as pd
import numpy as np

# ============================================================
# CONFIGURACIÓN
# ============================================================

PRODUCTS = ["P001M", "P002B", "P003N", "P004T", "P005L", "P006Z"]

PRODUCT_NAMES = {
    "P001M": "Manzana Roja",
    "P002B": "Banano Maduro",
    "P003N": "Naranja Dulce",
    "P004T": "Tomate Riñón",
    "P005L": "Lechuga Fresca",
    "P006Z": "Zapallo Andino"
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

# stock mínimo y objetivo por producto (para el modelo de stock tiene MUCHO sentido)
STOCK_MIN = {
    "P001M": 180,
    "P002B": 200,
    "P003N": 160,
    "P004T": 220,
    "P005L": 150,
    "P006Z": 140
}

STOCK_TARGET = {
    "P001M": 500,
    "P002B": 550,
    "P003N": 480,
    "P004T": 580,
    "P005L": 450,
    "P006Z": 430
}

def season_from_month(m):
    if m in [12, 1, 2]:
        return "época lluviosa"
    elif m in [6, 7, 8]:
        return "época seca"
    else:
        return "transición"

def demand_factor(date):
    """Pequeña corrección a la demanda según temporada y festivos."""
    factor = 1.0

    # un poco más de ventas en diciembre
    if date.month == 12:
        factor *= 1.15

    # fines de semana venden un poco más
    if date.weekday() >= 5:  # sábado o domingo
        factor *= 1.10

    return factor

def generate_dataset(start_date, end_date, filename):
    print(f"Generando dataset: {filename}")

    dates = pd.date_range(start_date, end_date, freq="D")
    rows = []

    for pid in PRODUCTS:

        # stock inicial cercano al objetivo
        stock = np.random.randint(STOCK_TARGET[pid] - 80, STOCK_TARGET[pid] + 40)

        price_low, price_high = PRICE_MAP[pid]
        price = np.random.uniform(price_low, price_high)
        product_name = PRODUCT_NAMES[pid]

        for d in dates:
            # ==============================
            # 1) DEMANDA DEL DÍA
            # ==============================
            base_sales = np.random.randint(50, 110)
            noise = np.random.randint(-20, 20)
            demand = max(0, base_sales + noise)

            # ajustar por temporada/fin de semana
            demand = int(demand * demand_factor(d))

            # no se puede vender más de lo que hay
            qty = min(stock, demand)

            # stock tras la venta
            stock_after_sale = stock - qty

            # ==============================
            # 2) REPOSICIÓN (REALISTA)
            # ==============================
            replen = 0

            # reposición fuerte si estamos por debajo del mínimo
            if stock_after_sale < STOCK_MIN[pid]:
                target = STOCK_TARGET[pid]
                faltante = max(0, target - stock_after_sale)
                # reponemos entre 70% y 110% del faltante para dar variabilidad
                replen = np.random.randint(int(faltante * 0.7), int(faltante * 1.1) + 1)

            else:
                # reposición ligera aleatoria algunos días (simula repos semanal)
                if np.random.rand() < 0.20:  # 20% de probabilidad
                    replen = np.random.randint(40, 130)

            # stock final del día
            stock = stock_after_sale + replen

            # ==============================
            # 3) OTRAS VARIABLES
            # ==============================
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

# ============================================================
# GENERAR LOS 4 DATASETS
# ============================================================

generate_dataset("2021-01-01", "2021-12-31", "dataset_2021.csv")
generate_dataset("2022-01-01", "2022-12-31", "dataset_2022.csv")
generate_dataset("2023-01-01", "2023-12-31", "dataset_2023.csv")
generate_dataset("2025-05-01", "2025-11-30", "dataset_2025_mayo_noviembre.csv")