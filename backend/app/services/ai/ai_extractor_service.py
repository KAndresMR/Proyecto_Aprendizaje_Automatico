import logging
import json
import re

from typing import Dict, Union
from google import genai
from google.genai.errors import ClientError
from backend.app.core.config import settings
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class AIExtractorService:
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    def extract_product_info(self, ocr_data: Union[Dict, str]) -> Dict:

        # 🔐 Blindaje contra JSON serializado
        if isinstance(ocr_data, str):
            try:
                ocr_data = json.loads(ocr_data)
            except Exception:
                logger.error("OCR data no es JSON válido")
                return self._empty_product_info()

        all_text = self._combine_ocr_text(ocr_data)

        if not all_text.strip():
            logger.info("⚠️ OCR vacío, retornando estructura vacía")
            return self._empty_product_info()

        try:
            return self._extract_with_gemini(all_text)

        except ClientError:
            logger.warning("⚠️ Gemini no disponible (quota o API error). Usando mock.")
            return self._extract_with_mock(all_text)

        except json.JSONDecodeError:
            logger.warning("⚠️ Gemini devolvió JSON inválido. Usando mock.")
            return self._extract_with_mock(all_text)

        except Exception:
            logger.exception("❌ Error inesperado en AIExtractorService")
            return self._extract_with_mock(all_text)

    def _extract_with_gemini(self, text: str) -> Dict:
        
        prompt = f"""
            Eres un experto en análisis de productos de consumo.

            Extrae información estructurada de este texto OCR y responde
            EXCLUSIVAMENTE en JSON válido.

            TEXTO OCR:
            {text}

            Devuelve EXACTAMENTE esta estructura:
            {{
            "name": null,
            "brand": null,
            "presentation": null,
            "size": null,
            "barcode": null,
            "batch": null,
            "expiry_date": null,
            "price": null,
            "category": null,
            "nutritional_info": {{
                "calories": null,
                "protein": null,
                "carbs": null,
                "fat": null,
                "sodium": null
            }}
            }}

            REGLAS:
            - Corrige errores de OCR
            - Limpia caracteres raros
            - Si no sabes un valor, usa null
            - NO agregues texto fuera del JSON
            """
        response = self.client.models.generate_content(
            model="gemini-2.0-flash", # o gemini-2.0-flash
            contents=prompt,
            config={
                "temperature": 0,
                "response_mime_type": "application/json"
            }
        )
        if not response.text:
            raise ValueError("Respuesta vacía de Gemini")
        return json.loads(response.text.strip())
    
    def _extract_with_mock(self, text: str) -> Dict:
        product = self._empty_product_info()

        barcode = re.search(r"\b\d{8,14}\b", text)
        if barcode:
            product["barcode"] = barcode.group()

        size = re.search(r"\b\d+\s?(ml|g|kg|l|L)\b", text, re.IGNORECASE)
        if size:
            product["size"] = size.group()

        price = re.search(r"\$?\d+(\.\d{2})?", text)
        if price:
            product["price"] = price.group()

        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 5]
        if lines:
            product["name"] = lines[0][:80]

        logger.info("🧠 Mock extractor usado")
        return product
    
    def _combine_ocr_text(self, ocr_data: Dict) -> str:
        parts = []

        for img_type, data in ocr_data.get("images", {}).items():
            text = data.get("text", "").strip()
            confidence = data.get("confidence", 0)

            if text:
                parts.append(
                    f"=== {img_type.upper()} (Conf:{confidence:.2f}) ===\n{text}\n"
                )

        return "\n".join(parts)
    
    def _empty_product_info(self) -> Dict:
        """Template de producto vacío"""
        return {
            "name": None,
            "brand": None,
            "presentation": None,
            "size": None,
            "barcode": None,
            "batch": None,
            "expiry_date": None,
            "price": None,
            "category": None,
            "nutritional_info": {
                "calories": None,
                "protein": None,
                "carbs": None,
                "fat": None,
                "sodium": None
            }
        }
