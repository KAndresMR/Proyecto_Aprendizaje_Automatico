import numpy as np
import pandas as pd
from keras import models

from .scaling import NUM_FEATURES

def generar_secuencias_scaled(df_model: pd.DataFrame, scalers: dict,
                                seq_len: int = 10, features=None):
    """
    Genera X, y usando df_model + scalers por producto.
    """
    if features is None:
        features = NUM_FEATURES

    X, y = [], []
    for pid, group in df_model.groupby("product_id"):
        data = group[features].values
        scaler = scalers[pid]
        data_scaled = scaler.transform(data)

        for i in range(len(data_scaled) - seq_len):
            X.append(data_scaled[i:i+seq_len])
            y.append(data_scaled[i+seq_len, 0])  # columna 0 = quantity_sold

    X = np.array(X)
    y = np.array(y)
    return X, y

def incremental_train(model_path: str,
                        df_model: pd.DataFrame,
                        scalers: dict,
                        features=None,
                        seq_len: int = 10,
                        extra_epochs: int = 8,
                        batch_size: int = 32,
                        save_path: str = "models/modelo_candidato.h5"):
    """
    1.	Carga el modelo existente
	2.	Entrena más épocas
	3.	Guarda un modelo nuevo
    """
    if features is None:
        features = NUM_FEATURES

    print("[INFO] Generando secuencias escaladas...")
    X, y = generar_secuencias_scaled(df_model, scalers, seq_len=seq_len, features=features)
    print("[INFO] X shape:", X.shape, " y shape:", y.shape)

    print(f"[INFO] Cargando modelo desde {model_path}")
    model = models.load_model(model_path)

    print("[INFO] Entrenando de forma incremental...")
    history = model.fit(
        X, y,
        epochs=extra_epochs,
        batch_size=batch_size,
        shuffle=True,
        verbose=1
    )

    print(f"[OK] Guardando modelo actualizado en {save_path}")
    model.save(save_path)

    return model, history