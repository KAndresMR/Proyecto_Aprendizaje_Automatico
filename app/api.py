from dotenv import load_dotenv
load_dotenv()
import os
import joblib
import shutil
import numpy as np
import pandas as pd

from io import BytesIO
from tensorflow.keras import models
from datetime import datetime
from datetime import timedelta
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ml.pipeline.update_dataset import simple_update_pipeline
#from app.llm_service import generate_summary




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
model = None
scalers = None
features = None
df = None
PRODUCTS = []

def load_resources():
    model = models.load_model("models/modelo_lstm_optimo.h5", compile=False)
    scalers = joblib.load("models/scalers_lstm_optimo.save")
    features = joblib.load("models/features_lstm_optimo.save")
    df = pd.read_csv("data/processed/dataset_final.csv", parse_dates=["date"])
    df = df.sort_values(["product_id", "date"])
    return model, scalers, features, df

#model, scalers, features, df = load_resources()
@app.on_event("startup")
def startup_event():
    global model, scalers, features, df, PRODUCTS
    try:
        model, scalers, features, df = load_resources()
        PRODUCTS = list(scalers.keys())
        print("DF shape:", df.shape)
        print("Recursos cargados correctamente")
    except Exception as e:
        print("Error cargando recursos:", e)


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
    
    if df_p.empty:
        raise ValueError(f"No hay datos históricos para {product_id}")
    
    if len(df_p) < seq_len:
        raise ValueError("Histórico insuficiente para generar secuencia.")

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
    
    if model is None or scalers is None or df is None:
        raise HTTPException(
            status_code=500, 
            detail="Recursos del modelo aún no cargados."
        )

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

        pred = predict_until_date(
            df, model, scalers, 
            req.product_id, 
            req.date, 
            req.seq_len
        )
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
    results = []

    for prod in scalers.keys():

        pred = predict_until_date(
            df, model, scalers,
            prod, req.date, req.seq_len
        )

        df_p = df[df["product_id"] == prod]

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

        results.append({
            "product_id": prod,
            "date": req.date,
            "pred_quantity_sold": pred,
            "alert": alert
        })

    return results
        
# =========================================
# Endpoint para actualizar dataset
# =========================================

@app.post("/update-dataset")
async def update_dataset(file: UploadFile = File(...)):

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan CSV")

    contents = await file.read()
    df_new = pd.read_csv(BytesIO(contents), parse_dates=["date"])

    try:
        result = simple_update_pipeline(
            base_path="data/raw/dataset_local.csv",
            df_new=df_new,
            final_path="data/processed/dataset_final.csv",
            model_path="models/modelo_lstm_optimo.h5"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Recargar recursos
    global model, scalers, features, df
    model = models.load_model("models/modelo_lstm_optimo.h5", compile=False)
    scalers = joblib.load("models/scalers_lstm_optimo.save")
    features = joblib.load("models/features_lstm_optimo.save")
    df = pd.read_csv(
        "data/processed/dataset_final.csv",
        parse_dates=["date"]
    ).sort_values(["product_id", "date"])

    return {
        "status": "ok",
        "msg": "Dataset actualizado y modelo reentrenado",
        "rows_added": result["rows_added"]
    }
    
# =========================================
# Endpoint para generar resumen LLM
# =========================================
'''
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

'''