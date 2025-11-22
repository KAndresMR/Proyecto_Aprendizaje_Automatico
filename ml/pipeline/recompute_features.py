import pandas as pd

def recompute_features(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    1.- Ordena el dataset
	2.- Calcula promedio móvil
	3.- Calcula ratio sold/stock
	4.- Selecciona columnas correctas
    """
    df = df_all.sort_values(["product_id", "date"]).copy()

    # Promedio móvil 7 días por producto
    df["sales_mavg_7d"] = (
        df.groupby("product_id")["quantity_sold"]
            .rolling(7, min_periods=1)
            .mean()
            .reset_index(0, drop=True)
    )

    # Ratio ventas / stock
    df["ratio_sold_stock"] = df["quantity_sold"] / (df["stock_available"] + 1)

    # Dataset final con columnas que ya usas en el modelo
    selected_features = [
        "product_id",
        "date",
        "quantity_sold",
        "stock_available",
        "sales_mavg_7d",
        "ratio_sold_stock",
        "price_per_unit",
        "total_sales_value"
    ]

    df_model = df[selected_features].copy()
    df_model = df_model.sort_values(["product_id", "date"]).reset_index(drop=True)
    return df_model