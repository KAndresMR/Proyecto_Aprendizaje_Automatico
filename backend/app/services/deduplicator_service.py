import logging

from fuzzywuzzy import fuzz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.models import Product
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class DeduplicatorService:
    def __init__(self, threshold: int = 0.85):
        self.SIMILARITY_THRESHOLD = threshold
    
    async def find_similar_products(
        self, 
        db: AsyncSession, 
        name: str, 
        brand: str, 
        barcode: Optional[str] = None,
        size: str = ""
    ) -> List[Dict]:
        """Buscar duplicados"""
        # 1. Match por barcode (exacto)
        # 2. Filtrar por marca en DB
        # 3. Fuzzy matching solo con candidatos
        try:
            # ESTRATEGIA 1: Buscar por barcode (MÁS RÁPIDO)
            if barcode and len(barcode) >= 8:
                logger.info(f"🔍 Buscando por barcode: {barcode}")
                
                stmt = select(Product).where(
                    Product.is_active == True,
                    Product.barcode == barcode
                )
                result = await db.execute(stmt)
                product = result.scalar_one_or_none()
                
                if product:
                    logger.info(f"✅ Match exacto por barcode: {product.name}")
                    return [{
                        "id": product.id,
                        "name": product.name,
                        "brand": product.brand,
                        "size": product.size,
                        "barcode": product.barcode,
                        "similarity": 1.0
                    }]
            # 🔹 ESTRATEGIA 2: Buscar por marca + nombre
            if not brand or not name:
                logger.warning("No hay marca/nombre para búsqueda fuzzy")
                return []
            
            logger.info(f"🔍 Buscando por marca: {brand}")
            
            # Filtrar por marca en DB (reduce candidatos 90%)
            stmt = (
                select(Product)
                .where(
                    Product.is_active == True,
                    Product.brand.ilike(f"%{brand}%")
                )
                .limit(50)  # Máximo 50 candidatos
            )
            
            result = await db.execute(stmt)
            products = result.scalars().all()
            
            if not products:
                logger.info("No hay candidatos con esa marca")
                return []
            
            logger.info(f"📦 Evaluando {len(products)} candidatos...")
            
            similar_products = []
            
            for product in products:
                # Similitud de nombre
                name_sim = fuzz.ratio(name.lower(), product.name.lower())
                
                # Early exit
                if name_sim < 60:
                    continue
                
                # Similitud de marca (debería ser alta ya que filtramos)
                brand_sim = fuzz.ratio(brand.lower(), product.brand.lower())
                
                # Similitud de tamaño (opcional)
                size_sim = 0
                if size and product.size:
                    size_sim = fuzz.ratio(size.lower(), product.size.lower())
                
                # Promedio ponderado (nombre vale más)
                avg_sim = (name_sim * 0.5 + brand_sim * 0.3 + size_sim * 0.2)
                
                if avg_sim >= self.SIMILARITY_THRESHOLD:
                    similar_products.append({
                        "id": product.id,
                        "name": product.name,
                        "brand": product.brand,
                        "size": product.size,
                        "barcode": product.barcode,
                        "similarity": round(avg_sim / 100, 2)
                    })
            
            similar_products.sort(key=lambda x: x["similarity"], reverse=True)
            
            logger.info(f"✅ Encontrados {len(similar_products)} duplicados potenciales")
            
            return similar_products[:5]  # Top 5
        except Exception as e:
            logger.error(f"❌ Error buscando duplicados: {e}")
            return []
