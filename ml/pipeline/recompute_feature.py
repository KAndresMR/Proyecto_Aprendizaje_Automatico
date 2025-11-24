import pandas as pd

def recompute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalcula las features que el modelo necesita.
    Mantiene simple el pipeline.
    """

    df = df.sort_values(["product_id", "date"]).copy()

    # Promedio móvil de ventas (7 días)
    df["sales_mavg_7d"] = (
        df.groupby("product_id")["quantity_sold"]
        .rolling(7, min_periods=1)
        .mean()
        .reset_index(0, drop=True)
    )

    # Ratio de ventas vs stock
    df["ratio_sold_stock"] = df["quantity_sold"] / (df["stock_available"] + 1)

    # Columnas finales que usará el modelo
    final_cols = [
        "product_id",
        "date",
        "quantity_sold",
        "stock_available",
        "sales_mavg_7d",
        "ratio_sold_stock",
        "price_per_unit",
        "total_sales_value"
    ]

    return df[final_cols].copy()