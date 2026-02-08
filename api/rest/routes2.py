import base64
import os
import shutil
from typing import List, Optional

import cv2
import mlflow
import numpy as np
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from mlflow.entities import ViewType

# este es el motor de reconocimiento de productos
from ml.models.sift_engine import get_sift_engine

router = APIRouter()

SIFT_STORAGE = "sift_data.pkl"

sift_engine = get_sift_engine(str(SIFT_STORAGE))


@router.post('/register')
async def register(
    image: UploadFile = File(...),
    name: str = Form("Unknown"),
    threshold: float = Form(0.04),
    mask: Optional[UploadFile] = File(None)
):
    """
    Registra un producto en la base de datos.
    por ahora funciona con una sola imagen, hay que hacerlo para un grupo de imagenes bien armadas

    Espera: 'image' file, 'name' text.
    Opcional: 'mask' file (binary image), 'threshold' float.
    """
    try:
        img_bytes = await image.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if cv_image is None:
            return JSONResponse(status_code=400, content={'error': 'Invalid image'})

        # Mask handling
        cv_mask = None
        if mask:
            mask_bytes = await mask.read()
            mask_nparr = np.frombuffer(mask_bytes, np.uint8)
            cv_mask = cv2.imdecode(mask_nparr, cv2.IMREAD_GRAYSCALE)
            
            # Ensure mask is same size as image
            if cv_mask is not None:
                 cv_mask = cv2.resize(cv_mask, (cv_image.shape[1], cv_image.shape[0]))
                 # Threshold just to be safe it's binary
                 _, cv_mask = cv2.threshold(cv_mask, 127, 255, cv2.THRESH_BINARY)
        
        # Registrar con los parámetros
        success, msg = sift_engine.register_product(name, cv_image, mask=cv_mask, contrast_threshold=threshold)
        
        if success:
            return JSONResponse(status_code=200, content={'message': msg})
        else:
            return JSONResponse(status_code=500, content={'error': msg})

    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@router.post('/preview_keypoints')
async def preview_keypoints(
    image: UploadFile = File(...),
    threshold: float = Form(0.04),
    mask: Optional[UploadFile] = File(None)
):
    """
    Previsualización de puntos clave, previo a guardar el producto.
    Expects: 'image', 'mask' (opt), 'threshold' (opt).
    """
    try:
        img_bytes = await image.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if cv_image is None:
            return JSONResponse(status_code=400, content={'error': 'Invalid image'})

        cv_mask = None
        if mask:
            mask_bytes = await mask.read()
            mask_nparr = np.frombuffer(mask_bytes, np.uint8)
            cv_mask = cv2.imdecode(mask_nparr, cv2.IMREAD_GRAYSCALE)
            if cv_mask is not None:
                 cv_mask = cv2.resize(cv_mask, (cv_image.shape[1], cv_image.shape[0]))
                 _, cv_mask = cv2.threshold(cv_mask, 127, 255, cv2.THRESH_BINARY)

        # Detect & Draw
        vis_img, count = sift_engine.detect_keypoints_vis(cv_image, mask=cv_mask, contrast_threshold=threshold)
        
        # Encode return
        _, buffer = cv2.imencode('.jpg', vis_img)
        vis_base64 = base64.b64encode(buffer).decode('utf-8')
        
        #retorna la imagen con los puntos dibujados
        return {
            'keypoint_image': vis_base64,
            'count': count
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@router.post('/predict')
async def predict(image: UploadFile = File(...)):
    """
    Identificación de producto en la imagen subida.
    """
    try:
        img_bytes = await image.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if cv_image is None:
             return JSONResponse(status_code=400, content={'error': 'Invalid image'})

        label, matches = sift_engine.identify_product(cv_image)  # identifica el producto
        
        if label:
            return {
                'label': label,
                'matches': matches,
                'probability': 1.0 # SIFT is deterministic "match found", simulated prob
            }
        else:
            return {
                'label': 'Unknown',
                'matches': matches,
                'probability': 0.0
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@router.get('/mlflow/versions')
def list_versions():
    """
    Lista de versiones del modelo entrenado de predicciones.
    """
    try:
        experiment = mlflow.get_experiment_by_name("SIFT_Product_Registry")
        if not experiment:
            return []
        
        # ordenados desde el mas reciente
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            run_view_type=ViewType.ACTIVE_ONLY,
            order_by=["attribute.start_time DESC"]
        )
        
        versions = []
        for _, run in runs.iterrows():
            versions.append({
                'run_id': run['run_id'],
                'date': run['start_time'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(run['start_time'], 'strftime') else str(run['start_time']),
                'product_count': int(run['metrics.product_count']) if 'metrics.product_count' in run and not np.isnan(run['metrics.product_count']) else 0
            })
        return versions
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


from pydantic import BaseModel

class RestoreRequest(BaseModel):
    run_id: str

@router.post('/mlflow/restore')
def restore_version(request: RestoreRequest):
    """
    Lista para restaurar versiones de modelos entrenados.
    """
    run_id = request.run_id
    if not run_id:
         return JSONResponse(status_code=400, content={'error': 'No run_id provided'})
    
    try:
        # Download (downloads to a temp directory)
        artifact_uri = f"runs:/{run_id}/sift_data.pkl"
        downloaded_path = mlflow.artifacts.download_artifacts(artifact_uri=artifact_uri)
        
        # Overwrite current database
        shutil.copy(downloaded_path, SIFT_STORAGE)
        
        # Reload memory
        sift_engine.load_database()
        
        return {'message': f'Restored version {run_id}', 'count': len(sift_engine.database)}
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})
    
    
    
    
    
    
