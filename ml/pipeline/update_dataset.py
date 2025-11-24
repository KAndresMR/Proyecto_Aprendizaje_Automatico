import pandas as pd
from .train_model import retrain_model
from .recompute_feature import recompute_features

def simple_update_pipeline(base_path, df_new, final_path, model_path):
    df_base = pd.read_csv(base_path, parse_dates=["date"])

    if df_new.empty:
        raise ValueError("Dataset nuevo está vacío")

    # Crear llaves
    df_base["_key"] = df_base["product_id"].astype(str) + "_" + df_base["date"].astype(str)
    df_new["_key"]  = df_new["product_id"].astype(str)  + "_" + df_new["date"].astype(str)

    # Filtrar solo nuevos
    df_new_filtered = df_new[~df_new["_key"].isin(df_base["_key"])]

    # Limpieza
    df_base.drop(columns=["_key"], inplace=True)
    df_new_filtered.drop(columns=["_key"], inplace=True)

    if df_new_filtered.empty:
        return {"rows_added": 0, "msg": "No había registros nuevos"}

    # Merge bien hecho
    df_all = pd.concat([df_base, df_new_filtered], ignore_index=True)
    df_all = df_all.sort_values(["product_id", "date"])

    # Guardar base actualizada
    df_all.to_csv(base_path, index=False)

    # Recalcular features
    df_model = recompute_features(df_all)
    df_model.to_csv(final_path, index=False)

    # Reentrenar (ligero)
    retrain_model("models/modelo_lstm_optimo.h5", df_model)

    return {"rows_added": len(df_new_filtered)}