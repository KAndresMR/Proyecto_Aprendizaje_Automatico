import os
import shutil
from typing import List
from fastapi import UploadFile
from datetime import datetime
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self):
        """Crear directorio de uploads si no existe"""
        os.makedirs(self.upload_dir, exist_ok=True)
        logger.info(f"📁 Directorio de uploads: {self.upload_dir}")
    
    def save_image(self, file: UploadFile, image_type: str) -> str:
        """Guardar imagen y retornar la ruta"""
        try:
            # Generar nombre único
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{image_type}_{timestamp}_{file.filename}"
            file_path = os.path.join(self.upload_dir, filename)
            
            # Guardar archivo
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"✅ Imagen guardada: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"❌ Error guardando imagen: {e}")
            raise
    
    def save_multiple_images(self, files: List[UploadFile], image_types: List[str]) -> dict:
        """Guardar múltiples imágenes"""
        saved_images = {}
        
        for file, img_type in zip(files, image_types):
            if file:
                file_path = self.save_image(file, img_type)
                saved_images[img_type] = file_path
        
        return saved_images
    
    def delete_image(self, file_path: str):
        """Eliminar imagen del sistema"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ Imagen eliminada: {file_path}")
        except Exception as e:
            logger.error(f"❌ Error eliminando imagen: {e}")

# Instancia global
image_service = ImageService()