from tensorflow.keras import models
import numpy as np
import joblib

def retrain_model(model_path, df_model, seq_len=10):
    # Cargar modelo
    model = models.load_model(model_path)

    # Cargar features originales
    features = joblib.load("models/features_lstm_optimo.save")

    # Usar solo esas columnas
    data = df_model[features].tail(500)

    X, y = [], []
    values = data.values

    for i in range(len(values) - seq_len):
        X.append(values[i:i+seq_len])
        y.append(values[i+seq_len, 0])  # quantity_sold

    X = np.array(X)
    y = np.array(y)

    # Entrenamiento ligero
    model.fit(X, y, epochs=1, batch_size=16, verbose=0)

    # Guardar
    model.save(model_path)

    return {"status": "updated", "samples": len(X)}