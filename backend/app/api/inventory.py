import logging
import asyncio
import time
import json

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.schemas import (
    ProductCreate, ProductResponse, OCRResult, 
    SaveProductResponse, BatchResponse
)
from backend.app.models.models import Product, ProductBatch, OCRLog
from backend.app.services import (
    ocr_service,
    image_service,
    normalizer_service,
    deduplicator_service,
    ai_extractor_service
    
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/from-images", response_model=OCRResult)
async def process_images_from_camera(
    photo_0: Optional[UploadFile] = File(None),
    photo_1: Optional[UploadFile] = File(None),
    photo_2: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Pipeline optimizado:
    1. Guardado paralelo
    2. OCR paralelo (con preprocesamiento interno)
    3. Normalización + Deduplicación en paralelo
    """
    try:
        logger.info("📸 Iniciando procesamiento optimizado...")
        start_total = time.time()
        
        # Recopilar archivos
        files = []
        image_types = []
        
        if photo_0:
            files.append(photo_0)
            image_types.append("front")
        if photo_1:
            files.append(photo_1)
            image_types.append("left")
        if photo_2:
            files.append(photo_2)
            image_types.append("right")
        if not files:
            raise HTTPException(status_code=400, detail="No se recibieron imágenes")
        
        # 1️⃣ Guardar imágenes EN PARALELO
        logger.info("💾 Guardando imágenes...")
        start = time.time()
        saved_images = await image_service.save_multiple_images_async(files, image_types)
        logger.info(f"⏱️ Guardado: {time.time()-start:.2f}s")
        
        # 2️⃣ OCR PARALELO
        logger.info("🔍 Ejecutando OCR optimizado...")
        start = time.time()
        ocr_data = ocr_service.extract_from_multiple_images(saved_images)
        logger.info(f"⏱️ OCR: {time.time()-start:.2f}s")
        
        # 3️⃣ EXTRACCIÓN CON IA (SOLO UNA VEZ)
        logger.info("🤖 Extrayendo información con Gemini...")
        start = time.time()
        product_info = await asyncio.to_thread(
            ai_extractor_service.extract_product_info,
            ocr_data
        )
        logger.info(f"⏱️ IA Extracción: {time.time()-start:.2f}s")
        
        # 4️⃣ BUSCAR DUPLICADOS (con barcode primero)
        logger.info("🔍 Buscando duplicados...")
        duplicates = []
        
        if product_info.get("barcode") or product_info.get("name"):
            duplicates = await deduplicator_service.find_similar_products(
                db=db,
                name=product_info.get("name", ""),
                brand=product_info.get("brand", ""),
                barcode=product_info.get("barcode"),
                size=product_info.get("size", "")
            )
        
        # 5️⃣ SI HAY DUPLICADO EXACTO, RETORNAR EXISTENTE
        if duplicates and duplicates[0].get("similarity", 0) >= 0.95:
            logger.info(f"🔄 Producto duplicado detectado: {duplicates[0]['name']}")
            existing_id = duplicates[0]["id"]
            
            # Cargar producto completo con imágenes
            stmt = select(Product).where(Product.id == existing_id)
            result = await db.execute(stmt)
            product = result.scalar_one()
            
            # Guardar log del OCR
            ocr_log = OCRLog(
                image_path=",".join(saved_images.values()),
                raw_text=str(ocr_data),
                confidence=ocr_data["overall_confidence"],
                ocr_engine=ocr_service.engine
            )
            db.add(ocr_log)
            await db.commit()
            
            total_time = time.time() - start_total
            logger.info(f"✅ Duplicado procesado en {total_time:.2f}s")
            
            return OCRResult(
                raw_text=ocr_data,
                confidence=ocr_data["overall_confidence"],
                product={
                    "name": product.name,
                    "brand": product.brand,
                    "presentation": product.presentation,
                    "size": product.size,
                    "barcode": product.barcode,
                    "batch": product_info.get("batch"),  # Del OCR nuevo
                    "expiry_date": product_info.get("expiry_date"),  # Del OCR nuevo
                    "price": product_info.get("price"),  # Del OCR nuevo
                    "image_front": product.image_front,
                    "image_left": product.image_left,
                    "image_right": product.image_right,
                },
                missing_fields=[],
                duplicates=duplicates,
                is_duplicate=True
            )
        
        # 6️⃣ PRODUCTO NUEVO: Agregar rutas de imágenes
        product_info["image_front"] = saved_images.get("front")
        product_info["image_left"] = saved_images.get("left")
        product_info["image_right"] = saved_images.get("right")
        
        # 7️⃣ DETECTAR CAMPOS FALTANTES
        required_fields = ["name", "brand", "size"]
        missing_fields = [
            field for field in required_fields
            if not product_info.get(field)
        ]
        
        # Defaults para campos opcionales
        for field in ["presentation", "barcode", "batch", "expiry_date", "price"]:
            product_info.setdefault(field, None)
        
        # 8️⃣ GUARDAR LOG
        formatted_ocr = json.dumps(ocr_data, indent=2, ensure_ascii=False)
        ocr_log = OCRLog(
            image_path=",".join(saved_images.values()),
            raw_text= formatted_ocr, # raw_text=str(ocr_data),
            confidence=ocr_data["overall_confidence"],
            ocr_engine=ocr_service.engine
        )
        logger.info("OCR DATA:\n%s", formatted_ocr)
        db.add(ocr_log)
        await db.commit()
        
        total_time = time.time() - start_total
        logger.info(f"✅ Procesamiento completado en {total_time:.2f}s")
        logger.info(
            f"📊 Producto: {product_info.get('name', 'N/A')} | "
            f"Marca: {product_info.get('brand', 'N/A')} | "
            f"Tamaño: {product_info.get('size', 'N/A')} | "
            f"Duplicados: {len(duplicates)}"
        )
        
        return OCRResult(
            raw_text=ocr_data,
            confidence=ocr_data["overall_confidence"],
            product=product_info,
            missing_fields=missing_fields,
            duplicates=duplicates,
            is_duplicate=False
        )
        
    except Exception as e:
        logger.error(f"❌ Error en procesamiento: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save", response_model=SaveProductResponse)
async def save_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Guardar producto en la base de datos.
    Crea el producto, batch e imágenes asociadas.
    """
    try:
        logger.info(f"💾 Guardando producto: {product_data.name}")
        
        # Normalizar tamaño
        normalized_value, normalized_unit = normalizer_service.normalize_size(
            product_data.size
        )
        
        # Crear producto
        new_product = Product(
            name=product_data.name,
            brand=product_data.brand,
            presentation=product_data.presentation,
            size=product_data.size,
            normalized_size_value=normalized_value,
            normalized_size_unit=normalized_unit,
            barcode=product_data.barcode,
            description=product_data.description
        )
        
        db.add(new_product)
        await db.flush()  # Para obtener el ID
        
        # Crear batch si hay información
        new_batch = None
        if any([
            product_data.batch_number,
            product_data.expiry_date,
            product_data.price
        ]):
            new_batch = ProductBatch(
                product_id=new_product.id,
                batch_number=product_data.batch_number,
                expiry_date=product_data.expiry_date,
                manufacturing_date=product_data.manufacturing_date,
                price=product_data.price
            )
            db.add(new_batch)
        
        await db.commit()
        await db.refresh(new_product)
        
        logger.info(f"✅ Producto guardado con ID: {new_product.id}")
        
        # 🔹 CAMBIADO: model_validate en lugar de from_orm
        return SaveProductResponse(
            id=new_product.id,
            product=ProductResponse.model_validate(new_product),
            batch=BatchResponse.model_validate(new_batch) if new_batch else None,
            message=f"Producto '{new_product.name}' registrado exitosamente"
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error guardando producto: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products", response_model=List[ProductResponse])
async def get_all_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Obtener todos los productos"""
    stmt = (
        select(Product)
        .where(Product.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    products = result.scalars().all()
    return products


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtener un producto por ID"""
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    return product