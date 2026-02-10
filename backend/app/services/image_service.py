import os
import shutil
import logging
import asyncio

from typing import List, Dict
from fastapi import UploadFile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self, upload_dir: str = "uploads"):
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.upload_dir = base_dir / upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def save_image(self, file: UploadFile, image_type: str) -> str:
        """Guardar UNA imagen"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{image_type}_{timestamp}_{file.filename}"
            file_path = self.upload_dir / filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"💾 Guardada: {filename}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ Error guardando {image_type}: {e}")
            raise
    
    async def save_multiple_images_async(
        self, 
        files: List[UploadFile], 
        image_types: List[str]
    ) -> Dict[str, str]:
        """Guardar múltiples imágenes EN PARALELO"""
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            tasks = [
                loop.run_in_executor(executor, self.save_image, file, img_type)
                for file, img_type in zip(files, image_types)
                if file
            ]
            
            saved_paths = await asyncio.gather(*tasks)
        
        # Construir diccionario
        saved_images = {}
        idx = 0
        for file, img_type in zip(files, image_types):
            if file:
                saved_images[img_type] = saved_paths[idx]
                idx += 1
        
        logger.info(f"💾 {len(saved_images)} imágenes guardadas en paralelo")
        return saved_images