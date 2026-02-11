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
        """Preprocesamiento MÁS SUAVE"""
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"No se pudo leer: {image_path}")
            return None
        
        # 1. Redimensionar moderadamente
        height, width = img.shape[:2]
        max_dim = 1600  # Más conservador
        
        if max(height, width) > max_dim:
            scale = max_dim / max(height, width)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        
        # 2. Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 3. SOLO CLAHE suave (no binarizar)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # 4. Denoise MUY suave
        denoised = cv2.fastNlMeansDenoising(enhanced, h=7)
        
        return denoised  # ← RETORNAR GRAYSCALE, NO BINARIO

    def _extract_single_image(self, img_type: str, img_path: str) -> Tuple[str, Dict]:
        """OCR de una imagen con preprocesamiento suave"""
        
        # Leer imagen original (sin preprocesar primero)
        img = cv2.imread(img_path)
        if img is None:
            logger.error(f"No se pudo leer: {img_path}")
            return img_type, {"text": "", "confidence": 0.0}
        
        # Redimensionar moderadamente
        height, width = img.shape[:2]
        max_dim = 1600
        if max(height, width) > max_dim:
            scale = max_dim / max(height, width)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        
        # Convertir a grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # CLAHE suave
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        try:
            # ✅ CAMBIO CRÍTICO: paragraph=False
            results = self.reader.readtext(
                enhanced, 
                detail=1, 
                paragraph=False  # ← CAMBIAR AQUÍ
            )
            
            logger.debug(f"EasyOCR detectó {len(results)} elementos en {img_type}")
            
            all_text = []
            confidences = []
            
            for item in results:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    bbox, text, conf = item[0], item[1], item[2]
                    
                    conf = float(conf)
                    logger.debug(f"  '{text[:30]}...' conf={conf:.2f}")
                    
                    if text.strip():
                        all_text.append(text.strip())
                        confidences.append(conf)
            
            full_text = " ".join(all_text)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            
            logger.info(f"✅ OCR {img_type}: {len(all_text)} textos, conf={avg_conf:.2f}")
            
            if avg_conf == 0.0 and all_text:
                logger.warning(f"⚠️ Confianza 0 pero hay texto! Forzando 0.5")
                avg_conf = 0.5
            
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

