from dotenv import load_dotenv
load_dotenv()
import os
import joblib
import shutil
import numpy as np
import pandas as pd

from keras import models
from datetime import datetime
from datetime import timedelta
from pydantic import BaseModel
from app.llm_service import generate_summary
from fastapi.middleware.cors import CORSMiddleware
from ml.pipeline.update_dataset import run_incremental_update
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware



# =========================================
# FastAPI + CORS
# =========================================

app = FastAPI(title="Stock Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================
# Cargar recursos del modelo
# =========================================

model = models.load_model("models/modelo_lstm_optimo.h5")
scalers = joblib.load("models/scalers_lstm_optimo.save")
features = joblib.load("models/features_lstm_optimo.save")

df = pd.read_csv("data/processed/dataset_final.csv", parse_dates=["date"])

df = df.sort_values(["product_id", "date"])

PRODUCTS = list(scalers.keys())

# =========================================
# Body esperado por /predict
# =========================================

class PredictRequest(BaseModel):
    date: str                     # fecha obligatoria
    product_id: str | None = None
    all_products: bool = False
    seq_len: int = 10

# =========================================
# Funcion Auxiliar
# =========================================

def predict_until_date(df, model, scalers, product_id, target_date, seq_len):
    df_p = df[df["product_id"] == product_id].sort_values("date")

    last_date = df_p["date"].max()

    target_date = pd.to_datetime(target_date)

    if target_date <= last_date:
        raise ValueError("La fecha debe ser FUTURA respecto al dataset.")

    days_needed = (target_date - last_date).days

    scaler = scalers[product_id]

    # Preparar secuencia inicial
    recent = df_p[features].tail(seq_len).values
    seq = scaler.transform(recent)

    # Predicción paso a paso
    for _ in range(days_needed):
        pred_scaled = model.predict(np.expand_dims(seq, 0), verbose=0)[0][0]

        new_row = seq[-1].copy()
        new_row[0] = pred_scaled
        seq = np.vstack([seq[1:], new_row])

    # Desescalar
    temp = np.zeros((1, len(features)))
    temp[0, 0] = pred_scaled
    pred_real = scaler.inverse_transform(temp)[0][0]

    return float(pred_real)

# =========================================
# Endpoint principal
# =========================================

@app.post("/predict")
def predict(req: PredictRequest):

    # Validaciones
    if not req.all_products and not req.product_id:
        raise HTTPException(status_code=400, detail="Debe elegir producto o activar 'todos'.")

    if req.all_products and req.product_id:
        raise HTTPException(status_code=400, detail="No puede elegir producto y 'todos' al mismo tiempo.")

    try:
        # Validación de fecha
        datetime.strptime(req.date, "%Y-%m-%d")
    except:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD.")

    # --------------------------
    # CASO 1: UN PRODUCTO
    # --------------------------
    if not req.all_products:

        if req.product_id not in scalers:
            raise HTTPException(status_code=404, detail="Producto no encontrado.")

        pred = predict_until_date(df, model, scalers, req.product_id, req.date, req.seq_len)
        df_p = df[df["product_id"] == req.product_id]

        mu = df_p["quantity_sold"].mean()
        sigma = df_p["quantity_sold"].std()
        stock_min = max(mu - sigma, 0)
        warning = stock_min * 1.20

        if pred <= stock_min:
            alert = "CRITICO"
        elif pred <= warning:
            alert = "ADVERTENCIA"
        else:
            alert = "OK"

        return [{
            "product_id": req.product_id,
            "date": req.date,
            "pred_quantity_sold": pred,
            "alert": alert
        }]

    # --------------------------
    # CASO 2: TODOS LOS PRODUCTOS
    # --------------------------
    all_preds = []

    for prod in scalers.keys():
        pred = predict_until_date(df, model, scalers, prod, req.date, req.seq_len)
        alert = "CRITICO" if pred <= 80 else "OK"

        all_preds.append({
            "product_id": prod,
            "date": req.date,
            "pred_quantity_sold": pred,
            "alert": alert
        })

    return all_preds
        
# =========================================
# Endpoint para actualizar dataset
# =========================================

@app.post("/update-dataset")
async def update_dataset(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV.")

    temp_path = "data/raw/dataset_2022.csv"

    # 1) Guardar el archivo subido
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el archivo temporal: {str(e)}")

    # 2) Ejecutar pipeline incremental
    try:
        resultado = run_incremental_update(
            path_base_raw="data/raw/dataset_local.csv",
            path_new_raw=temp_path,
            path_dataset_final="data/processed/dataset_final.csv",
            path_model="models/modelo_lstm_optimo.h5",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la actualización: {str(e)}")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # 3) Recargar artefactos actualizados
    global model, scalers, features, df

    model = models.load_model("models/modelo_lstm_optimo.h5")
    scalers = joblib.load("models/scalers_lstm_optimo.save")
    features = joblib.load("models/features_lstm_optimo.save")

    df = pd.read_csv("data/processed/dataset_final.csv", parse_dates=["date"]).sort_values(["product_id", "date"])

    return {
        "status": "success",
        "message": "Dataset actualizado y modelo reentrenado.",
        "details": resultado
    }

# =========================================
# Endpoint para generar resumen LLM
# =========================================

@app.post("/llm-summary")
async def llm_summary(data: dict):

    if "predictions" not in data:
        raise HTTPException(status_code=400, detail="Falta 'predictions'")

    try:
        summary = generate_summary(data["predictions"])
        return {"summary": summary}

    except Exception as e:
        print("\n================ LLM ERROR ================")
        print(e)
        print("===========================================\n")

        raise HTTPException(
            status_code=500,
            detail="Error generando resumen LLM."
        )
