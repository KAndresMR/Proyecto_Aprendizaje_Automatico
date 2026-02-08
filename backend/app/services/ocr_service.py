import easyocr
import cv2
import numpy as np
from typing import Dict, Tuple, List
import logging
from app.config import settings
import time
from concurrent.futures import ThreadPoolExecutor

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
            if self.engine.lower() == "easyocr":
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
    
    def preprocess_image(self, image_path: str) -> List[np.ndarray]:
        """Generar variantes de la imagen para mejorar OCR"""
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"No se pudo leer la imagen: {image_path}")
            return []

        variants = []

        # Original
        variants.append(img)

        # Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        variants.append(gray)

        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        variants.append(enhanced)

        # Blur ligero
        blur = cv2.GaussianBlur(enhanced, (3, 3), 0)
        variants.append(blur)

        return variants

    def process_variants(self, image_path: str) -> Tuple[str, float]:
        """
        OCR en todas las variantes de la imagen y devuelve texto combinado y confianza promedio
        """
        variants = self.preprocess_image(image_path)
        all_text = []
        confidences = []

        for img in variants:
            results = self.reader.readtext(img, detail=1, paragraph=True)
            for item in results:
                # EasyOCR puede devolver (bbox, text, conf)
                if isinstance(item, list) and len(item) >= 2:
                    text = item[1] if len(item) > 1 else ""
                    conf = float(item[2]) if len(item) > 2 else 0.0
                    if isinstance(text, list):
                        text = " ".join(text)  # Convertir listas internas a string
                    all_text.append(text)
                    confidences.append(conf)

        full_text = " ".join(all_text)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return full_text, avg_conf

    def _extract_single_image(self, img_type: str, img_path: str) -> Tuple[str, Dict]:
        text, confidence = self.process_variants(img_path)
        return img_type, {
            "text": text,
            "confidence": confidence
        }
    
    def extract_from_multiple_images(self, image_paths: Dict[str, str]) -> Dict:
        """OCR paralelo para múltiples imágenes usando process_variants"""
        start_time = time.time()
        logger.info(f"🚀 Iniciando OCR paralelo de {len(image_paths)} imágenes...")

        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self._extract_single_image, img_type, img_path)
                for img_type, img_path in image_paths.items()
            ]
            for future in futures:
                img_type, result = future.result()
                results[img_type] = result

        confidences = [r["confidence"] for r in results.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        logger.info(f"✅ OCR paralelo completado en {time.time()-start_time:.2f}s | Conf promedio={avg_confidence:.2f}")

        return {
            "images": results,
            "overall_confidence": avg_confidence
        }

# Instancia global
ocr_service = OCRService()
