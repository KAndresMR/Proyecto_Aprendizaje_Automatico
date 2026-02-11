import logging
import json
import re

from typing import Dict, Union
from google import genai
from backend.app.core.config import settings
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

logger = logging.getLogger(__name__)

try:
    from .llama_client import llama_client
except ImportError:
    logger.warning("⚠️ LlamaClient no disponible")
    llama_client = None


class AIExtractorService:
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    def extract_product_info(self, ocr_data: Union[Dict, str]) -> Dict:
        # Blindaje contra JSON serializado
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

        except (ResourceExhausted, ServiceUnavailable) as e:
            logger.warning(f"⚠️ Gemini no disponible ({e.__class__.__name__}). Intentando Llama...")
            
            # ✅ ARREGLADO: Verificar que llama_client existe
            if llama_client and llama_client.llm:
                try:
                    result = llama_client.extract(all_text)
                    result["_extracted_with"] = "llama"
                    return result
                except Exception as llama_error:
                    logger.warning(f"⚠️ Llama falló: {llama_error}. Usando mock.")
                    return self._extract_with_mock(all_text)
            else:
                logger.warning("⚠️ Llama no disponible. Usando mock.")
                return self._extract_with_mock(all_text)

        except json.JSONDecodeError:
            logger.warning("⚠️ Gemini devolvió JSON inválido. Usando mock.")
            return self._extract_with_mock(all_text)

        except Exception as e:
            logger.exception(f"❌ Error inesperado: {e}")
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
        """Extracción mejorada con NLP básico"""
        product = self._empty_product_info()
        product["_extracted_with"] = "mock"
        
        # Limpiar texto
        text_clean = re.sub(r'\s+', ' ', text).strip()
        
        # 1. BARCODE (prioritario)
        barcode = re.search(r'\b\d{8,14}\b', text)
        if barcode:
            product["barcode"] = barcode.group()
        
        # 2. TAMAÑO (buscar ml, g, kg, L)
        size_patterns = [
            r'\b(\d+\.?\d*)\s?(ml|ML|mL|milliliters?)\b',
            r'\b(\d+\.?\d*)\s?(g|G|gr|GR|gramos?)\b',
            r'\b(\d+\.?\d*)\s?(kg|KG|kilogramos?)\b',
            r'\b(\d+\.?\d*)\s?(l|L|litros?)\b',
            r'\b(\d+\.?\d*)\s?(oz|OZ|onzas?)\b',
        ]
        for pattern in size_patterns:
            size_match = re.search(pattern, text, re.IGNORECASE)
            if size_match:
                num = size_match.group(1)
                unit = size_match.group(2).lower()
                product["size"] = f"{num}{unit}"
                break
        
        # 3. PRECIO
        price_patterns = [
            r'S/\.?\s*(\d+\.?\d*)',
            r'\$\s*(\d+\.?\d*)',
            r'PRECIO\s*[:.]?\s*(\d+\.?\d*)',
        ]
        for pattern in price_patterns:
            price_match = re.search(pattern, text, re.IGNORECASE)
            if price_match:
                try:
                    product["price"] = float(price_match.group(1))
                    break
                except:
                    pass
        
        # 4. LOTE
        lote_patterns = [
            r'LOT[EO]?\s*[:.]?\s*([A-Z0-9]{4,})',
            r'BATCH\s*[:.]?\s*([A-Z0-9]{4,})',
            r'L[:\s]+([A-Z0-9]{4,})',
        ]
        for pattern in lote_patterns:
            lote = re.search(pattern, text, re.IGNORECASE)
            if lote:
                product["batch"] = lote.group(1)
                break
        
        # 5. FECHA VENCIMIENTO
        fecha_patterns = [
            r'VENC\.?\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})',
            r'VTO\.?\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})',
            r'EXP\.?\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})',
            r'(\d{2}[/-]\d{2}[/-]\d{4})',
        ]
        for pattern in fecha_patterns:
            fecha = re.search(pattern, text, re.IGNORECASE)
            if fecha:
                date_str = fecha.group(1)
                try:
                    parts = re.split(r'[/-]', date_str)
                    if len(parts) == 3:
                        product["expiry_date"] = f"{parts[2]}-{parts[1]}-{parts[0]}"
                        break
                except:
                    pass
        
        # 6. MARCA
        brands = [
            'GLORIA', 'NESTLE', 'COCA COLA', 'PEPSI', 'FLORES', 'LAIVE',
            'DONOFRIO', 'PILSEN', 'CUSQUEÑA', 'AJE', 'BACKUS', 'ALICORP',
            'MONDELEZ', 'UNILEVER', 'PROCTER', 'COLGATE', 'JOHNSON',
            'DOVE', 'PANTENE', 'SAPOLIO', 'BOLIVAR'
        ]
        text_upper = text.upper()
        for brand in brands:
            if brand in text_upper:
                product["brand"] = brand.title()
                break
        
        # 7. CATEGORÍA
        category_keywords = {
            'lácteo': ['LECHE', 'YOGURT', 'QUESO', 'MANTEQUILLA'],
            'bebida': ['GASEOSA', 'JUGO', 'AGUA', 'BEBIDA', 'REFRESCO'],
            'snack': ['GALLETA', 'CHOCOLATE', 'DULCE', 'CARAMELO'],
            'limpieza': ['JABÓN', 'JABON', 'DETERGENTE', 'LIMPIADOR'],
            'cuidado personal': ['SHAMPOO', 'CREMA', 'PASTA', 'DESODORANTE'],
        }
        for category, keywords in category_keywords.items():
            if any(kw in text_upper for kw in keywords):
                product["category"] = category
                break
        
        # 8. NOMBRE (inteligente)
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 8]
        
        product_lines = []
        for line in lines[:5]:
            line_upper = line.upper()
            # Descartar números, fechas, códigos
            if re.match(r'^[\d\s/\-:]+$', line):
                continue
            # Descartar metadatos
            if any(word in line_upper for word in ['CONF', 'FRONT', 'LEFT', 'RIGHT', 'DEBUG']):
                continue
            # Buscar palabras de producto
            if any(word in line_upper for word in ['JABÓN', 'JABON', 'LECHE', 'GASEOSA', 'AGUA', 'GALLETA']):
                product_lines.append(line)
        
        if product_lines:
            best_name = min(product_lines, key=len)
            # ✅ ARREGLADO: Escapar correctamente caracteres especiales
            best_name = re.sub(r'[^\w\sáéíóúñÁÉÍÓÚÑ-]', '', best_name)
            product["name"] = best_name[:80].strip()
        elif lines:
            first_line = re.sub(r'[^\w\sáéíóúñÁÉÍÓÚÑ-]', '', lines[0])
            product["name"] = first_line[:80].strip()
        
        # Fallback: usar categoría + marca
        if not product["name"] and (product["category"] or product["brand"]):
            parts = []
            if product["brand"]:
                parts.append(product["brand"])
            if product["category"]:
                parts.append(product["category"])
            if parts:
                product["name"] = " ".join(parts)
                
        if not product.get("brand"):
            if product.get("category"):
                product["brand"] = f"Sin Marca ({product['category']})"
            else:
                product["brand"] = "Sin Marca"
        
        if not product.get("size"):
            product["size"] = "N/A"
        
        logger.info("🧠 Mock extractor usado")
        logger.debug(f"Mock extraído: {json.dumps(product, indent=2, ensure_ascii=False)}")
        
        return product
    
    def _combine_ocr_text(self, ocr_data: Dict) -> str:
        """Combinar texto OCR sin metadatos"""
        parts = []
        
        for img_type, data in ocr_data.get("images", {}).items():
            text = data.get("text", "").strip()
            if text:
                parts.append(text)  # ← SOLO TEXTO, sin prefijos
        
        return "\n\n".join(parts)
    
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
