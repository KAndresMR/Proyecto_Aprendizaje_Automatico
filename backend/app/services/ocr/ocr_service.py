import logging
import cv2
import time
import re

from backend.app.core.config import settings
from typing import Dict, Tuple
from concurrent.futures import ThreadPoolExecutor


logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self, reader):
        self.reader = reader 
        self.engine = "EasyOCR"
    
    def _extract_single_image(self, img_type: str, img_path: str) -> Tuple[str, Dict]:
        img = cv2.imread(img_path)
        if img is None:
            logger.error(f"No se pudo leer: {img_path}")
            return img_type, {"text": "", "confidence_avg": 0.0}
        
        if self.is_blurry(img):
            logger.warning(f"Imagen {img_type} borrosa")
            return img_type, {
                "text": "",
                "confidence_avg": 0.0,
                "blur_detected": True
            }

        # Resize
        height, width = img.shape[:2]
        max_dim = 1600
        if max(height, width) > max_dim:
            scale = max_dim / max(height, width)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        try:
            results = self.reader.readtext(enhanced, detail=1, paragraph=False)

            logger.debug(f"EasyOCR detectó {len(results)} elementos en {img_type}")

            lines = []
            confidences = []

            for item in results:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    bbox, text, conf = item[0], item[1], item[2]
                    text = text.strip()
                    conf = float(conf)

                    if len(text) <= 2:
                        continue

                    if re.match(r'^[^a-zA-Z0-9]+$', text):
                        continue

                    y_min = min(point[1] for point in bbox)

                    lines.append((y_min, text, conf))
                    confidences.append(conf)

            # ordenar verticalmente
            lines.sort(key=lambda x: x[0])

            ordered_text = [line[1] for line in lines]
            full_text = "\n".join(ordered_text)

            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                min_conf = min(confidences)
                max_conf = max(confidences)
            else:
                avg_conf = min_conf = max_conf = 0.0

            logger.info(f"✅ OCR {img_type}: {len(ordered_text)} textos, conf={avg_conf:.2f}")

            return img_type, {
                "text": full_text,
                "confidence_avg": avg_conf,
                "confidence_min": min_conf,
                "confidence_max": max_conf
            }

        except Exception as e:
            logger.error(f"❌ Error EasyOCR en {img_type}: {e}")
            return img_type, {"text": "", "confidence_avg": 0.0}
        
    def is_blurry(self, image, threshold: float = 100.0) -> bool:
        """
        Detecta si una imagen está borrosa usando la varianza del Laplaciano.
        threshold bajo = más permisivo
        threshold alto = más estricto
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        logger.debug(f"Blur detection variance: {laplacian_var:.2f}")
        
        return laplacian_var < threshold

    
    def extract_from_multiple_images(self, image_paths: Dict[str, str]) -> Dict:
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
        confidences = [
            r["confidence_avg"]
            for r in results.values()
            if r["text"].strip()
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        elapsed = time.time() - start_time
        logger.info(f"✅ OCR paralelo completado en {elapsed:.2f}s | Confianza={avg_confidence:.2f}")
        logger.info(
            f"📊 OCR Stats | Images={len(results)} | "
            f"OverallConf={avg_confidence:.2f}"
        )

        for img_type, data in results.items():
            logger.debug(
                f"   └─ {img_type}: "
                f"avg={data['confidence_avg']:.2f} "
                f"min={data['confidence_min']:.2f} "
                f"max={data['confidence_max']:.2f} "
                f"text_len={len(data['text'])}"
            )
        
        return {
            "images": results,
            "overall_confidence": avg_confidence
        }
