import re
import logging

from typing import Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class NormalizerService:
    
    # Unidades de peso
    WEIGHT_UNITS = {
        'kg': 1000,
        'g': 1,
        'mg': 0.001,
        'lb': 453.592,
        'oz': 28.3495
    }
    
    # Unidades de volumen
    VOLUME_UNITS = {
        'l': 1000,
        'ml': 1,
        'cl': 10,
        'dl': 100,
        'gal': 3785.41,
        'fl oz': 29.5735
    }
    
    def normalize_size(self, size_str: str) -> Tuple[Optional[float], Optional[str]]:
        """Normalizar tamaño a unidad base"""
        try:
            size_str = size_str.lower().strip()
            
            # Buscar patrón número + unidad
            pattern = r'(\d+(?:\.\d+)?)\s*([a-z]+)'
            match = re.search(pattern, size_str)
            
            if not match:
                logger.warning(f"No se pudo extraer tamaño de: {size_str}")
                return None, None
            
            value = float(match.group(1))
            unit = match.group(2)
            
            # Normalizar peso
            if unit in self.WEIGHT_UNITS:
                normalized_value = value * self.WEIGHT_UNITS[unit]
                return normalized_value, 'g'
            
            # Normalizar volumen
            elif unit in self.VOLUME_UNITS:
                normalized_value = value * self.VOLUME_UNITS[unit]
                return normalized_value, 'ml'
            
            else:
                logger.warning(f"Unidad desconocida: {unit}")
                return value, unit
                
        except Exception as e:
            logger.error(f"Error normalizando tamaño: {e}")
            return None, None
    
    def normalize_date(self, date_str: str) -> Optional[datetime]:
        """Normalizar fecha a formato ISO"""
        try:
            # Patrones comunes de fecha
            patterns = [
                r'(\d{2})/(\d{2})/(\d{4})',  # DD/MM/YYYY
                r'(\d{2})-(\d{2})-(\d{4})',  # DD-MM-YYYY
                r'(\d{4})/(\d{2})/(\d{2})',  # YYYY/MM/DD
                r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            ]
            
            for pattern in patterns:
                match = re.search(pattern, date_str)
                if match:
                    groups = match.groups()
                    
                    # Intentar diferentes formatos
                    try:
                        # DD/MM/YYYY
                        if len(groups[0]) == 2:
                            return datetime.strptime(f"{groups[0]}/{groups[1]}/{groups[2]}", "%d/%m/%Y")
                        # YYYY/MM/DD
                        else:
                            return datetime.strptime(f"{groups[0]}/{groups[1]}/{groups[2]}", "%Y/%m/%d")
                    except:
                        continue
            
            logger.warning(f"No se pudo normalizar fecha: {date_str}")
            return None
            
        except Exception as e:
            logger.error(f"Error normalizando fecha: {e}")
            return None
    
    def extract_product_info(self, ocr_data: Dict) -> Dict:
        """Extraer y normalizar información del producto desde OCR"""
        product_info = {
            "name": None,
            "brand": None,
            "presentation": None,
            "size": None,
            "barcode": None,
            "batch": None,
            "expiry_date": None,
            "price": None
        }
        
        try:
            # Combinar todo el texto
            all_text = ""
            for img_type, data in ocr_data.get("images", {}).items():
                all_text += " " + data.get("text", "")
            
            all_text = all_text.upper()
            
            # Extraer nombre (primera línea significativa)
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            if lines:
                product_info["name"] = lines[0][:100]
            
            # Extraer marca (buscar palabras comunes)
            brand_keywords = ['GLORIA', 'NESTLE', 'COCA COLA', 'PEPSI', 'LAIVE', 'DONOFRIO']
            for keyword in brand_keywords:
                if keyword in all_text:
                    product_info["brand"] = keyword
                    break
            
            # Extraer tamaño
            size_pattern = r'(\d+(?:\.\d+)?)\s*(G|ML|L|KG|OZ|LB)'
            size_match = re.search(size_pattern, all_text)
            if size_match:
                product_info["size"] = f"{size_match.group(1)} {size_match.group(2).lower()}"
            
            # Extraer código de barras
            barcode_pattern = r'\b\d{13}\b|\b\d{12}\b|\b\d{8}\b'
            barcode_match = re.search(barcode_pattern, all_text)
            if barcode_match:
                product_info["barcode"] = barcode_match.group(0)
            
            # Extraer lote
            lote_pattern = r'LOTE?\s*[:.]?\s*([A-Z0-9]+)'
            lote_match = re.search(lote_pattern, all_text)
            if lote_match:
                product_info["batch"] = lote_match.group(1)
            
            # Extraer fecha de vencimiento
            venc_pattern = r'VENC\.?\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})'
            venc_match = re.search(venc_pattern, all_text)
            if venc_match:
                normalized_date = self.normalize_date(venc_match.group(1))
                if normalized_date:
                    product_info["expiry_date"] = normalized_date.date().isoformat()
            
            # Extraer precio
            price_pattern = r'S/\.?\s*(\d+(?:\.\d{2})?)'
            price_match = re.search(price_pattern, all_text)
            if price_match:
                product_info["price"] = float(price_match.group(1))
            
            logger.info(f"✅ Información extraída: {product_info}")
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo información: {e}")
        
        return product_info
