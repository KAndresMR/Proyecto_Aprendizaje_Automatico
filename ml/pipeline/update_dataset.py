import logging
import os
import pandas as pd
import numpy as np
import math

from app.storage import download_file, upload_file
from keras import models
from sklearn.metrics import mean_squared_error
from .incremental_model import incremental_train
from .recompute_features import recompute_features
from .scaling import fit_scalers, save_scalers_and_features, NUM_FEATURES

# ---------------------------
# LOGGING PROFESIONAL
# ---------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Cargar la base de datos principal
def load_base_dataset(path_base: str = "../dataset.csv") -> pd.DataFrame:
    df = pd.read_csv(path_base, parse_dates=["date"])
    df = df.sort_values(["product_id", "date"]).reset_index(drop=True)
    return df

# Carga el dataset de nuevos registros.
def load_new_dataset(path_new: str) -> pd.DataFrame:
    log.info(f"Cargando nuevos registros desde {path_new}")
    df_new = pd.read_csv(path_new, parse_dates=["date"])
    df_new = df_new.sort_values(["product_id", "date"]).reset_index(drop=True)
    return df_new

# Validar
def validate_new_data(df_new: pd.DataFrame, df_base: pd.DataFrame) -> None:
    log.info("Validando consistencia de nuevos datos...")
    expected_cols = list(df_base.columns)
    new_cols = list(df_new.columns)

    missing = set(expected_cols) - set(new_cols)
    extra = set(new_cols) - set(expected_cols)
    if missing:
        raise ValueError(f"Columnas faltantes en nuevos datos: {missing}")
    if extra:
        # No es error grave, pero lo avisamos
        print(f"[WARN] Columnas extra en nuevos datos (se ignorarán): {extra}")
        df_new = df_new[expected_cols]

    if df_new["date"].isna().any():
        raise ValueError("Hay fechas vacías en el dataset nuevo.")

    # Validar duplicados (product_id, date)
    base_pairs = set(zip(df_base["product_id"], df_base["date"]))
    new_pairs = set(zip(df_new["product_id"], df_new["date"]))
    duplicates = base_pairs & new_pairs
    if duplicates:
        raise ValueError(
            f"Existen registros nuevos con (product_id, date) ya presentes: {list(duplicates)[:5]}"
        )

    # Valores negativos
    for col in ["quantity_sold", "stock_available", "replenishment", "price_per_unit"]:
        if (df_new[col] < 0).any():
            raise ValueError(f"Hay valores negativos en la columna {col} en nuevos datos.")

