import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import joblib

NUM_FEATURES = [
    "quantity_sold",
    "stock_available",
    "sales_mavg_7d",
    "ratio_sold_stock",
    "price_per_unit",
    "total_sales_value"
]

def fit_scalers(df_model: pd.DataFrame, features=None):
    """
    1.- Crea un scaler por producto.
    2.- Esto evita mezclar productos con rangos distintos.
    """
    if features is None:
        features = NUM_FEATURES

    scalers = {}
    for pid, group in df_model.groupby("product_id"):
        scaler = MinMaxScaler()
        scaler.fit(group[features])
        scalers[pid] = scaler

    return scalers


def save_scalers_and_features(scalers, features=None,
                                path_scalers="models/scalers_lstm_optimo.save",
                                path_features="models/features_lstm_optimo.save"):
    """
    1.- Scalers por producto
	2.- Lista de columnas usadas
    """
    if features is None:
        features = NUM_FEATURES
    joblib.dump(scalers, path_scalers)
    joblib.dump(features, path_features)
    print(f"[OK] Scalers guardados en {path_scalers}")
    print(f"[OK] Features guardadas en {path_features}")