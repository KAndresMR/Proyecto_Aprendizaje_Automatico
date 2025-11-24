# ml/prediction_service.py

import pandas as pd
import numpy as np
import joblib
from tensorflow.keras.models import load_model

SEQ_LEN = 10

class StockPredictor:
    def __init__(self,
                 data_path="../data/processed/dataset_final.csv",
                 features_path="../models/features_lstm_optimo.save",
                 model_path="../models/modelo_lstm_optimo.h5",
                 scalers_path="../models/scalers_lstm_optimo.save"):

        self.df = pd.read_csv(data_path, parse_dates=["date"])
        self.df = self.df.sort_values(["product_id", "date"]).reset_index(drop=True)

        self.features = joblib.load(features_path)
        self.model = load_model(model_path)
        self.scalers = joblib.load(scalers_path)

    # ---------- núcleo de predicción a fecha ----------
    def predict_to_date(self, product_id: str, target_date: str):
        import pandas as pd
        target_date = pd.to_datetime(target_date)

        if product_id not in self.scalers:
            return {"error": f"Producto {product_id} no encontrado"}

        df_p = self.df[self.df["product_id"] == product_id].copy()
        df_p = df_p.sort_values("date")

        if len(df_p) < SEQ_LEN:
            return {"error": f"Datos insuficientes para {product_id}"}

        scaler = self.scalers[product_id]

        recent = df_p[self.features].tail(SEQ_LEN).values
        input_seq = scaler.transform(recent)

        last_date = df_p["date"].max()
        steps = (target_date - last_date).days

        if steps <= 0:
            return {"error": "La fecha objetivo debe ser mayor a la última fecha histórica"}

        pred = None
        for _ in range(steps):
            pred = self.model.predict(input_seq[np.newaxis, :, :], verbose=0)[0][0]
            new_row = input_seq[-1].copy()
            new_row[0] = pred
            input_seq = np.vstack([input_seq[1:], new_row])

        temp = np.zeros((1, len(self.features)))
        temp[0, 0] = pred
        pred_real = self._inverse_scale_single(product_id, temp)

        return {
            "product_id": product_id,
            "target_date": target_date.strftime("%Y-%m-%d"),
            "pred_quantity_sold": float(round(pred_real, 2))
        }

    def _inverse_scale_single(self, product_id, temp):
        scaler = self.scalers[product_id]
        return scaler.inverse_transform(temp)[0, 0]

    # ---------- predicción para todos los productos ----------
    def predict_all_for_date(self, target_date: str):
        results = []
        for pid in self.df["product_id"].unique():
            r = self.predict_to_date(pid, target_date)
            results.append(r)
        return results

    # ---------- thresholds / alertas ----------
    def compute_thresholds(self, product_id: str):
        df_hist = self.df[self.df["product_id"] == product_id]
        mean = df_hist["quantity_sold"].mean()
        std = df_hist["quantity_sold"].std()

        critical = max(mean - std, 0)
        warning = critical * 1.2

        return critical, warning

    def attach_alerts(self, predictions):
        enriched = []
        for row in predictions:
            if "error" in row:
                enriched.append(row)
                continue

            pid = row["product_id"]
            pred = row["pred_quantity_sold"]

            critical, warning = self.compute_thresholds(pid)

            if pred <= critical:
                estado = "CRITICO"
            elif pred <= warning:
                estado = "ADVERTENCIA"
            else:
                estado = "OK"

            row["critical_threshold"] = round(critical, 2)
            row["warning_threshold"] = round(warning, 2)
            row["alert"] = estado

            enriched.append(row)
        return enriched