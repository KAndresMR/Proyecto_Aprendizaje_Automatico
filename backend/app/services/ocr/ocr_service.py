import logging
import cv2
import numpy as np
import time

from backend.app.core.config import settings
from typing import Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor


logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self, reader):
        self.reader = reader 
        self.engine = "EasyOCR"
    
    def preprocess_image_smart(self, image_path: str, img_type: str = "front") -> np.ndarray:
        """Preprocesamiento adaptativo"""
        # FRONTAL: CLAHE + Denoise
        # LATERAL: Sharpen + Adaptive Threshold
        
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"No se pudo leer la imagen: {image_path}")
            return None
        
        # Redimensionar
        height, width = img.shape[:2]
        target_width = 1200 if img_type == "front" else 1400
        
        if width > target_width:
            scale = target_width / width
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Procesamiento específico
        if img_type == "front":
            # ✅ FRONTAL: CLAHE + Denoise
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
            return denoised
        else:
            # ✅ LATERALES: Sharpen + CLAHE + Otsu
            kernel_sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharpened = cv2.filter2D(gray, -1, kernel_sharpen)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(sharpened)
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return binary

    def _extract_single_image(self, img_type: str, img_path: str) -> Tuple[str, Dict]:
        """OCR de Una imagen"""
        # 1. Preprocesar
        # 2. EasyOCR readtext
        # 3. Retornar texto + confianza
        
        # Preprocesar según tipo
        optimal_variant = self.preprocess_image_smart(img_path, img_type)
        
        if optimal_variant is None:
            return img_type, {"text": "", "confidence": 0.0}
        
        try:
            # OCR con EasyOCR
            results = self.reader.readtext(optimal_variant, detail=1, paragraph=True)
            
            all_text = []
            confidences = []
            
            for item in results:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    text = item[1] if len(item) > 1 else ""
                    conf = float(item[2]) if len(item) > 2 else 0.0
                    
                    if isinstance(text, list):
                        text = " ".join(text)
                    
                    if text.strip():
                        all_text.append(text)
                        confidences.append(conf)
            
            full_text = " ".join(all_text)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            
            logger.info(f"✅ OCR {img_type}: {len(all_text)} textos, conf={avg_conf:.2f}")
            
            return img_type, {
                "text": full_text,
                "confidence": avg_conf
            }
            
        except Exception as e:
            logger.error(f"❌ Error EasyOCR en {img_type}: {e}")
            return img_type, {"text": "", "confidence": 0.0}

    
    def extract_from_multiple_images(self, image_paths: Dict[str, str]) -> Dict:
        """OCR PARALELO en 3 imágenes"""
        # ThreadPoolExecutor para procesar en paralelo
        
        start_time = time.time()
        results = {}
        
        # Procesar en paralelo
        with ThreadPoolExecutor(max_workers=4) as executor:
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
        
        elapsed = time.time() - start_time
        logger.info(f"✅ OCR paralelo completado en {elapsed:.2f}s | Confianza={avg_confidence:.2f}")
        
        return {
            "images": results,
            "overall_confidence": avg_confidence
        }

