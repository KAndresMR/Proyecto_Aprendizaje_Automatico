import pandas as pd
import numpy as np

# ================================
# CONFIGURACIÓN
# ================================

def reassign_season(s):
    if s == "época lluviosa":
        return "lluvioso"
    elif s == "época seca":
        return "seca"
    return s

def demand_logic(row):
    d = row["date"]
    qty = row["quantity_sold"]

    # Época festiva: diciembre
    if d.month == 12:
        return "alto"
    
    # Festivos clave
    if (d.month, d.day) in [(12, 24), (12, 25), (12, 31)]:
        return "alto"

    # Altas ventas según la cantidad
    if qty > 100:
        return "alto"
    elif qty >= 60:
        return "normal"
    else:
        return "bajo"


# ================================
# PROCESAMIENTO
# ================================

def safe_to_2021(date):
    try:
        return date.replace(year=2021)
    except ValueError:
        # Caso especial: 29/02/2024 -> 28/02/2021
        return date.replace(year=2021, day=28)

def modificar_dataset(input_file, output_file):
    print("Cargando dataset...")
    df = pd.read_csv(input_file, parse_dates=["date"])
    
    # ================================
    # CAMBIO DE FECHAS 2024 → 2021
    # ================================
    df["date"] = df["date"].apply(safe_to_2021)

    # Ajustar la columna season
    df["season"] = df["season"].apply(reassign_season)

    # Demand status con lógica coherente
    df["demand_status"] = df.apply(demand_logic, axis=1)

    # Guardar archivo modificado
    df.to_csv(output_file, index=False)
    print(f"✔ Dataset modificado guardado en: {output_file}")

    return df


# ================================
# EJECUCIÓN
# ================================

# El dataset ORIGINAL es 2024.
# El dataset MODIFICADO será 2021.

df_mod = modificar_dataset(
    input_file="dataset_2024.csv", 
    output_file="dataset_2021_modificado.csv"
)

df_mod.head()