import easyocr
import cv2
import numpy as np
from typing import Dict, Tuple
import logging
from app.config import settings
import time
from concurrent.futures import ThreadPoolExecutor
import asyncio

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.engine = settings.OCR_ENGINE
        self.languages = settings.OCR_LANGUAGES.split(',')
        self.reader = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Inicializar el motor OCR"""
        try:
            if self.engine == "easyocr":
                logger.info("Inicializando EasyOCR...")
                self.reader = easyocr.Reader(
                    self.languages, 
                    gpu=False,
                    verbose=False
                )
                logger.info("✅ EasyOCR inicializado")
            else:
                logger.warning(f"Motor OCR '{self.engine}' no soportado, usando EasyOCR")
                self.reader = easyocr.Reader(self.languages, gpu=False, verbose=False)
        except Exception as e:
            logger.error(f"❌ Error inicializando OCR: {e}")
            raise
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocesar imagen para mejorar OCR"""
        try:
            img = cv2.imread(image_path)
            
            if img is None:
                logger.error(f"No se pudo leer la imagen: {image_path}")
                return None
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
            binary = cv2.adaptiveThreshold(
                denoised, 255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 
                11, 2
            )
            
            return binary
            
        except Exception as e:
            logger.error(f"Error en preprocesamiento: {e}")
            return cv2.imread(image_path)
    
    def extract_text(self, image_path: str) -> Tuple[str, float]:
        """Extraer texto de una imagen"""
        start_time = time.time()
        
        try:
            processed_img = self.preprocess_image(image_path)
            
            if processed_img is None:
                logger.error(f"Imagen no válida: {image_path}")
                return "", 0.0
            
            results = self.reader.readtext(
                processed_img,
                detail=1,
                paragraph=False,
                min_size=10,
                text_threshold=0.7,
                low_text=0.4
            )
            
            texts = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                if confidence > 0.3:
                    texts.append(text)
                    confidences.append(confidence)
            
            full_text = " ".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            processing_time = time.time() - start_time
            
            logger.info(f"OCR completado en {processing_time:.2f}s - Confianza: {avg_confidence:.2f} - Texto: '{full_text[:50]}...'")
            
            return full_text, float(avg_confidence)
            
        except Exception as e:
            logger.error(f"❌ Error en OCR: {e}")
            return "", 0.0
    
    def _extract_single_image(self, img_type: str, img_path: str) -> Tuple[str, Dict]:
        """Extraer texto de una sola imagen (para ejecución paralela)"""
        text, confidence = self.extract_text(img_path)
        return img_type, {
            "text": text,
            "confidence": float(confidence)
        }
    
    def extract_from_multiple_images(self, image_paths: Dict[str, str]) -> Dict:
        """
        🔹 MEJORADO: Extraer texto de múltiples imágenes EN PARALELO
        """
        start_time = time.time()
        logger.info(f"🚀 Iniciando OCR paralelo de {len(image_paths)} imágenes...")
        
        results = {}
        
        # 🔹 Ejecutar OCR en paralelo usando ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self._extract_single_image, img_type, img_path)
                for img_type, img_path in image_paths.items()
            ]
            
            for future in futures:
                img_type, result = future.result()
                results[img_type] = result
        
        # Calcular confianza promedio
        confidences = [r["confidence"] for r in results.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        total_time = time.time() - start_time
        logger.info(f"✅ OCR paralelo completado en {total_time:.2f}s (vs ~{len(image_paths)*15}s secuencial)")
        
        return {
            "images": results,
            "overall_confidence": float(avg_confidence)
        }

# Instancia global
ocr_service = OCRService()