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
        """
        Buscar duplicados con criterios claros:
        
        DUPLICADO = mismo producto físico
        - Barcode exacto = 100% duplicado
        - Marca + Nombre similar + Tamaño EXACTO = duplicado probable
        
        NO DUPLICADO = mismo producto, diferente presentación
        - Marca + Nombre similar + Tamaño DIFERENTE = producto relacionado
        """
        try:
            # ============================================
            # ESTRATEGIA 1: BARCODE EXACTO = 100% MATCH
            # ============================================
            if barcode and len(barcode) >= 8:
                logger.info(f"🔍 Buscando por barcode: {barcode}")
                
                stmt = select(Product).where(
                    Product.is_active == True,
                    Product.barcode == barcode
                )
                result = await db.execute(stmt)
                product = result.scalar_one_or_none()
                
                if product:
                    logger.info(f"✅ Match EXACTO por barcode: {product.name}")
                    return [{
                        "id": product.id,
                        "name": product.name,
                        "brand": product.brand,
                        "size": product.size,
                        "barcode": product.barcode,
                        "similarity": 1.0,
                        "match_type": "barcode",
                        "is_exact_match": True
                    }]
            
            # ============================================
            # ESTRATEGIA 2: MARCA + NOMBRE (FUZZY)
            # ============================================
            if not brand or not name:
                logger.warning("No hay marca/nombre para búsqueda fuzzy")
                return []
            
            logger.info(f"🔍 Buscando por marca + nombre: '{brand}' - '{name}'")
            
            # Filtrar por marca en DB (reduce candidatos)
            stmt = (
                select(Product)
                .where(
                    Product.is_active == True,
                    Product.brand.ilike(f"%{brand}%")
                )
                .limit(50)
            )
            
            result = await db.execute(stmt)
            products = result.scalars().all()
            
            if not products:
                logger.info("No hay candidatos con esa marca")
                return []
            
            logger.info(f"📦 Evaluando {len(products)} candidatos...")
            
            similar_products = []
            
            for product in products:
                # ============================
                # PASO 1: Similitud de nombre
                # ============================
                name_sim = fuzz.ratio(name.lower(), product.name.lower())
                
                if name_sim < 60:
                    continue
                
                # ============================
                # PASO 2: Similitud de marca
                # ============================
                brand_sim = fuzz.ratio(brand.lower(), product.brand.lower())
                
                # ============================
                # PASO 3: TAMAÑO - MATCH EXACTO (NO FUZZY)
                # ============================
                size_match = False
                size_comparison = "unknown"
                
                if size and product.size:
                    # Normalizar espacios y mayúsculas
                    size_normalized = size.lower().replace(" ", "").strip()
                    product_size_normalized = product.size.lower().replace(" ", "").strip()
                    
                    # Match exacto
                    if size_normalized == product_size_normalized:
                        size_match = True
                        size_comparison = "exact"
                    # Muy cercano (ej: "500ml" vs "500 ml" vs "500ML")
                    elif fuzz.ratio(size_normalized, product_size_normalized) >= 95:
                        size_match = True
                        size_comparison = "very_close"
                    else:
                        size_comparison = "different"
                
                # ============================
                # PASO 4: CALCULAR SIMILITUD FINAL
                # ============================
                # Similitud base (solo nombre + marca)
                base_similarity = (name_sim * 0.6 + brand_sim * 0.4)
                
                # ✅ LÓGICA DE CLASIFICACIÓN:
                match_type = None
                final_similarity = 0
                is_exact_match = False
                
                if base_similarity >= 75:  # Umbral de similitud base
                    
                    if size_match:
                        # ✅ DUPLICADO: Mismo nombre, marca Y tamaño
                        final_similarity = base_similarity / 100
                        match_type = "name_brand_size"
                        is_exact_match = True
                        
                    elif not size or not product.size:
                        # ⚠️ DUPLICADO PROBABLE: No tenemos info de tamaño
                        final_similarity = base_similarity / 100
                        match_type = "name_brand_no_size"
                        is_exact_match = False
                        
                    else:
                        # ❌ NO DUPLICADO: Mismo producto, diferente presentación
                        # Ejemplo: "Coca Cola 500ml" vs "Coca Cola 1L"
                        final_similarity = 0.65  # Por debajo del umbral
                        match_type = "related_product"
                        is_exact_match = False
                    
                    similar_products.append({
                        "id": product.id,
                        "name": product.name,
                        "brand": product.brand,
                        "size": product.size,
                        "barcode": product.barcode,
                        "similarity": round(final_similarity, 2),
                        "match_type": match_type,
                        "is_exact_match": is_exact_match,
                        # Detalles para debugging
                        "name_similarity": round(name_sim / 100, 2),
                        "brand_similarity": round(brand_sim / 100, 2),
                        "size_match": size_match,
                        "size_comparison": size_comparison
                    })
            
            # Ordenar por similitud
            similar_products.sort(key=lambda x: x["similarity"], reverse=True)
            
            if similar_products:
                logger.info(
                    f"✅ Encontrados {len(similar_products)} candidatos. "
                    f"Mejor match: {similar_products[0]['name']} "
                    f"(similarity: {similar_products[0]['similarity']}, "
                    f"type: {similar_products[0]['match_type']})"
                )
            else:
                logger.info("No se encontraron duplicados")
            
            return similar_products[:5]  # Top 5
            
        except Exception as e:
            logger.exception(f"❌ Error buscando duplicados: {e}")
            return []
