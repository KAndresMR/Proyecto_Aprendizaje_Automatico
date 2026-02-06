from fuzzywuzzy import fuzz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Product
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class DeduplicatorService:
    
    SIMILARITY_THRESHOLD = 80  # 80% de similitud
    
    async def find_similar_products(
        self, 
        db: AsyncSession, 
        name: str, 
        brand: str, 
        size: str
    ) -> List[Dict]:
        """Encontrar productos similares en la base de datos"""
        try:
            # 🔹 CAMBIADO: Query asíncrona
            stmt = select(Product).where(Product.is_active == True)
            result = await db.execute(stmt)
            products = result.scalars().all()
            
            similar_products = []
            
            for product in products:
                # Calcular similitud del nombre
                name_similarity = fuzz.ratio(name.lower(), product.name.lower())
                
                # Calcular similitud de marca
                brand_similarity = fuzz.ratio(brand.lower(), product.brand.lower())
                
                # Calcular similitud de tamaño
                size_similarity = fuzz.ratio(size.lower(), product.size.lower())
                
                # Similitud promedio
                avg_similarity = (name_similarity + brand_similarity + size_similarity) / 3
                
                if avg_similarity >= self.SIMILARITY_THRESHOLD:
                    similar_products.append({
                        "id": product.id,
                        "name": product.name,
                        "brand": product.brand,
                        "size": product.size,
                        "similarity": round(avg_similarity / 100, 2)
                    })
            
            # Ordenar por similitud descendente
            similar_products.sort(key=lambda x: x["similarity"], reverse=True)
            
            logger.info(f"✅ Encontrados {len(similar_products)} productos similares")
            
            return similar_products
            
        except Exception as e:
            logger.error(f"❌ Error buscando duplicados: {e}")
            return []

# Instancia global
deduplicator_service = DeduplicatorService()