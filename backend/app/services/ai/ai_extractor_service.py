import logging
import json
import re

from typing import Dict, Union
from google import genai
from backend.app.core.config import settings
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

logger = logging.getLogger(__name__)


logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# ========================================
# IMPORTAR CLIENTES OPCIONALES
# ========================================

try:
    from .llama_client import llama_client
except ImportError:
    logger.warning("⚠️ LlamaClient no disponible")
    llama_client = None

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ OpenAI no disponible. Instala con: pip install openai")
    OPENAI_AVAILABLE = False

class AIExtractorService:
    
    def __init__(self):
        # Cliente Gemini
        self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Cliente OpenAI (si está disponible)
        if OPENAI_AVAILABLE and hasattr(settings, 'OPENAI_API_KEY'):
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.openai_client = None
        
    def extract_product_info(
        self, 
        ocr_data: Union[Dict, str],
        strategy: str = "gemini"
    ) -> Dict:
        """
        Extrae información del producto usando diferentes estrategias de IA.
        
        Args:
            ocr_data: Datos del OCR (dict o JSON string)
            strategy: "gemini" | "openai" | "llama" | "mock"
        
        Returns:
            Dict con información del producto extraída
        """
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
            logger.info(
                f"🧾 OCR combinado | length={len(all_text)} "
                f"| overall_conf={ocr_data.get('overall_confidence', 'N/A')} "
                f"| strategy={strategy}"
            )
            
            # ============================================
            # EJECUTAR LA ESTRATEGIA ELEGIDA
            # ============================================
            if strategy == "gemini":
                result = self._extract_with_gemini(all_text)
                result["_extracted_with"] = "gemini"
                
            elif strategy == "openai":
                result = self._extract_with_openai(all_text)
                result["_extracted_with"] = "openai"
                
            elif strategy == "llama":
                result = self._extract_with_llama(all_text)
                result["_extracted_with"] = "llama"
                
            else:
                logger.warning(f"⚠️ Estrategia desconocida: '{strategy}'. Usando mock.")
                return self._extract_with_mock(all_text)
            
            # Calcular completitud
            result["_completeness"] = self._calculate_completeness(result)
            
            filled_fields = sum(1 for k, v in result.items() 
                              if v and k not in ["nutritional_info", "_extracted_with", "_completeness"])
            logger.info(
                f"✅ Extraction Success | method={result.get('_extracted_with')} "
                f"| filled_fields={filled_fields}/9"
            )
            
            return result

        # ============================================
        # MANEJO DE ERRORES → FALLBACK A MOCK
        # ============================================
        except (ResourceExhausted, ServiceUnavailable) as e:
            logger.warning(
                f"⚠️ {strategy.upper()} no disponible ({e.__class__.__name__}). "
                f"Usando mock directamente."
            )
            return self._extract_with_mock(all_text)

        except json.JSONDecodeError as e:
            logger.warning(
                f"⚠️ {strategy.upper()} devolvió JSON inválido. "
                f"Usando mock directamente."
            )
            return self._extract_with_mock(all_text)

        except Exception as e:
            logger.exception(f"❌ Error inesperado en {strategy}: {e}. Usando mock.")
            return self._extract_with_mock(all_text)
        
    # ========================================
    # GEMINI EXTRACTION
    # ========================================
    def _extract_with_gemini(self, text: str) -> Dict:
        """
        Extracción con Google Gemini.
        
        MODELOS DISPONIBLES (2024-2026):
        - gemini-2.0-flash-exp (experimental, rápido)
        - gemini-1.5-flash (estable, rápido)
        - gemini-1.5-flash-8b (más rápido, menos capacidad)
        - gemini-1.5-pro-002 (más potente, más lento)
        """
        prompt = f"""
Eres un experto en análisis de productos de consumo.

Extrae información estructurada de este texto OCR y responde EXCLUSIVAMENTE en JSON válido.

TEXTO OCR:
El texto puede contener:
- Nombre del producto
- Marca
- Tamaño o contenido neto
- Código de barras
- Fecha de vencimiento
- Precio
- Categoría
- Información nutricional

El texto puede estar desordenado por errores de OCR.

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
- Si detectas múltiples posibles nombres, elige el más representativo
- No inventes información que no esté presente
- Para expiry_date usa formato YYYY-MM-DD
- Para price usa número sin símbolos
"""
        
        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt,
                config={
                    "temperature": 0,
                    "response_mime_type": "application/json"
                }
            )
            
            if not response.text:
                raise ValueError("Respuesta vacía de Gemini")
            
            data = json.loads(response.text.strip())

            # Validar estructura completa
            required_keys = [
                "name", "brand", "presentation", "size", "barcode",
                "batch", "expiry_date", "price", "category", "nutritional_info"
            ]

            if not all(key in data for key in required_keys):
                raise ValueError("Estructura incompleta de Gemini")

            return data
            
        except Exception as e:
            logger.error(f"Error en Gemini: {e}")
            raise
    
    # ========================================
    # OPENAI/CHATGPT EXTRACTION
    # ========================================
    def _extract_with_openai(self, text: str) -> Dict:
        """
        Extracción con OpenAI ChatGPT.
        
        MODELOS DISPONIBLES:
        - gpt-4o (recomendado, más preciso)
        - gpt-4o-mini (más rápido, más barato)
        - gpt-4-turbo (anterior generación)
        - gpt-3.5-turbo (más barato, menos preciso)
        """
        if not self.openai_client:
            raise ServiceUnavailable("OpenAI no está configurado")
        
        prompt = f"""
Eres un experto en análisis de productos de consumo.

Extrae información estructurada de este texto OCR y responde EXCLUSIVAMENTE en JSON válido.

TEXTO OCR:
{text}

Devuelve EXACTAMENTE esta estructura JSON (sin markdown, sin backticks):
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
- Si no sabes un valor, usa null
- NO agregues texto fuera del JSON
- Para expiry_date usa formato YYYY-MM-DD
- Para price usa número sin símbolos
- Responde SOLO con JSON, sin explicaciones
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Puedes cambiar a "gpt-4o" para mejor calidad
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un asistente que extrae datos de productos. Respondes SOLO con JSON válido, sin texto adicional."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"}  # Forzar JSON válido
            )
            
            content = response.choices[0].message.content
            
            if not content:
                raise ValueError("Respuesta vacía de OpenAI")
            
            # Limpiar posibles markdown backticks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            data = json.loads(content)

            # Validar estructura completa
            required_keys = [
                "name", "brand", "presentation", "size", "barcode",
                "batch", "expiry_date", "price", "category", "nutritional_info"
            ]

            if not all(key in data for key in required_keys):
                raise ValueError("Estructura incompleta de OpenAI")

            return data
            
        except Exception as e:
            logger.error(f"Error en OpenAI: {e}")
            raise
    
    # ========================================
    # LLAMA EXTRACTION
    # ========================================
    def _extract_with_llama(self, text: str) -> Dict:
        """Extracción con Llama (local o API)"""
        if not llama_client or not llama_client.llm:
            raise ServiceUnavailable("Llama no está disponible")
        logger.debug(f"Lo que nos llega:\n{text[:500]}")
        try:
            result = llama_client.extract(text)
            
            # Validar estructura completa
            required_keys = [
                "name", "brand", "presentation", "size", "barcode",
                "batch", "expiry_date", "price", "category", "nutritional_info"
            ]
            
            if not all(key in result for key in required_keys):
                raise ValueError("Estructura incompleta de Llama")
            
            return result
            
        except Exception as e:
            logger.error(f"Error en Llama: {e}")
            raise
    
    # ========================================
    # MOCK EXTRACTION (REGEX FALLBACK)
    # ========================================
    def _extract_with_mock(self, text: str) -> Dict:
        """Extracción con regex (fallback cuando las IAs fallan)"""
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
    
    # ========================================
    # UTILIDADES
    # ========================================
    def _combine_ocr_text(self, ocr_data: Dict) -> str:
        """Combina texto de todas las imágenes OCR"""
        parts = []
        
        for img_type, data in ocr_data.get("images", {}).items():
            text = data.get("text", "").strip()
            if text:
                parts.append(text)
        
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

    def _calculate_completeness(self, product: Dict) -> float:
        """Calcula el % de campos completados"""
        total_fields = 9  # sin contar nutritional_info interno
        filled = 0

        for key in ["name", "brand", "presentation", "size",
                    "barcode", "batch", "expiry_date",
                    "price", "category"]:
            if product.get(key):
                filled += 1

        return filled / total_fields


# ========================================
# INSTANCIA GLOBAL
# ========================================
ai_extractor_service = AIExtractorService()