# Combinar dataset
def merge_datasets(df_base: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    log.info("Fusionando dataset base + nuevos registros...")
    df_all = pd.concat([df_base, df_new], ignore_index=True)
    df_all = df_all.sort_values(["product_id", "date"]).reset_index(drop=True)
    return df_all

# Evaluar RMSE
def evaluate_rmse(model, X_eval, y_eval, scaler, num_features):
    """
    Evalúa RMSE desescalado para un modelo dado.
    """
    # Predicción escalada
    y_pred_scaled = model.predict(X_eval)

    # Reconstruir matriz para desescalar correctamente
    temp_pred = np.zeros((len(y_pred_scaled), len(num_features)))
    temp_true = np.zeros((len(y_eval), len(num_features)))

    temp_pred[:, 0] = y_pred_scaled.flatten()
    temp_true[:, 0] = y_eval.flatten()

    # Desescalar
    y_pred_real = scaler.inverse_transform(temp_pred)[:, 0]
    y_true_real = scaler.inverse_transform(temp_true)[:, 0]

    # RMSE real
    return math.sqrt(mean_squared_error(y_true_real, y_pred_real))


# Set de evaluación estable
def build_evaluation_set(df_model, scalers, seq_len=10, features=None):
    if features is None:
        raise ValueError("Debes pasar NUM_FEATURES")

    log.info("Construyendo set de evaluación estable...")

    df_eval = df_model.groupby("product_id").tail(200)

    X_eval = []
    y_eval = []

    pid_ref = list(df_eval["product_id"].unique())[0]
    scaler_ref = scalers[pid_ref]

    for pid, group in df_eval.groupby("product_id"):
        values = group[features].values
        scaled_values = scalers[pid].transform(values)

        for i in range(len(scaled_values) - seq_len):
            X_eval.append(scaled_values[i:i+seq_len])
            y_eval.append(scaled_values[i+seq_len, 0])

    return np.array(X_eval), np.array(y_eval), scaler_ref


# Lógica principal para comparar modelos
def compare_models(model_old, model_new, X_eval, y_eval, scaler, num_features):
    log.info("Evaluando RMSE para modelo actual y modelo candidato...")

    rmse_old = evaluate_rmse(model_old, X_eval, y_eval, scaler, num_features)
    rmse_new = evaluate_rmse(model_new, X_eval, y_eval, scaler, num_features)

    log.info(f"RMSE actual:     {rmse_old:.4f}")
    log.info(f"RMSE candidato:  {rmse_new:.4f}")

    return rmse_new < rmse_old, rmse_old, rmse_new

# Integración FINAL
def run_incremental_update(
    path_base_raw: str = "data/raw/dataset.csv",
    path_new_raw: str = "data/raw/nuevos_registros.csv",
    path_dataset_final: str = "data/processed/dataset_final.csv",
    path_model: str = "models/modelo_lstm_optimo.h5",
):
    os.makedirs("data/raw", exist_ok=True)

    download_file("dataset.csv", path_base_raw)

    if not os.path.exists(path_base_raw):
        raise FileNotFoundError(f"No se pudo descargar el dataset base: {path_base_raw}")

    if not os.path.exists(path_base_raw):
        download_file("dataset.csv", path_base_raw)
        log.info("Dataset base descargado desde la nube.")
    else:
        log.info("Dataset local encontrado, no se descargó desde la nube.")
    log.info("==== INICIANDO PIPELINE INCREMENTAL ====")

    # 1) Cargar base
    df_base = load_base_dataset(path_base_raw)

    # 2) Cargar nuevos
    df_new = load_new_dataset(path_new_raw)

    # 3) Validación
    validate_new_data(df_new, df_base)

    # 4) Unir datasets
    df_all = merge_datasets(df_base, df_new)
    df_all.to_csv(path_base_raw, index=False)
    log.info(f"[OK] dataset crudo actualizado: {path_base_raw}")

    # 5) Recompute features
    df_model = recompute_features(df_all)
    df_model.to_csv(path_dataset_final, index=False)
    log.info(f"[OK] dataset_final actualizado: {path_dataset_final}")

    # 6) Ajustar scalers (NO GUARDAR AÚN)
    scalers = fit_scalers(df_model, features=NUM_FEATURES)

    # 7) Entrenar modelo candidato
    log.info("Entrenando modelo candidato...")
    model_new, history = incremental_train(
        model_path=path_model,
        df_model=df_model,
        scalers=scalers,
        features=NUM_FEATURES,
        seq_len=10,
        extra_epochs=8,
        batch_size=32,
        save_path="models/modelo_candidato.h5"
    )

    # 8) Construir set de evaluación
    X_eval, y_eval, scaler_eval = build_evaluation_set(df_model, scalers, seq_len=10, features=NUM_FEATURES)

    # 9) Comparación
    log.info("Comparando modelos...")
    model_old = models.load_model(path_model)
    model_candidato = models.load_model("models/modelo_candidato.h5")

    mejora, rmse_old, rmse_new = compare_models(
        model_old, model_candidato, X_eval, y_eval, scaler_eval, NUM_FEATURES
    )

    if mejora:
        log.info(f"[MEJORA] El modelo candidato ES mejor (RMSE {rmse_new:.4f} < {rmse_old:.4f})")
        log.info("Actualizando modelo oficial y escaladores...")

        model_candidato.save(path_model)
        save_scalers_and_features(
            scalers,
            features=NUM_FEATURES,
            path_scalers="models/scalers_lstm_optimo.save",
            path_features="models/features_lstm_optimo.save"
        )
        upload_file(path_base_raw, "dataset.csv")
        log.info("Dataset sincronizado en la nube")
    else:
        log.info(f"[NO MEJORA] El modelo candidato es peor (RMSE {rmse_new:.4f} >= {rmse_old:.4f})")
        log.info("Descartando modelo candidato. Manteniendo el oficial.")
    log.info("==== PIPELINE COMPLETADO ====")